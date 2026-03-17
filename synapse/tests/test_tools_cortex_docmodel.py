import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.tools.cortex.docmodel as s_docmodel

class DocModelTest(s_t_utils.SynTest):

    async def test_tools_docmodel_tempcore(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main([], outp=outp), 0)

        text = str(outp)
        self.isin('# Synapse Data Model', text)
        self.isin('## Interfaces', text)
        self.isin('## Forms', text)
        self.isin('## Edges', text)

        # Verify interfaces are present
        self.isin('### `meta:observable`', text)

        # Verify interface forms table is present
        self.isin('| Form |', text)
        self.isin('|------|', text)

        # Verify form-level interfaces table is present
        self.isin('| Interface |', text)
        self.isin('|-----------|', text)

        # Verify inherited interfaces are fully resolved
        # edu:class implements ou:attendable which inherits meta:havable,
        # entity:attendable (which inherits geo:locatable, lang:transcript)
        classidx = text.index('### `edu:class`')
        # Find the next form heading after edu:class
        nextformidx = text.index('### `', classidx + 1)
        classtext = text[classidx:nextformidx]
        self.isin('`ou:attendable`', classtext)
        self.isin('`meta:havable`', classtext)
        self.isin('`entity:attendable`', classtext)
        self.isin('`geo:locatable`', classtext)

        # Verify interface template variables are resolved
        # meta:observable uses {title} with default 'node'
        obsidx = text.index('### `meta:observable`')
        nextidx = text.index('### `', obsidx + 1)
        obstext = text[obsidx:nextidx]
        self.isin('The node was observed during the time interval.', obstext)
        self.notin('{title}', obstext)

        # geo:locatable uses {title} and {happened} defaults
        locidx = text.index('### `geo:locatable`')
        nextidx = text.index('### `', locidx + 1)
        loctext = text[locidx:nextidx]
        self.isin('The place where the item was located.', loctext)
        self.notin('{title}', loctext)
        self.notin('{happened}', loctext)

        # meta:taxonomy uses {$self} which resolves to interface name
        taxidx = text.index('### `meta:taxonomy`')
        nextidx = text.index('### `', taxidx + 1)
        taxtext = text[taxidx:nextidx]
        self.isin('`meta:taxonomy`', taxtext)
        self.notin('{$self}', taxtext)

        # Verify poly types are resolved to their actual type names
        self.notin('| `poly` |', text)

        # Verify array types are resolved to show their element type
        self.notin('| `array` |', text)
        self.isin('`array of inet:fqdn`', text)

        # Verify forms are present
        self.isin('### `inet:ip`', text)
        self.isin('### `inet:fqdn`', text)

        # Verify properties are present with docs
        self.isin('| Property | Type | Doc |', text)
        self.isin('`:asn`', text)

        # Verify edges are present
        self.isin('| Source | Verb | Target | Doc |', text)
        self.isin('`refs`', text)

    async def test_tools_docmodel_cortex(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            lurl = core.getLocalUrl()

            outp = self.getTestOutp()
            self.eq(await s_docmodel.main(['--cortex', lurl], outp=outp), 0)

            text = str(outp)
            self.isin('# Synapse Data Model', text)
            self.isin('## Interfaces', text)
            self.isin('## Forms', text)
            self.isin('## Edges', text)

    async def test_tools_docmodel_save(self):

        with self.getTestDir() as dirn:

            filepath = s_common.genpath(dirn, 'datamodel.md')

            outp = self.getTestOutp()
            self.eq(await s_docmodel.main(['--save', filepath], outp=outp), 0)

            outp.expect('Model documentation written to')

            with open(filepath, 'r') as fd:
                text = fd.read()

            self.isin('# Synapse Data Model', text)
            self.isin('## Interfaces', text)
            self.isin('## Forms', text)
            self.isin('## Edges', text)
            self.isin('### `inet:ip`', text)

    def test_tools_docmodel_resolvetypenames(self):

        resolve = s_docmodel._resolveTypeNames

        # Falsy inputs
        self.eq(resolve(None), [''])
        self.eq(resolve(''), [''])
        self.eq(resolve(()), [''])
        self.eq(resolve([]), [''])

        # String input
        self.eq(resolve('inet:fqdn'), ['inet:fqdn'])

        # Poly with interfaces
        self.eq(resolve(('poly', {'interfaces': ['b', 'a']})), ['a', 'b'])

        # Poly with forms
        self.eq(resolve(('poly', {'forms': ['z', 'm']})), ['m', 'z'])

        # Poly with both interfaces and forms aggregated, uniqued, and sorted
        self.eq(resolve(('poly', {'interfaces': ['c', 'a'], 'forms': ['b', 'a']})), ['a', 'b', 'c'])

        # Poly with non-dict opts
        self.eq(resolve(('poly', 'notadict')), ['poly'])

        # Bare poly with no interfaces or forms
        self.eq(resolve(('poly', {})), ['poly'])

        # Array with string element type
        self.eq(resolve(('array', {'type': 'inet:fqdn'})), ['array of inet:fqdn'])

        # Array with tuple element type
        self.eq(resolve(('array', {'type': ('str', 'int')})), ['array of int, str'])

        # Array with non-dict opts
        self.eq(resolve(('array', 'notadict')), ['array'])

        # Array with no type key
        self.eq(resolve(('array', {})), ['array'])

        # Generic tuple type (not poly or array)
        self.eq(resolve(('str', {})), ['str'])
        self.eq(resolve(('int',)), ['int'])

        # Non-string, non-tuple, non-list input
        self.eq(resolve(12345), [''])

    async def test_tools_docmodel_sorted(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main([], outp=outp), 0)

        text = str(outp)
        lines = text.split('\n')

        # Verify forms are sorted alphabetically
        formsidx = next(i for i, line in enumerate(lines) if line == '## Forms')
        edgesidx = next(i for i, line in enumerate(lines) if line == '## Edges')
        formlines = [line for line in lines[formsidx:edgesidx] if line.startswith('### `')]
        formnames = [line[5:-1] for line in formlines]
        self.eq(formnames, sorted(formnames))

        # Verify interfaces are sorted alphabetically
        ifaceidx = next(i for i, line in enumerate(lines) if line == '## Interfaces')
        ifacelines = [line for line in lines[ifaceidx:] if line.startswith('### `')]
        ifacenames = [line[5:-1] for line in ifacelines]
        self.eq(ifacenames, sorted(ifacenames))
        self.gt(len(ifacenames), 0)

        # Verify edges are sorted by extracting source/verb/target tuples
        edgeidx = next(i for i, line in enumerate(lines) if line == '## Edges')
        headeridx = next(i for i in range(edgeidx, len(lines)) if lines[i].startswith('| Source'))
        edgekeys = []
        for line in lines[headeridx + 2:]:
            if not line.startswith('|'):
                break
            parts = [p.strip().strip('`') for p in line.split('|')[1:4]]
            # Normalize \* back to * for sorting comparison
            parts = [p.replace('\\*', '*') for p in parts]
            edgekeys.append(tuple(parts))
        self.gt(len(edgekeys), 0)
        self.eq(edgekeys, sorted(edgekeys))
