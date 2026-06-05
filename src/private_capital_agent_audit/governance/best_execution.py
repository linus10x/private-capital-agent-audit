"""Adviser control — Best-execution review gate (buy-side / quant).

A 0.1.0 MUST-HAVE control for the buy-side / quant sub-vertical. The
consequential write here is an **order/position**, governed by a best-execution
review plus surveillance under the adviser's §206 fiduciary duty of care.

This is a *documented reference control*, not a deployed adviser trading system.
It encodes the load-bearing concept of the duty of care's best-execution
obligation: an autonomous agent may not release an order unless a best-execution
review has (a) actually evaluated execution quality on a **systematic** basis
(qualitative factors considered, not commission alone) and (b) found the
execution within a deployer-set tolerance versus a benchmark. A review that
considered no factors, or whose slippage exceeds tolerance, is NOT approved —
and an unapproved order should be gated by the sovereign veto before it lands.

Engineering reference, not legal/compliance advice — the deployer's compliance
function owns the determination.

Regulatory anchor (honest claim layer): best execution derives from the adviser
fiduciary duty of care under **Advisers Act §206**, as articulated in SEC
Release **IA-5248** (2019). It is not a numbered standalone rule. See
``docs/regulatory/obligation_map.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


# The qualitative execution-quality factors the SEC's 2019 interpretation
# describes an adviser evaluating (price is necessary but not sufficient).
RECOGNIZED_EXECUTION_FACTORS: frozenset[str] = frozenset(
    {
        "price",
        "speed",
        "likelihood_of_execution",
        "likelihood_of_settlement",
        "order_size",
        "trading_characteristics",
        "venue_quality",
        "commission_rate",
        "market_impact",
    }
)


@dataclass(frozen=True)
class ExecutionFactors:
    """The execution outcome plus the qualitative factors that were evaluated.

    ``benchmark_price`` is the reference the deployer measures slippage against
    (arrival price, NBBO midpoint, VWAP — the deployer's choice). ``side``
    determines the sign of adverse slippage.
    """

    venue: str
    side: Side
    fill_price: float
    benchmark_price: float
    commission: float
    factors_considered: tuple[str, ...]

    def slippage_bps(self) -> float:
        """Signed slippage vs benchmark, in basis points. Positive = adverse.

        For a BUY, paying above benchmark is adverse; for a SELL, filling below
        benchmark is adverse. Returns ``inf`` (maximally adverse — never "in
        tolerance") when slippage cannot be assessed: a non-finite (NaN/inf)
        fill or benchmark, or a non-positive benchmark or fill. This fails closed
        — ``0.0`` would let a degenerate input masquerade as a good fill.
        """
        if not (math.isfinite(self.benchmark_price) and math.isfinite(self.fill_price)):
            return math.inf
        # A non-positive benchmark OR a non-positive fill is degenerate: a negative
        # fill would otherwise compute as a hugely *favorable* slippage and clear.
        if self.benchmark_price <= 0 or self.fill_price <= 0:
            return math.inf
        raw = (self.fill_price - self.benchmark_price) / self.benchmark_price
        signed = raw if self.side is Side.BUY else -raw
        return signed * 10_000.0


@dataclass(frozen=True)
class BestExReview:
    """The result of a best-execution review for one order."""

    order_id: str
    approved: bool
    slippage_bps: float
    factors_considered: tuple[str, ...]
    reasons: tuple[str, ...] = field(default_factory=tuple)


class BestExecutionGate:
    """Gate an order's release on a systematic best-execution review.

    Parameters
    ----------
    max_adverse_slippage_bps:
        Orders whose adverse (positive) slippage exceeds this are not approved.
    min_factors:
        Minimum count of recognized qualitative factors that must have been
        considered for the review to be "systematic". A review that considered
        fewer is not approved (commission/price alone is not best execution).
    audit_chain:
        Optional chain; the review and the governed order are recorded.
    """

    def __init__(
        self,
        *,
        max_adverse_slippage_bps: float = 50.0,
        min_factors: int = 2,
        audit_chain: AuditChain | None = None,
    ) -> None:
        if max_adverse_slippage_bps < 0:
            raise ValueError("max_adverse_slippage_bps must be non-negative")
        if min_factors < 1:
            raise ValueError("min_factors must be at least 1")
        self._max_slippage = max_adverse_slippage_bps
        self._min_factors = min_factors
        self._chain = audit_chain

    def review_order(self, order_id: str, factors: ExecutionFactors) -> BestExReview:
        """Review one order against the best-execution policy."""
        reasons: list[str] = []

        recognized = tuple(
            f for f in factors.factors_considered if f in RECOGNIZED_EXECUTION_FACTORS
        )
        unrecognized = tuple(
            f for f in factors.factors_considered if f not in RECOGNIZED_EXECUTION_FACTORS
        )
        if unrecognized:
            reasons.append(f"unrecognized factors ignored: {', '.join(sorted(set(unrecognized)))}")

        if len(set(recognized)) < self._min_factors:
            reasons.append(
                f"review not systematic: {len(set(recognized))} recognized factor(s) "
                f"considered, policy requires >= {self._min_factors}"
            )

        slippage = factors.slippage_bps()
        if not math.isfinite(slippage):
            # Non-finite slippage = unmeasurable execution (NaN/inf inputs or a
            # non-positive benchmark). Fail closed; never approve on a 0.0/NaN
            # technicality.
            reasons.append(
                f"slippage not assessable (benchmark={factors.benchmark_price}, "
                f"fill={factors.fill_price}) — review fails closed on the "
                "execution-quality axis"
            )
        elif slippage > self._max_slippage:
            reasons.append(
                f"adverse slippage {slippage:.1f}bps exceeds tolerance {self._max_slippage:.1f}bps"
            )

        approved = not reasons
        review = BestExReview(
            order_id=order_id,
            approved=approved,
            slippage_bps=slippage,
            factors_considered=tuple(sorted(set(recognized))),
            reasons=tuple(reasons),
        )
        self._record(review, factors)
        return review

    def _record(self, review: BestExReview, factors: ExecutionFactors) -> None:
        if self._chain is None:
            return
        self._chain.append(
            AuditEventType.BEST_EXECUTION_REVIEW,
            AutonomyLevel.A0_INFORMATIONAL,
            agent_id="best-execution-gate",
            payload={
                "order_id": review.order_id,
                "approved": review.approved,
                # JSON-safe: a non-finite slippage (unassessable) records as None.
                "slippage_bps": (
                    review.slippage_bps if math.isfinite(review.slippage_bps) else None
                ),
                "venue": factors.venue,
                "side": factors.side.value,
                "factors_considered": list(review.factors_considered),
                "reasons": list(review.reasons),
            },
        )
        if review.approved:
            self._chain.append(
                AuditEventType.ORDER_GOVERNED,
                AutonomyLevel.A2_DELEGATED,
                agent_id="best-execution-gate",
                payload={"order_id": review.order_id, "released": True},
            )
