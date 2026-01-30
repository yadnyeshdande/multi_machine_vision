"""
Camera Thread - Handles video capture with auto-reconnect
Each machine has its own camera thread
"""
import logging
import time
import threading
import queue
import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class FrameBuffer:
    """Thread-safe bounded frame buffer"""
    def __init__(self, maxsize=10):
        self.queue = queue.Queue(maxsize=maxsize)
        self.lock = threading.Lock()
    
    def put(self, frame, block=False):
        """Put frame in buffer, drop oldest if full"""
        try:
            self.queue.put(frame, block=block, timeout=0.001)
        except queue.Full:
            try:
                self.queue.get_nowait()
                self.queue.put(frame, block=False)
            except:
                pass
    
    def get(self, timeout=0.1):
        """Get frame from buffer"""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def clear(self):
        """Clear all frames from buffer"""
        with self.lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    break


class CameraThread(QThread):
    """
    Camera thread with auto-reconnect and watchdog heartbeat
    """
    frame_ready = pyqtSignal(int, np.ndarray)  # machine_id, frame
    error_signal = pyqtSignal(int, str)  # machine_id, error_msg
    status_signal = pyqtSignal(int, str)  # machine_id, status_msg
    heartbeat_signal = pyqtSignal(int)  # machine_id
    
    def __init__(self, machine_id, camera_source, camera_config):
        super().__init__()
        self.machine_id = machine_id
        self.camera_source = camera_source
        self.camera_config = camera_config
        
        self.running = False
        self.camera = None
        self.frame_buffer = FrameBuffer(maxsize=5)
        
        # Reconnect handling
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = camera_config.get("max_reconnect_attempts", 10)
        self.reconnect_backoff = 2  # seconds
        self.reconnect_backoff_max = camera_config.get("reconnect_backoff_max", 60)
        
        # Frame stats
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.current_fps = 0.0
        
        # Camera type detection
        self.is_ip_camera = isinstance(camera_source, str) and camera_source.startswith("rtsp")
        
        logger.info(f"M{machine_id}: CameraThread initialized - Source: {camera_source}")
    
    def run(self):
        """Main camera loop"""
        self.running = True
        camera_type = "RTSP" if self.is_ip_camera else f"USB{self.camera_source}"
        logger.info(f"M{self.machine_id}: Camera thread started ({camera_type})")
        
        while self.running:
            try:
                # Connect camera if not connected
                if self.camera is None or not self.camera.isOpened():
                    self.connect_camera()
                
                # Read frames
                if self.camera and self.camera.isOpened():
                    ret, frame = self.camera.read()
                    
                    if ret and frame is not None:
                        # Validate frame
                        if len(frame.shape) == 3 and frame.shape[2] == 3:
                            # Send frame
                            self.frame_buffer.put(frame.copy(), block=False)
                            self.frame_ready.emit(self.machine_id, frame)
                            
                            # Send heartbeat
                            self.heartbeat_signal.emit(self.machine_id)
                            
                            # Reset reconnect counter
                            self.reconnect_attempts = 0
                            self.reconnect_backoff = 2
                            
                            # Update FPS
                            self.frame_count += 1
                            current_time = time.time()
                            if current_time - self.last_frame_time >= 5.0:
                                self.current_fps = self.frame_count / (current_time - self.last_frame_time)
                                logger.debug(f"M{self.machine_id}: Camera FPS: {self.current_fps:.1f}")
                                self.frame_count = 0
                                self.last_frame_time = current_time
                        else:
                            logger.warning(f"M{self.machine_id}: Invalid frame dimensions {frame.shape}")
                    else:
                        logger.warning(f"M{self.machine_id}: Failed to read frame, reconnecting...")
                        self.reconnect_camera()
                else:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"M{self.machine_id}: Camera error: {e}")
                self.error_signal.emit(self.machine_id, str(e))
                self.reconnect_camera()
                time.sleep(1)
        
        self.cleanup()
        logger.info(f"M{self.machine_id}: Camera thread stopped")
    
    def connect_camera(self):
        """Connect to camera with retries"""
        camera_desc = f"RTSP" if self.is_ip_camera else f"USB{self.camera_source}"
        
        for attempt in range(self.max_reconnect_attempts):
            try:
                logger.info(f"M{self.machine_id}: Connecting to {camera_desc}, attempt {attempt + 1}")
                
                if self.is_ip_camera:
                    self.camera = cv2.VideoCapture(self.camera_source, cv2.CAP_FFMPEG)
                    self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 
                                   self.camera_config.get("buffer_size", 1))
                    self.camera.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 
                                   self.camera_config.get("rtsp_timeout_ms", 5000))
                    self.camera.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 
                                   self.camera_config.get("rtsp_timeout_ms", 5000))
                else:
                    self.camera = cv2.VideoCapture(self.camera_source)
                    self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 
                                   self.camera_config.get("buffer_size", 1))
                    self.camera.set(cv2.CAP_PROP_FPS, 
                                   self.camera_config.get("default_fps", 30))
                
                # Test camera
                if self.camera and self.camera.isOpened():
                    ret, test_frame = self.camera.read()
                    if ret and test_frame is not None:
                        logger.info(f"M{self.machine_id}: Camera connected - Frame size: {test_frame.shape}")
                        self.status_signal.emit(self.machine_id, f"Camera Connected ({camera_desc})")
                        self.reconnect_attempts = 0
                        return True
                    else:
                        logger.warning(f"M{self.machine_id}: Camera opened but cannot read")
                        if self.camera:
                            self.camera.release()
                            self.camera = None
                else:
                    logger.warning(f"M{self.machine_id}: Camera failed to open")
                    
            except Exception as e:
                logger.error(f"M{self.machine_id}: Connection error: {e}")
            
            time.sleep(2)
        
        self.error_signal.emit(self.machine_id, 
                              f"Failed to connect after {self.max_reconnect_attempts} attempts")
        return False
    
    def reconnect_camera(self):
        """Reconnect with exponential backoff"""
        self.reconnect_attempts += 1
        
        if self.camera:
            try:
                self.camera.release()
            except:
                pass
            self.camera = None
        
        # Exponential backoff
        sleep_time = min(self.reconnect_backoff * self.reconnect_attempts, 
                        self.reconnect_backoff_max)
        logger.info(f"M{self.machine_id}: Reconnecting in {sleep_time}s...")
        time.sleep(sleep_time)
    
    def get_latest_frame(self):
        """Get latest frame from buffer"""
        return self.frame_buffer.get(timeout=0.1)
    
    def cleanup(self):
        """Clean up camera resources"""
        logger.info(f"M{self.machine_id}: Cleaning up camera...")
        if self.camera:
            try:
                self.camera.release()
            except Exception as e:
                logger.error(f"M{self.machine_id}: Cleanup error: {e}")
        self.camera = None
        self.frame_buffer.clear()
    
    def stop(self):
        """Stop camera thread"""
        self.running = False
        logger.info(f"M{self.machine_id}: Camera stop requested")