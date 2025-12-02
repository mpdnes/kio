# Equipment Kiosk

A production-ready Flask web application for self-service IT asset management. Built for institutions that need secure, barcode-driven equipment checkout and return workflows, integrated with Snipe-IT asset tracking.

## What It Does

This application provides a locked-down kiosk interface where users can:

- **Authenticate** by scanning their employee ID barcode
- **Check out** equipment by scanning asset tags
- **Return** equipment with automatic status updates
- **Transfer** assets between users
- **Sign** digital loan agreements for high-value equipment

All operations sync in real-time with your Snipe-IT installation, maintaining accurate inventory records without manual data entry.

## Key Features

**Security First**
- Rate limiting on all endpoints (Redis-backed)
- CSRF protection on state-changing operations
- Content Security Policy headers
- Input sanitization and validation
- HTTPS enforcement in production
- Comprehensive audit logging

**Barcode-Driven Workflow**
- OpenCV and pyzbar for barcode detection
- Support for Code 128, Code 39, QR codes, and more
- Intelligent image preprocessing for difficult scans
- Camera access for barcode scanning on supported devices

**Touch-Optimized Interface**
- Large buttons designed for tablet/kiosk hardware
- Minimal text entry required
- Session timeout warnings
- Responsive layout for various screen sizes

**Admin Tools**
- User lookup and management
- Asset search across the inventory
- Bulk checkout operations
- Digital signature capture for loan agreements

## Architecture

**Backend**: Flask 3.0.3 with modular blueprint structure  
**Security**: Flask-Talisman (CSP/HSTS), Flask-Limiter (rate limiting)  
**Storage**: Redis for sessions and rate limiting  
**API Integration**: Snipe-IT REST API  
**Image Processing**: OpenCV, Pillow, pyzbar  
**Deployment**: WSGI-compatible (Apache mod_wsgi, Gunicorn, uWSGI)

## Quick Start

### Prerequisites

- Python 3.8+
- Redis server
- Snipe-IT installation with API access
- Barcode scanner (USB HID or camera-based)

### Installation

```bash
git clone https://github.com/mpdnes/kio.git
cd kio
npm run install-deps
```

### Configuration

Run the setup wizard:

```bash
npm run setup
```

Or manually create a `.env` file:

```bash
SECRET_KEY=your-secret-key-here
API_URL=https://your-snipeit-instance.com/api/v1
API_TOKEN=your-api-token
REDIS_URL=redis://localhost:6379/0
SESSION_COOKIE_SECURE=true
DEBUG=false
```

Generate a secure key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Running Locally

```bash
npm start
```

Visit `http://localhost:5000` to access the kiosk interface.

## Deployment

### Production Checklist

- [ ] Set `DEBUG=false` in `.env`
- [ ] Configure HTTPS with valid certificates
- [ ] Set `SESSION_COOKIE_SECURE=true`
- [ ] Configure Redis with persistence
- [ ] Set up log rotation
- [ ] Configure firewall rules
- [ ] Review rate limiting thresholds
- [ ] Test barcode scanner hardware

### Apache + mod_wsgi Example

```apache
<VirtualHost *:443>
    ServerName kiosk.example.com
    
    WSGIDaemonProcess kiosk python-path=/var/www/kiosk
    WSGIScriptAlias / /var/www/kiosk/kiosk/app.wsgi
    
    <Directory /var/www/kiosk/kiosk>
        Require all granted
    </Directory>
    
    SSLEngine on
    SSLCertificateFile /path/to/cert.pem
    SSLCertificateKeyFile /path/to/key.pem
</VirtualHost>
```

See `server-installer/` directory for complete installation scripts and configuration examples.

## Project Structure

```
.
├── kiosk/                      # Main application directory
│   ├── assetbot.py            # Flask application entry point
│   ├── config.py              # Configuration with security defaults
│   ├── blueprints/            # Route handlers (auth, assets, admin)
│   ├── services/              # Business logic layer
│   ├── templates/             # Jinja2 HTML templates
│   ├── static/                # CSS, images, client-side assets
│   └── utils/                 # Security, API client, helpers
├── server-installer/          # Production deployment scripts
├── setup.py                   # Interactive setup wizard
├── requirements.txt           # Python dependencies
└── package.json               # NPM script aliases
```

## Snipe-IT Integration

This application requires a Snipe-IT instance with API access. Configure the following in Snipe-IT:

1. Create an API token with appropriate permissions
2. Set up custom fields for inventory numbers (optional)
3. Configure asset statuses (Deployed, Ready to Deploy, etc.)
4. Create user accounts with employee numbers matching barcode values

The application uses the Snipe-IT API to:
- Authenticate users by employee number
- Query asset availability
- Check out/check in assets
- Update asset assignments
- Record audit logs

## Security Considerations

**Rate Limiting**: All endpoints are rate-limited to prevent abuse. Limits are configurable in `config.py`.

**Session Management**: Sessions expire after 30 minutes of inactivity. Session cookies are HTTPOnly, Secure (in production), and use SameSite=Strict.

**Input Validation**: All user input is sanitized and validated against defined schemas. File uploads are restricted to specific MIME types.

**HTTPS Only**: Production deployments must use HTTPS. The application sets HSTS headers with a 1-year max-age.

**Content Security Policy**: Strict CSP headers prevent XSS attacks. Inline scripts are disabled.

**Audit Logging**: All authentication attempts, asset operations, and errors are logged with timestamps and IP addresses.

## Customization

### Custom Fields

Edit the `INVENTORY_FIELDS` configuration to match your Snipe-IT custom field names:

```python
INVENTORY_FIELDS = ['Inventory Number', 'Asset ID', 'Device ID']
```

### Rate Limits

Adjust rate limits in `config.py`:

```python
RATELIMIT_SIGNIN = "10 per minute"
RATELIMIT_ASSET_OPS = "30 per minute"
RATELIMIT_ADMIN_OPS = "20 per hour"
```

### Branding

Replace `kiosk/static/images/logo.png` with your organization's logo.

## Troubleshooting

**Barcode scanner not working**: Ensure the scanner is configured for USB HID keyboard emulation. Test by scanning into a text editor.

**Redis connection errors**: Verify Redis is running (`redis-cli ping`) and the `REDIS_URL` is correct.

**Snipe-IT API errors**: Check API token permissions and URL format (`https://domain.com/api/v1`).

**Session issues**: Clear browser cookies and verify `SESSION_COOKIE_SECURE` matches your HTTPS configuration.

See `QUICK_START.md` and `server-installer/TROUBLESHOOTING.md` for detailed debugging steps.

## Documentation

- `QUICK_START.md` - Installation and setup guide
- `SNIPE_IT_SETUP_GUIDE.md` - Snipe-IT configuration instructions
- `SETUP_WIZARD_GUIDE.md` - Interactive setup wizard documentation
- `server-installer/OPERATIONS_GUIDE.md` - Production operations manual
- `server-installer/ARCHITECTURE.md` - System architecture overview

## Contributing

Contributions are welcome. Please read `CONTRIBUTING.md` for guidelines on submitting pull requests, reporting issues, and coding standards.

## License

MIT License - see `LICENSE` file for details.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

## Acknowledgments

This project integrates with [Snipe-IT](https://snipeitapp.com/), an open-source asset management system.
