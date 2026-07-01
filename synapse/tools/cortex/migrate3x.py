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
import synapse.models as s_models
import synapse.datamodel as s_datamodel
import synapse.models.language as s_language

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.cache as s_cache
import synapse.lib.cell as s_cell
import synapse.lib.time as s_time
import synapse.lib.const as s_const
import synapse.lib.layer as s_layer
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.logging as s_logging
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version
import synapse.lib.slabseqn as s_slabseqn
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.multislabseqn as s_multislabseqn

import synapse.tools.service.backup as s_backup

logger = logging.getLogger(__name__)

REQ_2X_CORE_VERS = '>=2.180.1,<3.0.0'

# ============================================================
# Module-level edit transformers (used by EDIT_MIGR dispatch)
#
# All dispatch entries share signature ``(migr, edit)`` so the
# dispatch site does not need to know which entries care about the
# migrator instance. The pure ones ignore ``migr``.
# ============================================================

async def migrIval(migr, ival):
    if ival == (None, None):
        return (None, None, None)
    return (await migr.ivaltype.norm(ival))[0]

async def migrNodeAdd(migr, edit):
    return edit + ({},)

async def migrNodeDel(migr, edit):
    return edit[0]

async def migrPropSet(migr, edit):
    name, valu, oldv, stortype = edit

    if stortype == s_layer.STOR_TYPE_IVAL:
        valu = await migrIval(migr, valu)

    return (name, valu, stortype, {})

async def migrPropDel(migr, edit):
    return edit[0]

async def migrTagSet(migr, edit):
    (tag, valu, oldv) = edit
    valu = await migrIval(migr, valu)
    return (tag, valu)

async def migrTagDel(migr, edit):
    return edit[0]

async def migrTagPropSet(migr, edit):
    tag, name, valu, oldv, stortype = edit

    if stortype == s_layer.STOR_TYPE_IVAL:
        valu = await migrIval(migr, valu)

    return (tag, name, valu, stortype, {})

async def migrTagPropDel(migr, edit):
    return edit[:2]

async def migrNodeDataSet(migr, edit):
    return edit[:2]

async def migrNodeDataDel(migr, edit):
    return edit[0]

async def migrNodeEdge(migr, edit):
    (verb, n2iden) = edit
    n2buid = s_common.uhex(n2iden)
    if (n2nid := migr.getNidByBuid(n2buid)) is None:
        if (newv := migr.migrslab.get(n2buid, db=migr.migrinfo)) is not None:
            n2nid = s_msgpack.un(newv)[0]

    # skip edges to unknown buids
    if n2nid is not None:
        return (verb, s_common.int64un(n2nid))

# ============================================================
# Module-level form/prop migration helpers
#
# Uniform signature ``(migr, valu, opts, edits=None)``. The pure
# normalizers ignore ``migr``; proptoedge uses it.
# ============================================================

async def rename(migr, valu, opts, edits=None):
    return valu, {}

async def renorm(migr, valu, opts, edits=None):
    return await opts['type'].norm(valu)

def _fqdnNeedsDecode(valu):
    # an inet:fqdn value can only carry idna normalization drift if it contains an
    # encoded ('xn--') label; otherwise it is already in canonical form. This lets
    # us skip the decode + renormalize round-trip for the vast majority of values.
    if isinstance(valu, (list, tuple)):
        return any('xn--' in fval for fval in valu)

    return 'xn--' in valu

def _fqdnDecode(fqdntype, valu):
    # decode each ACE (xn--) label back to unicode for renormalization, using the
    # inet:fqdn repr (idna decode with a stdlib fallback). Labels the current idna
    # cannot decode are left untouched: a stored label that no longer decodes is
    # indistinguishable from an opaque value that merely looks like punycode, so
    # decoding it with raw punycode could renormalize a value that was never a real
    # encoding into something else. Leaving it alone matches a fresh norm(), which
    # also keeps such values as-is.
    labels = []
    for label in valu.split('.'):
        if label.startswith('xn--'):
            label = fqdntype.repr(label)

        labels.append(label)

    return '.'.join(labels)

async def fqdndecnorm(migr, valu, opts, edits=None):
    # Decode a stored inet:fqdn value back to unicode and re-normalize it. idna
    # changed how some codepoints normalize, but idna.encode() treats an existing
    # punycode A-label as already valid, so norm() of the stored value alone is a
    # no-op. Decoding first lets the current normalization apply (e.g. stripping
    # default-ignorable codepoints like U+115F). ``opts['type']`` is the destination
    # type used to re-normalize, which may wrap inet:fqdn in an array or poly.
    ftyp = opts['type']
    needsdec = _fqdnNeedsDecode(valu)

    # a scalar value with no encoded label cannot have drifted and needs no
    # reshaping, so pass it straight through. This short circuits the common
    # case of renormalizing every inet:fqdn node in a Cortex.
    if not needsdec and ftyp.stortype == s_layer.STOR_TYPE_FQDN:
        return valu, {}

    fqdntype = migr.model.type('inet:fqdn')

    if isinstance(valu, (list, tuple)):
        valu = [_fqdnDecode(fqdntype, fval) for fval in valu]
    elif needsdec:
        valu = _fqdnDecode(fqdntype, valu)

    return await ftyp.norm(valu)

async def _urldecode(migr, uval):
    # return the url string with its fqdn host's punycode label decoded back to
    # unicode, so a subsequent norm() re-encodes the host under the current idna.
    # The host is the only part of a url that is idna encoded, so we touch only
    # the authority section and leave the path/params untouched.
    urltype = migr.model.type('inet:url')
    fqdntype = migr.model.type('inet:fqdn')

    norm, info = await urltype.norm(uval)

    # the host is stored as a poly 'host' sub: (typehash, (typename, valu), info).
    # only inet:fqdn hosts are idna encoded and can carry drift; skip ip hosts and
    # hostless (e.g. file://) urls.
    hostsub = info['subs'].get('host')
    if hostsub is None:
        return uval

    hosttype, punyhost = hostsub[1]
    if hosttype != 'inet:fqdn' or 'xn--' not in punyhost:
        return uval

    sep = norm.find('://')
    if sep == -1:  # pragma: no cover
        # a successfully normed url always has a proto; defensive only
        return uval

    start = sep + len('://')
    end = len(norm)
    for delim in ('/', '?', '#'):
        idx = norm.find(delim, start)
        if idx != -1 and idx < end:
            end = idx

    # authority is [user[:pass]@]host[:port]; the host follows the last @
    authority = norm[start:end]
    if '@' in authority:
        auth, hostport = authority.rsplit('@', 1)
        auth = f'{auth}@'
    else:
        auth, hostport = '', authority

    # replace only the host within the authority; if the host is somehow absent
    # this is a no-op and the value is renormalized unchanged
    hostport = hostport.replace(punyhost, _fqdnDecode(fqdntype, punyhost), 1)
    return f'{norm[:start]}{auth}{hostport}{norm[end:]}'

async def urldecnorm(migr, valu, opts, edits=None):
    # Re-normalize inet:url values. Like inet:fqdn, the url host is idna encoded,
    # so norm() of a stored value with an existing punycode host is a no-op for
    # the host. We decode the host first (when present) and then re-normalize.
    # norm() is always run since url normalization itself changed between 2.x and
    # 3.x; only the host decode is gated on the presence of an encoded label.
    ftyp = opts['type']

    if isinstance(valu, (list, tuple)):
        valu = [await _urldecode(migr, uval) if 'xn--' in uval else uval for uval in valu]
    elif 'xn--' in valu:
        valu = await _urldecode(migr, valu)

    return await ftyp.norm(valu)

async def toguidnorm(migr, valu, opts, edits=None):
    return await opts['type'].norm((valu,))

async def secstoduration(migr, valu, opts, edits=None):
    # the 2.x value is a TTL in seconds; duration stores microseconds.
    return valu * s_time.onesec, {}

