# -*- coding: utf-8 -*-
from Acquisition import aq_base
from collective.contentrules.mustread import config
from collective.contentrules.mustread.actions.mail import MustReadAction
from collective.contentrules.mustread.actions.mail import MustReadAddForm
from collective.contentrules.mustread.actions.mail import MustReadEditForm
from collective.contentrules.mustread.actions.mail import MustReadReminderExecutor  # noqa
from collective.contentrules.mustread.actions.mail import MustReadSendConfirmationExecutor  # noqa
from collective.contentrules.mustread.event import ReadReminderEvent
from collective.contentrules.mustread.testing import COLLECTIVE_CONTENTRULES_MUSTREAD_INTEGRATION_TESTING  # noqa
from collective.mustread.testing import tempDb
from collective.mustread.tracker import Tracker
from datetime import datetime
from datetime import time
from datetime import timedelta
from email import message_from_string
from plone import api
from plone.app.contentrules.rule import Rule
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.contentrules.engine.interfaces import IRuleStorage
from plone.contentrules.rule.interfaces import IExecutable
from plone.contentrules.rule.interfaces import IRuleAction
from Products.CMFPlone.tests.utils import MockMailHost
from Products.MailHost.interfaces import IMailHost
from Products.statusmessages.interfaces import IStatusMessage
from zope.component import getMultiAdapter
from zope.component import getSiteManager
from zope.component import getUtility
from zope.component.interfaces import IObjectEvent
from zope.interface import implements

import re
import unittest


class DummyEvent(object):
    """Event representing any content-rule related event,
    not mustread specific"""
    implements(IObjectEvent)

    def __init__(self, object):
        self.object = object


