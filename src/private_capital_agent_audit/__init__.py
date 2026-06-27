"""Governance patterns for autonomous AI agents at SEC-registered investment advisers.

Reference IP for adoption — **not** a control operating in production. The five
primitives (P1–P5) are real, tested reference patterns; the adviser-native
controls (best execution, MNPI/market-abuse surveillance, the custody rule, the
marketing rule, cross-client allocation fairness / anti-cherry-picking,
books-and-records / off-channel-communications capture, and independent-valuation
governance) are implemented and tested reference controls.

Scope: this library governs **investment advisers** under the Investment
Advisers Act of 1940 — the fiduciary duty (duty of care + duty of loyalty)
under **§206**, as articulated in SEC Release IA-5248. It encodes only the
investment-adviser fiduciary regime; it does not model any other actor's
standard of conduct.

Public API::

    from private_capital_agent_audit.governance import (
        AutonomyLadder, SovereignVeto, AuditChain, DEFCONMachine,
        EffectiveChallengeHarness,
        BestExecutionGate, MNPISurveillance, CustodyRuleCheck,
        MarketingReviewGate, AllocationFairnessMonitor, BooksAndRecordsMonitor,
        SubVertical, obligations_for,
    )

See README.md for the claim layer (implemented control vs documented pattern)
and docs/regulatory/ for the primary-sourced obligation mappings.
"""

from __future__ import annotations

__version__ = "0.1.4"

__all__ = ["__version__"]
