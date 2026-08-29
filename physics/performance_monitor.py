import time
from collections import defaultdict
from typing import Dict, List, Optional

class PerformanceMonitor:
    def __init__(self):
        self._timings: Dict[str, List[float]] = defaultdict(list)
        self._enabled = True
        self._start_times: Dict[str, float] = {}

    def record(self, label: str, duration: float) -> None:
        if not self._enabled:
            return
        self._timings[label].append(duration)

    def start(self, label: str) -> None:
        if not self._enabled:
            return
        self._start_times[label] = time.perf_counter()

    def stop(self, label: str) -> None:
        if not self._enabled:
            return
        if label not in self._start_times:
            return
        duration = time.perf_counter() - self._start_times[label]
        self.record(label, duration)
        del self._start_times[label]

    def get_stats(self, label: str) -> Optional[Dict]:
        if label not in self._timings or not self._timings[label]:
            return None
        data = self._timings[label]
        return {
            'count': len(data),
            'total': sum(data),
            'avg': sum(data) / len(data),
            'min': min(data),
            'max': max(data),
        }

    def clear(self) -> None:
        self._timings.clear()
        self._start_times.clear()

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def summary(self) -> Dict:
        return {k: self.get_stats(k) for k in self._timings}
