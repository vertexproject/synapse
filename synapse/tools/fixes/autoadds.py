import sys
import asyncio
import logging
import argparse
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

reqver = '>=2.48.0,<3.0.0'


template = '$now=$lib.time.now() {fullprop} $valu={secprop} [{form}=$valu] +{form}.created>=$now | count | spin'
missing_autoadds = (
    ('inet:dns:request:query:name:fqdn', ':query:name:fqdn', 'inet:fqdn',),
    ('inet:dns:request:query:name:ipv4', ':query:name:ipv4', 'inet:ipv4',),
    ('inet:dns:request:query:name:ipv6', ':query:name:ipv6', 'inet:ipv6',),
    ('inet:dns:query:name:fqdn', ':name:fqdn', 'inet:fqdn',),
    ('inet:dns:query:name:ipv4', ':name:ipv4', 'inet:ipv4',),
    ('inet:dns:query:name:ipv6', ':name:ipv6', 'inet:ipv6',),
    ('inet:asnet4:net4:min', ':net4:min', 'inet:ipv4',),
    ('inet:asnet4:net4:max', ':net4:max', 'inet:ipv4',),
    ('inet:asnet6:net6:min', ':net6:min', 'inet:ipv6',),
    ('inet:asnet6:net6:max', ':net6:max', 'inet:ipv6',),
    ('inet:whois:iprec:net4:min', ':net4:min', 'inet:ipv4',),
    ('inet:whois:iprec:net4:max', ':net4:max', 'inet:ipv4',),
    ('inet:whois:iprec:net6:min', ':net6:min', 'inet:ipv6',),
    ('inet:whois:iprec:net6:max', ':net6:max', 'inet:ipv6',),
    ('it:app:snort:hit:src:ipv4', ':src:ipv4', 'inet:ipv4',),
    ('it:app:snort:hit:src:ipv6', ':src:ipv6', 'inet:ipv6',),
    ('it:app:snort:hit:dst:ipv4', ':dst:ipv4', 'inet:ipv4',),
    ('it:app:snort:hit:dst:ipv6', ':dst:ipv6', 'inet:ipv6',),
)

storm_queries = []
for fullprop, secprop, form in missing_autoadds:
    query = template.format(fullprop=fullprop, secprop=secprop, form=form)
    storm_queries.append(query)

view_query = '$list = $lib.list() for $view in $lib.view.list() { $list.append($view.pack()) } return ( $list )'

newview_query = '''
$rootViews = $lib.list()
$view2children = $lib.dict()

for $view in $lib.view.list() {
    $iden=$view.iden
    $parent=$view.parent
    $layers=$lib.list()
    if ( $parent = $lib.null ) {
        $rootViews.append(($lib.len($view.layers), $iden))
    } else {
        if ($view2children.$parent = $lib.null) {
            $_a = $lib.list()
            $_a.append(($lib.len($view.layers), $iden))
            $view2children.$parent = $_a
        } else {
            $_a = $view2children.$parent
            $_a.append(($lib.len($view.layers), $iden))
            $_a.sort()
        }
    }
}

$rootViews.sort()

$absoluteOrder = $lib.list()
for ($_, $view) in $rootViews {
    $absoluteOrder.append($view)
    $children = $view2children.$view
    if $children {
        $todo=$lib.list()
        for ($_, $_child) in $children { $todo.append( $_child) }
        for $child in $todo {
            $absoluteOrder.append($child)
            $_children = $view2children.$child
            if $_children {
                for ($_, $_child) in $_children { $todo.append( $_child) }
            }
        }
    }
}

$queries = ( ${ inet:dns:request:query:name:fqdn $valu=:query:name:fqdn [inet:fqdn=$valu] },
${ inet:dns:request:query:name:ipv4 $valu=:query:name:ipv4 [inet:ipv4=$valu] },
${ inet:dns:request:query:name:ipv6 $valu=:query:name:ipv6 [inet:ipv6=$valu] },
${ inet:dns:query:name:fqdn $valu=:name:fqdn [inet:fqdn=$valu] },
${ inet:dns:query:name:ipv4 $valu=:name:ipv4 [inet:ipv4=$valu] },
${ inet:dns:query:name:ipv6 $valu=:name:ipv6 [inet:ipv6=$valu] },
${ inet:asnet4:net4:min $valu=:net4:min [inet:ipv4=$valu] },
${ inet:asnet4:net4:max $valu=:net4:max [inet:ipv4=$valu] },
${ inet:asnet6:net6:min $valu=:net6:min [inet:ipv6=$valu] },
${ inet:asnet6:net6:max $valu=:net6:max [inet:ipv6=$valu] },
${ inet:whois:iprec:net4:min $valu=:net4:min [inet:ipv4=$valu] },
${ inet:whois:iprec:net4:max $valu=:net4:max [inet:ipv4=$valu] },
${ inet:whois:iprec:net6:min $valu=:net6:min [inet:ipv6=$valu] },
${ inet:whois:iprec:net6:max $valu=:net6:max [inet:ipv6=$valu] },
${ it:app:snort:hit:src:ipv4 $valu=:src:ipv4 [inet:ipv4=$valu] },
${ it:app:snort:hit:src:ipv6 $valu=:src:ipv6 [inet:ipv6=$valu] },
${ it:app:snort:hit:dst:ipv4 $valu=:dst:ipv4 [inet:ipv4=$valu] },
${ it:app:snort:hit:dst:ipv6 $valu=:dst:ipv6 [inet:ipv6=$valu] },)

for $view in $absoluteOrder {
    $lib.print('Fixing data in view {v}', v=$view)
    for $query in $queries {
        // $lib.print('Executing { {q} }', q=$query)
        view.exec $view $query
    }
}

'''

