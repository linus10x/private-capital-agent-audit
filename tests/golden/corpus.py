"""Golden corpus — real, public SEC enforcement actions, one cluster per
adviser sub-vertical control.

Matters-of-record only. Every entry carries a primary-source URL and a
``verified`` flag (confirmed against a primary SEC / U.S.C. / CFR source on
2026-06-05) or is marked ``verified=False`` and described as UNVERIFIED. No
allegations, amounts, or outcomes are invented; where a precise SEC release
number or dollar figure could not be confirmed against a primary source this
pass, the field is left ``None`` and ``verified=False``.

Each entry maps the matter to the obligation_id (from
``governance.obligation_map``) the control set in this library addresses, so the
test asserts the obligation map actually covers every real enforcement theme.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnforcementMatter:
    """One public SEC enforcement matter, mapped to the obligation it implicates."""

    matter_id: str
    name: str
    date: str  # ISO date or year; "" if not pinned
    sec_release: str | None  # press-release / administrative-proceeding number
    outcome: str
    obligation_id: str
    primary_source_url: str
    verified: bool


# --- Category 1: off-channel comms / books-and-records (275.204-2) -----------

OFF_CHANNEL = (
    EnforcementMatter(
        matter_id="offchannel_2022_174",
        name="16 firms (15 broker-dealers + 1 affiliated adviser) — off-channel recordkeeping wave",
        date="2022-09-27",
        sec_release="2022-174",
        outcome="More than $1.1 billion in combined penalties; firms admitted facts.",
        obligation_id="books_and_records",
        primary_source_url="https://www.sec.gov/newsroom/press-releases/2022-174",
        verified=True,
    ),
    EnforcementMatter(
        matter_id="offchannel_2024_18",
        name="16 firms — off-channel communications follow-on wave",
        date="2024-02-09",
        sec_release="2024-18",
        outcome="More than $81 million in combined penalties.",
        obligation_id="books_and_records",
        primary_source_url="https://www.sec.gov/newsroom/press-releases/2024-18",
        verified=True,
    ),
    EnforcementMatter(
        matter_id="offchannel_2024_98",
        name="26 firms — off-channel communications wave (BDs, advisers, dual)",
        date="2024-08-14",
        sec_release="2024-98",
        outcome="$392.75 million in combined penalties.",
        obligation_id="books_and_records",
        primary_source_url="https://www.sec.gov/newsroom/press-releases/2024-98",
        verified=True,
    ),
    EnforcementMatter(
        matter_id="offchannel_2024_144",
        name="11 firms — off-channel communications wave (some self-reported)",
        date="2024-09-24",
        sec_release="2024-144",
        outcome="More than $88 million in combined penalties.",
        obligation_id="books_and_records",
        primary_source_url="https://www.sec.gov/newsroom/press-releases/2024-144",
        verified=True,
    ),
)

# --- Category 2: marketing rule (275.206(4)-1) ------------------------------

MARKETING = (
    EnforcementMatter(
        matter_id="marketing_titan_2023_153",
        name="Titan Global Capital Management USA LLC — Marketing Rule hypothetical-performance",
        date="2023-08-21",
        sec_release="2023-153",
        outcome=(
            "Cease-and-desist + censure; $192,454 disgorgement + prejudgment interest "
            "and an $850,000 civil penalty. Advertised hypothetical 'annualized' results "
            "without the required policies (an early action under the amended Marketing Rule)."
        ),
        obligation_id="marketing_rule",
        primary_source_url="https://www.sec.gov/newsroom/press-releases/2023-153",
        verified=True,
    ),
    EnforcementMatter(
        matter_id="marketing_nine_adviser_sweep_2023",
        name="Nine advisers — hypothetical-performance marketing-rule sweep",
        date="2023-09-11",
        sec_release=None,  # aggregate press-release number not confirmed this pass
        outcome="$850,000 combined civil penalties (per public reporting).",
        obligation_id="marketing_rule",
        primary_source_url="https://www.sec.gov/litigation/admin",
        verified=False,
    ),
)

# --- Category 3: custody rule (275.206(4)-2) --------------------------------

CUSTODY = (
    EnforcementMatter(
        matter_id="custody_munakata_ia_6901s",
        name="Munakata Associates — custody-rule surprise-exam failure",
        date="2024",
        sec_release="IA-6901-S",
        outcome=(
            "Cease-and-desist + $50,000 penalty. Firm had custody (signatory authority / "
            "POA over client accounts) but failed to arrange the required surprise examinations."
        ),
        obligation_id="custody_rule",
        primary_source_url=(
            "https://www.sec.gov/enforcement-litigation/administrative-proceedings/ia-6901-s"
        ),
        verified=True,
    ),
    EnforcementMatter(
        matter_id="custody_hi2_ia_6691",
        name="Hi2 Investment Management, LLC — custody-rule + compliance findings",
        date="2024",
        sec_release="IA-6691",
        outcome=(
            "Custody-rule and compliance violations (penalty amount not individually confirmed)."
        ),
        obligation_id="custody_rule",
        primary_source_url="https://www.sec.gov/files/litigation/admin/2024/ia-6691.pdf",
        verified=False,
    ),
)

# --- Category 4: MNPI / insider trading (204A / 10b-5) ----------------------

MNPI = (
    EnforcementMatter(
        matter_id="mnpi_soundpoint_2024_106",
        name="Sound Point Capital Management LP — CLO-trading MNPI controls",
        date="2024-08-26",
        sec_release="2024-106",
        outcome=(
            "$1.8 million civil penalty + cease-and-desist. Traded CLOs while on lender "
            "groups / creditors' committees holding MNPI; §204A controls failure."
        ),
        obligation_id="mnpi_surveillance",
        primary_source_url="https://www.sec.gov/newsroom/press-releases/2024-106",
        verified=True,
    ),
    EnforcementMatter(
        matter_id="mnpi_marathon_2024",
        name="Marathon Asset Management, LP — creditors'-committee MNPI controls",
        date="2024-09-30",
        sec_release=None,  # precise release number not confirmed this pass
        outcome="Cease-and-desist + $1.5 million civil penalty (per public reporting); §204A.",
        obligation_id="mnpi_surveillance",
        primary_source_url="https://www.sec.gov/litigation/admin",
        verified=False,
    ),
)

# --- Category 5: cherry-picking / allocation fairness (§206) ----------------

ALLOCATION = (
    EnforcementMatter(
        matter_id="alloc_js_oliver_2013_168",
        name="J.S. Oliver Capital Management, L.P. / Ian O. Mausner — cherry-picking",
        date="2013-08",
        sec_release="2013-168",
        outcome=(
            "Charged with allocating favorably-priced post-close trades to affiliated "
            "funds (alleged ~$10.7M client harm); the ALJ ordered penalties and a bar, "
            "with figures litigated/modified on review. Cite the primary source for the "
            "operative amounts."
        ),
        obligation_id="allocation_fairness",
        primary_source_url="https://www.sec.gov/newsroom/press-releases/2013-168",
        verified=True,
    ),
    EnforcementMatter(
        matter_id="alloc_breton_2017_32",
        name="Michael J. Breton / Strategic Capital Management — cherry-picking",
        date="2017",
        sec_release="2017-32",
        outcome=(
            "Defrauded clients of ~$1.3M by allocating profitable trades to himself and "
            "losses to clients via a master account; barred. Detected via SEC data analytics."
        ),
        obligation_id="allocation_fairness",
        primary_source_url="https://www.sec.gov/news/pressrelease/2017-32.html",
        verified=True,
    ),
)


ALL_MATTERS: tuple[EnforcementMatter, ...] = (
    *OFF_CHANNEL,
    *MARKETING,
    *CUSTODY,
    *MNPI,
    *ALLOCATION,
)
