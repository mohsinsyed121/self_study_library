# Self-Study Library Management System

A Django website for a **single-floor, self-study library** (students come to study; there is no book lending).
Public website, student panel and a separate admin panel.

* Backend: Python, Django 5.1 (custom user, Django auth)
* Frontend: HTML, Bootstrap 5, a little JavaScript (no frontend framework)
* Database: SQLite locally, PostgreSQL on Render (same code, chosen with `DATABASE_URL`)
* QR codes: `qrcode` + Pillow

> **Payments are manual.** No payment gateway is connected. Students *report* a payment (cash/UPI/bank) and an
> admin *verifies* it. Only confirmed payments count towards "paid". The website never marks money as received by itself.

---------------------------------------------------------------------

## 1. Run it on Windows (PowerShell + VS Code)

1. Install Python 3.12 from python.org (tick **Add Python to PATH**) and VS Code with the *Python* extension.
2. Open the project folder in VS Code (`File > Open Folder`), then open a terminal (`Ctrl + ~`, choose PowerShell).

```powershell
# create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
# (if PowerShell blocks scripts, run once:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)

# install packages
pip install -r requirements.txt

# create your settings file
Copy-Item .env.example .env
# generate a secret key and paste it after DJANGO_SECRET_KEY= in the .env file:
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"

# create the database tables
python manage.py migrate

# create YOUR admin login (superusers are library admins)
python manage.py createsuperuser

# optional: starter settings, 3 plans and 30 seats
python manage.py seed_demo

# start the website
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Log in with the superuser and you land in the **admin panel** (`/manage/`).
Students register at `/accounts/register/`. Select the venv interpreter in VS Code with `Ctrl+Shift+P > Python: Select Interpreter`.

Run the tests (all must pass): `python manage.py test`

Daily housekeeping (expires finished memberships and releases their seats; it also runs whenever an admin opens the
dashboard or the memberships page): `python manage.py expire_memberships`

---------------------------------------------------------------------

## 2. Typical workflow

1. Student registers -> account is **Pending**. Admin approves it (Admin > Students).
2. Student requests a plan (Membership > Renew) *or* admin activates one directly (Admin > Memberships).
   Activating sets start/end dates and creates a **fee record**.
3. Student pays at the desk and reports it (Fees & payments > Report payment) *or* admin records it
   (Admin > Payments > Record payment, which can confirm immediately).
4. Admin **verifies** pending payments. A receipt number is issued and the student is notified.
5. Student (approved + active membership) books a seat -> **Reserved**. Admin confirms -> **Occupied**.
   Admin can also allocate, move or cancel seats.
6. Student prints the QR ID card; admin scans it (opens `/id-card/verify/<token>/`, admin login required).

### Business rules (all enforced on the server)
* A seat has at most one active booking, and a student has at most one active booking.
  Checked in `seats/services.py` **and** by two database constraints (`SeatBooking.Meta.constraints`).
* Seat status is *calculated* from bookings: Available / Reserved / Occupied / Inactive. It cannot get out of date.
* Booking needs: approved account + active membership + free seat. A seat in use cannot be deactivated.
* `Remaining Due = Total Fee - Confirmed Payments`. Pending and rejected payments never count.
* Payments must be > 0, and may not exceed what is still owed (re-checked at verification time). Money = `DecimalField`.
* Renewing creates a **new** membership row that starts the day after the current one ends. History and the price at
  the time are kept. Memberships, payments, fees and bookings use `PROTECT`, so they cannot be deleted by accident.
* Expired membership -> seat released automatically.

---------------------------------------------------------------------

## 3. How the apps and models connect

```
accounts.User (custom user, is_staff = library admin)
   |-- 1:1 --> students.StudentProfile  (student_id, qr_token, approval_status)
   |               |-- 1:N --> seats.SeatBooking  --N:1--> seats.Seat
   |               |-- 1:N --> memberships.Membership --N:1--> memberships.MembershipPlan
   |               |                 `-- 1:1 --> payments.FeeRecord
   |               |-- 1:N --> payments.FeeRecord --1:N--> payments.Payment
   |               `-- 1:N --> complaints.Complaint
   `-- 1:N --> notifications.Notification
website.SiteSettings (one row)      website.ContactEnquiry
```

