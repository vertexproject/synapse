'''
Helpers for persistent queuing loop functions.
'''
import logging
import collections

import synapse.common as s_common
import synapse.telepath as s_telepath

logger = logging.getLogger(__name__)

qtypes = {}

def add(name, func):
    '''
    Register a task queue constructor function.

    Args:
        name (str): Name of the task queue alias.
        func: Function used to run the task queue.

    Notes:
        Third party modules which implement a task queue consumer class
        should import ``synapse.lib.persist`` and register their alias
        and queue function using this function.  This can be done in a module
        ``__init__.py`` file.  Functions are expected to take a Cortex with
        ``tqueue`` attribute which is a ``synapse.lib.queue.Queue`` object,
        and a dictionary of configuration data.

    Returns:
        None
    '''
    qtypes[name] = func

def getQueues():
    '''
    Get a list of registered queue names and their fully qualified paths.
    '''
    ret = []
    for alias, ctor in qtypes.items():
        ret.append((alias, '.'.join([ctor.__module__, ctor.__qualname__])))
    return ret

def run(core, conf):
    func = qtypes.get(conf.get('type'))
    func(core, conf)

def cryoCellQueue(core, conf):
    '''
    Consume task events from the Cortex.tqueue, and place them into CryoTanks
    managed by a CryoCell.

    Args:
        core: Cortex to consume events from.
        conf (dict): A config dictionary. The following keys are used:
          - url: The Cryocell to connect too via Telepath.
          - size: The number of items to pull from the queue at once. If not
          provided, the default size of 1000 will be used.

    Notes:
        Task events consumed by the Queue are bucketed by their task name, and
        only the task dictionaries are placed into the CryoTank. Tasks are put
        into the tanks by their name.
        For Cortex configuration purposes, this is named ``cryo:cell``.

    '''
    url = conf.get('url')
    sz = conf.get('size', 1000)
    with s_telepath.openurl(url) as cryocell:
        for items in core.tqueue.slices(sz):
            d = collections.defaultdict(list)
            for ttype, rec in items:
                d[ttype].append(rec)

            for ttype, recs in d.items():
                try:
                    cryocell.puts(ttype, recs)
                except Exception as e:
                    logger.exception('Failed to put items into tank for [%s]', ttype)
                    raise
            core.fire('persist:task:cryo:cell', len=len(items))

def cryoTankQueue(core, conf):
    '''
        Consume task events from the Cortex.tqueue, and put them directly into
        a Cryotank.

        Args:
            core: Cortex to consume events from.
            conf (dict): A config dictionary. The following keys are used:
              - url: The CryoTank to connect to via Telepath.
              - size: The number of items to pull from the queue at once. If not
              provided, the default size of 1000 will be used.

        Notes:
            This puts tasks into the CryoTanks as a tufo of
            ``('someTaskName', {..task data..})``.
            For Cortex configuration purposes, this is named ``cryo:tank``.

        '''
    url = conf.get('url')
    sz = conf.get('size', 1000)
    with s_telepath.openurl(url) as cryotank:
        for items in core.tqueue.slices(sz):
            try:
                cryotank.puts(items)
            except Exception as e:
                logger.exception('Failed to put items into cryotank')
                raise
            core.fire('persist:task:cryo:tank', len=len(items))

# Register built-in queue loop functions.
add('cryo:cell', cryoCellQueue)
add('cryo:tank', cryoTankQueue)
