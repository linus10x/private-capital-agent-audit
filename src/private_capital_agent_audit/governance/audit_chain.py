"""P3 — Tamper-evident hash-chain ledger.

Built to the *corrected* primitive standard (do NOT replicate the upstream
defect where the verifier seeds the legacy ``"0"*64`` sentinel unconditionally
and so raises a false TAMPER on a clean deployer-keyed chain):

* A hardened chain (``deployer_id`` supplied) writes a **deployer-keyed genesis
  event #0** whose payload carries ``deployer_id`` + ``chain_creation_iso``, and
  whose ``prev_hash`` is :func:`_compute_genesis_hash`. ``verify()`` /
  ``verify_strict()`` **branch the genesis prev-hash seed** on whether event #0
  is that deployer-keyed genesis event (re-deriving the seed from its OWN
  payload) or a legacy chain (``"0"*64`` sentinel). **Both verify ``True``**, and
  a chain re-opened from disk re-derives the correct seed from the stored genesis
  event (no wall-clock dependence).
* End-to-end *regeneration* (rebuilding the whole chain with internally
  consistent hashes) is detectable via an external **witness anchor** that is
  **non-optional in production mode** — see :class:`WitnessRegister` and
  :meth:`AuditChain.verify_regeneration_resistant`.

PRODUCTION MODE is a named strict opt-in (``mode="production"``). In it a
missing witness register **fails closed** (the constructor refuses to start).
The default ``mode="advisory"`` constructor stays backward-compatible and is
labeled advisory in code and docs — it does NOT fail closed.

For advisers handling SEC books-and-records (17 CFR 275.204-2), and where
dually-registered the SEC Rule 17a-4 electronic-records-retention regime, pair
this chain with a WORM-backed store and a trusted timestamp source; the hash
chain is the integrity control, retention/WORM is a storage-layer concern the
deployer wires (see ``docs/FAILURE-MODES.md``).
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from private_capital_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

GENESIS_HASH = "0" * 64
GENESIS_DOMAIN_SEPARATOR = "private-capital-agent-audit/genesis/v1"
GENESIS_VERSION = "v1"
GENESIS_AGENT_ID = "private-capital-audit-chain"


def _compute_genesis_hash(deployer_id: str, chain_creation_iso: str) -> str:
    """Deployer-keyed seed for the genesis prev-hash.

    ``SHA-256(domain_separator/deployer_id/chain_creation_iso)``. Binding the
    seed to a deployer identity means two deployers' chains cannot be
    transplanted into one another without detection.
    """
    payload = f"{GENESIS_DOMAIN_SEPARATOR}/{deployer_id}/{chain_creation_iso}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_deployer_keyed_genesis(event: AuditEvent) -> bool:
    """True when ``event`` is a deployer-keyed genesis event #0."""
    return (
        event.event_type is AuditEventType.GENESIS
        and event.agent_id == GENESIS_AGENT_ID
        and isinstance(event.payload, dict)
        and event.payload.get("genesis_version") == GENESIS_VERSION
        and "deployer_id" in event.payload
        and "chain_creation_iso" in event.payload
    )


def _seed_for_first(first_event: AuditEvent) -> str:
    """The prev-hash seed the chain's FIRST event must carry — branched.

    Hardened (deployer-keyed genesis present): re-derive from the genesis
    event's OWN payload, so a chain loaded from disk with no constructor
    ``deployer_id`` still validates. Legacy: the ``"0"*64`` sentinel.
    """
    if _is_deployer_keyed_genesis(first_event):
        return _compute_genesis_hash(
            str(first_event.payload["deployer_id"]),
            str(first_event.payload["chain_creation_iso"]),
        )
    return GENESIS_HASH


class AuditChainTamperError(Exception):
    """Raised by :meth:`AuditChain.verify_strict` on any inconsistency."""


