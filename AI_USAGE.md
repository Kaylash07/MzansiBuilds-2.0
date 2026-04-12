# Ethical Use of AI — MzansiBuilds

## Overview

This document outlines how AI tools were used during the development of MzansiBuilds, what safeguards were applied, and how responsible practices were maintained throughout the workflow.

---

## 1. AI Tools Used

| Tool | Purpose |
|---|---|
| **GitHub Copilot** | Code suggestions, boilerplate generation, test scaffolding |
| **ChatGPT / Claude** | Debugging assistance, design feedback, documentation drafting |

---

## 2. How AI Was Used

- **Code scaffolding** — AI was used to generate repetitive patterns (route handlers, model `to_dict()` methods, test fixtures) which were then reviewed and adapted to fit the project's conventions.
- **Test writing** — AI assisted in generating test case outlines. Every test was manually reviewed, adjusted for edge cases, and verified by running the full suite before committing.
- **Documentation** — AI helped draft sections of the README and DESIGN documents. All content was verified for accuracy against the actual codebase.
- **Debugging** — AI was consulted for error diagnosis (e.g. SQLAlchemy relationship issues, JWT configuration) and proposed fixes were validated locally before integration.

---

## 3. What AI Was **Not** Used For

- **No AI-generated production secrets** — All secret keys are generated at runtime via `secrets.token_hex(32)` or loaded from environment variables. No AI-suggested keys were hardcoded.
- **No blind copy-paste** — Every AI suggestion was reviewed for correctness, security implications, and alignment with the existing code style before being accepted.
- **No user data processed by AI** — No user-submitted data (emails, passwords, project content) is sent to any AI model or third-party service. The application does not integrate AI inference at runtime.
- **No AI-generated security logic** — Authentication flows, password hashing strategy, and authorization checks were designed manually following established best practices (Werkzeug, Flask-JWT-Extended docs).

---

## 4. Verification & Quality Assurance

All AI-assisted code went through the following checks before being committed:

1. **Manual code review** — Every suggestion was read line-by-line for logic errors, security issues, and style consistency.
2. **Test execution** — The full test suite (128 tests) was run after each significant change to catch regressions.
3. **Security audit** — AI-suggested code involving authentication, file uploads, or user input was cross-referenced against OWASP guidelines.
4. **Linting** — Code was checked with flake8 for syntax errors and style violations.

---

## 5. Data Privacy

- The application collects only the data necessary for its features (username, email, project info).
- No user data is shared with AI services, analytics platforms, or third parties.
- Passwords are hashed with Werkzeug's `generate_password_hash` (PBKDF2) and never stored or logged in plaintext.
- Email notifications are disabled by default and require explicit opt-in via environment configuration.

---

## 6. Bias & Fairness Considerations

- MzansiBuilds does not use AI for content moderation, ranking, or recommendation — all feeds are chronological and filter-based.
- No algorithmic decisions are made about user visibility or project prominence.
- The platform treats all users and projects equally regardless of content, category, or tech stack.

---

## 7. Lessons Learned

- AI is most useful for **accelerating known patterns**, not for designing novel architecture. Design decisions (blueprint structure, database schema, auth flow) were made manually.
- AI-generated tests tend to test the "happy path" — manual effort was needed to add edge-case and security-focused tests (wrong codes, expired tokens, unauthorized access).
- AI documentation drafts require careful fact-checking — generated text occasionally described features that didn't exist or used incorrect configuration names.

---

## 8. Commitment

As the developer, I take full responsibility for all code in this repository. AI was used as a productivity tool, not a decision-maker. All architectural choices, security measures, and quality standards reflect my own judgement and were validated through testing and review.

---

**Author:** Kaylash (MzansiBuilds)
