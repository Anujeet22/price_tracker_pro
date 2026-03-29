from app import app
from utils.mailer import send_price_alert

with app.app_context():
    result = send_price_alert(
        user_email   = "anujeetkadam14@gmail.com",
        product_name = "Apple MacBook Pro 14 M3 Pro",
        old_price    = 1999.00,
        new_price    = 1799.00,
        product_url  = "https://www.amazon.com",
        currency     = "₹"
    )

    if result:
        print("Alert sent successfully!")
    else:
        print("Alert failed.")