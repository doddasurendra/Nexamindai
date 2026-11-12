# Google Sign-In Setup — NexaMind AI

NexaMind AI supports **Continue with Google** on the login/register page.
It uses Google Identity Services on the frontend and verifies the ID token on the backend.

## Why it shows "not configured"

Google sign-in requires an OAuth Client ID, which only you can create in your own
Google Cloud project. NexaMind never ships credentials, so they must be added locally.

## What you need

A Google OAuth 2.0 **Web application** Client ID. Create one at:
https://console.cloud.google.com/apis/credentials

### Step-by-step (2 minutes)

1. Open Google Cloud Console → **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Web application**
4. Add **Authorized JavaScript origins**:
   - `http://localhost:5173`
   - `http://127.0.0.1:8000`
5. Copy the generated **Client ID** (ends with `.apps.googleusercontent.com`)

## Where to paste it

### 1. Frontend — `nexamind/frontend/.env`
```
VITE_GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
```

### 2. Backend — `nexamind/backend/.env`
```
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
```

## Apply the changes

```powershell
# backend (restart to load the env)
cd nexamind\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# frontend (rebuild so Vite bakes in the env)
cd nexamind\frontend
npm run build
```

## How it works

1. User clicks **Continue with Google**
2. Frontend loads Google Identity Services and shows the Google account picker
3. Google returns a signed ID token (`credential`)
4. Frontend POSTs it to `POST /api/auth/google`
5. Backend verifies the token with `google-auth` (issuer, audience, expiry),
   then creates or fetches the user by email and returns a NexaMind JWT
6. Google-created users get a random, unusable password hash — they can only
   sign in via Google or a password reset

The first Google account to sign in becomes the workspace **admin** (same rule as email registration).

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Google sign-in is not configured" | Set `VITE_GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_ID` in both `.env` files, then rebuild/restart |
| "Google Identity Services failed to load" | Check internet/firewall; the GIS script comes from `accounts.google.com` |
| "Invalid Google credential" | Client ID mismatch between frontend and backend — must be the same ID |
| Origin error in Google Console | Add both `http://localhost:5173` and `http://127.0.0.1:8000` to Authorized JavaScript origins |
