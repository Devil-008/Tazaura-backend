from controller.app import app
from db import query

with app.app_context():
    try:
        query("SELECT id, image_url, title, subtitle, link, sort_order FROM banners WHERE is_active = 1 ORDER BY sort_order ASC")
        print("Success query")
    except Exception as e:
        print("Error:", e)
