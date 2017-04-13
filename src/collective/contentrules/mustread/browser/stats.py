# -*- coding: utf-8 -*-
from collective.mustread.interfaces import ITracker
from cStringIO import StringIO
from datetime import date
from Products.Five.browser import BrowserView
from zope.component import getUtility


class CSVExport(BrowserView):

    def __call__(self):

        tracker = getUtility(ITracker)

        csv = StringIO()
        tracker.get_stats_csv(csv, self.context)
        fname = 'must-read-{date:%Y-%m-%d}-{path}'.format(
            date=date.today(),
            path='-'.join(self.context.getPhysicalPath()))
        self.request.response.setHeader('Content-Type', 'text/csv')
        self.request.response.setHeader(
            'Content-Disposition', 'attachment; filename="{0}"'.format(fname))

        return csv.getvalue()
