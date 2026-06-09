# private-capital-agent-audit

**The Advisers Act §206 control layer that makes an AI agent's orders, marketing, and valuation marks auditable.**

[![CI](https://github.com/linus10x/private-capital-agent-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/linus10x/private-capital-agent-audit/actions/workflows/ci.yml)
[![coverage](https://img.shields.io/badge/coverage-98.7%25-brightgreen)](#proof-on-real-enforcement)
[![tests](https://img.shields.io/badge/tests-181%20passing-brightgreen)](#test-strategy)
[![license](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue)](LICENSE-MIT)
[![python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![DOI](https://zenodo.org/badge/1260855848.svg)](https://doi.org/10.5281/zenodo.20564496)
[![Autonomy Ladder family](https://img.shields.io/badge/Autonomy%20Ladder-family-1f3a5f)](https://github.com/linus10x/autonomy-ladder-libraries)

> **Claim layer (read first).** This is *reference IP for adoption*, not a control
> operating in production at any firm. The five primitives are real, tested
> reference patterns; the seven adviser controls are implemented and tested
> reference controls. Nothing here is a deployed system, legal advice, or a
> substitute for qualified counsel and a qualified compliance function.
>
> **What this is:** the §206 control layer that makes an AI agent's orders,
> marketing, and valuation marks auditable — five corrected governance primitives
> plus seven adviser-native controls, every flag recorded to a tamper-evident
> ledger, every regulatory anchor primary-sourced.
> **What this is not:** a deployed compliance system, legal advice, or a
> substitute for counsel and a compliance function. See
> [`LIMITATIONS.md`](LIMITATIONS.md) and [`FAILURE-MODES.md`](FAILURE-MODES.md).
> **Who this is for:** an RIA / allocator compliance lead, or a buy-side-AI lead,
> wiring governance under an autonomous agent that places orders, sends marketing,
> or marks positions.

## 30-second tour

If your firm is letting an AI agent place orders, send marketing, or mark
positions, this is the **Advisers Act §206 control layer** that makes those
actions auditable. The consequential write an adviser's autonomous agent makes
is an **order, an allocation, or an outbound communication** — and each one is
governed here by a control with a primary-sourced anchor, recorded to a
tamper-evident ledger, demotable on breach.

`181 tests · 98.7% coverage (≥90% gate) · 18/18 mutation kill · golden corpus of 12 real SEC enforcement matters · zero runtime deps · mypy --strict`

- **5 corrected primitives** — level gate · sovereign veto · hash-chain ledger · DEFCON · effective-challenge harness.
- **7 adviser-native controls** — best execution · MNPI surveillance · custody rule · marketing rule · allocation fairness · books-and-records · valuation governance.
- **Proven on real enforcement** — each control catches the exact conduct a public SEC matter penalized (see [Proof on real enforcement](#proof-on-real-enforcement)).
- **Part of the [Autonomy Ladder™ family](#part-of-the-autonomy-ladder-family)** — one A0→A4 governance model across six regulated verticals.

## Read me first

1. **See a control fire** — run the golden-corpus suite (`pytest tests/golden/ -v`),
   where each control is fed the failing construction a real SEC matter describes
   and must flag it; or any control test under [`tests/`](tests/).
2. **Walk one control end to end** — [`WORKED_EXAMPLE.md`](WORKED_EXAMPLE.md)
   takes the allocation-fairness (anti-cherry-picking) control through the J.S.
   Oliver enforcement shape: the decision class, the agent acting, the envelope
   catching the out-of-envelope case, the audit entry, and the demotion. The
   script ([`examples/worked_example_allocation_fairness.py`](examples/worked_example_allocation_fairness.py))
   runs end to end.
3. **Understand the framework** — [autonomy-ladder.io](https://autonomy-ladder.io)
   for the A0→A4 model, and [`AUTONOMY_LADDER.md`](AUTONOMY_LADDER.md) for how the
   five primitives and seven controls map to the rungs.

## Why this exists for frontier autonomy stacks

The controls in this library are **domain-agnostic**. The DEFCON state machine, the non-overridable **sovereign veto** (a separate-process control the agent cannot switch off), the **hash-chain audit ledger** (it detects tampering within its trust boundary), the **hard envelopes with mechanical escalation**, the **sampled-review tripwires**, and **monitor-led promotion** were forged in real multi-agent production systems under consequence — and they apply directly to any high-stakes coordinated autonomy (vehicles, robots, agent swarms) where *invisible promotion* or *cascade failure* is unacceptable. The decision class is a parameter: this repo encodes it for **SEC-registered investment advisers (Advisers Act §206)**, but the same A0→A4 deployment-authority structure lifts into any decision class without inheriting financial-services assumptions.

- **Framework + whitepaper:** [autonomy-ladder.io](https://autonomy-ladder.io)
- **Non-financial demo (under 60s):** [`finserv-agent-audit/examples/agent_coordination`](https://github.com/linus10x/finserv-agent-audit/tree/main/examples/agent_coordination) — the same veto / envelope / audit-chain / demotion primitives on a generic agent swarm.

> **For reviewers & safety teams:** every control here is falsifiable — the test suite (181 tests · 98.7% coverage · 18/18 mutation kill) turns each rule into a runnable check, and the veto and ledger are infrastructure with operational properties (separate process boundary, distinct credentials, a gate the agent cannot reach; write-once retention). These are reference implementations for adoption, not deployed production controls.


## Part of the Autonomy Ladder™ family

Six co-equal regulated-vertical reference libraries implementing the **Autonomy
Ladder** — a governance framework for autonomous AI in regulated operations
(A0→A4, every rung demotable). **Family index:
[autonomy-ladder-libraries](https://github.com/linus10x/autonomy-ladder-libraries) ·
framework + whitepaper: [autonomy-ladder.io](https://autonomy-ladder.io).**

| Vertical | Library |
|---|---|
| Cross-vertical financial services | [`finserv-agent-audit`](https://github.com/linus10x/finserv-agent-audit) |
| Banking (model risk · ECOA/Reg B · BSA/AML/OFAC) | [`banking-agent-audit`](https://github.com/linus10x/banking-agent-audit) |
| Payments (OFAC · Reg E · rail finality) | [`payments-agent-audit`](https://github.com/linus10x/payments-agent-audit) |
| Health-insurance payer (UM · prior auth · appeals) | [`payer-agent-audit`](https://github.com/linus10x/payer-agent-audit) |
| SEC-registered investment advisers (Advisers Act §206) | **[`private-capital-agent-audit`](https://github.com/linus10x/private-capital-agent-audit)** |
| Commercial real estate | [`cre-agent-audit`](https://github.com/linus10x/cre-agent-audit) |

## Scope: investment advisers, not intermediaries

This library models the **investment-adviser fiduciary regime** under the
Investment Advisers Act of 1940 — the **duty of care** and **duty of loyalty**
under **§206**, as articulated in SEC Release **IA-5248** (2019). It encodes no
other actor's standard of conduct. The consequential write an adviser's
autonomous agent makes is an **order, an allocation, or an outbound
communication** — governed by best execution, surveillance, allocation fairness,
marketing review, custody discipline, and recordkeeping, all anchored in the
Advisers Act and its rules.

## The five corrected primitives

Built to the corrected Autonomy Ladder primitive standard — **"corrected" means
each primitive was re-derived to close the specific failure its committed
adversarial probe reproduces** (the probes live under
[`tests/adversarial/`](tests/adversarial/)):

| Primitive | What it enforces (in code) |
|---|---|
| **P1 — Autonomy Ladder level gate** (`AutonomyLadder`) | Refuses promotion when a required lower-rung control is unmet; requires **independent attestation** of its inputs (no caller-asserted booleans). Advisory mode is labeled advisory; production mode fails closed without a verifier. |
| **P2 — Sovereign veto** (`SovereignVeto`) | A kill switch an agent **cannot clear for itself**; production-mode clears require an **authenticated, authorized non-agent principal** (an IdP/KMS seam), never a free-string `operator_id`. |
| **P3 — Hash-chain ledger** (`AuditChain`) | A deployer-keyed genesis event makes a hardened chain **and** a legacy chain both verify; in-place tamper of any event **with a successor** is detected on replay, and regeneration **or** truncation below a witness checkpoint is caught by a witness anchor that is non-optional in production mode. The unwitnessed tail (events after the last anchor) shares the truncation residual — anchor to commit the head (`head_is_witnessed()`); see [`FAILURE-MODES.md`](FAILURE-MODES.md). |
| **P4 — DEFCON state machine** (`DEFCONMachine`) | Escalates immediately on risk; **de-escalates only** through the authorized manual-override path, **one level at a time** — a single call cannot move `HALT → NORMAL`. |
| **P5 — Effective-challenge harness** (`EffectiveChallengeHarness`) | Rejects self-challenge (`challenger == primary`); records an operator **independence attestation**. A model owner cannot self-validate to a clean `ACCEPT_PRIMARY`. |

## The seven adviser-native controls

Each is a thin governance layer over the primitives, recorded to the audit chain,
with a primary-sourced regulatory anchor (see
[`docs/regulatory/obligation_map.md`](docs/regulatory/obligation_map.md)):

| Control | Anchor | What it does |
|---|---|---|
| **Best execution** (`BestExecutionGate`) | §206 duty of care (IA-5248) | Gates an order's release on a *systematic* best-execution review — qualitative factors evaluated, slippage within tolerance. |
| **MNPI surveillance** (`MNPISurveillance`) | §204A; Exchange Act §10(b) / Rule 10b-5 | Restricted/watch lists + an information barrier; a restricted-name order screens **BLOCKED** and the breach is recorded (wiring that to the sovereign veto to stop the order is the deployer's integration). |
| **Custody rule** (`CustodyRuleCheck`) | 17 CFR 275.206(4)-2 | Assesses qualified-custodian, account-statement, and surprise-exam posture, including the pooled-vehicle audit exception (120-day window; 180 days for a fund of funds). |
| **Marketing rule** (`MarketingReviewGate`) | 17 CFR 275.206(4)-1 | Gates distribution on reviewer-asserted attributes — the three hypothetical-performance conditions, testimonial disclosure, and gross-vs-net at equal prominence. |
| **Allocation fairness** (`AllocationFairnessMonitor`) | §206(1),(2),(4) | Flags cherry-picking — disproportionate favorable fills to favored or proprietary accounts. |
| **Books & records** (`BooksAndRecordsMonitor`) | 17 CFR 275.204-2 | Flags off-channel business communications on uncaptured channels, and retention exceptions against the 5-year / first-2-years-accessible rule. |
| **Valuation governance** (`ValuationGovernanceCheck`) | §206; 275.206(4)-2 audit | Flags an adviser-set mark (Level-3 / adviser-marked / manual override) lacking an independent valuation attestation, and stale marks. |

> **What these controls are.** Each control acts on **deployer-asserted,
> structured inputs** (curated lists, execution factors, arrangement attributes,
> ad attributes, fills, communications) and records and surfaces consequences. A
> control **does not independently observe** your order flow, communications, or
> books, and a flag is a review signal, not an adjudication. Wiring these in does
> **not** make a firm compliant — the compliance function owns the judgment. See
> [`LIMITATIONS.md`](LIMITATIONS.md).

## Sub-vertical obligation map

The buyer-facing regulatory-accuracy surface (`obligation_map`), grouped by
private-capital sub-vertical. Every obligation-map citation is primary-source
verified.

| Sub-vertical | Obligations |
|---|---|
| **Buy-side / quant** | fiduciary duty · best execution · books-and-records · MNPI surveillance |
| **PE / credit GP** | fiduciary duty · allocation fairness (§206) · custody rule · MNPI surveillance |
| **Private wealth / UHNW** | fiduciary duty · marketing rule · duty-of-care for advice † |
| **Fund admin / valuation** | custody rule · independent valuation · books-and-records |

† Duty-of-care for advice is a **judgment obligation**, not a structured-attribute
gate — it has no dedicated automated control. The library names and maps it, and
the autonomy-ladder gate + sovereign veto + audit chain provide the human-
oversight substrate; the reasonable-basis determination is the deployer's. The
map names obligations that controls cover **plus** judgment obligations the
deployer owns.

```bash
private-capital-audit obligations buy_side_quant
```

## Proof on real enforcement

The credibility tier. The golden corpus
([`tests/golden/`](tests/golden/)) holds **12 real, public SEC enforcement
matters** — and for each enforcement theme, the relevant control is fed the
failing construction the matter describes and **must flag it**. The library does
not merely cite the law; it catches the exact conduct the SEC penalized.

| Theme | Matters in the corpus |
|---|---|
| **Cherry-picking / allocation fairness** | **J.S. Oliver Capital Management / Ian O. Mausner** — settled May 16, 2019 (Release 33-10639), ~$669,965 disgorgement (the operative settled figure; the stayed 2016 litigated figures are *not* quoted); Breton / Strategic Capital Management (2017). |
| **MNPI controls (§204A)** | **Sound Point Capital Management** (PR 2024-106, $1.8M) — the SEC found **no evidence of trading on MNPI**; the charge was the §204A controls failure on CLO/creditor-committee information; Marathon Asset Management (2024). |
| **Off-channel recordkeeping (275.204-2)** | The **$1.1B+ off-channel-communications wave** (PR 2022-174, firms admitted facts) plus the 2024 follow-on waves. |
| **Marketing rule (275.206(4)-1)** | **Titan Global Capital Management** (PR 2023-153) — hypothetical-performance without the required policies; plus the nine-adviser sweep (2023). |
| **Custody rule (275.206(4)-2)** | Surprise-exam / audited-statement failures (Munakata, Hi2). |

All 12 matters are currently primary-source verified; the schema supports an
`UNVERIFIED` flag for future additions, but the shipped corpus contains no
unverified entries.

Each matter is a parametrized fixture that asserts both the obligation mapping
and the behavioral catch:

```console
$ pytest tests/golden/ -v
tests/golden/test_golden_corpus.py::test_matter_maps_to_known_obligation[offchannel_2022_174] PASSED
tests/golden/test_golden_corpus.py::test_matter_maps_to_known_obligation[marketing_titan_2023_153] PASSED
tests/golden/test_golden_corpus.py::test_matter_maps_to_known_obligation[mnpi_soundpoint_2024_106] PASSED
tests/golden/test_golden_corpus.py::test_matter_maps_to_known_obligation[alloc_js_oliver_2013_168] PASSED
...
tests/golden/test_golden_corpus.py::test_corpus_has_each_theme PASSED
19 passed
```

## Quickstart

```python
from private_capital_agent_audit.governance import (
    AuditChain, SovereignVeto, VetoReason,
    BestExecutionGate, ExecutionFactors, Side,
)

# A hardened, witness-anchored ledger in production mode (fails closed without one).
chain = AuditChain(deployer_id="acme-capital")

# A best-execution review gates an autonomous order before it lands.
gate = BestExecutionGate(audit_chain=chain)
review = gate.review_order(
    "ORD-1",
    ExecutionFactors(
        venue="ATS-1", side=Side.BUY, fill_price=100.02, benchmark_price=100.00,
        commission=0.01, factors_considered=("price", "venue_quality", "speed"),
    ),
)
if not review.approved:
    veto = SovereignVeto(agent_id="execution-agent", audit_chain=chain)
    veto.trigger(VetoReason.BEST_EXECUTION_CONCERN, "best-ex-gate", review.reasons[0])

assert chain.verify()  # the ledger is internally consistent
```

## Test strategy

The suite is layered, not a handful of happy-path checks — **181 tests, 98.7%
coverage** (CI gate at `--cov-fail-under=90`) (`pytest`):

- **Unit + contract** for every primitive, control, and obligation-map entry.
- **Property-based** (`hypothesis`) — thousands of generated cases across ledger
  invariants, level-gate monotonicity, veto un-self-clearability, DEFCON
  transition algebra, challenger independence, slippage sign, and allocation
  symmetry.
- **Eight AL-PROBES** ([`tests/adversarial/`](tests/adversarial/)) reproduce the
  corrected-primitive failure modes and assert each is handled.
- **A golden corpus** ([`tests/golden/`](tests/golden/)) of 12 real, public SEC
  enforcement matters — see [Proof on real enforcement](#proof-on-real-enforcement).
- **Mutation** (`scripts/mutation_check.py`) over the load-bearing predicates;
  every targeted mutant is killed (**18/18, 100%**).

## Install

Install from the GitHub release (zero runtime dependencies):

```bash
pip install "git+https://github.com/linus10x/private-capital-agent-audit@v0.1.3"
# with the dev / property-test extras:
pip install "private_capital_agent_audit[dev,test-property] @ git+https://github.com/linus10x/private-capital-agent-audit@v0.1.3"
```

Requires Python 3.12+. A PyPI distribution (`pip install private-capital-agent-audit`)
is planned for a later release.

## Regulatory anchors (primary-sourced, verified 2026-06-05)

- Advisers Act **§206** — 15 U.S.C. 80b-6 · the fiduciary anti-fraud basis.
- SEC Release **IA-5248** (2019) — the adviser duty of care + duty of loyalty.
- Custody rule — **17 CFR 275.206(4)-2**.
- Marketing rule — **17 CFR 275.206(4)-1** (compliance date 2022-11-04).
- Books-and-records — **17 CFR 275.204-2**.
- MNPI policies — Advisers Act **§204A** (15 U.S.C. 80b-4a); Exchange Act §10(b) /
  Rule 10b-5.

These characterizations are summaries for engineering reference, not legal
advice. Confirm every obligation against the primary source and qualified
counsel before relying on it.

## License & citation

Dual-licensed **MIT OR Apache-2.0** ([`LICENSE-MIT`](LICENSE-MIT) /
[`LICENSE-APACHE`](LICENSE-APACHE)). If you use this work, please cite it — see
[`CITATION.cff`](CITATION.cff). Archived on Zenodo — concept DOI
[10.5281/zenodo.20564496](https://doi.org/10.5281/zenodo.20564496) (resolves to
the latest version).

Author: Kunjar Bhaduri.

## The Autonomy Ladder™ family

Part of a family of regulated-vertical reference libraries implementing one
A0→A4 governance model. Family index:
[**autonomy-ladder-libraries**](https://github.com/linus10x/autonomy-ladder-libraries) ·
framework + whitepaper: [**autonomy-ladder.io**](https://autonomy-ladder.io).

- [`finserv-agent-audit`](https://github.com/linus10x/finserv-agent-audit) — cross-vertical financial services
- [`banking-agent-audit`](https://github.com/linus10x/banking-agent-audit) — banking (model risk · ECOA/Reg B · BSA/AML/OFAC)
- [`payments-agent-audit`](https://github.com/linus10x/payments-agent-audit) — payments (OFAC · Reg E · rail finality)
- [`payer-agent-audit`](https://github.com/linus10x/payer-agent-audit) — health-insurance payer (UM · prior auth · appeals)
- **`private-capital-agent-audit`** — SEC-registered investment advisers (Advisers Act §206) — *this repo*
- [`cre-agent-audit`](https://github.com/linus10x/cre-agent-audit) — commercial real estate