async def currencytocurrencies(migr, valu, opts, edits=None):
    # rename the scalar pol:vitals:currency prop to the pol:vitals:currencies array.
    prop = migr.model.prop('pol:vitals:currencies')
    newvalu, stortype = getNewStorType(migr.model, prop.type, (valu,), None)
    edits.append((s_layer.EDIT_PROP_SET, ('currencies', newvalu, stortype, {})))
    return s_common.novalu, None

async def ipv4norm(migr, valu, opts, edits=None):
    return await opts['type'].norm((4, valu))

async def proptoedge(migr, valu, opts, edits=None):
    # TODO: can we rely on the dest node existing from the first pass and just getNidByBuid?
    if (desttype := opts.get('desttype')) is not None:
        valu = (await desttype.norm(valu))[0]

    destform = opts['destform']
    destbuid = s_common.buid((destform, valu))
    destnid = migr._genIndxNid(destbuid, (destform, valu))
    edits.append((s_layer.EDIT_EDGE_ADD, (opts['verb'], s_common.int64un(destnid))))
    return s_common.novalu, None

async def ipv4proptoedge(migr, valu, opts, edits=None):
    return await proptoedge(migr, (4, valu), opts, edits=edits)

async def arrayproptoedge(migr, valu, opts, edits=None):
    for aval in valu:
        await proptoedge(migr, aval, opts, edits=edits)
    return s_common.novalu, None

async def langtranslation(migr, sode, edits, nodeedits):

    def _propEdit(propname, valu, srcstortype):
        destprop = migr.model.prop(f'lang:translation:{propname}')
        if destprop is None:
            return None
        newvalu, newstor = getNewStorType(migr.model, destprop.type, valu, srcstortype)
        return (s_layer.EDIT_PROP_SET, (propname, newvalu, newstor, {}))

    def _langPropEdit(propname, valu, srcstortype):
        destprop = migr.model.prop(f'lang:language:{propname}')
        if destprop is None:
            return None
        newvalu, newstor = getNewStorType(migr.model, destprop.type, valu, srcstortype)
        return (s_layer.EDIT_PROP_SET, (propname, newvalu, newstor, {}))

    def _normLangCode(code):
        # The 3.x lang:code type is an enforced BCP-47 tag. Translate the 2.x dot
        # separator to the BCP-47 hyphen and normalize to canonical form. Fall back
        # to the raw value if it is not a valid BCP-47 tag so migration never aborts.
        text = code.replace('.', '-')
        if s_language.bcp47re.match(text) is None:
            logger.warning(f'migrate3x: legacy lang:code [{code}] is not a valid BCP-47 tag')
            return code

        return s_language.bcp47recase(text.split('-'))

    if (valu := sode.get('valu')) is not None:
        edits.append((s_layer.EDIT_NODE_ADD, (valu[0], s_layer.STOR_TYPE_GUID, {})))

    props = sode['props']

    if (valu := props.get('input')) is not None:
        if (edit := _propEdit('input', valu[0], valu[1])) is not None:
            edits.append(edit)

    if (valu := props.get('input:lang')) is not None:
        code = _normLangCode(valu[0])
        langguid = s_common.guid(('lang:code', code))
        ndef = ('lang:language', langguid)
        langnid = migr._genIndxNid(s_common.buid(ndef), ndef)

        if (edit := _propEdit('input:lang', langguid, s_layer.STOR_TYPE_GUID)) is not None:
            edits.append(edit)

        subedits = [(s_layer.EDIT_NODE_ADD, (langguid, s_layer.STOR_TYPE_GUID, {}))]
        if (edit := _langPropEdit('code', code, s_layer.STOR_TYPE_UTF8)) is not None:
            subedits.append(edit)
        nodeedits.append((s_common.int64un(langnid), 'lang:language', tuple(subedits)))

    if (valu := props.get('output')) is not None:
        if (edit := _propEdit('output', valu[0], valu[1])) is not None:
            edits.append(edit)

    if (valu := props.get('output:lang')) is not None:
        code = _normLangCode(valu[0])
        langguid = s_common.guid(('lang:code', code))
        ndef = ('lang:language', langguid)
        langnid = migr._genIndxNid(s_common.buid(ndef), ndef)

        if (edit := _propEdit('output:lang', langguid, s_layer.STOR_TYPE_GUID)) is not None:
            edits.append(edit)

        subedits = [(s_layer.EDIT_NODE_ADD, (langguid, s_layer.STOR_TYPE_GUID, {}))]
        if (edit := _langPropEdit('code', code, s_layer.STOR_TYPE_UTF8)) is not None:
            subedits.append(edit)
        nodeedits.append((s_common.int64un(langnid), 'lang:language', tuple(subedits)))

    if (valu := props.get('engine')) is not None:
        if (edit := _propEdit('engine', valu[0], valu[1])) is not None:
            edits.append(edit)

    if (valu := props.get('desc')) is not None:
        if (edit := _propEdit('desc', valu[0], valu[1])) is not None:
            edits.append(edit)

async def repocommentmigr(migr, sode, edits, nodeedits):
    # Fold the 2.x it:dev:repo:issue:comment and it:dev:repo:diff:comment forms
    # into the generic 3.x inet:service:comment form. The :issue / :diff props
    # become the :about commentable reference and the inet:service:object props
    # carry over unchanged. Props which have no inet:service:comment equivalent
    # ( :updated, :line, :offset, :created, :app, :instance ) are intentionally
    # dropped.
    model = migr.model

    if (valt := sode.get('valu')) is not None:
        edits.append((s_layer.EDIT_NODE_ADD, (valt[0], s_layer.STOR_TYPE_GUID, {})))

    props = sode.get('props', {})

    def _emit(name, valu, srcstor):
        destprop = model.prop(f'inet:service:comment:{name}')
        if destprop is None:
            return

        newvalu, stortype = getNewStorType(model, destprop.type, valu, srcstor)
        edits.append((s_layer.EDIT_PROP_SET, (name, newvalu, stortype, {})))

    # the referenced issue/diff becomes the :about commentable poly reference
    for srcname, destform in (('issue', 'it:dev:repo:issue'), ('diff', 'it:dev:repo:diff')):
        if (pval := props.get(srcname)) is not None:
            _emit('about', (destform, pval[0]), s_layer.STOR_TYPE_NDEF)

    # the inet:service:object props carry over to inet:service:comment unchanged
    for name in ('id', 'platform', 'status', 'url', 'period', 'creator', 'remover', 'text', 'replyto'):
        if (pval := props.get(name)) is not None:
            _emit(name, pval[0], pval[1])

async def repolabelmigr(migr, sode, edits, nodeedits):
    # Convert the 2.x it:dev:repo:label form into the generic inet:service:label
    # form. The 2.x :title becomes the :name property.
    model = migr.model

    if (valt := sode.get('valu')) is not None:
        edits.append((s_layer.EDIT_NODE_ADD, (valt[0], s_layer.STOR_TYPE_GUID, {})))

    props = sode.get('props', {})

    def _emit(name, valu, srcstor):
        destprop = model.prop(f'inet:service:label:{name}')
        if destprop is None:
            return

        newvalu, stortype = getNewStorType(model, destprop.type, valu, srcstor)
        edits.append((s_layer.EDIT_PROP_SET, (name, newvalu, stortype, {})))

    if (pval := props.get('title')) is not None:
        _emit('name', pval[0], pval[1])

    for name in ('id', 'desc'):
        if (pval := props.get(name)) is not None:
            _emit(name, pval[0], pval[1])

