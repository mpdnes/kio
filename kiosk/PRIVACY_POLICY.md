# Privacy Policy
## Equipment Loan Management System

### Overview
This system is designed to comply with data protection requirements for equipment loan management.

### Data Collection and Use

#### What Data We Collect:
- **User ID Numbers**: Used for authentication and loan tracking
- **User Names**: Required for equipment accountability  
- **Email Addresses**: Email for communication
- **Digital Signatures**: For loan agreement verification
- **Equipment Information**: Asset details for tracking purposes

#### What Data We Do NOT Collect:
- ~~Phone Numbers~~ (Removed for data minimization)
- Social Security Numbers
- Financial Information
- Academic Records beyond ID verification

### Data Protection Measures

#### Technical Safeguards:
1. **Encryption in Transit**: HTTPS/TLS for all communications
2. **Access Controls**: Role-based permissions with audit logging
3. **Rate Limiting**: Protection against brute force attacks
4. **Session Security**: Secure session management with anomaly detection
5. **File Permissions**: Restricted access to signature files (Unix permissions 0o600)

#### Administrative Safeguards:
1. **Staff Training**: All system users trained on privacy requirements
2. **Access Reviews**: Regular audit of user permissions
3. **Incident Response**: Documented procedures for security events
4. **Data Retention**: Automated deletion after retention period

### Data Retention Policy

#### User Data:
- **Loan Records**: Retained for 7 years after loan completion
- **Digital Signatures**: Secure storage with restricted permissions
- **Access Logs**: Retained for 3 years for audit purposes

#### Manual Cleanup:
- System administrators should periodically review and purge expired data
- Signature files can be manually deleted after retention period expires

### Access Controls

#### User Roles:
1. **Users**: Can view own loan history, create new loans
2. **Staff**: Can manage loans, view reports for their equipment
3. **Administrators**: Full system access with audit trail
4. **IT Administration**: System maintenance access only

#### Authentication:
- Authentication via ID barcode
- Session timeout after 30 minutes of inactivity
- IP address and browser verification

### Third-Party Integrations

#### Snipe-IT Asset Management:
- **Data Shared**: User names, email, equipment assignments
- **Purpose**: Asset tracking and inventory management
- **Protection**: API calls sanitized and rate-limited
- **Agreement**: Covered under institutional data sharing agreement

### User Rights

Users have the right to:
1. **Inspect Records**: View their equipment loan history
2. **Request Amendments**: Correct inaccurate information
3. **Control Disclosure**: Consent required for information sharing
4. **File Complaints**: Report violations to institution

### Data Breach Response

#### Immediate Actions:
1. **Containment**: Isolate affected systems
2. **Assessment**: Determine scope and impact
3. **Notification**: Alert institutional privacy officer within 24 hours
4. **Documentation**: Log all response activities

#### Regulatory Compliance:
- Institution notified within 24 hours
- Affected users notified within 72 hours if required
- Regulatory bodies notified if breach involves data protection violations

### Security Monitoring

#### Continuous Monitoring:
- **Failed Authentication Attempts**: Logged and rate-limited
- **Data Access Patterns**: Anomaly detection for unusual access
- **System Health**: Performance and security metrics
- **Compliance Checks**: Automated validation of security controls

### Contact Information

#### Privacy Questions:
- **System Administrator**: [IT Contact]
- **Privacy Officer**: [Privacy Officer Contact]
- **Security Incidents**: [Security Team Contact]

#### Policy Updates:
This policy is reviewed annually and updated as needed to maintain compliance and organizational requirements.

---

**Last Updated**: 2025-09-18  
**Next Review**: 2026-09-18  
**Version**: 1.0