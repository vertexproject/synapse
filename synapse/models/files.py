def getDataModel():
    return {

        'prefix':'file',
        'version':201701061638,

        'types':(
            ('file:guid',{'subof':'guid','doc':'A unique file identifier'}),
            ('file:sub',{'subof':'sepr','sep':'/','fields':'parent,file:guid|child,file:guid'}),
            ('file:base',{'subof':'str','lower':1,'doc':'A file basename such as foo.exe'}),
        ),

        'forms':(

            ('file:bytes', {'ptype':'file:guid'},(
                ('size',{'ptype':'int'}),
                ('md5',{'ptype':'hash:md5'}),
                ('sha1',{'ptype':'hash:sha1'}),
                ('sha256',{'ptype':'hash:sha256'}),
                ('sha512',{'ptype':'hash:sha512'}),
                ('name',{'ptype':'file:base','doc':'For display purposes only'}),
                ('mime',{'ptype':'str','defval':'??','doc':'Mime type for the file bytes'}),

                # FIXME could another model define props for this form?
                ('mime:x509:cn',{'ptype':'str','doc':'X509 Subject Common Name'}),

                ('mime:pe:size',{'ptype':'int','doc':'Size of the executable according to headers'}),
                ('mime:pe:imphash',{'ptype':'guid','doc':'PE Import hash as calculated by vivisect'}),
                ('mime:pe:compiled',{'ptype':'time','doc':'Compile time from the PE header'}),

                # once we have dark prop based text token indexes...
                #('mime:pe:imports',{'ptype':'time','doc':'Compile time from the PE header'}),

                ('mime:*',{'glob':1,'doc':'Namespace for high-value mime details'})
            )),

            ('file:subfile', {'ptype':'file:sub'},(
                ('parent',{'ptype':'file:guid'}),
                ('child',{'ptype':'file:guid'}),
                ('name',{'ptype':'file:base'}),
                #TODO others....
            )),

        ),
    }

def addCoreOns(core):

    def seedFileMd5(prop,valu,**props):
        props['md5'] = valu
        return core.formTufoByProp('file:bytes',valu,**props)

    def seedFileGoodHash(prop,valu,**props):
        '''
        Hashes that we consider "cardinal enough" to pivot.
        '''
        name = prop.rsplit(':',1)[-1]
        props[name] = valu

        # FIXME could we update additional hashes here and
        # maybe (gasp) update the primary property if we
        # finally have enough, then update all other known
        # records that reference this file guid?

        tufo = core.getTufoByProp(prop,valu)
        if tufo != None:
            # add more hashes if we know them...
            tufo = core.setTufoProps(tufo,**props)
            return tufo

        iden = core.getTypeCast('make:guid',valu)
        tufo = core.formTufoByProp('file:bytes',iden,**props)
        # update with any additional hashes we have...
        tufo = core.setTufoProps(tufo,**props)
        return tufo

    core.addSeedCtor('file:bytes:md5',seedFileMd5)

    # sha1 / sha256 / sha512 are good enough for now
    core.addSeedCtor('file:bytes:sha1',seedFileGoodHash)
    core.addSeedCtor('file:bytes:sha256',seedFileGoodHash)
    core.addSeedCtor('file:bytes:sha512',seedFileGoodHash)

#def revDataModel(core):

