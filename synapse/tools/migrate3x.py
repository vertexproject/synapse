import os
import sys
import gzip
import shutil
import asyncio
import logging
import argparse
import collections

import synapse.exc as s_exc
import synapse.assets as s_assets
import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.cache as s_cache
import synapse.lib.const as s_const
import synapse.lib.layer as s_layer
import synapse.lib.nexus as s_nexus
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.modules as s_modules
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version
import synapse.lib.slabseqn as s_slabseqn
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.multislabseqn as s_multislabseqn

import synapse.tools.backup as s_backup

logger = logging.getLogger(__name__)

REQ_2X_CORE_VERS = '>=2.180.1,<3.0.0'

class Migrator(s_base.Base):
    '''
    Standalone tool for migrating Synapse from a source Cortex to a new destination 3.x.x Cortex.

    migrate() is the primary method which steps through sequential migration steps.
    The step is then carried out by a dedicated _migr* method which calls
    _src*, _trn*, _dest* methods as needed to read from the 0.1.x source, translate data to 2.x.x syntax,
    and finally write to the destination layer, respectively.

    Auth migration is handled through a standalone class MigrAuth.

    Source 0.1.x data is not modified, and migration can be run as a background operation.

    A migration dir is created to store stats, progress logs, checkpoints, and error logs specific to migration.
    '''
    async def __anit__(self, conf):
        await s_base.Base.__anit__(self)
        self.migrdir = 'migration'

        logger.debug(f'Migrator conf: {conf}')

        self.src = conf.get('src')
        self.dirn = conf.get('dest')
        self.nodelim = conf.get('nodelim')

        self.editbatchsize = conf.get('editbatchsize')
        if self.editbatchsize is None:
            self.editbatchsize = 100

        self.fromlast = conf.get('fromlast', False)
        self.savechkpnt = 100000  # save a restart marker every this many nodes

        self.srcslabopts = {
            'readonly': True,
            'map_async': True,
            'readahead': False,
            'lockmemory': False,
        }

        # data model
        self.model = None
        self.oldmodel = None

        # storage
        self.migrslab = None
        self.migrdb = None
        self.nexsroot = None
        self.cellslab = None

        self.formmigr = {
            # deleted forms
            'edge:has': (None, None),
            'edge:refs': (None, None),
            'edge:wentto': (None, None),
            'graph:cluster': (None, None),
            'graph:edge': (None, None),
            'graph:event': (None, None),
            'graph:node': (None, None),
            'graph:timeedge': (None, None),
            'ou:contract:type': (None, None),
            'syn:cron': (None, None),
            'syn:trigger': (None, None),

            # renamed forms
            'biz:dealstatus': (self.rename, {'name': 'biz:deal:status:taxonomy'}),
            'biz:dealtype': (self.rename, {'name': 'biz:deal:type:taxonomy'}),
            'biz:prodtype': (self.rename, {'name': 'biz:product:type:taxonomy'}),
            'geo:place:taxonomy': (self.rename, {'name': 'geo:place:type:taxonomy'}),
            'it:prod:hardwaretype': (self.rename, {'name': 'it:prod:hardware:type:taxonomy'}),
            'mat:type': (self.rename, {'name': 'mat:item:type:taxonomy'}),
            'media:news:taxonomy': (self.rename, {'name': 'media:news:type:taxonomy'}),
            'meta:event:taxonomy': (self.rename, {'name': 'meta:event:type:taxonomy'}),
            'meta:timeline:taxonomy': (self.rename, {'name': 'meta:timeline:type:taxonomy'}),
            'ou:orgtype': (self.rename, {'name': 'ou:org:type:taxonomy'}),
            'ou:conttype': (self.rename, {'name': 'ou:contract:type:taxonomy'}),
            'ou:camptype': (self.rename, {'name': 'ou:campaign:type:taxonomy'}),
            'ou:jobtype': (self.rename, {'name': 'ou:job:type:taxonomy'}),
            'ou:employment': (self.rename, {'name': 'ou:employment:type:taxonomy'}),
            'ou:technique:taxonomy': (self.rename, {'name': 'ou:technique:type:taxonomy'}),
            'risk:attacktype': (self.rename, {'name': 'risk:attack:type:taxonomy'}),
            'risk:alert:taxonomy': (self.rename, {'name': 'risk:alert:type:taxonomy'}),
            'risk:compromisetype': (self.rename, {'name': 'risk:compromise:type:taxonomy'}),
            'risk:tool:software:taxonomy': (self.rename, {'name': 'risk:tool:software:type:taxonomy'}),

            # auto populated migrations
            # 'inet:email:message:link': (self.renorm, {'name': 'inet:email:message:link'}),
            # 'inet:email:message:attachment': (self.renorm, {'name': 'inet:email:message:attachment'}),
        }

        self.propmigr = collections.defaultdict(dict)
        self.propmigr |= {
            # deleted props
            'inet:email:message:link': {
                'message': (None, None),
            },
            'inet:email:message:attachment': {
                'message': (None, None),
            },
            'ou:campaign': {
                'type': (None, None),
            },
            'ou:contract': {
                'types': (None, None),
            },

            # renamed props
            'ou:opening': {
                'jobtype': (self.rename, {'name': 'job:type'}),
                'employment': (self.rename, {'name': 'employment:type'}),
            },
            'ou:campaign': {
                'camptype': (self.rename, {'name': 'type'}),
            },
            'ou:org': {
                'orgtype': (self.rename, {'name': 'type'}),
            },
            'ps:workhist': {
                'jobtype': (self.rename, {'name': 'job:type'}),
                'employment': (self.rename, {'name': 'employment:type'}),
            }

            # auto populated renorm migrations
            # meta:source:type
            # meta:timeline:type
            # inet:email:attachment:name
        }

        # auto populated form creations
        self.typetoform = set()
        # biz:service:type:taxonomy
        # inet:service:login:method:taxonomy
        # it:software:image:type:taxonomy

        self.proptoform = set([
            ('meta:source:type', 'meta:source:type:taxonomy'),
        ])

    def rename(self, valu, opts):
        return valu

    def renorm(self, valu, opts):
        norm = opts['type'].norm(valu)
        return norm[0]

    async def _chkValid(self):
        '''
        Check if the cortex is in a valid state to be migrated.

        Returns:
            (bool): Whether migration can proceed
        '''
        logger.info(f'Checking that source Cortex is in valid state to be migrated.')
        vld = True

        vers = self.cellinfo.get('cell:version') or (-1, -1, -1)
        await self._migrlogAdd('chkvalid', 'vers', 'src:cortex', vers)

        try:
            s_version.reqVersion(vers, REQ_2X_CORE_VERS)
        except s_exc.BadVersion:
            logger.error(f'Source Cortex does not meet minimum version: req={REQ_2X_CORE_VERS} actual={vers}')
            vld = False

        # check cell.guid exists and save to validate no layers have same iden
        guidpath = os.path.join(self.dirn, 'cell.guid')
        coreiden = None
        if not os.path.exists(guidpath):
            logger.error(f'Unable to read cell guid at {guidpath}')
            vld = False
        else:
            with open(guidpath, 'r') as fd:
                coreiden = fd.read().strip()

        await self._migrlogAdd('chkvalid', 'iden', 'src:cortex', coreiden)

        # check layer info
        for lyriden, lyrinfo in self.layrdefs.items():

            mirror = lyrinfo.pop('mirror', None)
            if mirror:
                logger.warning(f'{lyriden} is a mirror layer which is no longer supported in 3.x')

            upstream = lyrinfo.pop('upstream', None)
            if upstream:
                logger.warning(f'{lyriden} has an upstream layer configured which is no longer supported in 3.x')

        logger.info(f'Completed check of source Cortex state: valid={vld}')

        return vld

    async def migrate(self):
        '''
        Execute the migration
        '''
        if self.dirn is None:
            raise Exception('Destination dirn must be specified for migration.')

        # setup destination directory (migrop handled in method)
        locallyrs = await self._migrDirn()

        # initialize storage for migration
        await self._initStors()

        # check if configuration is valid to start
        isvalid = await self._chkValid()
        if not isvalid:
            return

        # migrate all of the config data first so cortex is
        # in a valid state during node data migration
        await self._migrCell()
        await self._migrDatamodel()
        await self._migrExtmodel()

        self.newlayers = {}
        for iden, layrinfo in self.layrdefs.items():
            layr = await s_layer.Layer.anit(self, layrinfo)
            self.onfini(layr.fini)
            self.newlayers[iden] = layr

        # generate NIDs from form indexes
        for iden, layr in self.newlayers.items():
            logger.info(f'Generating NIDs for layer {iden}')
            await self._migrLayerBuids(iden, layr)

        # rebuild nexus log with NIDs and actual edits from layer nodeeditlogs
        await self._migrNexslog()

        # migrate layer data
        for iden, layr in self.newlayers.items():
            logger.info(f'Migrating data for layer {iden}')
            await self._migrLayer(layr)

        await self._migrViewTriggerQueues()

    async def _migrViewTriggerQueues(self):

        for iden in self.viewdefs.keys():
            path = os.path.join(self.dirn, 'views', iden, 'viewstate.lmdb')

            async with await s_lmdbslab.Slab.anit(path) as viewslab:
                trigqueue = viewslab.getSeqn('trigqueue')

                for offs, triginfo in trigqueue.iter(0):
                    buid = triginfo.pop('buid')

                    if (nid := self.getNidByBuid(buid)) is None:
                        if (newv := self.migrslab.get(buid, db=self.migrbuids)) is None:
                            view.trigqueue.pop(offs)
                            continue
                        (nid, buid, form, valu) = s_msgpack.un(newv)

                    triginfo['nid'] = nid
                    view.trigqueue.put(triginfo, indx=offs)

    async def _initStors(self, migr=True, cell=True):
        '''
        Initialize required non-layer destination slabs for migration.
        '''
        # slab for tracking migration data
        if migr:
            path = os.path.join(self.dirn, self.migrdir, 'migr.lmdb')
            if self.migrslab is None:
                self.migrslab = await s_lmdbslab.Slab.anit(path, map_async=True, readonly=False)
            self.migrdb = self.migrslab.initdb('migr')
            self.unkbuids = self.migrslab.initdb('unkbuids')
            self.migrbuids = self.migrslab.initdb('migrbuids')
            self.onfini(self.migrslab.fini)

        # open cell
        if cell:
            path = os.path.join(self.dirn, 'slabs', 'cell.lmdb')
            if self.cellslab is None:
                self.cellslab = await s_lmdbslab.Slab.anit(path)
            self.onfini(self.cellslab.fini)

        self.cortexdata = self.cellslab.getSafeKeyVal('cortex')
        self.cellinfo = self.cellslab.getSafeKeyVal('cell:info')
        self.viewdefs = self.cortexdata.getSubKeyVal('view:info:')
        self.layrdefs = self.cortexdata.getSubKeyVal('layer:info:')

        v3path = os.path.join(self.dirn, 'slabs', 'layersv3.lmdb')
        self.v3stor = await s_lmdbslab.Slab.anit(v3path)
        self.onfini(self.v3stor.fini)

        self.indxabrv = self.v3stor.getNameAbrv('indxabrv')
        self.nid2ndef = self.v3stor.initdb('nid2ndef')
        self.nid2buid = self.v3stor.initdb('nid2buid')
        self.buid2nid = self.v3stor.initdb('buid2nid')

        self.nextnid = 0
        byts = self.v3stor.lastkey(db=self.nid2buid)
        if byts is not None:
            self.nextnid = s_common.int64un(byts) + 1

        logger.debug('Finished storage initialization')
        return

    async def _migrDirn(self):
        '''
        Setup the destination cortex dirn.  If dest already exists it will not be overwritten.
        Copies all data *except* the layers and nexuslog

        Returns:
            (list): Idens of discovered local physical layers
        '''
        dest = self.dirn
        src = self.src
        logger.info(f'Starting cortex dirn migration: {src} to {dest}')

        lyrdir = os.path.join(src, 'layers')
        locallyrs = []
        for item in os.listdir(lyrdir):
            if os.path.isdir(os.path.join(lyrdir, item)):
                locallyrs.append(item)

        logger.info(f'Found {len(locallyrs)} src physical layers.')
        logger.debug(f'Source layers: {locallyrs}')

        if not os.path.exists(dest):
            s_common.gendir(dest)

        for sdir in os.listdir(src):
            spath = os.path.join(src, sdir)
            dpath = os.path.join(dest, sdir)

            isdir = os.path.isdir(spath)
            isfile = os.path.isfile(spath)
            exists = os.path.exists(dpath)

            if sdir == 'layers':
                # make locallyr dirs if they don't exist but never overwrite
                for lyr in locallyrs:
                    lpath = os.path.join(dpath, lyr)
                    if not os.path.exists(lpath):
                        os.makedirs(lpath)
                    else:
                        logger.info(f'Layer dir exists, leaving as-is: {lyr}')

            elif isfile:
                if exists:
                    os.remove(dpath)
                shutil.copy(spath, dpath)

            elif spath.endswith('axon'):
                if exists:
                    shutil.rmtree(dpath)
                s_backup.backup(spath, dpath)

            elif spath.endswith('slabs'):
                # delete the non-nexus items from the destination if they exist
                if exists:
                    for _, dnames, fnames in os.walk(dpath, topdown=True):
                        for fname in fnames:
                            if 'nexus' not in fname:
                                os.remove(os.path.join(dpath, fname))
                        for dname in list(dnames):
                            if 'nexus' not in dname:
                                shutil.rmtree(os.path.join(dpath, dname))
                            dnames.remove(dname)

                s_backup.backup(spath, dpath, skipdirs=['**/nexuslog'])  # so we compress the slabs
            elif spath.endswith('views'):
                s_backup.backup(spath, dpath)

            elif isdir:
                if exists:
                    shutil.rmtree(dpath)
                shutil.copytree(spath, dpath, ignore=shutil.ignore_patterns('sock'))

        logger.info(f'Completed dirn copy from {src} to {dest}')
        return locallyrs

    async def _migrCell(self):
        '''
        Migrate top-level cell information including the YAML file if it exists to
        remove deprecated confdefs.
        '''
        # Set cortex:version to latest
        self.cellinfo.set('cortex:version', s_version.version)

        # confdefs
        validconfs = s_cortex.Cortex.confdefs
        yamlpath = os.path.join(self.dirn, 'cell.yaml')
        remconfs = []
        dedicated = False
        if os.path.exists(yamlpath):
            conf = s_common.yamlload(self.dirn, 'cell.yaml')
            remconfs = [k for k in conf.keys() if k not in validconfs]
            conf = {k: v for k, v in conf.items() if k not in remconfs}
            s_common.yamlsave(conf, self.dirn, 'cell.yaml')

        self.cellslab.dropdb('hive')

        logger.info(f'Completed cell migration, removed deprecated confdefs: {remconfs}')
        await self._migrlogAdd('cell', 'prog', 'none', s_common.now())

    async def _migrNexslog(self):

        editlogs = {}

        for iden, layrinfo in self.layrdefs.items():
            path = os.path.join(self.src, 'layers', iden, 'nodeedits.lmdb')
            nodeeditslab = await s_lmdbslab.Slab.anit(path)
            editlogs[iden] = s_slabseqn.SlabSeqn(nodeeditslab, 'nodeedits')

        spath = os.path.join(self.src, 'slabs', 'nexuslog')
        dpath = os.path.join(self.dirn, 'slabs', 'nexuslog')

        async with await s_multislabseqn.MultiSlabSeqn.anit(spath) as srclog, \
                   await s_multislabseqn.MultiSlabSeqn.anit(dpath) as dstlog:

            buidmap = {}

            async for offs, item in s_coro.pause(srclog.iter(0)):
                if item[1] != 'edits':
                    await dstlog.add(item + (None,), indx=offs)
                    continue

                nexsiden, event, args, kwargs, _ = item

                # skip nonexistent layers
                if (editlog := editlogs.get(nexsiden)) is None:
                    continue

                if (realedits := editlog.get(offs)) is None:
                    continue

                nodeedits, meta = realedits
                newnodeedits = []

                etime = None
                if meta is not None:
                    etime = meta.get('time')

                if etime is None:
                    if args[1] is not None:
                        etime = args[1].get('time')

                    if etime is None:  # pragma: no cover
                        etime = s_common.now()

                for buid, form, edits in nodeedits:
                    if (nid := self.getNidByBuid(buid)) is None:
                        if form in self.formmigr:
                            if (newv := self.migrslab.get(buid, db=self.migrbuids)) is None:
                                # this is a buid for a migrated form which has no value
                                # in any layers so we cannot compute the new buid
                                continue

                            nid = s_msgpack.un(newv)[0]
                        else:
                            nid = self._genBuidNid(buid)

                    newedits = []

                    for item in edits:
                        if len(item) == 3:
                            (etyp, edit, _) = item
                        else:
                            (etyp, edit) = item

                        if etyp in (s_layer.EDIT_EDGE_ADD, s_layer.EDIT_EDGE_DEL):
                            (verb, n2iden) = edit
                            n2buid = s_common.uhex(n2iden)
                            if (n2nid := self.getNidByBuid(n2buid)) is None:
                                if (newv := self.migrslab.get(n2buid, db=self.migrbuids)) is not None:
                                    n2nid = s_msgpack.un(newv)[0]

                            if n2nid is None:
                                # skip edges to unknown buids
                                continue

                            newedits.append((etyp, (verb, n2nid)))
                        else:
                            newedits.append((etyp, edit))

                    if newedits:
                        newnodeedits.append((nid, form, newedits))

                if newnodeedits:
                    await dstlog.add((nexsiden, event, (newnodeedits, meta), kwargs, meta, etime), indx=offs)
                    self.newlayers[nexsiden].nodeeditlog.add(None, indx=offs)

                buidmap.clear()

        for slabseqn in editlogs.values():
            await slabseqn.slab.fini()

    def _get2xModel(self):
        fp = s_assets.getAssetPath('model2x.yaml.gz')
        with s_common.genfile(fp) as fd:
            bytz = fd.read()
            large_bytz = gzip.decompress(bytz)
            ref_modl = s_common.yamlloads(large_bytz)
        return ref_modl['model']

    async def _migrDatamodel(self):
        '''
        Load datamodel and generate any automatic migrations from the 2.x model.
        '''
        self.model = s_datamodel.Model()
        self.oldmodel = self._get2xModel()

        # load core modules
        # TODO: remove once coremods are gone
        mods = list(s_modules.coremods)
        mdefs = []
        for mod in mods:
            modu = s_dyndeps.tryDynLocal(mod)
            mdefs.extend(modu.getModelDefs(self))

        self.model.addDataModels(mdefs)

        # generate automatic form migrations where possible and verify all forms exist
        # or have a migration defined

        nomigr = []
        for name, fdef in self.oldmodel['forms'].items():

            if name in self.formmigr:
                continue

            if (form := self.model.form(name)) is None:
                nomigr.append(f'form={name}')
                continue

            oldt = self.oldmodel['types'].get(name)
            oldopts = s_common.flatten(oldt['opts'])
            newopts = s_common.flatten(form.type.opts)
            if oldopts != newopts or oldt['stortype'] != form.type.stortype:
                opts = {'name': name, 'type': form.type}
                self.formmigr[name] = (self.renorm, opts)

        # generate automatic prop migrations where possible and verify all props exist
        # or have a migration defined

        for formname, fdef in self.oldmodel['forms'].items():

            if (migr := self.formmigr.get(formname)) is not None:
                if (migropts := migr[1]) is None:
                    continue
                formname = migropts['name']

            propmigr = self.propmigr.get(formname)

            for propname, pdef in fdef['props'].items():

                if propname[0] == '.':
                    continue

                if propmigr is not None and propname in propmigr:
                    continue

                propfull = f'{formname}:{propname}'
                if (prop := self.model.prop(propfull)) is None:
                    nomigr.append(f'prop={propfull}')
                    continue

                oldtname, oldtopts = pdef['type']
                if (tmigr := self.formmigr.get(oldtname)) is not None:
                    oldtname = tmigr[1]['name']

                newtname, newtopts = prop.typedef
                oldtopts = s_common.flatten(oldtopts)
                newtopts = s_common.flatten(newtopts)

                if newtname != oldtname or oldtopts != newtopts:
                    opts = {'name': propname, 'type': prop.type}
                    self.propmigr[formname][propname] = (self.renorm, opts)

        if nomigr:
            raise Exception(f'Missing model elements with no defined migration: {", ".join(nomigr)}')

        for name in self.model.forms.keys():
            if name in self.oldmodel['types'] and name not in self.oldmodel['forms']:
                self.typetoform.add(name)

        logger.info('Completed datamodel migration')
        await self._migrlogAdd('dmodel', 'prog', 'none', s_common.now())

    async def _migrExtmodel(self):

        self.extedges = self.cortexdata.getSubKeyVal('model:edges:')
        self.extforms = self.cortexdata.getSubKeyVal('model:forms:')
        self.extprops = self.cortexdata.getSubKeyVal('model:props:')
        self.extunivs = self.cortexdata.getSubKeyVal('model:univs:')
        self.exttagprops = self.cortexdata.getSubKeyVal('model:tagprops:')

        self.remforms = set()
        self.remprops = set()
        self.remunivs = set()
        self.remtagprops = set()

        for formname, basetype, typeopts, typeinfo in self.extforms.values():
            if bool(typeinfo.get('deprecated', False)):
                self.remforms.add(formname)
                mesg = f'The extended property {formname} is using a deprecated type {basetype} and will be removed.'
                logger.warning(mesg)
                continue

            try:
                self.model.addType(formname, basetype, typeopts, typeinfo)
                form = self.model.addForm(formname, {}, ())
            except Exception as e:
                logger.warning(f'Extended form ({formname}) error: {e}')

        for formname in self.remforms:
            self.extforms.pop(formname)

        for form, prop, tdef, info in self.extprops.values():
            if bool(info.get('deprecated', False)):
                self.remprops.add(formname)
                mesg = f'The extended property {formname} is using a deprecated type {basetype} and will be removed.'
                logger.warning(mesg)
                continue

            try:
                self.model.addFormProp(form, prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:  # pragma: no cover
                logger.warning(f'ext prop ({form}:{prop}) error: {e}')

        for prop, tdef, info in self.extunivs.values():
            try:
                self.model.addUnivProp(prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:  # pragma: no cover
                logger.warning(f'ext univ ({prop}) error: {e}')

        for prop, tdef, info in self.exttagprops.values():
            try:
                self.model.addTagProp(prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:  # pragma: no cover
                logger.warning(f'ext tag prop ({prop}) error: {e}')

        logger.info('Completed datamodel migration')
        await self._migrlogAdd('dmodel', 'prog', 'none', s_common.now())

    def _genIndxNid(self, buid, ndef):
        if (nid := self.v3stor.get(buid, db=self.buid2nid)) is not None:
            return nid

        nid = s_common.int64en(self.nextnid)
        self.nextnid += 1

        self.v3stor.put(nid, buid, db=self.nid2buid)
        self.v3stor.put(nid, s_msgpack.en(ndef), db=self.nid2ndef)
        self.v3stor.put(buid, nid, db=self.buid2nid)

        return nid

    def _genBuidNid(self, buid):
        '''
        Generate an NID for a buid with no ndef which may be later populated when the
        node is added.
        '''
        nid = s_common.int64en(self.nextnid)
        self.nextnid += 1

        self.v3stor.put(nid, buid, db=self.nid2buid)
        self.v3stor.put(buid, nid, db=self.buid2nid)

        return nid

#    def _genNdefNid(self, buid, ndef):
#        if (nid := self.migrslab.pop(buid, db=self.unkbuids)) is None:
#            nid = s_common.int64en(self.nextnid)
#            self.nextnid += 1
#            self.v3stor.put(buid, nid, db=self.buid2nid)
#
#        self.v3stor.put(nid, buid, db=self.nid2buid)
#        self.v3stor.put(nid, s_msgpack.en(ndef), db=self.nid2ndef)
#        return nid
#
#    def _genBuidNid(self, buid):
#        nid = s_common.int64en(self.nextnid)
#        self.nextnid += 1
#        self.migrslab.put(buid, nid, db=self.unkbuids)
#        return nid

    def getNidByBuid(self, buid):
        return self.v3stor.get(buid, db=self.buid2nid)

    def hasNidNdef(self, nid):
        return self.v3stor.has(nid, db=self.nid2ndef)

    def getNidNdef(self, nid):
        if (byts := self.v3stor.get(nid, db=self.nid2ndef)) is not None:
            return s_msgpack.un(byts)

    async def _migrLayerBuids(self, iden, newlayr):

        path = os.path.join(self.src, 'layers', iden, 'layer_v2.lmdb')

        async with await s_lmdbslab.Slab.anit(path) as layrslab:
            byprop = layrslab.initdb('byprop', dupsort=True)
            bybuidv3 = layrslab.initdb('bybuidv3')
            name2abrv = layrslab.initdb('propabrv:byts2abrv', dupsort=True, dupfixed=True)

            for byts, abrv in layrslab.scanByFull(db=name2abrv):
                await asyncio.sleep(0)

                form, prop = s_msgpack.un(byts)
                if prop is not None:
                    continue

                newform = form
                if (migr := self.formmigr.get(form)) is not None:
                    (migrfunc, migropts) = migr
                    if migrfunc is None:
                        continue

                    newform = migropts['name']

                if form[0] != '_':
                    tdef = self.oldmodel['types'].get(form)
                    if tdef is None:
                        continue

                    oldt = tdef['stortype']
                    stor = newlayr.stortypes[oldt]

                    tobj = self.model.type(newform)
                    if tobj is None or (tobj.stortype != oldt and migr is None):
                        print(f'Missing migration for {form}, nodes will not be migrated!')
                        continue

                else:
                    fdef = self.extforms.get(form)
                    if fdef is not None:
                        ftyp = self.model.type(fdef[1])
                        if ftyp is None:
                            print(f'Extended model form {form} is using deprecated type and will not be migrated')
                            continue

                        if ftyp.stortype > len(newlayr.stortypes) + 1:
                            print(f'Form {form} is using an invalid stortype={ftyp.stortype} and will not be migrated')
                            continue

                        stor = newlayr.stortypes[ftyp.stortype]

                abrvlen = len(abrv)

                async for lkey, buid in s_coro.pause(layrslab.scanByPref(abrv, db=byprop)):

                    if self.getNidByBuid(buid) is not None:
                        continue

                    indx = lkey[abrvlen:]
                    try:
                        valu = stor.decodeIndx(indx)
                    except:
                        print(form, lkey)
                        valu = s_common.novalu
                        if (byts := layrslab.get(buid, db=bybuidv3)) is not None:
                            print(s_msgpack.un(byts))

                    if valu is s_common.novalu:

                        if (byts := layrslab.get(buid, db=bybuidv3)) is None:
                            print(f'Invalid prop index value {lkey}:{buid}')
                            continue

                        sode = s_msgpack.un(byts)
                        if (valu := sode.get('valu')) is not None:
                            valu = valu[0]

                    if migr is not None:
                        try:
                            valu = migrfunc(valu, migropts)
                        except:
                            print(f'Failed to migrate value for {form}={valu}')
                            continue

                        newbuid = s_common.buid((newform, valu))
                        nid = self._genIndxNid(newbuid, (newform, valu))

                        if newbuid != buid:
                            migv = s_msgpack.en((nid, newbuid, newform, valu))
                            self.migrslab.put(buid, migv, db=self.migrbuids)
                    else:
                        self._genIndxNid(buid, (newform, valu))

    @s_cache.memoizemethod()
    def setIndxAbrv(self, indx, *args):
        return self.indxabrv.setBytsToAbrv(indx + s_msgpack.en(args))

    @s_cache.memoizemethod()
    def getBuidByNid(self, nid):
        return True

    def checkFreeSpace(self):
        pass

    async def _migrLayer(self, layr):
        async for nodeedits in self.translateLayerNodeEdits(layr.iden):
            await layr._storNodeEdits([nodeedits], None, None)

    async def translateLayerNodeEdits(self, iden):
        '''
        Scan the full layer and yield artificial sets of nodeedits in 3.x format.
        '''
        path = os.path.join(self.src, 'layers', iden, 'layer_v2.lmdb')
        nodedatapath = os.path.join(self.src, 'layers', iden, 'nodedata.lmdb')
        layrkey = s_common.uhex(iden)

        async with await s_lmdbslab.Slab.anit(path) as layrslab, \
                   await s_lmdbslab.Slab.anit(nodedatapath) as dataslab:

            byprop = layrslab.initdb('byprop', dupsort=True)
            edgesn1 = layrslab.initdb('edgesn1', dupsort=True)
            bybuidv3 = layrslab.initdb('bybuidv3')
            nodedata = dataslab.initdb('nodedata')
            propabrv = layrslab.getNameAbrv('propabrv')

            for buid, byts in layrslab.scanByFull(bybuidv3):

                sode = s_msgpack.un(byts)
                form = sode.get('form')
                if form is None:
                    logger.warning(f'NODE HAS NO FORM: {buid}')
                    continue

                valt = sode.get('valu')
                if valt is not None:
                    valu = valt[0]

                nid = None

                if (migr := self.formmigr.get(form)) is not None:
                    if migr[0] is None:
                        continue

                    if (newv := self.migrslab.get(buid, db=self.migrbuids)) is not None:
                        (nid, buid, form, valu) = s_msgpack.un(newv)
                    else:
                        # this is a buid for a migrated form which has no value
                        # in any layers so we cannot compute the new buid
                        print('NO MIGRATION DEFINED FOR', form, sode)
                        self.migrslab.put(buid + layrkey, byts, db=self.unkbuids)
                        continue

                elif (nid := self.getNidByBuid(buid)) is None:
                    nid = self._genBuidNid(buid)

                edits = []
                logedits = []

                if valt is not None:
                    ftyp = self.model.type(form)
                    if ftyp is None:
                        print(f'Unknown form {form} in layer {iden}')
                        continue

                    stortype = ftyp.stortype
                    if stortype == 10 and isinstance(valu, tuple):
                        print(sode)
                    edits.append((s_layer.EDIT_NODE_ADD, (valu, stortype)))

                propmigr = self.propmigr.get(form)
                for prop, (valu, stortype) in sode.get('props', {}).items():

                    if propmigr and (pmig := propmigr.get(prop)) is not None:
                        (pmigfunc, pmigopts) = pmig
                        if pmigfunc is None:
                            continue

                        try:
                            valu = pmigfunc(valu, pmigopts)
                        except:
                            print(f'Failed to migrate value for {form}:{prop}={valu}')
                            continue

                        if (newtype := pmigopts.get('type')) is not None:
                            stortype = newtype.stortype

                    elif stortype == s_layer.STOR_TYPE_NDEF:
                        (nform, nvalu) = valu
                        if (migr := self.formmigr.get(nform)) is not None:
                            (migrfunc, migropts) = migr
                            try:
                                valu = (migropts['name'], migrfunc(nvalu, migropts))
                            except:
                                print(f'Failed to migrate value for {form}:{prop}={valu}')
                                continue

                    edits.append((s_layer.EDIT_PROP_SET, (prop, valu, None, stortype)))

                for tag, tagv in sode.get('tags', {}).items():
                    edits.append((s_layer.EDIT_TAG_SET, (tag, tagv, None)))

                for tag, propdict in sode.get('tagprops', {}).items():
                    for prop, (valu, stortype) in propdict.items():
                        edits.append((s_layer.EDIT_TAGPROP_SET, (tag, prop, valu, None, stortype)))

                for lkey, byts in dataslab.scanByPref(buid, db=nodedata):
                    valu = s_msgpack.un(byts)
                    prop = s_msgpack.un(propabrv.abrvToByts(lkey[32:]))

                    edits.append((s_layer.EDIT_NODEDATA_SET, (prop[0], valu, None)))

                for lkey, n2buid in layrslab.scanByPref(buid, db=edgesn1):
                    verb = lkey[32:].decode()

                    if (n2nid := self.getNidByBuid(n2buid)) is None:
                        if (newv := self.migrslab.get(n2buid, db=self.migrbuids)) is None:
                            continue
                        (n2nid, _, n2form, _) = s_msgpack.un(newv)
                    else:
                        n2form = self.getNidNdef(n2nid)[0]

                    if not self.model.edgeIsValid(form, verb, n2form):
                        if verb[0] != '_':
                            verb = '_' + verb

                        edge = ('*', verb, '*')
                        edgeinfo = {'doc': 'Automatically added during 3.0.0 migration.'}
                        self.model.addEdge(edge, edgeinfo)
                        self.extedges.set(s_common.guid(edge), (edge, edgeinfo))

                    edits.append((s_layer.EDIT_EDGE_ADD, (verb, n2nid)))


#                if newedits:
#                    newnodeedits.append((nid, form, newedits))

#                if newnodeedits:
#                    await dstlog.add((nexsiden, event, (newnodeedits, meta), kwargs, meta, etime), indx=offs)

                yield (nid, form, edits)

    async def _migrlogAdd(self, migrop, logtyp, key, val):
        '''
        Add an error record to the migration data
        '''
        try:
            if isinstance(key, bytes):
                bkey = key
            else:
                bkey = key.encode()

            lkey = migrop.encode() + b'\x00' + logtyp.encode() + b'\x00' + bkey
            lval = s_msgpack.en(val)

            self.migrslab.put(lkey, lval, overwrite=True, db=self.migrdb)

        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception:  # pragma: no cover
            logger.exception(f'Unable to store migration log: {migrop}; {logtyp}; {key}; {val}')

async def main(argv, outp=s_output.stdout):
    desc = 'Tool for migrating Synapse Cortex storage from 2.x.x to 3.x.x'
    pars = argparse.ArgumentParser(prog='synapse.tools.migrate3x', description=desc)

    pars.add_argument('--src', required=True, type=str, help='Source cortex dirn to migrate from.')
    pars.add_argument('--dest', required=False, type=str, help='Destination cortex dirn to migrate to.')
    pars.add_argument('--nodelim', required=False, type=int,
                      help="Stop after migrating nodelim nodes")
    pars.add_argument('--edit-batchsize', required=False, type=int, default=100,
                      help='Batch size for writing new nodeedits')
    pars.add_argument('--from-last', required=False, action='store_true',
                      help='Start migration from the last node migrated (by count).')
    pars.add_argument('--log-level', required=False, default='info', choices=s_const.LOG_LEVEL_CHOICES,
                      help='Specify the log level', type=str.upper)
    pars.add_argument('--dump-errors', required=False, action='store_true',
                      help='Dump migration errors to an mpk file.')

    opts = pars.parse_args(argv)

    s_common.setlogging(logger, opts.log_level)

    dumperrors = opts.dump_errors
    dest = opts.dest

    conf = {
        'src': opts.src,
        'dest': dest,
        'nodelim': opts.nodelim,
        'editbatchsize': opts.edit_batchsize,
        'fromlast': opts.from_last,
    }

    migr = await Migrator.anit(conf=conf)

    try:
        if dumperrors:
            dumpf = await migr.dumpErrors()
            outp.printf(f'Dump file located at {dumpf}')
        else:
            await migr.migrate()

        return migr

    finally:
        await migr.fini()

if __name__ == '__main__':  # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
