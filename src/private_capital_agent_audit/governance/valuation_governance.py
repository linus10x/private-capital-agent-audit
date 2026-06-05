"""Adviser control — Independent-valuation governance (fund admin / valuation).

A *documented reference control* for the valuation sub-vertical. It encodes the
load-bearing §206 duty-of-loyalty concern in fund valuation: where the adviser's
fee depends on its own marks, an asset valued by the adviser itself (a manual
override, an adviser-marked price, or a hard-to-value Level-3 input) must be
**independently attested** before it is relied upon. It reuses the independence-
attestation pattern from the effective-challenge primitive: independence is
*attested by the deployer's valuation committee, not code-detected*.

The control flags two examiner-real exceptions on a deployer-supplied mark:

1. A mark requiring independence (Level-3, adviser-marked, or a manual override)
   that carries **no independent valuation attestation** — the duty-of-loyalty
   conflict is unmitigated.
2. A **stale mark** older than a deployer-set freshness window.

It does not price assets, run a valuation model, or judge whether a mark is
"right" — the valuation committee owns that judgment; this control records it and
surfaces the unmitigated conflict.

Engineering reference, not legal/compliance advice — the deployer's compliance
function owns the determination.

Regulatory anchor (honest claim layer): Advisers Act **§206** duty of loyalty;
the custody rule's audit/valuation interaction (**17 CFR 275.206(4)-2** audit
exception). See ``docs/regulatory/obligation_map.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


class PriceSource(Enum):
    """How a mark was sourced."""

    INDEPENDENT = "independent"  # third-party / qualified pricing service
    VENDOR = "vendor"  # vendor feed (may still need independence for Level 3)
    ADVISER_MARKED = "adviser_marked"  # the adviser priced it itself


@dataclass(frozen=True)
class ValuationInput:
    """A deployer-described mark to be governed.

    ``level`` is the fair-value hierarchy level (1 = quoted active market,
    2 = observable inputs, 3 = unobservable). ``independent_attestation`` is the
    valuation committee's attestation that an independent source validated the
    mark — attested, not code-detected.
    """

    asset_id: str
    level: int
    price_source: PriceSource
    independent_attestation: bool
    days_since_last_valuation: int
    manual_override: bool = False


@dataclass(frozen=True)
class ValuationAssessment:
    asset_id: str
    compliant: bool
    requires_independence: bool
    flags: tuple[str, ...] = field(default_factory=tuple)


class ValuationGovernanceCheck:
    """Flag valuation marks whose duty-of-loyalty conflict is unmitigated or stale.

    Parameters
    ----------
    max_staleness_days:
        A mark older than this is flagged stale.
    audit_chain:
        Optional chain; assessments and exceptions are recorded.
    """

    def __init__(
        self,
        *,
        max_staleness_days: int = 90,
        audit_chain: AuditChain | None = None,
    ) -> None:
        if max_staleness_days < 1:
            raise ValueError("max_staleness_days must be at least 1")
        self._max_staleness = max_staleness_days
        self._chain = audit_chain

    @staticmethod
    def _requires_independence(v: ValuationInput) -> bool:
        """A mark needs independent attestation when the adviser's own judgment
        sets the price: Level-3, adviser-marked, or a manual override."""
        return v.level >= 3 or v.price_source is PriceSource.ADVISER_MARKED or v.manual_override

    def assess(self, v: ValuationInput) -> ValuationAssessment:
        """Return an assessment with any valuation-governance exceptions."""
        if v.level not in (1, 2, 3):
            raise ValueError("level must be 1, 2, or 3 (fair-value hierarchy)")
        if v.days_since_last_valuation < 0:
            raise ValueError(
                "days_since_last_valuation must be non-negative "
                "(a future-dated mark is a data error, not a fresh one)"
            )
        flags: list[str] = []
        requires_independence = self._requires_independence(v)

        if requires_independence and not v.independent_attestation:
            flags.append(
                "mark set by adviser judgment (Level-3 / adviser-marked / manual override) "
                "without an independent valuation attestation — §206 duty-of-loyalty "
                "conflict unmitigated"
            )
        if v.days_since_last_valuation > self._max_staleness:
            flags.append(
                f"stale mark: {v.days_since_last_valuation}d since last valuation exceeds "
                f"the {self._max_staleness}d freshness window"
            )

        assessment = ValuationAssessment(
            asset_id=v.asset_id,
            compliant=not flags,
            requires_independence=requires_independence,
            flags=tuple(flags),
        )
        self._record(assessment, v)
        return assessment

    def _record(self, assessment: ValuationAssessment, v: ValuationInput) -> None:
        if self._chain is None:
            return
        event_type = (
            AuditEventType.VALUATION_REVIEW
            if assessment.compliant
            else AuditEventType.VALUATION_EXCEPTION
        )
        self._chain.append(
            event_type,
            AutonomyLevel.A0_INFORMATIONAL,
            agent_id="valuation-governance-check",
            payload={
                "asset_id": assessment.asset_id,
                "level": v.level,
                "price_source": v.price_source.value,
                "requires_independence": assessment.requires_independence,
                "independent_attestation": v.independent_attestation,
                "compliant": assessment.compliant,
                "flags": list(assessment.flags),
            },
        )
