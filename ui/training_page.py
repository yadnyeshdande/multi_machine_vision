"""
Training Page - EXACT ORIGINAL UI + Multi-Machine Support
Draw boundaries for selected machine with camera connection
"""
import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import json
import os
import logging

logger = logging.getLogger(__name__)


class DrawingWidget(QLabel):
    """
    EXACT ORIGINAL: Widget for interactive polygon drawing on camera frames
    """
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: black; border: 2px solid #333;")
        self.setAlignment(Qt.AlignCenter)
        
        # CRITICAL: Initialize current_points (was missing in original causing crash)
        self.current_points = []
        self.all_boundaries = {}
        self.current_boundary_key = None
        self.image = None
        self.original_image = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        
        # Colors for different boundaries (EXACT ORIGINAL)
        self.colors = {
            "pair1_oc": (0, 255, 0),      # Green
            "pair1_bh": (255, 0, 0),      # Blue  
            "pair2_oc": (0, 255, 255),    # Yellow
            "pair2_bh": (255, 0, 255),    # Magenta
            "pair3_oc": (0, 165, 255),    # Orange
            "pair3_bh": (255, 255, 0),    # Cyan
        }
    
    def set_image(self, image):
        """Set image for boundary drawing"""
        if image is None or image.size == 0:
            logger.warning("Invalid image provided to DrawingWidget")
            return False
            
        try:
            self.original_image = image.copy()
            self.image = image.copy()
            self.update_display()
            return True
        except Exception as e:
            logger.error(f"Failed to set image: {e}")
            return False
    
    def update_display(self):
        """Update the display with current drawing state"""
        if self.original_image is None:
            return
        
        try:
            # Start with original image
            display_image = self.original_image.copy()
            
            # Draw all completed boundaries
            for key, points in self.all_boundaries.items():
                if len(points) >= 3:
                    color = self.colors.get(key, (255, 255, 255))
                    pts = np.array(points, np.int32)
                    
                    # Draw filled polygon with transparency
                    overlay = display_image.copy()
                    cv2.fillPoly(overlay, [pts], color)
                    cv2.addWeighted(overlay, 0.3, display_image, 0.7, 0, display_image)
                    
                    # Draw boundary
                    cv2.polylines(display_image, [pts], True, color, 2)
                    
                    # Draw label
                    centroid = pts.mean(axis=0).astype(int)
                    label = key.replace("_", " ").upper()
                    cv2.putText(display_image, label, tuple(centroid), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Draw current boundary being drawn
            if len(self.current_points) > 0:
                color = self.colors.get(self.current_boundary_key, (0, 255, 0))
                
                # Draw points
                for point in self.current_points:
                    cv2.circle(display_image, point, 5, color, -1)
                
                # Draw lines
                if len(self.current_points) > 1:
                    for i in range(len(self.current_points) - 1):
                        cv2.line(display_image, self.current_points[i], 
                                self.current_points[i + 1], color, 2)
                
                # Draw closing line if more than 2 points
                if len(self.current_points) > 2:
                    cv2.line(display_image, self.current_points[-1], 
                            self.current_points[0], color, 1, cv2.LINE_AA)
            
            # Convert to QPixmap and display
            display_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
            h, w, ch = display_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(display_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Calculate scale factors for coordinate conversion
            self.scale_x = pixmap.width() / scaled_pixmap.width() if scaled_pixmap.width() > 0 else 1.0
            self.scale_y = pixmap.height() / scaled_pixmap.height() if scaled_pixmap.height() > 0 else 1.0
            
            self.setPixmap(scaled_pixmap)
            
        except Exception as e:
            logger.error(f"Display update error: {e}")
    
    def start_drawing(self, boundary_key):
        """Start drawing a new boundary"""
        if self.image is None:
            logger.warning("No image loaded for drawing")
            return False
        
        self.current_boundary_key = boundary_key
        self.current_points = []
        logger.info(f"Started drawing: {boundary_key}")
        self.update_display()
        return True
    
    def mousePressEvent(self, event):
        """Handle mouse clicks for adding polygon points"""
        if event.button() != Qt.LeftButton or self.current_boundary_key is None:
            return
        
        if self.image is None:
            return
        
        try:
            pixmap = self.pixmap()
            if pixmap is None:
                return
            
            # Get click position relative to the label
            click_x = event.pos().x()
            click_y = event.pos().y()
            
            # Calculate pixmap position in label (centered)
            pixmap_x = (self.width() - pixmap.width()) // 2
            pixmap_y = (self.height() - pixmap.height()) // 2
            
            # Convert to pixmap coordinates
            rel_x = click_x - pixmap_x
            rel_y = click_y - pixmap_y
            
            # Check if click is within pixmap
            if rel_x < 0 or rel_y < 0 or rel_x >= pixmap.width() or rel_y >= pixmap.height():
                return
            
            # Scale to original image coordinates
            img_x = int(rel_x * self.scale_x)
            img_y = int(rel_y * self.scale_y)
            
            # Clamp to image bounds
            img_x = max(0, min(img_x, self.original_image.shape[1] - 1))
            img_y = max(0, min(img_y, self.original_image.shape[0] - 1))
            
            self.current_points.append((img_x, img_y))
            self.update_display()
            
            logger.debug(f"Added point: ({img_x}, {img_y})")
            
        except Exception as e:
            logger.error(f"Mouse click error: {e}")
    
    def finish_boundary(self):
        """Finish current boundary"""
        if self.current_boundary_key is None:
            return False
        
        if len(self.current_points) < 3:
            QMessageBox.warning(self, "Invalid Boundary", 
                              "Need at least 3 points to create a boundary!")
            return False
        
        # Validate coordinates
        if not self._validate_polygon(self.current_points):
            QMessageBox.warning(self, "Invalid Boundary",
                              "Boundary coordinates are invalid!")
            return False
        
        self.all_boundaries[self.current_boundary_key] = self.current_points.copy()
        logger.info(f"Finished {self.current_boundary_key}: {len(self.current_points)} points")
        
        self.current_points = []
        self.current_boundary_key = None
        self.update_display()
        return True
    
    def _validate_polygon(self, points):
        """Validate polygon coordinates"""
        if len(points) < 3:
            return False
        
        for x, y in points:
            if x < 0 or y < 0:
                return False
            if self.original_image is not None:
                if x >= self.original_image.shape[1] or y >= self.original_image.shape[0]:
                    return False
        return True
    
    def undo_last_point(self):
        """Remove last point from current drawing"""
        if len(self.current_points) > 0:
            self.current_points.pop()
            self.update_display()
            logger.debug("Undid last point")
    
    def clear_current(self):
        """Clear current drawing"""
        self.current_points = []
        self.update_display()
        logger.debug("Cleared current drawing")
    
    def clear_boundary(self, boundary_key):
        """Clear a specific boundary"""
        if boundary_key in self.all_boundaries:
            del self.all_boundaries[boundary_key]
            self.update_display()
            logger.info(f"Cleared boundary: {boundary_key}")
    
    def clear_all(self):
        """Clear all boundaries"""
        self.all_boundaries = {}
        self.current_points = []
        self.current_boundary_key = None
        self.update_display()
        logger.info("Cleared all boundaries")
    
    def get_boundaries(self):
        """Get all boundaries"""
        return self.all_boundaries.copy()
    
    def set_boundaries(self, boundaries):
        """Set boundaries from saved data"""
        self.all_boundaries = boundaries.copy()
        self.update_display()
        logger.info(f"Loaded {len(boundaries)} boundaries")


class TrainingPage(QWidget):
    """
    EXACT ORIGINAL: Training page with camera connection + Multi-machine support
    """
    
    # Signal to request camera connection for specific machine
    connect_camera_requested = pyqtSignal(int, str)  # machine_id, camera_source
    disconnect_camera_requested = pyqtSignal(int)  # machine_id
    
    def __init__(self):
        super().__init__()
        self.current_machine_id = None
        self.current_machine_name = "No Machine Selected"
        self.current_camera_source = None
        self.camera_connected = False
        self.camera_thread = None  # Will be set by main app
        
        self.init_ui()
    
    def init_ui(self):
        """EXACT ORIGINAL UI Layout"""
        main_layout = QVBoxLayout()
        
        # ===== TOP PANEL: Machine Info & Controls =====
        top_panel = QHBoxLayout()
        
        # Machine label
        self.machine_label = QLabel("Training: No Machine Selected")
        self.machine_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        top_panel.addWidget(self.machine_label)
        
        top_panel.addStretch()
        
        # Camera controls
        camera_group = QGroupBox("Camera")
        camera_layout = QHBoxLayout()
        
        self.camera_input = QLineEdit()
        self.camera_input.setPlaceholderText("Camera source (RTSP URL or USB index)")
        self.camera_input.setMinimumWidth(300)
        camera_layout.addWidget(self.camera_input)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumWidth(100)
        self.connect_btn.clicked.connect(self.toggle_camera_connection)
        camera_layout.addWidget(self.connect_btn)
        
        self.camera_status_label = QLabel("● Disconnected")
        self.camera_status_label.setStyleSheet("color: red; font-weight: bold;")
        camera_layout.addWidget(self.camera_status_label)
        
        camera_group.setLayout(camera_layout)
        top_panel.addWidget(camera_group)
        
        main_layout.addLayout(top_panel)
        
        # ===== MIDDLE PANEL: Drawing Area + Controls =====
        middle_layout = QHBoxLayout()
        
        # LEFT: Drawing widget
        self.drawing_widget = DrawingWidget()
        middle_layout.addWidget(self.drawing_widget, stretch=3)
        
        # RIGHT: Control panel
        control_panel = QWidget()
        control_layout = QVBoxLayout()
        
        # Capture button
        self.capture_btn = QPushButton("📷 Capture Frame")
        self.capture_btn.setMinimumHeight(50)
        self.capture_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.capture_btn.clicked.connect(self.capture_frame)
        self.capture_btn.setEnabled(False)
        control_layout.addWidget(self.capture_btn)
        
        # Separator
        control_layout.addWidget(self._create_separator())
        
        # Instructions
        instructions = QLabel(
            "<b>Instructions:</b><br>"
            "1. Connect camera<br>"
            "2. Capture frame<br>"
            "3. Select boundary<br>"
            "4. Click to add points<br>"
            "5. Finish boundary<br>"
            "6. Repeat for all 6<br>"
            "7. Save boundaries"
        )
        instructions.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        instructions.setWordWrap(True)
        control_layout.addWidget(instructions)
        
        control_layout.addWidget(self._create_separator())
        
        # Boundary selection
        boundary_label = QLabel("Select Boundary to Draw:")
        boundary_label.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(boundary_label)
        
        self.boundary_buttons = {}
        boundaries = [
            ("pair1_oc", "Pair 1 - Oil Can", "#00ff00"),
            ("pair1_bh", "Pair 1 - Bunk Hole", "#ff0000"),
            ("pair2_oc", "Pair 2 - Oil Can", "#00ffff"),
            ("pair2_bh", "Pair 2 - Bunk Hole", "#ff00ff"),
            ("pair3_oc", "Pair 3 - Oil Can", "#ffa500"),
            ("pair3_bh", "Pair 3 - Bunk Hole", "#ffff00"),
        ]
        
        for key, label, color in boundaries:
            btn = QPushButton(f"🔲 {label}")
            btn.setStyleSheet(f"text-align: left; padding: 8px; border-left: 4px solid {color};")
            btn.clicked.connect(lambda checked, k=key: self.start_drawing(k))
            btn.setEnabled(False)
            control_layout.addWidget(btn)
            self.boundary_buttons[key] = btn
        
        control_layout.addWidget(self._create_separator())
        
        # Drawing controls
        btn_layout = QGridLayout()
        
        self.finish_btn = QPushButton("✓ Finish Boundary")
        self.finish_btn.clicked.connect(self.finish_boundary)
        self.finish_btn.setEnabled(False)
        btn_layout.addWidget(self.finish_btn, 0, 0)
        
        self.undo_btn = QPushButton("↶ Undo Point")
        self.undo_btn.clicked.connect(self.drawing_widget.undo_last_point)
        self.undo_btn.setEnabled(False)
        btn_layout.addWidget(self.undo_btn, 0, 1)
        
        self.clear_current_btn = QPushButton("✗ Clear Current")
        self.clear_current_btn.clicked.connect(self.drawing_widget.clear_current)
        self.clear_current_btn.setEnabled(False)
        btn_layout.addWidget(self.clear_current_btn, 1, 0)
        
        self.clear_all_btn = QPushButton("🗑 Clear All")
        self.clear_all_btn.clicked.connect(self.confirm_clear_all)
        self.clear_all_btn.setEnabled(False)
        btn_layout.addWidget(self.clear_all_btn, 1, 1)
        
        control_layout.addLayout(btn_layout)
        
        control_layout.addStretch()
        
        # Save button
        self.save_btn = QPushButton("💾 Save Boundaries")
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setStyleSheet(
            "font-size: 14px; font-weight: bold; "
            "background-color: #4CAF50; color: white;"
        )
        self.save_btn.clicked.connect(self.save_boundaries)
        self.save_btn.setEnabled(False)
        control_layout.addWidget(self.save_btn)
        
        control_panel.setLayout(control_layout)
        control_panel.setMaximumWidth(300)
        middle_layout.addWidget(control_panel, stretch=1)
        
        main_layout.addLayout(middle_layout)
        
        self.setLayout(main_layout)
    
    def _create_separator(self):
        """Create horizontal separator line"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line
    
    def set_machine(self, machine_id, machine_name, camera_source):
        """Set which machine to configure"""
        # Disconnect previous camera if any
        if self.camera_connected:
            self.toggle_camera_connection()
        
        self.current_machine_id = machine_id
        self.current_machine_name = machine_name
        self.current_camera_source = camera_source
        
        self.machine_label.setText(f"Training: Machine {machine_id} - {machine_name}")
        self.camera_input.setText(camera_source)
        
        # Load existing boundaries if any
        self.load_boundaries()
        
        logger.info(f"Training page set to M{machine_id}: {machine_name}")
    
    def toggle_camera_connection(self):
        """Toggle camera connection"""
        if not self.camera_connected:
            # Connect
            camera_source = self.camera_input.text().strip()
            if not camera_source:
                QMessageBox.warning(self, "No Camera Source", 
                                  "Please enter a camera source (RTSP URL or USB index)")
                return
            
            # Try to parse USB index
            try:
                camera_source = int(camera_source)
            except:
                pass
            
            # Request connection from main app
            self.connect_camera_requested.emit(self.current_machine_id, camera_source)
        else:
            # Disconnect
            self.disconnect_camera_requested.emit(self.current_machine_id)
    
    def on_camera_connected(self):
        """Called when camera successfully connects"""
        self.camera_connected = True
        self.camera_status_label.setText("● Connected")
        self.camera_status_label.setStyleSheet("color: green; font-weight: bold;")
        self.connect_btn.setText("Disconnect")
        self.capture_btn.setEnabled(True)
        logger.info(f"M{self.current_machine_id}: Camera connected")
    
    def on_camera_disconnected(self):
        """Called when camera disconnects"""
        self.camera_connected = False
        self.camera_status_label.setText("● Disconnected")
        self.camera_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.connect_btn.setText("Connect")
        self.capture_btn.setEnabled(False)
        logger.info(f"M{self.current_machine_id}: Camera disconnected")
    
    def set_camera_thread(self, camera_thread):
        """Set camera thread reference (called by main app)"""
        self.camera_thread = camera_thread
    
    def capture_frame(self):
        """Capture frame from camera"""
        if not self.camera_thread:
            QMessageBox.warning(self, "No Camera", "Camera not connected")
            return
        
        try:
            frame = self.camera_thread.get_latest_frame()
            if frame is None:
                QMessageBox.warning(self, "No Frame", "No frame available from camera")
                return
            
            if self.drawing_widget.set_image(frame):
                # Enable drawing controls
                for btn in self.boundary_buttons.values():
                    btn.setEnabled(True)
                self.finish_btn.setEnabled(True)
                self.undo_btn.setEnabled(True)
                self.clear_current_btn.setEnabled(True)
                self.clear_all_btn.setEnabled(True)
                self.save_btn.setEnabled(True)
                
                logger.info(f"M{self.current_machine_id}: Frame captured for training")
                QMessageBox.information(self, "Success", "Frame captured! Start drawing boundaries.")
            else:
                QMessageBox.warning(self, "Error", "Failed to set image")
                
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Capture error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to capture frame:\n{str(e)}")
    
    def start_drawing(self, boundary_key):
        """Start drawing a boundary"""
        if self.drawing_widget.start_drawing(boundary_key):
            label = boundary_key.replace("_", " ").upper()
            self.statusBar().showMessage(f"Drawing: {label} - Click to add points") if hasattr(self, 'statusBar') else None
    
    def finish_boundary(self):
        """Finish current boundary"""
        if self.drawing_widget.finish_boundary():
            QMessageBox.information(self, "Success", "Boundary saved!")
    
    def confirm_clear_all(self):
        """Confirm before clearing all boundaries"""
        reply = QMessageBox.question(
            self, 'Clear All',
            'Are you sure you want to clear all boundaries?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.drawing_widget.clear_all()
    
    def save_boundaries(self):
        """Save boundaries to file"""
        if self.current_machine_id is None:
            QMessageBox.warning(self, "No Machine", "No machine selected")
            return
        
        boundaries = self.drawing_widget.get_boundaries()
        
        # Validate all boundaries exist
        required = ["pair1_oc", "pair1_bh", "pair2_oc", "pair2_bh", "pair3_oc", "pair3_bh"]
        missing = [key for key in required if key not in boundaries or len(boundaries[key]) < 3]
        
        if missing:
            reply = QMessageBox.question(
                self, "Incomplete Boundaries",
                f"Missing boundaries:\n" + "\n".join(missing) + "\n\nSave anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Save to file
        try:
            config_dir = "config"
            os.makedirs(config_dir, exist_ok=True)
            filepath = os.path.join(config_dir, f"machine{self.current_machine_id}_boundaries.json")
            
            with open(filepath, 'w') as f:
                json.dump(boundaries, f, indent=2)
            
            logger.info(f"M{self.current_machine_id}: Boundaries saved to {filepath}")
            QMessageBox.information(
                self, "Success",
                f"Boundaries saved for Machine {self.current_machine_id}!\n\n"
                f"File: {filepath}"
            )
            
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Save error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save boundaries:\n{str(e)}")
    
    def load_boundaries(self):
        """Load existing boundaries for current machine"""
        if self.current_machine_id is None:
            return
        
        try:
            filepath = os.path.join("config", f"machine{self.current_machine_id}_boundaries.json")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    boundaries = json.load(f)
                self.drawing_widget.set_boundaries(boundaries)
                logger.info(f"M{self.current_machine_id}: Loaded boundaries from {filepath}")
        except Exception as e:
            logger.warning(f"M{self.current_machine_id}: Could not load boundaries: {e}")