# Installing ophix-tasks (Taskserver)

This walks through a production-style install of a taskserver: a Linux host, running as an
unprivileged service user, fronted by nginx and managed by systemd. If you just want a quick
local/dev instance with no TLS, no nginx, and no systemd, see the "Development setup" section of
[Server Installation](https://github.com/ophixproject/ophix-server-base) instead — this guide
covers the real deployment path.

---

## Before you start / Prerequisites

You will need:

- A Linux server with:
  - Python 3.10 or later
  - nginx
  - systemd
  - `openssl` (needed if you self-issue a certificate — see below)

  We test on Ubuntu (20/22/24/26 LTS). Other distros should work — `configure_install` (Step 3
  below) asks where nginx config should go, defaulting to the Debian/Ubuntu layout
  (`/etc/nginx/sites-available/`, symlinked into `sites-enabled/`). If your distro loads `*.conf`
  files directly from one directory instead — RHEL/Fedora-family `conf.d` in particular — point
  the config directory there and leave the enabled directory blank; no separate symlink step is
  created in that case. The systemd unit path (`/etc/systemd/system/`) is standard across all
  systemd distros, so nothing to configure there. `adduser` below is the Debian/Ubuntu frontend to
  `useradd`; on other distros use the equivalent for yours.

- If you're using the recommended default engine, `ophix-dbengine-mariadb` (Step 2 below) brings in
  `mysqlclient` (MariaDB/MySQL client bindings), which is a C extension. If pip has to build it
  from source on your platform (no prebuilt wheel available), you'll also need build tools
  installed first:

  ```bash
  sudo apt install -y build-essential default-libmysqlclient-dev pkg-config python3-dev
  ```

  Using a different engine instead? Skip this — it's only needed for MariaDB/MySQL.

- An SSL/TLS certificate for the hostname you'll run the server on. It can be from a public CA, or
  self-issued for internal use — [`ophix-ca-tools`](https://github.com/ophixproject/ophix-ca-tools)
  is a small standalone shell/OpenSSL CA built for exactly this. You'll need three files: the
  certificate, its private key (PEM format), and — if self-issued — the CA bundle used to sign it
  (not needed for a certificate from a public CA).

  With `ophix-ca-tools`, a cert's key and crt are already stored together under
  `ssl/<domain>/<host>/` after `issue_cert.sh create`, and the CA bundle lands in your current
  directory after you run `generate_ca_bundle.sh` (normally the `ophix-ca-tools` checkout itself,
  unless you `cd` elsewhere first). We recommend copying all three into a single folder under the
  service user's own home directory, e.g. `/home/ophix/ssl/tasks.internal.yourdomain.com/` — the
  `ophix` user (created below) needs read access to wherever you point `configure_install` at, and
  consolidating them there sidesteps any cross-user permission fiddling.

- A database (MariaDB/MySQL/PostgreSQL/CockroachDB/SQL Server), with the following ready:
  - host and port
  - database name
  - username and password

  Every engine — MariaDB included — needs its matching `ophix-dbengine-*` driver plugin installed
  alongside `ophix-tasks`; none is bundled by default (see Step 2 below).

Once all of the above is sorted, you're ready to install. These instructions install the server in
user space — the service runs as an unprivileged user throughout, and `sudo`/root is only needed
for the one step that wires up nginx and systemd.

---

## Step 0 (optional) — Create a user to run your server

As a user with `sudo` access:

```bash
sudo adduser --disabled-password --gecos "" ophix
```

This creates the `ophix` user with a home directory and no usable login password — you'll operate
as it via `sudo`, not by logging in directly. Everything from here on (Steps 1–4) runs as this
user, not root:

```bash
sudo -iu ophix
```

## Step 1 — Create the install directory and a virtual environment

```bash
cd ~
mkdir taskserver && cd taskserver

python3 -m venv .task-env
source .task-env/bin/activate
```

(Or use [uv](https://docs.astral.sh/uv/) instead of `venv` — `uv venv .task-env`. uv doesn't seed
`pip` by default, so either use `uv pip install` in Step 2 or create the venv with `--seed`.)

## Step 2 — Install the taskserver and recommended add-ons

```bash
pip install ophix-tasks ophix-dbengine-mariadb ophix-docs ophix-client-management venv-cmds
```

- `ophix-server-base` is pulled in automatically as a dependency of `ophix-tasks` — no need to
  install it separately.
- `ophix-dbengine-mariadb` installs the MariaDB/MySQL driver. Every database engine needs its
  matching `ophix-dbengine-*` plugin installed explicitly — none is bundled by default, MariaDB
  included. Swap it for a different one if you're using another engine:

  ```bash
  pip install ophix-dbengine-postgres     # PostgreSQL
  pip install ophix-dbengine-mssql        # SQL Server (also requires ODBC Driver 17/18 at the OS level)
  pip install ophix-dbengine-cockroachdb  # CockroachDB
  ```

- `ophix-docs` — inline markdown documentation in the admin UI (recommended, optional).
- `ophix-client-management` — fleet client status dashboard: token rotation health, client
  package versions, last-seen tracking (recommended, optional).
- `venv-cmds` — lists the console commands available in this venv and checks installed packages
  for updates (recommended, optional).

## Step 3 — Configure the server

```bash
ophix-manage configure_install ophixtaskserver
```

This is chosen as the slug deliberately — it doesn't have to match the install directory name
(`taskserver` above), and giving it the `ophix` prefix here means the resulting systemd service
(`ophixtaskserver`) reads unambiguously in `systemctl status` alongside any other, non-Ophix
services on the box. Use whatever slug you like; it becomes the name of every generated file and
the service itself.

The wizard is interactive and asks for:

- Install directory (where runtime data — logs, SSL certs, the socket — will live)
- Server hostname (used in the nginx config and to validate your TLS certificate)
- Service user and group (defaults to `ophix`/`ophix`, matching Step 0)
- nginx config directory and enabled directory — defaults to the Debian/Ubuntu layout; see the
  Prerequisites note above if you're on a distro that lays nginx config out differently
- TLS certificate and private key paths — point these at the files from the Prerequisites step;
  the wizard validates the certificate actually covers the hostname you gave, and warns if not
- Database engine and connection details, with a live connection test before anything is saved
- Superuser username, email, and password (your first admin login)
- Theme to activate and admin title, if a theme package is installed

`ophix-tasks` has no domain-specific secret to generate at this step (unlike, say, `ophix-creds`,
which needs an encryption key) — nothing extra to prepare here beyond the above.

The wizard writes `.ophixtaskserver.conf` (used by the next step) and `.env` (Django's runtime
settings, with everything above already patched in) — both `chmod 600`. It's safe to re-run at any
time to change a setting; existing values are offered as defaults.

## Step 4 — Install the configured server

```bash
ophix-manage run_install ophixtaskserver
```

Reads `.ophixtaskserver.conf` and, in one pass:

1. Creates the install directory's subdirectory structure (`logs/`, `ssl/`, `run/`, etc.)
2. Copies your TLS certificate and key into `ssl/certs/` and `ssl/private/`
3. Generates `ophixtaskserver.nginx.conf`
4. Generates `ophixtaskserver.service` (the systemd unit)
5. Generates `ophixtaskserver_sudo_install.sh` — the root script for Step 5
6. Generates `ophixtaskserver_sudo_uninstall.sh`
7. Runs database migrations
8. Collects static files
9. Creates the superuser account
10. Activates the selected theme and sets the admin title

Available flags if you need to skip a step: `--skip-migrate`, `--skip-collectstatic`,
`--skip-superuser`.

## Step 5 — System integration (as root)

Back with `sudo` access (exit the `ophix` shell, or open a new one):

```bash
sudo bash ophixtaskserver_sudo_install.sh
```

This is the only step that touches anything outside the install directory. It:

- Sets ownership and permissions on the install directory
- Installs the nginx config and enables it
- Installs the systemd unit, enables it, and starts the service

---

That's it — you're done. The admin UI should now be live at `https://<your-hostname>/admin/`.

## Next steps

- Go to **Admin → Hosts** and create a Host entry for each machine that will run a client — clients
  register themselves against a Host's IP on first run.
- See the **Client Quickstart** doc (in the admin's Documentation panel, since `ophix-docs` is
  installed) for how to bootstrap a client against this server.
- For `ophix-tasks` specifically: install `ophix-task-client` on each host, plus whichever
  scheduler backend applies (`ophix-task-crontab` for cron-based tasks, `ophix-task-systemd` for
  systemd timer units).
