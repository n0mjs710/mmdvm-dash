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
    
    # Transmission patterns
    DMR_RX_PATTERN = r'DMR Slot (\d), received (?:voice|data) (?:header|transmission) from (\d+) to (?:TG\s*)?(\d+)'
    DMR_TX_PATTERN = r'DMR Slot (\d), transmission from (\d+) to (?:TG\s*)?(\d+)'
    DMR_LATE_ENTRY_PATTERN = r'DMR Slot (\d), late entry from (\d+) to (?:TG\s*)?(\d+)'
    
    DSTAR_RX_PATTERN = r'D-Star, received (?:header|data) from ([A-Z0-9]+)\s+/([A-Z0-9]+)\s+to\s+([A-Z0-9]+)'
    
    YSF_RX_PATTERN = r'YSF, received (?:header|data) from ([A-Z0-9]+) to ([A-Z0-9]+)'
    
    P25_RX_PATTERN = r'P25, received (?:voice|data) (?:header|transmission) from (\d+) to (?:TG\s*)?(\d+)'
    
    NXDN_RX_PATTERN = r'NXDN, received (?:voice|data) (?:header|transmission) from (\d+) to (?:TG\s*)?(\d+)'
    
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
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'DMR'
            }
        
        elif match := re.search(self.DMR_TX_PATTERN, message):
            entry.data = {
                'event': 'dmr_tx',
                'slot': int(match.group(1)),
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'DMR'
            }
        
        elif match := re.search(self.DMR_LATE_ENTRY_PATTERN, message):
            entry.data = {
                'event': 'dmr_late_entry',
                'slot': int(match.group(1)),
                'source': match.group(2),
                'destination': match.group(3),
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
        
        # YSF transmissions
        elif match := re.search(self.YSF_RX_PATTERN, message):
            entry.data = {
                'event': 'ysf_rx',
                'source': match.group(1),
                'destination': match.group(2),
                'mode': 'YSF'
            }
        
        # P25 transmissions
        elif match := re.search(self.P25_RX_PATTERN, message):
            entry.data = {
                'event': 'p25_rx',
                'source': match.group(1),
                'destination': match.group(2),
                'mode': 'P25'
            }
        
        # NXDN transmissions
        elif match := re.search(self.NXDN_RX_PATTERN, message):
            entry.data = {
                'event': 'nxdn_rx',
                'source': match.group(1),
                'destination': match.group(2),
                'mode': 'NXDN'
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
    
    # Network patterns
    NETWORK_PATTERN = r'DMR, (BrandMeister|TGIF|DMR\+|FreeDMR) Network'
    LOGIN_PATTERN = r'Logged into the (.+) network'
    TALKGROUP_PATTERN = r'Received voice (?:header|data) from (\d+) to TG (\d+)'
    
    def __init__(self):
        self.networks: Dict[str, bool] = {}
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single DMRGateway log line"""
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
        
        entry = LogEntry(timestamp, level, message, 'dmrgateway')
        
        # Parse network activity
        if match := re.search(self.LOGIN_PATTERN, message):
            network = match.group(1)
            self.networks[network] = True
            entry.data = {
                'event': 'network_login',
                'network': network
            }
        
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
    REFLECTOR_PATTERN = r'Connect to (.+) has been requested'
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
        
        if match := re.search(self.REFLECTOR_PATTERN, message):
            entry.data = {
                'event': 'reflector_connect',
                'reflector': match.group(1)
            }
        
        elif re.search(self.DISCONNECT_PATTERN, message):
            entry.data = {
                'event': 'reflector_disconnect'
            }
        
        return entry


# Parser factory
def get_parser(source: str):
    """Get appropriate parser for log source"""
    parsers = {
        'mmdvmhost': MMDVMHostParser,
        'dmrgateway': DMRGatewayParser,
        'ysfgateway': YSFGatewayParser,
        'p25gateway': YSFGatewayParser,  # Reuse YSF parser for now (similar format)
        'nxdngateway': YSFGatewayParser,  # Reuse YSF parser for now (similar format)
    }
    parser_class = parsers.get(source.lower())
    if parser_class:
        return parser_class()
    logger.warning(f"No parser available for source: {source}")
    return None
