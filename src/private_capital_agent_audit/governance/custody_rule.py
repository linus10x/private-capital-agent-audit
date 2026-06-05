"""Adviser control — Custody-rule assessment (PE/credit GP; fund admin/valuation).

A 0.1.0 MUST-HAVE control. A *documented reference control* that assesses an
adviser's custody arrangement against the four load-bearing requirements of the
custody rule and surfaces exceptions an examiner would test. It does not move
assets or contact custodians — it evaluates a deployer-supplied
:class:`CustodyArrangement` and records exceptions to the chain.

Two compliance paths are modeled, exactly as the rule provides:

1. **Standard path** — qualified custodian + client account statements + an
   annual **surprise examination** by an independent public accountant.
2. **Pooled-vehicle (private-fund) audit exception** — an annual GAAP audit with
   audited financial statements distributed to investors **within 120 days** of
   fiscal year-end (rule text, 206(4)-2(b)(4)) substitutes for the surprise
   examination. For a **fund of funds**, SEC staff guidance (the Division's
   Custody Rule FAQ) extends the distribution window to **180 days**, because a
   fund of funds cannot finalize its audit until the underlying funds' audits
   complete. The control branches the window on ``is_fund_of_funds`` so a
   compliant fund of funds distributing at, say, day 165 is not false-flagged.

Engineering reference, not legal/compliance advice — the deployer's compliance
function owns the determination. Regulatory anchor: **17 CFR 275.206(4)-2**
(the 180-day fund-of-funds window is SEC staff guidance, NOT rule text).
Enforcement backdrop: custody-rule surprise-exam failures (e.g. SEC,
*Munakata Associates*, IA-6901-S). See ``docs/regulatory/obligation_map.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


@dataclass(frozen=True)
class CustodyArrangement:
    """A deployer-described custody arrangement for one client/fund.

    ``has_custody`` is the threshold question — if the adviser does not have
    custody (no possession, no authority to withdraw, not a GP of the fund), the
    rule's affirmative requirements do not attach.
    """

    client_id: str
    has_custody: bool
    qualified_custodian: bool
    account_statements_delivered: bool
    surprise_exam_current: bool
    is_pooled_vehicle: bool = False
    is_fund_of_funds: bool = False
    audited_financials_distributed: bool = False
    # Actual days from fiscal year-end to distribution of audited financials
    # (None if not distributed). Compared against the applicable window.
    days_to_distribute_audited_financials: int | None = None


@dataclass(frozen=True)
class CustodyAssessment:
    client_id: str
    compliant: bool
    path: str  # "no_custody", "audit_exception", "standard", or "non_compliant"
    exceptions: tuple[str, ...] = field(default_factory=tuple)


class CustodyRuleCheck:
    """Assess a custody arrangement against 17 CFR 275.206(4)-2."""

    def __init__(self, *, audit_chain: AuditChain | None = None) -> None:
        self._chain = audit_chain

    def assess(self, arrangement: CustodyArrangement) -> CustodyAssessment:
        """Return a compliance assessment with any custody-rule exceptions."""
        days = arrangement.days_to_distribute_audited_financials
        if days is not None and days < 0:
            raise ValueError(
                "days_to_distribute_audited_financials must be non-negative "
                "(a negative distribution lag is a data error)"
            )
        if not arrangement.has_custody:
            assessment = CustodyAssessment(
                client_id=arrangement.client_id,
                compliant=True,
                path="no_custody",
                exceptions=(),
            )
            self._record(assessment)
            return assessment

        exceptions: list[str] = []
        if not arrangement.qualified_custodian:
            exceptions.append("client assets not held with a qualified custodian (206(4)-2(a)(1))")
        if not arrangement.account_statements_delivered:
            # The quarterly account-statements obligation is (a)(3); (a)(2) is the
            # separate written notice of the qualified custodian.
            exceptions.append("account statements not delivered to clients (206(4)-2(a)(3))")

        # The surprise-exam requirement can be satisfied by the pooled-vehicle
        # audit exception, but only when the audit was distributed within the
        # applicable window: 120 days (rule text) or 180 days for a fund of funds
        # (SEC staff guidance).
        window = 180 if arrangement.is_fund_of_funds else 120
        distributed_in_time = (
            arrangement.audited_financials_distributed and days is not None and days <= window
        )
        audit_exception_met = arrangement.is_pooled_vehicle and distributed_in_time
        if audit_exception_met:
            path = "audit_exception"
        else:
            path = "standard"
            # Distributed but missed the applicable window — a real, common exception.
            if (
                arrangement.is_pooled_vehicle
                and arrangement.audited_financials_distributed
                and not distributed_in_time
            ):
                window_basis = (
                    "180 days (fund-of-funds, per SEC staff guidance)"
                    if (arrangement.is_fund_of_funds)
                    else "120 days (206(4)-2(b)(4))"
                )
                exceptions.append(
                    f"pooled-vehicle audited financials not distributed within {window_basis}; "
                    "audit exception NOT met"
                )
            if not arrangement.surprise_exam_current:
                exceptions.append(
                    "no current annual surprise examination by an independent public "
                    "accountant (206(4)-2(a)(4))"
                )

        compliant = not exceptions
        assessment = CustodyAssessment(
            client_id=arrangement.client_id,
            compliant=compliant,
            path=path if compliant else "non_compliant",
            exceptions=tuple(exceptions),
        )
        self._record(assessment)
        return assessment

    def _record(self, assessment: CustodyAssessment) -> None:
        if self._chain is None:
            return
        event_type = (
            AuditEventType.CUSTODY_CHECK
            if assessment.compliant
            else AuditEventType.CUSTODY_EXCEPTION
        )
        self._chain.append(
            event_type,
            AutonomyLevel.A0_INFORMATIONAL,
            agent_id="custody-rule-check",
            payload={
                "client_id": assessment.client_id,
                "compliant": assessment.compliant,
                "path": assessment.path,
                "exceptions": list(assessment.exceptions),
            },
        )
