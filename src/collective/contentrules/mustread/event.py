# -*- coding: utf-8 -*-
from collective.contentrules.mustread.interfaces import IReadConfirmationRequest  # noqa
from collective.contentrules.mustread.interfaces import IReadReminder
from zope.component.interfaces import ObjectEvent
from zope.interface import implements


class ReadConfirmationRequestEvent(ObjectEvent):

    implements(IReadConfirmationRequest)


class ReadReminderEvent(ObjectEvent):

    implements(IReadReminder)
