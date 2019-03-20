import json
import queue
import pprint
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cli as s_cli
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)


class Log(s_cli.Cmd):
    '''
    Add a storm log to the local command session.

    Syntax:
        log (--on|--off) [--splices-only] [--format (mpk|jsonl)] [--path /path/to/file]

    Required Arguments:
        --on: Enables logging of storm messages to a file.
        --off: Disables message logging and closes the current storm file.

    Optional Arguments:
        --splices-only: Only records splices. Does not record any other messages.
        --format: The format used to save messages to disk. Defaults to msgpack (mpk).
        --path: The path to the log file.  This will append messages to a existing file.

    Notes:
        By default, the log file contains all messages received from the execution of
        a Storm query by the current CLI. By default, these messages are saved to a
        file located in ~/.syn/stormlogs/storm_(date).(format).

    Examples:
        # Enable logging all messages to mpk files (default)
        log --on

        # Disable logging and close the current file
        log --off

        # Enable logging, but only log splices. Log them as jsonl instead of mpk.
        log --on --splices-only --format jsonl

        # Enable logging, but log to a custom path:
        log --on --path /my/aweome/log/directory/storm20010203.mpk

    '''
    _cmd_name = 'log'
    _cmd_syntax = (
        ('--on', {'type': 'flag'}),
        ('--off', {'type': 'flag'}),
        ('--path', {'type': 'valu'}),
        ('--format', {'type': 'enum',
                      'defval': 'mpk',
                      'enum:vals': ['mpk', 'jsonl']}),
        ('--splices-only', {'defval': False})
    )
    splicetypes = (
        'tag:add',
        'tag:del',
        'node:add',
        'node:del',
        'prop:set',
        'prop:del',
    )

    def __init__(self, cli, **opts):
        s_cli.Cmd.__init__(self, cli, **opts)
        # Give ourselves a local ref to locs since we're stateful.
        self.locs = self._cmd_cli.locs
        self._cmd_cli.onfini(self.closeLogFd)

    def onStormMesg(self, mesg):
        self.locs.get('log:queue').put(mesg)

    @s_common.firethread
    def queueLoop(self):
        q = self.locs.get('log:queue')
        while not self._cmd_cli.isfini:
            try:
                mesg = q.get(timeout=2)
            except queue.Empty:
                continue
            except s_exc.IsFini:
                break
            smesg = mesg[1].get('mesg')
            self.save(smesg)

    def save(self, mesg):
        fd = self.locs.get('log:fd')
        spliceonly = self.locs.get('log:splicesonly')
        if fd and not fd.closed:
            if spliceonly and mesg[0] not in self.splicetypes:
                return
            try:
                buf = self.encodeMsg(mesg)
            except Exception as e:
                logger.error('Failed to serialize message: [%s]', str(e))
                return
            fd.write(buf)

    def encodeMsg(self, mesg):
        '''Get byts for a message'''

        fmt = self.locs.get('log:fmt')
        if fmt == 'jsonl':
            s = json.dumps(mesg, sort_keys=True) + '\n'
            buf = s.encode()
            return buf

        elif fmt == 'mpk':
            buf = s_msgpack.en(mesg)
            return buf

        mesg = f'Unknown encoding format: {fmt}'
        raise s_exc.SynErr(mesg=mesg)

    def closeLogFd(self):
        self._cmd_cli.off('storm:mesg', self.onStormMesg)
        q = self.locs.pop('log:queue', None)
        if q is not None:
            self.printf('Marking log queue done')
        thr = self.locs.pop('log:thr', None)
        if thr:
            self.printf('Joining log thread.')
            thr.join(2)
        fp = self.locs.pop('log:fp', None)
        fd = self.locs.pop('log:fd', None)
        self.locs.pop('log:fmt', None)
        self.locs.pop('log:splicesonly', None)
        if fd:
            try:
                self.printf(f'Closing logfile: [{fp}]')
                fd.close()
            except Exception as e:  # pragma: no cover
                self.printf(f'Failed to close fd: [{str(e)}]')

    def openLogFd(self, opts):
        opath = self.locs.get('log:fp')
        if opath:
            self.printf('Must call --off to disable current file before starting a new file.')
            return
        fmt = opts.get('format')
        path = opts.get('path')
        splice_only = opts.get('splices-only')
        if not path:
            ts = s_time.repr(s_common.now(), True)
            fn = f'storm_{ts}.{fmt}'
            path = s_common.getSynPath('stormlogs', fn)
        self.printf(f'Starting logfile at [{path}]')
        q = queue.Queue()
        fd = s_common.genfile(path)
        # Seek to the end of the file. Allows a user to append to a file.
        fd.seek(0, 2)
        self.locs['log:fp'] = path
        self.locs['log:fd'] = fd
        self.locs['log:fmt'] = fmt
        self.locs['log:queue'] = q
        self.locs['log:thr'] = self.queueLoop()
        self.locs['log:splicesonly'] = splice_only
        self._cmd_cli.on('storm:mesg', self.onStormMesg)

    async def runCmdOpts(self, opts):
        on = opts.get('on')
        off = opts.get('off')

        if bool(on) == bool(off):
            self.printf('Pick one of "--on" or "--off".')
            return

        if on:
            return self.openLogFd(opts)

        if off:
            return self.closeLogFd()

