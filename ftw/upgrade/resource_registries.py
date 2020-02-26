from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from zope.component import getUtility
from zope.component.hooks import getSite


def recook_resources():
    site = getSite()
    for name in ('portal_css', 'portal_javascripts'):
        try:
            registry = getToolByName(site, name)
        except AttributeError:
            # Plone 5.2+ without the old-style resource registries
            continue
        registry.cookResources()

    # Plone 5: clear all bundles
    registry = getUtility(IRegistry)
    for key in filter(
            lambda key: (key.startswith('plone.bundles/')
                         and key.endswith('.last_compilation')),
            registry.records.keys()):
        registry[key] = None
