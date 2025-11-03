"""
Log Parsers for MMDVM and Gateway Programs
Extracts structured data from log files
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class LogEntry:
    """Represents a parsed log entry"""
    
    def __init__(self, timestamp: datetime, level: str, message: str, source: str):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.source = source
        self.data: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "data": self.data
        }


class MMDVMHostParser:
    """Parser for MMDVMHost log files"""
    
    # Log line patterns
    TIMESTAMP_PATTERN = r'([MDISEWF]):\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
    
    # Mode patterns
    MODE_SET_PATTERN = r'Mode set to (.+)'
    
    # Transmission patterns - based on actual MMDVMHost log format
    # DMR: Matches "DMR Slot X, received network/RF voice header from CALLSIGN to TG XXXX"
    DMR_RX_PATTERN = r'DMR Slot (\d), received (network|RF) voice header from ([A-Z0-9]+) to TG\s*(\d+)'
    DMR_END_PATTERN = r'DMR Slot (\d), received (network|RF) end of voice transmission from ([A-Z0-9]+) to TG\s*(\d+)'
    
    # D-Star: Keep existing patterns (not in provided logs but should work)
    DSTAR_RX_PATTERN = r'D-Star, received (?:header|data) from ([A-Z0-9]+)\s+/([A-Z0-9]+)\s+to\s+([A-Z0-9]+)'
    DSTAR_END_PATTERN = r'D-Star, end of transmission'
    
    # YSF: Matches "YSF, received RF header from CALLSIGN to DG-ID X"
    # Also matches "YSF, received RF end of transmission from CALLSIGN to DG-ID X"
    YSF_RX_PATTERN = r'YSF, received (network|RF) header from ([A-Z0-9\s]+)\s+to DG-ID\s+(\d+)'
    YSF_END_PATTERN = r'YSF, received (network|RF) end of transmission from ([A-Z0-9\s]+)\s+to DG-ID\s+(\d+)'
    
    # P25: Has separate header and voice transmission messages
    # Matches "P25, received RF voice transmission from CALLSIGN to TG XXXX"
    P25_RX_PATTERN = r'P25, received (network|RF) (?:voice transmission|header) from ([A-Z0-9]+) to TG\s*(\d+)'
    P25_HEADER_PATTERN = r'P25, received (network|RF) header'
    P25_END_PATTERN = r'P25, received (network|RF) end of voice transmission from ([A-Z0-9]+) to TG\s*(\d+)'
    
    # NXDN: Keep existing patterns (not in provided logs but should work)
    NXDN_RX_PATTERN = r'NXDN, received (network|RF) (?:voice|data) (?:header|transmission) from ([A-Z0-9]+) to (?:TG\s*)?(\d+)'
    NXDN_END_PATTERN = r'NXDN, received (network|RF) end of transmission from ([A-Z0-9]+) to (?:TG\s*)?(\d+)'
    
    # Note: POCSAG is transmit-only (paging), no receive events to track
    
    # Note: FM does not have specific start/end messages like other modes
    # FM activity detection relies on mode changes and will be cleared when mode changes to IDLE
    FM_RX_PATTERN = r'FM, received (?:header|transmission)'
    
    # Network patterns
    NETWORK_CONNECTED_PATTERN = r'(.+) Network, connected'
    NETWORK_DISCONNECTED_PATTERN = r'(.+) Network, (?:disconnected|connection lost)'
    
    # Modem patterns
    MODEM_STATUS_PATTERN = r'MMDVM protocol version: (\d+), description: (.+)'
    MODEM_ERROR_PATTERN = r'Error: (.+)'
    
    def __init__(self):
        self.current_mode = "IDLE"
        self.network_status: Dict[str, bool] = {}
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line"""
        match = re.match(self.TIMESTAMP_PATTERN, line)
        if not match:
            return None
        
        level_char, timestamp_str, message = match.groups()
        
        # Convert level character to name
        level_map = {
            'M': 'INFO',
            'D': 'DEBUG',
            'I': 'INFO',
            'S': 'INFO',
            'E': 'ERROR',
            'W': 'WARNING',
            'F': 'FATAL'
        }
        level = level_map.get(level_char, 'INFO')
        
        # Parse timestamp
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            timestamp = datetime.now()
        
        entry = LogEntry(timestamp, level, message, 'mmdvmhost')
        
        # Parse specific message types
        self._parse_message(entry, message)
        
        return entry
    
    def _parse_message(self, entry: LogEntry, message: str):
        """Extract structured data from message"""
        
        # Mode changes
        if match := re.search(self.MODE_SET_PATTERN, message):
            self.current_mode = match.group(1)
            entry.data = {
                'event': 'mode_change',
                'mode': self.current_mode
            }
        
        # DMR transmissions
        elif match := re.search(self.DMR_RX_PATTERN, message):
            entry.data = {
                'event': 'dmr_rx',
                'slot': int(match.group(1)),
                'source_type': match.group(2),  # 'network' or 'RF'
                'source': match.group(3),
                'destination': match.group(4),
                'mode': 'DMR'
            }
        
        elif match := re.search(self.DMR_END_PATTERN, message):
            entry.data = {
                'event': 'dmr_end',
                'slot': int(match.group(1)),
                'source_type': match.group(2),  # 'network' or 'RF'
                'source': match.group(3),
                'destination': match.group(4),
                'mode': 'DMR'
            }
        
        # D-Star transmissions
        elif match := re.search(self.DSTAR_RX_PATTERN, message):
            entry.data = {
                'event': 'dstar_rx',
                'source_callsign': match.group(1),
                'source_suffix': match.group(2),
                'destination': match.group(3),
                'mode': 'D-Star'
            }
        
        elif match := re.search(self.DSTAR_END_PATTERN, message):
            entry.data = {
                'event': 'dstar_end',
                'mode': 'D-Star'
            }
        
        # YSF transmissions
        elif match := re.search(self.YSF_RX_PATTERN, message):
            entry.data = {
                'event': 'ysf_rx',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2).strip(),
                'destination': match.group(3),
                'mode': 'YSF'
            }
        
        elif match := re.search(self.YSF_END_PATTERN, message):
            entry.data = {
                'event': 'ysf_end',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2).strip(),
                'destination': match.group(3),
                'mode': 'YSF'
            }
        
        # P25 transmissions
        # Note: P25 has separate "header" and "voice transmission" messages
        elif match := re.search(self.P25_RX_PATTERN, message):
            entry.data = {
                'event': 'p25_rx',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'P25'
            }
        
        elif match := re.search(self.P25_HEADER_PATTERN, message):
            # P25 header without callsign info - just note that P25 activity started
            entry.data = {
                'event': 'p25_rx',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': 'Unknown',
                'destination': 'Unknown',
                'mode': 'P25'
            }
        
        elif match := re.search(self.P25_END_PATTERN, message):
            entry.data = {
                'event': 'p25_end',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'P25'
            }
        
        # NXDN transmissions
        elif match := re.search(self.NXDN_RX_PATTERN, message):
            entry.data = {
                'event': 'nxdn_rx',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'NXDN'
            }
        
        elif match := re.search(self.NXDN_END_PATTERN, message):
            entry.data = {
                'event': 'nxdn_end',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'NXDN'
            }
        
        # FM transmissions
        # Note: FM doesn't have specific end-of-transmission messages
        # Active FM transmissions are cleared when mode changes to IDLE
        elif match := re.search(self.FM_RX_PATTERN, message):
            entry.data = {
                'event': 'fm_rx',
                'mode': 'FM'
            }
        
        # Network status
        elif match := re.search(self.NETWORK_CONNECTED_PATTERN, message):
            network = match.group(1)
            self.network_status[network] = True
            entry.data = {
                'event': 'network_connected',
                'network': network
            }
        
        elif match := re.search(self.NETWORK_DISCONNECTED_PATTERN, message):
            network = match.group(1)
            self.network_status[network] = False
            entry.data = {
                'event': 'network_disconnected',
                'network': network
            }
        
        # Modem status
        elif match := re.search(self.MODEM_STATUS_PATTERN, message):
            entry.data = {
                'event': 'modem_info',
                'protocol_version': match.group(1),
                'description': match.group(2)
            }
        
        # Errors
        elif match := re.search(self.MODEM_ERROR_PATTERN, message):
            entry.data = {
                'event': 'error',
                'error_message': match.group(1)
            }


