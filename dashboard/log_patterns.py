"""
Log Pattern Definitions for MMDVM Dashboard

This module centralizes all log parsing patterns for different protocols and gateways.
Each protocol defines standard events (connected, disconnected, link_failed, etc.) with
their specific regex patterns.

Adding a new protocol:
1. Add a new dictionary with the protocol name
2. Define patterns for standard events: connected, disconnected, link_failed, etc.
3. Add protocol-specific events as needed
4. Update get_parser() in parsers.py to use the new patterns
"""

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
    'mode_change': r'Mode set to (.+)',
    
    # Modem/hardware connection
    'modem_connected': r'MMDVM protocol version: (\d+), description: (.+)',
    
    # Network status (when MMDVMHost connects to protocol networks)
    'dmr_network_connected': r'DMR, Connection to ([^\s]+) opened',
    'p25_network_connected': r'P25, Connection to ([^\s]+) opened',
    'ysf_network_connected': r'YSF, Connection to ([^\s]+) opened',
    'nxdn_network_connected': r'NXDN, Connection to ([^\s]+) opened',
    
    # Voice transmissions - start
    'dmr_rx': r'DMR Slot (\d), received (network|RF) voice header from ([A-Z0-9]+) to TG\s*(\d+)',
    'dstar_rx': r'D-Star, received (?:header|data) from ([A-Z0-9]+)\s+/([A-Z0-9]+)\s+to\s+([A-Z0-9]+)',
    'ysf_rx': r'YSF, received (network|RF) header from ([A-Z0-9\s]+)\s+to DG-ID\s+(\d+)',
    'p25_rx': r'P25, received (network|RF) (?:voice transmission|header) from ([A-Z0-9]+) to TG\s*(\d+)',
    'nxdn_rx': r'NXDN, received (network|RF) (?:voice|data) (?:header|transmission) from ([A-Z0-9]+) to (?:TG\s*)?(\d+)',
    'fm_rx': r'FM, received (?:header|transmission)',
    
    # Voice transmissions - end
    'dmr_end': r'DMR Slot (\d), received (network|RF) end of voice transmission from ([A-Z0-9]+) to TG\s*(\d+)',
    'dstar_end': r'D-Star, end of transmission',
    'ysf_end': r'YSF, received (network|RF) end of transmission from ([A-Z0-9\s]+)\s+to DG-ID\s+(\d+)',
    'p25_end': r'P25, received (network|RF) end of voice transmission from ([A-Z0-9]+) to TG\s*(\d+)',
    'nxdn_end': r'NXDN, received (network|RF) end of transmission from ([A-Z0-9]+) to (?:TG\s*)?(\d+)',
}

# =============================================================================
# DMR GATEWAY PATTERNS
# =============================================================================
DMRGATEWAY_PATTERNS = {
    # Connection to MMDVMHost
    'mmdvm_connected': r'MMDVM has connected',
    
    # Network connections (e.g., HBlink4, BrandMeister, etc.)
    'network_connected': r'(.+), Logged into the master successfully',
    'network_disconnected': r'(.+), Closing DMR Network',
    
    # Talkgroup activity (legacy - may not be needed)
    'talkgroup_activity': r'Received voice (?:header|data) from (\d+) to TG (\d+)',
}

# =============================================================================
# YSF GATEWAY PATTERNS
# =============================================================================
YSFGATEWAY_PATTERNS = {
    # Connection to MMDVMHost
    'mmdvm_connected': r'Link successful to MMDVM',
    
    # Reflector connections
    'network_connected': r'Linked to (.+?)(?:\s+)?$',  # "Linked to Kansas          "
    'network_reconnected': r'Automatic \(re-\)connection to (\d+) - "(.+?)"',
    'network_connect_requested': r'Connect to (.+) has been requested',
    
    # Reflector disconnections
    'network_disconnected': r'Disconnect has been requested',
    'link_failed': r'Link has failed',  # Connection lost (polls lost)
}

# =============================================================================
# P25 GATEWAY PATTERNS
# =============================================================================
P25GATEWAY_PATTERNS = {
    # Connection to MMDVMHost
    'mmdvm_connected': r'Opening Rpt network connection',
    'mmdvm_disconnected': r'Closing Rpt network connection',
    
    # Reflector connections
    'network_connected': r'linked to reflector (\d+)',
    'network_opening': r'Opening P25 network connection',
    
    # Reflector disconnections
    'network_disconnected': r'Closing P25 network connection',
    'link_failed': r'Error returned from recvfrom',  # Connection lost
}

# =============================================================================
# NXDN GATEWAY PATTERNS
# =============================================================================
NXDNGATEWAY_PATTERNS = {
    # Connection to MMDVMHost
    'mmdvm_connected': r'Link successful to MMDVM',
    
    # Reflector connections (similar to YSF)
    'network_connected': r'Linked to (.+?)(?:\s+)?$',
    'network_reconnected': r'Automatic \(re-\)connection to (\d+) - "(.+?)"',
    'network_connect_requested': r'Connect to (.+) has been requested',
    
    # Reflector disconnections
    'network_disconnected': r'Disconnect has been requested',
    'link_failed': r'Link has failed',
}

# =============================================================================
# PATTERN LOOKUP
# =============================================================================
def get_patterns(protocol: str) -> dict:
    """
    Get log patterns for a specific protocol.
    
    Args:
        protocol: Protocol name (mmdvmhost, dmrgateway, ysfgateway, p25gateway, nxdngateway)
    
    Returns:
        Dictionary of event_name -> regex_pattern
    """
    patterns = {
        'mmdvmhost': MMDVMHOST_PATTERNS,
        'mmdvm': MMDVMHOST_PATTERNS,
        'dmrgateway': DMRGATEWAY_PATTERNS,
        'ysfgateway': YSFGATEWAY_PATTERNS,
        'p25gateway': P25GATEWAY_PATTERNS,
        'nxdngateway': NXDNGATEWAY_PATTERNS,
    }
    return patterns.get(protocol.lower(), {})


def get_all_patterns() -> dict:
    """
    Get all patterns for all protocols.
    
    Returns:
        Dictionary of protocol_name -> patterns_dict
    """
    return {
        'mmdvmhost': MMDVMHOST_PATTERNS,
        'dmrgateway': DMRGATEWAY_PATTERNS,
        'ysfgateway': YSFGATEWAY_PATTERNS,
        'p25gateway': P25GATEWAY_PATTERNS,
        'nxdngateway': NXDNGATEWAY_PATTERNS,
    }
