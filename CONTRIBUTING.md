# Contributing

Thanks for helping build the Requirements Discovery Copilot. This guide covers
the conventions that keep the monorepo maintainable.

## Ground rules

- **No business logic in UI components.** Derivation, coverage, and lifecycle
  logic live in `apps/api/app/services` (or shared, pure helpers in
  `packages/domain`). Components render state and dispatch intents.
- **No provider-specific logic in domain entities.** STT/LLM/embedding/export
  concerns go behind the interfaces in `apps/api/app/providers`.
- **Evidence-first.** Any new artifact-producing code path must attach at least
  one `EvidenceLink` (or explicitly mark the artifact `detected`/`inferred`
  with no confirmation).
- **Human validation before baselining.** Never set `validation_state` to
  `customer_confirmed`/`baselined` from an automated path.
- **No secrets in the repo.** Configuration is environment-driven.

## Development setup

```bash
cp .env.example .env
make api-install web-install
make migrate seed
make api      # terminal 1
make web      # terminal 2
```

## Code quality gates

| Area | Tooling |
|------|---------|
| Python | `ruff` (lint + format), `mypy` (strict-ish), `pytest` |
| TypeScript | `eslint`, `prettier`, `tsc --noEmit` (strict), `vitest` |
| Hooks | `pre-commit` (see `.pre-commit-config.yaml`) |

Run everything before pushing:

```bash
make format lint test
```

Install the git hooks once:

```bash
pip install pre-commit && pre-commit install
```

## Branching & commits

- Work on feature branches; keep commits focused with descriptive messages.
- Add or update tests with every behavior change.
- Update the relevant doc (ADR for architectural decisions, domain glossary for
  new entities, `docs/api` for endpoint changes).

## Tests

- Backend: `cd apps/api && pytest`. Add unit tests next to the layer you change
  (domain / services / api) and keep the e2e scenario green.
- Frontend: `cd apps/web && npm test`. Component + state tests use Vitest +
  Testing Library.

## Architecture decisions

Non-trivial structural choices get an ADR in `docs/adr` (copy `0001` as a
template, increment the number, link it from the ADR index).
