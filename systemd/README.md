# Stock Market Words - Systemd Service

Complete guide for setting up and managing the Stock Market Words data pipeline as a systemd service.

## Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Common Commands](#common-commands)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)

---

## Overview

The systemd service automatically runs the Stock Market Words data pipeline daily at 6PM EST. It:

- **Runs daily at 6PM EST** (23:00 UTC) via systemd timer
- **Fetches stock data** from NASDAQ FTP and Yahoo Finance
- **Calculates strategy scores** for all tickers
- **Generates Hugo site content** with updated data
- **Commits and pushes changes** to git (optional)
- **Logs everything** to systemd journal
- **Handles failures** gracefully with automatic retries

### What It Does

1. Downloads ticker lists from NASDAQ FTP
2. Fetches price/volume data for ~8,000 tickers
3. Filters to ~3,000 liquid stocks (price ≥ $5, volume ≥ 100k)
4. Fetches detailed metrics (market cap, dividend yield, beta, RSI, MA-200)
5. Calculates strategy scores for multiple strategies
6. Generates Hugo static site content
7. Commits and pushes to git repository

### Resource Limits

- **Memory**: 4GB maximum
- **CPU**: 200% (2 cores)
- **Timeout**: 1 hour (3600 seconds)
- **Typical runtime**: 30-45 minutes

---

## Quick Start

### Installation

```bash
# 1. Create service user
sudo useradd -r -s /bin/bash -d /opt/stock-market-words -m smw

# 2. Clone repository
sudo git clone https://github.com/YOUR_USERNAME/stock-market-words.git /opt/stock-market-words
sudo chown -R smw:smw /opt/stock-market-words

# 3. Set up Python environment
sudo su - smw
cd /opt/stock-market-words/python3
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m stock_ticker.cli init
exit

# 4. Install systemd files
sudo cp /opt/stock-market-words/systemd/system/*.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload

# 5. Enable and start
sudo systemctl enable --now stock-market-words.timer
```

### Basic Usage

```bash
# Run pipeline manually
sudo systemctl start stock-market-words.service

# Check timer status
sudo systemctl status stock-market-words.timer

# View logs
sudo journalctl -u stock-market-words.service -f

# See when next run is scheduled
sudo systemctl list-timers stock-market-words.timer
```

---

## Installation

### Prerequisites

- Linux system with systemd (Ubuntu, Debian, CentOS, RHEL, etc.)
- Python 3.8 or higher
- Git installed
- Network access to NASDAQ FTP and Yahoo Finance API

### Step 1: Create Service User

Create a dedicated user to run the service:

```bash
sudo useradd -r -s /bin/bash -d /opt/stock-market-words -m smw
```

### Step 2: Clone Repository

```bash
sudo mkdir -p /opt
sudo git clone https://github.com/YOUR_USERNAME/stock-market-words.git /opt/stock-market-words
sudo chown -R smw:smw /opt/stock-market-words
```

### Step 3: Set Up Python Virtual Environment

```bash
sudo su - smw
cd /opt/stock-market-words/python3

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
python -m stock_ticker.cli init

# Test the CLI
python -m stock_ticker.cli status

exit
```

### Step 4: Configure Git for Auto-Commit (Optional)

If you want automatic git commits and pushes:

#### Generate SSH Key

```bash
sudo su - smw
ssh-keygen -t ed25519 -C "smw@$(hostname)" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
# Copy this public key
exit
```

#### Add SSH Key to GitHub

1. Go to GitHub Settings → SSH and GPG keys
2. Click "New SSH key"
3. Paste the public key
4. Click "Add SSH key"

#### Configure Git Remote

```bash
sudo su - smw
cd /opt/stock-market-words

# Change remote to SSH
git remote set-url origin git@github.com:YOUR_USERNAME/stock-market-words.git

# Test SSH connection
ssh -T git@github.com

# Test push
git push origin main

exit
```

### Step 5: Install Systemd Service Files

```bash
# Copy service files
sudo cp /opt/stock-market-words/systemd/system/stock-market-words.service /etc/systemd/system/
sudo cp /opt/stock-market-words/systemd/system/stock-market-words.timer /etc/systemd/system/

# Make git script executable
sudo chmod +x /opt/stock-market-words/systemd/scripts/git-commit-and-push.sh

# Reload systemd
sudo systemctl daemon-reload
```

### Step 6: Enable and Start the Timer

```bash
# Enable timer to start on boot
sudo systemctl enable stock-market-words.timer

# Start timer
sudo systemctl start stock-market-words.timer

# Check status
sudo systemctl status stock-market-words.timer

# See when next run is scheduled
sudo systemctl list-timers stock-market-words.timer
```

---

