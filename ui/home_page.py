"""
Home Dashboard - Overview of all machines
Shows status, last fault, relay assignments
"""
import logging
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime

logger = logging.getLogger(__name__)


class MachineStatusCard(QGroupBox):
    """Status card for one machine"""
    
    monitor_clicked = pyqtSignal(int)  # machine_id
    train_clicked = pyqtSignal(int)
    settings_clicked = pyqtSignal(int)
    
    def __init__(self, machine_id, machine_name, relay_config):
        super().__init__(machine_name)
        self.machine_id = machine_id
        self.machine_name = machine_name
        self.relay_config = relay_config
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Status indicators
        status_layout = QGridLayout()
        
        # Camera status
        status_layout.addWidget(QLabel("Camera:"), 0, 0)
        self.camera_status = QLabel("●")
        self.camera_status.setStyleSheet("color: gray; font-size: 20px;")
        status_layout.addWidget(self.camera_status, 0, 1)
        self.camera_label = QLabel("Disconnected")
        status_layout.addWidget(self.camera_label, 0, 2)
        
        # Detection status
        status_layout.addWidget(QLabel("Detection:"), 1, 0)
        self.detection_status = QLabel("●")
        self.detection_status.setStyleSheet("color: gray; font-size: 20px;")
        status_layout.addWidget(self.detection_status, 1, 1)
        self.detection_label = QLabel("Inactive")
        status_layout.addWidget(self.detection_label, 1, 2)
        
        layout.addLayout(status_layout)
        
        # Separator
        layout.addWidget(self._create_separator())
        
        # Pair statuses
        pair_layout = QGridLayout()
        pair_layout.addWidget(QLabel("Pair 1:"), 0, 0)
        self.pair1_label = QLabel("UNKNOWN")
        self.pair1_label.setStyleSheet("font-weight: bold;")
        pair_layout.addWidget(self.pair1_label, 0, 1)
        
        pair_layout.addWidget(QLabel("Pair 2:"), 1, 0)
        self.pair2_label = QLabel("UNKNOWN")
        self.pair2_label.setStyleSheet("font-weight: bold;")
        pair_layout.addWidget(self.pair2_label, 1, 1)
        
        pair_layout.addWidget(QLabel("Pair 3:"), 2, 0)
        self.pair3_label = QLabel("UNKNOWN")
        self.pair3_label.setStyleSheet("font-weight: bold;")
        pair_layout.addWidget(self.pair3_label, 2, 1)
        
        layout.addLayout(pair_layout)
        
        # Last fault time
        layout.addWidget(QLabel("Last Fault:"))
        self.last_fault_label = QLabel("Never")
        self.last_fault_label.setStyleSheet("color: gray;")
        layout.addWidget(self.last_fault_label)
        
        # Relay assignment
        layout.addWidget(QLabel("Relay Channels:"))
        relay_text = f"{self.relay_config[0]}, {self.relay_config[1]}, {self.relay_config[2]}" \
                     if len(self.relay_config) == 3 else "Not configured"
        self.relay_label = QLabel(relay_text)
        self.relay_label.setStyleSheet("color: blue;")
        layout.addWidget(self.relay_label)
        
        layout.addWidget(self._create_separator())
        
        # Buttons
        btn_layout = QVBoxLayout()
        
        monitor_btn = QPushButton("Monitor")
        monitor_btn.clicked.connect(lambda: self.monitor_clicked.emit(self.machine_id))
        btn_layout.addWidget(monitor_btn)
        
        train_btn = QPushButton("Train Boundaries")
        train_btn.clicked.connect(lambda: self.train_clicked.emit(self.machine_id))
        btn_layout.addWidget(train_btn)
        
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(lambda: self.settings_clicked.emit(self.machine_id))
        btn_layout.addWidget(settings_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line
    
    def update_camera_status(self, connected):
        if connected:
            self.camera_status.setStyleSheet("color: green; font-size: 20px;")
            self.camera_label.setText("Connected")
        else:
            self.camera_status.setStyleSheet("color: red; font-size: 20px;")
            self.camera_label.setText("Disconnected")
    
    def update_detection_status(self, active):
        if active:
            self.detection_status.setStyleSheet("color: green; font-size: 20px;")
            self.detection_label.setText("Active")
        else:
            self.detection_status.setStyleSheet("color: gray; font-size: 20px;")
            self.detection_label.setText("Inactive")
    
    def update_pair_statuses(self, statuses):
        """Update pair status labels"""
        labels = [self.pair1_label, self.pair2_label, self.pair3_label]
        
        for label, status in zip(labels, statuses):
            label.setText(status)
            if status == "OK":
                label.setStyleSheet("color: green; font-weight: bold;")
            elif status == "FAULT":
                label.setStyleSheet("color: red; font-weight: bold;")
            else:
                label.setStyleSheet("color: gray; font-weight: bold;")
    
    def update_last_fault(self, fault_times):
        """Update last fault time from list of fault times"""
        # Find most recent fault
        valid_times = [t for t in fault_times if t is not None]
        if valid_times:
            latest = max(valid_times)
            self.last_fault_label.setText(latest.strftime("%H:%M:%S"))
            self.last_fault_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.last_fault_label.setText("Never")
            self.last_fault_label.setStyleSheet("color: gray;")


class HomePage(QWidget):
    """
    Home dashboard showing overview of all machines
    """
    
    monitor_machine = pyqtSignal(int)  # machine_id
    train_machine = pyqtSignal(int)
    settings_machine = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.machine_cards = {}
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Title
        title = QLabel("Multi-Machine Vision System")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # System status
        self.system_status = QLabel("System Initializing...")
        self.system_status.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        self.system_status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.system_status)
        
        # Machine cards in grid
        card_layout = QGridLayout()
        card_layout.setSpacing(20)
        
        # Will be populated with machine cards
        self.card_container = card_layout
        
        main_layout.addLayout(card_layout)
        main_layout.addStretch()
        
        # Global controls
        control_layout = QHBoxLayout()
        
        self.start_all_btn = QPushButton("Start All Machines")
        self.start_all_btn.setMinimumHeight(40)
        self.start_all_btn.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        control_layout.addWidget(self.start_all_btn)
        
        self.stop_all_btn = QPushButton("Stop All Machines")
        self.stop_all_btn.setMinimumHeight(40)
        self.stop_all_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.stop_all_btn.setEnabled(False)
        control_layout.addWidget(self.stop_all_btn)
        
        main_layout.addLayout(control_layout)
        
        self.setLayout(main_layout)
    
    def add_machine_card(self, machine_id, machine_name, relay_config):
        """Add a machine status card"""
        card = MachineStatusCard(machine_id, machine_name, relay_config)
        
        # Connect signals
        card.monitor_clicked.connect(self.monitor_machine)
        card.train_clicked.connect(self.train_machine)
        card.settings_clicked.connect(self.settings_machine)
        
        # Add to grid (3 columns)
        row = (machine_id - 1) // 3
        col = (machine_id - 1) % 3
        self.card_container.addWidget(card, row, col)
        
        self.machine_cards[machine_id] = card
        
        logger.info(f"Added machine card: {machine_name} (M{machine_id})")
    
    def update_machine_status(self, machine_id, camera_connected, detection_active, 
                             pair_statuses, fault_times):
        """Update machine status"""
        if machine_id in self.machine_cards:
            card = self.machine_cards[machine_id]
            card.update_camera_status(camera_connected)
            card.update_detection_status(detection_active)
            card.update_pair_statuses(pair_statuses)
            card.update_last_fault(fault_times)
    
    def set_system_status(self, status, color="black"):
        """Set system status message"""
        self.system_status.setText(status)
        self.system_status.setStyleSheet(
            f"padding: 5px; background-color: #f0f0f0; color: {color}; font-weight: bold;"
        )
    
    def set_detection_running(self, running):
        """Update button states based on detection status"""
        self.start_all_btn.setEnabled(not running)
        self.stop_all_btn.setEnabled(running)