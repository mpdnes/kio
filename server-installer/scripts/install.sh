#!/bin/bash

###############################################################################
# Server Installation Script
# This script automates the installation of the server environment
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root or with sudo"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

log_info "Starting server installation..."
log_info "Base directory: $BASE_DIR"

###############################################################################
# Step 1: Read Configuration
###############################################################################

log_info "Step 1: Reading configuration..."

if [ -f "$BASE_DIR/config/NEW_SERVER_IP.txt" ]; then
    NEW_SERVER_IP=$(cat "$BASE_DIR/config/NEW_SERVER_IP.txt" | tr -d '[:space:]')
    log_info "New server IP: $NEW_SERVER_IP"
else
    log_warn "NEW_SERVER_IP.txt not found. You'll need to manually update IP addresses in configs."
    read -p "Enter new server IP address (or press Enter to skip): " NEW_SERVER_IP
fi

###############################################################################
# Step 2: Update System
###############################################################################

log_info "Step 2: Updating system packages..."
apt update
apt upgrade -y

###############################################################################
# Step 3: Install Required Packages
###############################################################################

log_info "Step 3: Installing required packages..."

# Core packages
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
    git \
    curl \
    unzip \
    ufw

log_info "Packages installed successfully"

###############################################################################
# Step 4: Configure Apache
###############################################################################

log_info "Step 4: Configuring Apache..."

# Enable required modules
a2enmod ssl
a2enmod rewrite
a2enmod headers
a2enmod wsgi

# Copy ports configuration
if [ -f "$BASE_DIR/config/apache/ports.conf" ]; then
    cp "$BASE_DIR/config/apache/ports.conf" /etc/apache2/ports.conf
    log_info "Apache ports configured"
fi

# Add port 8080 and 8443 if not present
if ! grep -q "Listen 8080" /etc/apache2/ports.conf; then
    echo "Listen 8080" >> /etc/apache2/ports.conf
fi

if ! grep -q "Listen 8443" /etc/apache2/ports.conf; then
    echo "Listen 8443" >> /etc/apache2/ports.conf
fi

###############################################################################
# Step 5: Configure MariaDB
###############################################################################

log_info "Step 5: Configuring MariaDB..."

systemctl start mariadb
systemctl enable mariadb

log_warn "Please run 'mysql_secure_installation' after this script completes!"
log_warn "Setting temporary root password for database operations..."

# Set temporary root password for installation
TEMP_DB_PASS="TempInstall$(date +%s)"
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$TEMP_DB_PASS';" || true

# Create Snipe-IT database
log_info "Creating Snipe-IT database..."
mysql -u root -p"$TEMP_DB_PASS" -e "CREATE DATABASE IF NOT EXISTS snipeit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p"$TEMP_DB_PASS" -e "CREATE USER IF NOT EXISTS 'snipeit_user'@'localhost' IDENTIFIED BY 'ChangeThisPassword123!';"
mysql -u root -p"$TEMP_DB_PASS" -e "GRANT ALL PRIVILEGES ON snipeit.* TO 'snipeit_user'@'localhost';"
mysql -u root -p"$TEMP_DB_PASS" -e "FLUSH PRIVILEGES;"

# Import Snipe-IT database
if [ -f "$BASE_DIR/databases/snipeit.sql" ]; then
    log_info "Importing Snipe-IT database..."
    mysql -u root -p"$TEMP_DB_PASS" snipeit < "$BASE_DIR/databases/snipeit.sql"
    log_info "Database imported successfully"
else
    log_warn "snipeit.sql not found, skipping database import"
fi

log_warn "Temporary DB root password: $TEMP_DB_PASS"
log_warn "CHANGE THIS IMMEDIATELY after installation!"

###############################################################################
# Step 6: Deploy Snipe-IT
###############################################################################

log_info "Step 6: Deploying Snipe-IT..."

if [ -f "$BASE_DIR/applications/snipeit.tar.gz" ]; then
    mkdir -p /var/www/html
    cd /var/www/html
    tar -xzf "$BASE_DIR/applications/snipeit.tar.gz"

    # Set permissions
    chown -R www-data:www-data /var/www/html/snipeit
    chmod -R 755 /var/www/html/snipeit
    chmod -R 775 /var/www/html/snipeit/storage
    chmod -R 775 /var/www/html/snipeit/public/uploads

    log_info "Snipe-IT deployed successfully"
    log_warn "Update /var/www/html/snipeit/.env with new database credentials!"
else
    log_error "snipeit.tar.gz not found!"
fi

###############################################################################
# Step 7: Deploy Kiosk Application
###############################################################################

log_info "Step 7: Setting up Kiosk application placeholder..."
log_warn "You need to clone your kiosk app from GitHub manually:"
log_warn "  cd /var/www"
log_warn "  git clone YOUR_REPO_URL kiosk"
log_warn "  cd kiosk"
log_warn "  python3 -m venv .kiosk"
log_warn "  source .kiosk/bin/activate"
log_warn "  pip install -r requirements.txt"
log_warn "  cp .env.template .env  # Then edit .env"
log_warn "  sudo chown -R ubuntu:www-data /var/www/kiosk"

mkdir -p /var/www/kiosk
echo "Placeholder - clone from GitHub" > /var/www/kiosk/README.txt