class TestMustReadContentRule(unittest.TestCase):
    """Test the mustread content rule
    (test based on collective.contentrules.mailtorole)
    """

    layer = COLLECTIVE_CONTENTRULES_MUSTREAD_INTEGRATION_TESTING

    def setUp(self):
        # setup mustread db for testing
        self.db = tempDb()
        self.tracker = Tracker()

        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        self.installer.installProduct('collective.contentrules.mustread')

        # replace mailhost
        # this needs a new version of plone.app.testing:
        # see https://github.com/plone/plone.app.testing/pull/40
        self.portal._original_MailHost = self.portal.MailHost
        self.portal.MailHost = mailhost = MockMailHost('MailHost')
        sm = getSiteManager(context=self.portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(mailhost, provided=IMailHost)

        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.folder = api.content.create(self.portal, 'Folder', title='Folder')
        self.page1 = api.content.create(
            self.folder, 'Document', title='Page 1')

        user1 = api.user.create('user1@plone.org', 'user1',
                                properties={'fullname': u'User 1 Fullname'})
        user2 = api.user.create('user2@plone.org', 'user2',
                                properties={'fullname': u'John Döe'})
        group1 = api.group.create('group1')
        api.group.add_user(group=group1, user=user1)
        group2 = api.group.create('group2')
        api.group.add_user(group=group2, user=user2)
        api.group.create(
            'mega', u'Mega Group',
            description=u'Group containing group1 and group2',
            groups=['group1', 'group2'])

    def tearDown(self):
        # restore mailhost
        self.portal.MailHost = self.portal._original_MailHost
        sm = getSiteManager(context=self.portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(aq_base(self.portal._original_MailHost),
                           provided=IMailHost)

    def test_registered(self):
        element = getUtility(IRuleAction, name='plone.actions.MustRead')
        self.assertEqual('plone.actions.MustRead', element.addview)
        self.assertEqual('edit', element.editview)
        self.assertEqual(None, element.for_)
        self.assertEqual(IObjectEvent, element.event)

    def test_addview(self):
        element = getUtility(IRuleAction, name='plone.actions.MustRead')
        storage = getUtility(IRuleStorage)
        storage[u'foo'] = Rule()
        rule = self.portal.restrictedTraverse('++rule++foo')

        adding = getMultiAdapter((rule, self.portal.REQUEST), name='+action')
        addview = getMultiAdapter((adding, self.portal.REQUEST),
                                  name=element.addview)
        self.assertTrue(isinstance(addview, MustReadAddForm))

        addview.createAndAdd(data=dict(
            notification_subject=config.DEFAULT_NOTIFICATION_SUBJECT,
            reminder_subject=config.DEFAULT_REMINDER_SUBJECT,
            role=u'Owner',
            notification_message=config.DEFAULT_NOTIFICATION_TEXT,
            reminder_message=config.DEFAULT_REMINDER_TEXT,
            acquired=config.DEFAULT_ACQUIRED_ROLES,
            deadline=config.DEFAULT_DEADLINE_DELAY,
            reminder_delay=config.DEFAULT_REMINDER_DELAY,
        ))

        e = rule.actions[0]
        self.assertTrue(isinstance(e, MustReadAction))
        self.assertEqual(u'Read request', e.notification_subject)
        self.assertEqual(u'Reminder: read request', e.reminder_subject)
        self.assertTrue(u'Dear ${mustread_fullname}' in e.notification_message)
        self.assertTrue(u'please make sure to read' in e.reminder_message)
        self.assertEqual(5, e.deadline)
        self.assertEqual(2, e.reminder_delay)
        self.assertEqual(u'', e.source)
        self.assertEqual(u'Owner', e.role)
        self.assertEqual(True, e.acquired)
        self.assertEqual(False, e.global_roles)

    def test_editview(self):
        element = getUtility(IRuleAction, name='plone.actions.MustRead')
        e = MustReadAction()
        editview = getMultiAdapter((e, self.portal.REQUEST),
                                   name=element.editview)
        self.assertTrue(isinstance(editview, MustReadEditForm))

    def test_affected_users(self):
        """test computation of affected users via local roles
        (acquired and not) and global_roles
        """
        e = MustReadAction()
        e.role = 'Reader'
        e.acquired = False
        e.global_roles = False
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.page1)),
                             IExecutable)
        self.assertTrue(isinstance(ex, MustReadSendConfirmationExecutor))

        # no user has reader role
        self.assertEqual(0, len(ex.affected_users))

        # reader role acquired, but action.acquired=False
        api.user.grant_roles(username='user1', obj=self.folder,
                             roles=['Reader'])
        self.assertEqual(0, len(ex.affected_users))

        # reader role directly on object
        api.user.grant_roles(username='user2', obj=self.page1,
                             roles=['Reader'])
        self.assertEqual(ex.affected_users, ['user2'])

        # set action.acquired=False, both users should be returned
        e.acquired = True
        self.assertEqual(sorted(ex.affected_users), ['user1', 'user2'])

        # test global roles
        e.role = 'Editor'
        e.global_roles = True
        self.assertEqual(0, len(ex.affected_users))
        api.user.grant_roles('user1', roles=['Editor'])
        self.assertEqual(ex.affected_users, ['user1'])

    def test_affected_groups(self):
        """test computation of affected users via groups
        """
        e = MustReadAction()
        e.role = 'Reader'
        e.acquired = False
        e.global_roles = False
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.page1)),
                             IExecutable)

        # make group1, readers, user1 should be affected
        self.assertEqual(0, len(ex.affected_users))
        api.group.grant_roles('group1', obj=self.page1, roles=['Reader'])
        self.assertEqual(ex.affected_users, ['user1'])

        # make megagroup editors, both users should be affected
        e.role = 'Editor'
        e.acquired = True
        self.assertEqual(0, len(ex.affected_users))
        api.group.grant_roles('mega', obj=self.page1, roles=['Editor'])
        self.assertEqual(sorted(ex.affected_users), ['user1', 'user2'])

    def test_stringinterp(self):
        """test if mustread_ placeholders for plone.stringinterp work
        for the mustread-executors"""
        e = MustReadAction()
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.page1)),
                             IExecutable)

        interpolator = ex._get_interpolator('user1')

        self.assertEqual(interpolator(u'Hello ${mustread_fullname}'),
                         u'Hello User 1 Fullname')

        self.assertEqual(
            interpolator(u'url: ${mustread_url}'),
            'url: http://nohost/plone/folder/page-1/@@mark-read')

        # we need a mustread db entry for this user and page in order to
        # obtain the deadline
        self.assertEqual(interpolator(u'deadline: ${mustread_deadline}'),
                         'deadline: ')
        self.tracker.schedule_must_read(self.page1, ['user1'],
                                        datetime(2017, 4, 12, 13, 00))
        interpolator = ex._get_interpolator('user1')
        self.assertEqual(interpolator(u'deadline: ${mustread_deadline}'),
                         'deadline: Apr 12, 2017')

    def test_email(self):
        """test sending of emails

        * no source email given, use portal settings
        * string interpolation
        """
        e = MustReadAction()
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.page1)),
                             IExecutable)

        self.assertRaises(ValueError, ex._send_mail,
                          users=['user1'], subject='Subject', text='Text')

        # if we provide a site mail address this won't fail anymore
        sm = getSiteManager(context=self.portal)
        sm.manage_changeProperties({'email_from_address': 'admin@site.com',
                                    'email_from_name': 'Website Adminstratör'})
        ex._send_mail(['user1'],
                      u'Notification for ${mustread_fullname}',
                      u'Please read ${mustread_url}')

        messages = self.portal.MailHost.messages
        msg = message_from_string(messages[0])
        # from address is the one we defined on the portal
        self.assertEqual(
            msg['From'],
            '=?utf-8?q?Website_Adminstrat=C3=B6r?= <admin@site.com>')
        self.assertEqual(msg['Subject'],
                         '=?utf-8?q?Notification_for_User_1_Fullname?=')

    def test_confirmation_executor(self):
        """test if mustread entries are created and
        the correct users receive an email
        """
        e = MustReadAction()
        e.role = 'Reader'
        e.acquired = True
        e.global_roles = False
        e.deadline = 10
        e.notification_subject = u'Please read ${title}'
        e.notification_message = (
            u'Dear ${mustread_fullname}\nPlease read ${mustread_url} '
            u'by ${mustread_deadline} the latest.')
        e.source = '"Administrator" <admin@portal.com>'
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.page1)),
                             IExecutable)

        api.user.grant_roles('user1', obj=self.page1, roles=['Reader'])
        api.user.grant_roles('user2', obj=self.folder, roles=['Reader'])

        # no mustreads sheduled for our document
        self.assertEqual(len(self.tracker.who_did_not_read(self.page1)), 0)

        # execute
        ex()

        # 2 mustreads have been scheduled
        self.assertEqual(sorted(
            self.tracker.who_did_not_read(self.page1).keys()),
            ['user1', 'user2'])
        # the deadline is 10 days from today on
        deadline = datetime.utcnow() + timedelta(10)
        self.assertEqual(
            self.tracker.who_did_not_read(self.page1)['user1'].date(),
            deadline.date())

        # the user that invoked the action gets feedback in a status message
        messages = IStatusMessage(self.folder.REQUEST).show()  # noqa
        self.assertEqualEllipsis(
            messages[0].message,
            u'Read confirmation requested by ... for 2 users: user1, user2')

        # a notification has been sent to both users.
        messages = self.portal.MailHost.messages
        self.assertEqual(len(messages), 2)

        msg1 = message_from_string(messages[0])
        self.assertEqual(msg1['To'],
                         u'User 1 Fullname <user1@plone.org>')

        msg2 = message_from_string(messages[1])
        # from address is the one we defined as source
        self.assertEqual(msg2['From'],
                         'Administrator <admin@portal.com>')
        self.assertEqual(msg2['To'],
                         u'=?utf-8?q?John_D=C3=B6e?= <user2@plone.org>')
        self.assertEqual(msg2['Subject'],
                         '=?utf-8?q?Please_read_Page_1?=')

        self.assertEqualEllipsis(
            msg2.get_payload(),
            (u'Dear John D=C3=B6e\nPlease read '
             u'http://nohost/plone/folder/page-1/@@mark-read '
             u'by ... t=\nhe latest.'))

    def test_reminder(self):
        """
        - no text - no reminder
        - correct date computation
        """
        e = MustReadAction()
        e.role = 'Reader'
        e.reminder_delay = 2
        e.reminder_subject = u'Reminder, please read ${title}'
        e.reminder_message = (
            u'Dear ${mustread_fullname}\nPlease do not forget to '
            u'read ${mustread_url} by ${mustread_deadline} the latest.')
        e.source = '"Administrator" <admin@portal.com>'
        ex = getMultiAdapter((self.folder, e, ReadReminderEvent(self.page1)),
                             IExecutable)

        self.assertTrue(isinstance(ex, MustReadReminderExecutor))

        # create a mustread entry for user1 with
        # deadline 23:59:59 in 3 days
        # and user2 at 00:00:00 in 3 days
        dl1 = datetime.combine(datetime.utcnow(), time.max) + timedelta(3)
        dl2 = datetime.combine(datetime.utcnow(), time.min) + timedelta(3)
        self.tracker.schedule_must_read(self.page1, ['user1'], dl1)
        self.tracker.schedule_must_read(self.page1, ['user2'], dl2)
        # and another one at a later point for another user
        api.user.create('user3@plone.org', 'user3')
        self.tracker.schedule_must_read(self.page1, ['user3'],
                                        dl2 + timedelta(1))
        # as our reminder_delay is 2 days before the deadline and
        # the deadline is today+3 days no reminders will be triggered
        ex()

        messages = self.portal.MailHost.messages
        self.assertEqual(len(messages), 0)

        # we change the reminder_delay to 3 days, now reminders are sent out
        e.reminder_delay = 3
        ex()
        messages = self.portal.MailHost.messages
        self.assertEqual(len(messages), 2)
        msg = message_from_string(messages[0])
        self.assertEqual(msg['To'],
                         '=?utf-8?q?John_D=C3=B6e?= <user2@plone.org>')
        msg = message_from_string(messages[1])
        self.assertEqual(msg['To'],
                         'User 1 Fullname <user1@plone.org>')

        # empty the message list
        del self.portal.MailHost.messages[:]
        self.assertEqual(len(messages), 0)

        # change the reminder deadline to 4 days before the deadline.
        # now only user3 gets a reminder
        e.reminder_delay = 4
        ex()
        messages = self.portal.MailHost.messages
        self.assertEqual(len(messages), 1)
        msg = message_from_string(messages[0])
        self.assertEqual(msg['To'],
                         'user3@plone.org')

        # if no reminder message is set, no reminder is sent
        e.reminder_message = u''
        del self.portal.MailHost.messages[:]
        ex()
        self.assertEqual(len(messages), 0)

    def assertEqualEllipsis(self, first, second,
                            ellipsis_marker='...', msg=None):
        """
        Example :
            >>> self.assertEqualEllipsis('foo123bar', 'foo...bar')
        """
        if ellipsis_marker not in second:
            return first == second

        if (
            re.match(
                re.escape(second).replace(re.escape(ellipsis_marker), '(.*?)'),
                first,
                re.M | re.S
            ) is None
        ):
            self.assertMultiLineEqual(
                first,
                second,
                msg
            )
