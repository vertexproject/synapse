import copy
import logging

logger = logging.getLogger(__name__)

class Ingest(object):
    def __init__(self, gestdef):
        self.gestdef = gestdef

    def ingest(self, core):
        '''
        Add nodes to a Cortex with the configured ingest defnition.

        Args:
            core: A Cortex or Cortex proxy object.

        Returns:
            list: A list of nodes created by addNode()
        '''
        pnodes = list(self.genAdds())
        nodes = list(core.addNodes(pnodes))
        return nodes

    def genAdds(self):
        '''
        Generate packed nodes from the gestdef.
        '''
        seen = self.gestdef.get('seen')
        # Track all the ndefs we make so we can make sources
        ndefs = []

        # Make the form nodes
        tags = self.gestdef.get('tags', {})
        forms = self.gestdef.get('forms', {})
        for form, valus in forms.items():
            for valu in valus:
                ndef = [form, valu]
                ndefs.append(ndef)
                obj = [ndef, {'tags': tags}]
                if seen:
                    obj[1]['props'] = {'.seen': (seen, seen)}
                yield obj

        # Make the packed nodes
        nodes = self.gestdef.get('nodes', ())
        for pnode in copy.deepcopy(nodes):
            ndefs.append(pnode[0])
            pnode[1].setdefault('tags', {})
            for tag, valu in tags.items():
                # Tag in the packed node has a higher predecence
                # than the tag in the whole ingest set of data.
                pnode[1]['tags'].setdefault(tag, valu)
            if seen:
                pnode[1].setdefault('props', {})
                pnode[1]['props'].setdefault('.seen', (seen, seen))
            yield pnode

        # Make edges
        for srcdef, etyp, destndefs in self.gestdef.get('edges', ()):
            for destndef in destndefs:
                ndef = [etyp, [srcdef, destndef]]
                ndefs.append(ndef)
                obj = [ndef, {}]
                if seen:
                    obj[1]['props'] = {'.seen': (seen, seen)}
                if tags:
                    obj[1]['tags'] = tags.copy()
                yield obj

        # Make time based edges
        for srcdef, etyp, destndefs in self.gestdef.get('time:edges', ()):
            for destndef, time in destndefs:
                ndef = [etyp, [srcdef, destndef, time]]
                ndefs.append(ndef)
                obj = [ndef, {}]
                if seen:
                    obj[1]['props'] = {'.seen': (seen, seen)}
                if tags:
                    obj[1]['tags'] = tags.copy()
                yield obj

        # Make the source node and links
        source = self.gestdef.get('source')
        if source:
            # Base object
            obj = [['source', source], {}]
            yield obj

            # Subsequent links
            for ndef in ndefs:
                obj = [['seen', (source, ndef)],
                       {'props': {'.seen': (seen, seen)}}]
                yield obj
