# 🌊 Aqua Backend
A lightweight Flask + PostgreSQL backend to manage fish types in an aquaculture stock tracking system.

## Dependencies
Install the required system packages and Python libraries
```
sudo apt update
sudo apt install postgresql postgresql-contrib

pip install Flask Flask-Cors Flask-SQLAlchemy psycopg2-binary
```

## 🛠️ Setup Instructions
1. Setup PostgreSQL
    ```
    # Switch to the postgres user
    sudo -i -u postgres
    
    # Enter PostgreSQL shell
    psql
    
    # Inside psql:
    CREATE DATABASE aquastock;
    CREATE USER username WITH PASSWORD 'password';
    ALTER ROLE username SET client_encoding TO 'utf8';
    ALTER ROLE username SET default_transaction_isolation TO 'read committed';
    ALTER ROLE username SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE aquastock TO username;
    \q
    
    # Exit back to your regular user
    exit
    ```
    
2. Run the Backend Server
    ```
    python app.py
    ```
    The server will start at:📍 http://localhost:5000/

## Testing with Postman
Use Postman to test each endpoint with form-data (especially for image uploads). Collection [Aqua Stock Take Backend.postman_collection.json](./config/Aqua%20Stock%20Take%20Backend.postman_collection.json) had been provided.

<img src="./doc/post-api-fish-types.png" style="zoom: 50%;" />
