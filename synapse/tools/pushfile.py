import os
import sys
import logging
import argparse

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.hashset as s_hashset

logger = logging.getLogger(__name__)


def main(argv, outp=None):

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    pars = makeargparser()
    opts = pars.parse_args(argv)

    axon = s_telepath.openurl(opts.axon)

    core = None
    if opts.cortex:
        core = s_telepath.openurl(opts.cortex)

        tags = {}
        if opts.tags:
            for tag in opts.tags.split(','):
                tags[tag] = (None, None)

        if tags:
            outp.printf('adding tags: %r' % (list(tags.keys())))

    for path in opts.filenames:

        bname = os.path.basename(path)

        hset = s_hashset.HashSet()
        with s_common.reqfile(path) as fd:
            hset.eatfd(fd)

        fhashes = {htyp: hasher.hexdigest() for htyp, hasher in hset.hashes}

        sha256 = fhashes.get('sha256')
        bsha256 = s_common.uhex(sha256)

        if not axon.has(bsha256):

            with axon.upload() as upfd:

                with s_common.genfile(path) as fd:
                    for byts in s_common.iterfd(fd):
                        upfd.write(byts)

                size, hashval = upfd.save()

            if hashval != bsha256:  # pragma: no cover
                raise s_exc.SynErr(mesg='hashes do not match',
                                   ehash=s_common.ehex(hashval),
                                   ahash=hashval)

            outp.printf(f'Uploaded [{bname}] to axon')
        else:
            outp.printf(f'Axon already had [{bname}]')

        if core:
            pnode = (
                ('file:bytes', f'sha256:{sha256}'),
                {
                    'props': {
                        'md5': fhashes.get('md5'),
                        'sha1': fhashes.get('sha1'),
                        'sha256': fhashes.get('sha256'),
                        'size': hset.size,
                        'name': bname,
                    },
                    'tags': tags,
                }
            )

            node = list(core.addNodes([pnode]))[0]

            iden = node[0][1]
            size = node[1]['props']['size']
            name = node[1]['props']['name']
            mesg = f'file: {bname} ({size}) added to core ({iden}) as {name}'
            outp.printf(mesg)

    s_glob.sync(axon.fini())
    if core:
        s_glob.sync(core.fini())
    return 0

def makeargparser():
    desc = 'Command line tool for uploading files to an Axon and making ' \
           'file:bytes in a Cortex.'
    pars = argparse.ArgumentParser('synapse.tools.pushfile', description=desc)
    pars.add_argument('-a', '--axon', required=True, type=str, dest='axon',
                   help='URL for a target Axon to store files at.')
    pars.add_argument('-c', '--cortex', default=None, type=str, dest='cortex',
                   help='URL for a target Cortex to make file:bytes nodes.')
    pars.add_argument('filenames', nargs='+', help='files to upload')
    pars.add_argument('-t', '--tags', help='comma separated list of tags to add to the nodes')
    return pars

def _main():  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    return main(sys.argv[1:])

if __name__ == '__main__':  # pragma: no cover
    sys.exit(_main())
