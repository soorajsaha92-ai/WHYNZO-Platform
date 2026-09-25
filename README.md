# WHYNZO Backend V1

Minimal local backend foundation for WHYNZO.

## Purpose

This is the first server-side foundation for:

- learner accounts
- learner profiles
- learning progress
- audit logging
- future assessments and Skill Passport evidence

It intentionally does NOT contain external AI APIs, payment APIs, or production credentials.

## Run locally

```bash
python -m venv .venv
```

Activate the environment, then:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Health check:

```text
GET /health
```

Interactive API documentation is available from FastAPI during local development.

## Important production gaps

Before real users enter passwords or sensitive data, add:

1. secure session/authentication flow
2. email verification and password reset
3. rate limiting
4. CSRF protection where applicable
5. strict CORS configuration
6. server-side authorization
7. secure cookie/session settings
8. database backup and recovery
9. privacy/retention/deletion controls
10. security testing and dependency updates

This project is a development foundation, not a production security certification.
