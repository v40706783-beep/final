# CodeHub - Educational Code Snippet Sharing Platform

A Flask-based forum for programmers to share educational code snippets, discuss them, and learn from each other.

## Features

- **Code Snippets**: Create, edit, delete snippets with title, description, code, category, and tags
- **Moderation**: All new snippets require admin approval before becoming visible
- **Categories**: Web, Python, JavaScript, Malware Analysis, Reverse Engineering, Exploits, Algorithms, Data Structures, Other
- **Tags**: User-defined tags (max 10 per snippet)
- **Comments**: Nested threaded comments with replies
- **Voting**: Like/dislike on snippets and comments (changeable)
- **Reports**: Report snippets (spam, inappropriate, dangerous) or comments; 15 reports auto-deletes comment
- **Hot Page**: Top snippets by likes from the last 7 days
- **Search & Filter**: By title, tags, category; sort by newest, most liked, most viewed

## Setup

```bash
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:5000

## Create Admin User

Run in Python shell:

```python
from __init__ import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User(username='admin', password=generate_password_hash('admin123'), admin=True)
    db.session.add(admin)
    db.session.commit()
```

## Tech Stack

- Python 3.x, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- SQLite
- Bootstrap 5 (dark theme)
- Jinja2 templates

## Disclaimer

All code samples are for educational purposes only. Always test in isolated environments.
