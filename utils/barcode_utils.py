import barcode
from barcode.writer import ImageWriter
import os

def generate_barcode(code: str, product_id: int):
    BARCODE_DIR = "static/barcodes"
    os.makedirs(BARCODE_DIR, exist_ok=True)

    filename = f"product_{product_id}"
    filepath = os.path.join(BARCODE_DIR, filename)

    ean = barcode.get("code128", code, writer=ImageWriter())
    ean.save(filepath, {
        "write_text": False   # ❌ لا نص داخل صورة الباركود
})


    return f"{filename}.png"
