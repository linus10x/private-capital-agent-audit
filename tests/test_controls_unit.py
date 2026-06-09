"""Unit + contract tests for the adviser-native controls, the obligation map
(adviser §206 fiduciary grounding), and the CLI."""

from __future__ import annotations

import pytest

from private_capital_agent_audit.governance.allocation_fairness import (
    AllocationFairnessMonitor,
    Fill,
)
from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.governance.best_execution import (
    BestExecutionGate,
    ExecutionFactors,
    Side,
)
from private_capital_agent_audit.governance.books_and_records import (
    BooksAndRecordsMonitor,
    CommunicationEvent,
    RecordRetention,
)
from private_capital_agent_audit.governance.custody_rule import (
    CustodyArrangement,
    CustodyRuleCheck,
)
from private_capital_agent_audit.governance.marketing_rule import (
    Advertisement,
    MarketingReviewGate,
)
from private_capital_agent_audit.governance.mnpi_surveillance import (
    ListType,
    MNPISurveillance,
    ScreenOutcome,
)
from private_capital_agent_audit.governance.obligation_map import (
    ALL_OBLIGATIONS,
    SUB_VERTICAL_OBLIGATIONS,
    SubVertical,
    obligations_for,
)
from private_capital_agent_audit.schemas.audit_event import AuditEventType

# --- best execution ---------------------------------------------------------


def test_best_ex_approves_clean_order() -> None:
    chain = AuditChain(deployer_id="d")
    gate = BestExecutionGate(audit_chain=chain)
    review = gate.review_order(
        "ord-1",
        ExecutionFactors(
            venue="ATS-1",
            side=Side.BUY,
            fill_price=100.0,
            benchmark_price=100.0,
            commission=0.01,
            factors_considered=("price", "venue_quality", "speed"),
        ),
    )
    assert review.approved is True
    types = {e.event_type for e in chain.events()}
    assert AuditEventType.BEST_EXECUTION_REVIEW in types
    assert AuditEventType.ORDER_GOVERNED in types


def test_best_ex_rejects_high_slippage() -> None:
    gate = BestExecutionGate(max_adverse_slippage_bps=10.0)
    review = gate.review_order(
        "ord-2",
        ExecutionFactors(
            venue="v",
            side=Side.BUY,
            fill_price=101.0,
            benchmark_price=100.0,
            commission=0.0,
            factors_considered=("price", "venue_quality"),
        ),
    )
    assert review.approved is False
    assert any("slippage" in r for r in review.reasons)


def test_best_ex_rejects_non_systematic_review() -> None:
    gate = BestExecutionGate(min_factors=2)
    review = gate.review_order(
        "ord-3",
        ExecutionFactors(
            venue="v",
            side=Side.SELL,
            fill_price=100.0,
            benchmark_price=100.0,
            commission=0.0,
            factors_considered=("price",),  # only one factor
        ),
    )
    assert review.approved is False
    assert any("not systematic" in r for r in review.reasons)


def test_best_ex_flags_unrecognized_factor() -> None:
    gate = BestExecutionGate(min_factors=1)
    review = gate.review_order(
        "ord-4",
        ExecutionFactors(
            venue="v",
            side=Side.BUY,
            fill_price=100.0,
            benchmark_price=100.0,
            commission=0.0,
            factors_considered=("price", "vibes"),
        ),
    )
    assert any("unrecognized" in r for r in review.reasons)


def test_best_ex_degenerate_benchmark() -> None:
    import math

    # A non-positive benchmark is unassessable → maximally adverse (inf), never 0.0.
    f = ExecutionFactors(
        venue="v",
        side=Side.BUY,
        fill_price=100.0,
        benchmark_price=0.0,
        commission=0.0,
        factors_considered=("price", "speed"),
    )
    assert math.isinf(f.slippage_bps())


def test_best_ex_nan_inputs_fail_closed() -> None:
    import math

    gate = BestExecutionGate()
    review = gate.review_order(
        "ord-nan",
        ExecutionFactors(
            venue="v",
            side=Side.BUY,
            fill_price=math.nan,
            benchmark_price=100.0,
            commission=0.0,
            factors_considered=("price", "venue_quality"),
        ),
    )
    assert review.approved is False
    assert any("not assessable" in r for r in review.reasons)


def test_best_ex_construction_guards() -> None:
    with pytest.raises(ValueError):
        BestExecutionGate(max_adverse_slippage_bps=-1.0)
    with pytest.raises(ValueError):
        BestExecutionGate(min_factors=0)


