"""
Log File Monitor
Watches log files for changes and parses new entries
"""
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Optional
import logging
from datetime import datetime

from .parsers import get_parser
from .state import state, Transmission
from .config import config

logger = logging.getLogger(__name__)


class LogMonitor:
    """Monitors a single log file for changes"""
    
    def __init__(self, name: str, path: str, parser_type: str):
        self.name = name
        self.path = Path(path)
        self.parser = get_parser(parser_type)
        self.last_position = 0
        self.running = False
        
        if self.parser is None:
            logger.warning(f"No parser available for {name} (type: {parser_type})")
        else:
            logger.debug(f"Initialized monitor {name} with parser type {parser_type}")
    
    async def start(self):
        """Start monitoring the log file"""
        if not self.path.exists():
            logger.warning(f"Log file not found: {self.path}")
            return
        
        self.running = True
        logger.info(f"Starting monitor for {self.name}: {self.path}")
        
        # Parse recent log entries to establish current state
        await self.parse_recent_entries(lookback_lines=1000)
        
        # Now seek to end of file to only read new entries going forward
        try:
            self.last_position = self.path.stat().st_size
        except Exception as e:
            logger.error(f"Error getting file size for {self.name}: {e}")
            self.last_position = 0
        
        while self.running:
            try:
                await self.check_for_updates()
                await asyncio.sleep(0.5)  # Check twice per second
            except Exception as e:
                logger.error(f"Error monitoring {self.name}: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def parse_recent_entries(self, lookback_lines: int = 1000):
        """Parse recent log entries to establish current state on startup"""
        try:
            # Try current log file first
            if await self._parse_log_file(self.path, lookback_lines):
                return  # Found what we need
            
            # If not enough info, check previous days' logs (up to 5 days back)
            base_name = self.path.stem  # e.g., "MMDVM" from "MMDVM.log"
            parent_dir = self.path.parent
            
            from datetime import timedelta
            today = datetime.now()
            
            for days_back in range(1, 6):  # Check 1-5 days back
                date = today - timedelta(days=days_back)
                date_str = date.strftime('%Y-%m-%d')
                
                # Common log rotation patterns
                for pattern in [f"{base_name}-{date_str}.log", f"{base_name}.log.{days_back}"]:
                    old_log = parent_dir / pattern
                    if old_log.exists():
                        logger.info(f"Checking previous log: {old_log}")
                        await self._parse_log_file(old_log, lookback_lines=None)  # Parse entire old log
                        break
        
        except Exception as e:
            logger.error(f"Error parsing recent entries for {self.name}: {e}")
    
    async def _parse_log_file(self, log_path: Path, lookback_lines: int = None) -> bool:
        """Parse a log file. Returns True if we got useful data."""
        try:
            async with aiofiles.open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = await f.readlines()
                
                if not all_lines:
                    return False
                
                # Take last N lines, or all lines if lookback_lines is None
                if lookback_lines:
                    lines = all_lines[-lookback_lines:] if len(all_lines) > lookback_lines else all_lines
                    logger.info(f"Parsing {len(lines)} recent log entries from {log_path.name}")
                else:
                    lines = all_lines
                    logger.info(f"Parsing entire log file {log_path.name} ({len(lines)} lines)")
                
                # Parse lines
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if self.parser:
                        entry = self.parser.parse_line(line)
                        if entry:
                            await self.process_entry(entry)
                
                return len(lines) > 0
        
        except Exception as e:
            logger.error(f"Error parsing log file {log_path}: {e}")
            return False
    
    async def check_for_updates(self):
        """Check for new log entries"""
        try:
            current_size = self.path.stat().st_size
            
            # Check if file was rotated (size decreased)
            if current_size < self.last_position:
                logger.info(f"Log file rotated for {self.name}")
                self.last_position = 0
            
            if current_size == self.last_position:
                return  # No new data
            
            # Read new data
            async with aiofiles.open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                await f.seek(self.last_position)
                new_lines = await f.readlines()
                self.last_position = await f.tell()
            
            # Parse new lines
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                
                if self.parser is None:
                    logger.debug(f"Skipping line from {self.name} - no parser available")
                    continue
                
                try:
                    entry = self.parser.parse_line(line)
                    if entry:
                        await self.process_entry(entry)
                except Exception as e:
                    logger.debug(f"Error parsing line from {self.name}: {e} | Line: {line[:100]}")
        
        except Exception as e:
            logger.error(f"Error reading {self.name}: {e}")
    
    async def process_entry(self, entry):
        """Process a parsed log entry"""
        if not entry.data:
            return  # Skip entries with no extracted data
        
        event_type = entry.data.get('event')
        
        if event_type == 'mode_change':
            mode = entry.data.get('mode', 'IDLE')
            state.update_mode(mode)
            # If mode changes to IDLE, clear all active transmissions
            if mode == 'IDLE':
                state.clear_all_transmissions()
        
        elif event_type == 'network_connected':
            state.update_network_status(entry.data['network'], True)
        
        elif event_type == 'network_disconnected':
            state.update_network_status(entry.data['network'], False)
        
        # YSF Gateway events
        elif event_type == 'ysf_linked':
            # YSF linked to a reflector
            reflector = entry.data.get('reflector', 'Unknown')
            state.update_network_status('YSF', True, reflector)
            logger.info(f"YSF linked to reflector: {reflector}")
        
        elif event_type == 'ysf_reconnected':
            # YSF reconnected to reflector
            reflector = entry.data.get('reflector', 'Unknown')
            state.update_network_status('YSF', True, reflector)
            logger.info(f"YSF reconnected to reflector: {reflector}")
        
        elif event_type == 'ysf_mmdvm_connected':
            # YSFGateway successfully connected to MMDVMHost
            logger.info("YSF Gateway connected to MMDVM")
        
        elif event_type == 'ysf_disconnect_requested':
            # YSF disconnecting from reflector
            state.update_network_status('YSF', False)
            logger.info("YSF disconnect requested")
        
        # DMR Gateway events
        elif event_type == 'dmr_mmdvm_connected':
            # DMRGateway connected to MMDVMHost (no disconnect is logged)
            logger.info("DMR Gateway connected to MMDVM")
        
        elif event_type == 'dmr_network_connected':
            # DMR network (e.g., HBlink4) logged in
            network = entry.data.get('network', 'Unknown')
            state.update_network_status(f'DMR-{network}', True)
            logger.info(f"DMR network connected: {network}")
        
        elif event_type == 'dmr_network_disconnected':
            # DMR network closing
            network = entry.data.get('network', 'Unknown')
            state.update_network_status(f'DMR-{network}', False)
            logger.info(f"DMR network disconnected: {network}")
        
        elif event_type in ['dmr_rx', 'dstar_rx', 'ysf_rx', 'p25_rx', 'nxdn_rx', 'fm_rx']:
            # Create transmission record
            transmission = Transmission(
                timestamp=entry.timestamp.timestamp(),
                mode=entry.data.get('mode', 'Unknown'),
                source=entry.data.get('source', 'Unknown'),
                destination=entry.data.get('destination', 'Unknown'),
                slot=entry.data.get('slot', 0),
                network=entry.data.get('network', ''),
                active=True
            )
            state.add_transmission(transmission)
        
        elif event_type in ['dmr_end', 'dstar_end', 'ysf_end', 'p25_end', 'nxdn_end']:
            # End transmission for this mode
            # Note: FM doesn't have specific end messages, cleared on mode change to IDLE
            mode = entry.data.get('mode')
            if mode:
                state.end_transmission_by_mode(mode)
        
        elif event_type == 'modem_info':
            state.status.modem_connected = True
            state.status.modem_description = entry.data.get('description', '')
        
        # Broadcast to connected websockets
        await self.broadcast_update()
    
    async def broadcast_update(self):
        """Broadcast state update to all connected WebSocket clients"""
        if not state.websocket_clients:
            return
        
        update = {
            'type': 'state_update',
            'status': state.get_status(),
            'active_transmissions': state.get_active_transmissions(),
            'recent_calls': state.get_recent_calls(10),
            'events': state.get_events(20)
        }
        
        # Send to all clients
        disconnected_clients = set()
        for client in state.websocket_clients:
            try:
                await client.send_json(update)
            except Exception as e:
                logger.debug(f"Failed to send to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        state.websocket_clients -= disconnected_clients
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        logger.info(f"Stopped monitor for {self.name}")


class LogMonitorManager:
    """Manages multiple log monitors"""
    
    def __init__(self):
        self.monitors: Dict[str, LogMonitor] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
    
    def add_monitor(self, name: str, path: str, parser_type: str):
        """Add a log monitor"""
        monitor = LogMonitor(name, path, parser_type)
        self.monitors[name] = monitor
        logger.info(f"Added monitor: {name} -> {path}")
    
    async def start_all(self):
        """Start all monitors"""
        for name, monitor in self.monitors.items():
            task = asyncio.create_task(monitor.start())
            self.tasks[name] = task
        logger.info(f"Started {len(self.monitors)} log monitors")
    
    def stop_all(self):
        """Stop all monitors"""
        for monitor in self.monitors.values():
            monitor.stop()
        for task in self.tasks.values():
            task.cancel()
        logger.info("Stopped all log monitors")


# Global monitor manager
monitor_manager = LogMonitorManager()


async def initialize_monitors():
    """
    Initialize log monitors from configuration
    
    NOTE: This needs to be updated to use config_reader.ConfigManager
    to read log paths from INI files instead of config.json
    """
    log_files_config = config.get('log_files', default={})
    
    for name, settings in log_files_config.items():
        if settings.get('enabled', False):
            path = settings.get('path')
            if path:
                monitor_manager.add_monitor(name, path, name)
    
    await monitor_manager.start_all()
