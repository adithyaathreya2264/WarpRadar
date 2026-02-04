"""Debug launcher for WarpRadar - captures full error information."""

import sys
import traceback
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('warpradar_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('WarpRadar')

try:
    logger.info("Starting WarpRadar...")
    
    from warpradar.app import WarpRadarApp
    logger.info("✓ App imported successfully")
    
    app = WarpRadarApp()
    logger.info("✓ App instance created")
    
    logger.info("Running app...")
    app.run()
    
except Exception as e:
    logger.error(f"Application failed: {e}")
    logger.error("Full traceback:")
    traceback.print_exc()
    
    # Print specific socket error info
    if "socket" in str(e).lower() or "bind" in str(e).lower():
        logger.error("\n⚠️  SOCKET BINDING ERROR DETECTED")
        logger.error("Possible causes:")
        logger.error("1. Port 5555 (UDP) or 5556 (TCP) already in use")
        logger.error("2. Windows firewall blocking multicast")
        logger.error("3. Insufficient permissions")
        logger.error("\nTry running as Administrator or check if ports are in use:")
        logger.error("  netstat -ano | findstr ':5555'")
        logger.error("  netstat -ano | findstr ':5556'")
    
    sys.exit(1)
