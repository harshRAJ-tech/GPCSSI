# Security Policy and Scope

## Prototype scope: synthetic data only

This repository is a **demonstrator / prototype** for a Cyber Investigation
Intelligence Platform (CIIP). It is built and tested using **100% synthetic
data only**.

- It MUST NOT be loaded with real complaints, FIRs, bank records, or any
  personally identifiable information (PII) of real individuals.
- It is NOT certified for production law-enforcement use. Any such use would
  require formal security review, penetration testing, legal sign-off, and
  compliance assessment (e.g. the DPDP Act 2023, CCTNS norms, and digital
  evidence standards under the Bharatiya Sakshya Adhiniyam).

## Secure development principles applied

- **No secrets in source.** All secrets load from environment variables and
  the application fails closed if a required secret is missing.
- **Parameterized queries only.** No string-built SQL.
- **Audit logging and RBAC** are treated as MVP features, not afterthoughts.
- **Evidence integrity** via SHA-256 hashing of uploaded files.

## Reporting

This is a student prototype. Report security concerns via the project issue
tracker.
