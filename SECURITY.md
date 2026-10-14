# BloodGrid Security Policy & Architecture

**Classification**: Public  
**Last Revised**: 2026-10-15  
**Version**: 1.0.0

---

## 1. Security Architecture Principles

BloodGrid processes publicly available clinical inventory metrics provided by eRaktKosh (MoHFW) and provides search, time-series analysis, and emergency shortage notifications. Security is baked into the foundation:

1. **Separation of Concerns**: Analytical inventory data resides in read-only DuckDB files (`serving.duckdb`). Sensitive application state (users, hashed credentials, subscription metadata) is segregated into an isolated relational database.
2. **Zero Raw SQL String Concatenation**: All database queries are strictly parameterized with positional `?` or `$1` placeholders to eliminate SQL injection vulnerabilities.
3. **OWASP Top 10 Protections**:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: SAMEORIGIN`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `X-XSS-Protection: 1; mode=block`
   - Strict CORS origin validation locked to official domains.
4. **Credential Hashing**: User passwords are encrypted with `Argon2id` (memory-hard, resistant to GPU cracking). API key secrets are never stored in plain text; only SHA-256 digests are stored in the database.
5. **No PII in Logs**: Server logs record anonymized request identifiers and endpoint routes. Phone numbers and email addresses are masked or excluded from analytical logs.

---

## 2. Reporting a Vulnerability

If you discover a potential security vulnerability within BloodGrid, please notify the security team:
- **Email**: `security@bloodgrid.in`
- **PGP Key**: Available upon request
- **Response Time**: We acknowledge receipt of vulnerability reports within 24 hours and aim to provide a remediation patch within 7 business days.

Please do not disclose security issues publicly until a patch has been released.
