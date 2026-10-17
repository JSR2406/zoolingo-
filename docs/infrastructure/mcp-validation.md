# MCP Validation Report

Validated: 2026-09-08 · OpenCode `1.18.29` · Node `v24.14.1` · Windows

Commands used:

- `opencode mcp list` — start local servers, connect to remotes, report status
- `opencode mcp debug <name>` — test OAuth discovery (DCR) without completing authorization
- `npm view <pkg>` — confirm official package existence/versions before wiring

## Status

| MCP | Status | Evidence |
| --- | ------ | -------- |
| GitHub | PASS | `connected` (`https://api.githubcopilot.com/mcp/`) after `GITHUB_PAT` was registered as a user-level env var. |
| Filesystem | PASS | `connected` via `npx --no-install @modelcontextprotocol/server-filesystem .` — pinned `2026.8.31`. |
| Context7 | PASS | `connected` (`https://mcp.context7.com/mcp`). |
| Playwright | PASS | `connected` via `npx --no-install @playwright/mcp` (pinned `0.0.80`). Requires `npx playwright install chromium` before browser use. |
| Sequential Thinking | PASS | `connected` via pinned reference server `2026.8.31`. |
| Fetch / Web (Browser Run) | PASS | `connected` (`https://browser.mcp.cloudflare.com/mcp`) after `opencode mcp auth fetch`. |
| Vercel | PASS | `connected` (`https://mcp.vercel.com`) after `opencode mcp auth vercel`. OAuth-only — a Vercel PAT is not accepted as a Bearer header. |
| Cloudflare | PASS | `connected` (`https://mcp.cloudflare.com/mcp`) after `opencode mcp auth cloudflare`. |
| Supabase | PASS | `connected` (global config, existing project). |
| Vector DB | MAPPED | Supabase pgvector via `supabase` / Cloudflare Vectorize via `cloudflare`. No standalone server. |
| Observability (Sentry) | NEEDS-OAUTH | DCR verified; flow starts but browser authorization not completed. Run `opencode mcp auth sentry`. |
| Image Search | NOT CONFIGURED | No verified server with available credentials (Getty requires enterprise API key). |
| Writing / Documentation | MAPPED | Skills + built-in tools. |
| Model Context Docs | MAPPED | Context7. |
| Web Research / Scraping | MAPPED | `fetch` (Browser Run). |

## Definition of PASS

For every PASS entry the following were confirmed: configuration exists, server
starts/connects, tools are discoverable (server handshake completed), no secrets
stored, and at least a handshake-level read is possible. Authentication-based
servers cannot be marked PASS until the user completes the applicable auth step
above — an authenticated server that has never authorized is reported as
`NEEDS-OAUTH` / `NEEDS-ENV`, never as PASS.

## Required manual actions (blocking)

```text
1. opencode mcp auth sentry     (only if Sentry is the chosen observability provider)
2. npx playwright install chromium   (once, for browser automation)
```

`GITHUB_PAT` is set (user scope) and Vercel/Cloudflare/Fetch OAuth are complete; re-run `opencode mcp list` after the remaining steps.

## Notes

- OAuth tokens are stored by OpenCode in `~/.local/share/opencode/mcp-auth.json`; never commit this file.
- `github` is the only server that hard-disables OAuth (`oauth: false`) because GitHub's authorization server does not support Dynamic Client Registration.