# Django Login System

This Django replacement sits beside the unchanged PHP source in `Login-WS1/`. It uses Django authentication and password hashing, SQLite by default, PostgreSQL through environment settings, and the required `myproject.wsgi:application` WSGI path.

## Conversion mapping

| PHP functionality | Django equivalent |
|---|---|
| `register.php` | `/accounts/register/`, validated Django registration form; new accounts receive the `user` role |
| `login.php`, `auth.php`, `logout.php` | Django authentication views, session middleware, login-required access, CSRF-protected POST logout |
| `dashboard.php` | `/dashboard/`, showing the current account profile |
| `accounts.php`, `set_role.php` | `/accounts/manage/` and POST role updates; admin/superadmin may manage roles, but only superadmin may grant `superadmin` |
| `teachers.php`, `edit_teacher.php` | `/teachers/` and `/teachers/<id>/edit/`; teachers are user accounts whose role is `teacher`, as implied by the PHP queries |
| `update_password.php` and teacher edit password | Superadmin account password reset plus authenticated user's own password-change form; Django hashes all passwords |
| `seed_superadmin.php` | Deliberately not recreated with its hard-coded credentials. `createsuperuser` creates a Django superuser with the `superadmin` application role |
| `database.sql` | Django initial migration for the single users/accounts table and its fields/role choices |
| PHP CSS and images | Reused in `static/css/` and `static/images/` |

Login uses Google's reCAPTCHA v2 checkbox, verified server-side. In the Google reCAPTCHA admin console, register a reCAPTCHA v2 "I'm not a robot" checkbox site for the hostnames that serve the app (for local testing, add `localhost` and `127.0.0.1`). Set its site key and secret key as `RECAPTCHA_SITE_KEY` and `RECAPTCHA_SECRET_KEY` in the private `.env`; do not commit or share the secret key. The widget key is public; keep the secret key confidential. The app deliberately rejects login attempts if keys are unset, the CAPTCHA is unanswered/invalid, or Google's verification endpoint is unavailable. Restart Gunicorn after changing `.env`:

```bash
sudo systemctl restart gunicorn.service
```

The supplied SQL defines only `users(id, username, email, password_hash, phone, address, created_at)`; the PHP pages additionally rely on `role` and `password_plain`, which the SQL does not define. There are no record inserts or separate teacher table in that SQL. Existing database records are not altered or automatically imported. The PHP configuration contains live-looking database credentials; they were intentionally not copied or used. Do not keep those credentials active—rotate them at the former database provider. Legacy hashes may be imported only through a deliberate, verified migration; otherwise reset passwords in Django rather than storing or displaying plaintext.

## Install and run (Ubuntu)

From `/var/www/myproject`:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
python3 -m venv /var/www/myproject/venv
/var/www/myproject/venv/bin/pip install --upgrade pip
/var/www/myproject/venv/bin/pip install -r /var/www/myproject/requirements.txt
```

Set `SECRET_KEY` in the untracked `.env`. Generate a fresh value without printing it into source files:

```bash
cd /var/www/myproject
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Paste that generated value into `.env`; keep `.env` private. Set `ALLOWED_HOSTS` to the server IP and/or domain. SQLite requires no separate database setup. Then:

```bash
cd /var/www/myproject
/var/www/myproject/venv/bin/python manage.py migrate
/var/www/myproject/venv/bin/python manage.py createsuperuser
/var/www/myproject/venv/bin/python manage.py collectstatic --noinput
/var/www/myproject/venv/bin/python manage.py runserver 0.0.0.0:8000
```

Visit `http://SERVER_IP:8000/`. Stop the development server with Ctrl+C; use Gunicorn behind Nginx for deployment.

### PostgreSQL

Install and configure PostgreSQL separately, create a database and restricted application user, then set the following in `.env` (do not put actual values in source control):

