import os
import sys
import shutil
import signal
import asyncio
import multiprocessing
import unittest.mock as mock

import aiohttp
import aiohttp_socks

import synapse.tests.utils as s_test

from prompt_toolkit.document import Document
from prompt_toolkit.completion import Completion, CompleteEvent

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cli as s_cli
import synapse.lib.coro as s_coro
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.msgpack as s_msgpack
import synapse.lib.crypto.passwd as s_passwd
import synapse.tools.storm._cli as s_t_storm
import synapse.tools.storm._http as s_t_http

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

class FakeContent:
    '''
    Stand in for the content of an aiohttp response.
    '''
    def __init__(self, chunks):
        self.chunks = chunks

    async def iter_any(self):
        for byts in self.chunks:
            yield byts

class FakeResp:
    '''
    Stand in for an aiohttp response context manager.
    '''
    def __init__(self, chunks, status=200):
        self.status = status
        self.content = FakeContent(chunks)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

class StormCliTest(s_test.SynTest):

    async def getStormHttpInfo(self, core):
        '''
        Add an HTTPS listener to a Cortex and mint a root user API key.

        Note:
            The listener uses a self-signed certificate with a CN of the cell type,
            so callers must disable TLS verification.
        '''
        host, port = await core.addHttpsPort(0, host='127.0.0.1')
        apikey, _ = await core.addUserApiKey(core.auth.rootuser.iden, 'storm-cli')
        return port, apikey

    async def runStormCliItem(self, item):
        '''
        Drive StormCli directly against a Cortex API object.
        '''
        await item.callStorm('$lib.model.ext.addTagProp(_foo, (int, ({})), ({}))')
        await item.callStorm('$lib.model.ext.addFormProp(inet:ip, "_test:score", (int, ({})), ({}))')

        outp = s_output.OutPutStr()
        async with await s_t_storm.StormCli.anit(item, outp=outp) as scli:
            await scli.runCmdLine('[inet:ip=1.2.3.4 +#foo=2012 +#bar +#baz:_foo=10 :_test:score=7]')
            text = str(outp)
            self.isin('.....', text)
            self.isin('inet:ip=1.2.3.4', text)
            self.isin(':type = unicast', text)
            self.isin(':_test:score = 7', text)
            self.isin('#bar', text)
            self.isin('#baz:_foo = 10', text)
            self.isin('#foo = 2012-01-01T00:00:00Z - 2012-01-01T00:00:00.000001Z', text)
            self.isin('complete. 1 nodes in', text)

        outp = s_output.OutPutStr()
        async with await s_t_storm.StormCli.anit(item, outp=outp) as scli:
            await scli.runCmdLine('!quit')
            self.isin('o/', str(outp))
            self.true(scli.isfini)

        outp = s_output.OutPutStr()
        async with await s_t_storm.StormCli.anit(item, outp=outp) as scli:
            await scli.runCmdLine('!help')
            self.isin('!quit', str(outp))

        outp = s_output.OutPutStr()
        async with await s_t_storm.StormCli.anit(item, outp=outp) as scli:
            await scli.runCmdLine('$lib.print(woot)')
            self.isin('woot', str(outp))

        outp = s_output.OutPutStr()
        async with await s_t_storm.StormCli.anit(item, outp=outp) as scli:
            await scli.runCmdLine('$lib.warn(woot)')
            self.isin('WARNING: woot', str(outp))

        outp = s_output.OutPutStr()
        async with await s_t_storm.StormCli.anit(item, outp=outp) as scli:
            await scli.runCmdLine('---')
            self.isin("---\n ^\nSyntax Error: Unexpected token '-' at line 1, column 2", str(outp))

        outp = s_output.OutPutStr()
        async with await s_t_storm.StormCli.anit(item, outp=outp) as scli:
            await scli.runCmdLine('spin |' + ' ' * 80 + '---')
            self.isin("...                             ---\n                                 ^", str(outp))

        outp = s_output.OutPutStr()
        async with await s_t_storm.StormCli.anit(item, outp=outp) as scli:
            await scli.runCmdLine('---' + ' ' * 80 + 'spin')
            self.isin("---                            ...\n ^", str(outp))

    async def runStormCliMain(self, url, args=()):
        '''
        Drive the storm tool main() end to end. The Cortex must have an Axon.
        '''
        outp = s_output.OutPutStr()
        ret = await s_t_storm.main((*args, url, '$lib.print(woot)'), outp=outp)
        self.eq(ret, 0)
        self.isin('woot', str(outp))

        outp = s_output.OutPutStr()
        ret = await s_t_storm.main((*args, url, '| | |'), outp=outp)
        self.eq(ret, 1)
        self.isin('Syntax Error', str(outp))

        outp = s_output.OutPutStr()
        ret = await s_t_storm.main((*args, url, 'inet:asn=name'), outp=outp)
        self.eq(ret, 1)
        self.isin('ERROR:', str(outp))

        outp = s_output.OutPutStr()
        await s_t_storm.main((*args, url, '!runfile --help'), outp=outp)
        self.isin('Run a local storm file', str(outp))

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'foo.storm')
            with open(path, 'wb') as fd:
                fd.write(b'$lib.print(woot)')

            outp = s_output.OutPutStr()
            ret = await s_t_storm.main((*args, url, f'!runfile {path}'), outp=outp)
            self.eq(ret, 0)
            self.isin(f'running storm file: {path}', str(outp))
            self.isin('woot', str(outp))

            outp = s_output.OutPutStr()
            ret = await s_t_storm.main((*args, url, '!runfile /newp.storm'), outp=outp)
            self.eq(ret, 1)
            self.isin('no such file: /newp.storm', str(outp))

            outp = s_output.OutPutStr()
            ret = await s_t_storm.main((*args, url, '!pushfile /newp'), outp=outp)
            self.eq(ret, 1)
            self.isin('no such file: /newp', str(outp))

            outp = s_output.OutPutStr()
            await s_t_storm.main((*args, url, f'!pushfile {path}'), outp=outp)
            text = str(outp)
            self.isin(f'uploading file: {path}', text)
            self.isin(':name = foo.storm', text)
            self.isin(':sha256 = c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3', text)

            outp = s_output.OutPutStr()
            path = os.path.join(dirn, 'bar.storm')
            ret = await s_t_storm.main((*args, url, f'!pullfile c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3 {path}'), outp=outp)
            self.eq(ret, 0)

            text = str(outp)
            self.isin('downloading sha256: c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3', text)
            self.isin(f'saved to: {path}', text)

            with s_common.genfile(path) as fd:
                self.isin('woot', fd.read().decode())

            outp = s_output.OutPutStr()
            ret = await s_t_storm.main((*args, url, f'!pullfile c11adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3 {path}'), outp=outp)
            self.eq(ret, 1)
            text = str(outp)
            self.isin('Axon does not contain the requested file.', text)

            path = os.path.join(dirn, 'badsyntax.storm')
            with open(path, 'wb') as fd:
                fd.write(b'| | |')

            outp = s_output.OutPutStr()
            ret = await s_t_storm.main((*args, url, f'!runfile {path}'), outp=outp)
            self.eq(ret, 1)
            self.isin(f'running storm file: {path}', str(outp))
            self.isin('Syntax Error', str(outp))

            path = os.path.join(dirn, 'badquery.storm')
            with open(path, 'wb') as fd:
                fd.write(b'inet:asn=newp')

            outp = s_output.OutPutStr()
            ret = await s_t_storm.main((*args, url, f'!runfile {path}'), outp=outp)
            self.eq(ret, 1)
            self.isin(f'running storm file: {path}', str(outp))
            self.isin('ERROR:', str(outp))

            await s_t_storm.main((*args, url, '[test:str=foo +#foo +#bar +#baz]'), outp=outp)
            await s_t_storm.main((*args, url, '[test:str=bar +#foo +#bar +#baz]'), outp=outp)

            path = os.path.join(dirn, 'export1.nodes')
            await s_t_storm.main((*args, url, f'!export {path} {{ test:str }}'), outp=outp)
            text = str(outp)
            self.isin(f'saved 3 nodes to: {path}', text)

            with open(path, 'rb') as fd:
                byts = fd.read()
                podes = [i[1] for i in s_msgpack.Unpk().feed(byts)]
                self.sorteq(('bar', 'foo'), [p[0][1] for p in podes[1:]])
                for pode in podes[1:]:
                    self.sorteq(('bar', 'baz', 'foo'), pode[1]['tags'])

            ret = await s_t_storm.main((*args, url, f'!export {path} {{ test:newp }}'), outp=outp)
            self.eq(ret, 1)
            text = str(outp)
            self.isin('No property named test:newp.', text)

    async def runStormCliView(self, core, url, args=()):
        '''
        Drive the --view and --optsfile behavior through main().
        '''
        view = await core.callStorm('$view = $lib.view.get() $fork=$view.fork() return ( $fork.iden )')

        outp = s_output.OutPutStr()
        await s_t_storm.main((*args, '--view', view, url, '[file:bytes=246e7d5dab883eb28d345a33abcdb577]'), outp=outp)
        self.len(0, await core.nodes('file:bytes'))
        self.len(1, await core.nodes('file:bytes', opts={'view': view}))

        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'export.nodes')
            q = f'!export {path} {{ file:bytes }}'
            await s_t_storm.main((*args, '--view', view, url, q), outp=outp)
            text = str(outp)
            self.isin(f'saved 2 nodes to: {path}', text)

            optsfile = s_common.genpath(dirn, 'opts.yaml')
            with self.raises(s_exc.NoSuchFile):
                await s_t_storm.main((*args, '--optsfile', optsfile, url, 'file:bytes'), outp=outp)

            s_common.yamlsave({'view': view}, optsfile)

            outp = s_output.OutPutStr()
            await s_t_storm.main((*args, '--optsfile', optsfile, url, 'file:bytes'), outp=outp)
            self.isin('file:bytes=246e7d5dab883eb28d345a33abcdb577', str(outp))

    async def runStormCliComplete(self, item):
        '''
        Drive the StormCompleter against a Cortex API object.
        '''
        class DummyStorm:
            def __init__(self, item):
                self.item = item
                self.stormopts = {}

        async def addnodes(text, opts=None):
            async for mesg in item.storm(text, opts=opts):
                if mesg[0] == 'err':
                    raise s_exc.SynErr(mesg=repr(mesg))

        cli = DummyStorm(item)

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
        self.isin(Completion('dn:domain', display='[prop] inet:fqdn:domain - The parent domain for the FQDN.'), vals)
        self.isin(Completion('dn:host', display='[prop] inet:fqdn:host - The host part of the FQDN.'), vals)
        self.isin(Completion('dn:issuffix', display='[prop] inet:fqdn:issuffix - True if the FQDN is considered a suffix.'), vals)
        self.isin(Completion('dn:iszone', display='[prop] inet:fqdn:iszone - True if the FQDN is considered a zone.'), vals)
        self.isin(Completion('dn:zone', display='[prop] inet:fqdn:zone - The zone level parent for this FQDN.'), vals)

        vals = await get_completions('inet:fqdn:')
        self.isin(Completion('domain', display='[prop] inet:fqdn:domain - The parent domain for the FQDN.'), vals)

        vals = await get_completions('[inet:fq')
        self.isin(Completion('dn', display='[form] inet:fqdn - A Fully Qualified Domain Name (FQDN).'), vals)
        self.isin(Completion('dn:domain', display='[prop] inet:fqdn:domain - The parent domain for the FQDN.'), vals)

        vals = await get_completions('[inet:')
        self.isin(Completion('fqdn', display='[form] inet:fqdn - A Fully Qualified Domain Name (FQDN).'), vals)
        self.isin(Completion('ip', display='[form] inet:ip - An IPv4 or IPv6 address.'), vals)

        # No tags to return
        vals = await get_completions('inet:ip#')
        self.len(0, vals)

        # a value which fails to normalize produces an err message in the stream
        with self.raises(s_exc.SynErr) as cm:
            await addnodes('[inet:ip=notanip]')
        self.isin('BadTypeValu', cm.exception.get('mesg'))

        # Add some tags
        await addnodes('[inet:ip=1.2.3.4 +#rep.foo]')
        await addnodes('[inet:ip=1.2.3.5 +#rep.foo.bar]')
        await addnodes('[inet:ip=1.2.3.6 +#rep.bar]')
        await addnodes('[inet:ip=1.2.3.7 +#rep.baz]')
        await addnodes('[syn:tag=rep :doc="Reputation base."]')

        # Check completion of tags
        vals = await get_completions('inet:ip#')
        self.len(4, vals)
        self.isin(Completion('rep', display='[tag] rep - Reputation base.'), vals)
        self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)
        self.isin(Completion('rep.bar', display='[tag] rep.bar'), vals)
        self.isin(Completion('rep.baz', display='[tag] rep.baz'), vals)

        vals = await get_completions('inet:ip#rep.')
        self.len(4, vals)
        self.isin(Completion('foo', display='[tag] rep.foo'), vals)
        self.isin(Completion('foo.bar', display='[tag] rep.foo.bar'), vals)
        self.isin(Completion('bar', display='[tag] rep.bar'), vals)
        self.isin(Completion('baz', display='[tag] rep.baz'), vals)

        vals = await get_completions('inet:ip +#')
        self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)

        vals = await get_completions('inet:ip -#')
        self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)

        vals = await get_completions('[inet:ip +#')
        self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)

        vals = await get_completions('inet:ip { +#')
        self.isin(Completion('rep.foo', display='[tag] rep.foo'), vals)

        # Tag completion is view sensitive
        fork = await item.callStorm('return(  $lib.view.get().fork().iden )')
        await addnodes('[syn:tag=rep.fork]', opts={'view': fork})

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

        vals = await get_completions('inet:ip +#rep.foo | ser')
        self.isin(Completion('vice.add', display='[cmd] service.add - Add a storm service to the cortex.'), vals)
        self.isin(Completion('vice.del', display='[cmd] service.del - Remove a storm service from the cortex.'), vals)
        self.isin(Completion('vice.list', display='[cmd] service.list - List the storm services configured in the cortex.'), vals)

        # Check completion of libs
        vals = await get_completions('inet:ip $li')
        self.len(0, vals)

        vals = await get_completions('inet:ip $lib')
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

    async def runStormCliInterrupt(self, item):
        '''
        Interrupt a long running query in the command loop.
        '''
        outp = s_test.TstOutPut()
        async with await s_t_storm.StormCli.anit(item, outp=outp) as scli:

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

    async def test_tools_storm_args(self):

        pars = s_t_storm.getArgParser(self.getTestOutp())

        opts = pars.parse_args(('woot',))
        self.eq('woot', opts.cortex)
        self.none(opts.view)
        self.none(opts.https_proxy)
        self.none(opts.optsfile)
        self.none(opts.https_ca_dir)
        self.false(opts.https_noverify)

        opts = pars.parse_args(('woot', '--view', '246e7d5dab883eb28d345a33abcdb577'))
        self.eq(opts.view, '246e7d5dab883eb28d345a33abcdb577')

        argv = ('https://foo.bar.com:4443/', 'inet:ip', '--https-proxy', 'socks5://127.0.0.1:9050',
                '--https-ca-dir', '/path/to/cas', '--https-noverify')
        opts = pars.parse_args(argv)
        self.eq('https://foo.bar.com:4443/', opts.cortex)
        self.eq('inet:ip', opts.onecmd)
        self.eq('socks5://127.0.0.1:9050', opts.https_proxy)
        self.eq('/path/to/cas', opts.https_ca_dir)
        self.true(opts.https_noverify)

        # only https:// URLs are handled by the HTTP API client
        self.true(s_t_http.isHttpsUrl('https://foo.bar.com:4443/'))
        self.true(s_t_http.isHttpsUrl('HTTPS://foo.bar.com/'))
        self.false(s_t_http.isHttpsUrl('http://foo.bar.com/'))
        self.false(s_t_http.isHttpsUrl('cell:///vertex/storage'))

        # the base URL is built without userinfo and with a default port
        self.eq('https://foo.bar.com:443', s_t_http.getBaseUrl({'host': 'foo.bar.com', 'path': '/'}))
        self.eq('https://foo.bar.com:443', s_t_http.getBaseUrl({'host': 'foo.bar.com', 'path': ''}))
        self.eq('https://[::1]:4443/optic', s_t_http.getBaseUrl({'host': '::1', 'port': 4443, 'path': '/optic/'}))

        # the https only options require an https:// URL
        for argv in (('--https-proxy', 'socks5://127.0.0.1:9050'),
                     ('--https-ca-dir', '/path/to/cas'),
                     ('--https-noverify',)):

            with self.raises(s_exc.BadArg):
                await s_t_storm.main((*argv, 'cell://newp', 'inet:ip'), outp=self.getTestOutp())

    async def test_tools_storm(self):

        async with self.getTestCluster() as clus:
            core = clus.cortex

            async with core.getLocalProxy() as proxy:
                await self.runStormCliItem(proxy)

            await self.runStormCliMain(core.getLocalUrl())

    async def test_tools_storm_http(self):

        async with self.getTestCluster() as clus:
            core = clus.cortex

            port, apikey = await self.getStormHttpInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            async with await s_t_http.HttpCortex.anit(url, verify=False) as prox:

                await self.runStormCliItem(prox)

                # an upload with no bytes written saves the empty file
                async with await prox.getAxonUpload() as upload:
                    size, sha256 = await upload.save()

                self.eq(0, size)
                self.eq('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', s_common.ehex(sha256))

                # empty writes are skipped and an upload may be reused after a save
                async with await prox.getAxonUpload() as upload:

                    await upload.write(b'')
                    await upload.write(b'visi')
                    size, sha256 = await upload.save()
                    self.eq(4, size)
                    self.eq('e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f', s_common.ehex(sha256))

                    await upload.write(b'hehe')
                    size, sha256 = await upload.save()
                    self.eq(4, size)

                byts = b''.join(await s_test.alist(prox.getAxonBytes(s_common.ehex(sha256))))
                self.eq(b'hehe', byts)

            await self.runStormCliMain(url, args=('--https-noverify',))

    async def test_tools_storm_view(self):

        async with self.getTestCore() as core:
            await self.runStormCliView(core, core.getLocalUrl())

    async def test_tools_storm_view_http(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getStormHttpInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            await self.runStormCliView(core, url, args=('--https-noverify',))

    async def test_storm_tab_completion(self):

        async with self.getTestCore() as core:
            await self.runStormCliComplete(core)

    async def test_storm_tab_completion_http(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getStormHttpInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            async with await s_t_http.HttpCortex.anit(url, verify=False) as prox:
                await self.runStormCliComplete(prox)

    async def test_storm_cmdloop_interrupt(self):
        '''
        Test interrupting a long-running query in the command loop
        '''
        async with self.getTestCore() as core:

            async with core.getLocalProxy() as proxy:
                await self.runStormCliInterrupt(proxy)

    async def test_storm_cmdloop_interrupt_http(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getStormHttpInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            async with await s_t_http.HttpCortex.anit(url, verify=False) as prox:
                await self.runStormCliInterrupt(prox)

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

    async def runStormCliInteractive(self, url, args=()):
        '''
        Drive the interactive ( no onecmd ) storm CLI loop through main() end to end.

        Note:
            runItemStorm() constructs its own StormCli, so prompt is patched on the class
            rather than the instance. The CmdGenerator is a callable object rather than a
            function, so a class attribute is not bound as a method.

            runItemStorm() also sets colorsenabled, which routes every printf() through
            prompt_toolkit to stdout rather than outp, so this asserts control flow.
        '''
        outp = s_test.TstOutPut()

        cmds = s_test.CmdGenerator(['$lib.print(woot)', '!quit'])

        with mock.patch.object(s_t_storm.StormCli, 'prompt', cmds):

            with mock.patch.object(s_cli.Cli, 'addSignalHandlers', mock.AsyncMock()):
                ret = await asyncio.wait_for(s_t_storm.main((*args, url), outp=outp), timeout=30)

        self.none(ret)

    async def test_storm_cmdloop_interactive(self):
        '''
        Test the interactive storm CLI command loop over telepath.
        '''
        async with self.getTestCore() as core:
            await self.runStormCliInteractive(core.getLocalUrl())

    async def test_storm_cmdloop_interactive_http(self):
        '''
        Test the interactive storm CLI command loop over the HTTP API.
        '''
        async with self.getTestCore() as core:

            port, apikey = await self.getStormHttpInfo(core)

            url = f'https://{apikey}@127.0.0.1:{port}'
            await self.runStormCliInteractive(url, args=('--https-noverify',))

    async def test_tools_storm_http_apikey(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getStormHttpInfo(core)
            outp = s_output.OutPutStr()

            # an API key is required in the URL for https:// URLs
            with self.raises(s_exc.BadArg) as cm:
                await s_t_storm.main(('--https-noverify', f'https://127.0.0.1:{port}', 'inet:ip'), outp=outp)
            self.isin('https://<apikey>@host:port/', cm.exception.get('mesg'))

            # the key is taken from the URL userinfo
            ret = await s_t_storm.main(('--https-noverify', f'https://{apikey}@127.0.0.1:{port}',
                                        '$lib.print(woot)'), outp=outp)
            self.eq(ret, 0)
            self.isin('woot', str(outp))

            # a malformed API key is rejected before any network activity
            with self.raises(s_exc.BadArg) as cm:
                await s_t_storm.main(('--https-noverify', f'https://not+a+key@127.0.0.1:{port}',
                                      'inet:ip'), outp=outp)
            self.isin('not a valid Synapse user API key', cm.exception.get('mesg'))

            # a well formed but unknown API key is rejected by the Cortex
            _, badkey, _ = await s_passwd.generateApiKey()
            with self.raises(s_exc.AuthDeny) as cm:
                await s_t_storm.main(('--https-noverify', f'https://{badkey}@127.0.0.1:{port}', 'inet:ip'), outp=outp)
            self.isin('The session is not logged in.', cm.exception.get('mesg'))

            # only https is supported by the HTTP client
            for badurl in (f'cell://{apikey}@newp', f'http://{apikey}@127.0.0.1:{port}'):
                with self.raises(s_exc.BadUrl) as cm:
                    await s_t_http.HttpCortex.anit(badurl)
                self.isin('requires an https:// URL', cm.exception.get('mesg'))

            # an http:// URL is not routed to the HTTP client, so telepath rejects the scheme
            with self.raises(s_exc.BadUrl) as cm:
                await s_t_storm.main((f'http://{apikey}@127.0.0.1:{port}', 'inet:ip'), outp=outp)
            self.isin('Invalid URL scheme: http', cm.exception.get('mesg'))

            # the TLS CA directory must exist
            with self.raises(s_exc.BadArg) as cm:
                await s_t_http.HttpCortex.anit(f'https://{apikey}@127.0.0.1:{port}', cadir='/newp')
            self.isin('TLS CA directory does not exist', cm.exception.get('mesg'))

            # a base path which does not host the API has no JSON envelope to report
            with self.raises(s_exc.SynErr) as cm:
                await s_t_http.HttpCortex.anit(f'https://{apikey}@127.0.0.1:{port}/newp', verify=False)
            self.isin('REST API request failed (HTTP 404)', cm.exception.get('mesg'))

    async def test_tools_storm_http_keepalive(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getStormHttpInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            async with await s_t_http.HttpCortex.anit(url, verify=False) as prox:

                self.none(prox.sess.timeout.total)

                calls = []
                realpost = prox.sess.post

                def post(url, **kwargs):
                    calls.append((url, kwargs.get('json'), kwargs.get('timeout')))
                    return realpost(url, **kwargs)

                with mock.patch.object(prox.sess, 'post', post):

                    await s_test.alist(prox.storm('$lib.print(woot)'))
                    await prox.callStorm('return((0))')
                    await s_test.alist(prox.exportStorm('inet:ip'))
                    await s_test.alist(prox.storm('$lib.print(woot)', opts={'keepalive': 30}))

                stormurl, body, timeout = calls[0]
                self.eq(f'{url.split("@")[1]}/api/v3/storm', stormurl.split('//')[1])
                self.eq(6, body['opts']['keepalive'])
                self.notin('stream', body)
                self.none(timeout)

                # callStorm and exportStorm do not emit keepalive messages
                self.notin('keepalive', calls[1][1].get('opts', {}))
                self.notin('keepalive', calls[2][1].get('opts', {}))
                self.none(calls[1][2])

                # the export request is bounded rather than allowed to hang forever
                self.eq(s_t_http.EXPORT_TIMEOUT, calls[2][2].total)

                # an explicit keepalive wins over the default
                self.eq(30, calls[3][1]['opts']['keepalive'])

                # the Cortex really does emit ping messages
                msgs = await s_test.alist(prox.storm('$lib.time.sleep(0.35)', opts={'keepalive': 0.1}))
                pings = [m for m in msgs if m[0] == 'ping']
                self.gt(len(pings), 0)
                self.eq({}, pings[0][1])

                # ping messages produce no CLI output
                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(prox, outp=outp) as scli:
                    await scli.storm('$lib.time.sleep(0.35)', opts={'keepalive': 0.1})
                self.notin('ping', str(outp))

    async def test_tools_storm_http_bigmesg(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getStormHttpInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            # a single storm message larger than the aiohttp StreamReader high water mark
            # ( 524288 bytes ) must survive the jsonlines reassembly. reading the stream
            # with readline() raises LineTooLong for a message this size, which is why
            # iterJsonLines() buffers over iter_any() instead.
            size = 1000000
            q = f'$valu = $lib.cast(str, A) $lib.fire(bigmesg, data=$valu.ljust({size}, A))'

            async with await s_t_http.HttpCortex.anit(url, verify=False) as prox:

                msgs = await s_test.alist(prox.storm(q))

                fired = [m for m in msgs if m[0] == 'storm:fire']
                self.len(1, fired)
                self.eq('bigmesg', fired[0][1].get('type'))
                self.eq('A' * size, fired[0][1]['data'].get('data'))

                # the stream still terminated cleanly
                self.eq('fini', msgs[-1][0])

    async def test_tools_storm_http_redirect(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getStormHttpInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            core.addHttpApi('/api/v0/reflect', s_test.HttpReflector, {'cell': core})

            async with await s_t_http.HttpCortex.anit(url, verify=False) as prox:

                reflect = prox._getUrl('/api/v0/reflect')

                # the X-API-KEY header is a session default, and aiohttp only strips
                # Authorization / Cookie / Proxy-Authorization from a redirect. without
                # allow_redirects=False the key would be replayed to the redirect target.
                async with prox.sess.get(f'{reflect}?redirect={reflect}', **prox.reqinfo) as resp:
                    self.eq(302, resp.status)

                # the same request which follows the redirect does carry the key onward
                info = dict(prox.reqinfo)
                info['allow_redirects'] = True

                async with prox.sess.get(f'{reflect}?redirect={reflect}', **info) as resp:
                    self.eq(200, resp.status)
                    item = await resp.json()

                self.isin('x-api-key', [k.lower() for k in item['result']['headers']])

    async def test_tools_storm_http_tlscadir(self):

        with self.getTestDir() as dirn:

            cdir = s_common.gendir(dirn, 'certs')
            cadir = s_common.gendir(cdir, 'cas')

            tdir = s_certdir.CertDir(cdir)
            tdir.genCaCert('somelocalca')
            tdir.genHostCert('localhost', signas='somelocalca')

            shutil.copyfile(tdir.getHostKeyPath('localhost'), s_common.genpath(dirn, 'sslkey.pem'))
            shutil.copyfile(tdir.getHostCertPath('localhost'), s_common.genpath(dirn, 'sslcert.pem'))

            tlscadir = s_common.gendir(dirn, 'cadir')
            for name in os.listdir(cadir):
                if name.endswith('.crt'):
                    shutil.copyfile(os.path.join(cadir, name), os.path.join(tlscadir, name))

            async with self.getTestCore(dirn=dirn) as core:

                port, apikey = await self.getStormHttpInfo(core)
                url = f'https://{apikey}@localhost:{port}'

                outp = s_output.OutPutStr()

                # the CA is not in the default trust store
                with self.raises(aiohttp.ClientConnectorCertificateError):
                    await s_t_storm.main((url, '$lib.print(woot)'), outp=outp)

                ret = await s_t_storm.main(('--https-ca-dir', tlscadir, url, '$lib.print(woot)'), outp=outp)
                self.eq(ret, 0)
                self.isin('woot', str(outp))

    async def test_tools_storm_http_proxy(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getStormHttpInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            proxyurl = 'socks5://127.0.0.1:1080'

            with mock.patch.object(aiohttp_socks.ProxyConnector, 'from_url') as mokk:

                mokk.return_value = aiohttp.TCPConnector()

                outp = s_output.OutPutStr()
                ret = await s_t_storm.main(('--https-noverify', '--https-proxy', proxyurl, url, '$lib.print(woot)'), outp=outp)

                self.eq(ret, 0)
                self.isin('woot', str(outp))

                mokk.assert_called_once_with(proxyurl)

    async def test_tools_storm_http_jsonlines(self):

        async def genr(chunks):
            for byts in chunks:
                yield byts

        # a message split across chunks is reassembled
        chunks = (b'["pri', b'nt",{"mesg":"woot"}]\n["fini",{}]\n')
        msgs = await s_test.alist(s_t_http.iterJsonLines(genr(chunks)))
        self.eq([['print', {'mesg': 'woot'}], ['fini', {}]], msgs)

        # empty chunks and multiple messages per chunk are handled
        chunks = (b'', b'["init",{}]\n["print",{"mesg":"a"}]\n', b'', b'["fini",{}]\n')
        msgs = await s_test.alist(s_t_http.iterJsonLines(genr(chunks)))
        self.len(3, msgs)
        self.eq('init', msgs[0][0])

        # a trailing partial message is not yielded
        msgs = await s_test.alist(s_t_http.iterJsonLines(genr((b'["init",{}]\n["pri',))))
        self.eq([['init', {}]], msgs)

    async def test_tools_storm_http_errors(self):

        async with self.getTestCluster() as clus:
            core = clus.cortex

            port, apikey = await self.getStormHttpInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            async with await s_t_http.HttpCortex.anit(url, verify=False) as prox:

                # error envelopes are converted back into synapse exceptions
                with self.raises(s_exc.NoSuchView):
                    await prox.callStorm('return((0))', opts={'view': 'a' * 32})

                with self.raises(s_exc.NoSuchView):
                    await s_test.alist(prox.storm('inet:ip', opts={'view': 'a' * 32}))

                with self.raises(s_exc.NoSuchView):
                    await s_test.alist(prox.exportStorm('inet:ip', opts={'view': 'a' * 32}))

                # a missing file is normalized to match the telepath API
                with self.raises(s_exc.NoSuchFile) as cm:
                    await s_test.alist(prox.getAxonBytes('00' * 32))
                self.eq('Axon does not contain the requested file.', cm.exception.get('mesg'))
                self.eq('00' * 32, cm.exception.get('sha256'))

                # a truncated storm stream is reported rather than silently accepted
                async def truncated(genr):
                    yield ['init', {}]

                with mock.patch.object(s_t_http, 'iterJsonLines', truncated):
                    msgs = await s_test.alist(prox.storm('inet:ip'))

                self.eq('err', msgs[-1][0])
                self.eq('LinkShutDown', msgs[-1][1][0])

                # a truncated export stream raises rather than returning a short result
                pode = (('inet:ip', (4, 0x01020304)), {})
                byts = s_msgpack.en(pode)

                def post(url, **kwargs):
                    return FakeResp((byts, byts[:-3]))

                with mock.patch.object(prox.sess, 'post', post):
                    with self.raises(s_exc.BadDataValu) as cm:
                        await s_test.alist(prox.exportStorm('inet:ip'))
                self.isin('partial node', cm.exception.get('mesg'))

            # a user without the axon permissions gets a useful error rather than a hang
            lowuser = await core.auth.addUser('lowuser')
            lowkey, _ = await core.addUserApiKey(lowuser.iden, 'lowuser')

            async with await s_t_http.HttpCortex.anit(f'https://{lowkey}@127.0.0.1:{port}', verify=False) as prox:

                with self.raises(s_exc.AuthDeny):
                    await s_test.alist(prox.getAxonBytes('00' * 32))

                # the upload queue must not deadlock when the request fails early
                with self.raises(s_exc.AuthDeny):
                    async with await prox.getAxonUpload() as upload:
                        for _ in range(s_t_http.UPLOAD_QSIZE + 1):
                            await upload.write(b'A' * 10000000)
                        await upload.save()

            async with await s_t_http.HttpCortex.anit(url, verify=False) as prox:

                # an upload which ends before all the bytes are sent is an error
                async def _runUpload(self):
                    return {'size': 0, 'sha256': '00' * 32}

                with mock.patch.object(s_t_http.HttpUpload, '_runUpload', _runUpload):

                    async with await prox.getAxonUpload() as upload:

                        upload._initUpload()
                        for _ in range(s_t_http.UPLOAD_QSIZE):
                            upload.queue.put_nowait(b'A')

                        await upload.task

                        with self.raises(s_exc.BadDataValu) as cm:
                            await upload.write(b'A')

                self.isin('ended before all bytes were sent', cm.exception.get('mesg'))
