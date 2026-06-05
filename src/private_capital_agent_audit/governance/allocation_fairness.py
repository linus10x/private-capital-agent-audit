"""Adviser control — Cross-client allocation fairness / anti-cherry-picking.

A 0.1.0 MUST-HAVE control, and the deliberate **re-scope** of the "fairness"
control AWAY from protected-class disparate impact (a lending/credit concern
that does NOT govern investment-allocation decisions) toward the real
Advisers Act §206 concern: **cherry-picking** — disproportionately steering
favorably-priced fills to favored or proprietary accounts.

A *documented reference control*. Given how a block trade was allocated across
client accounts (each fill tagged favorable/unfavorable versus the block's
average execution), it flags when favored/proprietary accounts received a
disproportionate share of the favorable fills beyond a deployer-set tolerance.
It does not adjudicate intent; it surfaces the statistical asymmetry an examiner
(or the SEC's own trade-allocation analytics) would flag.

Engineering reference, not legal/compliance advice — the deployer's compliance
function owns the determination.

Regulatory anchor (honest claim layer): **Advisers Act §206(1),(2),(4)**.
Enforcement backdrop: SEC v. J.S. Oliver Capital Management (Release 2013-168;
final IA-5368-S) and SEC v. Michael Breton / Strategic Capital Management
(Release 2017-32) — both cherry-picking matters. See
``docs/regulatory/obligation_map.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


@dataclass(frozen=True)
class Fill:
    """One account's fill within a block allocation.

    ``favorable`` is True when this fill executed better than the block's average
    (a deployer/upstream determination, e.g. price better than VWAP for the
    block). ``is_favored`` marks proprietary / affiliated / preferred accounts
    whose over-allocation of favorable fills is the cherry-picking risk.
    """

    account_id: str
    favorable: bool
    is_favored: bool


@dataclass(frozen=True)
class AllocationAssessment:
    block_id: str
    fair: bool
    favored_favorable_rate: float
    other_favorable_rate: float
    disparity: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


class AllocationFairnessMonitor:
    """Flag disproportionate favorable allocation to favored accounts.

    Parameters
    ----------
    max_disparity:
        The favorable-fill rate among favored accounts may exceed the rate among
        other accounts by at most this fraction before the allocation is flagged.
    min_favored, min_other:
        Minimum sample sizes per group below which the result is reported as
        ``fair=True`` with an "insufficient sample" reason (no statistical claim
        is made on a degenerate sample, rather than a false flag).
    audit_chain:
        Optional chain; assessments and flags are recorded.
    """

    def __init__(
        self,
        *,
        max_disparity: float = 0.20,
        min_favored: int = 1,
        min_other: int = 1,
        audit_chain: AuditChain | None = None,
    ) -> None:
        if not 0.0 <= max_disparity <= 1.0:
            raise ValueError("max_disparity must be in [0, 1]")
        if min_favored < 1 or min_other < 1:
            raise ValueError("min_favored and min_other must be at least 1")
        self._max_disparity = max_disparity
        self._min_favored = min_favored
        self._min_other = min_other
        self._chain = audit_chain

    def assess(self, block_id: str, fills: list[Fill]) -> AllocationAssessment:
        """Assess one block's allocation for cherry-picking asymmetry."""
        favored = [f for f in fills if f.is_favored]
        other = [f for f in fills if not f.is_favored]

        reasons: list[str] = []
        if len(favored) < self._min_favored or len(other) < self._min_other:
            # Degenerate split. A one-sided block where the favored/proprietary
            # accounts took the allocation INCLUDING favorable fills, with no
            # comparison group, is the exact concentration cherry-picking produces
            # — it must NOT be reported fair. Only a genuinely empty/no-favorable
            # split is "insufficient sample".
            favored_favorable = sum(1 for f in favored if f.favorable)
            if not other and len(favored) >= self._min_favored and favored_favorable:
                rate = favored_favorable / len(favored)
                assessment = AllocationAssessment(
                    block_id=block_id,
                    fair=False,
                    favored_favorable_rate=rate,
                    other_favorable_rate=0.0,
                    disparity=rate,
                    reasons=(
                        "single-group concentration: favored/proprietary accounts "
                        f"received the block's favorable fills ({rate:.0%}) with no "
                        "comparison group — review for cherry-picking (§206)",
                    ),
                )
            else:
                assessment = AllocationAssessment(
                    block_id=block_id,
                    fair=True,
                    favored_favorable_rate=0.0,
                    other_favorable_rate=0.0,
                    disparity=0.0,
                    reasons=(
                        "insufficient sample to assess allocation fairness "
                        f"(favored={len(favored)}, other={len(other)})",
                    ),
                )
            self._record(assessment)
            return assessment

        favored_rate = sum(1 for f in favored if f.favorable) / len(favored)
        other_rate = sum(1 for f in other if f.favorable) / len(other)
        disparity = favored_rate - other_rate

        if disparity > self._max_disparity:
            reasons.append(
                f"favored accounts received favorable fills at {favored_rate:.0%} vs "
                f"{other_rate:.0%} for others (disparity {disparity:.0%} > tolerance "
                f"{self._max_disparity:.0%}) — possible cherry-picking (§206)"
            )

        fair = not reasons
        assessment = AllocationAssessment(
            block_id=block_id,
            fair=fair,
            favored_favorable_rate=favored_rate,
            other_favorable_rate=other_rate,
            disparity=disparity,
            reasons=tuple(reasons),
        )
        self._record(assessment)
        return assessment

    def _record(self, assessment: AllocationAssessment) -> None:
        if self._chain is None:
            return
        event_type = (
            AuditEventType.ALLOCATION_DECISION
            if assessment.fair
            else AuditEventType.ALLOCATION_FAIRNESS_FLAG
        )
        self._chain.append(
            event_type,
            AutonomyLevel.A0_INFORMATIONAL,
            agent_id="allocation-fairness-monitor",
            payload={
                "block_id": assessment.block_id,
                "fair": assessment.fair,
                "favored_favorable_rate": assessment.favored_favorable_rate,
                "other_favorable_rate": assessment.other_favorable_rate,
                "disparity": assessment.disparity,
                "reasons": list(assessment.reasons),
            },
        )
