# -*- coding: utf-8 -*-
from Acquisition import aq_base
from Products.CMFPlone.tests.utils import MockMailHost
from Products.MailHost.interfaces import IMailHost
from Products.statusmessages.interfaces import IStatusMessage
from collective.contentrules.mustread import testing
from collective.contentrules.mustread.interfaces import IMustReadEvent
from collective.contentrules.mustread.interfaces import IReadConfirmationRequest
from collective.contentrules.mustread.interfaces import IReadReminder
from collective.mustread.testing import tempDb
from collective.mustread.tracker import Tracker
from datetime import datetime
from datetime import timedelta
from plone import api
from plone.app.testing import TEST_USER_NAME, TEST_USER_ID
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
import unittest
import zope.component
from AccessControl import Unauthorized
import csv
from StringIO import StringIO

class EventCatcher(object):

    def __init__(self):
        self.fired = []
        self.setUp()

    def setUp(self):
        zope.component.provideHandler(self.handle_event)

    def tearDown(self):
        zope.component.getSiteManager().unregisterHandler(self.handle_event)

    def reset(self):
        self.fired = []

    @zope.component.adapter(IMustReadEvent)
    def handle_event(self, event):
        self.fired.append(event)


class TestMustReadViews(unittest.TestCase):
    """Test the mustread content rule
    (test based on collective.contentrules.mailtorole)
    """

    layer = testing.COLLECTIVE_CONTENTRULES_MUSTREAD_INTEGRATION_TESTING

    def setUp(self):
        # setup mustread db for testing
        self.db = tempDb()
        self.tracker = Tracker()

        # register handler that catches all events
        self.event_catcher = EventCatcher()

        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        self.installer.installProduct('collective.contentrules.mustread')

        # replace mailhost
        self.portal._original_MailHost = self.portal.MailHost
        self.portal.MailHost = mailhost = MockMailHost('MailHost')
        sm = zope.component.getSiteManager(context=self.portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(mailhost, provided=IMailHost)

        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.folder = api.content.create(self.portal, 'Folder', title='Folder')
        self.page1 = api.content.create(
            self.folder, 'Document', title='Page 1')
        self.folder2 = api.content.create(self.portal, 'Folder',
                                          title='Folder 2')
        self.file1 = api.content.create(
            self.folder2, 'File', 'file1.txt', title='File 1')

        api.user.create('user1@plone.org', 'user1',
                        properties={'fullname': u'User One'})
        api.user.grant_roles('user1', obj=self.page1, roles=['Reader'])
        setRoles(self.portal, TEST_USER_ID, ['Member'])

    def tearDown(self):
        # restore mailhost
        self.portal.MailHost = self.portal._original_MailHost
        sm = zope.component.getSiteManager(context=self.portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(aq_base(self.portal._original_MailHost),
                           provided=IMailHost)

        self.event_catcher.tearDown()

    def test_request_review(self):
        """test if our view triggers the correct event"""
        # ordinary members must not access our view
        self.assertRaises(Unauthorized, self.page1.restrictedTraverse,
                          '@@request-read-confirmation')

        # site admins and managers have the proper permission
        setRoles(self.portal, TEST_USER_ID, ['Site Manager'])
        view = self.page1.restrictedTraverse('@@request-read-confirmation')
        view()
        self.assertEqual(len(self.event_catcher.fired), 1)

        event = self.event_catcher.fired[0]
        self.assertTrue(
            IReadConfirmationRequest.providedBy(event))
        self.assertEqual(event.object, self.page1)

        # for types listed in typesUseViewActionInListings
        # users get redirected to the view action
        view = self.file1.restrictedTraverse('@@request-read-confirmation')
        view()
        self.assertEqual(
            self.portal.REQUEST.response.headers['location'],
            'http://nohost/plone/folder-2/file1.txt/view')

    def test_send_reminder(self):
        # ordinary members must not access our view
        self.assertRaises(Unauthorized, self.folder.restrictedTraverse,
                          '@@send-read-reminders')

        # site admins and managers have the proper permission
        setRoles(self.portal, TEST_USER_ID, ['Site Manager'])

        # calling our view w/o open requests results in no events fired
        view = self.portal.restrictedTraverse('@@send-read-reminders')
        view()
        self.assertEqual(len(self.event_catcher.fired), 0)
        # a status message indicates if reminders have been sent
        messages = IStatusMessage(self.portal.REQUEST).show()
        self.assertEqual(
            messages[-1].message,
            u'No reminder event fired')

        # schedule a must read and test again
        deadline = datetime.utcnow() + timedelta(1)
        self.tracker.schedule_must_read(self.page1, ['user1'], deadline)
        view = self.portal.restrictedTraverse('@@send-read-reminders')
        view()
        self.assertEqual(len(self.event_catcher.fired), 1)
        event = self.event_catcher.fired[0]
        self.assertTrue(
            IReadReminder.providedBy(event))
        self.assertEqual(event.object, self.page1)
        # a status message indicates if reminders have been sent
        messages = IStatusMessage(self.portal.REQUEST).show()
        self.assertEqual(
            messages[-1].message,
            u'Reminder event fired for 1 objects: /plone/folder/page-1')

        # the send-read-reminder view is only checking objects within
        # it's context
        # calling it on folder-2 does not result in an events fired
        self.event_catcher.reset()
        view = self.folder2.restrictedTraverse('@@send-read-reminders')
        view()
        self.assertEqual(len(self.event_catcher.fired), 0)

    def test_stats_csv(self):
        # ordinary members must not access our view
        self.assertRaises(Unauthorized, self.folder.restrictedTraverse,
                          '@@read-statistic-csv')

        # site admins and managers have the proper permission
        setRoles(self.portal, TEST_USER_ID, ['Site Manager'])
        view = self.portal.restrictedTraverse('@@read-statistic-csv')

        # no db entries, only headers are returned
        result = view()
        f = StringIO(result)
        reader = csv.DictReader(f)
        self.assertEqual(
            reader.fieldnames,
            ['path', 'userid', 'read_at', 'deadline', 'scheduled_at',
             'scheduled_by', 'status', 'uid', 'type'])
        row_count = sum(1 for _ in reader)
        self.assertEqual(row_count, 0)

        # create a db entry and call our view again
        self.tracker.mark_read(self.page1, 'user1',
                               datetime(2017, 4, 12, 13, 0))
        result = view()
        f = StringIO(result)
        reader = csv.DictReader(f)
        lines = [line for line in reader]
        self.assertEqual(len(lines), 1)
        self.assertDictContainsSubset(dict(
            status='read',
            read_at='2017-04-12 13:00:00',
            userid='user1',
            path='/plone/folder/page-1'),
            lines[0])

        # the view is context, dependent, and returns only db entries for
        # objects within the current context
        view = self.folder2.restrictedTraverse('@@read-statistic-csv')
        result = view()
        f = StringIO(result)
        reader = csv.DictReader(f)
        lines = [line for line in reader]
        self.assertEqual(len(lines), 0)
