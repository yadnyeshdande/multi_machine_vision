# Multi-Machine Vision System - Architecture

## System Overview

This is a production-ready, multi-machine industrial vision fault detection system designed for 24/7 operation in factory environments.

### Key Design Principles

1. **Single Model Efficiency**: One YOLO model serves all cameras
2. **Machine Independence**: Each machine operates independently
3. **Fault-Only Philosophy**: Relays indicate faults only (ON = Fault)
4. **Thread Safety**: All components use proper synchronization
5. **Fault Tolerance**: System continues operating despite component failures
6. **Auto Recovery**: Cameras and relays auto-reconnect/retry

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      MAIN APPLICATION                            │
│                     (MultiMachineApp)                            │
└────────────┬────────────────────────────────────┬───────────────┘
             │                                    │
   ┌─────────▼────────┐                 ┌────────▼────────┐
   │  UI Components   │                 │ Core Components │
   └─────────┬────────┘                 └────────┬────────┘
             │                                    │
   ┌─────────┴─────────────┐          ┌──────────┴─────────────┐
   │                       │          │                        │
┌──▼──────┐  ┌──────────┐ │    ┌─────▼──────┐  ┌────────────┐ │
│  Home   │  │Detection │ │    │ Inference  │  │   Relay    │ │
│  Page   │  │  Page    │ │    │  Engine    │  │  Manager   │ │
└─────────┘  └──────────┘ │    │  (1 YOLO)  │  │(16-channel)│ │
                          │    └─────┬──────┘  └────────────┘ │
         ┌────────────┐   │          │                        │
         │  Training  │   │          │                        │
         │   Page     │   │    ┌─────▼─────────────────┐     │
         └────────────┘   │    │ Machine Controllers   │     │
                          │    │  (3 instances)        │     │
                          │    └─────┬─────────────────┘     │
                          │          │                        │
                          │    ┌─────▼─────────────────┐     │
                          │    │  Camera Threads       │     │
                          │    │  (3 instances)        │     │
                          │    └───────────────────────┘     │
                          │                                  │
                          │    ┌───────────────────────┐    │
                          │    │  Watchdog Timers      │    │
                          │    │  (3 instances)        │    │
                          │    └───────────────────────┘    │
                          └────────────────────────────────┘
```

## Component Details

### 1. InferenceEngine (Core)

**Purpose**: Single YOLO model that processes frames from all cameras

**Key Features**:
- Loads model ONCE at startup
- Accepts frames from all machines via bounded queue
- Returns detections tagged with machine_id
- Maintains FPS statistics
- Never reloads model

**Thread**: 1 QThread

**Input Queue**: Bounded to 30 items (prevents memory leak)

**Flow**:
```
CameraThread → submit_frame(machine_id, frame) 
             → InferenceEngine processes
             → emits detections_ready(machine_id, results, fps)
             → MachineController receives
```

### 2. CameraThread (Core)

**Purpose**: Captures video frames from camera with auto-reconnect

**Key Features**:
- Per-machine instance (3 total)
- Auto-reconnect with exponential backoff
- Frame validation (dimension checks)
- Heartbeat signals for watchdog
- Frame buffer (bounded to 5 frames)

**Thread**: 1 QThread per machine (3 total)

**Reconnect Strategy**:
- Initial backoff: 2 seconds
- Max backoff: 60 seconds
- Max attempts: 10
- Exponential increase

**Signals**:
- `frame_ready(machine_id, frame)`: New frame available
- `heartbeat_signal(machine_id)`: Camera alive
- `status_signal(machine_id, status)`: Status update
- `error_signal(machine_id, error)`: Error occurred

### 3. MachineController (Core)

**Purpose**: Detection logic and boundary checking for one machine

**Key Features**:
- Independent boundaries per machine
- Pair status determination (OK/FAULT)
- Detection counting within boundaries
- Relay control via RelayManager
- Fault time tracking

**Detection Logic**:
```python
def determine_pair_status(pair_num):
    oc_count = detections_in_oc_boundary
    bh_count = detections_in_bh_boundary
    
    if oc_count == 1 and bh_count == 1:
        return "OK"
    else:
        return "FAULT"  # Both absent, mismatch, or multiple
```

**Signals**:
- `pair_status_changed(machine_id, statuses)`: Status update
- `detection_stats_updated(machine_id, stats)`: Statistics
- `error_signal(machine_id, error)`: Error

### 4. RelayManager (Core)

**Purpose**: Controls 16-channel USB relay board for all machines

**Key Features**:
- Fault-only philosophy (ON = Fault, OFF = OK)
- Per-machine relay mapping
- Retry logic on USB failures
- Thread-safe with locks
- Auto-reinitialize on failure

**Relay Assignment**:
```
Machine 1: Relays 6, 7, 8   (start=6)
Machine 2: Relays 9, 10, 11 (start=9)
Machine 3: Relays 12, 13, 14 (start=12)