async def repoissuelabelmigr(migr, sode, edits, nodeedits):
    # Convert the 2.x it:dev:repo:issue:label form into the generic
    # inet:service:labeled form. The :issue becomes the :about labelable
    # reference and :label points at the renamed inet:service:label form. Props
    # with no inet:service:labeled equivalent ( :applied, :removed, :app,
    # :instance ) are intentionally dropped.
    model = migr.model

    if (valt := sode.get('valu')) is not None:
        edits.append((s_layer.EDIT_NODE_ADD, (valt[0], s_layer.STOR_TYPE_GUID, {})))

    props = sode.get('props', {})

    def _emit(name, valu, srcstor):
        destprop = model.prop(f'inet:service:labeled:{name}')
        if destprop is None:
            return

        newvalu, stortype = getNewStorType(model, destprop.type, valu, srcstor)
        edits.append((s_layer.EDIT_PROP_SET, (name, newvalu, stortype, {})))

    # the labeled issue becomes the :about labelable reference
    if (pval := props.get('issue')) is not None:
        _emit('about', ('it:dev:repo:issue', pval[0]), s_layer.STOR_TYPE_NDEF)

    # :label points at the renamed inet:service:label form and the inet:service:object
    # props carry over to inet:service:labeled unchanged
    for name in ('label', 'id', 'platform', 'status', 'url', 'period', 'creator', 'remover'):
        if (pval := props.get(name)) is not None:
            _emit(name, pval[0], pval[1])

# ============================================================
# Pure utilities
# ============================================================

def getNewStorType(model, ptyp, valu, srcstortype):
    '''
    Return (new_valu, new_stortype) for an edit emitted at a destination prop
    whose 3.x type is ptyp.

    ``srcstortype`` indicates the shape of ``valu``:

      - ``STOR_TYPE_NDEF``: 2.x ndef tuple ``(formname, valu)`` - maps
        directly to a 3.x poly ``(typename, valu)`` shape.
      - ``STOR_TYPE_POLY``: caller asserts ``valu`` is already in 3.x
        poly ``(typename, valu)`` shape (e.g. output of a 3.x norm()).
      - any other 2.x stortype: raw scalar value that must be wrapped
        into 3.x poly shape using the destination's default inner type.
    '''
    if ptyp.stortype != s_layer.STOR_TYPE_POLY:
        return (valu, ptyp.stortype)

    if srcstortype in (s_layer.STOR_TYPE_NDEF, s_layer.STOR_TYPE_POLY):
        inner_name, inner_valu = valu
    else:
        defaulttypes = ptyp.opts.get('default_types') or ptyp.opts.get('types')
        inner_name = defaulttypes[0] if defaulttypes else ptyp.name
        inner_valu = valu

    inner_stor = model.type(inner_name).stortype
    return ((inner_name, inner_valu), s_layer.STOR_FLAG_POLY | inner_stor)

def _get2xModel():
    fp = s_assets.getAssetPath('model2x.yaml.gz')
    with s_common.genfile(fp) as fd:
        bytz = fd.read()
        large_bytz = gzip.decompress(bytz)
        ref_modl = s_common.yamlloads(large_bytz)
    return ref_modl['model']

def _migrRulePath(formmigr, propmigr, fullpropmap, path):
    '''
    Generic rule paths, runs first before auth paths.
    '''

    for part in path:
        if '.' in part:
            return

    if len(path) > 2 and path[:2] in (('node', 'add'), ('node', 'del')):
        form = path[2]
        if (fmigr := formmigr.get(form)) is not None:
            if (newform := fmigr[1].get('name')) is not None:
                form = newform

        return path[:2] + (form,)

    elif len(path) > 3 and path[:3] in (('node', 'prop', 'set'), ('node', 'prop', 'del')):
        form = path[3]
        prop = None
        if len(path) == 4:
            if form in fullpropmap:
                (form, prop) = fullpropmap[form]
        else:
            prop = path[4]

        if prop is not None and (finfo := propmigr.get(form)) is not None:
            if (pmigr := finfo.get(prop)) is not None:
                if (newprop := pmigr[1].get('name')) is not None:
                    prop = newprop

        if (fmigr := formmigr.get(form)) is not None:
            if (newform := fmigr[1].get('name')) is not None:
                form = newform

        if prop is not None:
            return path[:3] + (form, prop)
        else:
            return path[:3] + (form,)

    permmigrs = (
        (('auth', 'user', 'pop'), ('auth', 'user', 'del')),
        (('storm', 'lib', 'auth', 'users'), ('auth', 'user')),
        (('storm', 'lib', 'auth', 'roles'), ('auth', 'role')),
        (('storm', 'lib', 'cortex', 'httpapi'), ('httpapi',)),
        (('storm', 'lib', 'log'), ('log',)),
        (('storm', 'inet'), ('inet',)),
        (('cron', 'set', 'creator'), ('cron', 'set', 'user')),
        (('macro', 'add'), ('storm', 'macro', 'add')),
        (('macro', 'edit'), ('storm', 'macro', 'edit')),
        (('macro', 'admin'), ('storm', 'macro', 'admin')),
        (('node', 'data', 'pop'), ('node', 'data', 'del')),
        (('globals', 'pop'), ('globals', 'del')),
        (('storm', 'graph', 'add'), ('graph', 'add')),
    )

    for oldperm, newperm in permmigrs:
        if path[:len(oldperm)] == oldperm:
            return newperm + path[len(oldperm):]

    return path

# ============================================================
# Module-level dispatch tables
# ============================================================

EDIT_MIGR = (
    migrNodeAdd,
    migrNodeDel,
    migrPropSet,
    migrPropDel,
    migrTagSet,
    migrTagDel,
    migrTagPropSet,
    migrTagPropDel,
    migrNodeDataSet,
    migrNodeDataDel,
    migrNodeEdge,
    migrNodeEdge,
)

FORM_MIGR = {
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
    'mat:type': (None, None),

    # the deal status taxonomy was removed in favor of a free-form :status title
    'biz:dealstatus': (None, None),

    # removed taxonomy/forms (3.0 model cleanup)
    'risk:availability': (None, None),
    'belief:subscriber': (None, None),

    # renamed forms
    'biz:dealtype': (rename, {'name': 'biz:deal:type:taxonomy'}),
    'biz:prodtype': (rename, {'name': 'biz:product:type:taxonomy'}),

    'geo:place:taxonomy': (rename, {'name': 'geo:place:type:taxonomy'}),

    'hash:md5': (rename, {'name': 'crypto:hash:md5'}),
    'hash:sha1': (rename, {'name': 'crypto:hash:sha1'}),
    'hash:sha256': (rename, {'name': 'crypto:hash:sha256'}),
    'hash:sha384': (rename, {'name': 'crypto:hash:sha384'}),
    'hash:sha512': (rename, {'name': 'crypto:hash:sha512'}),

    'inet:cidr4': (rename, {'name': 'inet:net'}),
    'inet:cidr6': (rename, {'name': 'inet:net'}),
    'inet:fqdn': (fqdndecnorm, {'name': 'inet:fqdn'}),
    'inet:ipv4': (ipv4norm, {'name': 'inet:ip'}),
    'inet:net4': (rename, {'name': 'inet:net'}),
    'inet:net6': (rename, {'name': 'inet:net'}),
    'inet:url': (urldecnorm, {'name': 'inet:url'}),

    'it:prod:hardwaretype': (rename, {'name': 'it:hardware:type:taxonomy'}),

    'media:news:taxonomy': (rename, {'name': 'doc:report:type:taxonomy'}),

    'meta:event:taxonomy': (rename, {'name': 'meta:event:type:taxonomy'}),
    'meta:timeline:taxonomy': (rename, {'name': 'meta:timeline:type:taxonomy'}),

    'ou:orgtype': (rename, {'name': 'ou:org:type:taxonomy'}),
    'ou:conttype': (rename, {'name': 'doc:contract:type:taxonomy'}),
    'ou:camptype': (rename, {'name': 'entity:campaign:type:taxonomy'}),
    'ou:jobtype': (rename, {'name': 'ou:job:type:taxonomy'}),
    'ou:employment': (rename, {'name': 'ou:employment:type:taxonomy'}),
    'ou:technique:taxonomy': (rename, {'name': 'meta:technique:type:taxonomy'}),

    'ps:contact': (rename, {'name': 'entity:contact'}),

    'risk:attacktype': (rename, {'name': 'risk:attack:type:taxonomy'}),
    'risk:alert:taxonomy': (rename, {'name': 'risk:alert:type:taxonomy'}),
    'risk:compromisetype': (rename, {'name': 'risk:compromise:type:taxonomy'}),
    'risk:tool:software:taxonomy': (rename, {'name': 'it:software:type:taxonomy'}),

    # the repo issue/diff comment forms were folded into the generic
    # inet:service:comment form (see repocommentmigr in FULL_MIGR)
    'it:dev:repo:issue:comment': (rename, {'name': 'inet:service:comment'}),
    'it:dev:repo:diff:comment': (rename, {'name': 'inet:service:comment'}),

    # the repo label forms were generalized into inet:service:label /
    # inet:service:labeled (see repolabelmigr / repoissuelabelmigr in FULL_MIGR)
    'it:dev:repo:label': (rename, {'name': 'inet:service:label'}),
    'it:dev:repo:issue:label': (rename, {'name': 'inet:service:labeled'}),
}

