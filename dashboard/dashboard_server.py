#!/usr/bin/env python3
"""
Dashboard Server - Web interface for Atlas analytics
Provides a simple web server for viewing analytics and insights.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DashboardServer:
    """
    Simple dashboard server for Atlas analytics.

    Provides web interface for:
    - Analytics overview
    - Content insights
    - Consumption patterns
    - Trend analysis
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize DashboardServer with configuration."""
        self.config = config or {}
        self.host = self.config.get('dashboard_host', 'localhost')
        self.port = self.config.get('dashboard_port', 8080)
        self.static_dir = Path(self.config.get('static_dir', 'dashboard/static'))
        self.templates_dir = Path(self.config.get('templates_dir', 'dashboard/templates'))

        # Ensure directories exist
        self.static_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Initialize analytics engine
        from helpers.analytics_engine import AnalyticsEngine
        self.analytics = AnalyticsEngine(config)

        # Initialize intelligence dashboard
        from helpers.intelligence_dashboard import IntelligenceDashboard
        self.intelligence = IntelligenceDashboard(config)

        self._create_default_templates()

    def _create_default_templates(self):
        """Create default HTML templates."""
        # Enhanced intelligence dashboard template
        dashboard_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Intelligence Dashboard</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; color: white; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .card { background: rgba(255,255,255,0.95); border-radius: 12px; padding: 25px; margin-bottom: 25px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); backdrop-filter: blur(10px); }
        .metric { display: inline-block; margin: 15px 25px; text-align: center; }
        .metric-value { font-size: 2.5em; font-weight: bold; background: linear-gradient(45deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .metric-label { color: #666; font-size: 0.9em; margin-top: 5px; }
        .intelligence-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }
        .knowledge-graph { height: 400px; border: 2px solid #e0e0e0; border-radius: 8px; background: #fafafa; }
        .content-list { list-style: none; padding: 0; max-height: 300px; overflow-y: auto; }
        .content-item { padding: 12px; border-left: 4px solid #667eea; margin-bottom: 8px; background: #f8f9ff; border-radius: 4px; }
        .content-title { font-weight: bold; color: #333; margin-bottom: 4px; }
        .content-meta { color: #666; font-size: 0.85em; }
        .recommendation-item { padding: 15px; margin-bottom: 10px; background: linear-gradient(45deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1)); border-radius: 8px; border-left: 4px solid #667eea; }
        .recommendation-title { font-weight: bold; color: #333; margin-bottom: 5px; }
        .recommendation-reason { color: #666; font-size: 0.9em; }
        .priority-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; color: white; margin-left: 10px; }
        .priority-high { background: #ff4444; }
        .priority-medium { background: #ff9500; }
        .priority-low { background: #4CAF50; }
        .refresh-btn { background: linear-gradient(45deg, #667eea, #764ba2); color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); }
        .refresh-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4); }
        .chart-container { height: 250px; position: relative; }
        .insight-item { padding: 10px; background: rgba(102, 126, 234, 0.1); margin: 5px 0; border-radius: 6px; border-left: 3px solid #667eea; }
        .quality-badge { display: inline-block; padding: 4px 12px; border-radius: 16px; font-size: 0.8em; color: white; margin: 2px; }
        .quality-excellent { background: #4CAF50; }
        .quality-good { background: #2196F3; }
        .quality-average { background: #FF9800; }
        .quality-below { background: #f44336; }
        .tab-container { margin-bottom: 20px; }
        .tab-button { background: rgba(255,255,255,0.7); border: none; padding: 10px 20px; margin: 0 5px; border-radius: 6px; cursor: pointer; }
        .tab-button.active { background: #667eea; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Atlas Intelligence Dashboard</h1>
            <p>Personal Knowledge Amplification & Analytics</p>
            <button class="refresh-btn" onclick="window.location.reload()">🔄 Refresh Intelligence</button>
        </div>

        <div class="card">
            <h2>📊 Intelligence Overview</h2>
            <div id="overview-metrics">
                <div class="metric">
                    <div class="metric-value" id="total-content">-</div>
                    <div class="metric-label">Total Content</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="knowledge-nodes">-</div>
                    <div class="metric-label">Knowledge Nodes</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="topic-clusters">-</div>
                    <div class="metric-label">Topic Clusters</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="intelligence-level">-</div>
                    <div class="metric-label">Intelligence Level</div>
                </div>
            </div>
        </div>

        <div class="intelligence-grid">
            <div class="card">
                <h2>🕸️ Knowledge Graph</h2>
                <div id="knowledge-graph" class="knowledge-graph"></div>
                <p><small>Interactive visualization of your content relationships and topic clusters</small></p>
            </div>

            <div class="card">
                <h2>📈 Consumption Patterns</h2>
                <div class="chart-container">
                    <canvas id="consumption-chart"></canvas>
                </div>
                <div id="consumption-insights"></div>
            </div>
        </div>

        <div class="card">
            <h2>🎯 Learning Recommendations</h2>
            <div id="learning-recommendations"></div>
        </div>

        <div class="card">
            <h2>🏆 Content Quality Analysis</h2>
            <div class="tab-container">
                <button class="tab-button active" onclick="switchTab('quality-overview')">Overview</button>
                <button class="tab-button" onclick="switchTab('quality-distribution')">Distribution</button>
            </div>

            <div id="quality-overview" class="tab-content active">
                <div id="quality-metrics"></div>
            </div>

            <div id="quality-distribution" class="tab-content">
                <div id="quality-breakdown"></div>
            </div>
        </div>

        <div class="card">
            <h2>💡 Intelligence Insights</h2>
            <div id="intelligence-insights"></div>
        </div>

        <div class="card">
            <h2>⚙️ System Status</h2>
            <p><strong>Generated:</strong> <span id="generated-time">-</span></p>
            <p><strong>Intelligence Level:</strong> <span id="system-intelligence">-</span></p>
            <p><strong>Databases:</strong> <span id="database-status">-</span></p>
            <p><strong>Status:</strong> <span id="system-status">Analyzing...</span></p>
        </div>
    </div>

    <script>
        let networkInstance = null;
        let chartInstance = null;

        // Load intelligence data
        fetch('/api/intelligence')
            .then(response => response.json())
            .then(data => {
                updateIntelligenceDashboard(data);
            })
            .catch(error => {
                console.error('Error loading intelligence data:', error);
                document.getElementById('system-status').textContent = 'Error loading intelligence data';
            });

        function updateIntelligenceDashboard(intelligence) {
            // Update overview metrics
            const knowledgeGraph = intelligence.knowledge_graph || {};
            const stats = knowledgeGraph.stats || {};

            document.getElementById('total-content').textContent = stats.content_nodes || 0;
            document.getElementById('knowledge-nodes').textContent = stats.total_nodes || 0;
            document.getElementById('topic-clusters').textContent = stats.topic_nodes || 0;
            document.getElementById('intelligence-level').textContent =
                intelligence.system_status?.intelligence_level || 'basic';

            // Update knowledge graph
            updateKnowledgeGraph(knowledgeGraph);

            // Update consumption patterns
            updateConsumptionPatterns(intelligence.consumption_patterns || {});

            // Update learning recommendations
            updateLearningRecommendations(intelligence.learning_recommendations || []);

            // Update content quality analysis
            updateContentQuality(intelligence.content_quality || {});

            // Update intelligence insights
            updateIntelligenceInsights(intelligence);

            // Update system status
            updateSystemStatus(intelligence);
        }

        function updateKnowledgeGraph(graphData) {
            const container = document.getElementById('knowledge-graph');

            if (!graphData.nodes || graphData.nodes.length === 0) {
                container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">No knowledge graph data available</div>';
                return;
            }

            const nodes = new vis.DataSet(graphData.nodes.map(node => ({
                id: node.id,
                label: node.label,
                color: node.type === 'topic' ? '#667eea' : '#764ba2',
                size: node.size || 20,
                title: `${node.type}: ${node.label}`
            })));

            const edges = new vis.DataSet(graphData.edges.map(edge => ({
                from: edge.from,
                to: edge.to,
                color: { color: '#cccccc', opacity: 0.6 }
            })));

            const data = { nodes: nodes, edges: edges };
            const options = {
                nodes: {
                    font: { size: 12 },
                    borderWidth: 2,
                    shadow: true
                },
                edges: {
                    width: 1,
                    shadow: true
                },
                physics: {
                    stabilization: { iterations: 100 },
                    barnesHut: { gravitationalConstant: -2000 }
                }
            };

            if (networkInstance) {
                networkInstance.destroy();
            }
            networkInstance = new vis.Network(container, data, options);
        }

        function updateConsumptionPatterns(patterns) {
            const insights = patterns.insights || [];
            const insightsDiv = document.getElementById('consumption-insights');

            insightsDiv.innerHTML = insights.map(insight =>
                `<div class="insight-item">💡 ${insight}</div>`
            ).join('');

            // Create consumption chart
            const ctx = document.getElementById('consumption-chart').getContext('2d');
            const typeDistribution = patterns.content_type_distribution || [];

            if (chartInstance) {
                chartInstance.destroy();
            }

            if (typeDistribution.length > 0) {
                chartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: typeDistribution.map(item => item.content_type || 'Unknown'),
                        datasets: [{
                            data: typeDistribution.map(item => item.count || 0),
                            backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            }
        }

        function updateLearningRecommendations(recommendations) {
            const container = document.getElementById('learning-recommendations');

            if (!recommendations || recommendations.length === 0) {
                container.innerHTML = '<p>No recommendations available at this time.</p>';
                return;
            }

            container.innerHTML = recommendations.map(rec => {
                const priorityClass = rec.priority > 7 ? 'priority-high' :
                                    rec.priority > 4 ? 'priority-medium' : 'priority-low';
                return `
                    <div class="recommendation-item">
                        <div class="recommendation-title">
                            ${rec.title}
                            <span class="priority-badge ${priorityClass}">Priority: ${rec.priority}</span>
                        </div>
                        <div class="recommendation-reason">${rec.reason}</div>
                    </div>
                `;
            }).join('');
        }

        function updateContentQuality(quality) {
            const metricsDiv = document.getElementById('quality-metrics');
            const breakdownDiv = document.getElementById('quality-breakdown');

            if (quality.has_quality_analysis) {
                metricsDiv.innerHTML = `
                    <div class="metric">
                        <div class="metric-value">${quality.average_quality || 0}</div>
                        <div class="metric-label">Average Quality</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${quality.analyzed_content_count || 0}</div>
                        <div class="metric-label">Analyzed Items</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${quality.category_diversity || 0}</div>
                        <div class="metric-label">Categories</div>
                    </div>
                `;

                const distribution = quality.quality_distribution || [];
                breakdownDiv.innerHTML = distribution.map(item => {
                    const badgeClass = `quality-${item.quality_tier.toLowerCase().replace(' ', '-')}`;
                    return `<span class="quality-badge ${badgeClass}">${item.quality_tier}: ${item.count}</span>`;
                }).join('');
            } else {
                metricsDiv.innerHTML = `
                    <p>${quality.message || 'Quality analysis not yet available'}</p>
                    <div class="metric">
                        <div class="metric-value">${quality.total_content || 0}</div>
                        <div class="metric-label">Total Content</div>
                    </div>
                `;
                breakdownDiv.innerHTML = '<p>Quality analysis will be available after processing content through LLM extraction.</p>';
            }
        }

        function updateIntelligenceInsights(intelligence) {
            const insightsDiv = document.getElementById('intelligence-insights');
            const insights = [];

            // Generate insights based on available data
            const graph = intelligence.knowledge_graph || {};
            if (graph.stats && graph.stats.topic_nodes > 0) {
                insights.push(`🕸️ Knowledge network contains ${graph.stats.topic_nodes} topic clusters`);
            }

            const patterns = intelligence.consumption_patterns || {};
            if (patterns.insights && patterns.insights.length > 0) {
                insights.push(`📈 ${patterns.insights.length} consumption patterns identified`);
            }

            const recs = intelligence.learning_recommendations || [];
            if (recs.length > 0) {
                insights.push(`🎯 ${recs.length} personalized learning recommendations generated`);
            }

            if (insights.length === 0) {
                insights.push('🚀 Intelligence analysis in progress - building your knowledge profile...');
            }

            insightsDiv.innerHTML = insights.map(insight =>
                `<div class="insight-item">${insight}</div>`
            ).join('');
        }

        function updateSystemStatus(intelligence) {
            const systemStatus = intelligence.system_status || {};
            const databases = systemStatus.databases_available || {};

            document.getElementById('generated-time').textContent =
                new Date(intelligence.generated_at).toLocaleString();
            document.getElementById('system-intelligence').textContent =
                systemStatus.intelligence_level || 'unknown';

            const dbStatus = Object.entries(databases)
                .map(([db, available]) => `${db}: ${available ? '✅' : '❌'}`)
                .join(', ');
            document.getElementById('database-status').textContent = dbStatus;
            document.getElementById('system-status').textContent = 'Intelligence Active';
        }

        function switchTab(tabId) {
            // Remove active class from all tabs and contents
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            // Add active class to clicked tab and corresponding content
            event.target.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }
    </script>
</body>
</html>"""

        dashboard_file = self.templates_dir / 'dashboard.html'
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_html)

        logger.info("Created default dashboard template")

    def get_insights_json(self, days: int = 30) -> str:
        """Get insights as JSON for API endpoints."""
        try:
            insights = self.analytics.generate_insights(days)
            return json.dumps(insights, indent=2)
        except Exception as e:
            logger.error(f"Error getting insights JSON: {str(e)}")
            return json.dumps({"error": str(e)})

    def get_intelligence_json(self) -> str:
        """Get comprehensive intelligence report as JSON."""
        try:
            intelligence = self.intelligence.generate_comprehensive_intelligence_report()
            return json.dumps(intelligence, indent=2)
        except Exception as e:
            logger.error(f"Error getting intelligence JSON: {str(e)}")
            return json.dumps({"error": str(e), "generated_at": datetime.now().isoformat()})

    def get_dashboard_html(self) -> str:
        """Get dashboard HTML content."""
        try:
            dashboard_file = self.templates_dir / 'dashboard.html'
            if dashboard_file.exists():
                with open(dashboard_file, 'r') as f:
                    return f.read()
            else:
                return "<html><body><h1>Dashboard template not found</h1></body></html>"
        except Exception as e:
            logger.error(f"Error getting dashboard HTML: {str(e)}")
            return f"<html><body><h1>Error: {str(e)}</h1></body></html>"

    def start_server(self, threaded: bool = True):
        """Start the dashboard web server."""
        try:
            # Simple HTTP server implementation
            import http.server
            import socketserver
            from urllib.parse import urlparse, parse_qs

            class DashboardHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    parsed_path = urlparse(self.path)

                    if parsed_path.path == '/':
                        # Serve dashboard
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        dashboard_html = self.server.dashboard.get_dashboard_html()
                        self.wfile.write(dashboard_html.encode())

                    elif parsed_path.path == '/api/insights':
                        # Serve basic insights JSON (legacy)
                        query_params = parse_qs(parsed_path.query)
                        days = int(query_params.get('days', [30])[0])

                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        insights_json = self.server.dashboard.get_insights_json(days)
                        self.wfile.write(insights_json.encode())

                    elif parsed_path.path == '/api/intelligence':
                        # Serve comprehensive intelligence report
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        intelligence_json = self.server.dashboard.get_intelligence_json()
                        self.wfile.write(intelligence_json.encode())

                    elif parsed_path.path.startswith('/static/'):
                        # Serve static files
                        file_path = self.server.dashboard.static_dir / parsed_path.path[8:]
                        if file_path.exists():
                            self.send_response(200)
                            if file_path.suffix == '.css':
                                self.send_header('Content-type', 'text/css')
                            elif file_path.suffix == '.js':
                                self.send_header('Content-type', 'application/javascript')
                            else:
                                self.send_header('Content-type', 'application/octet-stream')
                            self.end_headers()
                            with open(file_path, 'rb') as f:
                                self.wfile.write(f.read())
                        else:
                            self.send_error(404)
                    else:
                        self.send_error(404)

                def log_message(self, format, *args):
                    # Suppress default HTTP logging
                    pass

            # Create server
            with socketserver.TCPServer((self.host, self.port), DashboardHandler) as httpd:
                httpd.dashboard = self

                logger.info(f"Dashboard server starting on http://{self.host}:{self.port}")
                print(f"Atlas Dashboard available at: http://{self.host}:{self.port}")
                print("Press Ctrl+C to stop the server")

                if threaded:
                    import threading
                    server_thread = threading.Thread(target=httpd.serve_forever)
                    server_thread.daemon = True
                    server_thread.start()
                    return httpd
                else:
                    httpd.serve_forever()

        except Exception as e:
            logger.error(f"Error starting dashboard server: {str(e)}")
            raise

    def stop_server(self, server):
        """Stop the dashboard server."""
        try:
            if server:
                server.shutdown()
                logger.info("Dashboard server stopped")
        except Exception as e:
            logger.error(f"Error stopping server: {str(e)}")

    def generate_static_dashboard(self, output_file: str = "dashboard_export.html"):
        """Generate static HTML dashboard."""
        try:
            insights = self.analytics.generate_insights(30)

            # Get template and inject data
            template = self.get_dashboard_html()

            # Replace the fetch call with embedded data
            insights_js = f"const insights = {json.dumps(insights)}; updateDashboard(insights);"
            template = template.replace(
                "fetch('/api/insights')\n            .then(response => response.json())\n            .then(data => {\n                updateDashboard(data);\n            })\n            .catch(error => {\n                console.error('Error loading analytics:', error);\n                document.getElementById('system-status').textContent = 'Error loading data';\n            });",
                insights_js
            )

            # Write to file
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                f.write(template)

            logger.info(f"Static dashboard generated: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error generating static dashboard: {str(e)}")
            return None


def start_dashboard_server(config: Dict[str, Any] = None, port: int = 8080):
    """Convenience function to start dashboard server."""
    config = config or {}
    config['dashboard_port'] = port

    dashboard = DashboardServer(config)
    return dashboard.start_server(threaded=True)


def generate_dashboard_export(config: Dict[str, Any] = None, output_file: str = "atlas_dashboard.html"):
    """Convenience function to generate static dashboard."""
    dashboard = DashboardServer(config)
    return dashboard.generate_static_dashboard(output_file)