## Common Commands

### Service Management

```bash
# Start manually
sudo systemctl start stock-market-words.service

# Stop if running
sudo systemctl stop stock-market-words.service

# Check service status
sudo systemctl status stock-market-words.service

# View full output
sudo systemctl status stock-market-words.service --no-pager -l
```

### Timer Management

```bash
# Enable timer (start on boot)
sudo systemctl enable stock-market-words.timer

# Start timer
sudo systemctl start stock-market-words.timer

# Check timer status
sudo systemctl status stock-market-words.timer

# See when next run is scheduled
sudo systemctl list-timers stock-market-words.timer

# Disable timer
sudo systemctl disable stock-market-words.timer

# Stop timer
sudo systemctl stop stock-market-words.timer
```

### Log Viewing

```bash
# View recent logs
sudo journalctl -u stock-market-words.service -n 100

# Follow logs in real-time
sudo journalctl -u stock-market-words.service -f

# View today's logs
sudo journalctl -u stock-market-words.service --since today

# View logs from last hour
sudo journalctl -u stock-market-words.service --since "1 hour ago"

# View only errors
sudo journalctl -u stock-market-words.service -p err

# Export logs to file
sudo journalctl -u stock-market-words.service --since today > pipeline-logs.txt
```

### Direct CLI Usage

```bash
# Switch to service user
sudo su - smw

# Navigate to directory
cd /opt/stock-market-words/python3
source venv/bin/activate

# Check status
python -m stock_ticker.cli status

# Run full pipeline
python -m stock_ticker.cli run-all

# Run individual steps
python -m stock_ticker.cli sync-ftp
python -m stock_ticker.cli extract-prices
python -m stock_ticker.cli extract-metadata
python -m stock_ticker.cli build
python -m stock_ticker.cli hugo all

# Reset today's data
python -m stock_ticker.cli reset

exit
```

---

## Configuration

### Change Run Time

Edit the timer to change when the pipeline runs:

```bash
sudo systemctl edit --full stock-market-words.timer
```

Modify the `OnCalendar` line:
```ini
OnCalendar=*-*-* 23:00:00  # UTC time (6PM EST)
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

### Adjust Resource Limits

Edit the service file:

```bash
sudo systemctl edit --full stock-market-words.service
```

Modify:
```ini
MemoryMax=4G          # Maximum memory
CPUQuota=200%         # Maximum CPU (200% = 2 cores)
TimeoutStartSec=3600  # Maximum runtime (1 hour)
```

Then reload:
```bash
sudo systemctl daemon-reload
```

### Disable Auto-Commit

To disable automatic git commits:

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

### Configure Backoff Limits

The pipeline uses exponential backoff for rate limiting. Edit config:

```bash
sudo su - smw
cd /opt/stock-market-words/python3
nano src/stock_ticker/config.py
```

Adjust these values:
```python
BACKOFF_INITIAL_DELAY = 0.5   # Starting delay (seconds)
BACKOFF_MAX_DELAY = 300        # Max delay before giving up (5 minutes)
BACKOFF_MULTIPLIER = 2.0       # Exponential multiplier
```

---

## Monitoring

### Check Timer Schedule

```bash
# See when the next run is scheduled
sudo systemctl list-timers stock-market-words.timer

# Output shows:
# NEXT                         LEFT          LAST                         PASSED
# Tue 2024-01-20 23:00:00 UTC  8h left       Mon 2024-01-19 23:00:00 UTC  15h ago
```

### Monitor Service Health

```bash
# Is timer enabled?
systemctl is-enabled stock-market-words.timer

# When was last run?
systemctl show stock-market-words.service -p ActiveEnterTimestamp

# Check last exit code
sudo systemctl show stock-market-words.service -p ExecMainStatus --value
```

### Exit Codes

The CLI uses specific exit codes for different failure modes:

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | All good |
| 1 | Needs to run | Normal state |
| 2 | Missing deps | `pip install -r requirements.txt` |
| 3 | DB not ready | `python -m stock_ticker.cli init` |
| 4 | Services unreachable | Check network |
| 5 | Interrupted | Resume with `run-all` |
| 6 | Failed | Check logs |
| 7 | Partial | Resume with `run-all` |

---

## Troubleshooting

### Service Won't Start

1. **Check dependencies:**
   ```bash
   sudo su - smw -c "cd /opt/stock-market-words/python3 && source venv/bin/activate && python -m stock_ticker.cli status"
   ```
   
   If dependencies are missing:
   ```bash
   sudo su - smw
   cd /opt/stock-market-words/python3
   source venv/bin/activate
   pip install -r requirements.txt
   exit
   ```

2. **Check database initialization:**
   ```bash
   sudo su - smw -c "cd /opt/stock-market-words/python3 && source venv/bin/activate && python -m stock_ticker.cli init"
   ```

3. **Check file permissions:**
   ```bash
   sudo chown -R smw:smw /opt/stock-market-words
   ```

4. **View errors:**
   ```bash
   sudo journalctl -u stock-market-words.service -p err --since today
   ```

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
# Test SSH
sudo su - smw -c "ssh -T git@github.com"

# Check remote
sudo su - smw -c "cd /opt/stock-market-words && git remote -v"

# Test push
sudo su - smw -c "cd /opt/stock-market-words && git push origin main"
```

