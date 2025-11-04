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
    # CONFIRMED USEFUL: Connection to MMDVMHost at startup
    # Matches: "MMDVM has connected"
    # No capture groups - just detects initial connection
    'mmdvm_connected': r'MMDVM has connected',
    
    # CONFIRMED USEFUL: Network connections (e.g., HBlink4, BrandMeister, etc.)
    # Matches: "HBlink4, Logged into the master successfully"
    # Groups: (1) network name (everything before comma)
    'network_connected': r'(.+), Logged into the master successfully',
    
    # CONFIRMED USEFUL: Network disconnections/timeouts
    # Matches: "HBlink4, Connection to the master has timed out, retrying connection"
    # Groups: (1) network name
    'network_disconnected': r'(.+), Connection to the master has timed out',
}

# =============================================================================
# YSF GATEWAY PATTERNS
# =============================================================================
YSFGATEWAY_PATTERNS = {
    # CONFIRMED USEFUL: Reflector connections
    # Matches: "Linked to Kansas          " (note: reflector name may have trailing spaces)
    # Groups: (1) reflector name (trailing spaces removed in parser)
    # This means BOTH network connected AND reflector connected (they are the same thing)
    'reflector_linked': r'Linked to (.+?)(?:\s+)?$',
    
    # CONFIRMED USEFUL: Network/Reflector disconnect
    # Matches: "Closing YSF network connection"
    # No capture groups
    # This means BOTH network disconnected AND reflector disconnected
    'network_disconnected': r'Closing YSF network connection',
    
    # NOT USEFUL - DO NOT USE: These look helpful but don't indicate actual connection status
    # 'reconnecting': r'Reconnecting startup reflector',
    # 'auto_reconnect': r'Automatic \(re-\)connection to (\d+) - "(.+?)"',
}

# =============================================================================
# P25 GATEWAY PATTERNS
# =============================================================================
P25GATEWAY_PATTERNS = {
    # CONFIRMED USEFUL: Reflector connection (but doesn't confirm it worked)
    # Matches: "Statically linked to reflector 31328"
    # Groups: (1) reflector number
    # NOTE: This just shows intent to link, not that it actually succeeded
    'reflector_linked': r'Statically linked to reflector (\d+)',
    
    # NOT USEFUL - DO NOT USE: These appear but don't indicate actual connection
    # 'opening_rpt': r'Opening Rpt network connection',
    # 'opening_p25': r'Opening P25 network connection',
}

# =============================================================================
# NXDN GATEWAY PATTERNS
# =============================================================================
# NXDN not included in user analysis - keeping structure for future expansion
NXDNGATEWAY_PATTERNS = {}

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
