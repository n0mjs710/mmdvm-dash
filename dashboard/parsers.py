"""
Log Parsers for MMDVM and Gateway Programs
Extracts structured data from log files

Patterns are centralized in log_patterns.py for easier maintenance
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
from dashboard.log_patterns import get_patterns

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
    
    # Log line patterns - timestamp extraction (common to all logs)
    TIMESTAMP_PATTERN = r'([MDISEWF]):\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
    
    def __init__(self):
        self.current_mode = "IDLE"
        self.network_status: Dict[str, bool] = {}
        # Load message patterns from centralized config
        self.patterns = get_patterns('mmdvmhost')
        # Mode name normalization (match config_reader and frontend)
        self.mode_name_map = {
            'System Fusion': 'YSF',
            'D-Star': 'D-Star',
            'Idle': 'IDLE'
        }
    
    def _normalize_mode(self, mode: str) -> str:
        """Normalize mode names to match frontend expectations"""
        return self.mode_name_map.get(mode, mode)
    
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
        if match := self.patterns['mode_change'].search(message):
            raw_mode = match.group(1)
            normalized_mode = self._normalize_mode(raw_mode)
            self.current_mode = normalized_mode
            entry.data = {
                'event': 'mode_change',
                'mode': normalized_mode
            }
        
        # DMR transmissions
        elif match := self.patterns['dmr_rx'].search(message):
            entry.data = {
                'event': 'dmr_rx',
                'slot': int(match.group(1)),
                'source_type': match.group(2),  # 'network' or 'RF'
                'source': match.group(3),
                'destination': match.group(4),
                'mode': 'DMR'
            }
        
        elif match := self.patterns['dmr_end'].search(message):
            entry.data = {
                'event': 'dmr_end',
                'slot': int(match.group(1)),
                'source_type': match.group(2),  # 'network' or 'RF'
                'source': match.group(3),
                'destination': match.group(4),
                'mode': 'DMR'
            }
        
        # D-Star transmissions
        elif match := self.patterns['dstar_rx'].search(message):
            entry.data = {
                'event': 'dstar_rx',
                'source_callsign': match.group(1),
                'source_suffix': match.group(2),
                'destination': match.group(3),
                'mode': 'D-Star'
            }
        
        elif match := self.patterns['dstar_end'].search(message):
            entry.data = {
                'event': 'dstar_end',
                'mode': 'D-Star'
            }
        
        # YSF transmissions
        elif match := self.patterns['ysf_rx'].search(message):
            entry.data = {
                'event': 'ysf_rx',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2).strip(),
                'destination': match.group(3),
                'mode': 'YSF'
            }
        
        elif match := self.patterns['ysf_end'].search(message):
            entry.data = {
                'event': 'ysf_end',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2).strip(),
                'destination': match.group(3),
                'mode': 'YSF'
            }
        
        # P25 transmissions
        elif match := self.patterns['p25_rx'].search(message):
            entry.data = {
                'event': 'p25_rx',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'P25'
            }
        
        elif match := self.patterns['p25_end'].search(message):
            entry.data = {
                'event': 'p25_end',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'P25'
            }
        
        # NXDN transmissions
        elif match := self.patterns['nxdn_rx'].search(message):
            entry.data = {
                'event': 'nxdn_rx',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'NXDN'
            }
        
        elif match := self.patterns['nxdn_end'].search(message):
            entry.data = {
                'event': 'nxdn_end',
                'source_type': match.group(1),  # 'network' or 'RF'
                'source': match.group(2),
                'destination': match.group(3),
                'mode': 'NXDN'
            }
        
        # Note: FM does not log reception events - activity tracked via mode changes only
        
        # Modem status
        elif match := self.patterns['modem_connected'].search(message):
            entry.data = {
                'event': 'modem_info',
                'protocol_version': match.group(1),
                'description': match.group(2)
            }


class DMRGatewayParser:
    """Parser for DMRGateway log files"""
    
    TIMESTAMP_PATTERN = r'([MDISEWF]):\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
    
    def __init__(self):
        self.networks: Dict[str, bool] = {}
        # Load patterns from centralized config
        self.patterns = get_patterns('dmrgateway')
    
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
        if self.patterns['mmdvm_connected'].search(message):
            entry.data = {
                'event': 'dmr_mmdvm_connected'
            }
        
        # Check for network login (e.g., "HBlink4, Logged into the master successfully")
        elif match := self.patterns['network_connected'].search(message):
            network = match.group(1).strip()
            self.networks[network] = True
            entry.data = {
                'event': 'dmr_network_connected',
                'network': network
            }
        
        # Check for network disconnection/timeout
        elif match := self.patterns['network_disconnected'].search(message):
            network = match.group(1).strip()
            self.networks[network] = False
            entry.data = {
                'event': 'dmr_network_disconnected',
                'network': network
            }
        
        return entry


class YSFGatewayParser:
    """Parser for YSFGateway log files"""
    
    TIMESTAMP_PATTERN = r'([MDISEWF]):\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
    
    def __init__(self):
        # Load patterns from centralized config
        self.patterns = get_patterns('ysfgateway')
    
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
        
        # Check for linked to reflector (network connected)
        if match := self.patterns['reflector_linked'].search(message):
            reflector = match.group(1).strip()
            entry.data = {
                'event': 'ysf_reflector_linked',
                'reflector': reflector
            }
        
        # Check for network disconnection
        elif self.patterns['network_disconnected'].search(message):
            entry.data = {
                'event': 'ysf_network_disconnected'
            }
        
        return entry


class P25GatewayParser:
    """Parser for P25Gateway log files"""
    
    TIMESTAMP_PATTERN = r'([MDISEWF]):\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
    
    def __init__(self):
        # Load patterns from centralized config
        self.patterns = get_patterns('p25gateway')
    
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
        
        # Check for reflector link (statically linked)
        if match := self.patterns['reflector_linked'].search(message):
            reflector = match.group(1)
            entry.data = {
                'event': 'p25_reflector_linked',
                'reflector': reflector
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
