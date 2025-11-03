"""
Dashboard State Management
Maintains current system state and recent activity
"""
import asyncio
from collections import deque
from datetime import datetime
from typing import Dict, List, Any, Set
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemStatus:
    """Overall system status"""
    current_mode: str = "IDLE"
    modem_connected: bool = False
    modem_description: str = ""
    networks: Dict[str, bool] = field(default_factory=dict)
    last_update: float = field(default_factory=lambda: datetime.now().timestamp())
    
    # Gateway and MMDVMHost operational status
    mmdvm_running: bool = False
    enabled_modes: List[str] = field(default_factory=list)
    gateways: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    info: Dict[str, Any] = field(default_factory=dict)  # Repeater info (callsign, location, etc)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Transmission:
    """Represents a transmission event"""
    timestamp: float
    mode: str
    source: str
    destination: str
    slot: int = 0
    network: str = ""
    duration: float = 0.0
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    """Represents a dashboard event"""
    timestamp: float
    event_type: str
    source: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DashboardState:
    """Maintains dashboard state"""
    
    def __init__(self, max_recent_calls: int = 50, max_events: int = 100):
        self.status = SystemStatus()
        self.recent_calls: deque = deque(maxlen=max_recent_calls)
        self.events: deque = deque(maxlen=max_events)
        self.active_transmissions: Dict[str, Transmission] = {}
        self.websocket_clients: Set = set()
        
        # Statistics
        self.stats = {
            'total_calls_today': 0,
            'calls_by_mode': {},
            'active_users': set()
        }
        
        # Debouncing for broadcasts
        self._broadcast_pending = False
        self._broadcast_task = None
    
    def update_mode(self, mode: str):
        """Update current operating mode"""
        old_mode = self.status.current_mode
        self.status.current_mode = mode
        self.status.last_update = datetime.now().timestamp()
        
        event = Event(
            timestamp=self.status.last_update,
            event_type='mode_change',
            source='mmdvmhost',
            message=f'Mode changed from {old_mode} to {mode}',
            data={'old_mode': old_mode, 'new_mode': mode}
        )
        self.add_event(event)
        logger.info(f"Mode changed: {old_mode} -> {mode}")
        
        # Immediate broadcast for mode changes (critical for responsive UI)
        asyncio.create_task(self.broadcast_status_update())
    
    def update_network_status(self, network: str, connected: bool, target: str = None):
        """Update network connection status
        
        Args:
            network: Network name (e.g., 'YSF', 'DMR', 'P25')
            connected: Whether the network is connected
            target: Optional target/reflector name (e.g., 'Kansas' for YSF reflector, '3120' for P25)
        """
        # Store the target (reflector name/number) if connected, otherwise False
        if connected and target:
            self.status.networks[network] = target
        else:
            self.status.networks[network] = connected
        
        self.status.last_update = datetime.now().timestamp()
        
        # Build message with target if provided
        if target and connected:
            message = f'{network} connected to {target}'
        else:
            message = f'{network} {"connected" if connected else "disconnected"}'
        
        event = Event(
            timestamp=self.status.last_update,
            event_type='network_status',
            source='network',
            message=message,
            data={'network': network, 'connected': connected, 'target': target}
        )
        self.add_event(event)
        logger.info(message)
    
    def add_transmission(self, transmission: Transmission):
        """Add or update a transmission"""
        key = f"{transmission.mode}_{transmission.slot}_{transmission.source}"
        self.active_transmissions[key] = transmission
        
        # Add to recent calls
        self.recent_calls.append(transmission)
        
        # Update statistics
        self.stats['total_calls_today'] += 1
        mode_stats = self.stats['calls_by_mode'].get(transmission.mode, 0)
        self.stats['calls_by_mode'][transmission.mode] = mode_stats + 1
        self.stats['active_users'].add(transmission.source)
        
        event = Event(
            timestamp=transmission.timestamp,
            event_type='transmission_start',
            source=transmission.mode.lower(),
            message=f'{transmission.source} → {transmission.destination} on {transmission.mode}',
            data=transmission.to_dict()
        )
        self.add_event(event)
        logger.debug(f"Transmission: {transmission.source} -> {transmission.destination} ({transmission.mode})")
        
        # Trigger immediate broadcast for transmission events (user wants responsive UI)
        asyncio.create_task(self.broadcast_status_update())
    
    def end_transmission(self, key: str, duration: float = 0.0):
        """Mark transmission as ended"""
        if key in self.active_transmissions:
            tx = self.active_transmissions[key]
            tx.active = False
            tx.duration = duration
            
            event = Event(
                timestamp=datetime.now().timestamp(),
                event_type='transmission_end',
                source=tx.mode.lower(),
                message=f'{tx.source} → {tx.destination} ended ({duration:.1f}s)',
                data=tx.to_dict()
            )
            self.add_event(event)
            
            del self.active_transmissions[key]
            logger.debug(f"Transmission ended: {tx.source} -> {tx.destination} ({duration:.1f}s)")
            
            # Trigger immediate broadcast for transmission end
            asyncio.create_task(self.broadcast_status_update())
    
    def end_transmission_by_mode(self, mode: str):
        """End all active transmissions for a specific mode"""
        keys_to_remove = [key for key, tx in self.active_transmissions.items() if tx.mode == mode]
        for key in keys_to_remove:
            self.end_transmission(key)
        if keys_to_remove:
            logger.debug(f"Ended {len(keys_to_remove)} transmission(s) for {mode}")
    
    def clear_all_transmissions(self):
        """Clear all active transmissions (e.g., when mode changes to IDLE)"""
        count = len(self.active_transmissions)
        if count > 0:
            self.active_transmissions.clear()
            logger.info(f"Cleared {count} active transmission(s) due to mode change")
    
    def add_event(self, event: Event):
        """Add event to history"""
        self.events.append(event)
    
    def update_expected_state(self, expected_state: Dict[str, Any]):
        """Update expected state from config reader"""
        self.status.mmdvm_running = expected_state.get('mmdvm_running', False)
        self.status.enabled_modes = expected_state.get('enabled_modes', [])
        self.status.info = expected_state.get('info', {})  # Store repeater info
        
        # Store enabled networks from MMDVM config
        enabled_networks = expected_state.get('enabled_networks', [])
        for network in enabled_networks:
            # Only set to True if not already set to a specific target (reflector/TG)
            if network not in self.status.networks or self.status.networks[network] is False:
                self.status.networks[network] = True  # Mark as configured
        
        # Update gateway status
        gateways = expected_state.get('gateways', {})
        self.status.gateways = {}
        
        for gw_name, gw_data in gateways.items():
            self.status.gateways[gw_name] = {
                'is_running': gw_data.get('is_running', False),
                'enabled': gw_data.get('enabled', False),
                'networks': gw_data.get('networks', {})
            }
        
        self.status.last_update = datetime.now().timestamp()
        logger.info(f"Updated expected state: MMDVMHost={self.status.mmdvm_running}, Networks={enabled_networks}, Gateways={list(self.status.gateways.keys())}")
        
        # Immediate broadcast for process status changes (critical updates)
        asyncio.create_task(self.broadcast_status_update())
    
    async def broadcast_status_update(self):
        """Broadcast status update to all connected WebSocket clients"""
        if not self.websocket_clients:
            logger.debug("No WebSocket clients connected, skipping broadcast")
            return
        
        status_data = self.get_status()
        message = {
            'type': 'state_update',  # Frontend expects 'state_update'
            'status': status_data,
            'active_transmissions': self.get_active_transmissions(),
            'recent_calls': self.get_recent_calls(10),
            'events': self.get_events(20)
        }
        
        logger.debug(f"Broadcasting status update to {len(self.websocket_clients)} clients")
        logger.debug(f"Gateway status being sent: dmr={status_data.get('gateways', {}).get('dmr', {})}, ysf={status_data.get('gateways', {}).get('ysf', {})}, p25={status_data.get('gateways', {}).get('p25', {})}")
        logger.debug(f"Network status being sent: {status_data.get('networks', {})}")
        
        # Send to all clients, removing disconnected ones
        disconnected = []
        for client in self.websocket_clients.copy():
            try:
                await client.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to client: {e}")
                disconnected.append(client)
        
        # Remove disconnected clients
        for client in disconnected:
            self.websocket_clients.discard(client)
    
    def schedule_broadcast(self):
        """Schedule a debounced broadcast (batches updates every 500ms)"""
        if self._broadcast_pending:
            return  # Already scheduled
        
        self._broadcast_pending = True
        
        async def debounced_broadcast():
            await asyncio.sleep(0.5)  # Wait 500ms to batch updates
            self._broadcast_pending = False
            await self.broadcast_status_update()
        
        # Cancel previous task if exists
        if self._broadcast_task and not self._broadcast_task.done():
            self._broadcast_task.cancel()
        
        self._broadcast_task = asyncio.create_task(debounced_broadcast())
    
    def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent calls"""
        calls = list(self.recent_calls)
        calls.reverse()
        return [call.to_dict() for call in calls[:limit]]
    
    def get_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent events"""
        events = list(self.events)
        events.reverse()
        return [event.to_dict() for event in events[:limit]]
    
    def get_active_transmissions(self) -> List[Dict[str, Any]]:
        """Get active transmissions"""
        return [tx.to_dict() for tx in self.active_transmissions.values()]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            **self.status.to_dict(),
            'enabled_networks': list(self.status.networks.keys()),  # List of network names
            'active_transmissions': len(self.active_transmissions),
            'total_calls_today': self.stats['total_calls_today'],
            'calls_by_mode': self.stats['calls_by_mode'],
            'active_users': len(self.stats['active_users'])
        }


# Global state instance
state = DashboardState()
