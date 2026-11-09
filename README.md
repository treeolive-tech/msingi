<!-- ramani: README.md -->
<h1 align="center">msingi</h1>

<p align="center">
  <strong>Lay the foundation, once, the same way every time.</strong><br>
  Provision an Ubuntu server from GitHub Actions: pick a profile, press run, and only the modules you chose are set up.
</p>

<p align="center">
  <img alt="Ubuntu 24.04" src="https://img.shields.io/badge/ubuntu-24.04-E95420?logo=ubuntu&logoColor=white">
  <img alt="GitHub Actions" src="https://img.shields.io/badge/runs%20on-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white">
  <img alt="Idempotent" src="https://img.shields.io/badge/scripts-idempotent-006600">
  <img alt="MIT license" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="msingi means foundation in Swahili" src="https://img.shields.io/badge/msingi-Swahili%20for%20%22foundation%22-006600">
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#profiles">Profiles</a> ·
  <a href="#run-it">Run it</a> ·
  <a href="#modules">Modules</a> ·
  <a href="#custom-profile">Custom profile</a> ·
  <a href="#dry-run">Dry run</a> ·
  <a href="#security">Security</a>
</p>

> **msingi** _(m-SEEN-gee)_ is Swahili for **"foundation"**. A server needs one before anything is built on it: a firewall, a web server, certificates, a database, and a user with the right tools. msingi lays all of that from a single GitHub Actions run, over SSH, with small shell scripts you can read in a minute each.

```text
Actions → Msingi → Run workflow

  server_host     203.0.113.10
  target_user     developer
  setup_profile   Full Development Server
```

## Why

Setting up a fresh server by hand means the same twenty commands, in a slightly different order, with one forgotten step every time. msingi writes the steps down once. Every script checks what is already there and skips it, so running the workflow again is always safe.

## Features

- 🧱 **Modular.** Nine small scripts, one job each. Run them all, or only the ones you pick.
- 🎛️ **Four profiles.** Full server, system services only, user tools only, or your own mix.
- ♻️ **Idempotent.** Re-run any time. Installed things are detected and skipped.
- 👤 **Creates the user for you.** Name a `target_user`. If it doesn't exist, msingi creates it, and can give it passwordless sudo.
- 🔒 **Lockout-aware firewall.** UFW is enabled only after the OpenSSH rule is confirmed.
- 🔍 **Dry run.** See what would happen before anything on the server changes.
- 🔑 **Hands you the Git key.** The generated SSH public key is printed in the run summary, ready to paste into GitHub or GitLab.
- 🧹 **Cleans up after itself.** The uploaded scripts and the runner's copy of the deploy key are removed at the end, even if a step fails.

## Quick start

1. **Fork this repository.** You need your own copy to add Secrets and Variables.
2. **Add two Secrets:** `SERVER_SSH_KEY` and `SUDO_ACCESS_USER`.
3. **Run it:** Actions → **Msingi** → **Run workflow**, then choose a profile.

