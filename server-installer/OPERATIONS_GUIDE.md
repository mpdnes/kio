# Operations and Maintenance Guide

## Quick Reference Card

### Essential Commands

| Task | Command |
|------|---------|
| Check all services | `sudo systemctl status apache2 mariadb redis-server` |
| Restart web service | `sudo systemctl restart apache2` |
| View Apache errors | `sudo tail -50 /var/log/apache2/error.log` |
| Test Apache config | `sudo apache2ctl configtest` |
| Create backup | `sudo bash /path/to/backup.sh` |
| Check disk space | `df -h` |
| Check memory | `free -h` |
| Database access | `sudo mysql` |
| Firewall status | `sudo ufw status` |

## Maintenance Schedule

### Daily (Automated via Monitoring)

- **Service availability checks**
  - Apache responding on all ports
  - MariaDB accepting connections
  - Redis responding

- **Disk space monitoring**
  - Alert if >80% on any partition

- **Error log review**
  - Check for critical errors

### Weekly (Manual - 15 minutes)

**Every Monday:**

1. **Check System Health**
   ```bash
   # Run verification script
   bash /path/to/verify.sh

   # Review for any warnings
   ```

2. **Review Logs**
   ```bash
   # Check for unusual errors
   sudo tail -100 /var/log/apache2/error.log
   sudo tail -100 /var/log/mysql/error.log
   ```

3. **Check Resources**
   ```bash
   df -h        # Disk space
   free -h      # Memory usage
   ```

4. **Backup Verification**
   ```bash
   # Verify last backup exists and size is reasonable
   ls -lh /home/ubuntu/backups/
   ```

### Weekly (Automated via Cron)

**Every Sunday 2 AM:**

```bash
# Setup automated backup
sudo crontab -e

# Add this line:
0 2 * * 0 /path/to/backup.sh
```

### Monthly (Manual - 30-45 minutes)

**First Monday of Each Month:**

1. **Security Updates**
   ```bash
   sudo apt update
   sudo apt list --upgradable

   # Review updates, then apply
   sudo apt upgrade -y

   # Note: May require reboot
   ```

2. **Create Full Backup**
   ```bash
   sudo bash /path/to/backup.sh

   # Download to secure location off-server
   ```

3. **Database Maintenance**
   ```bash
   # Optimize databases
   sudo mysqlcheck -u root -p --optimize --all-databases

   # Check for corruption
   sudo mysqlcheck -u root -p --check --all-databases
   ```

4. **Review Users and Access**
   - Check Snipe-IT user accounts (via web interface)
   - Review SSH access logs: `sudo grep 'Accepted' /var/log/auth.log`
   - Verify database users: `sudo mysql -e "SELECT user, host FROM mysql.user;"`

5. **Clean Up Old Files**
   ```bash
   # Old backups (manual review, keep last 3 months)
   ls -lht /home/ubuntu/backups/

   # Old logs (check logrotate is working)
   ls -lh /var/log/apache2/
   ```

6. **Review Disk Usage**
   ```bash
   # Find large directories
   sudo du -h --max-depth=2 /var/www | sort -hr | head -20

   # Check database sizes
   sudo mysql -e "SELECT table_schema AS 'Database',
                  ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
                  FROM information_schema.tables
                  GROUP BY table_schema;"
   ```

### Quarterly (Manual - 1-2 hours)

**First Week of Quarter:**

1. **Full System Update**
   ```bash
   # Create backup first!
   sudo bash /path/to/backup.sh

   # Full update
   sudo apt update
   sudo apt upgrade -y
   sudo apt dist-upgrade -y
   sudo apt autoremove -y
   sudo apt autoclean

   # Reboot during maintenance window
   sudo reboot
   ```

2. **SSL Certificate Check**
   ```bash
   # Check expiration
   echo | openssl s_client -connect localhost:443 2>/dev/null | openssl x509 -noout -dates

   # If using Let's Encrypt, renew
   sudo certbot renew
   ```

3. **Security Audit**
   - Review firewall rules: `sudo ufw status numbered`
   - Check for unauthorized users: `cat /etc/passwd`
   - Review sudo access: `sudo cat /etc/sudoers`
   - Check for suspicious cron jobs: `sudo crontab -l` and `crontab -l`
   - Review SSH config: `sudo cat /etc/ssh/sshd_config`

4. **Disaster Recovery Test**
   - Verify backups can be restored
   - Test on a separate test instance if possible
   - Document any issues

5. **Performance Review**
   - Check Apache performance
   - Review database query performance
   - Consider optimization opportunities

### Annually (Manual - Half Day)

**Beginning of Year:**

1. **Complete Documentation Review**
   - Update all documentation
   - Document any changes made during year
   - Review and update runbooks

