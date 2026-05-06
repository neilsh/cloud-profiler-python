"""Smoke test: import the package and call start() once.

start() will raise DefaultCredentialsError without GCP credentials; that's
expected and not treated as a failure. We just verify the C extension loads,
the agent's Python wrappers are importable, and start() doesn't crash the
process before/after the credential check.
"""

import sys
import time

import googlecloudprofiler

try:
    googlecloudprofiler.start(
        service="smoke",
        service_version="1.0.0",
        verbose=3,
    )
except Exception as exc:  # noqa: BLE001 - expected without GCP creds
    sys.stderr.write("start() raised (allowed without GCP creds): %r\n" % (exc,))

# Give the agent thread a moment to crash if it's going to.
time.sleep(2)
print("OK")
