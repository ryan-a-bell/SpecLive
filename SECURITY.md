# Security & Privacy

Discovery transcripts routinely contain sensitive customer information. This
document describes the security and privacy **architecture placeholders** for
the project.

> **No compliance claims.** Nothing here asserts conformance to SOC 2, ISO
> 27001, GDPR, HIPAA, or any other standard. Controls are documented as design
> intent and are only partially implemented in this increment. Do not represent
> the system as compliant unless a control has been implemented **and verified**.

## Reporting a vulnerability

Please open a private security advisory or email the maintainers rather than
filing a public issue. Include reproduction steps and affected components.

## Data classification

| Class | Examples | Handling intent |
|-------|----------|-----------------|
| Public | Product docs, ADRs | No restriction |
| Internal | Discovery scripts, coverage state | Access-controlled |
| Confidential | Transcript text, customer names, derived requirements | Encrypted at rest + in transit, redaction-eligible |
| Restricted | Provider credentials | Never persisted in app DB; env/secret store only |

## Control placeholders

Each item below is a **designed** control with its current status.

| Control | Design | Status in this increment |
|---------|--------|--------------------------|
| Data retention | `TRANSCRIPT_RETENTION_DAYS`; scheduled purge job | Config present; purge job not implemented |
| Transcript redaction | `ENABLE_TRANSCRIPT_REDACTION`; PII redaction pass before persistence | Flag present; redaction pass not implemented |
| Encryption at rest | DB-level / disk encryption; column encryption for confidential fields | Deployment concern; not enforced by app |
| Encryption in transit | TLS termination at the edge; `wss://`/`https://` in prod | Documented; local dev uses plain HTTP/WS |
| Role-based access control | `facilitator` / `reviewer` / `viewer` roles gate mutations | Modeled in `SECURITY.md` + placeholders; not enforced |
| Audit logging | Append-only log of confirm/reject/edit/export actions | `ArtifactRevision` captures edits; dedicated audit log pending |
| Provider data boundaries | Per-provider allow-list of what may leave the trust boundary; mock providers never egress | Mock providers only; boundary policy documented |
| Local-only deployment | Full stack runs offline with mock providers | Supported (`make up`, no external calls) |
| Sensitive-data classification | Field-level classification drives redaction/export rules | Table above; not yet enforced in code |

## Secrets handling

- Secrets are **never** committed. `.env` is git-ignored; `.env.example`
  contains only placeholders.
- Provider credentials are read from environment variables at runtime and are
  never written to the application database or logs.
- Structured logs redact known credential-shaped values by key name.

## Provider trust boundary

The provider abstraction (`SpeechToTextProvider`, `LanguageModelProvider`,
`EmbeddingProvider`) is the single egress point for customer data. In this
increment all providers are **mock/in-process** and perform **no network
egress**. When a real provider is added, it must:

1. Declare the data classes it transmits.
2. Be gated by an explicit configuration allow-list.
3. Support a "local-only" mode that disables it.
