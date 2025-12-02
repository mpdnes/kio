#!/usr/bin/python3
"""
WSGI Configuration for Flask Kiosk Application
This file is used by Apache mod_wsgi to serve the Flask application.
"""

import sys
import os
import logging
from pathlib import Path

# Application directory
APP_DIR = "/var/www/kiosk"
VENV_DIR = os.path.join(APP_DIR, ".kiosk")

# Configure logging for WSGI errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(APP_DIR, 'logs', 'wsgi.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    logger.info("Starting WSGI application initialization...")
    
    # Add project directory to Python path
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)
        logger.info(f"Added {APP_DIR} to Python path")
    
    # Change to project directory
    os.chdir(APP_DIR)
    logger.info(f"Changed working directory to {APP_DIR}")
    
    # Set production environment variables
    os.environ['FLASK_ENV'] = 'production'
    os.environ['DEBUG'] = 'false'
    logger.info("Set production environment variables")
    
    # Try to activate virtual environment - SECURE METHOD
    activate_script = os.path.join(VENV_DIR, 'bin', 'activate_this.py')
    if os.path.exists(activate_script):
        # Security: Validate the activate script path is within expected directory
        activate_realpath = os.path.realpath(activate_script)
        venv_realpath = os.path.realpath(VENV_DIR)
        
        if not activate_realpath.startswith(venv_realpath):
            logger.error(f"Security violation: activate_this.py path traversal detected")
            raise RuntimeError("Virtual environment path validation failed")
        
        # Security: Check file permissions and ownership
        stat_info = os.stat(activate_script)
        if stat_info.st_uid != os.getuid():
            logger.warning(f"Virtual environment script has different owner")
        
        logger.info(f"Safely activating virtual environment: {activate_script}")
        # Use safer exec with restricted globals/locals
        safe_globals = {'__file__': activate_script, '__name__': '__main__'}
        safe_locals = {}
        
        with open(activate_script, 'r') as f:
            activate_code = f.read()
            # Basic validation of activate script content
            if 'import' in activate_code and ('os' in activate_code or 'sys' in activate_code):
                exec(compile(activate_code, activate_script, 'exec'), safe_globals, safe_locals)
            else:
                logger.error("Virtual environment activation script failed validation")
                raise RuntimeError("Virtual environment script validation failed")
    else:
        logger.warning(f"activate_this.py not found at {activate_script}")
        
        # Alternative: Add site-packages to path
        site_packages_paths = [
            os.path.join(VENV_DIR, 'lib', 'python3.12', 'site-packages'),
            os.path.join(VENV_DIR, 'lib', 'python3.11', 'site-packages'),
            os.path.join(VENV_DIR, 'lib', 'python3.10', 'site-packages'),
        ]
        
        for site_packages in site_packages_paths:
            if os.path.exists(site_packages):
                if site_packages not in sys.path:
                    sys.path.insert(0, site_packages)
                    logger.info(f"Added site-packages to path: {site_packages}")
                break
        else:
            logger.warning("No virtual environment site-packages found")
    
    # Import the Flask application
    logger.info("Importing Flask application...")
    from assetbot import assetbot as application
    logger.info("✅ Flask application imported successfully")
    
    # Verify application is callable
    if not callable(application):
        raise RuntimeError("Application is not callable")
    
    logger.info("✅ WSGI application initialized successfully")
    
except Exception as e:
    logger.error(f"❌ WSGI initialization failed: {e}")
    logger.exception("Full traceback:")
    
    # Create a simple error application
    def application(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-type', 'text/html')]
        start_response(status, headers)
        
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Kiosk Application Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
                .error {{ background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #e74c3c; }}
                .error h1 {{ color: #e74c3c; margin: 0 0 10px 0; }}
                .details {{ background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 10px 0; }}
                code {{ background: #f1f2f6; padding: 2px 4px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>🚨 Kiosk Application Startup Error</h1>
                <p>The Flask kiosk application failed to start.</p>
                
                <div class="details">
                    <strong>Error:</strong> <code>Application failed to start</code>
                </div>
                
                <div class="details">
                    <strong>Working Directory:</strong> <code>{os.getcwd()}</code><br>
                    <strong>Python Path:</strong> <code>{':'.join(sys.path[:3])}...</code><br>
                    <strong>App Directory:</strong> <code>{APP_DIR}</code><br>
                    <strong>Virtual Environment:</strong> <code>{VENV_DIR}</code>
                </div>
                
                <h3>Troubleshooting Steps:</h3>
                <ol>
                    <li>Check that all Python files are present in <code>{APP_DIR}</code></li>
                    <li>Verify virtual environment at <code>{VENV_DIR}</code></li>
                    <li>Check Apache error logs: <code>sudo tail -f /var/log/apache2/error.log</code></li>
                    <li>Run diagnostic: <code>cd {APP_DIR} && python3 production_diagnostic.py</code></li>
                    <li>Check file permissions: <code>ls -la {APP_DIR}</code></li>
                </ol>
            </div>
        </body>
        </html>
        """
        return [error_html.encode('utf-8')]

# For standalone testing
if __name__ == "__main__":
    logger.info("Running application in standalone mode")
    application.run(debug=False, host='0.0.0.0', port=8000)
