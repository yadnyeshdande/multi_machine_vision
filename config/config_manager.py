"""
Configuration Manager - Handles machine configurations
"""
import json
import os
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages machine configurations
    """
    
    def __init__(self, config_dir="config"):
        self.config_dir = config_dir
        self.machines_config_file = os.path.join(config_dir, "machines_config.json")
        
        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)
        
        logger.info(f"ConfigManager initialized - Config dir: {config_dir}")
    
    def load_machines_config(self):
        """Load machines configuration"""
        try:
            if os.path.exists(self.machines_config_file):
                with open(self.machines_config_file, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded machines config: {len(config.get('machines', []))} machines")
                return config
            else:
                logger.warning("Machines config file not found, creating default")
                return self.create_default_config()
        except Exception as e:
            logger.error(f"Failed to load machines config: {e}")
            return self.create_default_config()
    
    def save_machines_config(self, config):
        """Save machines configuration"""
        try:
            with open(self.machines_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Machines config saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save machines config: {e}")
            return False
    
    def create_default_config(self):
        """Create default configuration"""
        default_config = {
            "model_path": "best.pt",
            "confidence_thresholds": {
                "oil_can": 0.40,
                "bunk_hole": 0.35
            },
            "camera_config": {
                "rtsp_timeout_ms": 5000,
                "buffer_size": 1,
                "default_fps": 30,
                "max_reconnect_attempts": 10,
                "reconnect_backoff_max": 60
            },
            "relay_config": {
                "max_retries": 3,
                "retry_delay": 0.5
            },
            "watchdog_timeout": 15,
            "machines": [
                {
                    "machine_id": 1,
                    "name": "Machine 1",
                    "camera_source": "rtsp://admin:admin123@192.168.1.64:554/Streaming/Channels/101",
                    "relay_start_channel": 6,
                    "enabled": True
                },
                {
                    "machine_id": 2,
                    "name": "Machine 2",
                    "camera_source": "rtsp://admin:admin123@192.168.1.65:554/Streaming/Channels/101",
                    "relay_start_channel": 9,
                    "enabled": True
                },
                {
                    "machine_id": 3,
                    "name": "Machine 3",
                    "camera_source": "rtsp://admin:admin123@192.168.1.66:554/Streaming/Channels/101",
                    "relay_start_channel": 12,
                    "enabled": True
                }
            ]
        }
        
        # Save default config
        self.save_machines_config(default_config)
        
        return default_config
    
    def get_machine_boundary_file(self, machine_id):
        """Get boundary file path for a machine"""
        return os.path.join(self.config_dir, f"machine{machine_id}_boundaries.json")
    
    def load_machine_boundaries(self, machine_id):
        """Load boundaries for a machine"""
        boundary_file = self.get_machine_boundary_file(machine_id)
        
        try:
            if os.path.exists(boundary_file):
                with open(boundary_file, 'r') as f:
                    boundaries = json.load(f)
                logger.info(f"M{machine_id}: Loaded boundaries from {boundary_file}")
                return boundaries
            else:
                logger.warning(f"M{machine_id}: No boundary file found")
                return self.create_default_boundaries()
        except Exception as e:
            logger.error(f"M{machine_id}: Failed to load boundaries: {e}")
            return self.create_default_boundaries()
    
    def save_machine_boundaries(self, machine_id, boundaries):
        """Save boundaries for a machine"""
        boundary_file = self.get_machine_boundary_file(machine_id)
        
        try:
            with open(boundary_file, 'w') as f:
                json.dump(boundaries, f, indent=2)
            logger.info(f"M{machine_id}: Saved boundaries to {boundary_file}")
            return True
        except Exception as e:
            logger.error(f"M{machine_id}: Failed to save boundaries: {e}")
            return False
    
    def create_default_boundaries(self):
        """Create empty boundaries structure"""
        return {
            "pair1_oc": [],
            "pair1_bh": [],
            "pair2_oc": [],
            "pair2_bh": [],
            "pair3_oc": [],
            "pair3_bh": []
        }
    
    def validate_config(self, config):
        """Validate configuration"""
        required_keys = ["model_path", "machines"]
        
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required config key: {key}")
                return False
        
        if not isinstance(config["machines"], list):
            logger.error("machines must be a list")
            return False
        
        for machine in config["machines"]:
            required_machine_keys = ["machine_id", "name", "camera_source", 
                                    "relay_start_channel", "enabled"]
            for key in required_machine_keys:
                if key not in machine:
                    logger.error(f"Machine missing key: {key}")
                    return False
        
        logger.info("Config validation passed")
        return True