Each machine's relays:
  +0: Pair 1 fault
  +1: Pair 2 fault
  +2: Pair 3 fault
```

**Methods**:
- `configure_machine(machine_id, start_relay)`: Setup
- `set_machine_relays(machine_id, [fault1, fault2, fault3])`: Update
- `test_machine_relays(machine_id)`: Diagnostics
- `reset_all_relays()`: Safety reset

### 5. WatchdogTimer (Core)

**Purpose**: Monitor component health

**Key Features**:
- Per-machine instance (3 total)
- Configurable timeout (default: 15s)
- Thread-safe heartbeat
- Auto-reset after timeout

**Thread**: 1 QThread per machine (3 total)

**Usage**:
```python
# Camera sends heartbeat on each frame
camera.heartbeat_signal.emit(machine_id)

# Watchdog resets timer
watchdog.heartbeat()

# If no heartbeat for 15s
watchdog.timeout_signal.emit(machine_id, "Camera")
```

### 6. HomePage (UI)

**Purpose**: Dashboard showing all machine statuses

**Features**:
- Machine status cards (camera, detection, pairs)
- Last fault times
- Relay assignments
- Start/Stop all machines
- Navigate to Monitor/Train

**Layout**:
```
┌─────────────────────────────────────────┐
│  Multi-Machine Vision System            │
├─────────────────────────────────────────┤
│  System Status: All machines running    │
├─────────────────────────────────────────┤
│  ┌────────┐  ┌────────┐  ┌────────┐   │
│  │Machine1│  │Machine2│  │Machine3│   │
│  │ Status │  │ Status │  │ Status │   │
│  │ Pairs  │  │ Pairs  │  │ Pairs  │   │
│  │ Relays │  │ Relays │  │ Relays │   │
│  │[Monitor]│  │[Monitor]│  │[Monitor]│  │
│  │ [Train]│  │ [Train]│  │ [Train]│   │
│  └────────┘  └────────┘  └────────┘   │
├─────────────────────────────────────────┤
│  [Start All]          [Stop All]        │
└─────────────────────────────────────────┘
```

### 7. DetectionPage (UI)

**Purpose**: Real-time monitoring of selected machine

**Features**:
- Live video with boundary overlays
- Pair statuses (OK/FAULT) with colors
- Detection counts (OC/BH per pair)
- Relay states (ON/OFF)
- Statistics (total detections, faults)
- FPS display

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  Machine 1: Production Line A       FPS: 28.5  │
├─────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌─────────────────────┐ │
│  │                  │  │  Pair Status        │ │
│  │   Live Video     │  │  Pair 1: OK         │ │
│  │   with           │  │    OC: 1  BH: 1     │ │
│  │   Boundaries     │  │  Pair 2: FAULT      │ │
│  │                  │  │    OC: 0  BH: 1     │ │
│  │                  │  │  Pair 3: OK         │ │
│  │                  │  │    OC: 1  BH: 1     │ │
│  │                  │  ├─────────────────────┤ │
│  │                  │  │  Relay Status       │ │
│  │                  │  │  Relay 6 (P1): OFF  │ │
│  │                  │  │  Relay 7 (P2): ON   │ │
│  │                  │  │  Relay 8 (P3): OFF  │ │
│  │                  │  ├─────────────────────┤ │
│  │                  │  │  Statistics         │ │
│  │                  │  │  Detections: 1523   │ │
│  │                  │  │  Faults: 47         │ │
│  └──────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 8. TrainingPage (UI)

**Purpose**: Draw detection boundaries for selected machine

**Features**:
- Capture frame from camera
- Draw polygon boundaries (click to add points)
- 6 boundaries per machine (3 pairs × 2 objects)
- Visual feedback with colors
- Save boundaries to machine-specific file

**Workflow**:
1. Select machine
2. Capture frame
3. Select boundary to draw (e.g., "Pair 1 - Oil Can")
4. Click points on image to create polygon
5. Click "Finish Boundary"
6. Repeat for all 6 boundaries
7. Click "Save Boundaries"

### 9. ConfigManager (Config)

**Purpose**: Load/save machine configurations

**Files**:
- `machines_config.json`: System configuration
- `machine1_boundaries.json`: Machine 1 boundaries
- `machine2_boundaries.json`: Machine 2 boundaries
- `machine3_boundaries.json`: Machine 3 boundaries

**Key Methods**:
- `load_machines_config()`: Load system config
- `save_machines_config(config)`: Save system config
- `load_machine_boundaries(machine_id)`: Load boundaries
- `save_machine_boundaries(machine_id, boundaries)`: Save boundaries

## Thread Safety

### Synchronization Mechanisms

1. **QThread Signals/Slots**: Cross-thread communication
2. **threading.Lock**: Protect shared resources
3. **queue.Queue**: Thread-safe queues
4. **Bounded Queues**: Prevent memory buildup

### Critical Sections

```python
# RelayManager
with self.lock:
    self.relay.set_state(relay_num, state)

