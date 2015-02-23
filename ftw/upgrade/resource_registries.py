from Products.CMFCore.utils import getToolByName
from zope.component.hooks import getSite


def recook_resources():
    for name in ('portal_css', 'portal_javascripts'):
        registry = getToolByName(getSite(), name)
        registry.cookResources()
