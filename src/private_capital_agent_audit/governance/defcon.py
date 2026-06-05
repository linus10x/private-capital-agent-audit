"""P4 — DEFCON risk-state machine with a transition-direction guard.

Built to the *corrected* primitive standard (do NOT replicate the upstream defect
where a single unguarded call could move ``HALT -> NORMAL``):

* **Escalation is immediate and automatic** — :meth:`evaluate` raises the level
  the moment risk metrics breach a threshold.
* **De-escalation is guarded.** :meth:`evaluate` never automatically lowers the
  level. Lowering requires the **manual-override + Authorizer path**
  (:meth:`manual_override`), authenticated and authorized, and it may only step
  **one level at a time** — a one-call ``HALT -> NORMAL`` is refused.

For an adviser the levels gate an autonomous program's authority to keep writing
consequential decisions (orders, allocations). The illustrative thresholds below
are EXAMPLES — calibrate to the program's strategy, capital base, and risk
appetite before relying on them. Regulatory anchors: NIST AI RMF (Manage),
EU AI Act Art. 9 (risk management).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.governance.sovereign_veto import Authorizer
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


class DEFCON(IntEnum):
    """Five risk levels — NORMAL (1, full execution) to HALT (5, suspended)."""

    NORMAL = 1
    CAUTION = 2
    ALERT = 3
    DANGER = 4
    HALT = 5


@dataclass(frozen=True)
class RiskMetrics:
    """Inputs that drive escalation. All fractions are 0.0–1.0.

    Illustrative drivers only — a deployer maps its own risk signals onto these
    (or onto a richer metric set) before calibrating the thresholds below.
    """

    portfolio_drawdown: float = 0.0
    daily_loss: float = 0.0
    consecutive_losses: int = 0


class DEFCONTransitionError(Exception):
    """Raised on an illegal transition (e.g. multi-step or unauthorized de-escalation)."""


def _target_from_metrics(m: RiskMetrics) -> DEFCON:
    """Map metrics to the severity they demand (escalation only).

    Thresholds are ILLUSTRATIVE EXAMPLES, not calibrated production values.
    """
    # Fail safe on a corrupted risk feed: a non-finite (NaN/inf) metric escapes
    # every threshold comparison, so treat it as a HALT condition, not NORMAL.
    # Covers all three drivers — ``consecutive_losses`` is typed int but Python
    # does not enforce it, and a NaN there would otherwise return NORMAL.
    if not (
        math.isfinite(m.portfolio_drawdown)
        and math.isfinite(m.daily_loss)
        and math.isfinite(m.consecutive_losses)
    ):
        return DEFCON.HALT
    if m.portfolio_drawdown >= 0.20 or m.daily_loss >= 0.10 or m.consecutive_losses >= 8:
        return DEFCON.HALT
    if m.portfolio_drawdown >= 0.12 or m.daily_loss >= 0.06 or m.consecutive_losses >= 6:
        return DEFCON.DANGER
    if m.portfolio_drawdown >= 0.07 or m.daily_loss >= 0.04 or m.consecutive_losses >= 4:
        return DEFCON.ALERT
    if m.portfolio_drawdown >= 0.03 or m.daily_loss >= 0.02 or m.consecutive_losses >= 2:
        return DEFCON.CAUTION
    return DEFCON.NORMAL


class DEFCONMachine:
    """Risk-state machine; escalates automatically, de-escalates only by guard.

    Parameters
    ----------
    authorizer:
        Authentication/authorization seam for de-escalation. Required in
        ``production`` mode.
    mode:
        ``"advisory"`` (default) or ``"production"`` (a missing authorizer raises
        at construction).
    audit_chain:
        Optional chain; transitions are recorded when wired.
    """

    DEESCALATE_ACTION = "defcon_deescalate"

    def __init__(
        self,
        *,
        authorizer: Authorizer | None = None,
        mode: str = "advisory",
        audit_chain: AuditChain | None = None,
    ) -> None:
        if mode not in ("advisory", "production"):
            raise ValueError(f"mode must be 'advisory' or 'production', got {mode!r}")
        if mode == "production" and authorizer is None:
            raise ValueError(
                "production mode requires a wired authorizer for de-escalation (fail-closed)"
            )
        self._authorizer = authorizer
        self._mode = mode
        self._chain = audit_chain
        self._level = DEFCON.NORMAL

    @property
    def mode(self) -> str:
        return self._mode

    def current_level(self) -> DEFCON:
        return self._level

    def evaluate(self, metrics: RiskMetrics) -> DEFCON:
        """Escalate immediately on breach; never auto-de-escalate."""
        target = _target_from_metrics(metrics)
        if target > self._level:
            self._record(self._level, target, actor_id="system:auto-escalate", manual=False)
            self._level = target
        return self._level

    def manual_override(
        self,
        target_level: DEFCON,
        reason: str,
        *,
        credential: str | None = None,
        operator_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> DEFCON:
        """Operator-driven transition. De-escalation is one-step and authorized.

        De-escalation (lowering severity) may move at most one level and, when an
        authorizer is wired, requires an authenticated, authorized non-agent
        principal. A one-call ``HALT -> NORMAL`` is refused.
        """
        context = context or {}
        if target_level == self._level:
            return self._level

        is_deescalation = target_level < self._level
        if is_deescalation:
            if self._level - target_level > 1:
                raise DEFCONTransitionError(
                    f"de-escalation must be one level at a time: "
                    f"{self._level.name} -> {target_level.name} is not permitted in one call"
                )
            actor = self._authorize_deescalation(credential, operator_id, context)
        else:
            # Manual escalation is always permitted (raising severity is safe).
            actor = operator_id or "operator:manual"

        self._record(self._level, target_level, actor_id=actor, manual=True, reason=reason)
        self._level = target_level
        return self._level

    def _authorize_deescalation(
        self,
        credential: str | None,
        operator_id: str | None,
        context: dict[str, Any],
    ) -> str:
        if self._authorizer is not None:
            if credential is None:
                raise DEFCONTransitionError("a credential is required to de-escalate")
            principal = self._authorizer.authenticate(credential)
            if principal is None:
                raise DEFCONTransitionError("credential failed authentication")
            if principal.is_agent:
                raise DEFCONTransitionError("an agent principal may not de-escalate DEFCON")
            if not self._authorizer.authorize(principal, self.DEESCALATE_ACTION, context):
                raise DEFCONTransitionError(
                    f"principal {principal.principal_id!r} not authorized to de-escalate"
                )
            return principal.principal_id
        # Advisory mode: labeled, not hidden.
        if operator_id is None:
            raise DEFCONTransitionError("operator_id required to de-escalate in advisory mode")
        return operator_id

    def _record(
        self,
        frm: DEFCON,
        to: DEFCON,
        *,
        actor_id: str,
        manual: bool,
        reason: str | None = None,
    ) -> None:
        if self._chain is None:
            return
        self._chain.append(
            AuditEventType.DEFCON_TRANSITION,
            AutonomyLevel.A0_INFORMATIONAL,
            agent_id="private-capital-defcon",
            payload={
                "from": frm.name,
                "to": to.name,
                "manual": manual,
                "reason": reason,
                "authenticated": self._authorizer is not None and manual and to < frm,
            },
            actor_id=actor_id,
        )
