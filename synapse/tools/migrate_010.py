import time
import logging
import pathlib
import argparse
import tempfile
from binascii import unhexlify

import lmdb  # type: ignore

import synapse.cortex as s_cortex
# import synapse.cores.common as s_common
import synapse.lib.msgpack as s_msgpack
# import synapse.lib.output as s_output

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

def _enc_iden(iden):
    return unhexlify(iden)

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
        if stage1_fn is None:
            with tempfile.NamedTemporaryFile(prefix='stage1', suffix='.lmdb', delete=True, dir=tmpdir) as fh:
                stage1_fn = fh.name
            logger.info('Creating stage 1 file at %s.  Delete when migration deemed successful.', stage1_fn)

        map_size = 1000000000
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
        self.outfh = outfh
        self._precalc_types()

    def _precalc_types(self):
        ''' Precalculate which types are sepr and which are comps '''
        seprs = []
        comps = []
        for formname in self.core.getTufoForms():
            parents = self.core.getTypeOfs(formname)
            if 'sepr' in parents:
                seprs.append(formname)
            if 'comp' in parents:
                comps.append(formname)
            for subpropname, _ in self.core.getSubProps(formname):
                parents = self.core.getTypeOfs(subpropname)
                if 'sepr' in parents:
                    seprs.append(subpropname)
                if 'comp' in parents:
                    comps.append(subpropname)

        self.seprs = set(seprs)
        self.comps = set(comps)

    def migrate(self):
        if not self.skip_stage1:
            self.do_stage1()
        self.do_stage2()

    def do_stage1(self):
        start_time = time.time()
        last_update = start_time
        logger.debug('Getting row count')
        totalrows = self.core.store.getSize()
        logger.debug('Total row count is %d', totalrows)
        rowcount = 0

        for rows in self.core.store.genStoreRows(gsize=10000):
            rowcount += len(rows)
            now = time.time()
            if last_update + 60 < now:  # pragma: no cover
                last_update = now
                percent_complete = rowcount / totalrows * 100
                timeperrow = (now - start_time) / rowcount
                estimate = int((totalrows - rowcount) * timeperrow)
                logger.info('%02.2f%% complete.  Estimated completion in %ds', percent_complete, estimate)
            with self.dbenv.begin(write=True) as txn:
                rowi = ((_enc_iden(i), s_msgpack.en((p, v))) for i, p, v, _ in rows)
                with txn.cursor(self.iden_tbl) as curs:
                    consumed, added = curs.putmulti(rowi)
                assert consumed == added == len(rows)

                # if prop is tufo:form, and form is a comp, add to form->iden table
                compi = ((v.encode('utf8'), _enc_iden(i)) for i, p, v, _ in rows
                         if p == 'tufo:form' and self.is_comp(v))
                with txn.cursor(self.form_tbl) as curs:
                    consumed, added = curs.putmulti(compi)
                assert consumed == added

        logger.info('Stage 1 complete.')

    def write_node_to_file(self, node):
        self.outfh.write(s_msgpack.en(node))

    def get_props(self, enc_iden, txn):
        '''
        Get all the props from lmdb for an iden
        '''
        with txn.cursor(self.iden_tbl) as curs:
            if not curs.set_key(enc_iden):
                raise Exception('missing iden')
            props = {}
            for pv_enc in curs.iternext_dup():
                p, v = s_msgpack.un(pv_enc)
                props[p] = v
            return props

    def do_stage2(self):
        comp_forms = [f for f in reversed(_comp_and_sepr_forms) if self.is_comp(f)]

        # Do the comp forms
        for formname in comp_forms:
            with self.dbenv.begin(write=True, db=self.form_tbl) as txn:
                curs = txn.cursor(self.form_tbl)
                if not curs.set_key(formname.encode('utf8')):
                    continue
                logger.debug('processing nodes from %s', formname)
                for enc_iden in curs.iternext_dup():
                    props = self.get_props(enc_iden, txn)
                    node = self.convert_props(props)
                    txn.put(props[formname].encode('utf8'), s_msgpack.en(node[0]), db=self.comp_tbl)
                    self.write_node_to_file(node)

        logger.debug('Finished processing comp nodes')

        # Do all the non-comp forms
        with self.dbenv.begin(db=self.iden_tbl) as txn:
            curs = txn.cursor(self.iden_tbl)
            curs.first()
            while True:
                props = {}
                for pv_enc in curs.iternext_dup():
                    p, v = s_msgpack.un(pv_enc)
                    # Skip dark rows or forms we've already done
                    if p[0] == '.' or p[0] == '_' or p == 'tufo:form' and v in comp_forms:
                        rv = curs.next_nodup()
                        break
                    props[p] = v
                else:
                    rv = curs.next()
                    self.write_node_to_file(self.convert_props(props))

                if not rv:
                    break  # end of table

    def just_guid(self, formname, pkval):
        return pkval

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

    primary_prop_special = {
        'inet:web:post': just_guid,
        'it:dev:regval': just_guid,
        'inet:dns:soa': just_guid
    }

    def convert_primary(self, props):
        formname = props['tufo:form']
        pkval = props[formname]
        if formname in self.primary_prop_special:
            return self.primary_prop_special[formname](self, formname, props[formname])
        if self.is_comp(formname):
            return self.convert_comp_primary(props)
        if self.is_sepr(formname):
            return self.convert_sepr(formname, pkval)
        _, val = self.convert_subprop(formname, formname, pkval)
        return val

    def convert_comp_secondary(self, formname, propval):
        ''' Convert secondary prop that is a comp type '''
        with self.dbenv.begin(db=self.comp_tbl) as txn:
            comp_enc = txn.get(propval.encode('utf8'), db=self.comp_tbl)
            if comp_enc is None:
                raise Exception('guid accessed before determined')
            return s_msgpack.un(comp_enc)

    def convert_foreign_key(self, pivot_formname, pivot_fk):
        ''' Convert secondary prop that is a pivot to another node '''
        # logger.debug('convert_foreign_key: %s=%s', pivot_formname, pivot_fk)
        if self.is_comp(pivot_formname):
            return self.convert_comp_secondary(pivot_formname, pivot_fk)

        if self.is_sepr(pivot_formname):
            return self.convert_sepr(pivot_formname, pivot_fk)

        return pivot_fk

    def convert_comp_primary(self, props):
        formname = props['tufo:form']
        compspec = self.core.getPropInfo(formname, 'fields')
        logger.debug('convert_comp_primary_property: %s, %s', formname, compspec)
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
        'inet:ipv4:cc': 'inet:ipv4:loc'
    }

    def ipv4_to_client(self, formname, propname, typename, val):
        return 'client', 'tcp://%s/' % val

    subprop_special = {
        'inet:web:logon:ipv4': ipv4_to_client
    }

    def ip_to_server(self, formname, propname, typename, val):
        _, props = self.core.getTufoByProp(typename, val)
        addr_propname = 'ipv' + typename[-1]
        addr = props[typename + ':' + addr_propname]
        port = props[typename + ':port']
        return propname, '%s://%s:%s/' % (typename[5:8], addr, port)

    type_special = {
        'inet:tcp4': ip_to_server,
        'inet:tcp6': ip_to_server,
        'inet:udp4': ip_to_server,
        'inet:udp6': ip_to_server
    }

    def convert_subprop(self, formname, propname, val):
        typename = self.core.getPropTypeName(propname)

        if propname in self.subprop_special:
            return self.subprop_special[propname](self, formname, propname, typename, val)

        if typename in self.type_special:
            return self.type_special[typename](self, formname, propname, typename, val)

        newpropname = self.prop_renames.get(propname, propname)
        newpropname = newpropname[len(formname) + 1:]

        return newpropname, self.default_subprop_convert(propname, typename, val)

    def convert_props(self, oldprops):
        formname = oldprops['tufo:form']
        props = {}
        tags = {}
        propsmeta = self.core.getSubProps(formname)
        pk = None
        for oldk, oldv in sorted(oldprops.items()):
            propmeta = next((x[1] for x in propsmeta if x[0] == oldk), {})
            if oldk[0] == '#':
                tags[oldk[1:]] = None
            elif oldk[0] == '>':
                start, end = tags.get(oldk[2:], (None, None)) or (None, None)
                start = oldv
                tags[oldk[2:]] = (start, end)
            elif oldk[0] == '<':
                start, end = tags.get(oldk[2:], (None, None)) or (None, None)
                end = oldv
                tags[oldk[2:]] = (start, end)
            elif oldk == formname:
                pk = self.convert_primary(oldprops)
            elif propmeta.get('ro', False):
                # logger.debug('Skipping readonly propname %s', oldk)
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
        assert pk is not None

        retn = ((formname, pk), {'props': props})
        if tags:
            retn[1]['tags'] = tags

        return retn

def main(argv, outp=None):  # pragma: no cover
    p = argparse.ArgumentParser()
    p.add_argument('cortex', help='telepath URL for a cortex to be dumped')
    p.add_argument('outfile', help='file to dump to')
    p.add_argument('--verbose', '-v', action='count', help='Verbose output')
    p.add_argument('--stage-1', help='Start at stage 2 with stage 1 file')
    # p.add_argument('--limit', action='store', type=int, help='max number of tufos per form', default=None)
    # p.add_argument('--form', nargs='+', help='which formnames to dump', default=None)
    # p.add_argument('--tag', help='limit dumping to one tag', default=None)
    opts = p.parse_args(argv)
    if opts.verbose is not None:
        if opts.verbose > 1:
            logger.setLevel(logging.DEBUG)
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
