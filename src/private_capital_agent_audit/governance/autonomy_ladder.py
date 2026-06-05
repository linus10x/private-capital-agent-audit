"""P1 — Autonomy-ladder level gate (A0→A4 promotion control).

Built to the *corrected* primitive standard:

* The gate **REFUSES promotion** when any control required by a rung at or below
  the target is unmet (monotonic; it also refuses rung-skipping unless
  explicitly allowed).
* It requires **independent attestation** of its inputs — it does not simply
  trust caller-asserted booleans. Each lower-level control must be presented as
  a :class:`ControlAttestation` that an :class:`AttestationVerifier` confirms is
  genuine *and* independent of the requesting agent.
* In the default ``advisory`` mode (no verifier wired) the gate still evaluates,
  but the decision is **labeled advisory** (``verified=False``) — it never
  *implies* enforcement it cannot deliver. ``production`` mode requires a
  verifier and fails closed without one.

Regulatory anchors: EU AI Act Art. 14 (human oversight); the duty-of-care /
duty-of-loyalty fiduciary standard the SEC articulated for investment advisers
in the 2019 *Commission Interpretation Regarding Standard of Conduct for
Investment Advisers* (Release No. IA-5248, under Advisers Act §206). Promoting
an agent to a tier where it can make consequential fiduciary writes (orders,
allocations) without the lower-rung controls attested is exactly the gap a
duty-of-care examination probes. See ``docs/regulatory/obligation_map.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from private_capital_agent_audit.schemas.audit_event import AutonomyLevel

# Controls a rung requires before an agent may operate at it. A0 requires none.
LEVEL_REQUIRED_CONTROLS: dict[AutonomyLevel, tuple[str, ...]] = {
    AutonomyLevel.A0_INFORMATIONAL: (),
    AutonomyLevel.A1_ASSISTED: ("human_approval_workflow",),
    AutonomyLevel.A2_DELEGATED: ("action_envelope", "sampled_human_review"),
    AutonomyLevel.A3_SUPERVISED_AUTONOMOUS: ("sovereign_veto", "audit_chain"),
    AutonomyLevel.A4_PRODUCTION_AUTONOMOUS: ("orchestration_guard", "escalation_path"),
}


@dataclass(frozen=True)
class ControlAttestation:
    """An attestation that a named control is in place at a given rung.

    ``attester_id`` is the independent party vouching for the control; the
    verifier checks both that the attestation is genuine and that the attester
    is not the requesting agent itself.
    """

    control_id: str
    level: AutonomyLevel
    attester_id: str
    statement: str
    signature: str = ""


@runtime_checkable
class AttestationVerifier(Protocol):
    """Seam that confirms an attestation is genuine and independent.

    A deployer wires real signature/identity verification here. ``verify``
    returns ``True`` only when the attestation is authentic AND ``attester_id``
    is independent of ``requesting_agent_id``.
    """

    def verify(self, attestation: ControlAttestation, requesting_agent_id: str) -> bool: ...


@dataclass(frozen=True)
class PromotionDecision:
    """The outcome of a promotion evaluation."""

    approved: bool
    current_level: AutonomyLevel
    requested_level: AutonomyLevel
    granted_level: AutonomyLevel
    missing_controls: tuple[str, ...] = ()
    unverified_controls: tuple[str, ...] = ()
    verified: bool = False
    reasons: tuple[str, ...] = field(default_factory=tuple)


class AutonomyLadder:
    """The promotion gate.

    Parameters
    ----------
    verifier:
        Independent-attestation verifier. Required in ``production`` mode.
    mode:
        ``"advisory"`` (default; labeled advisory) or ``"production"`` (strict:
        a missing verifier raises at construction).
    allow_skip:
        When ``False`` (default) a request to jump more than one rung is refused
        even if all controls are attested.
    """

    def __init__(
        self,
        *,
        verifier: AttestationVerifier | None = None,
        mode: str = "advisory",
        allow_skip: bool = False,
    ) -> None:
        if mode not in ("advisory", "production"):
            raise ValueError(f"mode must be 'advisory' or 'production', got {mode!r}")
        if mode == "production" and verifier is None:
            raise ValueError(
                "production mode requires an attestation verifier (fail-closed); "
                "the gate will not enforce on caller-asserted booleans alone"
            )
        self._verifier = verifier
        self._mode = mode
        self._allow_skip = allow_skip

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_advisory(self) -> bool:
        return self._verifier is None

    def evaluate_promotion(
        self,
        *,
        requesting_agent_id: str,
        current_level: AutonomyLevel,
        requested_level: AutonomyLevel,
        attestations: list[ControlAttestation],
    ) -> PromotionDecision:
        """Decide whether ``requesting_agent_id`` may move to ``requested_level``."""
        reasons: list[str] = []

        # A demotion or no-op is always allowed (controls only gate promotion up).
        if requested_level.rank <= current_level.rank:
            return PromotionDecision(
                approved=True,
                current_level=current_level,
                requested_level=requested_level,
                granted_level=requested_level,
                verified=self._verifier is not None,
                reasons=("non-promotion (demotion or no-op) — always permitted",),
            )

        if not self._allow_skip and requested_level.rank > current_level.rank + 1:
            reasons.append(
                f"rung-skip refused: {current_level.value}->{requested_level.value} "
                "skips a rung (allow_skip=False)"
            )

        # Which control_ids are attested, and which of those verify as independent?
        attested: set[str] = set()
        unverified: set[str] = set()
        for att in attestations:
            attested.add(att.control_id)
            if self._verifier is not None and not self._verifier.verify(att, requesting_agent_id):
                unverified.add(att.control_id)

        # Every control required by every rung up to (and including) the target.
        required: set[str] = set()
        for level, controls in LEVEL_REQUIRED_CONTROLS.items():
            if level.rank <= requested_level.rank:
                required.update(controls)

        missing = sorted(required - attested)
        if missing:
            reasons.append(f"missing required controls: {', '.join(missing)}")

        # In production, an attested-but-unverified control is treated as missing.
        blocking_unverified = sorted(unverified & required)
        if blocking_unverified and self._verifier is not None:
            reasons.append(
                f"attestations failed independent verification: {', '.join(blocking_unverified)}"
            )

        approved = not reasons
        verified = self._verifier is not None and not blocking_unverified
        if approved and self._verifier is None:
            reasons.append("ADVISORY: granted without independent verification (no verifier wired)")

        return PromotionDecision(
            approved=approved,
            current_level=current_level,
            requested_level=requested_level,
            granted_level=requested_level if approved else current_level,
            missing_controls=tuple(missing),
            unverified_controls=tuple(blocking_unverified),
            verified=verified,
            reasons=tuple(reasons),
        )