class PsCmd(s_cli.Cmd):

    '''
    List running tasks in the cortex.
    '''

    _cmd_name = 'ps'
    _cmd_syntax = ()

    async def runCmdOpts(self, opts):

        core = self.getCmdItem()
        tasks = await core.ps()

        for task in tasks:

            self.printf('task iden: %s' % (task.get('iden'),))
            self.printf('    name: %s' % (task.get('name'),))
            self.printf('    user: %r' % (task.get('user'),))
            self.printf('    status: %r' % (task.get('status'),))
            self.printf('    metadata: %r' % (task.get('info'),))
            self.printf('    start time: %s' % (s_time.repr(task.get('tick', 0)),))

        self.printf('%d tasks found.' % (len(tasks,)))

class KillCmd(s_cli.Cmd):
    '''
    Kill a running task/query within the cortex.

    Syntax:
        kill <iden>

    Users may specify a partial iden GUID in order to kill
    exactly one matching process based on the partial guid.
    '''
    _cmd_name = 'kill'
    _cmd_syntax = (
        ('iden', {}),
    )

    async def runCmdOpts(self, opts):

        core = self.getCmdItem()

        match = opts.get('iden')
        if not match:
            self.printf('no iden given to kill.')
            return

        idens = []
        for task in await core.ps():
            iden = task.get('iden')
            if iden.startswith(match):
                idens.append(iden)

        if len(idens) == 0:
            self.printf('no matching process found. aborting.')
            return

        if len(idens) > 1:
            self.printf('multiple matching process found. aborting.')
            return

        kild = await core.kill(idens[0])
        self.printf('kill status: %r' % (kild,))

class StormCmd(s_cli.Cmd):
    '''
    Execute a storm query.

    Syntax:
        storm <query>

    Arguments:
        query: The storm query

    Optional Arguments:
        --hide-tags: Do not print tags
        --hide-props: Do not print secondary properties
        --hide-unknown: Do not print messages which do not have known handlers.
        --raw: Print the nodes in their raw format
            (overrides --hide-tags and --hide-props)
        --debug: Display cmd debug information along with nodes in raw format
            (overrides --hide-tags, --hide-props and raw)
        --path: Get path information about returned nodes.

    Examples:
        storm inet:ipv4=1.2.3.4
        storm --debug inet:ipv4=1.2.3.4
    '''

    _cmd_name = 'storm'
    _cmd_syntax = (
        ('--hide-tags', {}),
        ('--hide-props', {}),
        ('--hide-unknown', {}),
        ('--raw', {}),
        ('--debug', {}),
        ('--path', {}),
        ('query', {'type': 'glob'}),
    )

    def __init__(self, cli, **opts):
        s_cli.Cmd.__init__(self, cli, **opts)
        self.cmdmeths = {
            'node': self._onNode,
            'init': self._onInit,
            'fini': self._onFini,
            'print': self._onPrint,
            'warn': self._onWarn,
        }

    def _onNode(self, mesg):

        node = mesg[1]
        opts = node[1].pop('_opts', {})
        formname = node[0][0]

        formvalu = node[1].get('repr')
        if formvalu is None:
            formvalu = str(node[0][1])

        if opts.get('raw'):
            self.printf(repr(node))
            return

        self.printf(f'{formname}={formvalu}')

        if not opts.get('hide-props'):

            for name, valu in sorted(node[1]['props'].items()):

                valu = node[1]['reprs'].get(name, valu)

                if name[0] != '.':
                    name = ':' + name

                self.printf(f'        {name} = {valu}')

        if not opts.get('hide-tags'):

            for tag in sorted(s_node.tags(node, leaf=True)):

                valu = node[1]['tags'].get(tag)
                if valu == (None, None):
                    self.printf(f'        #{tag}')
                    continue

                mint = s_time.repr(valu[0])
                maxt = s_time.repr(valu[1])
                self.printf(f'        #{tag} = ({mint}, {maxt})')

    def _onInit(self, mesg):
        pass

    def _onFini(self, mesg):
        took = mesg[1].get('took')
        took = max(took, 1)

        count = mesg[1].get('count')
        pers = float(count) / float(took / 1000)
        self.printf('complete. %d nodes in %d ms (%d/sec).' % (count, took, pers))

    def _onPrint(self, mesg):
        self.printf(mesg[1].get('mesg'))

    def _onWarn(self, mesg):
        warn = mesg[1].get('mesg')
        self.printf(f'WARNING: {warn}')

    async def runCmdOpts(self, opts):

        text = opts.get('query')
        if text is None:
            self.printf(self.__doc__)
            return

        hide_unknown = opts.get('hide-unknown', self._cmd_cli.locs.get('storm:hide-unknown'))
        core = self.getCmdItem()
        stormopts = {'repr': True}
        stormopts.setdefault('path', opts.get('path', False))

        self.printf('')

        try:

            async for mesg in await core.storm(text, opts=stormopts):

                await self._cmd_cli.fire('storm:mesg', mesg=mesg)

                if opts.get('debug'):
                    self.printf(pprint.pformat(mesg))

                else:
                    if mesg[0] == 'node':
                        # Tuck the opts into the node dictionary since
                        # they control node metadata display
                        mesg[1][1]['_opts'] = opts
                    try:
                        func = self.cmdmeths[mesg[0]]
                    except KeyError:
                        if hide_unknown:
                            continue
                        self.printf(repr(mesg))
                    else:
                        func(mesg)

        except s_exc.SynErr as e:

            if e.errinfo.get('errx') == 'CancelledError':
                self.printf('query canceled.')
                return

            raise
