'''
A data model focused on material objects.
'''
from synapse.lib.module import CoreModule, modelrev

class MatMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('mat:item', {'subof': 'guid', 'doc': 'A GUID assigned to a material object'}),
                ('mat:spec', {'subof': 'guid', 'doc': 'A GUID assigned to a material specification'}),
                ('mat:specimage', {'subof': 'sepr', 'sep': '/', 'fields': 'item,mat:spec|file,file:bytes'}),
                ('mat:itemimage', {'subof': 'sepr', 'sep': '/', 'fields': 'item,mat:item|file,file:bytes'}),
                # TODO add base types for mass / volume
            ),

            'forms': (

                ('mat:item', {}, (

                    ('name', {'ptype': 'str:lwr',
                        'doc': 'The human readable name of the material item'}),

                    ('latlong', {'ptype': 'geo:latlong',
                        'doc': 'The last known lat/long location of the node'}),

                    # FIXME add baseline things like dimensions / mass / etc?
                )),

                ('mat:spec', {}, (
                    ('name', {'ptype': 'str:lwr', 'doc': 'The human readable name of the material spec'}),
                )),

                ('mat:itemimage', {}, (
                    ('item', {'ptype': 'mat:item', 'doc': 'The item contained within the image file'}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file containing an image of the item'}),
                )),

                ('mat:specimage', {}, (
                    ('spec', {'ptype': 'mat:spec', 'doc': 'The spec contained within the image file'}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file containing an image of the spec'}),
                )),
            ),
        }
        name = 'mat'
        return ((name, modl), )