```dotenv
DB_ENGINE=postgresql
DB_NAME=your_database
DB_USER=your_application_user
DB_PASSWORD=your_database_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

Run the same `manage.py migrate` command after the database is available. `psycopg2-binary` is included for PostgreSQL.

## Checks

```bash
cd /var/www/myproject
/var/www/myproject/venv/bin/python -m compileall -q manage.py myproject accounts
/var/www/myproject/venv/bin/python manage.py check
/var/www/myproject/venv/bin/python manage.py makemigrations --check --dry-run
/var/www/myproject/venv/bin/python manage.py test accounts
/var/www/myproject/venv/bin/python manage.py migrate
/var/www/myproject/venv/bin/python manage.py collectstatic --noinput
/var/www/myproject/venv/bin/gunicorn --check-config myproject.wsgi:application
```

## Gunicorn, Nginx, and the teacher's 13 steps

The WSGI module is exactly `myproject.wsgi:application`. Start a foreground smoke-test using the teacher's command:

```bash
/var/www/myproject/venv/bin/gunicorn --bind 0.0.0.0:8000 myproject.wsgi:application
```

For the teacher's systemd socket setup, the service should run `/var/www/myproject/venv/bin/gunicorn` with working directory `/var/www/myproject` and `myproject.wsgi:application`; omit `--bind` so Gunicorn uses the socket descriptor passed by systemd. The socket unit creates `/run/gunicorn.sock`. The Nginx site should proxy to `unix:/run/gunicorn.sock` and serve:

```nginx
location /static/ { alias /var/www/myproject/staticfiles/; }
location /media/  { alias /var/www/myproject/media/; }
location / { include proxy_params; proxy_pass http://unix:/run/gunicorn.sock; }
```

After editing Nginx or systemd configuration, validate/reload those services using the commands in the teacher's guide; this project setup does not modify system services or firewall rules. Ensure the service user can read the application and `.env`, write to `media/` if uploads are later added, and access the socket; use the guide's `www-data` group/permissions without making secrets world-readable. `collectstatic` populates `/var/www/myproject/staticfiles/`; uploaded files belong in `/var/www/myproject/media/`. Configure `ALLOWED_HOSTS` for the IP/domain and `CSRF_TRUSTED_ORIGINS` with full `https://` origins when applicable. When HTTPS is enabled, set `SECURE_SSL_REDIRECT=True` and `SECURE_COOKIES=True`. `/admin/` is Django admin and requires an `is_staff` account created via `createsuperuser`.

For a service running as the deployment account with group `www-data`, grant only the needed group access (adjust the ownership command if your systemd `User=` differs):

```bash
sudo chgrp www-data /var/www/myproject/.env
sudo chmod 640 /var/www/myproject/.env
sudo chgrp -R www-data /var/www/myproject/staticfiles /var/www/myproject/media
sudo chmod -R g+rX /var/www/myproject/staticfiles
sudo chmod -R g+rwX /var/www/myproject/media
sudo chmod 600 /var/www/myproject/db.sqlite3
```

The Gunicorn service account must own or be able to read/write the SQLite database if SQLite is used; PostgreSQL is preferable for a multiworker production deployment. Do not recursively change ownership on `/var/www/myproject/`, since it also contains the original `Login-WS1/` tree.

Ready-to-install example unit and Nginx files are in `deploy/`. They run Gunicorn as the existing `angel` account, use systemd socket activation at `/run/gunicorn.sock`, and make the app the default HTTP site on port 80. Review and adapt `User=`, `SocketUser=`, `server_name`, and `ALLOWED_HOSTS` for your server before installation. The setup commands are:

```bash
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.before-myproject
sudo cp /var/www/myproject/deploy/nginx-myproject.conf /etc/nginx/sites-available/default
sudo cp /var/www/myproject/deploy/gunicorn.socket /etc/systemd/system/gunicorn.socket
sudo cp /var/www/myproject/deploy/gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo nginx -t
sudo systemctl enable --now gunicorn.socket
sudo systemctl restart nginx
```

The socket-activated service reads the passed listener from systemd's `LISTEN_FDS` environment; do not set a separate `--bind` address while the `.socket` unit owns that socket.

The code supports the requested configuration, but this environment did not run `sudo`, install OS services, create PostgreSQL roles, configure UFW/Nginx/systemd, or expose a public server. Those are deployment-host actions and should follow the teacher's guide.
