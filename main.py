"""
Main Application - Multi-Machine Industrial Vision System
Orchestrates all machines, cameras, inference, and UI
"""
import sys
import os
import logging
import traceback
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.inference_engine import InferenceEngine
from core.camera_thread import CameraThread
from core.watchdog import WatchdogTimer
from core.relay_manager import RelayManager
from core.machine_controller import MachineController
from ui.home_page import HomePage
from ui.detection_page import DetectionPage
from ui.training_page import TrainingPage
from config.config_manager import ConfigManager

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            f'multi_machine_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MultiMachineApp(QMainWindow):
    """
    Main application managing all machines
    """
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.config_manager = ConfigManager(config_dir="config")
        self.config = self.config_manager.load_machines_config()
        
        # Core components
        self.inference_engine = None
        self.relay_manager = None
        
        # Machine components (indexed by machine_id)
        self.camera_threads = {}
        self.machine_controllers = {}
        self.watchdogs = {}
        
        # State
        self.running = False
        self.current_detection_machine_id = None
        
        # UI
        self.home_page = None
        self.detection_page = None
        self.training_page = None
        
        self.init_ui()
        self.init_system()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Multi-Machine Industrial Vision System")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Central widget with tab widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create pages
        self.home_page = HomePage()
        self.detection_page = DetectionPage()
        self.training_page = TrainingPage()
        
        self.tab_widget.addTab(self.home_page, "Home")
        self.tab_widget.addTab(self.detection_page, "Detection Monitor")
        self.tab_widget.addTab(self.training_page, "Training")
        
        # Connect home page signals
        self.home_page.monitor_machine.connect(self.show_detection_monitor)
        self.home_page.train_machine.connect(self.show_training_page)
        self.home_page.start_all_btn.clicked.connect(self.start_all_machines)
        self.home_page.stop_all_btn.clicked.connect(self.stop_all_machines)
        
        # Connect training page signals
        self.training_page.boundaries_saved.connect(self.save_machine_boundaries)
        self.training_page.capture_btn.clicked.connect(self.capture_training_frame)
        
        # Menu bar
        self.create_menu_bar()
        
        # Status bar
        self.statusBar().showMessage("System Ready")
        
        logger.info("UI initialized")
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        view_logs_action = QAction('View Logs', self)
        view_logs_action.triggered.connect(self.view_logs)
        file_menu.addAction(view_logs_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        test_relay_action = QAction('Test Relay Board', self)
        test_relay_action.triggered.connect(self.test_relay_board)
        tools_menu.addAction(test_relay_action)
        
        config_action = QAction('Edit Configuration', self)
        config_action.triggered.connect(self.edit_configuration)
        tools_menu.addAction(config_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def init_system(self):
        """Initialize system components"""
        try:
            logger.info("="*60)
            logger.info("INITIALIZING MULTI-MACHINE VISION SYSTEM")
            logger.info("="*60)
            
            # Validate configuration
            if not self.config_manager.validate_config(self.config):
                QMessageBox.critical(self, "Config Error", 
                                   "Invalid configuration. Using defaults.")
                return
            
            # Initialize relay manager
            self.relay_manager = RelayManager(self.config.get("relay_config", {}))
            if not self.relay_manager.initialize():
                QMessageBox.warning(self, "Relay Warning", 
                                  "Failed to initialize relay board. System will continue without relay control.")
            
            # Initialize inference engine
            model_path = self.config.get("model_path", "best.pt")
            confidence_thresholds = self.config.get("confidence_thresholds", {})
            
            self.inference_engine = InferenceEngine(model_path, confidence_thresholds)
            
            # Initialize machines
            for machine_config in self.config.get("machines", []):
                if machine_config.get("enabled", True):
                    self.init_machine(machine_config)
            
            # Update home page
            self.home_page.set_system_status("System Ready - All machines initialized", "green")
            
            logger.info("✓ System initialization complete")
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "Initialization Error", 
                               f"System initialization failed:\n{str(e)}")
    
    def init_machine(self, machine_config):
        """Initialize a single machine"""
        machine_id = machine_config["machine_id"]
        machine_name = machine_config["name"]
        
        logger.info(f"M{machine_id}: Initializing {machine_name}...")
        
        try:
            # Create machine controller
            controller = MachineController(
                machine_id=machine_id,
                machine_name=machine_name,
                confidence_thresholds=self.config.get("confidence_thresholds", {}),
                relay_manager=self.relay_manager
            )
            
            # Load boundaries
            boundaries = self.config_manager.load_machine_boundaries(machine_id)
            controller.set_boundaries(boundaries)
            
            # Configure relay
            relay_start = machine_config.get("relay_start_channel", 6)
            self.relay_manager.configure_machine(machine_id, relay_start)
            
            # Create camera thread
            camera_thread = CameraThread(
                machine_id=machine_id,
                camera_source=machine_config["camera_source"],
                camera_config=self.config.get("camera_config", {})
            )
            
            # Create watchdog
            watchdog = WatchdogTimer(
                machine_id=machine_id,
                component_name="Camera",
                timeout_seconds=self.config.get("watchdog_timeout", 15)
            )
            
            # Connect signals
            camera_thread.frame_ready.connect(self.on_frame_ready)
            camera_thread.heartbeat_signal.connect(self.on_camera_heartbeat)
            camera_thread.status_signal.connect(self.on_camera_status)
            camera_thread.error_signal.connect(self.on_camera_error)
            
            controller.pair_status_changed.connect(self.on_pair_status_changed)
            controller.detection_stats_updated.connect(self.on_detection_stats_updated)
            
            watchdog.timeout_signal.connect(self.on_watchdog_timeout)
            
            # Store components
            self.camera_threads[machine_id] = camera_thread
            self.machine_controllers[machine_id] = controller
            self.watchdogs[machine_id] = watchdog
            
            # Add to home page
            relay_config = self.relay_manager.get_machine_relay_config(machine_id)
            self.home_page.add_machine_card(machine_id, machine_name, relay_config)
            
            logger.info(f"M{machine_id}: ✓ Initialized")
            
        except Exception as e:
            logger.error(f"M{machine_id}: Initialization failed: {e}")
            logger.error(traceback.format_exc())
    
    def start_all_machines(self):
        """Start all machines"""
        if self.running:
            return
        
        logger.info("="*60)
        logger.info("STARTING ALL MACHINES")
        logger.info("="*60)
        
        try:
            # Start inference engine
            self.inference_engine.start()
            
            # Connect inference engine signal
            self.inference_engine.detections_ready.connect(self.on_detections_ready)
            
            # Start all camera threads
            for machine_id, camera_thread in self.camera_threads.items():
                camera_thread.start()
                logger.info(f"M{machine_id}: Camera thread started")
            
            # Start all watchdogs
            for machine_id, watchdog in self.watchdogs.items():
                watchdog.start()
                logger.info(f"M{machine_id}: Watchdog started")
            
            self.running = True
            self.home_page.set_detection_running(True)
            self.home_page.set_system_status("All machines running", "green")
            self.statusBar().showMessage("Detection Active - All Machines Running")
            
            logger.info("✓ All machines started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start machines: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "Start Error", f"Failed to start machines:\n{str(e)}")
    
    def stop_all_machines(self):
        """Stop all machines"""
        if not self.running:
            return
        
        logger.info("="*60)
        logger.info("STOPPING ALL MACHINES")
        logger.info("="*60)
        
        try:
            # Stop all watchdogs
            for machine_id, watchdog in self.watchdogs.items():
                watchdog.stop()
                watchdog.wait(1000)
                logger.info(f"M{machine_id}: Watchdog stopped")
            
            # Stop all camera threads
            for machine_id, camera_thread in self.camera_threads.items():
                camera_thread.stop()
                camera_thread.wait(2000)
                logger.info(f"M{machine_id}: Camera thread stopped")
            
            # Stop inference engine
            self.inference_engine.stop()
            self.inference_engine.wait(2000)
            logger.info("Inference engine stopped")
            
            # Reset all relays
            self.relay_manager.reset_all_relays()
            
            self.running = False
            self.home_page.set_detection_running(False)
            self.home_page.set_system_status("All machines stopped", "gray")
            self.statusBar().showMessage("System Stopped")
            
            logger.info("✓ All machines stopped")
            
        except Exception as e:
            logger.error(f"Error stopping machines: {e}")
            logger.error(traceback.format_exc())
    
    def on_frame_ready(self, machine_id, frame):
        """Handle frame from camera"""
        try:
            # Submit frame to inference engine
            if self.running and self.inference_engine:
                controller = self.machine_controllers.get(machine_id)
                if controller:
                    self.inference_engine.submit_frame(machine_id, frame, 
                                                      controller.boundaries)
            
            # Update detection page if this is the selected machine
            if machine_id == self.current_detection_machine_id:
                controller = self.machine_controllers.get(machine_id)
                if controller:
                    self.detection_page.update_frame(frame, controller.detection_counts)
                    
        except Exception as e:
            logger.error(f"M{machine_id}: Frame processing error: {e}")
    
    def on_detections_ready(self, machine_id, results, fps):
        """Handle detections from inference engine"""
        try:
            controller = self.machine_controllers.get(machine_id)
            if controller:
                # Get latest frame from camera
                camera = self.camera_threads.get(machine_id)
                if camera:
                    frame = camera.get_latest_frame()
                    if frame is not None:
                        controller.process_detections(results, frame)
            
            # Update FPS if this is the displayed machine
            if machine_id == self.current_detection_machine_id:
                self.detection_page.update_fps(fps)
                
        except Exception as e:
            logger.error(f"M{machine_id}: Detection handling error: {e}")
    
    def on_pair_status_changed(self, machine_id, pair_statuses):
        """Handle pair status change"""
        try:
            controller = self.machine_controllers.get(machine_id)
            if controller:
                # Update home page
                camera_connected = self.camera_threads[machine_id].camera is not None
                self.home_page.update_machine_status(
                    machine_id, camera_connected, self.running,
                    pair_statuses, controller.get_last_fault_times()
                )
                
                # Update detection page if this is the selected machine
                if machine_id == self.current_detection_machine_id:
                    self.detection_page.update_pair_statuses(pair_statuses)
                    pair_faults = [status != "OK" for status in pair_statuses]
                    self.detection_page.update_relay_states(pair_faults)
                    
        except Exception as e:
            logger.error(f"M{machine_id}: Status update error: {e}")
    
    def on_detection_stats_updated(self, machine_id, stats):
        """Handle detection statistics update"""
        try:
            if machine_id == self.current_detection_machine_id:
                self.detection_page.update_statistics(stats)
        except Exception as e:
            logger.error(f"M{machine_id}: Stats update error: {e}")
    
    def on_camera_heartbeat(self, machine_id):
        """Handle camera heartbeat"""
        watchdog = self.watchdogs.get(machine_id)
        if watchdog:
            watchdog.heartbeat()
    
    def on_camera_status(self, machine_id, status):
        """Handle camera status message"""
        logger.info(f"M{machine_id}: {status}")
    
    def on_camera_error(self, machine_id, error):
        """Handle camera error"""
        logger.error(f"M{machine_id}: Camera error: {error}")
    
    def on_watchdog_timeout(self, machine_id, component):
        """Handle watchdog timeout"""
        logger.error(f"M{machine_id}: Watchdog timeout - {component}")
        QMessageBox.warning(self, "Watchdog Alert",
                          f"Machine {machine_id} - {component} timeout detected!")
    
    def show_detection_monitor(self, machine_id):
        """Show detection monitor for a machine"""
        controller = self.machine_controllers.get(machine_id)
        if controller:
            self.current_detection_machine_id = machine_id
            relay_config = self.relay_manager.get_machine_relay_config(machine_id)
            self.detection_page.set_machine(machine_id, controller.machine_name,
                                           relay_config, controller.boundaries)
            self.tab_widget.setCurrentWidget(self.detection_page)
            logger.info(f"Switched to detection monitor for M{machine_id}")
    
    def show_training_page(self, machine_id):
        """Show training page for a machine"""
        controller = self.machine_controllers.get(machine_id)
        if controller:
            self.training_page.set_machine(machine_id, controller.machine_name)
            self.training_page.load_boundaries(controller.boundaries)
            self.tab_widget.setCurrentWidget(self.training_page)
            logger.info(f"Switched to training page for M{machine_id}")
    
    def capture_training_frame(self):
        """Capture frame for training"""
        machine_id = self.training_page.current_machine_id
        if machine_id:
            camera = self.camera_threads.get(machine_id)
            if camera:
                frame = camera.get_latest_frame()
                if frame is not None:
                    self.training_page.set_frame(frame)
                else:
                    QMessageBox.warning(self, "No Frame", 
                                      "No frame available. Make sure camera is running.")
    
    def save_machine_boundaries(self, machine_id, boundaries):
        """Save boundaries for a machine"""
        # Save to file
        self.config_manager.save_machine_boundaries(machine_id, boundaries)
        
        # Update controller
        controller = self.machine_controllers.get(machine_id)
        if controller:
            controller.set_boundaries(boundaries)
            logger.info(f"M{machine_id}: Boundaries updated in controller")
    
    def test_relay_board(self):
        """Test relay board"""
        if not self.relay_manager:
            QMessageBox.warning(self, "No Relay", "Relay manager not initialized")
            return
        
        reply = QMessageBox.question(
            self, 'Test Relays',
            'Test all configured machine relays?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for machine_id in self.machine_controllers.keys():
                if not self.relay_manager.test_machine_relays(machine_id):
                    QMessageBox.warning(self, "Test Failed",
                                      f"Machine {machine_id} relay test failed")
                    return
            
            QMessageBox.information(self, "Test Complete", 
                                  "All machine relays tested successfully!")
    
    def edit_configuration(self):
        """Open configuration editor"""
        QMessageBox.information(self, "Configuration",
                              "Configuration editing will be available in settings page.\n"
                              "For now, edit config/machines_config.json manually.")
    
    def view_logs(self):
        """View log file"""
        log_file = f'multi_machine_{datetime.now().strftime("%Y%m%d")}.log'
        if os.path.exists(log_file):
            if sys.platform == "win32":
                os.startfile(log_file)
            elif sys.platform == "darwin":
                os.system(f"open {log_file}")
            else:
                os.system(f"xdg-open {log_file}")
        else:
            QMessageBox.information(self, "Logs", "No log file found for today")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About",
            "Multi-Machine Industrial Vision System\n\n"
            "Features:\n"
            "• Monitors up to 3 machines simultaneously\n"
            "• Single YOLO model for all cameras\n"
            "• Independent boundaries per machine\n"
            "• Fault-only relay control (ON = Fault)\n"
            "• 16-channel USB relay support\n"
            "• Auto-reconnect cameras\n"
            "• Watchdog monitoring\n"
            "• 24/7 industrial operation ready\n\n"
            "Detection Logic:\n"
            "• OK: Both Oil Can and Bunk Hole present\n"
            "• FAULT: Both absent OR mismatch\n\n"
            "Relay Philosophy:\n"
            "• Relay ON = Fault detected\n"
            "• Relay OFF = Pair OK\n"
            "• 3 relays per machine (one per pair)\n\n"
            "(c) 2025 Credence Technologies Pvt Ltd"
        )
    
    def closeEvent(self, event):
        """Handle application close"""
        logger.info("Application close requested")
        
        if self.running:
            reply = QMessageBox.question(
                self, 'Confirm Exit',
                'System is running. Stop all machines and exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            self.stop_all_machines()
        
        logger.info("="*60)
        logger.info("APPLICATION SHUTDOWN")
        logger.info("="*60)
        
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Global exception handler
    sys.excepthook = lambda exc_type, exc_value, exc_tb: logger.critical(
        f"Unhandled exception: {exc_type.__name__}: {exc_value}\n"
        f"{''.join(traceback.format_tb(exc_tb))}"
    )
    
    window = MultiMachineApp()
    window.show()
    
    logger.info("="*60)
    logger.info("MULTI-MACHINE VISION SYSTEM STARTED")
    logger.info("="*60)
    
    return_code = app.exec_()
    
    logger.info(f"Application exited with code {return_code}")
    sys.exit(return_code)


if __name__ == '__main__':
    main()