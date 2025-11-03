"""
Dashboard State Management
Maintains current system state and recent activity
"""
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
    
    def update_network_status(self, network: str, connected: bool):
        """Update network connection status"""
        self.status.networks[network] = connected
        self.status.last_update = datetime.now().timestamp()
        
        event = Event(
            timestamp=self.status.last_update,
            event_type='network_status',
            source='network',
            message=f'{network} {"connected" if connected else "disconnected"}',
            data={'network': network, 'connected': connected}
        )
        self.add_event(event)
        logger.info(f"Network {network}: {'connected' if connected else 'disconnected'}")
    
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
        logger.info(f"Transmission: {transmission.source} -> {transmission.destination} ({transmission.mode})")
    
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
            logger.info(f"Transmission ended: {tx.source} -> {tx.destination} ({duration:.1f}s)")
    
    def add_event(self, event: Event):
        """Add event to history"""
        self.events.append(event)
    
    def update_expected_state(self, expected_state: Dict[str, Any]):
        """Update expected state from config reader"""
        self.status.mmdvm_running = expected_state.get('mmdvm_running', False)
        self.status.enabled_modes = expected_state.get('enabled_modes', [])
        
        # Store enabled networks from MMDVM config
        enabled_networks = expected_state.get('enabled_networks', [])
        for network in enabled_networks:
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
