"""
SiliconForge Embedded Web Dashboard Server.
Zero-dependency HTTP server providing interactive DAG visualization,
Pareto frontier scatter plot, and node diff inspection.
"""

from __future__ import annotations
import http.server
import json
import socketserver
import threading
from typing import Dict, Any, Optional
from siliconforge.core.dag import ExperimentDAG


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SiliconForge Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen font-sans">
    <header class="border-b border-slate-800 bg-slate-950 px-8 py-4 flex justify-between items-center">
        <div>
            <h1 class="text-xl font-bold text-white tracking-wide">SiliconForge</h1>
            <p class="text-xs text-slate-400">Autonomous Hardware Execution Engine</p>
        </div>
        <div class="flex items-center space-x-4">
            <span id="node-count" class="text-xs bg-cyan-950 text-cyan-400 border border-cyan-800 px-3 py-1 rounded-full">0 Nodes</span>
            <span id="best-node" class="text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-3 py-1 rounded-full">No Winner</span>
        </div>
    </header>

    <main class="max-w-7xl mx-auto p-8 space-y-8">
        <!-- Top Row: Metrics & Pareto Chart -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div class="bg-slate-950 border border-slate-800 rounded-lg p-6">
                <h2 class="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">PPA Pareto Frontier (WNS vs Area)</h2>
                <div class="h-64">
                    <canvas id="paretoChart"></canvas>
                </div>
            </div>

            <div class="bg-slate-950 border border-slate-800 rounded-lg p-6 flex flex-col justify-between">
                <div>
                    <h2 class="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Selected Experiment Node</h2>
                    <div id="node-details" class="text-sm space-y-2 text-slate-300">
                        <p class="text-slate-500 italic">Select a node from the table below to inspect its diff and metrics.</p>
                    </div>
                </div>
                <div id="diff-container" class="hidden mt-4">
                    <h3 class="text-xs font-semibold text-slate-400 mb-2">RTL Diff from Parent:</h3>
                    <pre id="diff-box" class="bg-slate-900 border border-slate-800 text-xs p-3 rounded font-mono overflow-x-auto text-emerald-400 max-h-40"></pre>
                </div>
            </div>
        </div>

        <!-- Bottom Row: Experiment Table -->
        <div class="bg-slate-950 border border-slate-800 rounded-lg p-6">
            <h2 class="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Experiment DAG Lineage</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm">
                    <thead class="text-xs uppercase bg-slate-900 text-slate-400 border-b border-slate-800">
                        <tr>
                            <th class="p-3">Node ID</th>
                            <th class="p-3">Branch Name</th>
                            <th class="p-3">Status</th>
                            <th class="p-3 text-right">WNS Slack</th>
                            <th class="p-3 text-right">Cell Area</th>
                            <th class="p-3 text-center">Pareto</th>
                            <th class="p-3 text-center">Action</th>
                        </tr>
                    </thead>
                    <tbody id="nodes-tbody" class="divide-y divide-slate-800 text-slate-300"></tbody>
                </table>
            </div>
        </div>
    </main>

    <script>
        let chart = null;
        let dagData = null;

        async function fetchDAG() {
            try {
                const res = await fetch('/api/dag');
                dagData = await res.json();
                renderUI(dagData);
            } catch (err) {
                console.error("Failed to load DAG:", err);
            }
        }

        function renderUI(data) {
            document.getElementById('node-count').innerText = `${data.total_nodes} Experiment Nodes`;
            document.getElementById('best-node').innerText = data.best_id ? `Best: ${data.best_id}` : 'Exploring...';

            const tbody = document.getElementById('nodes-tbody');
            tbody.innerHTML = '';

            const paretoPoints = [];
            const otherPoints = [];

            Object.values(data.nodes).forEach(node => {
                const isPareto = data.pareto_ids.includes(node.id);
                const wns = node.metrics.wns_ns;
                const area = node.metrics.area_um2;

                if (wns !== null && area !== null) {
                    const pt = { x: area, y: wns, name: node.name, id: node.id };
                    if (isPareto) paretoPoints.push(pt);
                    else otherPoints.push(pt);
                }

                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-900 cursor-pointer";
                tr.innerHTML = `
                    <td class="p-3 font-mono text-xs text-slate-400">${node.id}</td>
                    <td class="p-3 font-medium text-white">${node.name}</td>
                    <td class="p-3">
                        <span class="px-2 py-0.5 rounded text-xs ${node.status === 'SUCCESS' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-rose-950 text-rose-400 border border-rose-800'}">
                            ${node.status}
                        </span>
                    </td>
                    <td class="p-3 text-right font-mono">${wns !== null ? wns.toFixed(2) + ' ns' : '-'}</td>
                    <td class="p-3 text-right font-mono">${area !== null ? area.toFixed(1) + ' um²' : '-'}</td>
                    <td class="p-3 text-center">${isPareto ? '<span class="text-amber-400 font-bold">★ YES</span>' : '<span class="text-slate-600">-</span>'}</td>
                    <td class="p-3 text-center">
                        <button onclick="inspectNode('${node.id}')" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-2 py-1 rounded">Inspect</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            updateChart(paretoPoints, otherPoints);
        }

        function inspectNode(id) {
            const node = dagData.nodes[id];
            if (!node) return;
            const container = document.getElementById('node-details');
            container.innerHTML = `
                <p><strong class="text-white">ID:</strong> ${node.id}</p>
                <p><strong class="text-white">Name:</strong> ${node.name}</p>
                <p><strong class="text-white">Description:</strong> ${node.description || 'N/A'}</p>
                <p><strong class="text-white">WNS Slack:</strong> ${node.metrics.wns_ns !== null ? node.metrics.wns_ns + ' ns' : 'N/A'}</p>
                <p><strong class="text-white">Area:</strong> ${node.metrics.area_um2 !== null ? node.metrics.area_um2 + ' um²' : 'N/A'}</p>
            `;

            const diffBox = document.getElementById('diff-box');
            const diffContainer = document.getElementById('diff-container');
            if (node.diff_from_parent) {
                diffBox.innerText = node.diff_from_parent;
                diffContainer.classList.remove('hidden');
            } else {
                diffContainer.classList.add('hidden');
            }
        }

        function updateChart(pareto, others) {
            const ctx = document.getElementById('paretoChart').getContext('2d');
            if (chart) chart.destroy();

            chart = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [
                        {
                            label: 'Pareto Optimal',
                            data: pareto,
                            backgroundColor: '#fbbf24',
                            pointRadius: 6
                        },
                        {
                            label: 'Explored Variants',
                            data: others,
                            backgroundColor: '#0284c7',
                            pointRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: { display: true, text: 'Cell Area (um²)', color: '#94a3b8' },
                            grid: { color: '#1e293b' },
                            ticks: { color: '#94a3b8' }
                        },
                        y: {
                            title: { display: true, text: 'Worst Negative Slack (ns)', color: '#94a3b8' },
                            grid: { color: '#1e293b' },
                            ticks: { color: '#94a3b8' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#e2e8f0' } }
                    }
                }
            });
        }

        fetchDAG();
    </script>
</body>
</html>
"""


class DashboardServer:
    """Embedded HTTP server serving DAG and Pareto analytics."""

    def __init__(self, dag: ExperimentDAG, port: int = 8080):
        self.dag = dag
        self.port = port
        self.httpd: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self, blocking: bool = False) -> None:
        dag_ref = self.dag

        class RequestHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/api/dag":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    payload = json.dumps(dag_ref.export_summary()).encode("utf-8")
                    self.wfile.write(payload)
                elif self.path in ("/", "/index.html"):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress default noisy access logs

        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer(("0.0.0.0", self.port), RequestHandler)

        if blocking:
            print(f"[SiliconForge Dashboard] Serving at http://localhost:{self.port}")
            self.httpd.serve_forever()
        else:
            self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.thread.start()
            print(f"[SiliconForge Dashboard] Running in background at http://localhost:{self.port}")

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
