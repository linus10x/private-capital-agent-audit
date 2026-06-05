"""P5 — Effective-challenge harness (model-validation second line).

Built to the *corrected* primitive standard, in two parts:

* **(a) ENFORCE in code** — the challenger's identity must differ from the
  primary's. ``challenger_id == primary_id`` (or the same callable object) is
  rejected at construction, so ``disagreement_rate`` can never be forced to 0
  by self-challenge.
* **(b) RECORD as attestation** — an operator-supplied
  :class:`IndependenceAttestation` (not same owner / not same vendor family /
  not same prompt template) plus WHO chose the challenger and WHEN, written to
  the chain. Vendor-family and prompt-template independence are **attested, not
  code-detected** (no detector is fabricated). **A model owner cannot
  self-challenge to a clean ``ACCEPT_PRIMARY``**: when independence is not
  attested, the recommendation is forced to ``ESCALATE``.

Regulatory anchor: the "effective challenge" concept originating in SR 11-7
(Federal Reserve / OCC 2011-12). For an SEC adviser the closest analogue is the
duty-of-care obligation to have a reasonable basis for the advice/decisions a
model produces (Advisers Act §206, per Release IA-5248) and §206(4)/Rule
206(4)-7 compliance-program adequacy. This harness produces the artifact a
second-line reviewer attaches to that basis. It is a *documented reference
pattern*, not a deployed adviser validation system. See
``docs/regulatory/obligation_map.md``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Recommendation(Enum):
    ACCEPT_PRIMARY = "accept_primary"
    INVESTIGATE = "investigate"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class IndependenceAttestation:
    """Operator's attestation of challenger independence (not code-detected).

    Independence holds only when none of the three "same" flags is set.
    """

    chosen_by: str
    same_owner: bool
    same_vendor_family: bool
    same_prompt_template: bool
    statement: str = ""
    chosen_at: str = field(default_factory=_now_iso)

    @property
    def is_independent(self) -> bool:
        return not (self.same_owner or self.same_vendor_family or self.same_prompt_template)


@dataclass(frozen=True)
class ChallengeReport:
    primary_id: str
    challenger_id: str
    primary_accuracy: float
    challenger_accuracy: float
    disagreement_rate: float
    disagreement_examples: tuple[tuple[Any, Any, Any], ...]
    independent: bool
    recommendation: Recommendation
    eval_set_hash: str
    methodology: str = "effective_challenge_v1"


class EffectiveChallengeHarness:
    """Run a primary model against an independent challenger and record the result.

    Parameters
    ----------
    primary_model, challenger_model:
        Callables ``input -> output``.
    eval_set:
        ``[(input, expected_output), ...]``.
    independence:
        Operator's :class:`IndependenceAttestation` for the challenger.
    primary_id, challenger_id:
        Identities; ``challenger_id == primary_id`` is rejected.
    """

    def __init__(
        self,
        *,
        primary_model: Callable[[Any], Any],
        challenger_model: Callable[[Any], Any],
        eval_set: list[tuple[Any, Any]],
        independence: IndependenceAttestation,
        primary_id: str,
        challenger_id: str,
        audit_chain: AuditChain | None = None,
        accept_threshold: float = 0.05,
        investigate_threshold: float = 0.30,
    ) -> None:
        if primary_id == challenger_id:
            raise ValueError(
                "challenger_id must differ from primary_id "
                "(self-challenge is rejected — P5 enforce-in-code)"
            )
        if primary_model is challenger_model:
            raise ValueError("challenger_model must not be the same callable as primary_model")
        if not eval_set:
            raise ValueError("eval_set must be non-empty")
        if not 0.0 <= accept_threshold < investigate_threshold <= 1.0:
            raise ValueError("require 0 <= accept_threshold < investigate_threshold <= 1")
        self._primary = primary_model
        self._challenger = challenger_model
        self._eval_set = eval_set
        self._independence = independence
        self._primary_id = primary_id
        self._challenger_id = challenger_id
        self._chain = audit_chain
        self._accept = accept_threshold
        self._investigate = investigate_threshold

    def _eval_set_hash(self) -> str:
        blob = json.dumps(self._eval_set, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def run(self) -> ChallengeReport:
        """Evaluate both models; derive a recommendation; record to chain."""
        n = len(self._eval_set)
        primary_correct = 0
        challenger_correct = 0
        disagreements = 0
        examples: list[tuple[Any, Any, Any]] = []
        for inp, expected in self._eval_set:
            p = self._primary(inp)
            c = self._challenger(inp)
            if p == expected:
                primary_correct += 1
            if c == expected:
                challenger_correct += 1
            if p != c:
                disagreements += 1
                if len(examples) < 20:
                    examples.append((inp, p, c))

        disagreement_rate = disagreements / n
        recommendation = self._recommend(disagreement_rate)

        report = ChallengeReport(
            primary_id=self._primary_id,
            challenger_id=self._challenger_id,
            primary_accuracy=primary_correct / n,
            challenger_accuracy=challenger_correct / n,
            disagreement_rate=disagreement_rate,
            disagreement_examples=tuple(examples),
            independent=self._independence.is_independent,
            recommendation=recommendation,
            eval_set_hash=self._eval_set_hash(),
        )
        self._record(report)
        return report

    def _recommend(self, disagreement_rate: float) -> Recommendation:
        # A model owner cannot self-challenge to a clean accept: without attested
        # independence, escalate regardless of disagreement rate.
        if not self._independence.is_independent:
            return Recommendation.ESCALATE
        if disagreement_rate <= self._accept:
            return Recommendation.ACCEPT_PRIMARY
        if disagreement_rate <= self._investigate:
            return Recommendation.INVESTIGATE
        return Recommendation.ESCALATE

    def _record(self, report: ChallengeReport) -> None:
        if self._chain is None:
            return
        self._chain.append(
            AuditEventType.MODEL_VALIDATED,
            AutonomyLevel.A0_INFORMATIONAL,
            agent_id=self._primary_id,
            payload={
                "challenger_id": self._challenger_id,
                "disagreement_rate": report.disagreement_rate,
                "recommendation": report.recommendation.value,
                "independent": report.independent,
                "independence_attestation": {
                    "chosen_by": self._independence.chosen_by,
                    "chosen_at": self._independence.chosen_at,
                    "same_owner": self._independence.same_owner,
                    "same_vendor_family": self._independence.same_vendor_family,
                    "same_prompt_template": self._independence.same_prompt_template,
                    "statement": self._independence.statement,
                },
                "eval_set_hash": report.eval_set_hash,
            },
            actor_id=self._independence.chosen_by,
        )
