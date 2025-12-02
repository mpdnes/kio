# System Architecture Documentation

## Overview

This document describes the technical architecture of the server environment, including all components, their interactions, and data flows.

## System Diagram

```
Internet
    |
    v
[Firewall (UFW)]
    |
    +-- Port 22  --> SSH
    +-- Port 80  --> Apache --> Snipe-IT (PHP/Laravel)
    +-- Port 443 --> Apache --> Snipe-IT (HTTPS)
    +-- Port 8080 --> Apache --> Kiosk (Python/WSGI)
    +-- Port 8443 --> Apache --> Kiosk (HTTPS)
    |
    v
[Apache Web Server 2.4.58]
    |
    +-- mod_php --> Snipe-IT Application
    |       |
    |       v
    |   [PHP 8.3] --> [MariaDB] --> snipeit database
    |       |
    |       v
    |   [Redis Cache] (port 6379)
    |
    +-- mod_wsgi --> Kiosk Application
            |
            v
        [Python/Flask] --> [MariaDB] (if configured)
            |
            v
        [Redis Cache] (if configured)
```

## Component Details

### Operating System
- **Platform:** Ubuntu 24.04 LTS
- **Kernel:** Linux 6.14.0-1014-aws
- **Architecture:** x86_64
- **Current IP:** 34.194.90.188

### Web Server Layer

#### Apache 2.4.58
**Configuration Files:**
- Main config: `/etc/apache2/apache2.conf`
- Ports: `/etc/apache2/ports.conf`
- Sites available: `/etc/apache2/sites-available/`
- Sites enabled: `/etc/apache2/sites-enabled/`

**Listening Ports:**
- 80: HTTP (Snipe-IT)
- 443: HTTPS (Snipe-IT)
- 8080: HTTP (Kiosk)
- 8443: HTTPS (Kiosk)

**Enabled Modules:**
- `mod_ssl` - SSL/TLS support
- `mod_rewrite` - URL rewriting
- `mod_headers` - HTTP header control
- `mod_wsgi` - Python WSGI support
- `mod_php` - PHP processing

**Process Model:** MPM Prefork
- Processes managed by prefork model
- Each process handles one connection at a time
- Configuration in `/etc/apache2/mods-available/mpm_prefork.conf`

### Application Layer

#### Snipe-IT Asset Management

**Technology Stack:**
- Framework: Laravel (PHP framework)
- Language: PHP 8.3
- Pattern: MVC (Model-View-Controller)

**File Structure:**
```
/var/www/html/snipeit/
├── app/              # Application code
├── bootstrap/        # Framework bootstrap
├── config/           # Configuration files
├── database/         # Migrations, seeds
├── public/           # Web root (DocumentRoot)
│   ├── index.php     # Entry point
│   └── uploads/      # User-uploaded files
├── resources/        # Views, assets
├── routes/           # Route definitions
├── storage/          # Cache, logs, sessions
│   ├── app/
│   ├── framework/
│   └── logs/         # Application logs
├── vendor/           # Composer dependencies
├── .env              # Environment configuration
└── artisan           # CLI tool
```

**Environment Configuration (.env):**
```
APP_URL=http://34.194.90.188
DB_CONNECTION=mysql
DB_HOST=localhost
DB_DATABASE=snipeit
DB_USERNAME=snipeit_user
DB_PASSWORD=[configured]
```

**Web Server Integration:**
- DocumentRoot: `/var/www/html/snipeit/public`
- All requests go through `public/index.php`
- Apache handles static files directly
- PHP-FPM or mod_php processes PHP requests

**Dependencies:**
- Composer packages (in vendor/)
- PHP extensions: mysql, gd, mbstring, xml, curl, zip, ldap, bcmath

#### Kiosk Application

**Technology Stack:**
- Framework: Flask (Python micro-framework)
- Language: Python 3.x
- WSGI Server: mod_wsgi (Apache module)

**File Structure:**
```
/var/www/kiosk/
├── .kiosk/              # Python virtual environment
│   ├── bin/
│   ├── lib/
│   └── ...
├── blueprints/          # Flask blueprints (modular routes)
├── static/              # Static files (CSS, JS, images)
├── templates/           # Jinja2 templates
├── app.wsgi            # WSGI entry point
├── assetbot.py         # Main application
├── config.py           # Configuration
├── .env                # Environment variables
├── requirements.txt    # Python dependencies
└── README.md
```

**WSGI Configuration:**
```apache
WSGIDaemonProcess kioskapp
    python-path=/var/www/kiosk
    python-home=/var/www/kiosk/.kiosk

WSGIProcessGroup kioskapp
WSGIScriptAlias / /var/www/kiosk/app.wsgi
```

