'''
An API to assist with the creation and enforcement of cortex data models.
'''
import fnmatch

class ModelError(Exception):pass
class NoSuchProp(ModelError):pass
class NoSuchType(ModelError):pass
class NoSuchTufo(ModelError):pass

class DupDataType(ModelError):pass
class DupTufoName(ModelError):pass
class DupTufoProp(ModelError):pass

class BadEnumValu(ModelError):
    def __init__(self, enum, valu):
        ModelError.__init__(self, '%s: %s' % (enum, valu))

class DataType:
    '''
    Base class for the  data types system.
    '''

    def __init__(self):
        pass

    def norm(self, valu):
        '''
        Return a "purified" system mode value from system mode input.
        '''
        return valu

    def repr(self, valu):
        '''
        Return a humon display form from system form.
        '''
        return valu

    def parse(self, text):
        '''
        Parse humon readable input and return system form.
        '''
        return text

class StrType(DataType):
    '''
    Simple sting type with no constraints.
    '''
    pass

class LwrType(DataType):

    def norm(self, valu):
        return valu.lower()

    def parse(self, text):
        return text.lower()

class TagType(DataType):
    '''
    Tag string type which normalizes to lower case.
    '''

    def norm(self, valu):
        return valu.lower()

    def parse(self, text):
        parts = text.lower().split('.')
        return '.'.join( [ p.strip() for p in parts ] )

class IntType(DataType):
    '''
    Simple integer type with no constraints.
    '''
    def repr(self, valu):
        return str(valu)

    def parse(self, text):
        return int(text)

class GuidType(DataType):

    def parse(self, text):
        # FIXME check for valid hex
        return text

class EnumType(DataType):

    def __init__(self, name, tags):
        self.name = name
        self.tags = tags

    def norm(self, valu):
        if valu not in self.tags:
            raise BadEnumValu(self.name,valu)
        return valu

    def parse(self, text):
        if text not in self.tags:
            raise BadEnumValu(self.name,text)
        return valu

#FIXME TODO
#class TimeType(DataType):
#class Ipv4Type(DataType):
#class Ipv4StrType(DataType):
#class CidrType(DataType):
#class HexType(DataType): # __init__(self, size):

