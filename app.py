from flask_cors import CORS
from app import create_app, db

app = create_app()
CORS(app)

# Run the server
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True)
