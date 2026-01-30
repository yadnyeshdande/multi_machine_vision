"""
Global Inference Engine - Single YOLO model for all machines
Receives frames from all cameras, runs inference, returns results tagged with machine_id
"""
import logging
import time
import queue
import traceback
from PyQt5.QtCore import QThread, pyqtSignal
from ultralytics import YOLO
import numpy as np

logger = logging.getLogger(__name__)


class InferenceEngine(QThread):
    """
    Single YOLO inference thread handling all machines
    Input: (machine_id, frame, boundaries)
    Output: detections_ready(machine_id, results, fps)
    """
    detections_ready = pyqtSignal(int, object, float)  # machine_id, results, fps
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    
    def __init__(self, model_path, confidence_thresholds):
        super().__init__()
        self.model_path = model_path
        self.confidence_thresholds = confidence_thresholds
        self.model = None
        self.running = False
        
        # Bounded input queue to prevent memory leaks
        self.input_queue = queue.Queue(maxsize=30)
        
        # FPS tracking
        self.inference_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0
        
        logger.info(f"InferenceEngine initialized with model: {model_path}")
    
    def load_model(self):
        """Load YOLO model once at startup"""
        try:
            logger.info(f"Loading YOLO model from {self.model_path}...")
            self.model = YOLO(self.model_path)
            logger.info("✓ YOLO model loaded successfully")
            self.status_signal.emit("Model loaded successfully")
            return True
        except Exception as e:
            error_msg = f"Failed to load YOLO model: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_signal.emit(error_msg)
            return False
    
    def submit_frame(self, machine_id, frame, boundaries=None):
        """
        Submit a frame for inference (called from MachineController)
        Non-blocking - drops frame if queue is full
        """
        try:
            self.input_queue.put((machine_id, frame, boundaries), block=False)
        except queue.Full:
            # Drop frame silently - prevents memory buildup
            pass
    
    def run(self):
        """Main inference loop"""
        self.running = True
        
        # Load model
        if not self.load_model():
            logger.critical("Cannot start inference engine - model load failed")
            return
        
        logger.info("InferenceEngine started - processing frames from all machines")
        
        while self.running:
            try:
                # Get frame from queue with timeout
                try:
                    machine_id, frame, boundaries = self.input_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Validate frame
                if frame is None or frame.size == 0:
                    logger.warning(f"M{machine_id}: Invalid frame received")
                    continue
                
                if len(frame.shape) != 3 or frame.shape[2] != 3:
                    logger.warning(f"M{machine_id}: Invalid frame dimensions {frame.shape}")
                    continue
                
                # Run YOLO inference
                results = self.model(frame, verbose=False)
                
                # Update FPS
                self.inference_count += 1
                current_time = time.time()
                if current_time - self.last_fps_time >= 1.0:
                    self.current_fps = self.inference_count / (current_time - self.last_fps_time)
                    self.inference_count = 0
                    self.last_fps_time = current_time
                
                # Emit results with machine_id tag
                self.detections_ready.emit(machine_id, results, self.current_fps)
                
            except Exception as e:
                error_msg = f"Inference error: {e}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                self.error_signal.emit(error_msg)
                time.sleep(0.1)
        
        logger.info("InferenceEngine stopped")
    
    def stop(self):
        """Stop the inference engine"""
        self.running = False
        # Clear queue
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
        logger.info("InferenceEngine stop requested")
    
    def get_fps(self):
        """Get current inference FPS"""
        return self.current_fps