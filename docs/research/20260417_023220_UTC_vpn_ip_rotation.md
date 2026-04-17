# Research: VPN IP Rotation for Yahoo Finance Rate Limits

**Date:** 2026-04-17
**Context:** The pipeline fetches ~3,000 tickers from Yahoo Finance daily,
hitting 429 rate limits partway through. PIA (Private Internet Access) VPN
is in use. Can we rotate IPs to mitigate?

---

## How Yahoo Finance Rate-Limits

Yahoo Finance uses **IP-based rate limiting** — no API key, no cookie
fingerprinting. The `yfinance` library makes unauthenticated HTTP requests.
A 429 means "too many requests from this IP." Changing IP genuinely resets
the counter.

**Current pipeline behavior on 429:** exponential backoff (0.5 s → doubling
→ cap at 300 s), then `BackoffLimitExceeded` halts the step. Pipeline is
idempotent and resumes on re-run, but may take multiple runs to complete.

---

## Three Approaches

### 1. Scheduled VPN rotation (proactive — recommended Tier 1)

Rotate IP 30 min before the pipeline runs. Simplest, no code changes.

PIA ships `piactl` on Linux:

```bash
piactl disconnect
sleep 2
piactl set region auto    # auto-selects fastest; or pick a region
piactl connect
```

PIA has **167 regions**. Setting `auto` or a random region each day gives a
fresh IP before the pipeline starts.

**Implementation:** systemd timer at 22:30 UTC (30 min before pipeline):

```ini
# /etc/systemd/system/pia-rotate.service
[Unit]
Description=Rotate PIA VPN IP
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/piactl disconnect
ExecStart=/bin/sleep 2
ExecStart=/usr/local/bin/piactl set region auto
ExecStart=/usr/local/bin/piactl connect
TimeoutStartSec=60
```

```ini
# /etc/systemd/system/pia-rotate.timer
[Unit]
Description=Daily PIA IP rotation (before pipeline)

[Timer]
OnCalendar=Mon..Fri *-*-* 22:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Pros:** Zero code changes, simple, proactive.
**Cons:** Doesn't help if 429 hits mid-run.

### 2. Dynamic VPN rotation on 429 (reactive — recommended Tier 2)

When the pipeline detects a 429, invoke `piactl` to rotate to a new region
and retry. This extends the existing `RetryTracker` in `retry.py`.

**New file: `python3/src/stock_ticker/vpn_rotator.py`**

```python
import subprocess
import time
import random
from .logging_setup import setup_logging

logger = setup_logging()

class PiaVpnRotator:
    def __init__(self, max_rotations=5):
        self.max_rotations = max_rotations
        self.rotation_count = 0

    def is_available(self) -> bool:
        """Check if piactl is installed and VPN is connected."""
        try:
            r = subprocess.run(['piactl', 'get', 'connectionstate'],
                             capture_output=True, text=True, timeout=5)
            return 'Connected' in r.stdout
        except FileNotFoundError:
            return False

    def rotate_ip(self) -> bool:
        """Disconnect, pick random region, reconnect."""
        if self.rotation_count >= self.max_rotations:
            logger.warning(f"VPN rotation limit reached ({self.max_rotations})")
            return False
        try:
            regions = subprocess.run(
                ['piactl', 'get', 'regions'],
                capture_output=True, text=True, timeout=5, check=True
            ).stdout.strip().split('\n')
            region = random.choice([r for r in regions if r.strip() and r != 'auto'])

            subprocess.run(['piactl', 'disconnect'], timeout=15)
            time.sleep(2)
            subprocess.run(['piactl', 'set', 'region', region], timeout=10, check=True)
            subprocess.run(['piactl', 'connect'], timeout=30, check=True)

            for _ in range(20):
                state = subprocess.run(
                    ['piactl', 'get', 'connectionstate'],
                    capture_output=True, text=True, timeout=5
                ).stdout.strip()
                if 'Connected' in state:
                    ip = subprocess.run(
                        ['piactl', 'get', 'vpnip'],
                        capture_output=True, text=True, timeout=5
                    ).stdout.strip()
                    self.rotation_count += 1
                    logger.info(f"✓ VPN rotated: {region} ({ip}) [{self.rotation_count}/{self.max_rotations}]")
                    return True
                time.sleep(1)
            return False
        except Exception as e:
            logger.error(f"VPN rotation failed: {e}")
            return False
```

**Integration in `extractors.py`:** after `BackoffLimitExceeded`, check
`vpn_rotator.is_available()` → `rotate_ip()` → reset backoff → retry batch.

**Pros:** Handles mid-run 429s automatically.
**Cons:** ~10–30 s latency per rotation; needs `piactl` on host.

### 3. PIA Dedicated IP (not recommended)

PIA offers dedicated IPs ($5/mo extra). A static IP is the **opposite** of
what we want — Yahoo would permanently associate rate-limit state with it.
Dedicated IPs help with allowlisting, not with evading rate limits.

---

## Comparison

| | Scheduled (1) | Dynamic (2) | Dedicated IP (3) |
|---|---|---|---|
| Implementation | systemd timer only | Python + subprocess | PIA subscription |
| Triggers on 429 | No (proactive) | Yes (reactive) | N/A |
| Code changes | None | New module + extractor hooks | None |
| Effectiveness | Prevents ~60% of 429s | Handles ~80%+ of 429s | Counterproductive |
| Cost | $0 | $0 | $5/mo |
| **Recommendation** | ✅ Do first | ✅ Do second | ❌ Skip |

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| DNS leak during reconnect | PIA kill switch (`piactl set killswitch on`) |
| Concurrent rotation in threaded code | `threading.Lock` around `piactl` calls |
| `piactl` not installed on target | `vpn_rotator.is_available()` returns `False`, falls back to pure backoff |
| Yahoo fingerprints beyond IP | Unlikely for unauthenticated requests; `yfinance` sets standard User-Agent |

## Recommended Rollout

1. **Now:** Add `pia-rotate.timer` to systemd files in repo (Approach 1)
2. **Next sprint:** Implement `vpn_rotator.py` module (Approach 2)
3. **Tuning:** Reduce `BACKOFF_MAX_DELAY` from 300 s to 60 s; let VPN rotation handle persistent 429s instead of long waits

## One-Time Setup on ThinkPad

```bash
piactl background enable          # Allow headless operation
piactl set killswitch on          # Prevent DNS leaks during rotation
sudo systemctl enable --now pia-rotate.timer
```
