# Complete Snipe-IT + Kiosk Setup Guide

This guide walks you through setting up Snipe-IT from scratch and then integrating this kiosk application.

## Part 1: Snipe-IT Setup

### Prerequisites
- Server with Linux/Windows (Ubuntu 20.04 LTS recommended)
- Minimum 2GB RAM, 20GB storage
- MySQL/MariaDB database
- Web server (Apache/nginx)
- PHP 8.0+

### Installation Steps

#### 1. Install Snipe-IT from scratch

Follow the official installation guide: https://snipe-it.readme.io/docs/installation

Quick start for Ubuntu:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y apache2 php php-mysql php-cli php-ldap php-zip \
  php-curl php-gd php-mbstring php-xml php-fpm curl git mysql-server

# Clone Snipe-IT
cd /var/www
sudo git clone https://github.com/snipe/snipe-it.git
cd snipe-it
sudo chown -R www-data:www-data .
sudo chmod -R 755 .

# Install PHP dependencies
curl -sS https://getcomposer.org/installer | sudo php -- --install-dir=/usr/local/bin --filename=composer
sudo -u www-data composer install --prefer-dist --no-dev
```

#### 2. Configure Your Snipe-IT Instance

1. **Create `.env` file:**
   ```bash
   cp .env.example .env
   sudo nano .env
   ```

2. **Key settings to configure:**
   - `APP_URL=https://your-domain.com` (your server URL)
   - `APP_KEY=` (generated during installation)
   - `DB_HOST=localhost`
   - `DB_DATABASE=snipeit`
   - `DB_USERNAME=snipeit_user`
   - `DB_PASSWORD=strong_password`

3. **Run migrations:**
   ```bash
   sudo -u www-data php artisan migrate
   sudo -u www-data php artisan db:seed
   ```

4. **Configure Apache/nginx to serve Snipe-IT**

#### 3. Create Admin User & API Token

1. Access your Snipe-IT at `https://your-domain.com`
2. Complete the setup wizard
3. Create an admin account
4. Login and go to **Admin Settings → API → API Tokens**
5. Create a new API token - **save this for the kiosk configuration**

#### 4. Set Up Snipe-IT for the Kiosk

**Create User Account for Kiosk:**
1. Go to **Admin → Users**
2. Create a user account (e.g., `kiosk_admin`)
3. Assign appropriate permissions for asset checkout/checkin
4. Generate API token for this user

**Create Custom Fields (Optional but Recommended):**
1. Go to **Admin → Custom Fields**
2. Create field: `Inventory Number` (for tracking equipment)
   - Type: Text
   - Show in list: Yes
3. Create field: `Equipment Category`
   - Type: Text
   - Show in list: Yes

**Configure Asset Categories & Status:**
1. Go to **Admin → Asset Statuses** - ensure you have "Available" and "Checked Out" statuses
2. Go to **Admin → Asset Models** - create models for your equipment
3. Go to **Admin → Assets** - start adding your equipment inventory

**Import Sample Data (Optional):**
```bash
# The database comes with some sample assets you can use to test
# Or manually add assets through the web interface
```

---

## Part 2: Kiosk Setup

### Prerequisites
- Python 3.10+
- Redis server (for rate limiting)
- Access to your Snipe-IT API

### Installation

#### 1. Clone and Setup
```bash
# Clone this repository
git clone https://github.com/your-repo/kiosk.git
cd kiosk

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment

```bash
# Copy template
cp kiosk/.env.template kiosk/.env

# Edit configuration
nano kiosk/.env
```

**Required settings:**
```dotenv
FLASK_ENV=production
DEBUG=False

# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your_generated_secret_key_here

# Your Snipe-IT server details
API_URL=https://your-snipe-it-server.com/api/v1
API_TOKEN=your_kiosk_api_token_from_snipe_it

# Redis for rate limiting (local or remote)
REDIS_URL=redis://localhost:6379/0

# Security
SESSION_COOKIE_SECURE=True
VERIFY_SSL=True

# Optional: Your organization name for customization
ORGANIZATION_NAME=Your Organization
```

#### 3. Set Up Redis

```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

#### 4. Initialize Database & Test

```bash
# Run production startup checks
python kiosk/start_production.py

# Test the application
python kiosk/assetbot.py
# Visit: http://localhost:5000
```

#### 6. Configure Custom Fields in Code

Edit `kiosk/utils/snipe_it_api.py` around line 47:

