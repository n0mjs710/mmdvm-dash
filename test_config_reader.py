#!/usr/bin/env python3
"""
Test script to verify config_reader can parse INI files
"""
from dashboard.config_reader import initialize_config_manager

def test_config_reader():
    """Test reading configuration from INI files"""
    print("Testing config_reader with default paths...")
    
    config_mgr = initialize_config_manager(
        mmdvm_ini="/etc/MMDVM.ini",
        dmr_gateway_ini="/etc/DMRGateway.ini",
        ysf_gateway_ini="/etc/YSFGateway.ini",
        p25_gateway_ini="/etc/P25Gateway.ini"
    )
    
    print("\n=== Expected State ===")
    state = config_mgr.get_expected_state()
    print(f"Enabled modes: {state['enabled_modes']}")
    print(f"Enabled networks: {state['enabled_networks']}")
    print(f"\nGateways:")
    for gw_name, gw_info in state['gateways'].items():
        print(f"  {gw_name}: enabled={gw_info['enabled']}, networks={gw_info['networks']}")
    
    print(f"\nModem: {state['modem']}")
    print(f"\nStation Info: {state['info']}")
    
    print("\n=== Log Paths ===")
    log_paths = config_mgr.get_all_log_paths()
    for path in log_paths:
        print(f"  {path}")
    
    return len(log_paths) > 0

if __name__ == "__main__":
    success = test_config_reader()
    print(f"\n{'✓' if success else '✗'} Test {'passed' if success else 'failed'}")
