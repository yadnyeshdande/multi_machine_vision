"""
Training Page - Draw boundaries for selected machine
Allows user to draw 3 Oil Can + 3 Bunk Hole boundaries
UPGRADED: Full original UI + Camera connection
"""
import logging
import cv2
import numpy as np
import json
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

logger = logging.getLogger(__name__)


class DrawingWidget(QLabel):
    """Widget for drawing polygons on image"""
    
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.image = None
        self.scale_factor = 1.0
        self.current_points = []
        self.all_boundaries = {}
        self.current_boundary_key = None
        
        self.setStyleSheet("background-color: black; border: 2px solid gray;")
        self.setAlignment(Qt.AlignCenter)
    
    def set_image(self, image):
        """Set the image to draw on"""
        self.image = image.copy()
        self.display_image()
    
    def display_image(self):
        """Display image with current boundaries"""
        if self.image is None:
            return
        
        display = self.image.copy()
        
        # Draw all completed boundaries
        colors = {
            "pair1_oc": (0, 255, 0),
            "pair1_bh": (255, 0, 0),
            "pair2_oc": (0, 255, 255),
            "pair2_bh": (255, 0, 255),
            "pair3_oc": (0, 128, 255),
            "pair3_bh": (255, 128, 0),
        }
        
        for key, points in self.all_boundaries.items():
            if len(points) > 0:
                poly = np.array(points, np.int32)
                color = colors.get(key, (255, 255, 255))
                cv2.polylines(display, [poly], True, color, 2)
                
                # Label
                centroid = poly.mean(axis=0).astype(int)
                label = key.replace("_", " ").upper()
                cv2.putText(display, label, tuple(centroid),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Draw current polygon being drawn
        if len(self.current_points) > 0:
            for i, point in enumerate(self.current_points):
                cv2.circle(display, point, 5, (0, 255, 0), -1)
                if i > 0:
                    cv2.line(display, self.current_points[i-1], point, (0, 255, 0), 2)
            
            # Close the polygon visually
            if len(self.current_points) > 2:
                cv2.line(display, self.current_points[-1], self.current_points[0], 
                        (0, 255, 0), 1)
        
        # Convert and display
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qt_image)
        scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Calculate scale factor for coordinate conversion
        self.scale_factor = pixmap.width() / scaled.width()
        
        self.setPixmap(scaled)
    
    def start_boundary(self, boundary_key):
        """Start drawing a new boundary"""
        self.current_boundary_key = boundary_key
        self.current_points = []
        logger.info(f"Started drawing boundary: {boundary_key}")
    
    def mousePressEvent(self, event):
        """Handle mouse clicks for polygon drawing"""
        if event.button() == Qt.LeftButton and self.current_boundary_key:
            # Convert widget coordinates to image coordinates
            pixmap = self.pixmap()
            if pixmap is None or self.image is None:
                return
            
            # Get click position relative to pixmap
            label_x = event.pos().x()
            label_y = event.pos().y()
            
            # Calculate offset (pixmap might be centered in label)
            pixmap_x = (self.width() - pixmap.width()) // 2
            pixmap_y = (self.height() - pixmap.height()) // 2
            
            # Convert to pixmap coordinates
            x = int((label_x - pixmap_x) * self.scale_factor)
            y = int((label_y - pixmap_y) * self.scale_factor)
            
            # Clamp to image bounds
            x = max(0, min(x, self.image.shape[1] - 1))
            y = max(0, min(y, self.image.shape[0] - 1))
            
            self.current_points.append((x, y))
            self.display_image()
            
            logger.debug(f"Added point: ({x}, {y}) to {self.current_boundary_key}")
    
    def finish_boundary(self):
        """Finish current boundary"""
        if self.current_boundary_key and len(self.current_points) >= 3:
            self.all_boundaries[self.current_boundary_key] = self.current_points.copy()
            logger.info(f"Finished boundary {self.current_boundary_key} "
                       f"with {len(self.current_points)} points")
            self.current_points = []
            self.current_boundary_key = None
            self.display_image()
            return True
        else:
            QMessageBox.warning(self, "Invalid Boundary", 
                              "Need at least 3 points to create a boundary")
            return False
    
    def clear_current(self):
        """Clear current drawing"""
        self.current_points = []
        self.display_image()
    
    def clear_all(self):
        """Clear all boundaries"""
        self.all_boundaries = {}
        self.current_points = []
        self.current_boundary_key = None
        self.display_image()
    
    def set_boundaries(self, boundaries):
        """Load existing boundaries"""
        self.all_boundaries = boundaries.copy()
        self.display_image()
    
    def get_boundaries(self):
        """Get all boundaries"""
        return self.all_boundaries.copy()


