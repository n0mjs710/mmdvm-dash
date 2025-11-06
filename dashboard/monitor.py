"""
Log File Monitor
Watches log files for changes and parses new entries
"""
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Optional, List
import logging
from datetime import datetime, timedelta

from .parsers import get_parser
from .state import state, Transmission
from .config import config

logger = logging.getLogger(__name__)


class LogMonitor:
    """Monitors a single log file for changes"""
    
    def __init__(self, name: str, path: str, parser_type: str):
        self.name = name
        self.path = Path(path)
        self.original_pattern = path  # Store original path pattern for rotation detection
        self.parser = get_parser(parser_type)
        self.last_position = 0
        self.running = False
        # Use UTC since MMDVM logs use UTC timestamps regardless of server timezone
        self.last_check_time = datetime.utcnow()
        
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
        logger.debug(f"Starting monitor for {self.name}: {self.path}")
        
        # Parse recent log entries to establish current state (suppress broadcasts during scan)
        state.suppress_broadcasts = True
        await self.parse_recent_entries(lookback_lines=5000)  # Increased from 1000 to 5000
        state.suppress_broadcasts = False
        
        logger.info(f"Initialized {self.name} monitor - now watching for live events")
        
        # Now seek to end of file to only read new entries going forward
        try:
            self.last_position = self.path.stat().st_size
        except Exception as e:
            logger.error(f"Error getting file size for {self.name}: {e}")
            self.last_position = 0
        
        while self.running:
            try:
                await self.check_for_updates()
                await asyncio.sleep(0.5)  # Check twice per second for responsive UI
            except Exception as e:
                logger.error(f"Error monitoring {self.name}: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def parse_recent_entries(self, lookback_lines: int = 5000):
        """Parse recent log entries to establish current state on startup
        
        Scans backwards through logs looking for current state only.
        Checks up to 14 days back, stopping when all state is found.
        Items not found after 14 days are marked as 'unknown'.
        """
        try:
            # Define what state we're looking for based on log type
            state_to_find = self._get_state_targets()
            found_count = 0
            
            # Try current day and up to 13 previous days (14 days total)
            for days_back in range(14):
                if all(state_to_find.values()):
                    break  # Found everything, stop scanning
                
                # Calculate the date for this iteration (use UTC since MMDVM uses UTC)
                scan_date = datetime.utcnow() - timedelta(days=days_back)
                date_str = scan_date.strftime('%Y-%m-%d')
                
                # Extract the base log file name pattern and construct the dated filename
                # e.g., "mmdvm-2025-11-05.log" -> look for "mmdvm-2025-11-04.log"
                import re
                base_pattern = re.sub(r'\d{4}-\d{2}-\d{2}', date_str, self.path.name)
                log_file = self.path.parent / base_pattern
                
                if not log_file.exists():
                    logger.debug(f"Log file not found: {log_file}")
                    continue
                
                day_label = "today" if days_back == 0 else f"{days_back} day(s) ago"
                logger.debug(f"Scanning {day_label} log for {self.name}: {log_file}")
                found_count += await self._scan_for_state(log_file, lookback_lines, state_to_find)
            
            # Mark any remaining unfound items as 'unknown'
            unfound = [k for k, v in state_to_find.items() if not v]
            if unfound:
                logger.warning(f"Could not find state for {self.name} after 14-day scan: {unfound}")
                await self._mark_unknown_state(unfound)
            
            logger.info(f"Initial scan for {self.name}: found {found_count} state items, marked {len(unfound)} as unknown")
        
        except Exception as e:
            logger.error(f"Error parsing recent entries for {self.name}: {e}")
    
    async def _mark_unknown_state(self, unfound_items: List[str]):
        """Mark state items as unknown when they can't be found in logs"""
        from dashboard.state import state
        
        # Mark network states as unknown
        if 'dmr_network_connection' in unfound_items:
            # Mark all DMR networks as unknown
            pass  # Will be handled when we update state management
        if 'ysf_reflector' in unfound_items:
            state.update_network_status('YSF-Reflector', 'unknown')
        if 'p25_reflector' in unfound_items:
            state.update_network_status('P25-Reflector', 'unknown')
    
    def _get_state_targets(self) -> Dict[str, bool]:
        """Get the state information we need to find for this log type"""
        targets = {}
        
        # MMDVMHost-specific state
        if 'mmdvm' in self.name.lower():
            targets['current_mode'] = False  # Current operating mode
        
        # Gateway-specific state
        if 'DMRGateway' in self.name:
            targets['dmr_mmdvm_connection'] = False
            targets['dmr_network_connection'] = False
        elif 'P25Gateway' in self.name:
            targets['p25_reflector'] = False
        elif 'YSFGateway' in self.name:
            targets['ysf_reflector'] = False
        
        return targets
    
    async def _scan_for_state(self, log_path: Path, lookback_lines: int, state_to_find: Dict[str, bool]) -> int:
        """Scan backwards through log file, stopping when we've found all state we need
        
        Returns number of state items found.
        """
        try:
            async with aiofiles.open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = await f.readlines()
                
                if not all_lines:
                    return 0
                
                # Take last N lines
                if lookback_lines:
                    lines = all_lines[-lookback_lines:] if len(all_lines) > lookback_lines else all_lines
                else:
                    lines = all_lines
                
                # Scan BACKWARDS from most recent
                lines.reverse()
                
                found_count = 0
                processed = 0
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Stop if we've found everything we need
                    if all(state_to_find.values()):
                        logger.debug(f"Found all state for {self.name} after scanning {processed} lines")
                        break
                    
                    processed += 1
                    
                    if self.parser:
                        entry = self.parser.parse_line(line)
                        if entry:
                            # Check if this entry gives us state we need
                            if await self._process_state_entry(entry, state_to_find):
                                found_count += 1
                
                return found_count
        
        except Exception as e:
            logger.error(f"Error scanning log file {log_path}: {e}")
            return 0
    
    async def _process_state_entry(self, entry, state_to_find: Dict[str, bool]) -> bool:
        """Process an entry during state scanning. Returns True if this entry provided useful state."""
        if not entry.data:
            return False
        
        event_type = entry.data.get('event')
        found_something = False
        
        # Mode changes - always want most recent
        if event_type == 'mode_change' and not state_to_find.get('current_mode'):
            mode = entry.data.get('mode', 'IDLE')
            state.update_mode(mode)
            state_to_find['current_mode'] = True
            found_something = True
        
        # Gateway connections
        elif event_type == 'dmr_mmdvm_connected' and not state_to_find.get('dmr_mmdvm_connection'):
            state.update_network_status('DMR-MMDVM', True)
            state_to_find['dmr_mmdvm_connection'] = True
            found_something = True
        
        elif event_type == 'dmr_network_connected' and not state_to_find.get('dmr_network_connection'):
            network = entry.data.get('network', 'Unknown')
            state.update_network_status(f'DMR-{network}', True)
            state.update_network_status('DMR', True)  # Also set top-level DMR for frontend
            state_to_find['dmr_network_connection'] = True
            found_something = True
        
        elif event_type == 'dmr_network_disconnected' and not state_to_find.get('dmr_network_connection'):
            network = entry.data.get('network', 'Unknown')
            state.update_network_status(f'DMR-{network}', False)
            state.update_network_status('DMR', False)  # Also clear top-level DMR
            state_to_find['dmr_network_connection'] = True  # Found state (disconnected)
            found_something = True
        
        # P25 initial scan
        elif event_type == 'p25_reflector_linked' and not state_to_find.get('p25_reflector'):
            reflector = entry.data.get('reflector', 'Unknown')
            state.update_network_status('Network', True, reflector)
            state_to_find['p25_reflector'] = True
            found_something = True
            logger.info(f"Initial scan: Found P25 reflector {reflector}")
        
        # YSF initial scan
        elif event_type == 'ysf_reflector_linked' and not state_to_find.get('ysf_reflector'):
            reflector = entry.data.get('reflector', 'Unknown')
            state.update_network_status('YSF Network', True, reflector)
            state_to_find['ysf_reflector'] = True
            found_something = True
            logger.info(f"Initial scan: Found YSF reflector {reflector}")
        
        elif event_type == 'ysf_network_disconnected' and not state_to_find.get('ysf_reflector'):
            state.update_network_status('YSF Network', False)
            state_to_find['ysf_reflector'] = True  # Found state (disconnected)
            found_something = True
        
        return found_something
    
    async def _check_log_rotation(self):
        """Check if a new daily log file has been created and switch to it"""
        try:
            # Extract the base pattern (remove the date part)
            path_str = str(self.path)
            
            # Check if path contains a date pattern (YYYY-MM-DD)
            import re
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', path_str)
            if not date_match:
                return  # Not a dated log file, nothing to do
            
            # Build today's log file path (use UTC since MMDVM uses UTC)
            old_date = date_match.group(1)
            today_date = datetime.utcnow().strftime('%Y-%m-%d')
            
            if old_date == today_date:
                return  # Already on today's file
            
            # Generate new path with today's date
            new_path = Path(path_str.replace(old_date, today_date))
            
            if new_path.exists():
                logger.info(f"Switching {self.name} from {self.path.name} to {new_path.name}")
                self.path = new_path
                self.last_position = 0  # Start reading from beginning of new file
            
        except Exception as e:
            logger.error(f"Error checking log rotation for {self.name}: {e}")
    
    async def check_for_updates(self):
        """Check for new log entries and handle daily log rotation"""
        try:
            # Check for daily log rotation (every 60 seconds, use UTC since MMDVM uses UTC)
            now = datetime.utcnow()
            if (now - self.last_check_time).total_seconds() > 60:
                self.last_check_time = now
                await self._check_log_rotation()
            
            # Check if current file still exists
            if not self.path.exists():
                logger.warning(f"Log file disappeared: {self.path}")
                return
            
            current_size = self.path.stat().st_size
            
            # Check if file was rotated (size decreased) - unlikely with dated files
            if current_size < self.last_position:
                logger.info(f"Log file size decreased for {self.name}, resetting position")
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
                
                # Add to log buffer (only for MMDVMHost logs)
                if self.name in ['MMDVM', 'mmdvm', 'MMDVMHost']:
                    state.add_log_entry(line)
                
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
        
        # Use DEBUG for historical logs, INFO for live events
        log_fn = logger.debug if state.suppress_broadcasts else logger.info
        
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
        
        # YSF Gateway events (CONFIRMED PATTERNS)
        elif event_type == 'ysf_reflector_linked':
            # YSF connected to reflector (network and reflector are the same thing)
            reflector = entry.data.get('reflector', 'Unknown')
            state.update_network_status('YSF Network', True, reflector)
            log_fn(f"YSF linked to reflector: {reflector}")
        
        elif event_type == 'ysf_network_disconnected':
            # YSF network/reflector disconnected (they're the same)
            state.update_network_status('YSF Network', False)
            log_fn("YSF network/reflector disconnected")
        
        # P25 Gateway events (CONFIRMED PATTERNS)
        elif event_type == 'p25_reflector_linked':
            # P25 linked to reflector (assume connected, can't verify)
            reflector = entry.data.get('reflector', 'Unknown')
            state.update_network_status('Network', True, reflector)
            log_fn(f"P25 statically linked to reflector: {reflector}")
        
        # DMR Gateway events (WORKING - DO NOT MODIFY)
        elif event_type == 'dmr_mmdvm_connected':
            # DMRGateway connected to MMDVMHost (no disconnect is logged)
            state.update_network_status('DMR-MMDVM', True)
            log_fn("DMR Gateway connected to MMDVM")
        
        elif event_type == 'dmr_network_connected':
            # DMR network (e.g., HBlink4) logged in
            network = entry.data.get('network', 'Unknown')
            state.update_network_status(f'DMR-{network}', True)
            state.update_network_status('DMR', True)  # Also set top-level DMR for frontend
            log_fn(f"DMR network connected: {network}")
        
        elif event_type == 'dmr_network_disconnected':
            # DMR network closing
            network = entry.data.get('network', 'Unknown')
            state.update_network_status(f'DMR-{network}', False)
            state.update_network_status('DMR', False)  # Also clear top-level DMR
            log_fn(f"DMR network disconnected: {network}")
        
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
