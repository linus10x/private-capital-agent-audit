# Security policy

## Reporting a vulnerability

Report suspected vulnerabilities privately via GitHub Security Advisories on this
repository, or by email to the maintainer listed in `CITATION.cff`. Please do not
open a public issue for a security report. Include a reproduction, the affected
version, and the impact you observed. We aim to acknowledge within a few business
days.

## Scope

This is a stdlib-only, zero-runtime-dependency Python library. The security
surface of interest:

- **Tamper-evidence claims of the audit chain.** Reports that a tampered or
  spliced chain passes `verify()` / `verify_strict()` within the trust boundary,
  or that a regenerated chain passes `verify_regeneration_resistant()` despite an
  anchored head, are in scope. Note the documented boundary: the chain is
  internally consistent, not adversarially tamper-proof without an external
  witness (see `FAILURE-MODES.md`).
- **Fail-closed contracts.** Reports that `production` mode can be constructed or
  bypassed without its required Authorizer / attestation verifier / witness
  register are in scope.
- **Self-clear / self-challenge / illegal-transition bypasses.** Reports that an
  agent can clear its own veto, a model can self-validate to `ACCEPT_PRIMARY`, or
  a single call can move `HALT → NORMAL` are in scope.

## Out of scope

- Misuse of advisory mode (it is documented as not fail-closed).
- Wrong findings from wrong deployer-supplied inputs (the controls record and
  surface; they do not independently verify the world).
- The reference `InMemoryWitnessRegister` not being durable or external — it is
  documented as a test reference.
