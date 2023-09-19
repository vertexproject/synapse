import os
import sys
import glob
import asyncio
import logging
import argparse

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.hashset as s_hashset

logger = logging.getLogger(__name__)


async def main(argv, outp=None):

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    pars = makeargparser()
    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        axon = await s_telepath.openurl(opts.axon)

        core = None
        if opts.cortex:
            core = await s_telepath.openurl(opts.cortex)

            tags = set()
            if opts.tags:
                for tag in opts.tags.split(','):
                    tags.add(tag)

            tags = tuple(tags)
            if tags:
                outp.printf(f'adding tags: {tags}')

        filepaths = set()
        for item in opts.filenames:
            paths = glob.glob(item, recursive=opts.recursive)

            if not paths:
                outp.printf(f'filepath does not contain any files: {item}')
                continue

            filepaths.update([path for path in paths if os.path.isfile(path)])

        for path in filepaths:

            bname = os.path.basename(path)

            hset = s_hashset.HashSet()
            with s_common.reqfile(path) as fd:
                hset.eatfd(fd)

            fhashes = {htyp: hasher.hexdigest() for htyp, hasher in hset.hashes}

            sha256 = fhashes.get('sha256')
            bsha256 = s_common.uhex(sha256)

            if not await axon.has(bsha256):

                async with await axon.upload() as upfd:

                    with s_common.genfile(path) as fd:
                        for byts in s_common.iterfd(fd):
                            await upfd.write(byts)

                    size, hashval = await upfd.save()

                if hashval != bsha256:  # pragma: no cover
                    raise s_exc.SynErr(mesg='hashes do not match',
                                       ehash=s_common.ehex(hashval),
                                       ahash=hashval)

                outp.printf(f'Uploaded [{bname}] to axon')
            else:
                outp.printf(f'Axon already had [{bname}]')

            if core:
                opts = {'vars': {
                    'md5': fhashes.get('md5'),
                    'sha1': fhashes.get('sha1'),
                    'sha256': fhashes.get('sha256'),
                    'size': hset.size,
                    'name': bname,
                    'tags': tags,
                }}

                q = '[file:bytes=$sha256 :md5=$md5 :sha1=$sha1 :size=$size :name=$name] ' \
                    '{ for $tag in $tags { [+#$tag] } }'

                msgs = await core.storm(q, opts=opts).list()
                node = [m[1] for m in msgs if m[0] == 'node'][0]

                iden = node[0][1]
                size = node[1]['props']['size']
                name = node[1]['props']['name']
                mesg = f'file: {bname} ({size}) added to core ({iden}) as {name}'
                outp.printf(mesg)

        await axon.fini()
        if core:
            await core.fini()

    return 0

def makeargparser():
    desc = 'Command line tool for uploading files to an Axon and making ' \
           'file:bytes in a Cortex.'
    pars = argparse.ArgumentParser('synapse.tools.pushfile', description=desc)
    pars.add_argument('-a', '--axon', required=True, type=str, dest='axon',
                   help='URL for a target Axon to store files at.')
    pars.add_argument('-c', '--cortex', default=None, type=str, dest='cortex',
                   help='URL for a target Cortex to make file:bytes nodes.')
    pars.add_argument('filenames', nargs='+', help='File names (or glob patterns) to upload')
    pars.add_argument('-r', '--recursive', action='store_true',
                      help='Recursively search paths to upload files.')
    pars.add_argument('-t', '--tags', help='comma separated list of tags to add to the nodes')
    return pars

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
