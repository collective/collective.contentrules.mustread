# -*- coding: utf-8 -*-
from collective.contentrules.mustread.interfaces import IMustReadSettings
from plone.registry.interfaces import IRegistry
from zope.component import getUtility


def to_1001_fix_registry_records(context):
    registry = getUtility(IRegistry)
    registry.registerInterface(IMustReadSettings)