# --- MNPI surveillance ------------------------------------------------------


def test_mnpi_lists_and_screen() -> None:
    chain = AuditChain(deployer_id="d")
    surv = MNPISurveillance(audit_chain=chain)
    surv.add("acme", ListType.RESTRICTED, "MNPI")
    surv.add("beta", ListType.WATCH, "rumor")
    assert surv.is_restricted("ACME") is True
    assert surv.restricted_list() == ("ACME",)
    assert surv.watch_list() == ("BETA",)
    assert surv.screen_order("o1", "ACME").outcome is ScreenOutcome.BLOCKED
    assert surv.screen_order("o2", "BETA").outcome is ScreenOutcome.FLAGGED
    assert surv.screen_order("o3", "GAMMA").outcome is ScreenOutcome.CLEARED
    assert any(e.event_type is AuditEventType.MNPI_BARRIER_BREACH for e in chain.events())


def test_mnpi_restricted_supersedes_watch() -> None:
    surv = MNPISurveillance()
    surv.add("acme", ListType.WATCH, "rumor")
    surv.add("acme", ListType.RESTRICTED, "now MNPI")
    assert surv.watch_list() == ()
    assert surv.is_restricted("ACME") is True


def test_mnpi_cannot_demote_restricted_to_watch() -> None:
    surv = MNPISurveillance()
    surv.add("acme", ListType.RESTRICTED, "MNPI")
    with pytest.raises(ValueError, match="restricted list"):
        surv.add("acme", ListType.WATCH, "downgrade")


def test_mnpi_empty_symbol_and_remove() -> None:
    surv = MNPISurveillance()
    with pytest.raises(ValueError, match="non-empty"):
        surv.add("   ", ListType.RESTRICTED, "x")
    surv.add("acme", ListType.RESTRICTED, "MNPI")
    surv.remove("ACME")
    assert surv.is_restricted("ACME") is False


# --- custody rule -----------------------------------------------------------


def test_custody_no_custody_compliant() -> None:
    check = CustodyRuleCheck()
    a = check.assess(
        CustodyArrangement(
            "c",
            has_custody=False,
            qualified_custodian=False,
            account_statements_delivered=False,
            surprise_exam_current=False,
        )
    )
    assert a.compliant is True
    assert a.path == "no_custody"


def test_custody_standard_path_compliant() -> None:
    chain = AuditChain(deployer_id="d")
    check = CustodyRuleCheck(audit_chain=chain)
    a = check.assess(
        CustodyArrangement(
            "c",
            has_custody=True,
            qualified_custodian=True,
            account_statements_delivered=True,
            surprise_exam_current=True,
        )
    )
    assert a.compliant is True
    assert a.path == "standard"
    assert any(e.event_type is AuditEventType.CUSTODY_CHECK for e in chain.events())


def test_custody_audit_exception_met() -> None:
    check = CustodyRuleCheck()
    a = check.assess(
        CustodyArrangement(
            "fund",
            has_custody=True,
            qualified_custodian=True,
            account_statements_delivered=True,
            surprise_exam_current=False,
            is_pooled_vehicle=True,
            audited_financials_distributed=True,
            days_to_distribute_audited_financials=100,  # within 120
        )
    )
    assert a.compliant is True
    assert a.path == "audit_exception"


def test_custody_fund_of_funds_180_day_window() -> None:
    # A fund of funds distributing at day 165 is COMPLIANT (180-day staff window),
    # not a false exception — the defect the regulatory chamber flagged.
    check = CustodyRuleCheck()
    fof = check.assess(
        CustodyArrangement(
            "fof",
            has_custody=True,
            qualified_custodian=True,
            account_statements_delivered=True,
            surprise_exam_current=False,
            is_pooled_vehicle=True,
            is_fund_of_funds=True,
            audited_financials_distributed=True,
            days_to_distribute_audited_financials=165,
        )
    )
    assert fof.compliant is True
    assert fof.path == "audit_exception"
    # The same 165 days for a NON-fund-of-funds (120-day window) is an exception.
    not_fof = check.assess(
        CustodyArrangement(
            "pe",
            has_custody=True,
            qualified_custodian=True,
            account_statements_delivered=True,
            surprise_exam_current=False,
            is_pooled_vehicle=True,
            is_fund_of_funds=False,
            audited_financials_distributed=True,
            days_to_distribute_audited_financials=165,
        )
    )
    assert not_fof.compliant is False