@runtime_checkable
class WitnessRegister(Protocol):
    """External anchor seam (Rekor / OpenTimestamps / a regulator log).

    The reference :class:`InMemoryWitnessRegister` is for tests and local demos
    only; a production deployer wires a real transparency log here. The contract
    is a **checkpoint log**: :meth:`anchor` records a ``(sequence, head_hash)``
    checkpoint outside the chain's own storage, and :meth:`checkpoints` returns
    every checkpoint ever anchored. Recording the *sequence* (not just the head)
    is what lets a verifier detect **truncation below an anchor** and
    **regeneration**: a chain truncated below an anchored sequence, or rewritten
    at an anchored position, no longer matches the external checkpoint.
    """

    def anchor(self, head_hash: str, sequence: int, timestamp: str) -> dict[str, Any]: ...

    def checkpoints(self) -> list[tuple[int, str]]: ...


class InMemoryWitnessRegister:
    """Reference, in-memory :class:`WitnessRegister`.

    NOT durable across processes — labeled a reference. A real deployment must
    substitute an external transparency log; this exists so the regeneration and
    truncation invariants are testable without network access.
    """

    def __init__(self) -> None:
        self._checkpoints: list[tuple[int, str]] = []

    def anchor(self, head_hash: str, sequence: int, timestamp: str) -> dict[str, Any]:
        self._checkpoints.append((sequence, head_hash))
        return {
            "head_hash": head_hash,
            "sequence": sequence,
            "timestamp": timestamp,
            "witness": "in-memory-reference",
        }

    def checkpoints(self) -> list[tuple[int, str]]:
        return list(self._checkpoints)


