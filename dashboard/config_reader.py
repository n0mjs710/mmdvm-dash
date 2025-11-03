"""
Configuration File Readers for MMDVM and Gateway Programs
Reads INI files to understand expected system state and checks process status
"""
import configparser
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


def is_process_running(process_name: str) -> bool:
    """Check if a process is running via systemd or process list"""
    # First try systemd
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', process_name],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.stdout.strip() == 'active':
            logger.debug(f"Process {process_name} is active via systemd")
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    # Fallback to checking process list
    try:
        result = subprocess.run(
            ['pgrep', '-f', process_name],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.debug(f"Process {process_name} found in process list")
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    logger.debug(f"Process {process_name} not running")
    return False


class MMDVMConfig:
    """Parse and provide access to MMDVM.ini configuration"""
    
    def __init__(self, config_path: str = "/etc/MMDVM.ini"):
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser(strict=False)  # Allow duplicate keys
        self.enabled_modes: Set[str] = set()
        self.enabled_networks: Set[str] = set()
        self.log_settings = {}
        self.is_running = is_process_running('mmdvmhost')
        
        if self.config_path.exists():
            self._load_config()
        else:
            logger.warning(f"MMDVM.ini not found at {config_path}")
    
    def _load_config(self):
        """Load and parse MMDVM.ini"""
        try:
            self.config.read(self.config_path)
            # Only parse if MMDVMHost is running
            if self.is_running:
                self._parse_modes()
                self._parse_networks()
                self._parse_log_settings()
                logger.info(f"Loaded MMDVM config: {len(self.enabled_modes)} modes, {len(self.enabled_networks)} networks")
            else:
                logger.warning("MMDVMHost config exists but process not running")
        except Exception as e:
            logger.error(f"Error loading MMDVM.ini: {e}")
    
    def _parse_modes(self):
        """Identify enabled digital/analog modes"""
        mode_sections = {
            'D-Star': 'D-Star',
            'DMR': 'DMR',
            'System Fusion': 'YSF',
            'P25': 'P25',
            'NXDN': 'NXDN',
            'POCSAG': 'POCSAG',
            'FM': 'FM'
        }
        
        for section, mode in mode_sections.items():
            if self.config.has_section(section):
                enabled = self.config.getboolean(section, 'Enable', fallback=False)
                if enabled:
                    self.enabled_modes.add(mode)
    
    def _parse_networks(self):
        """Identify enabled network connections"""
        network_sections = {
            'D-Star Network': 'D-Star',
            'DMR Network': 'DMR',
            'System Fusion Network': 'YSF',
            'P25 Network': 'P25',
            'NXDN Network': 'NXDN',
            'POCSAG Network': 'POCSAG',
            'FM Network': 'FM'
        }
        
        for section, network in network_sections.items():
            if self.config.has_section(section):
                enabled = self.config.getboolean(section, 'Enable', fallback=False)
                if enabled:
                    self.enabled_networks.add(network)
    
    def _parse_log_settings(self):
        """Extract log file configuration"""
        if self.config.has_section('Log'):
            self.log_settings = {
                'file_path': self.config.get('Log', 'FilePath', fallback='/var/log/mmdvm'),
                'file_root': self.config.get('Log', 'FileRoot', fallback='MMDVM'),
                'file_level': self.config.getint('Log', 'FileLevel', fallback=1),
                'display_level': self.config.getint('Log', 'DisplayLevel', fallback=1),
                'file_rotate': self.config.getboolean('Log', 'FileRotate', fallback=True)
            }
    
    def get_log_file_path(self) -> Optional[Path]:
        """Get the full path to MMDVMHost log file"""
        if self.log_settings:
            path = Path(self.log_settings['file_path'])
            root = self.log_settings['file_root']
            
            # MMDVMHost creates logs like: /var/log/mmdvm/MMDVM-2025-11-02.log
            # We'll return the base pattern for monitoring
            return path / f"{root}-*.log"
        return None
    
    def get_modem_settings(self) -> Dict:
        """Get modem configuration"""
        if not self.config.has_section('Modem'):
            return {}
        
        return {
            'port': self.config.get('Modem', 'Port', fallback=''),
            'protocol': self.config.get('Modem', 'Protocol', fallback='uart'),
            'address': self.config.get('Modem', 'Address', fallback=''),
            'rx_frequency': self.config.get('Modem', 'RXFrequency', fallback=''),
            'tx_frequency': self.config.get('Modem', 'TXFrequency', fallback=''),
            'power': self.config.get('Modem', 'TXPower', fallback=''),
        }
    
    def get_info(self) -> Dict:
        """Get station info"""
        if not self.config.has_section('Info'):
            return {}
        
        return {
            'callsign': self.config.get('Info', 'Callsign', fallback=''),
            'id': self.config.get('Info', 'Id', fallback=''),
            'rx_frequency': self.config.get('Info', 'RXFrequency', fallback=''),
            'tx_frequency': self.config.get('Info', 'TXFrequency', fallback=''),
            'power': self.config.get('Info', 'Power', fallback=''),
            'latitude': self.config.get('Info', 'Latitude', fallback=''),
            'longitude': self.config.get('Info', 'Longitude', fallback=''),
            'height': self.config.get('Info', 'Height', fallback=''),
            'location': self.config.get('Info', 'Location', fallback=''),
            'description': self.config.get('Info', 'Description', fallback=''),
            'url': self.config.get('Info', 'URL', fallback='')
        }


class GatewayConfig:
    """Base class for gateway configuration readers"""
    
    def __init__(self, config_path: str, process_name: str):
        self.config_path = Path(config_path)
        self.process_name = process_name
        self.config = configparser.ConfigParser(strict=False)  # Allow duplicate keys
        self.enabled = False
        self.networks: Dict[str, bool] = {}
        
        # Check if process is actually running
        self.is_running = is_process_running(process_name)
        
        if self.config_path.exists():
            self._load_config()
    
    def _load_config(self):
        """Load gateway config"""
        try:
            self.config.read(self.config_path)
            # Only parse if process is running
            if self.is_running:
                self._parse_settings()
            else:
                logger.debug(f"{self.process_name} config exists but process not running")
        except Exception as e:
            logger.error(f"Error loading {self.config_path}: {e}")
    
    def _parse_settings(self):
        """Override in subclass"""
        pass
    
    def get_log_file_path(self) -> Optional[Path]:
        """Get log file path"""
        if self.config.has_section('Log'):
            path = self.config.get('Log', 'FilePath', fallback='/var/log/mmdvm')
            root = self.config.get('Log', 'FileRoot', fallback='Gateway')
            return Path(path) / f"{root}-*.log"
        return None


class DMRGatewayConfig(GatewayConfig):
    """Parse DMRGateway.ini configuration"""
    
    def __init__(self, config_path: str = "/etc/DMRGateway.ini"):
        super().__init__(config_path, 'dmrgateway')
    
    def _parse_settings(self):
        """Parse DMR Gateway specific settings"""
        # Process is running, now check which networks are enabled
        
        # DMRGateway can connect to multiple networks
        network_sections = [
            'DMR Network 1',
            'DMR Network 2', 
            'DMR Network 3',
            'DMR Network 4',
            'DMR Network 5',
            'DMR Network Custom'
        ]
        
        for section in network_sections:
            if self.config.has_section(section):
                # Check both 'Enabled' and 'Enable'
                enabled = (self.config.getboolean(section, 'Enabled', fallback=False) or
                          self.config.getboolean(section, 'Enable', fallback=False))
                if enabled:
                    name = self.config.get(section, 'Name', fallback=section)
                    logger.info(f"DMRGateway: Found enabled network '{name}'")
                    self.networks[name] = True
                    self.enabled = True  # Gateway is operational with at least one network
                else:
                    logger.debug(f"DMRGateway: {section} exists but not enabled")


class YSFGatewayConfig(GatewayConfig):
    """Parse YSFGateway.ini configuration"""
    
    def __init__(self, config_path: str = "/etc/YSFGateway.ini"):
        super().__init__(config_path, 'ysfgateway')
    
    def _parse_settings(self):
        """Parse YSF Gateway specific settings"""
        # YSFGateway is operational if config exists
        # Check [YSF Network] for Enable flag and [Network] for startup
        
        if self.config.has_section('YSF Network'):
            enabled = (self.config.getboolean('YSF Network', 'Enable', fallback=False) or
                      self.config.getboolean('YSF Network', 'Enabled', fallback=False))
            if enabled:
                self.enabled = True
                # Get startup network from [Network] section
                if self.config.has_section('Network'):
                    startup = self.config.get('Network', 'Startup', fallback='')
                    if startup:
                        logger.info(f"YSFGateway: Enabled with startup reflector '{startup}'")
                        self.networks['Reflector'] = startup
                    else:
                        logger.info("YSFGateway: Enabled, no startup reflector")
                        self.networks['YSF Network'] = 'Enabled'
                else:
                    logger.info("YSFGateway: Enabled")
                    self.networks['YSF Network'] = 'Enabled'
            else:
                logger.debug("YSFGateway: YSF Network not enabled")
        
        # Also check FCS Network
        if self.config.has_section('FCS Network'):
            enabled = (self.config.getboolean('FCS Network', 'Enable', fallback=False) or
                      self.config.getboolean('FCS Network', 'Enabled', fallback=False))
            if enabled:
                self.enabled = True
                logger.info("YSFGateway: FCS Network enabled")
                self.networks['FCS Network'] = 'Enabled'


class P25GatewayConfig(GatewayConfig):
    """Parse P25Gateway.ini configuration"""
    
    def __init__(self, config_path: str = "/etc/P25Gateway.ini"):
        super().__init__(config_path, 'p25gateway')
    
    def _parse_settings(self):
        """Parse P25 Gateway specific settings"""
        # P25Gateway is operational if config exists
        # Network section contains Startup and Static TG definitions
        
        if self.config.has_section('Network'):
            # P25Gateway typically doesn't have Enable flag - presence of network config means it's operational
            startup = self.config.get('Network', 'Startup', fallback='')
            static = self.config.get('Network', 'Static', fallback='')
            
            if startup or static:
                self.enabled = True
                if startup:
                    logger.info(f"P25Gateway: Operational with startup TG {startup}")
                    self.networks['Startup'] = f"TG {startup}"
                if static and static != startup:
                    logger.info(f"P25Gateway: Also has static TG {static}")
                    self.networks['Static'] = f"TG {static}"
            else:
                logger.debug("P25Gateway: Network section exists but no TGs configured")


class NXDNGatewayConfig(GatewayConfig):
    """Parse NXDNGateway.ini configuration"""
    
    def __init__(self, config_path: str = "/etc/NXDNGateway.ini"):
        super().__init__(config_path, 'nxdngateway')
    
    def _parse_settings(self):
        """Parse NXDN Gateway specific settings"""
        if self.config.has_section('Network'):
            self.enabled = self.config.getboolean('Network', 'Enable', fallback=False)
            if self.enabled:
                self.networks['NXDNNetwork'] = True


class ConfigManager:
    """Manages all configuration files"""
    
    def __init__(self, 
                 mmdvm_ini: str = "/etc/MMDVM.ini",
                 dmr_gateway_ini: str = "/etc/DMRGateway.ini",
                 ysf_gateway_ini: str = "/etc/YSFGateway.ini",
                 p25_gateway_ini: str = "/etc/P25Gateway.ini",
                 nxdn_gateway_ini: Optional[str] = None):
        
        self.mmdvm = MMDVMConfig(mmdvm_ini)
        self.dmr_gateway = DMRGatewayConfig(dmr_gateway_ini)
        self.ysf_gateway = YSFGatewayConfig(ysf_gateway_ini)
        self.p25_gateway = P25GatewayConfig(p25_gateway_ini)
        self.nxdn_gateway = NXDNGatewayConfig(nxdn_gateway_ini) if nxdn_gateway_ini else None
    
    def get_expected_state(self) -> Dict:
        """Get the expected system state based on configuration files"""
        state = {
            'mmdvm_running': self.mmdvm.is_running,
            'enabled_modes': list(self.mmdvm.enabled_modes),
            'enabled_networks': list(self.mmdvm.enabled_networks),
            'gateways': {
                'dmr': {
                    'is_running': self.dmr_gateway.is_running,
                    'enabled': self.dmr_gateway.enabled,
                    'networks': self.dmr_gateway.networks
                },
                'ysf': {
                    'is_running': self.ysf_gateway.is_running,
                    'enabled': self.ysf_gateway.enabled,
                    'networks': self.ysf_gateway.networks
                },
                'p25': {
                    'is_running': self.p25_gateway.is_running,
                    'enabled': self.p25_gateway.enabled,
                    'networks': self.p25_gateway.networks
                }
            },
            'modem': self.mmdvm.get_modem_settings(),
            'info': self.mmdvm.get_info()
        }
        
        # Add NXDN if configured
        if self.nxdn_gateway:
            state['gateways']['nxdn'] = {
                'is_running': self.nxdn_gateway.is_running,
                'enabled': self.nxdn_gateway.enabled,
                'networks': self.nxdn_gateway.networks
            }
        
        return state
    
    def get_all_log_paths(self) -> List[Path]:
        """Get all log file paths to monitor"""
        paths = []
        
        # MMDVMHost log
        mmdvm_log = self.mmdvm.get_log_file_path()
        if mmdvm_log:
            paths.append(mmdvm_log)
        
        # Gateway logs
        gateways = [self.dmr_gateway, self.ysf_gateway, self.p25_gateway]
        if self.nxdn_gateway:
            gateways.append(self.nxdn_gateway)
            
        for gateway in gateways:
            if gateway and gateway.enabled:
                log_path = gateway.get_log_file_path()
                if log_path:
                    paths.append(log_path)
        
        return paths


# Global config manager instance
config_manager = None

def initialize_config_manager(**kwargs):
    """Initialize the global config manager"""
    global config_manager
    config_manager = ConfigManager(**kwargs)
    return config_manager
