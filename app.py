import os
import re
import cv2
import pytesseract
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

# Windows: set tesseract executable path (adjust if installed elsewhere)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)
app.secret_key = "smart_expiry_secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///items.db"
app.config["UPLOAD_FOLDER"] = "static/uploads"

db = SQLAlchemy(app)

# ---------------------------
# Database Model
# ---------------------------
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    image_path = db.Column(db.String(200), nullable=True)

    def status(self):
        today = datetime.today().date()
        if self.expiry_date < today:
            return "expired"
        elif self.expiry_date <= today + timedelta(days=3):
            return "soon"
        return "safe"

# ---------------------------
# Utility function: extract expiry date from OCR text
# ---------------------------
def extract_expiry_date(text):
    # Common date formats
    patterns = [
        r"(\d{2}[/-]\d{2}[/-]\d{4})",  # 12/09/2025 or 12-09-2025
        r"(\d{4}[/-]\d{2}[/-]\d{2})",  # 2025-09-12
        r"(\d{2}[/-]\d{2}[/-]\d{2})",  # 12/09/25
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
    return None

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def index():
    items = Item.query.all()
    items_json = [
        {
            "id": item.id,
            "name": item.name,
            "expiry_date": item.expiry_date.strftime("%Y-%m-%d"),
            "status": item.status(),
            "image_path": item.image_path
        }
        for item in items
    ]
    return render_template("index.html", items=items, items_json=items_json)

@app.route("/add_manual", methods=["POST"])
def add_manual():
    name = request.form["name"]
    expiry_date = request.form["expiry_date"]

    new_item = Item(
        name=name,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date()
    )
    db.session.add(new_item)
    db.session.commit()
    flash(f"✅ {name} added manually.")
    return redirect(url_for("index"))

@app.route("/add_ocr", methods=["POST"])
def add_ocr():
    if "image" not in request.files:
        flash("⚠️ No image uploaded.")
        return redirect(url_for("index"))

    image = request.files["image"]
    if image.filename == "":
        flash("⚠️ No image selected.")
        return redirect(url_for("index"))

    # Save uploaded image
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], image.filename)
    image.save(image_path)

    # OCR processing
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    text = pytesseract.image_to_string(thresh)

    expiry_date = extract_expiry_date(text)
    if not expiry_date:
        flash("⚠️ Could not detect expiry date from image.")
        return redirect(url_for("index"))

    name = request.form.get("ocr_name", "Unknown Product")

    new_item = Item(
        name=name,
        expiry_date=expiry_date,
        image_path=image_path
    )
    db.session.add(new_item)
    db.session.commit()

    flash(f"✅ {name} added via OCR with expiry {expiry_date}.")
    return redirect(url_for("index"))

@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash(f"🗑️ {item.name} deleted successfully.")
    return redirect(url_for("index"))

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)







