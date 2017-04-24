# -*- coding: utf-8 -*-
from collective.mustread.interfaces import ITracker
from cStringIO import StringIO
from datetime import date
from Products.Five.browser import BrowserView
from zope.component import getUtility


class CSVExport(BrowserView):

    # allows to customize exported columns in subclasses
    fieldnames = []

    @property
    def filename(self):
        return 'must-read-{date:%Y-%m-%d}-{path}.csv'.format(
            date=date.today(),
            path='-'.join(self.context.getPhysicalPath()))

    def __call__(self):

        tracker = getUtility(ITracker)

        csv = StringIO()
        tracker.get_report_csv(csv, self.context, fieldnames=self.fieldnames)
        self.request.response.setHeader('Content-Type', 'text/csv')
        self.request.response.setHeader(
            'Content-Disposition', 'attachment; filename="{0}"'.format(
                self.filename))

        return csv.getvalue()
