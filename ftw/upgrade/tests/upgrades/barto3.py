from ftw.upgrade import UpgradeStep


class BarTo3(UpgradeStep):
    def __call__(self):
        self.portal._updateProperty('title', 'bar updated')
        self.install_upgrade_profile()
