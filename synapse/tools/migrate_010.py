import time
import logging
import pathlib
import argparse
import tempfile
from binascii import unhexlify, hexlify

import lmdb  # type: ignore

import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.lib.modules as s_modules
import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const
import synapse.lib.types as s_types
import synapse.lib.msgpack as s_msgpack
import synapse.models.inet as s_inet

logger = logging.getLogger(__name__)

# Topologically sorted comp and sepr types that are form types that have other comp types as elements.  The beginning
# of the list has more dependencies than the end.
_comp_and_sepr_forms = [
    'tel:mob:imsiphone', 'tel:mob:imid', 'syn:tagform', 'syn:fifo', 'syn:auth:userrole', 'seen', 'rsa:key', 'recref',
    'ps:image', 'ou:user', 'ou:suborg', 'ou:member', 'ou:meet:attendee', 'ou:hasalias', 'ou:conference:attendee',
    'mat:specimage', 'mat:itemimage', 'it:hostsoft', 'it:dev:regval', 'it:av:filehit', 'it:av:sig',
    'inet:wifi:ap', 'inet:whois:regmail', 'inet:whois:recns', 'inet:whois:contact', 'inet:whois:rec',
    'inet:web:post', 'inet:web:mesg', 'inet:web:memb', 'inet:web:group', 'inet:web:follows', 'inet:web:file',
    'inet:web:acct', 'inet:urlredir', 'inet:urlfile', 'inet:ssl:tcp4cert', 'inet:servfile', 'inet:http:resphead',
    'inet:http:reqparam', 'inet:http:reqhead', 'inet:http:param', 'inet:http:header', 'inet:dns:txt',
    'inet:dns:soa', 'inet:dns:rev6', 'inet:dns:rev', 'inet:dns:req', 'inet:dns:ns', 'inet:dns:mx',
    'inet:dns:cname', 'inet:dns:aaaa', 'inet:dns:a', 'inet:asnet4', 'geo:nloc', 'file:subfile']

_subs_to_save = [
    'ou:org:name:en',
    'ps:person:name:en',
    'ps:person:name:sur',
    'ps:person:name:given',
    'ps:person:name:middle',
    'ps:persona:name:en',
    'ps:persona:name:sur',
    'ps:persona:name:given',
    'ps:persona:name:middle']

def _enc_iden(iden):
    return unhexlify(iden)

class ConsistencyError(Exception):
    pass

def _special_sort_key(t):
    '''
    For processing secondary properties in order, always processing tcp after udp, and v4 after v6
    '''
    k, v = t
    k = k.replace('tcp', chr(127) + 'tcp', 1)
    return (k.replace('v4', chr(127) + 'v4', 1), v)

