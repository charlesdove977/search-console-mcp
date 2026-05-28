<div align="center">

![search-console-mcp banner](assets/banner.png)

# search-console-mcp

**A Model Context Protocol server that brings Google Search Console keyword and ranking data into Claude Code, Cursor, and any MCP-compatible AI tool.**

[![PyPI](https://img.shields.io/pypi/v/search-console-mcp?color=4f46e5)](https://pypi.org/project/search-console-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22d3ee.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-7c3aed.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-fff?logo=anthropic&logoColor=000)](https://modelcontextprotocol.io/)

</div>

---

## Why this exists

Google Analytics 4 strips organic search keywords. Ask your favorite AI assistant for "the keywords driving traffic to my site" and it will tell you the data is hidden as `(not provided)`. That is technically true for GA4. **It is not true for Search Console**, which exposes every query that earned an impression or click through a separate API.

This MCP server closes that gap. It plugs into your existing Google login and surfaces Search Console data through standard MCP tools, so AI tools can answer real keyword and ranking questions without screen-scraping or copy-paste.

It pairs naturally with **[Google's official `analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp)**. Use the two together for a full picture: GA4 for traffic and behavior, Search Console for keywords and rankings.

## What you can ask Claude

Once installed, ask in plain language:

- *"Show me my top organic search keywords last 30 days."*
- *"What's Google showing me for that I'm not getting clicks on?"*
- *"Which pages are getting traffic from Google search this month?"*
- *"What queries drove people to my /blog/ page?"*
- *"Where am I close to ranking on page 1?"*
- *"Give me a full SEO snapshot."*

The model picks the right tool from the seven below.

## Tools

| Tool | What it returns |
|------|-----------------|
| `list_sites` | Every Search Console property visible to the authenticated user |
| `top_queries_by_clicks` | Queries ranked by clicks. The truth about "what's actually driving traffic" |
| `top_queries_by_impressions` | Queries ranked by impressions. Surface ranking opportunities |
| `landing_pages_from_search` | Top pages receiving organic traffic |
| `queries_for_page` | All queries that drove clicks to a specific URL |
| `page_2_opportunities` | Queries ranking on positions 11-20. Closest-to-win SEO wins |
| `ctr_opportunities` | High-impression, low-CTR queries. Title and meta rewrites |
| `full_seo_report` | One-shot SEO snapshot combining all of the above |

Every tool accepts a `days` argument (default 30) and an optional `site` argument that overrides the `SC_SITE` env var.

## Install

```bash
pipx install search-console-mcp
```

That installs a `search-console-mcp` console script in a clean virtual environment. (If you don't have `pipx` yet, see [pipx.pypa.io](https://pipx.pypa.io/) — `brew install pipx` on macOS, then `pipx ensurepath`.)

## Setup (one time)

You need a Google account with Search Console access and the `gcloud` SDK installed.

### 1. Enable the Search Console API in a Google Cloud project

Open [console.cloud.google.com](https://console.cloud.google.com/) and either pick an existing project or create one. Then visit:

```
https://console.cloud.google.com/apis/library/searchconsole.googleapis.com
```

Click **Enable**.

### 2. Authenticate with Application Default Credentials

```bash
gcloud auth application-default login \
  --scopes=openid,\
https://www.googleapis.com/auth/userinfo.email,\
https://www.googleapis.com/auth/cloud-platform,\
https://www.googleapis.com/auth/webmasters.readonly
```

A browser window opens. Approve "View Search Console data for your verified sites." Done.

> **If you hit "this app is blocked"** for the default scopes, your account is constrained by Google's 2026 OAuth client policy. You will need to create a custom OAuth client in your own GCP project and pass `--client-id-file=path/to/client_secret.json` to the command above. Full walkthrough in [docs/SETUP.md](docs/SETUP.md).

### 3. Wire it into your AI tool

**Claude Code** — edit `.mcp.json` at the root of your project:

```json
{
  "mcpServers": {
    "search-console": {
      "type": "stdio",
      "command": "search-console-mcp",
      "env": {
        "SC_SITE": "sc-domain:yourdomain.com"
      }
    }
  }
}
```

`SC_SITE` formats:
- Domain property: `sc-domain:example.com`
- URL prefix: `https://www.example.com/`

You can omit `SC_SITE` and pass the `site` argument on each call instead.

**Cursor, Continue, other MCP hosts** — point them at the `search-console-mcp` executable using whatever config format they support. The protocol is standard MCP over stdio.

### 4. Restart your AI tool

That's it. Ask your model "show me my top search queries this month."

## Companion: pair with `analytics-mcp`

For full web-analytics coverage, install Google's official GA4 MCP alongside:

```bash
pipx install analytics-mcp
```

Then add to `.mcp.json`:

```json
{
  "mcpServers": {
    "search-console": {
      "type": "stdio",
      "command": "search-console-mcp",
      "env": { "SC_SITE": "sc-domain:yourdomain.com" }
    },
    "ga4": {
      "type": "stdio",
      "command": "analytics-mcp",
      "env": { "GOOGLE_PROJECT_ID": "your-gcp-project-id" }
    }
  }
}
```

Both share the same ADC, so the auth step above also covers GA4 once you add analytics scopes. Recommended scopes for the combined setup:

```
openid
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/cloud-platform
https://www.googleapis.com/auth/analytics
https://www.googleapis.com/auth/analytics.edit
https://www.googleapis.com/auth/analytics.readonly
https://www.googleapis.com/auth/webmasters.readonly
```

## Claude Code skills

This repo ships with one Claude Code skill in `skills/`:

- **`/seo-snapshot`** — one-command call to `full_seo_report`, then a plain-language read of the data plus three concrete recommendations. Drop the file into your `.claude/commands/` directory or use it as a template for your own skills.

## Verify it works

Quick smoke test:

```bash
python -c "
from search_console_mcp.server import list_sites, top_queries_by_clicks
print('sites:', list_sites())
print()
print('queries:', top_queries_by_clicks(days=30, limit=5, site='sc-domain:yourdomain.com'))
"
```

If you see your verified sites and your top queries, you're done.

## Troubleshooting

**`403 Request had insufficient authentication scopes`** — Your ADC token doesn't include `webmasters.readonly`. Rerun the `gcloud auth application-default login` command in step 2.

**`404 site not found`** — The site string doesn't match a property you own. Run `list_sites()` to see what's available.

**Empty results everywhere** — Search Console only shows queries with enough impressions to clear its anonymization threshold. Brand-new sites or sites with low organic traffic may legitimately return 0-2 rows. Try a longer `days` window.

**"This app is blocked" during login** — Google's 2026 OAuth policy. See the note in setup step 2.

## How it stays simple

This server is intentionally small. ~350 lines of Python, one dependency on the official MCP SDK, one dependency on `google-auth`, one on `google-api-python-client`. No state, no cache, no background workers. Every tool is a synchronous Search Console API call with structured JSON out. Easy to read, easy to fork, easy to extend.

## Contributing

Open an issue or PR. For meaningful additions, open the issue first so we can talk about shape. The tool surface is deliberately small; if a tool can be expressed as a parameter on an existing one, prefer that over adding a new tool.

## Built for the Claude Code community

Built by [Charles J Dove](https://charlieautomates.com) at [Charlie Automates](https://charlieautomates.com). Drop into the [Skool community](https://skool.com/charlieautomates) for setup help, or follow [@charlieautomates](https://youtube.com/@charlieautomates) on YouTube for more MCP and Claude Code builds.

## License

MIT. Do whatever you want with it. Attribution appreciated but not required.

## Related projects

- [Anthropic Model Context Protocol](https://modelcontextprotocol.io/) — the spec this server implements
- [Google `analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp) — companion GA4 MCP, recommended install alongside this one
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk) — the library this server is built on
- [Claude Code](https://www.anthropic.com/claude-code) — the primary AI host this was built and tested against
