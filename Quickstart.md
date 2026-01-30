# Quick Start Guide - Multi-Machine Vision System

## Prerequisites

- ✅ Python 3.8 or higher installed
- ✅ USB Relay Board (16-channel) connected
- ✅ RTSP cameras accessible on network OR USB cameras connected
- ✅ YOLO model file (`best.pt`) trained for oil_can (class 0) and bunk_hole (class 1)

## Step-by-Step Setup

### Step 1: Extract and Navigate

```bash
# Extract the zip file to a location
cd multi_machine_vision
```

### Step 2: Install Dependencies

**Windows:**
```bash
# Double-click start.bat
# OR manually:
pip install -r requirements.txt
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
# OR manually:
pip3 install -r requirements.txt
```

### Step 3: Place Your YOLO Model

```bash
# Copy your trained model to the project directory
# The file should be named: best.pt
cp /path/to/your/model/best.pt .
```

### Step 4: Configure Cameras and Relays

Edit `config/machines_config.json` (will be created automatically on first run with defaults):

```json
{
  "model_path": "best.pt",
  "machines": [
    {
      "machine_id": 1,
      "name": "Production Line A",
      "camera_source": "rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101",
      "relay_start_channel": 6,
      "enabled": true
    },
    {
      "machine_id": 2,
      "name": "Production Line B",
      "camera_source": "rtsp://admin:password@192.168.1.65:554/Streaming/Channels/101",
      "relay_start_channel": 9,
      "enabled": true
    },
    {
      "machine_id": 3,
      "name": "Production Line C",
      "camera_source": "rtsp://admin:password@192.168.1.66:554/Streaming/Channels/101",
      "relay_start_channel": 12,
      "enabled": true
    }
  ]
}
```

**Camera Source Options:**
- RTSP: `rtsp://user:pass@ip:port/path`
- USB: `0`, `1`, `2` (camera index)

### Step 5: Run the Application

**Windows:**
```bash
# Double-click start.bat
# OR
python main.py
```

**Linux/Mac:**
```bash
./start.sh
# OR
python3 main.py
```

### Step 6: Train Boundaries (First Time Setup)

For **each machine**:

1. **Go to Home Tab**
   - You'll see 3 machine cards

2. **Click "Train Boundaries"** for Machine 1
   - Switches to Training tab

3. **Capture Frame**
   - Click "Capture Frame from Camera"
   - A frame from Machine 1's camera will appear

4. **Draw 6 Boundaries** (one at a time):
   
   **For each boundary:**
   - Click the boundary button (e.g., "Pair 1 - Oil Can")
   - Click on the image to add polygon points (minimum 3 points)
   - Click "Finish Current Boundary"
   
   **Required boundaries:**
   - ✅ Pair 1 - Oil Can
   - ✅ Pair 1 - Bunk Hole
   - ✅ Pair 2 - Oil Can
   - ✅ Pair 2 - Bunk Hole
   - ✅ Pair 3 - Oil Can
   - ✅ Pair 3 - Bunk Hole

5. **Save Boundaries**
   - Click "Save Boundaries"
   - Boundaries saved to `config/machine1_boundaries.json`

6. **Repeat for Machine 2 and Machine 3**

### Step 7: Start Detection

1. **Go to Home Tab**

2. **Click "Start All Machines"**
   - All 3 cameras start
   - Inference engine starts
   - Watchdogs start
   - Status indicators turn green

3. **Monitor a Machine**
   - Click "Monitor" on any machine card
   - View live detection with boundaries
   - See pair statuses (OK/FAULT)
   - See relay states

### Step 8: Verify Relay Operation

1. **Menu → Tools → Test Relay Board**
   - Tests all configured relays
   - Each relay turns ON for 1 second, then OFF

2. **Watch for Faults**
   - When a fault is detected, relay turns ON
   - When fault clears, relay turns OFF

## Understanding the Display

### Home Page - Machine Card

```
┌─────────────────────────┐
│  Machine 1              │
├─────────────────────────┤
│  Camera: ● Connected    │
│  Detection: ● Active    │
├─────────────────────────┤
│  Pair 1: OK             │
│  Pair 2: FAULT          │
│  Pair 3: OK             │
│  Last Fault: 14:32:15   │
│  Relays: 6, 7, 8        │
├─────────────────────────┤
│  [Monitor]              │
│  [Train Boundaries]     │
│  [Settings]             │
└─────────────────────────┘
```

### Detection Page - Live Monitor

