#!/usr/bin/env python3
"""Dr. AI — database schema and initialization. v2 with credits, appointments, ads."""
import sqlite3, os

DB_PATH = "/data/drai/drai.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    preferred_name TEXT,
    date_of_birth TEXT NOT NULL,
    age INTEGER,
    sex TEXT,
    gender TEXT,
    height REAL,
    weight REAL,
    bmi REAL,
    ethnicity TEXT,
    blood_type TEXT,
    nationality TEXT,
    primary_language TEXT,
    emergency_contact TEXT,
    occupation TEXT,
    smoking_status TEXT,
    alcohol_use TEXT,
    drug_use TEXT,
    activity_level TEXT,
    phone TEXT,
    phone_verified INTEGER DEFAULT 0,
    email TEXT,
    email_verified INTEGER DEFAULT 0,
    address TEXT,
    gp_name TEXT,
    gp_address TEXT,
    gp_phone TEXT,
    gp_email TEXT,
    official_id_type TEXT,
    official_id_number TEXT,
    onboarding_completed INTEGER DEFAULT 0,
    stripe_customer_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    consultation_date TEXT DEFAULT (datetime('now')),
    main_complaint TEXT,
    consultation_summary TEXT,
    differential_diagnosis TEXT,
    most_likely_condition TEXT,
    dangerous_conditions TEXT,
    confidence_level TEXT,
    supporting_evidence TEXT,
    contradicting_evidence TEXT,
    recommended_tests TEXT,
    treatment_plan TEXT,
    referrals TEXT,
    follow_up_required TEXT,
    follow_up_date TEXT,
    emergency_flag INTEGER DEFAULT 0,
    doctor_reasoning TEXT,
    patient_questions TEXT,
    recommended_actions TEXT,
    duration_minutes INTEGER DEFAULT 15,
    credits_cost INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- v2: Credits & Billing
CREATE TABLE IF NOT EXISTS credit_balance (
    patient_id TEXT PRIMARY KEY REFERENCES patients(patient_id),
    balance INTEGER NOT NULL DEFAULT 0,
    lifetime_earned INTEGER NOT NULL DEFAULT 0,
    lifetime_spent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS credit_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price_pence INTEGER NOT NULL,
    credits INTEGER NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS credit_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    transaction_type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    reference TEXT,
    stripe_session_id TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- v2: Appointments
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    status TEXT NOT NULL DEFAULT 'pending',
    credits_cost INTEGER NOT NULL DEFAULT 1,
    duration_minutes INTEGER NOT NULL DEFAULT 15,
    main_complaint TEXT,
    booked_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT,
    cancelled_at TEXT,
    timer_remaining_seconds INTEGER,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- v2: Advertising
CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    image_url TEXT,
    link_url TEXT,
    alt_text TEXT,
    display_duration_seconds INTEGER DEFAULT 10,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ad_tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    position TEXT NOT NULL DEFAULT 'top',
    scroll_speed_seconds INTEGER DEFAULT 15,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ad_impression_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id INTEGER REFERENCES ads(id),
    patient_id TEXT REFERENCES patients(patient_id),
    action TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- v2: App Settings
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO app_settings (key, value, description) VALUES
    ('credit_cost_per_15min', '1', 'Credits cost for a 15-minute consultation'),
    ('default_duration_minutes', '15', 'Default appointment duration'),
    ('ads_scroll_speed_seconds', '12', 'Ad rotation speed in seconds'),
    ('ads_per_minute', '4', 'Number of ads shown per minute'),
    ('onboarding_target_percent', '80', 'Target completion percentage for onboarding'),
    ('stripe_secret_key', '', 'Stripe secret key'),
    ('stripe_publishable_key', '', 'Stripe publishable key'),
    ('stripe_webhook_secret', '', 'Stripe webhook signing secret'),
    ('stripe_currency', 'gbp', 'Currency for Stripe payments');
"""

# (rest of existing tables kept in the full migration)
# The init_db function will create tables in order
EXISTING_SCHEMA = """
CREATE TABLE IF NOT EXISTS medical_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    condition_name TEXT, diagnosis_date TEXT, status TEXT DEFAULT 'active',
    notes TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS surgeries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    surgery_name TEXT, date TEXT, hospital TEXT, surgeon TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS allergies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    allergen TEXT, reaction TEXT, severity TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS family_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    relation TEXT, condition_name TEXT, age_of_onset INTEGER, notes TEXT
);
CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    medication_name TEXT, dosage TEXT, frequency TEXT, route TEXT,
    start_date TEXT, end_date TEXT, prescribed_by TEXT, reason TEXT,
    side_effects TEXT, adherence_level TEXT, status TEXT DEFAULT 'current', notes TEXT
);
CREATE TABLE IF NOT EXISTS symptoms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    symptom_name TEXT NOT NULL, date_started TEXT, severity TEXT,
    duration TEXT, frequency TEXT, progression TEXT, triggers TEXT,
    relieving_factors TEXT, associated_symptoms TEXT, body_location TEXT,
    pain_scale INTEGER, symptom_pattern TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    recorded_at TEXT DEFAULT (datetime('now')),
    blood_pressure_systolic INTEGER, blood_pressure_diastolic INTEGER,
    pulse INTEGER, oxygen_saturation REAL, respiratory_rate INTEGER,
    temperature REAL, blood_glucose REAL, weight REAL, sleep_quality TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS lab_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    test_name TEXT NOT NULL, test_date TEXT, result TEXT,
    reference_range TEXT, unit TEXT, abnormal_flag INTEGER DEFAULT 0,
    interpretation TEXT, trend TEXT, lab_name TEXT, file_path TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS imaging (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    imaging_type TEXT, body_area TEXT, date TEXT, findings TEXT,
    abnormalities TEXT, radiologist_notes TEXT, comparison_to_previous TEXT,
    file_path TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS risk_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    assessed_at TEXT DEFAULT (datetime('now')),
    cardiovascular_risk TEXT, diabetic_risk TEXT, cancer_risk TEXT,
    neurological_risk TEXT, infection_risk TEXT, autoimmune_risk TEXT,
    emergency_risk TEXT, overall_risk TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS verification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT, contact TEXT NOT NULL, contact_type TEXT NOT NULL,
    code TEXT NOT NULL, expires_at TEXT NOT NULL, verified INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS auth_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT UNIQUE REFERENCES patients(patient_id),
    password_hash TEXT, webauthn_credential_id TEXT, webauthn_public_key TEXT,
    created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id),
    document_type TEXT, filename TEXT, original_name TEXT, file_path TEXT,
    file_size INTEGER, mime_type TEXT, description TEXT,
    uploaded_at TEXT DEFAULT (datetime('now'))
);
"""

FULL_SCHEMA = SCHEMA + EXISTING_SCHEMA

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(FULL_SCHEMA)
    conn.commit()
    conn.close()
    print(f"Dr. AI database initialized at {DB_PATH}")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value, description=None):
    conn = get_db()
    conn.execute("""INSERT INTO app_settings (key, value, description, updated_at) 
        VALUES (?,?,?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
        (key, value, description))
    conn.commit()
    conn.close()

