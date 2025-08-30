from uuid import uuid4
from app.supabase_client import supabase, STORAGE_BUCKET


def upload_image(file_stream, content_type, folder_name, ext=".jpg"):
    """
    Uploads the original image bytes to Supabase Storage.
    Returns the path to store in DB.
    """
    filename = f"{uuid4().hex}{ext}"
    path = f"{folder_name}/{filename}"
    data = file_stream.read()
    res = supabase.storage.from_(STORAGE_BUCKET).upload(
        path,
        data,
        {"content-type": content_type, "cache-control": "31536000"},
    )
    if getattr(res, "error", None):
        raise RuntimeError(f"Upload failed: {res.error}")
    return path


def public_url(path: str) -> str:
    """
    For supabase-py v2 the SDK returns the URL string directly.
    """
    return supabase.storage.from_(STORAGE_BUCKET).get_public_url(path)


def thumb_url(path: str, width: int, quality: int = 75) -> str:
    base = public_url(path)              # may already end with '?'
    sep = '&' if '?' in base else '?'   # choose correct separator
    return (
        f"{base}{sep}width={width}"
        f"&resize=cover"
        f"&format=webp"
        f"&quality={quality}"
    )


def delete_path(path: str):
    supabase.storage.from_(STORAGE_BUCKET).remove([path])
