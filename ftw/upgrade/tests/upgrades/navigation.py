from ftw.upgrade import UpgradeStep


class UpdateNavigationIndex(UpgradeStep):

    def __call__(self):
        if self.catalog_has_index('excludeFromNav'):
            self.catalog_remove_index('excludeFromNav')

        self.catalog_add_index('excludeFromNav', 'FieldIndex')