# WatchdogTimer
with self.lock:
    self.last_heartbeat = time.time()

# FrameBuffer
with self.lock:
    while not self.queue.empty():
        self.queue.get_nowait()
```

## Data Flow

### Frame Processing Pipeline

```
1. CameraThread captures frame
   ↓
2. Emit frame_ready(machine_id, frame)
   ↓
3. MainApp receives frame
   ↓
4. Submit to InferenceEngine.submit_frame(machine_id, frame)
   ↓
5. InferenceEngine runs YOLO
   ↓
6. Emit detections_ready(machine_id, results, fps)
   ↓
7. MainApp routes to MachineController
   ↓
8. MachineController.process_detections()
   ↓
9. Check boundaries, count detections
   ↓
10. Determine pair statuses
   ↓
11. Update relays via RelayManager
   ↓
12. Emit pair_status_changed()
   ↓
13. Update UI (HomePage, DetectionPage)
```

### Configuration Loading

```
1. Application starts
   ↓
2. ConfigManager.load_machines_config()
   ↓
3. For each machine:
   ↓
4. Create MachineController
   ↓
5. Load boundaries from machine_N_boundaries.json
   ↓
6. Configure relay channels
   ↓
7. Create CameraThread
   ↓
8. Create WatchdogTimer
   ↓
9. Add machine card to HomePage
```

## Error Handling

### Camera Reconnect

```python
def reconnect_camera(self):
    self.reconnect_attempts += 1
    
    # Release old connection
    if self.camera:
        self.camera.release()
        self.camera = None
    
    # Exponential backoff
    sleep_time = min(
        self.reconnect_backoff * self.reconnect_attempts,
        self.reconnect_backoff_max
    )
    
    time.sleep(sleep_time)
    self.connect_camera()
```

### Relay Retry

```python
def _set_relay_with_retry(self, relay_num, state):
    for attempt in range(self.max_retries):
        try:
            self.relay.set_state(relay_num, state)
            return True
        except Exception as e:
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
                # Try reinitialize
                self.initialize()
    return False
```

### Watchdog Recovery

```python
def on_watchdog_timeout(self, machine_id, component):
    logger.error(f"M{machine_id}: Timeout - {component}")
    
    # Alert user
    QMessageBox.warning(...)
    
    # Watchdog auto-resets
    # System continues operating
```

## Performance Considerations

### Memory Management

- **Bounded Queues**: Prevent unbounded growth
- **Frame Drop**: Drop old frames when queue full
- **No Memory Leaks**: Proper cleanup on shutdown

### CPU/GPU Usage

- **Single Model**: Shares GPU across all cameras
- **Queue-Based**: Prevents blocking
- **FPS Monitoring**: Track performance

### Optimization Tips

1. Reduce camera resolution if needed
2. Increase confidence thresholds
3. Limit FPS per camera if system overloaded
4. Use GPU if available (automatic with YOLO)

## Deployment

### Industrial Environment

- **24/7 Operation**: Designed for continuous use
- **Auto Recovery**: Handles transient failures
- **Logging**: Comprehensive logging for diagnostics
- **Watchdog**: Detects freezes/crashes

### Startup Sequence

1. Load configuration
2. Initialize relay board
3. Load YOLO model
4. Create machine controllers
5. Load boundaries
6. Configure relays
7. Create camera threads (don't start)
8. Create watchdogs (don't start)
9. Show UI
10. Wait for user to "Start All Machines"
11. Start inference engine
12. Start camera threads
13. Start watchdogs

### Shutdown Sequence

1. Stop watchdogs
2. Stop camera threads
3. Stop inference engine
4. Reset all relays
5. Close application

## Future Enhancements

Potential improvements:

1. **Remote Monitoring**: Web interface
2. **Email/SMS Alerts**: Fault notifications
3. **Database Logging**: Store fault history
4. **Analytics Dashboard**: Trends, statistics
5. **OPC UA Integration**: Factory automation
6. **Model Auto-Update**: Remote model deployment
7. **Multi-Site**: Monitor across locations
8. **Predictive Maintenance**: ML-based predictions

---

**© 2025 Credence Technologies Pvt Ltd**