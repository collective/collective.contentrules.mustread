# -*- coding: utf-8 -*-
from zope.component.interfaces import IObjectEvent
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class IMustReadEvent(IObjectEvent):
    """base class for all events that shall trigger content rules engine"""

    pass


class IReadConfirmationRequest(IMustReadEvent):
    """Zope Event to be notified when a read confirmation is requested
    for an object
    """

    pass


class IReadReminder(IMustReadEvent):
    """Zope Event to be notified when a reminder for open read
    confirmation requests shall be sent
    """

    pass


class ICollectiveContentrulesMustreadLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""

    pass


class ICanBeMarkedAsMustRead(Interface):
    """Marker for content that shows mustread actions"""

    pass
