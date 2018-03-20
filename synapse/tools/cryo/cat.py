import sys
import json
import pprint
import argparse
import logging

import synapse.common as s_common
import synapse.cryotank as s_cryotank

import synapse.lib.cell as s_cell
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)


def _except_wrap(it, error_str_func):
    ''' Wrap an iterator and adds a bit of context to the exception message '''
    item_no = 0
    while True:
        item_no += 1
        try:
            yield next(it)
        except StopIteration:
            return
        except Exception as e:
            extra_context = error_str_func(item_no)
            e.args = (extra_context + ': ' + str(e.args[0]), ) + e.args[1:]
            raise

def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='cryo.cat', description='display data items from a cryo cell')
    pars.add_argument('cryocell', help='The cell descriptor and cryo tank path (cell://<host:port>/<name>).')
    pars.add_argument('--list', default=False, action='store_true', help='List tanks in the remote cell and return')
    pars.add_argument('--offset', default=0, type=int, help='Begin at offset index')
    pars.add_argument('--size', default=10, type=int, help='How many items to display')
    pars.add_argument('--timeout', default=10, type=int, help='The network timeout setting')
    pars.add_argument('--authfile', help='Path to your auth file for the remote cell')
    group = pars.add_mutually_exclusive_group()
    group.add_argument('--jsonl', action='store_true', help='Input/Output items in jsonl format')
    group.add_argument('--msgpack', action='store_true', help='Input/Output items in msgpack format')
    pars.add_argument('--verbose', '-v', default=False, action='store_true', help='Verbose output')
    pars.add_argument('--ingest', '-i', default=False, action='store_true',
                      help='Reverses direction: feeds cryotank from stdin in msgpack or jsonl format')
    pars.add_argument('--omit-offset', default=False, action='store_true',
                      help="Don't output offsets of objects. This is recommended to be used when jsonl/msgpack"
                           " output is used.")

    opts = pars.parse_args(argv)

    if opts.verbose:
        logger.setLevel(logging.INFO)

    if not opts.authfile:
        logger.error('Currently requires --authfile until neuron protocol is supported')
        return 1

    if opts.ingest and not opts.jsonl and not opts.msgpack:
            logger.error('Must specify exactly one of --jsonl or --msgpack if --ingest is specified')
            return 1

    authpath = s_common.genpath(opts.authfile)

    auth = s_msgpack.loadfile(authpath)

    netw, path = opts.cryocell[7:].split('/', 1)
    host, portstr = netw.split(':')

    addr = (host, int(portstr))
    logger.info('connecting to: %r', addr)

    cuser = s_cell.CellUser(auth)
    with cuser.open(addr, timeout=opts.timeout) as sess:
        cryo = s_cryotank.CryoClient(sess)

        if opts.list:
            for name, info in cryo.list(timeout=opts.timeout):
                outp.printf('%s: %r' % (name, info))

            return 0

        if opts.ingest:
            if opts.msgpack:
                fd = sys.stdin.buffer
                item_it = _except_wrap(s_msgpack.iterfd(fd), lambda x: 'Error parsing item %d' % x)
            else:
                fd = sys.stdin
                item_it = _except_wrap((json.loads(s) for s in fd), lambda x: ('Failure parsing line %d of input' % x))
            cryo.puts(path, item_it)
        else:
            for item in cryo.slice(path, opts.offset, opts.size, opts.timeout):
                i = item[1] if opts.omit_offset else item
                if opts.jsonl:
                    outp.printf(json.dumps(i, sort_keys=True))
                elif opts.msgpack:
                    sys.stdout.write(s_msgpack.en(i))
                else:
                    outp.printf(pprint.pformat(i))

    return 0

if __name__ == '__main__':  # pragma: no cover
    logging.basicConfig()
    sys.exit(main(sys.argv[1:]))
