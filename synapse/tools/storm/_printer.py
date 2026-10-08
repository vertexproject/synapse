import synapse.lib.node as s_node
import synapse.lib.time as s_time

ERROR_COLOR = '#ff0066'
WARNING_COLOR = '#f4e842'
NODEEDIT_COLOR = 'lightblue'

def reprTook(took):
    '''
    Return a display string for a duration in microseconds.

    Durations under a minute are shown in seconds with a ``sec`` suffix,
    longer ones as ``[ND ]HH:MM:SS[.ffffff]`` with leading zero fields trimmed.
    '''
    if took < s_time.onemin:
        secs, micros = divmod(took, s_time.onesec)
        valu = f'{secs}.{micros:06d}'.rstrip('0').rstrip('.')
        return f'{valu} sec'

    days, rem = divmod(took, s_time.oneday)
    hours, rem = divmod(rem, s_time.onehour)
    mins, rem = divmod(rem, s_time.onemin)
    secs, micros = divmod(rem, s_time.onesec)

    frac = ''
    if micros:
        frac = f'.{micros:06d}'.rstrip('0')

    if days:
        return f'{days}D {hours:02d}:{mins:02d}:{secs:02d}{frac}'

    if hours:
        return f'{hours:02d}:{mins:02d}:{secs:02d}{frac}'

    return f'{mins:02d}:{secs:02d}{frac}'

class StormPrinter:

    def __init__(self, outp):
        self.outp = outp
        self.hidetags = False
        self.hideprops = False
        self.hideedges = False

        # orders virts as the model declares them; without it they print as packed
        self.modeldict = None

    def printf(self, mesg, addnl=True, color=None):
        return self.outp.printf(mesg, addnl=addnl, color=color)

    def _printNodeProp(self, name, valu):
        self.printf(f'        {name} = {valu}')

    def _printNodeEdge(self, verb, form, count, level, n2=False):
        indent = ' ' * (8 + level)
        edge = f'<({verb})- {form}' if n2 else f'-({verb})> {form}'
        self.printf(f'{indent}{edge} = {count}')

    def _getVirtDefs(self, form, prop=None):

        if self.modeldict is None:
            return ()

        if prop is None:
            return self._getTypeVirtDefs(form)

        if (fdef := self.modeldict['forms'].get(form)) is None:
            return ()

        if (pdef := fdef['props'].get(prop)) is None:
            return ()

        # a poly prop declares its member virts ahead of its type's own
        return (*pdef.get('virts', ()), *self._getTypeVirtDefs(pdef['type'][0]))

    def _getTypeVirtDefs(self, name):

        if (tdef := self.modeldict['types'].get(name)) is None:
            return ()

        return tdef['info'].get('virts', ())

    def _printVirts(self, virts, vdefs, name):

        order = {}
        for vdef in vdefs:
            order.setdefault(vdef[0], len(order))

        for virt in sorted(virts, key=lambda v: order.get(v, len(order))):
            self._printNodeProp(f'{name}.{virt}', virts[virt])

    def _printPropVirts(self, node, prop, name):
        virts = s_node.reprPropVirts(node, prop)
        self._printVirts(virts, self._getVirtDefs(s_node.ndef(node)[0], prop), name)

    def _printNodeEdges(self, node):

        for n2 in (False, True):

            counts = s_node.edgeCounts(node, n2=n2)
            if not counts:
                continue

            total = sum(sum(forms.values()) for forms in counts.values())
            self._printNodeEdge('*', '*', total, 0, n2=n2)

            for verb in sorted(counts):

                forms = counts[verb]
                self._printNodeEdge(verb, '*', sum(forms.values()), 1, n2=n2)

                for form in sorted(forms):
                    self._printNodeEdge(verb, form, forms[form], 2, n2=n2)

    def printNode(self, node):

        formname, formvalu = s_node.reprNdef(node)
        self.printf(f'{formname}={formvalu}')

        if not self.hideprops:

            self._printVirts(s_node.reprVirts(node), self._getVirtDefs(formname), '')

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

            for name in props + extns:
                valu = s_node.reprProp(node, name)
                self._printNodeProp(':' + name, valu)
                self._printPropVirts(node, name, ':' + name)

            for name in univs:
                valu = s_node.reprProp(node, name)
                self._printNodeProp(name, valu)
                self._printPropVirts(node, name, name)

            for name, valu in sorted(s_node.reprMetas(node).items()):
                self._printNodeProp(f'.{name}', valu)

        if not self.hidetags:

            for tag in sorted(s_node.tagsnice(node)):

                valu = s_node.reprTag(node, tag)
                tprops = s_node.reprTagProps(node, tag)
                printed = False
                if valu:
                    self.printf(f'        #{tag} = {valu}')
                    printed = True

                if tprops:
                    for prop, pval in tprops:
                        self.printf(f'        #{tag}:{prop} = {pval}')
                    printed = True

                if not printed:
                    self.printf(f'        #{tag}')

        if not self.hideedges:
            self._printNodeEdges(node)

    def printErr(self, mesg):
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

                self.printf(text)
                self.printf(f'{" " * pos}^')
                self.printf(f'Syntax Error: {emsg}', color=ERROR_COLOR)
                return

        text = err[1].get('mesg', err[0])
        self.printf(f'ERROR: {text}', color=ERROR_COLOR)

    def printWarn(self, mesg):
        info = mesg[1].copy()
        warn = info.pop('mesg', '')
        xtra = ', '.join([f'{k}={v}' for k, v in info.items()])
        if xtra:
            warn = ' '.join([warn, xtra])
        self.printf(f'WARNING: {warn}', color=WARNING_COLOR)

    def printFini(self, mesg):
        took = mesg[1].get('took')
        count = mesg[1].get('count')
        rate = count * s_time.onesec // max(took, 1)
        self.printf(f'complete. {count} nodes in {reprTook(took)} ({rate}/sec).')

    def printMesg(self, mesg):
        '''
        Print a Storm message. Returns False for err messages, True otherwise.
        '''
        mtyp = mesg[0]

        if mtyp == 'node':
            self.printNode(mesg[1])
            return True

        if mtyp == 'edits':
            edit = mesg[1]
            count = sum(len(e[2]) for e in edit.get('edits', ()))
            self.printf('.' * count, addnl=False, color=NODEEDIT_COLOR)
            return True

        if mtyp == 'fini':
            self.printFini(mesg)
            return True

        if mtyp == 'print':
            self.printf(mesg[1].get('mesg'))
            return True

        if mtyp == 'warn':
            self.printWarn(mesg)
            return True

        if mtyp == 'err':
            self.printErr(mesg)
            return False

        return True
