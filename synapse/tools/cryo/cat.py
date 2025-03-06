import sys
import pprint
import asyncio
import argparse
import logging

import synapse.telepath as s_telepath

import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='cryo.cat', description='display data items from a cryo cell')
    pars.add_argument('cryotank', help='The telepath URL for the remote cryotank.')
    pars.add_argument('--offset', default=0, type=int, help='Begin at offset index')
    pars.add_argument('--size', default=10, type=int, help='How many items to display')
    pars.add_argument('--omit-offset', default=False, action='store_true', help='Output raw items with no offsets.')
    # TODO: synapse.tools.cryo.list <cryocell>
    # pars.add_argument('--list', default=False, action='store_true', help='List tanks in the remote cell and return')
    group = pars.add_mutually_exclusive_group()
    group.add_argument('--jsonl', action='store_true', help='Input/Output items in jsonl format')
    group.add_argument('--msgpack', action='store_true', help='Input/Output items in msgpack format')
    pars.add_argument('--verbose', '-v', default=False, action='store_true', help='Verbose output')
    pars.add_argument('--ingest', '-i', default=False, action='store_true',
                      help='Reverses direction: feeds cryotank from stdin in msgpack or jsonl format')

    opts = pars.parse_args(argv)

    if opts.verbose:
        logger.setLevel(logging.INFO)

    if opts.ingest and not opts.jsonl and not opts.msgpack:
        outp.printf('Must specify exactly one of --jsonl or --msgpack if --ingest is specified')
        return 1

    logger.info(f'connecting to: {opts.cryotank}')

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.cryotank) as tank:

            if opts.ingest:

                if opts.msgpack:
                    items = list(s_msgpack.iterfd(sys.stdin.buffer))
                    await tank.puts(items)
                    return 0

                items = [s_json.loads(line) for line in sys.stdin]
                await tank.puts(items)
                return 0

            async for item in tank.slice(opts.offset, opts.size):

                if opts.jsonl:
                    outp.printf(s_json.dumps(item[1], sort_keys=True).decode())

                elif opts.msgpack:
                    sys.stdout.buffer.write(s_msgpack.en(item[1]))

                else:
                    outp.printf(pprint.pformat(item))
    return 0

if __name__ == '__main__':  # pragma: no cover
    logging.basicConfig()
    sys.exit(asyncio.run(main(sys.argv[1:])))
