# -*- coding: utf-8 -*-
from Products.CMFPlone.utils import safe_unicode
from zope.schema.vocabulary import SimpleVocabulary


def RolesVocabularyFactory(context):
    """Vocabulary Factory for Roles in the Plone Site"""

    # context is the content rule object which is stored in the plone site
    sharing_page = context.restrictedTraverse('@@sharing')
    roles = sharing_page.roles()
    sane_roles = [(safe_unicode(role['id']).encode('ascii', 'replace'),
                   safe_unicode(role['id'])) for role in roles]
    sane_roles.append(('Owner', 'Owner'))
    return SimpleVocabulary.fromItems(sane_roles)
