'''
Helpers for persistent queuing functions.
'''
import logging

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.urlhelp as s_urlhelp

logger = logging.getLogger(__name__)

qtypes = {}

class QueueBase:
    '''
    Base class for implementing queue endpoints for the Storm ``queue``
    command.

    This class, and its derivatives, are never constructed as standalone
    objects. Implementors should override the ``validate`` and ``queue``
    classmethods in order to implement their endpoints.
    '''
    @classmethod
    def validate(cls, conf):
        '''
        Validate that a

        Args:
            conf ((str, dict)): A Configuration tufo.

        Returns:
            bool: True if the configuration is valid.

        Notes:
            Implementors may override this method to provide their
            own configuration validation.

        Raises:
            s_exc.BadConfValu: If the configuration is invalid.
        '''
        name = conf[0]
        if not isinstance(name, str):
            raise s_exc.BadConfValu(mesg='name is incorrect or missing.',
                                    key='name')
        return True

    @classmethod
    def queue(cls, conf, items):
        '''
        Queue up items to a endpoint with a given configuraiton.

        Args:
            conf (dict): A configuration dictionary. This should contain the
            information necessary to connect too and place items into a given
            queue endpoint.
            items (list): A list of packed nodes to queue.

        Notes:
            Implementors must override this method in order to connect to
            their remote queueing service and place packed nodes into the
            queue with the given configuration.

        Returns:
            int: The number of items placed into the queue.
        '''
        raise s_exc.NoSuchImpl(mesg='Queue function is not implemented on the base class.',
                               name='queue')

class CryoQueue(QueueBase):
    '''
    A CryoTank backed queue for nodes.
    '''
    @classmethod
    def validate(cls, conf):
        '''
        Ensure that the configuration has name and a valid URL managed by a CryoCell.
        '''
        QueueBase.validate(conf)
        name, conf = conf
        url = conf.get('url')
        try:
            parts = s_urlhelp.chopurl(url)
            path = parts.get('path')
            cellname, tankname = path.lstrip('/').split('/')
        except Exception as e:
            logger.exception('Failed to parse url [%s].', url)
            raise s_exc.BadConfValu(mesg='Unable to parse tank name from URL.',
                                    name='url', valu=url) from e
        if not tankname:
            raise s_exc.BadConfValu(mesg='No tank name found in url',
                                    name='url', valu=url)
        return True

    @classmethod
    def queue(cls, conf, items):
        '''
        Place items into the configured CryoTank.
        '''
        name, conf = conf
        url = conf.get('url')
        try:
            with s_telepath.openurl(url) as cryotank:
                cryotank.puts(items)
        except Exception as e:
            logger.exception('Failed to put items into cryotank')
            raise
        return len(items)

def add(name, ctor):
    '''
    Register a queue constructor class.

    Args:
        name (str): Name of the task queue alias.
        ctor: Class used to run the task queue.

    Notes:
        Third party modules which implement a QueueBase class should import
        ``synapse.lib.persist`` and register their alias and queue class using
        this function.  This can be done in a module ``__init__.py`` file.

    Returns:
        None
    '''
    qtypes[name] = ctor

def getQueues():
    '''
    Get a list of registered queue names and their fully qualified class paths.
    '''
    ret = []
    for alias, ctor in qtypes.items():
        ret.append((alias, '.'.join([ctor.__module__, ctor.__qualname__])))
    return ret

def validate(conf):
    '''
    Validate a configuration is correct.

    Args:
        conf ((str, dict)): A configuration tufo.

    Returns:
        bool: True if the configuration is valid.
    '''
    typ = conf[1].get('type')
    ctor = qtypes.get(typ)  # type: QueueBase
    if ctor is None:
        raise s_exc.NoSuchName(name=typ, mesg='No queue ctor by that name')
    return ctor.validate(conf)

def queue(conf, items):
    '''
    Place items in the queue for a given configuration.

    Args:
        conf ((str, dict)): A configuration tufo.
        items (list): A list of packed Nodes.
    '''
    typ = conf[1].get('type')
    ctor = qtypes.get(typ)  # type: QueueBase
    if ctor is None:
        raise s_exc.NoSuchName(name=typ, mesg='No queue ctor by that name')
    return ctor.queue(conf, items)

# Add a CryoTank backed queue implementation.
add('cryotank', CryoQueue)