**Python Virtual Environment:**
- Located: `/var/www/kiosk/.kiosk/`
- Isolated dependencies
- Activated via WSGI daemon process

**Dependencies:**
- Defined in `requirements.txt`
- Installed in virtual environment
- Managed via pip

### Database Layer

#### MariaDB 10.11.13

**Configuration:**
- Config file: `/etc/mysql/mariadb.conf.d/50-server.cnf`
- Data directory: `/var/lib/mysql/`
- Socket: `/var/run/mysqld/mysqld.sock`
- Port: 3306 (localhost only)

**Databases:**
```
snipeit         # Snipe-IT application data
mysql           # System database
information_schema
performance_schema
sys
```

**Users:**
```
root@localhost           # Administrative access
snipeit_user@localhost   # Snipe-IT application user
```

**Database: snipeit**
Key tables:
- `users` - User accounts
- `assets` - IT assets
- `models` - Asset models
- `categories` - Asset categories
- `locations` - Physical locations
- `components` - Computer components
- `licenses` - Software licenses
- And many more...

**Backup Strategy:**
- Full database dumps via mysqldump
- Stored in `/home/ubuntu/backups/`
- Automated weekly backups via cron

### Cache Layer

#### Redis Server

**Configuration:**
- Config: `/etc/redis/redis.conf`
- Port: 6379
- Binding: localhost only
- Persistence: RDB snapshots

**Usage:**
- Session storage
- Application caching
- Queue backend (if configured)

**Memory:**
- Default maxmemory policy
- Eviction: allkeys-lru (if configured)

### Security Layer

#### Firewall (UFW)

**Active Rules:**
```
Port 22/tcp   - SSH access
Port 80/tcp   - HTTP (Apache)
Port 443/tcp  - HTTPS (Apache)
Port 5000/tcp - Custom service
Port 8080/tcp - Kiosk HTTP
Port 8443/tcp - Kiosk HTTPS
```

**Default Policies:**
- Incoming: DENY
- Outgoing: ALLOW
- Routed: DENY

#### SSL/TLS Certificates

**Snipe-IT:**
- Certificate: `/etc/ssl/certs/snipeit.crt`
- Private Key: `/etc/ssl/private/snipeit.key`
- Type: Self-signed (365 day validity)

**Kiosk:**
- Certificate: `/etc/ssl/certs/kiosk/kiosk.crt`
- Private Key: `/etc/ssl/private/kiosk/kiosk.key`
- Type: Self-signed (365 day validity)

**TLS Configuration:**
- Protocols: TLS 1.2, TLS 1.3 only
- Cipher suites: Modern, secure ciphers
- HSTS enabled on HTTPS vhosts

**Security Headers:**
```apache
Strict-Transport-Security: max-age=63072000
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
```

### File System Layout

```
/
├── etc/
│   ├── apache2/              # Apache configuration
│   ├── mysql/                # MariaDB configuration
│   ├── redis/                # Redis configuration
│   ├── ssl/                  # SSL certificates
│   └── ufw/                  # Firewall rules
│
├── var/
│   ├── www/
│   │   ├── html/
│   │   │   └── snipeit/      # Snipe-IT application
│   │   └── kiosk/            # Kiosk application
│   │
│   ├── log/
│   │   ├── apache2/          # Web server logs
│   │   ├── mysql/            # Database logs
│   │   └── syslog            # System logs
│   │
│   └── lib/
│       └── mysql/            # Database files
│
└── home/
    └── ubuntu/
        └── backups/          # Backup storage
```

### Network Architecture

**Interfaces:**
- Primary network interface
- Loopback (127.0.0.1)

**DNS:**
- Configured via DHCP or system settings

**Outbound Connectivity:**
- Package repositories (apt)
- External APIs (if used by applications)
- Email (if SMTP configured)

## Data Flow

### User Request Flow (Snipe-IT)

```
1. User browser --> https://34.194.90.188/
                    |
2. Firewall (UFW) --> Allow port 443
                    |
3. Apache --> SSL termination
            |
4. Apache --> Route to Snipe-IT vhost
            |
5. Apache --> /var/www/html/snipeit/public/index.php
            |
6. PHP --> Laravel framework
            |
7. Laravel --> Route matching
            |
8. Laravel --> Controller action
            |
9. Controller --> Model (if data needed)
            |
10. Model --> MariaDB query
            |
11. MariaDB --> Return data
            |
12. Controller --> View rendering
            |
13. View --> HTML response
            |
14. Apache --> Send to browser
            |
15. Browser --> Display page
```

