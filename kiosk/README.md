# Asset Management Kiosk

A secure, self-service Flask web application for IT asset checkout and check-in operations, integrated with Snipe-IT asset management system.

## Overview

This kiosk application provides a user-friendly interface for managing IT equipment loans in institutional environments. Users can authenticate via barcode scanning and perform asset operations through a touch-friendly web interface.

## Features

### Core Functionality
- **Barcode Authentication**: Users sign in by scanning employee ID barcodes using the on-site barcode scanner
- **Asset Checkout/Check-in**: Self-service equipment borrowing and return
- **Asset Transfer**: Move equipment between users
- **Real-time Inventory**: Live integration with Snipe-IT for accurate asset tracking
- **Public Asset Lookup**: Allow users to view equipment information without authentication

### Advanced Features
- **VIP/Admin Interface**: Administrative user management and advanced asset operations
- **Loan Agreement System**: Digital signature capture for equipment loans
- **Bulk Operations**: Check out multiple items simultaneously
- **Computer Vision**: Intelligent barcode detection with multiple preprocessing techniques
- **Comprehensive Logging**: Security monitoring and audit trails

### Security
- **Rate Limiting**: Aggressive limits on all operations to prevent abuse
- **CSRF Protection**: Form-based attack prevention
- **Content Security Policy**: XSS protection with strict CSP headers
- **Session Security**: Secure cookie configuration with 30-minute timeouts
- **Input Validation**: Comprehensive sanitization of all user inputs
- **HTTPS Enforcement**: SSL/TLS required in production environments

## Architecture

### Technology Stack
- **Backend**: Flask 3.0.3 with Blueprint organization
- **Security**: Flask-Talisman, Flask-Limiter, CSRF protection
- **Computer Vision**: OpenCV, pyzbar for barcode processing
- **Image Processing**: Pillow for signature handling
- **External API**: Snipe-IT REST API integration
- **Environment**: Python 3.12+

### Project Structure
```
/
├── assetbot.py              # Main Flask application
├── config.py                # Security-hardened configuration
├── app.wsgi                 # WSGI deployment configuration
├── start_production.py      # Production startup script with security checks
├── blueprints/
│   └── main.py             # Route definitions and business logic
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, images, and client-side assets
├── utils/
│   ├── security.py         # Security utilities and validation
│   ├── snipe_it_api.py     # Snipe-IT API client
│   └── csrf.py             # CSRF protection utilities
├── loan_agreements/
│   └── signatures/         # Digital signature storage
└── logs/                   # Application and security logs
```

## API Integration

### Snipe-IT Integration
- **User Authentication**: Validate employee numbers against Snipe-IT user database
- **Asset Operations**: Real-time checkout, check-in, and transfer operations
- **Inventory Management**: Live asset status updates and availability checking
- **Department Support**: Organizational structure integration
- **Custom Fields**: Support for custom inventory numbers and asset identifiers

## Deployment

### Production Deployment
1. **Environment Setup**: Configure `.env` file with required API credentials
2. **Dependencies**: Install requirements via `pip install -r requirements.txt`
3. **Security Checks**: Run `python start_production.py` for automated security validation
4. **Web Server**: Deploy via WSGI (Apache/nginx + mod_wsgi/gunicorn)

### Required Environment Variables
```bash
SECRET_KEY=<cryptographically-secure-secret>
API_URL=<snipe-it-instance-url>
API_TOKEN=<snipe-it-api-token>
REDIS_URL=<redis-connection-string>  # For rate limiting
SESSION_COOKIE_SECURE=true           # Enable HTTPS-only cookies
DEBUG=false                          # Never true in production
```

### Security Requirements
- **Redis Server**: Required for distributed rate limiting
- **HTTPS Certificate**: SSL/TLS termination at web server or load balancer
- **File Permissions**: Restricted access to signature storage and logs
- **Firewall Rules**: Limit access to authorized networks only

## Usage

### Standard User Flow
1. **Sign In**: Scan employee ID barcode using the on-site scanner
2. **Dashboard**: View currently assigned equipment
3. **Asset Operations**: Scan equipment barcodes to check out/in or transfer
4. **Logout**: Secure session termination

### VIP/Admin Features
- **User Management**: Create new users and manage departments
- **Asset Lookup**: Advanced search by user name or asset number
- **Loan Agreements**: Create formal equipment loan contracts with digital signatures
- **Bulk Operations**: Administrative tools for managing multiple assets

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
# OR
npm run install-deps

# Set up environment
cp .env.example .env
# Edit .env with development credentials
# OR
npm run setup

# Run development server
export FLASK_ENV=development
python assetbot.py
# OR
npm run dev
```

### Testing
- **Manual Testing**: Use development Snipe-IT instance
- **Security Testing**: Rate limiting and input validation
- **Barcode Testing**: QR code generation tools for testing authentication

## Monitoring

### Logging
- **Application Logs**: `logs/assetbot.log`
- **Production Logs**: `logs/production_startup.log`
- **Security Events**: Logged to application log with WARNING+ levels

### Health Checks
- **Dependency Checks**: Redis connectivity, Snipe-IT API availability
- **Security Validation**: Configuration validation, file permissions
- **Performance Monitoring**: Rate limit status, session management

## License

This project is designed for institutional use and contains security-sensitive configurations. Ensure proper security review before deployment in production environments.
