from ftw.upgrade.exceptions import CyclicDependencies
from ftw.upgrade.exceptions import UpgradeNotFound
from ftw.upgrade.jsonapi.exceptions import APIError
from ftw.upgrade.jsonapi.exceptions import CyclicDependenciesWrapper
from ftw.upgrade.jsonapi.exceptions import MethodNotAllowed
from ftw.upgrade.jsonapi.exceptions import MissingParam
from ftw.upgrade.jsonapi.exceptions import UnauthorizedWrapper
from ftw.upgrade.jsonapi.exceptions import UpgradeNotFoundWrapper
from zExceptions import Unauthorized
from zope.security import checkPermission
import inspect
import json


class ErrorHandling(object):
    """Context manager for handling API errors and responding as JSON.
    """

    exception_wrappers = {
        CyclicDependencies: CyclicDependenciesWrapper,
        UpgradeNotFound: UpgradeNotFoundWrapper,
        Unauthorized: UnauthorizedWrapper}

    def __init__(self, response):
        self.response = response

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc, traceback):
        exc = self.wrap_exception(exc)
        if not isinstance(exc, APIError):
            return

        self.response.setStatus(exc.response_code, exc.message)
        self.response.setHeader('Content-Type',
                                'application/json; charset=utf-8')
        exc.process_error(self.response)
        self.response.setBody(json.dumps(['ERROR', exc.message, exc.details]))
        self.response.flush()
        return True

    def wrap_exception(self, original_exception):
        for original_type, wrapper_type in self.exception_wrappers.items():
            if isinstance(original_exception, original_type):
                return wrapper_type(original_exception)
        return original_exception


def action(method, rename_params={}):
    """Decorats an API action.
    The action is protected to only respond to one HTTP method
    and protects the action by the cmf.ManagePortal permission.
    Known API errors are written as JSON to the respond.
    """
    def wrap_action(func):
        def action_wrapper(self):
            with ErrorHandling(self.request.RESPONSE):
                if self.request.method != method:
                    raise MethodNotAllowed(method)

                if not checkPermission('cmf.ManagePortal', self.context):
                    raise Unauthorized()

                params = extract_action_params(
                    func, self.request, rename_params)
                return func(self, **params)

        action_wrapper.__doc__ = func.__doc__
        action_wrapper.__name__ = func.__name__
        return action_wrapper
    return wrap_action


def jsonify(func):
    """Action decorator for converting response data to JSON.
    """

    def json_wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        response = self.request.RESPONSE
        if 'json' in (response.getHeader('Content-Type') or ''):
            # already converted to json, e.g. on error.
            return result

        response.setHeader('Content-Type', 'application/json; charset=utf-8')
        return json.dumps(result, indent=4, encoding='utf-8')

    json_wrapper.__doc__ = func.__doc__
    json_wrapper.__name__ = func.__name__
    return json_wrapper


def extract_action_params(func, request, rename_params=None):
    rename_params = rename_params or {}
    form = request.form
    argspec = inspect.getargspec(func)
    required_params = argspec.args[len(argspec.defaults or []) + 1:]

    for arg_name in required_params:
        if not form.get(arg_name, None):
            raise MissingParam(rename_params.get(arg_name, arg_name))

    return dict([(name, form[name]) for name in form if name in argspec.args])
