"""
Log Pattern Definitions for MMDVM Dashboard

This module centralizes all log parsing patterns for different protocols and gateways.
Each protocol defines standard events (connected, disconnected, link_failed, etc.) with
their specific regex patterns.

Patterns are pre-compiled at module load time for optimal performance.

Adding a new protocol:
1. Add a new dictionary with the protocol name
2. Define patterns for standard events: connected, disconnected, link_failed, etc.
3. Add protocol-specific events as needed
4. Update get_parser() in parsers.py to use the new patterns
"""
import re

# Standard gateway events that should be consistent across protocols
STANDARD_GATEWAY_EVENTS = [
    'mmdvm_connected',      # Gateway connected to MMDVMHost
    'mmdvm_disconnected',   # Gateway disconnected from MMDVMHost
    'network_connected',    # Connected to network/reflector
    'network_disconnected', # Disconnected from network/reflector
    'link_failed',          # Connection lost (timeout/error)
]

# =============================================================================
# MMDVMHOST PATTERNS
# =============================================================================
MMDVMHOST_PATTERNS = {
    # Mode changes - the repeater switching between protocols
    # Matches: "Mode set to DMR" or "Mode set to IDLE"
    # Groups: (1) mode name
    'mode_change': r'Mode set to (.+)',
    
    # Modem/hardware connection
    # Matches: "MMDVM protocol version: 1, description: MMDVM 20170924 TCXO ADF7021 FW by CA6JAU GitID #4b0bfeb (D-Star/DMR/P25/NXDN)"
    # Groups: (1) protocol version, (2) description
    'modem_connected': r'MMDVM protocol version: (\d+), description: (.+)',
    
    # Network status (when MMDVMHost connects to protocol networks)
    # These are rarely used as gateways handle network connections
    'dmr_network_connected': r'DMR, Connection to ([^\s]+) opened',
    'p25_network_connected': r'P25, Connection to ([^\s]+) opened',
    'ysf_network_connected': r'YSF, Connection to ([^\s]+) opened',
    'nxdn_network_connected': r'NXDN, Connection to ([^\s]+) opened',
    
    # Voice transmissions - start
    # DMR: "DMR Slot 2, received RF voice header from N0CALL to TG 31665"
    # Groups: (1) slot number, (2) network|RF, (3) callsign, (4) talkgroup
    'dmr_rx': r'DMR Slot (\d), received (network|RF) voice header from ([A-Z0-9]+) to TG\s*(\d+)',
    
    # D-Star: "D-Star, received header from N0CALL  /1234    to  CQCQCQ"
    # Groups: (1) callsign, (2) suffix, (3) destination
    'dstar_rx': r'D-Star, received (?:header|data) from ([A-Z0-9]+)\s+/([A-Z0-9]+)\s+to\s+([A-Z0-9]+)',
    
    # YSF: "YSF, received RF header from N0CALL       to DG-ID 0"
    # Groups: (1) network|RF, (2) callsign with trailing spaces, (3) DG-ID
    'ysf_rx': r'YSF, received (network|RF) header from ([A-Z0-9\s]+)\s+to DG-ID\s+(\d+)',
    
    # P25: "P25, received RF voice transmission from N0CALL to TG 31328"
    # Groups: (1) network|RF, (2) callsign, (3) talkgroup
    'p25_rx': r'P25, received (network|RF) (?:voice transmission|header) from ([A-Z0-9]+) to TG\s*(\d+)',
    
    # NXDN: "NXDN, received RF voice header from N0CALL to TG 9"
    # Groups: (1) network|RF, (2) callsign, (3) talkgroup (TG prefix optional)
    'nxdn_rx': r'NXDN, received (network|RF) (?:voice|data) (?:header|transmission) from ([A-Z0-9]+) to (?:TG\s*)?(\d+)',
    
    # Note: FM does not log reception events - only mode changes
    
    # Voice transmissions - end
    # DMR: "DMR Slot 2, received RF end of voice transmission from N0CALL to TG 31665, 3.5 seconds, BER: 0.0%"
    # Groups: (1) slot, (2) network|RF, (3) callsign, (4) talkgroup
    'dmr_end': r'DMR Slot (\d), received (network|RF) end of voice transmission from ([A-Z0-9]+) to TG\s*(\d+)',
    
    # D-Star: "D-Star, end of transmission, 12.3 seconds, BER: 0.2%"
    # No capture groups - just detects end of transmission
    'dstar_end': r'D-Star, end of transmission',
    
    # YSF: "YSF, received RF end of transmission from N0CALL       to DG-ID 0, 2.1 seconds"
    # Groups: (1) network|RF, (2) callsign with spaces, (3) DG-ID
    'ysf_end': r'YSF, received (network|RF) end of transmission from ([A-Z0-9\s]+)\s+to DG-ID\s+(\d+)',
    
    # P25: "P25, received RF end of voice transmission from N0CALL to TG 31328, 4.2 seconds"
    # Groups: (1) network|RF, (2) callsign, (3) talkgroup
    'p25_end': r'P25, received (network|RF) end of voice transmission from ([A-Z0-9]+) to TG\s*(\d+)',
    
    # NXDN: "NXDN, received RF end of transmission from N0CALL to TG 9"
    # Groups: (1) network|RF, (2) callsign, (3) talkgroup
    'nxdn_end': r'NXDN, received (network|RF) end of transmission from ([A-Z0-9]+) to (?:TG\s*)?(\d+)',
}

