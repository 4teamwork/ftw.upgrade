from ftw.upgrade import UpgradeStep


class AddAction(UpgradeStep):
    """Add a new "test-action" to the portal-tabs actions.
    """

    def __call__(self):
        self.install_upgrade_profile()