def test_custody_audit_exception_missed_window() -> None:
    chain = AuditChain(deployer_id="d")
    check = CustodyRuleCheck(audit_chain=chain)
    a = check.assess(
        CustodyArrangement(
            "fund",
            has_custody=True,
            qualified_custodian=True,
            account_statements_delivered=True,
            surprise_exam_current=False,
            is_pooled_vehicle=True,
            audited_financials_distributed=True,
            days_to_distribute_audited_financials=150,  # missed 120
        )
    )
    assert a.compliant is False
    assert any("120 days" in e for e in a.exceptions)
    assert any("surprise examination" in e for e in a.exceptions)
    assert any(e.event_type is AuditEventType.CUSTODY_EXCEPTION for e in chain.events())


def test_custody_missing_qualified_custodian_and_statements() -> None:
    check = CustodyRuleCheck()
    a = check.assess(
        CustodyArrangement(
            "c",
            has_custody=True,
            qualified_custodian=False,
            account_statements_delivered=False,
            surprise_exam_current=True,
        )
    )
    assert a.compliant is False
    assert any("qualified custodian" in e for e in a.exceptions)
    assert any("account statements" in e for e in a.exceptions)


# --- marketing rule ---------------------------------------------------------


def test_marketing_clean_ad_approved() -> None:
    chain = AuditChain(deployer_id="d")
    gate = MarketingReviewGate(audit_chain=chain)
    r = gate.review(
        Advertisement("ad", shows_gross_performance=True, shows_net_at_equal_prominence=True)
    )
    assert r.approved is True
    assert any(e.event_type is AuditEventType.MARKETING_REVIEW for e in chain.events())


def test_marketing_net_only_does_not_trigger_d1() -> None:
    # (d)(1) is triggered by GROSS performance; net-only is fine.
    gate = MarketingReviewGate()
    r = gate.review(Advertisement("ad", shows_gross_performance=False))
    assert r.approved is True


def test_marketing_hypothetical_violations() -> None:
    gate = MarketingReviewGate()
    r = gate.review(Advertisement("ad", contains_hypothetical_performance=True))
    assert r.approved is False
    # (d)(6) has FOUR sub-conditions modeled: policies, relevance, criteria/
    # assumptions, risk/limitations.
    assert len(r.violations) == 4
    assert any("(d)(6)(iii)" in v for v in r.violations)  # risk/limitations cite corrected
    assert any("(d)(6)(ii)" in v for v in r.violations)  # criteria/assumptions present


def test_marketing_testimonial_and_gross_only() -> None:
    gate = MarketingReviewGate()
    r = gate.review(
        Advertisement(
            "ad",
            contains_testimonial=True,
            testimonial_has_disclosure=False,
            shows_gross_performance=True,
            shows_net_at_equal_prominence=False,
        )
    )
    assert r.approved is False
    assert any("testimonial" in v for v in r.violations)
    assert any("(d)(1)" in v for v in r.violations)


# --- allocation fairness ----------------------------------------------------


def test_allocation_fair_when_even() -> None:
    chain = AuditChain(deployer_id="d")
    mon = AllocationFairnessMonitor(audit_chain=chain)
    fills = [Fill(f"f{i}", i % 2 == 0, True) for i in range(4)]
    fills += [Fill(f"o{i}", i % 2 == 0, False) for i in range(4)]
    r = mon.assess("blk", fills)
    assert r.fair is True
    assert any(e.event_type is AuditEventType.ALLOCATION_DECISION for e in chain.events())


def test_allocation_insufficient_sample() -> None:
    mon = AllocationFairnessMonitor(min_favored=2, min_other=2)
    r = mon.assess("blk", [Fill("a", True, True)])
    assert r.fair is True
    assert any("insufficient sample" in x for x in r.reasons)


def test_allocation_construction_guards() -> None:
    with pytest.raises(ValueError):
        AllocationFairnessMonitor(max_disparity=1.5)
    with pytest.raises(ValueError):
        AllocationFairnessMonitor(min_favored=0)


# --- books and records ------------------------------------------------------


def test_books_approved_channel_ok() -> None:
    mon = BooksAndRecordsMonitor(approved_channels=frozenset({"corporate_email"}))
    f = mon.evaluate_communication(
        CommunicationEvent("c1", "corporate_email", is_business_communication=True, captured=True)
    )
    assert f.compliant is True