That is the whole setup. Variables are optional (see [Configuration](#configuration)).

### Before you start

- An Ubuntu server (tested on 24.04).
- An existing user on it with passwordless sudo (`NOPASSWD:ALL`), reachable with your deploy key.
- The deploy key's public half in that user's `~/.ssh/authorized_keys`.

### Secrets

Add these under **Settings** → **Secrets and variables** → **Actions** → **Secrets**.

| Secret             | What it is                                                                                                                                                                |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SERVER_SSH_KEY`   | The private key the runner uses to connect. Paste the full key, no passphrase. Its public key must be in `authorized_keys` of `SUDO_ACCESS_USER`.                         |
| `SUDO_ACCESS_USER` | An existing user with passwordless sudo, such as `ubuntu`, `root`, or a dedicated deploy user. Used for every system module. Only required when a system module will run. |

## Profiles

Pick one when you run the workflow.

| Profile                               | System modules                                    | User modules                  | Best for                                         |
| ------------------------------------- | ------------------------------------------------- | ----------------------------- | ------------------------------------------------ |
| **Full Development Server**           | OpenSSH/UFW, Packages, Nginx, Certbot, PostgreSQL | uv, nvm, repos dir, Git + SSH | A brand-new server, everything in one go         |
| **System Services Only**              | OpenSSH/UFW, Packages, Nginx, Certbot, PostgreSQL | none                          | Infrastructure without personal dev tools        |
| **User Tools Only**                   | none                                              | uv, nvm, repos dir, Git + SSH | Adding dev tools to a user, no sudo needed       |
| **Custom (use repository variables)** | whatever `SETUP_*` says                           | whatever `SETUP_*` says       | Fine-grained control, or adding one module later |

## Run it

When you dispatch the workflow you are asked for:

| Input            | Required | Default | What it does                                                              |
| ---------------- | -------- | ------- | ------------------------------------------------------------------------- |
| `server_host`    | yes      | n/a     | Server IP or hostname                                                     |
| `server_port`    | no       | `22`    | SSH port                                                                  |
| `target_user`    | yes      | n/a     | The user to configure. Created if missing. User modules run as this user. |
| `make_user_sudo` | no       | `false` | Give the target user passwordless sudo (new or existing)                  |
| `ssh_public_key` | no       | n/a     | Added to the target user's `authorized_keys` if not already there         |
| `setup_profile`  | yes      | Full    | One of the four profiles                                                  |
| `git_user_name`  | no       | n/a     | Required when the Git + SSH module runs                                   |
| `git_user_email` | no       | n/a     | Required when the Git + SSH module runs; must look like an email          |
| `dry_run`        | no       | `false` | Show what would happen, change nothing                                    |

There is no "create user" switch. If `target_user` doesn't exist, it is created.

## Modules

### System modules

These run as `SUDO_ACCESS_USER` and need sudo.

| Module         | Script           | What it does                                                                                                    | Variable            |
| -------------- | ---------------- | --------------------------------------------------------------------------------------------------------------- | ------------------- |
| 🔒 OpenSSH/UFW | `openssh-ufw.sh` | Allows OpenSSH in UFW, then enables UFW only once the rule is confirmed. Skips enabling if it can't confirm it. | `SETUP_OPENSSH_UFW` |
| 🛠️ Packages    | `packages.sh`    | Installs git, curl, wget, snapd, SQLite, Pandoc, TeX (XeTeX), and build tools                                   | `SETUP_PACKAGES`    |
| 🌐 Nginx       | `nginx.sh`       | Installs, enables and starts Nginx, opens `Nginx Full` in UFW, and writes the `port-proxy.conf` snippet         | `SETUP_NGINX`       |
| 🔏 Certbot     | `certbot.sh`     | Installs Certbot through snap (needs `snapd`, which Packages provides)                                          | `SETUP_CERTBOT`     |
| 🐘 PostgreSQL  | `postgres.sh`    | Installs PostgreSQL and contrib, then enables and starts the service                                            | `SETUP_POSTGRES`    |

### User modules

These run as `target_user`, without sudo.

| Module       | Script       | What it does                                                                         | Variable          |
| ------------ | ------------ | ------------------------------------------------------------------------------------ | ----------------- |
| 🐍 uv        | `uv.sh`      | Installs [uv](https://docs.astral.sh/uv/), then a Python through it if none is there | `SETUP_UV`        |
| 📗 nvm       | `nvm.sh`     | Installs nvm (version from `NVM_VERSION`), then the latest Node.js, and updates npm  | `SETUP_NVM`       |
| 📁 Repos dir | `repos.sh`   | Makes sure `~/repos` exists                                                          | `SETUP_REPOS_DIR` |
| 🔑 Git + SSH | `git-ssh.sh` | Sets global git name and email, and creates `~/.ssh/id_ed25519` if absent            | `SETUP_GIT_SSH`   |

### Nginx: a proxy snippet, not a site

msingi installs Nginx and a reusable snippet. It does **not** create a server block; that part is yours.

```nginx
server {
  listen 80;
  server_name your.domain;
  set $upstream_port 8080;   # the port your app listens on
  include /etc/nginx/snippets/port-proxy.conf;
}
```

Then `sudo nginx -t && sudo systemctl reload nginx`.

## What you do after a run

msingi stops at the foundation on purpose. These are left to you:

| Module     | Follow-up                                                                               |
| ---------- | --------------------------------------------------------------------------------------- |
| Nginx      | Add your server block (above)                                                           |
| Certbot    | Once your domain and server block exist: `sudo certbot certonly --nginx -d your.domain` |
| PostgreSQL | Create roles and databases: `sudo -iu postgres psql`                                    |
| Git + SSH  | Copy the public key from the run summary into GitHub, GitLab or wherever you host code  |

## Dry run

Set `dry_run` to `true` to see what a run would do. Steps print `[DRY RUN] Would …` lines instead of acting.

```console
[DRY RUN] Would create user: developer
[DRY RUN] Would run apt-get update
[DRY RUN] Would setup OpenSSH and UFW
[DRY RUN] Would install necessary packages
[DRY RUN] Would setup Nginx
[DRY RUN] Would setup uv
[DRY RUN] Would setup Git and SSH
```

What a dry run does and doesn't do:

- ✅ Connects over SSH and checks whether the target user exists.
- ✅ Copies the scripts to a temporary folder in `/tmp` on the server (removed again at the end).
- ❌ Doesn't create users, install packages, enable services or edit configuration.

## Custom profile

Choose **Custom (use repository variables)** and the `SETUP_*` variables decide what runs. Each must be the literal string `true` or `false`. Anything unset counts as `false`.

Add them under **Settings** → **Secrets and variables** → **Actions** → **Variables**.

```text
SETUP_NGINX=true
SETUP_NVM=true
```

Run the workflow with the Custom profile and only Nginx and nvm are touched. This is also how you add a module later: set just that one to `true`, and everything already installed stays as it is.

## Configuration

| Variable      | Default   | What it does                                   |
| ------------- | --------- | ---------------------------------------------- |
| `NVM_VERSION` | `v0.40.4` | The nvm release tag the install script fetches |
| `SETUP_*`     | `false`   | Module switches for the Custom profile         |

## How it works

```text
  checkout repo
       │
       ▼
  pick modules  ◄── profile, or SETUP_* variables (Custom)
       │
       ▼
  validate      ── Git name/email present? SUDO_ACCESS_USER set for system modules?
       │
       ▼
  SSH key + connection test  ── as SUDO_ACCESS_USER, or target_user if no system modules
       │
       ▼
  create / update target user  (+ sudo, + authorized key)
       │
       ▼
  upload scripts to /tmp/msingi-<UTC timestamp>/
       │
       ▼
  system modules (sudo)  →  user modules (target_user)
       │
       ▼
  fetch Git public key  →  run summary
       │
       ▼
  cleanup: remove remote scripts and the runner's key   (always runs)
```

### Idempotency

The workflow variables only decide **whether** a script runs. Each script then checks its own state: binary already installed, service already enabled, directory or key already present. Run it twice and the second run changes nothing.

## Troubleshooting

| Problem                       | What to check                                                                               |
| ----------------------------- | ------------------------------------------------------------------------------------------- |
| SSH connection fails          | Host, port, key format (`ssh -i key user@host`), the server's firewall, and that it is up   |
| `SUDO_ACCESS_USER` error      | Add the secret, and make sure that user really has passwordless sudo                        |
| Git module error              | Provide both `git_user_name` and `git_user_email` whenever the profile includes Git + SSH   |
| UFW wasn't enabled            | The OpenSSH rule couldn't be confirmed. Fix that and run again; it's a deliberate safeguard |
| Certbot says snapd is missing | Run Packages first (it installs `snapd`), or include it in your Custom profile              |

## Security

- Passwordless sudo goes only to `SUDO_ACCESS_USER` and, if you ask for it, `target_user`. Keep that list short.
- Use a **dedicated** deploy key, and rotate it now and then.
- The generated Git private key never leaves the server. Only the public half appears in the run summary.
- Audit `~/.ssh/authorized_keys` and skim run logs for surprises.
- Give `SUDO_ACCESS_USER` no more privilege than the modules need.

## Add your own module

1. Add `scripts/your-module.sh` in the same shape as the others: check first, exit early if satisfied, print clear status lines.
2. Add a `SETUP_YOUR_MODULE` variable and wire it into the "Determine modules" step.
3. Add a step to `.github/workflows/msingi.yaml` with the same `if:` condition and dry-run guard.

## Repository layout

```text
.github/workflows/msingi.yaml          the workflow
scripts/
  openssh-ufw.sh  packages.sh  nginx.sh  certbot.sh  postgres.sh
  uv.sh  nvm.sh  repos.sh  git-ssh.sh
LICENSE
README.md
```

## License

MIT © Treeolive Tech Ltd. Use it, change it, ship it; just keep the copyright notice.

---

<p align="center">
  <em>"...but the people who know their God shall be strong and do exploits."</em><br>
  Daniel 11:32
</p>
