import collections

import xml.etree.ElementTree as x_etree

import synapse.lib.syntax as s_syntax

class DataElem:

    def __init__(self, item, name=None, parent=None):
        self._d_name = name
        self._d_item = item
        self._d_parent = parent
        self._d_special = {'..':parent,'.':self}

    def _elem_valu(self):
        return self._d_item

    def _elem_step(self, step):
        try:
            item = self._d_item[step]
        except Exception as e:
            return None
        return initelem(item,name=step,parent=self)

    def _elem_kids(self, step):
        # Most primitives only have 1 child at a given step...
        # However, we must handle the case of nested children
        # during this form of iteration to account for constructs
        # like XML/HTML ( See XmlDataElem )
        try:
            item = self._d_item[step]
        except Exception as e:
            return

        yield initelem(item,name=step,parent=self)

    def step(self, path):
        '''
        Step to the given DataElem within the tree.
        '''
        base = self
        for step in self._parse_path(path):

            spec = base._d_special.get(step)
            if spec != None:
                base = spec
                continue

            base = base._elem_step(step)
            if base == None:
                return None

        return base

    def valu(self, path):
        '''
        Return the value of the element at the given path.
        '''
        if not path:
            return self._elem_valu()

        elem = self.step(path)
        return elem._elem_valu()

    def vals(self, path):
        '''
        Iterate the given path elements and yield values.

        Example:

            data = { 'foo':[ {'bar':'lol'}, {'bar':'heh'} ] }

            root = s_datapath.initelem(data)

            for elem in root.iter('foo/*/bar'):
                dostuff(elem) # elem is at value "lol" and "heh"
        '''
        for elem in self.iter(path):
            yield elem._elem_valu()

    def _elem_iter(self):
        for i,item in enumerate(self._d_item):
            yield initelem(item,name=str(i),parent=self)

    def iter(self, path):
        '''
        Iterate sub elements using the given path.

        Example:

            data = { 'foo':[ {'bar':'lol'}, {'bar':'heh'} ] }

            root = s_datapath.initelem(data)

            for elem in root.iter('foo/*/bar'):
                dostuff(elem) # elem is at value "lol" and "heh"

        '''
        steps = self._parse_path(path)
        if not steps:
            return

        omax = len(steps) - 1
        todo = collections.deque([ (self,0) ] )

        while todo:
            base,off = todo.popleft()

            step = steps[off]

            # some special syntax for "all kids" / iterables
            if step == '*':
                for elem in base._elem_iter():

                    if off == omax:
                        yield elem
                    else:
                        todo.append( (elem,off+1) )

                continue

            for elem in base._elem_kids(step):
                if off == omax:
                    yield elem
                else:
                    todo.append( (elem,off+1) )

    def _parse_path(self, path):

        off = 0
        steps = []

        plen = len(path)
        while off < plen:

            # eat the next (or possibly a first) slash
            _,off = s_syntax.nom(path,off,('/',))

            if off >= plen:
                break

            if s_syntax.is_literal(path,off):
                elem,off = s_syntax.parse_literal(path,off)
                steps.append(elem)
                continue

            # eat until the next /
            elem,off = s_syntax.meh(path,off,('/',))
            if not elem:
                continue

            steps.append(elem)

        return steps

class XmlDataElem(DataElem):

    def __init__(self, item, name=None, parent=None):
        DataElem.__init__(self, item, name=name, parent=parent)

    def _elem_kids(self, step):
        #TODO possibly make step fnmatch compat?
        for xmli in self._d_item:
            if xmli.tag == step:
                yield XmlDataElem(xmli,name=step,parent=self)

    def _elem_step(self, step):

        # optional explicit syntax for dealing with colliding
        # attributes and sub elements.
        if step.startswith('$'):
            item = self._d_item.attrib.get(step[1:])
            if item == None:
                return None

            return initelem(item,name=step,parent=self)

        for xmli in self._d_item:
            if xmli.tag == step:
                return XmlDataElem(xmli,name=step,parent=self)

        item = self._d_item.attrib.get(step)
        if item != None:
            return initelem(item,name=step,parent=self)

    def _elem_valu(self):
        return self._d_item.text

    def _elem_iter(self):
        for item in self._d_item:
            yield initelem(item,name=item.tag,parent=self)

# Special Element Handler Classes
elemcls = {
    x_etree.Element:XmlDataElem,
}

def initelem(item, name=None, parent=None):
    '''
    Construct a new DataElem from the given item using
    which ever DataElem class is most correct for the type.

    Example:

        elem = initelem(

    '''
    ecls = elemcls.get(type(item),DataElem)
    return ecls(item,name=name,parent=parent)
