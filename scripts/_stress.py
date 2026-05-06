"""Signal-handler stress test for cloud-profiler-python.

Models the asyncio reproducer from issue #142 in the main thread while the C++
CPU profiler runs SIGPROF-driven sampling in a daemon thread. Exits 0 cleanly
on success; any segfault, abort, or fatal Python error in the signal handler
will crash this process with a non-zero exit (139 = SIGSEGV, 134 = SIGABRT).

Direct invocation of `cpu_profiler.CPUProfiler` skips the agent's auth/upload
path entirely, so no GCP credentials or network are needed. Sampling rate is
the agent's default (10ms / 100Hz). Override duration via STRESS_DURATION_SEC.
"""

import asyncio
import os
import threading
import time

from googlecloudprofiler import cpu_profiler

DURATION_SEC = int(os.environ.get('STRESS_DURATION_SEC', '60'))


def _run_profiler():
  cpu_profiler.CPUProfiler(period_ms=10).profile(DURATION_SEC * 1_000_000_000)


async def _dostuff():
  await asyncio.gather(*[asyncio.sleep(0.001) for _ in range(1000)])


async def _main():
  deadline = time.time() + DURATION_SEC
  iters = 0
  while time.time() < deadline:
    await asyncio.gather(*[_dostuff() for _ in range(50)])
    iters += 1
  return iters


threading.Thread(target=_run_profiler, daemon=True).start()
time.sleep(0.5)  # let SIGPROF begin firing before we start the workload

iters = asyncio.run(_main())
print('STAGE:stress:OK iterations=%d' % iters, flush=True)