```python
inventory_fields = [
    'Inventory Number',  # Update to your Snipe-IT custom field name
    'inventory_number', 
    'item_number'
]
```

Do the same in `kiosk/blueprints/assets.py` around line 318.

#### 7. Add Your Logo

Replace `kiosk/static/images/logo.png` with your organization's logo (recommended: 512x512 PNG)

---

## Part 3: Testing the Integration

### Test Barcode Authentication

1. In Snipe-IT, go to **Admin → Users**
2. Find a user and note their employee number
3. In the kiosk, try signing in with this number
4. You should see the user's dashboard

### Test Asset Checkout

1. Go to **Checkout** in the kiosk
2. Scan or enter an asset barcode
3. Verify the asset details appear correctly
4. Complete the checkout
5. Check Snipe-IT to confirm the assignment

### Test Admin Functions

1. Go to **Admin → Add User** with a VIP account
2. Create a new test user
3. Verify it appears in Snipe-IT

---

## Part 4: Production Deployment

### Choose Your Deployment Method

#### Option A: Apache + mod_wsgi (Recommended for Linux)
```bash
# Install mod_wsgi
sudo apt install libapache2-mod-wsgi-py3

# Configure Apache virtual host with WSGIScriptAlias
```

#### Option B: Nginx + Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Create systemd service file
sudo nano /etc/systemd/system/kiosk.service

# Configure gunicorn to run on port 5000+
# Use nginx as reverse proxy
```

#### Option C: Docker (Easiest)
```bash
# Build Docker image from Dockerfile
docker build -t equipment-kiosk .

# Run container
docker run -p 80:5000 \
  -e FLASK_ENV=production \
  -e API_URL=https://your-snipe-it-server/api/v1 \
  -e API_TOKEN=your_token \
  -e REDIS_URL=redis://redis:6379/0 \
  equipment-kiosk
```

### Security Checklist

- [ ] Use HTTPS/SSL certificates
- [ ] Set `VERIFY_SSL=True` in production
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] Configure firewall to limit Snipe-IT API access
- [ ] Set strong `SECRET_KEY` (use `secrets.token_hex(32)`)
- [ ] Restrict Redis access to localhost only
- [ ] Configure rate limiting (already enabled)
- [ ] Set up file permissions (600 for sensitive files)
- [ ] Enable audit logging (`ENABLE_AUDIT_LOGGING=True`)

### Enable HTTPS

```bash
# Using Let's Encrypt (free)
sudo apt install certbot python3-certbot-apache
sudo certbot certonly --apache -d your-kiosk-domain.com

# Configure your web server to use the certificate
```

---

## Part 5: Customization

### Update Loan Agreement Terms

Edit `kiosk/templates/loan_agreement.html` to match your organization's policies:
- Search for "Equipment Condition & Responsibility"
- Update terms as needed
- Update contact email and procedures

### Update Color Scheme

Search for `#f76902` (orange) throughout the CSS and HTML to customize colors:
- `kiosk/static/styles.css` - main stylesheet
- `kiosk/templates/` - inline styles in templates

### Update Email Addresses

Search and replace any generic email placeholders with your organization's contact info.

### Configure Department Management

In Snipe-IT:
1. Create departments matching your organization structure
2. Assign users to departments
3. Users will see their department in the kiosk interface

---

## Troubleshooting

### "API Error: Connection refused"
- Verify `API_URL` and `API_TOKEN` are correct
- Check if Snipe-IT server is reachable from the kiosk server
- Verify API token hasn't expired in Snipe-IT

### "Asset not found"
- Make sure asset exists in Snipe-IT
- Verify the barcode/asset tag matches exactly
- Check custom field names match in `snipe_it_api.py`

### "Redis connection error"
- Verify Redis is running: `redis-cli ping`
- Check `REDIS_URL` in `.env`
- If Redis is remote, ensure firewall allows connection

### "Session expires too quickly"
- Increase `MAX_SESSION_DURATION` in `.env` (in seconds)
- Check `SESSION_COOKIE_SECURE` setting

---

## Support

For Snipe-IT support: https://snipe-it.readme.io/
For this kiosk: Check the repository issues and documentation

---

## Next Steps

1. ✅ Install and configure Snipe-IT
2. ✅ Get API token for kiosk user
3. ✅ Install Python dependencies
4. ✅ Configure `.env` file
5. ✅ Test integration locally
6. ✅ Deploy to production with HTTPS
7. ✅ Train staff on using the kiosk
8. ✅ Monitor logs and performance

Good luck! 
