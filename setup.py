#!/usr/bin/env python3
"""
Quick setup helper - runs the setup wizard

Usage:
    python setup.py              # Interactive setup wizard
    python setup.py --skip-tests # Skip test phase
    python setup.py --check-only # Only check environment
"""

import sys
import os
from pathlib import Path

# Add kiosk directory to path
kiosk_dir = Path(__file__).parent / 'kiosk'
sys.path.insert(0, str(kiosk_dir))

# Parse arguments
args = sys.argv[1:] if len(sys.argv) > 1 else []

if '--help' in args or '-h' in args:
    print(__doc__)
    sys.exit(0)

# Run setup wizard
try:
    from setup_wizard import SetupWizard
    
    wizard = SetupWizard()
    wizard.run()
    
except ImportError as e:
    print(f"Error: Could not import setup wizard: {e}")
    print("Make sure you're running from the kiosk directory")
    sys.exit(1)
except KeyboardInterrupt:
    print("\nSetup cancelled")
    sys.exit(0)
