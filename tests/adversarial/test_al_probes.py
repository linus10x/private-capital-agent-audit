"""The five AL-PROBES — committed adversarial reproductions of the primitive
failure modes the corrected standard fixes.

Each probe reconstructs the *exact failing construction* from the upstream
defect catalog and asserts the corrected behavior. PASS here is the load-bearing
evidence that this library was built to the corrected §2 standard, not copied
from a defective upstream:

* AL-PROBE-01 — promote-without-lower-gates → REFUSED.
* AL-PROBE-02 — veto is un-self-clearable; clear requires an authenticated
  non-agent principal.
* AL-PROBE-03 — ledger detects BOTH in-place tamper AND end-to-end regeneration.
* AL-PROBE-04 — a one-call HALT → NORMAL DEFCON transition FAILS SAFE.
* AL-PROBE-05 — self-challenge (challenger == primary) is REJECTED, and an
  un-attested-independence challenge cannot reach ACCEPT_PRIMARY.
"""

from __future__ import annotations

import pytest

from private_capital_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
    InMemoryWitnessRegister,
)
from private_capital_agent_audit.governance.autonomy_ladder import (
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
    AuditEventType,
    AutonomyLevel,
)
from tests.conftest import FakeAuthorizer, agent, human

pytestmark = pytest.mark.adversarial


def test_al_probe_01_promote_without_lower_gates_refused() -> None:
    """AL-PROBE-01: an agent at A2 cannot reach A3 with no controls attested."""
    ladder = AutonomyLadder(mode="advisory")
    decision = ladder.evaluate_promotion(
        requesting_agent_id="rogue-agent",
        current_level=AutonomyLevel.A2_DELEGATED,
        requested_level=AutonomyLevel.A3_SUPERVISED_AUTONOMOUS,
        attestations=[],  # the failing construction: promote with nothing attested
    )
    assert decision.approved is False
    assert decision.granted_level is AutonomyLevel.A2_DELEGATED
    assert any("missing required controls" in r for r in decision.reasons)
    # And the controls A3 requires must be named as missing.
    assert "sovereign_veto" in decision.missing_controls
    assert "audit_chain" in decision.missing_controls


def test_al_probe_01b_caller_asserted_booleans_are_not_trusted() -> None:
    """AL-PROBE-01 (independence): in production mode an attestation that fails
    the independent-verification check is treated as missing — the gate does not
    trust a caller-supplied attestation just because it exists."""
    from tests.conftest import RejectingVerifier

    ladder = AutonomyLadder(verifier=RejectingVerifier(), mode="production")
    atts = [
        ControlAttestation("human_approval_workflow", AutonomyLevel.A1_ASSISTED, "x", "ok"),
    ]
    decision = ladder.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=AutonomyLevel.A0_INFORMATIONAL,
        requested_level=AutonomyLevel.A1_ASSISTED,
        attestations=atts,
    )
    assert decision.approved is False
    assert "human_approval_workflow" in decision.unverified_controls


def test_al_probe_02_veto_un_self_clearable_and_authenticated() -> None:
    """AL-PROBE-02: an agent cannot clear its own veto, and production-mode clear
    requires an authenticated non-agent principal."""
    # Advisory mode: the self-clear attempt (operator_id == agent_id) is rejected.
    veto_adv = SovereignVeto(agent_id="zeus")
    veto_adv.trigger(VetoReason.RISK_LIMIT_BREACH, "risk-monitor", "drawdown breach")
    with pytest.raises(VetoNotAuthorizedError):
        veto_adv.clear("self-serving clear", operator_id="zeus")
    assert veto_adv.is_vetoed  # still vetoed

    # Production mode: an agent principal credential is rejected; a human clears.
    authz = FakeAuthorizer(
        valid_credentials={"agent-cred": agent("zeus"), "human-cred": human("cco")},
    )
    veto = SovereignVeto(agent_id="zeus", authorizer=authz, mode="production")
    veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk-monitor", "drawdown breach")
    with pytest.raises(VetoNotAuthorizedError):
        veto.clear("agent self-clear", credential="agent-cred")
    assert veto.is_vetoed
    record = veto.clear("reviewed and accepted", credential="human-cred")
    assert record.cleared_by == "cco"
    assert record.cleared_authenticated is True
    assert veto.is_vetoed is False


