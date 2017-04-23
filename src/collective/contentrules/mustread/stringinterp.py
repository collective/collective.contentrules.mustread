# -*- coding: utf-8 -*-
from plone.stringinterp.adapters import BaseSubstitution
from Products.CMFCore.interfaces import IContentish
from zope.component import adapts


class Fullname(BaseSubstitution):
    adapts(IContentish)

    category = u'Mustread'
    description = (
        u'Full Name of the person the read request is assigned to '
        u'(only available in `Request read confirmation` action)')

    def safe_call(self):
        return self.wrapper.mustread_fullname


class Deadline(BaseSubstitution):
    adapts(IContentish)

    category = u'Mustread'
    description = (
        u'Localized deadline of the read request '
        u'(only available in `Request read confirmation` action)')

    def safe_call(self):
        return self.wrapper.mustread_deadline


class URL(BaseSubstitution):
    adapts(IContentish)

    category = u'Mustread'
    description = u'URL of the item that marks the object as read'

    def safe_call(self):
        return self.context.absolute_url() + '/@@mark-read'
