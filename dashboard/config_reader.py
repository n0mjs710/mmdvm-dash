"""
Configuration File Readers for MMDVM and Gateway Programs
Reads INI files to understand expected system state and checks process status
"""
import configparser
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

from .config import config

logger = logging.getLogger(__name__)


# Cache for process status to avoid repeated checks
_process_cache = {}
_cache_timestamp = 0


def check_all_processes(process_names: List[str]) -> Dict[str, bool]:
    """
    Check multiple processes in a single operation (optimized)
    Returns dict mapping process_name -> is_running
    """
    import time
    global _process_cache, _cache_timestamp
    
    # Use cache if less than 1 second old
    current_time = time.time()
    if current_time - _cache_timestamp < 1.0:
        return {name: _process_cache.get(name, False) for name in process_names}
    
    results = {}
    
    # Try systemctl for all processes at once
    systemctl_results = {}
    try:
        # Check all services in one systemctl call
        for process_name in process_names:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', process_name],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                systemctl_results[process_name] = (result.stdout.strip() == 'active')
            except:
                systemctl_results[process_name] = False
    except:
        pass
    
    # Get all processes in one ps call
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            timeout=2
        )
        process_list = result.stdout.lower()
        
        for process_name in process_names:
            # Check systemctl first, then fallback to ps
            if systemctl_results.get(process_name, False):
                results[process_name] = True
            else:
                # Case-insensitive search in process list
                results[process_name] = process_name.lower() in process_list
            
            logger.debug(f"Process {process_name}: {results[process_name]}")
    
    except Exception as e:
        logger.error(f"Error checking processes: {e}")
        # Fallback to False for all
        results = {name: False for name in process_names}
    
    # Update cache
    _process_cache = results
    _cache_timestamp = current_time
    
    return results


def is_process_running(process_name: str) -> bool:
    """Check if a process is running (uses cached check_all_processes)"""
    # Use the optimized batch check with cache
    result = check_all_processes([process_name])
    return result.get(process_name, False)


class MMDVMConfig:
    """Parse and provide access to MMDVM.ini configuration"""
    
    def __init__(self, config_path: str = "/etc/MMDVM.ini"):
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser(strict=False)  # Allow duplicate keys
        self.enabled_modes: Set[str] = set()
        self.enabled_networks: Set[str] = set()
        self.log_settings = {}
        # Get process name from config
        process_name = config.get('process_names', 'mmdvmhost', default='mmdvmhost')
        self.is_running = is_process_running(process_name)
        
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
        """Get station info from [General] and [Info] sections"""
        info = {}
        
        # Get callsign and DMR ID from [General] section
        if self.config.has_section('General'):
            info['callsign'] = self.config.get('General', 'Callsign', fallback='').strip('"').strip("'")
            info['dmr_id'] = self.config.get('General', 'Id', fallback='').strip('"').strip("'")
        
        # Get rest from [Info] section (if it exists)
        if self.config.has_section('Info'):
            info.update({
                'rx_frequency': self.config.get('Info', 'RXFrequency', fallback=''),
                'tx_frequency': self.config.get('Info', 'TXFrequency', fallback=''),
                'power': self.config.get('Info', 'Power', fallback=''),
                'latitude': self.config.get('Info', 'Latitude', fallback=''),
                'longitude': self.config.get('Info', 'Longitude', fallback=''),
                'height': self.config.get('Info', 'Height', fallback=''),
                'location': self.config.get('Info', 'Location', fallback='').strip('"').strip("'"),
                'description': self.config.get('Info', 'Description', fallback='').strip('"').strip("'"),
                'url': self.config.get('Info', 'URL', fallback='')
            })
        
        return info


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
            # Parse settings to determine enabled status
            self._parse_settings()
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
        process_name = config.get('process_names', 'dmrgateway', default='dmrgateway')
        super().__init__(config_path, process_name)
    
    def _parse_settings(self):
        """Parse DMR Gateway specific settings - scan ALL enabled stanzas"""
        # Scan all sections for anything with an 'Enable' or 'Enabled' parameter
        for section in self.config.sections():
            # Check if this section has Enable/Enabled parameter
            has_enable = (self.config.has_option(section, 'Enable') or 
                         self.config.has_option(section, 'Enabled'))
            
            if not has_enable:
                continue
                
            enabled = (self.config.getboolean(section, 'Enabled', fallback=False) or
                      self.config.getboolean(section, 'Enable', fallback=False))
            
            if not enabled:
                logger.debug(f"DMRGateway: {section} exists but not enabled")
                continue
            
            # Section is enabled - determine if it's a network or not
            is_network = section.startswith('DMR Network')
            
            if is_network:
                # Network sections use the 'Name' parameter for the pill label
                name = self.config.get(section, 'Name', fallback=section)
                logger.info(f"DMRGateway: Found enabled network '{name}' in section '{section}'")
                self.networks[name] = {'type': 'network', 'section': section, 'status': 'unknown'}
            else:
                # Non-network sections use the section name as the pill label
                logger.info(f"DMRGateway: Found enabled feature '{section}'")
                self.networks[section] = {'type': 'feature', 'section': section, 'status': 'enabled'}
            
            self.enabled = True  # Gateway has at least one enabled feature


