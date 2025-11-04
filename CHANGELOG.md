# Changelog

All notable changes to MMDVM Dashboard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-04

### Tested and Verified
- ✅ DMR mode and DMRGateway (fully functional)
- ✅ YSF mode and YSFGateway (fully functional with reflector support)
- ✅ P25 mode and P25Gateway (fully functional with reflector support)
- ✅ FM mode (tracking functional)

### Implemented but Untested
- ⚠️ D-Star mode (code present, not verified on live system)
- ⚠️ NXDN mode and NXDNGateway (code present, not verified on live system)
- ⚠️ POCSAG mode (code present, not verified on live system)

### Added
- Real-time log monitoring for MMDVMHost and gateway programs
- WebSocket-based live updates for system status
- Configuration-aware monitoring (reads MMDVM.ini and gateway configs)
- Multi-day log scanning for initial state discovery (up to 5 days back)
- Mode and network status cards with three-state pills (connected/disconnected/unknown)
- Gateway support: DMRGateway, YSFGateway, P25Gateway, NXDNGateway
- Multi-mode support: DMR, D-Star, YSF, P25, NXDN, FM
- Repeater information display (callsign, frequencies, location)
- Live transmission tracking with mode hang detection
- Resizable log viewer window with ring buffer (configurable, default 50 lines)
- Mode name normalization (System Fusion → YSF)
- Process status monitoring via systemctl
- Disabled/enabled stanza visualization in gateway cards

### Technical Features
- FastAPI backend with async log monitoring
- Pre-compiled regex patterns for optimal performance
- Incremental multi-day log scanning (stops when state found)
- Configuration merging (user config + defaults)
- Ring buffer for recent log entries
- Modern dark UI with responsive design

### Configuration
- Minimal configuration required (host, port, monitoring limits)
- Automatic detection of log paths from INI files
- Process name mapping for systemd services
- Configurable log buffer size

### Documentation
- Comprehensive README with Quick Start guide
- DEVELOPMENT.md with architecture details
- CRITICAL-ARCHITECTURE-NOTES.md for implementation specifics
- UI-DESIGN.md for interface guidelines

### Performance
- Optimized for single-board computers (tested on NanoPi NEO)
- Minimal resource footprint
- Efficient log parsing with pattern caching
- Debounced WebSocket broadcasts

## [Unreleased]

### Future Considerations
- Historical statistics and graphs
- Alert/notification system
- Mobile-optimized layout
- Theme customization
- Export functionality for logs/stats

---

[1.0.0]: https://github.com/n0mjs710/mmdvm-dash/releases/tag/v1.0.0
