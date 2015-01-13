
class APIError(Exception):
    def __init__(self, message, details='', response_code=400):
        super(APIError, self).__init__(message)
        self.message = message
        self.details = details
        self.response_code = response_code

    def process_error(self, response):
        return


class UnauthorizedWrapper(APIError):
    def __init__(self, original_exception):
        super(UnauthorizedWrapper, self).__init__(
            'Unauthorized',
            'Admin authorization required.',
            response_code=401)


class MethodNotAllowed(APIError):
    def __init__(self, required_method):
        self.required_method = required_method.upper()
        super(MethodNotAllowed, self).__init__(
            'Method Not Allowed',
            'Action requires {0}'.format(self.required_method),
            response_code=405)

    def process_error(self, response):
        response.setHeader('Allow', self.required_method)


class MissingParam(APIError):
    def __init__(self, param_name):
        super(MissingParam, self).__init__(
            'Param missing',
            'The param "{0}" is required for this API action.'.format(
                param_name))


class PloneSiteOutdated(APIError):
    def __init__(self):
        super(PloneSiteOutdated, self).__init__(
            'Plone site outdated',
            'The Plone site is outdated and needs to be upgraded'
            ' first using the regular Plone upgrading tools.')


class CyclicDependenciesWrapper(APIError):
    def __init__(self, original_exception):
        super(CyclicDependenciesWrapper, self).__init__(
            'Cyclic dependencies',
            'There are cyclic Generic Setup profile dependencies.',
            response_code=500)


class UpgradeNotFoundWrapper(APIError):
    def __init__(self, original_exception):
        api_upgrade_id = original_exception.api_id
        super(UpgradeNotFoundWrapper, self).__init__(
            'Upgrade not found',
            'The upgrade "{0}" is unkown.'.format(api_upgrade_id))
