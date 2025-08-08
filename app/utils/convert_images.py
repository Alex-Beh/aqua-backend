import io, mimetypes
from PIL import Image
import pillow_heif
pillow_heif.register_heif_opener() # enables Pillow to read HEIC/HEIF

def normalize_image_to_jpeg(file_storage):
    """
    Returns (bytes_io, mime, ext) where mime is image/jpeg and ext is .jpg
    Converts HEIC/HEIF/WEBP to JPEG. Pass-through for JPEG/PNG.
    """
    mime = (file_storage.mimetype or "").lower()
    stream = file_storage.stream

    # If already jpeg or png, just return stream as-is
    if mime in ("image/jpeg", "image/jpg", "image/png"):
        stream.seek(0)
        return stream, mime, (".jpg" if "jpeg" in mime else ".png")

    # Convert everything else (e.g., image/heic, image/heif, image/webp) to jpeg
    stream.seek(0)
    img = Image.open(stream)
    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=90)
    out.seek(0)
    return out, "image/jpeg", ".jpg"
