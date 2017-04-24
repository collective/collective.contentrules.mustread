# -*- coding: UTF-8 -*-
from collective.contentrules.mustread import _
from collective.contentrules.mustread.interfaces import ICanBeMarkedAsMustRead
from collective.contentrules.mustread.event import ReadConfirmationRequestEvent
from collective.contentrules.mustread.event import ReadReminderEvent
from collective.mustread.interfaces import ITracker
from plone import api
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope import event
from zope.component import getUtility
from zope.i18n import translate
from zope.i18nmessageid.message import Message

import datetime


class MustReadEnabled(BrowserView):
    """returns true if mustread actions
    (such as request read confirmations, mark as read)
    are  available on the context
    """

    def __call__(self):
        return ICanBeMarkedAsMustRead.providedBy(self.context)


class BaseView(BrowserView):

    def do_redirect(self):
        props = api.portal.get_tool('portal_properties').site_properties
        view_types = props.getProperty('typesUseViewActionInListings', [])
        url = self.context.absolute_url()
        if self.context.portal_type in view_types:
            url = url + '/view'
        self.request.response.redirect(url)


class RequestReadConfirmation(BaseView):
    """triggers a ReadConfirmationRequestEvent to notify
    contentrules engine
    """

    def __call__(self):
        event.notify(ReadConfirmationRequestEvent(self.context))
        self.do_redirect()


class MarkRead(BaseView):
    """marks context as read for currently logged in user
    """

    def __call__(self):
        tracker = getUtility(ITracker)
        tracker.mark_read(self.context)
        self.do_redirect()


class SendReminders(BaseView):
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

        self.do_redirect()


class ExpiredNotificationEmail(BrowserView):
    """remind the portal admin when people have open read requests.
    """
    template = ViewPageTemplateFile('expired_email.pt')

    # email address to send notification to, portal's admin address if empty
    RECIPIENT_EMAIL = ''

    SUBJECT = _(u'expired-mail-subject',
                default=u'Expired read requests')

    def __call__(self):
        tracker = getUtility(ITracker)
        items = tracker.what_to_read(context=self.context,
                                     force_deadline=True)
        data = []

        for item in items:
            users = tracker.who_did_not_read(
                item, force_deadline=True,
                deadline_before=datetime.datetime.utcnow())
            info = dict(item=item, users=[])
            for userid, deadline in users.iteritems():
                user = api.user.get(userid)
                info['users'].append(dict(
                    name=user.getProperty('fullname', u''),
                    email=user.getProperty('email'),
                    deadline=deadline))
            data.append(info)
        if len(data) == 0:
            # nothing to do
            return

        mail_text = self.template(
            self.context,
            self.request,
            data=data)
        portal = api.portal.get()
        email_charset = portal.getProperty('email_charset')
        mailhost = api.portal.get_tool('MailHost')
        from_address = portal.getProperty('email_from_address')
        if self.RECIPIENT_EMAIL:
            recipient = self.RECIPIENT_EMAIL
        else:
            recipient = from_address

        subject = self.SUBJECT
        if isinstance(subject, Message):
            subject = translate(subject, context=self.request)

        mailhost.send(
            messageText=mail_text,
            mto=recipient,
            mfrom=from_address,
            subject=subject,
            charset=email_charset)
