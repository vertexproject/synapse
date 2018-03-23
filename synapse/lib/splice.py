import tempfile

import synapse.common as s_common
import synapse.lib.msgpack as s_msgpack

_readsz = 10000000


def splice(act, **info):
    '''
    Form a splice event from a given act name and info.

    Args:
        act (str): The name of the action.
        **info:    Additional information about the event.

    Example:
        splice = splice('add:node', form='inet:ipv4', valu=0)
        self.fire(splice)

    Notes:
        Splice events were reworked in v0.0.45 and now contain a sub-event of
        the (act, info) under the 'mesg' key.

    Returns:
        (str, dict): The splice event.
    '''
    return (act, info)

def convertOldSplice(mesg):
    '''
    Converts an "old" splice event to the "new" format.

    Args:
        mesg ((str,dict)):  An event tuple.

    Examples:
        Convert a splice to the new format:

            newsplice = convertOldSplice(oldsplice)

    Raises:
        (BadSpliceMesg): The splice was unable to be converted.

    Returns:
        (str, dict): The splice event.
    '''
    if not(isinstance(mesg, tuple) and len(mesg) is 2):
        raise s_common.BadSpliceMesg('invalid event mesg')

    evtname = mesg[0]
    if evtname != 'splice':
        raise s_common.BadSpliceMesg('event mesg is not a splice')

    data = mesg[1]
    if data.get('mesg'):
        raise s_common.BadSpliceMesg('splice has already been converted')

    act = mesg[1].pop('act', None)
    if not act:
        raise s_common.BadSpliceMesg('splice is missing act')

    return splice(act, **data)

def convertSpliceFd(fpath):
    '''
    Converts an "old" splice log to the new format.

    Args:
        fpath (str): The path to the "old" splice log file.

    Example:
        convertSpliceFd('/stuff/oldsplicelog.mpk')

    Notes:
        This function reads the an "old" splice log file, writes to a temporary
        file, and then overwrites the old file with the new data. This function
        only converts old splices to new splices. If any messages are invalid,
        an exception will be raised and the conversion will exit early and not
        overwrite any data.

    Returns:
        None
    '''
    with tempfile.SpooledTemporaryFile() as tmp:
        with open(fpath, 'r+b') as fd:

            for chnk in s_common.chunks(s_msgpack.iterfd(fd), 1000):
                for mesg in chnk:
                    mesg = convertOldSplice(mesg)
                    tmp.write(s_msgpack.en(mesg))

            tmp.seek(0)
            fd.seek(0)

            data = tmp.read(_readsz)
            while data:
                fd.write(data)
                data = tmp.read(_readsz)

            fd.truncate()