def test_al_probe_03_ledger_detects_inplace_tamper_and_regeneration() -> None:
    """AL-PROBE-03: in-place mutation breaks verify; end-to-end regeneration is
    caught by the external witness anchor."""
    witness = InMemoryWitnessRegister()
    chain = AuditChain(deployer_id="acme-capital", witness_register=witness, mode="production")
    for i in range(5):
        chain.append(
            AuditEventType.AGENT_ACTION,
            AutonomyLevel.A2_DELEGATED,
            agent_id="trader",
            payload={"order": i},
        )
    chain.anchor_to_witness()
    assert chain.verify() is True
    assert chain.verify_regeneration_resistant() is True

    # (a) In-place tamper: rewrite a stored event's payload.
    tampered = chain.events()[2]
    object.__setattr__(tampered, "payload", {"order": 999})
    assert chain.verify() is False
    with pytest.raises(AuditChainTamperError):
        chain.verify_strict()

    # (b) End-to-end regeneration: rebuild a fresh, internally-consistent chain.
    #     It passes verify() (internal consistency) but the witness still holds
    #     the original anchored head, which the regenerated chain lacks.
    regen = AuditChain(deployer_id="acme-capital", witness_register=witness, mode="production")
    for i in range(5):
        regen.append(
            AuditEventType.AGENT_ACTION,
            AutonomyLevel.A2_DELEGATED,
            agent_id="trader",
            payload={"order": i},
        )
    assert regen.verify() is True  # internally consistent…
    assert regen.verify_regeneration_resistant() is False  # …but missing the anchored head


def test_al_probe_03b_hardened_and_legacy_chains_both_verify() -> None:
    """AL-PROBE-03b: the corrected verifier branches the genesis seed — a clean
    hardened chain does NOT raise a false TAMPER, and a legacy chain still
    verifies."""
    hardened = AuditChain(deployer_id="acme-capital")
    hardened.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A0_INFORMATIONAL, "a", {"x": 1})
    assert hardened.is_hardened is True
    assert hardened.verify() is True  # the upstream defect raised here

    legacy = AuditChain()  # deployer_id=None
    legacy.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A0_INFORMATIONAL, "a", {"x": 1})
    assert legacy.is_hardened is False
    assert legacy.verify() is True


def test_al_probe_04_one_call_halt_to_normal_fails_safe() -> None:
    """AL-PROBE-04: a single call cannot move HALT → NORMAL."""
    machine = DEFCONMachine()
    machine.evaluate(RiskMetrics(portfolio_drawdown=0.25))  # auto-escalate to HALT
    assert machine.current_level() is DEFCON.HALT

    with pytest.raises(DEFCONTransitionError):
        machine.manual_override(DEFCON.NORMAL, "rush back to normal", operator_id="op")
    assert machine.current_level() is DEFCON.HALT  # still halted

    # Even evaluate() with calm metrics must not auto-de-escalate.
    assert machine.evaluate(RiskMetrics()) is DEFCON.HALT


def test_al_probe_04b_production_deescalation_requires_authorized_human() -> None:
    """AL-PROBE-04: in production mode, de-escalation requires an authenticated,
    authorized, non-agent principal — one step at a time."""
    authz = FakeAuthorizer(
        valid_credentials={"human": human("cro"), "bot": agent("bot")},
        allowed_actions={DEFCONMachine.DEESCALATE_ACTION},
    )
    machine = DEFCONMachine(authorizer=authz, mode="production")
    machine.evaluate(RiskMetrics(portfolio_drawdown=0.25))
    assert machine.current_level() is DEFCON.HALT

    # An agent principal may not de-escalate.
    with pytest.raises(DEFCONTransitionError):
        machine.manual_override(DEFCON.DANGER, "step down", credential="bot")
    # A human steps down one level at a time.
    assert machine.manual_override(DEFCON.DANGER, "reviewed", credential="human") is DEFCON.DANGER


def test_al_probe_05_self_challenge_rejected() -> None:
    """AL-PROBE-05: challenger == primary is rejected, and un-attested
    independence can never reach ACCEPT_PRIMARY."""
    model = lambda x: x  # noqa: E731 - terse stand-in model

    # (a) Same identity is rejected at construction.
    with pytest.raises(ValueError, match="self-challenge"):
        EffectiveChallengeHarness(
            primary_model=model,
            challenger_model=lambda x: x,
            eval_set=[(1, 1)],
            independence=IndependenceAttestation("mrm", False, False, False),
            primary_id="model-A",
            challenger_id="model-A",
        )

    # (b) Same callable object is rejected.
    with pytest.raises(ValueError, match="same callable"):
        EffectiveChallengeHarness(
            primary_model=model,
            challenger_model=model,
            eval_set=[(1, 1)],
            independence=IndependenceAttestation("mrm", False, False, False),
            primary_id="model-A",
            challenger_id="model-B",
        )

    # (c) A distinct-but-non-independent challenger (same vendor family) that
    #     agrees perfectly STILL cannot reach ACCEPT_PRIMARY.
    harness = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x,  # perfect agreement → disagreement_rate 0
        eval_set=[(i, i) for i in range(20)],
        independence=IndependenceAttestation(
            "owner", same_owner=True, same_vendor_family=True, same_prompt_template=True
        ),
        primary_id="model-A",
        challenger_id="model-A-twin",
    )
    report = harness.run()
    assert report.disagreement_rate == 0.0
    assert report.independent is False
    assert report.recommendation is Recommendation.ESCALATE  # NOT accept_primary
