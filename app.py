import os
import json
import base64
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for, jsonify
import firebase_admin
from firebase_admin import credentials, db, storage
import logging

app = Flask(__name__)

# --- Logging ---
logging.basicConfig(level=logging.INFO)

# --- Load Firebase config from environment ---
firebase_base64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64")
firebase_db_url = os.environ.get("FIREBASE_DATABASE_URL")
firebase_bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")

if not firebase_base64:
    raise ValueError("Missing FIREBASE_SERVICE_ACCOUNT_BASE64 environment variable")
if not firebase_db_url:
    raise ValueError("Missing FIREBASE_DATABASE_URL environment variable")
if not firebase_bucket:
    raise ValueError("Missing FIREBASE_STORAGE_BUCKET environment variable")

# Decode Base64 Firebase credentials
firebase_json = json.loads(base64.b64decode(firebase_base64).decode("utf-8"))

# --- Initialize Firebase ---
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred, {
        "databaseURL": firebase_db_url,
        "storageBucket": firebase_bucket
    })

DB_REF = db.reference("records")
BUCKET = storage.bucket()

# --- Helper ---
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
        "wife_epic": "",
        "remark": "",
        "pdf_urls": [],
        "created_date": "",
        "updated_date": ""
    }
    defaults.update(d)
    return defaults


@app.context_processor
def inject_now():
    return {"now": datetime.now(ZoneInfo("Asia/Kolkata"))}


# --- Routes ---
@app.route("/")
def index():
    try:
        records_snapshot = DB_REF.get()
    except Exception as e:
        app.logger.warning(f"⚠️ Firebase read failed: {e}")
        records_snapshot = None

    if records_snapshot is None:
        DB_REF.set({})
        records_snapshot = {}

    records = []
    for rid, data in records_snapshot.items():
        rec = default_record(data)
        rec["id"] = rid
        if isinstance(rec.get("pdf_urls"), str):
            rec["pdf_urls"] = [rec["pdf_urls"]]
        records.append(rec)
    records.sort(key=lambda r: r.get("name", "").lower())
    return render_template("index.html", records=records)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        rec_id = str(uuid.uuid4())
        current_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

        pdf_files = request.files.getlist("pdfs")
        pdf_urls = []
        for pdf_file in pdf_files:
            if pdf_file and pdf_file.filename.endswith(".pdf"):
                blob = BUCKET.blob(f"pdfs/{rec_id}/{pdf_file.filename}")
                blob.upload_from_file(pdf_file, content_type="application/pdf")
                blob.make_public()
                pdf_urls.append(blob.public_url)

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
            "wife_epic": request.form.get("wife_epic", ""),
            "remark": request.form.get("remark", ""),
            "pdf_urls": pdf_urls,
            "created_date": current_time,
            "updated_date": current_time
        })

        DB_REF.child(rec_id).set(data)
        app.logger.info(f"✅ Added record {rec_id}")
        return redirect(url_for("index"))

    return render_template("form.html", action="Add", rec=None)


@app.route("/edit/<string:id>", methods=["GET", "POST"])
def edit(id):
    rec_snapshot = DB_REF.child(id).get()
    if not rec_snapshot:
        return "Record not found", 404

    if request.method == "POST":
        updated_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
        existing_pdfs = rec_snapshot.get("pdf_urls", [])
        if isinstance(existing_pdfs, str):
            existing_pdfs = [existing_pdfs]

        pdf_files = request.files.getlist("pdfs")
        for pdf_file in pdf_files:
            if pdf_file and pdf_file.filename.endswith(".pdf"):
                blob = BUCKET.blob(f"pdfs/{id}/{pdf_file.filename}")
                blob.upload_from_file(pdf_file, content_type="application/pdf")
                blob.make_public()
                existing_pdfs.append(blob.public_url)

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
            "wife_epic": request.form.get("wife_epic", ""),
            "remark": request.form.get("remark", rec_snapshot.get("remark", "")),
            "pdf_urls": existing_pdfs,
            "created_date": rec_snapshot.get("created_date", ""),
            "updated_date": updated_time
        })

        DB_REF.child(id).update(updated)
        app.logger.info(f"✏️ Updated record {id}")
        return redirect(url_for("index"))

    rec = default_record(rec_snapshot)
    rec["id"] = id
    return render_template("form.html", action="Edit", rec=rec)


# ✅ unified delete route (one only!)
@app.route("/delete_pdf/<string:record_id>", methods=["POST"])
def delete_pdf_route(record_id):
    """Delete a specific PDF URL from record and Firebase Storage."""
    pdf_url = request.form.get("pdf_url")
    filename = pdf_url.split("/")[-1] if pdf_url else ""

    if filename:
        blob = BUCKET.blob(f"pdfs/{record_id}/{filename}")
        if blob.exists():
            blob.delete()
            app.logger.info(f"🗑 Deleted PDF: {filename}")

    rec = DB_REF.child(record_id).get()
    if rec and "pdf_urls" in rec:
        updated_pdfs = [url for url in rec["pdf_urls"] if url != pdf_url]
        DB_REF.child(record_id).update({"pdf_urls": updated_pdfs})
        app.logger.info(f"Updated record {record_id} PDF list")

    return redirect(url_for("edit", id=record_id))


@app.route("/update_remark", methods=["POST"])
def update_remark():
    id = request.form["id"]
    remark = request.form["remark"]
    DB_REF.child(id).update({"remark": remark})
    app.logger.info(f"Remark updated for {id}")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