```
┌─────────────────────────────────────┐
│  Machine 1: Production Line A       │
│  FPS: 28.5                          │
├─────────────────────────────────────┤
│  Live Video    │  Pair 1: OK        │
│  with          │    OC: 1  BH: 1    │
│  Boundaries    │  Pair 2: FAULT     │
│                │    OC: 0  BH: 1    │
│                │  Pair 3: OK        │
│                │    OC: 1  BH: 1    │
│                ├──────────────────┤
│                │  Relay 6: OFF    │
│                │  Relay 7: ON     │
│                │  Relay 8: OFF    │
└─────────────────────────────────────┘
```

## Detection Logic Explained

### Pair Status

**OK** = Exactly 1 Oil Can AND exactly 1 Bunk Hole detected
- `OC: 1, BH: 1` → ✅ OK

**FAULT** = Any other case:
- `OC: 0, BH: 0` → ❌ Both absent
- `OC: 1, BH: 0` → ❌ Bunk Hole missing
- `OC: 0, BH: 1` → ❌ Oil Can missing
- `OC: 2, BH: 1` → ❌ Multiple Oil Cans
- `OC: 1, BH: 2` → ❌ Multiple Bunk Holes

### Relay States

- **Relay OFF** (0V) = Pair is OK
- **Relay ON** (12V) = Fault detected

**Example:**
```
Machine 1 uses relays 6, 7, 8
Relay 6 = Pair 1 → OFF (OK)
Relay 7 = Pair 2 → ON (FAULT)
Relay 8 = Pair 3 → OFF (OK)
```

## Common Issues & Solutions

### ❌ Camera Not Connecting

**Problem:** "Failed to connect camera"

**Solutions:**
1. Check RTSP URL is correct
2. Verify camera is on network: `ping 192.168.1.64`
3. Test RTSP in VLC: `rtsp://admin:pass@ip:port/path`
4. Check firewall settings
5. Verify camera credentials

### ❌ Relay Not Working

**Problem:** "Failed to initialize relay board"

**Solutions:**
1. Check USB cable connection
2. Verify relay board is powered
3. Check device permissions (Linux: add user to dialout group)
4. Try different USB port
5. Test manually: Menu → Tools → Test Relay Board

### ❌ Model Not Loading

**Problem:** "Failed to load YOLO model"

**Solutions:**
1. Verify `best.pt` exists in project directory
2. Check file is not corrupted
3. Ensure model has correct classes (0=oil_can, 1=bunk_hole)
4. Check Python has enough memory

### ❌ Low FPS

**Problem:** FPS below 10

**Solutions:**
1. Reduce camera resolution in camera settings
2. Increase confidence thresholds in config
3. Check CPU/GPU usage
4. Close other applications
5. Use GPU if available

### ❌ False Detections

**Problem:** Too many false positives

**Solutions:**
1. Increase confidence thresholds in `machines_config.json`:
   ```json
   "confidence_thresholds": {
     "oil_can": 0.50,
     "bunk_hole": 0.45
   }
   ```
2. Retrain boundaries more precisely
3. Improve lighting conditions
4. Retrain YOLO model with more data

## Logs and Debugging

**Log File Location:**
```
multi_machine_YYYYMMDD.log
```

**View Logs:**
- Menu → File → View Logs
- Opens in default text editor

**Log Levels:**
- INFO: Normal operation
- WARNING: Non-critical issues
- ERROR: Failures that need attention
- CRITICAL: System failures

**Example Log:**
```
2025-01-30 14:30:15 - M1: Camera connected - Frame size: (1920, 1080, 3)
2025-01-30 14:30:16 - M1: Boundaries loaded
2025-01-30 14:30:17 - InferenceEngine started
2025-01-30 14:30:18 - M1: Pair status: ['OK', 'FAULT', 'OK']
```

## Tips for Best Results

1. **Lighting**: Ensure consistent lighting at all times
2. **Camera Position**: Keep cameras steady, avoid vibration
3. **Boundaries**: Draw boundaries precisely around expected positions
4. **Confidence**: Start with lower thresholds, increase if too many false positives
5. **Network**: Use wired network for RTSP cameras (not WiFi)
6. **Testing**: Test each machine individually before running all
7. **Monitoring**: Check logs regularly for issues

## Next Steps

Once system is running:

1. **Monitor Performance**
   - Check FPS on each machine
   - Review fault logs
   - Verify relay operation

2. **Fine-Tune**
   - Adjust confidence thresholds
   - Redraw boundaries if needed
   - Optimize camera settings

3. **Production Use**
   - Document your configuration
   - Train operators
   - Set up alerts (future feature)
   - Monitor fault trends

## Support

For issues:
1. Check logs: `multi_machine_YYYYMMDD.log`
2. Verify configuration: `config/machines_config.json`
3. Test components individually
4. Review ARCHITECTURE.md for technical details

---

**System is ready for 24/7 industrial operation!**

© 2025 Credence Technologies Pvt Ltd