class Migrator:
    '''
    Sucks all rows out of a < .0.1.0 cortex, into a temporary LMDB database, migrates the schema, then dumps to new
    file suitable for ingesting into a >= .0.1.0 cortex.
    '''
    def __init__(self, core, outfh, tmpdir=None, stage1_fn=None, rejects_fh=None, good_forms=None):
        '''
        Create a migrator.

        Args:
            core (synapse.cores.common.Cortex): 0.0.x *local* cortex to export from

            outfh (IO['bin']): file handle opened for binary to push messagepacked data into

            tmpdir (Optional[str]):  location to write stage 1 LMDB database.  Please note that /tmp on Linux might
                *not* a good location since it is usually mounted tmpfs with not enough space.  This parameter is not
                used if stage1_fn parameter is specified.

            stage1_fn (Optional[str]):   Skips stage1 altogether and starts with existing stage 1 DB.

            rejects_fh (Optional[IO['bin']]):  file handle in which to place the nodes that couldn't be migrated.  If
                not provided, no rejects file will be used.

            good_forms (Optional[List[str]]):  whitelist of form names to accept.  If not None, all other forms will be
                skipped
        '''

        self.core = core
        self.dbenv = None
        self.skip_stage1 = bool(stage1_fn)
        assert tmpdir or stage1_fn
        self.next_val = 0
        self.rejects_fh = rejects_fh
        self.good_forms = set(good_forms) if good_forms is not None else None

        if stage1_fn is None:
            with tempfile.NamedTemporaryFile(prefix='stage1_', suffix='.lmdb', delete=True, dir=str(tmpdir)) as fh:
                stage1_fn = fh.name
            logger.info('Creating stage 1 file at %s.  Delete when migration deemed successful.', stage1_fn)

        map_size = s_lmdb.DEFAULT_MAP_SIZE
        self.dbenv = lmdb.Environment(stage1_fn,
                                      map_size=map_size,
                                      subdir=False,
                                      metasync=False,
                                      writemap=True,
                                      max_readers=1,
                                      max_dbs=4,
                                      sync=False,
                                      lock=False)
        self.iden_tbl = self.dbenv.open_db(key=b'idens', dupsort=True)  # iden -> row
        self.form_tbl = self.dbenv.open_db(key=b'forms', dupsort=True)  # formname -> iden
        self.comp_tbl = self.dbenv.open_db(key=b'comp')  # guid -> comp tuple
        self.valu_tbl = self.dbenv.open_db(key=b'vals', integerkey=True)
        self.outfh = outfh
        self._precalc_types()
        self.first_forms = ['file:bytes'] + [f for f in reversed(_comp_and_sepr_forms) if self.is_comp(f)]

    def _get_comp_fields(self, formname):
        '''
        Returns the fields for a comp type
        '''
        t = self.core.getPropType(formname)
        return [x[0] for x in t.fields]

    def _get_sepr_fields(self, formname):
        t = self.core.getPropType(formname)
        return [x[0] for x in t._get_fields()]

    def _precalc_types(self):
        '''
        Precalculate which types are sepr and which are comps, and which are subs of comps
        '''
        seprs = []
        seprfields = []
        compfields = []
        comps = []
        subs = []
        filebytes = []
        xrefs = []
        forms = self.core.getTufoForms()
        for formname in forms:
            t = self.core.getPropType(formname)
            parents = self.core.getTypeOfs(formname)
            if 'sepr' in parents or isinstance(t, s_types.SeprType):
                seprs.append(formname)
                seprfields.extend(('%s:%s' % (formname, field) for field in self._get_sepr_fields(formname)))
            if 'comp' in parents or isinstance(t, s_types.CompType):
                comps.append(formname)
                compfields.extend(('%s:%s' % (formname, field) for field in self._get_comp_fields(formname)))
            if 'file:bytes' in parents:
                filebytes.append(formname)
            if 'xref' in parents:
                xrefs.append(formname)
            subpropnameprops = self.core.getSubProps(formname)
            subpropnames = [x[0] for x in subpropnameprops]
            for subpropname, subpropprops in subpropnameprops:
                parents = self.core.getTypeOfs(subpropprops['ptype'])
                if 'sepr' in parents:
                    seprs.append(subpropname)
                if 'comp' in parents:
                    comps.append(subpropname)
                if ('comp' in parents) or ('sepr' in parents) or subpropprops['ptype'] in forms:
                    subs.extend(x for x in subpropnames if x.startswith(subpropname + ':') and ':seen:' not in x)

        self.filebytes = set(filebytes)
        self.seprs = set(seprs)
        self.comps = set(comps)
        self.subs = set(subs) - set(_subs_to_save)
        self.xrefs = set(xrefs)
        self.seprfields = set(seprfields)
        self.compfields = set(compfields)

    def migrate(self):
        '''
        Convenience function to do both stages
        '''
        if not self.skip_stage1:
            self.do_stage1()
        self.do_stage2a()
        self.do_stage2b()

    def _write_props(self, txn, rows):
        '''
        Emit propbags to the migration DB
        '''
        MAX_VAL_LEN = 511

        idens = []
        bigvals = []
        for i, p, v, _ in rows:
            enci = _enc_iden(i)
            val = s_msgpack.en((p, v))
            if len(val) > MAX_VAL_LEN:
                next_val_enc = self.next_val.to_bytes(8, 'big')
                bigvals.append((next_val_enc, val))
                val = next_val_enc
                self.next_val += 1
            idens.append((enci, val))

        with txn.cursor(self.iden_tbl) as icurs, txn.cursor(self.valu_tbl) as vcurs:
            consumed, added = icurs.putmulti(idens)
            if consumed != added or added != len(rows):
                raise ConsistencyError('Failure writing to Db.  consumed %d != added %d != len(rows) %d',
                                       consumed, added, len(rows))
            consumed, added = vcurs.putmulti(bigvals)
            if consumed != added:
                raise ConsistencyError('Failure writing to Db.  consumed %d != added %d',
                                       consumed, added)

    def do_stage1(self):
        '''
        Do the first stage: suck all the data out of a cortex into an intermediate LMDB DB
        '''
        start_time = time.time()
        last_update = start_time
        logger.debug('Getting row count')
        totalrows = self.core.store.getSize()
        logger.debug('Total row count is %d', totalrows)
        rowcount = 0
        last_rowcount = 0

        for rows in self.core.store.genStoreRows(gsize=10000):
            lenrows = len(rows)
            rowcount += lenrows
            now = time.time()
            if last_update + 60 < now:  # pragma: no cover
                percent_complete = rowcount / totalrows * 100
                timeperrow = (now - last_update) / (rowcount - last_rowcount)
                estimate = int((totalrows - rowcount) * timeperrow)
                last_update = now
                last_rowcount = rowcount
                logger.info('%02.2f%% complete.  Estimated completion in %ds', percent_complete, estimate)

            with self.dbenv.begin(write=True) as txn:
                self._write_props(txn, rows)

                # if prop is tufo:form, and form is a comp, add to form->iden table
                compi = ((v.encode('utf8'), _enc_iden(i)) for i, p, v, _ in rows
                         if p == 'tufo:form' and (self.is_comp(v) or v == 'file:bytes'))
                with txn.cursor(self.form_tbl) as curs:
                        consumed, added = curs.putmulti(compi)
                        if consumed != added:
                            raise ConsistencyError('Failure writing to Db.  consumed %d != added %d',
                                                   consumed, added)

        logger.info('Stage 1 complete in %.1fs.', time.time() - start_time)

    def write_node_to_file(self, node):
        assert(len(node) == 2)
        self.outfh.write(s_msgpack.en(node))

    def _get_props_from_cursor(self, txn, curs):
        props = {}
        for pv_enc in curs.iternext_dup():
            if len(pv_enc) == 8:
                pv_enc = txn.get(pv_enc, db=self.valu_tbl)
                if pv_enc is None:
                    raise ConsistencyError('Missing big val')
            p, v = s_msgpack.un(pv_enc)
            props[p] = v
        return props

    def do_stage2a(self):
        '''
        Do the first part of the second stage:  take all the data out of the intermediate DB and emit to a flat file,
        just for the "first forms", all the seprs and comps and those that are migrated to comps.
        '''
        start_time = time.time()

        # Do the comp forms
        for i, formname in enumerate(self.first_forms):
            if formname in self.forms_to_drop or (self.good_forms is not None and formname not in self.good_forms):
                continue
            with self.dbenv.begin(write=True, db=self.form_tbl) as txn:
                curs = txn.cursor(self.form_tbl)
                if not curs.set_key(formname.encode('utf8')):
                    continue
                logger.info('Stage 2a: (%2d/%2d) processing nodes from %s', i + 1, len(self.first_forms), formname)
                for enc_iden in curs.iternext_dup():
                    props = None
                    try:
                        with txn.cursor(self.iden_tbl) as curs:
                            if not curs.set_key(enc_iden):
                                raise ConsistencyError('missing iden', hexlify(s_msgpack.un(enc_iden)))
                            props = self._get_props_from_cursor(txn, curs)
                        node = self.convert_props(props)
                        if node is None:
                            logger.debug('cannot convert %s', props)
                            continue
                        if formname == 'file:bytes':
                            if not txn.put(props['node:ndef'].encode('utf8'), s_msgpack.en(node[0]), db=self.comp_tbl):
                                raise ConsistencyError('put failure')
                            if not txn.put(props[formname].encode('utf8'), s_msgpack.en(node[0]), db=self.comp_tbl):
                                raise ConsistencyError('put failure')
                        else:
                            txn.put(props[formname].encode('utf8'), s_msgpack.en(node[0]), db=self.comp_tbl)
                        self.write_node_to_file(node)
                    except Exception:
                        logger.debug('Failed on processing node of form %s', formname, exc_info=True)
                        if props is not None and self.rejects_fh is not None:
                            self.rejects_fh.write(s_msgpack.en(props))

        comp_node_time = time.time()
        logger.debug('Stage 2a complete in %.1fs', comp_node_time - start_time)

    def do_stage2b(self):
        '''
        Do the rest (the non-comp) forms
        '''
        # Do all the non-comp forms
        start_time = time.time()
        iden_first = 0
        iden_last = 2 ** 128 - 1
        prev_update = time.time()
        prev_iden = iden_first
        with self.dbenv.begin(db=self.iden_tbl) as txn:
            curs = txn.cursor(self.iden_tbl)
            if not curs.set_range(iden_first.to_bytes(16, 'big')):
                raise Exception('no data!')
            while True:
                iden_int = int.from_bytes(curs.key(), 'big')
                if iden_int > iden_last:
                    break

                now = time.time()
                if prev_update + 60 < now:  # pragma: no cover
                    percent_complete = (iden_int - iden_first) / (iden_last - iden_first) * 100.0
                    try:
                        timeperiden = (now - prev_update) / (iden_int - prev_iden)
                    except ZeroDivisionError:
                        timeperiden = 0.0
                    estimate = int((iden_last - iden_int) * timeperiden)
                    logger.info('Stage 2 %02.2f%% complete.  Estimated completion in %ds', percent_complete, estimate)

                    prev_update = now
                    prev_iden = iden_int

                props = self._get_props_from_cursor(txn, curs)
                rv = curs.next()
                formname = props.get('tufo:form')
                if not (formname is None or formname in self.first_forms or
                        (self.good_forms and formname not in self.good_forms)):
                    try:
                        node = self.convert_props(props)
                        if node is not None:
                            self.write_node_to_file(node)
                        else:
                            logger.debug('Cannot convert %s', props)
                    except Exception:
                        logger.debug('Failed on processing node with props: %s', props, exc_info=True)
                        if self.rejects_fh is not None:
                            self.rejects_fh.write(s_msgpack.en(props))
                if not rv:
                    break  # end of data

        logger.info('Stage 2b complete in %.1fs.', time.time() - start_time)

    def just_guid(self, formname, props):
        return props[formname]

    def is_sepr(self, formname):
        return formname in self.seprs

    def is_comp(self, formname):
        return formname in self.comps

    def convert_sepr(self, formname, propname, propval, props):
        t = self.core.getPropType(propname)
        retn = []
        valdict = t.norm(propval)[1]
        for field in (x[0] for x in t._get_fields()):
            oldval = valdict[field]
            full_member = '%s:%s' % (propname, field)
            _, val = self.convert_subprop(formname, full_member, oldval, props)
            retn.append(val)

        return tuple(retn)

    def convert_file_bytes(self, formname, props):
        sha256 = props.get(formname + ':sha256')
        if sha256 is None:
            return 'guid:' + props[formname]
        return 'sha256:' + sha256

    def convert_xref(self, propname, propval, props):
        t = self.core.getPropType(propname)
        sourceval = props[propname + ':' + t._sorc_name]
        destprop = props[propname + ':xref:prop']

        destval = props.get(propname + ':xref:intval', props.get(propname + ':xref:strval'))
        if destval is None:
            destval = props[propname + ':xref'].split('=', 1)[1]
        source_final = self.convert_foreign_key(propname, t._sorc_type, sourceval)
        dest_final = self.convert_foreign_key(propname, destprop, destval)

        if destprop in self.form_renames:
            destprop = self.form_renames[destprop]

        return (source_final, (destprop, dest_final))

    def convert_primary(self, props):
        formname = props['tufo:form']
        pkval = props[formname]
        if formname in self.primary_prop_special:
            return self.primary_prop_special[formname](self, formname, props)
        if self.is_comp(formname):
            return self.convert_comp_primary(props)
        if self.is_sepr(formname):
            return self.convert_sepr(formname, formname, pkval, props)
        if formname in self.xrefs:
            return self.convert_xref(formname, pkval, props)
        _, val = self.convert_subprop(formname, formname, pkval, props)
        return val

    def convert_comp_secondary(self, formname, propval):
        '''
        Convert secondary prop that is a comp type
        '''
        with self.dbenv.begin(db=self.comp_tbl) as txn:
            comp_enc = txn.get(propval.encode('utf8'), db=self.comp_tbl)
            if comp_enc is None:
                raise ConsistencyError('guid accessed before determined')
            return s_msgpack.un(comp_enc)[1]

    def convert_filebytes_secondary(self, formname, propval):
        '''
        Convert secondary prop that is a filebytes type
        '''
        with self.dbenv.begin(db=self.comp_tbl) as txn:
            comp_enc = txn.get(propval.encode('utf8'), db=self.comp_tbl)
            if comp_enc is None:
                raise ConsistencyError('ndef accessed before determined')
            return s_msgpack.un(comp_enc)[1]

    def convert_foreign_key(self, formname, pivot_formname, pivot_fk):
        '''
        Convert secondary prop that is a pivot to another node
        '''
        if pivot_formname in self.filebytes:
            return self.convert_filebytes_secondary(pivot_formname, pivot_fk)
        if pivot_formname in ('inet:tcp4', 'inet:tcp6', 'inet:udp4', 'inet:udp6'):
            return self.xxp_to_server(pivot_formname, pivot_formname, pivot_formname, pivot_fk, {})[1]
        if self.is_comp(pivot_formname):
            return self.convert_comp_secondary(pivot_formname, pivot_fk)
        if self.is_sepr(pivot_formname):
            return self.convert_sepr(formname, pivot_formname, pivot_fk, None)

        return pivot_fk

    def convert_comp_primary(self, props):
        formname = props['tufo:form']
        # logger.debug('convert_comp_primary_property: %s, %s', formname, compspec)
        t = self.core.getPropType(formname)
        members = [x[0] for x in t.fields]
        if formname == 'inet:dns:soa':
            members = ['ns', 'email']
        retn = []
        for member in members:
            full_member = '%s:%s' % (formname, member)
            if full_member in props:
                _, val = self.convert_subprop(formname, full_member, props[full_member], props)
                retn.append(val)
        return tuple(retn)

    def default_subprop_convert(self, formname, subpropname, subproptype, val):
        # logger.debug('default_subprop_convert : %s(type=%s)=%s', subpropname, subproptype, val)
        if subproptype != subpropname and subproptype in self.core.getTufoForms():
            return self.convert_foreign_key(formname, subproptype, val)
        return val

    def ipv4_to_client(self, formname, propname, typename, val, props):
        return formname + ':client', 'tcp://%s' % s_inet.ipv4str(val)

    def ipv6_to_client(self, formname, propname, typename, val, props):
        return formname + ':client', 'tcp://[%s]' % val

    def convert_inet_xxp_primary(self, formname, props):
        oldpkval = props[formname]
        _, newpkval = self.xxp_to_server(formname, formname, formname, oldpkval, props)
        return newpkval

    def xxp_to_server(self, formname, propname, typename, val, props):
        if typename[-1] == '4':
            addrport = self.core.getTypeRepr('inet:srv4', val)
        else:
            addrport = val
        return None, '%s://%s' % (typename[5:8], addrport)

    def check_file_base_primary(self, formname, props):
        pk = props[formname]
        if '\\' not in pk:
            return props[formname]
        _, new_pk = self.check_file_base(formname, formname, formname, pk, props)

        # Make a file:path node with the same tags
        ndef = ('file:path', self.core.getTypeRepr('file:path', pk.replace('\\', '/')))
        propscopy = props.copy()
        propscopy[formname] = new_pk
        template = self.convert_props(propscopy)
        new_node = (ndef, {'props': {'.created': template[1]['props']['.created']},
                           'tags': template[1].get('tags', {})})

        self.write_node_to_file(new_node)

        return new_pk

    def check_file_base(self, formname, propname, typename, val, props):
        return None, val.rsplit('\\', 1)[-1]

    dns_enums = {
        'soa': 6,
        'ns': 2,
        'mx': 15,
        'a': 1,
        'aaaa': 28,
        'txt': 16,
        'srv': 33,
        'ptr': 12,
        'cname': 5,
        'hinfo': 13,
        'isdn': 20,
    }

    def convert_dns_type(self, formname, propname, typename, val, props):
        return None, self.dns_enums.get(val, 1)

    type_special = {
        'inet:tcp4': xxp_to_server,
        'inet:tcp6': xxp_to_server,
        'inet:udp4': xxp_to_server,
        'inet:udp6': xxp_to_server,
        'file:base': check_file_base,
        'inet:dns:type': convert_dns_type
    }

    form_renames = {
        'file:txtref': 'file:ref',
        'file:imgof': 'file:ref',
        'ps:image': 'file:ref',
        'it:exec:bind:tcp': 'it:exec:bind',
        'it:exec:bind:udp': 'it:exec:bind',
        'inet:tcp4': 'inet:server',
        'inet:tcp6': 'inet:server',
        'inet:udp4': 'inet:server',
        'inet:udp4': 'inet:server',
        'inet:ssl:tcp4cert': 'inet:ssl:cert',
        'inet:dns:req': 'inet:dns:query',
        'inet:dns:look': 'inet:dns:request'
    }

    prop_renames = {
        'inet:fqdn:zone': 'inet:fqdn:iszone',
        'inet:fqdn:sfx': 'inet:fqdn:issuffix',
        'inet:ipv4:cc': 'inet:ipv4:loc',
        'tel:phone:cc': 'tel:phone:loc',
        'ou:org:cc': 'ou:org:loc',
        'inet:web:acct:client': 'inet:web:acct:signup:client',
        'inet:dns:look:ipv4': 'inet:dns:look:client',
        'inet:dns:look:tcp4': 'inet:dns:look:server',
        'inet:dns:look:udp4': 'inet:dns:look:server',
        'inet:dns:look:rcode': 'inet:dns:look:reply:code',

        'inet:flow:dst:udp4': 'inet:flow:dst',
        'inet:flow:dst:udp6': 'inet:flow:dst',
        'inet:flow:dst:tcp4': 'inet:flow:dst',
        'inet:flow:dst:tcp6': 'inet:flow:dst',
        'inet:flow:src:udp4': 'inet:flow:src',
        'inet:flow:src:udp6': 'inet:flow:src',
        'inet:flow:src:tcp4': 'inet:flow:src',
        'inet:flow:src:tcp6': 'inet:flow:src',
        'file:bytes:mime:pe:timestamp': 'file:bytes:mime:pe:compiled',
        'it:exec:bind:tcp:ipv4': 'it:exec:bind:tcp:server',
        'it:exec:bind:tcp:ipv6': 'it:exec:bind:tcp:server',
        'it:exec:bind:udp:ipv4': 'it:exec:bind:tcp:server',
        'it:exec:bind:udp:ipv6': 'it:exec:bind:tcp:server',
    }

    forms_to_drop = set((
        'syn:tagform',
    ))

    secondary_props_to_drop = set((
        'syn:tag:depth',
        'ps:name:middle',
        'ps:name:sur',
        'ps:name:given',
        'inet:tcp4:ipv4',
        'inet:tcp4:port',
        'inet:udp4:ipv4',
        'inet:udp4:port',
        'inet:tcp6:ipv6',
        'inet:tcp6:port',
        'inet:udp6:ipv6',
        'inet:udp6:port',
        'inet:cidr4:ipv4',
        'file:path:ext',
        'ps:person:guidname',
        'ps:persona:guidname',
        'inet:web:action:info',
        'inet:web:action:ipv4',
        'inet:ssl:tcp4cert:file',
        'inet:ssl:tcp4cert:cert',
        'inet:ssl:tcp4cert:tcp4',
        'ps:image:person',
        'ps:image:file',
        'it:exec:bind:tcp:port',
        'it:exec:bind:udp:port',
        'inet:dns:look:a',
        'inet:dns:look:ns',
        'inet:dns:look:rev',
        'inet:dns:look:aaaa',
        'inet:dns:look:cname',
        'inet:dns:look:mx',
        'inet:dns:look:soa',
        'inet:dns:look:txt',
    ))

    def convert_subprop(self, formname, propname, val, props):
        typename = self.core.getPropTypeName(propname)
        converted = False

        if propname in self.subprop_special:
            propname, val = self.subprop_special[propname](self, formname, propname, typename, val, props)
            if propname is None:
                return None, None
            converted = True
        elif typename in self.type_special:
            newpropname, val = self.type_special[typename](self, formname, propname, typename, val, props)
            if newpropname is not None:
                propname = newpropname
            converted = True

        newpropname = self.prop_renames.get(propname, propname)
        newpropname = newpropname[len(formname) + 1:]
        if converted:
            return newpropname, val

        return newpropname, self.default_subprop_convert(formname, propname, typename, val)

    def convert_props(self, oldprops):
        formname = oldprops['tufo:form']
        if formname in self.forms_to_drop:
            return None
        props = {}
        tags = {}
        propsmeta = self.core.getSubProps(formname)
        pk = None
        for oldk, oldv in sorted(oldprops.items(), key=_special_sort_key):
            propmeta = next((x[1] for x in propsmeta if x[0] == oldk), {})
            if oldk in self.secondary_props_to_drop:
                continue
            if oldk in self.compfields or oldk in self.seprfields:
                continue
            if oldk[0] == '#':
                tags[oldk[1:]] = (None, None)
            elif oldk[0] == '>':
                start, end = tags.get(oldk[2:], (None, None))
                start = oldv
                tags[oldk[2:]] = (start, end)
            elif oldk[0] == '<':
                start, end = tags.get(oldk[2:], (None, None))
                end = oldv
                tags[oldk[2:]] = (start, end)
            elif oldk == formname:
                pk = self.convert_primary(oldprops)
            elif oldk in self.subs:
                # Skip if a sub to a comp or sepr that's another secondary property
                continue
            elif 'defval' in propmeta and oldv == propmeta['defval']:
                # logger.debug('Skipping field %s with default value', oldk)
                continue
            elif oldk.startswith(formname + ':'):
                if oldk[len(formname) + 1:] in ('seen:min', 'seen:max'):
                    new_pname, newv = self.handle_seen(oldk, oldv, props)
                elif formname in self.xrefs:
                    # skip all non-seed secondary props in xrefs
                    continue
                else:
                    new_pname, newv = self.convert_subprop(formname, oldk, oldv, oldprops)
                    if new_pname is None:
                        continue
                props[new_pname] = newv
            elif oldk == 'node:created':
                props['.created'] = oldv
            else:
                # logger.debug('Skipping propname %s', oldk)
                pass
        if pk is None:
            raise ConsistencyError('Missing pk', oldprops)

        if formname == 'file:txtref':
            props['type'] = 'text'
        elif formname == 'file:imgof':
            props['type'] = 'image'
        elif formname == 'ps:image':
            props['type'] = 'image'

        if formname in self.form_renames:
            formname = self.form_renames[formname]

        assert '' not in props

        retn = ((formname, pk), {'props': props})
        if tags:
            retn[1]['tags'] = tags

        return retn

    def convert_ps_image(self, formname, props):
        '''
        Transform ps:image into a file:ref
        '''
        person, file = self.convert_sepr(formname, formname, props[formname], props)
        return (file, ('ps:person', person))

    primary_prop_special = {
        'inet:web:post': just_guid,
        'it:dev:regval': just_guid,
        'file:bytes': convert_file_bytes,
        'inet:udp4': convert_inet_xxp_primary,
        'inet:udp6': convert_inet_xxp_primary,
        'inet:tcp4': convert_inet_xxp_primary,
        'inet:tcp6': convert_inet_xxp_primary,
        'ps:image': convert_ps_image,
        'file:base': check_file_base_primary,
    }

    def handle_seen(self, propname, propval, newprops):
        '''
        :seen:min, :seen:max -> .seen = (min, max)
        '''
        seenmin, seenmax = newprops.get('.seen', (None, None))
        if propname.endswith(':min'):
            seenmin = propval
        if propname.endswith(':max'):
            seenmax = propval
        if seenmax is None:
            seenmax = seenmin + 1
        if seenmin is None:
            seenmin = seenmax - 1
        return '.seen', (seenmin, seenmax)

    def ip_with_port_to_server(self, formname, propname, typename, val, props):
        port = props.get(formname + ':port')
        if propname[-1] == '4':
            if port is not None:
                val = (val << 16) + port
            addrport = self.core.getTypeRepr('inet:srv4', val)
        else:
            if port is None:
                addrport = '[' + val + ']'
            else:
                addrport = '[%s]:%s' % (val, port)
        return propname, '%s://%s' % (formname[-3:], addrport)

    def name_en_to_has(self, formname, propname, typename, val, props):
        ''' Handle {ou:org,,ps:person,ps:persona} name:en props '''

        # First write the new {ou,ps}:name node
        psorou = formname.split(':', 1)[0]
        nameformname = 'ps:name' if psorou == 'ps' else 'ou:org:name'
        nameprops = {}
        if psorou == 'ps':
            for prop in [':sur', ':given', ':middle']:
                part = props.get(propname + prop)
                if part is not None:
                    nameprops[nameformname + prop] = part
        namenode = ((nameformname, val), {'props': nameprops})
        self.write_node_to_file(namenode)

        # Then write the new {ou:org:has,ps:person:has,ps:persona:has} node
        hasformname = formname + ':has'
        hasnode = ((hasformname, (props[formname], (nameformname, val))), {})
        self.write_node_to_file(hasnode)

        return None, None

    def dns_look_ipv4_to_query(self, formname, propname, typename, val, props):
        '''
        While we're converting inet:dns:look:ipv4 to a dns:query, also emit a inet:dns:answer
        '''
        client = 'tcp://%s' % s_inet.ipv4str(val)
        answer_fields = {
            'inet:dns:look:a',
            'inet:dns:look:ns',
            'inet:dns:look:rev',
            'inet:dns:look:cname',
            'inet:dns:look:mx',
            'inet:dns:look:soa',
            'inet:dns:look:txt',
        }
        query_name_fields = {
            'inet:dns:look:a:fqdn',
            'inet:dns:look:ns:zone',
            'inet:dns:look:rev:fqdn',
            'inet:dns:look:cname:fqdn',
            'inet:dns:look:mx:fqdn',
            'inet:dns:look:soa:fqdn',
            'inet:dns:look:txt:fqdn'
        }
        name = None
        for f in query_name_fields:
            name = props.get(f)
            if name is not None:
                break
        else:
            name = '<unknown>'
        dnstype = props.get('inet:dns:look:rcode', 1)
        answer_props = {'request': props['inet:dns:look']}
        for fname in answer_fields:
            val = props.get(fname)
            if val is None:
                continue
            answer_props[fname.rsplit(':', 1)[-1]] = self.convert_foreign_key('inet:dns:look', fname, val)
        created = props.get('node:created')
        if created is not None:
            answer_props['.created'] = created
        tags = {}
        for k in props:
            if k[0] == '#':
                tags[k[1:]] = (None, None)

        answer_node = (('inet:dns:answer', s_common.guid()), {'props': answer_props})
        if tags:
            answer_node[1]['tags'] = tags
        self.write_node_to_file(answer_node)

        return 'inet:dns:look:query', (client, name, dnstype)

    subprop_special = {
        'inet:exec:url:ipv4': ipv4_to_client,
        'inet:exec:url:ipv6': ipv6_to_client,
        'inet:web:logon:ipv4': ipv4_to_client,
        'inet:web:logon:ipv6': ipv6_to_client,
        'inet:web:action:ipv4': ipv4_to_client,
        'inet:web:action:ipv6': ipv6_to_client,
        'inet:web:acct:signup:ipv4': ipv4_to_client,
        'inet:dns:look:ipv4': dns_look_ipv4_to_query,
        'it:exec:bind:tcp:ipv4': ip_with_port_to_server,
        'it:exec:bind:tcp:ipv6': ip_with_port_to_server,
        'it:exec:bind:udp:ipv4': ip_with_port_to_server,
        'it:exec:bind:udp:ipv6': ip_with_port_to_server,
        'ps:person:name:en': name_en_to_has,
        'ps:persona:name:en': name_en_to_has,
        'ou:org:name:en': name_en_to_has,
    }