class YSFGatewayConfig(GatewayConfig):
    """Parse YSFGateway.ini configuration"""
    
    def __init__(self, config_path: str = "/etc/YSFGateway.ini"):
        process_name = config.get('process_names', 'ysfgateway', default='ysfgateway')
        super().__init__(config_path, process_name)
    
    def _parse_settings(self):
        """Parse YSF Gateway specific settings - scan ALL enabled stanzas"""
        # Scan all sections for anything with an 'Enable' or 'Enabled' parameter
        for section in self.config.sections():
            # Check if this section has Enable/Enabled parameter
            has_enable = (self.config.has_option(section, 'Enable') or 
                         self.config.has_option(section, 'Enabled'))
            
            if not has_enable:
                continue
                
            enabled = (self.config.getboolean(section, 'Enabled', fallback=False) or
                      self.config.getboolean(section, 'Enable', fallback=False))
            
            if not enabled:
                logger.debug(f"YSFGateway: {section} exists but not enabled")
                continue
            
            # Section is enabled - YSF Network and FCS Network are networks, others are features
            is_network = section in ['YSF Network', 'FCS Network']
            
            if is_network:
                logger.info(f"YSFGateway: Found enabled network '{section}'")
                # For YSF Network, try to get startup reflector name
                startup_reflector = None
                if section == 'YSF Network' and self.config.has_section('Network'):
                    startup = self.config.get('Network', 'Startup', fallback='').strip()
                    if startup and not startup.startswith('#'):
                        startup_reflector = startup
                        
                self.networks[section] = {
                    'type': 'network', 
                    'section': section, 
                    'status': 'unknown',
                    'startup_reflector': startup_reflector
                }
            else:
                # Non-network sections (APRS, GPSD, etc.) use section name as label
                logger.info(f"YSFGateway: Found enabled feature '{section}'")
                self.networks[section] = {'type': 'feature', 'section': section, 'status': 'enabled'}
            
            self.enabled = True  # Gateway has at least one enabled feature


class P25GatewayConfig(GatewayConfig):
    """Parse P25Gateway.ini configuration"""
    
    def __init__(self, config_path: str = "/etc/P25Gateway.ini"):
        process_name = config.get('process_names', 'p25gateway', default='p25gateway')
        super().__init__(config_path, process_name)
    
    def _parse_settings(self):
        """Parse P25 Gateway specific settings - scan ALL enabled stanzas"""
        # Scan all sections for anything with an 'Enable' or 'Enabled' parameter
        for section in self.config.sections():
            # Check if this section has Enable/Enabled parameter
            has_enable = (self.config.has_option(section, 'Enable') or 
                         self.config.has_option(section, 'Enabled'))
            
            if not has_enable:
                continue
                
            enabled = (self.config.getboolean(section, 'Enabled', fallback=False) or
                      self.config.getboolean(section, 'Enable', fallback=False))
            
            if not enabled:
                logger.debug(f"P25Gateway: {section} exists but not enabled")
                continue
            
            # Section is enabled - P25 Network is a network, others are features
            is_network = section in ['Network', 'P25 Network']
            
            if is_network:
                logger.info(f"P25Gateway: Found enabled network '{section}'")
                # Try to get static reflector ID from Network section
                reflector_id = None
                if self.config.has_option(section, 'Static'):
                    reflector_id = self.config.get(section, 'Static', fallback='').strip()
                    
                self.networks[section] = {
                    'type': 'network', 
                    'section': section, 
                    'status': 'unknown',  # Assume connected since we can't detect
                    'reflector_id': reflector_id
                }
            else:
                # Non-network sections use section name as label
                logger.info(f"P25Gateway: Found enabled feature '{section}'")
                self.networks[section] = {'type': 'feature', 'section': section, 'status': 'enabled'}
            
            self.enabled = True  # Gateway has at least one enabled feature


class NXDNGatewayConfig(GatewayConfig):
    """Parse NXDNGateway.ini configuration"""
    
    def __init__(self, config_path: str = "/etc/NXDNGateway.ini"):
        process_name = config.get('process_names', 'nxdngateway', default='nxdngateway')
        super().__init__(config_path, process_name)
    
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
    
    def refresh_process_status(self):
        """Efficiently refresh all process statuses in a single batch check"""
        # Collect all process names
        process_names = [
            config.get('process_names', 'mmdvmhost', default='mmdvmhost'),
            config.get('process_names', 'dmrgateway', default='DMRGateway'),
            config.get('process_names', 'ysfgateway', default='YSFGateway'),
            config.get('process_names', 'p25gateway', default='P25Gateway'),
        ]
        
        if self.nxdn_gateway:
            process_names.append(config.get('process_names', 'nxdngateway', default='NXDNGateway'))
        
        # Single optimized check for all processes
        results = check_all_processes(process_names)
        
        # Update each component
        self.mmdvm.is_running = results.get(process_names[0], False)
        self.dmr_gateway.is_running = results.get(process_names[1], False)
        self.ysf_gateway.is_running = results.get(process_names[2], False)
        self.p25_gateway.is_running = results.get(process_names[3], False)
        if self.nxdn_gateway:
            self.nxdn_gateway.is_running = results.get(process_names[4], False)
    
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
