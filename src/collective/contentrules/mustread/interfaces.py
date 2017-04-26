# -*- coding: utf-8 -*-
from collective.contentrules.mustread import _
from zope import schema
from zope.component.interfaces import IObjectEvent
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class IMustReadSettings(Interface):
    '''registry settings
    '''

    expired_recipient = schema.List(
        title=_(u'label_expired-recipient',
                default=u'Expired recipient'),
        description=_(
            u'help_expired-recipient',
            default=(
                u'Email address(es) the expired notifications are sent to '
                u"If not given, the portal's admin address is used"
            )
        ),
        value_type=schema.TextLine(),
        required=False,
        default=[],
    )


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
