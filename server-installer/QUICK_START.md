# Quick Start Guide

## What You Have

A complete server installation package containing:
- Snipe-IT asset management system with full database
- Apache configurations for both applications
- Automated installation script
- All necessary configuration files

## Installation on New Ubuntu Server

### 1. Transfer the Package

Copy `server-installer.tar.gz` to your new Ubuntu 24.04 server:

```bash
scp server-installer.tar.gz user@new-server:/home/user/
```

### 2. Extract

```bash
tar -xzf server-installer.tar.gz
cd server-installer
```

### 3. Configure

Edit the new server IP address:

```bash
nano config/NEW_SERVER_IP.txt
# Replace YOUR_NEW_SERVER_IP_HERE with your actual IP
```

### 4. Run Installer

```bash
sudo bash scripts/install.sh
```

The script will:
- Install all required packages (Apache, MariaDB, PHP, Redis, Python)
- Configure Apache with SSL
- Import Snipe-IT database
- Set up firewall rules
- Generate SSL certificates
- Start all services

**Time estimate:** 10-15 minutes

### 5. Post-Installation (Manual Steps)

#### A. Secure the Database
```bash
sudo mysql_secure_installation
```

#### B. Update Snipe-IT Configuration
```bash
sudo nano /var/www/html/snipeit/.env
# Update DB_PASSWORD to match your new MySQL password
```

#### C. Clone and Deploy Kiosk App
```bash
cd /var/www
sudo git clone YOUR_GITHUB_REPO_URL kiosk
cd kiosk
python3 -m venv .kiosk
source .kiosk/bin/activate
pip install -r requirements.txt
cp .env.template .env
nano .env  # Update with your settings
deactivate
sudo chown -R ubuntu:www-data /var/www/kiosk
sudo a2ensite kiosk.conf
sudo systemctl reload apache2
```

#### D. Verify Installation
```bash
bash scripts/verify.sh
```

### 6. Test Access

- **Snipe-IT:** `http://YOUR_IP/` or `https://YOUR_IP/`
- **Kiosk:** `http://YOUR_IP:8080/` or `https://YOUR_IP:8443/`

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status apache2
sudo systemctl status mariadb
sudo systemctl status redis-server
```

### View Logs
```bash
# Apache error logs
sudo tail -f /var/log/apache2/error.log

# Snipe-IT specific
sudo tail -f /var/log/apache2/snipeit_error.log

# Kiosk specific
sudo tail -f /var/log/apache2/kiosk_error.log
```

### Apache Config Test
```bash
sudo apache2ctl configtest
```

### Common Issues

**Issue:** Apache won't start
**Solution:** Check `apache2ctl configtest` for syntax errors

**Issue:** Database connection failed
**Solution:** Verify credentials in .env files match MySQL users

**Issue:** Kiosk 500 error
**Solution:** Check Python virtual environment is activated and dependencies installed

## Security Checklist

- [ ] Run `mysql_secure_installation`
- [ ] Change all default passwords
- [ ] Update .env files with secure secrets
- [ ] Review firewall rules (`sudo ufw status`)
- [ ] Install proper SSL certificates (Let's Encrypt recommended)
- [ ] Update Apache security headers if needed

## For Production

Replace self-signed certificates with Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d yourdomain.com
```

## Need Help?

See the full README.md for detailed documentation and troubleshooting steps.
