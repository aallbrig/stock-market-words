"""
PIA VPN IP rotation for rate-limit mitigation.

Wraps the piactl CLI to rotate VPN IP addresses when Yahoo Finance
returns 429 rate-limit errors. Degrades gracefully when piactl is
not installed or PIA is not connected.
"""
import subprocess
import time
import random
from .logging_setup import setup_logging

logger = setup_logging()


class PiaVpnRotator:
    """Rotates PIA VPN IP address to mitigate rate limiting."""

    def __init__(self, max_rotations=5):
        self.max_rotations = max_rotations
        self.rotation_count = 0
        self._available = None  # cached after first check

    def is_available(self) -> bool:
        """Check if piactl is installed and VPN is connected."""
        if self._available is not None:
            return self._available

        try:
            result = subprocess.run(
                ['piactl', 'get', 'connectionstate'],
                capture_output=True, text=True, timeout=5
            )
            connected = 'Connected' in result.stdout
            if not connected:
                logger.warning(
                    f"PIA VPN not connected (state: {result.stdout.strip()}). "
                    "VPN rotation disabled — falling back to backoff-only."
                )
            else:
                ip = self._get_vpnip()
                logger.info(f"PIA VPN available (IP: {ip}). VPN rotation enabled.")
            self._available = connected
            return connected
        except FileNotFoundError:
            logger.warning(
                "piactl not found — PIA VPN is not installed. "
                "VPN rotation disabled — falling back to backoff-only."
            )
            self._available = False
            return False
        except subprocess.TimeoutExpired:
            logger.warning("piactl timed out. VPN rotation disabled.")
            self._available = False
            return False
        except Exception as e:
            logger.warning(f"piactl check failed: {e}. VPN rotation disabled.")
            self._available = False
            return False

    def should_rotate(self) -> bool:
        """Check if rotation is feasible (available + under limit)."""
        if not self.is_available():
            return False
        if self.rotation_count >= self.max_rotations:
            logger.warning(
                f"VPN rotation limit reached ({self.rotation_count}/{self.max_rotations}). "
                "No more rotations this run."
            )
            return False
        return True

    def rotate_ip(self) -> bool:
        """Disconnect, pick a random region, reconnect. Returns True on success."""
        if not self.should_rotate():
            return False

        old_ip = self._get_vpnip()

        try:
            # Get available regions
            result = subprocess.run(
                ['piactl', 'get', 'regions'],
                capture_output=True, text=True, timeout=10, check=True
            )
            regions = [
                r.strip() for r in result.stdout.split('\n')
                if r.strip() and r.strip() != 'auto'
            ]

            if not regions:
                logger.error("No PIA regions available")
                return False

            new_region = random.choice(regions)
            logger.info(f"VPN rotating to region: {new_region}")

            # Disconnect
            subprocess.run(['piactl', 'disconnect'], timeout=15,
                           capture_output=True)
            time.sleep(2)

            # Set region and connect
            subprocess.run(['piactl', 'set', 'region', new_region],
                           timeout=10, check=True, capture_output=True)
            subprocess.run(['piactl', 'connect'], timeout=30, check=True,
                           capture_output=True)

            # Wait for connection (up to 30s)
            for _ in range(30):
                state = self._get_connection_state()
                if 'Connected' in state:
                    self.rotation_count += 1
                    new_ip = self._get_vpnip()
                    logger.info(
                        f"✓ VPN rotated: {old_ip} → {new_ip} "
                        f"(region: {new_region}) "
                        f"[{self.rotation_count}/{self.max_rotations}]"
                    )
                    return True
                time.sleep(1)

            logger.error(
                f"VPN rotation timeout: could not reconnect after 30s "
                f"(region: {new_region})"
            )
            return False

        except Exception as e:
            logger.error(f"VPN rotation failed: {e}")
            return False

    def reset(self):
        """Reset rotation counter (e.g., between pipeline steps)."""
        self.rotation_count = 0

    def _get_vpnip(self) -> str:
        """Get current VPN IP address."""
        try:
            result = subprocess.run(
                ['piactl', 'get', 'vpnip'],
                capture_output=True, text=True, timeout=5
            )
            ip = result.stdout.strip()
            return ip if ip.lower() != 'unknown' else 'unknown'
        except Exception:
            return 'unknown'

    def _get_connection_state(self) -> str:
        """Get current VPN connection state."""
        try:
            result = subprocess.run(
                ['piactl', 'get', 'connectionstate'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return 'Unknown'


# Global instance
_rotator = None


def get_vpn_rotator() -> PiaVpnRotator:
    """Get or create global VPN rotator instance."""
    global _rotator
    if _rotator is None:
        _rotator = PiaVpnRotator(max_rotations=5)
    return _rotator
