# -*- coding: utf-8 -*-
from collective.contentrules.mustread import _
from collective.contentrules.mustread import config
from collective.contentrules.mustread.interfaces import IReadReminder
from collective.mustread.interfaces import ITracker
from datetime import datetime
from datetime import timedelta
from email.utils import formataddr
from OFS.SimpleItem import SimpleItem
from plone import api
from plone.app.contentrules.browser.formhelper import AddForm
from plone.app.contentrules.browser.formhelper import EditForm
from plone.contentrules.rule.interfaces import IExecutable
from plone.contentrules.rule.interfaces import IRuleElementData
from plone.stringinterp.interfaces import IContextWrapper
from plone.stringinterp.interfaces import IStringInterpolator
from zope import schema
from zope.component import adapts
from zope.component import getUtility
from zope.component.interfaces import IObjectEvent
from zope.formlib import form
from zope.i18nmessageid import MessageFactory
from zope.interface import implements
from zope.interface import Interface

import logging


logger = logging.getLogger('collective.contentrules.mustread')

_p = MessageFactory('plone')


class IMustReadAction(Interface):
    """Definition of the configuration available for a mustread action
    """

    source = schema.TextLine(
        title=_p(u'Email source'),
        description=_p(
            ('The email address that sends the email. If no email is '
             'provided here, it will use the portal from address.')),
        required=False)

    role = schema.Choice(
        title=_(u'field_role_title', default=u"Role"),
        description=_(
            u'field_role_description',
            default=(
                u"Select a role. The action will look up the all Plone site "
                u"users who explicitly have this role (also via groups) on the"
                u" object and send a message to their email address.")),
        vocabulary='collective.contentrules.mailtorole.roles',
        required=True)

    acquired = schema.Bool(
        title=_(u'field_acquired_title', default=u"Acquired Roles"),
        description=_(
            u'field_acquired_description',
            default=(
                u"Should users that have this role as an acquired role "
                u"also receive this email?")),
        required=False,
        default=config.DEFAULT_ACQUIRED_ROLES)

    global_roles = schema.Bool(
        title=_(u'field_global_roles_title', default=u"Global Roles"),
        description=_(
            u'field_global_roles_description',
            default=(
                u"Should users that have this role as a role in the "
                u"whole site also receive this email?")),
        required=False)

    notification_subject = schema.TextLine(
        title=_(u"Notification Subject"),
        description=_p(u"Subject of the message"),
        required=True,
        default=config.DEFAULT_NOTIFICATION_SUBJECT)

    notification_message = schema.Text(
        title=_(u"Notification Message"),
        description=_(
            u'field_message_description',
            default=(
                u"Type in here the message that you want to mail. Some "
                u"defined content can be replaced: ${title} will be replaced "
                u"by the title of the newly created item. ${url} will be "
                u"replaced by the URL of the newly created item.")),
        required=True,
        default=config.DEFAULT_NOTIFICATION_TEXT)

    reminder_subject = schema.TextLine(
        title=_(u"Reminder Subject"),
        description=_p(u"Subject of the message"),
        required=True,
        default=config.DEFAULT_REMINDER_SUBJECT)

    reminder_message = schema.Text(
        title=_(u"Reminder Message"),
        description=_(
            u'field_message_reminder_description',
            default=(
                u""
                u"leave empty to not send a reminder message")),
        required=False,
        default=config.DEFAULT_REMINDER_TEXT)

    deadline = schema.Int(
        title=_(u'label_deadline', default=u"Deadline Delay"),
        description=_(
            u'help_deadline',
            default=(
                u"Number of days a read requests must be confirmed within. "
                u"Will be used to compute the deadline of requests.")),
        required=True,
        default=config.DEFAULT_DEADLINE_DELAY
        )

    reminder_delay = schema.Int(
        title=_(u'label_reminder-delay', default=u"Reminder Delay"),
        description=_(
            u'help_reminder-delay',
            default=(
                u"Defines how many days before the deadline a "
                u"reminder email will be sent")),
        required=True,
        default=config.DEFAULT_REMINDER_DELAY
        )


