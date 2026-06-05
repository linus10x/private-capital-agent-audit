"""Unit + contract tests for the five primitives — branch and edge coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from private_capital_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
    InMemoryWitnessRegister,
    _compute_genesis_hash,
)
from private_capital_agent_audit.governance.autonomy_ladder import (
    LEVEL_REQUIRED_CONTROLS,
    AutonomyLadder,
    ControlAttestation,
)
from private_capital_agent_audit.governance.defcon import (
    DEFCON,
    DEFCONMachine,
    DEFCONTransitionError,
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
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)
from tests.conftest import AcceptingVerifier, FakeAuthorizer, agent, human

# --- schema -----------------------------------------------------------------


def test_autonomy_level_properties() -> None:
    assert AutonomyLevel.A0_INFORMATIONAL.rank == 0
    assert AutonomyLevel.A4_PRODUCTION_AUTONOMOUS.rank == 4
    assert AutonomyLevel.A0_INFORMATIONAL.can_write is False
    assert AutonomyLevel.A2_DELEGATED.can_write is True
    assert AutonomyLevel.A1_ASSISTED.requires_human_approval is True
    assert AutonomyLevel.A3_SUPERVISED_AUTONOMOUS.requires_human_approval is False


def test_audit_event_roundtrip() -> None:
    e = AuditEvent(
        sequence=0,
        event_type=AuditEventType.AGENT_ACTION,
        autonomy_level=AutonomyLevel.A2_DELEGATED,
        agent_id="a",
        payload={"k": "v"},
        timestamp="2026-06-05T00:00:00+00:00",
        prev_hash="0" * 64,
    ).with_hash()
    restored = AuditEvent.from_dict(e.to_dict())
    assert restored == e
    assert restored.compute_hash() == e.event_hash


# --- P3 audit chain ---------------------------------------------------------


def test_chain_mode_validation() -> None:
    with pytest.raises(ValueError, match="mode must be"):
        AuditChain(mode="bogus")


def test_production_mode_requires_witness() -> None:
    with pytest.raises(ValueError, match="witness_register"):
        AuditChain(deployer_id="d", mode="production")
    # With a witness it constructs.
    AuditChain(deployer_id="d", witness_register=InMemoryWitnessRegister(), mode="production")


def test_genesis_seed_branches() -> None:
    legacy = AuditChain()
    assert legacy.genesis_seed() == "0" * 64
    hardened = AuditChain(deployer_id="acme", chain_creation_iso="2026-01-01T00:00:00+00:00")
    assert hardened.genesis_seed() == _compute_genesis_hash("acme", "2026-01-01T00:00:00+00:00")
    assert hardened.genesis_seed() != legacy.genesis_seed()


def test_chain_head_empty_returns_seed() -> None:
    # A legacy (un-keyed) chain is empty at construction; its head is the sentinel.
    legacy = AuditChain()
    assert legacy.chain_head() == legacy.genesis_seed() == "0" * 64
    # A hardened chain seeds a genesis event #0; its head is that event's hash and
    # the genesis event's prev_hash is the deployer-keyed seed.
    hardened = AuditChain(deployer_id="d")
    assert hardened.chain_head() == hardened.events()[0].event_hash
    assert hardened.events()[0].prev_hash == hardened.genesis_seed()


def test_chain_persistence_roundtrip(tmp_path: Path) -> None:
    log = tmp_path / "ledger.jsonl"
    chain = AuditChain(log_file=log, deployer_id="d")
    for i in range(3):
        chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    # Re-open WITHOUT passing chain_creation_iso: the genesis event carries it,
    # so the reopened chain re-derives the correct seed (no wall-clock drift).
    reopened = AuditChain(log_file=log, deployer_id="d")
    assert len(reopened) == 4  # genesis event #0 + the 3 appended events
    assert reopened.verify() is True
    assert reopened.events()[0].event_type is AuditEventType.GENESIS


def test_anchor_requires_witness() -> None:
    chain = AuditChain(deployer_id="d")
    with pytest.raises(ValueError, match="no witness_register"):
        chain.anchor_to_witness()
    with pytest.raises(ValueError, match="no witness_register"):
        chain.verify_regeneration_resistant()


def test_prev_hash_break_detected() -> None:
    chain = AuditChain(deployer_id="d")
    chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": 0})
    chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": 1})
    object.__setattr__(chain.events()[1], "prev_hash", "deadbeef")
    assert chain.verify() is False


def test_prev_link_break_isolated_from_hash_and_sequence_checks() -> None:
    """Break ONLY the prev_hash link: tamper an event's prev_hash AND re-stamp its
    own event_hash, leaving sequence intact. Now the event's own-hash check passes
    and its sequence is contiguous — only the prev_hash *link* check can catch the
    broken chain. This isolates the link check (which the other checks would
    otherwise mask)."""
    chain = AuditChain(deployer_id="d")
    for i in range(3):
        chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    ev = chain.events()[2]
    object.__setattr__(ev, "prev_hash", "0" * 64)  # wrong link
    object.__setattr__(ev, "event_hash", ev.compute_hash())  # restamp → own-hash consistent
    assert ev.sequence == 2  # sequence untouched
    assert ev.event_hash == ev.compute_hash()  # own-hash check would pass
    assert chain.verify() is False  # only the prev_hash link check fires
    with pytest.raises(AuditChainTamperError):
        chain.verify_strict()


def test_sequence_gap_isolated_from_hash_and_link_checks() -> None:
    """Forge a chain with a SEQUENCE GAP but otherwise-consistent links and
    hashes: drop a middle event, then re-point and re-stamp the successor so its
    prev_hash links and its own hash recompute. Now only the sequence-contiguity
    check can detect that an event is missing (sequence 0,1,3 at indices 0,1,2)."""
    chain = AuditChain(deployer_id="d")
    for i in range(3):
        chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    # store == [genesis(0), e0(1), e1(2), e2(3)]; drop e1, then repair the link.
    del chain._store[2]
    successor = chain.events()[2]  # was e2, sequence 3, now at index 2
    predecessor_hash = chain.events()[1].event_hash
    object.__setattr__(successor, "prev_hash", predecessor_hash)  # link repaired
    object.__setattr__(successor, "event_hash", successor.compute_hash())  # own-hash repaired
    # Links and hashes are now internally consistent; only the sequence gap remains.
    assert successor.sequence == 3  # at index 2 — the gap
    assert chain.verify() is False  # only the sequence-contiguity check fires
    with pytest.raises(AuditChainTamperError, match="sequence"):
        chain.verify_strict()


def test_spliced_chain_detected_by_prev_link() -> None:
    """Dropping a middle event leaves every remaining event INTERNALLY consistent
    (its own event_hash still matches its fields), so only the prev_hash *link*
    check catches the break — this is what the link check exists for."""
    chain = AuditChain(deployer_id="d")
    for i in range(3):
        chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": i})
    # store == [genesis, e0, e1, e2]; excise e1. Each surviving event's own hash
    # is still valid; the link e0 -> e2 is broken (e2.prev_hash points to e1).
    del chain._store[2]
    for ev in chain.events():
        assert ev.event_hash == ev.compute_hash()  # all internally consistent
    assert chain.verify() is False  # the prev_hash link check fires
    with pytest.raises(AuditChainTamperError):
        chain.verify_strict()


# --- P2 sovereign veto ------------------------------------------------------


def test_veto_production_requires_authorizer() -> None:
    with pytest.raises(ValueError, match="requires a wired authorizer"):
        SovereignVeto(agent_id="z", mode="production")


def test_veto_advisory_clear_records_unauthenticated() -> None:
    chain = AuditChain(deployer_id="d")
    veto = SovereignVeto(agent_id="z", audit_chain=chain)
    veto.trigger(VetoReason.MANUAL, "monitor", "halt")
    rec = veto.clear("ok", operator_id="human-op")
    assert rec.cleared_authenticated is False
    assert rec.cleared_by == "human-op"
    assert veto.is_vetoed is False


def test_veto_clear_nothing_active() -> None:
    veto = SovereignVeto(agent_id="z")
    with pytest.raises(ValueError, match="no active veto"):
        veto.clear("ok", operator_id="op")


def test_veto_advisory_requires_operator_id() -> None:
    veto = SovereignVeto(agent_id="z")
    veto.trigger(VetoReason.MANUAL, "m", "d")
    with pytest.raises(ValueError, match="operator_id is required"):
        veto.clear("ok")


def test_veto_production_paths() -> None:
    authz = FakeAuthorizer(
        valid_credentials={"bad": human("nope")},
        allowed_actions=set(),  # authenticates but authorizes nothing
    )
    veto = SovereignVeto(agent_id="z", authorizer=authz, mode="production")
    veto.trigger(VetoReason.MANUAL, "m", "d")
    with pytest.raises(VetoNotAuthorizedError, match="not authorized"):
        veto.clear("ok", credential="bad")
    with pytest.raises(VetoNotAuthorizedError, match="failed authentication"):
        veto.clear("ok", credential="unknown")
    with pytest.raises(VetoNotAuthorizedError, match="credential is required"):
        veto.clear("ok")


# --- P1 autonomy ladder -----------------------------------------------------


def test_ladder_production_requires_verifier() -> None:
    with pytest.raises(ValueError, match="requires an attestation verifier"):
        AutonomyLadder(mode="production")


def test_ladder_advisory_grant_is_labeled() -> None:
    ladder = AutonomyLadder()
    d = ladder.evaluate_promotion(
        requesting_agent_id="a",
        current_level=AutonomyLevel.A0_INFORMATIONAL,
        requested_level=AutonomyLevel.A1_ASSISTED,
        attestations=[
            ControlAttestation("human_approval_workflow", AutonomyLevel.A1_ASSISTED, "x", "ok")
        ],
    )
    assert d.approved is True
    assert d.verified is False
    assert any("ADVISORY" in r for r in d.reasons)


def test_ladder_production_verified_grant() -> None:
    ladder = AutonomyLadder(verifier=AcceptingVerifier(), mode="production")
    d = ladder.evaluate_promotion(
        requesting_agent_id="agent-x",
        current_level=AutonomyLevel.A0_INFORMATIONAL,
        requested_level=AutonomyLevel.A1_ASSISTED,
        attestations=[
            ControlAttestation(
                "human_approval_workflow", AutonomyLevel.A1_ASSISTED, "auditor", "ok"
            )
        ],
    )
    assert d.approved is True
    assert d.verified is True


def test_ladder_allow_skip() -> None:
    ladder = AutonomyLadder(allow_skip=True)
    atts = []
    for lvl, controls in LEVEL_REQUIRED_CONTROLS.items():
        if lvl.rank <= 3:
            atts += [ControlAttestation(c, lvl, "auditor", "ok") for c in controls]
    d = ladder.evaluate_promotion(
        requesting_agent_id="a",
        current_level=AutonomyLevel.A0_INFORMATIONAL,
        requested_level=AutonomyLevel.A3_SUPERVISED_AUTONOMOUS,
        attestations=atts,
    )
    assert d.approved is True


# --- P4 DEFCON --------------------------------------------------------------


def test_defcon_mode_validation() -> None:
    with pytest.raises(ValueError, match="mode must be"):
        DEFCONMachine(mode="bogus")
    with pytest.raises(ValueError, match="requires a wired authorizer"):
        DEFCONMachine(mode="production")


def test_defcon_escalation_levels() -> None:
    m = DEFCONMachine()
    assert m.evaluate(RiskMetrics(daily_loss=0.02)) is DEFCON.CAUTION
    assert m.evaluate(RiskMetrics(portfolio_drawdown=0.10)) is DEFCON.ALERT
    assert m.evaluate(RiskMetrics(portfolio_drawdown=0.13)) is DEFCON.DANGER


def test_defcon_manual_escalation_and_noop() -> None:
    m = DEFCONMachine()
    assert m.manual_override(DEFCON.NORMAL, "noop") is DEFCON.NORMAL  # same level
    assert m.manual_override(DEFCON.DANGER, "raise", operator_id="op") is DEFCON.DANGER


def test_defcon_advisory_deescalation_requires_operator() -> None:
    m = DEFCONMachine()
    m.evaluate(RiskMetrics(portfolio_drawdown=0.13))  # DANGER
    with pytest.raises(DEFCONTransitionError, match="operator_id required"):
        m.manual_override(DEFCON.ALERT, "down")
    assert m.manual_override(DEFCON.ALERT, "down", operator_id="op") is DEFCON.ALERT


def test_defcon_records_to_chain() -> None:
    chain = AuditChain(deployer_id="d")
    m = DEFCONMachine(audit_chain=chain)
    m.evaluate(RiskMetrics(portfolio_drawdown=0.25))
    assert any(e.event_type is AuditEventType.DEFCON_TRANSITION for e in chain.events())


def test_defcon_production_authentication_failures() -> None:
    authz = FakeAuthorizer(
        valid_credentials={"a": agent("bot")}, allowed_actions={"defcon_deescalate"}
    )
    m = DEFCONMachine(authorizer=authz, mode="production")
    m.evaluate(RiskMetrics(portfolio_drawdown=0.13))  # DANGER
    with pytest.raises(DEFCONTransitionError, match="credential is required"):
        m.manual_override(DEFCON.ALERT, "down")
    with pytest.raises(DEFCONTransitionError, match="failed authentication"):
        m.manual_override(DEFCON.ALERT, "down", credential="unknown")
    with pytest.raises(DEFCONTransitionError, match="agent principal"):
        m.manual_override(DEFCON.ALERT, "down", credential="a")


def test_defcon_production_unauthorized_action() -> None:
    authz = FakeAuthorizer(valid_credentials={"h": human("cro")}, allowed_actions=set())
    m = DEFCONMachine(authorizer=authz, mode="production")
    m.evaluate(RiskMetrics(portfolio_drawdown=0.13))
    with pytest.raises(DEFCONTransitionError, match="not authorized"):
        m.manual_override(DEFCON.ALERT, "down", credential="h")


# --- P5 effective challenge -------------------------------------------------


def test_challenge_empty_eval_set_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        EffectiveChallengeHarness(
            primary_model=lambda x: x,
            challenger_model=lambda x: x + 1,
            eval_set=[],
            independence=IndependenceAttestation("c", False, False, False),
            primary_id="P",
            challenger_id="C",
        )


def test_challenge_threshold_validation() -> None:
    with pytest.raises(ValueError, match="accept_threshold"):
        EffectiveChallengeHarness(
            primary_model=lambda x: x,
            challenger_model=lambda x: x + 1,
            eval_set=[(1, 1)],
            independence=IndependenceAttestation("c", False, False, False),
            primary_id="P",
            challenger_id="C",
            accept_threshold=0.5,
            investigate_threshold=0.3,
        )


def test_challenge_recommendation_bands_and_chain() -> None:
    chain = AuditChain(deployer_id="d")
    # Independent challenger; ~10% disagreement → investigate.
    eval_set = [(i, i) for i in range(10)]
    harness = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x if x != 0 else 999,  # disagree on 1/10
        eval_set=eval_set,
        independence=IndependenceAttestation("mrm", False, False, False),
        primary_id="P",
        challenger_id="C",
        audit_chain=chain,
    )
    report = harness.run()
    assert report.recommendation is Recommendation.INVESTIGATE
    assert 0.0 < report.disagreement_rate < 0.3
    assert any(e.event_type is AuditEventType.MODEL_VALIDATED for e in chain.events())


def test_challenge_escalate_band() -> None:
    harness = EffectiveChallengeHarness(
        primary_model=lambda x: 1,
        challenger_model=lambda x: 2,  # disagree on everything
        eval_set=[(i, 1) for i in range(10)],
        independence=IndependenceAttestation("mrm", False, False, False),
        primary_id="P",
        challenger_id="C",
    )
    assert harness.run().recommendation is Recommendation.ESCALATE
