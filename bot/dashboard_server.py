"""
Dashboard WebSocket Server - Serves real-time bot data to the web dashboard.
"""
import json
import asyncio
import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from config.settings import DASHBOARD_PORT, DASHBOARD_HOST


class DashboardHandler(SimpleHTTPRequestHandler):
    """Serves dashboard static files."""
    
    def __init__(self, *args, **kwargs):
        dashboard_dir = str(Path(__file__).parent.parent / 'dashboard')
        super().__init__(*args, directory=dashboard_dir, **kwargs)
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs


def start_dashboard_server(trader_instance=None, port=None):
    """Start the dashboard HTTP server in a background thread."""
    port = port or DASHBOARD_PORT
    
    # Write bot status to a JSON file that dashboard reads
    def update_status_file():
        status_file = Path(__file__).parent.parent / 'dashboard' / 'status.json'
        while True:
            try:
                if trader_instance:
                    status = trader_instance.get_status()
                else:
                    status = {'running': False, 'message': 'Bot not connected'}
                status_file.write_text(json.dumps(status, default=str), encoding='utf-8')
            except Exception:
                pass
            import time
            time.sleep(5)
    
    # Start status updater thread
    status_thread = threading.Thread(target=update_status_file, daemon=True)
    status_thread.start()
    
    # Start HTTP server
    server = HTTPServer((DASHBOARD_HOST, port), DashboardHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    print(f"🖥️ Dashboard: http://{DASHBOARD_HOST}:{port}")
    return server
