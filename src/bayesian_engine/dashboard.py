"""Lightweight HTTP dashboard for reliability monitoring.

Implements issue #20: Optional Dashboard Visualization

Pure stdlib HTTP server (no Flask/FastAPI dependency) that displays:
- Reliability distribution across all sources
- Consensus statistics and recent history
- Source leaderboard sorted by reliability

Usage:
    bayesian-engine dashboard --db reliability.db --port 8080

Or programmatically:
    from bayesian_engine.dashboard import start_dashboard
    start_dashboard(db_path="reliability.db", port=8080)
"""

from __future__ import annotations

import json
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from bayesian_engine.reliability import SQLiteReliabilityStore


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bayesian Consensus Engine — Dashboard</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: #0d1117; color: #c9d1d9; padding: 2rem; }}
  h1 {{ color: #58a6ff; margin-bottom: 0.5rem; font-size: 1.5rem; }}
  h2 {{ color: #8b949e; margin: 1.5rem 0 0.75rem; font-size: 1.1rem; }}
  .subtitle {{ color: #8b949e; margin-bottom: 1.5rem; font-size: 0.85rem; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem; margin-bottom: 1.5rem; }}
  .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                padding: 1rem; }}
  .stat-label {{ color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  .stat-value {{ color: #58a6ff; font-size: 1.75rem; font-weight: 700; margin-top: 0.25rem; }}
  table {{ width: 100%; border-collapse: collapse; background: #161b22;
           border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }}
  th {{ background: #21262d; color: #8b949e; text-align: left; padding: 0.75rem 1rem;
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  td {{ padding: 0.6rem 1rem; border-top: 1px solid #21262d; font-size: 0.85rem; }}
  tr:hover {{ background: #1c2128; }}
  .bar {{ height: 8px; border-radius: 4px; background: #21262d; width: 100px; display: inline-block; }}
  .bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
  .high {{ background: #3fb950; }}
  .mid {{ background: #d29922; }}
  .low {{ background: #f85149; }}
  .refresh-note {{ color: #484f58; font-size: 0.7rem; margin-top: 1rem; }}
  a {{ color: #58a6ff; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>Bayesian Consensus Engine</h1>
<p class="subtitle">Reliability Dashboard &mdash; Auto-refreshes every 30s</p>

<div class="stats" id="stats"></div>

<h2>Source Reliability</h2>
<table>
<thead><tr><th>Source</th><th>Market</th><th>Reliability</th><th></th><th>Confidence</th><th>Last Updated</th></tr></thead>
<tbody id="sources"></tbody>
</table>

<p class="refresh-note">Last updated: <span id="ts"></span></p>

<script>
function reliabilityClass(r) {{
  if (r >= 0.7) return 'high';
  if (r >= 0.4) return 'mid';
  return 'low';
}}

function refresh() {{
  fetch('/api/data')
    .then(r => r.json())
    .then(d => {{
      // Stats cards
      const statsEl = document.getElementById('stats');
      statsEl.innerHTML = [
        ['Total Sources', d.total_sources],
        ['Markets Tracked', d.total_markets],
        ['Avg Reliability', d.avg_reliability.toFixed(3)],
        ['Avg Confidence', d.avg_confidence.toFixed(3)],
        ['Highest', d.highest_reliability ? d.highest_reliability.source_id : 'N/A'],
      ].map(([label, value]) =>
        '<div class="stat-card"><div class="stat-label">' + label +
        '</div><div class="stat-value">' + value + '</div></div>'
      ).join('');

      // Source table
      const tbody = document.getElementById('sources');
      tbody.innerHTML = d.sources.map(s => {{
        const cls = reliabilityClass(s.reliability);
        const pct = (s.reliability * 100).toFixed(0);
        return '<tr><td>' + s.source_id + '</td><td>' + s.market_id +
          '</td><td>' + s.reliability.toFixed(3) + '</td><td><div class="bar"><div class="bar-fill ' +
          cls + '" style="width:' + pct + '%"></div></div></td><td>' +
          s.confidence.toFixed(3) + '</td><td>' + (s.updated_at || 'Never') + '</td></tr>';
      }}).join('');

      document.getElementById('ts').textContent = new Date().toLocaleTimeString();
    }})
    .catch(err => console.error('Dashboard refresh failed:', err));
}}

refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>"""


def _get_dashboard_data(store: SQLiteReliabilityStore) -> dict[str, Any]:
    """Gather all data needed by the dashboard."""
    sources = store.list_sources()

    if not sources:
        return {
            "total_sources": 0,
            "total_markets": 0,
            "avg_reliability": 0.0,
            "avg_confidence": 0.0,
            "highest_reliability": None,
            "sources": [],
        }

    reliabilities = [s.reliability for s in sources]
    confidences = [s.confidence for s in sources]
    markets = set(s.market_id for s in sources)

    highest = max(sources, key=lambda s: s.reliability)

    return {
        "total_sources": len(sources),
        "total_markets": len(markets),
        "avg_reliability": sum(reliabilities) / len(reliabilities),
        "avg_confidence": sum(confidences) / len(confidences),
        "highest_reliability": {
            "source_id": highest.source_id,
            "reliability": highest.reliability,
        },
        "sources": [
            {
                "source_id": s.source_id,
                "market_id": s.market_id,
                "reliability": s.reliability,
                "confidence": s.confidence,
                "updated_at": s.updated_at,
            }
            for s in sorted(sources, key=lambda s: s.reliability, reverse=True)
        ],
    }


def _make_handler(db_path: str):
    """Create a request handler class bound to a specific DB path."""

    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)

            if parsed.path == "/" or parsed.path == "/dashboard":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(_DASHBOARD_HTML.encode("utf-8"))

            elif parsed.path == "/api/data":
                try:
                    with SQLiteReliabilityStore(db_path) as store:
                        data = _get_dashboard_data(store)
                    payload = json.dumps(data, indent=2)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(payload.encode("utf-8"))
                except Exception as exc:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    error = json.dumps({"error": str(exc)})
                    self.wfile.write(error.encode("utf-8"))

            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Not Found")

        def log_message(self, format, *args):
            # Suppress default request logging to stderr
            pass

    return DashboardHandler


def start_dashboard(db_path: str, port: int = 8080, open_browser: bool = False) -> None:
    """Start the dashboard HTTP server.

    Args:
        db_path: Path to the SQLite reliability database.
        port: Port to listen on (default 8080).
        open_browser: Whether to open the browser automatically.
    """
    handler = _make_handler(db_path)
    server = HTTPServer(("0.0.0.0", port), handler)
    url = f"http://localhost:{port}"

    print(f"Bayesian Engine Dashboard running at {url}")
    print(f"Database: {db_path}")
    print("Press Ctrl+C to stop")

    if open_browser:
        import webbrowser
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        server.server_close()
