<!-- ramani: README.md -->
<h1 align="center">msingi</h1>

<p align="center">
  <strong>Lay the foundation, once, the same way every time.</strong><br>
  Provision an Ubuntu server over SSH from your own machine or from the GitHub Actions tab: pick a profile, run it, and only the modules you chose are set up.
</p>

<p align="center">
  <a href="https://pypi.org/project/msingi/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/msingi?color=006600&label=pypi"></a>
  <a href="https://www.python.org/"><img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://docs.astral.sh/uv/"><img alt="Built with uv" src="https://img.shields.io/badge/built%20with-uv-DE5FE9"></a>
  <img alt="Idempotent" src="https://img.shields.io/badge/modules-idempotent-006600">
  <img alt="MIT license" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="msingi means foundation in Swahili" src="https://img.shields.io/badge/msingi-Swahili%20for%20%22foundation%22-006600">
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#run-from-github-actions">GitHub Actions</a> ·
  <a href="#profiles">Profiles</a> ·
  <a href="#options">Options</a> ·
  <a href="#modules">Modules</a> ·
  <a href="#dry-run">Dry run</a> ·
  <a href="#security">Security</a>
</p>

> **msingi** _(m-SEEN-gee)_ is Swahili for **"foundation"**. A server needs one before anything is built on it: a firewall, a web server, certificates, a database, and a user with the right tools. msingi lays all of that in one run, over SSH, with small Python modules you can read from top to bottom in a minute each.

```console
$ uvx msingi 203.0.113.10 developer --sudo-user ubuntu --git-name "Ada Lovelace" --git-email ada@example.com
```

## Why

Setting up a fresh server by hand means the same twenty commands, in a slightly different order, with one forgotten step every time. msingi writes the steps down once. Every module checks what is already there and skips it, so running it again is always safe.

## Features

