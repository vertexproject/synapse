import synapse.tests.utils as s_t_utils

import synapse.tools.storm._printer as s_printer

class TestStormPrinter(s_t_utils.SynTest):

    async def test_tools_storm_printer_node(self):

        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)

        node = (
            ('test:str', 'hello'),
            {
                'repr': 'hello',
                'props': {
                    '.created': 1234567890000,
                    '_ext': 'extval',
                    'tick': 1234567890000,
                },
                'reprs': {
                    '.created': '2009/02/13 23:31:30.000',
                    '_ext': 'extval',
                    'tick': '2009/02/13 23:31:30.000',
                },
                'tags': {
                    'foo': (None, None, None),
                    'bar': (1577836800000, 1609459200000, None),
                },
                'tagprops': {
                    'bar': {'risk': 50},
                },
                'tagpropreprs': {
                    'bar': {'risk': '50'},
                },
            },
        )

        printer.printNode(node)
        s = str(outp)
        self.isin('test:str=hello', s)
        self.isin(':tick', s)
        self.isin(':_ext', s)
        self.isin('.created', s)
        self.isin('#bar =', s)
        self.isin('#bar:risk = 50', s)
        self.isin('#foo', s)

        # hideprops suppresses props but not tags
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.hideprops = True
        printer.printNode(node)
        s = str(outp)
        self.isin('test:str=hello', s)
        self.notin(':tick', s)
        self.notin('.created', s)
        self.isin('#foo', s)

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
        outp.expect('complete. 10 nodes in 2000 ms')

        # Very fast (took < 1 gets clamped to 1)
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        printer.printFini(('fini', {'took': 0, 'count': 5}))
        outp.expect('complete. 5 nodes in 1 ms')

    async def test_tools_storm_printer_mesg(self):

        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)

        # Node message
        node = (
            ('test:str', 'hi'),
            {
                'repr': 'hi',
                'props': {},
                'reprs': {},
                'tags': {},
                'tagprops': {},
                'tagpropreprs': {},
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
        outp.expect('complete.')

        # Err message returns False
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        self.false(printer.printMesg(('err', ('SomeErr', {'mesg': 'boom'}))))
        outp.expect('ERROR: boom')

        # node:edits message
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        edits = {'edits': [('iden', 'form', [('edit1',), ('edit2',)])]}
        self.true(printer.printMesg(('node:edits', edits)))
        self.isin('..', str(outp))

        # Unknown message type
        outp = self.getTestOutp()
        printer = s_printer.StormPrinter(outp)
        self.true(printer.printMesg(('init', {})))
        self.eq('', str(outp))
