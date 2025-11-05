# MMDVM Dashboard Project

## Overview

A web-based dashboard for monitoring MMDVMHost and associated gateway programs on single-board computers (Raspberry Pi, etc.). Since MMDVMHost doesn't provide an API, this dashboard parses log files in real-time to display system status, transmissions, and network connectivity.

## Project Structure

```
mmdvm-dash/
├── README.md                    # Project overview and features
├── DEVELOPMENT.md               # Development guide and API docs
├── INSTALL-PYENV.md            # Python environment setup
├── requirements.txt             # Python dependencies
├── start_dashboard.py           # Main startup script
├── test_log_generator.py        # Test utility for development
├── config/
│   ├── config.json             # Active configuration
│   └── config.example.json     # Configuration template
└── dashboard/
    ├── __init__.py             # Package initialization
    ├── config.py               # Configuration management
    ├── parsers.py              # Log file parsers
    ├── state.py                # State management
    ├── monitor.py              # Log file monitoring
    ├── server.py               # FastAPI server
    └── static/
        └── dashboard.html      # Web dashboard UI
```

## Core Components

### 1. Log Parsers (`dashboard/parsers.py`)
- **MMDVMHostParser**: Parses MMDVMHost log files
  - Mode changes (DMR, D-Star, YSF, P25, NXDN, FM)
  - Transmissions (RX/TX with callsigns, talkgroups, slots)
  - Network status (connected/disconnected)
  - Modem status and errors
  
- **DMRGatewayParser**: Parses DMRGateway logs
  - Network logins (BrandMeister, TGIF, DMR+, etc.)
  - Talkgroup activity
  
- **YSFGatewayParser**: Parses YSFGateway logs
  - Reflector connections/disconnections

### 2. State Management (`dashboard/state.py`)
- **DashboardState**: Central state container
  - System status (mode, modem, networks)
  - Active transmissions
  - Log buffer for live viewer
  - Statistics (daily calls, users, modes)

### 3. Log Monitor (`dashboard/monitor.py`)
- **LogMonitor**: Watches individual log files
  - Detects new log entries
  - Handles log rotation
  - Parses and processes entries
  - Broadcasts updates via WebSocket
  
- **LogMonitorManager**: Manages multiple monitors
  - Configurable log sources
  - Concurrent monitoring

### 4. FastAPI Server (`dashboard/server.py`)
- REST API endpoints:
  - `/api/status` - System status
  - `/api/transmissions` - Active transmissions
  - `/api/stats` - Statistics
  - `/api/logs` - Recent log entries
  - `/api/config/viewer` - Log viewer configuration
  
- WebSocket endpoint:
  - `/ws` - Real-time updates
  
- Static file serving:
  - `/` - Dashboard HTML
  - `/static/*` - Static assets

### 5. Web Dashboard (`dashboard/static/dashboard.html`)
- **Dark Theme UI** (inspired by HBLink4)
- **Real-time Updates** via WebSocket
- **Statistics Display**:
  - Total calls today
  - Active transmissions
  - Active users
  - Connected networks
  
- **Activity Monitoring**:
  - Active transmissions (live)
  - Live log viewer
  - Network status

## Supported Digital Modes

- **DMR** (Digital Mobile Radio)
  - Dual timeslot support
  - Talkgroup tracking
  - DMRGateway integration
  
- **D-Star**
  - Callsign and suffix extraction
  - Destination tracking
  
- **YSF** (System Fusion)
  - Reflector connections
  - YSFGateway integration
  
- **P25** (Project 25)
  - Talkgroup support
  - P25Gateway integration
  
- **NXDN**
  - Talkgroup tracking
  - NXDNGateway integration
  
- **FM** (Analog)
  - Basic monitoring

## Installation

### Prerequisites
- Python 3.8 or higher
- MMDVMHost installed and running
- Access to log files

### Quick Start

