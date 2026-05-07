     1|#!/usr/bin/env python3
     2|"""Dr. AI — Medical Diagnostic & Patient Portal"""
     3|import json, os, re, secrets, hashlib, base64, time, io, uuid
     4|from datetime import datetime, timedelta
     5|from functools import wraps
     6|
     7|import sqlite3
     8|from flask import Flask, jsonify, render_template, request, redirect, url_for, session, send_from_directory, make_response
     9|import bcrypt
    10|
    11|# ── Init ──────────────────────────────────────────────────────────────
    12|DB_PATH = "/data/drai/drai.db"
    13|UPLOAD_DIR = "/data/drai/uploads"
    14|os.makedirs(UPLOAD_DIR, exist_ok=True)
    15|
    16|app = Flask(__name__)
    17|app.secret_key = os.environ.get("DRAI_SECRET", secrets.token_hex(32))
    18|
    19|app.config.update(
    20|    MAX_CONTENT_LENGTH=50*1024*1024,  # 50MB upload max
    21|)
    22|
    23|from database import get_db, init_db
    24|
    25|# ── Helpers ───────────────────────────────────────────────────────────
    26|
    27|def generate_patient_id(country="UK"):
    28|    rand = secrets.token_hex(3).upper()
    29|    return f"DRAI-{country}-{datetime.now().year}-{rand}"
    30|
    31|def login_required(f):
    32|    @wraps(f)
    33|    def decorated(*args, **kwargs):
    34|        if not session.get("patient_id") and not session.get("admin"):
    35|            if request.is_json:
    36|                return jsonify({"error": "Unauthorized"}), 401
    37|            return redirect(url_for("login"))
    38|        return f(*args, **kwargs)
    39|    return decorated
    40|
    41|def admin_required(f):
    42|    @wraps(f)
    43|    def decorated(*args, **kwargs):
    44|        if not session.get("admin"):
    45|            if request.is_json:
    46|                return jsonify({"error": "Admin only"}), 403
    47|            return redirect(url_for("login"))
    48|        return f(*args, **kwargs)
    49|    return decorated
    50|
    51|def send_verification_email(email, code):
    52|    """Send verification code via SMTP. Uses m271.com mail server."""
    53|    import smtplib
    54|    from email.mime.text import MIMEText
    55|    try:
    56|        msg = MIMEText(f"Your Dr. AI verification code is: {code}\n\nThis code expires in 10 minutes.")
    57|        msg["Subject"] = "Dr. AI — Verify Your Email"
    58|        msg["From"] = "noreply@m271.com"
    59|        msg["To"] = email
    60|        
    61|        s = smtplib.SMTP("mail.m271.com", 587, timeout=10)
    62|        s.starttls()
    63|        s.login("noreply@m271.com", "Scuzzi12@12")
    64|        s.send_message(msg)
    65|        s.quit()
    66|        return True
    67|    except Exception as e:
    68|        print(f"Email send failed: {e}")
    69|        return False
    70|
    71|def send_verification_sms(phone, code):
    72|    """Send SMS via Twilio Verify. Twilio generates and sends its own code via SMS."""
    73|    try:
    74|        from twilio.rest import Client
    75|        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    76|        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    77|        verify_sid = os.environ.get("TWILIO_VERIFY_SID", "VAb366072bf591e8b10975ed752a04ae0f")
    78|        
    79|        if account_sid and auth_token:
    80|            client = Client(account_sid, auth_token)
    81|            verification = client.verify.v2.services(verify_sid).verifications.create(
    82|                to=phone, channel="sms"
    83|            )
    84|            return verification.status == "pending"
    85|        else:
    86|            print(f"[SMS would send] To: {phone} (no Twilio creds)")
    87|            return True
    88|    except Exception as e:
    89|        print(f"SMS send failed: {e}")
    90|        return False
    91|
    92|def generate_code():
    93|    return str(secrets.randbelow(900000) + 100000)  # 6-digit code
    94|
    95|# ── Routes ────────────────────────────────────────────────────────────
    96|
    97|@app.route("/")
    98|def index():
    99|    if session.get("patient_id"):
   100|        return redirect(url_for("dashboard"))
   101|    if session.get("admin"):
   102|        return redirect(url_for("admin_panel"))
   103|    return render_template("drai_index.html")
   104|
   105|@app.route("/register", methods=["GET", "POST"])
   106|def register():
   107|    if request.method == "POST":
   108|        data = request.form
   109|        first = data.get("first_name", "").strip()
   110|        last = data.get("last_name", "").strip()
   111|        email = data.get("email", "").strip()
   112|        phone = data.get("phone", "").strip()
   113|        dob = data.get("date_of_birth", "").strip()
   114|        password = data.get("password", "")
   115|        
   116|        errors = []
   117|        if not first or not last: errors.append("Name required")
   118|        if not email: errors.append("Email required")
   119|        if len(password) < 8: errors.append("Password must be 8+ characters")
   120|        if errors:
   121|            return render_template("drai_register.html", error=", ".join(errors))
   122|        
   123|        conn = get_db()
   124|        existing = conn.execute("SELECT patient_id FROM patients WHERE email=?", (email,)).fetchone()
   125|        if existing:
   126|            conn.close()
   127|            return render_template("drai_register.html", error="Email already registered")
   128|        
   129|        patient_id = generate_patient_id()
   130|        
   131|        # Calculate age from DOB
   132|        age = 0
   133|        if dob:
   134|            try:
   135|                born = datetime.strptime(dob, "%Y-%m-%d")
   136|                today = datetime.now()
   137|                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
   138|            except: pass
   139|        
   140|        conn.execute("""INSERT INTO patients 
   141|            (patient_id, first_name, last_name, date_of_birth, age, email, phone, preferred_name)
   142|            VALUES (?,?,?,?,?,?,?,?)""",
   143|            (patient_id, first, last, dob, age, email, phone, first))
   144|        
   145|        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
   146|        conn.execute("INSERT INTO auth_credentials (patient_id, password_hash) VALUES (?,?)",
   147|            (patient_id, pw_hash))
   148|        
   149|        # Generate verification codes
   150|        email_code = generate_code()
   151|        phone_code = generate_code()
   152|        expires = (datetime.now() + timedelta(minutes=10)).isoformat()
   153|        
   154|        conn.execute("INSERT INTO verification_codes (patient_id, contact, contact_type, code, expires_at) VALUES (?,?,?,?,?)",
   155|            (patient_id, email, "email", email_code, expires))
   156|        if phone:
   157|            conn.execute("INSERT INTO verification_codes (patient_id, contact, contact_type, code, expires_at) VALUES (?,?,?,?,?)",
   158|                (patient_id, phone, "phone", phone_code, expires))
   159|        conn.commit()
   160|        conn.close()
   161|        
   162|        # Send verification codes
   163|        send_verification_email(email, email_code)
   164|        if phone:
   165|            send_verification_sms(phone, phone_code)
   166|        
   167|        session["verify_patient_id"] = patient_id
   168|        return redirect(url_for("verify"))
   169|    
   170|    return render_template("drai_register.html")
   171|
   172|@app.route("/verify", methods=["GET", "POST"])
   173|def verify():
   174|    patient_id = session.get("verify_patient_id")
   175|    if not patient_id:
   176|        return redirect(url_for("register"))
   177|    
   178|    if request.method == "POST":
   179|        email_code = request.form.get("email_code", "").strip()
   180|        phone_code = request.form.get("phone_code", "").strip()
   181|        
   182|        now = datetime.now().isoformat()
   183|        conn = get_db()
   184|        
   185|        if email_code:
   186|            row = conn.execute("""SELECT id FROM verification_codes 
   187|                WHERE patient_id=? AND contact_type='email' AND code=? AND expires_at>? AND verified=0""",
   188|                (patient_id, email_code, now)).fetchone()
   189|            if row:
   190|                conn.execute("UPDATE verification_codes SET verified=1 WHERE id=?", (row["id"],))
   191|                conn.execute("UPDATE patients SET email_verified=1 WHERE patient_id=?", (patient_id,))
   192|        
   193|        if phone_code and request.form.get("phone_code"):
   194|            # Check via Twilio Verify API
   195|            phone = conn.execute("SELECT phone FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
   196|            verified = False
   197|            if phone and phone["phone"]:
   198|                try:
   199|                    from twilio.rest import Client
   200|                    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
   201|                    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
   202|                    verify_sid = os.environ.get("TWILIO_VERIFY_SID", "VAb366072bf591e8b10975ed752a04ae0f")
   203|                    if account_sid and auth_token:
   204|                        client = Client(account_sid, auth_token)
   205|                        check = client.verify.v2.services(verify_sid).verification_checks.create(
   206|                            to=phone["phone"], code=phone_code
   207|                        )
   208|                        verified = check.status == "approved"
   209|                except Exception as e:
   210|                    print(f"Twilio Verify check failed: {e}")
   211|                    # Fallback: check local DB
   212|                    row = conn.execute("""SELECT id FROM verification_codes 
   213|                        WHERE patient_id=? AND contact_type='phone' AND code=? AND expires_at>? AND verified=0""",
   214|                        (patient_id, phone_code, now)).fetchone()
   215|                    if row:
   216|                        conn.execute("UPDATE verification_codes SET verified=1 WHERE id=?", (row["id"],))
   217|                        verified = True
   218|            if verified:
   219|                conn.execute("UPDATE patients SET phone_verified=1 WHERE patient_id=?", (patient_id,))
   220|        
   221|        conn.commit()
   222|        
   223|        # Check if at least email is verified
   224|        patient = conn.execute("SELECT email_verified FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
   225|        conn.close()
   226|        
   227|        if patient and patient["email_verified"]:
   228|            session.pop("verify_patient_id", None)
   229|            session["patient_id"] = patient_id
   230|            return redirect(url_for("dashboard"))
   231|        
   232|        return render_template("drai_verify.html", error="Codes didn't match. Try again.")
   233|    
   234|    conn = get_db()
   235|    patient = conn.execute("SELECT email, phone FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
   236|    conn.close()
   237|    return render_template("drai_verify.html", patient=dict(patient) if patient else {})
   238|
   239|@app.route("/login", methods=["GET", "POST"])
   240|def login():
   241|    if request.method == "POST":
   242|        email = request.form.get("email", "").strip()
   243|        password = request.form.get("password", "")
   244|        
   245|        conn = get_db()
   246|        row = conn.execute("""SELECT p.patient_id, a.password_hash 
   247|            FROM patients p JOIN auth_credentials a ON p.patient_id=a.patient_id 
   248|            WHERE p.email=?""", (email,)).fetchone()
   249|        conn.close()
   250|        
   251|        if row and bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
   252|            session["patient_id"] = row["patient_id"]
   253|            return redirect(url_for("dashboard"))
   254|        
   255|        return render_template("drai_login.html", error="Invalid email or password")
   256|    
   257|    return render_template("drai_login.html")
   258|
   259|@app.route("/login/admin", methods=["GET", "POST"])
   260|def admin_login():
   261|    if request.method == "POST":
   262|        pw = request.form.get("password", "")
   263|        admin_pw = os.environ.get("DRAI_ADMIN_PASSWORD", "DrAI2025!")
   264|        if pw == admin_pw:
   265|            session["admin"] = True
   266|            return redirect(url_for("admin_panel"))
   267|        return render_template("drai_admin_login.html", error="Wrong password")
   268|    return render_template("drai_admin_login.html")
   269|
   270|@app.route("/logout")
   271|def logout():
   272|    session.clear()
   273|    return redirect(url_for("index"))
   274|
   275|# ── Patient Dashboard ─────────────────────────────────────────────────
   276|
   277|@app.route("/dashboard")
   278|@login_required
   279|def dashboard():
   280|    pid = session["patient_id"]
   281|    conn = get_db()
   282|    patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
   283|    recent_consultations = conn.execute(
   284|        "SELECT id, main_complaint, consultation_date FROM consultations WHERE patient_id=? ORDER BY id DESC LIMIT 5",
   285|        (pid,)).fetchall()
   286|    meds = conn.execute(
   287|        "SELECT medication_name, dosage, status FROM medications WHERE patient_id=? AND status='current'",
   288|        (pid,)).fetchall()
   289|    conn.close()
   290|    return render_template("drai_dashboard.html",
   291|        patient=dict(patient) if patient else {},
   292|        consultations=[dict(c) for c in recent_consultations],
   293|        medications=[dict(m) for m in meds],
   294|    )
   295|
   296|@app.route("/profile", methods=["GET", "POST"])
   297|@login_required
   298|def profile():
   299|    pid = session["patient_id"]
   300|    conn = get_db()
   301|    
   302|    if request.method == "POST":
   303|        fields = ["preferred_name","address","phone","emergency_contact","occupation",
   304|                   "height","weight","smoking_status","alcohol_use","activity_level",
   305|                   "gp_name","gp_address","gp_phone","gp_email","ethnicity","blood_type"]
   306|        updates = {f: request.form.get(f, "") for f in fields}
   307|        updates["updated_at"] = datetime.now().isoformat()
   308|        
   309|        # Calculate BMI
   310|        try:
   311|            h = float(updates.get("height", 0) or 0) / 100
   312|            w = float(updates.get("weight", 0) or 0)
   313|            updates["bmi"] = round(w / (h*h), 1) if h > 0 and w > 0 else None
   314|        except: pass
   315|        
   316|        set_clause = ", ".join(f"{k}=?" for k in updates)
   317|        values = list(updates.values()) + [pid]
   318|        conn.execute(f"UPDATE patients SET {set_clause} WHERE patient_id=?", values)
   319|        conn.commit()
   320|    
   321|    patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
   322|    allergies = conn.execute("SELECT * FROM allergies WHERE patient_id=?", (pid,)).fetchall()
   323|    conditions = conn.execute("SELECT * FROM medical_history WHERE patient_id=?", (pid,)).fetchall()
   324|    conn.close()
   325|    
   326|    return render_template("drai_profile.html",
   327|        patient=dict(patient) if patient else {},
   328|        allergies=[dict(a) for a in allergies],
   329|        conditions=[dict(c) for c in conditions],
   330|    )
   331|
   332|@app.route("/medical-history")
   333|@login_required
   334|def medical_history():
   335|    pid = session["patient_id"]
   336|    conn = get_db()
   337|    conditions = conn.execute("SELECT * FROM medical_history WHERE patient_id=? ORDER BY diagnosis_date DESC", (pid,)).fetchall()
   338|    surgeries = conn.execute("SELECT * FROM surgeries WHERE patient_id=? ORDER BY date DESC", (pid,)).fetchall()
   339|    family = conn.execute("SELECT * FROM family_history WHERE patient_id=?", (pid,)).fetchall()
   340|    meds = conn.execute("SELECT * FROM medications WHERE patient_id=? ORDER BY start_date DESC", (pid,)).fetchall()
   341|    vitals = conn.execute("SELECT * FROM vitals WHERE patient_id=? ORDER BY recorded_at DESC LIMIT 20", (pid,)).fetchall()
   342|    labs = conn.execute("SELECT * FROM lab_results WHERE patient_id=? ORDER BY test_date DESC LIMIT 20", (pid,)).fetchall()
   343|    conn.close()
   344|    return render_template("drai_medical_history.html",
   345|        conditions=[dict(c) for c in conditions],
   346|        surgeries=[dict(s) for s in surgeries],
   347|        family=[dict(f) for f in family],
   348|        medications=[dict(m) for m in meds],
   349|        vitals=[dict(v) for v in vitals],
   350|        labs=[dict(l) for l in labs],
   351|    )
   352|
   353|# ── Dr. AI Consultation ───────────────────────────────────────────────
   354|
   355|@app.route("/consult")
   356|@login_required
   357|def consult():
   358|    return render_template("drai_consult.html")
   359|
   360|@app.route("/api/consult", methods=["POST"])
   361|@login_required
   362|def api_consult():
   363|    """Save consultation to database."""
   364|    pid = session["patient_id"]
   365|    data = request.get_json()
   366|    
   367|    conn = get_db()
   368|    conn.execute("""INSERT INTO consultations 
   369|        (patient_id, main_complaint, consultation_summary, differential_diagnosis,
   370|         most_likely_condition, dangerous_conditions, confidence_level,
   371|         supporting_evidence, contradicting_evidence, recommended_tests,
   372|         treatment_plan, referrals, follow_up_required, emergency_flag,
   373|         doctor_reasoning, patient_questions, recommended_actions)
   374|        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
   375|        (pid, data.get("main_complaint"), data.get("summary"),
   376|         data.get("differential"), data.get("most_likely"), data.get("dangerous"),
   377|         data.get("confidence"), data.get("evidence"), data.get("contradicting"),
   378|         data.get("tests"), data.get("treatment"), data.get("referrals"),
   379|         data.get("follow_up"), 1 if data.get("emergency") else 0,
   380|         data.get("reasoning"), data.get("questions"), data.get("actions")))
   381|    conn.commit()
   382|    consultation_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
   383|    conn.close()
   384|    
   385|    return jsonify({"status": "saved", "consultation_id": consultation_id})
   386|
   387|@app.route("/consultations")
   388|@login_required
   389|def consultations_list():
   390|    pid = session["patient_id"]
   391|    conn = get_db()
   392|    rows = conn.execute(
   393|        "SELECT id, main_complaint, consultation_date, confidence_level, emergency_flag FROM consultations WHERE patient_id=? ORDER BY id DESC",
   394|        (pid,)).fetchall()
   395|    conn.close()
   396|    return render_template("drai_consultations.html", consultations=[dict(r) for r in rows])
   397|
   398|@app.route("/consultations/<int:cid>")
   399|@login_required
   400|def consultation_detail(cid):
   401|    pid = session["patient_id"]
   402|    conn = get_db()
   403|    row = conn.execute("SELECT * FROM consultations WHERE id=? AND patient_id=?", (cid, pid)).fetchone()
   404|    conn.close()
   405|    if not row:
   406|        return "Not found", 404
   407|    return render_template("drai_consultation_view.html", c=dict(row))
   408|
   409|# ── Document Upload ───────────────────────────────────────────────────
   410|
   411|@app.route("/documents")
   412|@login_required
   413|def documents():
   414|    pid = session["patient_id"]
   415|    conn = get_db()
   416|    rows = conn.execute("SELECT * FROM documents WHERE patient_id=? ORDER BY uploaded_at DESC", (pid,)).fetchall()
   417|    conn.close()
   418|    return render_template("drai_documents.html", documents=[dict(r) for r in rows])
   419|
   420|@app.route("/documents/upload", methods=["POST"])
   421|@login_required
   422|def upload_document():
   423|    pid = session["patient_id"]
   424|    
   425|    if "file" not in request.files:
   426|        return jsonify({"error": "No file"}), 400
   427|    
   428|    f = request.files["file"]
   429|    if f.filename == "":
   430|        return jsonify({"error": "No file selected"}), 400
   431|    
   432|    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
   433|    safe_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
   434|    filepath = os.path.join(UPLOAD_DIR, safe_name)
   435|    f.save(filepath)
   436|    
   437|    doc_type = request.form.get("document_type", "other")
   438|    description = request.form.get("description", "")
   439|    file_size = os.path.getsize(filepath)
   440|    mime = f.content_type or "application/octet-stream"
   441|    
   442|    conn = get_db()
   443|    conn.execute("""INSERT INTO documents 
   444|        (patient_id, document_type, filename, original_name, file_path, file_size, mime_type, description)
   445|        VALUES (?,?,?,?,?,?,?,?)""",
   446|        (pid, doc_type, safe_name, f.filename, filepath, file_size, mime, description))
   447|    conn.commit()
   448|    conn.close()
   449|    
   450|    return jsonify({"status": "uploaded", "filename": f.filename, "size": file_size})
   451|
   452|@app.route("/documents/<int:did>/download")
   453|@login_required
   454|def download_document(did):
   455|    pid = session["patient_id"]
   456|    conn = get_db()
   457|    doc = conn.execute("SELECT * FROM documents WHERE id=? AND patient_id=?", (did, pid)).fetchone()
   458|    conn.close()
   459|    if not doc:
   460|        return "Not found", 404
   461|    return send_from_directory(os.path.dirname(doc["file_path"]), doc["filename"],
   462|        download_name=doc["original_name"])
   463|
   464|@app.route("/documents/<int:did>/delete", methods=["POST"])
   465|@login_required
   466|def delete_document(did):
   467|    pid = session["patient_id"]
   468|    conn = get_db()
   469|    doc = conn.execute("SELECT * FROM documents WHERE id=? AND patient_id=?", (did, pid)).fetchone()
   470|    if doc:
   471|        try: os.remove(doc["file_path"])
   472|        except: pass
   473|        conn.execute("DELETE FROM documents WHERE id=?", (did,))
   474|        conn.commit()
   475|    conn.close()
   476|    return redirect(url_for("documents"))
   477|
   478|# ── Camera Upload (from phone) ────────────────────────────────────────
   479|
   480|@app.route("/api/camera-upload", methods=["POST"])
   481|@login_required
   482|def camera_upload():
   483|    pid = session["patient_id"]
   484|    
   485|    data = request.get_data()
   486|    if not data:
   487|        return jsonify({"error": "No image data"}), 400
   488|    
   489|    safe_name = f"camera_{uuid.uuid4().hex}.jpg"
   490|    filepath = os.path.join(UPLOAD_DIR, safe_name)
   491|    with open(filepath, "wb") as f:
   492|        f.write(data)
   493|    
   494|    file_size = os.path.getsize(filepath)
   495|    
   496|    conn = get_db()
   497|    conn.execute("""INSERT INTO documents 
   498|        (patient_id, document_type, filename, original_name, file_path, file_size, mime_type, description)
   499|        VALUES (?,?,?,?,?,?,?,?)""",
   500|        (pid, "scan", safe_name, f"Camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
   501|