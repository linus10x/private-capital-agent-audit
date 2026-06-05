"""Regression tests for the adversarial-review remediations.

Each test pins a defect the beat-the-shit / JPMC-audit pass surfaced, so it
cannot silently return: chain tail-truncation / torn-load resistance, the
Unicode MNPI bypass, NaN/inf fail-opens, allocation single-group concentration,
the PE↔MNPI obligation mapping, and the valuation-governance control.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from private_capital_agent_audit.governance.allocation_fairness import (
    AllocationFairnessMonitor,
    Fill,
)
from private_capital_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
    InMemoryWitnessRegister,
)
from private_capital_agent_audit.governance.defcon import DEFCON, DEFCONMachine, RiskMetrics
from private_capital_agent_audit.governance.mnpi_surveillance import (
    ListType,
    MNPISurveillance,
    ScreenOutcome,
)
from private_capital_agent_audit.governance.obligation_map import (
    SUB_VERTICAL_OBLIGATIONS,
    SubVertical,
)
from private_capital_agent_audit.governance.valuation_governance import (
    PriceSource,
    ValuationGovernanceCheck,
    ValuationInput,
)
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel

# --- P3: tail-truncation / regeneration / torn-load -------------------------


def _seed_chain(n: int) -> tuple[AuditChain, InMemoryWitnessRegister]:
    witness = InMemoryWitnessRegister()
    chain = AuditChain(deployer_id="acme", witness_register=witness, mode="production")
    for i in range(n):
        chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    return chain, witness


def test_truncation_below_anchor_detected() -> None:
    chain, _ = _seed_chain(5)
    chain.anchor_to_witness()  # checkpoint at the current tail
    # verify() (internal) still passes a truncated prefix, but the witness catches it.
    del chain._store[3:]  # drop below the anchored sequence
    assert chain.verify() is True  # internally consistent prefix
    assert chain.verify_regeneration_resistant() is False  # anchored checkpoint gone


def test_full_regeneration_detected() -> None:
    _, witness = _seed_chain(5)
    # Original chain anchored; rebuild a fresh chain sharing the witness.
    orig = AuditChain(deployer_id="acme", witness_register=witness, mode="production")
    for i in range(5):
        orig.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    orig.anchor_to_witness()
    regen = AuditChain(deployer_id="acme", witness_register=witness, mode="production")
    for i in range(5):
        regen.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    assert regen.verify() is True
    assert regen.verify_regeneration_resistant() is False  # checkpoint head differs


def test_tail_rewrite_and_restamp_of_witnessed_tail_detected() -> None:
    """After anchoring, the witnessed checkpoint IS the tail (the anchor event).
    Rewriting + re-stamping that tail passes internal verify() (no successor links
    to it), but the external witness checkpoint no longer matches — caught."""
    chain, _ = _seed_chain(3)
    chain.anchor_to_witness()
    assert chain.head_is_witnessed() is True
    tail = chain.events()[-1]  # the WITNESS_ANCHOR event = the witnessed tail
    object.__setattr__(tail, "payload", {"FORGED": True})
    object.__setattr__(tail, "event_hash", tail.compute_hash())
    assert chain.verify() is True  # internally consistent (restamped, no successor)
    assert chain.verify_regeneration_resistant() is False  # witness catches it
    assert chain.head_is_witnessed() is False


def test_post_anchor_tail_rewrite_is_the_documented_residual() -> None:
    """A NON-witnessed tail (an event appended after the last anchor) can be
    rewritten undetected — the irreducible residual documented in FAILURE-MODES.
    The mitigation is anchor cadence: head_is_witnessed() reveals the exposure."""
    chain, _ = _seed_chain(3)
    chain.anchor_to_witness()
    chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": 99})
    assert chain.head_is_witnessed() is False  # exposure is visible
    tail = chain.events()[-1]
    object.__setattr__(tail, "payload", {"FORGED": True})
    object.__setattr__(tail, "event_hash", tail.compute_hash())
    # Residual: undetected internally AND by the (stale) witness checkpoint.
    assert chain.verify() is True
    assert chain.verify_regeneration_resistant() is True


def test_sequence_reorder_detected() -> None:
    chain, _ = _seed_chain(4)
    s = chain._store
    s[2], s[3] = s[3], s[2]  # swap two events (hashes intact, sequence now out of order)
    assert chain.verify() is False
    with pytest.raises(AuditChainTamperError):
        chain.verify_strict()


def test_torn_trailing_line_recovers_prefix(tmp_path: Path) -> None:
    log = tmp_path / "led.jsonl"
    chain = AuditChain(log_file=log, deployer_id="d")
    for i in range(3):
        chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    # Simulate a crash mid-append: append a half-written JSON line.
    with log.open("a", encoding="utf-8") as fh:
        fh.write('{"sequence": 4, "event_type": "agent_action"')  # no newline, truncated
    reopened = AuditChain(log_file=log, deployer_id="d")
    assert len(reopened) == 4  # genesis + 3 valid events; torn line dropped
    assert reopened.verify() is False  # refuses to certify clean
    with pytest.raises(AuditChainTamperError):
        reopened.verify_strict()


def test_malformed_interior_line_raises(tmp_path: Path) -> None:
    log = tmp_path / "led.jsonl"
    chain = AuditChain(log_file=log, deployer_id="d")
    for i in range(3):
        chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    lines = log.read_text(encoding="utf-8").splitlines()
    lines.insert(2, "{not valid json")  # corrupt an interior line
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(AuditChainTamperError, match="interior"):
        AuditChain(log_file=log, deployer_id="d")


def test_post_anchor_tail_residual_is_documented_only() -> None:
    """The irreducible residual: events appended AFTER the last anchor and then
    dropped are not internally detectable (documented in FAILURE-MODES)."""
    chain, _ = _seed_chain(3)
    chain.anchor_to_witness()  # checkpoint at sequence 3
    chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": 99})
    del chain._store[-1:]  # drop the post-anchor event
    # This is the residual: still passes (the anchored checkpoint is intact).
    assert chain.verify_regeneration_resistant() is True


# --- MNPI Unicode bypass -----------------------------------------------------


def test_mnpi_zero_width_bypass_blocked() -> None:
    surv = MNPISurveillance()
    surv.add("AAPL", ListType.RESTRICTED, "holds MNPI")
    # Zero-width space spliced into the symbol must still resolve to AAPL.
    spliced = "A​APL"
    assert surv.is_restricted(spliced) is True
    assert surv.screen_order("o1", spliced).outcome is ScreenOutcome.BLOCKED


def test_mnpi_fullwidth_bypass_blocked() -> None:
    surv = MNPISurveillance()
    surv.add("AAPL", ListType.RESTRICTED, "holds MNPI")
    fullwidth = "ＡＡＰＬ"  # fullwidth AAPL
    assert surv.screen_order("o2", fullwidth).outcome is ScreenOutcome.BLOCKED


def test_mnpi_whitespace_bypass_blocked() -> None:
    surv = MNPISurveillance()
    surv.add("AAPL", ListType.RESTRICTED, "holds MNPI")
    assert surv.screen_order("o3", "A APL").outcome is ScreenOutcome.BLOCKED  # NBSP


def test_mnpi_cyrillic_homoglyph_flagged_not_cleared() -> None:
    """NFKC does not fold a Cyrillic 'А' (U+0410) to Latin 'A'. The homoglyphed
    symbol must NOT silently CLEAR — it is surfaced (FLAGGED) for review."""
    surv = MNPISurveillance()
    surv.add("AAPL", ListType.RESTRICTED, "holds MNPI")
    homoglyph = "АAPL"  # leading Cyrillic А
    result = surv.screen_order("o4", homoglyph)
    assert result.outcome is ScreenOutcome.FLAGGED
    assert "homoglyph" in result.reason


def test_mnpi_add_rejects_homoglyph_list_entry() -> None:
    surv = MNPISurveillance()
    with pytest.raises(ValueError, match="homoglyph"):
        surv.add("АAPL", ListType.RESTRICTED, "Cyrillic in a list entry")


def test_best_ex_negative_fill_fails_closed() -> None:
    from private_capital_agent_audit.governance.best_execution import (
        BestExecutionGate,
        ExecutionFactors,
        Side,
    )

    gate = BestExecutionGate()
    review = gate.review_order(
        "ord-neg",
        ExecutionFactors(
            venue="v",
            side=Side.BUY,
            fill_price=-50.0,  # would otherwise compute as a huge favorable fill
            benchmark_price=100.0,
            commission=0.0,
            factors_considered=("price", "venue_quality"),
        ),
    )
    assert review.approved is False


def test_valuation_negative_days_rejected() -> None:
    check = ValuationGovernanceCheck()
    with pytest.raises(ValueError, match="non-negative"):
        check.assess(
            ValuationInput("a", 1, PriceSource.INDEPENDENT, True, days_since_last_valuation=-5)
        )


# --- allocation single-group concentration ----------------------------------


def test_allocation_single_group_concentration_flagged() -> None:
    monitor = AllocationFairnessMonitor()
    # Every favorable fill went to favored/proprietary accounts; no comparison group.
    fills = [Fill(f"prop{i}", favorable=True, is_favored=True) for i in range(5)]
    result = monitor.assess("blk", fills)
    assert result.fair is False
    assert any("concentration" in r for r in result.reasons)


def test_allocation_single_fill_still_insufficient() -> None:
    monitor = AllocationFairnessMonitor(min_favored=2, min_other=2)
    result = monitor.assess("blk", [Fill("a", favorable=True, is_favored=True)])
    assert result.fair is True
    assert any("insufficient sample" in r for r in result.reasons)


# --- DEFCON NaN fail-safe ----------------------------------------------------


def test_defcon_nan_metric_halts() -> None:
    machine = DEFCONMachine()
    assert machine.evaluate(RiskMetrics(portfolio_drawdown=math.nan)) is DEFCON.HALT


def test_defcon_inf_metric_halts() -> None:
    machine = DEFCONMachine()
    assert machine.evaluate(RiskMetrics(daily_loss=math.inf)) is DEFCON.HALT


# --- PE ↔ MNPI obligation mapping -------------------------------------------


def test_pe_credit_gp_maps_mnpi() -> None:
    assert "mnpi_surveillance" in SUB_VERTICAL_OBLIGATIONS[SubVertical.PE_CREDIT_GP]


# --- valuation governance ----------------------------------------------------


def test_valuation_level3_without_attestation_flagged() -> None:
    chain = AuditChain(deployer_id="d")
    check = ValuationGovernanceCheck(audit_chain=chain)
    a = check.assess(
        ValuationInput(
            asset_id="asset-1",
            level=3,
            price_source=PriceSource.ADVISER_MARKED,
            independent_attestation=False,
            days_since_last_valuation=10,
        )
    )
    assert a.compliant is False
    assert a.requires_independence is True
    assert any("duty-of-loyalty" in f for f in a.flags)
    assert any(e.event_type is AuditEventType.VALUATION_EXCEPTION for e in chain.events())


def test_valuation_level3_with_attestation_ok() -> None:
    check = ValuationGovernanceCheck()
    a = check.assess(
        ValuationInput(
            asset_id="asset-2",
            level=3,
            price_source=PriceSource.ADVISER_MARKED,
            independent_attestation=True,
            days_since_last_valuation=10,
        )
    )
    assert a.compliant is True


def test_valuation_manual_override_requires_independence() -> None:
    check = ValuationGovernanceCheck()
    a = check.assess(
        ValuationInput(
            asset_id="asset-3",
            level=1,
            price_source=PriceSource.INDEPENDENT,
            independent_attestation=False,
            days_since_last_valuation=1,
            manual_override=True,
        )
    )
    assert a.requires_independence is True
    assert a.compliant is False


def test_valuation_level1_independent_ok() -> None:
    chain = AuditChain(deployer_id="d")
    check = ValuationGovernanceCheck(audit_chain=chain)
    a = check.assess(
        ValuationInput(
            asset_id="asset-4",
            level=1,
            price_source=PriceSource.INDEPENDENT,
            independent_attestation=False,  # Level-1 quoted does not need attestation
            days_since_last_valuation=5,
        )
    )
    assert a.requires_independence is False
    assert a.compliant is True
    assert any(e.event_type is AuditEventType.VALUATION_REVIEW for e in chain.events())


def test_valuation_stale_mark_flagged() -> None:
    check = ValuationGovernanceCheck(max_staleness_days=30)
    a = check.assess(
        ValuationInput(
            asset_id="asset-5",
            level=2,
            price_source=PriceSource.VENDOR,
            independent_attestation=False,
            days_since_last_valuation=120,
        )
    )
    assert a.compliant is False
    assert any("stale mark" in f for f in a.flags)


def test_valuation_invalid_level_and_construction_guard() -> None:
    with pytest.raises(ValueError):
        ValuationGovernanceCheck(max_staleness_days=0)
    check = ValuationGovernanceCheck()
    with pytest.raises(ValueError, match="level must be"):
        check.assess(ValuationInput("a", 4, PriceSource.INDEPENDENT, True, 1))
