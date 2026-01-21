# Stock Market Words - Systemd Service Setup

This document provides step-by-step instructions for setting up the Stock Market Words data pipeline as a systemd service that runs daily at 6PM EST.

## Overview

The systemd service will:
- Run the full data pipeline daily at 6PM EST (23:00 UTC)
- Automatically commit and push changes to git (if configured)
- Log all output to systemd journal (view with `journalctl`)
- Handle failures gracefully with automatic retries
- Check system dependencies before running

## Prerequisites

Before setting up the service, ensure you have:
- A Linux system with systemd (Ubuntu, Debian, CentOS, RHEL, etc.)
- Python 3.8 or higher
- Git installed
- Network access to NASDAQ FTP and Yahoo Finance API

## Installation Steps

### 1. Create Service User

Create a dedicated user to run the service:

```bash
sudo useradd -r -s /bin/bash -d /opt/stock-market-words -m smw
```

### 2. Clone Repository

Clone the repository to `/opt/stock-market-words`:

```bash
sudo mkdir -p /opt
sudo git clone https://github.com/YOUR_USERNAME/stock-market-words.git /opt/stock-market-words
sudo chown -R smw:smw /opt/stock-market-words
```

### 3. Set Up Python Virtual Environment

```bash
sudo su - smw
cd /opt/stock-market-words/python3

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
python -m stock_ticker.cli init

# Test the CLI
python -m stock_ticker.cli status

# Exit back to your user
exit
```

### 4. Configure Git for Auto-Commit (Optional)

If you want the service to automatically commit and push changes:

#### 4a. Generate SSH Key for Service User

```bash
sudo su - smw
ssh-keygen -t ed25519 -C "smw@$(hostname)" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
# Copy this public key to add to GitHub
exit
```

#### 4b. Add SSH Key to GitHub

1. Go to GitHub Settings → SSH and GPG keys
2. Click "New SSH key"
3. Give it a descriptive title (e.g., "Home Server - Stock Market Words")
4. Paste the public key from the previous step
5. Click "Add SSH key"

#### 4c. Configure Git Remote

```bash
sudo su - smw
cd /opt/stock-market-words

# Change remote to SSH (if currently using HTTPS)
git remote set-url origin git@github.com:YOUR_USERNAME/stock-market-words.git

# Test SSH connection
ssh -T git@github.com

# Test push (should work without password)
git push origin main

exit
```

### 5. Install Systemd Service Files

```bash
# Copy service files to systemd directory
sudo cp /opt/stock-market-words/systemd/system/stock-market-words.service /etc/systemd/system/
sudo cp /opt/stock-market-words/systemd/system/stock-market-words.timer /etc/systemd/system/

# Make the git commit script executable
sudo chmod +x /opt/stock-market-words/systemd/scripts/git-commit-and-push.sh

# Reload systemd to recognize new services
sudo systemctl daemon-reload
```

### 6. Enable and Start the Timer

```bash
# Enable the timer to start on boot
sudo systemctl enable stock-market-words.timer

# Start the timer
sudo systemctl start stock-market-words.timer

# Check timer status
sudo systemctl status stock-market-words.timer

# List all timers to see when next run is scheduled
sudo systemctl list-timers stock-market-words.timer
```

## Usage

### Manual Run

To run the pipeline manually (without waiting for the timer):

```bash
sudo systemctl start stock-market-words.service
```

### Check Status

```bash
# Check timer status (when will it run next?)
sudo systemctl status stock-market-words.timer

# Check service status (is it currently running?)
sudo systemctl status stock-market-words.service

# Check last run details
sudo systemctl status stock-market-words.service --no-pager -l
```

### View Logs

```bash
# View all logs for the service
sudo journalctl -u stock-market-words.service

# View logs from today
sudo journalctl -u stock-market-words.service --since today

# View logs from the last run
sudo journalctl -u stock-market-words.service --since "1 hour ago"

# Follow logs in real-time (useful during manual run)
sudo journalctl -u stock-market-words.service -f

# View logs with priority (errors only)
sudo journalctl -u stock-market-works.service -p err

# Export logs to file
sudo journalctl -u stock-market-words.service --since today > pipeline-logs.txt
```

### Run CLI Directly

As the service user:

