from flask_cors import CORS
from app import create_app, db

app = create_app()
# When initializing the app:
CORS(app, origins=[
    "https://aqua.permai-kencana.com",
    # "http://localhost:5173",            # optional: local dev
])

with app.app_context():
    db.create_all()  # Create tables if they don't exist

# # Run the server
# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=5000, debug=True)
print("Exited, if it is not intentional, please uncomment the last two lines to test locally")