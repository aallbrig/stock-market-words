# Stock Market Words — Systemd Automation

Runs the data pipeline on weekday evenings and commits results as
`stockmarketwords-bot`.

## Contents

- `system/stock-market-words.service` — oneshot service: `ticker-cli run-all` → git commit → (optional) S3 backup
- `system/stock-market-words.timer` — fires Mon–Fri at 23:00 UTC (~6–7 PM ET)
- `scripts/install.sh` — automated setup on a fresh Ubuntu host
- `scripts/verify.sh` — non-destructive health checks (run any time)
- `scripts/git-commit-and-push.sh` — commits as `stockmarketwords-bot`
- `scripts/backup-db-s3.sh` — optional S3 backup (see [ADR](../docs/design/20260417_015817_UTC_s3_database_backup.md))

## Quick Start

```bash
# 1. Clone repo to /opt/stock-market-words
sudo git clone git@github.com:aallbrig/stock-market-words.git /opt/stock-market-words

# 2. Copy your existing database
scp data/market_data.db target-host:/opt/stock-market-words/data/

# 3. Run the installer
sudo bash /opt/stock-market-words/systemd/scripts/install.sh

# 4. Set up SSH deploy key for git push
sudo su - smw
ssh-keygen -t ed25519 -C "smw@$(hostname)"
cat ~/.ssh/id_ed25519.pub    # Add as deploy key (write access) on GitHub
exit

# 5. Configure git remote
sudo su - smw -c "cd /opt/stock-market-words && git remote set-url origin git@github.com:aallbrig/stock-market-words.git"

# 6. Verify everything
sudo bash /opt/stock-market-words/systemd/scripts/verify.sh
```

## Bot Identity (stockmarketwords-bot)

Automated commits are attributed to:

- **Name:** `stockmarketwords-bot`
- **Email:** `stockmarketwords-bot@users.noreply.github.com`

This uses a **fine-grained PAT** (personal access token) scoped to
`aallbrig/stock-market-words` with `contents: write` permission.
The PAT authenticates pushes; the committer identity is set via
environment variables in `git-commit-and-push.sh`.

### Commit format

```
Daily data update: 2026-04-17

Pipeline: ticker-cli run-all
Host: thinkpad-2
Files changed: 42
```

## Schedule

| Setting | Value |
|---------|-------|
| **When** | Mon–Fri 23:00 UTC |
| **EST/EDT** | 6 PM EST (winter) / 7 PM EDT (summer) |
| **On boot** | 5 min after startup if a run was missed |
| **Jitter** | ±5 min (`RandomizedDelaySec`) |
| **Persistent** | Yes — catches up after downtime |

US market holidays: the pipeline is idempotent; running on a holiday
produces no new data and commits nothing.

## Resource Limits

| Limit | Value |
|-------|-------|
| Memory | 4 GB |
| CPU | 200% (2 cores) |
| Timeout | 1 hour |
| Typical runtime | 30–45 min |

## Monitoring

```bash
# Timer status / next fire time
sudo systemctl list-timers stock-market-words.timer

# Live logs
sudo journalctl -u stock-market-words.service -f

# Today's errors only
sudo journalctl -u stock-market-words.service -p err --since today

# Manual run
sudo systemctl start stock-market-words.service

# Health check
sudo bash /opt/stock-market-words/systemd/scripts/verify.sh
```

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | — |
| 1 | Needs to run | Normal |
| 2 | Missing deps | `pip install -e .` in venv |
| 3 | DB not ready | `ticker-cli init` |
| 4 | Services unreachable | Check network |
| 5 | Interrupted | Re-run (idempotent) |
| 6 | Failed | Check logs |
| 7 | Partial | Re-run (resumes) |

## Troubleshooting

```bash
# Test CLI as service user
sudo -u smw bash -c "cd /opt/stock-market-words/python3 && source venv/bin/activate && ticker-cli status"

# Test SSH push
sudo su - smw -c "ssh -T git@github.com"

# Test network
curl -sI https://query1.finance.yahoo.com | head -1

# Fix permissions
sudo chown -R smw:smw /opt/stock-market-words
```

## S3 Backup (Optional)

See the full ADR: [`docs/design/20260417_015817_UTC_s3_database_backup.md`](../docs/design/20260417_015817_UTC_s3_database_backup.md)

To enable, uncomment the `ExecStartPost` line for `backup-db-s3.sh` in
the service file and configure AWS credentials for the `smw` user.

## File Locations (when installed)

| Item | Path |
|------|------|
| Service/Timer | `/etc/systemd/system/stock-market-words.*` |
| Repository | `/opt/stock-market-words/` |
| Python venv | `/opt/stock-market-words/python3/venv/` |
| Database | `/opt/stock-market-words/data/market_data.db` |
| Logs | `journalctl -u stock-market-words.service` |

## Uninstallation

```bash
sudo systemctl stop stock-market-words.timer
sudo systemctl disable stock-market-words.timer
sudo rm /etc/systemd/system/stock-market-words.{service,timer}
sudo systemctl daemon-reload
# Optionally: sudo rm -rf /opt/stock-market-words && sudo userdel -r smw
```

## Related Docs

- [Architecture overview](../docs/design/20260408_013203_UTC_architecture_overview.md)
- [Data pipeline](../docs/design/20260408_013203_UTC_data_pipeline.md)
- [S3 backup ADR](../docs/design/20260417_015817_UTC_s3_database_backup.md)
- [Daily automation spec](../docs/specs/daily_automation.md)
