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
    def __init__(self, core, svcbus):
        s_eventbus.EventBus.__init__(self)
        self.currMs = None
        self.jobNum = None
        self.core = s_cortex.openurl(core)
        #self.core.setConfOpt('caching', True)
        self.core.addTufoForm('dendrite:job', ptype='guid')
        self.core.addTufoProp('dendrite:job', 'link', ptype='guid')
        self.core.addTufoProp('dendrite:job', 'queue', ptype='str', req=True)
        self.core.addTufoProp('dendrite:job', 'data', ptype='str', req=True)
        self.core.addTufoProp('dendrite:job', 'runkey', ptype='int', req=True)
        self.core.addTufoProp('dendrite:job', 'status', ptype='str', req=True)
        self.core.addTufoProp('dendrite:job', 'failed_at', ptype='time', req=True)
        self.core.addTufoProp('dendrite:job', 'queued_at', ptype='time', req=True)
        self.core.addTufoProp('dendrite:job', 'working_at', ptype='time', req=True)
        self.core.addTufoProp('dendrite:job', 'completed_at', ptype='time', req=True)

        self.core.addTufoForm('dendrite:queue', ptype='str')
        self.core.addTufoProp('dendrite:queue', 'head', ptype='guid')
        self.core.addTufoProp('dendrite:queue', 'tail', ptype='guid')

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
        tail = queueState[1].get('dendrite:queue:tail')
        tailTufo = self.core.getTufoByIden(tail) if tail else None
        for job in jobList:
            props = self._initJobProps(queue, job)
            tufo = self.core.formTufoByProp('dendrite:job', s_common.guid(), **props)
            if tail == None:
                self.core.setTufoProps(queueState, head=tufo[0], tail=tufo[0])
            else:
                self.core.setTufoProps(tailTufo, link=tufo[0])
            tail = tufo[0]
            tailTufo = tufo

        if tail:
            self.core.setTufoProps(queueState, tail=tail)
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
        head = queueState[1].get('dendrite:queue:head')
        if head:
            tufo = self.core.getTufoByIden(head)
            job = json.loads(tufo[1].get('dendrite:job:data'))
            job.update({'iden': tufo[0]})
            self.core.setTufoProps(tufo, status='working', working_at=s_common.now())
            link = tufo[1].get('dendrite:job:link')
            if link:
                self.core.setTufoProps(queueState, head=link)
            else:
                self.core.delTufo(queueState)
            return job
        return None

    def clear(self, queue, status='any'):
        '''
        Clear all the jobs from the queue specified. By default, the pseudo status of 'any' is used to clear all jobs
        from the queue, regardless of status. Any status may be provided to only clear certain jobs from a queue.

        Args:
            queue (str):
                The name of the queue to clear.

            status (str):
                The job status to predicate on while clearing jobs from the specified queue.
        '''
        for tufo in self._jobsByQueue(queue, status):
            logger.debug('Deleting job %s', tufo)
            self.core.delTufo(tufo)

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
        return len(self._jobsByQueue(queue, status))

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
        if status == 'any':
            return self.core.getStatByProp('histo', 'dendrite:job:queue')

        histo = collections.defaultdict(int)
        for tufo in self.core.getTufosByProp('dendrite:job:status', status):
            histo[tufo[1].get('dendrite:job:queue')] += 1
        return histo

    def _initJobProps(self, queue, job):
        return {
            'queue':    queue,
            'data':     json.dumps(job),
            'runkey':   self._runkey(),
            'status':   'queued',
            'queued_at': s_common.now()
        }

    def _runkey(self):
        currms = s_common.now()
        if currms != self.currMs:
            self.currMs = currms
            self.jobNum = 1
        else:
            self.jobNum += 1
        return (currms << 8) | self.jobNum

    def _jobsByQueue(self, queue, status='queued'):
        if status == 'any':
            return self.core.getTufosByProp('dendrite:job:queue', queue)

        jobs = []
        for tufo in self.core.getTufosByProp('dendrite:job:queue', queue):
            if tufo[1].get('dendrite:job:status') == status:
                jobs.append(tufo)
        return jobs

    def _eventName(self, queue):
        return 'dendrite:jobs:%s' % queue

    def _updateLinksOnPut(self, tufo):
        queueState = self._getQueue(tufo[1].get('dendrite:job:queue'))
        tail = queueState[1].get('dendrite:queue:tail')
        if tail == None:
            self.core.setTufoProps(queueState, head=tufo[0], tail=tufo[0])
        else:
            tailTufo = self.core.getTufoByIden(tail)
            self.core.setTufoProps(tailTufo, link=tufo[0])
            self.core.setTufoProps(queueState, tail=tufo[0])

    def _getQueue(self, queue):
        tufo = self.core.getTufoByProp('dendrite:queue', queue)
        if tufo == None:
            tufo = self.core.formTufoByProp('dendrite:queue', queue)
        return tufo
