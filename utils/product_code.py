from models import Product

def generate_product_code(main_prefix, sub_prefix, brand_prefix):
    base_code = f"{main_prefix}-{sub_prefix}-{brand_prefix}"

    last_product = (
        Product.query
        .filter(Product.code.like(f"{base_code}-%"))
        .order_by(Product.id.desc())
        .first()
    )

    if last_product:
        last_number = int(last_product.code.split("-")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{base_code}-{str(new_number).zfill(6)}"
