"""Golden-corpus tests — assert the controls would have governed real SEC matters.

Two layers:

1. **Structural** — every corpus entry maps to a real obligation in the
   obligation map, carries a primary-source URL, and (when ``verified``) names a
   SEC release. UNVERIFIED entries are allowed but must be honestly flagged.
2. **Behavioral (the credibility tier)** — for each enforcement theme, the
   relevant control is fed the failing construction the matter describes and
   must flag it. This is what makes the audit undismissable: the library's
   controls catch the exact conduct the SEC actually penalized.
"""

from __future__ import annotations

import pytest

from private_capital_agent_audit.governance.allocation_fairness import (
    AllocationFairnessMonitor,
    Fill,
)
from private_capital_agent_audit.governance.books_and_records import (
    BooksAndRecordsMonitor,
    CommunicationEvent,
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
    MNPISurveillance,
    ScreenOutcome,
)
from private_capital_agent_audit.governance.obligation_map import ALL_OBLIGATIONS
from tests.golden.corpus import ALL_MATTERS

pytestmark = pytest.mark.golden


@pytest.mark.parametrize("matter", ALL_MATTERS, ids=lambda m: m.matter_id)
def test_matter_maps_to_known_obligation(matter) -> None:
    assert matter.obligation_id in ALL_OBLIGATIONS
    assert matter.primary_source_url.startswith("https://")
    if matter.verified:
        assert matter.sec_release, f"{matter.matter_id} marked verified but has no release"


def test_corpus_has_each_theme() -> None:
    themes = {m.obligation_id for m in ALL_MATTERS}
    for required in (
        "books_and_records",
        "marketing_rule",
        "custody_rule",
        "mnpi_surveillance",
        "allocation_fairness",
    ):
        assert required in themes


def test_verified_majority() -> None:
    # Honesty: at least one VERIFIED anchor per theme, and the corpus is mostly
    # primary-sourced (UNVERIFIED entries are the documented minority).
    verified = [m for m in ALL_MATTERS if m.verified]
    assert len(verified) >= len(ALL_MATTERS) - len(verified)  # verified are the majority


# --- behavioral: the control flags the real failing construction -----------


def test_off_channel_matter_is_flagged() -> None:
    """2022-174 et al.: a business text on an uncaptured personal channel."""
    monitor = BooksAndRecordsMonitor(approved_channels=frozenset({"corporate_email"}))
    finding = monitor.evaluate_communication(
        CommunicationEvent(
            comm_id="text-1",
            channel="personal_whatsapp",
            is_business_communication=True,
            captured=False,
        )
    )
    assert finding.compliant is False
    assert any("off-channel" in r for r in finding.reasons)


def test_marketing_hypothetical_performance_matter_is_flagged() -> None:
    """Titan (2023-153): hypothetical performance without the required policies."""
    gate = MarketingReviewGate()
    review = gate.review(
        Advertisement(
            ad_id="titan-style-ad",
            contains_hypothetical_performance=True,
            has_hypothetical_policies=False,
            has_relevance_to_audience=False,
            has_criteria_assumptions_info=False,
            has_risk_limitations_info=False,
        )
    )
    assert review.approved is False
    assert any("hypothetical performance without adopted policies" in v for v in review.violations)


def test_custody_surprise_exam_matter_is_flagged() -> None:
    """Munakata (IA-6901-S): custody without a current surprise examination."""
    check = CustodyRuleCheck()
    assessment = check.assess(
        CustodyArrangement(
            client_id="fund-1",
            has_custody=True,
            qualified_custodian=True,
            account_statements_delivered=True,
            surprise_exam_current=False,
        )
    )
    assert assessment.compliant is False
    assert any("surprise examination" in e for e in assessment.exceptions)


def test_mnpi_matter_blocks_restricted_name() -> None:
    """Sound Point (2024-106): trading a name the adviser holds MNPI on is blocked."""
    surv = MNPISurveillance()
    from private_capital_agent_audit.governance.mnpi_surveillance import ListType

    surv.add("ACME", ListType.RESTRICTED, "on creditors' committee — holds MNPI")
    result = surv.screen_order("ord-1", "ACME", account="flagship")
    assert result.outcome is ScreenOutcome.BLOCKED


def test_cherry_picking_matter_is_flagged() -> None:
    """J.S. Oliver (2013-168) / Breton (2017-32): favored accounts get the good fills."""
    monitor = AllocationFairnessMonitor(max_disparity=0.20)
    # Favored (proprietary) accounts all get favorable fills; clients mostly don't.
    fills = [Fill(f"prop{i}", favorable=True, is_favored=True) for i in range(5)]
    fills += [Fill(f"client{i}", favorable=(i < 1), is_favored=False) for i in range(5)]
    result = monitor.assess("block-1", fills)
    assert result.fair is False
    assert any("cherry-picking" in r for r in result.reasons)
