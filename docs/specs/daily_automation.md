# Daily Automation: Systemd Timer + Bot Commits

**Status:** In progress
**Author:** aallbright
**Created:** 2026-04-17

## Context

The repo already has systemd unit files (`systemd/system/`) and a git
commit script (`systemd/scripts/git-commit-and-push.sh`) designed to run
`ticker-cli run-all` daily and commit the results. These files have never
been deployed to an always-on host. The goal is to deploy them on a
second ThinkPad running Ubuntu, copy the existing 74 MB SQLite database
over, and have the pipeline run unattended after each US trading day —
committing changes as `stockmarketwords-bot`.

Several gaps exist between the current files and a trustworthy automated
setup:

1. **Timer fires 7 days/week** — stock markets are closed Sat/Sun. Running
   on weekends wastes resources and creates empty commits.
2. **EDT/EST ambiguity** — the timer comment says "6 PM EST" but uses a
   fixed 23:00 UTC. During US Eastern Daylight Time (mid-March to
   early-November) that's 7 PM EDT, which is fine but the comment is
   misleading. More importantly, 23:00 UTC during EST is 6 PM — still
   after market close. No functional change needed, but the comment
   should be accurate.
3. **Bot identity** — the git script hard-codes
   `"Stock Market Words Bot" / bot@stockmarketwords.local`. The owner
   wants commits attributed to **`stockmarketwords-bot`** with a proper
   `noreply` GitHub email so GitHub's contributor graph picks them up.
   This means a GitHub account must exist for that username (or a
   machine-user PAT) and the commit email should be
   `stockmarketwords-bot@users.noreply.github.com` (or whatever GitHub
   assigns after account creation).
4. **Commit message consistency** — current message is
   `Auto-update: Daily pipeline run YYYY-MM-DD`. It should also include
   a summary of what changed (e.g., ticker count, strategy scores date).
5. **No install / verification script** — the README has a long manual
   Quick Start. A single `install.sh` and a `verify.sh` would reduce
   human error and serve as a runbook for testing on the target host.
6. **Database migration** — the 74 MB `data/market_data.db` needs to be
   securely copied to the new host before the first automated run.
7. **No dry-run mode** — there's no way to prove the systemd setup works
   without actually hitting Yahoo Finance and NASDAQ FTP. A lightweight
   smoke test that validates paths, permissions, Python venv, DB
   connectivity, and git identity would catch 90 % of deployment errors.
8. **Service uses `python -m stock_ticker.cli`** — should use the
   installed `ticker-cli` entry point from `pyproject.toml` for
   consistency with docs and developer usage.
