from blinker import Namespace

_signals = Namespace()

enrollment_linked = _signals.signal('enrollment_linked')
"""Notifies receivers that enrollment has been linked to an invenio user

:param  enrollment: the linked enrollment
"""

enrollment_created = _signals.signal('enrollment_created')
"""Notifies receivers that enrollment has been created.

:param  enrollment: the linked enrollment
:return True if no notification should be sent
"""

enrollment_accepted = _signals.signal('enrollment_accepted')
"""Notifies receivers that enrollment has been accepted (when accept is required)

:param  enrollment: the accepted enrollment
"""

enrollment_rejected = _signals.signal('enrollment_rejected')
"""Notifies receivers that enrollment has been rejected (when accept is required)

:param  enrollment: the rejected enrollment
"""

enrollment_successful = _signals.signal('enrollment_successful')
"""Notifies receivers that enrollment has been successfully carried out

:param  enrollment: the successful enrollment
"""

enrollment_failed = _signals.signal('enrollment_handler_failed')
"""Notifies receivers that enrollment failed.

:param  enrollment: the failed enrollment
:param  exception: failure exception
"""

enrollment_duplicit_user = _signals.signal('enrollment_duplicit_user')
"""Notifies receivers that the same enrollment is used by two different accounts.

:param  enrollment: the failed enrollment
:param  impostor: the second user that wants to use the enrollment
"""

enrollment_revoked = _signals.signal('enrollment_revoked')
"""Notifies receivers that enrollment has been successfully revoked

:param  enrollment: the revoked enrollment
"""

revocation_failed = _signals.signal('revocation_failed')
"""Notifies receivers that revocation failed.

:param  enrollment: the failed enrollment
:param  exception: failure exception
"""
