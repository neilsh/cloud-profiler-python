"""Signal-handler stress test for cloud-profiler-python.

Runs the asyncio reproducer from issue #142 on the main thread while the C++
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

DURATION_SEC = int(os.environ.get('STRESS_DURATION_SEC', '20'))

# Python exceptions raised in a daemon thread are otherwise swallowed by
# threading.excepthook while the main thread runs to completion, hiding any
# non-segfault failure of the C profiler.
profiler_failed = []


def _run_profiler():
  try:
    cpu_profiler.CPUProfiler(period_ms=10).profile(DURATION_SEC * 1_000_000_000)
  except BaseException as exc:
    profiler_failed.append(exc)
    raise


async def _dostuff():
  await asyncio.gather(*[asyncio.sleep(0.001) for _ in range(1000)])


async def _main():
  deadline = time.time() + DURATION_SEC
  iters = 0
  while time.time() < deadline:
    await asyncio.gather(*[_dostuff() for _ in range(50)])
    iters += 1
  return iters


_t = threading.Thread(target=_run_profiler, daemon=True)
_t.start()
time.sleep(0.5)  # let SIGPROF begin firing before we start the workload
if not _t.is_alive() or profiler_failed:
  raise SystemExit('profiler thread died early: %r' % (profiler_failed,))

iters = asyncio.run(_main())

if profiler_failed:
  raise SystemExit('profiler thread raised: %r' % (profiler_failed,))
print('STAGE:stress:OK iterations=%d' % iters, flush=True)
