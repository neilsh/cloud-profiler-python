"""Smoke test: import the package and run start()'s preflight path.

Without GCP creds, start() raises DefaultCredentialsError from setup_auth
before any SIGPROF handler is installed, so this validates only:
- the package imports (which on Linux loads the _profiler C extension)
- start()'s argument validation and Client construction don't crash

SIGPROF runtime behavior is exercised by `nox -s stress`.
"""

import sys

from google.auth.exceptions import DefaultCredentialsError, RefreshError

import googlecloudprofiler

try:
    googlecloudprofiler.start(
        service="smoke",
        service_version="1.0.0",
        verbose=3,
    )
except (DefaultCredentialsError, RefreshError) as exc:
    sys.stderr.write("start() raised expected creds error: %r\n" % (exc,))

print("OK")
