from AccessControl import getSecurityManager
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import SpecialUsers
from Acquisition import aq_inner
from Acquisition import aq_parent
from binascii import hexlify
from ftw.upgrade.exceptions import CyclicDependencies
from ftw.upgrade.exceptions import UpgradeNotFound
from ftw.upgrade.jsonapi.exceptions import AbortTransactionWithStreamedResponse
from ftw.upgrade.jsonapi.exceptions import APIError
from ftw.upgrade.jsonapi.exceptions import CyclicDependenciesWrapper
from ftw.upgrade.jsonapi.exceptions import MethodNotAllowed
from ftw.upgrade.jsonapi.exceptions import MissingParam
from ftw.upgrade.jsonapi.exceptions import UnauthorizedWrapper
from ftw.upgrade.jsonapi.exceptions import UpgradeNotFoundWrapper
from ftw.upgrade.utils import get_tempfile_authentication_directory
from OFS.interfaces import IApplication
from zExceptions import Unauthorized
from zope.interface import alsoProvides
from zope.security import checkPermission

import json
import os
import re
import stat
import transaction


try:
    from plone.protect.interfaces import IDisableCSRFProtection
except ImportError:
    DISABLE_CSRF = False
else:
    DISABLE_CSRF = True

try:
    from inspect import getfullargspec
except ImportError:
    # Python2.7 compatibility
    from inspect import getargspec as getfullargspec


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
        return self

    def __exit__(self, _type, exc, _traceback):
        if isinstance(exc, AbortTransactionWithStreamedResponse):
            if isinstance(self.wrap_exception(exc.original_exception),
                          APIError):
                exc = exc.original_exception
            else:
                transaction.abort()
                return True

        exc = self.wrap_exception(exc)
        if not isinstance(exc, APIError):
            return

        self.response.setStatus(exc.response_code, exc.message)
        self.response.setHeader('Content-Type',
                                'application/json; charset=utf-8')
        exc.process_error(self.response)
        self.response.setBody(
            json.dumps(['ERROR', exc.message, exc.details]) + '\n')
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

                perform_tempfile_authentication(self.context, self.request)

                if not checkPermission('cmf.ManagePortal', self.context):
                    raise Unauthorized()

                if DISABLE_CSRF:
                    alsoProvides(self.request, IDisableCSRFProtection)

                params = extract_action_params(
                    func, self.request, rename_params)
                return func(self, **params)

        action_wrapper.__doc__ = func.__doc__
        action_wrapper.__name__ = func.__name__
        action_wrapper.action_info = {
            'method': method,
            'rename_params': rename_params,
            'name': func.__name__,
            'doc': func.__doc__,
            'argspec': getfullargspec(func)}
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
        return json.dumps(result, indent=4) + '\n'

    json_wrapper.__doc__ = func.__doc__
    json_wrapper.__name__ = func.__name__
    json_wrapper.action_info = getattr(func, 'action_info', None)
    return json_wrapper


def extract_action_params(func, request, rename_params=None):
    rename_params = rename_params or {}
    form = request.form
    argspec = getfullargspec(func)
    required_params = get_required_args(argspec)

    for arg_name in required_params:
        if not form.get(arg_name, None):
            raise MissingParam(rename_params.get(arg_name, arg_name))

    return dict([(name, form[name]) for name in form if name in argspec.args])


def get_action_discovery_information(view):
    result = []
    for name in sorted(dir(view)):
        if name == '__call__':
            continue

        func = getattr(view, name, None)
        if not func:
            continue

        action_info = getattr(func, 'action_info', None)
        if not action_info:
            continue

        argspec = action_info['argspec']
        required_params = sorted(get_required_args(argspec))
        rename_params = action_info['rename_params']
        required_params = [rename_params.get(name, name)
                           for name in required_params]

        result.append({
                'name': action_info['name'],
                'description': re.sub(r'\s+', ' ', action_info['doc']).strip(),
                'required_params': required_params,
                'request_method': action_info['method'].upper()})

    return result


def get_required_args(argspec):
    if not argspec.defaults:
        return argspec.args[1:]
    else:
        return argspec.args[1:-len(argspec.defaults)]


def perform_tempfile_authentication(context, request):
    """When the "x-ftw.upgrade-tempfile-auth" header is set, authentication is
    initialized based on a tempfile value for verifying that the client and the
    server is on the same machine with the same user.

    When necessary, a system-upgrade user is created with Manager role and
    the security is set to this user.
    """
    if getSecurityManager().getUser() != SpecialUsers.nobody:
        return

    auth_value = request.getHeader('x-ftw.upgrade-tempfile-auth')
    if not auth_value:
        return

    validate_tempfile_authentication_header_value(auth_value)
    user = get_system_upgrade_user(context)
    newSecurityManager(request, user)
    transaction.get().setUser(user.getId(), '')


def validate_tempfile_authentication_header_value(header_value):
    if not re.match(r'^tmp\w{6,8}:\w{64}', header_value):
        raise ValueError(
            'tempfile auth: invalid x-ftw.upgrade-tempfile-auth header value.')

    filename, authhash = header_value.split(':')
    directory = get_tempfile_authentication_directory(os.getcwd())
    filepath = directory.joinpath(filename)

    if not filepath.isfile():
        raise ValueError('tempfile auth: tempfile does not exist.')

    # Verify that "others" do not have any permissions on this file.
    if filepath.stat().st_mode & stat.S_IRWXO:
        raise ValueError('tempfile auth: tempfile is accesible by "others".')

    if filepath.getsize() != 64:
        raise ValueError('tempfile auth: tempfile size is invalid.')

    with open(filepath, 'r') as authfile:
        if authfile.read() != authhash:
            raise ValueError('tempfile auth: authentication failed.')


def get_system_upgrade_user(context):
    while not IApplication.providedBy(context):
        context = aq_parent(aq_inner(context))

    acl_users = context.acl_users
    if not acl_users.getUserById('system-upgrade'):
        acl_users.userFolderAddUser(
            'system-upgrade', hexlify(os.urandom(16)), ['Manager'], None)
    return acl_users.getUserById('system-upgrade')


def parse_bool(string):
    return string in ('True', 'true', True)
