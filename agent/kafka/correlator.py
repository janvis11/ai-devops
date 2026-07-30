# agent/kafka/correlator.py
# EventCorrelator — groups Kafka events by pod_name within a time window.
# Prevents duplicate investigations for the same pod.

import time
import logging
from collections import defaultdict
from threading import Lock

from agent.config import cfg

logger = logging.getLogger(__name__)


class EventCorrelator:
    """
    Correlates Alertmanager events + K8s events by pod_name within a sliding
    time window. Also deduplicates: once a pod is being investigated,
    further events for that pod are ignored until the window expires.
    """

    def __init__(
        self,
        correlation_window: int | None = None,
        dedup_window: int | None = None,
    ):
        self.correlation_window = correlation_window or cfg.correlation_window_seconds
        self.dedup_window = dedup_window or cfg.dedup_window_seconds
        self._buffer: dict[str, list[dict]] = defaultdict(list)
        self._active: dict[str, float] = {}   # pod_name → investigation start time
        self._lock = Lock()

    def add(self, topic: str, event: dict) -> None:
        """Add an event to the correlation buffer."""
        pod = event.get("pod_name", "unknown")
        with self._lock:
            self._buffer[pod].append({
                "topic": topic,
                "event": event,
                "ts": time.time(),
            })
            self._evict_old()

    def should_investigate(self, pod_name: str) -> bool:
        """
        Returns True if this pod should trigger a new investigation.
        False if already under investigation (dedup) or recently investigated.
        """
        with self._lock:
            last = self._active.get(pod_name, 0)
            if time.time() - last < self.dedup_window:
                logger.debug(
                    f"[correlator] Dedup: pod={pod_name} already investigated "
                    f"{int(time.time() - last)}s ago"
                )
                return False
            self._active[pod_name] = time.time()
            return True

    def get_correlated(self, pod_name: str) -> list[dict]:
        """Return all events for a pod within the correlation window."""
        with self._lock:
            cutoff = time.time() - self.correlation_window
            return [
                e for e in self._buffer.get(pod_name, [])
                if e["ts"] >= cutoff
            ]

    def mark_resolved(self, pod_name: str) -> None:
        """Clear the active investigation for a pod (after verify completes)."""
        with self._lock:
            self._active.pop(pod_name, None)

    def _evict_old(self) -> None:
        """Remove events older than 2x the correlation window."""
        cutoff = time.time() - self.correlation_window * 2
        for pod in list(self._buffer.keys()):
            self._buffer[pod] = [
                e for e in self._buffer[pod] if e["ts"] >= cutoff
            ]
            if not self._buffer[pod]:
                del self._buffer[pod]

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "buffered_pods": len(self._buffer),
                "active_investigations": len(self._active),
                "total_buffered_events": sum(len(v) for v in self._buffer.values()),
            }


# Global singleton
correlator = EventCorrelator()
