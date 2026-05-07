# Dr. AI — Private Healthcare System

**Closed system.** AI doctor consultations, patient records, credit-based billing, advertising.

## Architecture

- **Backend:** Flask + SQLite + Stripe — runs in Docker on VPS
- **Android App:** React Native (Expo) — connects to backend API
- **Payments:** Stripe Checkout (GBP)

## Backend API

Base URL: `http://100.82.200.47:5003`

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/login | JSON login (email, password) |
| POST | /register | Form registration |
| GET | /api/logout | Logout |

### Patient
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/patient/profile | Get full profile + credit balance |
| PUT | /api/patient/profile | Update profile fields |

### Health Records
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/patient/conditions | Medical conditions list |
| POST | /api/patient/conditions | Add condition |
| GET | /api/patient/allergies | Allergies list |
| POST | /api/patient/allergies | Add allergy |
| GET | /api/patient/medications | Medications list |
| POST | /api/patient/medications | Add medication |
| GET | /api/patient/vitals | Vitals history |
| POST | /api/patient/vitals | Add vitals reading |
| GET | /api/documents | Uploaded documents |

### Credits
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/credits/balance | Current balance |
| GET | /api/credits/packages | Available packages |
| POST | /api/credits/create-checkout | Create Stripe checkout (package_id) |
| GET | /api/credits/history | Transaction history |

### Appointments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/appointments | List appointments |
| POST | /api/appointments/book | Book (main_complaint, duration_minutes) |
| POST | /api/appointments/start/{id} | Start appointment |
| POST | /api/appointments/complete/{id} | Complete |
| POST | /api/appointments/cancel/{id} | Cancel (refunds if pending) |

### Ads
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/ads/next | Next ad in rotation |
| GET | /api/ads/tickers | Top + bottom ticker text |
| POST | /api/ads/click/{id} | Log ad click |

### Onboarding
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/patient/onboarding-progress | Completion % breakdown |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | /api/admin/credit-packages | Manage packages |
| GET | /api/admin/appointments | All appointments |
| GET/POST | /api/admin/ads | Manage ads |
| GET/POST | /api/admin/tickers | Manage tickers |
| GET/PUT | /api/admin/settings | App settings |

## Android App

11 screens, dark theme, built with Expo.

### Screens
1. Splash → Login / Register
2. Dashboard (credits, onboarding %, quick actions, ads)
3. Top Up (credit packages)
4. Medical Records (camera + file upload)
5. Appointments (list + book)
6. Consultation (countdown timer, chat, dual ads)
7. My Health (progressive onboarding form)
8. Settings (profile edit, logout)

### Build
```bash
cd android
npm install
npx expo start
```

## Deployment

Backend runs in Docker:
```bash
docker run -d --name drai --restart unless-stopped \
  --network proxy -p 5003:5003 \
  -v /data/drai:/data/drai \
  -e DRAI_SECRET=... \
  -e DRAI_ADMIN_PASSWORD=DrAI2025! \
  -e TWILIO_ACCOUNT_SID=... \
  -e TWILIO_AUTH_TOKEN=... \
  -e TWILIO_VERIFY_SID=... \
  -e STRIPE_SECRET_KEY=... \
  containers-drai \
  gunicorn --bind 0.0.0.0:5003 --workers 2 app:app
```

## Credits System

| Package | Price | Credits |
|---------|-------|---------|
| Starter | 5 GBP | 5 |
| Popular | 10 GBP | 12 |
| Boost | 20 GBP | 25 |
| Pro | 50 GBP | 65 |

1 credit = 15 min consultation. Set in admin panel.

## Environment Variables

- DRAI_SECRET - Flask session key
- DRAI_ADMIN_PASSWORD - Admin panel password
- TWILIO_ACCOUNT_SID - Twilio for SMS verification
- TWILIO_AUTH_TOKEN - Twilio auth
- TWILIO_VERIFY_SID - Twilio Verify service
- STRIPE_SECRET_KEY - Stripe live/secret key
- STRIPE_WEBHOOK_SECRET - Stripe webhook signing secret

