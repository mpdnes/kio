#!/bin/bash

###############################################################################
# Post-Installation Verification Script
###############################################################################

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================================================="
echo "Server Installation Verification"
echo "=========================================================================="
echo ""

# Check services
echo "Checking Services..."
echo ""

if systemctl is-active --quiet apache2; then
    echo -e "${GREEN}✓${NC} Apache2 is running"
else
    echo -e "${RED}✗${NC} Apache2 is NOT running"
fi

if systemctl is-active --quiet mariadb; then
    echo -e "${GREEN}✓${NC} MariaDB is running"
else
    echo -e "${RED}✗${NC} MariaDB is NOT running"
fi

if systemctl is-active --quiet redis-server; then
    echo -e "${GREEN}✓${NC} Redis is running"
else
    echo -e "${RED}✗${NC} Redis is NOT running"
fi

echo ""
echo "Checking Applications..."
echo ""

# Check Snipe-IT
if [ -d "/var/www/html/snipeit" ]; then
    echo -e "${GREEN}✓${NC} Snipe-IT directory exists"

    if [ -f "/var/www/html/snipeit/.env" ]; then
        echo -e "${GREEN}✓${NC} Snipe-IT .env file exists"
    else
        echo -e "${YELLOW}!${NC} Snipe-IT .env file missing"
    fi
else
    echo -e "${RED}✗${NC} Snipe-IT directory not found"
fi

# Check Kiosk
if [ -d "/var/www/kiosk" ]; then
    echo -e "${GREEN}✓${NC} Kiosk directory exists"

    if [ -f "/var/www/kiosk/.env" ]; then
        echo -e "${GREEN}✓${NC} Kiosk .env file exists"
    else
        echo -e "${YELLOW}!${NC} Kiosk .env file missing"
    fi

    if [ -d "/var/www/kiosk/.kiosk" ]; then
        echo -e "${GREEN}✓${NC} Kiosk virtual environment exists"
    else
        echo -e "${YELLOW}!${NC} Kiosk virtual environment missing"
    fi
else
    echo -e "${YELLOW}!${NC} Kiosk directory not found (needs to be cloned from GitHub)"
fi

echo ""
echo "Checking Databases..."
echo ""

if sudo mysql -e "USE snipeit;" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Snipe-IT database exists"
    TABLE_COUNT=$(sudo mysql -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'snipeit';" 2>/dev/null)
    echo "  Tables: $TABLE_COUNT"
else
    echo -e "${RED}✗${NC} Snipe-IT database not accessible"
fi

echo ""
echo "Checking Apache Configuration..."
echo ""

if apache2ctl configtest 2>&1 | grep -q "Syntax OK"; then
    echo -e "${GREEN}✓${NC} Apache configuration is valid"
else
    echo -e "${RED}✗${NC} Apache configuration has errors"
    echo "Run: sudo apache2ctl configtest"
fi

# Check enabled sites
echo ""
echo "Enabled Apache sites:"
ls -1 /etc/apache2/sites-enabled/

echo ""
echo "Checking Firewall..."
echo ""

if sudo ufw status | grep -q "Status: active"; then
    echo -e "${GREEN}✓${NC} Firewall is active"
    echo ""
    sudo ufw status numbered
else
    echo -e "${YELLOW}!${NC} Firewall is not active"
fi

echo ""
echo "Checking SSL Certificates..."
echo ""

if [ -f "/etc/ssl/certs/kiosk/kiosk.crt" ]; then
    echo -e "${GREEN}✓${NC} Kiosk SSL certificate exists"
else
    echo -e "${RED}✗${NC} Kiosk SSL certificate missing"
fi

if [ -f "/etc/ssl/certs/snipeit.crt" ]; then
    echo -e "${GREEN}✓${NC} Snipe-IT SSL certificate exists"
else
    echo -e "${RED}✗${NC} Snipe-IT SSL certificate missing"
fi

echo ""
echo "Testing HTTP Endpoints..."
echo ""

# Test Snipe-IT
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200\|302"; then
    echo -e "${GREEN}✓${NC} Snipe-IT HTTP responding"
else
    echo -e "${YELLOW}!${NC} Snipe-IT HTTP not responding on port 80"
fi

# Test Kiosk (may not be deployed yet)
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ | grep -q "200\|302\|500"; then
    echo -e "${GREEN}✓${NC} Kiosk HTTP responding on port 8080"
else
    echo -e "${YELLOW}!${NC} Kiosk HTTP not responding (may not be deployed yet)"
fi

echo ""
echo "=========================================================================="
echo "Verification Complete"
echo "=========================================================================="
