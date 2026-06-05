"""Shared test doubles for the private-capital governance suite.

These fakes implement the library's seam Protocols (Authorizer,
AttestationVerifier) with deterministic, inspectable behavior so tests can
exercise the production-mode/authenticated paths without a real IdP.
"""

from __future__ import annotations

from typing import Any

from private_capital_agent_audit.governance.autonomy_ladder import ControlAttestation
from private_capital_agent_audit.governance.sovereign_veto import Principal


class FakeAuthorizer:
    """Deterministic Authorizer for tests.

    ``valid_credentials`` maps a credential string to the Principal it resolves
    to; unknown credentials fail authentication. ``allowed_actions`` (when set)
    restricts which actions authorize True; ``None`` authorizes any action for an
    authenticated non-agent principal.
    """

    def __init__(
        self,
        valid_credentials: dict[str, Principal] | None = None,
        allowed_actions: set[str] | None = None,
    ) -> None:
        self.valid_credentials = valid_credentials or {}
        self.allowed_actions = allowed_actions

    def authenticate(self, credential: str) -> Principal | None:
        return self.valid_credentials.get(credential)

    def authorize(self, principal: Principal, action: str, context: dict[str, Any]) -> bool:
        if self.allowed_actions is None:
            return True
        return action in self.allowed_actions


def human(principal_id: str = "operator-1") -> Principal:
    return Principal(principal_id=principal_id, is_agent=False)


def agent(principal_id: str = "agent-1") -> Principal:
    return Principal(principal_id=principal_id, is_agent=True)


class AcceptingVerifier:
    """AttestationVerifier that accepts any attestation whose attester != the agent."""

    def verify(self, attestation: ControlAttestation, requesting_agent_id: str) -> bool:
        return attestation.attester_id != requesting_agent_id


class RejectingVerifier:
    """AttestationVerifier that rejects everything (models a failed independence check)."""

    def verify(self, attestation: ControlAttestation, requesting_agent_id: str) -> bool:
        return False
