# MMDVM Dashboard Development Guide

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

Create `config/config.json` based on `config/config.example.json`:

```bash
cp config/config.example.json config/config.json
nano config/config.json
```

Edit the log file paths to match your MMDVMHost installation.

### 3. Run Dashboard

```bash
python start_dashboard.py
```

Access at: http://localhost:8080

## Configuration

### Log File Paths

The dashboard monitors log files from MMDVMHost and gateway programs. Configure paths in `config/config.json`:

```json
{
  "log_files": {
    "mmdvmhost": {
      "enabled": true,
      "path": "/var/log/mmdvm/MMDVMHost.log"
    },
    "dmrgateway": {
      "enabled": true,
      "path": "/var/log/mmdvm/DMRGateway.log"
    }
  }
}
```

### Dashboard Settings

```json
{
  "dashboard": {
    "title": "MMDVM Dashboard",
    "description": "Amateur Radio Digital Voice Monitor",
    "host": "0.0.0.0",
    "port": 8080,
    "refresh_interval": 1000
  }
}
```

## Architecture

### Components

1. **Log Parsers** (`dashboard/parsers.py`)
   - Extract structured data from log files
   - Support for MMDVMHost, DMRGateway, YSFGateway, etc.
   - Pattern matching for transmissions, mode changes, network status

2. **Log Monitor** (`dashboard/monitor.py`)
   - Watch log files for changes
   - Parse new entries in real-time
   - Broadcast updates via WebSocket

3. **State Management** (`dashboard/state.py`)
   - Maintain current system status
   - Track active transmissions
   - Store recent calls and events

4. **FastAPI Server** (`dashboard/server.py`)
   - REST API endpoints
   - WebSocket for real-time updates
   - Serve static dashboard files

5. **Web Dashboard** (`dashboard/static/dashboard.html`)
   - Dark-themed responsive UI
   - Real-time updates via WebSocket
   - Statistics and activity monitoring

## Supported Log Formats

### MMDVMHost

The parser recognizes these log patterns:

**Mode Changes:**
```
M: 2025-01-15 12:34:56.789 Mode set to DMR
```

**Transmissions:**
```
M: 2025-01-15 12:34:56.789 DMR Slot 1, received voice header from 3106849 to TG 91
M: 2025-01-15 12:34:56.789 D-Star, received header from N0CALL  /1234    to CQCQCQ
M: 2025-01-15 12:34:56.789 YSF, received header from N0CALL to ALL
M: 2025-01-15 12:34:56.789 P25, received voice header from 1234567 to TG 10100
M: 2025-01-15 12:34:56.789 NXDN, received voice header from 12345 to TG 65000
```

**Network Status:**
```
M: 2025-01-15 12:34:56.789 DMR Network, connected
M: 2025-01-15 12:34:56.789 YSF Network, disconnected
```

### DMRGateway

**Network Login:**
```
M: 2025-01-15 12:34:56.789 Logged into the BrandMeister network
```

**Talkgroup Activity:**
```
M: 2025-01-15 12:34:56.789 Received voice header from 3106849 to TG 91
```

## Development

### Adding New Parsers

To add support for additional log formats:

1. Create a new parser class in `dashboard/parsers.py`
2. Define regex patterns for log lines
3. Implement `parse_line()` method
4. Add to parser factory in `get_parser()`

Example:

```python
class MyGatewayParser:
    TIMESTAMP_PATTERN = r'([MDISEWF]):\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        # Parse log line
        # Return LogEntry with structured data
        pass
```

### Testing Without MMDVMHost

Create a test log file:

```bash
mkdir -p /tmp/test-logs
cat > /tmp/test-logs/MMDVMHost.log << 'EOF'
M: 2025-01-15 12:00:00.000 Mode set to DMR
M: 2025-01-15 12:00:01.000 DMR Slot 1, received voice header from 3106849 to TG 91
M: 2025-01-15 12:00:05.000 DMR Slot 1, transmission ended, duration: 4.2s
EOF
```

Configure `config/config.json`:
```json
{
  "log_files": {
    "mmdvmhost": {
      "enabled": true,
      "path": "/tmp/test-logs/MMDVMHost.log"
    }
  }
}
```

Append new lines to see real-time updates:
```bash
echo "M: $(date '+%Y-%m-%d %H:%M:%S.000') DMR Slot 1, received voice header from 1234567 to TG 3100" >> /tmp/test-logs/MMDVMHost.log
```

## API Endpoints

### GET /api/config
Returns dashboard configuration

### GET /api/status
Returns current system status:
- Current mode
- Modem connection status
- Network connections
- Active transmissions count
- Statistics

### GET /api/transmissions
Returns active and recent transmissions

### GET /api/events?limit=50
Returns recent events (mode changes, network status, etc.)

### GET /api/stats
Returns system statistics

### WebSocket /ws
Real-time updates for all dashboard data

## Troubleshooting

### Dashboard shows "Disconnected"
- Check that log files exist and are readable
- Verify paths in `config/config.json`
- Check server logs for errors

### No transmissions appearing
- Verify log file format matches parser patterns
- Check that log files are being written to
- Enable debug logging to see parsing details

### WebSocket connection fails
- Check firewall settings
- Verify port is not already in use
- Try different browser

## License

GNU GPLv3

## Credits

Visual design inspired by [HBLink4](https://github.com/n0mjs710/hblink4) dashboard by N0MJS710.
