"""Private-capital governance primitives and adviser-native controls.

Five corrected primitives (P1–P5) plus the 0.1.0 adviser-native controls for
SEC-registered investment advisers. See each module's docstring for its claim
layer (implemented control vs documented pattern) and primary-sourced
regulatory anchors. Every obligation is grounded in the Advisers Act §206
fiduciary regime; the package encodes no other actor's standard of conduct.
"""

from __future__ import annotations

from private_capital_agent_audit.governance.allocation_fairness import (
    AllocationAssessment,
    AllocationFairnessMonitor,
    Fill,
)
from private_capital_agent_audit.governance.audit_chain import (
    GENESIS_DOMAIN_SEPARATOR,
    GENESIS_HASH,
    AuditChain,
    AuditChainTamperError,
    InMemoryWitnessRegister,
    WitnessRegister,
    _compute_genesis_hash,
)
from private_capital_agent_audit.governance.autonomy_ladder import (
    LEVEL_REQUIRED_CONTROLS,
    AttestationVerifier,
    AutonomyLadder,
    ControlAttestation,
    PromotionDecision,
)
from private_capital_agent_audit.governance.best_execution import (
    RECOGNIZED_EXECUTION_FACTORS,
    BestExecutionGate,
    BestExReview,
    ExecutionFactors,
    Side,
)
from private_capital_agent_audit.governance.books_and_records import (
    BooksAndRecordsMonitor,
    CommunicationEvent,
    RecordkeepingFinding,
    RecordRetention,
)
from private_capital_agent_audit.governance.custody_rule import (
    CustodyArrangement,
    CustodyAssessment,
    CustodyRuleCheck,
)
from private_capital_agent_audit.governance.defcon import (
    DEFCON,
    DEFCONMachine,
    DEFCONTransitionError,
    RiskMetrics,
)
from private_capital_agent_audit.governance.effective_challenge_harness import (
    ChallengeReport,
    EffectiveChallengeHarness,
    IndependenceAttestation,
    Recommendation,
)
from private_capital_agent_audit.governance.marketing_rule import (
    Advertisement,
    MarketingReview,
    MarketingReviewGate,
)
from private_capital_agent_audit.governance.mnpi_surveillance import (
    ListType,
    MNPISurveillance,
    ScreeningResult,
    ScreenOutcome,
)
from private_capital_agent_audit.governance.obligation_map import (
    ALL_OBLIGATIONS,
    SUB_VERTICAL_OBLIGATIONS,
    Obligation,
    SubVertical,
    obligations_for,
)
from private_capital_agent_audit.governance.sovereign_veto import (
    Authorizer,
    Principal,
    SovereignVeto,
    VetoNotAuthorizedError,
    VetoReason,
    VetoRecord,
)
from private_capital_agent_audit.governance.valuation_governance import (
    PriceSource,
    ValuationAssessment,
    ValuationGovernanceCheck,
    ValuationInput,
)

__all__ = [
    # P1 — level gate
    "AutonomyLadder",
    "AttestationVerifier",
    "ControlAttestation",
    "PromotionDecision",
    "LEVEL_REQUIRED_CONTROLS",
    # P2 — sovereign veto
    "SovereignVeto",
    "Authorizer",
    "Principal",
    "VetoReason",
    "VetoRecord",
    "VetoNotAuthorizedError",
    # P3 — audit chain
    "AuditChain",
    "AuditChainTamperError",
    "WitnessRegister",
    "InMemoryWitnessRegister",
    "GENESIS_HASH",
    "GENESIS_DOMAIN_SEPARATOR",
    "_compute_genesis_hash",
    # P4 — DEFCON
    "DEFCON",
    "DEFCONMachine",
    "DEFCONTransitionError",
    "RiskMetrics",
    # P5 — effective challenge
    "EffectiveChallengeHarness",
    "ChallengeReport",
    "IndependenceAttestation",
    "Recommendation",
    # adviser-native controls
    "BestExecutionGate",
    "BestExReview",
    "ExecutionFactors",
    "Side",
    "RECOGNIZED_EXECUTION_FACTORS",
    "MNPISurveillance",
    "ListType",
    "ScreenOutcome",
    "ScreeningResult",
    "CustodyRuleCheck",
    "CustodyArrangement",
    "CustodyAssessment",
    "MarketingReviewGate",
    "Advertisement",
    "MarketingReview",
    "AllocationFairnessMonitor",
    "AllocationAssessment",
    "Fill",
    "BooksAndRecordsMonitor",
    "CommunicationEvent",
    "RecordRetention",
    "RecordkeepingFinding",
    "ValuationGovernanceCheck",
    "ValuationInput",
    "ValuationAssessment",
    "PriceSource",
    # obligation map (regulatory-accuracy surface)
    "SubVertical",
    "Obligation",
    "ALL_OBLIGATIONS",
    "SUB_VERTICAL_OBLIGATIONS",
    "obligations_for",
]
