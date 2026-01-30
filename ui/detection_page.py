"""
Detection Page - EXACT ORIGINAL UI + Multi-Machine Support
Real-time detection monitoring with health metrics
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

# PASTE LINES 1162-1940 FROM ORIGINAL HERE
# (The entire DetectionPage class)

class DetectionPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.camera_thread = None
        self.detection_thread = None
        self.relay_thread = None
        self.watchdog = None
        self.boundaries = []
        self.oil_can_boundaries = []
        self.bunk_hole_boundaries = []
        self.model_path = None
        self.running = False
        self.detection_count = 0
        self.error_count = 0
        self.problem_count = 0
        self.detection_history = deque(maxlen=100)
        self.uptime_start = None
        self.load_boundaries()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("Detection - 4-Relay Pairing System (Problem Detection Mode)")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        controls_layout = QHBoxLayout()
        
        camera_type_layout = QVBoxLayout()
        self.camera_type_group = QButtonGroup()
        self.usb_radio = QRadioButton("USB")
        self.ip_radio = QRadioButton("IP Camera")
        self.usb_radio.setChecked(True)
        self.camera_type_group.addButton(self.usb_radio)
        self.camera_type_group.addButton(self.ip_radio)
        camera_type_layout.addWidget(self.usb_radio)
        camera_type_layout.addWidget(self.ip_radio)
        controls_layout.addLayout(camera_type_layout)
        
        self.camera_combo = QComboBox()
        self.refresh_cameras()
        controls_layout.addWidget(QLabel("USB:"))
        controls_layout.addWidget(self.camera_combo)
        
        controls_layout.addWidget(QLabel("RTSP:"))
        self.ip_url_input = QLineEdit()
        self.ip_url_input.setPlaceholderText("rtsp://admin:pass@192.168.1.64:554/stream")
        self.ip_url_input.setText("rtsp://admin:Pass_123@192.168.1.64:554/stream")
        self.ip_url_input.setMinimumWidth(300)
        controls_layout.addWidget(self.ip_url_input)
        
        self.usb_radio.toggled.connect(self.on_camera_type_changed)
        self.ip_radio.toggled.connect(self.on_camera_type_changed)

        self.load_model_btn = QPushButton("Load Model")
        self.load_model_btn.clicked.connect(self.load_model)
        controls_layout.addWidget(self.load_model_btn)
        
        self.start_btn = QPushButton("Start Detection")
        self.start_btn.clicked.connect(self.toggle_detection)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        controls_layout.addWidget(self.start_btn)
        
        layout.addLayout(controls_layout)
        
        self.detection_label = QLabel("Detection View")
        self.detection_label.setMinimumSize(800, 600)
        self.detection_label.setStyleSheet("border: 2px solid #333;")
        self.detection_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.detection_label)
        
        metrics_layout = QHBoxLayout()
        
        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet("padding: 5px; font-weight: bold; background-color: #E3F2FD;")
        metrics_layout.addWidget(self.fps_label)
        
        self.detection_count_label = QLabel("Detections: 0")
        self.detection_count_label.setStyleSheet("padding: 5px; font-weight: bold; background-color: #E3F2FD;")
        metrics_layout.addWidget(self.detection_count_label)
        
        self.problem_count_label = QLabel("Problems: 0")
        self.problem_count_label.setStyleSheet("padding: 5px; font-weight: bold; background-color: #FFEBEE;")
        metrics_layout.addWidget(self.problem_count_label)
        
        layout.addLayout(metrics_layout)
        
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
        
        relay_status_layout = QHBoxLayout()
        relay_label = QLabel("Relay Status:")
        relay_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        relay_status_layout.addWidget(relay_label)
        
        self.relay_status_labels = []
        relay_names = ["R1 (Pair 1)", "R2 (Pair 2)", "R3 (Pair 3)", "R4 (All OK)"]
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
        
        self.overall_status = QLabel("System Status: Idle")
        self.overall_status.setStyleSheet(
            "padding: 15px; font-size: 16px; font-weight: bold; "
            "background-color: #f0f0f0; border-radius: 5px;"
        )
        self.overall_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.overall_status)
        
        self.health_label = QLabel("System Health: Ready")
        self.health_label.setStyleSheet(
            "padding: 10px; font-size: 12px; "
            "background-color: #E8F5E8; color: #2E7D32; border-radius: 5px;"
        )
        layout.addWidget(self.health_label)
        
        stats_layout = QHBoxLayout()
        
        self.uptime_label = QLabel("Uptime: 00:00:00")
        self.uptime_label.setStyleSheet("padding: 5px; font-size: 11px; background-color: #F5F5F5;")
        stats_layout.addWidget(self.uptime_label)
        
        self.success_rate_label = QLabel("Success Rate: 100%")
        self.success_rate_label.setStyleSheet("padding: 5px; font-size: 11px; background-color: #F5F5F5;")
        stats_layout.addWidget(self.success_rate_label)
        
        layout.addLayout(stats_layout)
        
        self.setLayout(layout)
        
        self.uptime_timer = QTimer()
        self.uptime_timer.timeout.connect(self.update_uptime)
        
        self.health_check_timer = QTimer()
        self.health_check_timer.timeout.connect(self.check_system_health)
        self.health_check_timer.start(5000)
        
        self.on_camera_type_changed()

    def on_camera_type_changed(self):
        is_usb = self.usb_radio.isChecked()
        self.camera_combo.setEnabled(is_usb)
        self.ip_url_input.setEnabled(not is_usb)

    def refresh_cameras(self):
        self.camera_combo.clear()
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.camera_combo.addItem(f"Camera {i}")
                cap.release()

    def load_boundaries(self):
        try:
            if os.path.exists('boundaries.json'):
                with open('boundaries.json', 'r') as f:
                    data = json.load(f)
                
                self.oil_can_boundaries = data.get('oil_can_boundaries', [])
                self.bunk_hole_boundaries = data.get('bunk_hole_boundaries', [])
                self.boundaries = data.get('all_boundaries', [])
                self.reference_frame_shape = data.get('frame_shape', None)
                
                logger.info(f"Boundaries loaded: {len(self.oil_can_boundaries)} oil cans, {len(self.bunk_hole_boundaries)} bunk holes")
            else:
                logger.warning("No boundaries file found")
                QMessageBox.warning(self, "Warning", "No boundaries found. Please train first!")
        except Exception as e:
            logger.error(f"Failed to load boundaries: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load boundaries: {str(e)}")

    def load_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select YOLO Model", "", "YOLO Model (*.pt *.onnx *.engine);;All Files (*)"
        )
        
        if file_path:
            self.model_path = file_path
            self.start_btn.setEnabled(True)
            logger.info(f"Model selected: {file_path}")
            QMessageBox.information(self, "Success", f"Model loaded: {os.path.basename(file_path)}")

    def toggle_detection(self):
        if self.running:
            self.stop_detection()
        else:
            self.start_detection()

    def start_detection(self):
        if not self.model_path:
            QMessageBox.warning(self, "Error", "Please load a model first!")
            return
        
        if not self.boundaries:
            QMessageBox.warning(self, "Error", "No boundaries defined!")
            return
        
        try:
            logger.info("="*60)
            logger.info("STARTING 4-RELAY DETECTION SYSTEM")
            logger.info("="*60)
            
            self.detection_count = 0
            self.error_count = 0
            self.problem_count = 0
            self.detection_history.clear()
            self.uptime_start = time.time()
            
            if self.usb_radio.isChecked():
                camera_source = self.camera_combo.currentIndex()
                camera_desc = f"USB Camera {camera_source}"
            else:
                camera_source = self.ip_url_input.text().strip()
                if not camera_source:
                    QMessageBox.warning(self, "Error", "Please enter RTSP URL!")
                    return
                if not camera_source.startswith("rtsp://"):
                    QMessageBox.warning(self, "Error", "Invalid RTSP URL! Must start with rtsp://")
                    return
                camera_desc = "IP Camera (RTSP)"
            
            logger.info(f"Starting camera thread for: {camera_desc}")
            self.camera_thread = CameraThread(camera_source)
            self.camera_thread.frame_ready.connect(self.on_frame_ready)
            self.camera_thread.error_signal.connect(self.handle_error)
            self.camera_thread.status_signal.connect(self.update_camera_status)
            self.camera_thread.start()

            logger.info("Waiting for camera to initialize...")
            camera_wait_deadline = time.time() + 15.0
            camera_ok = False
            while time.time() < camera_wait_deadline:
                if getattr(self.camera_thread, 'camera', None) and self.camera_thread.camera.isOpened():
                    camera_ok = True
                    logger.info("Camera initialized successfully")
                    break
                time.sleep(0.2)

            if not camera_ok:
                raise Exception("Camera failed to initialize within 15 seconds")
            
            model_size_mb = os.path.getsize(self.model_path) / (1024 ** 2)
            watchdog_timeout = max(CONFIG["detection"]["watchdog_timeout_base"], int(model_size_mb / 5))
            logger.info(f"Model size: {model_size_mb:.1f}MB, Watchdog timeout: {watchdog_timeout}s")
            
            logger.info("Starting detection thread...")
            self.detection_thread = DetectionThread(self.model_path, self.boundaries)
            self.detection_thread.detection_ready.connect(self.on_detection_ready)
            self.detection_thread.error_signal.connect(self.handle_error)
            self.detection_thread.fps_signal.connect(self.update_fps)
            self.detection_thread.start()

            logger.info("Waiting for model to load...")
            model_wait_deadline = time.time() + 30.0
            model_ok = False
            while time.time() < model_wait_deadline:
                if getattr(self.detection_thread, 'model', None):
                    model_ok = True
                    logger.info("Model loaded successfully")
                    break
                time.sleep(0.5)

            if not model_ok:
                raise Exception("YOLO model failed to load within 30 seconds")
            
            logger.info("Starting relay control thread (4-relay mode)...")
            self.relay_thread = RelayControlThread()
            self.relay_thread.error_signal.connect(self.handle_relay_error)
            self.relay_thread.status_signal.connect(self.update_relay_status)
            self.relay_thread.start()
            
            logger.info(f"Starting watchdog timer (timeout: {watchdog_timeout}s)...")
            self.watchdog = WatchdogTimer("Detection System", timeout_seconds=watchdog_timeout)
            self.watchdog.timeout_signal.connect(self.handle_watchdog_timeout)
            self.watchdog.start()
            
            self.uptime_timer.start(1000)
            
            self.running = True
            self.start_btn.setText("Stop Detection")
            self.start_btn.setStyleSheet("background-color: #F44336; color: white; padding: 10px;")
            self.overall_status.setText("System Status: Running")
            self.overall_status.setStyleSheet(
                "padding: 15px; font-size: 16px; font-weight: bold; "
                "background-color: #4CAF50; color: white; border-radius: 5px;"
            )
            self.health_label.setText("System Health: All threads running")
            self.health_label.setStyleSheet(
                "padding: 10px; font-size: 12px; "
                "background-color: #E8F5E8; color: #2E7D32; border-radius: 5px;"
            )
            
            logger.info("="*60)
            logger.info("4-RELAY DETECTION SYSTEM STARTED")
            logger.info(f"Camera: {camera_desc}")
            logger.info(f"Model: {os.path.basename(self.model_path)}")
            logger.info(f"Watchdog timeout: {watchdog_timeout}s")
            logger.info(f"Boundaries: {len(self.oil_can_boundaries)} oil cans, {len(self.bunk_hole_boundaries)} bunk holes")
            logger.info("Relay Logic: R1=Pair1 Problem, R2=Pair2 Problem, R3=Pair3 Problem, R4=All OK")
            logger.info("="*60)
            
        except Exception as e:
            logger.critical(f"Failed to start detection: {e}")
            logger.critical(traceback.format_exc())
            QMessageBox.critical(self, "Startup Error", f"Failed to start system:\n{str(e)}\n\nCheck logs for details.")
            self.stop_detection()

    def stop_detection(self):
        logger.info("="*60)
        logger.info("STOPPING DETECTION SYSTEM")
        logger.info("="*60)
        
        self.running = False
        
        if hasattr(self, 'uptime_timer'):
            self.uptime_timer.stop()
        
        if self.uptime_start:
            uptime_seconds = time.time() - self.uptime_start
            logger.info(f"Session uptime: {uptime_seconds:.0f} seconds")
            logger.info(f"Total detections: {self.detection_count}")
            logger.info(f"Total problems: {self.problem_count}")
            logger.info(f"Total errors: {self.error_count}")
            if self.detection_count > 0:
                success_rate = ((self.detection_count - self.problem_count) / self.detection_count) * 100
                logger.info(f"Success rate: {success_rate:.1f}%")
        
        threads_to_stop = [
            ("Watchdog", self.watchdog),
            ("Camera", self.camera_thread),
            ("Detection", self.detection_thread),
            ("Relay", self.relay_thread)
        ]
        
        for name, thread in threads_to_stop:
            if thread:
                try:
                    logger.info(f"Stopping {name} thread...")
                    thread.stop()
                    if not thread.wait(3000):
                        logger.warning(f"{name} thread did not stop gracefully")
                except Exception as e:
                    logger.error(f"Error stopping {name} thread: {e}")
        
        self.watchdog = None
        self.camera_thread = None
        self.detection_thread = None
        self.relay_thread = None
        
        self.start_btn.setText("Start Detection")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
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
        
        for label in self.pair_status_labels:
            label.setText(label.text().split(':')[0] + ": --")
            label.setStyleSheet(
                "padding: 10px; font-size: 11px; font-weight: bold; "
                "background-color: #cccccc; border-radius: 5px; min-width: 180px;"
            )
        
        for i, label in enumerate(self.relay_status_labels):
            relay_names = ["R1 (Pair 1)", "R2 (Pair 2)", "R3 (Pair 3)", "R4 (All OK)"]
            label.setText(f"{relay_names[i]}: OFF")
            label.setStyleSheet(
                "padding: 8px; font-size: 10px; font-weight: bold; "
                "background-color: #E0E0E0; border-radius: 5px; min-width: 120px;"
            )
        
        logger.info("Detection system stopped successfully")
        logger.info("="*60)

    def on_frame_ready(self, frame):
        """Fixed: Added frame dimension validation"""
        if self.detection_thread and self.running:
            try:
                if hasattr(self, 'reference_frame_shape') and self.reference_frame_shape:
                    ref_h, ref_w = int(self.reference_frame_shape[0]), int(self.reference_frame_shape[1])
                    h, w = frame.shape[0], frame.shape[1]
                    
                    # Validate dimensions
                    if ref_h <= 0 or ref_w <= 0 or h <= 0 or w <= 0:
                        logger.warning(f"Invalid frame dimensions: frame=({h},{w}), ref=({ref_h},{ref_w})")
                        return
                    
                    if (h, w) != (ref_h, ref_w):
                        resized = cv2.resize(frame, (ref_w, ref_h), interpolation=cv2.INTER_LINEAR)
                        self.detection_thread.add_frame(resized)
                    else:
                        self.detection_thread.add_frame(frame)
                else:
                    self.detection_thread.add_frame(frame)
            except Exception as e:
                logger.error(f"Frame resize/forward error: {e}")
            
            if self.watchdog:
                self.watchdog.heartbeat()

    def on_detection_ready(self, result):
        try:
            self.detection_count += 1
            self.detection_count_label.setText(f"Detections: {self.detection_count}")
            
            all_ok = result['all_ok']
            pair_statuses = result['pair_statuses']
            problem_pairs = result['problem_pairs']
            
            if not all_ok:
                self.problem_count += 1
                self.problem_count_label.setText(f"Problems: {self.problem_count}")
            
            self.detection_history.append(all_ok)
            
            if len(self.detection_history) > 0:
                success_count = sum(self.detection_history)
                success_rate = (success_count / len(self.detection_history)) * 100
                self.success_rate_label.setText(f"Success Rate: {success_rate:.1f}%")
            
            # Update pair status labels
            for i, pair_status in enumerate(pair_statuses):
                if i < len(self.pair_status_labels):
                    oc_present = pair_status['oc_present']
                    bh_present = pair_status['bh_present']
                    status = pair_status['status']
                    
                    if status == 'ok':
                        text = f"Pair {i + 1}: Both Present ✓"
                        color = "#4CAF50"
                        text_color = "white"
                    elif status == 'both_absent':
                        text = f"Pair {i + 1}: Both Absent ✗"
                        color = "#F44336"
                        text_color = "white"
                    elif status == 'oc_missing':
                        text = f"Pair {i + 1}: OC Missing ✗"
                        color = "#F44336"
                        text_color = "white"
                    else:  # bh_missing
                        text = f"Pair {i + 1}: BH Missing ✗"
                        color = "#F44336"
                        text_color = "white"
                    
                    self.pair_status_labels[i].setText(text)
                    self.pair_status_labels[i].setStyleSheet(
                        f"padding: 10px; font-size: 11px; font-weight: bold; "
                        f"background-color: {color}; color: {text_color}; "
                        f"border-radius: 5px; min-width: 180px;"
                    )
            
            # Update relay status labels
            relay_states = {
                'pair1_ok': pair_statuses[0]['ok'] if len(pair_statuses) > 0 else True,
                'pair2_ok': pair_statuses[1]['ok'] if len(pair_statuses) > 1 else True,
                'pair3_ok': pair_statuses[2]['ok'] if len(pair_statuses) > 2 else True,
                'all_ok': all_ok
            }
            
            # Update UI relay indicators
            relay_names = ["R1 (Pair 1)", "R2 (Pair 2)", "R3 (Pair 3)", "R4 (All OK)"]
            relay_active = [
                not relay_states['pair1_ok'],  # R1 ON when pair 1 has problem
                not relay_states['pair2_ok'],  # R2 ON when pair 2 has problem
                not relay_states['pair3_ok'],  # R3 ON when pair 3 has problem
                relay_states['all_ok']         # R4 ON when all OK
            ]
            
            for i, (name, active) in enumerate(zip(relay_names, relay_active)):
                if active:
                    self.relay_status_labels[i].setText(f"{name}: ON")
                    if i < 3:  # Problem relays (R1, R2, R3)
                        self.relay_status_labels[i].setStyleSheet(
                            "padding: 8px; font-size: 10px; font-weight: bold; "
                            "background-color: #F44336; color: white; border-radius: 5px; min-width: 120px;"
                        )
                    else:  # All OK relay (R4)
                        self.relay_status_labels[i].setStyleSheet(
                            "padding: 8px; font-size: 10px; font-weight: bold; "
                            "background-color: #4CAF50; color: white; border-radius: 5px; min-width: 120px;"
                        )
                else:
                    self.relay_status_labels[i].setText(f"{name}: OFF")
                    self.relay_status_labels[i].setStyleSheet(
                        "padding: 8px; font-size: 10px; font-weight: bold; "
                        "background-color: #E0E0E0; color: #666; border-radius: 5px; min-width: 120px;"
                    )
            
            # Update overall status
            if all_ok:
                overall_text = "All Pairs OK - Production Running Normally"
                overall_color = "#4CAF50"
                logger.debug(f"Detection #{self.detection_count}: All Pairs OK")
            else:
                problem_details = []
                for problem in problem_pairs:
                    pair_idx = problem['pair_index']
                    status = problem['status']
                    if status == 'both_absent':
                        problem_details.append(f"P{pair_idx}:Both Absent")
                    elif status == 'oc_missing':
                        problem_details.append(f"P{pair_idx}:OC Missing")
                    else:  # bh_missing
                        problem_details.append(f"P{pair_idx}:BH Missing")
                
                overall_text = f"Problems Detected: {', '.join(problem_details)}"
                overall_color = "#F44336"
                logger.warning(f"Detection #{self.detection_count}: Problems {problem_details}")
            
            self.overall_status.setText(overall_text)
            self.overall_status.setStyleSheet(
                f"padding: 15px; font-size: 16px; font-weight: bold; "
                f"background-color: {overall_color}; color: white; border-radius: 5px;"
            )
            
            # Send relay command
            if self.relay_thread:
                self.relay_thread.set_state(relay_states)
            
            self.draw_frame(result)
            
            if self.watchdog:
                self.watchdog.heartbeat()
            
            if self.detection_count % 100 == 0:
                logger.info(f"Milestone: {self.detection_count} detections completed")
            
        except Exception as e:
            logger.error(f"Error processing detection result: {e}")
            logger.error(traceback.format_exc())
            self.error_count += 1

    def draw_frame(self, result):
        try:
            frame = result['frame'].copy()
            pair_statuses = result['pair_statuses']
            
            # Draw oil can boundaries
            for i, boundary in enumerate(self.oil_can_boundaries):
                if i < len(pair_statuses):
                    status = pair_statuses[i]['status']
                    if status == 'ok':
                        color = (0, 255, 0)  # Green = OK
                    else:
                        color = (0, 0, 255)  # Red = Problem
                else:
                    color = (255, 0, 0)
                
                if 'polygon' in boundary and boundary.get('polygon'):
                    pts = np.array(boundary['polygon'], dtype=np.int32)
                    cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=3)
                    x0, y0 = pts[0]
                    cv2.putText(frame, f"OC{i + 1}", (int(x0), int(y0) - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Draw bunk hole boundaries
            for i, boundary in enumerate(self.bunk_hole_boundaries):
                if i < len(pair_statuses):
                    status = pair_statuses[i]['status']
                    if status == 'ok':
                        color = (0, 255, 0)  # Green = OK
                    else:
                        color = (0, 0, 255)  # Red = Problem
                else:
                    color = (0, 165, 255)
                
                if 'polygon' in boundary and boundary.get('polygon'):
                    pts = np.array(boundary['polygon'], dtype=np.int32)
                    cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=3)
                    x0, y0 = pts[0]
                    cv2.putText(frame, f"BH{i + 1}", (int(x0), int(y0) - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Draw detected objects
            for obj in result.get('oil_cans', []):
                x1, y1, x2, y2 = obj['bbox']
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                cv2.putText(frame, f"Oil: {obj['confidence']:.2f}",
                    (int(x1), int(y1) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            for obj in result.get('bunk_holes', []):
                x1, y1, x2, y2 = obj['bbox']
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 165, 255), 2)
                cv2.putText(frame, f"Bunk: {obj['confidence']:.2f}",
                    (int(x1), int(y1) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
            
            # Draw timestamp
            timestamp = datetime.fromtimestamp(result['timestamp']).strftime('%H:%M:%S')
            cv2.putText(frame, timestamp, (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Draw status
            status_text = "ALL OK" if result['all_ok'] else "PROBLEM"
            status_color = (0, 255, 0) if result['all_ok'] else (0, 0, 255)
            cv2.putText(frame, status_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, status_color, 3)
            
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(
                self.detection_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.detection_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            logger.error(f"Error drawing frame: {e}")

    def update_fps(self, fps):
        self.fps_label.setText(f"FPS: {fps:.1f}")

    def update_relay_status(self, status):
        pass  # Individual relay status now handled in on_detection_ready
    
    def update_camera_status(self, status):
        logger.info(f"Camera status: {status}")

    def handle_error(self, error):
        self.error_count += 1
        logger.error(f"Thread error: {error}")
        self.health_label.setText(f"Error: {error[:50]}...")
        self.health_label.setStyleSheet(
            "padding: 10px; font-size: 12px; "
            "background-color: #FFEBEE; color: #C62828; border-radius: 5px;"
        )
        
        if self.error_count > 0 and self.error_count % 3 == 0:
            logger.warning(f"Multiple errors detected ({self.error_count}), attempting recovery...")
            QTimer.singleShot(2000, self.attempt_recovery)
    
    def handle_relay_error(self, error):
        logger.error(f"Relay error: {error}")

    def handle_watchdog_timeout(self, name):
        logger.critical(f"WATCHDOG TIMEOUT: {name} - System frozen detected!")
        logger.critical("Initiating emergency recovery...")
        
        QMessageBox.critical(
            self, "System Frozen",
            f"Detection system has frozen!\n\n"
            f"Component: {name}\n"
            f"Action: Automatic restart in 3 seconds..."
        )
        
        self.stop_detection()
        QTimer.singleShot(3000, self.attempt_recovery)
    
    def attempt_recovery(self):
        if not self.running:
            logger.info("Attempting automatic system recovery...")
            try:
                self.start_detection()
                logger.info("Recovery successful")
                QMessageBox.information(self, "Recovery", "System recovered and restarted successfully!")
            except Exception as e:
                logger.error(f"Recovery failed: {e}")
                QMessageBox.critical(self, "Recovery Failed", f"Automatic recovery failed:\n{str(e)}\n\nManual intervention required.")
    
    def update_uptime(self):
        if self.uptime_start:
            uptime_seconds = int(time.time() - self.uptime_start)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60
            self.uptime_label.setText(f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def check_system_health(self):
        if not self.running:
            return
        
        health_issues = []
        
        if not self.camera_thread or not self.camera_thread.isRunning():
            health_issues.append("Camera thread dead")
        
        if not self.detection_thread or not self.detection_thread.isRunning():
            health_issues.append("Detection thread dead")
        
        if not self.relay_thread or not self.relay_thread.isRunning():
            health_issues.append("Relay thread dead")
        
        if not self.watchdog or not self.watchdog.isRunning():
            health_issues.append("Watchdog dead")
        
        current_fps_text = self.fps_label.text()
        try:
            fps_value = float(current_fps_text.split(':')[1].strip())
            if fps_value < 1.0:
                health_issues.append("Low FPS")
        except:
            pass
        
        if health_issues:
            health_text = f"Issues: {', '.join(health_issues)}"
            logger.warning(f"System health check - {health_text}")
            self.health_label.setText(health_text)
            self.health_label.setStyleSheet(
                "padding: 10px; font-size: 12px; "
                "background-color: #FFF3E0; color: #E65100; border-radius: 5px;"
            )
            
            if len(health_issues) >= 2:
                logger.error("Critical system health issues detected!")
                self.attempt_recovery()
        else:
            if self.problem_count == 0:
                self.health_label.setText("System Health: Excellent")
                self.health_label.setStyleSheet(
                    "padding: 10px; font-size: 12px; "
                    "background-color: #E8F5E8; color: #2E7D32; border-radius: 5px;"
                )
            else:
                self.health_label.setText(f"System Health: Good ({self.problem_count} problems detected)")
                self.health_label.setStyleSheet(
                    "padding: 10px; font-size: 12px; "
                    "background-color: #E8F5E8; color: #2E7D32; border-radius: 5px;"
                )

    def closeEvent(self, event):
        logger.info("Application close requested")
        
        if self.running:
            reply = QMessageBox.question(
                self, 'Confirm Exit',
                'Detection is running. Are you sure you want to exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        self.stop_detection()
        
        if hasattr(self, 'health_check_timer'):
            self.health_check_timer.stop()
        
        event.accept()
        logger.info("Detection page closed")
