# Quick Reference: Stock Market Words Systemd Service

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

# Activate virtual environment
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

# Exit back to your user
exit
```

## Exit Codes

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

Check last exit code:
```bash
sudo systemctl show stock-market-words.service -p ExecMainStatus --value
```

## Troubleshooting

### Service won't start
```bash
# Check dependencies
sudo su - smw -c "cd /opt/stock-market-words/python3 && source venv/bin/activate && python -m stock_ticker.cli status"

# Check permissions
sudo chown -R smw:smw /opt/stock-market-words

# View errors
sudo journalctl -u stock-market-words.service -p err --since today
```

### Network issues
```bash
# Test FTP
telnet ftp.nasdaqtrader.com 21

# Test Yahoo Finance
curl -I https://query1.finance.yahoo.com

# Check network target
sudo systemctl status network-online.target
```

### Git push fails
```bash
# Test SSH
sudo su - smw -c "ssh -T git@github.com"

# Check remote
sudo su - smw -c "cd /opt/stock-market-words && git remote -v"

# Test push
sudo su - smw -c "cd /opt/stock-market-words && git push origin main"
```

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

## Configuration

### Change run time
```bash
sudo systemctl edit --full stock-market-words.timer
# Edit: OnCalendar=*-*-* 23:00:00
sudo systemctl daemon-reload
sudo systemctl restart stock-market-words.timer
```

### Adjust resources
```bash
sudo systemctl edit --full stock-market-words.service
# Edit: MemoryMax=4G, CPUQuota=200%, TimeoutStartSec=3600
sudo systemctl daemon-reload
```

### Disable auto-commit
```bash
sudo systemctl edit --full stock-market-words.service
# Comment out: # ExecStartPost=/opt/stock-market-words/systemd/scripts/git-commit-and-push.sh
sudo systemctl daemon-reload
```

## Schedule

- **Default**: Daily at 6PM EST (23:00 UTC)
- **On boot**: 5 minutes after startup if missed
- **Random delay**: ±5 minutes
- **Persistent**: Catches up if system was down

## Monitoring

```bash
# Is timer enabled?
systemctl is-enabled stock-market-words.timer

# When is next run?
systemctl list-timers stock-market-words.timer

# When was last run?
systemctl show stock-market-words.service -p ActiveEnterTimestamp

# How long did last run take?
journalctl -u stock-market-words.service --since "1 hour ago" | grep "PIPELINE COMPLETE"
```

## Full Documentation

- **Installation**: See `systemd/SETUP.md`
- **Architecture**: See `systemd/README.md`
- **Metrics Plan**: See `systemd/METRICS_PLAN.md`
- **Changes**: See `IMPLEMENTATION_SUMMARY.md`