class DMRGatewayParser:
    """Parser for DMRGateway log files"""
    
    TIMESTAMP_PATTERN = r'([MDISEWF]):\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
    
    # Key DMR Gateway events
    MMDVM_CONNECTED_PATTERN = r'MMDVM has connected'  # Gateway linked to MMDVM (no disconnect logged)
    
    # Network connection events
    NETWORK_LOGIN_PATTERN = r'(.+), Logged into the master successfully'  # Connection established
    NETWORK_CLOSING_PATTERN = r'(.+), Closing DMR Network'  # Network disconnected
    
    # Legacy patterns (may not be in current logs)
    TALKGROUP_PATTERN = r'Received voice (?:header|data) from (\d+) to TG (\d+)'
    
    def __init__(self):
        self.networks: Dict[str, bool] = {}
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single DMRGateway log line"""
        match = re.match(self.TIMESTAMP_PATTERN, line)
        if not match:
            return None
        
        level_char, timestamp_str, message = match.groups()
        
        level_map = {'M': 'INFO', 'D': 'DEBUG', 'I': 'INFO', 'E': 'ERROR', 'W': 'WARNING', 'F': 'FATAL'}
        level = level_map.get(level_char, 'INFO')
        
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            timestamp = datetime.now()
        
        entry = LogEntry(timestamp, level, message, 'dmrgateway')
        
        # Check for MMDVM connection (no disconnect is logged by gateway)
        if re.search(self.MMDVM_CONNECTED_PATTERN, message):
            entry.data = {
                'event': 'dmr_mmdvm_connected'
            }
        
        # Check for network login (e.g., "HBlink4, Logged into the master successfully")
        elif match := re.search(self.NETWORK_LOGIN_PATTERN, message):
            network = match.group(1).strip()
            self.networks[network] = True
            entry.data = {
                'event': 'dmr_network_connected',
                'network': network
            }
        
        # Check for network closing (e.g., "HBlink4, Closing DMR Network")
        elif match := re.search(self.NETWORK_CLOSING_PATTERN, message):
            network = match.group(1).strip()
            self.networks[network] = False
            entry.data = {
                'event': 'dmr_network_disconnected',
                'network': network
            }
        
        # Talkgroup activity (legacy)
        elif match := re.search(self.TALKGROUP_PATTERN, message):
            entry.data = {
                'event': 'talkgroup_activity',
                'source': match.group(1),
                'talkgroup': match.group(2)
            }
        
        return entry


class YSFGatewayParser:
    """Parser for YSFGateway log files"""
    
    TIMESTAMP_PATTERN = r'([MDISEWF]):\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
    
    # Key YSF events to track
    LINKED_PATTERN = r'Linked to (.+?)(?:\s+)?$'  # "Linked to Kansas          "
    LINK_MMDVM_PATTERN = r'Link successful to MMDVM'
    RECONNECT_PATTERN = r'Automatic \(re-\)connection to (\d+) - "(.+?)"'  # Reconnecting to reflector
    REFLECTOR_PATTERN = r'Connect to (.+) has been requested'  # Manual connection request
    DISCONNECT_PATTERN = r'Disconnect has been requested'
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single YSFGateway log line"""
        match = re.match(self.TIMESTAMP_PATTERN, line)
        if not match:
            return None
        
        level_char, timestamp_str, message = match.groups()
        level_map = {'M': 'INFO', 'D': 'DEBUG', 'I': 'INFO', 'E': 'ERROR', 'W': 'WARNING'}
        level = level_map.get(level_char, 'INFO')
        
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            timestamp = datetime.now()
        
        entry = LogEntry(timestamp, level, message, 'ysfgateway')
        
        # Check for linked to reflector
        if match := re.search(self.LINKED_PATTERN, message):
            reflector = match.group(1).strip()
            entry.data = {
                'event': 'ysf_linked',
                'reflector': reflector
            }
        
        # Check for link to MMDVM successful
        elif re.search(self.LINK_MMDVM_PATTERN, message):
            entry.data = {
                'event': 'ysf_mmdvm_connected'
            }
        
        # Check for automatic reconnection
        elif match := re.search(self.RECONNECT_PATTERN, message):
            reflector_id = match.group(1)
            reflector_name = match.group(2).strip()
            entry.data = {
                'event': 'ysf_reconnected',
                'reflector_id': reflector_id,
                'reflector': reflector_name
            }
        
        # Manual connection request
        elif match := re.search(self.REFLECTOR_PATTERN, message):
            entry.data = {
                'event': 'ysf_connect_requested',
                'reflector': match.group(1).strip()
            }
        
        # Disconnect request
        elif re.search(self.DISCONNECT_PATTERN, message):
            entry.data = {
                'event': 'ysf_disconnect_requested'
            }
        
        return entry


