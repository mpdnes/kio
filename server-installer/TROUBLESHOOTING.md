# Troubleshooting Guide

## Common Installation Issues

### Apache Won't Start

**Symptoms:**
```bash
sudo systemctl status apache2
# Shows: failed or inactive
```

**Solutions:**

1. **Check configuration syntax:**
   ```bash
   sudo apache2ctl configtest
   ```
   Look for errors and fix them in the reported files.

2. **Check if ports are already in use:**
   ```bash
   sudo netstat -tlnp | grep -E ':(80|443|8080|8443)'
   # or
   sudo lsof -i :80
   ```
   Kill conflicting processes or change ports in `/etc/apache2/ports.conf`

3. **Check error logs:**
   ```bash
   sudo tail -50 /var/log/apache2/error.log
   ```

4. **Verify required modules are enabled:**
   ```bash
   apache2ctl -M | grep -E '(ssl|wsgi|rewrite|headers)'
   ```
   Enable missing modules:
   ```bash
   sudo a2enmod ssl rewrite headers wsgi
   sudo systemctl restart apache2
   ```

### Database Connection Failed

**Symptoms:**
- Snipe-IT shows database connection error
- Kiosk can't connect to database

**Solutions:**

1. **Verify MariaDB is running:**
   ```bash
   sudo systemctl status mariadb
   sudo systemctl restart mariadb
   ```

2. **Test database credentials:**
   ```bash
   # For Snipe-IT
   mysql -u snipeit_user -p snipeit
   # Enter password from /var/www/html/snipeit/.env
   ```

3. **Check .env file settings:**
   ```bash
   sudo nano /var/www/html/snipeit/.env
   ```
   Verify:
   - `DB_HOST=localhost`
   - `DB_DATABASE=snipeit`
   - `DB_USERNAME=snipeit_user`
   - `DB_PASSWORD=<correct password>`

4. **Reset database user password:**
   ```bash
   sudo mysql
   ALTER USER 'snipeit_user'@'localhost' IDENTIFIED BY 'NewPassword123!';
   FLUSH PRIVILEGES;
   exit;
   ```
   Update the password in the .env file accordingly.

### Snipe-IT Shows Blank Page or 500 Error

**Solutions:**

1. **Check Apache error logs:**
   ```bash
   sudo tail -100 /var/log/apache2/error.log
   ```

2. **Check Snipe-IT storage permissions:**
   ```bash
   sudo chown -R www-data:www-data /var/www/html/snipeit/storage
   sudo chmod -R 775 /var/www/html/snipeit/storage
   sudo chmod -R 775 /var/www/html/snipeit/public/uploads
   ```

3. **Clear Snipe-IT cache:**
   ```bash
   cd /var/www/html/snipeit
   sudo php artisan cache:clear
   sudo php artisan config:clear
   sudo php artisan view:clear
   ```

4. **Check PHP error logs:**
   ```bash
   sudo tail -50 /var/log/apache2/snipeit_error.log
   ```

5. **Verify .env file exists and is readable:**
   ```bash
   sudo ls -la /var/www/html/snipeit/.env
   # Should show: -rw-r----- www-data www-data
   ```

### Kiosk Application Issues

**Symptoms:**
- 500 Internal Server Error
- Module not found errors
- WSGI errors

**Solutions:**

1. **Check WSGI logs:**
   ```bash
   sudo tail -100 /var/log/apache2/kiosk_error.log
   ```

2. **Verify Python virtual environment:**
   ```bash
   ls -la /var/www/kiosk/.kiosk/
   # Should show bin/ lib/ etc.
   ```

3. **Reinstall Python dependencies:**
   ```bash
   cd /var/www/kiosk
   source .kiosk/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   deactivate
   ```

4. **Check .env file:**
   ```bash
   sudo nano /var/www/kiosk/.env
   ```
   Ensure all required variables are set.

5. **Verify WSGI configuration points to correct paths:**
   ```bash
   sudo nano /etc/apache2/sites-available/kiosk.conf
   ```
   Check:
   - `python-path=/var/www/kiosk`
   - `python-home=/var/www/kiosk/.kiosk`
   - `WSGIScriptAlias / /var/www/kiosk/app.wsgi`

6. **Fix permissions:**
   ```bash
   sudo chown -R ubuntu:www-data /var/www/kiosk
   sudo chmod -R 755 /var/www/kiosk
   sudo chmod 640 /var/www/kiosk/.env
   ```

7. **Test Python app manually:**
   ```bash
   cd /var/www/kiosk
   source .kiosk/bin/activate
   python app.wsgi
   # Look for import errors or configuration issues
   ```

### SSL Certificate Issues

**Symptoms:**
- Browser shows "Not Secure" or certificate warnings
- SSL handshake errors in logs

**Solutions:**

1. **Verify certificates exist:**
   ```bash
   ls -la /etc/ssl/certs/kiosk/kiosk.crt
   ls -la /etc/ssl/private/kiosk/kiosk.key
   ls -la /etc/ssl/certs/snipeit.crt
   ls -la /etc/ssl/private/snipeit.key
   ```

