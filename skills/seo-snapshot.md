---
name: seo-snapshot
description: Pull a one-shot SEO snapshot from Google Search Console for your default site. Use when the user asks "how is my SEO", "what are my top keywords", "what's working in search", or any organic-search performance question.
---

# /seo-snapshot

Pulls a full Search Console snapshot using the `search-console` MCP server.

## What it does

1. Calls `mcp__search-console__full_seo_report(days=30)` to get one-shot SEO data
2. Surfaces five sections in plain language:
   - 30-day totals (clicks, impressions, avg CTR)
   - Top queries by clicks (what's actually driving traffic)
   - Top queries by impressions (what Google shows you for)
   - Top landing pages from organic search
   - Page-2 opportunities (positions 11-20, closest to wins)
   - CTR opportunities (good rank, weak click-through)
3. Ends with 3 specific recommendations the user can act on this week

## Usage

```
/seo-snapshot
```

Or with a different window:

```
/seo-snapshot 90
```

## Output style

Plain language, ninth-grade reading level by default. Numbers come first.
Recommendations are concrete (page URL, suggested action), not vague.

## Requirements

- `search-console` MCP server installed and registered in `.mcp.json`
- ADC authenticated with `webmasters.readonly` scope
- `SC_SITE` environment variable set in the MCP server config, or pass `site=...`

## When to skip

Skip if the user is asking about traffic that did not come from Google search
(direct, social, email, paid). Those answers live in `analytics-mcp` (GA4), not
Search Console.
