import synapse.lib.node as s_node

ERROR_COLOR = '#ff0066'
WARNING_COLOR = '#f4e842'
NODEEDIT_COLOR = 'lightblue'

class StormPrinter:

    def __init__(self, outp):
        self.outp = outp
        self.hidetags = False
        self.hideprops = False

    def printf(self, mesg, addnl=True, color=None):
        return self.outp.printf(mesg, addnl=addnl, color=color)

    def _printNodeProp(self, name, valu):
        self.printf(f'        {name} = {valu}')

    def printNode(self, node):

        formname, formvalu = s_node.reprNdef(node)
        self.printf(f'{formname}={formvalu}')

        if not self.hideprops:

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

            for name in props:
                valu = s_node.reprProp(node, name)
                name = ':' + name
                self._printNodeProp(name, valu)

            for name in extns:
                valu = s_node.reprProp(node, name)
                name = ':' + name
                self._printNodeProp(name, valu)

            for name in univs:
                valu = s_node.reprProp(node, name)
                self._printNodeProp(name, valu)

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
        took = max(took, 1)
        count = mesg[1].get('count')
        pers = float(count) / float(took / 1000)
        self.printf('complete. %d nodes in %d ms (%d/sec).' % (count, took, pers))

    def printMesg(self, mesg):
        '''
        Print a Storm message. Returns False for err messages, True otherwise.
        '''
        mtyp = mesg[0]

        if mtyp == 'node':
            self.printNode(mesg[1])
            return True

        if mtyp == 'node:edits':
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
