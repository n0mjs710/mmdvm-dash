"""
MMDVM Dashboard - Main Entry Point
FastAPI server for monitoring MMDVMHost and gateway programs via log file parsing
"""
import asyncio
import logging
import glob
from pathlib import Path
from dashboard.server import app
from dashboard.config import config
from dashboard.config_reader import initialize_config_manager
from dashboard.monitor import monitor_manager

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def start_monitors():
    """Initialize and start log monitors from INI file configuration"""
    # Get INI file paths from config.json
    config_paths = config.get('config_paths', default={})
    
    mmdvm_ini = config_paths.get('mmdvm_ini', '/etc/MMDVM.ini')
    dmr_gateway_ini = config_paths.get('dmr_gateway_ini', '/etc/DMRGateway.ini')
    ysf_gateway_ini = config_paths.get('ysf_gateway_ini', '/etc/YSFGateway.ini')
    p25_gateway_ini = config_paths.get('p25_gateway_ini', '/etc/P25Gateway.ini')
    nxdn_gateway_ini = config_paths.get('nxdn_gateway_ini')
    
    # Initialize config manager to read INI files
    logger.info("Reading configuration from INI files...")
    config_mgr = initialize_config_manager(
        mmdvm_ini=mmdvm_ini,
        dmr_gateway_ini=dmr_gateway_ini,
        ysf_gateway_ini=ysf_gateway_ini,
        p25_gateway_ini=p25_gateway_ini,
        nxdn_gateway_ini=nxdn_gateway_ini
    )
    
    # Get expected state and update dashboard state
    expected_state = config_mgr.get_expected_state()
    from dashboard.state import state
    state.update_expected_state(expected_state)
    logger.info(f"System state updated: MMDVMHost running={expected_state.get('mmdvm_running')}")
    
    # Get all log paths from INI files
    log_paths = config_mgr.get_all_log_paths()
    
    if not log_paths:
        logger.warning("No log files configured in INI files")
        return
    
    # Add monitors for each log file pattern
    for log_pattern in log_paths:
        log_dir = log_pattern.parent
        pattern = log_pattern.name
        
        # Find actual log files matching pattern
        if log_dir.exists():
            matching_files = glob.glob(str(log_pattern))
            
            if matching_files:
                # Monitor the most recent log file
                latest_log = sorted(matching_files)[-1]
                source_name = log_pattern.stem.split('-')[0]  # e.g., "MMDVM" from "MMDVM-*.log"
                
                # Map log file names to parser types
                parser_map = {
                    'MMDVM': 'mmdvmhost',
                    'mmdvm': 'mmdvmhost',
                    'DMRGateway': 'dmrgateway',
                    'YSFGateway': 'ysfgateway',
                    'P25Gateway': 'p25gateway',
                    'NXDNGateway': 'nxdngateway'
                }
                parser_type = parser_map.get(source_name, source_name.lower())
                
                logger.info(f"Monitoring {latest_log} as {source_name} (parser: {parser_type})")
                monitor_manager.add_monitor(source_name, latest_log, parser_type)
            else:
                logger.warning(f"No log files found matching {log_pattern}")
        else:
            logger.warning(f"Log directory does not exist: {log_dir}")
    
    # Start all monitors
    await monitor_manager.start_all()
    logger.info(f"Started {len(monitor_manager.monitors)} log monitors")
    
    # Return config_mgr for use in background task
    return config_mgr


async def update_process_status(config_mgr):
    """Periodically check if processes are still running"""
    from dashboard.state import state
    
    while True:
        try:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            # Get fresh process status
            expected_state = config_mgr.get_expected_state()
            state.update_expected_state(expected_state)
            
        except Exception as e:
            logger.error(f"Error updating process status: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting MMDVM Dashboard...")
    logger.info(f"Config paths: {config.get('config_paths')}")
    
    # Create uvicorn config
    uvicorn_config = uvicorn.Config(
        app,
        host=config.get('dashboard', 'host', default='0.0.0.0'),
        port=config.get('dashboard', 'port', default=8080),
        log_level="info"
    )
    server = uvicorn.Server(uvicorn_config)
    
    # Run with startup tasks
    async def main():
        # Start log monitors and get config manager
        config_mgr = await start_monitors()
        
        # Start background task to update process status
        asyncio.create_task(update_process_status(config_mgr))
        
        # Run server
        await server.serve()
    
    asyncio.run(main())
