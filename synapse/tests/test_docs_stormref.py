import os
import asyncio

import regex

import synapse

import synapse.tests.utils as s_tests
import synapse.lib.stormlib.modelext as s_modelext

def getCmdSections(text):
    '''
    The command name of every section heading in a command reference page.

    Args:
        text (str): The rendered page.

    Returns:
        set: The heading names.
    '''
    return set(regex.findall(r'^#{2,4} (\S+)$', text, regex.MULTILINE))

def getListedCmds(text):
    '''
    The command and group names listed at the top of a command reference page.

    Args:
        text (str): The page text.

    Returns:
        set: The names the list links to.
    '''
    start = text.index('## Storm Command Reference')
    end = text.index('<a id="storm-help">')

    return set(regex.findall(r'^- \[([^\]]+)\]', text[start:end], regex.MULTILINE))

def getListedAnchors(text):
    '''
    The anchors the list at the top of a command reference page links to.

    Args:
        text (str): The page text.

    Returns:
        list: The anchor names.
    '''
    start = text.index('## Storm Command Reference')
    end = text.index('<a id="storm-help">')

    return regex.findall(r'^- \[[^\]]+\]\(storm_ref_cmd\.md#([a-z0-9-]+)\)',
                         text[start:end], regex.MULTILINE)

class DocsStormRefTest(s_tests.SynTest):

    async def test_storm_ref_cmd_covers_every_command(self):

        # Every command a Cortex registers has a section of its own in the
        # command reference, and that section carries the command's own help
        # output. Adding a command fails this until it is documented.
        path = os.path.join(os.path.dirname(synapse.__file__),
                            'assets', 'docs', 'userguides', 'storm_ref_cmd.md')

        with open(path, 'r') as fd:
            text = fd.read()

        heads = getCmdSections(text)

        async with self.getTestCore() as core:
            names = sorted(core.stormcmds)
            await asyncio.sleep(0)

        self.gt(len(names), 100)

        self.eq([], [n for n in names if n not in heads])
        self.eq([], [n for n in names if f'storm> {n} --help' not in text])

        # a description declared in Python carries its source indentation into
        # the help text, so a continuation line has to come back flush
        self.isin('\nWhen this is used a Storm pipeline, only the first instance of a\n', text)

        # the list at the top of the page names every section on it, and each
        # entry links to an anchor which exists
        self.eq(getListedCmds(text), set(regex.findall(r'^## (\S+)$', text, regex.MULTILINE)))
        self.eq([], [a for a in getListedAnchors(text) if f'<a id="{a}">' not in text])

    async def test_storm_lib_modelext_covers_every_function(self):

        # Every $lib.model.ext function is shown in the Extended Model guide.
        # Adding a function fails this until it is documented.
        path = os.path.join(os.path.dirname(synapse.__file__),
                            'assets', 'docs', 'storm_lib_modelext.md')

        with open(path, 'r') as fd:
            text = fd.read()

        names = [lcl['name'] for lcl in s_modelext.LibModelExt._storm_locals]

        self.gt(len(names), 10)
        self.eq([], [n for n in names if f'$lib.model.ext.{n}(' not in text])

        # The guide links the library and each function to an anchor in the library reference
        path = os.path.join(os.path.dirname(path), 'stormtypes_libs.md')
        with open(path, 'r') as fd:
            libs = fd.read()

        anchors = ['stormlibs-lib-model-ext'] + [f'stormlibs-lib-model-ext-{n}' for n in names]
        self.eq([], [a for a in anchors if f'](stormtypes_libs.md#{a})' not in text])
        self.eq([], [a for a in anchors if f'<a id="{a}"></a>' not in libs])
