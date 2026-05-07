"""Nox sessions for cloud-profiler-python.

Run all sessions across all Python versions:
    nox

Run a specific session:
    nox -s smoke               # all Python versions
    nox -s smoke-3.12          # one Python version
    nox -s stress-3.12

Smoke runs on each target Python on the host (fast feedback for build/import).
It needs each version's interpreter on PATH; locally:
    pyenv install 3.8.20 3.9.20 3.10.15 3.11.10 3.12.7 3.13.0
In CI: actions/setup-python with the matching python-version.

Stress runs inside a python:X.Y-slim Docker container regardless of host, so
the same command exercises the SIGPROF C++ profiler identically on macOS and
on Linux CI. Requires Docker on PATH.

Override per-run duration / number of runs:
    STRESS_DURATION_SEC=30 STRESS_RUNS=5 nox -s stress-3.12
"""

import os

import nox

PY_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]

# Default sessions when invoked without -s.
nox.options.sessions = ["smoke"] + [f"stress-{v}" for v in PY_VERSIONS]
# Don't fail bare `nox` for missing host interpreters; smoke skips them and
# stress is Docker-based and unaffected.
nox.options.error_on_missing_interpreters = False
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
        against CPython's frame-setup code paths. Loops STRESS_RUNS short
        runs to lift per-cell catch probability.
        """
        duration = os.environ.get("STRESS_DURATION_SEC", "20")
        runs = os.environ.get("STRESS_RUNS", "3")
        session.run(
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}:/work:ro",
            "-e", f"STRESS_DURATION_SEC={duration}",
            "-e", f"STRESS_RUNS={runs}",
            f"python:{py}-slim",
            "bash", "-c",
            # Mount is read-only; copy to a writable path so pip install and
            # setuptools' build_ext have somewhere to write build artifacts.
            "set -e; "
            "cp -r /work /tmp/src && "
            "cd /tmp/src && "
            "apt-get update -qq && "
            "apt-get install -y -qq --no-install-recommends g++ && "
            "pip install -q . && "
            "echo STAGE:install:OK && "
            'for i in $(seq 1 "${STRESS_RUNS}"); do '
            '  echo "STAGE:run:$i" && python scripts/_stress.py; '
            "done",
            external=True,
        )
    return stress


for _py in PY_VERSIONS:
    _make_stress(_py)