class MustReadAction(SimpleItem):
    """
    The implementation of the action
    """
    implements(IMustReadAction, IRuleElementData)

    notification_subject = u''
    reminder_subject = u''
    source = u''
    role = u''
    notification_message = u''
    reminder_message = u''
    acquired = config.DEFAULT_ACQUIRED_ROLES
    global_roles = False
    deadline = config.DEFAULT_DEADLINE_DELAY
    reminder_delay = config.DEFAULT_REMINDER_DELAY
    element = 'plone.actions.MustRead'

    @property
    def summary(self):

        if self.reminder_message is None or (
                not self.reminder_message.strip()):
            return _(
                u'rule_description_noreminder',
                default=(
                    u"Request confirmation for users with role '${role}' "
                    u"on the object (deadline today + ${days} days, "
                    u"no reminder)"),
                mapping=dict(role=self.role,
                             days=self.deadline))
        return _(
            u'rule_description',
            default=(
                u"Request confirmation for users with role '${role}' on "
                u"the object (deadline today + ${days} days, reminder "
                u"${reminder} days before deadline)"),
            mapping=dict(role=self.role,
                         days=self.deadline,
                         reminder=self.reminder_delay))


class BaseExecutor(object):
    """Base Class for MustRead Executors"""

    @property
    def affected_users(self):
        """return users that match the contentrule's role filters"""
        obj = self.event.object
        recipients = set()

        # search through all local roles on the object, and add
        # userid to the recipients list if they have the local
        # role stored in the action
        local_roles = obj.get_local_roles()

        for user, roles in local_roles:
            rolelist = list(roles)
            if self.element.role in rolelist:
                recipients.add(user)

        # check for the acquired roles
        if self.element.acquired:
            sharing_page = obj.unrestrictedTraverse('@@sharing')
            acquired_roles = sharing_page._inherited_roles()
            try:
                acquired_roles += sharing_page._borg_localroles()
            except AttributeError:
                # ignore if method is missing
                pass
            acquired_users = [r[0] for r in acquired_roles
                              if self.element.role in r[1]]
            recipients.update(acquired_users)

        # check for the global roles
        if self.element.global_roles:
            pas = api.portal.get_tool('acl_users')
            rolemanager = pas.portal_role_manager
            global_role_ids = [
                p[0] for p in
                rolemanager.listAssignedPrincipals(self.element.role)]
            recipients.update(global_role_ids)

        # check to see if the recipients are users or groups
        group_ids = set()  # ids of affected groups - will be filtered out

        def _getGroupMemberIds(group):
            """Helper method to support groups in groups."""
            members = []
            for member_id in group.getGroupMemberIds():
                subgroup = api.group.get(member_id)
                if subgroup is not None:
                    members.extend(_getGroupMemberIds(subgroup))
                else:
                    members.append(member_id)
            return members

        for recipient in list(recipients):
            group = api.group.get(recipient)
            if group is not None:
                group_ids.add(recipient)
                recipients.update(_getGroupMemberIds(group))

        # remove group ids from recipients
        recipients.difference_update(group_ids)
        return sorted(recipients)

    def _send_mail(self, users, subject, text):
        mailhost = api.portal.get_tool('MailHost')
        portal = api.portal.get()

        # obtain email settings
        email_charset = portal.getProperty('email_charset')
        source = self.element.source
        if not source:
            # no source provided, looking for the site wide from email
            # address
            from_address = portal.getProperty('email_from_address')
            if not from_address:
                raise ValueError((
                    'You must provide a source address for this action or '
                    'enter an email in the portal properties'))
            from_name = portal.getProperty('email_from_name').strip('"')
            source = formataddr((from_name, from_address))

        # look up e-mail addresses for the found users
        for user in users:
            member = api.user.get(user)
            # check whether user really exists
            # before getting its email address
            if not member:
                logger.warn('non-existent user: ' + user)
                continue

            email = member.getProperty('email')
            if email is None or len(email) == 0:
                logger.warn('user without email address: ' + user)
                continue

            fullname = member.getProperty('fullname', '')
            recipient = formataddr((fullname, email))

            interpolator = self._get_interpolator(user)
            # Prepend interpolated message with \n to avoid interpretation
            # of first line as header.
            message = '\n' + interpolator(text)
            subject = interpolator(subject)

            mailhost.send(
                messageText=message,
                mto=recipient,
                mfrom=source,
                subject=subject,
                charset=email_charset)

    def _get_interpolator(self, userid):
        """adds a plone.stringinterp IContextWrapper
        around our event.object to add support for
        mustread_ variable substitution
        """
        obj = self.event.object
        tracker = getUtility(ITracker)
        deadlines = tracker.who_did_not_read(obj)
        deadline = deadlines.get(userid, None)
        if deadline:
            deadline = api.portal.get_localized_time(deadline, False)
        else:
            deadline = ''
        user = api.user.get(userid=userid)
        wrapped = IContextWrapper(obj)(
            mustread_deadline=deadline,
            mustread_fullname=user.getProperty('fullname'))
        return IStringInterpolator(wrapped)