- 🧱 **Modular.** Nine modules, one job each. Run them all, or only the ones you pick.
- 🎛️ **Four profiles.** Full server, system services only, user tools only, or your own mix.
- ♻️ **Idempotent.** Re-run any time. Installed things are detected and skipped.
- 👤 **Creates the user for you.** Name the user. If it doesn't exist, msingi creates it, and can give it passwordless sudo and your public key.
- 🔒 **Lockout-aware firewall.** UFW is enabled only after the SSH rule is confirmed, and a custom SSH port is allowed too.
- 🔍 **Dry run.** See what would happen before anything on the server changes.
- 🖱️ **No terminal needed.** Fork the repo and run msingi from the Actions tab with a form.
- 🔑 **Hands you the Git key.** The generated SSH public key is printed at the end, and `--copy` puts it on your clipboard, ready to paste into GitHub or GitLab.
- 🪶 **Nothing to install on the server, one small dependency here.** msingi uses the `ssh` command you already have, plus [`pyperclip`](https://pypi.org/project/pyperclip/) for `--copy`.

## Install

```bash
uv tool install msingi      # install the command globally (recommended)
uvx msingi --help           # or run it once without installing anything
pipx install msingi         # pipx or plain pip work too: pip install msingi
```

msingi needs the OpenSSH client (`ssh`) on your machine. It comes with macOS, Linux and Windows 10/11.

No terminal or ssh client? Skip to [Run from GitHub Actions](#run-from-github-actions).

## Quick start

### Before you start

- An Ubuntu server you can reach over SSH.
- An existing user on it with **passwordless sudo** (`NOPASSWD:ALL`), such as `ubuntu` or `root`. msingi uses it for the system modules (`--sudo-user`).
- A way to log in as that user **without typing a password or passphrase**: an ssh-agent with your key loaded (`ssh-add`), or a key file without a passphrase (`--key`). msingi never prompts for either.

### Run it

```bash
msingi 203.0.113.10 developer --sudo-user ubuntu \
  --git-name "Ada Lovelace" --git-email ada@example.com
```

That runs the **Full Development Server** profile: it creates `developer` if needed, sets up the system services as `ubuntu`, then the user tools as `developer`. Add `--dry-run` first if you want to see the plan.

If `developer` is new, give it your public key so msingi can log in as that user for the user modules:

```bash
msingi 203.0.113.10 developer --sudo-user ubuntu --make-sudo \
  --public-key ~/.ssh/id_ed25519.pub \
  --git-name "Ada Lovelace" --git-email ada@example.com
```

## Run from GitHub Actions

No terminal? Fork this repo (a **private** fork is best) and run msingi from the **Actions** tab. The workflow runs the same `msingi` CLI from your fork's code, so nothing is duplicated in YAML.

### Set up once

1. **Settings → Secrets and variables → Actions:** add a secret named `SERVER_SSH_KEY`. It is a private key **without a passphrase** that can log in as your sudo user.
2. Optional: **Settings → Environments → New environment** named `provision`, tick **Required reviewers** and add people as an approval gate. On a private repo this needs a paid GitHub plan.

### Run it

1. Open **Actions → Provision a server → Run workflow**.
2. Fill in the form. The inputs mirror the CLI flags: host, user, sudo user, port, profile, modules, make sudo, public key, Git name and email, nvm version and dry run.
3. Leave **Dry run** on for the first run to see the plan, then run again with it off.

The new Git public key is printed in the run log. `modules` only applies to the `custom` profile, just like `-m` on the command line. `--copy` doesn't apply on a runner.

> [!NOTE]
> Logs are public in a public repo. The workflow masks the host and Git email (shown as `***`), but not every input: user names and the Git public key still appear. The public key is safe to share. A private fork is the safest choice if you don't want any of it visible. GitHub-hosted runners also have changing IP addresses, so this won't reach a server whose firewall only allows SSH from known addresses.

## Profiles

Pick one with `-P`, or choose your own modules with `-m`.

| Profile                    | System modules                                    | User modules                  | Best for                                         |
| -------------------------- | ------------------------------------------------- | ----------------------------- | ------------------------------------------------ |
| **`full`** (default)       | OpenSSH/UFW, Packages, Nginx, Certbot, PostgreSQL | uv, nvm, repos dir, Git + SSH | A brand-new server, everything in one go         |
| **`system`**               | OpenSSH/UFW, Packages, Nginx, Certbot, PostgreSQL | none                          | Infrastructure without personal dev tools        |
| **`user`**                 | none                                              | uv, nvm, repos dir, Git + SSH | Adding dev tools to a user, no sudo needed       |
| **`custom`** (set by `-m`) | the ones you name                                 | the ones you name             | Fine-grained control, or adding one module later |

```bash
msingi 203.0.113.10 developer -s ubuntu -P system
msingi 203.0.113.10 developer -P user --git-name "Ada" --git-email ada@example.com
msingi 203.0.113.10 developer -s ubuntu -m nginx,nvm     # only these two
```

Modules always run in the same order, whatever order you list them in.

## Options

```text
msingi HOST USER [options]
```

| Option                     | What it does                                                                                                                                                                            |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HOST`                     | Server IP address or hostname                                                                                                                                                           |
| `USER`                     | The user to set up. Created if missing. User modules run as this user.                                                                                                                  |
| `-p, --port PORT`          | SSH port (default: `22`)                                                                                                                                                                |
| `-k, --key FILE`           | Private key to log in with (also `MSINGI_SSH_KEY`). Default: ssh's own keys and agent.                                                                                                  |
| `-s, --sudo-user USER`     | Existing user with passwordless sudo, used for system modules (also `MSINGI_SUDO_USER`)                                                                                                 |
| `--make-sudo`              | Give `USER` passwordless sudo (new or existing)                                                                                                                                         |
| `--public-key KEY_OR_FILE` | Public key (or a `.pub` file) to add to `USER`'s `authorized_keys`                                                                                                                      |
| `-P, --profile NAME`       | `full`, `system`, `user` or `custom` (default: `full`)                                                                                                                                  |
| `-m, --modules A,B`        | Set up only these modules (a custom profile). Can't be combined with `-P full`, `system` or `user`.                                                                                     |
| `--git-name NAME`          | Git user name. Required when the Git + SSH module runs.                                                                                                                                 |
| `--git-email EMAIL`        | Git user email. Required when the Git + SSH module runs; must look like an email.                                                                                                       |
| `--nvm-version TAG`        | nvm release to install (default: `v0.40.4`; also `MSINGI_NVM_VERSION`)                                                                                                                  |
| `-c, --copy`               | Copy the new Git public key to your clipboard (needs the Git + SSH module). On Linux the clipboard needs `xclip`, `xsel` or `wl-clipboard`. If copying fails, the key is still printed. |
| `-n, --dry-run`            | Show what would happen, change nothing                                                                                                                                                  |
| `-V, --version`            | Print the installed version and exit                                                                                                                                                    |

Flags beat environment variables. `NO_COLOR=1` turns colour off.

## Modules

### System modules

These run as `--sudo-user` and need sudo.

| Module         | Name          | What it does                                                                                                |
| -------------- | ------------- | ----------------------------------------------------------------------------------------------------------- |
| 🔒 OpenSSH/UFW | `openssh-ufw` | Allows OpenSSH (and your SSH port, if it isn't 22) in UFW, then enables UFW only once the rule is confirmed |
| 🛠️ Packages    | `packages`    | Installs git, curl, wget, snapd, SQLite, Pandoc, TeX (XeTeX), and build tools                               |
| 🌐 Nginx       | `nginx`       | Installs, enables and starts Nginx, opens `Nginx Full` in UFW, and writes the `port-proxy.conf` snippet     |
| 🔏 Certbot     | `certbot`     | Installs Certbot through snap (needs `snapd`, which Packages provides)                                      |
| 🐘 PostgreSQL  | `postgres`    | Installs PostgreSQL and contrib, then enables and starts the service                                        |

### User modules

These run as `USER`, without sudo.

| Module       | Name      | What it does                                                                               |
| ------------ | --------- | ------------------------------------------------------------------------------------------ |
| 🐍 uv        | `uv`      | Installs [uv](https://docs.astral.sh/uv/), then a Python through it if uv manages none yet |
| 📗 nvm       | `nvm`     | Installs nvm (version from `--nvm-version`), then the latest Node.js, and updates npm      |
| 📁 Repos dir | `repos`   | Makes sure `~/repos` exists                                                                |
| 🔑 Git + SSH | `git-ssh` | Sets global git name and email, and creates `~/.ssh/id_ed25519` if absent                  |

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

| Module     | Follow-up                                                                                                         |
| ---------- | ----------------------------------------------------------------------------------------------------------------- |
| Nginx      | Add your server block (above)                                                                                     |
| Certbot    | Once your domain and server block exist: `sudo certbot certonly --nginx -d your.domain`                           |
| PostgreSQL | Create roles and databases: `sudo -iu postgres psql`                                                              |
| Git + SSH  | Copy the public key printed at the end of the run (or use `--copy`) into GitHub, GitLab or wherever you host code |

## Dry run

Add `--dry-run` to see what a run would do. Steps print `[DRY RUN] Would …` lines instead of acting.

```console
$ msingi 203.0.113.10 developer -s ubuntu --git-name Ada --git-email ada@example.com --dry-run
[DRY RUN] Would create user: developer
[DRY RUN] Would run apt-get update
[DRY RUN] Would set up OpenSSH and UFW
[DRY RUN] Would set up necessary packages
[DRY RUN] Would set up Nginx
...
[DRY RUN] Would set up Git and SSH
```

What a dry run does and doesn't do:

- ✅ Connects over SSH and checks whether the target user exists.
- ❌ Doesn't create users, install packages, enable services or edit configuration.

## How it works

```text
  read the command line  ◄── profile, or --modules
       │
       ▼
  validate      ── names, port, key, Git name/email, --sudo-user for system modules
       │
       ▼
  connect       ── as --sudo-user, or USER if there are no system modules
       │
       ▼
  create / update USER  (+ sudo, + authorized key)
       │
       ▼
  apt-get update  (only if a system module will run)
       │
       ▼
  system modules (as --sudo-user)  →  user modules (as USER)
       │
       ▼
  summary  →  the new Git public key
```

Each module is one file in `src/msingi/modules/` with a `setup(conn, settings)` function. It checks its own state (binary installed, service enabled, directory or key present) and does only what is missing, so the second run changes nothing.

## Troubleshooting

| Problem                       | What to check                                                                                            |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| "can't connect to …"          | Host, port, and that `ssh -i KEY USER@HOST` works by itself. msingi can't type passwords or passphrases. |
| `a sudo user is required`     | System modules need `--sudo-user` (or `MSINGI_SUDO_USER`), and that user needs passwordless sudo         |
| Can't log in as the new user  | Pass `--public-key` so msingi can add your key before the user modules run                               |
| Git module error              | Give both `--git-name` and `--git-email` whenever the profile includes Git + SSH                         |
| UFW wasn't enabled            | The SSH rule couldn't be confirmed. Fix that and run again; it's a deliberate safeguard                  |
| Certbot says snapd is missing | Run `packages` first (it installs `snapd`), or include it in your `--modules`                            |
| Workflow can't connect        | Check the `SERVER_SSH_KEY` secret (no passphrase) and that the server's firewall allows runner IPs       |

## Security

- Passwordless sudo goes only to `--sudo-user` and, if you ask for it with `--make-sudo`, `USER`. Keep that list short.
- Use a **dedicated** deploy key, and rotate it now and then.
- msingi accepts new host keys on first contact (`StrictHostKeyChecking=accept-new`) and refuses changed ones. For a server you haven't connected to before, compare the fingerprint yourself if that matters to you.
- The generated Git private key never leaves the server. Only the public half is printed.
- Audit `~/.ssh/authorized_keys` and skim the output of a run for surprises.
- Give `--sudo-user` no more privilege than the modules need.
- In the GitHub Actions workflow, keep `SERVER_SSH_KEY` as a secret, prefer a private fork (logs are public in a public repo, and only the host and Git email are masked), and consider required reviewers on the `provision` environment. The key is written to a temporary file readable only by the runner user and deleted when the job ends.

## Add your own module

1. Add `src/msingi/modules/your_module.py` with `NAME` (its command-line name), `TITLE` (shown in the run), `SYSTEM` (`True` if it needs sudo) and `setup(conn, settings)`. Check first, return early if satisfied, print clear status lines. Copy `repos.py`; it is the smallest.
2. Add it to `MODULES` in `src/msingi/modules/__init__.py`, in the order it should run.
3. Add its name to `SYSTEM_MODULES` or `USER_MODULES` in `src/msingi/profiles.py`.
4. Add a test in `tests/test_modules.py`. The `server` fixture is a fake server that records commands, so tests need no real server.

## Development

```bash
uv sync
uv run pytest
```

msingi has one runtime dependency, [`pyperclip`](https://pypi.org/project/pyperclip/), imported only when you pass `--copy`. Tests use a fake server, plus a stand-in `ssh` that runs commands on your own machine to check quoting.

```text
.github/workflows/
  provision.yml run msingi from the Actions tab
  publish.yml   publish to PyPI or TestPyPI
src/msingi/
  cli.py        arguments in, settings out
  runner.py     the whole run, top to bottom
  account.py    create the user, sudo, authorized key
  ssh.py        run commands on the server
  system.py     apt, services, UFW
  clipboard.py  copy the Git public key
  profiles.py   the module sets
  settings.py   what a run needs, and its checks
  modules/      one file per module
```

## License

MIT © Treeolive Tech Ltd. Use it, change it, ship it; just keep the copyright notice.

---

<p align="center">
  <em>"...but the people who know their God shall be strong and do exploits."</em><br>
  Daniel 11:32
</p>
