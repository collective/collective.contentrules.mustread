# -*- coding: UTF-8 -*-
from collective.contentrules.mustread import _
from collective.contentrules.mustread.event import ReadConfirmationRequestEvent
from collective.contentrules.mustread.event import ReadReminderEvent
from collective.mustread.interfaces import ITracker
from plone import api
from Products.Five.browser import BrowserView
from zope import event
from zope.component import getUtility


class RequestReadConfirmation(BrowserView):
    """triggers a ReadConfirmationRequestEvent to notify
    contentrules engine
    """

    def __call__(self):
        event.notify(ReadConfirmationRequestEvent(self.context))
        props = api.portal.get_tool('portal_properties').site_properties
        view_types = props.getProperty('typesUseViewActionInListings', [])
        url = self.context.absolute_url()
        if self.context.portal_type in view_types:
            url = url + '/view'
        self.request.response.redirect(url)


class SendReminders(BrowserView):
    """finds objects with unconfirmed read requests
    and notifies contentrules engine for each of them
    """

    def __call__(self):
        tracker = getUtility(ITracker)
        notified = []
        for obj in tracker.what_to_read(context=self.context):
            event.notify(ReadReminderEvent(obj))
            notified.append('/'.join(obj.getPhysicalPath()))

        if notified:
            api.portal.show_message(_(
                u'msg_reminder_fired',
                default=(
                    u'Reminder event fired for ${count} objects: ${objects}'),
                mapping={'count': len(notified),
                         'objects': ', '.join(notified)}),
                self.request,
                'info')
        else:
            api.portal.show_message(_(
                u'msg_no_reminder_fired',
                default=u'No reminder event fired'),
                self.request,
                'info')

        props = api.portal.get_tool('portal_properties').site_properties
        view_types = props.getProperty('typesUseViewActionInListings', [])
        url = self.context.absolute_url()
        if self.context.portal_type in view_types:
            url = url + '/view'
        self.request.response.redirect(url)