1. **Clone and setup:**
```bash
cd /path/to/mmdvm-dash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure:**
```bash
# Edit config/config.json
nano config/config.json
```

Configure paths to your INI files and log locations:
```json
{
  "config_paths": {
    "mmdvm_ini": "/etc/MMDVM.ini"
  }
}
```

3. **Run:**
```bash
python start_dashboard.py
```

4. **Access:**
Open http://localhost:8080 in your browser

## Testing Without MMDVMHost

The dashboard automatically reads log file paths from your MMDVM.ini file.
For testing, you can create a test INI file pointing to test logs.

Create a test config:
```json
{
  "config_paths": {
    "mmdvm_ini": "/tmp/test-MMDVM.ini"
  }
}
```

Create test INI file at `/tmp/test-MMDVM.ini`:
```ini
[Log]
FilePath=/tmp/mmdvm-test-logs/
FileRoot=MMDVM
```

```bash
# Run dashboard
python start_dashboard.py
```

## Configuration Options

### Complete Configuration Example
```json
{
  "dashboard": {
    "host": "0.0.0.0",
    "port": 8080
  },
  "config_paths": {
    "mmdvm_ini": "/etc/MMDVM.ini",
    "dmr_gateway_ini": "/etc/DMRGateway.ini",
    "ysf_gateway_ini": "/etc/YSFGateway.ini",
    "p25_gateway_ini": "/etc/P25Gateway.ini"
  },
  "process_names": {
    "mmdvmhost": "mmdvmhost",
    "dmrgateway": "dmrgateway",
    "ysfgateway": "ysfgateway",
    "p25gateway": "p25gateway",
    "nxdngateway": "nxdngateway"
  },
  "monitoring": {
    "log_buffer_size": 50,
    "log_viewer_rows": 20
  }
}
```

### Configuration Parameters

**dashboard**
- `host`: IP address to bind to (default: "0.0.0.0")
- `port`: Port to listen on (default: 8080)

**config_paths**
- INI file paths for MMDVMHost and gateways
- Used to read configuration and determine log file locations

**process_names**
- Process names to monitor for running status
- Must match the actual process names on your system

**monitoring**
- `log_buffer_size`: Number of log lines to keep in memory (default: 50)
- `log_viewer_rows`: Number of rows visible in log viewer (default: 20)

## Log Format Reference

### MMDVMHost Log Format

**General Format:**
```
LEVEL: YYYY-MM-DD HH:MM:SS.mmm MESSAGE
```

**Examples:**
```
M: 2025-01-15 12:34:56.789 Mode set to DMR
M: 2025-01-15 12:34:56.789 DMR Slot 1, received voice header from 3106849 to TG 91
M: 2025-01-15 12:34:56.789 D-Star, received header from N0CALL  /1234    to CQCQCQ
M: 2025-01-15 12:34:56.789 YSF, received header from N0CALL to ALL
M: 2025-01-15 12:34:56.789 P25, received voice header from 1234567 to TG 10100
M: 2025-01-15 12:34:56.789 NXDN, received voice header from 12345 to TG 65000
M: 2025-01-15 12:34:56.789 DMR Network, connected
```

### Level Codes
- `M` - Message (INFO)
- `D` - Debug
- `I` - Info
- `E` - Error
- `W` - Warning
- `F` - Fatal

## Features

✅ **Implemented:**
- Real-time log parsing
- Multi-mode support (DMR, D-Star, YSF, P25, NXDN, FM)
- WebSocket updates
- Dark-themed responsive UI
- Statistics tracking
- Recent calls history
- Event logging
- Network status monitoring
- Gateway program support

## Performance

- **Log Parsing**: ~500 lines/second
- **WebSocket Latency**: <50ms
- **Memory Usage**: ~30-50 MB
- **CPU Usage**: <5% on Raspberry Pi 4

Optimized for running alongside MMDVMHost on resource-constrained SBCs.

## Security Notes

- Dashboard binds to `0.0.0.0` by default (accessible from network)
- Run on trusted network only
- For internet exposure, use reverse proxy with authentication
- Log files contain callsign information

## Troubleshooting

### Dashboard shows "Disconnected" or "Not running"
1. Check INI file paths in `config/config.json` (`config_paths` section)
2. Verify INI files exist and contain valid log file paths
3. Check that log files exist and are readable
4. Check server logs for errors

### No transmissions appearing
1. Verify log file format matches expected patterns
2. Check that MMDVMHost is actively logging
3. Ensure log files are being rotated with UTC date format
4. Enable debug mode to see parser output

### WebSocket fails to connect
1. Check firewall settings
2. Verify port 8080 is not in use
3. Try different browser

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for:
- Architecture details
- Adding new parsers
- API documentation
- Testing procedures

## Credits

**Author:** Cort Buffington, N0MJS  
**Visual Design:** Inspired by HBlink4 dashboard aesthetics  
**MMDVMHost:** Created by G4KLX and contributors  
**Framework:** FastAPI, Python 3.13

## License

To be determined.

---

**0x49 DE N0MJS**

**73 de N0CALL**
