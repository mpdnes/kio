# Server Installation Package

This package contains everything needed to replicate your Ubuntu server setup on a fresh Ubuntu 24.04 instance.

## What's Included

- **Kiosk Application**: Python/Flask web application (ports 8080/8443)
- **Snipe-IT**: PHP asset management system (ports 80/443)
- **MariaDB Database**: Database server with exported data
- **Redis**: Key-value store for caching
- **Apache2**: Web server with SSL configuration
- **Firewall Rules**: UFW configuration

## System Requirements

- Fresh Ubuntu 24.04 LTS server
- Minimum 2GB RAM
- 20GB available disk space
- Root or sudo access
- Internet connection for package installation

## Quick Start

```bash
# 1. Extract the package
tar -xzf server-installer.tar.gz
cd server-installer

# 2. Review and edit configuration
nano config/NEW_SERVER_IP.txt  # Set your new server's IP address

# 3. Run the installer (will prompt for sudo password)
sudo bash scripts/install.sh

# 4. Follow post-installation steps below
```

## Installation Steps (Detailed)

### Pre-Installation

1. **Set new server IP address:**
   ```bash
   echo "YOUR_NEW_SERVER_IP" > config/NEW_SERVER_IP.txt
   ```

2. **Review credentials (if needed):**
   - Database passwords are in `databases/credentials.txt`
   - Application .env files will need manual review

### Running the Installer

The installer script will:
1. Update system packages
2. Install required software (Apache, MariaDB, Redis, PHP, Python)
3. Configure Apache with virtual hosts
4. Import databases
5. Deploy applications
6. Configure SSL certificates (self-signed)
7. Set up firewall rules
8. Set correct file permissions

```bash
sudo bash scripts/install.sh
```

### Post-Installation Steps

1. **Update Application Configs:**
   ```bash
   # Edit kiosk .env file with new server IP/domain
   sudo nano /var/www/kiosk/.env

   # Edit Snipe-IT .env file
   sudo nano /var/www/html/snipeit/.env
   ```

2. **Regenerate SSL Certificates (if using custom domain):**
   ```bash
   # For production, use Let's Encrypt:
   sudo apt install certbot python3-certbot-apache
   sudo certbot --apache -d your-domain.com
   ```

3. **Test Services:**
   ```bash
   # Check Apache
   sudo systemctl status apache2

   # Check MariaDB
   sudo systemctl status mariadb

   # Check Redis
   sudo systemctl status redis-server

   # Test kiosk app
   curl http://localhost:8080

   # Test Snipe-IT
   curl http://localhost:80
   ```

4. **Update DNS/IP References:**
   - Update any hardcoded IP addresses in your applications
   - Update DNS records to point to new server
   - Update firewall rules if IP changed

## Manual Configuration Required

### Database Credentials
- MariaDB root password: See `databases/credentials.txt`
- Database users: Will be created during installation

### Application Secrets
- Kiosk `.env` file: Review and update SECRET_KEY, database URLs
- Snipe-IT `.env` file: Review APP_KEY and database settings

### SSL Certificates
- Self-signed certificates will be generated automatically
- For production, replace with valid certificates (Let's Encrypt recommended)

## Troubleshooting

### Apache won't start
```bash
# Check configuration
sudo apache2ctl configtest

# Check error logs
sudo tail -f /var/log/apache2/error.log
```

### Database import fails
```bash
# Import manually
sudo mysql -u root -p < databases/snipeit.sql

# Check database status
sudo systemctl status mariadb
```

### Python app errors
```bash
# Check Apache WSGI logs
sudo tail -f /var/log/apache2/kiosk_error.log

# Verify virtual environment
source /var/www/kiosk/.kiosk/bin/activate
pip list
```

### Permission issues
```bash
# Fix kiosk permissions
sudo chown -R ubuntu:www-data /var/www/kiosk
sudo chmod -R 755 /var/www/kiosk

# Fix Snipe-IT permissions
sudo chown -R www-data:www-data /var/www/html/snipeit
sudo chmod -R 755 /var/www/html/snipeit
```

## Security Checklist

- [ ] Change all default passwords
- [ ] Review and update .env files with new secrets
- [ ] Configure proper SSL certificates
- [ ] Review firewall rules for your network
- [ ] Update SSH configuration if needed
- [ ] Enable automatic security updates
- [ ] Review Apache security headers
- [ ] Secure database with mysql_secure_installation

## File Structure

```
server-installer/
├── README.md (this file)
├── INSTALLATION_LOG.md (detailed steps performed)
├── config/
│   ├── apache/          # Apache virtual host configs
│   ├── ssl/             # SSL certificate templates
│   ├── php/             # PHP configuration
│   └── NEW_SERVER_IP.txt
├── databases/
│   ├── snipeit.sql      # Database dump
│   └── credentials.txt   # Database passwords
├── applications/
│   ├── kiosk.tar.gz     # Kiosk application
│   └── snipeit.tar.gz   # Snipe-IT application
└── scripts/
    ├── install.sh       # Main installation script
    ├── backup.sh        # Backup script for future use
    └── verify.sh        # Post-install verification
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs in /var/log/apache2/
3. Check application-specific logs

## Version Info

- Created: $(date)
- Source Server: Ubuntu 24.04 LTS
- Apache: 2.4.58
- MariaDB: 10.11.13
- PHP: 8.3
- Python: 3.x (check applications/kiosk/requirements.txt)
