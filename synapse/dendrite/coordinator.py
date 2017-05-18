import time
import logging
import magic
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath
import synapse.lib.service as s_service

logger = logging.getLogger(__name__)

class Coordinator:
    '''
    Coordinator listens to file:bytes tufo changes and coordinates jobs for parsers.

    Dendrite provides a distributed file parsing queue subsystem for Synapse. The Coordinator, Jobs, and Parser objects
    were designed to be run as independent processes(dmon) via a distributed deployment. The EventBus is the primary
    means of driving interactions between components. The Coordinator listens for file:bytes tufo changes from a
    cortex that is recommended to have an axon associated with it via the axon:url option. The Coordinator then adds a
    Parser job to the queue via the Jobs service. When a Parser comes online, it registers a mimeType => queue mapping
    with the Coordinator that is used to determine where to enqueue the job. After the Coordinator adds the job to a
    queue, it fires a queue specific event via the ServiceBus' EventBus. Any Parsers registered for that queue receive
    the event and attempt to dequeue the job from the Jobs service. After processing the job, the job is moved to a
    completed status. There can be multiple Parsers online for a given queue, as they will all work independently to
    drain the queue without duplicating work.

    Keyword Arguments:
        svcbus (str):
            URL for the SvcBus service that is used to locate the Cortex, Axon, and Jobs services.

        core (str):
            The name that the Cortex is shared as on the SvcBus. The Cortex must be shared with a 'link'
            property that is set with the URL that the Cortex is listening on. This is needed so that the
            Coordinator can connect directly to the Cortex for listening to the tufo change events.

        axon (str):
            The name that the Axon is shared as on the SvcBus. The Axon must be shared with a 'link'
            property that is set with the URL that the Cortex is listening on. This is needed so that the
            Coordinator can connect directly to the Axon for looking up and reading axon nodes.

        jobs (str):
            The name that the Jobs service is shared as on the SvcBus.

        mintime (int):
            Timestamp represented as milliseconds since the epoch. When specified, all file:bytes tufos
            created since this time will be processed on startup. This is useful for ensuring that any
            work that would have been processed during Coordinator downtime is accounted for.

    Raises:
        TypeError:
            If one of 'svcbus', 'core', 'axon', 'jobs' kwargs are not provided.

        synapse.exc.NoSuchObj:
            If the Coordinator is unable to connect to the Cortex, Axon, or Jobs services.

    '''
    _REQUIRED_ARGS = set(('svcbus', 'core', 'axon', 'jobs'))
    _BYTES_TO_READ = 1024

    def __init__(self, **kwargs):
        self.opts = kwargs
        self._assertOpts()
        self.svcbus = s_service.openurl(self.opts.get('svcbus'))
        coreSvc = self.svcbus.getSynSvcByName(self.opts.get('core'))
        self.listenCore = s_telepath.openurl(coreSvc[1].get('link'))
        axonSvc = self.svcbus.getSynSvcByName(self.opts.get('axon'))
        self.axonLink = axonSvc[1].get('link')
        self.axon = s_telepath.openurl(self.axonLink)
        self.jobs = self.svcbus.getNameProxy(self.opts.get('jobs'))
        self._assertConnected()
        self._registerListeners()
        self._initCortex()
        self._initState()
        self._processExistingTufos()

    def register(self, mimeType, queue):
        '''
        Registers a MIME type with a queue name.

        This method is intended to be called remotely via Telepath by the individual Parsers. When a Parser comes
        online, it should call this method to register the MIME type that it is interested in Parsing. The queue name
        can be any value, however, care should be taken that queue names do not collide unintentionally in a given
        deployment.

        Args:
            mimeType (str):
                The MIME type as is returned by filemagic with the MAGIC_MIME_TYPE flag set. For more
                information, see: https://filemagic.readthedocs.io/en/latest/api.html.

            queue (str):
                The name of the queue to enqueue Parser jobs for this MIME type on.

        '''
        if not self.isRegistered(mimeType, queue):
            logger.debug('Registering mime: %s, queue: %s', mimeType, queue)
            self.core.formTufoByProp('dendrite:coordinator', self._guid(mimeType, queue), mime=mimeType, queue=queue)
        else:
            logger.debug('Registration already exists for mime: %s, queue: %s', mimeType, queue)

    def unregister(self, mimeType, queue):
        '''
        Remove a MIME type to queue name mapping that was created by calling 'register'.

        This method is intended to be called remotely via Telepath by the individual Parsers. When a Parser comes
        online, it should call this method to register the MIME type that it is interested in Parsing. The queue name
        can be any value, however, care should be taken that queue names do not collide unintentionally in a given
        deployment.

        Args:
            mimeType (str):
                The MIME type as is returned by filemagic with the MAGIC_MIME_TYPE flag set. For more
                information, see: https://filemagic.readthedocs.io/en/latest/api.html.

            queue (str):
                The name of the queue to enqueue Parser jobs for this MIME type on.

        '''
        tufo = self._registration(mimeType, queue)
        if tufo:
            logger.debug('Unregistering mime: %s, queue: %s', mimeType, queue)
            self.core.delTufo(tufo)
        else:
            logger.debug('Registration does not exist for mime: %s, queue: %s', mimeType, queue)

    def isRegistered(self, mimeType, queue):
        '''
        Determine if a MIME type to queue name mapping exists.

        Args:
            mimeType (str):
                The MIME type as is returned by filemagic with the MAGIC_MIME_TYPE flag set. For more
                information, see: https://filemagic.readthedocs.io/en/latest/api.html.

            queue (str):
                The name of the queue to enqueue Parser jobs for this MIME type on.

        Returns:
            bool: True if a MIME type to queue name mapping exists, False otherwise.
        '''
        return self._registration(mimeType, queue) != None

    def queues(self, mimeType):
        '''
        Returns the queue names for which a MIME type is registered.

        While there can only exist one registration for a given MIME type and queue name, there can be many associated
        queue names for a given MIME type. This method is used to find all the queue names that are associated with a
        specified MIME type.

        Args:
            mimeType (str):
                The MIME type as is returned by filemagic with the MAGIC_MIME_TYPE flag set. For more
                information, see: https://filemagic.readthedocs.io/en/latest/api.html.

        Returns:
            list: A list of queue names, or an empty list if none are found.
        '''
        queues = []
        for tufo in self.core.getTufosByProp('dendrite:coordinator:mime', mimeType):
            queues.append(tufo[1].get('dendrite:coordinator:queue'))
        return queues

    def _guid(self, mimeType, queue):
        return s_common.guid('%s:%s' % (mimeType, queue))

    def _registration(self, mimeType, queue):
        return self.core.getTufoByProp('dendrite:coordinator', self._guid(mimeType, queue))

    def _registerListeners(self):
        self.listenCore.on('tufo:add:file:bytes', self._fileAdded)
        self.listenCore.on('tufo:props:file:bytes', self._fileUpdated)

    def _fileAdded(self, mesg):
        tufo = mesg[1].get('tufo')
        logger.debug('Received file added event: %s', tufo)
        self._processTufo(tufo)

    def _fileUpdated(self, mesg):
        tufo = mesg[1].get('tufo')
        logger.debug('Received file updated event: %s', tufo)
        self._processTufo(tufo)

    def _processTufo(self, tufo):
        self._updateState()
        guid = tufo[1].get('file:bytes')
        blob = self.axon.byiden(guid)
        blob[1]['axon:blob:size'] = min(Coordinator._BYTES_TO_READ, tufo[1].get('file:bytes:size'))
        bytes = b''.join(self.axon.iterblob(blob))
        mimeType = self._getMimeType(bytes)
        logger.debug('Detected mime: %s for guid: %s', mimeType, guid)
        job = {'axon': self.axonLink, 'guid': guid, 'mime': mimeType}
        for queue in self.queues(mimeType):
            logger.debug('Adding job:put in queue %s', queue)
            self.jobs.put(queue, job)

    def _getMimeType(self, bytes):
        mimeType = None
        with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as mimer:
            try:
                mimeType = mimer.id_buffer(bytes)
            except magic.MagicError as e:
                logger.error('Error determining mime type %s', e)
        return mimeType

    def _assertOpts(self):
        if not Coordinator._REQUIRED_ARGS.issubset(self.opts):
            raise TypeError("kwargs missing required args: %s" % (Coordinator._REQUIRED_ARGS - set(self.opts.keys())))

    def _assertConnected(self):
        try:
            self.listenCore.getTufoByIden('')
            logger.info('Successfully connected to cortex')
        except s_exc.NoSuchObj:
            raise s_exc.NoSuchObj(msg='unable to connect to cortex, please check url')
        try:
            self.axon.alloc(0)
            logger.info('Successfully connected to axon')
        except s_exc.NoSuchObj:
            raise s_exc.NoSuchObj(msg='unable to connect to axon, please check url')
        try:
            self.jobs.isEmpty('')
            logger.info('Successfully connected to job queue')
        except s_exc.NoSuchObj:
            raise s_exc.NoSuchObj(msg='unable to connect to job queue, please check url')

    def _initCortex(self):
        coreurl = self.opts.get('interncore', 'ram:///')
        logger.debug('Managing parser registrations via internal cortex with url %s', coreurl)
        self.core = s_cortex.openurl(coreurl)
        self.core.addTufoForm('dendrite:coordinator', ptype='guid')
        self.core.addTufoProp('dendrite:coordinator', 'mime', ptype='str', req=True)
        self.core.addTufoProp('dendrite:coordinator', 'queue', ptype='str', req=True)

        self.core.addTufoForm('dendrite:state', ptype='guid')
        self.core.addTufoProp('dendrite:state', 'mintime', ptype='int')

    def _initState(self):
        self.state = self.core.getTufoByProp('dendrite:state', self._stateGuid())
        mintime = self.opts.get('mintime')
        if not self.state:
            if not mintime:
                mintime = int(time.time() * 1000)
            self.state = self.core.formTufoByProp('dendrite:state', self._stateGuid(), mintime=mintime)
        elif mintime:
            self.core.setTufoProps(self.state, mintime=mintime)

    def _updateState(self):
        # currently, the tstamp on a tufo is only set when a tufo is created, and not when a prop is updated. For now
        # just record current time as a point of return on restart... there may exist tufos that had prop updates during
        # down time, but at least all new tufos will be processed.
        self.core.setTufoProps(self.state, mintime=int(time.time() * 1000))

    def _stateGuid(self):
        return s_common.guid('coordinator')

    def _processExistingTufos(self):
        mintime = self.state[1].get('dendrite:state:mintime')
        tufos = self.listenCore.getTufosByProp('file:bytes', mintime=mintime)
        logger.info('Processing existing file:bytes tufos: found %s records using mintime %s', len(tufos), mintime)
        for tufo in tufos:
            self._processTufo(tufo)