9. **Hugo build not in pipeline** — `run-all` generates Hugo data files
   but doesn't run `hugo --minify`. If the intent is that a separate CI
   job builds Hugo (triggered by the bot's push), this is fine — but it
   should be documented. If the intent is to also build Hugo on the
   ThinkPad, the service needs an additional step.

## Goal

A single `install.sh` + `verify.sh` pair that, when run on a fresh
Ubuntu host with the repo cloned and the database copied over, produces
a working systemd timer that runs `ticker-cli run-all` on weekday
evenings and commits the results as `stockmarketwords-bot` — with enough
automated checks that we trust it to run unattended.

## Non-goals

- Prometheus / Pushgateway metrics (documented in a separate plan).
- Hugo build on the automation host — the bot's push triggers a separate
  deploy pipeline (Cloudflare Pages or similar).
- Handling US market holidays (President's Day, etc.) — the pipeline is
  idempotent so running on a holiday just produces "no new data" and
  skips gracefully.
- Multi-repo or multi-host orchestration.

## User stories

- As the repo owner, I want to copy my DB to the ThinkPad, run one
  install script, and have the pipeline running on autopilot within
  minutes.
- As the repo owner, I want every automated commit attributed to
  `stockmarketwords-bot` so I can distinguish bot work from manual work
  in `git log`.
- As the repo owner, I want a verification script I can re-run any time
  to confirm the automation is healthy.

## Design

### 1. Timer: weekdays only

```ini
OnCalendar=Mon..Fri *-*-* 23:00:00
```

### 2. Service: use `ticker-cli` entry point

```ini
ExecStart=/opt/stock-market-words/python3/venv/bin/ticker-cli run-all
```

The venv's `bin/ticker-cli` is created by `pip install -e .` (or
`pip install .`) inside the venv thanks to `[project.scripts]` in
`pyproject.toml`.

### 3. Bot identity in git script

```bash
GIT_AUTHOR_NAME="stockmarketwords-bot"
GIT_AUTHOR_EMAIL="stockmarketwords-bot@users.noreply.github.com"
GIT_COMMITTER_NAME="stockmarketwords-bot"
GIT_COMMITTER_EMAIL="stockmarketwords-bot@users.noreply.github.com"
```

The owner needs to either:
- Create a GitHub account named `stockmarketwords-bot`, OR
- Use a machine-user personal access token (fine-grained, repo-scoped).

For SSH push, generate an ed25519 key for the `smw` user and add it as a
deploy key (write access) on the repo.

### 4. Structured commit messages

```
Daily data update: YYYY-MM-DD

Pipeline: ticker-cli run-all
Host: $(hostname)
```

### 5. `install.sh` script (new file: `systemd/scripts/install.sh`)

Automates the README's Quick Start:
1. Create `smw` user if not exists.
2. Ensure Python 3.8+ present.
3. Create venv, install deps + package.
4. Initialize DB (if no existing DB copied).
5. Copy systemd units to `/etc/systemd/system/`.
6. `systemctl daemon-reload && systemctl enable --now stock-market-words.timer`.

### 6. `verify.sh` script (new file: `systemd/scripts/verify.sh`)

Non-destructive checks:
1. `smw` user exists.
2. Venv exists and `ticker-cli --help` succeeds.
3. `data/market_data.db` exists and is readable; tables present.
4. Git identity is configured correctly.
5. SSH key exists and `ssh -T git@github.com` succeeds (or warns).
6. systemd timer is enabled and next-fire time is in the future.
7. `ticker-cli status` reports healthy.

Exit 0 = all checks pass. Non-zero = prints which check failed.

### 7. Database migration

```bash
# On source machine:
scp data/market_data.db thinkpad:/opt/stock-market-words/data/
# Then on target:
sudo chown smw:smw /opt/stock-market-words/data/market_data.db
```

`verify.sh` confirms the DB has the expected tables and recent data.

### 8. Experiments to build trust

| # | Experiment | What it proves |
|---|-----------|---------------|
| 1 | Run `verify.sh` on target host | All paths, perms, deps correct |
| 2 | `sudo -u smw ticker-cli status` | CLI works under service user |
| 3 | `sudo -u smw ticker-cli run-all --limit 5` | Pipeline runs end-to-end with 5 tickers |
| 4 | `sudo systemctl start stock-market-words.service` then check journal | systemd invocation works |
| 5 | Check git log for bot identity | Commit attributed correctly |
| 6 | `sudo systemctl list-timers` | Timer fires at correct weekday time |
| 7 | Let it run unattended for 1 weekday, inspect results | Full confidence |

## Affected files

| File | Action |
|------|--------|
| `systemd/system/stock-market-words.timer` | Modify: weekdays only, fix comment |
| `systemd/system/stock-market-words.service` | Modify: use `ticker-cli` entry point |
| `systemd/scripts/git-commit-and-push.sh` | Modify: bot identity, structured commit msg |
| `systemd/scripts/install.sh` | **Create** |
| `systemd/scripts/verify.sh` | **Create** |
| `systemd/README.md` | Update: bot setup, install/verify docs, weekday schedule |

## Verification

- **Manual on target host:**
  1. `bash systemd/scripts/install.sh` exits 0.
  2. `bash systemd/scripts/verify.sh` exits 0.
  3. `sudo systemctl start stock-market-words.service` completes
     successfully (journal shows pipeline output).
  4. `git log -1` shows author `stockmarketwords-bot`.
  5. `systemctl list-timers` shows next fire on a weekday.

- **On dev machine (this repo):**
  1. `shellcheck systemd/scripts/*.sh` passes.
  2. Timer unit parses: `systemd-analyze calendar "Mon..Fri *-*-* 23:00:00"`.

## Open questions

1. **GitHub account vs deploy key?** Default: create a
   `stockmarketwords-bot` GitHub account. Alternative: use the owner's
   account with a fine-grained PAT and set committer identity locally
   (commits appear as bot but pushes authenticate as owner). The PAT
   approach is simpler but less clean in the contributor graph.

2. **Should `install.sh` clone the repo or assume it's already cloned?**
   Default: assume already cloned to `/opt/stock-market-words`. The
   owner will `git clone` manually first so they control SSH setup.

3. **Hugo build on bot host?** Default: no. The bot pushes data; a CI
   pipeline (Cloudflare Pages) builds and deploys Hugo. If that changes,
   add `ExecStartPost` for Hugo.

## Alternatives considered

- **cron instead of systemd** — rejected because systemd provides
  journald logging, resource limits, `Persistent=true` catch-up, and
  dependency ordering (`After=network-online.target`). The project
  already chose systemd.
- **GitHub Actions scheduled workflow** — would avoid the second
  ThinkPad entirely, but the 74 MB SQLite DB and ~45-minute runtime
  make this impractical on free-tier runners, and the owner explicitly
  wants to run on local hardware.