### User Request Flow (Kiosk)

```
1. User browser --> https://34.194.90.188:8443/
                    |
2. Firewall (UFW) --> Allow port 8443
                    |
3. Apache --> SSL termination
            |
4. Apache --> Route to Kiosk vhost
            |
5. mod_wsgi --> /var/www/kiosk/app.wsgi
            |
6. WSGI --> Python virtual environment
            |
7. Flask --> Route matching
            |
8. Flask --> View function
            |
9. View --> Business logic
            |
10. View --> Database query (if needed)
            |
11. View --> Template rendering
            |
12. Template --> HTML response
            |
13. mod_wsgi --> Apache
            |
14. Apache --> Send to browser
            |
15. Browser --> Display page
```

### Database Backup Flow

```
1. Cron trigger --> Sunday 2 AM
                    |
2. Execute --> backup.sh script
                    |
3. Script --> mysqldump all databases
                    |
4. mysqldump --> Read from /var/lib/mysql/
                    |
5. Output --> .sql file in /home/ubuntu/backups/
                    |
6. Script --> Compress applications
                    |
7. Script --> Copy configurations
                    |
8. Script --> Create .tar.gz archive
                    |
9. Script --> Clean old backups (>7 days)
                    |
10. Complete --> Log results
```

## Performance Characteristics

### Expected Load

**Snipe-IT:**
- Typical: 10-50 concurrent users
- Database queries: 5-20 per page load
- Response time: <500ms typical page load

**Kiosk:**
- Depends on usage pattern
- Python WSGI processes handle requests
- Response time: Varies by operation

### Resource Usage (Typical)

**Memory:**
- Apache: 100-300MB
- MariaDB: 200-500MB
- Redis: 50-100MB
- Total system: ~1.5GB used (on 2GB server)

**Disk:**
- OS and packages: ~5GB
- Snipe-IT application: ~500MB
- Snipe-IT uploads: Varies (grows over time)
- Database: ~100MB-1GB (grows over time)
- Logs: ~100MB (rotated)

**CPU:**
- Idle: <5%
- Normal load: 10-30%
- Peak: 50-80%

## Scaling Considerations

### Vertical Scaling (Current Approach)

**When to scale up:**
- Memory usage consistently >80%
- CPU usage consistently >70%
- Slow database queries
- Disk space <20% free

**How to scale:**
1. Increase instance size (more RAM/CPU)
2. Optimize database queries
3. Enable caching more aggressively
4. Optimize Apache configuration

### Horizontal Scaling (Future)

**If needed:**
- Multiple web servers behind load balancer
- Separate database server
- Redis cluster
- Shared storage (NFS/S3) for uploads

## Monitoring Points

**Key metrics to monitor:**

1. **Service availability**
   - Apache responding
   - MariaDB accepting connections
   - Redis responding

2. **Resource usage**
   - CPU utilization
   - Memory usage
   - Disk space
   - Disk I/O

3. **Application health**
   - Response times
   - Error rates
   - Database query times

4. **Security**
   - Failed login attempts
   - Unusual traffic patterns
   - Firewall blocks

## Disaster Recovery

### Recovery Time Objective (RTO)
- Target: 4 hours
- Actual: ~1-2 hours with documented procedures

### Recovery Point Objective (RPO)
- Target: 24 hours (daily backups)
- Current: 7 days (weekly backups)
- Recommendation: Daily backups for better RPO

### Recovery Procedure

See `README.md` and `ADMIN_HANDOFF.md` for detailed procedures.

## Dependencies

### External Services
- Ubuntu package repositories (apt)
- Composer (PHP packages) - if updating Snipe-IT
- PyPI (Python packages) - if updating Kiosk
- GitHub - for Kiosk source code

### Internal Dependencies
```
Apache depends on:
  - OpenSSL (SSL/TLS)
  - mod_wsgi (Kiosk)
  - mod_php (Snipe-IT)

Snipe-IT depends on:
  - MariaDB (required)
  - Redis (optional, performance)
  - Apache/PHP

Kiosk depends on:
  - Apache/mod_wsgi
  - Python virtual environment
  - Potentially MariaDB/Redis

MariaDB depends on:
  - None (self-contained)

Redis depends on:
  - None (self-contained)
```

## Change Log

Document significant architecture changes here:

```
[YYYY-MM-DD] - Initial deployment
[YYYY-MM-DD] - [Description of change]
```

---

**Document Version:** 1.0
**Architecture Date:** October 2025
**Last Updated:** $(date)