# =============================================================================
# DMR GATEWAY PATTERNS
# =============================================================================
DMRGATEWAY_PATTERNS = {
    # Connection to MMDVMHost
    # Matches: "MMDVM has connected"
    # No capture groups - just detects connection
    'mmdvm_connected': r'MMDVM has connected',
    
    # Network connections (e.g., HBlink4, BrandMeister, etc.)
    # Matches: "HBlink4, Logged into the master successfully"
    # Groups: (1) network name (everything before comma)
    'network_connected': r'(.+), Logged into the master successfully',
    
    # Network disconnections
    # Matches: "HBlink4, Closing DMR Network"
    # Groups: (1) network name
    'network_disconnected': r'(.+), Closing DMR Network',
    
    # Talkgroup activity (legacy - may not be in current logs)
    # Matches: "Received voice header from 3113999 to TG 31665"
    # Groups: (1) source ID, (2) talkgroup
    'talkgroup_activity': r'Received voice (?:header|data) from (\d+) to TG (\d+)',
}

# =============================================================================
# YSF GATEWAY PATTERNS
# =============================================================================
YSFGATEWAY_PATTERNS = {
    # Connection to MMDVMHost
    # Matches: "Link successful to MMDVM"
    # No capture groups
    'mmdvm_connected': r'Link successful to MMDVM',
    
    # Reflector connections
    # Matches: "Linked to Kansas          " (note: reflector name may have trailing spaces)
    # Groups: (1) reflector name (trailing spaces removed by .strip() in parser)
    'network_connected': r'Linked to (.+?)(?:\s+)?$',
    
    # Automatic reflector reconnection
    # Matches: "Automatic (re-)connection to 12345 - "US Mountain""
    # Groups: (1) reflector ID number, (2) reflector name
    'network_reconnected': r'Automatic \(re-\)connection to (\d+) - "(.+?)"',
    
    # Manual connection request
    # Matches: "Connect to US Mountain has been requested"
    # Groups: (1) reflector name
    'network_connect_requested': r'Connect to (.+) has been requested',
    
    # Reflector disconnections
    # Manual disconnect: "Disconnect has been requested"
    # No capture groups
    'network_disconnected': r'Disconnect has been requested',
    
    # Connection lost (polls lost)
    # Matches: "Link has failed, polls lost"
    # No capture groups - indicates connection timeout/failure
    'link_failed': r'Link has failed',
}

