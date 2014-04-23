import transaction


TRANSACTION_NOTE_MAX_LENGTH = 65533


class TransactionNote(object):
    """The zope transaction note is limited to a length of 65533 characters.
    When installing a lot of upgrades at once, this limitation may be
    exceeded.

    Transaction not strategy:
    - Use "profileid -> dest (description)" for each upgrade
    - when too long, use "profileid -> dest" (without the description)
    - when still too long, crop at the end, appending "..."
    """

    def add_upgrade(self, profileid, destination, description):
        self._upgrades.append({'profileid': profileid,
                               'destination': '.'.join(destination),
                               'description': description})
        self._update_transaction_note()

    def _update_transaction_note(self):
        message = '\n'.join(self._transaction_messages(True))
        if len(message) >= TRANSACTION_NOTE_MAX_LENGTH:
            message = '\n'.join(self._transaction_messages(False))

        if len(message) >= TRANSACTION_NOTE_MAX_LENGTH:
            message = message[:TRANSACTION_NOTE_MAX_LENGTH-4] + '...'

        transaction.get().description = message

    def _transaction_messages(self, include_description=True):
        if include_description:
            template = '%(profileid)s -> %(destination)s (%(description)s)'
        else:
            template = '%(profileid)s -> %(destination)s'

        return [template % upgrade for upgrade in self._upgrades]

    @property
    def _upgrades(self):
        current_transaction = transaction.get()
        if not hasattr(current_transaction, 'ftw.upgrade:upgrades'):
            setattr(current_transaction, 'ftw.upgrade:upgrades', [])
        return getattr(current_transaction, 'ftw.upgrade:upgrades')
