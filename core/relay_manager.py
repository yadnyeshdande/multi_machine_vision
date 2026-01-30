"""
Relay Manager - Controls 16-channel USB relay board
Fault-only logic: Relay ON = Fault, Relay OFF = OK
Each machine gets 3 relays (one per pair)
"""
import logging
import time
import threading
import pyhid_usb_relay

logger = logging.getLogger(__name__)


class RelayManager:
    """
    Manages relay board for all machines
    - Each machine gets 3 consecutive relays
    - Relay ON = Fault detected
    - Relay OFF = OK
    """
    
    def __init__(self, relay_config):
        self.relay_config = relay_config
        self.relay = None
        self.lock = threading.Lock()
        
        # Machine relay mappings
        # Format: {machine_id: [relay1, relay2, relay3]}
        self.machine_relays = {}
        
        # Retry settings
        self.max_retries = relay_config.get("max_retries", 3)
        self.retry_delay = relay_config.get("retry_delay", 0.5)
        
        logger.info("RelayManager initialized")
    
    def initialize(self):
        """Initialize relay board"""
        try:
            logger.info("Initializing USB relay board...")
            self.relay = pyhid_usb_relay.find()
            
            if self.relay:
                logger.info("✓ USB relay board connected")
                # Turn off all relays at startup
                self.reset_all_relays()
                return True
            else:
                logger.error("USB relay board not found")
                return False
                
        except Exception as e:
            logger.error(f"Relay initialization failed: {e}")
            return False
    
    def configure_machine(self, machine_id, start_relay):
        """
        Configure relay channels for a machine
        machine_id: 1, 2, or 3
        start_relay: starting relay channel (1-indexed)
        """
        if start_relay < 1 or start_relay > 14:  # Need 3 consecutive relays
            logger.error(f"Invalid start relay {start_relay} for M{machine_id}")
            return False
        
        relays = [start_relay, start_relay + 1, start_relay + 2]
        self.machine_relays[machine_id] = relays
        
        logger.info(f"M{machine_id}: Relays configured: {relays} "
                   f"(Pair1={relays[0]}, Pair2={relays[1]}, Pair3={relays[2]})")
        
        # Initialize machine relays to OFF (no fault)
        self.set_machine_relays(machine_id, [False, False, False])
        
        return True
    
    def set_machine_relays(self, machine_id, pair_faults):
        """
        Set relay states for a machine based on pair faults
        pair_faults: [pair1_fault, pair2_fault, pair3_fault]
                     True = Fault (relay ON), False = OK (relay OFF)
        """
        if machine_id not in self.machine_relays:
            logger.error(f"M{machine_id}: Machine not configured in relay manager")
            return False
        
        relays = self.machine_relays[machine_id]
        
        # Set each relay based on fault status
        success = True
        for i, (relay_num, is_fault) in enumerate(zip(relays, pair_faults)):
            if not self._set_relay_with_retry(relay_num, is_fault):
                logger.error(f"M{machine_id}: Failed to set Pair{i+1} relay {relay_num}")
                success = False
        
        return success
    
    def _set_relay_with_retry(self, relay_num, state):
        """Set relay with retry logic"""
        for attempt in range(self.max_retries):
            try:
                with self.lock:
                    if self.relay is None:
                        # Try to reinitialize
                        self.initialize()
                        if self.relay is None:
                            return False
                    
                    self.relay.set_state(relay_num, state)
                    return True
                    
            except Exception as e:
                logger.error(f"Relay {relay_num} set failed (attempt {attempt+1}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    # Try to reinitialize on failure
                    try:
                        self.relay = None
                        self.initialize()
                    except:
                        pass
        
        return False
    
    def reset_all_relays(self):
        """Turn off all relays (all machines OK)"""
        logger.info("Resetting all relays to OFF (no faults)")
        try:
            with self.lock:
                if self.relay:
                    for i in range(1, 17):  # 16 channels
                        try:
                            self.relay.set_state(i, False)
                        except Exception as e:
                            logger.error(f"Failed to reset relay {i}: {e}")
                    logger.info("✓ All relays reset")
                    return True
        except Exception as e:
            logger.error(f"Reset all relays failed: {e}")
        return False
    
    def reset_machine_relays(self, machine_id):
        """Reset all relays for a specific machine (all pairs OK)"""
        if machine_id in self.machine_relays:
            logger.info(f"M{machine_id}: Resetting relays to OFF (all pairs OK)")
            return self.set_machine_relays(machine_id, [False, False, False])
        return False
    
    def test_relay(self, relay_num):
        """Test a single relay (for diagnostics)"""
        try:
            logger.info(f"Testing relay {relay_num}...")
            self._set_relay_with_retry(relay_num, True)
            time.sleep(1)
            self._set_relay_with_retry(relay_num, False)
            logger.info(f"Relay {relay_num} test complete")
            return True
        except Exception as e:
            logger.error(f"Relay {relay_num} test failed: {e}")
            return False
    
    def test_machine_relays(self, machine_id):
        """Test all relays for a machine"""
        if machine_id not in self.machine_relays:
            logger.error(f"M{machine_id}: Not configured")
            return False
        
        relays = self.machine_relays[machine_id]
        logger.info(f"M{machine_id}: Testing relays {relays}...")
        
        for i, relay_num in enumerate(relays):
            logger.info(f"M{machine_id}: Testing Pair{i+1} relay {relay_num}")
            if not self.test_relay(relay_num):
                return False
            time.sleep(0.5)
        
        logger.info(f"M{machine_id}: All relays tested successfully")
        return True
    
    def get_machine_relay_config(self, machine_id):
        """Get relay configuration for a machine"""
        return self.machine_relays.get(machine_id, [])
    
    def cleanup(self):
        """Clean up relay resources"""
        logger.info("Cleaning up relay manager...")
        self.reset_all_relays()
        self.relay = None