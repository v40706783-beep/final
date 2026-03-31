"""Run the CodeHub Flask application."""
from __init__ import app, db, init_categories

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_categories()
    app.run(debug=True)
