#!/bin/bash

###############################################################################
# Server Uninstall/Cleanup Script
# Removes all installed applications and configurations
# WARNING: This will delete databases and applications!
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

echo "=========================================================================="
log_error "WARNING: This will remove all server applications and databases!"
echo "=========================================================================="
echo ""
echo "This script will:"
echo "  - Stop all services (Apache, MariaDB, Redis)"
echo "  - Remove Snipe-IT and Kiosk applications"
echo "  - DROP all databases (including data!)"
echo "  - Remove Apache configurations"
echo "  - Remove SSL certificates"
echo "  - Optionally remove installed packages"
echo ""
log_warn "This action CANNOT be undone!"
echo ""
read -p "Are you absolutely sure? Type 'DELETE EVERYTHING' to confirm: " CONFIRM

if [ "$CONFIRM" != "DELETE EVERYTHING" ]; then
    log_info "Uninstall cancelled."
    exit 0
fi

echo ""
log_warn "Last chance! Creating a backup first..."
read -p "Create a backup before removing? (y/n): " CREATE_BACKUP

if [ "$CREATE_BACKUP" == "y" ] || [ "$CREATE_BACKUP" == "Y" ]; then
    if [ -f "backup.sh" ]; then
        bash backup.sh
        log_info "Backup created. Proceeding with uninstall in 5 seconds..."
        sleep 5
    else
        log_warn "backup.sh not found. Proceeding without backup..."
    fi
fi

###############################################################################
# Stop Services
###############################################################################

log_info "Stopping services..."
systemctl stop apache2 || true
systemctl stop mariadb || true
systemctl stop redis-server || true
log_info "Services stopped"

###############################################################################
# Remove Databases
###############################################################################

log_info "Removing databases..."

# Start MariaDB temporarily to drop databases
systemctl start mariadb || true
sleep 2

read -p "Enter MariaDB root password: " -s DB_PASSWORD
echo ""

mysql -u root -p"$DB_PASSWORD" -e "DROP DATABASE IF EXISTS snipeit;" 2>/dev/null || log_warn "Could not drop snipeit database"
mysql -u root -p"$DB_PASSWORD" -e "DROP USER IF EXISTS 'snipeit_user'@'localhost';" 2>/dev/null || true

log_info "Databases removed"

###############################################################################
# Remove Applications
###############################################################################

log_info "Removing applications..."

# Remove Snipe-IT
if [ -d "/var/www/html/snipeit" ]; then
    rm -rf /var/www/html/snipeit
    log_info "✓ Snipe-IT removed"
fi

# Remove Kiosk
if [ -d "/var/www/kiosk" ]; then
    rm -rf /var/www/kiosk
    log_info "✓ Kiosk removed"
fi

###############################################################################
# Remove Apache Configurations
###############################################################################

log_info "Removing Apache configurations..."

# Disable sites
a2dissite kiosk.conf 2>/dev/null || true
a2dissite snipeit.conf 2>/dev/null || true

# Remove site configs
rm -f /etc/apache2/sites-available/kiosk.conf
rm -f /etc/apache2/sites-available/snipeit.conf
rm -f /etc/apache2/sites-enabled/kiosk.conf
rm -f /etc/apache2/sites-enabled/snipeit.conf

log_info "Apache configurations removed"

###############################################################################
# Remove SSL Certificates
###############################################################################

log_info "Removing SSL certificates..."

rm -rf /etc/ssl/certs/kiosk
rm -f /etc/ssl/certs/snipeit.crt
rm -f /etc/ssl/private/snipeit.key
rm -rf /etc/ssl/private/kiosk

log_info "SSL certificates removed"

###############################################################################
# Restore Default Apache Config
###############################################################################

log_info "Restoring default Apache configuration..."

# Restore default ports
cat > /etc/apache2/ports.conf <<EOF
# Default Apache ports configuration
Listen 80

<IfModule ssl_module>
    Listen 443
</IfModule>

<IfModule mod_gnutls.c>
    Listen 443
</IfModule>
EOF

# Enable default site
a2ensite 000-default.conf || true

###############################################################################
# Optional: Remove Packages
###############################################################################

echo ""
read -p "Remove installed packages (Apache, MariaDB, PHP, Redis)? (y/n): " REMOVE_PACKAGES

if [ "$REMOVE_PACKAGES" == "y" ] || [ "$REMOVE_PACKAGES" == "Y" ]; then
    log_warn "Removing packages..."

    apt-get remove --purge -y \
        apache2 \
        apache2-bin \
        apache2-data \
        apache2-utils \
        libapache2-mod-php* \
        libapache2-mod-wsgi-py3 \
        mariadb-server \
        mariadb-client \
        php8.3* \
        redis-server \
        2>/dev/null || log_warn "Some packages could not be removed"

    apt-get autoremove -y
    apt-get autoclean

    log_info "Packages removed"
else
    log_info "Packages kept (you can remove them manually later)"
fi

###############################################################################
# Optional: Reset Firewall
###############################################################################

echo ""
read -p "Reset firewall rules? (y/n): " RESET_FIREWALL

if [ "$RESET_FIREWALL" == "y" ] || [ "$RESET_FIREWALL" == "Y" ]; then
    log_warn "Resetting firewall..."
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp comment "SSH"
    ufw --force enable
    log_info "Firewall reset (only SSH allowed)"
else
    log_info "Firewall rules kept"
fi

###############################################################################
# Summary
###############################################################################

echo ""
echo "=========================================================================="
log_info "Uninstall Complete!"
echo "=========================================================================="
echo ""
echo "Removed:"
echo "  ✓ All databases and database users"
echo "  ✓ Snipe-IT and Kiosk applications"
echo "  ✓ Apache virtual host configurations"
echo "  ✓ SSL certificates"
echo ""

if [ "$REMOVE_PACKAGES" == "y" ] || [ "$REMOVE_PACKAGES" == "Y" ]; then
    echo "  ✓ Apache, MariaDB, PHP, Redis packages"
else
    echo "  - Packages were NOT removed (still installed)"
fi

if [ "$RESET_FIREWALL" == "y" ] || [ "$RESET_FIREWALL" == "Y" ]; then
    echo "  ✓ Firewall reset to defaults"
else
    echo "  - Firewall rules unchanged"
fi

echo ""
echo "What remains:"
echo "  - System packages (if you chose to keep them)"
echo "  - Log files in /var/log/"
echo "  - Any backups you created"
echo ""
log_info "Server cleanup complete."
echo "=========================================================================="