# Parser factory
class P25GatewayParser:
    """Parser for P25Gateway log files"""
    
    TIMESTAMP_PATTERN = r'([MDISEWF]):\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
    
    # Key P25 events to track
    OPENING_RPT_PATTERN = r'Opening Rpt network connection'  # MMDVM connection opening
    CLOSING_RPT_PATTERN = r'Closing Rpt network connection'  # MMDVM connection closing
    LINKED_REFLECTOR_PATTERN = r'linked to reflector (\d+)'  # Connected to reflector (static or dynamic)
    OPENING_P25_PATTERN = r'Opening P25 network connection'  # P25 network opening
    CLOSING_P25_PATTERN = r'Closing P25 network connection'  # P25 network closing
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single P25Gateway log line"""
        match = re.match(self.TIMESTAMP_PATTERN, line)
        if not match:
            return None
        
        level_char, timestamp_str, message = match.groups()
        level_map = {'M': 'INFO', 'D': 'DEBUG', 'I': 'INFO', 'E': 'ERROR', 'W': 'WARNING'}
        level = level_map.get(level_char, 'INFO')
        
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            timestamp = datetime.now()
        
        entry = LogEntry(timestamp, level, message, 'p25gateway')
        
        # Check for MMDVM (Rpt network) connection opening
        if re.search(self.OPENING_RPT_PATTERN, message):
            entry.data = {
                'event': 'p25_mmdvm_connected'
            }
        
        # Check for MMDVM (Rpt network) connection closing
        elif re.search(self.CLOSING_RPT_PATTERN, message):
            entry.data = {
                'event': 'p25_mmdvm_disconnected'
            }
        
        # Check for P25 network (reflector) connection
        elif match := re.search(self.LINKED_REFLECTOR_PATTERN, message):
            reflector = match.group(1)
            entry.data = {
                'event': 'p25_reflector_linked',
                'reflector': reflector
            }
        
        # Check for P25 network opening
        elif re.search(self.OPENING_P25_PATTERN, message):
            entry.data = {
                'event': 'p25_network_opening'
            }
        
        # Check for P25 network closing
        elif re.search(self.CLOSING_P25_PATTERN, message):
            entry.data = {
                'event': 'p25_network_closing'
            }
        
        return entry


def get_parser(source: str):
    """Get appropriate parser for a log source"""
    parsers = {
        'mmdvm': MMDVMHostParser,
        'mmdvmhost': MMDVMHostParser,
        'dmrgateway': DMRGatewayParser,
        'ysfgateway': YSFGatewayParser,
        'p25gateway': P25GatewayParser,
        'nxdngateway': YSFGatewayParser,  # Reuse YSF parser for now (similar format)
    }
    parser_class = parsers.get(source.lower())
    if parser_class:
        return parser_class()
    logger.warning(f"No parser available for source: {source}")
    return None
