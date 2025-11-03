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
    
    async def start(self):
        """Start monitoring the log file"""
        if not self.path.exists():
            logger.warning(f"Log file not found: {self.path}")
            return
        
        self.running = True
        logger.info(f"Starting monitor for {self.name}: {self.path}")
        
        # Seek to end of file to only read new entries
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
                
                try:
                    entry = self.parser.parse_line(line)
                    if entry:
                        await self.process_entry(entry)
                except Exception as e:
                    logger.debug(f"Error parsing line from {self.name}: {e}")
        
        except Exception as e:
            logger.error(f"Error reading {self.name}: {e}")
    
    async def process_entry(self, entry):
        """Process a parsed log entry"""
        if not entry.data:
            return  # Skip entries with no extracted data
        
        event_type = entry.data.get('event')
        
        if event_type == 'mode_change':
            state.update_mode(entry.data['mode'])
        
        elif event_type == 'network_connected':
            state.update_network_status(entry.data['network'], True)
        
        elif event_type == 'network_disconnected':
            state.update_network_status(entry.data['network'], False)
        
        elif event_type in ['dmr_rx', 'dstar_rx', 'ysf_rx', 'p25_rx', 'nxdn_rx']:
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
