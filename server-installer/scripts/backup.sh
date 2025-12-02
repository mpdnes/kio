#!/bin/bash

###############################################################################
# Server Backup Script
# Creates a backup of databases, configurations, and application files
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root or with sudo"
    exit 1
fi

# Configuration
BACKUP_DIR="/home/ubuntu/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="server-backup-$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

log_info "Starting server backup..."
log_info "Backup location: $BACKUP_PATH"

# Create backup directory
mkdir -p "$BACKUP_PATH"/{databases,applications,config}

###############################################################################
# Backup Databases
###############################################################################

log_info "Backing up databases..."

# Backup all databases
mysqldump --all-databases > "$BACKUP_PATH/databases/all-databases.sql"
log_info "✓ All databases backed up"

# Backup individual databases (compressed)
if mysql -e "USE snipeit;" 2>/dev/null; then
    mysqldump snipeit | gzip > "$BACKUP_PATH/databases/snipeit.sql.gz"
    log_info "✓ Snipe-IT database backed up (compressed)"
fi

###############################################################################
# Backup Applications
###############################################################################

log_info "Backing up applications..."

# Backup Snipe-IT
if [ -d "/var/www/html/snipeit" ]; then
    tar --exclude='snipeit/storage/logs/*' \
        --exclude='snipeit/storage/framework/cache/*' \
        -czf "$BACKUP_PATH/applications/snipeit.tar.gz" \
        -C /var/www/html snipeit
    log_info "✓ Snipe-IT application backed up"
fi

# Backup Kiosk (if exists)
if [ -d "/var/www/kiosk" ]; then
    tar --exclude='kiosk/__pycache__' \
        --exclude='kiosk/.git' \
        -czf "$BACKUP_PATH/applications/kiosk.tar.gz" \
        -C /var/www kiosk
    log_info "✓ Kiosk application backed up"
fi

###############################################################################
# Backup Configurations
###############################################################################

log_info "Backing up configurations..."

# Apache configurations
mkdir -p "$BACKUP_PATH/config/apache"
cp -r /etc/apache2/sites-available/*.conf "$BACKUP_PATH/config/apache/" 2>/dev/null || true
cp /etc/apache2/ports.conf "$BACKUP_PATH/config/apache/" 2>/dev/null || true
log_info "✓ Apache configs backed up"

# SSL certificates
mkdir -p "$BACKUP_PATH/config/ssl"
cp -r /etc/ssl/certs/kiosk "$BACKUP_PATH/config/ssl/" 2>/dev/null || true
cp /etc/ssl/certs/snipeit.crt "$BACKUP_PATH/config/ssl/" 2>/dev/null || true
log_info "✓ SSL certificates backed up"

# Firewall rules
ufw status numbered > "$BACKUP_PATH/config/firewall_rules.txt"
log_info "✓ Firewall rules backed up"

# PHP configuration
php -i > "$BACKUP_PATH/config/php_info.txt"
log_info "✓ PHP configuration backed up"

# Installed packages list
apt list --installed > "$BACKUP_PATH/config/installed_packages.txt" 2>/dev/null
log_info "✓ Package list backed up"

# Cron jobs
crontab -l > "$BACKUP_PATH/config/crontab.txt" 2>/dev/null || echo "No crontab" > "$BACKUP_PATH/config/crontab.txt"
log_info "✓ Crontab backed up"

###############################################################################
# Create Archive
###############################################################################

log_info "Creating backup archive..."

cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)

###############################################################################
# Cleanup Old Backups (keep last 7 days)
###############################################################################

log_info "Cleaning up old backups (keeping last 7 days)..."
find "$BACKUP_DIR" -name "server-backup-*.tar.gz" -type f -mtime +7 -delete

###############################################################################
# Summary
###############################################################################

echo ""
echo "=========================================================================="
log_info "Backup Complete!"
echo "=========================================================================="
echo ""
echo "Backup file: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Size: $BACKUP_SIZE"
echo ""
echo "To restore this backup on another server:"
echo "1. Extract: tar -xzf ${BACKUP_NAME}.tar.gz"
echo "2. Import databases: mysql < databases/all-databases.sql"
echo "3. Restore applications to /var/www/"
echo "4. Restore Apache configs to /etc/apache2/"
echo "5. Restore SSL certificates"
echo "6. Restart services: systemctl restart apache2 mariadb"
echo ""
echo "=========================================================================="
