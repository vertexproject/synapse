import decimal

import synapse.exc as s_exc

import synapse.lib.ast as s_ast
import synapse.lib.parser as s_parser
import synapse.lib.stormbin as s_stormbin

import synapse.tests.utils as s_test

class StormBinTest(s_test.SynTest):

    def _assertAstEqual(self, node1, node2):
        '''Assert two AST trees are structurally equivalent.'''
        self.eq(node1.__class__, node2.__class__)
        self.eq(len(node1.kids), len(node2.kids))

        # Check class-specific attributes
        if isinstance(node1, s_ast.Const) and not isinstance(node1, s_ast.EmbedQuery):
            # EmbedQuery.valu is rewritten to a compiled stormbin payload at
            # load time, so the raw valu strings won't match. Class + kids
            # equality is enough — kids round-trip is asserted recursively.
            self.eq(node1.valu, node2.valu)
            if isinstance(node1.valu, decimal.Decimal):
                self.assertIsInstance(node2.valu, decimal.Decimal)

        if isinstance(node1, s_ast.PivotOper):
            self.eq(node1.isjoin, node2.isjoin)

        if isinstance(node1, (s_ast.N1Walk, s_ast.N2Walk)):
            self.eq(node1.isjoin, node2.isjoin)

        if isinstance(node1, (s_ast.EditEdgeAdd, s_ast.EditEdgeDel)):
            self.eq(node1.n2, node2.n2)

        if isinstance(node1, s_ast.CondSetOper):
            self.eq(node1.errok, node2.errok)

        if isinstance(node1, s_ast.SubQuery):
            self.eq(node1.hasyield, node2.hasyield)

        if isinstance(node1, s_ast.Lookup):
            self.eq(node1.autoadd, node2.autoadd)

        if isinstance(node1, s_ast.LiftOper):
            self.eq(node1.reverse, node2.reverse)

        if isinstance(node1, s_ast.CaseEntry):
            self.eq(node1.defcase, node2.defcase)

        for k1, k2 in zip(node1.kids, node2.kids):
            self._assertAstEqual(k1, k2)

    def test_stormbin_roundtrip_basic(self):
        '''Test round-trip compile/load for basic queries.'''
        queries = [
            'inet:fqdn',
            'inet:fqdn=vertex.link',
            '#foo.bar',
            'inet:fqdn -> inet:dns:a',
            'inet:fqdn +inet:fqdn=vertex.link',
            'inet:fqdn -inet:fqdn=vertex.link',
            '[ inet:fqdn=woot.com ]',
            '[ inet:fqdn=woot.com :issuffix=$lib.true ]',
            'inet:fqdn | limit 10',
        ]
        for text in queries:
            byts = s_stormbin.compile(text)
            self.assertIsInstance(byts, bytes)

            query = s_stormbin.load(byts)
            orig = s_parser.parseQuery(text)
            self._assertAstEqual(orig, query)

    def test_stormbin_roundtrip_complex(self):
        '''Test round-trip for complex query constructs.'''
        queries = [
            # Subqueries
            'inet:fqdn { -> inet:dns:a }',
            # Control flow
            'for $x in $vals { $lib.print($x) }',
            'while ($x < 10) { $x = ($x + 1) }',
            'if ($x = 1) { $lib.print(yes) } else { $lib.print(no) }',
            # Switch
            'switch $x { "foo": { $lib.print(foo) } *: { $lib.print(default) } }',
            # Try/catch
            'try { [ inet:fqdn=woot.com ] } catch StormRuntimeError as err { $lib.print($err) }',
            # Functions
            'function f(x) { return(($x + 1)) }',
            # Variable assignment
            '$x = (10 + 20)',
            '$x = $lib.str.format("{foo}", foo=bar)',
            # Edit operations
            '[ inet:fqdn=woot.com +#foo.bar ]',
            '[ inet:fqdn=woot.com -#foo.bar ]',
            # Tag property set
            '[ inet:fqdn=woot.com +#foo:risk=50 ]',
            # Expressions
            '$x = ($y + 1)',
            '$x = ($y * 2)',
            '$x = ($y and $z)',
            '$x = ($y or $z)',
            '$x = (not $y)',
            # Format strings
            '$x = `hello {$name}`',
            # Embedded queries
            '$q = ${ inet:fqdn }',
            # Lift by array
            'inet:fqdn*[=woot.com]',
            # Emit / stop / return
            'emit $x',
            'stop',
            'return((42))',
            # Break / continue
            'for $x in $y { break }',
            'for $x in $y { continue }',
            # Init / fini blocks
            'init { $x = 0 }',
            'fini { $lib.print(done) }',
            # Empty block
            'empty { $lib.print(empty) }',
        ]
        for text in queries:
            byts = s_stormbin.compile(text)
            query = s_stormbin.load(byts)
            orig = s_parser.parseQuery(text)
            self._assertAstEqual(orig, query)

    def test_stormbin_roundtrip_pivots(self):
        '''Test round-trip for pivot operations including joins.'''
        queries = [
            'inet:fqdn -> inet:dns:a',
            'inet:fqdn -> *',
            'inet:fqdn <- *',
            'inet:fqdn -> inet:dns:a:fqdn',
        ]
        for text in queries:
            byts = s_stormbin.compile(text)
            query = s_stormbin.load(byts)
            orig = s_parser.parseQuery(text)
            self._assertAstEqual(orig, query)

    def test_stormbin_roundtrip_reverse_lift(self):
        '''Reverse-lift queries round-trip with .reverse preserved.'''
        queries = [
            'reverse(inet:fqdn)',
            'reverse(inet:fqdn=vertex.link)',
            'reverse(#foo.bar)',
        ]
        for text in queries:
            orig = s_parser.parseQuery(text)
            byts = s_stormbin.compile(text)
            query = s_stormbin.load(byts)
            self._assertAstEqual(orig, query)
            # Find the LiftOper and confirm reverse survived.
            def find_lift(node):
                if isinstance(node, s_ast.LiftOper):
                    return node
                for k in node.kids:
                    lift = find_lift(k)
                    if lift is not None:
                        return lift
                return None
            self.true(find_lift(query).reverse)

    def test_stormbin_roundtrip_walks(self):
        '''Test round-trip for walk operations.'''
        queries = [
            'inet:fqdn --> *',
            'inet:fqdn <-- *',
        ]
        for text in queries:
            byts = s_stormbin.compile(text)
            query = s_stormbin.load(byts)
            orig = s_parser.parseQuery(text)
            self._assertAstEqual(orig, query)

    def test_stormbin_roundtrip_edge_edits(self):
        '''Test round-trip for edge edit operations.'''
        queries = [
            '[ inet:fqdn=woot.com +(refs)> { inet:fqdn=vertex.link } ]',
            '[ inet:fqdn=woot.com -(refs)> { inet:fqdn=vertex.link } ]',
            '[ inet:fqdn=woot.com <(refs)+ { inet:fqdn=vertex.link } ]',
            '[ inet:fqdn=woot.com <(refs)- { inet:fqdn=vertex.link } ]',
        ]
        for text in queries:
            byts = s_stormbin.compile(text)
            query = s_stormbin.load(byts)
            orig = s_parser.parseQuery(text)
            self._assertAstEqual(orig, query)

    def test_stormbin_value_types(self):
        '''Test value preservation for different types.'''
        # int
        byts = s_stormbin.compile('$x = 42')
        query = s_stormbin.load(byts)
        orig = s_parser.parseQuery('$x = 42')
        self._assertAstEqual(orig, query)

        # string
        byts = s_stormbin.compile('$x = "hello"')
        query = s_stormbin.load(byts)
        orig = s_parser.parseQuery('$x = "hello"')
        self._assertAstEqual(orig, query)

        # bool
        byts = s_stormbin.compile('$x = $lib.true')
        query = s_stormbin.load(byts)
        orig = s_parser.parseQuery('$x = $lib.true')
        self._assertAstEqual(orig, query)

        # None
        byts = s_stormbin.compile('$x = $lib.null')
        query = s_stormbin.load(byts)
        orig = s_parser.parseQuery('$x = $lib.null')
        self._assertAstEqual(orig, query)

    def test_stormbin_mode_storm(self):
        '''Test storm parse mode.'''
        text = 'inet:fqdn=vertex.link'
        byts = s_stormbin.compile(text, mode='storm')
        query = s_stormbin.load(byts)
        self.assertIsInstance(query, s_ast.Query)

    def test_stormbin_mode_lookup(self):
        '''Test lookup parse mode.'''
        text = 'vertex.link'
        byts = s_stormbin.compile(text, mode='lookup')
        query = s_stormbin.load(byts)
        self.assertIsInstance(query, s_ast.Lookup)
        self.false(query.autoadd)

    def test_stormbin_mode_autoadd(self):
        '''Test autoadd parse mode.'''
        text = 'vertex.link'
        byts = s_stormbin.compile(text, mode='autoadd')
        query = s_stormbin.load(byts)
        self.assertIsInstance(query, s_ast.Lookup)
        self.true(query.autoadd)

    def test_stormbin_mode_search(self):
        '''Test search parse mode.'''
        text = 'hello world'
        byts = s_stormbin.compile(text, mode='search')
        query = s_stormbin.load(byts)
        self.assertIsInstance(query, s_ast.Search)

    def test_stormbin_base64_roundtrip(self):
        '''Test BASE64 encoding/decoding round trip.'''
        text = 'inet:fqdn=vertex.link'
        byts = s_stormbin.compile(text)

        encoded = s_stormbin.enBase64(byts)
        self.assertIsInstance(encoded, str)
        self.true(encoded.startswith('}'))

        decoded = s_stormbin.unBase64(encoded)
        self.eq(byts, decoded)

        query = s_stormbin.load(decoded)
        orig = s_parser.parseQuery(text)
        self._assertAstEqual(orig, query)

    def test_stormbin_base64_load(self):
        '''Test that load accepts } strings directly.'''
        text = 'inet:fqdn=vertex.link'
        byts = s_stormbin.compile(text)
        encoded = s_stormbin.enBase64(byts)

        query = s_stormbin.load(encoded)
        orig = s_parser.parseQuery(text)
        self._assertAstEqual(orig, query)

    def test_stormbin_dump(self):
        '''dump() round-trips an AST node back through load() in both modes.'''
        text = 'inet:fqdn=vertex.link'
        query = s_parser.parseQuery(text)

        # ascii=False returns bytes
        byts = s_stormbin.dump(query)
        self.assertIsInstance(byts, bytes)
        self.eq(query.__class__, s_stormbin.load(byts).__class__)

        # ascii=True returns a }-prefixed base64 string
        enc = s_stormbin.dump(query, ascii=True)
        self.assertIsInstance(enc, str)
        self.true(enc.startswith('}'))
        self.eq(query.__class__, s_stormbin.load(enc).__class__)

        # The two outputs encode the same payload.
        self.eq(byts, s_stormbin.unBase64(enc))

    def test_stormbin_iscompiled(self):
        '''Test compiled input detection.'''
        # Raw bytes are compiled
        self.true(s_stormbin.isCompiled(b'\x00\x01'))

        # } prefixed strings are compiled
        self.true(s_stormbin.isCompiled('}AAAB'))

        # Plain strings are not compiled
        self.false(s_stormbin.isCompiled('inet:fqdn'))
        self.false(s_stormbin.isCompiled(''))

        # Other types are not compiled
        self.false(s_stormbin.isCompiled(42))
        self.false(s_stormbin.isCompiled(None))

    def test_stormbin_pos_preserved(self):
        '''Position info round-trips through compile/load.'''
        text = 'inet:fqdn=vertex.link'
        byts = s_stormbin.compile(text)
        query = s_stormbin.load(byts)
        orig = s_parser.parseQuery(text)
        self.eq(query.astinfo.soff, orig.astinfo.soff)
        self.eq(query.astinfo.eoff, orig.astinfo.eoff)
        self.eq(query.astinfo.sline, orig.astinfo.sline)
        self.eq(query.astinfo.eline, orig.astinfo.eline)
        self.eq(query.astinfo.scol, orig.astinfo.scol)
        self.eq(query.astinfo.ecol, orig.astinfo.ecol)
        self.eq(query.astinfo.isterm, orig.astinfo.isterm)

    def test_stormbin_invalid_version(self):
        '''Test that future versions are rejected.'''
        import synapse.lib.msgpack as s_msgpack
        envelope = (999, (0, [], {}), {})
        byts = s_msgpack.en(envelope)
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.load(byts)
        self.isin('Unsupported stormbin version', cm.exception.errinfo.get('mesg'))

    def test_stormbin_invalid_envelope(self):
        '''Test that malformed envelopes raise BadArg.'''
        import synapse.lib.msgpack as s_msgpack

        # Too few elements
        byts = s_msgpack.en((1, 2))
        with self.raises(s_exc.BadArg):
            s_stormbin.load(byts)

        # Invalid meta type
        byts = s_msgpack.en((1, (0, [], {}), 'notadict'))
        with self.raises(s_exc.BadArg):
            s_stormbin.load(byts)

    def test_stormbin_invalid_typeid(self):
        '''Test that unknown type IDs raise BadArg.'''
        import synapse.lib.msgpack as s_msgpack

        tree = (9999, [], {})
        envelope = (1, tree, {})
        byts = s_msgpack.en(envelope)
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.load(byts)
        self.isin('Unknown AST type ID', cm.exception.errinfo.get('mesg'))

    def test_stormbin_invalid_node_format(self):
        '''Test that invalid node format raises BadArg.'''
        import synapse.lib.msgpack as s_msgpack

        tree = (0, 1)  # Only 2 elements instead of 3
        envelope = (1, tree, {})
        byts = s_msgpack.en(envelope)
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.load(byts)
        self.isin('Invalid AST node format', cm.exception.errinfo.get('mesg'))

    def test_stormbin_depth_limit(self):
        '''Test that excessive nesting is rejected.'''
        queryid = s_ast.Query._bin_id

        # Call un directly with excessive depth
        tree = (queryid, [], {})
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.un(tree, depth=s_stormbin.MAX_DEPTH + 1)
        self.isin('maximum depth', cm.exception.errinfo.get('mesg'))

    def test_stormbin_invalid_mode(self):
        '''Test that invalid mode names are rejected.'''
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.compile('inet:fqdn', mode='invalid')
        self.isin('Invalid storm mode', cm.exception.errinfo.get('mesg'))

    def test_stormbin_invalid_mode_int(self):
        '''Test that invalid mode values in meta are rejected.'''
        import synapse.lib.msgpack as s_msgpack
        queryid = s_ast.Query._bin_id
        tree = (queryid, [], {})
        envelope = (1, tree, {'mode': 'invalid'})
        byts = s_msgpack.en(envelope)
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.load(byts)
        self.isin('Invalid stormbin mode', cm.exception.errinfo.get('mesg'))

    def test_stormbin_bad_base64(self):
        '''Test that invalid base64 data raises BadArg.'''
        with self.raises(s_exc.BadArg):
            s_stormbin.unBase64('}!!!invalid!!!')

        with self.raises(s_exc.BadArg):
            s_stormbin.unBase64('notbase64')

    def test_stormbin_bad_msgpack(self):
        '''Test that invalid msgpack data raises BadArg.'''
        with self.raises(s_exc.BadArg):
            s_stormbin.load(b'\xff\xff\xff')

    def test_stormbin_en_unknown_class(self):
        '''en() rejects an AST node whose class has no _bin_id.'''
        astinfo = s_parser.AstInfo('', 0, 0, 0, 0, 0, 0, False)
        node = s_ast.Value(astinfo)
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.en(node)
        self.isin('Unknown AST class', cm.exception.errinfo.get('mesg'))

    def test_stormbin_invalid_node_meta_type(self):
        '''un() rejects a node whose meta is not a dict.'''
        import synapse.lib.msgpack as s_msgpack
        queryid = s_ast.Query._bin_id
        tree = (queryid, [], 'notadict')
        envelope = (1, tree, {})
        byts = s_msgpack.en(envelope)
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.load(byts)
        self.isin('Invalid AST node metadata', cm.exception.errinfo.get('mesg'))

    def test_stormbin_missing_pos(self):
        '''un() rejects a node whose meta is missing pos.'''
        import synapse.lib.msgpack as s_msgpack
        queryid = s_ast.Query._bin_id
        tree = (queryid, [], {})
        envelope = (1, tree, {})
        byts = s_msgpack.en(envelope)
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.load(byts)
        self.isin('missing pos info', cm.exception.errinfo.get('mesg'))

    def test_stormbin_bad_pos_length(self):
        '''un() rejects a node whose pos tuple isn't 7 elements.'''
        import synapse.lib.msgpack as s_msgpack
        queryid = s_ast.Query._bin_id
        # 6 elements instead of 7
        tree = (queryid, [], {'pos': (0, 0, 0, 0, 0, 0)})
        envelope = (1, tree, {})
        byts = s_msgpack.en(envelope)
        with self.raises(s_exc.BadArg) as cm:
            s_stormbin.load(byts)
        self.isin('Invalid AST node pos info', cm.exception.errinfo.get('mesg'))

    def test_stormbin_attr_default(self):
        '''un() falls back to the default when an attr key is absent.'''
        import synapse.lib.msgpack as s_msgpack
        # Lookup has _bin_attrs = (('autoadd', 'a', False),). Encode with attrs
        # containing some unrelated key so the missing-key branch fires.
        lookupid = s_ast.Lookup._bin_id
        pos = (0, 0, 0, 0, 0, 0, False)
        meta = {'a': {'unused': True}, 'pos': pos}
        tree = (lookupid, [], meta)
        envelope = (1, tree, {'mode': 'lookup'})
        byts = s_msgpack.en(envelope)
        query = s_stormbin.load(byts)
        self.assertIsInstance(query, s_ast.Lookup)
        self.false(query.autoadd)

    def test_stormbin_duplicate_bin_id(self):
        '''AstRegistry raises immediately if a new subclass takes an existing _bin_id.'''
        with self.raises(s_exc.BadArg) as cm:
            class _Duplicate(s_ast.AstNode):
                _bin_id = s_ast.Query._bin_id
        self.isin('Duplicate _bin_id', cm.exception.errinfo.get('mesg'))

    def test_stormbin_load_plain_string(self):
        '''Test that load rejects plain strings.'''
        with self.raises(s_exc.BadArg):
            s_stormbin.load('inet:fqdn')

    async def test_stormbin_cortex_binary(self):
        '''Test that cortex.storm() accepts compiled binary input.'''
        async with self.getTestCore() as core:

            # Add a node via text
            msgs = await core.stormlist('[ inet:fqdn=vertex.link ]')
            self.stormHasNoWarnErr(msgs)

            # Compile a lift query
            byts = s_stormbin.compile('inet:fqdn=vertex.link')

            # Execute the compiled query
            msgs = await core.stormlist(byts)
            self.stormHasNoWarnErr(msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][0], ('inet:fqdn', 'vertex.link'))

    async def test_stormbin_cortex_base64(self):
        '''Test that cortex.storm() accepts } prefixed input.'''
        async with self.getTestCore() as core:

            await core.stormlist('[ inet:fqdn=vertex.link ]')

            byts = s_stormbin.compile('inet:fqdn=vertex.link')
            encoded = s_stormbin.enBase64(byts)

            msgs = await core.stormlist(encoded)
            self.stormHasNoWarnErr(msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)

    async def test_stormbin_cortex_callstorm(self):
        '''Test that callStorm works with compiled binary.'''
        async with self.getTestCore() as core:

            byts = s_stormbin.compile('return((42))')
            result = await core.callStorm(byts)
            self.eq(result, 42)

    async def test_stormbin_cortex_reqvalidstorm(self):
        '''Test that reqValidStorm works with compiled binary.'''
        async with self.getTestCore() as core:
            byts = s_stormbin.compile('inet:fqdn')
            result = await core.reqValidStorm(byts)
            self.true(result)

    async def test_stormbin_cortex_same_results(self):
        '''Test that compiled and text queries produce identical results.'''
        async with self.getTestCore() as core:

            await core.stormlist('[ inet:fqdn=vertex.link inet:fqdn=woot.com ]')

            text = 'inet:fqdn | sort inet:fqdn'
            byts = s_stormbin.compile(text)

            text_msgs = await core.stormlist(text)
            bin_msgs = await core.stormlist(byts)

            text_nodes = [m[1] for m in text_msgs if m[0] == 'node']
            bin_nodes = [m[1] for m in bin_msgs if m[0] == 'node']

            self.eq(text_nodes, bin_nodes)

    async def test_stormbin_http_base64(self):
        '''Test that HTTP API accepts } prefixed queries.'''
        async with self.getTestCore() as core:

            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')

            await core.stormlist('[ inet:fqdn=vertex.link ]')

            byts = s_stormbin.compile('return((42))')
            encoded = s_stormbin.enBase64(byts)

            host, port = await core.addHttpsPort(0)
            async with self.getHttpSess(auth=('root', 'secret'), port=port) as sess:
                data = {'query': encoded}
                async with sess.get(f'https://localhost:{port}/api/v1/storm/call', json=data) as resp:
                    result = await resp.json()
                    self.eq(result.get('status'), 'ok')
                    self.eq(result.get('result'), 42)

    async def test_stormbin_cortex_background(self):
        '''background { ... } executes correctly after compile/load.'''
        async with self.getTestCore() as core:

            byts = s_stormbin.compile('''
                $lib.queue.add(bgq)
                background {
                    [ it:dev:str=haha ]
                    fini { $lib.queue.get(bgq).put(done) }
                }
            ''')

            await core.stormlist(byts)

            # Wait for the background coro to run.
            self.eq((0, 'done'), await core.callStorm('return($lib.queue.get(bgq).get())'))
            self.len(1, await core.nodes('it:dev:str=haha'))

    async def test_stormbin_cortex_batch(self):
        '''batch { ... } executes correctly after compile/load.'''
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=woot.com inet:fqdn=vertex.link ]')

            byts = s_stormbin.compile('''
                inet:fqdn
                batch $lib.true --size 5 {
                    [ it:dev:str=batchran ]
                }
            ''')

            await core.stormlist(byts)
            self.len(1, await core.nodes('it:dev:str=batchran'))

    async def test_stormbin_cortex_view_exec(self):
        '''view.exec runs its inner storm after compile/load.'''
        async with self.getTestCore() as core:

            viden = core.view.iden
            byts = s_stormbin.compile(f'view.exec {viden} {{ [ it:dev:str=viewexec ] }}')

            await core.stormlist(byts)
            self.len(1, await core.nodes('it:dev:str=viewexec'))

    async def test_stormbin_cortex_embed_query(self):
        '''${ ... } embedded queries execute after compile/load.'''
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=vertex.link ]')

            byts = s_stormbin.compile('''
                $q = ${ inet:fqdn=vertex.link }
                $q.exec()
            ''')
            msgs = await core.stormlist(byts)
            self.stormHasNoWarnErr(msgs)

            # And the embedded query yields nodes as expected when iterated.
            byts = s_stormbin.compile('''
                $q = ${ inet:fqdn=vertex.link }
                yield $q
            ''')
            msgs = await core.stormlist(byts)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][0], ('inet:fqdn', 'vertex.link'))
