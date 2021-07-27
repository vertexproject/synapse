import sys
import asyncio
import logging
import argparse
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

reqver = '>=2.48.0,<3.0.0'

data = (
    {'iden': '4ac0ac1b218e416e548e9f2c657c7868', 'name': 'default', 'layers': (
        {'name': 'default', 'iden': 'e7e45c3ddcededbe2e69934142444306', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
         'lockmemory': False, 'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},),
     'parent': None, 'creator': '4f84d6c1738f14d981d2bda3686e4021', 'triggers': ()},
    {'iden': 'ef99ece79ead2c4d5e31d6c3af651e70', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': '4ac0ac1b218e416e548e9f2c657c7868', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '2891ca272024fef90077243d07a892e1', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'name': 'default', 'iden': 'e7e45c3ddcededbe2e69934142444306', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
         'lockmemory': False, 'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}),
     'triggers': ()},
    {'iden': 'f97ccaebd788228b25ffc7bc1c753acd', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': '4ac0ac1b218e416e548e9f2c657c7868', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '2ae74fcdc9f1c71b7930fdb06a0c43d6',
         'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'name': 'default', 'iden': 'e7e45c3ddcededbe2e69934142444306',
         'creator': '4f84d6c1738f14d981d2bda3686e4021',
         'lockmemory': False, 'logedits': True, 'readonly': False, 'model:version': (0, 2, 4),
         'totalsize': 110592}),
     'triggers': ()},
    {'iden': 'b4adad091507747e702af95d0c4a5a94', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': 'f97ccaebd788228b25ffc7bc1c753acd', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '6680054164920b9bb03540a4a80411c4', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '2ae74fcdc9f1c71b7930fdb06a0c43d6', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'name': 'default', 'iden': 'e7e45c3ddcededbe2e69934142444306', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
         'lockmemory': False, 'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}),
     'triggers': ()},
    {'iden': '4c15d2c9f0c949fe2435bb9125a6e854', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': 'f97ccaebd788228b25ffc7bc1c753acd', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '6a60113411ed90451495d72fcdc92d6d',
         'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '2ae74fcdc9f1c71b7930fdb06a0c43d6',
         'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'name': 'default', 'iden': 'e7e45c3ddcededbe2e69934142444306',
         'creator': '4f84d6c1738f14d981d2bda3686e4021',
         'lockmemory': False, 'logedits': True, 'readonly': False, 'model:version': (0, 2, 4),
         'totalsize': 110592}),
     'triggers': ()},
    {'iden': 'cfae53943d70e1d2095629ff0905c1e7', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': 'b4adad091507747e702af95d0c4a5a94', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '60871b67ba2b99156cf7ee77286a0c46', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '6680054164920b9bb03540a4a80411c4', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '2ae74fcdc9f1c71b7930fdb06a0c43d6', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'name': 'default', 'iden': 'e7e45c3ddcededbe2e69934142444306', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
         'lockmemory': False, 'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}),
     'triggers': ()},
    {'iden': 'faf5075e3dd15d1a50de218080dbf37b', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'layers': (
         {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4f54f2aff339d30f87644c4d925fce8a',
          'lockmemory': False, 'logedits': True, 'readonly': False, 'model:version': (0, 2, 4),
          'totalsize': 110592},), 'parent': None, 'triggers': ()},
    {'iden': 'ce8452bdb0ae0e50fbeee6a3d80b6090', 'creator': '4f84d6c1738f14d981d2bda3686e4021', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4f54f2aff339d30f87644c4d925fce8a', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'f505478888599b4dff73ca6a307a2f7d', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}), 'parent': None,
     'triggers': ()},
    {'iden': 'f7f2322279fb757565719f2c9f4e821b', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': 'faf5075e3dd15d1a50de218080dbf37b', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '14ffc3fdd1dfdf15139834eee3afae0c',
         'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4f54f2aff339d30f87644c4d925fce8a',
         'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}), 'triggers': ()},
    {'iden': '34040bb9d46e61243578692c9e1dbf19', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': 'ce8452bdb0ae0e50fbeee6a3d80b6090', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'e862c5edbcee98d321935e469547eff6', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4f54f2aff339d30f87644c4d925fce8a', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'f505478888599b4dff73ca6a307a2f7d', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}), 'triggers': ()},
    {'iden': 'faaeed29dde26b6eaaba818a9dd79ce1', 'creator': '4f84d6c1738f14d981d2bda3686e4021', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'b3659a487e6c43887d09f0bfafcbcff6', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4fcab854a265a50472dd06ed1154cb37', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}), 'parent': None,
     'triggers': ()},
    {'iden': '3ea455e4bafac1b1482ee5bbacd4a60f', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'layers': (
         {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4fcab854a265a50472dd06ed1154cb37',
          'lockmemory': False, 'logedits': True, 'readonly': False, 'model:version': (0, 2, 4),
          'totalsize': 110592},
         {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'b3659a487e6c43887d09f0bfafcbcff6',
          'lockmemory': False, 'logedits': True, 'readonly': False, 'model:version': (0, 2, 4),
          'totalsize': 110592}), 'parent': None, 'triggers': ()},
    {'iden': '30709dcb8841bb5283a2843253772d0f', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': '3ea455e4bafac1b1482ee5bbacd4a60f', 'layers': (
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '2caec6b99df3b6d670ad191e0cf28c85', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4fcab854a265a50472dd06ed1154cb37', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'b3659a487e6c43887d09f0bfafcbcff6', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}), 'triggers': ()},
    {'iden': 'cc9d7c4356d6853aa76566adc1ecd953', 'creator': '4f84d6c1738f14d981d2bda3686e4021', 'layers': [
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4f54f2aff339d30f87644c4d925fce8a', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'f505478888599b4dff73ca6a307a2f7d', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '8e85f7d5d7f358b7b37904c8f505f79a', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}], 'parent': None,
     'triggers': []},
    {'iden': '34800f4e58e9ae64dea33118fe90b777', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': 'cc9d7c4356d6853aa76566adc1ecd953', 'layers': [
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '42a5cb0571ecda4e479845759b61a76d', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4f54f2aff339d30f87644c4d925fce8a', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'f505478888599b4dff73ca6a307a2f7d', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '8e85f7d5d7f358b7b37904c8f505f79a', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}], 'triggers': []},
    {'iden': '609b3f398dd7cfcb7581386d8f4299f8', 'creator': '4f84d6c1738f14d981d2bda3686e4021', 'layers': [
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'b3659a487e6c43887d09f0bfafcbcff6', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4fcab854a265a50472dd06ed1154cb37', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'a2e140abdc9d85d57d2bba5d48357cb5', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}], 'parent': None,
     'triggers': []},
    {'iden': 'b53db5dcad29842be5457009244e7971', 'creator': '4f84d6c1738f14d981d2bda3686e4021', 'layers': [
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4f54f2aff339d30f87644c4d925fce8a', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'f505478888599b4dff73ca6a307a2f7d', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '8235a0e19ccde2fad6f037f2615b3bde', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}], 'parent': None,
     'triggers': []},
    {'iden': '9446567b27b71f39671cdd4b890c90ad', 'creator': '4f84d6c1738f14d981d2bda3686e4021',
     'parent': 'b53db5dcad29842be5457009244e7971', 'layers': [
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '882ad43b74f8c0946ada24fcf2076b40', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '4f54f2aff339d30f87644c4d925fce8a', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': 'f505478888599b4dff73ca6a307a2f7d', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592},
        {'creator': '4f84d6c1738f14d981d2bda3686e4021', 'iden': '8235a0e19ccde2fad6f037f2615b3bde', 'lockmemory': False,
         'logedits': True, 'readonly': False, 'model:version': (0, 2, 4), 'totalsize': 110592}], 'triggers': []},

)


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

import collections

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
        outp.printf("User is not an admin")
        return 1

    # Get views and order them
    views = await prox.callStorm(view_query)
    view_list = getOrderedViews(views, outp=outp, debug=debug)

    for view in view_list:
        outp.printf(f'Fixing Missing autoads on view {view}')
        for q in storm_queries:
            opts = {'view': view, 'edits': 'none'}
            outp.printf(f'Executing query: [{q}]')
            if dry_run:
                continue
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
