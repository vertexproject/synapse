import json
import logging
import collections
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

logger = logging.getLogger(__name__)

class Jobs(s_eventbus.EventBus):
    '''
    Jobs provides a simple remote queue for managing Parser jobs in Dendrite.

    Parser jobs are added to named queues, an event is fired on the Service Bus, the Parsers registered for
    the named queue receive the event and proceed to retrieve the job for processing. Basic job lifecycle management
    is provided where a job can be in one of the following states: queued, working, and completed.

    Args:
        core (str):
            URL of the Cortex to be used for internal management of the job queues.

        svcbus (str):
            URL of the SvcBus that events will be emitted on.
    '''
    _EMPTY_STR = ''

    def __init__(self, core, svcbus):
        s_eventbus.EventBus.__init__(self)
        self.core = s_cortex.openurl(core)
        self.core.addTufoForm('dendrite:job', ptype='guid')
        self.core.addTufoProp('dendrite:job', 'link', ptype='str', defval=Jobs._EMPTY_STR)
        self.core.addTufoProp('dendrite:job', 'queue', ptype='str', req=True)
        self.core.addTufoProp('dendrite:job', 'data', ptype='str', req=True)
        self.core.addTufoProp('dendrite:job', 'status', ptype='str', req=True)
        self.core.addTufoProp('dendrite:job', 'failed_at', ptype='time', req=True)
        self.core.addTufoProp('dendrite:job', 'queued_at', ptype='time', req=True)
        self.core.addTufoProp('dendrite:job', 'working_at', ptype='time', req=True)
        self.core.addTufoProp('dendrite:job', 'completed_at', ptype='time', req=True)

        self.core.addTufoForm('dendrite:queue', ptype='str')
        self.core.addTufoProp('dendrite:queue', 'head', ptype='str', defval=Jobs._EMPTY_STR)
        self.core.addTufoProp('dendrite:queue', 'tail', ptype='str', defval=Jobs._EMPTY_STR)
        self.core.addTufoProp('dendrite:queue', 'failed', ptype='int', defval=0)
        self.core.addTufoProp('dendrite:queue', 'queued', ptype='int', defval=0)
        self.core.addTufoProp('dendrite:queue', 'working', ptype='int', defval=0)
        self.core.addTufoProp('dendrite:queue', 'completed', ptype='int', defval=0)

        self.svcbus = s_telepath.openurl(svcbus)

    def put(self, queue, job):
        '''
        Adds job to a queue.

        The job is added to the queue and an event of the form ``'dendrite:jobs:%s' % queue`` is fired on
        the Service Bus.

        Args:
            queue (str):
                Name of the queue to add the job to.

            job (dict):
                Dict containing any properties needed to represent the job.
        '''
        logger.debug('Adding job %s to queue %s', job, queue)
        props = self._initJobProps(queue, job)
        tufo = self.core.formTufoByProp('dendrite:job', s_common.guid(), **props)
        self._updateLinksOnPut(tufo)
        self.svcbus.fire(self._eventName(queue), queue=queue)

    def putAll(self, queue, jobList):
        '''
        Adds a list of jobs to a queue.

        The list of jobs are added to the queue and an event of the form ``'dendrite:jobs:%s' % queue`` is fired on
        the Service Bus.

        Args:
            queue (str):
                Name of the queue to add the job to.

            jobList (list):
                List of jobs containing any properties needed to represent the job.
        '''
        logger.debug('Adding %d jobs to queue %s', len(jobList), queue)
        queueState = self._getQueue(queue)
        count = queueState[1].get('dendrite:queue:queued')
        tail = queueState[1].get('dendrite:queue:tail')
        tailTufo = self.core.getTufoByIden(tail) if tail else None
        for job in jobList:
            count += 1
            props = self._initJobProps(queue, job)
            tufo = self.core.formTufoByProp('dendrite:job', s_common.guid(), **props)
            if tail == Jobs._EMPTY_STR:
                self.core.setTufoProps(queueState, head=tufo[0], tail=tufo[0])
            else:
                self.core.setTufoProps(tailTufo, link=tufo[0])
            tail = tufo[0]
            tailTufo = tufo

        if tail:
            self.core.setTufoProps(queueState, tail=tail, queued=count)
        self.svcbus.fire(self._eventName(queue), queue=queue)

    def get(self, queue):
        '''
        Get the next job off the queue specified.

        Args:
            queue (str):
                The name of the queue to retrieve a job from.

        Returns:
            dict: The next job if one exists, None otherwise.
        '''
        queueState = self._getQueue(queue)
        queuedCount = queueState[1].get('dendrite:queue:queued')
        workingCount = queueState[1].get('dendrite:queue:working')
        head = queueState[1].get('dendrite:queue:head')
        job = None
        if head:
            tufo = self.core.getTufoByIden(head)
            job = json.loads(tufo[1].get('dendrite:job:data'))
            job.update({'iden': tufo[0]})
            self.core.setTufoProps(tufo, status='working', working_at=s_common.now())
            link = tufo[1].get('dendrite:job:link')
            if link != Jobs._EMPTY_STR:
                self.core.setTufoProps(queueState, head=link, queued=queuedCount-1, working=workingCount+1)
            else:
                self.core.setTufoProps(
                    queueState, head=Jobs._EMPTY_STR, queued=queuedCount - 1, working=workingCount + 1)
        return job

    def clear(self, queue):
        '''
        Clear all the jobs from the queue specified.

        Args:
            queue (str):
                The name of the queue to clear.
        '''
        logger.debug('Deleting job from queue %s', queue)
        self.core.delTufosByProp('dendrite:job:queue', queue)
        queueState = self.core.getTufoByProp('dendrite:queue', queue)
        if queueState:
            self.core.delTufo(queueState)

    def complete(self, job):
        '''
        Complete the job provided.

        The job provided is transitioned to a state of 'completed'.

        Args:
            job (dict):
                The job to be completed.
        '''
        tufo = self.core.getTufoByIden(job.get('iden'))
        if tufo:
            logger.debug('Completing job %s', tufo)
            self.core.setTufoProps(tufo, status='completed', completed_at=s_common.now())
            queueState = self._getQueue(tufo[1].get('dendrite:job:queue'))
            workingCount = queueState[1].get('dendrite:queue:working')
            completedCount = queueState[1].get('dendrite:queue:completed')
            self.core.setTufoProps(queueState, working=workingCount-1, completed=completedCount+1)

    def fail(self, job):
        '''
        Fail the job provided.

        The job provided is transitioned back to a state of 'queued', this will make the job available again for
        retrieval from the queue.

        Args:
            job (dict):
                The job to fail.
        '''
        tufo = self.core.getTufoByIden(job.get('iden'))
        if tufo:
            # for now, just log and requeue the job
            logger.debug('Failing job %s', tufo)
            self.core.setTufoProps(tufo, status='failed', failed_at=s_common.now())
            queueState = self._getQueue(tufo[1].get('dendrite:job:queue'))
            workingCount = queueState[1].get('dendrite:queue:working')
            failedCount = queueState[1].get('dendrite:queue:failed')
            self.core.setTufoProps(queueState, working=workingCount-1, failed=failedCount+1)

    def qsize(self, queue, status='queued'):
        '''
        Determine the size of the queue specified.

        By default, the number of 'queued' jobs is returned. A status is optionally specified to determine the number
        of jobs in other states, e.g. 'working' or 'completed'. The pseudo status of 'any' is also accepted for
        counting all jobs regardless of status.

        Args:
            queue (str):
                The name of the queue to determine the size of.

            status (str):
                The job status to predicate on while determining the size.

        Returns:
            int: Size of the queue.
        '''
        return self._getQueueSize(self.core.getTufoByProp('dendrite:queue', queue), status)

    def isEmpty(self, queue, status='queued'):
        '''
        Determine whether the queue specified is empty.

        A convenience method for determining whether a queue's size is 0.

        Args:
            queue (str):
                The name of the queue to determine the size of.

            status (str):
                The job status to predicate on while determining if a queue is empty.

        Returns:
            bool: True if the queue is empty, False otherwise.
        '''
        return self.qsize(queue, status) == 0

    def stats(self, status='any'):
        '''
        Returns a histogram showing job count by queue name.

        The default status argument is 'any', which is a pseudo status for collecting all jobs regardless of status.

        Args:
            status (str):
                The status to filter the jobs by, e.g. 'queued', 'working', 'completed'.

        Returns:
            collections.defaultdict: A dictionary containing a histogram of count by queue name.
        '''
        histo = collections.defaultdict(int)
        for tufo in self.core.getTufosByProp('dendrite:queue'):
            histo[tufo[1].get('dendrite:queue')] = self._getQueueSize(tufo, status)
        return histo

    def _initJobProps(self, queue, job):
        return {
            'queue':    queue,
            'data':     json.dumps(job),
            'status':   'queued',
            'queued_at': s_common.now()
        }

    def _eventName(self, queue):
        return 'dendrite:jobs:%s' % queue

    def _updateLinksOnPut(self, tufo):
        queueState = self._getQueue(tufo[1].get('dendrite:job:queue'))
        count = queueState[1].get('dendrite:queue:queued')
        tail = queueState[1].get('dendrite:queue:tail')
        if tail == Jobs._EMPTY_STR:
            self.core.setTufoProps(queueState, head=tufo[0], tail=tufo[0], queued=count+1)
        else:
            tailTufo = self.core.getTufoByIden(tail)
            self.core.setTufoProps(tailTufo, link=tufo[0])
            self.core.setTufoProps(queueState, tail=tufo[0], queued=count+1)

    def _getQueue(self, queue):
        tufo = self.core.getTufoByProp('dendrite:queue', queue)
        if tufo == None:
            tufo = self.core.formTufoByProp('dendrite:queue', queue)
        return tufo

    def _getQueueSize(self, tufo, status):
        count = 0
        if tufo != None:
            if status == 'any':
                queued    = tufo[1].get('dendrite:queue:queued')
                working   = tufo[1].get('dendrite:queue:working')
                completed = tufo[1].get('dendrite:queue:completed')
                failed    = tufo[1].get('dendrite:queue:failed')
                count     = queued + working + completed + failed
            else:
                count = tufo[1].get('dendrite:queue:%s' % status, 0)
        return count
