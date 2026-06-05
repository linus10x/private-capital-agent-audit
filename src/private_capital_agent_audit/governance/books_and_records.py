"""Adviser control — Books-and-records + off-channel-communications capture.

A 0.1.0 MUST-HAVE control. A *documented reference control* anchoring two real
obligations:

1. **Retention** — required records must be retained at least 5 years, the first
   2 of them readily accessible. The control evaluates a record's retention
   posture and flags a record that is past-due-for-disposal-but-still-needed or
   not in an accessible tier within the first-two-years window.
2. **Off-channel communications** — a business communication sent over a channel
   the firm does not capture (personal text/messaging app) is the recordkeeping
   failure mode behind the 9-figure SEC enforcement wave. The control flags a
   communication on a non-approved channel that was not captured, so an
   autonomous agent's outbound (or an ingested inbound) on an uncaptured channel
   is surfaced rather than silently lost.

Regulatory anchor (honest claim layer): **17 CFR 275.204-2** (and, where
dually-registered, Exchange Act Rule 17a-4). Enforcement backdrop: the
off-channel-communications recordkeeping wave — SEC Press Releases 2022-174
(~$1.1B, 16 firms, 2022-09-27), 2024-18 (~$81M), 2024-98 (~$392.75M), and
2024-144 (~$88M). See ``docs/regulatory/obligation_map.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel

# 17 CFR 275.204-2: retain >= 5 years; first 2 years readily accessible.
RETENTION_YEARS_MIN = 5
ACCESSIBLE_YEARS_MIN = 2


@dataclass(frozen=True)
class CommunicationEvent:
    """A business communication to be evaluated for capture/recordkeeping."""

    comm_id: str
    channel: str
    is_business_communication: bool
    captured: bool


@dataclass(frozen=True)
class RecordRetention:
    """A record's retention posture for evaluation."""

    record_id: str
    record_type: str
    age_years: float
    readily_accessible: bool
    disposed: bool = False


@dataclass(frozen=True)
class RecordkeepingFinding:
    subject_id: str
    compliant: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


class BooksAndRecordsMonitor:
    """Flag off-channel communications and retention exceptions (275.204-2).

    Parameters
    ----------
    approved_channels:
        Channels the firm captures and supervises (e.g. corporate email, an
        archived messaging platform). A business communication on any other
        channel that was not captured is flagged.
    audit_chain:
        Optional chain; findings are recorded.
    """

    def __init__(
        self,
        *,
        approved_channels: frozenset[str] | None = None,
        audit_chain: AuditChain | None = None,
    ) -> None:
        self._approved = frozenset(c.strip().lower() for c in (approved_channels or frozenset()))
        self._chain = audit_chain

    def evaluate_communication(self, comm: CommunicationEvent) -> RecordkeepingFinding:
        """Flag a business communication on a non-approved, uncaptured channel."""
        reasons: list[str] = []
        channel = comm.channel.strip().lower()
        off_channel = comm.is_business_communication and channel not in self._approved
        if off_channel and not comm.captured:
            reasons.append(
                f"off-channel business communication on uncaptured channel "
                f"{comm.channel!r} (recordkeeping failure — 275.204-2)"
            )

        finding = RecordkeepingFinding(
            subject_id=comm.comm_id, compliant=not reasons, reasons=tuple(reasons)
        )
        if self._chain is not None:
            event_type = (
                AuditEventType.RECORDKEEPING_EVENT
                if finding.compliant
                else AuditEventType.OFF_CHANNEL_FLAG
            )
            self._chain.append(
                event_type,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id="books-and-records-monitor",
                payload={
                    "comm_id": comm.comm_id,
                    "channel": comm.channel,
                    "captured": comm.captured,
                    "compliant": finding.compliant,
                    "reasons": list(finding.reasons),
                },
            )
        return finding

    def evaluate_retention(self, record: RecordRetention) -> RecordkeepingFinding:
        """Flag retention exceptions under the 5-year / first-2-years-accessible rule."""
        reasons: list[str] = []
        if record.disposed and record.age_years < RETENTION_YEARS_MIN:
            reasons.append(
                f"record disposed at {record.age_years:.1f}y; minimum retention is "
                f"{RETENTION_YEARS_MIN}y (275.204-2(e))"
            )
        if (
            not record.disposed
            and record.age_years < ACCESSIBLE_YEARS_MIN
            and not record.readily_accessible
        ):
            reasons.append(
                f"record within the first {ACCESSIBLE_YEARS_MIN} years not held in a "
                f"readily accessible tier (275.204-2(e))"
            )

        finding = RecordkeepingFinding(
            subject_id=record.record_id, compliant=not reasons, reasons=tuple(reasons)
        )
        if self._chain is not None:
            self._chain.append(
                AuditEventType.RECORDKEEPING_EVENT,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id="books-and-records-monitor",
                payload={
                    "record_id": record.record_id,
                    "record_type": record.record_type,
                    "age_years": record.age_years,
                    "compliant": finding.compliant,
                    "reasons": list(finding.reasons),
                },
            )
        return finding
