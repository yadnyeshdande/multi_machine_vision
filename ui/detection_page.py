"""
Detection Page - EXACT ORIGINAL UI + Multi-Machine Support
Real-time detection monitoring with all original metrics and health monitoring
"""
import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import json
import os
import time
import logging
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


class DetectionPage(QWidget):
    """
    EXACT ORIGINAL: Detection page with full metrics, health monitoring, and relay status
    UPGRADED: Works with multi-machine architecture
    """
    
    def __init__(self):
        super().__init__()
        
        # Machine context
        self.current_machine_id = None
        self.current_machine_name = "No Machine Selected"
        self.current_camera_source = None
        
        # Detection state
        self.running = False
        self.boundaries = []
        self.oil_can_boundaries = []
        self.bunk_hole_boundaries = []
        self.reference_frame_shape = None
        
        # Metrics (EXACT ORIGINAL)
        self.detection_count = 0
        self.error_count = 0
        self.problem_count = 0
        self.detection_history = deque(maxlen=100)
        self.uptime_start = None
        
        # External references (set by main app)
        self.machine_controller = None
        self.relay_manager = None
        self.camera_thread = None
        
        self.init_ui()
        
    def init_ui(self):
        """EXACT ORIGINAL UI - Preserved completely"""
        layout = QVBoxLayout()
        
        # Title with machine name
        self.title = QLabel("Detection - 3-Relay Pairing System (Fault Detection Mode)")
        self.title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)
        
        # Controls (simplified for multi-machine - camera already connected)
        controls_layout = QHBoxLayout()
        
        self.machine_info_label = QLabel("Machine: Not Selected")
        self.machine_info_label.setStyleSheet(
            "padding: 10px; background-color: #E3F2FD; "
            "border-radius: 5px; font-weight: bold;"
        )
        controls_layout.addWidget(self.machine_info_label)
        
        controls_layout.addStretch()
        
        self.start_btn = QPushButton("Start Detection")
        self.start_btn.clicked.connect(self.toggle_detection)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; min-width: 150px;")
        controls_layout.addWidget(self.start_btn)
        
        layout.addLayout(controls_layout)
        
        # Detection view (EXACT ORIGINAL)
        self.detection_label = QLabel("Detection View")
        self.detection_label.setMinimumSize(800, 600)
        self.detection_label.setStyleSheet("border: 2px solid #333;")
        self.detection_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.detection_label)
        
        # Metrics row (EXACT ORIGINAL)
        metrics_layout = QHBoxLayout()
        
        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet("padding: 5px; font-weight: bold; background-color: #E3F2FD;")
        metrics_layout.addWidget(self.fps_label)
        
        self.detection_count_label = QLabel("Detections: 0")
        self.detection_count_label.setStyleSheet("padding: 5px; font-weight: bold; background-color: #E3F2FD;")
        metrics_layout.addWidget(self.detection_count_label)
        
        self.problem_count_label = QLabel("Faults: 0")
        self.problem_count_label.setStyleSheet("padding: 5px; font-weight: bold; background-color: #FFEBEE;")
        metrics_layout.addWidget(self.problem_count_label)
        
        layout.addLayout(metrics_layout)
        
        # Pair status row (EXACT ORIGINAL)
        pair_status_layout = QHBoxLayout()
        pair_label = QLabel("Pair Status:")
        pair_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        pair_status_layout.addWidget(pair_label)
        
        self.pair_status_labels = []
        for i in range(3):
            status_label = QLabel(f"Pair {i + 1}: --")
            status_label.setStyleSheet(
                "padding: 10px; font-size: 11px; font-weight: bold; "
                "background-color: #cccccc; border-radius: 5px; min-width: 180px;"
            )
            status_label.setAlignment(Qt.AlignCenter)
            pair_status_layout.addWidget(status_label)
            self.pair_status_labels.append(status_label)
        
        layout.addLayout(pair_status_layout)
        
        # Relay status row (ADAPTED: 3 relays instead of 4, but same style)
        relay_status_layout = QHBoxLayout()
        relay_label = QLabel("Relay Status:")
        relay_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        relay_status_layout.addWidget(relay_label)
        
        self.relay_status_labels = []
        relay_names = ["R? (Pair 1)", "R? (Pair 2)", "R? (Pair 3)"]
        for i, name in enumerate(relay_names):
            relay_status = QLabel(f"{name}: OFF")
            relay_status.setStyleSheet(
                "padding: 8px; font-size: 10px; font-weight: bold; "
                "background-color: #E0E0E0; border-radius: 5px; min-width: 120px;"
            )
            relay_status.setAlignment(Qt.AlignCenter)
            relay_status_layout.addWidget(relay_status)
            self.relay_status_labels.append(relay_status)
        
        layout.addLayout(relay_status_layout)
        
        # Overall status (EXACT ORIGINAL)
        self.overall_status = QLabel("System Status: Idle")
        self.overall_status.setStyleSheet(
            "padding: 15px; font-size: 16px; font-weight: bold; "
            "background-color: #f0f0f0; border-radius: 5px;"
        )
        self.overall_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.overall_status)
        
        # Health monitoring (EXACT ORIGINAL)
        self.health_label = QLabel("System Health: Ready")
        self.health_label.setStyleSheet(
            "padding: 10px; font-size: 12px; "
            "background-color: #E8F5E8; color: #2E7D32; border-radius: 5px;"
        )
        layout.addWidget(self.health_label)
        
        # Statistics row (EXACT ORIGINAL)
        stats_layout = QHBoxLayout()
        
        self.uptime_label = QLabel("Uptime: 00:00:00")
        self.uptime_label.setStyleSheet("padding: 5px; font-size: 11px; background-color: #F5F5F5;")
        stats_layout.addWidget(self.uptime_label)
        
        self.success_rate_label = QLabel("Success Rate: 100%")
        self.success_rate_label.setStyleSheet("padding: 5px; font-size: 11px; background-color: #F5F5F5;")
        stats_layout.addWidget(self.success_rate_label)
        
        layout.addLayout(stats_layout)
        
        self.setLayout(layout)
        
        # Timers (EXACT ORIGINAL)
        self.uptime_timer = QTimer()
        self.uptime_timer.timeout.connect(self.update_uptime)
        
        self.health_check_timer = QTimer()
        self.health_check_timer.timeout.connect(self.check_system_health)
        self.health_check_timer.start(5000)
    
    def set_machine(self, machine_id, machine_name, camera_source, machine_controller, relay_manager, camera_thread):
        """Set which machine to monitor"""
        # Stop current detection if running
        if self.running:
            self.stop_detection()
        
        self.current_machine_id = machine_id
        self.current_machine_name = machine_name
        self.current_camera_source = camera_source
        self.machine_controller = machine_controller
        self.relay_manager = relay_manager
        self.camera_thread = camera_thread
        
        # Update UI
        self.title.setText(f"Detection - Machine {machine_id}: {machine_name}")
        self.machine_info_label.setText(f"Machine {machine_id}: {machine_name}")
        
        # Load boundaries
        self.load_boundaries()
        
        # Update relay labels with actual relay numbers
        if relay_manager:
            relay_config = relay_manager.get_machine_relay_config(machine_id)
            if len(relay_config) == 3:
                for i, relay_num in enumerate(relay_config):
                    self.relay_status_labels[i].setText(f"R{relay_num} (Pair {i+1}): OFF")
        
        # Enable start button
        self.start_btn.setEnabled(True)
        
        logger.info(f"Detection page set to M{machine_id}: {machine_name}")
    
    def load_boundaries(self):
        """Load boundaries for current machine"""
        if self.current_machine_id is None:
            return
        
        try:
            filepath = os.path.join("config", f"machine{self.current_machine_id}_boundaries.json")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Convert to old format for compatibility
                self.oil_can_boundaries = [
                    data.get('pair1_oc', []),
                    data.get('pair2_oc', []),
                    data.get('pair3_oc', [])
                ]
                self.bunk_hole_boundaries = [
                    data.get('pair1_bh', []),
                    data.get('pair2_bh', []),
                    data.get('pair3_bh', [])
                ]
                self.boundaries = data
                
                logger.info(f"M{self.current_machine_id}: Boundaries loaded")
            else:
                logger.warning(f"M{self.current_machine_id}: No boundaries file found")
                QMessageBox.warning(self, "Warning", 
                                  f"No boundaries found for Machine {self.current_machine_id}.\n"
                                  "Please train boundaries first!")
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Failed to load boundaries: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load boundaries:\n{str(e)}")
    
    def toggle_detection(self):
        """Toggle detection on/off"""
        if self.running:
            self.stop_detection()
        else:
            self.start_detection()
    
    def start_detection(self):
        """Start detection for current machine"""
        if self.current_machine_id is None:
            QMessageBox.warning(self, "Error", "No machine selected!")
            return
        
        if not self.boundaries:
            QMessageBox.warning(self, "Error", "No boundaries defined! Train boundaries first.")
            return
        
        if not self.camera_thread or not self.camera_thread.running:
            QMessageBox.warning(self, "Error", "Camera not running! Start the system from home page.")
            return
        
        try:
            logger.info("="*60)
            logger.info(f"STARTING DETECTION FOR M{self.current_machine_id}")
            logger.info("="*60)
            
            # Reset metrics
            self.detection_count = 0
            self.error_count = 0
            self.problem_count = 0
            self.detection_history.clear()
            self.uptime_start = time.time()
            
            # Connect to machine controller signals
            if self.machine_controller:
                self.machine_controller.pair_status_changed.connect(self.on_pair_status_changed)
                self.machine_controller.detection_stats_updated.connect(self.on_detection_stats_updated)
            
            # Start uptime timer
            self.uptime_timer.start(1000)
            
            # Update UI
            self.running = True
            self.start_btn.setText("Stop Detection")
            self.start_btn.setStyleSheet("background-color: #F44336; color: white; padding: 10px; min-width: 150px;")
            self.overall_status.setText("System Status: Running")
            self.overall_status.setStyleSheet(
                "padding: 15px; font-size: 16px; font-weight: bold; "
                "background-color: #4CAF50; color: white; border-radius: 5px;"
            )
            self.health_label.setText("System Health: All systems running")
            self.health_label.setStyleSheet(
                "padding: 10px; font-size: 12px; "
                "background-color: #E8F5E8; color: #2E7D32; border-radius: 5px;"
            )
            
            logger.info(f"M{self.current_machine_id}: Detection started")
            logger.info("="*60)
            
        except Exception as e:
            logger.critical(f"M{self.current_machine_id}: Failed to start detection: {e}")
            QMessageBox.critical(self, "Startup Error", f"Failed to start detection:\n{str(e)}")
            self.stop_detection()
    
    def stop_detection(self):
        """Stop detection"""
        logger.info("="*60)
        logger.info(f"STOPPING DETECTION FOR M{self.current_machine_id}")
        logger.info("="*60)
        
        self.running = False
        
        # Stop uptime timer
        if hasattr(self, 'uptime_timer'):
            self.uptime_timer.stop()
        
        # Log session stats
        if self.uptime_start:
            uptime_seconds = time.time() - self.uptime_start
            logger.info(f"Session uptime: {uptime_seconds:.0f} seconds")
            logger.info(f"Total detections: {self.detection_count}")
            logger.info(f"Total faults: {self.problem_count}")
            logger.info(f"Total errors: {self.error_count}")
            if self.detection_count > 0:
                success_rate = ((self.detection_count - self.problem_count) / self.detection_count) * 100
                logger.info(f"Success rate: {success_rate:.1f}%")
        
        # Disconnect signals
        if self.machine_controller:
            try:
                self.machine_controller.pair_status_changed.disconnect(self.on_pair_status_changed)
                self.machine_controller.detection_stats_updated.disconnect(self.on_detection_stats_updated)
            except:
                pass
        
        # Update UI
        self.start_btn.setText("Start Detection")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; min-width: 150px;")
        self.detection_label.clear()
        self.detection_label.setText("Detection View")
        self.overall_status.setText("System Status: Stopped")
        self.overall_status.setStyleSheet(
            "padding: 15px; font-size: 16px; font-weight: bold; "
            "background-color: #f0f0f0; border-radius: 5px;"
        )
        self.health_label.setText("System Health: Stopped")
        self.health_label.setStyleSheet(
            "padding: 10px; font-size: 12px; "
            "background-color: #F5F5F5; color: #666; border-radius: 5px;"
        )
        
        # Reset pair status labels
        for i, label in enumerate(self.pair_status_labels):
            label.setText(f"Pair {i + 1}: --")
            label.setStyleSheet(
                "padding: 10px; font-size: 11px; font-weight: bold; "
                "background-color: #cccccc; border-radius: 5px; min-width: 180px;"
            )
        
        # Reset relay status labels
        for i, label in enumerate(self.relay_status_labels):
            current_text = label.text().split(':')[0]
            label.setText(f"{current_text}: OFF")
            label.setStyleSheet(
                "padding: 8px; font-size: 10px; font-weight: bold; "
                "background-color: #E0E0E0; border-radius: 5px; min-width: 120px;"
            )
        
        logger.info(f"M{self.current_machine_id}: Detection stopped")
        logger.info("="*60)
    
    def on_frame_ready(self, machine_id, frame):
        """Handle frame from camera (called by main app)"""
        if machine_id != self.current_machine_id or not self.running:
            return
        
        try:
            # Draw boundaries on frame
            display_frame = self.draw_boundaries_on_frame(frame.copy())
            
            # Display frame
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(self.detection_label.size(), 
                                         Qt.KeepAspectRatio, 
                                         Qt.SmoothTransformation)
            self.detection_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Frame display error: {e}")
    
    def draw_boundaries_on_frame(self, frame):
        """Draw boundaries on frame (EXACT ORIGINAL STYLE)"""
        try:
            # Colors matching original
            oc_color = (255, 0, 0)  # Blue for oil can
            bh_color = (0, 165, 255)  # Orange for bunk hole
            
            # Draw oil can boundaries
            for i, boundary in enumerate(self.oil_can_boundaries):
                if len(boundary) >= 3:
                    pts = np.array(boundary, np.int32)
                    cv2.polylines(frame, [pts], True, oc_color, 2)
                    # Label
                    centroid = pts.mean(axis=0).astype(int)
                    cv2.putText(frame, f"OC{i+1}", tuple(centroid), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, oc_color, 2)
            
            # Draw bunk hole boundaries
            for i, boundary in enumerate(self.bunk_hole_boundaries):
                if len(boundary) >= 3:
                    pts = np.array(boundary, np.int32)
                    cv2.polylines(frame, [pts], True, bh_color, 2)
                    # Label
                    centroid = pts.mean(axis=0).astype(int)
                    cv2.putText(frame, f"BH{i+1}", tuple(centroid), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, bh_color, 2)
            
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Boundary drawing error: {e}")
        
        return frame
    
    def on_pair_status_changed(self, machine_id, pair_statuses):
        """Handle pair status change (EXACT ORIGINAL LOGIC)"""
        if machine_id != self.current_machine_id or not self.running:
            return
        
        try:
            # Get detection counts from machine controller
            detection_counts = self.machine_controller.detection_counts if self.machine_controller else {}
            
            # Update pair status labels
            for i, status in enumerate(pair_statuses):
                if i < len(self.pair_status_labels):
                    oc_count = detection_counts.get(f'pair{i+1}_oc', 0)
                    bh_count = detection_counts.get(f'pair{i+1}_bh', 0)
                    
                    if status == 'OK':
                        text = f"Pair {i + 1}: Both Present ✓"
                        color = "#4CAF50"
                        text_color = "white"
                    else:  # FAULT
                        if oc_count == 0 and bh_count == 0:
                            text = f"Pair {i + 1}: Both Absent ✗"
                        elif oc_count == 0:
                            text = f"Pair {i + 1}: OC Missing ✗"
                        elif bh_count == 0:
                            text = f"Pair {i + 1}: BH Missing ✗"
                        else:
                            text = f"Pair {i + 1}: Mismatch ✗"
                        color = "#F44336"
                        text_color = "white"
                    
                    self.pair_status_labels[i].setText(text)
                    self.pair_status_labels[i].setStyleSheet(
                        f"padding: 10px; font-size: 11px; font-weight: bold; "
                        f"background-color: {color}; color: {text_color}; "
                        f"border-radius: 5px; min-width: 180px;"
                    )
            
            # Update relay status labels
            pair_faults = [status != "OK" for status in pair_statuses]
            relay_config = self.relay_manager.get_machine_relay_config(machine_id) if self.relay_manager else []
            
            for i, is_fault in enumerate(pair_faults):
                if i < len(self.relay_status_labels):
                    relay_num = relay_config[i] if i < len(relay_config) else "?"
                    state_text = "ON" if is_fault else "OFF"
                    color = "#F44336" if is_fault else "#4CAF50"
                    text_color = "white"
                    
                    self.relay_status_labels[i].setText(f"R{relay_num} (Pair {i+1}): {state_text}")
                    self.relay_status_labels[i].setStyleSheet(
                        f"padding: 8px; font-size: 10px; font-weight: bold; "
                        f"background-color: {color}; color: {text_color}; "
                        f"border-radius: 5px; min-width: 120px;"
                    )
            
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Status update error: {e}")
    
    def on_detection_stats_updated(self, machine_id, stats):
        """Handle detection statistics update"""
        if machine_id != self.current_machine_id or not self.running:
            return
        
        try:
            self.detection_count = stats.get('total_detections', 0)
            self.problem_count = stats.get('fault_count', 0)
            
            self.detection_count_label.setText(f"Detections: {self.detection_count}")
            self.problem_count_label.setText(f"Faults: {self.problem_count}")
            
            # Update success rate
            if self.detection_count > 0:
                success_count = self.detection_count - self.problem_count
                success_rate = (success_count / self.detection_count) * 100
                self.success_rate_label.setText(f"Success Rate: {success_rate:.1f}%")
            
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Stats update error: {e}")
    
    def update_fps(self, fps):
        """Update FPS display"""
        if self.running:
            self.fps_label.setText(f"FPS: {fps:.1f}")
    
    def update_uptime(self):
        """Update uptime display (EXACT ORIGINAL)"""
        if self.uptime_start and self.running:
            uptime_seconds = int(time.time() - self.uptime_start)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60
            self.uptime_label.setText(f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def check_system_health(self):
        """Check system health (EXACT ORIGINAL)"""
        if not self.running:
            return
        
        try:
            # Check camera
            camera_ok = self.camera_thread and self.camera_thread.running
            
            # Check machine controller
            controller_ok = self.machine_controller is not None
            
            # Check relay
            relay_ok = self.relay_manager is not None
            
            if camera_ok and controller_ok and relay_ok:
                health_text = "System Health: All systems running"
                health_style = (
                    "padding: 10px; font-size: 12px; "
                    "background-color: #E8F5E8; color: #2E7D32; border-radius: 5px;"
                )
            else:
                issues = []
                if not camera_ok:
                    issues.append("Camera")
                if not controller_ok:
                    issues.append("Controller")
                if not relay_ok:
                    issues.append("Relay")
                
                health_text = f"System Health: Issues - {', '.join(issues)}"
                health_style = (
                    "padding: 10px; font-size: 12px; "
                    "background-color: #FFEBEE; color: #C62828; border-radius: 5px;"
                )
            
            self.health_label.setText(health_text)
            self.health_label.setStyleSheet(health_style)
            
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Health check error: {e}")