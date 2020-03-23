from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from zope.component import getUtility
from zope.component.hooks import getSite


def recook_resources():
    for name in ('portal_css', 'portal_javascripts'):
        registry = getToolByName(getSite(), name, None)
        if registry is not None:
            registry.cookResources()

    # Plone 5: clear all bundles
    registry = getUtility(IRegistry)
    for key in [key for key in registry.records.keys()
                if (key.startswith('plone.bundles/')
                    and key.endswith('.last_compilation'))]:
        registry[key] = None
