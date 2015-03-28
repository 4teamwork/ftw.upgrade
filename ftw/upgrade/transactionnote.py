import transaction


TRANSACTION_NOTE_MAX_LENGTH = 65533


class TransactionNote(object):
    """The zope transaction note is limited to a length of 60000 characters.
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

    def set_transaction_note(self):
        maximum_possible_length = TRANSACTION_NOTE_MAX_LENGTH \
            - len(transaction.get().description) \
            - len('\n')

        message = '\n'.join(self._transaction_messages(True))
        if len(message) >= maximum_possible_length:
            message = '\n'.join(self._transaction_messages(False))

        if len(message) >= maximum_possible_length:
            message = message[:maximum_possible_length - 4] + '...'

        if len(message) <= maximum_possible_length:
            transaction.get().note(message)

    def _transaction_messages(self, include_description=True):
        if include_description:
            template = '%(profileid)s -> %(destination)s (%(description)s)'
        else:
            template = '%(profileid)s -> %(destination)s'

        return [template % upgrade for upgrade in self._upgrades]

    def _reset_upgrade_info(self):
        current_transaction = transaction.get()
        if not hasattr(current_transaction, 'ftw.upgrade:upgrades'):
            setattr(current_transaction, 'ftw.upgrade:upgrades', [])

    @property
    def _upgrades(self):
        self._reset_upgrade_info()
        current_transaction = transaction.get()
        return getattr(current_transaction, 'ftw.upgrade:upgrades')