2. **Full Security Assessment**
   - Review all accounts and access
   - Update all passwords
   - Review security patches
   - Consider penetration testing

3. **Capacity Planning**
   - Review growth trends (disk, users, traffic)
   - Plan for upcoming needs
   - Budget for upgrades if needed

4. **Disaster Recovery Drill**
   - Full restore test on separate server
   - Verify all procedures documented
   - Update recovery procedures

## Change Management

### Making Configuration Changes

**ALWAYS:**

1. **Create Backup First**
   ```bash
   sudo bash /path/to/backup.sh
   ```

2. **Document the Change**
   - What you're changing
   - Why you're changing it
   - How to revert if needed

3. **Test Configuration**
   ```bash
   # For Apache
   sudo apache2ctl configtest

   # For database
   # Test connection after change
   ```

4. **Apply During Maintenance Window**
   - Notify users if downtime expected
   - Have rollback plan ready

5. **Verify After Change**
   ```bash
   bash /path/to/verify.sh
   ```

### Common Change Procedures

#### Adding a New Firewall Rule

```bash
# Test locally first
sudo ufw allow PORT/tcp comment "Description"

# Verify
sudo ufw status numbered

# Test access
```

#### Updating Apache Configuration

```bash
# Backup current config
sudo cp /etc/apache2/sites-available/site.conf /etc/apache2/sites-available/site.conf.backup

# Edit config
sudo nano /etc/apache2/sites-available/site.conf

# Test
sudo apache2ctl configtest

# If OK, reload
sudo systemctl reload apache2

# Verify
curl http://localhost/
```

#### Changing Database Password

```bash
# 1. Change in database
sudo mysql
ALTER USER 'username'@'localhost' IDENTIFIED BY 'newpassword';
FLUSH PRIVILEGES;
exit;

# 2. Update in .env file
sudo nano /var/www/html/snipeit/.env
# Update DB_PASSWORD=newpassword

# 3. Restart Apache
sudo systemctl restart apache2

# 4. Test application access
```

## Performance Tuning

### Apache Optimization

**Check current settings:**
```bash
apache2ctl -M  # Enabled modules
apache2 -V      # Compile settings
```

**Optimize for your workload:**
```bash
sudo nano /etc/apache2/mods-available/mpm_prefork.conf
```

Recommended settings for 2GB RAM:
```
<IfModule mpm_prefork_module>
    StartServers             5
    MinSpareServers          5
    MaxSpareServers          10
    MaxRequestWorkers        150
    MaxConnectionsPerChild   3000
</IfModule>
```

### Database Optimization

**Enable slow query log:**
```bash
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

Add:
```
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow-query.log
long_query_time = 2
```

**Optimize tables regularly:**
```bash
sudo mysqlcheck -u root -p --optimize --all-databases
```

### PHP Optimization

**Enable OPcache:**
```bash
sudo apt install php8.3-opcache
sudo systemctl restart apache2
```

**Adjust PHP limits:**
```bash
sudo nano /etc/php/8.3/apache2/php.ini
```

Key settings:
```
memory_limit = 256M
upload_max_filesize = 20M
post_max_size = 20M
max_execution_time = 60
```

## Monitoring and Alerts

### Simple Monitoring Setup

**Install monitoring tools:**
```bash
sudo apt install htop iotop nethogs
```

**Create simple health check script:**
```bash
sudo nano /usr/local/bin/health-check.sh
```

```bash
#!/bin/bash
# Simple health check script

# Check services
systemctl is-active --quiet apache2 || echo "ALERT: Apache is down!"
systemctl is-active --quiet mariadb || echo "ALERT: MariaDB is down!"

# Check disk space
df -h | awk '$5 > 80 {print "ALERT: Disk usage high on "$1}'

# Check for errors in last hour
ERROR_COUNT=$(sudo grep -c "error" /var/log/apache2/error.log)
if [ $ERROR_COUNT -gt 10 ]; then
    echo "ALERT: $ERROR_COUNT errors in Apache log"
fi
```

**Schedule health checks:**
```bash
sudo crontab -e
# Add: Run every hour
0 * * * * /usr/local/bin/health-check.sh
```

### Log Monitoring

**Watch logs in real-time:**
```bash
# All Apache errors
sudo tail -f /var/log/apache2/error.log

# Multiple logs at once
sudo tail -f /var/log/apache2/error.log /var/log/mysql/error.log
```

**Search logs for issues:**
```bash
# Find all errors today
sudo grep "$(date +%Y-%m-%d)" /var/log/apache2/error.log | grep -i error

