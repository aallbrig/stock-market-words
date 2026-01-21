# Systemd Service Files

This directory contains systemd service and timer files for running the Stock Market Words data pipeline as a scheduled system service.

## Contents

- **`system/`** - Systemd unit files (service and timer)
  - `stock-market-words.service` - Main service definition
  - `stock-market-words.timer` - Timer for daily execution at 6PM EST

- **`scripts/`** - Helper scripts
  - `git-commit-and-push.sh` - Automatically commits and pushes changes after pipeline runs

- **`SETUP.md`** - Complete installation and configuration guide
- **`METRICS_PLAN.md`** - Detailed plan for adding Prometheus metrics (not yet implemented)

## Quick Start

See [SETUP.md](SETUP.md) for complete installation instructions.

### Basic Installation

```bash
# Install service files
sudo cp system/*.service system/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start timer
sudo systemctl enable --now stock-market-words.timer

# Check status
sudo systemctl status stock-market-words.timer
```

## Service Overview

### Execution Schedule
- **Default**: Daily at 6PM EST (23:00 UTC)
- **On boot**: Runs 5 minutes after system startup if missed
- **Randomization**: ±5 minutes to avoid load spikes

### What It Does
1. Runs the full data pipeline (`python -m stock_ticker.cli run-all`)
2. Fetches ticker lists from NASDAQ FTP
3. Downloads price/volume data from Yahoo Finance
4. Calculates strategy scores
5. Generates Hugo static site content
6. Commits and pushes changes to git (if configured)

### Resource Limits
- **Memory**: 4GB maximum
- **CPU**: 200% (2 cores)
- **Timeout**: 1 hour (3600 seconds)

## Monitoring

### View Logs

```bash
# Recent logs
sudo journalctl -u stock-market-words.service -n 100

# Follow logs in real-time
sudo journalctl -u stock-market-words.service -f

# Logs from today
sudo journalctl -u stock-market-words.service --since today

# Errors only
sudo journalctl -u stock-market-words.service -p err
```

### Check Status

```bash
# Timer status (when is next run?)
sudo systemctl status stock-market-words.timer

# Service status (is it running now?)
sudo systemctl status stock-market-words.service

# List all timers
sudo systemctl list-timers stock-market-words.timer
```

### Exit Codes

The CLI uses specific exit codes for different failure modes:

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | None needed |
| 1 | Pipeline needs to run | Normal - will run on timer |
| 2 | Missing Python dependencies | Run `pip install -r requirements.txt` |
| 3 | Database not initialized | Run `python -m stock_ticker.cli init` |
| 4 | External services unreachable | Check network connectivity |
| 5 | Pipeline interrupted | Will resume automatically |
| 6 | Pipeline failed | Check logs for details |
| 7 | Pipeline partially complete | Will resume automatically |

## Configuration

### Change Run Time

Edit the timer to change when the pipeline runs:

```bash
sudo systemctl edit --full stock-market-words.timer
```

Modify the `OnCalendar` line:
```ini
OnCalendar=*-*-* 23:00:00  # UTC time
```

Common schedules:
- `*-*-* 23:00:00` - Daily at 23:00 (6PM EST)
- `Mon-Fri *-*-* 23:00:00` - Weekdays only
- `*-*-* 06:00:00` - Daily at 06:00 (1AM EST)

After editing:
```bash
sudo systemctl daemon-reload
sudo systemctl restart stock-market-words.timer
```

### Disable Auto-Commit

To disable automatic git commits, edit the service:

```bash
sudo systemctl edit --full stock-market-words.service
```

Comment out the `ExecStartPost` line:
```ini
# ExecStartPost=/opt/stock-market-words/systemd/scripts/git-commit-and-push.sh
```

Then reload:
```bash
sudo systemctl daemon-reload
```

## Troubleshooting

### Service Won't Start

1. Check dependencies: `sudo su - smw -c "cd /opt/stock-market-words/python3 && source venv/bin/activate && python -m stock_ticker.cli status"`
2. Check permissions: `sudo chown -R smw:smw /opt/stock-market-words`
3. View errors: `sudo journalctl -u stock-market-words.service -p err`

### Network Issues

```bash
# Test FTP
telnet ftp.nasdaqtrader.com 21

# Test Yahoo Finance
curl -I https://query1.finance.yahoo.com

# Check network target
sudo systemctl status network-online.target
```

### Git Push Fails

```bash
# Test SSH key
sudo su - smw -c "ssh -T git@github.com"

# Check git config
sudo su - smw -c "cd /opt/stock-market-words && git remote -v"

# Test manual push
sudo su - smw -c "cd /opt/stock-market-words && git push origin main"
```

## Manual Operations

### Run Pipeline Now

```bash
sudo systemctl start stock-market-words.service
```

### Stop Running Pipeline

```bash
sudo systemctl stop stock-market-words.service
```

### Disable Scheduled Runs

```bash
sudo systemctl stop stock-market-words.timer
sudo systemctl disable stock-market-words.timer
```

### Re-enable Scheduled Runs

```bash
sudo systemctl enable --now stock-market-words.timer
```

## File Locations

When installed:
- Service files: `/etc/systemd/system/stock-market-words.*`
- Repository: `/opt/stock-market-words/`
- Python venv: `/opt/stock-market-words/python3/venv/`
- Database: `/opt/stock-market-words/data/market_data.db`
- Logs: `journalctl -u stock-market-words.service`

## Architecture Notes

### Why systemd?

- **Reliability**: Automatic restarts on failure
- **Logging**: Centralized logging via journald
- **Scheduling**: Built-in timer support (no cron needed)
- **Resource control**: Memory and CPU limits
- **Dependencies**: Ensures network is available before running

### Why Oneshot Service Type?

The pipeline is a batch job that:
- Runs to completion (not a daemon)
- Should not restart automatically mid-run
- Produces discrete output files
- Is scheduled by a timer

The `Type=oneshot` is appropriate for these characteristics.

### Why Pushgateway for Metrics?

For batch jobs like this pipeline:
- Metrics need to persist after job completion
- No long-running HTTP server needed
- Simple integration with existing scheduled jobs
- Prometheus can scrape Pushgateway at its own interval

See [METRICS_PLAN.md](METRICS_PLAN.md) for full metrics implementation details.

## Contributing

When modifying these files:
1. Test changes in a VM or container first
2. Update SETUP.md with any new steps
3. Increment version in service file comments
4. Update this README with any new features

## License

Same as main repository.