class DataModel:

    def __init__(self, model=None):

        self.types = {}
        self.model = {}

        if model != None:
            self.model.update(model)

        self.model.setdefault('ver', (0,0,0))

        self.model.setdefault('enums',{})
        self.model.setdefault('tufos',{})
        self.model.setdefault('props',{})
        self.model.setdefault('globs',{})

        self.addDataType('int', IntType())
        self.addDataType('lwr', LwrType())
        self.addDataType('str', StrType())
        self.addDataType('tag', TagType())

        self.addDataType('guid', GuidType())

        for name,tags in self.model.get('enums').items():
            self._loadDataEnum(enum,tags)

    def getDataVer(self):
        return self.model.get('ver')

    def setDataVer(self, maj, min, rev):
        '''
        Set the data modle version for this data model.

        Example:

            model.setDataVer(1,2,3)

        '''
        self.model['ver'] = (maj, min, rev)

    def _loadDataEnum(self, enum, tags):
        self.addDataType(enum, EnumType(enum,tags))

    def addDataTufo(self, name, ptype='str'):
        '''
        Add a named tufo to the data model

        Example:

            # must add tufo before adding tufo props
            model.addDataTufo('woot')

        '''
        tufos = self.model.get('tufos')
        tdef = tufos.get(name)
        if tdef != None:
            raise DupTufoName(name)

        tufos[name] = {'props':[]}

        self.addTufoProp(name, name, ptype=ptype)

    def getTufoDef(self, name):
        '''
        Return the tufo definition by name.
        '''
        tdef = self.model['tufos'].get(name)
        if tdef == None:
            raise NoSuchTufo(name)
        return tdef

    def addDataEnum(self, enum, tags):
        '''
        Add an enum data type to the data model.

        Example:

            model.addDataEnum('woot', ('foo','bar','baz','faz') )

        '''
        if self.types.get(enum) != None:
            raise DupDataType(enum)

        enums = self.model.get('enums')
        tags = enums.get(enum)
        if tags != None:
            raise DupDataType(enum)

        enums[enum] = tags
        self._loadDataEnum(enum,tags)

    def addDataType(self, name, typeobj):
        '''
        Add a data type validator/parser to the data model.

        Example:

            class FooType(DataType):
                # over-ride stuff

            model.addDataType('foo', FooType() )

        '''
        if self.types.get(name) != None:
            raise DupDataType(name)
        self.types[name] = typeobj

    def getDataType(self, name):
        '''
        Return the DataType instance for the given type name.

        Example:

            typeobj = model.getDataType('int')

        '''
        typeobj = self.types.get(name)
        if typeobj == None:
            raise NoSuchType(name)
        return typeobj

    def getModelDict(self):
        '''
        Return the model dictionary for the current data model.

        Example:

            md = model.getModelDict()

        '''
        return dict(self.model)

    def addTufoProp(self, name, prop, ptype='str', uniq=False, defval=None, **info):
        '''
        Add a property to the data model.

        Example:

            # all foo tufos must have a foo:bar property
            model.addTufoProp('foo', 'foo:bar', ptype='int', defval=0)

        '''
        props = self.model.get('props')
        if props.get(prop) != None:
            raise DupTufoProp(prop)

        tdef = self.getTufoDef(name)
        dtype = self.getDataType(ptype)

        tdef['props'].append(prop)

        info = dict(tufo=name, ptype=ptype, uniq=uniq, defval=defval, **info)

        pdef = (prop, info)

        props[prop] = pdef

        return pdef

    def addTufoGlob(self, name, glob, ptype):
        '''
        Add a property glob to the tufo.
        '''
        # to validate the existance of ptype
        self.getDataType(ptype)
        self.model['globs'][glob] = ptype

    def getPropRepr(self, prop, valu):
        '''
        Return the humon readable representation for a property.

        Example:
            valu = tufo[1].get(prop)
            x = model.getPropRepr(prop, valu)

        '''
        ptype = self.getPropType(prop)
        typeobj = self.getDataType(ptype)
        return typeobj.repr(valu)

    def getPropNorm(self, prop, valu):
        '''
        Return a normalized system mode value for the given property.

        Example:

            valu = model.getPropNorm(prop,valu)

        '''
        ptype = self.getPropType(prop)
        typeobj = self.getDataType(ptype)
        return typeobj.norm(valu)

    def getPropParse(self, prop, text):
        '''
        Parse a humon input string into a system mode property value.

        Example:

            valu = model.getPropParse(prop, text)

        '''
        ptype = self.getPropType(prop)
        typeobj = self.getDataType(ptype)
        return typeobj.parse(text)

    def getPropDef(self, prop):
        '''
        Return a property definition tufo by property name.

        Example:

            pdef = model.getPropDef('foo:bar')

        '''
        props = self.model.get('props')
        pdef = props.get(prop)
        if pdef != None:
            return pdef

        # no match, lets check the globs...
        for glob,ptype in self.model.get('globs').items():
            if fnmatch.fnmatch(prop,glob):
                return (prop, dict(ptype=ptype, uniq=False, defval=None))

        raise NoSuchProp(prop)

    def getPropType(self, prop):
        '''
        Return the name of the data model type for the given property.

        Example:

            ptype = model.getPropType('foo:bar')

        '''
        pdef = self.getPropDef(prop)
        return pdef[1].get('ptype')

    def getPropDefval(self, prop):
        '''
        Retrieve the default value ( if specified ) for the prop.

        Example:

            defval = model.getPropDefval('foo:bar')

        '''
        pdef = self.getPropDef(prop)
        return pdef[1].get('defval')
