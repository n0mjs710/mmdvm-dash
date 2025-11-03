#!/usr/bin/env python3
"""
Test script to verify config_reader can parse INI files
"""
import sys
from dashboard.config_reader import initialize_config_manager

def test_config_reader(mmdvm_ini=None, dmr_ini=None, ysf_ini=None, p25_ini=None):
    """Test reading configuration from INI files"""
    
    # Use provided paths or defaults
    mmdvm_path = mmdvm_ini or "/etc/MMDVM.ini"
    dmr_path = dmr_ini or "/etc/DMRGateway.ini"
    ysf_path = ysf_ini or "/etc/YSFGateway.ini"
    p25_path = p25_ini or "/etc/P25Gateway.ini"
    
    print(f"Testing config_reader with:")
    print(f"  MMDVM: {mmdvm_path}")
    print(f"  DMR Gateway: {dmr_path}")
    print(f"  YSF Gateway: {ysf_path}")
    print(f"  P25 Gateway: {p25_path}")
    
    config_mgr = initialize_config_manager(
        mmdvm_ini=mmdvm_path,
        dmr_gateway_ini=dmr_path,
        ysf_gateway_ini=ysf_path,
        p25_gateway_ini=p25_path
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
    # Parse command line arguments
    if len(sys.argv) == 5:
        success = test_config_reader(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Usage: test_config_reader.py <mmdvm.ini> <dmr_gateway.ini> <ysf_gateway.ini> <p25_gateway.ini>")
        print("Using default paths...")
        success = test_config_reader()
    print(f"\n{'✓' if success else '✗'} Test {'passed' if success else 'failed'}")
