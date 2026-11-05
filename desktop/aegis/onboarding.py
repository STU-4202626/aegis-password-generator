"""Qt-independent first-run flow rules and final vault creation checks.

A single explicit route definition prevents 'Next' from pointing to a missing
page when the authenticator step is skipped. It is also directly unit-testable.
"""
from __future__ import annotations

from .auth import Enrolment, validate_new_master
from .vault import new_data

WELCOME = 0
MASTER = 1
AUTH_CHOICE = 2
AUTH_VERIFY = 3
RECOVERY = 4
READY = 5
FINISHED = -1


def next_page(current_page: int, enable_authenticator: bool) -> int:
    """Return the next page ID for each valid route, or raise on invalid IDs."""
    routes = {
        WELCOME: MASTER,
        MASTER: AUTH_CHOICE,
        AUTH_CHOICE: AUTH_VERIFY if enable_authenticator else READY,
        AUTH_VERIFY: RECOVERY,
        RECOVERY: READY,
        READY: FINISHED,
    }
    if current_page not in routes:
        raise ValueError(f'Unknown onboarding page ID: {current_page}')
    return routes[current_page]


def prepare_first_vault(master: str, confirmation: str, *,
                        enable_authenticator: bool,
                        enrolment: Enrolment | None,
                        recovery_saved: bool) -> dict:
    """Validate the final state; return fresh data only if setup is complete.

    Does not write to disk. Callers must commit atomically and only then unlock.
    """
    validate_new_master(master, confirmation)
    if not enable_authenticator:
        # Ignore any stale in-memory enrolment from a previous branch selection.
        return new_data()
    if enrolment is None or not recovery_saved:
        raise ValueError('Verify the authenticator and save recovery codes before finishing.')
    updated = enrolment.updated
    if (not updated.get('totp_secret') or
            len(updated.get('recovery_hashes', [])) != 10 or
            updated.get('totp_last_counter', -1) < 0):
        raise ValueError('Authenticator setup is incomplete. Go back and verify a live code.')
    # Defensive copy: the caller owns the data it is about to persist.
    import copy
    return copy.deepcopy(updated)


def setup_complete_message(authenticator_enabled: bool) -> str:
    """Accurate context-specific guidance; a vault backup is NOT a recovery kit."""
    base = ('Your vault is ready. Keep your master passphrase safe. '
            'You can use Back up encrypted vault in Security Centre to save a copy. ')
    if authenticator_enabled:
        return base + ('Your 10 recovery codes work once each. Store them privately. '
                       'They do not reset your master passphrase or restore a lost vault.')
    return base + 'Authenticator is off. You can enable it later in Security Centre.'