| App | Purpose |
|---|---|
| `config` | settings, main `urls.py` (also holds `test_helpers.py` used by tests) |
| `accounts` | custom User, register/login/logout, **permission decorators** (`student_required`, `approved_student_required`, `admin_required`) |
| `students` | profile + dashboard; admin: search/approve/deactivate students |
| `seats` | seats, bookings, **`services.py` = all booking rules**; seat map; admin seat tools |
| `memberships` | plans, memberships, **`services.py`** (request/activate/renew/expire) |
| `payments` | fees, payments, **`services.py`** (record/verify/summary), receipts |
| `id_cards` | QR ID card (generated on the fly, no extra table) and admin verification |
| `complaints` | student complaints, admin responses |
| `notifications` | `notify(user, title, message)` helper + student inbox |
| `reports` | admin dashboard numbers and date-range reports (`services.py`) |
| `website` | public pages, contact form, **SiteSettings**, context processor `site` |

Pattern used everywhere: **views are short**, rules live in `services.py`, forms validate input, templates only display.
Student pages are in `<app>/urls.py`; admin pages are in `<app>/admin_urls.py` and `<app>/admin_views.py` (mounted under `/manage/`).

### Templates and CSS
`templates/base.html` is the common shell. Sidebar pages extend `layouts/student_base.html` or `layouts/admin_base.html`
(both build on `layouts/app_base.html`). Reusable pieces are in `templates/partials/` (navbar, footer, messages,
pagination, form fields, sidebars). Each page is its own file. CSS: `static/css/main.css`, `student.css`, `admin.css`,
`forms.css`. JS: `static/js/main.js` (confirm prompts, print), `seats.js` (seat filter).
Template helpers: `{{ form.field|bs }}`, `{% status_badge value label %}`, `{{ amount|money }}` (`website/templatetags/ui.py`).
Public Facilities/Gallery content is plain HTML you can edit in `templates/website/`.

---------------------------------------------------------------------

## 4. Security notes
* Logout uses Django's `logout()` on **POST** and clears the session.
* Every private view uses a decorator that applies `login_required` **and** `never_cache`
  (so the Back button cannot show an old private page after logout), then checks the role on the server.
* Students only query their own data (`student=request.student`); another student's ID in the URL gives **404**. Tested in `students/tests/test_privacy.py`.
* QR code = a link with a random UUID token only. The verification page is admin-only.
* CSRF on all forms, state-changing actions are POST-only, custom 403/404/500 pages.
* Secrets come from environment variables. With `DEBUG=False` the app refuses to start without `DJANGO_SECRET_KEY`,
  and turns on HTTPS redirect, secure cookies and HSTS.

---------------------------------------------------------------------

## 5. Deploy to Render (PostgreSQL)

1. Push the project to GitHub (`.env` and `db.sqlite3` are git-ignored, so no secrets are uploaded).
2. In Render choose **New > Blueprint**, select your repo. `render.yaml` creates a PostgreSQL database and a web service,
   generates `DJANGO_SECRET_KEY`, and connects `DATABASE_URL` automatically. `build.sh` installs packages, collects static files and migrates.
   (Manual alternative: New Web Service, build command `./build.sh`, start command `gunicorn config.wsgi:application`.)
3. Environment variables (Render > Environment):

| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | long random string (generated by the blueprint) |
| `DJANGO_DEBUG` | `False` |
| `DATABASE_URL` | from the Render PostgreSQL database |
| `DJANGO_ALLOWED_HOSTS` | your domain, e.g. `library.onrender.com` (the Render hostname is added automatically) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://library.onrender.com` |

4. Create your admin: Render > service > **Shell**: `python manage.py createsuperuser`, then `python manage.py seed_demo` (optional).
5. Run `python manage.py expire_memberships` daily with a Render **Cron Job** (optional, since admin pages also run it).

**Important:** Render's free disk is temporary. Uploaded files (logo, student photos) disappear on redeploy.
For real use attach a Render Disk mounted at the `media/` folder, or move media to S3/Cloudinary (e.g. `django-storages`).
Also serve media in production by that storage; Django only serves `media/` itself while `DEBUG=True`.

---------------------------------------------------------------------

## 6. Not included (by design)
Attendance, staff management, notices module, multi-floor features, online payment gateway, refunds/credits.
Ideas for later: email/SMS reminders before expiry, real gallery uploads, refunds as a documented credit process.
