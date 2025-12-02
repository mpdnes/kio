# Setup Wizard Guide

The **Setup Wizard** automates the first-time configuration of the Equipment Kiosk, eliminating manual `.env` editing and dependency checking.

## Quick Start

```bash
# From the root directory:
python setup.py
```

That's it. The wizard will:
1. ✓ Check Python version and OS compatibility
2. ✓ Validate all required files exist
3. ✓ Verify/install Python dependencies
4. ✓ Test Snipe-IT connection
5. ✓ Configure custom fields
6. ✓ Generate secure `.env` file
7. ✓ Run basic tests
8. ✓ Show next steps

## What It Does

### Step 1: Environment Check
- Verifies Python 3.8+ is installed
- Checks for required project files
- Validates Python dependencies
- Installs missing packages (if you approve)

### Step 2: Snipe-IT Connection
- Prompts for API URL and token
- Tests connection to your Snipe-IT instance
- Verifies API access

### Step 3: Custom Field Mapping
- Asks for your custom field names
- Maps kiosk to your Snipe-IT fields
- (Optionally) validates fields exist in Snipe-IT

### Step 4: Configuration
- Generates secure `SECRET_KEY`
- Prompts for Redis URL, Flask environment, debug mode
- Creates `.env` file with all settings

### Step 5: Test Setup
- Imports Flask app
- Validates `.env` loading
- Tests Redis connection
- Reports test results

### Step 6: Summary
- Shows what was configured
- Lists next steps
- Displays startup commands

## Usage Examples

### Typical First-Time Setup
```bash
python setup.py
# Follow the prompts, answer questions
```

### Just Check Environment
```bash
python setup.py --check-only
# Validates Python, files, dependencies without making changes
```

### Skip Tests
```bash
python setup.py --skip-tests
# Faster setup, skips Step 5 testing
```

### Run Wizard Multiple Times
```bash
python setup.py
# You can safely re-run - it will ask before overwriting .env
```

## Requirements for Wizard

### Before Running

1. **Snipe-IT instance running** (local or remote)
   - You need the API URL (e.g., `https://snipeit.company.com/api/v1`)
   - You need an API token (Admin → API Tokens)

2. **Redis running** (optional, but recommended)
   - Wizard tests for it but doesn't require it
   - You can start it later manually

### Python Version
- Python 3.8 or higher
- Check with: `python --version`

## What the Wizard Creates

### `.env` File
Located at the root directory: `kiosk/.env`

Contains:
- `API_URL` - Your Snipe-IT API endpoint
- `API_TOKEN` - Your Snipe-IT API token (keep this SECRET!)
- `SECRET_KEY` - Secure random key for Flask sessions
- `REDIS_URL` - Connection string for Redis
- `FLASK_ENV` - Environment mode (development/production)
- `DEBUG` - Debug mode (True/False)
- Custom field names

**IMPORTANT:** Never commit `.env` to git. Add it to `.gitignore`:
```
.env
*.env
```

## Common Issues & Solutions

### "Python 3.8+ required"
Update Python:
- Windows: Download from python.org
- Mac: `brew install python@3.11`
- Linux: `sudo apt update && sudo apt install python3.11`

### "Failed to install packages"
Install manually:
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### "Snipe-IT connection failed"
1. Verify Snipe-IT is running (`https://your-snipeit-url`)
2. Check API URL format (should end with `/api/v1`)
3. Verify API token is correct (Admin → API Tokens)
4. Check firewall/network connectivity

### "Redis not available"
This is optional for testing but required for production:
```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis-server

# Mac
brew install redis
redis-server

# Docker
docker run -d -p 6379:6379 redis:latest
```

### ".env file already exists"
The wizard will ask if you want to overwrite it. Choose:
- **Yes** - Replace with new configuration
- **No** - Keep existing and exit

## Next Steps After Setup

1. **Start the app:**
   ```bash
   python kiosk/assetbot.py
   ```

2. **Visit http://localhost:5000**
   - Log in with your Snipe-IT user credentials
   - Test the barcode scanner
   - Test checkout/checkin

3. **Create test data** (if needed):
   - Add assets to Snipe-IT
   - Create test users
   - Assign assets to categories

4. **Configure for production:**
   - Set `FLASK_ENV=production`
   - Configure HTTPS
   - Set up web server (Apache/Nginx)
   - See SNIPE_IT_SETUP_GUIDE.md for details

## Advanced Options

### Programmatic Setup (for automation)

Create a script that sets environment variables before running:

```bash
export API_URL="https://snipeit.mycompany.com/api/v1"
export API_TOKEN="your_token_here"
export REDIS_URL="redis://localhost:6379/0"

python setup.py
```

The wizard will use these as defaults.

### Custom Environment File

If you want to use a different environment file name:

```python
# In kiosk/setup_wizard.py, modify SetupWizard.__init__()
self.env_file = Path(__file__).parent.parent / '.env.production'
```

### Validate Existing Setup

To check if your current setup is valid:

```python
from kiosk.setup_wizard import SetupWizard

wizard = SetupWizard()
wizard.step_1_environment_check()
wizard.step_5_test_setup()
```

## Troubleshooting

### Wizard hangs on "Installing packages"
- Press Ctrl+C to cancel
- Install manually: `pip install -r requirements.txt`
- Re-run wizard: `python setup.py`

### `.env` file is empty
- Check file permissions (must be writable)
- Ensure wizard completed all steps
- Verify directory is writable: `ls -la`

### "Cannot find setup_wizard module"
- Make sure you're running from the root directory
- Verify `kiosk/setup_wizard.py` exists
- Try: `python -m kiosk.setup_wizard`

## Architecture

The wizard is built as a single comprehensive Python script (`kiosk/setup_wizard.py`) with:

- **SetupWizard** class - Main orchestrator
- **Helper functions** - Input prompts, output formatting
- **Test methods** - Connection and dependency validation
- **Color output** - Terminal-friendly formatting

No external dependencies beyond what's already required (requests, redis).

## Testing the Wizard

To test the wizard yourself:

```bash
# Test environment checking
python -c "from kiosk.setup_wizard import SetupWizard; w = SetupWizard(); w.step_1_environment_check()"

# Test Snipe-IT connection
python -c "from kiosk.setup_wizard import SetupWizard; w = SetupWizard(); w._test_snipe_it_connection('http://localhost/api/v1', 'token')"
```

## Contributing Improvements

Possible enhancements to the wizard:

- [ ] Web-based setup UI (Flask route)
- [ ] Headless mode for CI/CD pipelines
- [ ] Backup/restore configuration
- [ ] Multi-instance support
- [ ] Configuration validation before writing
- [ ] Docker Compose generation
- [ ] Sample data import

## Support

For issues with the setup wizard:
1. See QUICK_START.md for general setup
2. See SNIPE_IT_SETUP_GUIDE.md for detailed Snipe-IT setup
3. Check TROUBLESHOOTING.md for common issues
4. Review the wizard output messages - they often suggest solutions
