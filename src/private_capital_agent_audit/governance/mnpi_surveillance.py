"""Adviser control — MNPI / market-abuse surveillance (buy-side / quant; PE/credit GP).

A 0.1.0 MUST-HAVE control. It is a *documented reference control* implementing
the load-bearing concept of an information barrier: a restricted list (names the
adviser holds material nonpublic information on — trading is blocked) and a watch
list (heightened monitoring, trading allowed). An autonomous trading agent must
screen every order against the restricted list before the order is released; an
attempt to trade a restricted name is a barrier breach that is recorded and
should be gated by the sovereign veto.

This is NOT a deployed surveillance platform and does not infer what is or is
not MNPI — the deployer (the compliance function) curates the lists. The control
enforces the *consequence*: restricted-name orders are blocked.

Regulatory anchor (honest claim layer): **Advisers Act §204A** (15 U.S.C.
80b-4a) requires written policies reasonably designed to prevent the misuse of
MNPI; insider-trading liability anchors in **Exchange Act §10(b)** and **Rule
10b-5** (17 CFR 240.10b-5). See ``docs/regulatory/obligation_map.md``. The
enforcement backdrop includes adviser MNPI-controls actions such as SEC v. Sound
Point Capital Management (2024, Release 2024-106).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel

# Zero-width / BOM code points an agent could splice into a symbol to slip a
# restricted name past an exact-match barrier. Stripped during normalization.
_ZERO_WIDTH = dict.fromkeys(
    (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF), None
)  # ZWSP, ZWNJ, ZWJ, word-joiner, BOM


class ListType(Enum):
    RESTRICTED = "restricted"  # adviser holds MNPI; trading blocked
    WATCH = "watch"  # heightened monitoring; trading permitted


class ScreenOutcome(Enum):
    CLEARED = "cleared"
    BLOCKED = "blocked"  # restricted name — barrier breach
    FLAGGED = "flagged"  # watch-list name — monitored, not blocked


@dataclass(frozen=True)
class ScreeningResult:
    order_id: str
    symbol: str
    outcome: ScreenOutcome
    reason: str


class MNPISurveillance:
    """Restricted/watch lists + order screening against an information barrier.

    Parameters
    ----------
    audit_chain:
        Optional chain; list changes, screenings, and barrier breaches recorded.
    """

    def __init__(self, *, audit_chain: AuditChain | None = None) -> None:
        self._chain = audit_chain
        self._restricted: dict[str, str] = {}  # symbol -> reason
        self._watch: dict[str, str] = {}

    @staticmethod
    def _norm(symbol: str) -> str:
        """Aggressively normalize a symbol so homoglyph / zero-width / whitespace
        splicing cannot slip a restricted name past the exact-match barrier.

        NFKC folds fullwidth and compatibility forms (e.g. a fullwidth ``AAPL``
        normalizes to ASCII ``AAPL``); the zero-width set is stripped; ``split()``
        removes every Unicode whitespace run (including NBSP / ideographic space).
        The SAME normalization is applied on ``add`` and on ``screen_order`` so a
        restricted ``AAPL`` blocks an order whose symbol was spliced with a
        zero-width space or rendered in fullwidth glyphs.
        """
        s = unicodedata.normalize("NFKC", symbol)
        s = s.translate(_ZERO_WIDTH)
        return "".join(s.split()).upper()

    def add(self, symbol: str, list_type: ListType, reason: str) -> None:
        """Add a symbol to the restricted or watch list."""
        sym = self._norm(symbol)
        if not sym:
            raise ValueError("symbol must be non-empty")
        if list_type is ListType.RESTRICTED:
            self._restricted[sym] = reason
            self._watch.pop(sym, None)  # restricted supersedes watch
        else:
            # Do not demote a restricted name by adding it to the watch list.
            if sym in self._restricted:
                raise ValueError(
                    f"{sym!r} is on the restricted list; remove it before watch-listing"
                )
            self._watch[sym] = reason
        if self._chain is not None:
            self._chain.append(
                AuditEventType.MNPI_SCREENING,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id="mnpi-surveillance",
                payload={"action": "add", "symbol": sym, "list": list_type.value, "reason": reason},
            )

    def remove(self, symbol: str) -> None:
        """Remove a symbol from both lists (e.g. when MNPI goes stale/public)."""
        sym = self._norm(symbol)
        self._restricted.pop(sym, None)
        self._watch.pop(sym, None)
        if self._chain is not None:
            self._chain.append(
                AuditEventType.MNPI_SCREENING,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id="mnpi-surveillance",
                payload={"action": "remove", "symbol": sym},
            )

    def is_restricted(self, symbol: str) -> bool:
        return self._norm(symbol) in self._restricted

    def restricted_list(self) -> tuple[str, ...]:
        return tuple(sorted(self._restricted))

    def watch_list(self) -> tuple[str, ...]:
        return tuple(sorted(self._watch))

    def screen_order(self, order_id: str, symbol: str, *, account: str = "") -> ScreeningResult:
        """Screen a proposed order against the information barrier.

        A restricted name is BLOCKED (a barrier breach is recorded); a watch-list
        name is FLAGGED but permitted; anything else is CLEARED.
        """
        sym = self._norm(symbol)
        if sym in self._restricted:
            result = ScreeningResult(
                order_id=order_id,
                symbol=sym,
                outcome=ScreenOutcome.BLOCKED,
                reason=f"restricted (MNPI): {self._restricted[sym]}",
            )
            if self._chain is not None:
                self._chain.append(
                    AuditEventType.MNPI_BARRIER_BREACH,
                    AutonomyLevel.A0_INFORMATIONAL,
                    agent_id="mnpi-surveillance",
                    payload={
                        "order_id": order_id,
                        "symbol": sym,
                        "account": account,
                        "reason": result.reason,
                    },
                )
            return result

        if sym in self._watch:
            outcome, reason = ScreenOutcome.FLAGGED, f"watch list: {self._watch[sym]}"
        else:
            outcome, reason = ScreenOutcome.CLEARED, "no MNPI restriction"

        result = ScreeningResult(order_id=order_id, symbol=sym, outcome=outcome, reason=reason)
        if self._chain is not None:
            self._chain.append(
                AuditEventType.MNPI_SCREENING,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id="mnpi-surveillance",
                payload={
                    "action": "screen",
                    "order_id": order_id,
                    "symbol": sym,
                    "account": account,
                    "outcome": outcome.value,
                },
            )
        return result
