"""
Watchdog Timer - Monitors machine health
"""
import logging
import time
import threading
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class WatchdogTimer(QThread):
    """
    Watchdog timer for monitoring machine health
    Emits timeout signal if no heartbeat received within timeout period
    """
    timeout_signal = pyqtSignal(int, str)  # machine_id, component_name
    
    def __init__(self, machine_id, component_name, timeout_seconds=15):
        super().__init__()
        self.machine_id = machine_id
        self.component_name = component_name
        self.timeout_seconds = timeout_seconds
        
        self.last_heartbeat = time.time()
        self.running = True
        self.lock = threading.Lock()
        
        logger.info(f"M{machine_id}: Watchdog started for {component_name} "
                   f"(timeout: {timeout_seconds}s)")
    
    def heartbeat(self):
        """Reset watchdog timer - called when component is healthy"""
        with self.lock:
            self.last_heartbeat = time.time()
    
    def run(self):
        """Monitor heartbeat"""
        while self.running:
            time.sleep(1)
            
            with self.lock:
                elapsed = time.time() - self.last_heartbeat
            
            if elapsed > self.timeout_seconds:
                logger.error(f"M{self.machine_id}: Watchdog timeout for "
                           f"{self.component_name}: {elapsed:.1f}s")
                self.timeout_signal.emit(self.machine_id, self.component_name)
                
                # Reset timer to avoid spam
                with self.lock:
                    self.last_heartbeat = time.time()
    
    def stop(self):
        """Stop watchdog"""
        self.running = False
        logger.info(f"M{self.machine_id}: Watchdog stopped for {self.component_name}")