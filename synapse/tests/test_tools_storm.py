import os
import sys
import signal
import asyncio
import multiprocessing

import synapse.tests.utils as s_test

from prompt_toolkit.document import Document
from prompt_toolkit.completion import Completion, CompleteEvent

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.tools.storm as s_t_storm

def run_cli_till_print(url, evt1):
    '''
    Run the stormCLI until we get a print mesg then set the event.

    This is a Process target.
    '''
    async def main():
        outp = s_output.OutPutStr()  # Capture output instead of sending it to stdout
        async with await s_telepath.openurl(url) as proxy:
            async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                cmdqueue = asyncio.Queue()
                await cmdqueue.put('while (true) { $lib.print(go) $lib.time.sleep(1) }')
                await cmdqueue.put('!quit')

                async def fake_prompt():
                    return await cmdqueue.get()

                scli.prompt = fake_prompt

                d = {'evt1': False}
                async def onmesg(event):
                    if d.get('evt1'):
                        return
                    mesg = event[1].get('mesg')
                    if mesg[0] != 'print':
                        return
                    evt1.set()
                    d['evt1'] = True

                with scli.onWith('storm:mesg', onmesg):
                    await scli.addSignalHandlers()
                    await scli.runCmdLoop()

    asyncio.run(main())
    sys.exit(137)

