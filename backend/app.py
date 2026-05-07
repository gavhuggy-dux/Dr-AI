#!/usr/bin/env python3
"""Dr. AI — Medical Diagnostic & Patient Portal"""
import json, os, re, secrets, hashlib, base64, time, io, uuid
from datetime import datetime, timedelta
from functools import wraps

import sqlite3
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, send_from_directory, make_response
import bcrypt

# ── Init ──────────────────────────────────────────────────────────────
DB_PATH = "/data/drai/drai.db"
UPLOAD_DIR = "/data/drai/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("DRAI_SECRET", secrets.token_hex(32))

app.config.update(
    MAX_CONTENT_LENGTH=50*1024*1024,  # 50MB upload max
)

from database import get_db, init_db

# ── Helpers ───────────────────────────────────────────────────────────

def generate_patient_id(country="UK"):
    rand = secrets.token_hex(3).upper()
    return f"DRAI-{country}-{datetime.now().year}-{rand}"

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("patient_id") and not session.get("admin"):
            if request.is_json:
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            if request.is_json:
                return jsonify({"error": "Admin only"}), 403
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def send_verification_email(email, code):
    """Send verification code via SMTP. Uses m271.com mail server."""
    import smtplib
    from email.mime.text import MIMEText
    try:
        msg = MIMEText(f"Your Dr. AI verification code is: {code}\n\nThis code expires in 10 minutes.")
        msg["Subject"] = "Dr. AI — Verify Your Email"
        msg["From"] = "noreply@m271.com"
        msg["To"] = email
        
        s = smtplib.SMTP("mail.m271.com", 587, timeout=10)
        s.starttls()
        s.login("noreply@m271.com", "Scuzzi12@12")
        s.send_message(msg)
        s.quit()
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

def send_verification_sms(phone, code):
    """Send SMS via Twilio Verify. Twilio generates and sends its own code via SMS."""
    try:
        from twilio.rest import Client
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        verify_sid = os.environ.get("TWILIO_VERIFY_SID", "VAb366072bf591e8b10975ed752a04ae0f")
        
        if account_sid and auth_token:
            client = Client(account_sid, auth_token)
            verification = client.verify.v2.services(verify_sid).verifications.create(
                to=phone, channel="sms"
            )
            return verification.status == "pending"
        else:
            print(f"[SMS would send] To: {phone} (no Twilio creds)")
            return True
    except Exception as e:
        print(f"SMS send failed: {e}")
        return False

def generate_code():
    return str(secrets.randbelow(900000) + 100000)  # 6-digit code

# ── Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if session.get("patient_id"):
        return redirect(url_for("dashboard"))
    if session.get("admin"):
        return redirect(url_for("admin_panel"))
    return render_template("drai_index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form
        first = data.get("first_name", "").strip()
        last = data.get("last_name", "").strip()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        dob = data.get("date_of_birth", "").strip()
        password = data.get("password", "")
        
        errors = []
        if not first or not last: errors.append("Name required")
        if not email: errors.append("Email required")
        if len(password) < 8: errors.append("Password must be 8+ characters")
        if errors:
            return render_template("drai_register.html", error=", ".join(errors))
        
        conn = get_db()
        existing = conn.execute("SELECT patient_id FROM patients WHERE email=?", (email,)).fetchone()
        if existing:
            conn.close()
            return render_template("drai_register.html", error="Email already registered")
        
        patient_id = generate_patient_id()
        
        # Calculate age from DOB
        age = 0
        if dob:
            try:
                born = datetime.strptime(dob, "%Y-%m-%d")
                today = datetime.now()
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            except: pass
        
        conn.execute("""INSERT INTO patients 
            (patient_id, first_name, last_name, date_of_birth, age, email, phone, preferred_name)
            VALUES (?,?,?,?,?,?,?,?)""",
            (patient_id, first, last, dob, age, email, phone, first))
        
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        conn.execute("INSERT INTO auth_credentials (patient_id, password_hash) VALUES (?,?)",
            (patient_id, pw_hash))
        
        # Generate verification codes
        email_code = generate_code()
        phone_code = generate_code()
        expires = (datetime.now() + timedelta(minutes=10)).isoformat()
        
        conn.execute("INSERT INTO verification_codes (patient_id, contact, contact_type, code, expires_at) VALUES (?,?,?,?,?)",
            (patient_id, email, "email", email_code, expires))
        if phone:
            conn.execute("INSERT INTO verification_codes (patient_id, contact, contact_type, code, expires_at) VALUES (?,?,?,?,?)",
                (patient_id, phone, "phone", phone_code, expires))
        conn.commit()
        conn.close()
        
        # Send verification codes
        send_verification_email(email, email_code)
        if phone:
            send_verification_sms(phone, phone_code)
        
        session["verify_patient_id"] = patient_id
        return redirect(url_for("verify"))
    
    return render_template("drai_register.html")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    patient_id = session.get("verify_patient_id")
    if not patient_id:
        return redirect(url_for("register"))
    
    if request.method == "POST":
        email_code = request.form.get("email_code", "").strip()
        phone_code = request.form.get("phone_code", "").strip()
        
        now = datetime.now().isoformat()
        conn = get_db()
        
        if email_code:
            row = conn.execute("""SELECT id FROM verification_codes 
                WHERE patient_id=? AND contact_type='email' AND code=? AND expires_at>? AND verified=0""",
                (patient_id, email_code, now)).fetchone()
            if row:
                conn.execute("UPDATE verification_codes SET verified=1 WHERE id=?", (row["id"],))
                conn.execute("UPDATE patients SET email_verified=1 WHERE patient_id=?", (patient_id,))
        
        if phone_code and request.form.get("phone_code"):
            # Check via Twilio Verify API
            phone = conn.execute("SELECT phone FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
            verified = False
            if phone and phone["phone"]:
                try:
                    from twilio.rest import Client
                    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
                    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
                    verify_sid = os.environ.get("TWILIO_VERIFY_SID", "VAb366072bf591e8b10975ed752a04ae0f")
                    if account_sid and auth_token:
                        client = Client(account_sid, auth_token)
                        check = client.verify.v2.services(verify_sid).verification_checks.create(
                            to=phone["phone"], code=phone_code
                        )
                        verified = check.status == "approved"
                except Exception as e:
                    print(f"Twilio Verify check failed: {e}")
                    # Fallback: check local DB
                    row = conn.execute("""SELECT id FROM verification_codes 
                        WHERE patient_id=? AND contact_type='phone' AND code=? AND expires_at>? AND verified=0""",
                        (patient_id, phone_code, now)).fetchone()
                    if row:
                        conn.execute("UPDATE verification_codes SET verified=1 WHERE id=?", (row["id"],))
                        verified = True
            if verified:
                conn.execute("UPDATE patients SET phone_verified=1 WHERE patient_id=?", (patient_id,))
        
        conn.commit()
        
        # Check if at least email is verified
        patient = conn.execute("SELECT email_verified FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
        conn.close()
        
        if patient and patient["email_verified"]:
            session.pop("verify_patient_id", None)
            session["patient_id"] = patient_id
            return redirect(url_for("dashboard"))
        
        return render_template("drai_verify.html", error="Codes didn't match. Try again.")
    
    conn = get_db()
    patient = conn.execute("SELECT email, phone FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
    conn.close()
    return render_template("drai_verify.html", patient=dict(patient) if patient else {})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        conn = get_db()
        row = conn.execute("""SELECT p.patient_id, a.password_hash 
            FROM patients p JOIN auth_credentials a ON p.patient_id=a.patient_id 
            WHERE p.email=?""", (email,)).fetchone()
        conn.close()
        
        if row and bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
            session["patient_id"] = row["patient_id"]
            return redirect(url_for("dashboard"))
        
        return render_template("drai_login.html", error="Invalid email or password")
    
    return render_template("drai_login.html")

@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        admin_pw = os.environ.get("DRAI_ADMIN_PASSWORD", "DrAI2025!")
        if pw == admin_pw:
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        return render_template("drai_admin_login.html", error="Wrong password")
    return render_template("drai_admin_login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ── Patient Dashboard ─────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    pid = session["patient_id"]
    conn = get_db()
    patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
    recent_consultations = conn.execute(
        "SELECT id, main_complaint, consultation_date FROM consultations WHERE patient_id=? ORDER BY id DESC LIMIT 5",
        (pid,)).fetchall()
    meds = conn.execute(
        "SELECT medication_name, dosage, status FROM medications WHERE patient_id=? AND status='current'",
        (pid,)).fetchall()
    conn.close()
    return render_template("drai_dashboard.html",
        patient=dict(patient) if patient else {},
        consultations=[dict(c) for c in recent_consultations],
        medications=[dict(m) for m in meds],
    )

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    pid = session["patient_id"]
    conn = get_db()
    
    if request.method == "POST":
        fields = ["preferred_name","address","phone","emergency_contact","occupation",
                   "height","weight","smoking_status","alcohol_use","activity_level",
                   "gp_name","gp_address","gp_phone","gp_email","ethnicity","blood_type"]
        updates = {f: request.form.get(f, "") for f in fields}
        updates["updated_at"] = datetime.now().isoformat()
        
        # Calculate BMI
        try:
            h = float(updates.get("height", 0) or 0) / 100
            w = float(updates.get("weight", 0) or 0)
            updates["bmi"] = round(w / (h*h), 1) if h > 0 and w > 0 else None
        except: pass
        
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [pid]
        conn.execute(f"UPDATE patients SET {set_clause} WHERE patient_id=?", values)
        conn.commit()
    
    patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
    allergies = conn.execute("SELECT * FROM allergies WHERE patient_id=?", (pid,)).fetchall()
    conditions = conn.execute("SELECT * FROM medical_history WHERE patient_id=?", (pid,)).fetchall()
    conn.close()
    
    return render_template("drai_profile.html",
        patient=dict(patient) if patient else {},
        allergies=[dict(a) for a in allergies],
        conditions=[dict(c) for c in conditions],
    )

@app.route("/medical-history")
@login_required
def medical_history():
    pid = session["patient_id"]
    conn = get_db()
    conditions = conn.execute("SELECT * FROM medical_history WHERE patient_id=? ORDER BY diagnosis_date DESC", (pid,)).fetchall()
    surgeries = conn.execute("SELECT * FROM surgeries WHERE patient_id=? ORDER BY date DESC", (pid,)).fetchall()
    family = conn.execute("SELECT * FROM family_history WHERE patient_id=?", (pid,)).fetchall()
    meds = conn.execute("SELECT * FROM medications WHERE patient_id=? ORDER BY start_date DESC", (pid,)).fetchall()
    vitals = conn.execute("SELECT * FROM vitals WHERE patient_id=? ORDER BY recorded_at DESC LIMIT 20", (pid,)).fetchall()
    labs = conn.execute("SELECT * FROM lab_results WHERE patient_id=? ORDER BY test_date DESC LIMIT 20", (pid,)).fetchall()
    conn.close()
    return render_template("drai_medical_history.html",
        conditions=[dict(c) for c in conditions],
        surgeries=[dict(s) for s in surgeries],
        family=[dict(f) for f in family],
        medications=[dict(m) for m in meds],
        vitals=[dict(v) for v in vitals],
        labs=[dict(l) for l in labs],
    )

# ── Dr. AI Consultation ───────────────────────────────────────────────

@app.route("/consult")
@login_required
def consult():
    return render_template("drai_consult.html")

@app.route("/api/consult", methods=["POST"])
@login_required
def api_consult():
    """Save consultation to database."""
    pid = session["patient_id"]
    data = request.get_json()
    
    conn = get_db()
    conn.execute("""INSERT INTO consultations 
        (patient_id, main_complaint, consultation_summary, differential_diagnosis,
         most_likely_condition, dangerous_conditions, confidence_level,
         supporting_evidence, contradicting_evidence, recommended_tests,
         treatment_plan, referrals, follow_up_required, emergency_flag,
         doctor_reasoning, patient_questions, recommended_actions)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (pid, data.get("main_complaint"), data.get("summary"),
         data.get("differential"), data.get("most_likely"), data.get("dangerous"),
         data.get("confidence"), data.get("evidence"), data.get("contradicting"),
         data.get("tests"), data.get("treatment"), data.get("referrals"),
         data.get("follow_up"), 1 if data.get("emergency") else 0,
         data.get("reasoning"), data.get("questions"), data.get("actions")))
    conn.commit()
    consultation_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    
    return jsonify({"status": "saved", "consultation_id": consultation_id})

@app.route("/consultations")
@login_required
def consultations_list():
    pid = session["patient_id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT id, main_complaint, consultation_date, confidence_level, emergency_flag FROM consultations WHERE patient_id=? ORDER BY id DESC",
        (pid,)).fetchall()
    conn.close()
    return render_template("drai_consultations.html", consultations=[dict(r) for r in rows])

@app.route("/consultations/<int:cid>")
@login_required
def consultation_detail(cid):
    pid = session["patient_id"]
    conn = get_db()
    row = conn.execute("SELECT * FROM consultations WHERE id=? AND patient_id=?", (cid, pid)).fetchone()
    conn.close()
    if not row:
        return "Not found", 404
    return render_template("drai_consultation_view.html", c=dict(row))

# ── Document Upload ───────────────────────────────────────────────────

@app.route("/documents")
@login_required
def documents():
    pid = session["patient_id"]
    conn = get_db()
    rows = conn.execute("SELECT * FROM documents WHERE patient_id=? ORDER BY uploaded_at DESC", (pid,)).fetchall()
    conn.close()
    return render_template("drai_documents.html", documents=[dict(r) for r in rows])

@app.route("/documents/upload", methods=["POST"])
@login_required
def upload_document():
    pid = session["patient_id"]
    
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    safe_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    f.save(filepath)
    
    doc_type = request.form.get("document_type", "other")
    description = request.form.get("description", "")
    file_size = os.path.getsize(filepath)
    mime = f.content_type or "application/octet-stream"
    
    conn = get_db()
    conn.execute("""INSERT INTO documents 
        (patient_id, document_type, filename, original_name, file_path, file_size, mime_type, description)
        VALUES (?,?,?,?,?,?,?,?)""",
        (pid, doc_type, safe_name, f.filename, filepath, file_size, mime, description))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "uploaded", "filename": f.filename, "size": file_size})

@app.route("/documents/<int:did>/download")
@login_required
def download_document(did):
    pid = session["patient_id"]
    conn = get_db()
    doc = conn.execute("SELECT * FROM documents WHERE id=? AND patient_id=?", (did, pid)).fetchone()
    conn.close()
    if not doc:
        return "Not found", 404
    return send_from_directory(os.path.dirname(doc["file_path"]), doc["filename"],
        download_name=doc["original_name"])

@app.route("/documents/<int:did>/delete", methods=["POST"])
@login_required
def delete_document(did):
    pid = session["patient_id"]
    conn = get_db()
    doc = conn.execute("SELECT * FROM documents WHERE id=? AND patient_id=?", (did, pid)).fetchone()
    if doc:
        try: os.remove(doc["file_path"])
        except: pass
        conn.execute("DELETE FROM documents WHERE id=?", (did,))
        conn.commit()
    conn.close()
    return redirect(url_for("documents"))

# ── Camera Upload (from phone) ────────────────────────────────────────

@app.route("/api/camera-upload", methods=["POST"])
@login_required
def camera_upload():
    pid = session["patient_id"]
    
    data = request.get_data()
    if not data:
        return jsonify({"error": "No image data"}), 400
    
    safe_name = f"camera_{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    with open(filepath, "wb") as f:
        f.write(data)
    
    file_size = os.path.getsize(filepath)
    
    conn = get_db()
    conn.execute("""INSERT INTO documents 
        (patient_id, document_type, filename, original_name, file_path, file_size, mime_type, description)
        VALUES (?,?,?,?,?,?,?,?)""",
        (pid, "scan", safe_name, f"Camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
         filepath, file_size, "image/jpeg", "Camera scan"))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "uploaded", "filename": safe_name})

# ── Admin ─────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_panel():
    conn = get_db()
    patients = conn.execute("SELECT patient_id, first_name, last_name, age, email, phone, created_at FROM patients ORDER BY created_at DESC").fetchall()
    total = len(patients)
    consultations = conn.execute("SELECT COUNT(*) FROM consultations").fetchone()[0]
    conn.close()
    return render_template("drai_admin.html",
        patients=[dict(p) for p in patients],
        total_patients=total,
        total_consultations=consultations,
    )

@app.route("/admin/patient/<pid>")
@admin_required
def admin_patient(pid):
    conn = get_db()
    patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
    consults = conn.execute("SELECT * FROM consultations WHERE patient_id=? ORDER BY id DESC", (pid,)).fetchall()
    docs = conn.execute("SELECT * FROM documents WHERE patient_id=? ORDER BY uploaded_at DESC", (pid,)).fetchall()
    conn.close()
    if not patient:
        return "Not found", 404
    return render_template("drai_admin_patient.html",
        patient=dict(patient),
        consultations=[dict(c) for c in consults],
        documents=[dict(d) for d in docs],
    )


# ============================================================
# v2: Credits and Billing API
# ============================================================

@app.route("/api/credits/balance")
@login_required
def api_credits_balance():
    pid = session["patient_id"]
    bal = get_credit_balance(pid)
    return jsonify({"patient_id": pid, "balance": bal})

@app.route("/api/credits/packages")
def api_credit_packages():
    conn = get_db()
    rows = conn.execute("SELECT id, name, price_pence, credits FROM credit_packages WHERE active=1").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/credits/create-checkout", methods=["POST"])
@login_required
def api_create_checkout():
    pid = session["patient_id"]
    data = request.get_json()
    package_id = data.get("package_id")
    if not package_id:
        return jsonify({"error": "package_id required"}), 400
    conn = get_db()
    pkg = conn.execute("SELECT * FROM credit_packages WHERE id=? AND active=1", (package_id,)).fetchone()
    conn.close()
    if not pkg:
        return jsonify({"error": "Invalid package"}), 404
    try:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or get_setting("stripe_secret_key")
        if not stripe.api_key:
            return jsonify({"error": "Stripe not configured"}), 500
        stripe_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "gbp",
                    "product_data": {"name": f"{pkg["credits"]} Credits - {pkg["name"]}"},
                    "unit_amount": pkg["price_pence"],
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=request.host_url + "payment/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.host_url + "payment/cancelled",
            metadata={"patient_id": pid, "package_id": str(package_id), "credits": str(pkg["credits"])},
        )
        return jsonify({"url": stripe_session.url, "session_id": stripe_session.id})
    except Exception as e:
        print(f"Stripe checkout error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stripe/webhook", methods=["POST"])
def api_stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET") or get_setting("stripe_webhook_secret")
    if endpoint_secret:
        try:
            import stripe
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or get_setting("stripe_secret_key")
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except Exception as e:
            print(f"Stripe webhook verification failed: {e}")
            return jsonify({"error": "Invalid signature"}), 400
    else:
        try:
            event = json.loads(payload)
        except:
            return jsonify({"error": "Invalid payload"}), 400
    if event.get("type") == "checkout.session.completed":
        sesh = event["data"]["object"]
        pid = sesh.get("metadata", {}).get("patient_id")
        credits = int(sesh.get("metadata", {}).get("credits", 0))
        if pid and credits:
            add_credits(pid, credits, reference=sesh.get("id", ""), stripe_session_id=sesh.get("id", ""))
            print(f"Credited {credits} to {pid}")
    return jsonify({"status": "ok"})

@app.route("/payment/success")
def payment_success():
    return "<h2>Payment successful!</h2><p>Your credits have been added. You can close this window.</p>"

@app.route("/payment/cancelled")
def payment_cancelled():
    return "<h2>Payment cancelled.</h2><p>No credits were charged.</p>"

@app.route("/api/credits/history")
@login_required
def api_credit_history():
    pid = session["patient_id"]
    conn = get_db()
    rows = conn.execute("SELECT * FROM credit_transactions WHERE patient_id=? ORDER BY id DESC LIMIT 50", (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ============================================================
# v2: Appointments API
# ============================================================

@app.route("/api/appointments")
@login_required
def api_appointments():
    pid = session["patient_id"]
    conn = get_db()
    rows = conn.execute("SELECT * FROM appointments WHERE patient_id=? ORDER BY id DESC", (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/appointments/book", methods=["POST"])
@login_required
def api_book_appointment():
    pid = session["patient_id"]
    data = request.get_json()
    complaint = data.get("main_complaint", "")
    duration = int(data.get("duration_minutes", 15))
    cost = int(get_setting("credit_cost_per_15min", 1))
    total_cost = max(1, round(cost * duration / 15))
    if not spend_credits(pid, total_cost, reference="appointment"):
        return jsonify({"error": "Insufficient credits"}), 400
    conn = get_db()
    sql = "INSERT INTO appointments (patient_id, status, credits_cost, duration_minutes, main_complaint, timer_remaining_seconds) VALUES (?, 'pending', ?, ?, ?, ?)"
    conn.execute(sql, (pid, total_cost, duration, complaint, duration * 60))
    conn.commit()
    apt_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify({"status": "booked", "id": apt_id})

@app.route("/api/appointments/start/<int:apt_id>", methods=["POST"])
@login_required
def api_start_appointment(apt_id):
    pid = session["patient_id"]
    conn = get_db()
    apt = conn.execute("SELECT * FROM appointments WHERE id=? AND patient_id=?", (apt_id, pid)).fetchone()
    if not apt:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    conn.execute("UPDATE appointments SET status='in_progress', started_at=datetime('now') WHERE id=?", (apt_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "started", "duration_minutes": apt["duration_minutes"]})

@app.route("/api/appointments/complete/<int:apt_id>", methods=["POST"])
@login_required
def api_complete_appointment(apt_id):
    pid = session["patient_id"]
    conn = get_db()
    conn.execute("UPDATE appointments SET status='completed', completed_at=datetime('now') WHERE id=? AND patient_id=?", (apt_id, pid))
    conn.commit()
    conn.close()
    return jsonify({"status": "completed"})

@app.route("/api/appointments/cancel/<int:apt_id>", methods=["POST"])
@login_required
def api_cancel_appointment(apt_id):
    pid = session["patient_id"]
    conn = get_db()
    apt = conn.execute("SELECT * FROM appointments WHERE id=? AND patient_id=?", (apt_id, pid)).fetchone()
    if not apt:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    if apt["status"] in ("pending",):
        add_credits(pid, apt["credits_cost"], reference="refund-appt-" + str(apt_id))
    conn.execute("UPDATE appointments SET status='cancelled', cancelled_at=datetime('now') WHERE id=?", (apt_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "cancelled", "refunded": apt["credits_cost"] if apt["status"] == "pending" else 0})

# ============================================================
# v2: Ads API
# ============================================================

@app.route("/api/ads/next")
@login_required
def api_next_ad():
    conn = get_db()
    row = conn.execute("SELECT id, name, image_url, link_url, alt_text, display_duration_seconds FROM ads WHERE active=1 ORDER BY impressions ASC, RANDOM() LIMIT 1").fetchone()
    if row:
        conn.execute("UPDATE ads SET impressions=impressions+1 WHERE id=?", (row["id"],))
        conn.commit()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"id": 0, "name": "", "image_url": "", "link_url": "", "alt_text": "No ads", "display_duration_seconds": 10})

@app.route("/api/ads/tickers")
@login_required
def api_ad_tickers():
    conn = get_db()
    top = conn.execute("SELECT text, scroll_speed_seconds FROM ad_tickers WHERE position='top' AND active=1 ORDER BY RANDOM() LIMIT 1").fetchone()
    bottom = conn.execute("SELECT text, scroll_speed_seconds FROM ad_tickers WHERE position='bottom' AND active=1 ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    result = {}
    if top:
        result["top"] = {"text": top["text"], "speed": top["scroll_speed_seconds"]}
    else:
        result["top"] = {"text": "", "speed": 15}
    if bottom:
        result["bottom"] = {"text": bottom["text"], "speed": bottom["scroll_speed_seconds"]}
    else:
        result["bottom"] = {"text": "", "speed": 15}
    return jsonify(result)

@app.route("/api/ads/click/<int:ad_id>", methods=["POST"])
@login_required
def api_ad_click(ad_id):
    conn = get_db()
    conn.execute("UPDATE ads SET clicks=clicks+1 WHERE id=?", (ad_id,))
    conn.execute("INSERT INTO ad_impression_log (ad_id, patient_id, action) VALUES (?,?,?)",
        (ad_id, session["patient_id"], "click"))
    conn.commit()
    conn.close()
    return jsonify({"status": "logged"})

# ============================================================
# v2: Onboarding Progress API
# ============================================================

@app.route("/api/patient/onboarding-progress")
@login_required
def api_onboarding_progress():
    pid = session["patient_id"]
    progress = calculate_onboarding_progress(pid)
    target = int(get_setting("onboarding_target_percent", 80))
    progress["target"] = target
    return jsonify(progress)

# ============================================================
# v2: Patient info for mobile app (JSON)
# ============================================================

@app.route("/api/patient/profile")
@login_required
def api_patient_profile():
    pid = session["patient_id"]
    conn = get_db()
    patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
    bal = conn.execute("SELECT balance FROM credit_balance WHERE patient_id=?", (pid,)).fetchone()
    conn.close()
    if not patient:
        return jsonify({"error": "Not found"}), 404
    data = dict(patient)
    data["credit_balance"] = bal["balance"] if bal else 0
    return jsonify(data)

@app.route("/api/patient/profile", methods=["PUT"])
@login_required
def api_update_profile():
    pid = session["patient_id"]
    data = request.get_json()
    allowed = ["preferred_name","address","phone","emergency_contact","occupation",
        "height","weight","smoking_status","alcohol_use","activity_level",
        "gp_name","gp_address","gp_phone","gp_email","ethnicity","blood_type"]
    updates = {k: str(data[k]) for k in allowed if k in data}
    if not updates:
        return jsonify({"error": "No valid fields"}), 400
    try:
        h = float(updates.get("height", 0) or 0) / 100
        w = float(updates.get("weight", 0) or 0)
        if h > 0 and w > 0:
            updates["bmi"] = round(w / (h * h), 1)
    except:
        pass
    updates["updated_at"] = datetime.now().isoformat()
    conn = get_db()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE patients SET {set_clause} WHERE patient_id=?", list(updates.values()) + [pid])
    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})

@app.route("/api/documents")
@login_required
def api_documents():
    pid = session["patient_id"]
    conn = get_db()
    rows = conn.execute("SELECT * FROM documents WHERE patient_id=? ORDER BY uploaded_at DESC", (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    conn = get_db()
    row = conn.execute("SELECT p.patient_id, a.password_hash FROM patients p JOIN auth_credentials a ON p.patient_id=a.patient_id WHERE p.email=?", (email,)).fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        session["patient_id"] = row["patient_id"]
        return jsonify({"patient_id": row["patient_id"], "status": "ok"})
    return jsonify({"error": "Invalid credentials"}), 401

# ============================================================
# v2: Admin API
# ============================================================

@app.route("/api/admin/credit-packages")
def api_admin_credit_packages():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM credit_packages ORDER BY price_pence").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/credit-packages", methods=["POST"])
def api_admin_add_package():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    conn = get_db()
    conn.execute("INSERT INTO credit_packages (name, price_pence, credits, active) VALUES (?,?,?,?)",
        (data.get("name"), data.get("price_pence"), data.get("credits"), data.get("active", 1)))
    conn.commit()
    conn.close()
    return jsonify({"status": "added"})

@app.route("/api/admin/appointments")
def api_admin_appointments():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT a.*, p.first_name, p.last_name, p.email FROM appointments a JOIN patients p ON a.patient_id=p.patient_id ORDER BY a.id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/ads")
def api_admin_ads():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM ads ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/ads", methods=["POST"])
def api_admin_add_ad():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    conn = get_db()
    sql = "INSERT INTO ads (name, image_url, link_url, alt_text, display_duration_seconds, active) VALUES (?,?,?,?,?,?)"
    conn.execute(sql, (data.get("name"), data.get("image_url"), data.get("link_url"), data.get("alt_text"), data.get("display_duration_seconds", 10), data.get("active", 1)))
    conn.commit()
    conn.close()
    return jsonify({"status": "added"})

@app.route("/api/admin/tickers")
def api_admin_tickers():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM ad_tickers ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/tickers", methods=["POST"])
def api_admin_add_ticker():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    conn = get_db()
    sql = "INSERT INTO ad_tickers (text, position, scroll_speed_seconds, active) VALUES (?,?,?,?)"
    conn.execute(sql, (data.get("text"), data.get("position","top"), data.get("scroll_speed_seconds", 15), data.get("active", 1)))
    conn.commit()
    conn.close()
    return jsonify({"status": "added"})

@app.route("/api/admin/settings")
def api_admin_settings():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM app_settings ORDER BY key").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/settings", methods=["PUT"])
def api_admin_update_setting():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    key = data.get("key")
    value = data.get("value")
    if not key or value is None:
        return jsonify({"error": "key and value required"}), 400
    set_setting(key, value)
    return jsonify({"status": "updated"})



# ============================================================
# Admin Web Pages
# ============================================================

@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    patients = conn.execute("SELECT patient_id, first_name, last_name, email, created_at FROM patients ORDER BY created_at DESC LIMIT 10").fetchall()
    appointments = conn.execute("SELECT a.*, p.first_name, p.last_name FROM appointments a JOIN patients p ON a.patient_id=p.patient_id ORDER BY a.id DESC LIMIT 10").fetchall()
    pat_count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    cons_count = conn.execute("SELECT COUNT(*) FROM consultations").fetchone()[0]
    apt_count = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
    ad_count = conn.execute("SELECT COUNT(*) FROM ads WHERE active=1").fetchone()[0]
    doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    conn.close()
    enriched = []
    for p in patients:
        d = dict(p)
        d["credits"] = get_credit_balance(p["patient_id"])
        enriched.append(d)
    return render_template("admin/drai_admin_dashboard.html",
        stats={"patients": pat_count, "consultations": cons_count, "appointments": apt_count, "ads": ad_count, "documents": doc_count},
        patients=enriched, appointments=[dict(a) for a in appointments])

@app.route("/admin/packages", methods=["GET", "POST"])
def admin_packages():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    msg = None
    if request.method == "POST":
        conn = get_db()
        conn.execute("INSERT INTO credit_packages (name, price_pence, credits, active) VALUES (?,?,?,1)",
            (request.form.get("name"), int(request.form.get("price_pence")), int(request.form.get("credits"))))
        conn.commit()
        conn.close()
        msg = "Package added"
    conn = get_db()
    packages = conn.execute("SELECT * FROM credit_packages ORDER BY price_pence").fetchall()
    conn.close()
    return render_template("admin/drai_admin_packages.html", packages=[dict(p) for p in packages], msg=msg)

@app.route("/admin/packages/toggle/<int:pid>", methods=["POST"])
def admin_package_toggle(pid):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    conn.execute("UPDATE credit_packages SET active = CASE WHEN active THEN 0 ELSE 1 END WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_packages"))

@app.route("/admin/packages/delete/<int:pid>", methods=["POST"])
def admin_package_delete(pid):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    conn.execute("DELETE FROM credit_packages WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_packages"))

@app.route("/admin/ads", methods=["GET", "POST"])
def admin_ads():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    msg = None
    if request.method == "POST":
        conn = get_db()
        conn.execute("INSERT INTO ads (name, image_url, link_url, alt_text, display_duration_seconds, active) VALUES (?,?,?,?,?,1)",
            (request.form.get("name"), request.form.get("image_url"), request.form.get("link_url"),
             request.form.get("alt_text"), int(request.form.get("display_duration_seconds", 10))))
        conn.commit()
        conn.close()
        msg = "Ad added"
    conn = get_db()
    ads = conn.execute("SELECT * FROM ads ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin/drai_admin_ads.html", ads=[dict(a) for a in ads], msg=msg)

@app.route("/admin/ads/toggle/<int:aid>", methods=["POST"])
def admin_ad_toggle(aid):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    conn.execute("UPDATE ads SET active = CASE WHEN active THEN 0 ELSE 1 END WHERE id=?", (aid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_ads"))

@app.route("/admin/ads/delete/<int:aid>", methods=["POST"])
def admin_ad_delete(aid):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    conn.execute("DELETE FROM ads WHERE id=?", (aid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_ads"))

@app.route("/admin/tickers", methods=["GET", "POST"])
def admin_tickers():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    msg = None
    if request.method == "POST":
        conn = get_db()
        conn.execute("INSERT INTO ad_tickers (text, position, scroll_speed_seconds, active) VALUES (?,?,?,1)",
            (request.form.get("text"), request.form.get("position","top"), int(request.form.get("scroll_speed_seconds", 15))))
        conn.commit()
        conn.close()
        msg = "Ticker added"
    conn = get_db()
    tickers = conn.execute("SELECT * FROM ad_tickers ORDER BY id").fetchall()
    settings = conn.execute("SELECT * FROM app_settings ORDER BY key").fetchall()
    conn.close()
    return render_template("admin/drai_admin_tickers.html", tickers=[dict(t) for t in tickers], settings=[dict(s) for s in settings], msg=msg)

@app.route("/admin/tickers/toggle/<int:tid>", methods=["POST"])
def admin_ticker_toggle(tid):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    conn.execute("UPDATE ad_tickers SET active = CASE WHEN active THEN 0 ELSE 1 END WHERE id=?", (tid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_tickers"))

@app.route("/admin/tickers/delete/<int:tid>", methods=["POST"])
def admin_ticker_delete(tid):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    conn.execute("DELETE FROM ad_tickers WHERE id=?", (tid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_tickers"))

@app.route("/admin/settings/update", methods=["POST"])
def admin_setting_update():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    key = request.form.get("key")
    value = request.form.get("value")
    if key and value is not None:
        set_setting(key, value)
    return redirect(url_for("admin_tickers"))

@app.route("/admin/appointments")
def admin_appointments():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    status_filter = request.args.get("status")
    conn = get_db()
    if status_filter:
        rows = conn.execute("SELECT a.*, p.first_name, p.last_name FROM appointments a JOIN patients p ON a.patient_id=p.patient_id WHERE a.status=? ORDER BY a.id DESC", (status_filter,)).fetchall()
    else:
        rows = conn.execute("SELECT a.*, p.first_name, p.last_name FROM appointments a JOIN patients p ON a.patient_id=p.patient_id ORDER BY a.id DESC").fetchall()
    conn.close()
    return render_template("admin/drai_admin_appointments.html", appointments=[dict(r) for r in rows], page="appointments", status_filter=status_filter)

@app.route("/admin/patients")
def admin_patients():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    patients = conn.execute("SELECT * FROM patients ORDER BY created_at DESC").fetchall()
    conn.close()
    enriched = []
    for p in patients:
        d = dict(p)
        d["credits"] = get_credit_balance(p["patient_id"])
        prog = calculate_onboarding_progress(p["patient_id"])
        d["onboarding_progress"] = prog["percent"]
        enriched.append(d)
    return render_template("admin/drai_admin_appointments.html", patients=enriched, page="patients")

# ── Init ──────────────────────────────────────────────────────────────

if __name__ != "__main__":
    init_db()

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5003, debug=True)