class AuditChain:
    """Append-only, hash-chained, tamper-evident ledger.

    Parameters
    ----------
    log_file:
        Optional JSONL path; events are appended on write and loaded on init.
    deployer_id, chain_creation_iso:
        When ``deployer_id`` is supplied the chain is *hardened* — a deployer-
        keyed genesis event #0 is written and the seed is deployer-keyed. When
        ``None`` the chain is *legacy* and seeds from the ``"0"*64`` sentinel.
        Both verify ``True``. ``chain_creation_iso`` defaults to now; pass an
        explicit value to make the genesis event reproducible across hosts.
    witness_register:
        External anchor seam. Required in ``production`` mode.
    mode:
        ``"advisory"`` (default, backward-compatible, does not fail closed) or
        ``"production"`` (strict opt-in: a missing witness register raises at
        construction).
    """

    GENESIS_HASH = GENESIS_HASH

    def __init__(
        self,
        *,
        log_file: Path | None = None,
        deployer_id: str | None = None,
        chain_creation_iso: str | None = None,
        witness_register: WitnessRegister | None = None,
        mode: str = "advisory",
    ) -> None:
        if mode not in ("advisory", "production"):
            raise ValueError(f"mode must be 'advisory' or 'production', got {mode!r}")
        if mode == "production" and witness_register is None:
            # Fail closed: P3 production mode requires a non-optional witness anchor.
            raise ValueError(
                "production mode requires a witness_register (fail-closed); "
                "the witness anchor is non-optional in production mode"
            )
        self._mode = mode
        self._deployer_id = deployer_id
        self._chain_creation_iso = chain_creation_iso or _now_iso()
        self._witness = witness_register
        self._log_file = log_file
        self._store: list[AuditEvent] = []
        self._tail_corrupt = False  # set by _load on a malformed trailing line
        self._lock = threading.RLock()
        if log_file is not None and log_file.exists():
            self._load(log_file)
        # Seed the genesis event only for a fresh hardened chain (empty store).
        if deployer_id is not None and not self._store:
            self._seed_genesis_event()

    # -- properties -------------------------------------------------------

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_hardened(self) -> bool:
        """True when the chain is deployer-keyed (not a legacy sentinel chain)."""
        return self._deployer_id is not None

    def __len__(self) -> int:
        return len(self._store)

    def events(self) -> list[AuditEvent]:
        """A shallow copy of the event list for reading.

        The :class:`AuditEvent` objects are frozen, but ``payload`` is a dict —
        do not mutate ``event.payload`` in place; any such mutation invalidates
        the event's hash and is reported by :meth:`verify` as tamper.
        """
        return list(self._store)

    # -- genesis ----------------------------------------------------------

    def genesis_seed(self) -> str:
        """The prev-hash seed for entry #0, per this chain's construction params."""
        if self._deployer_id is not None:
            return _compute_genesis_hash(self._deployer_id, self._chain_creation_iso)
        return GENESIS_HASH

    def _seed_genesis_event(self) -> None:
        assert self._deployer_id is not None
        seed = _compute_genesis_hash(self._deployer_id, self._chain_creation_iso)
        genesis = AuditEvent(
            sequence=0,
            event_type=AuditEventType.GENESIS,
            autonomy_level=AutonomyLevel.A0_INFORMATIONAL,
            agent_id=GENESIS_AGENT_ID,
            payload={
                "deployer_id": self._deployer_id,
                "chain_creation_iso": self._chain_creation_iso,
                "genesis_version": GENESIS_VERSION,
            },
            timestamp=self._chain_creation_iso,  # deterministic — no wall-clock read
            prev_hash=seed,
        ).with_hash()
        self._store.append(genesis)
        if self._log_file is not None:
            self._persist(genesis)

    def chain_head(self) -> str:
        """Current head hash; the genesis seed for an empty (legacy) chain."""
        with self._lock:
            if not self._store:
                return self.genesis_seed()
            return self._store[-1].event_hash

    # -- append -----------------------------------------------------------

    def append(
        self,
        event_type: AuditEventType,
        autonomy_level: AutonomyLevel,
        agent_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> AuditEvent:
        """Append one event, chaining it to the current head.

        The ``payload`` is deep-copied so a caller who reuses or mutates the dict
        they passed cannot retroactively invalidate the stored (hashed) event.
        """
        with self._lock:
            event = AuditEvent(
                sequence=len(self._store),
                event_type=event_type,
                autonomy_level=autonomy_level,
                agent_id=agent_id,
                payload=copy.deepcopy(payload),
                timestamp=_now_iso(),
                prev_hash=self.chain_head(),
                actor_id=actor_id,
            ).with_hash()
            self._store.append(event)
            if self._log_file is not None:
                self._persist(event)
            return event

    # -- verification (corrected: branched seed) --------------------------

    def verify(self) -> bool:
        """Soft variant — replay the chain, return ``False`` on any mismatch.

        Checks, for every event: its own ``event_hash`` recomputes, its
        ``prev_hash`` links to the prior event (branched genesis seed via
        :func:`_seed_for_first`), and its ``sequence`` is contiguous ``0..n-1``
        (so reordering or an interior gap is caught independently of the link).
        A chain whose persisted tail line was malformed is never reported clean.
        """
        with self._lock:
            if self._tail_corrupt:
                return False
            prev: str | None = None
            for index, event in enumerate(self._store):
                if prev is None:
                    prev = _seed_for_first(event)
                if event.sequence != index:
                    return False
                if event.event_hash != event.compute_hash():
                    return False
                if event.prev_hash != prev:
                    return False
                prev = event.event_hash
            return True

    def verify_strict(self) -> None:
        """Raise :class:`AuditChainTamperError` on the first inconsistency."""
        with self._lock:
            if self._tail_corrupt:
                raise AuditChainTamperError(
                    "the persisted ledger's trailing line was malformed; the valid "
                    "prefix was loaded but the chain cannot be certified clean"
                )
            prev: str | None = None
            for index, event in enumerate(self._store):
                if prev is None:
                    prev = _seed_for_first(event)
                if event.sequence != index:
                    raise AuditChainTamperError(
                        f"sequence mismatch at index {index}: event carries "
                        f"sequence {event.sequence} (reorder or gap)"
                    )
                if event.event_hash != event.compute_hash():
                    raise AuditChainTamperError(
                        f"event_hash mismatch at index {index}: stored "
                        f"{event.event_hash[:12]}… != recomputed "
                        f"{event.compute_hash()[:12]}…"
                    )
                if event.prev_hash != prev:
                    raise AuditChainTamperError(
                        f"prev_hash mismatch at index {index}: links to "
                        f"{event.prev_hash[:12]}… expected {prev[:12]}…"
                    )
                prev = event.event_hash

    # -- witness anchoring (regeneration resistance) ----------------------

    def anchor_to_witness(self) -> dict[str, Any]:
        """Append a ``WITNESS_ANCHOR`` event and anchor IT to the external witness.

        The anchor event is appended FIRST (committing the prior head in its
        payload), then the anchor event's OWN ``(sequence, event_hash)`` is
        recorded to the external witness. This is deliberate: it makes the
        witnessed checkpoint the chain's *current tail*, so a rewrite-and-restamp
        of the last event is caught by :meth:`verify_regeneration_resistant`
        (the external checkpoint no longer matches). Anchoring the *pre-anchor*
        head instead would leave the anchor event itself an unwitnessed,
        forgeable tail. The residual is unchanged and irreducible: events
        appended *after* this anchor are unwitnessed until the next anchor.
        """
        if self._witness is None:
            raise ValueError("no witness_register configured; cannot anchor")
        with self._lock:
            prior_head = self.chain_head()
            anchor_event = self.append(
                AuditEventType.WITNESS_ANCHOR,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id=GENESIS_AGENT_ID,
                payload={"anchored_prior_head": prior_head},
            )
            return self._witness.anchor(anchor_event.event_hash, anchor_event.sequence, _now_iso())

    def head_is_witnessed(self) -> bool:
        """True when the current chain head matches the most-recent witness checkpoint.

        Use in production to confirm nothing has been appended since the last
        anchor — i.e. the tail is committed externally and cannot be silently
        rewritten or truncated. ``False`` means there are unwitnessed tail events;
        call :meth:`anchor_to_witness` to commit them.
        """
        if self._witness is None:
            raise ValueError("no witness_register configured")
        with self._lock:
            checkpoints = self._witness.checkpoints()
            if not checkpoints or not self._store:
                return False
            seq, head = checkpoints[-1]
            return seq == self._store[-1].sequence and head == self._store[-1].event_hash

    def verify_regeneration_resistant(self) -> bool:
        """Detect regeneration AND truncation-below-an-anchor via the witness.

        ``verify()`` only proves *internal* consistency — an attacker who rebuilds
        the chain, or who drops a suffix, produces an internally consistent (but
        different or shorter) chain that ``verify()`` accepts. Every external
        checkpoint ``(sequence, head)`` must still match the current chain: the
        event at that ``sequence`` must exist and carry that ``event_hash``. This
        catches full regeneration (the head differs), truncation below any
        anchored sequence (the event is gone), and a rewrite at an anchored
        position.

        **Residual limit (documented):** events appended *after the most recent
        anchor* and then dropped cannot be detected internally — that is the
        irreducible minimum for any append-only log, and the mitigation is anchor
        cadence (anchor frequently; for the strictest assurance, anchor on every
        append). See ``FAILURE-MODES.md``.
        """
        if self._witness is None:
            raise ValueError("no witness_register configured; cannot prove regeneration resistance")
        with self._lock:
            n = len(self._store)
            for sequence, head in self._witness.checkpoints():
                if sequence >= n or self._store[sequence].event_hash != head:
                    return False
            return True

    # -- persistence ------------------------------------------------------

    def _persist(self, event: AuditEvent) -> None:
        assert self._log_file is not None
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        with self._log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")

    def _load(self, log_file: Path) -> None:
        """Load a persisted JSONL ledger, degrading gracefully on a torn tail.

        A crash/power-loss mid-append can leave a malformed *trailing* line. That
        is recoverable: load the valid prefix and set ``_tail_corrupt`` so the
        chain refuses to certify clean (``verify()`` False / ``verify_strict``
        raises) rather than bricking on construction. A malformed *interior* line
        is hard tamper and raises immediately.
        """
        lines = [
            ln.strip() for ln in log_file.read_text(encoding="utf-8").splitlines() if ln.strip()
        ]
        for i, line in enumerate(lines):
            try:
                self._store.append(AuditEvent.from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                if i == len(lines) - 1:
                    # Torn trailing line — recoverable; load the prefix and flag.
                    self._tail_corrupt = True
                    break
                raise AuditChainTamperError(
                    f"malformed interior ledger line at index {i}: {exc}"
                ) from exc
