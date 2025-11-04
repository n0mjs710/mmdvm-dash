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
                "host": "0.0.0.0",
                "port": 8080
            },
            "config_paths": {
                "mmdvm_ini": "/etc/MMDVM.ini",
                "dmr_gateway_ini": "/etc/DMRGateway.ini",
                "ysf_gateway_ini": "/etc/YSFGateway.ini",
                "p25_gateway_ini": "/etc/P25Gateway.ini"
            },
            "process_names": {
                "mmdvmhost": "mmdvmhost",
                "dmrgateway": "dmrgateway",
                "ysfgateway": "ysfgateway",
                "p25gateway": "p25gateway",
                "nxdngateway": "nxdngateway"
            },
            "monitoring": {
                "max_recent_calls": 50,
                "max_events": 100,
                "log_buffer_size": 50
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
