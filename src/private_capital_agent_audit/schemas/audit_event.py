"""The append-only audit-event schema and supporting enums.

An :class:`AuditEvent` is the unit hashed into the tamper-evident ledger
(:mod:`private_capital_agent_audit.governance.audit_chain`). The hash is computed
over a canonical JSON serialization of every field *except* ``event_hash``
itself, so the stored hash can be independently recomputed and compared during
verification.

Within-trust-boundary tamper *evidence*, not tamper *prevention*: the chain
detects after-the-fact mutation; it does not stop a privileged in-process actor
from rewriting the store. End-to-end regeneration is defended by an external
witness anchor (see ``docs/FAILURE-MODES.md`` and
:meth:`~.governance.audit_chain.AuditChain.verify_regeneration_resistant`).

Scope note. This library governs **SEC-registered investment advisers**
(Investment Advisers Act of 1940). Advisers owe a fiduciary duty under §206 —
the duty of care and the duty of loyalty articulated in SEC Release IA-5248.
This library models only that adviser fiduciary regime; it encodes no other
actor's standard of conduct.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AutonomyLevel(Enum):
    """The Autonomy Ladder — A0 (read-only) through A4 (production autonomous).

    A proprietary governance framework. Each rung names the human-oversight
    posture an agent operates under; promotion is gated by the lower rungs'
    controls being independently attested (see
    :mod:`~.governance.autonomy_ladder`).
    """

    A0_INFORMATIONAL = "A0"  # Read-only; recommends, never writes.
    A1_ASSISTED = "A1"  # Drafts; a human approves every write.
    A2_DELEGATED = "A2"  # Writes inside an envelope; sampled human review.
    A3_SUPERVISED_AUTONOMOUS = "A3"  # Autonomous; sovereign veto + full audit.
    A4_PRODUCTION_AUTONOMOUS = "A4"  # A3 + orchestration + escalation.

    @property
    def rank(self) -> int:
        """Ordinal 0..4 for monotonic comparison."""
        return int(self.value[1:])

    @property
    def can_write(self) -> bool:
        """A0 is read-only; every rung above it may write."""
        return self is not AutonomyLevel.A0_INFORMATIONAL

    @property
    def requires_human_approval(self) -> bool:
        """A1 (and A0) require a human to approve every write before it lands."""
        return self in (
            AutonomyLevel.A0_INFORMATIONAL,
            AutonomyLevel.A1_ASSISTED,
        )


class AuditEventType(Enum):
    """The closed set of event types the governance primitives + controls emit."""

    # Primitive lifecycle (P1–P5)
    GENESIS = "genesis"
    AGENT_ACTION = "agent_action"
    LEVEL_GATE_EVALUATED = "level_gate_evaluated"
    VETO_TRIGGERED = "veto_triggered"
    VETO_CLEARED = "veto_cleared"
    DEFCON_TRANSITION = "defcon_transition"
    MODEL_VALIDATED = "model_validated"
    WITNESS_ANCHOR = "witness_anchor"

    # Adviser-native controls
    BEST_EXECUTION_REVIEW = "best_execution_review"  # §206 fiduciary best-ex
    ORDER_GOVERNED = "order_governed"  # the consequential write (order/position)
    MNPI_SCREENING = "mnpi_screening"  # §204A information-barrier surveillance
    MNPI_BARRIER_BREACH = "mnpi_barrier_breach"
    CUSTODY_CHECK = "custody_check"  # 17 CFR 275.206(4)-2
    CUSTODY_EXCEPTION = "custody_exception"
    MARKETING_REVIEW = "marketing_review"  # 17 CFR 275.206(4)-1
    ALLOCATION_DECISION = "allocation_decision"  # §206 cross-client allocation
    ALLOCATION_FAIRNESS_FLAG = "allocation_fairness_flag"  # cherry-picking flag
    RECORDKEEPING_EVENT = "recordkeeping_event"  # 17 CFR 275.204-2
    OFF_CHANNEL_FLAG = "off_channel_flag"  # off-channel-comms recordkeeping risk
    VALUATION_REVIEW = "valuation_review"  # §206 duty of loyalty; 206(4)-2 audit
    VALUATION_EXCEPTION = "valuation_exception"


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no insignificant whitespace.

    The same logical event always serializes to the same bytes, so the hash is
    reproducible across processes and machines.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class AuditEvent:
    """A single hash-chained ledger entry.

    ``event_hash`` is excluded from its own preimage; ``prev_hash`` links to the
    prior entry's ``event_hash`` (or the genesis seed for entry #0).
    """

    sequence: int
    event_type: AuditEventType
    autonomy_level: AutonomyLevel
    agent_id: str
    payload: dict[str, Any]
    timestamp: str
    prev_hash: str
    actor_id: str | None = None
    event_hash: str = field(default="")

    def _preimage(self) -> str:
        """The canonical string hashed to produce ``event_hash``."""
        return _canonical_json(
            {
                "sequence": self.sequence,
                "event_type": self.event_type.value,
                "autonomy_level": self.autonomy_level.value,
                "agent_id": self.agent_id,
                "payload": self.payload,
                "timestamp": self.timestamp,
                "prev_hash": self.prev_hash,
                "actor_id": self.actor_id,
            }
        )

    def compute_hash(self) -> str:
        """SHA-256 over the canonical preimage (excludes ``event_hash``)."""
        return hashlib.sha256(self._preimage().encode("utf-8")).hexdigest()

    def with_hash(self) -> AuditEvent:
        """Return a copy with ``event_hash`` populated from the preimage."""
        from dataclasses import replace

        return replace(self, event_hash=self.compute_hash())

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable view (e.g. for a JSONL ledger file)."""
        return {
            "sequence": self.sequence,
            "event_type": self.event_type.value,
            "autonomy_level": self.autonomy_level.value,
            "agent_id": self.agent_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "actor_id": self.actor_id,
            "event_hash": self.event_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEvent:
        """Reconstruct an event from its :meth:`to_dict` form."""
        return cls(
            sequence=int(data["sequence"]),
            event_type=AuditEventType(data["event_type"]),
            autonomy_level=AutonomyLevel(data["autonomy_level"]),
            agent_id=str(data["agent_id"]),
            payload=dict(data["payload"]),
            timestamp=str(data["timestamp"]),
            prev_hash=str(data["prev_hash"]),
            actor_id=data.get("actor_id"),
            event_hash=str(data.get("event_hash", "")),
        )
