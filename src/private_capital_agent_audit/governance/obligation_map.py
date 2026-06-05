"""Sub-vertical → obligation map for SEC-registered investment advisers.

This is the buyer-facing **regulatory-accuracy surface** of the library. Each
:class:`Obligation` carries an exact statutory/CFR citation and a primary-source
URL, verified against the primary source (sec.gov / govinfo.gov / ecfr.gov /
the U.S. Code) on **2026-06-05**. Obligations not confirmable against a primary
source are marked ``verified=False`` and named ``UNVERIFIED`` in the summary.

**Load-bearing scope statement.** This library governs **investment advisers**
under the Investment Advisers Act of 1940. Advisers owe a **fiduciary duty**
(duty of care + duty of loyalty) under **§206**, as articulated in SEC Release
**IA-5248** (2019). Every obligation below is grounded in the Advisers Act / its
rules; the library models only the investment-adviser fiduciary regime and
encodes no other actor's standard of conduct.

Sub-vertical obligation map (per the build brief):

* **buy-side / quant** — fiduciary duty + best execution + books-and-records +
  MNPI / market-abuse surveillance. The consequential write is an *order /
  position*, governed by best-ex + surveillance, not a retail-client record.
* **PE / credit GP** — fiduciary duty + §206 conflicts & allocation fairness +
  the custody rule.
* **private wealth / UHNW** — fiduciary duty + the marketing rule + the
  duty-of-care obligation to provide advice in the client's best interest
  (the adviser's own duty-of-care standard for advice).
* **fund admin / valuation** — the custody rule + independent valuation +
  books-and-records.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Engineering reference, not legal/compliance advice. This map names obligations
# and cites primary sources for engineering use; it does not determine which
# obligations apply to any particular adviser or whether one is met. That is a
# determination only the firm's compliance function and qualified counsel can
# make. Confirm every obligation against the primary source before relying on it.
DISCLAIMER = (
    "Engineering reference, not legal/compliance advice; the deployer's "
    "compliance function and counsel own the determination."
)


class SubVertical(Enum):
    """The four private-capital sub-verticals this library maps obligations for."""

    BUY_SIDE_QUANT = "buy_side_quant"
    PE_CREDIT_GP = "pe_credit_gp"
    PRIVATE_WEALTH_UHNW = "private_wealth_uhnw"
    FUND_ADMIN_VALUATION = "fund_admin_valuation"


@dataclass(frozen=True)
class Obligation:
    """A single regulatory obligation with a primary-sourced citation."""

    obligation_id: str
    title: str
    citation: str
    primary_source_url: str
    verified: bool
    summary: str


# --- Obligation registry (citations verified 2026-06-05) --------------------

FIDUCIARY_DUTY = Obligation(
    obligation_id="fiduciary_duty",
    title="Adviser fiduciary duty (duty of care + duty of loyalty)",
    citation="Advisers Act §206 (15 U.S.C. 80b-6); SEC Release IA-5248 (2019)",
    primary_source_url="https://www.sec.gov/files/rules/interp/2019/ia-5248.pdf",
    verified=True,
    summary=(
        "The overarching fiduciary duty an adviser owes its clients — duty of "
        "care and duty of loyalty — grounded in the §206 anti-fraud provisions "
        "and articulated in the SEC's 2019 Commission Interpretation (IA-5248)."
    ),
)

BEST_EXECUTION = Obligation(
    obligation_id="best_execution",
    title="Duty to seek best execution",
    citation="Advisers Act §206 fiduciary duty of care; SEC Release IA-5248 (2019)",
    primary_source_url="https://www.sec.gov/files/rules/interp/2019/ia-5248.pdf",
    verified=True,
    summary=(
        "Where an adviser has responsibility to select brokers and execute "
        "trades, the duty of care requires seeking best execution — periodic and "
        "systematic evaluation of execution quality (qualitative, not lowest "
        "commission alone)."
    ),
)

BOOKS_AND_RECORDS = Obligation(
    obligation_id="books_and_records",
    title="Books-and-records retention",
    citation="17 CFR 275.204-2",
    primary_source_url="https://www.ecfr.gov/current/title-17/chapter-II/part-275/section-275.204-2",
    verified=True,
    summary=(
        "Required books and records (including advertisements and "
        "communications) must be retained at least 5 years from the end of the "
        "fiscal year of last entry, the first 2 years in an appropriate office "
        "of the adviser and readily accessible."
    ),
)

MNPI_SURVEILLANCE = Obligation(
    obligation_id="mnpi_surveillance",
    title="Policies to prevent misuse of material nonpublic information",
    citation=(
        "Advisers Act §204A (15 U.S.C. 80b-4a); Exchange Act §10(b) & Rule 10b-5 (17 CFR 240.10b-5)"
    ),
    primary_source_url="https://www.law.cornell.edu/uscode/text/15/80b-4a",
    verified=True,
    summary=(
        "Every adviser subject to §204 (registered advisers and exempt reporting "
        "advisers) must establish, maintain, and enforce written policies "
        "reasonably designed to prevent the misuse of MNPI; insider-trading "
        "liability anchors in Exchange Act §10(b) and Rule 10b-5."
    ),
)

ALLOCATION_FAIRNESS = Obligation(
    obligation_id="allocation_fairness",
    title="Cross-client allocation fairness (anti-cherry-picking)",
    citation="Advisers Act §206(1),(2),(4) (15 U.S.C. 80b-6)",
    primary_source_url="https://www.law.cornell.edu/uscode/text/15/80b-6",
    verified=True,
    summary=(
        "Disproportionately allocating favorably-priced trades to favored or "
        "proprietary accounts (cherry-picking) is conduct the SEC has charged as "
        "fraud under §206. Allocation must be fair and consistent with disclosed "
        "policy."
    ),
)

CUSTODY_RULE = Obligation(
    obligation_id="custody_rule",
    title="Custody of client funds and securities",
    citation="17 CFR 275.206(4)-2",
    primary_source_url="https://www.ecfr.gov/current/title-17/chapter-II/part-275/section-275.206(4)-2",
    verified=True,
    summary=(
        "An adviser with custody must use a qualified custodian, ensure clients "
        "receive account statements, and obtain an annual surprise examination — "
        "unless the pooled-vehicle (private-fund) audit exception applies (annual "
        "GAAP audit + audited financials to investors within 120 days; 180 days "
        "for a fund of funds, per SEC staff guidance — not rule text)."
    ),
)

MARKETING_RULE = Obligation(
    obligation_id="marketing_rule",
    title="Investment-adviser marketing",
    citation="17 CFR 275.206(4)-1 (compliance date 2022-11-04)",
    primary_source_url="https://www.ecfr.gov/current/title-17/chapter-II/part-275/section-275.206(4)-1",
    verified=True,
    summary=(
        "Governs testimonials/endorsements, performance advertising, and "
        "hypothetical performance (which requires policies ensuring relevance to "
        "the audience plus sufficient information to evaluate it). Advertisements "
        "are also retained records under 275.204-2."
    ),
)

DUTY_OF_CARE_ADVICE = Obligation(
    obligation_id="duty_of_care_advice",
    title="Reasonable basis to believe advice is in the client's best interest",
    citation="Advisers Act §206 duty of care; SEC Release IA-5248 (2019)",
    primary_source_url="https://www.sec.gov/files/rules/interp/2019/ia-5248.pdf",
    verified=True,
    summary=(
        "The adviser's duty of care requires a reasonable basis to believe advice "
        "is in the client's best interest given the client's objectives. This is "
        "the adviser's own duty-of-care standard for the advice it provides under "
        "§206 — grounded in the fiduciary duty, not in any other regime."
    ),
)

INDEPENDENT_VALUATION = Obligation(
    obligation_id="independent_valuation",
    title="Independent valuation of fund assets",
    citation="Advisers Act §206 duty of loyalty (IA-5248); 17 CFR 275.206(4)-2 audit interaction",
    primary_source_url="https://www.sec.gov/files/rules/interp/2019/ia-5248.pdf",
    verified=True,
    summary=(
        "Valuation of fund assets implicates the §206 duty of loyalty (a conflict "
        "where the adviser's fee depends on its own marks) and interacts with the "
        "custody-rule audit exception. Independent valuation is the control that "
        "addresses the conflict; the obligation is conduct-based (grounded in the "
        "§206 fiduciary duty), not a single numbered valuation rule."
    ),
)


ALL_OBLIGATIONS: dict[str, Obligation] = {
    o.obligation_id: o
    for o in (
        FIDUCIARY_DUTY,
        BEST_EXECUTION,
        BOOKS_AND_RECORDS,
        MNPI_SURVEILLANCE,
        ALLOCATION_FAIRNESS,
        CUSTODY_RULE,
        MARKETING_RULE,
        DUTY_OF_CARE_ADVICE,
        INDEPENDENT_VALUATION,
    )
}


SUB_VERTICAL_OBLIGATIONS: dict[SubVertical, tuple[str, ...]] = {
    SubVertical.BUY_SIDE_QUANT: (
        "fiduciary_duty",
        "best_execution",
        "books_and_records",
        "mnpi_surveillance",
    ),
    SubVertical.PE_CREDIT_GP: (
        "fiduciary_duty",
        "allocation_fairness",
        "custody_rule",
        # A credit GP sitting on a creditors'/lender committee holds MNPI — the
        # §204A exposure behind SEC v. Sound Point Capital (Release 2024-106).
        "mnpi_surveillance",
    ),
    SubVertical.PRIVATE_WEALTH_UHNW: (
        "fiduciary_duty",
        "marketing_rule",
        "duty_of_care_advice",
    ),
    SubVertical.FUND_ADMIN_VALUATION: (
        "custody_rule",
        "independent_valuation",
        "books_and_records",
    ),
}


def obligations_for(sub_vertical: SubVertical) -> tuple[Obligation, ...]:
    """Return the obligations that apply to ``sub_vertical``, in declared order."""
    return tuple(ALL_OBLIGATIONS[oid] for oid in SUB_VERTICAL_OBLIGATIONS[sub_vertical])
