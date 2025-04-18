class Config:
    SQLALCHEMY_DATABASE_URI = "postgresql://username:password@localhost:5432/aquastock"
    UPLOAD_FOLDER = "uploads/fish_images"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024