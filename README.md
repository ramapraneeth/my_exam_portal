# My Exam Portal (AP EAPCET-style) — Supabase + Render Edition

A Django-based online mock test / exam platform, identical in features to
the original project, but wired to use **Supabase Postgres** as its
database and **Supabase Storage** for candidate photos — instead of the
local `db.sqlite3` file — so your data survives Render restarts, redeploys,
and inactivity sleep on the free tier.

## What changed from the original project

1. **Database**: SQLite → Supabase Postgres. Configured via a single
   `DATABASE_URL` environment variable (no code changes needed when you
   set this up — just env vars).
2. **Candidate photos**: local `media/` folder → Supabase Storage (S3-compatible
   bucket). Toggled with `USE_SUPABASE_STORAGE=True`.
3. **DEBUG**: now reads from an environment variable instead of being
   hardcoded, so you can turn on detailed error pages any time without
   touching code — just flip `DEBUG=True` in Render's dashboard and redeploy.
4. **`db.sqlite3` removed** from the project entirely (and ignored via
   `.gitignore`) — it's no longer the real datastore.
5. **No shell access needed**: every step below is done either in the
   Supabase web dashboard, the Render web dashboard, or your own local
   terminal before you push code — nothing requires Render's (paid-only)
   shell feature.

---

## 1. Requirements

