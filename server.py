"""Entry point.

Development :  python server.py
Production  :  APP_ENV=production gunicorn -w 2 -b 0.0.0.0:8000 server:app
"""
import os

from web import create_app

app = create_app()

if __name__ == "__main__":
    # Debug mode is only possible outside production and must be asked for explicitly.
    debug = os.environ.get("FLASK_DEBUG") == "1" and os.environ.get("APP_ENV") != "production"
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")), debug=debug)
