import time
import logging
import pathlib
import argparse
import tempfile
from binascii import unhexlify, hexlify

import lmdb  # type: ignore

import synapse.cortex as s_cortex
import synapse.lib.lmdb as s_lmdb
import synapse.lib.msgpack as s_msgpack
import synapse.models.inet as s_inet

logger = logging.getLogger(__name__)

# TODO
# seen:min, seen:max into universal interval prop.  (If missing, make minimal valid interval)
# for each field of type derived from xref, must look up
# Add config file to allow additional coremodules
# parallelize stage2
# file:base -> filepath if backslash in them (?? separate the last part out?)
# * fix the file:base to only include the last part
# # add a corresponding file:path with the correct normalized path
# # copy any tags on the former to the latter
# # if a secondary prop, just normalize and use the last part
# inet:flow -> inetserver/inetclient
# file:txtref, file:imgof -> both turn into file:ref comp: (file:bytes, ndef)
#     secondary prop: type ("image", "text")
# ps:name, reverse order, remove comma, remove all subproperties on ps:name form (*not* type)
# throw all syn:tagform nodes on the floor
# throw syn:tag:depth subprop on the floor
# drop file:path:ext subprop
# tel:phone:cc -> tel:phone:loc
# drop ps:name:{middle,sur}
# ps:image ( another in the xrefs reconstruction guys ) should get merged into being a file:imgof=(<file>, <node>)
#   which is still a guid node, so you can just make the ndef ('ps:person', <oldguid>)
#   where oldguid is the :person prop
# Bugs:
# 'inet:web:acct:avatar' seems to still be just a guid
# ps:person:has may have missed comp conversion
# inet:ssl:tcp4cert needs to be renamed to:   inet:ssl:servercert
# ou:org:has seems to have escaped comp/xref reconstruction

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

def _enc_iden(iden):
    return unhexlify(iden)

class ConsistencyError(Exception):
    pass

