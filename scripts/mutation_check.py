#!/usr/bin/env python3
"""Deterministic, reviewable mutation pass over the load-bearing predicates.

Why a hand-authored harness rather than ``mutmut``: ``mutmut`` 3.5's copied-
``mutants/`` test runner does not resolve this package's imports under Python
3.14 in CI. Rather than ship an unreproducible result, this harness applies a
fixed catalog of *targeted* source mutations to the safety-critical predicates
(the corrected-primitive invariants and the control gates), runs the full test
suite against each mutated tree in an isolated copy, and asserts every mutant is
**killed** (the suite fails). A surviving mutant means a weak assertion.

Run:  python scripts/mutation_check.py
Exit: 0 if every mutant is killed; 1 otherwise (names the survivors).

This is a focused, bounded catalog (not exhaustive operator mutation) — the
``logged cap`` the test strategy requires: it covers the predicates whose flip
would break a corrected-primitive guarantee or a control's flag/approve
decision, which is where a surviving mutant would actually matter.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOV = "src/private_capital_agent_audit/governance"


@dataclass(frozen=True)
class Mutant:
    name: str
    rel_path: str
    old: str
    new: str


# Each mutant flips one load-bearing predicate/constant. If the suite still
# passes with the mutation applied, the mutant SURVIVES → a weak assertion.
MUTANTS: tuple[Mutant, ...] = (
    # P3 — chain link / tamper detection
    Mutant("chain_prev_link", f"{GOV}/audit_chain.py", "if event.prev_hash != prev:", "if False:"),
    Mutant(
        "chain_hash_recompute",
        f"{GOV}/audit_chain.py",
        "if event.event_hash != event.compute_hash():\n                    return False",
        "if event.event_hash != event.compute_hash():\n                    pass",
    ),
    Mutant(
        "chain_genesis_branch",
        f"{GOV}/audit_chain.py",
        "if _is_deployer_keyed_genesis(first_event):",
        "if False:",
    ),
    Mutant(  # sequence-contiguity check (reorder / interior-gap detection)
        "chain_sequence_check",
        f"{GOV}/audit_chain.py",
        "if event.sequence != index:\n                    return False",
        "if event.sequence != index:\n                    pass",
    ),
    Mutant(  # witness checkpoint match (regeneration / truncation / tail-rewrite)
        "chain_regen_checkpoint",
        f"{GOV}/audit_chain.py",
        "if sequence >= n or self._store[sequence].event_hash != head:",
        "if False:",
    ),
    # P2 — self-clear + agent-principal guard
    Mutant(
        "veto_self_clear",
        f"{GOV}/sovereign_veto.py",
        "if operator_id == self._agent_id:",
        "if False:",
    ),
    Mutant(
        "veto_agent_principal",
        f"{GOV}/sovereign_veto.py",
        "if principal.is_agent:\n                raise VetoNotAuthorizedError(",
        "if False:\n                raise VetoNotAuthorizedError(",
    ),
    # P4 — one-step de-escalation guard + escalation direction
    Mutant(
        "defcon_multistep_guard",
        f"{GOV}/defcon.py",
        "if self._level - target_level > 1:",
        "if False:",
    ),
    Mutant(
        "defcon_escalate_dir",
        f"{GOV}/defcon.py",
        "if target > self._level:",
        "if target < self._level:",
    ),
    Mutant(
        "defcon_agent_deescalate",
        f"{GOV}/defcon.py",
        "if principal.is_agent:",
        "if False:",
    ),
    # P5 — self-challenge + un-attested-independence escalation
    Mutant(
        "challenge_self_id",
        f"{GOV}/effective_challenge_harness.py",
        "if primary_id == challenger_id:",
        "if False:",
    ),
    Mutant(
        "challenge_independence_escalate",
        f"{GOV}/effective_challenge_harness.py",
        "if not self._independence.is_independent:\n            return Recommendation.ESCALATE",
        "if not self._independence.is_independent:\n"
        "            return Recommendation.ACCEPT_PRIMARY",
    ),
    # control — allocation cherry-picking flag direction
    Mutant(
        "allocation_disparity_dir",
        f"{GOV}/allocation_fairness.py",
        "if disparity > self._max_disparity:",
        "if disparity < self._max_disparity:",
    ),
    # control — best-ex slippage gate direction
    Mutant(
        "bestex_slippage_dir",
        f"{GOV}/best_execution.py",
        "if slippage > self._max_slippage:",
        "if slippage < self._max_slippage:",
    ),
    # control — custody surprise-exam exception
    Mutant(
        "custody_surprise_exam",
        f"{GOV}/custody_rule.py",
        "if not arrangement.surprise_exam_current:",
        "if False:",
    ),
)


def _run_suite(tree: Path) -> bool:
    """Run the test suite in ``tree``. Returns True if it PASSES (mutant survived)."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "--no-header", "-p", "no:cacheprovider"],
        cwd=tree,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> int:
    survivors: list[str] = []
    killed = 0
    for m in MUTANTS:
        with tempfile.TemporaryDirectory() as td:
            tree = Path(td) / "repo"
            shutil.copytree(
                REPO,
                tree,
                ignore=shutil.ignore_patterns(
                    ".git",
                    ".venv",
                    "__pycache__",
                    ".pytest_cache",
                    ".ruff_cache",
                    ".mypy_cache",
                    ".hypothesis",
                    "build",
                    "dist",
                    "*.egg-info",
                ),
            )
            target = tree / m.rel_path
            src = target.read_text(encoding="utf-8")
            if m.old not in src:
                survivors.append(f"{m.name} (SPEC ERROR: anchor not found in {m.rel_path})")
                continue
            target.write_text(src.replace(m.old, m.new, 1), encoding="utf-8")
            survived = _run_suite(tree)
            if survived:
                survivors.append(m.name)
            else:
                killed += 1
            print(f"  {'SURVIVED' if survived else 'killed  '}  {m.name}")

    total = len(MUTANTS)
    score = killed / total if total else 1.0
    print(f"\nMutation score: {killed}/{total} killed ({score:.0%})")
    if survivors:
        print("SURVIVORS (weak assertions — strengthen the suite):")
        for s in survivors:
            print(f"  - {s}")
        return 1
    print("All targeted mutants killed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
