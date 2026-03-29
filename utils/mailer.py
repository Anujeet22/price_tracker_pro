import re
from flask_mail import Message
from app import mail


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def send_price_alert(user_email, product_name, old_price, new_price, product_url, currency='$'):

    if not is_valid_email(user_email):
        print(f"Invalid email address: {user_email}")
        return False

    drop_amount  = round(old_price - new_price, 2)
    drop_percent = round((drop_amount / old_price) * 100, 1)

    try:
        msg = Message(
            subject    = f"Price Drop — {product_name} is {drop_percent}% cheaper now",
            recipients = [user_email]
        )

        msg.html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Price Drop Alert</title>
</head>
<body style="margin:0; padding:0; background-color:#f6f8fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f6f8fa; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%;">

          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #0f172a 0%, #0f4c75 100%); border-radius: 16px 16px 0 0; padding: 32px 40px; text-align: center;">
              <p style="margin:0 0 8px 0; font-size:13px; font-weight:600; color:rgba(255,255,255,0.6); letter-spacing:2px; text-transform:uppercase;">PriceTracker Pro</p>
              <h1 style="margin:0; font-size:26px; font-weight:700; color:#ffffff; letter-spacing:-0.5px;">Price Drop Alert</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="background-color:#ffffff; padding: 40px;">

              <p style="margin:0 0 24px 0; font-size:15px; color:#57606a; line-height:1.6;">
                Good news! A product you are tracking just dropped in price.
              </p>

              <!-- Product Name -->
              <div style="background-color:#f6f8fa; border-left: 4px solid #0969da; border-radius: 0 12px 12px 0; padding: 16px 20px; margin-bottom: 32px;">
                <p style="margin:0 0 4px 0; font-size:12px; font-weight:600; color:#768390; text-transform:uppercase; letter-spacing:1px;">Product</p>
                <p style="margin:0; font-size:16px; font-weight:700; color:#24292f;">{product_name}</p>
              </div>

              <!-- Price Comparison -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
                <tr>
                  <td width="48%" style="background-color:#fff8f0; border: 1px solid #fcd34d; border-radius:12px; padding:20px; text-align:center;">
                    <p style="margin:0 0 6px 0; font-size:12px; font-weight:600; color:#9e6a03; text-transform:uppercase; letter-spacing:1px;">Was</p>
                    <p style="margin:0; font-size:28px; font-weight:700; color:#9e6a03; text-decoration:line-through;">{currency}{old_price}</p>
                  </td>
                  <td width="4%" style="text-align:center;">
                    <p style="margin:0; font-size:20px; color:#0969da;">→</p>
                  </td>
                  <td width="48%" style="background-color:#dafbe1; border: 1px solid #34d399; border-radius:12px; padding:20px; text-align:center;">
                    <p style="margin:0 0 6px 0; font-size:12px; font-weight:600; color:#1a7f37; text-transform:uppercase; letter-spacing:1px;">Now</p>
                    <p style="margin:0; font-size:28px; font-weight:700; color:#1a7f37;">{currency}{new_price}</p>
                  </td>
                </tr>
              </table>

              <!-- Savings Badge -->
              <div style="background: linear-gradient(135deg, #0969da 0%, #1f6feb 100%); border-radius:12px; padding:20px; text-align:center; margin-bottom:32px;">
                <p style="margin:0 0 4px 0; font-size:13px; font-weight:600; color:rgba(255,255,255,0.8);">Your Total Savings</p>
                <p style="margin:0; font-size:32px; font-weight:800; color:#ffffff;">{currency}{drop_amount} <span style="font-size:18px; font-weight:600; opacity:0.85;">({drop_percent}% off)</span></p>
              </div>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
                <tr>
                  <td align="center">
                    <a href="{product_url}" target="_blank" style="display:inline-block; background: linear-gradient(135deg, #0969da 0%, #0860ca 100%); color:#ffffff; text-decoration:none; font-size:15px; font-weight:700; padding:14px 40px; border-radius:10px; letter-spacing:-0.3px;">
                      View Product →
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:0; font-size:13px; color:#8c959f; line-height:1.6; text-align:center;">
                You are receiving this because you have alerts enabled for this product.<br>
                You can manage your alert preferences in your dashboard settings.
              </p>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f6f8fa; border-top:1px solid #e5e7eb; border-radius: 0 0 16px 16px; padding: 24px 40px; text-align:center;">
              <p style="margin:0 0 8px 0; font-size:13px; font-weight:600; color:#24292f;">PriceTracker Pro</p>
              <p style="margin:0; font-size:12px; color:#8c959f;">This is an automated alert. Please do not reply to this email.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
"""

        mail.send(msg)
        print(f"Alert sent to {user_email} for {product_name}")
        return True

    except Exception as e:
        print(f"Failed to send alert to {user_email}: {str(e)}")
        return False