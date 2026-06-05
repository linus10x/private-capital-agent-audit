"""P2 — Sovereign veto (human-in-the-loop kill switch).

Built to the *corrected* primitive standard (do NOT replicate the upstream
defect of a no-Authorizer default plus an unauthenticated free-string
``operator_id``):

* In **production mode** a wired :class:`Authorizer` is **mandatory** — the
  constructor refuses to start without one (fail closed).
* ``operator_id`` is never a trusted free string: clearing a veto requires a
  **credential** that the Authorizer resolves to an **authenticated principal**
  (an IdP/KMS-style seam) and then authorizes for the ``clear_veto`` action.
* **An agent cannot clear its own (or any) veto.** Veto clearance is a
  human-oversight act (EU AI Act Art. 14); an agent principal is rejected.
* The **default ``advisory`` mode** stays backward-compatible and is *labeled
  advisory*: an unauthenticated clear is permitted but recorded as
  ``authenticated=false, mode="advisory"`` — honest, not hidden.

Regulatory anchors: EU AI Act Art. 14 (human oversight). For an adviser, the
veto is the last line between an autonomous agent and a consequential write
(an order, an allocation, an outbound marketing communication) that could
breach the §206 fiduciary duty. Veto state persistence/recovery is documented
in ``docs/FAILURE-MODES.md`` — the reference in-memory state is lost on process
exit unless an ``audit_chain`` with a durable log file is wired, which is the
recommended recovery path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class VetoReason(Enum):
    """Why a veto fired — recorded to the chain for the audit trail."""

    RISK_LIMIT_BREACH = "risk_limit_breach"
    BEST_EXECUTION_CONCERN = "best_execution_concern"
    ALLOCATION_FAIRNESS = "allocation_fairness"
    MNPI_HOLD = "mnpi_hold"
    MARKETING_NONCOMPLIANCE = "marketing_noncompliance"
    CUSTODY_EXCEPTION = "custody_exception"
    REGULATORY_HOLD = "regulatory_hold"
    MODEL_DRIFT = "model_drift"
    MANUAL = "manual"


@dataclass(frozen=True)
class Principal:
    """An authenticated identity resolved from a credential by the Authorizer.

    ``is_agent`` distinguishes a non-human agent principal (which may never
    clear a veto) from a human/operator principal.
    """

    principal_id: str
    is_agent: bool = False
    claims: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Authorizer(Protocol):
    """IdP/KMS-style seam: authenticate a credential, then authorize an action.

    A deployer wires a real identity provider here. ``authenticate`` returns the
    resolved :class:`Principal` or ``None`` if the credential is invalid;
    ``authorize`` decides whether that principal may perform ``action``.
    """

    def authenticate(self, credential: str) -> Principal | None: ...

    def authorize(self, principal: Principal, action: str, context: dict[str, Any]) -> bool: ...


@dataclass
class VetoRecord:
    """A single veto's lifecycle (triggered → optionally cleared)."""

    veto_id: str
    reason: VetoReason
    triggered_by: str
    description: str
    triggered_at: str
    cleared_by: str | None = None
    cleared_at: str | None = None
    clear_reason: str | None = None
    cleared_authenticated: bool = False


class VetoNotAuthorizedError(PermissionError):
    """Raised when a clear attempt fails authentication/authorization."""


class SovereignVeto:
    """A fail-closed kill switch with an un-self-clearable, authenticated clear.

    Parameters
    ----------
    agent_id:
        The agent this veto governs. An agent principal whose id matches (or any
        agent principal) is rejected from clearing.
    authorizer:
        The authentication/authorization seam. Required in ``production`` mode.
    mode:
        ``"advisory"`` (default, backward-compatible) or ``"production"``
        (strict: a missing authorizer raises at construction).
    audit_chain:
        Optional chain; trigger/clear are recorded when wired.
    """

    CLEAR_ACTION = "clear_veto"

    def __init__(
        self,
        *,
        agent_id: str,
        authorizer: Authorizer | None = None,
        mode: str = "advisory",
        audit_chain: AuditChain | None = None,
    ) -> None:
        if mode not in ("advisory", "production"):
            raise ValueError(f"mode must be 'advisory' or 'production', got {mode!r}")
        if mode == "production" and authorizer is None:
            raise ValueError(
                "production mode requires a wired authorizer (fail-closed); "
                "refusing to start a sovereign veto without one"
            )
        self._agent_id = agent_id
        self._authorizer = authorizer
        self._mode = mode
        self._chain = audit_chain
        self._active: VetoRecord | None = None
        self._counter = 0

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_vetoed(self) -> bool:
        return self._active is not None

    @property
    def active_record(self) -> VetoRecord | None:
        return self._active

    def allow_execution(self) -> bool:
        """The gate an agent must consult before acting; ``False`` while vetoed."""
        return not self.is_vetoed

    def trigger(
        self,
        reason: VetoReason,
        triggered_by: str,
        description: str,
    ) -> VetoRecord:
        """Engage the veto. A second trigger replaces the active record."""
        self._counter += 1
        record = VetoRecord(
            veto_id=f"veto-{self._counter}",
            reason=reason,
            triggered_by=triggered_by,
            description=description,
            triggered_at=_now_iso(),
        )
        self._active = record
        if self._chain is not None:
            self._chain.append(
                AuditEventType.VETO_TRIGGERED,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id=self._agent_id,
                payload={
                    "veto_id": record.veto_id,
                    "reason": reason.value,
                    "description": description,
                },
                actor_id=triggered_by,
            )
        return record

    def clear(
        self,
        reason: str,
        *,
        credential: str | None = None,
        operator_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> VetoRecord:
        """Clear the active veto.

        Production mode requires ``credential``; the authorizer must resolve it
        to a non-agent principal authorized for ``clear_veto``. Advisory mode
        permits an unauthenticated ``operator_id`` clear but records it as such.
        """
        if self._active is None:
            raise ValueError("no active veto to clear")
        context = context or {}

        if self._authorizer is not None:
            if credential is None:
                raise VetoNotAuthorizedError(
                    "a credential is required to clear a veto when an authorizer is wired"
                )
            principal = self._authorizer.authenticate(credential)
            if principal is None:
                raise VetoNotAuthorizedError("credential failed authentication")
            if principal.is_agent:
                raise VetoNotAuthorizedError(
                    "an agent principal may not clear a sovereign veto "
                    "(human-oversight act per EU AI Act Art. 14)"
                )
            if not self._authorizer.authorize(principal, self.CLEAR_ACTION, context):
                raise VetoNotAuthorizedError(
                    f"principal {principal.principal_id!r} not authorized to clear the veto"
                )
            cleared_by = principal.principal_id
            authenticated = True
        else:
            # Advisory mode only: labeled, not hidden.
            if operator_id is None:
                raise ValueError("operator_id is required to clear in advisory mode")
            if operator_id == self._agent_id:
                raise VetoNotAuthorizedError("an agent cannot clear its own veto")
            cleared_by = operator_id
            authenticated = False

        record = self._active
        record.cleared_by = cleared_by
        record.cleared_at = _now_iso()
        record.clear_reason = reason
        record.cleared_authenticated = authenticated
        self._active = None
        if self._chain is not None:
            self._chain.append(
                AuditEventType.VETO_CLEARED,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id=self._agent_id,
                payload={
                    "veto_id": record.veto_id,
                    "clear_reason": reason,
                    "authenticated": authenticated,
                    "mode": self._mode,
                },
                actor_id=cleared_by,
            )
        return record