def tree():
    return collections.defaultdict(tree)

class EzTree:
    def __init__(self):
        self.t = tree()

    def add(self, path):
        t = self.t
        for node in path:
            t = t[node]

    def dicts(self):
        def _dicts(t):
            return {k: _dicts(t[k]) for k in t}

        return _dicts(self.t)

def getOrderedViews(views, outp, debug=False):
    ret = []
    view2parent = {}
    view2layers = {}
    forkTree = EzTree()

    # Get all view -> parent and view -> layer mappings
    for view in views:
        iden = view.get('iden')
        parent = view.get('parent')
        view2parent[iden] = parent
        layers = ()
        for layer in view.get('layers'):
            layers = layers + (layer.get('iden'),)
        layers = layers[::-1]
        view2layers[iden] = layers

    root_views = sorted([iden for iden, parent in view2parent.items() if parent is None],
                        key=lambda x: len(view2layers.get(x)))

    # For each View, list of the chain of his parents, if any
    for iden, parent in view2parent.items():

        if iden in root_views:
            continue

        path = (iden,)
        while True:
            if parent is None:
                break
            path = (parent,) + path
            parent = view2parent.get(parent)

        forkTree.add(path)

    forkd = forkTree.dicts()
    # For each view, build a list of his forks and their views
    for iden in root_views:
        ret.append(iden)
        forks = forkd.get(iden, {})
        q = collections.deque(list(forks.items()))
        while q:
            fork, forks = q.popleft()
            ret.append(fork)
            q.extend(list(forks.items()))

    assert len(ret) == len(views), 'The total number of views returned does not match the size of the input.'

    if debug:
        outp.printf('The following Views will be processed:')
        for iden in ret:
            outp.printf(f'View: {iden} Layers: {view2layers.get(iden)}')

    return ret

async def fixCortexAutoAdds(prox, outp, debug=False, dry_run=False):
    # Admin check
    user_info = await prox.getCellUser()
    if not user_info.get('admin'):
        outp.printf("User must be an admin user to execute this script.")
        return 1

    # Get views and order them
    views = await prox.callStorm(view_query)
    view_list = getOrderedViews(views, outp=outp, debug=debug)

    for view in view_list:
        outp.printf(f'Fixing Missing autoads on view {view}')
        for q in storm_queries:
            opts = {'view': view, 'edits': 'none'}
            if dry_run:
                outp.printf(f'Would execute query: [{q}]')

            else:
                outp.printf(f'Executing query: [{q}]')
            async for mesg in prox.storm(q, opts=opts):
                if mesg[0] == 'print':
                    outp.printf(f'Print: {mesg[1].get("mesg")}')
                    continue
                if mesg[0] == 'err':
                    outp.printf(f'ERROR: {mesg[1]}')
                    continue
    return 0

async def _main(argv, outp: s_output.OutPut):
    pars = getArgParser()
    opts = pars.parse_args(argv)
    async with await s_telepath.openurl(opts.url) as prox:
        try:
            s_version.reqVersion(prox._getSynVers(), reqver)
        except s_exc.BadVersion as e:  # pragma: no cover
            valu = s_version.fmtVersion(*e.get('valu'))
            outp.printf(f'Proxy version {valu} is outside of the tool supported range ({reqver}).')
            return 1

        return await fixCortexAutoAdds(prox, outp, debug=opts.debug, dry_run=opts.dry_run)

async def main(argv, outp=None):  # pragma: no cover
    if outp is None:
        outp = s_output.stdout

    s_common.setlogging(logger, 'WARNING')

    path = s_common.getSynPath('telepath.yaml')
    async with contextlib.AsyncExitStack() as ctx:

        telefini = await s_telepath.loadTeleEnv(path)
        if telefini is not None:
            ctx.push_async_callback(telefini)

        return await _main(argv, outp)

def getArgParser():
    desc = 'A tool to fix potentially missing Autoadd nodes from a Cortex.'
    pars = argparse.ArgumentParser(prog='fixes.autoadds00', description=desc)
    pars.add_argument('url', type=str, help='Telepath URL')
    pars.add_argument('--debug', action='store_true', help='Debug output')
    pars.add_argument('--dry-run', action='store_true',
                      help='Do not execut queries, just print what would have been executed.')

    return pars

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