# forms requiring plain renormalization which will not be populated
# automatically. Forms whose normalization needs a decode step (e.g. inet:url,
# inet:fqdn) use TYPE_DECNORM callbacks instead.
FORM_RENORM = ()

# types whose stored values require a decode + renormalize migration because
# their normalization changed, mapped to the migration callback for that type.
# The form and any prop of one of these types (including arrays of it) is migrated
# with its callback so prop values stay consistent with their renormalized nodes.
TYPE_DECNORM = {
    'inet:fqdn': fqdndecnorm,
    'inet:url': urldecnorm,
}

PROP_MIGR = {
    # deleted props
    'inet:email:message:link': {
        'message': (None, None),
    },
    'inet:email:message:attachment': {
        'message': (None, None),
    },
    'ou:campaign': {
        'type': (None, None),
        'camptype': (rename, {'name': 'type'}),
    },
    'ou:contract': {
        'types': (None, None),
    },

    # renamed props
    'ou:opening': {
        'jobtype': (rename, {'name': 'job:type'}),
        'employment': (rename, {'name': 'employment:type'}),
    },
    'ou:org': {
        'orgtype': (rename, {'name': 'type'}),
    },
    'ps:workhist': {
        'jobtype': (rename, {'name': 'job:type'}),
        'employment': (rename, {'name': 'employment:type'}),
    },

    # converted props
    'inet:dns:answer': {
        'ttl': (secstoduration, {}),
    },
    'inet:dns:mx:answer': {
        'ttl': (secstoduration, {}),
    },
    'pol:vitals': {
        'currency': (currencytocurrencies, {}),
    },
    'risk:attack': {
        'target:host': (proptoedge, {'verb': 'targets', 'destform': 'it:host'}),
        'target:org': (proptoedge, {'verb': 'targets', 'destform': 'ou:org'}),
        'techniques': (arrayproptoedge, {'verb': 'uses', 'destform': 'ou:technique'}),
        'via:ipv4': (ipv4proptoedge, {'verb': 'uses', 'destform': 'inet:ip', 'renorm': True}),
        'via:ipv6': (proptoedge, {'verb': 'uses', 'destform': 'inet:ip', 'renorm': True}),
    },
}

FULL_MIGR = {
    'lang:translation': langtranslation,
    'it:dev:repo:issue:comment': repocommentmigr,
    'it:dev:repo:diff:comment': repocommentmigr,
    'it:dev:repo:label': repolabelmigr,
    'it:dev:repo:issue:label': repoissuelabelmigr,
}

class MigrAuth:
    '''
    Helper for migrating auth related data during 2.x.x to 3.x.x migration.
    '''

    def __init__(self, authkv, rulePathFn):
        self.authkv = authkv
        self.rulePathFn = rulePathFn

    def migrate(self):
        self._migrUsers()
        self._migrRoles()

    def _migrUsers(self):
        userkv = self.authkv.getSubKeyVal('user:info:')

        for iden, info in userkv.items():
            updated = False

            valu = info.get('onepass')
            if valu is not None and not isinstance(valu, dict):
                logger.warning(f'Removing deprecated one time password shadow for user {iden}!')
                info.pop('onepass')
                updated = True

            valu = info.get('passwd')
            if valu is not None and not isinstance(valu, dict):
                logger.warning(f'Removing deprecated password shadow for user {iden}!')
                info.pop('passwd')
                updated = True

            self._migrRules(info)
            updated = True

            if updated:
                userkv.set(iden, info)

    def _migrRoles(self):
        rolekv = self.authkv.getSubKeyVal('role:info:')
        for iden, info in rolekv.items():
            self._migrRules(info)
            rolekv.set(iden, info)

    def _migrRules(self, info):
        rules = []
        for allow, path in info.get('rules', ()):
            if (newpath := self._migrRulePath(path)) is not None:
                rules.append((allow, newpath))

        info['rules'] = rules

        for gateiden, gateinfo in list(info.get('authgates').items()):
            rules = []
            for allow, path in gateinfo.get('rules', ()):
                if (newpath := self._migrRulePath(path)) is not None:
                    rules.append((allow, newpath))

            gateinfo['rules'] = rules

    def _migrRulePath(self, path):
        path = self.rulePathFn(path)
        if path is None:
            return None

        if len(path) >= 4 and path[0] == 'auth' and path[1] == 'user' and path[3] == 'profile':
            action = path[2]
            return ('auth', 'user', 'profile', action, *path[4:])

        return path

