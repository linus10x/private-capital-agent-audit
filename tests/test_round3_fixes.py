"""Regression tests for the round-3 fresh-review remediations.

Each pins a NaN/negative-input fail-open or integrity gap the cold code/security
chamber surfaced, so the hardening cannot silently regress.
"""

from __future__ import annotations

import math

import pytest

from private_capital_agent_audit.governance.audit_chain import AuditChain
from private_capital_agent_audit.governance.books_and_records import (
    BooksAndRecordsMonitor,
    RecordRetention,
)
from private_capital_agent_audit.governance.custody_rule import (
    CustodyArrangement,
    CustodyRuleCheck,
)
from private_capital_agent_audit.governance.defcon import DEFCON, DEFCONMachine, RiskMetrics
from private_capital_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

# --- M1: books-and-records NaN age fails closed -----------------------------


def test_books_retention_nan_age_fails_closed() -> None:
    mon = BooksAndRecordsMonitor()
    finding = mon.evaluate_retention(
        RecordRetention("r", "ad", age_years=math.nan, readily_accessible=False, disposed=True)
    )
    assert finding.compliant is False
    assert any("non-finite" in r for r in finding.reasons)


# --- M2: DEFCON NaN consecutive_losses halts (fail-safe) --------------------


def test_defcon_nan_consecutive_losses_halts() -> None:
    machine = DEFCONMachine()
    # consecutive_losses is typed int but Python does not enforce it; a NaN must
    # not escape every threshold and return NORMAL.
    assert machine.evaluate(RiskMetrics(consecutive_losses=float("nan"))) is DEFCON.HALT


# --- m4: custody rejects a negative distribution day-count ------------------


def test_custody_negative_days_rejected() -> None:
    check = CustodyRuleCheck()
    with pytest.raises(ValueError, match="non-negative"):
        check.assess(
            CustodyArrangement(
                "c",
                has_custody=True,
                qualified_custodian=True,
                account_statements_delivered=True,
                surprise_exam_current=False,
                is_pooled_vehicle=True,
                audited_financials_distributed=True,
                days_to_distribute_audited_financials=-30,
            )
        )


# --- m3: a caller mutating its payload dict cannot invalidate the stored event


def test_append_deep_copies_payload() -> None:
    chain = AuditChain(deployer_id="d")
    p = {"order": {"qty": 100}}
    chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", p)
    # Mutate the caller's dict (and a nested value) after append.
    p["order"]["qty"] = 999
    p["extra"] = "tampered"
    assert chain.verify() is True  # the stored event holds an independent copy
    assert chain.events()[-1].payload == {"order": {"qty": 100}}


# --- m5: a non-JSON-serializable payload raises at hash time -----------------


def test_non_serializable_payload_raises_not_coerced() -> None:
    ev = AuditEvent(
        sequence=0,
        event_type=AuditEventType.AGENT_ACTION,
        autonomy_level=AutonomyLevel.A2_DELEGATED,
        agent_id="a",
        payload={"v": object()},  # not JSON-serializable
        timestamp="2026-06-05T00:00:00+00:00",
        prev_hash="0" * 64,
    )
    with pytest.raises(TypeError):
        ev.compute_hash()
