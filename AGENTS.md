# AGENTS.md

Engineering ground rules for AI agents working in this repository. Read this
before any substantial implementation work.

## Inspect before acting

- Read `docs/infrastructure/mcp-registry.md` and `docs/infrastructure/mcp-validation.md` before using MCP servers.
- Check `opencode.json` and `package.json` before assuming which tools/servers exist.
- Verify framework/library APIs against `context7` current docs before implementing version-sensitive code; do not rely on model memory for unfamiliar APIs.

## MCP usage rules

- Use MCP servers only when relevant; every MCP tool consumes model context.
- Prefer the specialized pair: focused agent + focused MCP + focused skill. Do not hand every agent every MCP.
- `sequential-thinking` is for architecture decisions, hard debugging, multi-step planning — not trivial requests.
- `fetch` (Browser Run) and `playwright` are for web/browser work; prefer official documentation sources.
- `filesystem` scopes to the workspace root. External directory access requires explicit approval. Never read `~/.ssh`, `~/.aws`, `~/.config`, or credential stores.
- **Never print or log secrets**: API keys, tokens, passwords, private keys, OAuth values. Inspect variable *names* only.
- `opencode mcp list` reports real connectivity; do not claim a server works if it shows `failed` or `needs authentication`.

## Security classification

| Operation | Policy |
| --------- | ------ |
| READ | allow |
| WRITE (code, files) | allow within rules above |
| WRITE (remote: deploy, env vars) | ask |
| DESTRUCTIVE (delete, merge, destructive SQL, rotate secrets) | deny unless explicitly approved by the user |
| SECRET | deny |

- Never: auto-merge production PRs, delete Vercel projects/deployments, run destructive SQL against production, delete Cloudflare resources, expose environment secrets.
- Schema change loop: inspect → propose migration → review → execute → verify. Use RLS where applicable.
- Production deploys: test → build → review → preview → verify → approval → production → smoke test.

## Delegation model

Primary agent plans, then delegates to specialized subagents instead of doing everything itself:

```
USER → BUILD → ARCHITECT → FRONTEND/BACKEND → AI ENGINEER/DATABASE → QA → SECURITY → REVIEWER → DEVOPS
```

Spawn only the agents needed; give each a single clear responsibility; never duplicate work across agents.

## Definition of done

- Implementation follows the repository's language/framework conventions.
- Relevant tests written and passing; critical user journeys have E2E coverage (Playwright).
- Lint + typecheck + build pass.
- No secrets added; `.gitignore` covers all new artifact paths.
- Docs updated (API, schema, architecture) to stay in sync with code.

## Versions (verified 2026-09-08)

- OpenCode 1.18.29, Node 24, npm 11, pnpm 11.5, yarn 1.22, Python 3.11, Docker 29.
- Pinned local MCP servers in `package.json`; run `npm install` after cloning before using `filesystem`, `sequential-thinking`, or `playwright`.