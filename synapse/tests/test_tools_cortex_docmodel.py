import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.tools.cortex.docmodel as s_docmodel

class DocModelTest(s_t_utils.SynTest):

    async def test_tools_docmodel_tempcore(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main([], outp=outp), 0)

        text = str(outp)
        self.isin('# Synapse Data Model', text)
        self.isin('## Forms', text)
        self.isin('## Edges', text)

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
            self.isin('## Forms', text)
            self.isin('## Edges', text)
            self.isin('### `inet:ip`', text)

    async def test_tools_docmodel_sorted(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main([], outp=outp), 0)

        text = str(outp)
        lines = text.split('\n')

        # Verify forms are sorted alphabetically
        formlines = [line for line in lines if line.startswith('### `')]
        formnames = [line[5:-1] for line in formlines]
        self.eq(formnames, sorted(formnames))

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
