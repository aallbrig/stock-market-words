# VPN IP Rotation for Rate Limit Mitigation

**Status:** Draft
**Author:** aallbright
**Created:** 2026-04-17

## Context

The daily pipeline fetches ~3,000 tickers from Yahoo Finance via `yfinance`.
Yahoo uses IP-based rate limiting — no API key, no cookie fingerprinting.
When the pipeline hits a 429, the existing `RetryTracker` backs off
exponentially (0.5 s → 300 s max), then raises `BackoffLimitExceeded` and
the pipeline halts (idempotent resume on next run).

The always-on ThinkPad runs PIA (Private Internet Access) VPN, which ships
`piactl` — a CLI tool supporting `connect`, `disconnect`, `set region`,
`get vpnip`, and `get regions` (167 regions). Changing region gives a fresh
IP and genuinely resets Yahoo's rate-limit counter.

Related research: `docs/research/20260417_023220_UTC_vpn_ip_rotation.md`

## Goal

Two-layer VPN rotation: (1) a systemd timer rotates PIA IP proactively
before each pipeline run, and (2) the Python CLI rotates reactively when it
detects a 429 mid-run. Both layers degrade gracefully when `piactl` is
absent — logging warnings but never failing the pipeline for VPN reasons.

## Non-goals

- Replacing PIA with another VPN provider.
- Multi-VPN chaining or Tor integration.
- Handling non-429 Yahoo errors (already covered by existing retry logic).
- Scheduled VPN reconnection on weekends (pipeline doesn't run).

## User stories

- As the automation operator, I want the VPN IP to rotate before each
  pipeline run so that I start with a clean rate-limit slate.
- As the automation operator, I want the pipeline to automatically rotate
  VPN when it hits a 429 so that a single rate limit doesn't halt the run.
- As a developer without PIA, I want the pipeline to work identically
  (minus VPN rotation) with clear log messages explaining why rotation
  was skipped.

## Design

### Layer 1: Systemd timer — proactive rotation

New files in `systemd/system/`:

**`pia-rotate.service`**
```ini
[Unit]
Description=Rotate PIA VPN IP before stock pipeline
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/stock-market-words/systemd/scripts/pia-rotate.sh
TimeoutStartSec=60
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pia-rotate
```

**`pia-rotate.timer`**
```ini
[Unit]
Description=Rotate PIA VPN IP 30min before stock pipeline

[Timer]
OnCalendar=Mon..Fri *-*-* 22:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

New script: `systemd/scripts/pia-rotate.sh` — wraps `piactl` with logging,
connection verification, and graceful failure if PIA isn't installed.

The main `stock-market-words.service` gains `After=pia-rotate.service` so
systemd orders them correctly if both fire close together.

### Layer 2: Python module — reactive rotation on 429

New file: `python3/src/stock_ticker/vpn_rotator.py`

```python
class PiaVpnRotator:
    """Wraps piactl to rotate VPN IP on rate-limit detection."""
    
    def __init__(self, max_rotations=5):
        ...
    
    def is_available(self) -> bool:
        """True if piactl is installed and VPN is connected."""
        ...
    
    def rotate_ip(self) -> bool:
        """Disconnect, pick random region, reconnect. Returns success."""
        ...
    
    def should_rotate(self) -> bool:
        """False if max rotations exhausted."""
        ...
```

Integration points in `extractors.py`:
- `extract_prices()`: catch `BackoffLimitExceeded` → attempt VPN rotation →
  reset retry tracker → continue batch loop instead of re-raising.
- `extract_metadata()`: same pattern.

The rotator logs every action at INFO level (rotation attempts, new IP,
region selected) and every failure at ERROR level. If `piactl` is not
found, `is_available()` returns `False` and a single WARNING is logged
at module load time.

### Graceful degradation

| Condition | Behavior |
|-----------|----------|
| `piactl` not installed | `is_available()` → False, logs WARNING, backoff-only |
| PIA not connected | `is_available()` → False, logs WARNING, backoff-only |
| Rotation fails (timeout) | Logs ERROR, re-raises `BackoffLimitExceeded` |
| Max rotations exhausted | Logs WARNING, re-raises `BackoffLimitExceeded` |
| systemd timer, no PIA | `pia-rotate.sh` exits 0 with WARNING in journal |

## Affected files

| File | Action |
|------|--------|
| `systemd/system/pia-rotate.service` | **Create** |
| `systemd/system/pia-rotate.timer` | **Create** |
| `systemd/scripts/pia-rotate.sh` | **Create** |
| `systemd/system/stock-market-words.service` | Modify: add `After=pia-rotate.service` |
| `python3/src/stock_ticker/vpn_rotator.py` | **Create** |
| `python3/src/stock_ticker/extractors.py` | Modify: integrate VPN rotation on 429 |
| `systemd/README.md` | Update: document PIA rotation |
| `systemd/scripts/verify.sh` | Update: add PIA status check |
| `docs/specs/daily_automation.md` | Update: reference this spec |

## Verification

- **Unit:** `piactl` not installed → `PiaVpnRotator.is_available()` returns
  `False`, logs warning, no crash.
- **Manual on ThinkPad:**
  1. `systemctl start pia-rotate.service` → journal shows new IP.
  2. Run `ticker-cli run-all --limit 5` with VPN connected → logs show
     "VPN available" at startup.
  3. Simulate 429 (mock or natural) → logs show rotation attempt.
- **Shellcheck:** `shellcheck systemd/scripts/pia-rotate.sh` passes.
- **Timer calendar:** `systemd-analyze calendar "Mon..Fri *-*-* 22:30:00"`.

## Open questions

1. **Should rotation pick US-only regions?** Default: no, use `auto`
   (fastest). Yahoo doesn't geo-restrict. Can revisit if needed.

2. **Max rotations per run?** Default: 5. After 5 rotations in one pipeline
   run, assume systemic block and let `BackoffLimitExceeded` propagate.

## Alternatives considered

- **Tor exit nodes** — rejected: slow, unreliable, many exit IPs are
  already blocked by Yahoo.
- **Proxy rotation service (e.g., Bright Data)** — rejected: monthly cost,
  unnecessary when PIA is already available.
- **PIA Dedicated IP** — rejected: static IP is counterproductive for
  rate-limit evasion.
