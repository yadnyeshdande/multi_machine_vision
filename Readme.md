# Multi-Machine Industrial Vision Fault Detection System

Production-ready multi-machine vision system for simultaneous monitoring of up to 3 identical machines with fault detection and relay control.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Machine System                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Camera1 ─┐                                                  │
│  Camera2 ─┼─► InferenceEngine (1 YOLO model)                │
│  Camera3 ─┘         │                                        │
│                     ├─► MachineController[1] ─┐             │
│                     ├─► MachineController[2] ─┼─► RelayMgr  │
│                     └─► MachineController[3] ─┘             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Features

✅ **Multi-Machine Monitoring**: Monitor up to 3 machines simultaneously  
✅ **Single YOLO Model**: One model instance serves all cameras  
✅ **Independent Boundaries**: Each machine has its own detection boundaries  
✅ **Fault-Only Relays**: Relay ON = Fault, Relay OFF = OK  
✅ **Auto-Reconnect**: Cameras automatically reconnect on failure  
✅ **Watchdog Monitoring**: Health monitoring for each machine  
✅ **24/7 Operation**: Designed for continuous industrial use  
✅ **Thread-Safe**: All components use proper thread synchronization  

## System Requirements

- Python 3.8+
- USB Relay Board (16-channel)
- RTSP Cameras or USB Cameras
- YOLO model trained for oil_can (class 0) and bunk_hole (class 1)

## Installation

1. **Clone or extract the system**
```bash
cd multi_machine_vision
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Place your YOLO model**
```bash
# Copy your trained model to the project directory
cp /path/to/your/best.pt .
```

4. **Configure machines**

Edit `config/machines_config.json` (will be auto-created on first run):

```json
{
  "model_path": "best.pt",
  "confidence_thresholds": {
    "oil_can": 0.40,
    "bunk_hole": 0.35
  },
  "machines": [
    {
      "machine_id": 1,
      "name": "Machine 1",
      "camera_source": "rtsp://admin:admin123@192.168.1.64:554/Streaming/Channels/101",
      "relay_start_channel": 6,
      "enabled": true
    },
    {
      "machine_id": 2,
      "name": "Machine 2",
      "camera_source": "rtsp://admin:admin123@192.168.1.65:554/Streaming/Channels/101",
      "relay_start_channel": 9,
      "enabled": true
    },
    {
      "machine_id": 3,
      "name": "Machine 3",
      "camera_source": "rtsp://admin:admin123@192.168.1.66:554/Streaming/Channels/101",
      "relay_start_channel": 12,
      "enabled": true
    }
  ]
}
```

## Usage

### Start the Application

```bash
python main.py
```

### Train Boundaries for Each Machine

1. Go to **Home** tab
2. Click **Train Boundaries** for a machine
3. Click **Capture Frame from Camera**
4. Draw 6 boundaries (3 pairs × 2 objects):
   - Pair 1 - Oil Can
   - Pair 1 - Bunk Hole
   - Pair 2 - Oil Can
   - Pair 2 - Bunk Hole
   - Pair 3 - Oil Can
   - Pair 3 - Bunk Hole
5. Click **Save Boundaries**
6. Repeat for all machines

### Start Detection

1. Go to **Home** tab
2. Click **Start All Machines**
3. Click **Monitor** for any machine to view live detection

## Relay Configuration

### Philosophy
- **Fault-Only**: Relays indicate faults only
- **No "All OK" relay**: Removed from design
- **Relay ON** = Fault detected
- **Relay OFF** = Pair is OK

### Assignment Example

| Machine | Start Channel | Relays Used | Purpose |
|---------|--------------|-------------|---------|
| M1 | 6 | 6, 7, 8 | Pair 1, 2, 3 faults |
| M2 | 9 | 9, 10, 11 | Pair 1, 2, 3 faults |
| M3 | 12 | 12, 13, 14 | Pair 1, 2, 3 faults |

## Detection Logic

### Pair Status Determination

**OK Status:**
- Exactly 1 Oil Can detected in boundary
- Exactly 1 Bunk Hole detected in boundary

**FAULT Status:**
- Both absent (0 OC, 0 BH)
- One absent (1 OC, 0 BH) or (0 OC, 1 BH)
- Multiple detected (>1 OC or >1 BH)

## File Structure

```
multi_machine_vision/
├── main.py                      # Main application
├── requirements.txt             # Dependencies
├── core/                        # Core components
│   ├── inference_engine.py      # Single YOLO model
│   ├── camera_thread.py         # Camera capture
│   ├── machine_controller.py    # Per-machine logic
│   ├── relay_manager.py         # Relay control
│   └── watchdog.py              # Health monitoring
├── ui/                          # UI components
│   ├── home_page.py             # Dashboard
│   ├── detection_page.py        # Live monitoring
│   └── training_page.py         # Boundary training
└── config/                      # Configuration
    ├── config_manager.py        # Config handling
    ├── machines_config.json     # System config
    ├── machine1_boundaries.json # M1 boundaries
    ├── machine2_boundaries.json # M2 boundaries
    └── machine3_boundaries.json # M3 boundaries
```

## Thread Model

| Thread | Count | Purpose |
|--------|-------|---------|
| CameraThread | 3 | One per machine |
| InferenceEngine | 1 | Shared YOLO model |
| MachineController | 3 | Detection logic per machine |
| RelayManager | 1 | Relay control |
| WatchdogTimer | 3 | Health monitoring per machine |

## Safety Features

✅ **Auto-Reconnect**: Cameras reconnect automatically with exponential backoff  
✅ **Watchdog**: Detects camera/detection freezes  
✅ **Bounded Queues**: Prevents memory leaks  
✅ **Frame Validation**: Checks frame dimensions before processing  
✅ **Relay Retry**: Retries relay operations on USB failure  
✅ **Thread-Safe**: All shared resources protected with locks  
✅ **Error Recovery**: System continues operating despite component failures  

## Logging

Logs are saved to: `multi_machine_YYYYMMDD.log`

View logs:
- Menu: File → View Logs

## Troubleshooting

### Camera Not Connecting

1. Check RTSP URL format
2. Verify network connectivity
3. Check camera credentials
4. Review logs for detailed error messages

### Relay Not Working

1. Menu: Tools → Test Relay Board
2. Check USB connection
3. Verify relay channel configuration
4. Check relay_start_channel in config

### Detection Not Working

1. Ensure model file exists (best.pt)
2. Train boundaries for the machine
3. Check confidence thresholds
4. Verify model classes (0=oil_can, 1=bunk_hole)

### Performance Issues

1. Reduce camera resolution
2. Increase confidence thresholds
3. Check CPU/GPU usage
4. Review inference FPS in logs

## Support

For issues, check:
1. Log files (multi_machine_YYYYMMDD.log)
2. Configuration files (config/*.json)
3. Camera connectivity
4. Relay board connection

---

**© 2025 Credence Technologies Pvt Ltd**