class Migrator:
    '''
    Sucks all rows out of a < .0.1.0 cortex, into a temporary LMDB database, migrates the schema, then dumps to new
    file suitable for ingesting into a >= .0.1.0 cortex.
    '''
    def __init__(self, core, outfh, tmpdir=None, stage1_fn=None):
        self.core = core
        self.dbenv = None
        self.skip_stage1 = bool(stage1_fn)
        assert tmpdir or stage1_fn
        self.next_val = 0

        if stage1_fn is None:
            with tempfile.NamedTemporaryFile(prefix='stage1_', suffix='.lmdb', delete=True, dir=tmpdir) as fh:
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

    def _precalc_types(self):
        ''' Precalculate which types are sepr and which are comps, and which are subs of comps '''
        seprs = []
        comps = []
        subs = []
        forms = self.core.getTufoForms()
        for formname in forms:
            parents = self.core.getTypeOfs(formname)
            if 'sepr' in parents:
                seprs.append(formname)
            if 'comp' in parents:
                comps.append(formname)
            subpropnameprops = self.core.getSubProps(formname)
            subpropnames = [x[0] for x in subpropnameprops]
            for subpropname, subpropprops in subpropnameprops:
                parents = self.core.getTypeOfs(subpropprops['ptype'])
                if 'sepr' in parents:
                    seprs.append(subpropname)
                if 'comp' in parents:
                    comps.append(subpropname)
                if ('comp' in parents) or ('sepr' in parents) or subpropprops['ptype'] in forms:
                    subs.extend(x for x in subpropnames if x.startswith(subpropname + ':'))

        self.seprs = set(seprs)
        self.comps = set(comps)
        self.subs = set(subs)

    def migrate(self):
        if not self.skip_stage1:
            self.do_stage1()
        self.do_stage2()

    def _write_props(self, txn, rows):
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
                         if p == 'tufo:form' and self.is_comp(v))
                # Nic tmp
                compi = list(compi)
                with txn.cursor(self.form_tbl) as curs:
                        consumed, added = curs.putmulti(compi)
                        if consumed != added:
                            raise ConsistencyError('Failure writing to Db.  consumed %d != added %d',
                                                   consumed, added)

        logger.info('Stage 1 complete in %.1fs.', time.time() - start_time)

    def write_node_to_file(self, node):
        self.outfh.write(s_msgpack.en(node))

    def get_props(self, enc_iden, txn):
        '''
        Get all the props from lmdb for an iden
        '''
        with txn.cursor(self.iden_tbl) as curs:
            if not curs.set_key(enc_iden):
                raise ConsistencyError('missing iden', hexlify(s_msgpack.un(enc_iden)))
            props = {}
            for pv_enc in curs.iternext_dup():
                if len(pv_enc) == 8:
                    pv_enc = txn.get(pv_enc, db=self.valu_tbl)
                    if pv_enc is None:
                        raise ConsistencyError('Missing big val')
                p, v = s_msgpack.un(pv_enc)
                props[p] = v
            return props

    forms_to_drop = set((
        'syn:tagform',
    ))

    def do_stage2(self):
        start_time = time.time()
        comp_forms = [f for f in reversed(_comp_and_sepr_forms) if self.is_comp(f)]

        # Do the comp forms
        for i, formname in enumerate(comp_forms):
            if formname in self.forms_to_drop:
                continue
            with self.dbenv.begin(write=True, db=self.form_tbl) as txn:
                curs = txn.cursor(self.form_tbl)
                if not curs.set_key(formname.encode('utf8')):
                    continue
                logger.info('Stage 2a: (%3d/%3d) processing nodes from %s', i + 1, len(comp_forms), formname)
                for enc_iden in curs.iternext_dup():
                    try:
                        props = self.get_props(enc_iden, txn)
                        node = self.convert_props(props)
                        if node is None:
                            continue
                        txn.put(props[formname].encode('utf8'), s_msgpack.en(node[0]), db=self.comp_tbl)
                        self.write_node_to_file(node)
                    except Exception:
                        logger.debug('Failed on processing node of form %s', formname, exc_info=True)

        comp_node_time = time.time()
        logger.debug('Finished processing comp nodes in %.1fs', comp_node_time - start_time)

        # Do all the non-comp forms
        iden_first = 0
        iden_last = 2 ** 128 - 1
        prev_update = comp_node_time
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
                    timeperiden = (now - prev_update) / (iden_int / prev_iden)
                    estimate = int((iden_last - iden_int) * timeperiden)
                    logger.info('Stage 2 %02.2f%% complete.  Estimated completion in %ds', percent_complete, estimate)

                    prev_update = now
                    prev_iden = iden_int

                props = {}
                for pv_enc in curs.iternext_dup():
                    if len(pv_enc) == 8:
                        pv_enc = txn.get(pv_enc, db=self.valu_tbl)
                    p, v = s_msgpack.un(pv_enc)
                    # Skip dark rows or forms we've already done
                    if p[0] == '.' or p[0] == '_' or p == 'tufo:form' and v in comp_forms:
                        rv = curs.next_nodup()
                        break
                    props[p] = v
                else:
                    rv = curs.next()
                    try:
                        node = self.convert_props(props)
                        if node is not None:
                            self.write_node_to_file(node)
                    except Exception:
                        logger.debug('Failed on processing node with props: %s', props, exc_info=True)
                if not rv:
                    break  # end of data

        logger.info('Stage 2 complete in %.1fs.', time.time() - start_time)

    def just_guid(self, formname, props):
        return None, props[formname]

    def is_sepr(self, formname):
        return formname in self.seprs

    def is_comp(self, formname):
        return formname in self.comps

    def convert_sepr(self, propname, propval):
        t = self.core.getPropType(propname)
        retn = []
        valdict = t.norm(propval)[1]
        for field in (x[0] for x in t._get_fields()):
            retn.append((valdict[field]))
        return tuple(retn)

    def convert_file_bytes(self, formname, props):
        sha256 = props.get(formname + ':sha256')
        if sha256 is None:
            return None, 'guid:' + props[formname]
        return None, 'sha256:' + sha256

    def convert_primary(self, props):
        formname = props['tufo:form']
        pkval = props[formname]
        if formname in self.primary_prop_special:
            return self.primary_prop_special[formname](self, formname, props)
        if self.is_comp(formname):
            return None, self.convert_comp_primary(props)
        if self.is_sepr(formname):
            return None, self.convert_sepr(formname, pkval)
        _, val = self.convert_subprop(formname, formname, pkval)
        return None, val

    def convert_comp_secondary(self, formname, propval):
        ''' Convert secondary prop that is a comp type '''
        with self.dbenv.begin(db=self.comp_tbl) as txn:
            comp_enc = txn.get(propval.encode('utf8'), db=self.comp_tbl)
            if comp_enc is None:
                raise ConsistencyError('guid accessed before determined')
            return s_msgpack.un(comp_enc)

    def convert_foreign_key(self, pivot_formname, pivot_fk):
        ''' Convert secondary prop that is a pivot to another node '''
        # logger.debug('convert_foreign_key: %s=%s', pivot_formname, pivot_fk)
        if self.is_comp(pivot_formname):
            return self.convert_comp_secondary(pivot_formname, pivot_fk)

        if self.is_sepr(pivot_formname):
            return self.convert_sepr(pivot_formname, pivot_fk)

        special_func = self.secondary_prop_special.get(pivot_formname)
        if special_func:
            return special_func(pivot_formname, pivot_fk)

        return pivot_fk

    def convert_comp_primary(self, props):
        formname = props['tufo:form']
        # logger.debug('convert_comp_primary_property: %s, %s', formname, compspec)
        t = self.core.getPropType(formname)
        members = [x[0] for x in t.fields]
        retn = []
        for member in members:
            full_member = '%s:%s' % (formname, member)
            _, val = self.convert_subprop(formname, full_member, props[full_member])
            retn.append(val)
        return tuple(retn)

    def default_subprop_convert(self, subpropname, subproptype, val):
        # logger.debug('default_subprop_convert : %s(type=%s)=%s', subpropname, subproptype, val)
        if subproptype != subpropname and subproptype in self.core.getTufoForms():
            return self.convert_foreign_key(subproptype, val)
        return val

    prop_renames = {
        'inet:fqdn:zone': 'inet:fqdn:iszone',
        'inet:fqdn:sfx': 'inet:fqdn:issuffix',
        'inet:ipv4:cc': 'inet:ipv4:loc',
        'inet:flow:dst:tcp4': 'inet:flow:dst',
        'inet:flow:dst:tcp4': 'inet:flow:dst',
        'inet:flow:dst:udp4': 'inet:flow:dst',
        'inet:flow:dst:tcp6': 'inet:flow:dst',
        'inet:flow:src:udp6': 'inet:flow:src',
        'inet:flow:src:udp4': 'inet:flow:src',
        'inet:flow:src:tcp6': 'inet:flow:src',
        'inet:flow:src:udp6': 'inet:flow:src'
    }

    def ipv4_to_client(self, formname, propname, typename, val):
        return 'client', 'tcp://%s/' % s_inet.ipv4str(val)

    def ipv6_to_client(self, formname, propname, typename, val):
        return 'client', 'tcp://[%s]/' % val

    def ipv4_to_server(self, formname, propname, typename, val):
        _, props = self.core.getTufoByProp(typename, val)
        addr_propname = 'ipv' + typename[-1]
        addr = s_inet.ipv4str(props[typename + ':' + addr_propname])
        port = props[typename + ':port']
        return propname, '%s://%s:%s/' % (typename[5:8], addr, port)

    def ipv6_to_server(self, formname, propname, typename, val):
        _, props = self.core.getTufoByProp(typename, val)
        addr_propname = 'ipv' + typename[-1]
        addr = props[typename + ':' + addr_propname]
        port = props[typename + ':port']
        return propname, '%s://[%s]:%s/' % (typename[5:8], addr, port)

    type_special = {
        'inet:tcp4': ipv4_to_server,
        'inet:tcp6': ipv6_to_server,
        'inet:udp4': ipv4_to_server,
        'inet:udp6': ipv6_to_server
    }

    def convert_subprop(self, formname, propname, val):
        typename = self.core.getPropTypeName(propname)
        converted = False

        if propname in self.subprop_special:
            propname, val = self.subprop_special[propname](self, formname, propname, typename, val)
            converted = True
        elif typename in self.type_special:
            propname, val = self.type_special[typename](self, formname, propname, typename, val)
            converted = True

        newpropname = self.prop_renames.get(propname, propname)
        newpropname = newpropname[len(formname) + 1:]
        if converted:
            return newpropname, val

        return newpropname, self.default_subprop_convert(propname, typename, val)

    def convert_props(self, oldprops):
        formname = oldprops['tufo:form']
        if formname in self.forms_to_drop:
            return None

        props = {}
        tags = {}
        propsmeta = self.core.getSubProps(formname)
        pk = None
        skipfields = set()
        for oldk, oldv in sorted(oldprops.items()):
            propmeta = next((x[1] for x in propsmeta if x[0] == oldk), {})
            if oldk in skipfields:
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
                newskipfields, pk = self.convert_primary(oldprops)
                if newskipfields:
                    skipfields.update(newskipfields)
            elif oldk in self.subs:
                # Skip if a sub to a comp or sepr that's another secondary property
                continue
            elif 'defval' in propmeta and oldv == propmeta['defval']:
                # logger.debug('Skipping field %s with default value', oldk)
                continue
            elif oldk.startswith(formname + ':'):
                new_pname, newv = self.convert_subprop(formname, oldk, oldv)
                props[new_pname] = newv
            elif oldk == 'node:created':
                props['.created'] = oldv
            else:
                # logger.debug('Skipping propname %s', oldk)
                pass
        if pk is None:
            raise ConsistencyError(oldprops)

        retn = ((formname, pk), {'props': props})
        if tags:
            retn[1]['tags'] = tags

        return retn

    primary_prop_special = {
        'inet:web:post': just_guid,
        'it:dev:regval': just_guid,
        'inet:dns:soa': just_guid,
        'file:bytes': convert_file_bytes
    }

    secondary_prop_special = {
            # 'file:bytes': convert_file_bytes_secondary
        }

    subprop_special = {
        'inet:web:logon:ipv4': ipv4_to_client,
        'inet:web:logon:ipv6': ipv6_to_client,
        # 'inet:flow:dest:tcp4': foo,
        # 'inet:flow:dest:tcp4': foo,
        # 'inet:flow:dest:udp6': foo,
        # 'inet:flow:dest:udp6': foo,
        # 'inet:flow:src:tcp4': foo,
        # 'inet:flow:src:tcp4': foo,
        # 'inet:flow:src:udp6': foo,
        # 'inet:flow:src:udp6': foo,
    }

def main(argv, outp=None):  # pragma: no cover
    p = argparse.ArgumentParser()
    p.add_argument('cortex', help='telepath URL for a cortex to be dumped')
    p.add_argument('outfile', help='file to dump to')
    p.add_argument('--verbose', '-v', action='count', help='Verbose output')
    p.add_argument('--stage-1', help='Start at stage 2 with stage 1 file')
    opts = p.parse_args(argv)

    if opts.verbose is not None:
        if opts.verbose > 1:
            # logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler(opts.outfile + '.log')
            fh.setLevel(logging.DEBUG)
        elif opts.verbose > 0:
            logger.setLevel(logging.INFO)

    fh = open(opts.outfile, 'wb')
    with s_cortex.openurl(opts.cortex, conf={'caching': True, 'cache:maxsize': 1000000}) as core:
        m = Migrator(core, fh, tmpdir=pathlib.Path(opts.outfile).parent, stage1_fn=opts.stage_1)
        m.migrate()
    return 0

if __name__ == '__main__':  # pragma: no cover
    import sys
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    sys.exit(main(sys.argv[1:]))