### Rate Limiting Issues

If you see "Backoff limit exceeded" errors:

1. **Increase backoff limit:**
   Edit `/opt/stock-market-words/python3/src/stock_ticker/config.py`:
   ```python
   BACKOFF_MAX_DELAY = 600  # Increase to 10 minutes
   ```

2. **Re-run pipeline:**
   The pipeline is idempotent - just run again:
   ```bash
   sudo systemctl start stock-market-words.service
   ```

3. **Check error logs:**
   ```bash
   sudo journalctl -u stock-market-words.service | grep -i "backoff\|rate limit"
   ```

---

## Architecture

### Why systemd?

- **Reliability**: Automatic restarts on failure
- **Logging**: Centralized logging via journald
- **Scheduling**: Built-in timer support (no cron needed)
- **Resource control**: Memory and CPU limits
- **Dependencies**: Ensures network is available before running

### Service Type

The pipeline uses `Type=oneshot` because it:
- Runs to completion (not a daemon)
- Should not restart automatically mid-run
- Produces discrete output files
- Is scheduled by a timer

### Execution Schedule

- **Default**: Daily at 6PM EST (23:00 UTC)
- **On boot**: Runs 5 minutes after system startup if missed
- **Randomization**: ±5 minutes to avoid load spikes
- **Persistent**: Catches up if system was down

### Exponential Backoff

The pipeline implements exponential backoff for rate limiting:

1. **Initial delay**: 0.5 seconds
2. **On failure**: Double the delay (0.5s → 1s → 2s → 4s → ...)
3. **Max delay**: 5 minutes (configurable)
4. **On success**: Reset to initial delay
5. **Per-topic**: Separate backoff for each API/ticker
6. **Idempotent**: Safe to re-run after hitting limit

### Request Metrics

The pipeline tracks all API requests:

- **NASDAQ FTP**: connect, download, healthcheck
- **Yahoo Finance**: batch_download, ticker_info, ticker_history, healthcheck
- **Database**: queries and updates

Metrics are logged at the end of each run.

---

## File Locations

| Item | Path |
|------|------|
| Service file | `/etc/systemd/system/stock-market-words.service` |
| Timer file | `/etc/systemd/system/stock-market-words.timer` |
| Repository | `/opt/stock-market-words/` |
| Virtual env | `/opt/stock-market-words/python3/venv/` |
| Database | `/opt/stock-market-words/data/market_data.db` |
| Logs | `journalctl -u stock-market-words.service` |
| Git script | `/opt/stock-market-words/systemd/scripts/git-commit-and-push.sh` |
| Metrics plan | `/opt/stock-market-words/METRICS_PLAN.md` |

---

## Uninstallation

To completely remove the service:

```bash
# Stop and disable timer
sudo systemctl stop stock-market-words.timer
sudo systemctl disable stock-market-words.timer

# Remove service files
sudo rm /etc/systemd/system/stock-market-words.service
sudo rm /etc/systemd/system/stock-market-words.timer

# Reload systemd
sudo systemctl daemon-reload

# Optionally remove repository and user
sudo rm -rf /opt/stock-market-words
sudo userdel -r smw
```

---

## Security Notes

1. **Service User**: Runs as dedicated `smw` user with limited privileges
2. **SSH Key**: Only has access to this one repository
3. **Resource Limits**: Memory and CPU limits prevent runaway processes
4. **Network**: Only connects to public APIs (NASDAQ FTP, Yahoo Finance)

---

## Support

For issues or questions:
- **Check logs**: `sudo journalctl -u stock-market-words.service`
- **Run status**: `python -m stock_ticker.cli status` (as smw user)
- **GitHub Issues**: https://github.com/YOUR_USERNAME/stock-market-words/issues
- **Metrics Plan**: See `/opt/stock-market-words/METRICS_PLAN.md`

---

## Related Documentation

- **Metrics Implementation**: `/opt/stock-market-words/METRICS_PLAN.md`
- **Testing Guide**: `/opt/stock-market-words/TESTING.md`
- **Main README**: `/opt/stock-market-words/README.md`
