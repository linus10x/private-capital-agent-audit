"""Adviser control — Marketing-rule review gate (private wealth / UHNW).

A 0.1.0 MUST-HAVE control. A *documented reference control* that reviews an
outbound advertisement against the conditions of the SEC marketing rule before
an autonomous agent may distribute it. An advertisement that fails review is NOT
approved and should be gated by the sovereign veto before it reaches an investor.

The control evaluates the rule's load-bearing conditions:

* **Hypothetical performance** may only be shown when the adviser has adopted
  policies reasonably designed to ensure relevance to the audience AND provides
  information sufficient to evaluate it (including risk/limitation disclosures).
* **Testimonials / endorsements** require clear-and-prominent disclosure of the
  promoter relationship and any compensation.
* **Performance** presentations require net-of-fees alongside gross.

This control does not invent independence detectors or read advertisement prose;
it gates on deployer-supplied structured attributes. It is not a deployed
marketing-review system.

Regulatory anchor (honest claim layer): **17 CFR 275.206(4)-1** (compliance date
2022-11-04). Enforcement backdrop: SEC v. Titan Global Capital Management (2023,
Release 2023-153, the first marketing-rule action, re: hypothetical-performance
advertising). Advertisements are also retained records
under 275.204-2. See ``docs/regulatory/obligation_map.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


@dataclass(frozen=True)
class Advertisement:
    """A deployer-described outbound advertisement's compliance-relevant attributes."""

    ad_id: str
    contains_hypothetical_performance: bool = False
    has_hypothetical_policies: bool = False
    has_relevance_to_audience: bool = False
    has_risk_disclosures: bool = False
    contains_testimonial: bool = False
    testimonial_has_disclosure: bool = False
    contains_performance: bool = False
    performance_net_of_fees: bool = False


@dataclass(frozen=True)
class MarketingReview:
    ad_id: str
    approved: bool
    violations: tuple[str, ...] = field(default_factory=tuple)


class MarketingReviewGate:
    """Review an advertisement against 17 CFR 275.206(4)-1 conditions."""

    def __init__(self, *, audit_chain: AuditChain | None = None) -> None:
        self._chain = audit_chain

    def review(self, ad: Advertisement) -> MarketingReview:
        """Return a review; ``approved`` is False if any condition is unmet."""
        violations: list[str] = []

        if ad.contains_hypothetical_performance:
            if not ad.has_hypothetical_policies:
                violations.append(
                    "hypothetical performance without adopted policies (206(4)-1(d)(6)(i))"
                )
            if not ad.has_relevance_to_audience:
                violations.append(
                    "hypothetical performance not tailored to the audience's financial "
                    "situation and objectives (206(4)-1(d)(6)(i))"
                )
            if not ad.has_risk_disclosures:
                violations.append(
                    "hypothetical performance without sufficient information/risk "
                    "disclosures to evaluate it (206(4)-1(d)(6)(ii))"
                )

        if ad.contains_testimonial and not ad.testimonial_has_disclosure:
            violations.append(
                "testimonial/endorsement without clear-and-prominent relationship and "
                "compensation disclosure (206(4)-1(b))"
            )

        if ad.contains_performance and not ad.performance_net_of_fees:
            violations.append(
                "performance shown without net-of-fees alongside gross (206(4)-1(d)(1))"
            )

        approved = not violations
        review = MarketingReview(ad_id=ad.ad_id, approved=approved, violations=tuple(violations))
        if self._chain is not None:
            self._chain.append(
                AuditEventType.MARKETING_REVIEW,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id="marketing-review-gate",
                payload={
                    "ad_id": ad.ad_id,
                    "approved": approved,
                    "violations": list(violations),
                },
            )
        return review
