from apps.common.audit import register_audit_signals
from apps.users.models import Role, User


def _connect_signals():
    register_audit_signals(User)
    register_audit_signals(Role)


_connect_signals()
