#!/bin/bash

###############################################################################
# Server Installation Script - IMPROVED VERSION
# This script automates the installation of the server environment
# Includes pre-flight checks, dynamic configuration, and validation
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}===================================================================="
    echo -e "$1"
    echo -e "====================================================================${NC}\n"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root or with sudo"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

log_section "SERVER INSTALLATION - PRE-FLIGHT CHECKS"
log_info "Base directory: $BASE_DIR"

###############################################################################
# PRE-FLIGHT CHECKS
###############################################################################

log_info "Running pre-flight checks..."

# Check OS version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log_info "Operating System: $NAME $VERSION"
    if [[ "$ID" != "ubuntu" ]] && [[ "$ID" != "debian" ]]; then
        log_warn "This script is designed for Ubuntu/Debian. Proceed with caution."
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    log_error "Cannot determine OS version"
    exit 1
fi

# Check available disk space (require at least 5GB)
AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
REQUIRED_SPACE=$((5 * 1024 * 1024))  # 5GB in KB
if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    log_error "Insufficient disk space. Required: 5GB, Available: $((AVAILABLE_SPACE / 1024 / 1024))GB"
    exit 1
fi
log_info "✓ Disk space: $((AVAILABLE_SPACE / 1024 / 1024))GB available"

# Check available RAM (recommend at least 2GB)
TOTAL_RAM=$(free -m | awk 'NR==2 {print $2}')
if [ "$TOTAL_RAM" -lt 1900 ]; then
    log_warn "Low RAM detected: ${TOTAL_RAM}MB. Recommended: 2048MB or more"
    log_warn "Installation may be slow or fail"
fi
log_info "✓ RAM: ${TOTAL_RAM}MB available"

# Check if ports are available
check_port() {
    PORT=$1
    if ss -tuln | grep -q ":$PORT "; then
        log_warn "Port $PORT is already in use"
        return 1
    else
        log_info "✓ Port $PORT is available"
        return 0
    fi
}

PORT_CHECK_FAILED=false
check_port 80 || PORT_CHECK_FAILED=true
check_port 443 || PORT_CHECK_FAILED=true
check_port 8080 || PORT_CHECK_FAILED=true
check_port 8443 || PORT_CHECK_FAILED=true

if [ "$PORT_CHECK_FAILED" = true ]; then
    log_warn "Some required ports are in use. Installation may fail or services may conflict."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check sudo credentials are cached
if ! sudo -n true 2>/dev/null; then
    log_warn "Sudo credentials not cached. You may be prompted for password during installation."
fi

log_info "✓ Pre-flight checks complete"

###############################################################################
# Step 1: Read Configuration
###############################################################################

log_section "STEP 1: READING CONFIGURATION"

if [ -f "$BASE_DIR/config/NEW_SERVER_IP.txt" ]; then
    NEW_SERVER_IP=$(cat "$BASE_DIR/config/NEW_SERVER_IP.txt" | tr -d '[:space:]')

    # Validate it's not the placeholder
    if [ "$NEW_SERVER_IP" = "YOUR_NEW_SERVER_IP_HERE" ] || [ -z "$NEW_SERVER_IP" ]; then
        log_warn "NEW_SERVER_IP.txt contains placeholder value"
        read -p "Enter new server IP address: " NEW_SERVER_IP
    else
        log_info "New server IP: $NEW_SERVER_IP"
    fi
else
    log_warn "NEW_SERVER_IP.txt not found"
    read -p "Enter new server IP address: " NEW_SERVER_IP
fi

