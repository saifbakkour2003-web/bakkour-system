import os
import uuid
from werkzeug.utils import secure_filename


def allowed_file(filename: str, allowed_exts: set[str]) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_exts


def save_product_image(file_storage, upload_folder: str, allowed_exts: set[str]) -> str:
    """
    Saves uploaded image to /static/uploads/products and returns relative path:
    'uploads/products/<filename>'
    """
    filename = secure_filename(file_storage.filename)
    if not allowed_file(filename, allowed_exts):
        raise ValueError("Invalid image type")

    ext = filename.rsplit(".", 1)[1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"

    os.makedirs(upload_folder, exist_ok=True)
    abs_path = os.path.join(upload_folder, new_name)
    file_storage.save(abs_path)

    # relative path used with url_for('static', filename=...)
    return f"uploads/products/{new_name}"
