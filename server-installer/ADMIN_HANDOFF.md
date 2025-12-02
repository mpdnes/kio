# IT Administrator Handoff Document

## Overview

This document provides everything a new IT administrator needs to manage and maintain this server environment.

## System Architecture

### Current Server Setup

**Operating System:** Ubuntu 24.04 LTS
**Current Server IP:** 34.194.90.188
**Cloud Provider:** AWS (based on IP range)

### Applications Deployed

#### 1. Snipe-IT Asset Management System
- **Purpose:** IT asset tracking and management
- **Technology:** PHP 8.3 / Laravel framework
- **Web Ports:** 80 (HTTP), 443 (HTTPS)
- **Location:** `/var/www/html/snipeit/`
- **Database:** MariaDB database `snipeit`
- **Access:** `http://SERVER_IP/` or `https://SERVER_IP/`

#### 2. Kiosk Application
- **Purpose:** Custom kiosk management system
- **Technology:** Python/Flask with WSGI
- **Web Ports:** 8080 (HTTP), 8443 (HTTPS)
- **Location:** `/var/www/kiosk/`
- **GitHub:** [Owner should provide repository URL]
- **Access:** `http://SERVER_IP:8080/` or `https://SERVER_IP:8443/`

### Infrastructure Services

**Web Server:** Apache 2.4.58
- Main config: `/etc/apache2/apache2.conf`
- Virtual hosts: `/etc/apache2/sites-available/`
- Enabled sites: `/etc/apache2/sites-enabled/`
- Logs: `/var/log/apache2/`

**Database Server:** MariaDB 10.11.13
- Config: `/etc/mysql/mariadb.conf.d/`
- Data directory: `/var/lib/mysql/`
- Logs: `/var/log/mysql/`

**Cache Server:** Redis
- Config: `/etc/redis/redis.conf`
- Port: 6379 (localhost only)

**Firewall:** UFW
- Allowed ports: 22 (SSH), 80, 443, 5000, 8080, 8443

## Daily Operations

### Checking System Health

```bash
# Check all services
sudo systemctl status apache2
sudo systemctl status mariadb
sudo systemctl status redis-server

# Quick verification script
bash /path/to/verify.sh

# Check system resources
htop  # or top
df -h  # disk space
free -h  # memory
```

### Monitoring Logs

```bash
# Apache errors
sudo tail -f /var/log/apache2/error.log

# Snipe-IT specific
sudo tail -f /var/log/apache2/snipeit_error.log

# Kiosk specific
sudo tail -f /var/log/apache2/kiosk_error.log

# MariaDB errors
sudo tail -f /var/log/mysql/error.log

# System logs
sudo journalctl -xe
```

### Application Access

**Snipe-IT Admin Panel:**
- URL: `https://SERVER_IP/`
- Admin credentials: [Owner should provide separately]
- User management in web interface

**Kiosk Application:**
- URL: `https://SERVER_IP:8443/`
- Admin access: [Owner should provide details]

## Maintenance Tasks

### Weekly Tasks

1. **Check Disk Space**
   ```bash
   df -h
   # Alert if any partition >80% full
   ```

2. **Review Error Logs**
   ```bash
   sudo tail -100 /var/log/apache2/error.log
   ```

3. **Check for Failed Services**
   ```bash
   sudo systemctl --failed
   ```

### Monthly Tasks

1. **Create Backup**
   ```bash
   sudo bash /path/to/backup.sh
   ```

2. **Review Security Updates**
   ```bash
   sudo apt update
   sudo apt list --upgradable
   ```

3. **Clean Up Old Logs**
   ```bash
   # Apache logs are rotated automatically
   # Check /etc/logrotate.d/apache2
   ```

4. **Database Optimization**
   ```bash
   sudo mysqlcheck -u root -p --optimize --all-databases
   ```

### Quarterly Tasks

1. **Full System Update**
   ```bash
   sudo apt update
   sudo apt upgrade
   sudo apt autoremove
   sudo reboot  # Schedule during maintenance window
   ```