def test_books_offchannel_captured_is_ok() -> None:
    # A non-approved channel that WAS captured (e.g. an archived app) is not flagged.
    mon = BooksAndRecordsMonitor(approved_channels=frozenset({"corporate_email"}))
    f = mon.evaluate_communication(
        CommunicationEvent("c2", "personal_text", is_business_communication=True, captured=True)
    )
    assert f.compliant is True


def test_books_personal_nonbusiness_not_flagged() -> None:
    mon = BooksAndRecordsMonitor(approved_channels=frozenset({"corporate_email"}))
    f = mon.evaluate_communication(
        CommunicationEvent("c3", "personal_text", is_business_communication=False, captured=False)
    )
    assert f.compliant is True


def test_books_retention_exceptions() -> None:
    chain = AuditChain(deployer_id="d")
    mon = BooksAndRecordsMonitor(audit_chain=chain)
    early_disposal = mon.evaluate_retention(
        RecordRetention(
            "r1", "advertisement", age_years=3.0, readily_accessible=True, disposed=True
        )
    )
    assert early_disposal.compliant is False
    not_accessible = mon.evaluate_retention(
        RecordRetention("r2", "order", age_years=1.0, readily_accessible=False, disposed=False)
    )
    assert not_accessible.compliant is False
    ok = mon.evaluate_retention(
        RecordRetention("r3", "order", age_years=1.0, readily_accessible=True, disposed=False)
    )
    assert ok.compliant is True
    assert any(
        e.event_type is AuditEventType.OFF_CHANNEL_FLAG
        or e.event_type is AuditEventType.RECORDKEEPING_EVENT
        for e in chain.events()
    )


# --- obligation map (adviser §206 grounding) --------------------------------


def test_obligations_grounded_in_advisers_act() -> None:
    """Every obligation cites the Advisers Act / its rules — the adviser
    fiduciary regime — and none other. Tokens are specific (a bare '204' would
    match almost any CFR-ish string; require the actual adviser-regime cites)."""
    adviser_cites = (
        "Advisers Act",  # §206 / §204A / §204-2 narrative
        "275.",  # 17 CFR Part 275 adviser rules
        "80b",  # 15 U.S.C. 80b-* Advisers Act
        "IA-5248",  # the 2019 fiduciary interpretation
        "10b-5",  # the insider-trading anchor
        "§204A",  # MNPI policies
        "§206",  # fiduciary
    )
    for o in ALL_OBLIGATIONS.values():
        assert any(tok in o.citation for tok in adviser_cites), (
            f"{o.obligation_id} not grounded in an adviser-regime cite: {o.citation}"
        )


def test_every_sub_vertical_maps_to_real_obligations() -> None:
    for sub in SubVertical:
        oids = SUB_VERTICAL_OBLIGATIONS[sub]
        assert oids, f"{sub} has no obligations"
        for oid in oids:
            assert oid in ALL_OBLIGATIONS
        assert obligations_for(sub)  # resolves without KeyError


def test_buy_side_names_best_ex_books_and_mnpi() -> None:
    oids = SUB_VERTICAL_OBLIGATIONS[SubVertical.BUY_SIDE_QUANT]
    assert "best_execution" in oids
    assert "books_and_records" in oids
    assert "mnpi_surveillance" in oids


def test_all_obligations_have_primary_sources() -> None:
    for o in ALL_OBLIGATIONS.values():
        assert o.primary_source_url.startswith("https://")
        assert o.citation
        assert o.verified is True  # all nine are primary-source verified


# --- CLI --------------------------------------------------------------------


def test_cli_version(capsys) -> None:
    from private_capital_agent_audit.cli import main

    assert main(["version"]) == 0
    from private_capital_agent_audit import __version__

    assert __version__ in capsys.readouterr().out


def test_cli_obligations_all(capsys) -> None:
    from private_capital_agent_audit.cli import main

    assert main(["obligations"]) == 0
    out = capsys.readouterr().out
    assert "best_execution" in out
    assert "custody_rule" in out


def test_cli_obligations_sub_vertical(capsys) -> None:
    from private_capital_agent_audit.cli import main

    assert main(["obligations", "buy_side_quant"]) == 0
    assert "mnpi_surveillance" in capsys.readouterr().out


def test_cli_unknown_sub_vertical(capsys) -> None:
    from private_capital_agent_audit.cli import main

    assert main(["obligations", "nope"]) == 2


def test_cli_help_and_unknown(capsys) -> None:
    from private_capital_agent_audit.cli import main

    assert main([]) == 0
    assert main(["help"]) == 0
    assert main(["frobnicate"]) == 2
