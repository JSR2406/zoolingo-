# MCP Registry

Status of every MCP-integrated capability for this project's OpenCode setup.
All server definitions live in `opencode.json` (project root). Global additions
(only `supabase` today) live in `~/.config/opencode/opencode.json`.

Legend — Validation status:

- `PASS`        — configured and OpenCode reports `connected`
- `NEEDS-OAUTH` — configured, OAuth discovery verified (`opencode mcp debug`), user authorization pending
- `NEEDS-ENV`   — configured, requires an environment variable the user must provide
- `MAPPED`      — requested capability intentionally served by another configured server
- `NOT-CONFIGURED` — no verified official server available; do not fabricate config

## Configured servers

| MCP | Purpose | Provider | Type | Auth | Env vars | Agents (planned) | R/W | Production risk | Validation | Fallback | Official reference |
| --- | ------- | -------- | ---- | ---- | -------- | ---------------- | --- | --------------- | ---------- | -------- | ------------------ |
| `github` | repos, branches, commits, issues, PRs, review | GitHub (hosted `github/github-mcp-server`) | remote `https://api.githubcopilot.com/mcp/` | PAT via `Authorization: Bearer` (OAuth auto-disabled: GitHub does **not** support DCR) | `GITHUB_PAT` (repo, workflow, read:org) | architect, backend, devops, reviewer | read/write | HIGH — can mutate repos; never merge/delete without approval | `NEEDS-ENV` | Local Docker server `ghcr.io/github/github-mcp-server` | https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-opencode.md |
| `filesystem` | read/write project files, inspect code | MCP reference server | local stdio (`npx --no-install @modelcontextprotocol/server-filesystem .`) | none | none | all agents | read/write, scoped to workspace | MEDIUM — directory traversal outside allowed roots blocked by server | `PASS` | OpenCode built-in edit/read/grep/glob tools | https://github.com/modelcontextprotocol/servers |
| `context7` | up-to-date library/framework docs | Upstash | remote `https://mcp.context7.com/mcp` | none (optional API key) | `CONTEXT7_API_KEY` (optional, higher rate limits) | architect, frontend, backend, ai-engineer, database | read | LOW | `PASS` | `fetch` (official docs) | https://mcp.context7.com |
| `playwright` | browser automation, E2E, screenshots, resp. tests | Microsoft | local stdio (`npx --no-install @playwright/mcp`) | none | none (browsers: `npx playwright install chromium`) | frontend, qa, designer, reviewer | read/write (browser state) | LOW | `PASS` | `fetch` for DOM-only reads | https://github.com/microsoft/playwright-mcp |
| `sequential-thinking` | architecture, debugging, multi-step planning | MCP reference server | local stdio | none | none | architect, backend, ai-engineer, database, security | read | LOW | `PASS` | — | https://github.com/modelcontextprotocol/servers |
| `fetch` | web fetching → markdown, screenshots (web research/scraping) | Cloudflare (Browser Run) | remote `https://browser.mcp.cloudflare.com/mcp` | OAuth (DCR verified) | none | researcher, architect, frontend, security | read | LOW | `NEEDS-OAUTH` | OpenCode docs / official sites | https://github.com/cloudflare/mcp-server-cloudflare/tree/main/apps/browser-rendering |
| `vercel` | deployments, env, logs, domains, project metadata | Vercel | remote `https://mcp.vercel.com` | OAuth (DCR verified) | none | devops, architect, reviewer | read/write/deploy | HIGH — deploys & production changes | `NEEDS-OAUTH` | `vercel` CLI | https://vercel.com/docs/agent-resources/vercel-mcp |
| `cloudflare` | Workers, Pages, DNS, KV, R2, D1, Vectorize, AI Gateway | Cloudflare (Code Mode) | remote `https://mcp.cloudflare.com/mcp` | OAuth (DCR verified) | none | devops, backend, database | read/write | HIGH — full Cloudflare API surface | `NEEDS-OAUTH` | `wrangler` CLI | https://github.com/cloudflare/mcp |
| `supabase` | SQL, schema, migrations, auth, storage, edge functions, RLS | Supabase | remote `https://mcp.supabase.com/mcp?project_ref=…&features=…` (global config) | OAuth (already connected) | none | database, backend, architect | read/write | HIGH — SQL against project DB; destructive SQL must be gated | `PASS` | `supabase` CLI | https://supabase.com/docs/guides/dev-sdks/mcp |
| `sentry` | errors, traces, performance, incidents (observability) | Sentry | remote `https://mcp.sentry.dev/mcp` | OAuth (DCR verified) | none | devops, backend, qa, ai-engineer | read (no prod mutation) | LOW-MEDIUM | `NEEDS-OAUTH` | Sentry web UI | https://mcp.sentry.dev |

## Requested capabilities — resolved without a duplicate/unverifiable server

| Requested capability | Resolution | Rationale |
| -------------------- | ---------- | --------- |
| Fetch / Web  | `fetch` (Cloudflare Browser Run) | Official fetch server; `@modelcontextprotocol/server-fetch` has been removed from npm (verified 404). |
| Web research / scraping | `fetch` (Browser Run) | Browser Run converts pages to markdown + screenshots; covers research market. Firecrawl (`mcp.firecrawl.dev/mcp`) is an optional upgrade requiring `FIRECRAWL_API_KEY` — not enabled. |
| Model context documentation (OpenAI/Anthropic/Gemini/MCP) | `context7` | Context7 indexes current docs for these libraries; no separate official server exists. |
| Vector database | Supabase `pgvector` via `supabase`, and Cloudflare `Vectorize` via `cloudflare` | No standalone vector DB delegated by this project. Embedding model / dims / distance to be decided when vector features are built. |
| Image search | **NOT-CONFIGURED** | Only verified official server is Getty Images (`https://mcp.gettyimages.com/v1`, enterprise API key + secret, OAuth client-credentials). No credentials available → deliberately not configured. Unsplash `unsplash-mcp` is community (Bun), not official. |
| Writing / documentation | **MAPPED** | No official MCP; handled by project skills + built-in file tools. |
| Observability | `sentry` | Canonical, documented in OpenCode docs; enable after provider selection. |

## Degraded / follow-up notes

- `@modelcontextprotocol/server-fetch` is unpublished; the old stdio fetch entry has been removed from config.
- Local reference servers (`filesystem`, `sequential-thinking`) are installed **and pinned** in `package.json` (calver `2026.8.31`) and launched with `npx --no-install` for reproducibility.
- `github` cannot use OAuth automatically — GitHub's auth server does not support Dynamic Client Registration (open GitHub issue), so a PAT is required and OAuth is hard-disabled (`"oauth": false`).