###############################################################################
# Step 8: Configure SSL Certificates
###############################################################################

log_info "Step 8: Generating self-signed SSL certificates..."

# Create directories
mkdir -p /etc/ssl/certs/kiosk
mkdir -p /etc/ssl/private/kiosk
mkdir -p /etc/ssl/private

# Generate certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/kiosk/kiosk.key \
    -out /etc/ssl/certs/kiosk/kiosk.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=${NEW_SERVER_IP:-localhost}"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/snipeit.key \
    -out /etc/ssl/certs/snipeit.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=${NEW_SERVER_IP:-localhost}"

chmod 600 /etc/ssl/private/kiosk/kiosk.key
chmod 600 /etc/ssl/private/snipeit.key

log_info "SSL certificates generated"
log_warn "These are self-signed! Use Let's Encrypt for production."

###############################################################################
# Step 9: Configure Apache Virtual Hosts
###############################################################################

log_info "Step 9: Configuring Apache virtual hosts..."

# Copy virtual host configurations
if [ -f "$BASE_DIR/config/apache/snipeit.conf" ]; then
    cp "$BASE_DIR/config/apache/snipeit.conf" /etc/apache2/sites-available/

    # Update IP address if provided
    if [ -n "$NEW_SERVER_IP" ]; then
        sed -i "s/ServerName .*/ServerName $NEW_SERVER_IP/" /etc/apache2/sites-available/snipeit.conf
    fi

    a2ensite snipeit.conf
    log_info "Snipe-IT virtual host configured"
fi

if [ -f "$BASE_DIR/config/apache/kiosk.conf" ]; then
    cp "$BASE_DIR/config/apache/kiosk.conf" /etc/apache2/sites-available/

    # Update IP address if provided
    if [ -n "$NEW_SERVER_IP" ]; then
        sed -i "s/ServerName .*/ServerName $NEW_SERVER_IP/" /etc/apache2/sites-available/kiosk.conf
    fi

    # Don't enable yet since kiosk isn't deployed
    log_info "Kiosk virtual host configured (not enabled - enable after cloning repo)"
    log_warn "Run 'sudo a2ensite kiosk.conf' after deploying kiosk"
fi

# Disable default site
a2dissite 000-default.conf || true

###############################################################################
# Step 10: Configure Firewall
###############################################################################

log_info "Step 10: Configuring firewall..."

ufw --force enable
ufw allow 22/tcp comment "SSH"
ufw allow 80/tcp comment "HTTP Apache"
ufw allow 443/tcp comment "HTTPS Apache"
ufw allow 5000/tcp
ufw allow 8080/tcp comment "HTTP Kiosk"
ufw allow 8443/tcp comment "HTTPS Kiosk"

log_info "Firewall configured"

###############################################################################
# Step 11: Start Services
###############################################################################

log_info "Step 11: Starting services..."

systemctl enable apache2
systemctl enable mariadb
systemctl enable redis-server

systemctl restart apache2
systemctl restart mariadb
systemctl restart redis-server

log_info "Services started"

###############################################################################
# Step 12: Verification
###############################################################################

log_info "Step 12: Verifying installation..."

# Check services
if systemctl is-active --quiet apache2; then
    log_info "✓ Apache is running"
else
    log_error "✗ Apache is not running"
fi

if systemctl is-active --quiet mariadb; then
    log_info "✓ MariaDB is running"
else
    log_error "✗ MariaDB is not running"
fi

if systemctl is-active --quiet redis-server; then
    log_info "✓ Redis is running"
else
    log_error "✗ Redis is not running"
fi

###############################################################################
# Final Instructions
###############################################################################

echo ""
echo "=========================================================================="
log_info "Installation Complete!"
echo "=========================================================================="
echo ""
log_warn "IMPORTANT POST-INSTALLATION STEPS:"
echo ""
echo "1. Secure MariaDB:"
echo "   sudo mysql_secure_installation"
echo ""
echo "2. Update database password in Snipe-IT:"
echo "   sudo nano /var/www/html/snipeit/.env"
echo "   Change DB_PASSWORD to match your new password"
echo ""
echo "3. Clone and set up Kiosk application:"
echo "   cd /var/www"
echo "   sudo git clone YOUR_GITHUB_REPO_URL kiosk"
echo "   cd kiosk"
echo "   python3 -m venv .kiosk"
echo "   source .kiosk/bin/activate"
echo "   pip install -r requirements.txt"
echo "   cp .env.template .env"
echo "   nano .env  # Update with your settings"
echo "   sudo chown -R ubuntu:www-data /var/www/kiosk"
echo "   sudo a2ensite kiosk.conf"
echo "   sudo systemctl reload apache2"
echo ""
echo "4. Test the applications:"
echo "   Snipe-IT: http://${NEW_SERVER_IP:-YOUR_IP}/"
echo "   Kiosk: http://${NEW_SERVER_IP:-YOUR_IP}:8080/"
echo ""
echo "5. For production, install Let's Encrypt certificates:"
echo "   sudo apt install certbot python3-certbot-apache"
echo "   sudo certbot --apache"
echo ""
log_warn "Temporary DB root password: $TEMP_DB_PASS"
log_warn "CHANGE THIS IMMEDIATELY!"
echo ""
echo "=========================================================================="
