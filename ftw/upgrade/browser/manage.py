from Products.CMFCore.utils import getToolByName
from ftw.upgrade.exceptions import CyclicDependencies
from ftw.upgrade.interfaces import IExecutioner
from ftw.upgrade.interfaces import IUpgradeInformationGatherer
from zope.component import getAdapter
from zope.publisher.browser import BrowserView
import logging
import traceback


LOG = logging.getLogger('ftw.upgrade')


class ResponseLogger(object):

    def __init__(self, response):
        self.response = response
        self.handler = None
        self.formatter = None

    def __enter__(self):
        self.handler = logging.StreamHandler(self)
        self.formatter = logging.root.handlers[-1].formatter
        self.handler.setFormatter(self.formatter)
        logging.root.addHandler(self.handler)

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            LOG.error('FAILED')
            traceback.print_exception(exc_type, exc_value, tb, None, self)

        logging.root.removeHandler(self.handler)

    def write(self, line):
        if isinstance(line, unicode):
            line = line.encode('utf8')

        self.response.write(line)
        self.response.flush()

    def writelines(self, lines):
        for line in lines:
            self.write(line)


class ManageUpgrades(BrowserView):

    def __init__(self, *args, **kwargs):
        super(ManageUpgrades, self).__init__(*args, **kwargs)
        self.cyclic_dependencies = False

    def __call__(self):
        if self.request.get('submitted', False):
            assert not self.plone_needs_upgrading(), \
                'Plone is outdated. Upgrading add-ons is disabled.'

            if self.request.get('ajax', False):
                return self.install_with_ajax_stream()

            else:
                self.install()

        return super(ManageUpgrades, self).__call__(self)

    def install(self):
        """Installs the selected upgrades.
        """
        gstool = getToolByName(self.context, 'portal_setup')
        executioner = getAdapter(gstool, IExecutioner)
        data = self._get_upgrades_to_install()
        executioner.install(data)

        logging.getLogger('ftw.upgrade').info(
            'FINISHED')

    def install_with_ajax_stream(self):
        """Installs the selected upgrades and streams the log into
        the HTTP response.
        """
        response = self.request.RESPONSE
        response.setHeader('Content-Type', 'text/html')
        response.setHeader('Transfer-Encoding', 'chunked')
        response.write('<html>')
        response.write('<body>')
        response.write('  ' * getattr(response, 'http_chunk_size', 100))
        response.write('<pre>')

        with ResponseLogger(self.request.RESPONSE):
            self.install()

        response.write('</pre>')
        response.write('</body>')
        response.write('</html>')

    def get_data(self):
        gstool = getToolByName(self.context, 'portal_setup')
        gatherer = getAdapter(gstool, IUpgradeInformationGatherer)
        try:
            return gatherer.get_upgrades()
        except CyclicDependencies, exc:
            self.cyclic_dependencies = True
            return exc.dependencies

    def plone_needs_upgrading(self):
        portal_migration = getToolByName(self.context, 'portal_migration')
        return portal_migration.needUpgrading()

    def _get_upgrades_to_install(self):
        """Returns a dict where the key is a profileid and the value
        is a list of upgrade ids.
        """

        data = {}
        for item in self.request.get('upgrade', []):
            item = dict(item)
            profileid = item['profileid']
            del item['profileid']

            if item:
                data[profileid] = item.keys()

        upgrades = []

        for profile in self.get_data():
            if profile.get('id') not in data:
                continue

            profile_data = data[profile.get('id')]
            if not profile.get('upgrades', []):
                continue

            profile_upgrades = []
            upgrades.append((profile.get('id'), profile_upgrades))

            for upgrade in profile.get('upgrades', []):
                if upgrade.get('id') in profile_data:
                    profile_upgrades.append(upgrade.get('id'))

        return upgrades
