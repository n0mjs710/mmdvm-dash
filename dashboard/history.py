"""
Historical Log Scanner
Efficiently scans previous days' logs to establish initial state
Optimized for minimal memory usage on resource-constrained systems
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import logging

from .parsers import MMDVMHostParser, DMRGatewayParser, YSFGatewayParser
from .state import DashboardState

logger = logging.getLogger(__name__)


class HistoricalScanner:
    """
    Scans historical log files to establish initial state
    Memory-efficient: streams files line-by-line, discards old data
    """
    
    def __init__(self, state: DashboardState, days_back: int = 7):
        self.state = state
        self.days_back = days_back
        self.parsers = {
            'mmdvm': MMDVMHostParser(),
            'dmr_gateway': DMRGatewayParser(),
            'ysf_gateway': YSFGatewayParser()
        }
        
        # Track what we're looking for to minimize processing
        self.seeking = {
            'last_mode': True,
            'network_connections': True,
            'gateway_reflectors': True,
            'recent_activity': True
        }
    
    def scan_log_directory(self, log_path: Path, file_pattern: str = "MMDVM-*.log"):
        """
        Scan log directory for historical files
        Args:
            log_path: Directory containing log files
            file_pattern: Glob pattern for log files (e.g., "MMDVM-*.log")
        """
        if not log_path.exists():
            logger.warning(f"Log directory not found: {log_path}")
            return
        
        # Find log files within our time window
        log_files = self._get_historical_logs(log_path, file_pattern)
        
        if not log_files:
            logger.info(f"No historical logs found in {log_path}")
            return
        
        logger.info(f"Scanning {len(log_files)} historical log files")
        
        # Process files in chronological order (oldest first)
        for log_file in sorted(log_files):
            if not any(self.seeking.values()):
                logger.info("All historical data found, stopping scan")
                break
            
            self._scan_file(log_file)
    
    def _get_historical_logs(self, log_path: Path, pattern: str) -> List[Path]:
        """Get log files from the last N days"""
        cutoff_date = datetime.now() - timedelta(days=self.days_back)
        log_files = []
        
        for log_file in log_path.glob(pattern):
            # Extract date from filename (e.g., MMDVM-2025-01-15.log)
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', log_file.name)
            if date_match:
                try:
                    file_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                    if file_date >= cutoff_date:
                        log_files.append(log_file)
                except ValueError:
                    continue
        
        return log_files
    
    def _scan_file(self, log_file: Path):
        """
        Stream through a log file looking for key state information
        Memory efficient: processes line-by-line without loading entire file
        """
        parser = self._get_parser_for_file(log_file)
        if not parser:
            return
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse the line
                    entry = parser.parse_line(line)
                    if not entry:
                        continue
                    
                    # Update state based on what we find
                    self._process_historical_entry(entry, log_file.name)
                    
        except Exception as e:
            logger.error(f"Error scanning {log_file}: {e}")
    
    def _get_parser_for_file(self, log_file: Path):
        """Determine which parser to use based on filename"""
        name = log_file.name.lower()
        
        if 'dmrgateway' in name:
            return self.parsers['dmr_gateway']
        elif 'ysfgateway' in name:
            return self.parsers['ysf_gateway']
        elif 'mmdvm' in name:
            return self.parsers['mmdvm']
        
        return None
    
    def _process_historical_entry(self, entry, filename: str):
        """Process a log entry for historical state"""
        entry_type = entry.entry_type
        
        # Mode changes
        if entry_type == 'mode_set' and self.seeking['last_mode']:
            self.state.update_mode(entry.data.get('mode'))
            logger.debug(f"Found historical mode: {entry.data.get('mode')}")
        
        # Network connections
        elif entry_type in ['network_connected', 'network_login'] and self.seeking['network_connections']:
            mode = entry.data.get('mode')
            if mode:
                self.state.system_status.network_status[mode] = 'connected'
                logger.debug(f"Found network connection: {mode}")
        
        # Gateway reflector connections
        elif entry_type in ['gateway_linked', 'reflector_connected'] and self.seeking['gateway_reflectors']:
            reflector = entry.data.get('reflector') or entry.data.get('target')
            mode = entry.data.get('mode')
            if reflector and mode:
                self.state.system_status.gateway_reflectors[mode] = reflector
                logger.info(f"Found gateway connection: {mode} -> {reflector}")
        
        # Recent transmissions (only keep very recent ones to save memory)
        elif entry_type in ['dmr_rx', 'dstar_rx', 'ysf_rx', 'p25_rx', 'nxdn_rx'] and self.seeking['recent_activity']:
            # Only store if from today or yesterday
            if self._is_recent_timestamp(entry.timestamp):
                self.state.add_transmission(entry.data)
    
    def _is_recent_timestamp(self, timestamp: Optional[datetime]) -> bool:
        """Check if timestamp is within the last 24 hours"""
        if not timestamp:
            return False
        
        cutoff = datetime.now() - timedelta(hours=24)
        return timestamp >= cutoff
    
    def scan_all_configured_logs(self, config_manager):
        """
        Scan all log paths from configuration
        Args:
            config_manager: ConfigManager instance with loaded configs
        """
        log_paths = config_manager.get_all_log_paths()
        
        for log_pattern in log_paths:
            log_dir = log_pattern.parent
            pattern = log_pattern.name
            self.scan_log_directory(log_dir, pattern)


class NetworkStateReconstructor:
    """
    Reconstructs network connection state from historical logs
    Specifically handles gateway reflector connections that may have happened days ago
    """
    
    def __init__(self):
        self.gateway_connections: Dict[str, str] = {}  # mode -> reflector/target
        self.network_status: Dict[str, str] = {}  # mode -> status
        self.last_seen: Dict[str, datetime] = {}  # track when we last saw activity
    
    def process_historical_logs(self, log_path: Path, days_back: int = 30):
        """
        Look back through logs to find when gateways connected
        Goes back further than regular scanning since connections can be long-lived
        """
        cutoff = datetime.now() - timedelta(days=days_back)
        
        # Patterns for gateway connections
        patterns = {
            'ysf_link': re.compile(r'Link to (.+?) has been established'),
            'dmr_link': re.compile(r'Linked to (.+?)$'),
            'p25_link': re.compile(r'Linked to (.+?)$'),
        }
        
        for log_file in sorted(log_path.glob("*Gateway-*.log")):
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', log_file.name)
            if not date_match:
                continue
            
            try:
                file_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                if file_date < cutoff:
                    continue
                
                # Determine gateway type from filename
                gateway_type = None
                if 'YSFGateway' in log_file.name:
                    gateway_type = 'YSF'
                elif 'DMRGateway' in log_file.name:
                    gateway_type = 'DMR'
                elif 'P25Gateway' in log_file.name:
                    gateway_type = 'P25'
                
                if not gateway_type:
                    continue
                
                # Scan for most recent connection in this file
                last_connection = None
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        for pattern_name, pattern in patterns.items():
                            match = pattern.search(line)
                            if match:
                                last_connection = match.group(1)
                
                # Store the most recent connection we found
                if last_connection:
                    self.gateway_connections[gateway_type] = last_connection
                    self.last_seen[gateway_type] = file_date
                    logger.info(f"Reconstructed {gateway_type} gateway connection: {last_connection} (from {file_date.date()})")
            
            except Exception as e:
                logger.error(f"Error reconstructing state from {log_file}: {e}")
    
    def get_state(self) -> Dict:
        """Get the reconstructed state"""
        return {
            'gateway_connections': self.gateway_connections,
            'network_status': self.network_status,
            'last_seen': self.last_seen
        }
