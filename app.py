from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timezone
import os
import json
import firebase_admin
from firebase_admin import credentials, db
import uuid

# --- Flask app setup ---
app = Flask(__name__)

# --- Firebase configuration from environment variables ---
firebase_url = os.getenv("FIREBASE_DATABASE_URL")

# Render does not support JSON files directly, so we rebuild the credentials dict manually
firebase_creds = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL')}"
}

if not firebase_url:
    raise RuntimeError("FIREBASE_DATABASE_URL missing from environment variables.")

# --- Initialize Firebase ---
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred, {"databaseURL": firebase_url})

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

# --- Inject current time ---
@app.context_processor
def inject_now():
    return {"now": datetime.now(timezone.utc)}

# --- Routes ---
@app.route("/")
def index():
    records_snapshot = DB_REF.get() or {}
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