2. **Regenerate self-signed certificates:**
   ```bash
   # For Kiosk
   sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
       -keyout /etc/ssl/private/kiosk/kiosk.key \
       -out /etc/ssl/certs/kiosk/kiosk.crt \
       -subj "/C=US/ST=State/L=City/O=Org/CN=YOUR_IP"

   # For Snipe-IT
   sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
       -keyout /etc/ssl/private/snipeit.key \
       -out /etc/ssl/certs/snipeit.crt \
       -subj "/C=US/ST=State/L=City/O=Org/CN=YOUR_IP"

   sudo systemctl restart apache2
   ```

3. **For production, use Let's Encrypt:**
   ```bash
   sudo apt install certbot python3-certbot-apache
   sudo certbot --apache -d yourdomain.com
   ```

### Firewall Blocking Access

**Symptoms:**
- Can't access websites from external IP
- Connection timeout errors

**Solutions:**

1. **Check firewall status:**
   ```bash
   sudo ufw status verbose
   ```

2. **Ensure required ports are open:**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 8080/tcp
   sudo ufw allow 8443/tcp
   sudo ufw reload
   ```

3. **Check if Apache is listening:**
   ```bash
   sudo netstat -tlnp | grep apache
   # Should show ports 80, 443, 8080, 8443
   ```

4. **Test locally first:**
   ```bash
   curl http://localhost/
   curl http://localhost:8080/
   ```
   If this works but external access doesn't, check cloud provider security groups.

### Permission Denied Errors

**Solutions:**

1. **Fix Snipe-IT permissions:**
   ```bash
   sudo chown -R www-data:www-data /var/www/html/snipeit
   sudo chmod -R 755 /var/www/html/snipeit
   sudo chmod -R 775 /var/www/html/snipeit/storage
   sudo chmod -R 775 /var/www/html/snipeit/public/uploads
   ```

2. **Fix Kiosk permissions:**
   ```bash
   sudo chown -R ubuntu:www-data /var/www/kiosk
   sudo chmod -R 755 /var/www/kiosk
   sudo chmod 640 /var/www/kiosk/.env
   ```

3. **Check SELinux (if enabled):**
   ```bash
   getenforce
   # If Enforcing, you may need to adjust policies
   sudo setenforce 0  # Temporary disable to test
   ```

## Database Issues

### Can't Import Database

**Solutions:**

1. **Check SQL file:**
   ```bash
   head -20 databases/snipeit.sql
   # Verify it looks like valid SQL
   ```

2. **Import with error logging:**
   ```bash
   sudo mysql snipeit < databases/snipeit.sql 2> import_errors.log
   cat import_errors.log
   ```

3. **Import with verbose output:**
   ```bash
   sudo mysql -v snipeit < databases/snipeit.sql
   ```

### Database Too Large

**Solutions:**

1. **Increase MySQL limits:**
   ```bash
   sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
   ```
   Add/modify:
   ```
   max_allowed_packet = 256M
   ```
   Restart:
   ```bash
   sudo systemctl restart mariadb
   ```

## Performance Issues

### Site Loading Slowly

**Solutions:**

1. **Check system resources:**
   ```bash
   top
   free -h
   df -h
   ```

2. **Check Apache processes:**
   ```bash
   ps aux | grep apache2 | wc -l
   ```

3. **Optimize Apache:**
   ```bash
   sudo nano /etc/apache2/mods-available/mpm_prefork.conf
   ```
   Adjust based on available RAM.

4. **Enable PHP OPcache:**
   ```bash
   sudo apt install php8.3-opcache
   sudo systemctl restart apache2
   ```

5. **Check Redis:**
   ```bash
   sudo systemctl status redis-server
   redis-cli ping  # Should return PONG
   ```

## Getting More Help

### Useful Commands for Diagnostics

```bash
# System info
uname -a
lsb_release -a

# Check all services
sudo systemctl status apache2 mariadb redis-server

# Check listening ports
sudo netstat -tlnp

# Check recent logs
sudo journalctl -xe

# Check disk space
df -h

# Check memory
free -h

# Apache configuration test
sudo apache2ctl configtest

# List enabled Apache sites
ls -la /etc/apache2/sites-enabled/

# List enabled Apache modules
apache2ctl -M
```

### Log Files Locations

```
/var/log/apache2/error.log           # Main Apache errors
/var/log/apache2/access.log          # Apache access logs
/var/log/apache2/kiosk_error.log     # Kiosk app errors
/var/log/apache2/snipeit_error.log   # Snipe-IT errors
/var/log/mysql/error.log             # MySQL errors
/var/log/syslog                      # System logs
```

### Still Having Issues?

1. Run the verification script:
   ```bash
   bash scripts/verify.sh
   ```

2. Check all configuration files for typos

3. Review the installation log output for any warnings

4. Compare working configuration with your setup

5. Try reinstalling specific components (Apache, MariaDB, etc.)
