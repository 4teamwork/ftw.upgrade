from ftw.upgrade.jsonapi.exceptions import UnkownAPIAction
from ftw.upgrade.jsonapi.exceptions import WrongAPIVersion
from ftw.upgrade.jsonapi.utils import action
from ftw.upgrade.jsonapi.utils import ErrorHandling
from ftw.upgrade.jsonapi.utils import get_action_discovery_information
from ftw.upgrade.jsonapi.utils import jsonify
from zope.interface import implementer
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces import IPublishTraverse

import re


@implementer(IPublishTraverse)
class APIView(BrowserView):
    api_version = 'v1'

    def __init__(self, *args, **kwargs):
        super(APIView, self).__init__(*args, **kwargs)
        self.requested_api_version = None

    def publishTraverse(self, request, name):
        requested_api_version = None
        if re.match(r'v\d+', name):
            requested_api_version = name

        if requested_api_version == self.api_version:
            return self
        elif requested_api_version is not None:
            with ErrorHandling(self.request.RESPONSE):
                raise WrongAPIVersion(requested_api_version)
            request['TraversalRequestNameStack'] = []
            return ''

        action = getattr(self, name, None)
        if action and getattr(action, 'action_info', None):
            return action

        with ErrorHandling(self.request.RESPONSE):
            raise UnkownAPIAction(name)
        request['TraversalRequestNameStack'] = []
        return ''

    @jsonify
    @action('GET')
    def __call__(self):
        return {'actions': get_action_discovery_information(self),
                'api_version': self.api_version}
