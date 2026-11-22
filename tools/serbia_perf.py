"""Best-effort, bounded page-cache warming for the small Serbia host."""
from pathlib import Path
import subprocess
import time

MIB = 1024 * 1024


def available_budget():
    """Preserve host and container headroom; skip warming if it cannot be measured."""
    try:
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                             if line.startswith('MemAvailable:'))) * 1024
        limit = Path('/sys/fs/cgroup/memory.max').read_text().strip()
        used = int(Path('/sys/fs/cgroup/memory.current').read_text())
        if limit != 'max':
            available = min(available, int(limit) - used)
        return max(0, min(256 * MIB, available - 512 * MIB))
    except (OSError, ValueError, StopIteration):
        return 0


def read_packs(directory, budget, seconds=5):
    """Populate Linux page cache, not Python heap or a second copy of the repository."""
    total = 0
    deadline = time.monotonic() + seconds
    for suffix in ('idx', 'pack'):
        for path in sorted(directory.glob(f'*.{suffix}')):
            if total >= budget or time.monotonic() >= deadline:
                return total
            with path.open('rb') as stream:
                while total < budget and time.monotonic() < deadline:
                    chunk = stream.read(min(MIB, budget - total))
                    if not chunk:
                        break
                    total += len(chunk)
    return total


def warm_packs(corpus):
    try:
        budget = available_budget()
        if not budget:
            return 0
        directory = subprocess.check_output(
            ['git', 'rev-parse', '--path-format=absolute', '--git-path', 'objects/pack'],
            cwd=corpus, text=True, timeout=3).strip()
        return read_packs(Path(directory), budget)
    except (OSError, subprocess.SubprocessError):
        return 0
