# CRITICAL ARCHITECTURE NOTES

## ⚠️ LOG FILE ISOLATION - READ THIS FIRST ⚠️

**EACH PROGRAM'S STATUS IS DERIVED ONLY FROM ITS OWN LOG FILE**

### DO NOT MIX LOG SOURCES:

1. **MMDVMHost Card/Status** 
   - Source: MMDVMHost log files ONLY
   - Shows: Current mode, modem status, RF and network transmissions
   - Network pills (DMR, P25, YSF, NXDN, D-Star): Based on `[DMR Network]`, `[P25 Network]` etc. sections in MMDVM.ini
   - These show what networks are ENABLED in MMDVMHost, not gateway connection status

2. **DMRGateway Card/Status**
   - Source: DMRGateway log files + DMRGateway.ini ONLY
   - Shows: All stanzas with Enable parameter (networks and features)
   - Network pills (HBlink4, BrandMeister, etc.): Actual connections tracked from "Logged into the master successfully" / "timed out"
   - Feature pills (Dynamic TG Control, Remote Control, etc.): Enabled/disabled from config
   - Connection states: Light blue (connected), dark blue (enabled/disconnected), yellow (unknown), outlined (disabled in config)

3. **YSFGateway Card/Status**
   - Source: YSFGateway log files + YSFGateway.ini ONLY
   - Shows: All stanzas with Enable parameter (networks and features)
   - Network pills (YSF Network, FCS Network): Tracked from "Linked to {reflector}" / "Closing YSF network connection"
   - Feature pills (APRS, GPSD, Remote Commands): Enabled/disabled from config
   - Reflector name: Displayed below pills when connected
   - Connection states: Light blue (connected), dark blue (enabled/disconnected), yellow (unknown), outlined (disabled in config)

4. **P25Gateway Card/Status**
   - Source: P25Gateway log files + P25Gateway.ini ONLY
   - Shows: Network section (implicitly enabled) + features with Enable parameter
   - Network pill: Tracked from "Statically linked to reflector {number}"
   - Feature pills (Voice, Remote Commands): Enabled/disabled from config
   - Reflector number: Displayed below pills when connected
   - Connection states: Light blue (connected), dark blue (enabled/disconnected), yellow (unknown), outlined (disabled in config)

## THREE-STATE PILL SYSTEM

Each gateway card displays ALL stanzas found in the config file with an Enable/Enabled parameter:

### Network Pills (type='network'):
- **Light Blue (filled)**: Network connected (tracked from log events)
- **Dark Blue (filled)**: Network enabled but disconnected
- **Yellow (filled)**: State unknown (not found in 14-day log scan)
- **Outlined (empty)**: Disabled in config (Enable=0)

### Feature Pills (type='feature'):
- **Dark Blue (filled)**: Feature enabled in config
- **Outlined (empty)**: Feature disabled in config (Enable=0)

## 14-DAY LOG LOOKBACK

On startup, each monitor scans logs backwards to find current state:
1. Try today's log file first
2. If not found, check previous day incrementally (up to 14 days back)
3. Stop as soon as all required state is found (efficient)
4. If state not found after 14 days, mark as 'unknown' (yellow pill)

This prevents assuming connection state when gateways have been running for days/weeks without reconnection events.

## RELIABLE PATTERNS ONLY

Based on 9 years of operational experience (since 2016), only confirmed reliable patterns are used:

### DMRGateway:
- ✅ `"Logged into the master successfully"` → network connected
- ✅ `"Connection to the master has timed out"` → network disconnected
- ❌ Other patterns are misleading or unreliable

### YSFGateway:
- ✅ `"Linked to {reflector}"` → reflector/network connected (they are the same)
- ✅ `"Closing YSF network connection"` → reflector/network disconnected
- ❌ "Reconnecting" messages do NOT indicate actual connection state

### P25Gateway:
- ✅ `"Statically linked to reflector {number}"` → shows reflector ID
- ⚠️  Cannot reliably verify actual connection, assume connected if process running
- ❌ "Opening connection" messages do NOT indicate successful connection

## WHY THIS MATTERS:

Gateway cards show **gateway → MMDVMHost** and **gateway → reflector** connections.
MMDVMHost card shows **modem** and **modes**, NOT gateway connections.

Each program runs independently and logs to its own file. Never try to update gateway status from MMDVMHost logs or vice versa.

## COMMON MISTAKES TO AVOID:

❌ Using MMDVMHost logs to determine gateway connection status
❌ Using gateway logs to determine MMDVMHost network status  
❌ Mixing `networks['DMR']` (from MMDVM.ini) with `networks['DMR-HBlink4']` (from DMRGateway logs)
❌ Setting gateway status from config files instead of log parsing
❌ Assuming connection state without checking recent logs
❌ Using unreliable patterns (reconnecting messages, opening connection messages)

✅ Each card reads ONLY its corresponding log file
✅ MMDVMHost networks come from MMDVM.ini configuration
✅ Gateway networks come from actual log events (connected/disconnected)
✅ Unknown state shown honestly when logs don't contain connection info
✅ All config stanzas visible (enabled AND disabled)
✅ Only use confirmed reliable patterns from years of operational experience
