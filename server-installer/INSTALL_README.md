# Server Installation Guide

Complete guide for deploying Snipe-IT Asset Management and Kiosk Application

## Table of Contents

- [Prerequisites](#prerequisites)
- [Pre-Installation Checklist](#pre-installation-checklist)
- [Installation Steps](#installation-steps)
- [Post-Installation Configuration](#post-installation-configuration)
- [Troubleshooting](#troubleshooting)
- [Security Hardening](#security-hardening)

## Prerequisites

### System Requirements

**Minimum:**
- Ubuntu 22.04+ or Debian 11+
- 2GB RAM
- 20GB available disk space
- Internet connection (for package installation)

**Recommended:**
- Ubuntu 24.04 LTS
- 4GB RAM
- 40GB disk space
- Static IP address or domain name

### Required Access

- Root or sudo access
- Ability to configure passwordless sudo (temporary)
- SSH access to the server (if remote)

### Network Requirements

The installation requires the following ports to be available:
- **22** - SSH
- **80** - HTTP (Apache)
- **443** - HTTPS (Snipe-IT)
- **8080** - HTTP (Kiosk - optional)
- **8443** - HTTPS (Kiosk)

### Before You Begin

1. **Backup existing data** if this is not a fresh installation
2. **Note your server's IP address** or domain name
3. **Prepare API tokens** for Snipe-IT integration (can be generated after installation)
4. **Review firewall rules** on your network

## Pre-Installation Checklist

- [ ] Server meets minimum requirements
- [ ] You have root/sudo access
- [ ] Ports 80, 443, 8080, 8443 are available
- [ ] You have noted your server's IP address
- [ ] You have extracted the server-installer tarball
- [ ] You have reviewed the ARCHITECTURE.md document (optional)

## Installation Steps

### Step 1: Extract Installation Package

```bash
# Extract the tarball
tar -xzf server-installer.tar.gz
cd server-installer
```

### Step 2: Configure Server IP Address

Edit the configuration file with your server's IP address:

```bash
nano config/NEW_SERVER_IP.txt
```

Replace `YOUR_NEW_SERVER_IP_HERE` with your actual server IP address (e.g., `192.168.1.100`) or domain name.

**Important:** Do not use `localhost` unless you're only testing locally!

### Step 3: Set Up Passwordless Sudo (Temporary)

The installer requires passwordless sudo to run unattended. This will be reverted after installation.

```bash
echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/temp_nopasswd
```

**Note:** You'll remove this after installation completes.

### Step 4: Run the Improved Installer

```bash
sudo ./scripts/install-improved.sh
```

The installer will:
1. Run pre-flight checks (disk space, RAM, ports, OS compatibility)
2. Update system packages
3. Install required packages (Apache, MariaDB, Redis, PHP, Python)
4. Configure and secure MariaDB
5. Deploy Snipe-IT application
6. Deploy Kiosk application (if available)
7. Generate SSL certificates
8. Configure Apache virtual hosts
9. Configure firewall (UFW)
10. Start all services
11. Validate installation

**Installation time:** 10-20 minutes depending on your internet connection

### Step 5: Review Installation Output

The installer will display:
- Temporary database password (save this!)
- Access URLs for both applications
- Post-installation tasks
- Installation log location

**Important:** Save the temporary database password shown at the end!

### Step 6: Remove Temporary Sudo Access

```bash
sudo rm /etc/sudoers.d/temp_nopasswd
```

## Post-Installation Configuration

### 1. Secure MariaDB

**CRITICAL:** Change the temporary database password immediately!

```bash
sudo mysql_secure_installation
```

Answer the prompts:
- Enter current root password: [Use the temporary password from installation]
- Change root password: **YES** - Choose a strong password
- Remove anonymous users: **YES**
- Disallow root login remotely: **YES**
- Remove test database: **YES**
- Reload privilege tables: **YES**

### 2. Update Snipe-IT Database Password

After changing the MySQL root password, update Snipe-IT's configuration:

```bash
sudo nano /var/www/html/snipeit/.env
```

Find and update:
```
DB_PASSWORD=ChangeThisPassword123!
```

Change to your new secure password.

### 3. Configure Snipe-IT

Access Snipe-IT at `https://YOUR_SERVER_IP/`

If the database was imported from backup:
- You should see the login page
- Use your existing credentials

If starting fresh:
- Complete the setup wizard
- Create an admin account
- Generate an API token (Settings → API)

### 4. Configure Kiosk Application

#### Generate Secret Key

The kiosk application needs a secret key for Flask sessions:

```bash
# Generate secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

#### Update Kiosk .env

```bash
sudo nano /var/www/kiosk/.env
```

Update the following values:
```bash
SECRET_KEY=<paste your secret key>
API_TOKEN=<paste Snipe-IT API token>
ALLOWED_HOSTS=<your server IP>
```

#### Restart Apache

```bash
sudo systemctl restart apache2
```

### 5. Test Both Applications

**Snipe-IT:**
```bash
curl -k https://YOUR_SERVER_IP/
```

**Kiosk:**
```bash
curl -k https://YOUR_SERVER_IP:8443/
```

Both should return HTML (HTTP 200 or 302).

### 6. Create Application Backups

Now that everything is working, create a backup:

```bash
cd /path/to/server-installer
sudo ./scripts/backup.sh
```

This will create timestamped backups of:
- Databases
- Configuration files
- SSL certificates
- Environment files

## Troubleshooting

### Installation Fails at Pre-Flight Checks

**Ports already in use:**
- Check what's using the ports: `sudo netstat -tulpn | grep -E ':(80|443|8080|8443)'`
- Stop conflicting services or change port configuration

**Insufficient disk space:**
- Free up space: `sudo apt clean && sudo apt autoremove`
- Check usage: `df -h`

**Low RAM warning:**
- Installation may be slow but should complete
- Consider upgrading RAM for production use

### Apache Won't Start

Check the error log:
```bash
sudo tail -100 /var/log/apache2/error.log
```

Common issues:
- Port conflicts → See pre-flight checks
- SSL certificate issues → Regenerate certificates
- Configuration syntax errors → Run `sudo apache2ctl configtest`

### Can't Connect to Database

Verify MariaDB is running:
```bash
sudo systemctl status mariadb
```

Test connection:
```bash
mysql -u snipeit -p'ChangeThisPassword123!' -e "SELECT 1;"
```

If connection fails:
- Check password in `/var/www/html/snipeit/.env`
- Verify user exists: `sudo mysql -e "SELECT user, host FROM mysql.user WHERE user='snipeit';"`

### Kiosk Application Shows 500 Error

Check WSGI error log:
```bash
sudo tail -100 /var/www/kiosk/logs/wsgi.log
```

Common issues:
- Missing Python dependencies → Reinstall: `.kiosk/bin/pip install -r requirements.txt`
- Permission errors → Fix: `sudo chown -R www-data:www-data /var/www/kiosk/logs`
- Redis not running → Start: `sudo systemctl start redis-server`
- Missing directories → Create: `sudo mkdir -p /var/www/kiosk/{logs,loan_agreements,secure_data}`

### SSL Certificate Errors in Browser

The installer generates self-signed certificates which browsers will warn about. This is expected.

Options:
1. **For testing:** Click "Advanced" → "Proceed anyway"
2. **For production:** Install Let's Encrypt certificates (see below)

## Security Hardening

### Install Let's Encrypt SSL Certificates

For production, replace self-signed certificates with Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-apache -y

# For Snipe-IT (port 443)
sudo certbot --apache -d your-domain.com

# For Kiosk (port 8443) - requires manual configuration
sudo certbot certonly --standalone -d kiosk.your-domain.com
# Then update kiosk.conf to use the new certificates
```

### Firewall Configuration

Review and customize firewall rules:

```bash
# Check current status
sudo ufw status verbose

# Example: Limit SSH access to specific IP
sudo ufw delete allow 22/tcp
sudo ufw allow from YOUR_ADMIN_IP to any port 22

# Example: Close HTTP port (force HTTPS only)
sudo ufw delete allow 80/tcp
```

### Disable Debugging

For production deployments:

**Snipe-IT:**
```bash
sudo nano /var/www/html/snipeit/.env
```
Set: `APP_DEBUG=false`

**Kiosk:**
```bash
sudo nano /var/www/kiosk/.env
```
Set:
```
FLASK_ENV=production
DEBUG=False
```

### Regular Updates

Set up automatic security updates:

```bash
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### Database Security

Additional MariaDB hardening:

```bash
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

Add under `[mysqld]`:
```
# Security settings
local-infile=0
symbolic-links=0
max_connections=100
```

Restart MariaDB:
```bash
sudo systemctl restart mariadb
```

### Application-Level Security

**Change all default passwords:**
- [x] MariaDB root password
- [x] Snipe-IT database password
- [x] Snipe-IT admin user password
- [x] API tokens (regenerate)

**Review application logs regularly:**
```bash
# Snipe-IT logs
sudo tail -f /var/www/html/snipeit/storage/logs/laravel.log

# Kiosk logs
sudo tail -f /var/www/kiosk/logs/wsgi.log

# Apache logs
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/apache2/kiosk_error.log
```

## Additional Resources

- **Snipe-IT Documentation:** https://snipe-it.readme.io/
- **Flask Security:** https://flask.palletsprojects.com/en/latest/security/
- **Ubuntu Security Guide:** https://ubuntu.com/security
- **Let's Encrypt:** https://letsencrypt.org/

## Getting Help

If you encounter issues:

1. Check the logs (see Troubleshooting section)
2. Review the TROUBLESHOOTING.md document
3. Check the OPERATIONS_GUIDE.md for maintenance procedures
4. Verify all post-installation steps were completed

## Appendix: Installation Files

### Directory Structure

```
server-installer/
├── applications/
│   └── snipeit.tar.gz          # Snipe-IT application
├── config/
│   ├── apache/
│   │   ├── snipeit.conf         # Apache vhost for Snipe-IT
│   │   ├── kiosk.conf           # Apache vhost for Kiosk
│   │   └── ports.conf           # Port configuration
│   ├── NEW_SERVER_IP.txt        # Server IP configuration
│   └── snipeit.env.template     # Snipe-IT environment template
├── databases/
│   ├── snipeit.sql              # Database backup
│   └── credentials.txt          # Database credentials
├── scripts/
│   ├── install.sh               # Original installer
│   ├── install-improved.sh      # Improved installer (USE THIS)
│   ├── backup.sh                # Backup script
│   ├── uninstall.sh             # Uninstaller
│   └── verify.sh                # Verification script
├── README.md                    # Overview
├── INSTALL_README.md            # This file
├── ARCHITECTURE.md              # System architecture
├── OPERATIONS_GUIDE.md          # Operations manual
└── TROUBLESHOOTING.md           # Troubleshooting guide
```

### Kiosk Application

The kiosk application should be cloned from your GitHub repository or placed in:
```
/var/www/kiosk/
```

See the installer output for instructions on deploying the kiosk application if it wasn't included in the installation package.

## Version Information

- **Installer Version:** 2.0 (Improved)
- **Supported OS:** Ubuntu 22.04+, Debian 11+
- **PHP Version:** 8.3
- **Python Version:** 3.10+
- **MariaDB Version:** 10.6+
- **Apache Version:** 2.4+

---

**Installation Date:** [Recorded in /root/installation-log-*.txt]
**Last Updated:** October 2025