class TrainingPage(QWidget):
    """
    Training page for drawing boundaries
    """
    
    # Signals
    boundaries_saved = pyqtSignal(int, dict)  # machine_id, boundaries
    connect_camera_requested = pyqtSignal(int, str)  # machine_id, camera_source
    disconnect_camera_requested = pyqtSignal(int)  # machine_id
    
    def __init__(self):
        super().__init__()
        self.current_machine_id = None
        self.current_machine_name = "No Machine Selected"
        self.current_camera_source = None
        self.current_frame = None
        self.camera_thread = None
        self.camera_connected = False
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        self.machine_label = QLabel(self.current_machine_name)
        self.machine_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.machine_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Camera connection controls
        camera_layout = QHBoxLayout()
        camera_layout.addWidget(QLabel("Camera Source:"))
        
        self.camera_input = QLineEdit()
        self.camera_input.setPlaceholderText("RTSP URL or USB index (0, 1, 2...)")
        self.camera_input.setMinimumWidth(400)
        camera_layout.addWidget(self.camera_input)
        
        self.connect_btn = QPushButton("Connect Camera")
        self.connect_btn.clicked.connect(self.toggle_camera)
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        camera_layout.addWidget(self.connect_btn)
        
        self.camera_status_label = QLabel("● Disconnected")
        self.camera_status_label.setStyleSheet("color: red; font-weight: bold;")
        camera_layout.addWidget(self.camera_status_label)
        
        layout.addLayout(camera_layout)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "1. Connect to camera\n"
            "2. Capture a frame from the camera\n"
            "3. Select a boundary to draw (e.g., Pair 1 - Oil Can)\n"
            "4. Click on the image to create polygon points\n"
            "5. Click 'Finish Boundary' when done (need at least 3 points)\n"
            "6. Repeat for all 6 boundaries (3 pairs × 2 objects)\n"
            "7. Click 'Save Boundaries' when all done"
        )
        instructions.setStyleSheet("background-color: #f0f0f0; padding: 10px;")
        layout.addWidget(instructions)
        
        # Main content
        content_layout = QHBoxLayout()
        
        # Left: Drawing area
        self.drawing_widget = DrawingWidget()
        self.drawing_widget.setMinimumSize(800, 600)
        content_layout.addWidget(self.drawing_widget, stretch=3)
        
        # Right: Controls
        control_widget = QWidget()
        control_layout = QVBoxLayout()
        
        # Capture frame button
        self.capture_btn = QPushButton("Capture Frame from Camera")
        self.capture_btn.setMinimumHeight(40)
        self.capture_btn.setEnabled(False)  # Disabled until camera connects
        self.capture_btn.clicked.connect(self.capture_frame)
        control_layout.addWidget(self.capture_btn)
        
        control_layout.addWidget(QLabel("Select Boundary to Draw:"))
        
        # Boundary selection buttons
        boundary_group = QGroupBox("Boundaries")
        boundary_layout = QVBoxLayout()
        
        self.boundary_buttons = {}
        boundaries = [
            ("pair1_oc", "Pair 1 - Oil Can"),
            ("pair1_bh", "Pair 1 - Bunk Hole"),
            ("pair2_oc", "Pair 2 - Oil Can"),
            ("pair2_bh", "Pair 2 - Bunk Hole"),
            ("pair3_oc", "Pair 3 - Oil Can"),
            ("pair3_bh", "Pair 3 - Bunk Hole"),
        ]
        
        for key, label in boundaries:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, k=key: self.start_boundary(k))
            boundary_layout.addWidget(btn)
            self.boundary_buttons[key] = btn
        
        boundary_group.setLayout(boundary_layout)
        control_layout.addWidget(boundary_group)
        
        # Drawing controls
        self.finish_btn = QPushButton("Finish Current Boundary")
        self.finish_btn.clicked.connect(self.finish_boundary)
        control_layout.addWidget(self.finish_btn)
        
        self.clear_current_btn = QPushButton("Clear Current")
        self.clear_current_btn.clicked.connect(self.drawing_widget.clear_current)
        control_layout.addWidget(self.clear_current_btn)
        
        self.clear_all_btn = QPushButton("Clear All Boundaries")
        self.clear_all_btn.clicked.connect(self.clear_all)
        control_layout.addWidget(self.clear_all_btn)
        
        control_layout.addStretch()
        
        # Save button
        self.save_btn = QPushButton("Save Boundaries")
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_boundaries)
        control_layout.addWidget(self.save_btn)
        
        control_widget.setLayout(control_layout)
        content_layout.addWidget(control_widget, stretch=1)
        
        layout.addLayout(content_layout)
        
        self.setLayout(layout)
    
    def set_machine(self, machine_id, machine_name, camera_source):
        """Set which machine to configure"""
        # Disconnect previous camera if any
        if self.camera_connected:
            self.toggle_camera()
        
        self.current_machine_id = machine_id
        self.current_machine_name = machine_name
        self.current_camera_source = camera_source
        
        self.machine_label.setText(f"Training: Machine {machine_id} - {machine_name}")
        self.camera_input.setText(camera_source)
        
        # Load existing boundaries if any
        self.load_boundaries_from_file()
        
        logger.info(f"Training page set to M{machine_id}: {machine_name}")
    
    def toggle_camera(self):
        """Toggle camera connection"""
        if not self.camera_connected:
            # Connect
            camera_source = self.camera_input.text().strip()
            if not camera_source:
                QMessageBox.warning(self, "No Camera Source",
                                  "Please enter a camera source (RTSP URL or USB index)")
                return
            
            # Try to parse as USB index
            try:
                camera_source = int(camera_source)
            except:
                pass  # Keep as string (RTSP URL)
            
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
        self.connect_btn.setText("Disconnect Camera")
        self.connect_btn.setStyleSheet("background-color: #F44336; color: white; padding: 8px;")
        self.capture_btn.setEnabled(True)
        logger.info(f"M{self.current_machine_id}: Camera connected in training")
    
    def on_camera_disconnected(self):
        """Called when camera disconnects"""
        self.camera_connected = False
        self.camera_status_label.setText("● Disconnected")
        self.camera_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.connect_btn.setText("Connect Camera")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        self.capture_btn.setEnabled(False)
        logger.info(f"M{self.current_machine_id}: Camera disconnected in training")
    
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
            
            self.set_frame(frame)
            QMessageBox.information(self, "Success", "Frame captured! Start drawing boundaries.")
            logger.info(f"M{self.current_machine_id}: Frame captured for training")
            
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Capture error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to capture frame:\n{str(e)}")
    
    def load_boundaries_from_file(self):
        """Load existing boundaries for current machine"""
        if self.current_machine_id is None:
            return
        
        try:
            filepath = os.path.join("config", f"machine{self.current_machine_id}_boundaries.json")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    boundaries = json.load(f)
                self.load_boundaries(boundaries)
                logger.info(f"M{self.current_machine_id}: Loaded existing boundaries")
        except Exception as e:
            logger.warning(f"M{self.current_machine_id}: Could not load boundaries: {e}")
    
    def set_frame(self, frame):
        """Set the current frame for drawing"""
        if frame is not None:
            self.current_frame = frame.copy()
            self.drawing_widget.set_image(frame)
    
    def capture_frame(self):
        """Request to capture a frame - signal handled by main app"""
        # This will be connected to camera in main app
        pass
    
    def start_boundary(self, boundary_key):
        """Start drawing a boundary"""
        if self.current_frame is None:
            QMessageBox.warning(self, "No Frame", "Please capture a frame first!")
            return
        
        self.drawing_widget.start_boundary(boundary_key)
    
    def finish_boundary(self):
        """Finish current boundary"""
        self.drawing_widget.finish_boundary()
    
    def clear_all(self):
        """Clear all boundaries"""
        reply = QMessageBox.question(
            self, "Clear All",
            "Are you sure you want to clear all boundaries?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.drawing_widget.clear_all()
    
    def save_boundaries(self):
        """Save boundaries and emit signal"""
        boundaries = self.drawing_widget.get_boundaries()
        
        # Validate all boundaries exist
        required = ["pair1_oc", "pair1_bh", "pair2_oc", "pair2_bh", "pair3_oc", "pair3_bh"]
        missing = [key for key in required if key not in boundaries or len(boundaries[key]) < 3]
        
        if missing:
            QMessageBox.warning(
                self, "Incomplete Boundaries",
                f"Please draw all 6 boundaries. Missing:\n" + "\n".join(missing)
            )
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
                f"Boundaries saved for Machine {self.current_machine_id}!\n\nFile: {filepath}"
            )
            
        except Exception as e:
            logger.error(f"M{self.current_machine_id}: Save error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save boundaries:\n{str(e)}")
    
    def load_boundaries(self, boundaries):
        """Load existing boundaries"""
        self.drawing_widget.set_boundaries(boundaries)