class MustReadSendConfirmationExecutor(BaseExecutor):
    """schedules a read request for all users matching
    our role-filter on the event.object
    and notifies them via email

    registerd for iobjectevent so other contentrule events
    (i.e objectadded) can trigger our executor too.
    """
    implements(IExecutable)
    adapts(Interface, IMustReadAction, IObjectEvent)

    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):
        obj = self.event.object
        now = datetime.utcnow()
        deadline = now + timedelta(days=self.element.deadline)

        users = self.affected_users

        tracker = getUtility(ITracker)
        current_user = api.user.get_current().id
        new_users = tracker.schedule_must_read(obj, users, deadline,
                                               current_user)

        logger.info((
            'scheduled mustread on {path}, deadline '
            '{deadline:%Y-%m-%d %H:%M:%S} '
            'for {usercount} users: {users}').format(
                path='/'.join(obj.getPhysicalPath()),
                deadline=deadline,
                usercount=len(new_users),
                users=', '.join(new_users))
        )

        self._send_mail(new_users,
                        self.element.notification_subject,
                        self.element.notification_message)

        api.portal.show_message(_(
            u'msg-confirmation-requested',
            default=(
                u'Read confirmation requested by ${deadline} for ${count} '
                'users: ${userlist}'),
            mapping=dict(
                count=len(new_users),
                deadline=api.portal.get_localized_time(deadline, True),
                userlist=', '.join(new_users))),
            self.context.REQUEST,
            'info')


class MustReadReminderExecutor(BaseExecutor):
    """reminds users that have open read requests via email

    This can only be triggered by an IReadReminder event.
    (which is typically notified by the @@send-read-reminders view.

    .. ATTENTION::
        This reminderexecutor only compares the date of the deadline
        so it should only be called once a day to not send out multiple
        reminders for the same object.
        We might register different executors or add a parameter to
        the event to realize different behaviours at a later stage.
    """
    implements(IExecutable)
    adapts(Interface, IMustReadAction, IReadReminder)

    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):
        obj = self.event.object
        path = '/'.join(obj.getPhysicalPath())

        msg = self.element.reminder_message
        if not (msg and msg.strip()):
            logger.info((
                'no reminder message set, '
                'not sending a reminder to for {0}').format(path))
            return

        tracker = getUtility(ITracker)
        today = datetime.utcnow().date()
        remind_today = []
        too_early = []
        for userid, deadline in tracker.who_did_not_read(obj).iteritems():
            reminder_date = (
                deadline - timedelta(self.element.reminder_delay)).date()
            if reminder_date == today:
                remind_today.append(userid)
            if reminder_date > today:
                too_early.append((userid, deadline))

        if remind_today:
            logger.info(
                'sending {count} reminders for {path} to: {userlist}'.format(
                    count=len(remind_today), path=path,
                    userlist=', '.join(remind_today)
                ))
        if too_early:
            logger.info((
                u'too early to remind {count} users for {path}: '
                u'{userlist}').format(
                    count=len(too_early), path=path,
                    userlist=', '.join([
                        '{0}({1:%Y-%m-%d})'.format(*u) for u in too_early])
                    ))

        self._send_mail(remind_today, self.element.reminder_subject,
                        self.element.reminder_message)


form_description = _(
    u'form_description',
    default=(
        u"An action action that requests a read-confirmation from users who "
        u"have a role on the object")
    )


class MustReadAddForm(AddForm):
    """
    An add form for the mail action
    """
    form_fields = form.FormFields(IMustReadAction)
    label = _(u'title_addform', default=u"Add MustRead Action")
    description = form_description
    form_name = _p(u"Configure element")

    def create(self, data):
        a = MustReadAction()
        form.applyChanges(a, self.form_fields, data)
        return a


class MustReadEditForm(EditForm):
    """
    An edit form for the mail action
    """
    form_fields = form.FormFields(IMustReadAction)
    label = _(u'title_editform', default=u"Edit MustRead Action")
    description = form_description
    form_name = _p(u"Configure element")
