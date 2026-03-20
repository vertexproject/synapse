import sys
import json
import shutil
import tempfile

import synapse.cortex as s_cortex

import synapse.lib.cmd as s_cmd
import synapse.lib.node as s_node
import synapse.lib.output as s_output

desc = 'Run Storm queries against a local Cortex.'

def handleErr(outp, mesg):
    err = mesg[1]
    if err[0] == 'BadSyntax':
        pos = err[1].get('at', None)
        text = err[1].get('text', None)
        tlen = len(text)
        emsg = err[1].get('mesg', None)
        if pos is not None and text is not None and emsg is not None:
            text = text.replace('\n', ' ')
            if tlen > 60:
                text = text[max(0, pos - 30):pos + 30]
                if pos < tlen - 30:
                    text += '...'
                if pos > 30:
                    text = '...' + text
                    pos = 33

            outp.printf(text)
            outp.printf(f'{" " * pos}^')
            outp.printf(f'Syntax Error: {emsg}')
            return

    text = err[1].get('mesg', err[0])
    outp.printf(f'ERROR: {text}')

def printNodeProp(outp, name, valu):
    outp.printf(f'        {name} = {valu}')

def printStormMesg(outp, mesg):
    mtyp = mesg[0]

    if mtyp == 'node':
        node = mesg[1]
        formname, formvalu = s_node.reprNdef(node)
        outp.printf(f'{formname}={formvalu}')

        props = []
        extns = []
        univs = []

        for name in s_node.props(node).keys():

            if name.startswith('.'):
                univs.append(name)
                continue

            if name.startswith('_'):
                extns.append(name)
                continue

            props.append(name)

        props.sort()
        extns.sort()
        univs.sort()

        for name in props:
            valu = s_node.reprProp(node, name)
            name = ':' + name
            printNodeProp(outp, name, valu)

        for name in extns:
            valu = s_node.reprProp(node, name)
            name = ':' + name
            printNodeProp(outp, name, valu)

        for name in univs:
            valu = s_node.reprProp(node, name)
            printNodeProp(outp, name, valu)

        for tag in sorted(s_node.tagsnice(node)):

            valu = s_node.reprTag(node, tag)
            tprops = s_node.reprTagProps(node, tag)
            printed = False
            if valu:
                outp.printf(f'        #{tag} = {valu}')
                printed = True

            if tprops:
                for prop, pval in tprops:
                    outp.printf(f'        #{tag}:{prop} = {pval}')
                printed = True

            if not printed:
                outp.printf(f'        #{tag}')

        return True

    if mtyp == 'node:edits':
        edit = mesg[1]
        count = sum(len(e[2]) for e in edit.get('edits', ()))
        outp.printf('.' * count, addnl=False)
        return True

    if mtyp == 'fini':
        took = mesg[1].get('took') / 1000
        took = max(took, 1)
        count = mesg[1].get('count')
        pers = float(count) / float(took / 1000)
        outp.printf('complete. %d nodes in %d ms (%d/sec).' % (count, took, pers))
        return True

    if mtyp == 'print':
        outp.printf(mesg[1].get('mesg'))
        return True

    if mtyp == 'warn':
        info = mesg[1].copy()
        warn = info.pop('mesg', '')
        xtra = ', '.join([f'{k}={v}' for k, v in info.items()])
        if xtra:
            warn = ' '.join([warn, xtra])
        outp.printf(f'WARNING: {warn}')
        return True

    if mtyp == 'err':
        handleErr(outp, mesg)
        return False

    return True

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.storm.tester', outp=outp, description=desc)
    pars.add_argument('file', help='Path to a .storm file to run (use - for stdin).')
    pars.add_argument('--raw', action='store_true', default=False, help='Output raw JSON lines.')
    pars.add_argument('--dir', help='Cortex data directory (persists between runs).')
    pars.add_argument('--view', help='View iden to execute the query in.')
    pars.add_argument('--forked', action='store_true', default=False,
                      help='Fork the target view before running, then delete the fork after.')

    opts = pars.parse_args(argv)

    if opts.file == '-':
        text = sys.stdin.read()
    else:
        with open(opts.file, 'r') as fd:
            text = fd.read()

    if text is None or text.strip() == '':
        outp.printf('No Storm query text provided.')
        return 1

    cleanup = False
    dirn = opts.dir
    if dirn is None:
        dirn = tempfile.mkdtemp()
        cleanup = True

    try:

        ret = 0

        async with await s_cortex.Cortex.anit(dirn) as core:

            stormopts = {'node:opts': {'repr': True}}

            forkiden = None

            if opts.forked:
                if opts.view is not None:
                    view = core.getView(opts.view)
                else:
                    view = core.view

                vdef = await view.fork()
                forkiden = vdef.get('iden')
                stormopts['view'] = forkiden

            elif opts.view is not None:
                stormopts['view'] = opts.view

            try:

                async for mesg in core.storm(text, opts=stormopts):

                    if opts.raw:
                        outp.printf(json.dumps(mesg, sort_keys=True))
                        continue

                    if not printStormMesg(outp, mesg):
                        ret = 1

            finally:
                if forkiden is not None:
                    await core.delViewWithLayer(forkiden)

        return ret

    finally:
        if cleanup:
            shutil.rmtree(dirn, ignore_errors=True)

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
