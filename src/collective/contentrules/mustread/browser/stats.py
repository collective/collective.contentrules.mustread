from Products.Five.browser import BrowserView
from cStringIO import StringIO
from collective.mustread.interfaces import ITracker
from datetime import date
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
            'Content-Disposition', 'attachment; filename="{}"'.format(fname))

        return csv.getvalue()
