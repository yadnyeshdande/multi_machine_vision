"""
Machine Controller - Controls one machine's detection logic
- Receives detections from global InferenceEngine
- Applies machine-specific boundaries
- Determines pair status (OC/BH matching)
- Sends relay commands via RelayManager
"""
import logging
import json
import os
import numpy as np
import cv2
from PyQt5.QtCore import QObject, pyqtSignal
from datetime import datetime

logger = logging.getLogger(__name__)


class MachineController(QObject):
    """
    Controls detection logic for one machine
    """
    pair_status_changed = pyqtSignal(int, list)  # machine_id, [pair1, pair2, pair3]
    detection_stats_updated = pyqtSignal(int, dict)  # machine_id, stats
    error_signal = pyqtSignal(int, str)  # machine_id, error
    
    def __init__(self, machine_id, machine_name, confidence_thresholds, relay_manager):
        super().__init__()
        self.machine_id = machine_id
        self.machine_name = machine_name
        self.confidence_thresholds = confidence_thresholds
        self.relay_manager = relay_manager
        
        # Boundaries (loaded from file)
        self.boundaries = {
            "pair1_oc": [],
            "pair1_bh": [],
            "pair2_oc": [],
            "pair2_bh": [],
            "pair3_oc": [],
            "pair3_bh": []
        }
        
        # Current pair statuses
        self.pair_statuses = ["UNKNOWN", "UNKNOWN", "UNKNOWN"]
        
        # Detection counts
        self.detection_counts = {
            "pair1_oc": 0,
            "pair1_bh": 0,
            "pair2_oc": 0,
            "pair2_bh": 0,
            "pair3_oc": 0,
            "pair3_bh": 0
        }
        
        # Last fault times
        self.last_fault_times = [None, None, None]
        
        # Statistics
        self.total_detections = 0
        self.fault_count = 0
        
        logger.info(f"M{machine_id}: MachineController initialized ({machine_name})")
    
    def load_boundaries(self, config_path):
        """Load machine-specific boundaries from JSON file"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.boundaries = json.load(f)
                logger.info(f"M{self.machine_id}: Boundaries loaded from {config_path}")
                return True
            else:
                logger.warning(f"M{self.machine_id}: Boundary file not found: {config_path}")
                return False
        except Exception as e:
            logger.error(f"M{self.machine_id}: Failed to load boundaries: {e}")
            return False
    
    def save_boundaries(self, config_path):
        """Save boundaries to JSON file"""
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self.boundaries, f, indent=2)
            logger.info(f"M{self.machine_id}: Boundaries saved to {config_path}")
            return True
        except Exception as e:
            logger.error(f"M{self.machine_id}: Failed to save boundaries: {e}")
            return False
    
    def set_boundaries(self, boundaries):
        """Set boundaries (used from training page)"""
        self.boundaries = boundaries
        logger.info(f"M{self.machine_id}: Boundaries updated")
    
    def process_detections(self, results, frame):
        """
        Process YOLO detections and determine pair status
        Called when InferenceEngine emits results for this machine
        """
        try:
            self.total_detections += 1
            
            # Reset detection counts
            for key in self.detection_counts:
                self.detection_counts[key] = 0
            
            # Extract detections
            if results and len(results) > 0:
                boxes = results[0].boxes
                
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].cpu().numpy()
                        
                        # Get class name
                        class_name = "oil_can" if cls == 0 else "bunk_hole"
                        
                        # Check confidence threshold
                        min_conf = self.confidence_thresholds.get(class_name, 0.35)
                        if conf < min_conf:
                            continue
                        
                        # Get center point
                        center_x = int((xyxy[0] + xyxy[2]) / 2)
                        center_y = int((xyxy[1] + xyxy[3]) / 2)
                        
                        # Check which boundary contains this detection
                        self._check_boundaries(class_name, center_x, center_y)
            
            # Determine pair statuses
            new_statuses = []
            for i in range(1, 4):
                status = self._determine_pair_status(i)
                new_statuses.append(status)
            
            # Update pair statuses
            status_changed = new_statuses != self.pair_statuses
            self.pair_statuses = new_statuses
            
            # Update relay states (fault = True if not OK)
            pair_faults = [status != "OK" for status in self.pair_statuses]
            self.relay_manager.set_machine_relays(self.machine_id, pair_faults)
            
            # Update fault times and counts
            for i, status in enumerate(self.pair_statuses):
                if status != "OK":
                    if self.last_fault_times[i] is None:
                        self.last_fault_times[i] = datetime.now()
                        self.fault_count += 1
                else:
                    self.last_fault_times[i] = None
            
            # Emit signals
            if status_changed:
                self.pair_status_changed.emit(self.machine_id, self.pair_statuses)
            
            # Emit stats
            stats = {
                "total_detections": self.total_detections,
                "fault_count": self.fault_count,
                "detection_counts": self.detection_counts.copy(),
                "pair_statuses": self.pair_statuses.copy(),
                "last_fault_times": [t.strftime("%H:%M:%S") if t else "-" 
                                    for t in self.last_fault_times]
            }
            self.detection_stats_updated.emit(self.machine_id, stats)
            
        except Exception as e:
            logger.error(f"M{self.machine_id}: Detection processing error: {e}")
            self.error_signal.emit(self.machine_id, str(e))
    
    def _check_boundaries(self, class_name, center_x, center_y):
        """Check which boundary contains the detection"""
        point = (center_x, center_y)
        
        for pair_num in range(1, 4):
            # Check Oil Can boundary
            oc_key = f"pair{pair_num}_oc"
            if oc_key in self.boundaries and len(self.boundaries[oc_key]) > 0:
                poly = np.array(self.boundaries[oc_key], np.int32)
                if cv2.pointPolygonTest(poly, point, False) >= 0:
                    if class_name == "oil_can":
                        self.detection_counts[oc_key] += 1
            
            # Check Bunk Hole boundary
            bh_key = f"pair{pair_num}_bh"
            if bh_key in self.boundaries and len(self.boundaries[bh_key]) > 0:
                poly = np.array(self.boundaries[bh_key], np.int32)
                if cv2.pointPolygonTest(poly, point, False) >= 0:
                    if class_name == "bunk_hole":
                        self.detection_counts[bh_key] += 1
    
    def _determine_pair_status(self, pair_num):
        """
        Determine status of a pair
        Logic:
        - OK: Both OC and BH detected (exactly 1 each)
        - FAULT: Both absent OR mismatch (counts not equal) OR multiple detected
        """
        oc_key = f"pair{pair_num}_oc"
        bh_key = f"pair{pair_num}_bh"
        
        oc_count = self.detection_counts[oc_key]
        bh_count = self.detection_counts[bh_key]
        
        # OK: Exactly 1 OC and 1 BH
        if oc_count == 1 and bh_count == 1:
            return "OK"
        
        # FAULT: Any other case
        # - Both absent (0, 0)
        # - Mismatch (1, 0) or (0, 1)
        # - Multiple detected (>1)
        else:
            return "FAULT"
    
    def get_pair_statuses(self):
        """Get current pair statuses"""
        return self.pair_statuses.copy()
    
    def get_last_fault_times(self):
        """Get last fault times"""
        return self.last_fault_times.copy()
    
    def reset_stats(self):
        """Reset statistics"""
        self.total_detections = 0
        self.fault_count = 0
        self.last_fault_times = [None, None, None]
        logger.info(f"M{self.machine_id}: Statistics reset")