- Python 3.10+
- A free [Supabase](https://supabase.com) account
- A free [Render](https://render.com) account
- pip

## 2. Local setup

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

pip install -r requirements.txt

# Copy the example env file and fill in your own values (see Section 3 below)
cp .env.example .env

python manage.py migrate
python manage.py createsuperuser

# Optional: load demo data (1 candidate + 2 sample tests)
python manage.py seed_demo_data

python manage.py runserver
```

Visit:
- **Candidate login:** http://127.0.0.1:8000/
- **Admin panel:** http://127.0.0.1:8000/admin/

If you don't create a `.env` file or don't set `DATABASE_URL`, the project
automatically falls back to a local SQLite file so commands like
`manage.py check` still work — but that fallback is for quick local checks
only. Supabase Postgres is the real database for this project.

---

## 3. Setting up Supabase (step by step)

### 3a. Create the project

1. Go to [supabase.com](https://supabase.com) → **New Project**.
2. Pick an organization, give it a name (e.g. `my-exam-portal`), set a
   **database password** (save this somewhere — you'll need it below),
   and choose a region close to your Render region.
3. Wait ~2 minutes while Supabase provisions the Postgres database.

### 3b. Get your database connection string (`DATABASE_URL`)

1. In your Supabase project, go to **Project Settings** (gear icon) →
   **Database**.
2. Scroll to **Connection string** → click the **URI** tab.
3. Use the **"Transaction" pooler connection** (port **6543**), not the
   direct connection (port 5432). The pooled connection handles many
   short-lived connections much better, which fits how Django opens a
   connection per request — important since Render's free tier and
   Supabase's free tier both limit concurrent direct connections.
4. Copy the string. It looks like:
   ```
   postgresql://postgres.xxxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-REGION.pooler.supabase.com:6543/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with the database password you set in step 3a.

   **Important:** if your password contains special characters (`@`, `:`,
   `/`, `#`, `?`, `[`, `]`, etc.), they must be **URL-encoded** or Django
   won't be able to parse the connection string at all (e.g. `@` becomes
   `%40`). Easiest fix: when creating the password in step 3a, stick to
   letters and numbers only, or use Supabase's "Generate a password" button
   and copy the URL it gives you directly.

6. This full string is your `DATABASE_URL`.

### 3c. Do you need to create any tables yourself?

**No.** Once `DATABASE_URL` is set and you run `python manage.py migrate`
(either locally pointed at Supabase, or automatically during Render's
deploy step — see Section 5), Django reads your `models.py` and creates
**every table automatically**: `Subject`, `Test`, `TestSection`, `Question`,
`Choice`, `CandidateProfile`, `TestAttempt`, `Answer`, plus Django's own
`auth_user` (for logins), sessions, and admin tables.

You can watch this happen by opening **Table Editor** in the Supabase
dashboard after running `migrate` — all the tables will appear there with
their correct columns. You only need to *add rows* (via `/admin/` as
before) — not create tables or columns by hand, unless you later add a
brand new model/field yourself, in which case the normal Django flow
applies: edit `models.py` → `python manage.py makemigrations` →
`python manage.py migrate`.

### 3d. Set up Supabase Storage for candidate photos

This is a separate feature from the database — Storage is Supabase's
file-bucket product (like an S3 bucket), used here so uploaded candidate
photos also persist across Render restarts.

1. In Supabase, go to **Storage** in the left sidebar → **New bucket**.
2. Name it `candidate-photos`, and toggle **Public bucket** to ON (so the
   exam page can display photos via a plain URL, same as before).
3. Go to **Project Settings** → **API**. You'll need:
   - **Project URL** (e.g. `https://xxxxxxxxxxxxx.supabase.co`)
4. Go to **Project Settings** → **Storage** (or **API** → scroll to S3
   connection details, naming varies slightly by Supabase version) and
   find the **S3 Connection** section. You need:
   - **Endpoint** — looks like `https://xxxxxxxxxxxxx.supabase.co/storage/v1/s3`
   - **Region** — e.g. `ap-south-1`
5. Go to **Storage** → **Settings** (or **Project Settings** → **Storage**)
   → **S3 Access Keys** → **New access key**. This gives you:
   - **Access Key ID**
   - **Secret Access Key** (shown once — copy it immediately)

You'll plug all of these into environment variables in Section 4.

---

## 4. Environment variables reference

These go in your local `.env` file (copy `.env.example` → `.env`) for local
development, and as **Environment Variables in Render's dashboard** (not a
`.env` file — Render doesn't read `.env` files) for production.

| Variable | Example | Notes |
|---|---|---|
| `DEBUG` | `True` or `False` | `True` while setting up so you see real error pages. Set to `False` once it's working and real candidates will use it. |
| `DJANGO_SECRET_KEY` | (random string) | Generate one at [djecrety.ir](https://djecrety.ir/). Never reuse the placeholder. |
| `ALLOWED_HOSTS` | `my-exam-portal.onrender.com` | Comma-separated, no spaces. `*` works but isn't recommended for a real domain. |
| `DATABASE_URL` | `postgresql://postgres.xxx:[email protected]:6543/postgres` | From Section 3b. |
| `USE_SUPABASE_STORAGE` | `True` or `False` | `False` keeps photos on local disk (fine for quick local testing only). `True` uses Supabase Storage — required for Render since its disk is wiped on restart. |
| `SUPABASE_S3_ACCESS_KEY_ID` | (from 3d) | Only needed if `USE_SUPABASE_STORAGE=True`. |
| `SUPABASE_S3_SECRET_ACCESS_KEY` | (from 3d) | Only needed if `USE_SUPABASE_STORAGE=True`. |
| `SUPABASE_S3_BUCKET_NAME` | `candidate-photos` | Must match the bucket name from Section 3d. |
| `SUPABASE_S3_ENDPOINT_URL` | `https://xxxxxxxxxxxxx.supabase.co/storage/v1/s3` | From Section 3d. |
| `SUPABASE_S3_REGION` | `ap-south-1` | From Section 3d. |

---

## 5. Deploying to Render (free tier, no shell needed)

1. Push this project to a GitHub repository.
2. In Render, click **New** → **Web Service** → connect your repo.
3. Render should auto-detect Python. Set:
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn exam_portal.wsgi`
4. Under **Environment**, add every variable from the table in Section 4
   as a Render **Environment Variable** (one at a time, via the dashboard
   — no shell required).
5. Render will run `build.sh` on every deploy, which installs
   requirements, collects static files, and **runs `migrate` for you
   automatically** — so your Supabase tables get created/updated on every
   deploy without you ever needing a shell.
6. Click **Create Web Service**. After the first successful deploy, your
   data (users, tests, attempts, photos) lives in Supabase — restarting,
   redeploying, or the free tier "spinning down" after inactivity will
   **not** erase it, since none of it lives on Render's own disk anymore.
7. (Optional, one-time) Create your admin login: since there's no shell on
   the free tier, the easiest way is to run
   `python manage.py createsuperuser` **locally** with your `.env` pointed
   at the same `DATABASE_URL` as Render — it creates the user directly in
   the shared Supabase database, so it's immediately usable on the live
   Render site too.

---

## 6. Verifying everything actually persists

After deploying:
1. Log into `/admin/`, add a `Subject`, a `Test`, a `Question`, and a
   `CandidateProfile` with a photo.
2. In the Supabase dashboard → **Table Editor**, confirm the rows appear
   in `exams_subject`, `exams_test`, etc.
3. In Supabase → **Storage** → your bucket, confirm the uploaded photo
   file appears there.
4. On Render, manually restart the service (or just wait for free-tier
   inactivity sleep + a new request to wake it). Reload `/admin/` —
   everything you added in step 1 should still be there, and the photo
   should still display.

---

## 7. Production checklist

- [ ] `DEBUG=False` once everything works (don't leave it `True` for real candidates)
- [ ] A real, unique `DJANGO_SECRET_KEY`
- [ ] `ALLOWED_HOSTS` set to your actual Render domain, not `*`
- [ ] `USE_SUPABASE_STORAGE=True` so photos survive restarts
- [ ] Confirm Supabase's free-tier limits work for your candidate volume
      (connection count, storage size, bandwidth) before a real exam date

## Project structure

```
my_exam_portal/
├── manage.py
├── requirements.txt
├── build.sh                 # Render build step: installs deps, collects
│                              static files, runs migrate against Supabase
├── Procfile                  # alternative start command reference
├── .env.example               # template - copy to .env locally, never commit .env
├── exam_portal/
│   ├── settings.py            # Supabase Postgres + Supabase Storage wiring
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── exams/                     # the main app (unchanged data model/logic)
│   ├── models.py
│   ├── admin.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── templates/exams/
│   └── management/commands/
│       ├── seed_demo_data.py
│       └── fix_database_issues.py
├── static/
│   ├── css/style.css
│   └── js/exam.js
└── media/candidate_photos/    # only used when USE_SUPABASE_STORAGE=False
```
