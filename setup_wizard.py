#!/usr/bin/env python3
"""
Equipment Kiosk Setup Wizard

Comprehensive setup validation and configuration for first-time deployment.
Handles: environment validation, Snipe-IT connection, custom field mapping, test data.
"""

import os
import sys
import json
import hashlib
import secrets
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import platform

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"{text.center(60)}")
    print(f"{'='*60}{Colors.ENDC}\n")


def print_step(step_num: int, text: str):
    """Print a step header"""
    print(f"{Colors.BOLD}{Colors.OKBLUE}Step {step_num}: {text}{Colors.ENDC}")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def prompt_input(question: str, default: Optional[str] = None) -> str:
    """Prompt user for input with optional default"""
    if default:
        prompt_text = f"{Colors.BOLD}{question} [{default}]: {Colors.ENDC}"
    else:
        prompt_text = f"{Colors.BOLD}{question}: {Colors.ENDC}"
    
    response = input(prompt_text).strip()
    return response if response else (default or "")


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt yes/no question"""
    default_text = "Y/n" if default else "y/N"
    response = prompt_input(f"{question} [{default_text}]").lower()
    if response in ('y', 'yes'):
        return True
    elif response in ('n', 'no'):
        return False
    else:
        return default


class SetupWizard:
    """Main setup wizard orchestrator"""
    
    def __init__(self):
        self.kiosk_root = Path(__file__).parent.parent
        self.kiosk_app = Path(__file__).parent
        self.env_file = self.kiosk_root / '.env'
        self.env_template = self.kiosk_root / '.env.template'
        self.config = {}
        self.results = {
            'environment': {},
            'snipe_it': {},
            'custom_fields': {},
            'tests': {}
        }
    
    def run(self):
        """Execute the complete setup wizard"""
        print_header("EQUIPMENT KIOSK SETUP WIZARD")
        print_info("This wizard will help you set up the Equipment Management Kiosk")
        print_info(f"Project root: {self.kiosk_root}\n")
        
        try:
            self.step_1_environment_check()
            self.step_2_snipe_it_connection()
            self.step_3_custom_fields()
            self.step_4_configuration()
            self.step_5_test_setup()
            self.step_6_summary()
        except KeyboardInterrupt:
            print_warning("\nSetup cancelled by user")
            sys.exit(0)
        except Exception as e:
            print_error(f"Setup failed: {e}")
            sys.exit(1)
    
    def step_1_environment_check(self):
        """Check system environment and dependencies"""
        print_step(1, "Environment Check")
        
        # Check Python version
        version_info = sys.version_info
        python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        print(f"Python version: {python_version}")
        
        if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 8):
            print_error(f"Python 3.8+ required (you have {python_version})")
            sys.exit(1)
        print_success(f"Python {python_version} is compatible")
        
        # Check OS
        os_name = platform.system()
        print(f"Operating System: {os_name}")
        print_success(f"Running on {os_name}")
        
        # Check required files
        print("\nChecking required files...")
        required_files = [
            ('kiosk/config.py', 'Configuration module'),
            ('kiosk/utils/snipe_it_api.py', 'Snipe-IT API client'),
            ('kiosk/assetbot.py', 'Main Flask app'),
            ('requirements.txt', 'Dependencies list'),
        ]
        
        for file_path, description in required_files:
            full_path = self.kiosk_root / file_path
            if full_path.exists():
                print_success(f"{description}: {file_path}")
            else:
                print_error(f"Missing {description}: {file_path}")
                sys.exit(1)
        
        # Check Python dependencies
        print("\nChecking Python dependencies...")
        self._check_dependencies()
        
        self.results['environment']['python_version'] = python_version
        self.results['environment']['os'] = os_name
    
    def _check_dependencies(self):
        """Check if required Python packages are installed"""
        required_packages = [
            'flask',
            'requests',
            'redis',
            'cryptography',
            'pillow',
            'pyzbar',
            'cv2',
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package if package != 'cv2' else 'cv2')
                print_success(f"✓ {package}")
            except ImportError:
                print_warning(f"✗ {package} (not installed)")
                missing_packages.append(package)
        
        if missing_packages:
            print_warning(f"\nMissing packages: {', '.join(missing_packages)}")
            if prompt_yes_no("Install missing packages now?"):
                self._install_packages(missing_packages)
            else:
                print_warning("Skipping package installation. Run: pip install -r requirements.txt")
        
        self.results['environment']['dependencies'] = {
            'all_installed': len(missing_packages) == 0,
            'missing': missing_packages
        }
    
    def _install_packages(self, packages: List[str]):
        """Install missing packages"""
        try:
            print("\nInstalling packages...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + packages)
            print_success("Packages installed successfully")
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to install packages: {e}")
            print_warning("Continue setup anyway? (not recommended)")
            if not prompt_yes_no("Continue?"):
                sys.exit(1)
    
    def step_2_snipe_it_connection(self):
        """Configure and test Snipe-IT connection"""
        print_step(2, "Snipe-IT Connection")
        
        print_info("You need a Snipe-IT API token to proceed")
        print_info("Get it from: Admin → API Tokens in your Snipe-IT instance\n")
        
        api_url = prompt_input("Snipe-IT API URL", "http://localhost/api/v1")
        api_token = prompt_input("Snipe-IT API Token")
        
        if not api_url or not api_token:
            print_error("API URL and token are required")
            if not prompt_yes_no("Skip this step and continue?"):
                sys.exit(1)
            self.results['snipe_it']['skipped'] = True
            return
        
        # Test connection
        print("\nTesting Snipe-IT connection...")
        if self._test_snipe_it_connection(api_url, api_token):
            print_success("Snipe-IT connection successful!")
            self.config['API_URL'] = api_url
            self.config['API_TOKEN'] = api_token
            self.results['snipe_it']['connected'] = True
            self.results['snipe_it']['url'] = api_url
        else:
            print_error("Failed to connect to Snipe-IT")
            print_warning("Check your URL and token, then try again")
            if not prompt_yes_no("Continue anyway?"):
                sys.exit(1)
            self.results['snipe_it']['connected'] = False
    
    def _test_snipe_it_connection(self, api_url: str, api_token: str) -> bool:
        """Test Snipe-IT API connection"""
        try:
            import requests
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Accept': 'application/json',
            }
            # Try to get assets (basic test)
            response = requests.get(
                f"{api_url.rstrip('/')}/assets?limit=1",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print_warning(f"Connection test failed: {e}")
            return False
    
    def step_3_custom_fields(self):
        """Configure custom field mapping"""
        print_step(3, "Custom Field Mapping")
        
        if not self.results['snipe_it'].get('connected'):
            print_warning("Skipping (Snipe-IT not connected)")
            return
        
        print_info("The kiosk uses custom Snipe-IT fields for inventory numbers")
        print_info("Common field names: 'Inventory Number', 'Asset ID', 'Device ID'\n")
        
        inventory_fields_str = prompt_input(
            "Custom inventory field names (comma-separated)",
            "Inventory Number"
        )
        
        inventory_fields = [f.strip() for f in inventory_fields_str.split(',')]
        self.config['INVENTORY_FIELDS'] = ','.join(inventory_fields)
        
        print_success(f"Custom fields configured: {inventory_fields}")
        
        # Test field access
        if prompt_yes_no("\nTest field access in Snipe-IT?"):
            self._test_custom_fields(inventory_fields)
        
        self.results['custom_fields']['fields'] = inventory_fields
    
    def _test_custom_fields(self, field_names: List[str]):
        """Test if custom fields exist in Snipe-IT"""
        print("\nThis would fetch custom fields from Snipe-IT...")
        print_info("(Custom field validation requires additional implementation)")
    
    def step_4_configuration(self):
        """Generate .env configuration file"""
        print_step(4, "Configuration")
        
        # Generate secure keys
        print("Generating secure configuration...")
        
        secret_key = secrets.token_hex(32)
        
        # Get other settings
        print("\nOptional settings:")
        
        redis_url = prompt_input(
            "Redis URL",
            "redis://localhost:6379/0"
        )
        
        flask_env = prompt_input(
            "Flask environment (development/production)",
            "production"
        )
        
        debug_mode = prompt_yes_no("Enable debug mode?", False)
        
        self.config.update({
            'SECRET_KEY': secret_key,
            'REDIS_URL': redis_url,
            'FLASK_ENV': flask_env,
            'DEBUG': 'True' if debug_mode else 'False',
        })
        
        # Write .env file
        if self._write_env_file():
            print_success(".env file created successfully")
            self.results['configuration']['env_file_created'] = True
        else:
            print_error("Failed to create .env file")
            self.results['configuration']['env_file_created'] = False
    
    def _write_env_file(self) -> bool:
        """Write configuration to .env file"""
        try:
            env_content = "# Equipment Kiosk Configuration\n"
            env_content += "# Generated by setup wizard\n"
            env_content += "# IMPORTANT: Keep this file secure and never commit to git\n\n"
            
            for key, value in self.config.items():
                env_content += f"{key}={value}\n"
            
            # Write to file
            with open(self.env_file, 'w') as f:
                f.write(env_content)
            
            # Verify
            return self.env_file.exists()
        except Exception as e:
            print_error(f"Failed to write .env file: {e}")
            return False
    
    def step_5_test_setup(self):
        """Run basic functionality tests"""
        print_step(5, "Test Setup")
        
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Import main app
        print("\nTest 1: Import Flask app...")
        tests_total += 1
        try:
            sys.path.insert(0, str(self.kiosk_app))
            from assetbot import assetbot as app
            print_success("Flask app imported successfully")
            tests_passed += 1
        except Exception as e:
            print_error(f"Failed to import Flask app: {e}")
        
        # Test 2: Config loading
        print("\nTest 2: Load configuration...")
        tests_total += 1
        try:
            if self.env_file.exists():
                print_success(".env file exists and is readable")
                tests_passed += 1
            else:
                print_warning(".env file not found (create it in step 4)")
        except Exception as e:
            print_error(f"Failed to load config: {e}")
        
        # Test 3: Redis connection (if available)
        print("\nTest 3: Test Redis connection...")
        tests_total += 1
        if self._test_redis_connection(self.config.get('REDIS_URL', 'redis://localhost:6379/0')):
            print_success("Redis connection successful")
            tests_passed += 1
        else:
            print_warning("Redis not available (you may need to start it)")
        
        self.results['tests']['passed'] = tests_passed
        self.results['tests']['total'] = tests_total
    
    def _test_redis_connection(self, redis_url: str) -> bool:
        """Test Redis connectivity"""
        try:
            import redis
            r = redis.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            return True
        except Exception:
            return False
    
    def step_6_summary(self):
        """Display summary and next steps"""
        print_step(6, "Summary")
        
        print_header("SETUP SUMMARY")
        
        print(f"{Colors.BOLD}Environment:{Colors.ENDC}")
        print(f"  Python: {self.results['environment'].get('python_version', 'N/A')}")
        print(f"  OS: {self.results['environment'].get('os', 'N/A')}")
        
        if self.results['snipe_it'].get('connected'):
            print(f"\n{Colors.BOLD}Snipe-IT:{Colors.ENDC}")
            print(f"  Status: {Colors.OKGREEN}Connected{Colors.ENDC}")
            print(f"  URL: {self.results['snipe_it'].get('url', 'N/A')}")
        else:
            print(f"\n{Colors.BOLD}Snipe-IT:{Colors.ENDC}")
            print(f"  Status: {Colors.WARNING}Not configured{Colors.ENDC}")
        
        if self.results.get('custom_fields', {}).get('fields'):
            print(f"\n{Colors.BOLD}Custom Fields:{Colors.ENDC}")
            for field in self.results['custom_fields']['fields']:
                print(f"  - {field}")
        
        print(f"\n{Colors.BOLD}Tests:{Colors.ENDC}")
        tests_passed = self.results['tests'].get('passed', 0)
        tests_total = self.results['tests'].get('total', 0)
        status = Colors.OKGREEN if tests_passed == tests_total else Colors.WARNING
        print(f"  {status}{tests_passed}/{tests_total} tests passed{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}Configuration file:{Colors.ENDC}")
        if self.results.get('configuration', {}).get('env_file_created'):
            print(f"  {Colors.OKGREEN}✓ .env created{Colors.ENDC}")
        else:
            print(f"  {Colors.WARNING}✗ .env not created{Colors.ENDC}")
        
        print_header("NEXT STEPS")
        
        print("1. Review .env file:")
        print(f"   {self.env_file}\n")
        
        print("2. Start Redis (if not already running):")
        print("   redis-server\n")
        
        print("3. Run the kiosk:")
        print("   python kiosk/assetbot.py\n")
        
        print("4. Visit in browser:")
        print("   http://localhost:5000\n")
        
        print("5. Test barcode scanner:")
        print("   Click 'Scan Asset' and scan a barcode\n")
        
        print_success("Setup wizard completed!")
        print_info("For more details, see SNIPE_IT_SETUP_GUIDE.md and QUICK_START.md")


def main():
    """Entry point"""
    wizard = SetupWizard()
    wizard.run()


if __name__ == '__main__':
    main()
