"""Synthetic build_plan benchmark that excludes media disk I/O."""
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

import renamer_core as core


def run(total_files):
    with TemporaryDirectory(prefix='anime_bench_') as td:
        root = Path(td)
        paths = []
        for episode in range(1, total_files // 2 + 1):
            paths.append(root / f'Show E{episode:04d}.mkv')
            paths.append(root / f'Show E{episode:04d}.chs.ass')
        with patch.object(core, '_iter_files', return_value=iter(paths)), \
             patch.object(core, '_signature', return_value=(1, 2, 3, 4)):
            started = perf_counter()
            plan = core.build_plan(str(root), 'Show', 1, '{title} - {episode:02d}')
        return perf_counter() - started, len(plan)


if __name__ == '__main__':
    for total in (1000, 3000, 6000):
        seconds, count = run(total)
        print(f'{total:>5} files: {seconds:.4f}s ({count} planned)')
