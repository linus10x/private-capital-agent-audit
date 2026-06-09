"""Runnable worked example — the allocation-fairness (anti-cherry-picking) control.

Walks ONE Advisers Act §206 control end to end against a real enforcement
matter: SEC v. J.S. Oliver Capital Management, L.P. / Ian O. Mausner
(charged PR 2013-168; SETTLED May 16, 2019, Release 33-10639 — ~$669,965
disgorgement, neither admitting nor denying).

The five beats this script demonstrates (and prints):

  1. The decision class      — a block-trade allocation across client accounts.
  2. The agent acting        — an autonomous execution-allocation agent at A3.
  3. The envelope catching   — the AllocationFairnessMonitor flags the
     out-of-envelope case: favorable fills concentrated in the favored
     (affiliated/proprietary) accounts beyond tolerance.
  4. The audit entry         — the flag is recorded to the tamper-evident chain.
  5. The demotion            — the sovereign veto fires and DEFCON escalates,
     withdrawing the agent's authority to keep allocating.

Run it:

    python examples/worked_example_allocation_fairness.py

It uses the REAL public API only. Exit code 0 on success.
"""

from __future__ import annotations

from private_capital_agent_audit.governance import (
    DEFCON,
    AllocationFairnessMonitor,
    AuditChain,
    DEFCONMachine,
    Fill,
    RiskMetrics,
    SovereignVeto,
    VetoReason,
)
from private_capital_agent_audit.schemas.audit_event import AuditEventType


def rule(title: str) -> None:
    print(f"\n{'─' * 72}\n{title}\n{'─' * 72}")


def main() -> int:
    print("WORKED EXAMPLE — Allocation fairness (§206 anti-cherry-picking)")
    print("Enforcement backdrop: SEC v. J.S. Oliver Capital Management / Mausner")
    print("  charged PR 2013-168; SETTLED 2019-05-16 (Release 33-10639), ~$669,965")
    print("  disgorgement. The conduct: favorably-priced post-close fills steered")
    print("  to affiliated funds. Below, the control catches that exact shape.")

    # One hardened, tamper-evident ledger threads the whole episode.
    chain = AuditChain(deployer_id="acme-capital-advisers")

    # ── 1. The decision class ────────────────────────────────────────────
    rule("1. Decision class — a block trade allocated across client accounts")
    print("A single block executes, then its fills are split across accounts.")
    print("Each fill is tagged favorable/unfavorable vs the block's average")
    print("execution, and accounts are tagged favored (affiliated/proprietary)")
    print("or other (unaffiliated client). Cherry-picking = favorable fills")
    print("disproportionately routed to the favored accounts.")

    # ── 2. The agent acting ──────────────────────────────────────────────
    rule("2. The agent acting — an autonomous allocation agent at A3")
    agent_id = "allocation-agent"
    print(f"Agent {agent_id!r} proposes this allocation of the block's fills:")
    # The J.S. Oliver shape: the favored (affiliated) accounts take the good
    # fills; the unaffiliated clients are left the bad ones.
    fills = [
        Fill(account_id="affiliated-fund-A", favorable=True, is_favored=True),
        Fill(account_id="affiliated-fund-B", favorable=True, is_favored=True),
        Fill(account_id="affiliated-fund-C", favorable=True, is_favored=True),
        Fill(account_id="client-001", favorable=False, is_favored=False),
        Fill(account_id="client-002", favorable=False, is_favored=False),
        Fill(account_id="client-003", favorable=True, is_favored=False),
    ]
    for f in fills:
        tag = "favored " if f.is_favored else "client  "
        good = "FAVORABLE" if f.favorable else "unfavorable"
        print(f"    {tag} {f.account_id:<18} {good}")

    # ── 3. The envelope catching the out-of-envelope case ────────────────
    rule("3. The envelope — AllocationFairnessMonitor flags the asymmetry")
    monitor = AllocationFairnessMonitor(max_disparity=0.20, audit_chain=chain)
    assessment = monitor.assess("BLOCK-2026-0420", fills)
    print(f"    fair                    : {assessment.fair}")
    print(f"    favored favorable rate  : {assessment.favored_favorable_rate:.0%}")
    print(f"    other   favorable rate  : {assessment.other_favorable_rate:.0%}")
    print(f"    disparity               : {assessment.disparity:.0%}  (tolerance 20%)")
    for r in assessment.reasons:
        print(f"    reason                  : {r}")

    if assessment.fair:  # pragma: no cover — example must demonstrate the catch
        print("UNEXPECTED: the allocation was not flagged.")
        return 1

    # ── 4. The audit entry ───────────────────────────────────────────────
    rule("4. The audit entry — the flag is on the tamper-evident ledger")
    flag_events = [
        e for e in chain.events() if e.event_type is AuditEventType.ALLOCATION_FAIRNESS_FLAG
    ]
    print(f"    chain length            : {len(chain)} events")
    print(f"    allocation-fairness flags recorded : {len(flag_events)}")
    flag = flag_events[-1]
    print(f"    flagged block_id        : {flag.payload['block_id']}")
    print(f"    flagged disparity       : {flag.payload['disparity']:.0%}")
    print(f"    chain verifies clean    : {chain.verify()}")

    # ── 5. The demotion ──────────────────────────────────────────────────
    rule("5. Demotion — the veto fires and DEFCON escalates")
    veto = SovereignVeto(agent_id=agent_id, audit_chain=chain)
    veto.trigger(
        VetoReason.ALLOCATION_FAIRNESS,
        triggered_by="allocation-fairness-monitor",
        description=assessment.reasons[0],
    )
    print(f"    agent may keep allocating: {veto.allow_execution()}  (False = halted)")

    defcon = DEFCONMachine(audit_chain=chain)
    # A repeated fairness breach is a governance risk signal; escalate the
    # program's risk posture so it cannot quietly resume.
    level = defcon.evaluate(RiskMetrics(consecutive_losses=4))
    print(
        f"    DEFCON level            : {level.name}  "
        f"(NORMAL={DEFCON.NORMAL.value} … HALT={DEFCON.HALT.value})"
    )
    print("    An agent CANNOT clear its own veto; a human-oversight act")
    print("    (EU AI Act Art. 14) is required to restore authority, and")
    print("    de-escalation is one level at a time.")

    # The whole episode — allocation, flag, veto, escalation — is one
    # internally consistent, replayable audit trail.
    rule("Result")
    print(f"    Full audit trail: {len(chain)} events, chain.verify() = {chain.verify()}")
    print("    The control caught the J.S. Oliver allocation shape, recorded")
    print("    it immutably, and withdrew the agent's authority. That is the")
    print("    §206 control layer doing its one job.")
    assert chain.verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
