"""Search Console MCP server.

Exposes Google Search Console query data as MCP tools. Pairs with the official
`analytics-mcp` (Google Analytics MCP) so AI tools can answer both
"where is my traffic coming from" AND "what are people searching to find me".

Auth: Application Default Credentials (ADC).
Required scope: https://www.googleapis.com/auth/webmasters.readonly

Default site is configured via the SC_SITE environment variable. If unset,
every tool requires an explicit `site` argument.
"""
import os
from datetime import date, timedelta

import google.auth
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

DEFAULT_SITE = os.environ.get("SC_SITE")
DATA_LAG_DAYS = 3  # Search Console data has a 2-3 day reporting lag

mcp = FastMCP("search-console")


def _resolve_site(site):
    resolved = site or DEFAULT_SITE
    if not resolved:
        raise ValueError(
            "No site specified. Either pass `site=...` or set SC_SITE env var "
            "(example: SC_SITE=sc-domain:example.com)."
        )
    return resolved


def _service():
    """Build a Search Console client using ADC."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def _date_range(days):
    end = date.today() - timedelta(days=DATA_LAG_DAYS)
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def _query(svc, site, dimensions, days, row_limit=25, dim_filter=None):
    start, end = _date_range(days)
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    if dim_filter:
        body["dimensionFilterGroups"] = [{"filters": [dim_filter]}]
    return svc.searchanalytics().query(siteUrl=site, body=body).execute().get("rows", [])


@mcp.tool()
def list_sites() -> dict:
    """List all Search Console properties visible to the authenticated user.

    Use this to discover what `site` values are valid for other tools.
    Returns each site's URL and the user's permission level.
    """
    svc = _service()
    entries = svc.sites().list().execute().get("siteEntry", [])
    return {
        "sites": [
            {"siteUrl": s.get("siteUrl"), "permissionLevel": s.get("permissionLevel")}
            for s in entries
        ],
        "default_site": DEFAULT_SITE,
    }


@mcp.tool()
def top_queries_by_clicks(days: int = 30, limit: int = 25, site: str = None) -> dict:
    """Top search queries ranked by CLICKS over the last N days.

    Use this for "what searches are actually sending people to my site".
    Returns each query with clicks, impressions, click-through rate, and
    average Google ranking position.

    Args:
        days: Lookback window in days (default 30).
        limit: Max queries to return (default 25).
        site: Search Console site URL. Defaults to SC_SITE env var.
    """
    site = _resolve_site(site)
    rows = _query(_service(), site, ["query"], days, limit)
    return {
        "site": site,
        "window_days": days,
        "data_lag_days": DATA_LAG_DAYS,
        "rows": [
            {
                "query": r["keys"][0],
                "clicks": int(r["clicks"]),
                "impressions": int(r["impressions"]),
                "ctr": round(r["ctr"], 4),
                "position": round(r["position"], 1),
            }
            for r in rows
        ],
        "row_count": len(rows),
    }


@mcp.tool()
def top_queries_by_impressions(days: int = 30, limit: int = 25, site: str = None) -> dict:
    """Top queries ranked by IMPRESSIONS (Google show-ups, click or not).

    Use this to find ranking opportunities: queries Google is willing to
    surface you for but where you don't yet earn the click.

    Args:
        days: Lookback window in days (default 30).
        limit: Max queries to return (default 25).
        site: Search Console site URL.
    """
    site = _resolve_site(site)
    rows = _query(_service(), site, ["query"], days, max(limit * 4, 100))
    rows.sort(key=lambda r: r["impressions"], reverse=True)
    rows = rows[:limit]
    return {
        "site": site,
        "window_days": days,
        "rows": [
            {
                "query": r["keys"][0],
                "impressions": int(r["impressions"]),
                "clicks": int(r["clicks"]),
                "ctr": round(r["ctr"], 4),
                "position": round(r["position"], 1),
            }
            for r in rows
        ],
        "row_count": len(rows),
    }


@mcp.tool()
def landing_pages_from_search(days: int = 30, limit: int = 20, site: str = None) -> dict:
    """Top landing pages by organic search clicks over the last N days.

    Tells you WHICH pages on your site are getting traffic from Google.
    Pair with `queries_for_page` to drill into what queries drove each page.

    Args:
        days: Lookback window in days (default 30).
        limit: Max pages to return (default 20).
        site: Search Console site URL.
    """
    site = _resolve_site(site)
    rows = _query(_service(), site, ["page"], days, limit)
    rows.sort(key=lambda r: r["clicks"], reverse=True)
    return {
        "site": site,
        "window_days": days,
        "rows": [
            {
                "page": r["keys"][0],
                "clicks": int(r["clicks"]),
                "impressions": int(r["impressions"]),
                "ctr": round(r["ctr"], 4),
                "position": round(r["position"], 1),
            }
            for r in rows
        ],
        "row_count": len(rows),
    }


@mcp.tool()
def queries_for_page(page_url: str, days: int = 30, limit: int = 25,
                     site: str = None) -> dict:
    """All search queries that drove organic clicks to a SPECIFIC page.

    Use this when you want to know "what are people searching to find
    /some-specific-url". The page_url must match the URL Search Console
    indexed (typically the full https://... form).

    Args:
        page_url: Exact page URL to filter on.
        days: Lookback window in days (default 30).
        limit: Max queries to return (default 25).
        site: Search Console site URL.
    """
    site = _resolve_site(site)
    rows = _query(
        _service(),
        site,
        ["query"],
        days,
        limit,
        dim_filter={"dimension": "page", "operator": "equals", "expression": page_url},
    )
    return {
        "site": site,
        "page": page_url,
        "window_days": days,
        "rows": [
            {
                "query": r["keys"][0],
                "clicks": int(r["clicks"]),
                "impressions": int(r["impressions"]),
                "ctr": round(r["ctr"], 4),
                "position": round(r["position"], 1),
            }
            for r in rows
        ],
        "row_count": len(rows),
    }


@mcp.tool()
def page_2_opportunities(days: int = 30, limit: int = 15, site: str = None) -> dict:
    """Queries ranking on positions 11-20 (Google's page 2).

    These are your CLOSEST-TO-WIN searches: already visible to Google but
    not yet on page 1. Pushing them to positions 1-10 is the highest-ROI
    SEO work because the ranking work is mostly done.

    Args:
        days: Lookback window in days (default 30).
        limit: Max queries to return (default 15).
        site: Search Console site URL.
    """
    site = _resolve_site(site)
    rows = _query(_service(), site, ["query"], days, row_limit=500)
    p2 = [r for r in rows if 11 <= r["position"] <= 20]
    p2.sort(key=lambda r: r["impressions"], reverse=True)
    p2 = p2[:limit]
    return {
        "site": site,
        "window_days": days,
        "rows": [
            {
                "query": r["keys"][0],
                "impressions": int(r["impressions"]),
                "clicks": int(r["clicks"]),
                "ctr": round(r["ctr"], 4),
                "position": round(r["position"], 1),
            }
            for r in p2
        ],
        "row_count": len(p2),
    }


@mcp.tool()
def ctr_opportunities(days: int = 30, min_impressions: int = 10,
                      ctr_below: float = 0.05, max_position: float = 15.0,
                      limit: int = 15, site: str = None) -> dict:
    """Queries with strong impressions but unusually low click-through rate.

    These are pages where Google ranks you well but your title and meta
    description aren't earning the click. Rewriting the title is often the
    fastest SEO win.

    Args:
        days: Lookback window in days (default 30).
        min_impressions: Minimum impressions to consider (default 10).
        ctr_below: CTR threshold below which counts as an opportunity (default 0.05 = 5%).
        max_position: Only include queries ranked at or above this position (default 15).
        limit: Max queries to return (default 15).
        site: Search Console site URL.
    """
    site = _resolve_site(site)
    rows = _query(_service(), site, ["query"], days, row_limit=500)
    opps = [
        r for r in rows
        if r["impressions"] >= min_impressions
        and r["ctr"] < ctr_below
        and r["position"] <= max_position
    ]
    opps.sort(key=lambda r: r["impressions"], reverse=True)
    opps = opps[:limit]
    return {
        "site": site,
        "window_days": days,
        "criteria": {
            "min_impressions": min_impressions,
            "ctr_below": ctr_below,
            "max_position": max_position,
        },
        "rows": [
            {
                "query": r["keys"][0],
                "impressions": int(r["impressions"]),
                "clicks": int(r["clicks"]),
                "ctr": round(r["ctr"], 4),
                "position": round(r["position"], 1),
            }
            for r in opps
        ],
        "row_count": len(opps),
    }


@mcp.tool()
def full_seo_report(days: int = 30, site: str = None) -> dict:
    """One-shot SEO snapshot: queries, pages, page-2 opportunities, CTR opps, totals.

    Returns everything you would need for "give me my SEO snapshot" in a
    single tool call. Use this as the default when a user asks for an SEO
    read.

    Args:
        days: Lookback window in days (default 30).
        site: Search Console site URL.
    """
    site = _resolve_site(site)
    svc = _service()
    all_q = _query(svc, site, ["query"], days, row_limit=500)
    pages = _query(svc, site, ["page"], days, 20)
    pages.sort(key=lambda r: r["clicks"], reverse=True)
    p2 = [r for r in all_q if 11 <= r["position"] <= 20]
    p2.sort(key=lambda r: r["impressions"], reverse=True)
    opps = [
        r for r in all_q
        if r["impressions"] >= 10 and r["ctr"] < 0.05 and r["position"] <= 15
    ]
    opps.sort(key=lambda r: r["impressions"], reverse=True)
    total_clicks = sum(int(r["clicks"]) for r in all_q)
    total_imps = sum(int(r["impressions"]) for r in all_q)

    def _q(r):
        return {
            "query": r["keys"][0], "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"], 4), "position": round(r["position"], 1),
        }

    def _p(r):
        return {
            "page": r["keys"][0], "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"], 4), "position": round(r["position"], 1),
        }

    return {
        "site": site,
        "window_days": days,
        "totals": {
            "clicks": total_clicks,
            "impressions": total_imps,
            "avg_ctr": round(total_clicks / total_imps, 4) if total_imps else 0,
            "queries_returned": len(all_q),
        },
        "top_queries_by_clicks": [_q(r) for r in sorted(all_q, key=lambda r: r["clicks"], reverse=True)[:15]],
        "top_queries_by_impressions": [_q(r) for r in sorted(all_q, key=lambda r: r["impressions"], reverse=True)[:15]],
        "top_landing_pages": [_p(r) for r in pages[:15]],
        "page_2_opportunities": [_q(r) for r in p2[:15]],
        "ctr_opportunities": [_q(r) for r in opps[:15]],
    }


def main():
    """Entry point used by the `search-console-mcp` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
