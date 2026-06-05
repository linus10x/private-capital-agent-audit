# Obligation map — investment advisers (Advisers Act §206 regime)

The regulatory-accuracy surface of the library, in prose. Every citation below
was verified against a primary source (sec.gov / govinfo.gov / ecfr.gov / the
U.S. Code via the Legal Information Institute)
on **2026-06-05**. The machine-readable version is
`private_capital_agent_audit.governance.obligation_map`.

> **Engineering reference, not legal or compliance advice.** This map names
> obligations and cites primary sources for engineering use; it does not
> determine which obligations apply to any particular adviser, or whether one is
> met — that is a determination only the firm's compliance function and qualified
> counsel can make. Confirm every obligation against the primary source before
> relying on it. The enforcement matters below are public records cited to show
> what conduct the controls would surface; quote the primary source for operative
> figures (some sanctions were litigated, stayed, or settled at different amounts).

## Scope

This library models the **investment-adviser fiduciary regime** under the
Investment Advisers Act of 1940: the **duty of care** and **duty of loyalty**
under **§206**, as articulated in SEC Release **IA-5248** (2019). It encodes no
other actor's standard of conduct.

## Obligations and their anchors

| Obligation | Citation | Primary source |
|---|---|---|
| Fiduciary duty (care + loyalty) | Advisers Act §206 (15 U.S.C. 80b-6); IA-5248 (2019) | https://www.sec.gov/files/rules/interp/2019/ia-5248.pdf |
| Best execution | §206 duty of care; IA-5248 (2019) | https://www.sec.gov/files/rules/interp/2019/ia-5248.pdf |
| Books-and-records retention | 17 CFR 275.204-2 | https://www.ecfr.gov/current/title-17/chapter-II/part-275/section-275.204-2 |
| MNPI policies | Advisers Act §204A (15 U.S.C. 80b-4a); Exchange Act §10(b) / Rule 10b-5 | https://www.law.cornell.edu/uscode/text/15/80b-4a |
| Allocation fairness (anti-cherry-picking) | §206(1),(2),(4) (15 U.S.C. 80b-6) | https://www.law.cornell.edu/uscode/text/15/80b-6 |
| Custody rule | 17 CFR 275.206(4)-2 | https://www.ecfr.gov/current/title-17/chapter-II/part-275/section-275.206(4)-2 |
| Marketing rule | 17 CFR 275.206(4)-1 (compliance 2022-11-04) | https://www.ecfr.gov/current/title-17/chapter-II/part-275/section-275.206(4)-1 |
| Duty of care for advice | §206 duty of care; IA-5248 (2019) | https://www.sec.gov/files/rules/interp/2019/ia-5248.pdf |
| Independent valuation | §206 duty of loyalty (IA-5248); 17 CFR 275.206(4)-2 audit interaction | https://www.sec.gov/files/rules/interp/2019/ia-5248.pdf |

## Sub-vertical mapping

| Sub-vertical | Obligations | Library control(s) |
|---|---|---|
| Buy-side / quant | fiduciary duty · best execution · books-and-records · MNPI surveillance | `BestExecutionGate`, `MNPISurveillance`, `BooksAndRecordsMonitor` |
| PE / credit GP | fiduciary duty · allocation fairness · custody rule · MNPI surveillance | `AllocationFairnessMonitor`, `CustodyRuleCheck`, `MNPISurveillance` |
| Private wealth / UHNW | fiduciary duty · marketing rule · duty of care for advice | `MarketingReviewGate` (+ duty-of-care substrate †) |
| Fund admin / valuation | custody rule · independent valuation · books-and-records | `CustodyRuleCheck`, `ValuationGovernanceCheck`, `BooksAndRecordsMonitor` |

† **Duty of care for advice** is a judgment obligation, not a structured-attribute
gate. The library does not adjudicate whether advice is in the client's best
interest — that reasonable-basis determination is the deployer's. What the
library provides is the *substrate*: the duty-of-care obligation is mapped and
named, the agent's advice decision passes the autonomy-ladder level gate, and the
sovereign veto + audit chain record the human-oversight act. The MNPI control was
added to **PE / credit GP** because a credit GP on a creditors'/lender committee
holds MNPI — the §204A exposure behind SEC v. Sound Point Capital (Release
2024-106).

## Enforcement backdrop (golden corpus)

Each control is exercised against real, public SEC matters (full list and
primary-source links in `tests/golden/corpus.py`):

- **Off-channel communications / recordkeeping** (275.204-2): the 2022 wave
  (16 firms — 15 broker-dealers and one affiliated adviser — >$1.1B, Release
  2022-174) and 2024 follow-on waves (Releases 2024-18, 2024-98, 2024-144).
- **Marketing rule** (275.206(4)-1): *Titan Global Capital Management* (Release
  2023-153) — an early action under the amended Marketing Rule, on hypothetical
  performance.
- **Custody rule** (275.206(4)-2): *Munakata Associates* (IA-6901-S, order 2025)
  — a surprise-examination failure; *Hi2 Investment Management* (IA-6691-S,
  $75,000) — Custody Rule violated on 17 occasions.
- **MNPI** (§204A): *Sound Point Capital Management* (Release 2024-106, $1.8M) —
  CLO trading while holding creditors'-committee MNPI; *Marathon Asset
  Management* (IA-6737, $1.5M) — creditors'-committee MNPI controls.
- **Cherry-picking** (§206): *J.S. Oliver Capital Management / Ian O. Mausner*
  (charged Release 2013-168; **settled May 2019, Release 33-10639, ~$669,965
  disgorgement** — the earlier litigated sanctions were stayed and superseded;
  quote the 2019 order for operative amounts) and *Michael Breton / Strategic
  Capital Management* (Release 2017-32).

One marketing-rule matter (the September 2023 nine-adviser hypothetical-
performance sweep) is included and explicitly marked `UNVERIFIED` — it names no
individual firm and a precise aggregate release could not be confirmed against a
primary source this pass; it is an honest placeholder, not a relied-upon anchor.
