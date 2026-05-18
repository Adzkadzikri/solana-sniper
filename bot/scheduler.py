"""
Task Scheduler - Periodic tasks for the trading bot.
"""
import time
import threading
from datetime import datetime, timezone


class Scheduler:
    """Simple scheduler for periodic bot tasks."""
    
    def __init__(self):
        self.tasks = []
        self._running = False
    
    def add_task(self, name: str, interval_seconds: int, callback):
        """Register a periodic task."""
        self.tasks.append({
            'name': name,
            'interval': interval_seconds,
            'callback': callback,
            'last_run': 0,
        })
    
    def start(self):
        """Start the scheduler in a background thread."""
        self._running = True
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()
    
    def stop(self):
        self._running = False
    
    def _loop(self):
        while self._running:
            now = time.time()
            for task in self.tasks:
                if now - task['last_run'] >= task['interval']:
                    try:
                        task['callback']()
                        task['last_run'] = now
                    except Exception as e:
                        print(f"Scheduler error [{task['name']}]: {e}")
            time.sleep(1)
