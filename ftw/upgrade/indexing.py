import pkg_resources


HAS_INDEXING = False

try:
    # Plone 5
    from Products.CMFCore.indexing import processQueue
    from Products.CMFCore.indexing import getQueue
except ImportError:
    try:
        # Plone 4 with collective.indexing
        pkg_resources.get_distribution('collective.indexing')
    except pkg_resources.DistributionNotFound:
        def processQueue():
            # Plone 4 without collective.indexing
            pass
    else:
        from collective.indexing.queue import getQueue
        from collective.indexing.queue import processQueue
        HAS_INDEXING = True
else:
    HAS_INDEXING = True


if HAS_INDEXING:
    from ftw.upgrade.interfaces import IDuringUpgrade
    from ftw.upgrade.progresslogger import ProgressLogger
    from zope.globalrequest import getRequest

    class LoggingQueueProcessor(object):
        """Queue processor to log collective.indexing progress.

        A queue processor is used whenever a collective.indexing queue is
        processed, i.e. when collective.indexing indexes, reindexes or
        unindexes objects in the queue. This may happen several times while
        executing upgrades (e.g. every time when executing a catalog-query).

        For larger deployments with a lot of objects that process may take a
        while, thus we display a progress bar while reindexing.
        """
        should_log = False

        def begin(self):
            self.should_log = IDuringUpgrade.providedBy(getRequest())
            if not self.should_log:
                return

            indexing_queue_length = getQueue().length()
            self.logger = ProgressLogger(
                'Processing indexing queue',
                indexing_queue_length)

        def commit(self):
            pass

        def abort(self):
            pass

        def index(self, obj, attributes):
            if not self.should_log:
                return
            self.logger()

        def reindex(self, obj, attributes, update_metadata=False):
            if not self.should_log:
                return
            self.logger()

        def unindex(self, obj):
            if not self.should_log:
                return
            self.logger()