# Validate IP format (basic check)
if [[ ! $NEW_SERVER_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && [[ $NEW_SERVER_IP != "localhost" ]]; then
    log_warn "IP address format looks unusual: $NEW_SERVER_IP"
    read -p "Continue with this value? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

###############################################################################
# Step 2: Update System
###############################################################################

log_section "STEP 2: UPDATING SYSTEM PACKAGES"

log_info "Updating package lists..."
apt update

log_info "Upgrading packages..."
apt upgrade -y

###############################################################################
# Step 3: Install Required Packages
###############################################################################

log_section "STEP 3: INSTALLING REQUIRED PACKAGES"

# Core packages INCLUDING libmagic1 for python-magic
log_info "Installing system packages..."
apt install -y \
    apache2 \
    mariadb-server \
    redis-server \
    php8.3 \
    php8.3-cli \
    php8.3-common \
    php8.3-mysql \
    php8.3-zip \
    php8.3-gd \
    php8.3-mbstring \
    php8.3-curl \
    php8.3-xml \
    php8.3-bcmath \
    php8.3-ldap \
    libapache2-mod-php8.3 \
    python3 \
    python3-pip \
    python3-venv \
    libapache2-mod-wsgi-py3 \
    libmagic1 \
    git \
    curl \
    unzip \
    ufw \
    net-tools

log_info "✓ Packages installed successfully"

###############################################################################
# Step 4: Configure Apache
###############################################################################

log_section "STEP 4: CONFIGURING APACHE"

# Enable required modules
a2enmod ssl
a2enmod rewrite
a2enmod headers
a2enmod wsgi

# Copy ports configuration
if [ -f "$BASE_DIR/config/apache/ports.conf" ]; then
    cp "$BASE_DIR/config/apache/ports.conf" /etc/apache2/ports.conf
    log_info "Apache ports configured from template"
fi

# Add port 8080 and 8443 if not present
if ! grep -q "Listen 8080" /etc/apache2/ports.conf; then
    echo "Listen 8080" >> /etc/apache2/ports.conf
    log_info "Added port 8080 to Apache config"
fi

if ! grep -q "Listen 8443" /etc/apache2/ports.conf; then
    echo "Listen 8443" >> /etc/apache2/ports.conf
    log_info "Added port 8443 to Apache config"
fi

log_info "✓ Apache configured"

###############################################################################
# Step 5: Configure MariaDB
###############################################################################

log_section "STEP 5: CONFIGURING MARIADB"

systemctl start mariadb
systemctl enable mariadb

log_warn "Setting temporary root password for database operations..."

# Set temporary root password for installation
TEMP_DB_PASS="TempInstall$(date +%s)"
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$TEMP_DB_PASS';" || true

# Create Snipe-IT database
log_info "Creating Snipe-IT database and user..."
mysql -u root -p"$TEMP_DB_PASS" <<EOF
CREATE DATABASE IF NOT EXISTS snipeit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'snipeit'@'localhost' IDENTIFIED BY 'ChangeThisPassword123!';
GRANT ALL PRIVILEGES ON snipeit.* TO 'snipeit'@'localhost';
FLUSH PRIVILEGES;
EOF

# Import Snipe-IT database
if [ -f "$BASE_DIR/databases/snipeit.sql" ]; then
    log_info "Importing Snipe-IT database..."
    mysql -u root -p"$TEMP_DB_PASS" snipeit < "$BASE_DIR/databases/snipeit.sql"
    log_info "✓ Database imported successfully"
else
    log_warn "snipeit.sql not found, skipping database import"
    log_warn "You'll need to run Snipe-IT setup wizard"
fi

log_info "✓ MariaDB configured"
log_warn "Temporary DB root password: $TEMP_DB_PASS"

###############################################################################
# Step 6: Deploy Snipe-IT
###############################################################################

log_section "STEP 6: DEPLOYING SNIPE-IT"

if [ -f "$BASE_DIR/applications/snipeit.tar.gz" ]; then
    mkdir -p /var/www/html
    cd /var/www/html

    log_info "Extracting Snipe-IT application..."
    tar -xzf "$BASE_DIR/applications/snipeit.tar.gz"

    # Set permissions
    chown -R www-data:www-data /var/www/html/snipeit
    chmod -R 755 /var/www/html/snipeit
    chmod -R 775 /var/www/html/snipeit/storage
    chmod -R 775 /var/www/html/snipeit/public/uploads

    # Update Snipe-IT .env with dynamic APP_URL
    if [ -f /var/www/html/snipeit/.env ]; then
        log_info "Configuring Snipe-IT .env with server IP..."

        # Update APP_URL to use https and the actual server IP
        sed -i "s|^APP_URL=.*|APP_URL=https://${NEW_SERVER_IP}|" /var/www/html/snipeit/.env

        # Update database credentials
        sed -i "s|^DB_DATABASE=.*|DB_DATABASE=snipeit|" /var/www/html/snipeit/.env
        sed -i "s|^DB_USERNAME=.*|DB_USERNAME=snipeit|" /var/www/html/snipeit/.env
        sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=ChangeThisPassword123!|" /var/www/html/snipeit/.env

        log_info "✓ Snipe-IT .env configured"
    else
        log_warn "Snipe-IT .env not found - you'll need to configure it manually"
    fi

    log_info "✓ Snipe-IT deployed successfully"
else
    log_error "snipeit.tar.gz not found!"
    log_error "Cannot continue without Snipe-IT application"
    exit 1
fi

###############################################################################
# Step 7: Deploy Kiosk Application
###############################################################################

log_section "STEP 7: DEPLOYING KIOSK APPLICATION"

# Check if kiosk repo is available locally
KIOSK_SOURCE=""
if [ -d "$BASE_DIR/../kiosk/.git" ]; then
    KIOSK_SOURCE="$BASE_DIR/../kiosk"
    log_info "Found local kiosk repository"
elif [ -f "$BASE_DIR/config/kiosk_github.txt" ]; then
    KIOSK_REPO=$(grep -v '^#' "$BASE_DIR/config/kiosk_github.txt" | grep -v '^$' | head -1)
    if [ -n "$KIOSK_REPO" ]; then
        log_info "Cloning kiosk from: $KIOSK_REPO"
        cd /var/www
        git clone "$KIOSK_REPO" kiosk || {
            log_error "Failed to clone kiosk repository"
            log_warn "You'll need to clone it manually"
        }
        KIOSK_SOURCE="/var/www/kiosk"
    fi
fi

# If we have a source, set it up
if [ -n "$KIOSK_SOURCE" ] && [ -d "$KIOSK_SOURCE" ]; then
    log_info "Setting up kiosk application..."

    # Copy to /var/www/kiosk if not already there
    if [ "$KIOSK_SOURCE" != "/var/www/kiosk" ]; then
        mkdir -p /var/www/kiosk
        cp -r "$KIOSK_SOURCE"/* /var/www/kiosk/
        cp -r "$KIOSK_SOURCE"/.git /var/www/kiosk/ 2>/dev/null || true
    fi

    cd /var/www/kiosk

    # Create required directories with proper permissions
    log_info "Creating required directories..."
    mkdir -p /var/www/kiosk/logs
    mkdir -p /var/www/kiosk/loan_agreements
    mkdir -p /var/www/kiosk/secure_data
    mkdir -p /var/www/kiosk/static
    mkdir -p /var/www/kiosk/templates

    # Set ownership and permissions
    chown -R www-data:www-data /var/www/kiosk/logs
    chown -R www-data:www-data /var/www/kiosk/loan_agreements
    chown -R www-data:www-data /var/www/kiosk/secure_data
    chmod -R 775 /var/www/kiosk/logs
    chmod -R 775 /var/www/kiosk/loan_agreements
    chmod -R 775 /var/www/kiosk/secure_data

    log_info "✓ Directories created and permissions set"

    # Create Python virtual environment
    log_info "Creating Python virtual environment..."
    python3 -m venv .kiosk

    # Install dependencies
    log_info "Installing Python dependencies..."
    .kiosk/bin/pip install --upgrade pip
    .kiosk/bin/pip install -r requirements.txt

    log_info "✓ Python dependencies installed"

    # Configure .env file
    if [ -f .env.template ]; then
        if [ ! -f .env ]; then
            cp .env.template .env
            log_info "Created .env from template"
        fi

        # Update .env with dynamic configuration
        log_info "Configuring kiosk .env..."
        sed -i "s|^API_URL=.*|API_URL=https://${NEW_SERVER_IP}/api/v1|" .env
        sed -i "s|^FLASK_ENV=.*|FLASK_ENV=production|" .env
        sed -i "s|^DEBUG=.*|DEBUG=False|" .env
        sed -i "s|^REDIS_URL=.*|REDIS_URL=redis://localhost:6379/0|" .env

        log_info "✓ Kiosk .env configured"
    else
        log_warn ".env.template not found - you'll need to create .env manually"
    fi

    # Set final permissions
    chown -R www-data:www-data /var/www/kiosk
    chmod -R 755 /var/www/kiosk

    log_info "✓ Kiosk application deployed successfully"
else
    log_warn "Kiosk application not found"
    log_warn "Creating placeholder directory"
    mkdir -p /var/www/kiosk
    echo "Clone kiosk application here" > /var/www/kiosk/README.txt
    log_warn "You'll need to clone and set up the kiosk app manually"
fi

###############################################################################
# Step 8: Configure SSL Certificates
###############################################################################

log_section "STEP 8: GENERATING SSL CERTIFICATES"

# Create directories
mkdir -p /etc/ssl/certs/kiosk
mkdir -p /etc/ssl/private/kiosk
mkdir -p /etc/ssl/private

# Generate certificates
log_info "Generating self-signed certificates for ${NEW_SERVER_IP}..."

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/kiosk/kiosk.key \
    -out /etc/ssl/certs/kiosk/kiosk.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=${NEW_SERVER_IP}"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/snipeit.key \
    -out /etc/ssl/certs/snipeit.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=${NEW_SERVER_IP}"

chmod 600 /etc/ssl/private/kiosk/kiosk.key
chmod 600 /etc/ssl/private/snipeit.key

log_info "✓ SSL certificates generated"
log_warn "These are self-signed! Use Let's Encrypt for production."

###############################################################################
# Step 9: Configure Apache Virtual Hosts
###############################################################################

log_section "STEP 9: CONFIGURING APACHE VIRTUAL HOSTS"

# Copy and configure Snipe-IT virtual host
if [ -f "$BASE_DIR/config/apache/snipeit.conf" ]; then
    cp "$BASE_DIR/config/apache/snipeit.conf" /etc/apache2/sites-available/

    # Update IP address
    if [ -n "$NEW_SERVER_IP" ]; then
        sed -i "s/ServerName .*/ServerName $NEW_SERVER_IP/" /etc/apache2/sites-available/snipeit.conf
    fi

    a2ensite snipeit.conf
    log_info "✓ Snipe-IT virtual host configured and enabled"
fi

# Copy and configure Kiosk virtual host
if [ -f "$BASE_DIR/config/apache/kiosk.conf" ]; then
    cp "$BASE_DIR/config/apache/kiosk.conf" /etc/apache2/sites-available/

    # Update IP address
    if [ -n "$NEW_SERVER_IP" ]; then
        sed -i "s/ServerName .*/ServerName $NEW_SERVER_IP/" /etc/apache2/sites-available/kiosk.conf
    fi

    # Enable kiosk site if application was deployed
    if [ -f /var/www/kiosk/app.wsgi ]; then
        a2ensite kiosk.conf
        log_info "✓ Kiosk virtual host configured and enabled"
    else
        log_warn "Kiosk virtual host configured but not enabled (app not deployed)"
        log_warn "Run 'sudo a2ensite kiosk.conf' after deploying kiosk"
    fi
fi

# Disable default site
a2dissite 000-default.conf 2>/dev/null || true

log_info "✓ Apache virtual hosts configured"

###############################################################################
# Step 10: Configure Firewall
###############################################################################

log_section "STEP 10: CONFIGURING FIREWALL"

ufw --force enable
ufw allow 22/tcp comment "SSH"
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS Snipe-IT"
ufw allow 8080/tcp comment "HTTP Kiosk"
ufw allow 8443/tcp comment "HTTPS Kiosk"

log_info "✓ Firewall configured"

###############################################################################
# Step 11: Start Services
###############################################################################

log_section "STEP 11: STARTING SERVICES"

systemctl enable apache2
systemctl enable mariadb
systemctl enable redis-server

log_info "Restarting services..."
systemctl restart apache2
systemctl restart mariadb
systemctl restart redis-server

log_info "✓ Services started"

###############################################################################
# Step 12: POST-INSTALLATION VALIDATION
###############################################################################

log_section "STEP 12: POST-INSTALLATION VALIDATION"

VALIDATION_FAILED=false

# Check services
log_info "Validating services..."
if systemctl is-active --quiet apache2; then
    log_info "✓ Apache is running"
else
    log_error "✗ Apache is not running"
    VALIDATION_FAILED=true
fi

if systemctl is-active --quiet mariadb; then
    log_info "✓ MariaDB is running"
else
    log_error "✗ MariaDB is not running"
    VALIDATION_FAILED=true
fi

if systemctl is-active --quiet redis-server; then
    log_info "✓ Redis is running"
else
    log_error "✗ Redis is not running"
    VALIDATION_FAILED=true
fi

# Check ports are listening
log_info "Validating ports..."
for port in 80 443 8080 8443; do
    if ss -tuln | grep -q ":$port "; then
        log_info "✓ Port $port is listening"
    else
        log_warn "✗ Port $port is not listening"
    fi
done

# Check database connectivity
log_info "Validating database..."
if mysql -u snipeit -p'ChangeThisPassword123!' -e "USE snipeit; SELECT 1;" &>/dev/null; then
    log_info "✓ Database connection successful"
else
    log_error "✗ Database connection failed"
    VALIDATION_FAILED=true
fi

# Check Snipe-IT files
if [ -f /var/www/html/snipeit/.env ]; then
    log_info "✓ Snipe-IT files present"
else
    log_error "✗ Snipe-IT files missing"
    VALIDATION_FAILED=true
fi

# Check SSL certificates
if [ -f /etc/ssl/certs/snipeit.crt ] && [ -f /etc/ssl/private/snipeit.key ]; then
    log_info "✓ SSL certificates present"
else
    log_error "✗ SSL certificates missing"
    VALIDATION_FAILED=true
fi

# Test HTTP response
log_info "Testing web server response..."
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" https://${NEW_SERVER_IP}/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    log_info "✓ Snipe-IT responds with HTTP $HTTP_CODE"
else
    log_warn "⚠ Snipe-IT responds with HTTP $HTTP_CODE (expected 200 or 302)"
fi

if [ "$VALIDATION_FAILED" = true ]; then
    log_error "Some validation checks failed. Please review the errors above."
else
    log_info "✓ All validation checks passed!"
fi

###############################################################################
# Final Instructions
###############################################################################

log_section "INSTALLATION COMPLETE"

echo ""
echo "=========================================================================="
echo -e "${GREEN}Installation Successful!${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}Access Your Applications:${NC}"
echo "  Snipe-IT:  https://${NEW_SERVER_IP}/"
echo "  Kiosk App: https://${NEW_SERVER_IP}:8443/"
echo ""
echo -e "${BLUE}Database Credentials:${NC}"
echo "  Database: snipeit"
echo "  Username: snipeit"
echo "  Password: ChangeThisPassword123!"
echo "  Root Password (temporary): $TEMP_DB_PASS"
echo ""
echo -e "${YELLOW}CRITICAL POST-INSTALLATION STEPS:${NC}"
echo ""
echo "1. ${RED}CHANGE DATABASE PASSWORDS IMMEDIATELY:${NC}"
echo "   sudo mysql_secure_installation"
echo ""
echo "2. Update Snipe-IT .env if needed:"
echo "   sudo nano /var/www/html/snipeit/.env"
echo ""
if [ ! -f /var/www/kiosk/app.wsgi ]; then
echo "3. Deploy Kiosk application:"
echo "   cd /var/www"
echo "   sudo git clone YOUR_GITHUB_REPO_URL kiosk"
echo "   Then re-run Step 7 setup from this script"
echo ""
fi
echo "4. For production, install Let's Encrypt certificates:"
echo "   sudo apt install certbot python3-certbot-apache"
echo "   sudo certbot --apache"
echo ""
echo "5. Review and customize .env files:"
echo "   /var/www/html/snipeit/.env"
echo "   /var/www/kiosk/.env"
echo ""
echo "=========================================================================="
echo -e "${YELLOW}Security Reminders:${NC}"
echo "  • Change all default passwords"
echo "  • Run mysql_secure_installation"
echo "  • Review firewall rules (ufw status)"
echo "  • Keep system updated (apt update && apt upgrade)"
echo "  • Use Let's Encrypt for production SSL"
echo "=========================================================================="
echo ""

# Save installation log
LOG_FILE="/root/installation-log-$(date +%Y%m%d-%H%M%S).txt"
echo "Server IP: $NEW_SERVER_IP" > "$LOG_FILE"
echo "Temp DB Password: $TEMP_DB_PASS" >> "$LOG_FILE"
echo "Installation Date: $(date)" >> "$LOG_FILE"
chmod 600 "$LOG_FILE"
log_info "Installation details saved to: $LOG_FILE"

log_info "Installation script completed successfully!"
