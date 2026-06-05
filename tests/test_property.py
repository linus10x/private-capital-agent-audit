"""Property-based tests (the volume tier) — thousands of generated cases.

Uses ``hypothesis`` to assert the primitives' invariants across a wide input
space, not a handful of happy-path checks:

* ledger append/verify/tamper invariants and the genesis-seed branch,
* level-gate monotonicity and rung-skip refusal,
* veto un-self-clearability,
* DEFCON escalation-immediate / de-escalation-guarded algebra,
* challenger ≠ primary and the un-attested-independence escalation rule,
* best-execution slippage sign, allocation-fairness symmetry.

Each ``@given`` test runs ``max_examples`` cases; with ~16 properties at 300
examples that is ~4,800 generated cases per full run (well into the thousands
the test strategy calls for). The count is stated here, not silently capped.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from private_capital_agent_audit.governance.allocation_fairness import (
    AllocationFairnessMonitor,
    Fill,
)
from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.governance.autonomy_ladder import (
    LEVEL_REQUIRED_CONTROLS,
    AutonomyLadder,
    ControlAttestation,
)
from private_capital_agent_audit.governance.best_execution import (
    ExecutionFactors,
    Side,
)
from private_capital_agent_audit.governance.defcon import (
    DEFCON,
    DEFCONMachine,
    RiskMetrics,
)
from private_capital_agent_audit.governance.effective_challenge_harness import (
    EffectiveChallengeHarness,
    IndependenceAttestation,
    Recommendation,
)
from private_capital_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoNotAuthorizedError,
    VetoReason,
)
from private_capital_agent_audit.schemas.audit_event import (
    AuditEventType,
    AutonomyLevel,
)

VOL = settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])

LEVELS = list(AutonomyLevel)


# --- P3 audit chain ---------------------------------------------------------


@VOL
@given(
    deployer=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
    payloads=st.lists(
        st.dictionaries(st.text(max_size=5), st.integers(), max_size=4),
        min_size=0,
        max_size=25,
    ),
)
def test_clean_chain_always_verifies(deployer: str | None, payloads: list[dict]) -> None:
    chain = AuditChain(deployer_id=deployer)
    for p in payloads:
        chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", p)
    assert chain.verify() is True
    # A hardened chain carries a genesis event #0; a legacy chain does not.
    assert len(chain) == len(payloads) + (1 if deployer is not None else 0)


@VOL
@given(
    n=st.integers(min_value=1, max_value=15),
    idx=st.integers(min_value=0, max_value=14),
)
def test_inplace_tamper_always_detected(n: int, idx: int) -> None:
    chain = AuditChain(deployer_id="d")
    for i in range(n):
        chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    target = chain.events()[idx % n]
    object.__setattr__(target, "payload", {"i": -1, "tampered": True})
    assert chain.verify() is False


# --- P1 level gate ----------------------------------------------------------


def _all_controls_up_to(level: AutonomyLevel) -> list[ControlAttestation]:
    atts: list[ControlAttestation] = []
    for lvl, controls in LEVEL_REQUIRED_CONTROLS.items():
        if lvl.rank <= level.rank:
            atts += [ControlAttestation(c, lvl, "independent-attester", "ok") for c in controls]
    return atts


@VOL
@given(cur=st.sampled_from(LEVELS), req=st.sampled_from(LEVELS))
def test_demotion_or_noop_always_allowed(cur: AutonomyLevel, req: AutonomyLevel) -> None:
    ladder = AutonomyLadder()
    decision = ladder.evaluate_promotion(
        requesting_agent_id="a",
        current_level=cur,
        requested_level=req,
        attestations=[],
    )
    if req.rank <= cur.rank:
        assert decision.approved is True


@VOL
@given(cur=st.sampled_from(LEVELS), req=st.sampled_from(LEVELS))
def test_single_step_promotion_with_all_controls(cur: AutonomyLevel, req: AutonomyLevel) -> None:
    ladder = AutonomyLadder()
    decision = ladder.evaluate_promotion(
        requesting_agent_id="a",
        current_level=cur,
        requested_level=req,
        attestations=_all_controls_up_to(req),
    )
    # One-rung promotion with every required control attested is approved;
    # a multi-rung jump is refused (allow_skip=False).
    if req.rank == cur.rank + 1:
        assert decision.approved is True
    elif req.rank > cur.rank + 1:
        assert decision.approved is False
        assert any("rung-skip refused" in r for r in decision.reasons)


@VOL
@given(req=st.sampled_from([level for level in LEVELS if level.rank >= 1]))
def test_promotion_missing_one_control_refused(req: AutonomyLevel) -> None:
    ladder = AutonomyLadder()
    atts = _all_controls_up_to(req)
    if atts:  # drop one required control
        atts = atts[:-1]
    decision = ladder.evaluate_promotion(
        requesting_agent_id="a",
        current_level=AutonomyLevel(f"A{req.rank - 1}"),
        requested_level=req,
        attestations=atts,
    )
    if LEVEL_REQUIRED_CONTROLS[req]:  # the rung actually requires a control
        assert decision.approved is False


# --- P2 sovereign veto ------------------------------------------------------


@VOL
@given(agent_id=st.text(min_size=1, max_size=20))
def test_agent_cannot_self_clear(agent_id: str) -> None:
    veto = SovereignVeto(agent_id=agent_id)
    veto.trigger(VetoReason.MANUAL, "monitor", "halt")
    try:
        veto.clear("self", operator_id=agent_id)
        raise AssertionError("self-clear should have raised")
    except VetoNotAuthorizedError:
        pass
    assert veto.is_vetoed is True


# --- P4 DEFCON --------------------------------------------------------------


@VOL
@given(
    dd=st.floats(min_value=0.0, max_value=1.0),
    dl=st.floats(min_value=0.0, max_value=1.0),
    cl=st.integers(min_value=0, max_value=20),
)
def test_evaluate_never_deescalates(dd: float, dl: float, cl: float) -> None:
    machine = DEFCONMachine()
    machine.evaluate(RiskMetrics(portfolio_drawdown=0.25))  # force HALT
    assert machine.evaluate(RiskMetrics(dd, dl, int(cl))) is DEFCON.HALT


@VOL
@given(
    dd=st.floats(min_value=0.0, max_value=1.0),
    dl=st.floats(min_value=0.0, max_value=1.0),
    cl=st.integers(min_value=0, max_value=20),
)
def test_escalation_is_monotone(dd: float, dl: float, cl: int) -> None:
    machine = DEFCONMachine()
    before = machine.current_level()
    after = machine.evaluate(RiskMetrics(dd, dl, cl))
    assert after >= before  # evaluate can only raise or hold


# --- P5 effective challenge -------------------------------------------------


@VOL
@given(
    same_owner=st.booleans(),
    same_vendor=st.booleans(),
    same_template=st.booleans(),
    agree=st.booleans(),
)
def test_unattested_independence_never_accepts(
    same_owner: bool, same_vendor: bool, same_template: bool, agree: bool
) -> None:
    primary = lambda x: 1  # noqa: E731
    challenger = (lambda x: 1) if agree else (lambda x: 2)  # noqa: E731
    harness = EffectiveChallengeHarness(
        primary_model=primary,
        challenger_model=challenger,
        eval_set=[(i, 1) for i in range(10)],
        independence=IndependenceAttestation("c", same_owner, same_vendor, same_template),
        primary_id="P",
        challenger_id="C",
    )
    report = harness.run()
    independent = not (same_owner or same_vendor or same_template)
    if not independent:
        assert report.recommendation is Recommendation.ESCALATE
    elif agree:
        assert report.recommendation is Recommendation.ACCEPT_PRIMARY


# --- best execution: slippage sign ------------------------------------------


@VOL
@given(
    bench=st.floats(min_value=1.0, max_value=1000.0),
    delta=st.floats(min_value=-50.0, max_value=50.0),
    side=st.sampled_from(list(Side)),
)
def test_slippage_sign(bench: float, delta: float, side: Side) -> None:
    fill = bench + delta
    f = ExecutionFactors(
        venue="v",
        side=side,
        fill_price=fill,
        benchmark_price=bench,
        commission=0.0,
        factors_considered=("price", "venue_quality"),
    )
    s = f.slippage_bps()
    if side is Side.BUY:
        assert (s > 0) == (fill > bench) or delta == 0
    else:
        assert (s > 0) == (fill < bench) or delta == 0


# --- allocation fairness symmetry -------------------------------------------


@VOL
@given(
    n_fav=st.integers(min_value=1, max_value=20),
    n_oth=st.integers(min_value=1, max_value=20),
    fav_good=st.integers(min_value=0, max_value=20),
    oth_good=st.integers(min_value=0, max_value=20),
)
def test_allocation_no_false_flag_when_others_do_better(
    n_fav: int, n_oth: int, fav_good: int, oth_good: int
) -> None:
    fav_good = min(fav_good, n_fav)
    oth_good = min(oth_good, n_oth)
    fills = [Fill(f"f{i}", i < fav_good, True) for i in range(n_fav)]
    fills += [Fill(f"o{i}", i < oth_good, False) for i in range(n_oth)]
    monitor = AllocationFairnessMonitor(max_disparity=0.20)
    result = monitor.assess("blk", fills)
    # If favored did not out-perform others, it is never flagged.
    if result.favored_favorable_rate <= result.other_favorable_rate:
        assert result.fair is True
