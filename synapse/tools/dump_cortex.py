import argparse
import logging
import pathlib
import time
from collections import OrderedDict

from typing import Optional, List, Any, Union, Tuple, Dict

import synapse.cortex as s_cortex
import synapse.cores.common as s_common

import synapse.lib.msgpack as s_msgpack
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

TypeType = Union[str, int, Tuple['TypeType', ...]]  # type: ignore
Tufo = Tuple[str, Dict[str, TypeType]]

def membersFromCompSpec(c: str):
    if '=' in c:
        segments = c.split(',')
        kvchar = '='
    else:
        segments = c.split('|')
        kvchar = ','
    return OrderedDict(((k, v) for k, v in (s.split(kvchar) for s in segments)))

def convert_primary_property(core: s_common.Cortex, tufo: Tufo) -> TypeType:
    formname = tufo[1]['tufo:form']
    parent_types = core.getTypeOfs(formname)
    logger.debug(f'convert_primary_property: {formname}, {parent_types}')
    if 'sepr' in parent_types or 'comp' in parent_types:
        return convert_comp_primary_property(core, tufo)
    _, val = convert_subprop(core, formname, formname, tufo[1][formname])
    return val

def convert_foreign_key(core: s_common.Cortex, pivot_formname, pivot_fk: TypeType) -> TypeType:
    ''' Convert field that is a pivot to another node '''
    logger.debug('convert_foreign_key: %s=%s', pivot_formname, pivot_fk)
    pivot_tufo = core.getTufoByProp(pivot_formname, pivot_fk)
    assert pivot_tufo
    new_val = convert_primary_property(core, pivot_tufo)
    return new_val

def convert_comp_primary_property(core, tufo) -> Tuple[Any, ...]:
    formname = tufo[1]['tufo:form']
    compspec = core.getPropInfo(formname, 'fields')
    logger.debug('convert_comp_primary_property: %s, %s', formname, compspec)
    members_dict = membersFromCompSpec(compspec)
    retn = []
    for member in members_dict:
        _, val = convert_subprop(core, formname, member, tufo[1][f'{formname}:{member}'])
        retn.append(val)
    return tuple(retn)

# _TufoConvMap = {
#     'comp': convCompSeprTufo,
#     'sepr': convCompSeprTufo
# }

def default_subprop_convert(core: s_common.Cortex, propname, proptype, val) -> TypeType:
    if proptype != propname and proptype in core.getTufoForms():
        return convert_foreign_key(core, propname, val)
    return val

def convert_subprop(core: s_common.Cortex, formname: str, propname: str, val: Union[str, int]) -> Tuple[str, TypeType]:
    newpropname = propname[len(formname) + 1:]
    _type = core.getPropTypeName(propname)
    # parent_types = core.getTypeOfs(formname)
    # for t in parent_types:
    #     handler = _SubpropConvMap.get(t)
    #     if handler:
    #         return handler(val)
    #         break
    return newpropname, default_subprop_convert(core, propname, _type, val)

def default_convert_tufo(core: s_common.Cortex, tufo: Tufo) -> Tuple[Tuple[str, TypeType], Dict[str, Any]]:
    _, oldprops = tufo
    formname = tufo[1]['tufo:form']
    props = {}
    tags = {}
    propsmeta: List[Tuple[Any, ...]] = core.getSubProps(formname)
    pk = None
    for oldk, oldv in sorted(oldprops.items()):
        propmeta = next((x[1] for x in propsmeta if x[0] == oldk), {})
        if oldk[0] == '#':
            tags[oldk[1:]] = oldv
        elif oldk == formname:
            pk = convert_primary_property(core, tufo)
        elif propmeta.get('ro', False):
            logger.debug('Skipping readonly propname %s', oldk)
            continue
        elif 'defval' in propmeta and oldv == propmeta['defval']:
            logger.debug('Skipping field %s with default value', oldk)
            continue
        elif oldk.startswith(formname + ':'):
            new_pname, newv = convert_subprop(core, formname, oldk, oldv)
            props[new_pname] = newv
        elif oldk == 'node:created':
            props['.created'] = oldv
        else:
            logger.debug('Skipping propname %s', oldk)
    assert pk is not None
    return ((formname, pk), {'props': props, 'tags': tags})


def convert_tufo(core: s_common.Cortex, tufo: Tufo):
    # formname = tufo[0]['tufo:form']
    # handler = _TufoConvMap.get('formname', default_convert_node)
    return default_convert_tufo(core, tufo)


def dumpCortex(core: s_common.Cortex, outdir: pathlib.Path, limit=None, forms=None):
    '''
    Sucks all *tufos* out of a cortex and dumps to a directory with one file per form
    '''
    formlist = core.getTufoForms()
    for i, fnam in enumerate(forms or formlist):
        safe_fnam = fnam.replace(':', '_')
        with (outdir / safe_fnam).with_suffix('.dump').open(mode='wb') as f:
            logger.debug('Starting to dump form %s', fnam)
            start = time.time()

            tufos = core.getTufosByProp('tufo:form', fnam, limit=limit)
            after_query = time.time()
            for t in tufos:
                newt = convert_tufo(core, t)
                f.write(s_msgpack.en(newt))
            finish = time.time()
            if len(tufos):
                logger.debug('Query time: %.2f, write time %.2f, total time %.2f, total/tufo %.4f',
                             after_query - start, finish - after_query, finish - start, (finish - start) / len(tufos))
            logger.info('(%3d/%3d) Dumped %d %s tufos', i + 1, len(forms or formlist), len(tufos), fnam)

def main(argv: List[str], outp: Optional[s_output.OutPut]=None):
    p = argparse.ArgumentParser()
    p.add_argument('cortex', help='telepath URL for a cortex to be dumped')
    p.add_argument('outdir', help='directory in which to place dump files')
    p.add_argument('--verbose', '-v', action='count', help='Verbose output')
    p.add_argument('--limit', action='store', type=int, help='max number of tufos per form', default=None)
    p.add_argument('--form', nargs='+', help='which formnames to dump', default=None)
    opts = p.parse_args(argv)
    if opts.verbose is not None:
        if opts.verbose > 1:
            logger.setLevel(logging.DEBUG)
        elif opts.verbose > 0:
            logger.setLevel(logging.INFO)

    core = s_cortex.openurl(opts.cortex)
    dirpath = pathlib.Path(opts.outdir)
    dirpath.mkdir(parents=True, exist_ok=True)
    dumpCortex(core, dirpath, limit=opts.limit, forms=opts.form)
    return 0

if __name__ == '__main__':  # pragma: no cover
    import sys
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    sys.exit(main(sys.argv[1:]))
