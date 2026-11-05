"""AEGIS mandatory installer-build tests (no QApplication / Qt GUI lifecycle).

The full interactive GUI suite is intentionally separate: on some Windows Qt
runtimes it prints a successful unittest result but then terminates with the
native 0xC0000409 exit code on interpreter shutdown. Masking that exit code
would make the packaging gate dishonest. The builder therefore checks every
non-GUI test before packaging, and GUI tests are an explicit diagnostic run.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

# Explicit class names prevent starting QApplication within this process.
# Any new non-GUI test class must be added to this list.
BACKEND_CASES = (
    "test_security.SecurityTests",
    "test_recovery.RecoveryTests",
    "test_onboarding.OnboardingRoutingTests",
    "test_v031_polish.ContextAndBackupTests",
    "test_v033_restore.RestoreBackendTests",
    "test_v034_product_experience.CopyContractTests",
    "test_windows_packaging.WindowsPackagingTests",
)


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in BACKEND_CASES)
    if loader.errors:
        for error in loader.errors:
            print(error, file=sys.stderr)
        return 1
    total = suite.countTestCases()
    print(f"Checking {total} backend / packaging tests; no Qt widgets will be created.", flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped:
        print("Mandatory tests did not all pass.", file=sys.stderr)
        return 1
    print("Backend / packaging checks passed. GUI integration is a separate check.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
