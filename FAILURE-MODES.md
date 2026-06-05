# Failure modes

How each primitive and control fails, and what the deployer must do about it.

## P1 — Autonomy Ladder level gate

- **Advisory mode grants without verification.** With no verifier wired, a
  promotion can be granted on attested-but-unverified controls; the decision is
  labeled `verified=False` and a reason states it. *Mitigation:* run `production`
  mode with a real `AttestationVerifier` for any consequential promotion.
- **Attester independence is the verifier's job.** The gate calls
  `verifier.verify(att, requesting_agent_id)`; a permissive verifier that always
  returns `True` defeats the independence requirement. *Mitigation:* the verifier
  must actually check signature/identity and attester ≠ requesting agent.

## P2 — Sovereign veto

- **In-memory state is lost on process exit.** The active veto lives in memory.
  *Mitigation:* wire an `AuditChain` with a durable `log_file`; trigger/clear are
  recorded, so the active-veto set is reconstructable by replaying the ledger.
- **Advisory clears are unauthenticated.** Advisory mode permits an
  `operator_id` clear with no credential; it is recorded `authenticated=false`.
  *Mitigation:* `production` mode requires an Authorizer; an agent principal is
  always rejected, and an agent can never clear its own veto.

## P3 — Hash-chain ledger

- **Within-trust-boundary only.** A privileged in-process actor can rewrite the
  store and recompute a fresh, internally consistent chain. `verify()` proves
  internal consistency (each event's hash recomputes, links chain, and
  `sequence` is contiguous `0..n-1`, so reorder and interior gaps are caught),
  but not regeneration. *Mitigation:* anchor heads to an external
  `WitnessRegister`. The witness records `(sequence, head)` checkpoints, so
  `verify_regeneration_resistant()` detects **full regeneration** (the head
  differs at an anchored sequence), **truncation below any anchored sequence**
  (the event is gone), and a **rewrite at an anchored position**. Production mode
  requires a witness register.
- **Tail truncation after the last anchor is the irreducible residual.** Events
  appended *after the most recent anchor* and then dropped cannot be detected
  internally — no append-only log can prove the existence of events that were
  never witnessed. *Mitigation:* anchor cadence. Anchor frequently; for the
  strictest assurance, anchor on (or immediately after) every consequential
  append, so the witness always holds a checkpoint at or near the true head.
- **Torn tail on load.** A crash mid-append can leave a malformed trailing JSONL
  line. `_load` loads the valid prefix and sets a corrupt-tail flag; `verify()`
  returns `False` and `verify_strict()` raises rather than bricking on
  construction or silently certifying. A malformed *interior* line is treated as
  hard tamper and raises immediately.
- **The bundled witness is a reference.** `InMemoryWitnessRegister` is not
  durable and not external — it exists for tests. *Mitigation:* wire a real
  transparency log (OpenTimestamps / Rekor / a regulator-side log).
- **Concurrency.** Append/verify are serialized under a re-entrant lock within a
  process. Cross-process writers to the same JSONL log are the deployer's
  concern — wire a store that enforces single-writer or external locking.

## P4 — DEFCON state machine

- **Advisory de-escalation trusts `operator_id`.** With no Authorizer, a
  de-escalation requires only an `operator_id` string. *Mitigation:* `production`
  mode requires an authenticated, authorized, non-agent principal. Note that even
  in advisory mode, de-escalation is **one level at a time** and `evaluate()`
  never auto-de-escalates — a single call can never move `HALT → NORMAL`.
- **Thresholds are illustrative.** Uncalibrated thresholds will mis-classify
  risk. *Mitigation:* calibrate before relying on the machine.

## P5 — Effective-challenge harness

- **Independence is attested, not detected.** A false `IndependenceAttestation`
  (claiming independence where there is none) produces a rubber-stamp report.
  *Mitigation:* the attestation, the chooser, and the timestamp are recorded to
  the chain; a model owner who self-attests independence owns that record. Code
  still rejects literal self-challenge (`challenger == primary`), and an
  un-attested-independence challenge can never reach `ACCEPT_PRIMARY`.

## Adviser controls

- **Garbage in.** Every control acts on deployer-supplied structured inputs
  (factors, lists, arrangement attributes, ad attributes, fills, communications).
  Wrong inputs produce wrong findings. These controls surface and record; they do
  not independently verify the world.
- **A flag is a signal, not a verdict.** Allocation-fairness flags, off-channel
  flags, and custody exceptions are review triggers, not adjudications.