2. **SSL Certificate Renewal** (if using Let's Encrypt)
   ```bash
   sudo certbot renew
   # Or setup auto-renewal with cron
   ```

3. **Review User Access**
   - Snipe-IT users
   - Server SSH access
   - Database users

## Common Administrative Tasks

### Restarting Services

```bash
# Restart Apache (for config changes)
sudo systemctl restart apache2

# Restart MariaDB
sudo systemctl restart mariadb

# Restart all web services
sudo systemctl restart apache2 mariadb redis-server
```

### Updating Applications

**Snipe-IT Update:**
```bash
cd /var/www/html/snipeit
sudo git pull  # If managed via git
sudo composer install --no-dev --prefer-source
sudo php artisan migrate
sudo chown -R www-data:www-data /var/www/html/snipeit
sudo systemctl restart apache2
```

**Kiosk Update:**
```bash
cd /var/www/kiosk
sudo git pull
source .kiosk/bin/activate
pip install -r requirements.txt --upgrade
deactivate
sudo systemctl restart apache2
```

### Database Management

**Backup Single Database:**
```bash
sudo mysqldump snipeit > snipeit_backup_$(date +%Y%m%d).sql
```

**Restore Database:**
```bash
sudo mysql snipeit < snipeit_backup_YYYYMMDD.sql
```

**Access Database:**
```bash
sudo mysql
# Then: USE snipeit;
```

**Create Database User:**
```bash
sudo mysql
CREATE USER 'newuser'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON database.* TO 'newuser'@'localhost';
FLUSH PRIVILEGES;
```

### Managing Apache

**Test Configuration:**
```bash
sudo apache2ctl configtest
```

**Enable/Disable Sites:**
```bash
sudo a2ensite sitename.conf
sudo a2dissite sitename.conf
sudo systemctl reload apache2
```

**Enable/Disable Modules:**
```bash
sudo a2enmod module_name
sudo a2dismod module_name
sudo systemctl restart apache2
```

### Firewall Management

**Check Status:**
```bash
sudo ufw status numbered
```

**Add Rule:**
```bash
sudo ufw allow PORT/tcp comment "Description"
```

**Remove Rule:**
```bash
sudo ufw delete RULE_NUMBER
```

## Security Management

### Current Security Measures

✓ UFW firewall enabled
✓ SSH access (port 22)
✓ SSL/TLS configured for all web services
✓ Modern TLS protocols only (TLS 1.2+)
✓ Security headers configured in Apache

### Security Best Practices

1. **Regular Updates**
   - Enable automatic security updates
   - Review and apply updates monthly

2. **Strong Passwords**
   - Database passwords in .env files
   - Snipe-IT admin accounts
   - SSH keys preferred over passwords

3. **SSL Certificates**
   - Currently using self-signed certificates
   - STRONGLY RECOMMEND: Install Let's Encrypt
   ```bash
   sudo apt install certbot python3-certbot-apache
   sudo certbot --apache -d yourdomain.com
   ```

4. **Backup Strategy**
   - Run weekly backups (automate with cron)
   - Store backups off-server
   - Test restores quarterly

5. **Access Control**
   - Limit SSH access
   - Use SSH keys
   - Review sudo access regularly

### Automated Security Updates

```bash
# Install unattended-upgrades (usually pre-installed)
sudo apt install unattended-upgrades

# Configure
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Configuration Files Reference

### Critical Configuration Files

**Application Configs:**
- `/var/www/html/snipeit/.env` - Snipe-IT configuration
- `/var/www/kiosk/.env` - Kiosk configuration

**Apache Configs:**
- `/etc/apache2/sites-available/snipeit.conf`
- `/etc/apache2/sites-available/kiosk.conf`
- `/etc/apache2/ports.conf`

**Database:**
- `/etc/mysql/mariadb.conf.d/50-server.cnf`

**SSL Certificates:**
- `/etc/ssl/certs/kiosk/kiosk.crt`
- `/etc/ssl/private/kiosk/kiosk.key`
- `/etc/ssl/certs/snipeit.crt`
- `/etc/ssl/private/snipeit.key`

### IMPORTANT: Sensitive Files

**Never commit to version control:**
- `.env` files (contain passwords and secrets)
- SSL private keys
- Database credentials

**Backup securely:**
- Store encrypted
- Restrict access
- Keep off-server copies

## Disaster Recovery

### Backup Procedures

**Automated Backup Script:**
```bash
sudo bash /path/to/backup.sh
```

Creates backups of:
- All databases
- Application files
- Configurations
- SSL certificates

**Backup Location:** `/home/ubuntu/backups/`

**Setup Automated Backups:**
```bash
sudo crontab -e
# Add line:
0 2 * * 0 /path/to/backup.sh  # Weekly at 2 AM Sunday
```

### Restore Procedures

See `README.md` section on restoration, or:

1. Extract backup archive
2. Import databases: `sudo mysql < backup.sql`
3. Restore application files to `/var/www/`
4. Restore Apache configs
5. Restart services

### Full Server Migration

Use the installer package:
1. Create fresh backup on current server
2. Transfer `server-installer.tar.gz` to new server
3. Run `sudo bash install.sh`
4. Restore latest database backups
5. Update IP addresses in configs
6. Update DNS records

## Troubleshooting

### Quick Diagnostics

**Service Down:**
```bash
sudo systemctl status SERVICE_NAME
sudo journalctl -u SERVICE_NAME -n 50
```

**Web App Not Responding:**
```bash
sudo apache2ctl configtest
sudo tail -50 /var/log/apache2/error.log
curl http://localhost/  # Test locally
```

**Database Connection Failed:**
```bash
sudo systemctl status mariadb
sudo mysql -u root -p  # Test connection
# Check .env file credentials
```

**High Resource Usage:**
```bash
top  # Identify CPU hogs
free -h  # Check memory
df -h  # Check disk
```

### Full Troubleshooting Guide

See `TROUBLESHOOTING.md` for comprehensive issue resolution.

## Emergency Contacts

**System Owner:** [To be provided]
**Email:** [To be provided]
**Phone:** [To be provided]

**Application Developers:**
- Kiosk App: [GitHub repository owner]
- Snipe-IT: Official documentation at https://snipe-it.readme.io/

**Escalation Path:**
1. Check logs and troubleshooting guide
2. Contact system owner
3. Consult application documentation
4. Community forums / GitHub issues

## Useful Resources

### Documentation Included in Package

- `README.md` - Installation guide
- `QUICK_START.md` - Quick installation
- `TROUBLESHOOTING.md` - Problem solving
- `MANIFEST.txt` - Package inventory

### External Resources

**Snipe-IT:**
- Docs: https://snipe-it.readme.io/
- GitHub: https://github.com/snipe/snipe-it
- Community: https://gitter.im/snipe/snipe-it

**Apache:**
- Docs: https://httpd.apache.org/docs/2.4/

**MariaDB:**
- Docs: https://mariadb.org/documentation/

**Ubuntu:**
- Docs: https://help.ubuntu.com/

### Command Reference

**Most Used Commands:**
```bash
# Service management
sudo systemctl status|start|stop|restart SERVICE

# Check logs
sudo tail -f /var/log/FILE

# Test Apache
sudo apache2ctl configtest

# Database access
sudo mysql

# Firewall
sudo ufw status

# Disk space
df -h

# System resources
top or htop

# Run backup
sudo bash backup.sh

# Verify system
bash verify.sh
```

## Onboarding Checklist

For the new administrator, complete these tasks:

- [ ] Receive admin credentials for Snipe-IT
- [ ] Receive SSH access to server
- [ ] Receive database root password
- [ ] Review this handoff document
- [ ] Run verification script: `bash verify.sh`
- [ ] Access all web applications
- [ ] Review log files locations
- [ ] Test backup script
- [ ] Setup automated backups (cron)
- [ ] Document any changes made
- [ ] Setup monitoring alerts (optional)
- [ ] Install Let's Encrypt certificates
- [ ] Join relevant support communities
- [ ] Save emergency contact information

## Notes and Custom Configurations

[Space for the admin to document custom changes]

---

**Document Version:** 1.0
**Last Updated:** $(date)
**Server:** 34.194.90.188
