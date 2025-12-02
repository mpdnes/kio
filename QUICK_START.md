# Quick Start: Getting This Setup Working

## TL;DR - 5 Steps to Running

1. **Install Snipe-IT** (1-2 hours)
   - See `SNIPE_IT_SETUP_GUIDE.md` - Part 1
   - Get your API token

2. **Clone this repo and install dependencies** (10 mins)
   
   **Option A: Python (Standard)**
   ```bash
   git clone <repo>
   cd kiosk
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

   **Option B: NPM (Convenience)**
   ```bash
   git clone <repo>
   cd kiosk
   npm run install-deps  # Installs Python requirements
   ```

3. **Configure `.env`** (5 mins)
   
   **Option A: Setup Wizard (Recommended)**
   ```bash
   npm run setup
   # Follow the interactive prompts to configure API keys and settings
   ```

   **Option B: Manual**
   ```bash
   cp kiosk/.env.template kiosk/.env
   # Edit with your API_URL and API_TOKEN from Snipe-IT
   ```

4. **Start Redis** (2 mins)
   ```bash
   redis-server  # or use Docker
   ```

5. **Run the app** (1 min)
   
   **Option A: Python**
   ```bash
   python kiosk/assetbot.py
   ```

   **Option B: NPM**
   ```bash
   npm start
   ```
   # Visit http://localhost:5000

---

## Overall Setup Assessment

### ✅ What's Already Good

- **Well-documented API integration** - The `snipe_it_api.py` handles all Snipe-IT communication cleanly
- **Security built-in** - Rate limiting, CSRF protection, input validation all enabled
- **Barcode scanning ready** - OpenCV integration for multiple barcode formats
- **Modern tech stack** - Flask, Redis, encryption for sensitive data
- **Comprehensive logging** - Audit trails for security compliance
- **Generic & customizable** - All branding removed, easy to adapt to any organization

### ⚠️ Setup Friction Points for First-Time Users

1. **Multiple configuration files**
   - `.env` template exists but could be clearer
   - Custom field names need manual updating in code
   - No wizard/CLI tool to guide setup

2. **Redis dependency**
   - Required for rate limiting
   - Adds one more service to manage
   - Could be optional in dev mode

3. **Snipe-IT learning curve**
   - Users need to understand Snipe-IT basics first
   - Need to know how to:
     - Create users and assets
     - Generate API tokens
     - Set up custom fields
     - Configure asset statuses

4. **Missing setup wizard**
   - No automated way to:
     - Test Snipe-IT connection
     - Create sample data
     - Verify barcode scanner
     - Set up custom fields

5. **Deployment complexity**
   - Production setup requires HTTPS, web server config, systemd services
   - Multiple deployment options (Apache, Nginx, Docker) - could be overwhelming

### 🎯 Recommendations for Improvement

#### Short Term (Easy wins)

1. **Add setup validation script** - verify all dependencies, connections
   ```bash
   python kiosk/setup_check.py
   ```

2. **Create `.env` helper** - generate secure keys automatically
   ```bash
   python kiosk/generate_env.py
   ```

3. **Add sample Snipe-IT data** - SQL dump with test users/assets

4. **Create demo mode** - run without Redis for development

#### Medium Term

1. **Add web-based setup wizard** - walk through configuration
   - API endpoint verification
   - Custom field mapping UI
   - Test barcode scanner
   - Create sample data

2. **Docker Compose template** - one command to start everything
   ```yaml
   version: '3'
   services:
     kiosk:
       build: .
       ports: ["5000:5000"]
     redis:
       image: redis:latest
   ```

3. **Snipe-IT template** - pre-configured Snipe-IT Docker image
   - With required custom fields
   - Sample asset categories
   - Demo users

#### Long Term

1. **Admin dashboard** - manage configuration without editing `.env`
2. **Health checks UI** - see Snipe-IT API status, Redis status, etc.
3. **One-click deployment** - automated setup scripts for major cloud providers

---

## Current Workflow for New Users

### Getting Started Today

1. **Install Snipe-IT** (follow official docs or Part 1 of `SNIPE_IT_SETUP_GUIDE.md`)
   - ~1-2 hours depending on experience
   - Requires Linux/Windows server
   - Need to understand database setup

2. **Get API token**
   - Log into Snipe-IT
   - Navigate to Admin → API Tokens
   - Create token for kiosk user
   - **SAVE THIS** - you need it

3. **Clone kiosk repo**
   ```bash
   git clone <repo>
   cd kiosk
   ```

4. **Setup Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Run Setup Wizard**
   ```bash
   npm run setup
   # Or manually: python setup.py
   ```
   This will guide you through creating the `.env` file and configuring your Snipe-IT connection.

6. **Install & start Redis**
   ```bash
   # Ubuntu
   sudo apt install redis-server
   sudo systemctl start redis-server
   
   # Or Docker
   docker run -d -p 6379:6379 redis:latest
   ```

7. **Test everything**
   ```bash
   npm start
   # Visit http://localhost:5000
   ```

8. **Deploy to production**
   - Configure HTTPS with Let's Encrypt
   - Set up Apache/Nginx or use Docker
   - Point your kiosk hardware to the URL
   - Ensure barcode scanner works

### Time Estimate

| Step | Time | Notes |
|------|------|-------|
| Install Snipe-IT | 1-2 hrs | Varies by OS/experience |
| Get API token | 5 min | Easy once Snipe-IT is up |
| Clone & setup Python | 10 min | Straightforward |
| Configure `.env` | 5 min | Just edit 3-4 values |
| Install Redis | 5 min | `apt install` or Docker |
| Test locally | 15 min | Verify it works |
| Deploy to prod | 30-60 min | HTTPS + web server config |
| **TOTAL** | **2-3.5 hrs** | For complete first-time setup |

---

## What Works Well for Self-Service

✅ **Easy:** Set up Python app locally and test
✅ **Easy:** Configure barcode scanner (just point and click)
✅ **Easy:** Create users and assets in Snipe-IT UI
✅ **Easy:** Scale to multiple kiosks (just clone the app)
✅ **Easy:** Monitor logs and user activity

❌ **Hard:** Installing Snipe-IT from scratch (learning curve)
❌ **Hard:** Understanding Snipe-IT API/permissions
❌ **Hard:** Setting up HTTPS certificates
❌ **Hard:** Configuring web server (Apache/Nginx)

---

## Setup Wizard

We have included a setup wizard to make configuration easier.

1. **Validates environment**
   - Checks for required files

2. **Configures connection**
   - Prompts for API URL and Token
   - Generates secure keys

To run it:
```bash
npm run setup
```

---

## Bottom Line

For someone willing to spend 2-3 hours on setup, this is a **solid, production-ready solution**. The biggest time investment is Snipe-IT itself, not the kiosk.

Use the setup wizard (`npm run setup`) to reduce configuration errors.