class StormCliTest(s_test.SynTest):

    async def test_tools_storm(self):

        async with self.getTestCore() as core:

            await core.addTagProp('foo', ('int', {}), {})

            pars = s_t_storm.getArgParser()
            opts = pars.parse_args(('woot',))
            self.eq('woot', opts.cortex)
            self.none(opts.view)

            q = '$lib.model.ext.addFormProp(inet:ipv4, "_test:score", (int, ({})), ({}))'
            await core.callStorm(q)

            async with core.getLocalProxy() as proxy:

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('[inet:ipv4=1.2.3.4 +#foo=2012 +#bar +#baz:foo=10 :_test:score=7]')
                    text = str(outp)
                    self.isin('.....', text)
                    self.isin('inet:ipv4=1.2.3.4', text)
                    self.isin(':type = unicast', text)
                    self.isin(':_test:score = 7', text)
                    self.isin('.created = ', text)
                    self.isin('#bar', text)
                    self.isin('#baz:foo = 10', text)
                    self.isin('#foo = (2012/01/01 00:00:00.000, 2012/01/01 00:00:00.001)', text)
                    self.isin('complete. 1 nodes in', text)

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('!quit')
                    self.isin('o/', str(outp))
                    self.true(scli.isfini)

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('!help')
                    self.isin('!quit', str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('$lib.print(woot)')
                    self.isin('woot', str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('$lib.warn(woot)')
                    self.isin('WARNING: woot', str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('---')
                    self.isin("---\n ^\nSyntax Error: Unexpected token '-' at line 1, column 2", str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('spin |' + ' ' * 80 + '---')
                    self.isin("...                             ---\n                                 ^", str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('---' + ' ' * 80 + 'spin')
                    self.isin("---                            ...\n ^", str(outp))

            lurl = core.getLocalUrl()

            outp = s_output.OutPutStr()
            ret = await s_t_storm.main((lurl, '$lib.print(woot)'), outp=outp)
            self.eq(ret, 0)
            self.isin('woot', str(outp))

            outp = s_output.OutPutStr()
            ret = await s_t_storm.main((lurl, '| | |'), outp=outp)
            self.eq(ret, 1)
            self.isin('Syntax Error', str(outp))

            outp = s_output.OutPutStr()
            ret = await s_t_storm.main((lurl, 'inet:asn=name'), outp=outp)
            self.eq(ret, 1)
            self.isin('ERROR:', str(outp))

            outp = s_output.OutPutStr()
            await s_t_storm.main((lurl, f'!runfile --help'), outp=outp)
            self.isin('Run a local storm file', str(outp))

            with self.getTestDir() as dirn:

                path = os.path.join(dirn, 'foo.storm')
                with open(path, 'wb') as fd:
                    fd.write(b'$lib.print(woot)')

                outp = s_output.OutPutStr()
                ret = await s_t_storm.main((lurl, f'!runfile {path}'), outp=outp)
                self.eq(ret, 0)
                self.isin(f'running storm file: {path}', str(outp))
                self.isin('woot', str(outp))

                outp = s_output.OutPutStr()
                ret = await s_t_storm.main((lurl, f'!runfile /newp.storm'), outp=outp)
                self.eq(ret, 1)
                self.isin(f'no such file: /newp.storm', str(outp))

                outp = s_output.OutPutStr()
                ret = await s_t_storm.main((lurl, f'!pushfile /newp'), outp=outp)
                self.eq(ret, 1)
                self.isin(f'no such file: /newp', str(outp))

                outp = s_output.OutPutStr()
                await s_t_storm.main((lurl, f'!pushfile {path}'), outp=outp)
                text = str(outp)
                self.isin(f'uploading file: {path}', text)
                self.isin(':name = foo.storm', text)
                self.isin(':sha256 = c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3', text)

                outp = s_output.OutPutStr()
                path = os.path.join(dirn, 'bar.storm')
                ret = await s_t_storm.main((lurl, f'!pullfile c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3 {path}'), outp=outp)
                self.eq(ret, 0)

                text = str(outp)
                self.isin('downloading sha256: c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3', text)
                self.isin(f'saved to: {path}', text)

                with s_common.genfile(path) as fd:
                    self.isin('woot', fd.read().decode())

                outp = s_output.OutPutStr()
                ret = await s_t_storm.main((lurl, f'!pullfile c11adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3 {path}'), outp=outp)
                self.eq(ret, 1)
                text = str(outp)
                self.isin('Axon does not contain the requested file.', text)

                path = os.path.join(dirn, 'badsyntax.storm')
                with open(path, 'wb') as fd:
                    fd.write(b'| | |')

                outp = s_output.OutPutStr()
                ret = await s_t_storm.main((lurl, f'!runfile {path}'), outp=outp)
                self.eq(ret, 1)
                self.isin(f'running storm file: {path}', str(outp))
                self.isin('Syntax Error', str(outp))

                path = os.path.join(dirn, 'badquery.storm')
                with open(path, 'wb') as fd:
                    fd.write(b'inet:asn=newp')

                outp = s_output.OutPutStr()
                ret = await s_t_storm.main((lurl, f'!runfile {path}'), outp=outp)
                self.eq(ret, 1)
                self.isin(f'running storm file: {path}', str(outp))
                self.isin('ERROR:', str(outp))

                await scli.runCmdLine('[test:str=foo +#foo +#bar +#baz]')
                await scli.runCmdLine('[test:str=bar +#foo +#bar +#baz]')

                path = os.path.join(dirn, 'export1.nodes')
                await s_t_storm.main((lurl, f'!export {path} {{ test:str }}'), outp=outp)
                text = str(outp)
                self.isin(f'saved 2 nodes to: {path}', text)

                with open(path, 'rb') as fd:
                    byts = fd.read()
                    podes = [i[1] for i in s_msgpack.Unpk().feed(byts)]
                    self.sorteq(('bar', 'foo'), [p[0][1] for p in podes])
                    for pode in podes:
                        self.sorteq(('bar', 'baz', 'foo'), pode[1]['tags'])

                path = os.path.join(dirn, 'export2.nodes')
                q = f'!export {path} {{ test:str }} --include-tags foo bar'
                await s_t_storm.main((lurl, q), outp=outp)
                text = str(outp)
                self.isin(f'saved 2 nodes to: {path}', text)

                with open(path, 'rb') as fd:
                    byts = fd.read()
                    podes = [i[1] for i in s_msgpack.Unpk().feed(byts)]
                    self.sorteq(('bar', 'foo'), [p[0][1] for p in podes])
                    for pode in podes:
                        self.sorteq(('bar', 'foo'), pode[1]['tags'])

                path = os.path.join(dirn, 'export3.nodes')
                q = f'!export {path} {{ test:str }} --no-tags'
                ret = await s_t_storm.main((lurl, q), outp=outp)
                self.eq(ret, 0)
                text = str(outp)
                self.isin(f'saved 2 nodes to: {path}', text)

                with open(path, 'rb') as fd:
                    byts = fd.read()
                    podes = [i[1] for i in s_msgpack.Unpk().feed(byts)]
                    self.sorteq(('bar', 'foo'), [p[0][1] for p in podes])
                    for pode in podes:
                        self.eq({}, pode[1]['tags'])

                ret = await s_t_storm.main((lurl, f'!export {path} {{ test:newp }}'), outp=outp)
                self.eq(ret, 1)
                text = str(outp)
                self.isin('No property named test:newp.', text)

    async def test_tools_storm_view(self):

        async with self.getTestCore() as core:

            url = core.getLocalUrl()

            pars = s_t_storm.getArgParser()
            opts = pars.parse_args(('woot', '--view', '246e7d5dab883eb28d345a33abcdb577'))
            self.eq(opts.view, '246e7d5dab883eb28d345a33abcdb577')

            view = await core.callStorm('$view = $lib.view.get() $fork=$view.fork() return ( $fork.iden )')

            outp = s_output.OutPutStr()
            await s_t_storm.main(('--view', view, url, f'[file:bytes={"a"*64}]'), outp=outp)
            self.len(0, await core.nodes('file:bytes'))
            self.len(1, await core.nodes('file:bytes', opts={'view': view}))

            with self.getTestDir() as dirn:
                path = os.path.join(dirn, 'export.nodes')
                q = f'!export {path} {{ file:bytes }}'
                await s_t_storm.main(('--view', view, url, q), outp=outp)
                text = str(outp)
                self.isin(f'saved 1 nodes to: {path}', text)

                optsfile = s_common.genpath(dirn, 'opts.yaml')
                with self.raises(s_exc.NoSuchFile):
                    await s_t_storm.main(('--optsfile', optsfile, url, 'file:bytes'), outp=outp)

                s_common.yamlsave({'view': view}, optsfile)

                outp = s_output.OutPutStr()
                await s_t_storm.main(('--optsfile', optsfile, url, 'file:bytes'), outp=outp)
                self.isin('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', str(outp))

    async def test_storm_tab_completion(self):
        class DummyStorm:
            def __init__(self, core):
                self.item = core
                self.stormopts = {}

        async with self.getTestCore() as core:
            cli = DummyStorm(core)

            completer = s_t_storm.StormCompleter(cli)

            async def get_completions(text):
                document = Document(text)
                event = CompleteEvent(completion_requested=True)
                return await s_test.alist(completer.get_completions_async(document, event))

            vals = await get_completions('')
            self.len(0, vals)

            # Check completion of forms/props
            vals = await get_completions('inet:fq')
            self.isin(Completion('dn', display='[form] inet:fqdn - A Fully Qualified Domain Name (FQDN).'), vals)
            self.isin(Completion('dn.seen', display='[prop] inet:fqdn.seen - The time interval for first/last observation of the node.'), vals)
            self.isin(Completion('dn.created', display='[prop] inet:fqdn.created - The time the node was created in the cortex.'), vals)
            self.isin(Completion('dn:domain', display='[prop] inet:fqdn:domain - The parent domain for the FQDN.'), vals)
            self.isin(Completion('dn:host', display='[prop] inet:fqdn:host - The host part of the FQDN.'), vals)
            self.isin(Completion('dn:issuffix', display='[prop] inet:fqdn:issuffix - True if the FQDN is considered a suffix.'), vals)
            self.isin(Completion('dn:iszone', display='[prop] inet:fqdn:iszone - True if the FQDN is considered a zone.'), vals)
            self.isin(Completion('dn:zone', display='[prop] inet:fqdn:zone - The zone level parent for this FQDN.'), vals)

            vals = await get_completions('inet:fqdn.')
            self.isin(Completion('seen', display='[prop] inet:fqdn.seen - The time interval for first/last observation of the node.'), vals)
            self.isin(Completion('created', display='[prop] inet:fqdn.created - The time the node was created in the cortex.'), vals)

            vals = await get_completions('[inet:fq')
            self.isin(Completion('dn', display='[form] inet:fqdn - A Fully Qualified Domain Name (FQDN).'), vals)
            self.isin(Completion('dn.seen', display='[prop] inet:fqdn.seen - The time interval for first/last observation of the node.'), vals)

            vals = await get_completions('[inet:')
            self.isin(Completion('fqdn', display='[form] inet:fqdn - A Fully Qualified Domain Name (FQDN).'), vals)
            self.isin(Completion('ipv4', display='[form] inet:ipv4 - An IPv4 address.'), vals)

            # No tags to return
            vals = await get_completions('inet:ipv4#')
            self.len(0, vals)

            # Add some tags
            await core.stormlist('[inet:ipv4=1.2.3.4 +#rep.foo]')
            await core.stormlist('[inet:ipv4=1.2.3.5 +#rep.foo.bar]')
            await core.stormlist('[inet:ipv4=1.2.3.6 +#rep.bar]')
            await core.stormlist('[inet:ipv4=1.2.3.7 +#rep.baz]')
            await core.stormlist('[syn:tag=rep :doc="Reputation base."]')

            # Check completion of tags
            vals = await get_completions('inet:ipv4#')
            self.len(4, vals)
            self.isin(Completion('rep', display='[tag] rep - Reputation base.'), vals)
            self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)
            self.isin(Completion('rep.bar', display='[tag] rep.bar'), vals)
            self.isin(Completion('rep.baz', display='[tag] rep.baz'), vals)

            vals = await get_completions('inet:ipv4#rep.')
            self.len(4, vals)
            self.isin(Completion('foo', display='[tag] rep.foo'), vals)
            self.isin(Completion('foo.bar', display='[tag] rep.foo.bar'), vals)
            self.isin(Completion('bar', display='[tag] rep.bar'), vals)
            self.isin(Completion('baz', display='[tag] rep.baz'), vals)

            vals = await get_completions('inet:ipv4 +#')
            self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)

            vals = await get_completions('inet:ipv4 -#')
            self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)

            vals = await get_completions('[inet:ipv4 +#')
            self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)

            vals = await get_completions('inet:ipv4 { +#')
            self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)

            # Tag completion is view sensitive
            fork = await core.callStorm('return(  $lib.view.get().fork().iden )')
            await core.nodes('[syn:tag=rep.fork]', opts={'view': fork})

            vals = await get_completions('test:str#rep.f')
            self.len(2, vals)
            self.isin(Completion('oo', display='[tag] rep.foo'), vals)
            self.isin(Completion('oo.bar', display='[tag] rep.foo.bar'), vals)

            cli.stormopts['view'] = fork
            vals = await get_completions('test:str#rep.f')
            self.len(3, vals)
            self.isin(Completion('oo', display='[tag] rep.foo'), vals)
            self.isin(Completion('ork', display='[tag] rep.fork'), vals)
            self.isin(Completion('oo.bar', display='[tag] rep.foo.bar'), vals)
            cli.stormopts.pop('view')

            # Check completion of cmds
            vals = await get_completions('vau')
            self.isin(Completion('lt.add', display='[cmd] vault.add - Add a vault.'), vals)
            self.isin(Completion('lt.set.secrets', display='[cmd] vault.set.secrets - Set vault secret data.'), vals)
            self.isin(Completion('lt.set.configs', display='[cmd] vault.set.configs - Set vault config data.'), vals)
            self.isin(Completion('lt.del', display='[cmd] vault.del - Delete a vault.'), vals)
            self.isin(Completion('lt.list', display='[cmd] vault.list - List available vaults.'), vals)
            self.isin(Completion('lt.set.perm', display='[cmd] vault.set.perm - Set permissions on a vault.'), vals)

            vals = await get_completions('inet:ipv4 +#rep.foo | ser')
            self.isin(Completion('vice.add', display='[cmd] service.add - Add a storm service to the cortex.'), vals)
            self.isin(Completion('vice.del', display='[cmd] service.del - Remove a storm service from the cortex.'), vals)
            self.isin(Completion('vice.list', display='[cmd] service.list - List the storm services configured in the cortex.'), vals)

            # Check completion of libs
            vals = await get_completions('inet:ipv4 $li')
            self.len(0, vals)

            vals = await get_completions('inet:ipv4 $lib')
            self.isin(
                Completion(
                    '.auth.easyperm.allowed',
                    display='[lib] $lib.auth.easyperm.allowed(edef: dict, level: int) - Check if the current user has a permission level in an easy perm dictionary.'
                ),
                vals
            )

            self.isin(
                Completion(
                    '.vault.list',
                    display='[lib] $lib.vault.list() - List vaults accessible to the current user.'
                ),
                vals
            )

    async def test_storm_cmdloop_interrupt(self):
        '''
        Test interrupting a long-running query in the command loop
        '''
        async with self.getTestCore() as core:

            async with core.getLocalProxy() as proxy:

                outp = s_test.TstOutPut()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:

                    cmdqueue = asyncio.Queue()
                    await cmdqueue.put('while (true) { $lib.time.sleep(1) }')
                    await cmdqueue.put('!quit')

                    async def fake_prompt():
                        return await cmdqueue.get()
                    scli.prompt = fake_prompt

                    cmdloop_task = asyncio.create_task(scli.runCmdLoop())
                    await asyncio.sleep(0.1)

                    if scli.cmdtask is not None:
                        scli.cmdtask.cancel()

                    await cmdloop_task

                    outp.expect('<ctrl-c>')
                    outp.expect('o/')
                    self.true(scli.isfini)

    async def test_storm_cmdloop_sigint(self):
        '''
        Test interrupting a long-running query in the command loop with a process target and SIGINT.
        '''

        async with self.getTestCore() as core:
            url = core.getLocalUrl()

            ctx = multiprocessing.get_context('spawn')

            evt1 = ctx.Event()

            proc = ctx.Process(target=run_cli_till_print, args=(url, evt1,))
            proc.start()

            self.true(await s_coro.executor(evt1.wait, timeout=30))
            os.kill(proc.pid, signal.SIGINT)
            proc.join(timeout=30)
            self.eq(proc.exitcode, 137)
