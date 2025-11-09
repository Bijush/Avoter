import os
import json
import base64
import uuid
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, jsonify
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- Load Firebase config from environment ---
firebase_base64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64")
firebase_db_url = os.environ.get("FIREBASE_DATABASE_URL")

if not firebase_base64:
    raise ValueError("Missing FIREBASE_SERVICE_ACCOUNT_BASE64 environment variable")
if not firebase_db_url:
    raise ValueError("Missing FIREBASE_DATABASE_URL environment variable")

# Decode Base64 Firebase credentials
firebase_json = json.loads(base64.b64decode(firebase_base64).decode("utf-8"))

# --- Initialize Firebase ---
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred, {"databaseURL": firebase_db_url})

DB_REF = db.reference("records")

# --- Helper function ---
def default_record(data=None):
    d = data or {}
    defaults = {
        "name": "",
        "epic": "",
        "ps": "",
        "old_house": "",
        "new_house": "",
        "payment": 0.0,
        "paid": "",
        "complete": "",
        "wife_name": "",
        "wife_payment": 0.0,
        "wife_paid": "",
        "wife_complete": "",
        "remark": ""
    }
    defaults.update(d)
    return defaults

# --- Inject current time into templates ---
@app.context_processor
def inject_now():
    return {"now": datetime.now(timezone.utc)}

# --- Routes ---
@app.route("/")
def index():
    # Try to safely read from Firebase
    try:
        records_snapshot = DB_REF.get()
    except Exception as e:
        print("⚠️ Firebase read failed:", e)
        records_snapshot = None

    # Create the /records node if missing
    if records_snapshot is None:
        DB_REF.set({})
        records_snapshot = {}

    records = []
    for rid, data in records_snapshot.items():
        rec = default_record(data)
        rec["id"] = rid
        records.append(rec)
    records.sort(key=lambda r: r.get("name", "").lower())
    return render_template("index.html", records=records)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        rec_id = str(uuid.uuid4())
        data = default_record({
            "name": request.form.get("name", "").strip(),
            "epic": request.form.get("epic", "").strip(),
            "ps": request.form.get("ps", "").strip(),
            "old_house": request.form.get("old_house", "").strip(),
            "new_house": request.form.get("new_house", "").strip(),
            "payment": float(request.form.get("payment") or 0),
            "paid": request.form.get("paid", ""),
            "complete": request.form.get("complete", ""),
            "wife_name": request.form.get("wife_name", ""),
            "wife_payment": float(request.form.get("wife_payment") or 0),
            "wife_paid": request.form.get("wife_paid", ""),
            "wife_complete": request.form.get("wife_complete", ""),
            "remark": request.form.get("remark", "")
        })
        DB_REF.child(rec_id).set(data)
        return redirect(url_for("index"))
    return render_template("form.html", action="Add", rec=None)

@app.route("/edit/<string:id>", methods=["GET", "POST"])
def edit(id):
    rec_snapshot = DB_REF.child(id).get()
    if not rec_snapshot:
        return "Record not found", 404

    if request.method == "POST":
        updated = default_record({
            "name": request.form.get("name", "").strip(),
            "epic": request.form.get("epic", "").strip(),
            "ps": request.form.get("ps", "").strip(),
            "old_house": request.form.get("old_house", "").strip(),
            "new_house": request.form.get("new_house", "").strip(),
            "payment": float(request.form.get("payment") or 0),
            "paid": request.form.get("paid", ""),
            "complete": request.form.get("complete", ""),
            "wife_name": request.form.get("wife_name", ""),
            "wife_payment": float(request.form.get("wife_payment") or 0),
            "wife_paid": request.form.get("wife_paid", ""),
            "wife_complete": request.form.get("wife_complete", ""),
            "remark": request.form.get("remark", rec_snapshot.get("remark", ""))
        })
        DB_REF.child(id).update(updated)
        return redirect(url_for("index"))

    rec = default_record(rec_snapshot)
    rec["id"] = id
    return render_template("form.html", action="Edit", rec=rec)

@app.route("/delete/<string:id>", methods=["POST"])
def delete(id):
    DB_REF.child(id).delete()
    return redirect(url_for("index"))

@app.route("/update_remark", methods=["POST"])
def update_remark():
    id = request.form["id"]
    remark = request.form["remark"]
    DB_REF.child(id).update({"remark": remark})
    return ("", 204)

@app.route("/test_connection")
def test_connection():
    try:
        ref = db.reference("test_connection")
        ref.set({"status": "connected"})
        data = ref.get()
        return jsonify({"message": "✅ Firebase connected successfully!", "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Main entry ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