```bash
sudo su - smw
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

## Troubleshooting

### Service Won't Start

1. **Check Python dependencies:**
   ```bash
   sudo su - smw
   cd /opt/stock-market-words/python3
   source venv/bin/activate
   python -m stock_ticker.cli status
   ```
   
   If dependencies are missing:
   ```bash
   pip install -r requirements.txt
   ```

2. **Check database initialization:**
   ```bash
   python -m stock_ticker.cli init
   ```

3. **Check file permissions:**
   ```bash
   sudo chown -R smw:smw /opt/stock-market-words
   ```

### Network Connectivity Issues

If the service reports FTP or Yahoo Finance as unreachable:

```bash
# Test FTP connectivity
telnet ftp.nasdaqtrader.com 21

# Test Yahoo Finance connectivity
curl -I https://query1.finance.yahoo.com

# Check network status
sudo systemctl status network-online.target
```

### Service Fails to Commit/Push

If git push fails:

1. **Verify SSH key is added to GitHub:**
   ```bash
   sudo su - smw
   ssh -T git@github.com
   ```

2. **Check git configuration:**
   ```bash
   cd /opt/stock-market-words
   git remote -v
   git config --list
   ```

3. **Test manual push:**
   ```bash
   git push origin main
   ```

### Check Exit Codes

The CLI uses specific exit codes to indicate different failure modes:

- **0**: Success
- **1**: Pipeline needs to run
- **2**: Missing Python dependencies
- **3**: Database not initialized
- **4**: External services unreachable (FTP or Yahoo Finance)
- **5**: Pipeline interrupted
- **6**: Pipeline failed
- **7**: Pipeline partially complete

View exit code from last run:
```bash
sudo systemctl show stock-market-words.service -p ExecMainStatus --value
```

## Configuration

### Change Run Time

To change when the pipeline runs, edit the timer file:

```bash
sudo systemctl edit --full stock-market-words.timer
```

Change the `OnCalendar` line:
```ini
OnCalendar=*-*-* 23:00:00  # 6PM EST (23:00 UTC)
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart stock-market-words.timer
```

### Adjust Resource Limits

Edit the service file to adjust memory or CPU limits:

```bash
sudo systemctl edit --full stock-market-words.service
```

Modify:
```ini
MemoryMax=4G      # Maximum memory
CPUQuota=200%     # Maximum CPU (200% = 2 cores)
TimeoutStartSec=3600  # Maximum runtime (1 hour)
```

### Disable Auto-Commit

To disable automatic git commits, edit the service file:

```bash
sudo systemctl edit --full stock-market-words.service
```

Comment out the ExecStartPost line:
```ini
# ExecStartPost=/opt/stock-market-words/systemd/scripts/git-commit-and-push.sh
```

Then reload:
```bash
sudo systemctl daemon-reload
```

## Monitoring

### Check Timer Schedule

```bash
# See when the next run is scheduled
sudo systemctl list-timers stock-market-words.timer

# Output shows:
# NEXT                         LEFT          LAST                         PASSED  UNIT
# Tue 2024-01-20 23:00:00 UTC  8h left       Mon 2024-01-19 23:00:00 UTC  15h ago stock-market-words.timer
```

### Monitor Service Health

Create a simple monitoring script:

```bash
#!/bin/bash
# /opt/stock-market-words/systemd/scripts/check-health.sh

cd /opt/stock-market-words/python3
source venv/bin/activate

python -m stock_ticker.cli status
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Pipeline healthy"
elif [ $EXIT_CODE -eq 1 ]; then
    echo "⚠ Pipeline needs to run"
elif [ $EXIT_CODE -eq 4 ]; then
    echo "❌ Network connectivity issues"
else
    echo "❌ Pipeline has issues (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
```

### Email Notifications on Failure

To get email notifications when the service fails, install a monitoring tool like `systemd-mail` or configure `OnFailure` in the service file.

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

## Security Notes

1. **Service User**: The service runs as a dedicated `smw` user with limited privileges
2. **SSH Key**: Keep the SSH private key secure; it only has access to this one repository
3. **Resource Limits**: Memory and CPU limits prevent runaway processes
4. **Network**: The service only connects to public APIs (NASDAQ FTP, Yahoo Finance)

## Support

For issues or questions:
- Check logs: `sudo journalctl -u stock-market-words.service`
- Run status: `python -m stock_ticker.cli status` (as smw user)
- GitHub Issues: https://github.com/YOUR_USERNAME/stock-market-words/issues
