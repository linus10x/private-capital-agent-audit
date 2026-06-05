"""Adviser control — Marketing-rule review gate (private wealth / UHNW).

A 0.1.0 MUST-HAVE control. A *documented reference control* that reviews an
outbound advertisement against the conditions of the SEC marketing rule before
an autonomous agent may distribute it. An advertisement that fails review is NOT
approved and should be gated by the sovereign veto before it reaches an investor.

The control evaluates the rule's load-bearing conditions, with the precise
sub-paragraph for each:

* **Hypothetical performance** (17 CFR 275.206(4)-1(d)(6)) may be shown only when
  the adviser (i) has adopted policies reasonably designed to ensure relevance to
  the audience's financial situation and objectives — **(d)(6)(i)**; (ii)
  provides sufficient information about the criteria and assumptions used —
  **(d)(6)(ii)**; and (iii) provides sufficient information about the risks and
  limitations of using the hypothetical performance — **(d)(6)(iii)**.
* **Testimonials / endorsements** — **(b)(1)** — require clear-and-prominent
  disclosure of the promoter relationship and any compensation.
* **Performance** — **(d)(1)** — prohibits presenting *gross* performance unless
  *net* performance is shown with at least equal prominence (the trigger is
  showing gross; an ad showing only net does not implicate (d)(1)).

This control does not invent independence detectors or read advertisement prose;
it gates on deployer-supplied structured attributes. It is not a deployed
marketing-review system.

Engineering reference, not legal/compliance advice — the deployer's compliance
function owns the determination. Regulatory anchor: **17 CFR 275.206(4)-1**
(compliance date 2022-11-04). Enforcement backdrop: SEC v. Titan Global Capital
Management (2023, Release 2023-153 — an early action under the amended Marketing
Rule, re: hypothetical-performance advertising). Advertisements are also retained
records under 275.204-2. See ``docs/regulatory/obligation_map.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


@dataclass(frozen=True)
class Advertisement:
    """A deployer-described outbound advertisement's compliance-relevant attributes.

    The hypothetical-performance flags map 1:1 to the three (d)(6) conditions; the
    performance flags model the (d)(1) gross-vs-net trigger precisely.
    """

    ad_id: str
    contains_hypothetical_performance: bool = False
    has_hypothetical_policies: bool = False  # (d)(6)(i) — policies adopted
    has_relevance_to_audience: bool = False  # (d)(6)(i) — relevance to the audience
    has_criteria_assumptions_info: bool = False  # (d)(6)(ii) — criteria + assumptions
    has_risk_limitations_info: bool = False  # (d)(6)(iii) — risks + limitations
    contains_testimonial: bool = False
    testimonial_has_disclosure: bool = False  # (b)
    shows_gross_performance: bool = False  # (d)(1) trigger
    shows_net_at_equal_prominence: bool = False  # (d)(1) cure


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
            if not ad.has_criteria_assumptions_info:
                violations.append(
                    "hypothetical performance without sufficient information on the "
                    "criteria and assumptions used (206(4)-1(d)(6)(ii))"
                )
            if not ad.has_risk_limitations_info:
                violations.append(
                    "hypothetical performance without sufficient information on the risks "
                    "and limitations of using it (206(4)-1(d)(6)(iii))"
                )

        if ad.contains_testimonial and not ad.testimonial_has_disclosure:
            violations.append(
                "testimonial/endorsement without clear-and-prominent relationship and "
                "compensation disclosure (206(4)-1(b)(1))"
            )

        # (d)(1) is triggered by presenting GROSS performance; the cure is net at
        # equal prominence. Net-only performance does not implicate (d)(1).
        if ad.shows_gross_performance and not ad.shows_net_at_equal_prominence:
            violations.append(
                "gross performance presented without net performance shown with at least "
                "equal prominence (206(4)-1(d)(1))"
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
