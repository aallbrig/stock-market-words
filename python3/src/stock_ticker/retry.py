"""
Exponential backoff retry logic with configurable limits.
"""
import time
from .config import BACKOFF_INITIAL_DELAY, BACKOFF_MAX_DELAY, BACKOFF_MULTIPLIER
from .logging_setup import setup_logging

logger = setup_logging()


class BackoffLimitExceeded(Exception):
    """Raised when backoff delay exceeds configured maximum."""
    pass


class RetryTracker:
    """
    Tracks retry attempts and calculates exponential backoff delays.
    
    Implements a per-topic backoff strategy where failures double the wait time.
    When successful requests occur, backoff resets to initial delay.
    """
    
    def __init__(self, max_delay=BACKOFF_MAX_DELAY):
        """
        Initialize retry tracker.
        
        Args:
            max_delay: Maximum backoff delay in seconds before giving up
        """
        self.max_delay = max_delay
        self.topic_delays = {}  # topic -> current delay
        self.topic_attempts = {}  # topic -> attempt count
    
    def record_failure(self, topic):
        """
        Record a failed request and calculate next delay.
        
        Args:
            topic: Identifier for the request type (e.g., 'yahoo_finance_batch', 'yahoo_finance_metadata:AAPL')
            
        Returns:
            float: Delay in seconds to wait before next attempt
            
        Raises:
            BackoffLimitExceeded: If delay would exceed max_delay
        """
        if topic not in self.topic_delays:
            self.topic_delays[topic] = BACKOFF_INITIAL_DELAY
            self.topic_attempts[topic] = 0
        
        current_delay = self.topic_delays[topic]
        self.topic_attempts[topic] += 1
        
        # Check if we've exceeded the limit
        if current_delay >= self.max_delay:
            logger.error(
                f"Backoff limit exceeded for {topic}: "
                f"{current_delay}s >= {self.max_delay}s after {self.topic_attempts[topic]} attempts"
            )
            raise BackoffLimitExceeded(
                f"Retry backoff exceeded {self.max_delay}s limit for {topic} "
                f"after {self.topic_attempts[topic]} attempts"
            )
        
        # Wait the current delay
        logger.warning(
            f"Rate limit/error on {topic} (attempt {self.topic_attempts[topic]}). "
            f"Waiting {current_delay:.1f}s before retry..."
        )
        time.sleep(current_delay)
        
        # Calculate next delay (exponential backoff)
        next_delay = min(current_delay * BACKOFF_MULTIPLIER, self.max_delay)
        self.topic_delays[topic] = next_delay
        
        return current_delay
    
    def record_success(self, topic):
        """
        Record a successful request, resetting backoff for this topic.
        
        Args:
            topic: Identifier for the request type
        """
        if topic in self.topic_delays:
            attempts = self.topic_attempts.get(topic, 0)
            if attempts > 0:
                logger.info(f"✓ Successful request to {topic} after {attempts} retries. Backoff reset.")
            del self.topic_delays[topic]
            del self.topic_attempts[topic]
    
    def reset(self, topic=None):
        """
        Reset backoff state for a specific topic or all topics.
        
        Args:
            topic: Topic to reset, or None to reset all
        """
        if topic is None:
            self.topic_delays.clear()
            self.topic_attempts.clear()
        elif topic in self.topic_delays:
            del self.topic_delays[topic]
            del self.topic_attempts[topic]
    
    def get_stats(self):
        """
        Get current retry statistics.
        
        Returns:
            dict: Statistics about current backoff state
        """
        return {
            'active_topics': len(self.topic_delays),
            'topics': {
                topic: {
                    'current_delay': delay,
                    'attempts': self.topic_attempts.get(topic, 0),
                    'next_delay': min(delay * BACKOFF_MULTIPLIER, self.max_delay)
                }
                for topic, delay in self.topic_delays.items()
            }
        }


class RequestMetrics:
    """
    Tracks API request counts by service and endpoint.
    
    Provides runtime statistics on external API usage.
    """
    
    def __init__(self):
        """Initialize request counter."""
        self.requests = {}  # (service, endpoint) -> count
    
    def record_request(self, service, endpoint='default'):
        """
        Record an API request.
        
        Args:
            service: Service name (e.g., 'yahoo_finance', 'nasdaq_ftp', 'database')
            endpoint: Specific endpoint or operation (e.g., 'healthcheck', 'download', 'batch_fetch')
        """
        key = (service, endpoint)
        self.requests[key] = self.requests.get(key, 0) + 1
    
    def get_counts(self):
        """
        Get request counts grouped by service.
        
        Returns:
            dict: Service -> {endpoint -> count}
        """
        result = {}
        for (service, endpoint), count in self.requests.items():
            if service not in result:
                result[service] = {}
            result[service][endpoint] = count
        return result
    
    def get_total(self, service=None):
        """
        Get total request count for a service or all services.
        
        Args:
            service: Service name, or None for grand total
            
        Returns:
            int: Request count
        """
        if service is None:
            return sum(self.requests.values())
        return sum(count for (srv, _), count in self.requests.items() if srv == service)
    
    def reset(self):
        """Reset all counters."""
        self.requests.clear()
    
    def summary(self):
        """
        Get a formatted summary of request metrics.
        
        Returns:
            str: Human-readable summary
        """
        counts = self.get_counts()
        lines = ["API Request Summary:"]
        for service in sorted(counts.keys()):
            total = sum(counts[service].values())
            lines.append(f"  {service}: {total:,} requests")
            for endpoint in sorted(counts[service].keys()):
                count = counts[service][endpoint]
                lines.append(f"    - {endpoint}: {count:,}")
        lines.append(f"  TOTAL: {self.get_total():,} requests")
        return "\n".join(lines)


# Global instances
_retry_tracker = None
_request_metrics = None


def get_retry_tracker():
    """Get or create global retry tracker instance."""
    global _retry_tracker
    if _retry_tracker is None:
        _retry_tracker = RetryTracker()
    return _retry_tracker


def get_request_metrics():
    """Get or create global request metrics instance."""
    global _request_metrics
    if _request_metrics is None:
        _request_metrics = RequestMetrics()
    return _request_metrics
