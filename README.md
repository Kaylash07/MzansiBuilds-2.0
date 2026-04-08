# MzansiBuilds

A platform where South African developers can share what they're building, find collaborators, and celebrate shipped projects together.

Built for the **Derivco Code Skills Challenge**.

**Live site:** https://mzansibuilds.pythonanywhere.com

## What it does

- Post your projects and track them through stages (Idea → In Progress → Testing → Launched)
- Browse a live feed of what other devs are working on
- Search and filter by tech stack, category, or project stage
- Request to collaborate on projects that interest you
- Comment and give feedback on other people's builds
- Celebrate launched projects on the Celebration Wall
- Get notified when someone comments or wants to collab
- Dark mode because obviously

## Tech stack

**Backend:** Python / Flask, SQLite, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-CORS

**Frontend:** Vanilla HTML, CSS, JavaScript (no frameworks — just a single-page app with page toggling)

**Deployment:** PythonAnywhere

## Project structure

```
├── run.py                  # entry point
├── requirements.txt
├── server/
│   ├── app.py              # app factory, blueprint registration
│   ├── config.py           # configuration
│   ├── extensions.py       # db + jwt instances
│   ├── models.py           # all SQLAlchemy models
│   ├── email_service.py    # async email notifications
│   └── routes/
│       ├── auth.py         # register, login, profile, password reset
│       ├── projects.py     # CRUD projects + milestones
│       ├── feed.py         # live feed with search/filter/pagination
│       ├── comments.py     # project comments
│       ├── collaborations.py  # collab requests + responses
│       ├── notifications.py   # user notifications
│       ├── support.py      # bug reports / support tickets
│       ├── celebration.py  # celebration wall
│       └── activities.py   # project activity timeline
├── templates/
│   └── index.html          # the whole frontend lives here
├── static/
│   ├── css/style.css
│   └── js/
│       ├── api.js          # API client class
│       └── app.js          # all frontend logic
└── uploads/                # user avatars
```

## Running locally

```bash
pip install -r requirements.txt
python run.py
```

Server starts on http://localhost:5000. That's it — SQLite creates the database automatically on first run.

## Design decisions

- **Blueprints split by domain** — each route file handles one thing (comments, collabs, notifications, etc.) instead of stuffing everything into one file. Keeps it manageable and follows SRP.
- **No frontend framework** — the brief said HTML/CSS/JS, so that's what it is. One HTML file with sections that toggle visibility, plus a JS API client that talks to the backend.
- **JWT auth** — stateless, simple, works well for an API-driven SPA.
- **SQLite** — good enough for this scale, zero setup, just works.
- **CSS custom properties for theming** — dark mode toggles a `data-theme` attribute and all the colours swap via CSS variables.

## Features list

- User registration & login (JWT)
- Password reset flow
- Editable profiles with avatar upload
- Project CRUD with stage tracking
- Milestones per project
- Tech stack tags
- Project categories
- Live feed with search, filters, and pagination
- Comments on projects
- Collaboration requests (send, accept, decline)
- Notification system (in-app)
- Email notifications (optional, off by default)
- Activity timeline per project
- Celebration Wall for launched projects
- Support / bug report system
- Dark / light mode toggle
- Public user profiles
- Progress bars based on milestones

## Architecture

```mermaid
flowchart TD
    Browser["Browser (HTML/CSS/JS)"]
    API["api.js — API Client"]
    Flask["Flask App Factory"]

    API -->|HTTP + JWT| Flask

    Browser --> API

    Flask --> Auth["auth.py"]
    Flask --> Projects["projects.py"]
    Flask --> Feed["feed.py"]
    Flask --> Comments["comments.py"]
    Flask --> Collabs["collaborations.py"]
    Flask --> Notifs["notifications.py"]
    Flask --> Support["support.py"]
    Flask --> Celebration["celebration.py"]
    Flask --> Activities["activities.py"]

    Auth --> DB[(SQLite)]
    Projects --> DB
    Feed --> DB
    Comments --> DB
    Collabs --> DB
    Notifs --> DB
    Support --> DB
    Celebration --> DB
    Activities --> DB

    Comments -->|async| Email["Email Service"]
    Collabs -->|async| Email
```

## Database ER Diagram

```mermaid
erDiagram
    USER {
        int id PK
        string username UK
        string email UK
        string password_hash
        string bio
        string avatar_url
        datetime created_at
    }

    PROJECT {
        int id PK
        string title
        text description
        string tech_stack
        string repo_url
        string category
        string stage
        text support_needed
        bool is_completed
        datetime completed_at
        datetime created_at
        datetime updated_at
        int owner_id FK
    }

    MILESTONE {
        int id PK
        string title
        text description
        bool is_achieved
        datetime achieved_at
        int project_id FK
    }

    COMMENT {
        int id PK
        text content
        datetime created_at
        int author_id FK
        int project_id FK
    }

    COLLABORATION_REQUEST {
        int id PK
        text message
        string status
        datetime created_at
        int requester_id FK
        int project_id FK
    }

    NOTIFICATION {
        int id PK
        string type
        text message
        bool is_read
        datetime created_at
        int user_id FK
        int project_id FK
        int triggered_by_id FK
    }

    ACTIVITY {
        int id PK
        string type
        text message
        text detail
        datetime created_at
        int project_id FK
        int user_id FK
    }

    SUPPORT_REPORT {
        int id PK
        string category
        string subject
        text description
        string priority
        string status
        datetime created_at
        int user_id FK
    }

    USER ||--o{ PROJECT : owns
    USER ||--o{ COMMENT : writes
    USER ||--o{ COLLABORATION_REQUEST : sends
    USER ||--o{ NOTIFICATION : receives
    USER ||--o{ SUPPORT_REPORT : submits
    PROJECT ||--o{ MILESTONE : has
    PROJECT ||--o{ COMMENT : has
    PROJECT ||--o{ COLLABORATION_REQUEST : has
    PROJECT ||--o{ NOTIFICATION : about
    PROJECT ||--o{ ACTIVITY : logs
    USER ||--o{ ACTIVITY : triggers
```

## Colours

Green, white, and black — South African inspired. The green is `#00a86b`.
