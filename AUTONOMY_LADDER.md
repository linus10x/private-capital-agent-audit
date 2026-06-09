# How this library maps to the Autonomy Ladder™

This repository is the **SEC-registered investment-adviser** member of the
Autonomy Ladder family of regulated-vertical reference libraries. The framework
and whitepaper live at **[autonomy-ladder.io](https://autonomy-ladder.io)**; the
family index is the meta-repo
**[autonomy-ladder-libraries](https://github.com/linus10x/autonomy-ladder-libraries)**.

The Autonomy Ladder is a five-rung deployment-authority model for autonomous AI
in regulated operations. **Every rung is demotable** — promotion is earned by
satisfying the controls a rung requires, and a breach (a flag, a veto, a DEFCON
escalation) drops authority back down. The rung is what an agent is allowed to
*do on its own*; the controls below are what make each rung safe.

## The five rungs

| Rung | Name | What the agent may do unsupervised | Controls the rung requires |
|---|---|---|---|
| **A0** | Informational | Nothing consequential — read / advise only | none (everything is logged) |
| **A1** | Assisted | Propose; a human approves each action | human-approval workflow |
| **A2** | Delegated | Act within a bounded envelope; humans sample-review | action envelope · sampled human review |
| **A3** | Supervised-autonomous | Act continuously under a live kill switch + immutable trail | sovereign veto · audit chain |
| **A4** | Production-autonomous | Coordinate at scale with self-escalation | orchestration guard · escalation path |

These required-control sets are enforced in code by the level gate
(`LEVEL_REQUIRED_CONTROLS` in
[`src/private_capital_agent_audit/governance/autonomy_ladder.py`](src/private_capital_agent_audit/governance/autonomy_ladder.py)):
promotion to a rung is **refused** unless its controls are independently
attested — no caller-asserted booleans.

## The five primitives → rungs

The primitives are the rung-making infrastructure. They are domain-agnostic; the
adviser controls sit on top of them.

| Primitive | Rung it makes possible | Role |
|---|---|---|
| **P1 — Autonomy Ladder level gate** (`AutonomyLadder`) | the gate between every rung | Refuses promotion when a required lower-rung control is unmet; demands independent attestation. |
| **P2 — Sovereign veto** (`SovereignVeto`) | A3+ | The non-overridable kill switch an agent cannot clear for itself; the precondition for any unsupervised action. |
| **P3 — Hash-chain ledger** (`AuditChain`) | A3+ | The tamper-evident trail that makes autonomous action auditable after the fact; witness-anchored against regeneration. |
| **P4 — DEFCON state machine** (`DEFCONMachine`) | A2+ (escalation) / A4 (self-escalation) | Immediate escalation on risk, one-step authorized de-escalation — the demotion mechanism. |
| **P5 — Effective-challenge harness** (`EffectiveChallengeHarness`) | promotion evidence | Independent validation of the model/agent before promotion; rejects self-challenge. |

## The seven adviser controls → rungs

Each adviser-native control is the §206 obligation that governs a *specific
consequential write* an agent makes. They become load-bearing the moment the
agent acts on its own — i.e. from **A2 (delegated)** upward — and every flag
they raise is a demotion trigger that drops the agent back toward A0.

| Control | §206 anchor | Gates this write | Lowest rung where it is load-bearing |
|---|---|---|---|
| **best_execution** (`BestExecutionGate`) | duty of care (IA-5248) | releasing an order | A2 |
| **mnpi_surveillance** (`MNPISurveillance`) | §204A; 10b-5 | placing a restricted-name order | A2 |
| **custody_rule** (`CustodyRuleCheck`) | 17 CFR 275.206(4)-2 | acting on client-asset custody posture | A2 |
| **marketing_rule** (`MarketingReviewGate`) | 17 CFR 275.206(4)-1 | distributing an outbound communication | A2 |
| **allocation_fairness** (`AllocationFairnessMonitor`) | §206(1),(2),(4) | allocating a block across accounts | A2 |
| **books_and_records** (`BooksAndRecordsMonitor`) | 17 CFR 275.204-2 | conducting business on a channel | A2 |
| **valuation_governance** (`ValuationGovernanceCheck`) | §206; 275.206(4)-2 audit | marking a position | A2 |

The worked example in [`WORKED_EXAMPLE.md`](WORKED_EXAMPLE.md) shows one of these
— `allocation_fairness` — running through the full A3 episode: an agent acting,
the control flagging the out-of-envelope case, the audit entry, and the
veto-driven demotion.

## Demotion in practice

A control flag is recorded to the audit chain, fires the sovereign veto
(withdrawing authority), and escalates DEFCON. Restoring authority is a
human-oversight act (EU AI Act Art. 14): an agent can never clear its own veto,
and DEFCON de-escalates one level at a time. That is the ladder's core promise —
**no invisible promotion, and every rung demotable.**

See **[autonomy-ladder.io](https://autonomy-ladder.io)** for the framework, and
the [sibling libraries](https://github.com/linus10x/autonomy-ladder-libraries)
that encode the same A0→A4 structure for banking, payments, payer, CRE, and
cross-vertical financial services.
