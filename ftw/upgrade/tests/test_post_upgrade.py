from ftw.builder import Builder
from ftw.upgrade.interfaces import IPostUpgrade
from ftw.upgrade.tests.base import UpgradeTestCase
from zope.interface import Interface


class TestPostUpgrade(UpgradeTestCase):

    def test_post_upgrade_adapters_are_executed(self):
        execution_info = {}
        def post_upgrade_adapter(portal, request):
            execution_info.update({
                    'executed': True,
                    'portal_argument': portal,
                    'request_argument': request})

        self.portal.getSiteManager().registerAdapter(
            post_upgrade_adapter,
            required=(Interface, Interface),
            provided=IPostUpgrade,
            name='name-is-not-really-relevant')

        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(self.default_upgrade()))

        with self.package_created():
            self.install_profile('the.package:default', version='1000')
            self.install_profile_upgrades('the.package:default')
            self.assertDictEqual(
                {'executed': True,
                 'portal_argument': self.portal,
                 'request_argument': self.portal.REQUEST},
                execution_info)

    def test_post_upgrade_adapters_are_executed_in_order_of_name(self):
        self.package.with_profile(Builder('genericsetup profile')
                                  .with_upgrade(self.default_upgrade()))
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('bar')
                                  .with_dependencies('the.package:foo'))
        self.package.with_profile(Builder('genericsetup profile')
                                  .named('foo')
                                  .with_dependencies('the.package:default'))

        site_manager = self.portal.getSiteManager()
        execution_order = []

        def register_post_component_adapter(profile_id):
            class PostComponentAdapter(object):
                def __init__(self, portal, request):
                    pass
                def __call__(self):
                    execution_order.append(profile_id)
            site_manager.registerAdapter(PostComponentAdapter,
                                         required=(Interface, Interface),
                                         provided=IPostUpgrade,
                                         name=profile_id)

        map(register_post_component_adapter,
            ('the.package:default', 'the.package:foo', 'the.package:bar'))

        with self.package_created():
            self.install_profile('the.package:default', version='1000')
            self.install_profile('the.package:foo')
            self.install_profile('the.package:bar')

            self.assertEquals([], execution_order)
            self.install_profile_upgrades('the.package:default')

            # XXX the order should actually be reversed.
            # See https://github.com/4teamwork/ftw.upgrade/issues/59
            self.assertEquals(['the.package:default',
                               'the.package:foo',
                               'the.package:bar'],
                              execution_order)
