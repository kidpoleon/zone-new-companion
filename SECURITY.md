# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.2.2   | :white_check_mark: |
| 1.2.1   | :white_check_mark: |
| 1.2.0   | :white_check_mark: |
| 1.1.x   | :white_check_mark: |
| < 1.1.4 | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in zone-new-companion, please report it to us privately before disclosing it publicly.

### How to Report

1. **Email**: Send a detailed report to kidpoleon@proton.me (or use GitHub Security Advisory below)
2. **GitHub Security**: Use the [GitHub Security Advisory](https://github.com/kidpoleon/zone-new-companion/security/advisories) feature
3. **Private Issue**: Create a private issue on GitHub

### What to Include

- **Description**: Detailed description of the vulnerability
- **Steps to Reproduce**: Clear steps to reproduce the issue
- **Impact**: Potential impact of the vulnerability
- **Environment**: OS version, Python version, app version
- **Proof of Concept**: If available, a safe proof of concept

### Response Time

- **Critical**: Within 24 hours
- **High**: Within 48 hours
- **Medium**: Within 72 hours
- **Low**: Within 1 week

## Security Best Practices

### For Users

1. **Keep Updated**: Always use the latest version of the application
2. **Secure Credentials**: Store IPTV credentials securely
3. **Network Security**: Use secure networks when connecting to IPTV services
4. **VLC Security**: Keep VLC media player updated
5. **Python Security**: Keep Python and dependencies updated

### For Developers

1. **Code Review**: All code changes should be reviewed
2. **Dependency Scanning**: Regularly scan for vulnerable dependencies
3. **Input Validation**: Validate all user inputs
4. **Secure Storage**: Use secure methods for storing sensitive data
5. **Logging**: Avoid logging sensitive information

## Known Security Considerations

### Network Communications
- The application connects to various IPTV services over HTTP/HTTPS
- SSL certificate validation is performed but can be configured for compatibility
- User credentials are stored locally in plain text (considered acceptable for IPTV use case)

### Third-Party Dependencies
- VLC media player is used for stream playback
- FFmpeg is used for stream analysis
- Tesseract OCR is used for text recognition
- PyQt6 is used for the GUI framework

### Data Storage
- Configuration is stored locally in JSON format
- Connection history is stored for convenience
- No telemetry or analytics data is collected

## Security Updates

Security updates will be released as:
- **Patch versions** (e.g., 1.1.4.1) for security fixes
- **Minor versions** (e.g., 1.2.0) for security features
- **Major versions** (e.g., 2.0.0) for security architecture changes

Users are encouraged to enable automatic updates or check for updates regularly.

## Responsible Disclosure

We follow responsible disclosure principles:
- We will acknowledge receipt of your report within 48 hours
- We will provide a detailed response within 7 days
- We will work with you to understand and resolve the issue
- We will notify you when the issue has been fixed
- We will credit you in the security advisory (with your permission)

## Security Contacts

- **Security Team**: kidpoleon@proton.me
- **GitHub Issues**: Use the security advisory feature
- **Discussions**: Tag `@security-team` in any security-related discussions

---

Thank you for helping keep zone-new-companion secure!
