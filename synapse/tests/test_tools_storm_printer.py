import synapse.tests.utils as s_t_utils

import synapse.tools.storm._printer as s_printer

class TestStormPrinter(s_t_utils.SynTest):

    async def test_tools_storm_printer_node(self):

        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)

        node = (
            ('test:str', 'hello'),
            {
                'meta': {
                    'created': 1234567890000000,
                    'updated': 1234567900000000,
                },
                'props': {
                    '.newp': (1, {}),
                    '_ext': ('extval', {'t': 'str'}),
                    'tick': (1234567890000, {'t': 'time', 'r': '2009/02/13 23:31:30.000'}),
                    'seen': ((1577836800000, 1609459200000, None), {'t': 'ival', 'v': {
                        'min': (1577836800000, {'r': '2020/01/01'}),
                        'max': (1609459200000, {'r': '2021/01/01'}),
                        'duration': (31622400000, {}),
                    }}),
                },
                'valuinfo': {
                    'r': 'hello',
                    'v': {
                        'port': (80, {}),
                        'ip': ((4, 16909060), {'r': '1.2.3.4'}),
                    },
                },
                'tags': {
                    'foo': ((None, None, None), {}),
                    'bar': ((1577836800000, 1609459200000, None), {'r': '2020/01/01 - 2021/01/01'}),
                },
                'tagprops': {
                    'bar': {'risk': (50, {'r': '50'})},
                },
                'n1verbs': {'refs': {'inet:fqdn': 2, 'inet:ip': 1}},
                'n2verbs': {'seen': {'meta:source': 3}},
            },
        )

        printer.printNode(node)
        s = str(outp)
        self.isin('test:str=hello', s)
        self.isin(':tick', s)
        self.isin(':_ext', s)
        self.isin('#bar =', s)
        self.isin('#bar:risk = 50', s)
        self.isin('#foo', s)

        # a primary virt is named with a leading dot, and without a model virts print as packed
        self.isin('        .port = 80\n        .ip = 1.2.3.4\n', s)

        # a prop virt is named after the prop it belongs to and follows it
        self.isin('        :seen = ', s)
        self.isin('        :seen.min = 2020/01/01\n        :seen.max = 2021/01/01\n', s)
        self.lt(s.index(':seen = '), s.index(':seen.min ='))

        # a virt with no repr falls back to the value
        self.isin('        :seen.duration = 31622400000\n', s)

        # a name the model does not define still prints, with its virts
        self.isin('        .newp = 1\n', s)

        # a meta prop is a time and is rendered without a repr from the Cortex
        self.isin('        .created = 2009-02-13T23:31:30Z\n', s)
        self.isin('        .updated = 2009-02-13T23:31:40Z\n', s)

        # edge counts roll up from the wildcard total down to each verb and form
        self.isin('        -(*)> * = 3\n', s)
        self.isin('         -(refs)> * = 3\n', s)
        self.isin('          -(refs)> inet:fqdn = 2\n', s)
        self.isin('          -(refs)> inet:ip = 1\n', s)
        self.isin('        <(*)- * = 3\n', s)
        self.isin('         <(seen)- * = 3\n', s)
        self.isin('          <(seen)- meta:source = 3\n', s)

        # with a model, virts print in declared order, a poly prop's member virts
        # lead its type's own, and an undeclared name follows the declared ones
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.modeldict = {
            'types': {
                'test:str': {'info': {'virts': (('ip', ('inet:ip', {}), {}), ('port', ('inet:port', {}), {}))}},
                'poly': {'info': {'virts': (('duration', ('duration', {}), {}),)}},
            },
            'forms': {
                'test:str': {'props': {
                    'seen': {'type': ('poly', {}), 'virts': (('max', ('time', {}), {}),)},
                }},
            },
        }
        printer.printNode(node)
        s = str(outp)
        self.isin('        .ip = 1.2.3.4\n        .port = 80\n', s)
        self.isin('        :seen.max = 2021/01/01\n'
                  '        :seen.duration = 31622400000\n'
                  '        :seen.min = 2020/01/01\n', s)

        # a form the model does not define prints its virts as packed
        outp.clear()
        printer.printNode((('newp:form', 'x'), {
            'props': {'foo': ('bar', {'v': {'b': (2, {}), 'a': (1, {})}})},
            'valuinfo': {'v': {'d': (4, {}), 'c': (3, {})}},
            'tags': {},
            'tagprops': {},
        }))
        self.eq(str(outp), 'newp:form=x\n'
                           '        .d = 4\n'
                           '        .c = 3\n'
                           '        :foo = bar\n'
                           '        :foo.b = 2\n'
                           '        :foo.a = 1\n')

        # hideprops suppresses props, virts, and meta but not tags or edges
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.hideprops = True
        printer.printNode(node)
        s = str(outp)
        self.isin('test:str=hello', s)
        self.notin(':tick', s)
        self.notin('.created', s)
        self.notin('.port', s)
        self.notin(':seen.min', s)
        self.isin('#foo', s)
        self.isin('-(refs)> inet:fqdn = 2', s)

        # hideedges suppresses edge counts but not props or tags
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.hideedges = True
        printer.printNode(node)
        s = str(outp)
        self.isin(':tick', s)
        self.isin('#foo', s)
        self.notin('-(refs)>', s)
        self.notin('<(seen)-', s)

        # a node with no edges prints no edge lines
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.printNode((('test:str', 'hi'), {'props': {}, 'tags': {}, 'tagprops': {}}))
        s = str(outp)
        self.eq('test:str=hi\n', s)

        # hidetags suppresses tags but not props
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.hidetags = True
        printer.printNode(node)
        s = str(outp)
        self.isin(':tick', s)
        self.notin('#foo', s)

        # _printNodeProp override is called by printNode
        called = []

        class CustomPrinter(s_printer.StormPrinter):
            def _printNodeProp(self, name, valu):
                called.append((name, valu))
                self.printf(f'CUSTOM: {name} = {valu}')

        outp = self.getTestOutp()
        printer = CustomPrinter(outp)
        printer.printNode(node)
        s = str(outp)
        self.isin('CUSTOM: :tick =', s)
        self.gt(len(called), 0)

    async def test_tools_storm_printer_err(self):

        # BadSyntax with caret
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        mesg = ('err', ('BadSyntax', {'at': 3, 'text': '%%%badquery', 'mesg': 'bad input'}))
        printer.printErr(mesg)
        s = str(outp)
        self.isin('Syntax Error: bad input', s)
        self.isin('^', s)

        # Long text truncation (error near end -- trailing ...)
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        longtext = 'inet:fqdn=a.b.c.d.e.f.g.h.i.j.k.l.m.n.o.p.q.r.s.t.u.v.w.x %%%'
        mesg = ('err', ('BadSyntax', {'at': len(longtext) - 3, 'text': longtext, 'mesg': 'bad input'}))
        printer.printErr(mesg)
        s = str(outp)
        self.isin('Syntax Error:', s)

        # Long text truncation (error in middle -- leading and trailing ...)
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        padding = 'a' * 40
        midtext = f'{padding} %%% {padding}'
        mesg = ('err', ('BadSyntax', {'at': 41, 'text': midtext, 'mesg': 'bad input'}))
        printer.printErr(mesg)
        s = str(outp)
        self.isin('...', s)
        self.isin('Syntax Error:', s)

        # Generic error
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        mesg = ('err', ('FooBar', {'mesg': 'something broke'}))
        printer.printErr(mesg)
        s = str(outp)
        self.isin('ERROR: something broke', s)

        # Generic error without mesg key
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        mesg = ('err', ('FooBar', {}))
        printer.printErr(mesg)
        s = str(outp)
        self.isin('ERROR: FooBar', s)

    async def test_tools_storm_printer_warn(self):

        # Warn with extras
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.printWarn(('warn', {'mesg': 'bad thing', 'key': 'val'}))
        outp.expect('WARNING: bad thing key=val')

        # Warn without extras
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.printWarn(('warn', {'mesg': 'simple warning'}))
        outp.expect('WARNING: simple warning')

    async def test_tools_storm_printer_fini(self):

        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.printFini(('fini', {'took': 2000, 'count': 10}))
        outp.expect('complete. 10 nodes in 0.002 sec (5000/sec).')

        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.printFini(('fini', {'took': 3558, 'count': 3}))
        outp.expect('complete. 3 nodes in 0.003558 sec (843/sec).')

        # a minute or more prints as a duration, without a sec suffix
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.printFini(('fini', {'took': 90070200000, 'count': 90070200}))
        outp.expect('complete. 90070200 nodes in 1D 01:01:10.2 (1000/sec).')

        # zero took prints as zero and clamps the rate divisor
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.printFini(('fini', {'took': 0, 'count': 5}))
        outp.expect('complete. 5 nodes in 0 sec (5000000/sec).')

        self.eq('0 sec', s_printer.reprTook(0))
        self.eq('0.003558 sec', s_printer.reprTook(3558))
        self.eq('2 sec', s_printer.reprTook(2000000))
        self.eq('3.5 sec', s_printer.reprTook(3500000))
        self.eq('10 sec', s_printer.reprTook(10000000))
        self.eq('10.2 sec', s_printer.reprTook(10200000))
        self.eq('59.999999 sec', s_printer.reprTook(59999999))

        self.eq('01:00', s_printer.reprTook(60000000))
        self.eq('01:10.2', s_printer.reprTook(70200000))
        self.eq('01:01:10.2', s_printer.reprTook(3670200000))
        self.eq('01:00:00', s_printer.reprTook(3600000000))
        self.eq('1D 00:00:00', s_printer.reprTook(86400000000))
        self.eq('1D 01:01:10.2', s_printer.reprTook(90070200000))

    async def test_tools_storm_printer_mesg(self):

        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)

        # Node message
        node = (
            ('test:str', 'hi'),
            {
                'valuinfo': {'r': 'hi'},
                'props': {},
                'tags': {},
                'tagprops': {},
            },
        )
        self.true(printer.printMesg(('node', node)))
        outp.expect('test:str=hi')

        # Print message
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        self.true(printer.printMesg(('print', {'mesg': 'hello world'})))
        outp.expect('hello world')

        # Warn message
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        self.true(printer.printMesg(('warn', {'mesg': 'uh oh'})))
        outp.expect('WARNING: uh oh')

        # Fini message
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        self.true(printer.printMesg(('fini', {'took': 1000, 'count': 3})))
        outp.expect('complete. 3 nodes in 0.001 sec (3000/sec).')

        # Err message returns False
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        self.false(printer.printMesg(('err', ('SomeErr', {'mesg': 'boom'}))))
        outp.expect('ERROR: boom')

        # edits message
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        edits = {'edits': [('iden', 'form', [('edit1',), ('edit2',)])]}
        self.true(printer.printMesg(('edits', edits)))
        self.isin('..', str(outp))

        # Unknown message type
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        self.true(printer.printMesg(('init', {})))
        self.eq('', str(outp))