def main(argv, outp=None):  # pragma: no cover
    p = argparse.ArgumentParser(description='''Command line tool to export a Synapse Cortex v. 0.0.5 to a mpk file
 for importation into a 0.1.0 cortex''')
    p.add_argument('cortex', help='URL to a *local* cortex to be dumped')
    p.add_argument('outfile', help='file to dump to')
    p.add_argument('--stage-1', help='Start at stage 2 with stage 1 file')
    p.add_argument('--log-level', choices=s_const.LOG_LEVEL_CHOICES, help='specify the log level', type=str.upper)
    p.add_argument('--extra-module', nargs='+', help='name of an extra module to load')
    p.add_argument('--only-convert-forms-file', type=argparse.FileType('r'),
                   help='Path to newline-delimited file of forms to convert')
    opts = p.parse_args(argv)

    s_common.setlogging(logger, opts.log_level)

    fh = logging.FileHandler(opts.outfile + '.log')
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    if opts.extra_module is not None:
        for modname in opts.extra_module:
            s_modules.load(modname)

    if opts.only_convert_forms_file:
        good_forms = []
        for line in opts.only_convert_forms_file:
            good_forms.append(line.rstrip())
    else:
        good_forms = None

    fh = open(opts.outfile, 'wb')
    rejects_fh = open(opts.outfile + '.rejects', 'wb')
    with s_cortex.openurl(opts.cortex, conf={'caching': True, 'cache:maxsize': 1000000}) as core:
        m = Migrator(core, fh, tmpdir=pathlib.Path(opts.outfile).parent, stage1_fn=opts.stage_1, rejects_fh=rejects_fh,
                     good_forms=good_forms)
        m.migrate()
    return 0

if __name__ == '__main__':  # pragma: no cover
    import sys
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    sys.exit(main(sys.argv[1:]))
