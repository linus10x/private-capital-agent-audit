# private-capital-agent-audit

**Governance patterns for autonomous AI agents at SEC-registered investment advisers.**

Reference IP for adoption — five corrected governance primitives plus seven
adviser-native controls, built to the Investment Advisers Act fiduciary regime
(§206). Zero runtime dependencies, `mypy --strict` clean, property-tested, with a
golden corpus of real SEC enforcement actions wired as executable fixtures.

> **Claim layer (read first).** This is *reference IP for adoption*, not a control
> operating in production at any firm. The five primitives are real, tested
> reference patterns; the seven adviser controls are implemented and tested
> reference controls. Nothing here is a deployed system, legal advice, or a
> substitute for qualified counsel and a qualified compliance function. See
> [`LIMITATIONS.md`](LIMITATIONS.md) and [`FAILURE-MODES.md`](FAILURE-MODES.md).

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

Built to the corrected Autonomy Ladder primitive standard (each ships with a
committed adversarial probe under [`tests/adversarial/`](tests/adversarial/) that
reproduces the exact failure the correction fixes):

| Primitive | What it guarantees |
|---|---|
| **P1 — Autonomy Ladder level gate** (`AutonomyLadder`) | Refuses promotion when a required lower-rung control is unmet; requires **independent attestation** of its inputs (no caller-asserted booleans). Advisory mode is labeled advisory; production mode fails closed without a verifier. |
| **P2 — Sovereign veto** (`SovereignVeto`) | A kill switch an agent **cannot clear for itself**; production-mode clears require an **authenticated, authorized non-agent principal** (an IdP/KMS seam), never a free-string `operator_id`. |
| **P3 — Hash-chain ledger** (`AuditChain`) | A deployer-keyed genesis event makes a hardened chain **and** a legacy chain both verify; in-place tamper is detected on replay, and **end-to-end regeneration** is caught by a witness anchor that is non-optional in production mode. |
| **P4 — DEFCON state machine** (`DEFCONMachine`) | Escalates immediately on risk; **de-escalates only** through the authorized manual-override path, **one level at a time** — a single call cannot move `HALT → NORMAL`. |
| **P5 — Effective-challenge harness** (`EffectiveChallengeHarness`) | Rejects self-challenge (`challenger == primary`); records an operator **independence attestation**. A model owner cannot self-validate to a clean `ACCEPT_PRIMARY`. |

## The seven adviser-native controls

Each is a thin, real governance layer over the primitives, recorded to the audit
chain, with a primary-sourced regulatory anchor (see
[`docs/regulatory/obligation_map.md`](docs/regulatory/obligation_map.md)):

| Control | Anchor | What it does |
|---|---|---|
| **Best execution** (`BestExecutionGate`) | §206 duty of care (IA-5248) | Gates an order's release on a *systematic* best-execution review — qualitative factors evaluated, slippage within tolerance. |
| **MNPI surveillance** (`MNPISurveillance`) | §204A; Exchange Act §10(b) / Rule 10b-5 | Restricted/watch lists + an information barrier; a restricted-name order is **blocked** and the breach recorded. |
| **Custody rule** (`CustodyRuleCheck`) | 17 CFR 275.206(4)-2 | Assesses qualified-custodian, account-statement, and surprise-exam posture, including the pooled-vehicle audit exception (120-day window). |
| **Marketing rule** (`MarketingReviewGate`) | 17 CFR 275.206(4)-1 | Gates distribution on reviewer-asserted attributes — hypothetical-performance policy present, testimonial disclosure, net-of-fees performance. |
| **Allocation fairness** (`AllocationFairnessMonitor`) | §206(1),(2),(4) | Flags cherry-picking — disproportionate favorable fills to favored or proprietary accounts. |
| **Books & records** (`BooksAndRecordsMonitor`) | 17 CFR 275.204-2 | Flags off-channel business communications on uncaptured channels, and retention exceptions against the 5-year / first-2-years-accessible rule. |
| **Valuation governance** (`ValuationGovernanceCheck`) | §206; 275.206(4)-2 audit | Flags an adviser-set mark (Level-3 / adviser-marked / manual override) lacking an independent valuation attestation, and stale marks. |

## Sub-vertical obligation map

The buyer-facing regulatory-accuracy surface (`obligation_map`), grouped by
private-capital sub-vertical. Every obligation-map citation is primary-source
verified (the golden corpus separately mixes verified matters with explicitly
`UNVERIFIED`-flagged placeholders):

| Sub-vertical | Obligations |
|---|---|
| **Buy-side / quant** | fiduciary duty · best execution · books-and-records · MNPI surveillance |
| **PE / credit GP** | fiduciary duty · allocation fairness (§206) · custody rule |
| **Private wealth / UHNW** | fiduciary duty · marketing rule · duty-of-care for advice |
| **Fund admin / valuation** | custody rule · independent valuation · books-and-records |

```bash
private-capital-audit obligations buy_side_quant
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

The suite is layered, not a handful of happy-path checks (`pytest`):

- **Unit + contract** for every primitive, control, and obligation-map entry.
- **Property-based** (`hypothesis`) — thousands of generated cases across ledger
  invariants, level-gate monotonicity, veto un-self-clearability, DEFCON
  transition algebra, challenger independence, slippage sign, and allocation
  symmetry.
- **The five AL-PROBES** ([`tests/adversarial/`](tests/adversarial/)) reproduce
  the corrected-primitive failure modes and assert each is handled.
- **A golden corpus** ([`tests/golden/`](tests/golden/)) of real, public SEC
  enforcement actions — the off-channel-communications recordkeeping wave, a
  Marketing Rule hypothetical-performance action, custody surprise-exam failures,
  an MNPI-controls matter, and cherry-picking cases — each turned into a fixture
  asserting the control would have flagged the conduct. Every fixture carries a
  primary-source URL or is marked `UNVERIFIED`.
- **Mutation** (`scripts/mutation_check.py`) over the load-bearing predicates;
  every targeted mutant is killed.
- **Coverage gate** at `--cov-fail-under=90` (a floor, not a ceiling).

## Install

```bash
pip install private-capital-agent-audit            # runtime: zero dependencies
pip install "private-capital-agent-audit[dev]"     # tests + lint + type-check
pip install "private-capital-agent-audit[test-property]"  # hypothesis
```

Requires Python 3.12+.

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
[`CITATION.cff`](CITATION.cff). A Zenodo DOI is planned for the first public
release.

Author: Kunjar Bhaduri.