class Migrator(s_base.Base):
    '''
    Standalone tool for migrating Synapse from a source Cortex to a new destination 3.x.x Cortex.

    migrate() is the primary method which steps through sequential migration steps.

    Auth migration is handled through a standalone class MigrAuth.

    Source 2.x.x data is not modified, and migration can be run as a background operation.

    A migration dir is created to store stats, progress logs, checkpoints, and error logs specific to migration.
    '''
    async def __anit__(self, conf):
        await s_base.Base.__anit__(self)
        self.migrdir = 'migration'

        logger.debug(f'Migrator conf: {conf}')
        self.conf = conf

        self.src = conf.get('src')
        self.dirn = conf.get('dest')

        self.migrtime = s_common.now()

        # data model
        self.model = None
        self.oldmodel = None

        # storage
        self.migrslab = None
        self.migrdb = None
        self.nexsroot = None
        self.cellslab = None

        # mutable per-instance copies of the module-level dispatch tables so
        # _migrDatamodel/_migrExtmodel can append automatic migrations
        self.formmigr = dict(FORM_MIGR)
        self.formrenorm = list(FORM_RENORM)
        self.propmigr = collections.defaultdict(dict)
        for fname, props in PROP_MIGR.items():
            self.propmigr[fname] = dict(props)
        self.fullmigr = dict(FULL_MIGR)

        # auto populated form creations
        self.typetoform = set()

    async def _chkValid(self):
        '''
        Check if the cortex is in a valid state to be migrated.

        Returns:
            (bool): Whether migration can proceed
        '''
        logger.info('Checking that source Cortex is in valid state to be migrated.')
        vld = True

        vers = self.cellinfo.get('cell:version') or (-1, -1, -1)
        await self._migrlogAdd('chkvalid', 'vers', 'src:cortex', vers)

        try:
            s_version.reqVersion(vers, REQ_2X_CORE_VERS)
        except s_exc.BadVersion:
            logger.error(f'Source Cortex does not meet minimum version: req={REQ_2X_CORE_VERS} actual={vers}')
            vld = False

        guidpath = os.path.join(self.dirn, 'cell.guid')
        if not os.path.exists(guidpath):
            logger.error(f'Unable to read cell guid at {guidpath}')
            vld = False
        else:
            with open(guidpath, 'r') as fd:
                self.celliden = fd.read().strip()

        logger.info(f'Completed check of source Cortex state: valid={vld}')

        return vld

    async def migrate(self):
        '''
        Execute the migration as a sequence of named phases.
        '''
        if self.dirn is None:
            raise Exception('Destination dirn must be specified for migration.')

        if not await self._setupDest():
            return

        await self._loadModels()

        # migrate config data after loading the model so we have mappings for node perm migrations
        await self._migrCell()

        await self._buildLayers()
        await self._generateAllNIDs()
        await self._migrNexslog()
        await self._writeLayerData()
        await self._migrViewTriggerQueues()

    async def _setupDest(self):
        '''
        Copy source dirn into dest, open required slabs, and verify the
        source cortex is in a migratable state. Returns ``True`` if migration
        can proceed.
        '''
        await self._migrDirn()
        await self._initStors()
        return await self._chkValid()

    async def _loadModels(self):
        '''
        Load both the bundled 2.x model and the current 3.x model;
        run extended- and auto-datamodel migrations.
        '''
        self.model = s_datamodel.Model()
        self.oldmodel = _get2xModel()

        self.fullpropmap = {}
        for formname, fdef in self.oldmodel['forms'].items():
            for propname in fdef['props'].keys():
                self.fullpropmap[f'{formname}:{propname}'] = (formname, propname)

        mdefs = []
        for path in s_models.modeldefs:
            if (defs := s_dyndeps.getDynLocal(path)) is not None:
                mdefs.extend(defs)
        self.model.addModelDefs(mdefs)

        self.ivaltype = self.model.type('ival')

        await self._migrExtmodel()
        await self._migrDatamodel()

    async def _buildLayers(self):
        '''
        Open Layer objects for every destination layer.
        '''
        self.newlayers = {}
        for iden, layrinfo in self.layrdefs.items():
            layr = await s_layer.Layer.anit(self, layrinfo)
            self.onfini(layr.fini)
            self.newlayers[iden] = layr

    async def _generateAllNIDs(self):
        '''
        Walk every layer's form indexes and allocate destination NIDs.
        '''
        for iden, layr in self.newlayers.items():
            logger.info(f'Generating NIDs for layer {iden}')
            await self._migrLayerBuids(iden, layr)

    async def _writeLayerData(self):
        '''
        Translate sodes from each layer's source data and write them
        as 3.x node edits.
        '''
        dpath = os.path.join(self.dirn, 'slabs', 'nexuslog')
        async with await s_multislabseqn.MultiSlabSeqn.anit(dpath) as dstlog:
            for iden, layr in self.newlayers.items():
                logger.info(f'Migrating data for layer {iden}')
                await self._migrLayer(layr, dstlog)

    async def _migrViewTriggerQueues(self):

        for iden in self.viewdefs.keys():
            path = os.path.join(self.dirn, 'views', iden, 'viewstate.lmdb')

            async with await s_lmdbslab.Slab.anit(path) as viewslab:
                viewslab.dropdb('trigqueue')

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
            self.migrinfo = self.migrslab.initdb('migrinfo')
            self.migrnids = self.migrslab.initdb('migrnids')
            self.onfini(self.migrslab.fini)

        # open cell
        if cell:
            path = os.path.join(self.dirn, 'slabs', 'cell.lmdb')
            if self.cellslab is None:
                self.cellslab = await s_lmdbslab.Slab.anit(path)
            self.onfini(self.cellslab.fini)

        self.cortexdata = self.cellslab.getSafeKeyVal('cortex')
        self.cellinfo = self.cellslab.getSafeKeyVal('cell:info')
        self.layeroffs = await self.cellslab.getHotCount('layeroffs')
        self.viewdefs = self.cortexdata.getSubKeyVal('view:info:')
        self.layrdefs = self.cortexdata.getSubKeyVal('layer:info:')

        v3path = os.path.join(self.dirn, 'slabs', 'layersv3.lmdb')
        self.v3stor = await s_lmdbslab.Slab.anit(v3path)
        self.onfini(self.v3stor.fini)

        self.indxabrv = self.v3stor.getNameAbrv('indxabrv')
        self.nid2ndef = self.v3stor.initdb('nid2ndef')
        self.ndef2nid = self.v3stor.initdb('ndef2nid')

        self.nextnid = 0
        byts = self.v3stor.lastkey(db=self.nid2ndef)
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

    def _migrRulePath(self, path):
        return _migrRulePath(self.formmigr, self.propmigr, self.fullpropmap, path)

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

        authkv = self.cellslab.getSafeKeyVal('auth')

        migrauth = MigrAuth(authkv, self._migrRulePath)
        migrauth.migrate()

        userkv = authkv.getSubKeyVal('user:info:')

        for viewiden in self.viewdefs.keys():
            trigdict = self.cortexdata.getSubKeyVal(f'view:{viewiden}:trigger:')

            for trigiden, tdef in trigdict.items():
                tdef['enabled'] = False

                if tdef.get('creator') is None:
                    tdef['creator'] = tdef['user']

                trigdict.set(trigiden, tdef)

        defview = self.cellinfo.get('defaultview')
        apptdefs = self.cortexdata.getSubKeyVal('agenda:appt:')
        for apptiden, info in apptdefs.items():
            info['ver'] = 2
            info['user'] = info.get('creator')
            info['enabled'] = False

            # 2.x stored these time values as float epoch-seconds; convert to int epoch-micros
            for tkey in ('nexttime', 'laststarttime', 'lastfinishtime'):
                if (tval := info.get(tkey)) is not None:
                    info[tkey] = int(tval * s_time.onesec)

            if (query := info.pop('query')) is not None:
                info['storm'] = query

            if info.get('view') is not None:
                apptdefs.set(apptiden, info)
                continue

            if (userinfo := userkv.get(info['user'])) is None:
                logger.warning(f'CronJob ({apptiden}) has no user or view set and will be removed!')
                apptdefs.delete(apptiden)
                continue

            profilekv = authkv.getSubKeyVal(f'user:{userinfo["iden"]}:profile:')
            info['view'] = profilekv.get('cortex:view', defview)

            apptdefs.set(apptiden, info)

        stormvars = self.cortexdata.getSubKeyVal('storm:vars:')
        for iden, layrinfo in self.layrdefs.items():
            logger.info(f'Migrating layer offsets for {iden}')
            pushs = layrinfo.get('pushs', None)
            pulls = layrinfo.get('pulls', None)
            if pushs:
                for push in pushs:
                    offs = stormvars.pop(f'push:{push}', None)
                    if offs is not None:
                        self.layeroffs.set(push, offs)
            if pulls:
                for pull in pulls:
                    offs = stormvars.pop(f'push:{pull}', None)
                    if offs is not None:
                        self.layeroffs.set(pull, offs)

        for iden, layrinfo in self.layrdefs.items():
            if (mirror := layrinfo.pop('mirror', None)) is not None:
                logger.warning(f'{iden} is a mirror layer which is no longer supported in 3.x')
                self.layrdefs.set(iden, layrinfo)

            if (upstream := layrinfo.pop('upstream', None)) is not None:
                logger.warning(f'{iden} has an upstream layer configured which is no longer supported in 3.x')
                self.layrdefs.set(iden, layrinfo)

        oauth_providers = s_lmdbslab.SlabDict(self.cellslab, db=self.cellslab.initdb('oauth:v2:providers'))
        for iden, conf in oauth_providers.items():
            if (verify := conf.pop('ssl_verify', None)) is not None:
                conf['ssl'] = {'verify': verify}
                oauth_providers.set(iden, conf)

        self._migrStormPkgVers()

        logger.info(f'Completed cell migration, removed deprecated confdefs: {remconfs}')
        await self._migrlogAdd('cell', 'prog', 'none', s_common.now())

    def _migrStormPkgVers(self):
        '''
        Move each storm package's ``storage:version`` from the 2.x package vars
        into the 3.x package state.
        '''
        pkgdefs = self.cortexdata.getSubKeyVal('storm:packages:')
        for name in pkgdefs.keys():
            pkgvars = self.cortexdata.getSubKeyVal(f'stormpkg:vars:{name}:')
            vers = pkgvars.pop('storage:version', defv=s_common.novalu)
            if vers is s_common.novalu:
                continue

            pkgstate = self.cortexdata.getSubKeyVal(f'stormpkg:state:{name}:')
            pkgstate.set('storage:version', vers)

    async def migrNodeEdits(self, nodeedits):

        newnodeedits = []

        for buid, form, edits in nodeedits:
            if (nid := self.getNidByBuid(buid)) is None:
                if form in self.formmigr:
                    if (newv := self.migrslab.get(buid, db=self.migrinfo)) is None:
                        # This is a buid for a migrated form which has no value
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

                if (newedit := await EDIT_MIGR[etyp](self, edit)) is not None:
                    newedits.append((etyp, newedit))

            if newedits:
                newnodeedits.append((s_common.int64un(nid), form, newedits))

        return newnodeedits

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

            kwargs = {}
            meta = None
            etime = self.migrtime

            # Check for entries in nodeeditlogs with offsets before the start of a trimmed nexus log
            if (logstrt := srclog.firstindx) > 0:

                async def wrapgenr(iden, genr):
                    async for offs, realedits in genr:
                        yield offs, realedits, iden
                genrs = [wrapgenr(iden, seqn.aiter(0, wait=False)) for iden, seqn in editlogs.items()]

                async for offs, realedits, iden in s_common.merggenr2(genrs):
                    if offs >= logstrt:
                        break

                    nodeedits, meta = realedits
                    newnodeedits = await self.migrNodeEdits(nodeedits)

                    etime = None
                    if meta is not None:
                        if (etime := meta.get('time')) is None:
                            etime = self.migrtime

                    if newnodeedits:
                        await dstlog.add((iden, 'edits', (newnodeedits, meta), kwargs, meta, etime), indx=offs)

            async for offs, item in s_coro.pause(srclog.iter(0)):
                if item[1] != 'edits':
                    await dstlog.add(item + (None,), indx=offs)
                    continue

                nexsiden, event, args, kwargs, _ = item

                # Skip nonexistent layers
                if (editlog := editlogs.get(nexsiden)) is None:
                    continue

                if (realedits := editlog.get(offs)) is None:
                    continue

                nodeedits, meta = realedits
                newnodeedits = await self.migrNodeEdits(nodeedits)

                etime = None
                if meta is not None:
                    etime = meta.get('time')

                if etime is None:
                    if args and args[1] is not None:
                        etime = args[1].get('time')

                    if etime is None:  # pragma: no cover
                        etime = self.migrtime

                if newnodeedits:
                    await dstlog.add((nexsiden, event, (newnodeedits, meta), kwargs, meta, etime), indx=offs)

            await dstlog.add((self.celliden, 'nexs:vers:set', (s_cell.NEXUS_VERSION,), kwargs, meta, etime))

        for slabseqn in editlogs.values():
            await slabseqn.slab.fini()

    async def _migrDatamodel(self):
        '''
        Generate datamodel migrations from the 2.x model.
        '''
        for name in self.formrenorm:
            form = self.model.form(name)
            opts = {'name': name, 'type': form.type}
            self.formmigr[name] = (renorm, opts)

        # generate automatic form migrations where possible and verify all forms exist
        # or have a migration defined

        nomigr = collections.defaultdict(list)
        for name, fdef in self.oldmodel['forms'].items():

            if name in self.formmigr:
                if (normopts := self.formmigr[name][1]) is not None and 'type' not in normopts:
                    normopts['type'] = self.model.form(normopts['name']).type
                continue

            newname = name

            if (form := self.model.form(name)) is None:
                if (newname := self.model.formprevnames.get(name)) is None:
                    nomigr['forms'].append(name)
                    continue

                form = self.model.form(newname)

            oldt = self.oldmodel['types'].get(name)
            oldopts = s_common.flatten(oldt['opts'])
            newopts = s_common.flatten(form.type.opts)
            if oldopts != newopts or oldt['stortype'] != form.type.stortype:
                opts = {'name': newname, 'type': form.type}
                self.formmigr[name] = (renorm, opts)

        # generate automatic prop migrations where possible and verify all props exist
        # or have a migration defined

        for formname, fdef in self.oldmodel['forms'].items():

            if formname in self.fullmigr:
                continue

            if (migr := self.formmigr.get(formname)) is not None:
                if (migropts := migr[1]) is None:
                    continue
                formname = migropts['name']

            propmigr = self.propmigr.get(formname)

            for propname, pdef in fdef['props'].items():

                if propname[0] == '.':
                    continue

                if propmigr is not None and propname in propmigr:
                    if (normopts := propmigr[propname][1]) is not None:
                        if 'destform' in normopts and normopts.get('renorm'):
                            normopts['desttype'] = self.model.form(normopts['destform']).type
                    continue

                propfull = f'{formname}:{propname}'
                if (prop := self.model.prop(propfull)) is None:
                    if (newpropfull := self.model.propprevnames.get(propfull)) is None:
                        if self.model.prop(formname) is not None:
                            nomigr['props'].append(propfull)
                        continue

                    prop = self.model.prop(newpropfull)

                oldtname, oldtopts = pdef['type']
                if (tmigr := self.formmigr.get(oldtname)) is not None and tmigr[1] is not None:
                    oldtname = tmigr[1]['name']

                # a prop whose 2.x value is a decode+renorm type (e.g. inet:fqdn),
                # including an array of that type, gets that type's decode +
                # renormalize callback so normalization drift is corrected. The
                # destination type may wrap the base type (e.g. a poly or array),
                # which the callback handles by normalizing through prop.type.
                decnormfunc = TYPE_DECNORM.get(oldtname)
                if decnormfunc is None and oldtname == 'array':
                    decnormfunc = TYPE_DECNORM.get(oldtopts.get('type'))

                newtname, newtopts = prop.typedef
                oldtopts = s_common.flatten(oldtopts)
                newtopts = s_common.flatten(newtopts)

                if decnormfunc is not None:
                    opts = {'name': propname, 'type': prop.type, 'oldname': oldtname}
                    self.propmigr[formname][propname] = (decnormfunc, opts)

                elif newtname != oldtname or oldtopts != newtopts:
                    opts = {'name': propname, 'type': prop.type, 'oldname': oldtname}
                    self.propmigr[formname][propname] = (renorm, opts)

        if nomigr:
            if (forms := nomigr.get('forms')) is not None:
                logger.debug(f"Missing forms with no defined migration: {', '.join(sorted(forms))}")

            if (props := nomigr.get('props')) is not None:
                logger.debug(f"Missing props with no defined migration: {', '.join(sorted(props))}")

            # TODO: this check should raise an exception once all migrations are implemented

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
                mesg = f'The extended form {formname} is using a deprecated type {basetype} and will be removed.'
                logger.warning(mesg)
                continue

            try:
                self.model.addType(formname, basetype, typeopts, typeinfo)
                form = self.model.addForm(formname, {}, ())
            except Exception as e:
                logger.warning(f'Extended form ({formname}) error: {e}')

        for formname in self.remforms:
            self.extforms.pop(formname)

        for full, (form, prop, tdef, info) in self.extprops.items():
            if bool(info.get('deprecated', False)):
                self.remprops.add(full)
                mesg = f'The extended property {form}:{prop} is using a deprecated type {tdef[0]} and will be removed.'
                logger.warning(mesg)
                continue

            try:
                self.model.addFormProp(form, prop, tdef, info)
                self.fullpropmap[f'{form}:{prop}'] = (form, prop)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:  # pragma: no cover
                logger.warning(f'ext prop ({form}:{prop}) error: {e}')

        for full in self.remprops:
            self.extprops.pop(full)

        for prop, tdef, info in self.extunivs.values():
            mesg = f'Universal props are no longer supported, extended property {prop} will be removed.'
            logger.warning(mesg)
            continue

        for prop, tdef, info in self.exttagprops.values():
            try:
                self.model.addTagProp(prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:  # pragma: no cover
                logger.warning(f'ext tag prop ({prop}) error: {e}')

        logger.info('Completed extended datamodel migration')
        await self._migrlogAdd('dmodel', 'prog', 'none', s_common.now())

    def _genIndxNid(self, buid, ndef):
        if (nid := self.v3stor.get(buid, db=self.ndef2nid)) is not None:
            return nid

        nid = s_common.int64en(self.nextnid)
        self.nextnid += 1

        self.v3stor._put(nid, s_msgpack.en(ndef), db=self.nid2ndef)
        self.v3stor._put(buid, nid, db=self.ndef2nid)

        return nid

    def _genBuidNid(self, buid):
        '''
        Generate an NID for a buid with no ndef which may be later populated when the
        node is added via setNidNdef.
        '''
        nid = s_common.int64en(self.nextnid)
        self.nextnid += 1

        self.v3stor._put(buid, nid, db=self.ndef2nid)

        return nid

    def setNidNdef(self, nid, ndef):
        self.v3stor._put(s_common.buid(ndef), nid, db=self.ndef2nid)
        self.v3stor._put(nid, s_msgpack.en(ndef), db=self.nid2ndef)

        if (n := s_common.int64un(nid)) >= self.nextnid:
            self.nextnid = n + 1

    def getNidByBuid(self, buid):
        return self.v3stor.get(buid, db=self.ndef2nid)

    def hasNidNdef(self, nid):
        return self.v3stor.has(nid, db=self.nid2ndef)

    def getNidNdef(self, nid):
        if (byts := self.v3stor.get(nid, db=self.nid2ndef)) is not None:
            return s_msgpack.un(byts)

    @s_cache.memoizemethod()
    def getAbrvIndx(self, abrv):
        byts = self.indxabrv.abrvToByts(abrv)
        return s_msgpack.un(byts[2:])

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
                        logger.warning(f'Missing migration for {form}, nodes will not be migrated!')
                        continue

                else:
                    fdef = self.extforms.get(form)
                    if fdef is not None:
                        ftyp = self.model.type(fdef[1])
                        if ftyp is None:
                            logger.warning(f"Extended model form {form} is using deprecated type and will not be migrated")
                            continue

                        if ftyp.stortype > len(newlayr.stortypes) + 1:
                            logger.warning(f"Form {form} is using an invalid stortype={ftyp.stortype} and will not be migrated")
                            continue

                        stor = newlayr.stortypes[ftyp.stortype]

                abrvlen = len(abrv)

                async for lkey, buid in s_coro.pause(layrslab.scanByPref(abrv, db=byprop)):

                    if self.getNidByBuid(buid) is not None:
                        continue

                    indx = lkey[abrvlen:]
                    try:
                        valu = stor.decodeIndx(indx)
                    except Exception as e:
                        logger.warning(f'Failed to decode prop index for {form}={lkey}: {e}')
                        valu = s_common.novalu

                    if valu is s_common.novalu:

                        if (byts := layrslab.get(buid, db=bybuidv3)) is None:
                            logger.warning(f'Invalid prop index value {lkey}:{buid}')
                            continue

                        sode = s_msgpack.un(byts)
                        if (valu := sode.get('valu')) is not None:
                            valu = valu[0]

                    if migr is not None:
                        try:
                            valu, norminfo = await migrfunc(self, valu, migropts)
                        except Exception as e:
                            logger.warning(f'Failed to migrate value for {form}={valu}: {e}')
                            continue

                        newbuid = s_common.buid((newform, valu))
                        nid = self._genIndxNid(newbuid, (newform, valu))

                        if newbuid != buid:
                            migv = s_msgpack.en((nid, newbuid, newform, valu, norminfo))
                            self.migrslab._put(buid, migv, db=self.migrinfo)
                            self.migrslab._put(nid, b'\x01', db=self.migrnids)
                    else:
                        self._genIndxNid(buid, (newform, valu))

    @s_cache.memoizemethod()
    def setIndxAbrv(self, indx, *args):
        return self.indxabrv.setBytsToAbrv(indx + s_msgpack.en(args))

    @s_cache.memoizemethod()
    def getIndxAbrv(self, indx, *args):
        return self.indxabrv.bytsToAbrv(indx + s_msgpack.en(args))

    def checkFreeSpace(self):
        pass

    async def _migrLayer(self, layr, dstlog):

        meta = {'time': self.migrtime}
        async for nodeedits in self.translateLayerNodeEdits(layr, dstlog):
            await layr._storNodeEdits(nodeedits, meta, None)

    async def translateLayerNodeEdits(self, layr, dstlog=None):
        '''
        Scan the full layer and yield artificial sets of nodeedits in 3.x format.

        Any edits which represent a value change made by the migration ( as opposed to a
        faithful reproduction of the 2.x data ) are also appended to the destination nexus
        log so the history of a node may be followed by its nid to see how it ended up in
        its current 3.x state.
        '''
        iden = layr.iden
        path = os.path.join(self.src, 'layers', iden, 'layer_v2.lmdb')
        nodedatapath = os.path.join(self.src, 'layers', iden, 'nodedata.lmdb')
        layrkey = s_common.uhex(iden)

        nexsmeta = {'time': self.migrtime}

        async def emitMigrEdits(migrnodeedits):
            # migrnodeedits: a nodeedits list [(nid, form, edits), ...]
            if dstlog is not None and migrnodeedits:
                await dstlog.add((iden, 'edits', (migrnodeedits, nexsmeta), {}, nexsmeta, nexsmeta['time']))

        async with await s_lmdbslab.Slab.anit(path) as layrslab, \
                   await s_lmdbslab.Slab.anit(nodedatapath) as dataslab:

            byprop = layrslab.initdb('byprop', dupsort=True)
            edgesn1 = layrslab.initdb('edgesn1', dupsort=True)
            bybuidv3 = layrslab.initdb('bybuidv3')
            nodedata = dataslab.initdb('nodedata')
            propabrv = layrslab.getNameAbrv('propabrv')

            migrsubs = set()

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
                migr = None
                newform = form

                if (nid := self.getNidByBuid(buid)) is None:
                    if (migr := self.formmigr.get(form)) is not None:
                        if migr[0] is None:
                            continue

                        if (newv := self.migrslab.get(buid, db=self.migrinfo)) is not None:
                            (nid, _, newform, valu, norminfo) = s_msgpack.un(newv)
                        else:
                            # this is a buid for a migrated form which has no value
                            # in any layers so we cannot compute the new buid
                            logger.warning(f'No migration defined for {form} buid={buid.hex()}')
                            self.migrslab._put(buid + layrkey, byts, db=self.unkbuids)
                            continue

                    else:
                        nid = self._genBuidNid(buid)

                edits = []
                nodeedits = [(s_common.int64un(nid), newform, edits)]
                migredits = []
                migrsubs.clear()

                if (fullmigr := self.fullmigr.get(form)) is not None:
                    await fullmigr(self, sode, edits, nodeedits)

                    migredits.extend(edits)
                    for extra in nodeedits[1:]:
                        await emitMigrEdits([extra])

                else:
                    if valt is not None:
                        if (ftyp := self.model.type(newform)) is None:
                            logger.warning(f'Unknown form {newform} in layer {iden}')
                            continue

                        valu, stortype = getNewStorType(self.model, ftyp, valu, valt[1])

                        virts = None if migr is None else norminfo.get('virts')

                        nodeadd = (s_layer.EDIT_NODE_ADD, (valu, stortype, virts))
                        edits.append(nodeadd)

                        # the node value was renormed by the migration
                        if migr is not None:
                            migredits.append(nodeadd)

                        if migr is not None and (subs := norminfo.get('subs')) is not None:
                            for subn, subv in subs.items():
                                migrsubs.add(subn)
                                subprop = self.model.prop(f'{newform}:{subn}')
                                if subprop is None:
                                    continue
                                # most subs from 3.x norm() carry a raw scalar value to be
                                # wrapped, but a sub whose typehash matches the prop type is
                                # already in the prop's native (poly) shape (e.g.
                                # inet:url:host -> (typename, valu)) and must not be rewrapped.
                                if subprop.type.ispoly and subv[0] == subprop.type.typehash:
                                    srcstor = s_layer.STOR_TYPE_POLY
                                else:
                                    srcstor = None
                                subv1, substortype = getNewStorType(self.model, subprop.type, subv[1], srcstor)
                                subedit = (s_layer.EDIT_PROP_SET, (subn, subv1, substortype, {}))
                                edits.append(subedit)
                                migredits.append(subedit)

                    propmigr = self.propmigr.get(form)
                    for prop, (valu, stortype) in sode.get('props', {}).items():
                        if prop in migrsubs:
                            continue

                        srcvalu, srcstor = valu, stortype
                        edgestart = len(edits)

                        ptyp = None

                        if propmigr and (pmig := propmigr.get(prop)) is not None:
                            (pmigfunc, pmigopts) = pmig
                            if pmigfunc is None:
                                continue

                            origvalu = valu

                            try:
                                valu, norminfo = await pmigfunc(self, valu, pmigopts, edits=edits)
                            except Exception as e:
                                logger.warning(f'Failed to migrate value for {form}:{prop}={valu}: {e}')
                                continue

                            if valu is s_common.novalu:
                                # the prop was converted to one or more edges by the migration
                                migredits.extend(edits[edgestart:])
                                continue

                            if (newtype := pmigopts.get('type')) is not None:
                                ptyp = newtype
                                stortype = newtype.stortype

                                if newtype.stortype == s_layer.STOR_TYPE_POLY:
                                    addformname, addformvalu = valu

                                    oldname = pmigopts.get('oldname')
                                    unchanged = (oldname == addformname and origvalu == addformvalu)

                                    if not unchanged and self.model.form(addformname) is not None:
                                        addformtype = self.model.form(addformname).type
                                        addbuid = s_common.buid((addformname, addformvalu))
                                        addnid = self._genIndxNid(addbuid, (addformname, addformvalu))
                                        addvalu, addstor = getNewStorType(self.model, addformtype, addformvalu, addformtype.stortype)
                                        addedit = (s_layer.EDIT_NODE_ADD, (addvalu, addstor, {}))
                                        addnodeedits = [(s_common.int64un(addnid), addformname, (addedit,))]
                                        # the referenced node was created by the migration
                                        await emitMigrEdits(addnodeedits)
                                        yield addnodeedits

                        elif stortype == s_layer.STOR_TYPE_NDEF:
                            (nform, nvalu) = valu
                            if (migr := self.formmigr.get(nform)) is not None:
                                (migrfunc, migropts) = migr
                                try:
                                    valu = (migropts['name'], (await migrfunc(self, nvalu, migropts, edits=edits))[0])
                                except Exception as e:
                                    logger.warning(f'Failed to migrate value for {form}:{prop}={valu}: {e}')
                                    continue

                        if ptyp is None:
                            destprop = self.model.prop(f'{newform}:{prop}')
                            if destprop is not None:
                                ptyp = destprop.type

                        if ptyp is not None:
                            valu, stortype = getNewStorType(self.model, ptyp, valu, stortype)

                        propedit = (s_layer.EDIT_PROP_SET, (prop, valu, stortype, {}))
                        edits.append(propedit)

                        # record the prop only if the migration changed its value or stortype
                        if (valu, stortype) != (srcvalu, srcstor):
                            migredits.append(propedit)

                for tag, tagv in sode.get('tags', {}).items():
                    tagv = await migrIval(self, tagv)
                    edits.append((s_layer.EDIT_TAG_SET, (tag, tagv)))

                for tag, propdict in sode.get('tagprops', {}).items():
                    for prop, (valu, stortype) in propdict.items():
                        edits.append((s_layer.EDIT_TAGPROP_SET, (tag, prop, valu, stortype, {})))

                for lkey, byts in dataslab.scanByPref(buid, db=nodedata):
                    valu = s_msgpack.un(byts)
                    prop = s_msgpack.un(propabrv.abrvToByts(lkey[32:]))

                    edits.append((s_layer.EDIT_NODEDATA_SET, (prop[0], valu)))

                for lkey, n2buid in layrslab.scanByPref(buid, db=edgesn1):
                    verb = lkey[32:].decode()

                    if (n2nid := self.getNidByBuid(n2buid)) is None:
                        if (newv := self.migrslab.get(n2buid, db=self.migrinfo)) is None:
                            continue
                        (n2nid, _, n2form, _, _) = s_msgpack.un(newv)
                    else:
                        n2ndef = self.getNidNdef(n2nid)
                        if n2ndef is None:
                            # n2 buid was reserved via _genBuidNid but the ndef
                            # has not yet been recorded; skip this edge.
                            continue
                        n2form = n2ndef[0]

                    if not self.model.edgeIsValid(newform, verb, n2form):
                        if verb[0] != '_':
                            verb = '_' + verb

                        if not self.model.edgeIsValid(newform, verb, n2form):
                            edge = (None, verb, None)
                            edgeinfo = {'doc': 'Automatically added during 3.0.0 migration.'}
                            self.model.addEdge(edge, edgeinfo)
                            self.extedges.set(s_common.guid(edge), (edge, edgeinfo))

                    edits.append((s_layer.EDIT_EDGE_ADD, (verb, s_common.int64un(n2nid))))

                if self.migrslab.get(nid, db=self.migrnids) is not None:
                    realedits = await layr.calcEdits(nodeedits, {})
                    # the primary value changed enough to change the buid, so the whole
                    # node is a migration change recorded under its new nid
                    await emitMigrEdits(realedits)
                    yield realedits
                    continue

                if migredits:
                    await emitMigrEdits([(nodeedits[0][0], newform, migredits)])

                yield nodeedits

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

            self.migrslab._put(lkey, lval, overwrite=True, db=self.migrdb)

        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception:  # pragma: no cover
            logger.exception(f'Unable to store migration log: {migrop}; {logtyp}; {key}; {val}')

async def main(argv, outp=s_output.stdout):
    desc = 'Tool for migrating Synapse Cortex storage from 2.x.x to 3.x.x'
    pars = argparse.ArgumentParser(prog='synapse.tools.migrate3x', description=desc)

    pars.add_argument('--src', required=True, type=str, help='Source cortex dirn to migrate from.')
    pars.add_argument('--dest', required=False, type=str, help='Destination cortex dirn to migrate to.')
    pars.add_argument('--log-level', required=False, default='info', choices=s_const.LOG_LEVEL_CHOICES,
                      help='Specify the log level', type=str.upper)

    opts = pars.parse_args(argv)

    s_logging.setup(level=opts.log_level)

    dest = opts.dest

    conf = {
        'src': opts.src,
        'dest': dest,
    }

    migr = await Migrator.anit(conf=conf)

    try:
        await migr.migrate()
        return migr

    finally:
        await migr.fini()

if __name__ == '__main__':  # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
