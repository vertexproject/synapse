import logging
import synapse.telepath as s_telepath
import synapse.lib.service as s_service

logger = logging.getLogger(__name__)

class Parser:
    '''
    Parser provides a base implementation for processing parsing jobs in Dendrite.

    The Parser is intended to be used by sub-classes for the handling of basic operations required for processing jobs
    in Dendrite. Sub-classes must implement ``register`` to register a MIME type of interest with a specific queue
    name. Some care should be taken to ensure that queue names do not collide on a given deployment.

    Keyword Arguments:
        svcbus (str):
            URL for the SvcBus service that is used to locate the Coordinator and Jobs services.

        coordinator (str):
            The name that the Coordinator service is shared as on the SvcBus.

        jobs (str):
            The name that the Jobs service is shared as on the SvcBus.

    Raises:
        TypeError:
            If one of 'svcbus', 'coordinator', 'jobs' kwargs are not provided.
    '''
    _REQUIRED_ARGS = set(('svcbus', 'coordinator', 'jobs'))

    def __init__(self, **kwargs):
        self.opts = kwargs
        self._assertOpts()
        self.svcbus = s_telepath.openurl(self.opts.get('svcbus'))
        self.proxy = s_service.SvcProxy(self.svcbus)
        self.coordinator = self.proxy.getNameProxy(self.opts.get('coordinator'))
        self.jobs = self.proxy.getNameProxy(self.opts.get('jobs'))

    def register(self, mimeType, queue):
        '''
        Register a MIME type to queue name with the Dendrite Coordinator.

        As a part of the registration process, a listener is attached to the ``'dendrite:jobs:%s' % queue`` in order
        to detect when jobs become available for processing.

        Args:
            mimeType (str):
                The MIME type as is returned by filemagic with the MAGIC_MIME_TYPE flag set. For more
                information, see: https://filemagic.readthedocs.io/en/latest/api.html.

            queue (str):
                The name of the queue for the Coordinator to put jobs on.
        '''
        logger.info('registering %s => %s, and svcbus event: %s', mimeType, queue, self._eventName(queue))
        self.coordinator.register(mimeType, queue)
        self.svcbus.on(self._eventName(queue), self._processEvent)

    def unregister(self, mimeType, queue):
        '''
        Unregister a MIME type to queue name mapping with the Dendrite Coordinator.

        Removes the MIME type to queue name mapping that the Coordinator uses to enqueue jobs. This has a system wide
        impact and individual Parsers should use care when calling this method, as there may be other parser instances
        running that expect the registration to exist.

        Args:
            mimeType (str):
                The MIME type as is returned by filemagic with the MAGIC_MIME_TYPE flag set. For more
                information, see: https://filemagic.readthedocs.io/en/latest/api.html.

            queue (str):
                The name of the queue to unregister.
        '''
        logger.info('unregistering %s => %s, and svcbus event: %s', mimeType, queue, self._eventName(queue))
        self.coordinator.unregister(mimeType, queue)
        self.svcbus.off(self._eventName(queue), self._processEvent)

    def process(self, queue, job):
        '''
        Process a parse job.

        This method invokes the internal method '_process', which should be overridden by sub-classes. The typical
        implementation should involve actions such as reading the bytes from the Axon service, parse the bytes, and
        store results in a Cortex. If an exception occurs during the processing and the exception is allowed to
        propagate out of the process method, the job will be moved to a 'failed' status.

        Args:
            queue (str):
                Name of the queue that the job came from.

            job (dict):
                Dict containing properties of the job.
        '''
        self._process(queue, job)

    def processAll(self, queue):
        '''
        Process all jobs in specified queue.

        Process all parser jobs in the specified queue. When an event is received, this method is invoked to process
        all outstanding jobs. Depending on implementation of Parser Sub-classes, it may be desirable to call this 
        method explicitly during startup to process any existing jobs.

        Args:
            queue (str):
                Name of the queue to process jobs from.
        '''
        job = self.jobs.get(queue)
        while job:
            try:
                self.process(queue, job)
                self.jobs.complete(job)
            except:
                self.jobs.fail(job)
            job = self.jobs.get(queue)

    def _process(self, queue, job):
        raise NotImplementedError("Parser._process needs to be implemented by subclass")

    def _processEvent(self, mesg):
        queue = mesg[1].get('queue')
        logger.info('Parser received event', mesg[1])
        self.processAll(queue)

    def _assertOpts(self):
        if not Parser._REQUIRED_ARGS.issubset(self.opts):
            raise TypeError("kwargs missing required args: %s" % (Parser._REQUIRED_ARGS - set(self.opts.keys())))

    def _eventName(self, queue):
        return 'dendrite:jobs:%s' % queue
