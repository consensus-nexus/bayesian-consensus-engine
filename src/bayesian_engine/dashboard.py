"""Optional dashboard visualization for Bayesian Consensus Engine.

This module provides a simple web-based dashboard for visualizing
reliability scores, consensus history, and source performance.

Usage:
    from bayesian_engine.dashboard import DashboardServer
    
    # Start dashboard
    server = DashboardServer(reliability_store, port=8080)
    server.start()
    
    # Or via CLI:
    # bayesian-engine --dashboard --port 8080

The dashboard is optional and requires extra dependencies:
    pip install bayesian-consensus-engine[dashboard]
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from bayesian_engine.reliability import SQLiteReliabilityStore


class DashboardData:
    """Data provider for dashboard."""
    
    def __init__(self, reliability_store: SQLiteReliabilityStore):
        self._store = reliability_store
    
    def get_sources(self) -> List[Dict[str, Any]]:
        """Get all sources with reliability data."""
        records = self._store.list_sources()
        return [
            {
                "sourceId": r.source_id,
                "marketId": r.market_id,
                "reliability": round(r.reliability, 4),
                "confidence": round(r.confidence, 4),
                "updatedAt": r.updated_at,
            }
            for r in records
        ]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        sources = self._store.list_sources()
        
        if not sources:
            return {
                "totalSources": 0,
                "avgReliability": 0,
                "avgConfidence": 0,
                "highReliabilityCount": 0,
            }
        
        reliabilities = [s.reliability for s in sources]
        confidences = [s.confidence for s in sources]
        
        return {
            "totalSources": len(sources),
            "avgReliability": round(sum(reliabilities) / len(reliabilities), 4),
            "avgConfidence": round(sum(confidences) / len(confidences), 4),
            "highReliabilityCount": sum(1 for r in reliabilities if r >= 0.7),
        }
    
    def get_reliability_distribution(self) -> Dict[str, int]:
        """Get reliability distribution buckets."""
        sources = self._store.list_sources()
        
        buckets = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0,
        }
        
        for s in sources:
            if s.reliability < 0.2:
                buckets["0.0-0.2"] += 1
            elif s.reliability < 0.4:
                buckets["0.2-0.4"] += 1
            elif s.reliability < 0.6:
                buckets["0.4-0.6"] += 1
            elif s.reliability < 0.8:
                buckets["0.6-0.8"] += 1
            else:
                buckets["0.8-1.0"] += 1
        
        return buckets


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for dashboard."""
    
    data_provider: DashboardData = None
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/" or path == "/index.html":
            self._serve_html()
        elif path == "/api/sources":
            self._serve_json(self.data_provider.get_sources())
        elif path == "/api/summary":
            self._serve_json(self.data_provider.get_summary())
        elif path == "/api/distribution":
            self._serve_json(self.data_provider.get_reliability_distribution())
        else:
            self.send_error(404, "Not Found")
    
    def _serve_html(self):
        """Serve the dashboard HTML."""
        html = self._get_dashboard_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def _serve_json(self, data: Any):
        """Serve JSON data."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bayesian Consensus Engine Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { margin-bottom: 20px; color: #00d9ff; }
        h2 { margin: 20px 0 10px; color: #00d9ff; font-size: 1.2em; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        
        .card {
            background: #16213e;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .stat { text-align: center; padding: 10px; }
        .stat-value { font-size: 2em; font-weight: bold; color: #00d9ff; }
        .stat-label { color: #888; font-size: 0.9em; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #333; }
        th { color: #00d9ff; font-weight: 500; }
        
        .reliability-bar {
            height: 8px;
            background: #333;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }
        .reliability-fill {
            height: 100%;
            background: linear-gradient(90deg, #ff6b6b, #ffd93d, #6bcb77);
            transition: width 0.3s;
        }
        
        .distribution-bar {
            display: flex;
            align-items: center;
            margin: 5px 0;
        }
        .distribution-label { width: 80px; color: #888; }
        .distribution-fill {
            flex: 1;
            height: 20px;
            background: #00d9ff;
            margin: 0 10px;
            border-radius: 4px;
            min-width: 2px;
        }
        .distribution-count { width: 40px; text-align: right; }
        
        .refresh-btn {
            background: #00d9ff;
            color: #1a1a2e;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        .refresh-btn:hover { background: #00b8d9; }
        
        .updated { color: #888; font-size: 0.8em; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🦞 Bayesian Consensus Engine</h1>
        
        <div class="grid">
            <div class="card">
                <h2>Summary</h2>
                <div id="summary" class="grid">
                    <div class="stat">
                        <div class="stat-value" id="total-sources">-</div>
                        <div class="stat-label">Total Sources</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="avg-reliability">-</div>
                        <div class="stat-label">Avg Reliability</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="avg-confidence">-</div>
                        <div class="stat-label">Avg Confidence</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="high-reliability">-</div>
                        <div class="stat-label">High Reliability (&gt;70%)</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>Reliability Distribution</h2>
                <div id="distribution"></div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h2>Sources</h2>
            <table id="sources-table">
                <thead>
                    <tr>
                        <th>Source ID</th>
                        <th>Market</th>
                        <th>Reliability</th>
                        <th>Confidence</th>
                        <th>Updated</th>
                    </tr>
                </thead>
                <tbody id="sources-body"></tbody>
            </table>
        </div>
        
        <button class="refresh-btn" onclick="refreshData()">Refresh</button>
        <div class="updated" id="updated-at">Last updated: -</div>
    </div>
    
    <script>
        async function fetchAPI(endpoint) {
            const response = await fetch(endpoint);
            return response.json();
        }
        
        async function refreshData() {
            // Summary
            const summary = await fetchAPI('/api/summary');
            document.getElementById('total-sources').textContent = summary.totalSources;
            document.getElementById('avg-reliability').textContent = (summary.avgReliability * 100).toFixed(1) + '%';
            document.getElementById('avg-confidence').textContent = (summary.avgConfidence * 100).toFixed(1) + '%';
            document.getElementById('high-reliability').textContent = summary.highReliabilityCount;
            
            // Distribution
            const dist = await fetchAPI('/api/distribution');
            let distHtml = '';
            const maxCount = Math.max(...Object.values(dist), 1);
            for (const [bucket, count] of Object.entries(dist)) {
                const width = (count / maxCount) * 100;
                distHtml += `
                    <div class="distribution-bar">
                        <span class="distribution-label">${bucket}</span>
                        <div class="distribution-fill" style="width: ${width}%"></div>
                        <span class="distribution-count">${count}</span>
                    </div>
                `;
            }
            document.getElementById('distribution').innerHTML = distHtml;
            
            // Sources
            const sources = await fetchAPI('/api/sources');
            let tableHtml = '';
            sources.forEach(s => {
                const relWidth = (s.reliability * 100).toFixed(0);
                tableHtml += `
                    <tr>
                        <td>${s.sourceId}</td>
                        <td>${s.marketId}</td>
                        <td>
                            ${(s.reliability * 100).toFixed(1)}%
                            <div class="reliability-bar">
                                <div class="reliability-fill" style="width: ${relWidth}%"></div>
                            </div>
                        </td>
                        <td>${(s.confidence * 100).toFixed(1)}%</td>
                        <td>${s.updatedAt || 'Never'}</td>
                    </tr>
                `;
            });
            document.getElementById('sources-body').innerHTML = tableHtml || '<tr><td colspan="5">No sources found</td></tr>';
            
            document.getElementById('updated-at').textContent = 'Last updated: ' + new Date().toLocaleTimeString();
        }
        
        // Initial load
        refreshData();
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
    </script>
</body>
</html>"""


class DashboardServer:
    """Dashboard HTTP server.
    
    Args:
        reliability_store: SQLite reliability store to visualize
        port: Port to run server on (default 8080)
        host: Host to bind to (default localhost)
    """
    
    def __init__(
        self,
        reliability_store: SQLiteReliabilityStore,
        port: int = 8080,
        host: str = "localhost",
    ):
        self._store = reliability_store
        self._port = port
        self._host = host
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
    
    def start(self, blocking: bool = True) -> None:
        """Start the dashboard server.
        
        Args:
            blocking: If True, blocks until server stops. If False, runs in background.
        """
        # Configure handler with data provider
        DashboardHandler.data_provider = DashboardData(self._store)
        
        self._server = HTTPServer((self._host, self._port), DashboardHandler)
        
        print(f"Dashboard running at http://{self._host}:{self._port}")
        
        if blocking:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever)
            self._thread.daemon = True
            self._thread.start()
    
    def stop(self) -> None:
        """Stop the dashboard server."""
        if self._server:
            self._server.shutdown()
            self._server = None
