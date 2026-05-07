"""Nox sessions for cloud-profiler-python.

Run all sessions across all Python versions:
    nox

Run a specific session:
    nox -s smoke               # all Python versions
    nox -s smoke-3.12          # one Python version
    nox -s stress-3.12

Smoke runs on the host Python (fast feedback for build/import). It needs the
target interpreter on PATH; locally:
    pyenv install 3.8.20 3.9.20 3.10.15 3.11.10 3.12.7 3.13.0
In CI: actions/setup-python with the matching python-version.

Stress runs inside a python:X.Y-slim Docker container regardless of host, so
the same command exercises the SIGPROF C++ profiler identically on macOS and
on Linux CI. Requires Docker on PATH.

Override stress duration:
    STRESS_DURATION_SEC=120 nox -s stress-3.12
"""

import os

import nox

PY_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]

# Default sessions when invoked without -s.
nox.options.sessions = ["smoke"] + [f"stress-{v}" for v in PY_VERSIONS]
nox.options.reuse_existing_virtualenvs = True


@nox.session(python=PY_VERSIONS)
def smoke(session):
    """Install the package, import it, and call start() once.

    Runs on the host Python. On Linux this builds and imports the C extension;
    on macOS it only verifies the pure-Python wrappers (the C extension is
    Linux-only).
    """
    session.install(".")
    session.run("python", "tests/smoke.py")


def _make_stress(py):
    @nox.session(name=f"stress-{py}", python=False, venv_backend="none")
    def stress(session):
        """Asyncio signal-handler stress test (issue #142 reproducer).

        Runs in python:{py}-slim so the same command works on macOS and
        Linux CI. Drives the C++ CPU profiler in a daemon thread while the
        main thread runs an asyncio workload; catches SIGPROF-handler races
        against CPython's frame-setup code paths.
        """
        duration = os.environ.get("STRESS_DURATION_SEC", "60")
        session.run(
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}:/work:ro",
            "-e", f"STRESS_DURATION_SEC={duration}",
            f"python:{py}-slim",
            "bash", "-c",
            # Copy source to /tmp so the build is isolated from any
            # host-built artifacts left in the mounted tree by the smoke step.
            "set -e; "
            "cp -r /work /tmp/src && "
            "cd /tmp/src && "
            "apt-get update -qq >/dev/null && "
            "apt-get install -y -qq --no-install-recommends g++ >/dev/null && "
            "pip install -q . && "
            "python scripts/_stress.py",
            external=True,
        )
    return stress


for _py in PY_VERSIONS:
    _make_stress(_py)
