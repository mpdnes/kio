#!/usr/bin/env python3
"""
Production Server Startup Script
RIT Kiosk Application - HARDENED SECURITY EDITION

This script ensures all security measures are properly configured
before starting the production server.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/production_startup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_redis():
    """Check if Redis is running"""
    try:
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'PONG' in result.stdout:
            logger.info("✅ Redis server is running")
            return True
        else:
            logger.error("❌ Redis server is not responding")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to check Redis: {e}")
        return False

def check_environment():
    """Check required environment variables"""
    required_vars = [
        'SECRET_KEY',
        'REDIS_URL', 
        'API_URL',
        'API_TOKEN'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    logger.info("✅ All required environment variables present")
    return True

def check_file_permissions():
    """Check critical file permissions"""
    checks = [
        ('loan_agreements/signatures/', '750'),
        ('logs/', '755'),
        ('.env', '600')
    ]
    
    for path, expected_perm in checks:
        if os.path.exists(path):
            stat = os.stat(path)
            actual_perm = oct(stat.st_mode)[-3:]
            if actual_perm == expected_perm:
                logger.info(f"✅ {path}: Permissions {actual_perm}")
            else:
                logger.warning(f"⚠️  {path}: Expected {expected_perm}, got {actual_perm}")
        else:
            logger.warning(f"⚠️  {path}: Does not exist")

def run_security_tests():
    """Run basic security validation"""
    logger.info("🔒 Running security validation...")
    
    try:
        # Import and test basic app functionality
        from assetbot import assetbot
        
        # Test configuration
        if assetbot.config.get('DEBUG'):
            logger.error("❌ DEBUG mode is enabled - SECURITY RISK")
            return False
            
        if not assetbot.config.get('SESSION_COOKIE_SECURE'):
            logger.error("❌ SESSION_COOKIE_SECURE is disabled - SECURITY RISK") 
            return False
            
        # Test basic route
        with assetbot.test_client() as client:
            response = client.get('/')
            if response.status_code in [200, 302]:
                logger.info("✅ Landing page renders correctly")
            else:
                logger.error(f"❌ Landing page failed: {response.status_code}")
                return False
                
        logger.info("✅ Security validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Security validation failed: {e}")
        return False

def start_production_server():
    """Start the production server with security checks"""
    logger.info("🚀 STARTING RIT KIOSK - PRODUCTION MODE")
    logger.info("=" * 50)
    
    # Pre-flight security checks
    checks = [
        ("Environment Variables", check_environment),
        ("Redis Server", check_redis), 
        ("File Permissions", lambda: (check_file_permissions(), True)[1]),
        ("Security Validation", run_security_tests)
    ]
    
    for check_name, check_func in checks:
        logger.info(f"Checking {check_name}...")
        if not check_func():
            logger.error(f"❌ {check_name} failed - ABORTING STARTUP")
            return False
    
    logger.info("✅ All security checks passed")
    logger.info("🔐 Starting hardened production server...")
    
    # Set production environment
    os.environ['FLASK_ENV'] = 'production'
    os.environ['DEBUG'] = 'False'
    
    try:
        from assetbot import assetbot
        
        # Start with production settings
        assetbot.run(
            host='0.0.0.0',
            port=8443,
            debug=False,
            threaded=True,
            ssl_context='adhoc' if os.getenv('USE_SSL', 'false').lower() == 'true' else None
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Server shutdown requested")
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    success = start_production_server()
    sys.exit(0 if success else 1)