# Count errors by type
sudo grep "error" /var/log/apache2/error.log | awk '{print $NF}' | sort | uniq -c | sort -rn
```

## Backup Management

### Backup Strategy

**What to backup:**
- All databases (automated by backup.sh)
- Application files (automated by backup.sh)
- Configuration files (automated by backup.sh)
- SSL certificates (automated by backup.sh)

**Backup retention:**
- Daily: Keep 7 days
- Weekly: Keep 4 weeks
- Monthly: Keep 12 months
- Yearly: Keep indefinitely

**Backup locations:**
- Primary: `/home/ubuntu/backups/` (automated cleanup keeps 7 days)
- Secondary: Off-server storage (S3, external drive, etc.)

### Manual Backup

```bash
# Full backup
sudo bash /path/to/backup.sh

# Database only
sudo mysqldump --all-databases > all-databases-$(date +%Y%m%d).sql

# Specific application
cd /var/www/html
sudo tar -czf snipeit-backup-$(date +%Y%m%d).tar.gz snipeit/
```

### Automated Backups

```bash
# Setup weekly backups
sudo crontab -e

# Add these lines:
# Full backup every Sunday at 2 AM
0 2 * * 0 /path/to/backup.sh

# Database backup every day at 1 AM
0 1 * * * mysqldump --all-databases > /home/ubuntu/backups/daily-db-$(date +\%Y\%m\%d).sql
```

### Offsite Backup

**Using SCP:**
```bash
# In backup script or separate cron job
scp /home/ubuntu/backups/latest-backup.tar.gz user@backup-server:/backups/
```

**Using AWS S3 (if applicable):**
```bash
# Install AWS CLI
sudo apt install awscli

# Configure
aws configure

# Upload backups
aws s3 cp /home/ubuntu/backups/ s3://your-bucket/server-backups/ --recursive
```

## Incident Response

### Service Down

1. **Check service status**
   ```bash
   sudo systemctl status SERVICE_NAME
   ```

2. **Review logs**
   ```bash
   sudo journalctl -u SERVICE_NAME -n 100
   ```

3. **Attempt restart**
   ```bash
   sudo systemctl restart SERVICE_NAME
   ```

4. **If restart fails, check configuration**
   ```bash
   sudo apache2ctl configtest  # For Apache
   ```

5. **Document incident**
   - What happened
   - What you did
   - Resolution

### High Load / Slow Performance

1. **Identify resource bottleneck**
   ```bash
   top           # CPU usage
   free -h       # Memory
   iotop         # Disk I/O
   nethogs       # Network
   ```

2. **Check for runaway processes**
   ```bash
   ps aux | sort -k 3 -rn | head -10  # Top CPU
   ps aux | sort -k 4 -rn | head -10  # Top Memory
   ```

3. **Review recent changes**
   - What changed recently?
   - Any new traffic patterns?

4. **Temporary mitigation**
   ```bash
   # Restart heavy services
   sudo systemctl restart apache2
   ```

5. **Long-term resolution**
   - Optimize queries
   - Add caching
   - Scale resources

### Security Incident

1. **Isolate system if compromised**
   ```bash
   sudo ufw deny from SUSPICIOUS_IP
   ```

2. **Review access logs**
   ```bash
   sudo grep "Failed password" /var/log/auth.log
   sudo tail -500 /var/log/apache2/access.log
   ```

3. **Change passwords**
   - Database
   - Application admin accounts
   - SSH keys

4. **Document and escalate**
   - Contact system owner
   - Preserve logs for investigation

## Best Practices

### Configuration Management

- ✓ Always backup before changes
- ✓ Test changes in staging if possible
- ✓ Document all changes
- ✓ Use version control for configs (git)
- ✓ Keep rollback plans ready

### Security

- ✓ Apply security updates promptly
- ✓ Use strong passwords (16+ characters)
- ✓ Enable automatic updates for security patches
- ✓ Review access logs regularly
- ✓ Limit sudo access
- ✓ Use SSH keys instead of passwords
- ✓ Keep software up to date

### Backups

- ✓ Automate backups
- ✓ Store off-server
- ✓ Test restores regularly
- ✓ Encrypt sensitive data
- ✓ Document restore procedures

### Monitoring

- ✓ Set up alerts for critical issues
- ✓ Review logs regularly
- ✓ Monitor resource usage trends
- ✓ Document baseline performance

## Useful Scripts

All scripts are in `/path/to/scripts/`:

- **install.sh** - Install on new server
- **backup.sh** - Create full backup
- **verify.sh** - Verify system health
- **uninstall.sh** - Remove all components

Custom scripts can be added to `/usr/local/bin/` for system-wide access.

## Getting Help

1. **Check documentation** - This guide and TROUBLESHOOTING.md
2. **Review logs** - Often tells you what's wrong
3. **Search online** - Many common issues documented
4. **Contact system owner** - For application-specific issues
5. **Community forums** - Snipe-IT has active community

---

**Document Version:** 1.0
**Last Updated:** $(date)
