# CRITICAL ARCHITECTURE NOTES

## ⚠️ LOG FILE ISOLATION - READ THIS FIRST ⚠️

**EACH PROGRAM'S STATUS IS DERIVED ONLY FROM ITS OWN LOG FILE**

### DO NOT MIX LOG SOURCES:

1. **MMDVMHost Card/Status** 
   - Source: MMDVMHost log files ONLY
   - Shows: Current mode, modem status, transmissions
   - Network pills (DMR, P25, YSF, NXDN, D-Star): Based on `[DMR Network]`, `[P25 Network]` etc. sections in MMDVM.ini
   - These show what networks are ENABLED in MMDVMHost, not gateway connection status

2. **DMRGateway Card/Status**
   - Source: DMRGateway log files ONLY
   - Shows: DMRGateway process status, network connections (HBlink4, BrandMeister, etc.)
   - `DMR-MMDVM` pill: Connection from DMRGateway TO MMDVMHost
   - Network pills (HBlink4, etc.): Actual network connections from DMRGateway logs

3. **YSFGateway Card/Status**
   - Source: YSFGateway log files ONLY
   - Shows: YSFGateway process status, reflector connections
   - `YSF-MMDVM` pill: Connection from YSFGateway TO MMDVMHost ("Link successful to MMDVM")
   - `Reflector` pill: Connection to YSF reflector ("Linked to Kansas")
   - Reflector name: Extracted from "Linked to {name}" in YSFGateway logs

4. **P25Gateway Card/Status**
   - Source: P25Gateway log files ONLY
   - Shows: P25Gateway process status, reflector connections
   - `P25-MMDVM` pill: Connection from P25Gateway TO MMDVMHost ("Opening Rpt network connection")
   - `Reflector` pill: Connection to P25 reflector ("linked to reflector 31328")
   - Reflector number: Extracted from "linked to reflector {number}" in P25Gateway logs

### WHY THIS MATTERS:

Gateway cards show **gateway → MMDVMHost** and **gateway → reflector** connections.
MMDVMHost card shows **modem** and **modes**, NOT gateway connections.

Each program runs independently and logs to its own file. Never try to update gateway status from MMDVMHost logs or vice versa.

### COMMON MISTAKES TO AVOID:

❌ Using MMDVMHost logs to determine gateway connection status
❌ Using gateway logs to determine MMDVMHost network status
❌ Mixing `networks['DMR']` (from MMDVM.ini) with `networks['DMR-HBlink4']` (from DMRGateway logs)
❌ Setting gateway status from config files instead of log parsing

✅ Each card reads ONLY its corresponding log file
✅ MMDVMHost networks come from MMDVM.ini configuration
✅ Gateway networks come from actual log events (connected/disconnected)
