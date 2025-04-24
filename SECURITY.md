# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you believe you have found a security vulnerability in mmdb-server, please report it to us:

1. **Do Not** open a public issue
2. Send a description of the vulnerability to security@hireflix.com
3. Include steps to reproduce the vulnerability
4. We will acknowledge receipt within 24 hours
5. We will provide a more detailed response within 72 hours
6. We will work with you to understand and resolve the issue

## Security Controls

### Code & Repository Security
- All commits must be signed
- Branch protection rules are enabled for `main`
- Pull requests require approval from code owners
- Automated security scanning on all PRs
- Regular dependency updates via Dependabot

### Release Process Security
- Only authorized team members can create releases
- All releases must go through code review
- Automated security checks before release
- Container images are scanned for vulnerabilities

### Runtime Security
- Non-root container execution
- Minimal base image (distroless)
- Regular security updates
- Resource limits enforced

## Acknowledgments

We would like to thank the following for their contributions to our security:

- All security researchers who responsibly disclose vulnerabilities
- The GitHub Security Lab team
- Our security contributors and reviewers 