def ensure_credit_balance(patient_id):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO credit_balance (patient_id, balance) VALUES (?, 0)", (patient_id,))
    conn.commit()
    conn.close()

def get_credit_balance(patient_id):
    ensure_credit_balance(patient_id)
    conn = get_db()
    row = conn.execute("SELECT balance FROM credit_balance WHERE patient_id=?", (patient_id,)).fetchone()
    conn.close()
    return row["balance"] if row else 0

def add_credits(patient_id, amount, reference=None, stripe_session_id=None):
    ensure_credit_balance(patient_id)
    conn = get_db()
    conn.execute("UPDATE credit_balance SET balance=balance+?, lifetime_earned=lifetime_earned+?, updated_at=datetime('now') WHERE patient_id=?",
        (amount, amount, patient_id))
    bal = conn.execute("SELECT balance FROM credit_balance WHERE patient_id=?", (patient_id,)).fetchone()[0]
    conn.execute("""INSERT INTO credit_transactions 
        (patient_id, transaction_type, amount, balance_after, reference, stripe_session_id, notes)
        VALUES (?, 'topup', ?, ?, ?, ?, 'Credit top-up')""",
        (patient_id, amount, bal, reference or '', stripe_session_id or ''))
    conn.commit()
    conn.close()
    return bal

def spend_credits(patient_id, amount, reference=None):
    ensure_credit_balance(patient_id)
    conn = get_db()
    bal = conn.execute("SELECT balance FROM credit_balance WHERE patient_id=?", (patient_id,)).fetchone()
    if not bal or bal["balance"] < amount:
        conn.close()
        return False
    conn.execute("UPDATE credit_balance SET balance=balance-?, lifetime_spent=lifetime_spent+?, updated_at=datetime('now') WHERE patient_id=?",
        (amount, amount, patient_id))
    new_bal = conn.execute("SELECT balance FROM credit_balance WHERE patient_id=?", (patient_id,)).fetchone()[0]
    conn.execute("""INSERT INTO credit_transactions 
        (patient_id, transaction_type, amount, balance_after, reference, notes)
        VALUES (?, 'spend', ?, ?, ?, 'Consultation')""",
        (patient_id, -amount, new_bal, reference or ''))
    conn.commit()
    conn.close()
    return True

def calculate_onboarding_progress(patient_id):
    conn = get_db()
    patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
    if not patient:
        conn.close()
        return {"percent": 0, "filled": 0, "total": 0}
    fields = {
        "first_name": 5, "last_name": 5, "date_of_birth": 5, "phone": 5, "email": 5,
        "address": 5, "height": 5, "weight": 5, "blood_type": 5, "ethnicity": 5,
        "smoking_status": 5, "alcohol_use": 5, "activity_level": 5, "emergency_contact": 5,
        "gp_name": 5, "gp_address": 5, "occupation": 5,
    }
    med_count = conn.execute("SELECT COUNT(*) FROM medical_history WHERE patient_id=?", (patient_id,)).fetchone()[0]
    allergy_count = conn.execute("SELECT COUNT(*) FROM allergies WHERE patient_id=?", (patient_id,)).fetchone()[0]
    meds_count = conn.execute("SELECT COUNT(*) FROM medications WHERE patient_id=?", (patient_id,)).fetchone()[0]
    doc_count = conn.execute("SELECT COUNT(*) FROM documents WHERE patient_id=?", (patient_id,)).fetchone()[0]
    total_weight = sum(fields.values()) + 20
    filled_weight = 0
    field_status = {}
    for field, weight in fields.items():
        val = patient[field] if field in patient.keys() else None
        is_filled = bool(val and str(val).strip())
        field_status[field] = {"filled": is_filled, "weight": weight}
        if is_filled:
            filled_weight += weight
    if med_count > 0: filled_weight += 8
    if allergy_count > 0: filled_weight += 4
    if meds_count > 0: filled_weight += 4
    if doc_count > 0: filled_weight += 4
    percent = min(100, round(filled_weight / total_weight * 100))
    conn.close()
    return {"percent": percent, "filled": filled_weight, "total": total_weight,
        "fields": field_status, "conditions": med_count, "allergies": allergy_count,
        "medications": meds_count, "documents": doc_count}

if __name__ == "__main__":
    init_db()
