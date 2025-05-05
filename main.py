from flask_cors import CORS
from app import create_app, db

app = create_app()
CORS(app)

with app.app_context():
    db.create_all()  # Create tables if they don't exist

# Run the server
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