# =============================================================================
# P25 GATEWAY PATTERNS
# =============================================================================
P25GATEWAY_PATTERNS = {
    # Connection to MMDVMHost
    # Matches: "Opening Rpt network connection"
    # No capture groups
    'mmdvm_connected': r'Opening Rpt network connection',
    
    # Disconnection from MMDVMHost
    # Matches: "Closing Rpt network connection"
    # No capture groups
    'mmdvm_disconnected': r'Closing Rpt network connection',
    
    # Reflector connections
    # Matches: "P25, linked to reflector 31328" or "P25GW, linked to reflector 3120"
    # Groups: (1) reflector number
    'network_connected': r'linked to reflector (\d+)',
    
    # P25 network opening (before link established)
    # Matches: "Opening P25 network connection"
    # No capture groups
    'network_opening': r'Opening P25 network connection',
    
    # Reflector disconnections
    # Matches: "Closing P25 network connection"
    # No capture groups
    'network_disconnected': r'Closing P25 network connection',
    
    # Connection lost (network error)
    # Matches: "Error returned from recvfrom, err: 88"
    # No capture groups - indicates socket/network failure
    'link_failed': r'Error returned from recvfrom',
}

# =============================================================================
# NXDN GATEWAY PATTERNS
# =============================================================================
NXDNGATEWAY_PATTERNS = {
    # Connection to MMDVMHost
    # Matches: "Link successful to MMDVM"
    # No capture groups (same format as YSF)
    'mmdvm_connected': r'Link successful to MMDVM',
    
    # Reflector connections
    # Matches: "Linked to NXDN Reflector" (format similar to YSF)
    # Groups: (1) reflector name
    'network_connected': r'Linked to (.+?)(?:\s+)?$',
    
    # Automatic reconnection (if supported)
    # Groups: (1) reflector ID, (2) reflector name
    'network_reconnected': r'Automatic \(re-\)connection to (\d+) - "(.+?)"',
    
    # Manual connection request
    # Groups: (1) reflector name
    'network_connect_requested': r'Connect to (.+) has been requested',
    
    # Reflector disconnections
    # Manual disconnect request
    # No capture groups
    'network_disconnected': r'Disconnect has been requested',
    
    # Connection lost (polls lost)
    # Same as YSF - indicates connection timeout
    # No capture groups
    'link_failed': r'Link has failed',
}

# =============================================================================
# PATTERN COMPILATION - Pre-compile all patterns for performance
# =============================================================================
def _compile_patterns(pattern_dict):
    """
    Pre-compile all regex patterns in a dictionary for better performance.
    
    Instead of compiling patterns on every log line parse, we compile them once
    at module load time. This significantly improves performance for high-volume
    log parsing.
    
    Args:
        pattern_dict: Dictionary of pattern_name -> regex_string
        
    Returns:
        Dictionary of pattern_name -> compiled regex object
    """
    return {key: re.compile(pattern) for key, pattern in pattern_dict.items()}

# Pre-compile all patterns at module load time
_COMPILED_PATTERNS = {
    'mmdvmhost': _compile_patterns(MMDVMHOST_PATTERNS),
    'dmrgateway': _compile_patterns(DMRGATEWAY_PATTERNS),
    'ysfgateway': _compile_patterns(YSFGATEWAY_PATTERNS),
    'p25gateway': _compile_patterns(P25GATEWAY_PATTERNS),
    'nxdngateway': _compile_patterns(NXDNGATEWAY_PATTERNS),
}

# =============================================================================
# PATTERN LOOKUP
# =============================================================================
def get_patterns(protocol: str) -> dict:
    """
    Get pre-compiled regex patterns for a specific protocol.
    
    Returns compiled regex objects for optimal performance - no need to compile
    patterns on every log line parse.
    
    Args:
        protocol: Protocol name (mmdvmhost, dmrgateway, ysfgateway, p25gateway, nxdngateway)
    
    Returns:
        Dictionary of event_name -> compiled regex pattern object
    """
    return _COMPILED_PATTERNS.get(protocol.lower(), {})


def get_all_patterns() -> dict:
    """
    Get all pre-compiled patterns for all protocols.
    
    Returns:
        Dictionary of protocol_name -> patterns_dict (with compiled regex objects)
    """
    return _COMPILED_PATTERNS
