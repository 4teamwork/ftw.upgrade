
class APIError(Exception):
    def __init__(self, message, details='', response_code=400):
        super(APIError, self).__init__(message)
        self.message = message
        self.details = details
        self.response_code = response_code

    def process_error(self, response):
        return


class WrongAPIVersion(APIError):
    def __init__(self, requested_version):
        super(WrongAPIVersion, self).__init__(
            'Wrong API version',
            'The API version "{0}" is not available.'.format(
                requested_version),
            response_code=404)


class UnkownAPIAction(APIError):
    def __init__(self, action_name):
        super(UnkownAPIAction, self).__init__(
            'Unkown API action',
            'There is no API action "{0}".'.format(action_name),
            response_code=404)


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


class ProfileNotAvailable(APIError):
    def __init__(self, profileid):
        super(ProfileNotAvailable, self).__init__(
            'Profile not available',
            'The profile "{0}" is wrong or not installed'
            ' on this Plone site.'.format(profileid))


class ProfileNotFound(APIError):
    def __init__(self, profileid):
        super(ProfileNotFound, self).__init__(
            'Profile not found',
            'The profile "{0}" is unknown.'.format(profileid))


class UpgradeNotFoundWrapper(APIError):
    def __init__(self, original_exception):
        api_upgrade_id = original_exception.api_id
        super(UpgradeNotFoundWrapper, self).__init__(
            'Upgrade not found',
            'The upgrade "{0}" is unkown.'.format(api_upgrade_id))


class AbortTransactionWithStreamedResponse(Exception):
    """This exception wraps another exception and is used to indicate that
    the original exception should cause the transaction to be aborted but
    not cause 500 since we are streaming a response.
    It is expected that the exception information (e.g. the traceback) is
    already written to the response and streamed to the browser.
    """

    def __init__(self, original_exception):
        self.original_exception = original_exception
