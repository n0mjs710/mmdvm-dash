"""
Configuration Management for MMDVM Dashboard
"""
import json
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class Config:
    """Dashboard configuration"""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        default_config = {
            "dashboard": {
                "title": "MMDVM Dashboard",
                "description": "Amateur Radio Digital Voice Monitor",
                "host": "0.0.0.0",
                "port": 8080,
                "refresh_interval": 1000
            },
            "config_paths": {
                "mmdvm_ini": "/etc/MMDVM.ini",
                "dmr_gateway_ini": "/etc/DMRGateway.ini",
                "ysf_gateway_ini": "/etc/YSFGateway.ini",
                "p25_gateway_ini": "/etc/P25Gateway.ini"
            },
            "process_names": {
                "mmdvmhost": "MMDVMHost",
                "dmrgateway": "DMRGateway",
                "ysfgateway": "YSFGateway",
                "p25gateway": "P25Gateway",
                "nxdngateway": "NXDNGateway"
            },
            "history": {
                "enabled": True,
                "scan_on_startup": True,
                "days_back": 7,
                "max_days_for_gateway_connections": 30
            },
            "live_log": {
                "enabled": True,
                "max_lines": 500,
                "update_interval_ms": 200
            },
            "monitoring": {
                "max_recent_transmissions": 50,
                "max_events": 100,
                "transmission_timeout_seconds": 300
            },
            "display": {
                "show_mode_icons": True,
                "show_timestamps": True,
                "compact_view": False,
                "color_coded_logs": True
            },
            "performance": {
                "max_websocket_clients": 5,
                "log_buffer_size": 8192,
                "state_cleanup_interval": 3600
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    return self._merge_configs(default_config, user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
                logger.info("Using default configuration")
                return default_config
        else:
            logger.info(f"Config file not found at {self.config_path}, using defaults")
            # Create example config
            config_dir = self.config_path.parent
            config_dir.mkdir(parents=True, exist_ok=True)
            return default_config
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Deep merge user config with defaults"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, *keys, default=None):
        """Get nested config value"""
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value if value is not None else default

# Global config instance
config = Config()
