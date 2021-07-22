import sys
import asyncio
import logging
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

        ret = _dicts(self.t)
        return ret
    #
    # def get(self, path):
    #     ret = self.t
    #     for node in path:
    #         ret = ret.get(node)
    #     return ret

def getOrderedViews(views):
    ret = []
    view2parent = {}
    view2layers = {}
    view2path = {}
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

    root_views = [iden for iden, parent in view2parent.items() if parent is None]
    root_views = sorted(root_views, key=lambda x: len(view2layers.get(x)))

    # For each View, get a mapping of the chain of his parents, if any
    for iden, parent in view2parent.items():

        if iden in root_views:
            continue

        path = (iden,)
        while True:
            if parent is None:
                break
            path = (parent,) + path
            parent = view2parent.get(parent)
        print(f'PATH TO {iden=} => {path=}')
        view2path[iden] = path
        forkTree.add(path)

    for iden in root_views:
        layers = view2layers.get(iden)
        print(iden, layers)

    forkd = forkTree.dicts()

    for iden in root_views:
        ret.append(iden)
        forks = forkd.get(iden, {})
        q = collections.deque(list(forks.items()))
        while q:
            fork, forks = q.popleft()
            ret.append(fork)
            q.extend(list(forks.items()))
    for iden in ret:
        print(iden, view2layers.get(iden))

    assert len(ret) == len(views)
    return ret

async def fixCortexAutoAdds(prox):
    # 0 - Am I a admin?
    # 1 - get view definitions
    # 2 - order views into a list of trees to fix
    # 3 - fix each view in order by lifting all known missing autoadds
    # user_info = await prox.getCellUser()
    # assert user_info.get('admin') is True, "User is not an admin"
    #
    # q = '$list = $lib.list() for $view in $lib.view.list() { $list.append($view.pack()) } return ( $list )'
    # views = await prox.callStorm(q)

    views = data

    view_list = getOrderedViews(views)


async def _main(argv, outp):
    # async with await s_telepath.openurl(argv[0]) as prox:
    #     try:
    #         s_version.reqVersion(prox._getSynVers(), reqver)
    #     except s_exc.BadVersion as e:  # pragma: no cover
    #         valu = s_version.fmtVersion(*e.get('valu'))
    #         outp.printf(f'Proxy version {valu} is outside of the tool supported range ({reqver}).')
    #         return 1
    prox = None
    if await fixCortexAutoAdds(prox):
        return 0
    return 1

async def main(argv, outp=None):  # pragma: no cover

    if outp is None:
        outp = s_output.stdout

    if len(argv) not in (1, 2):
        outp.printf('usage: python -m synapse.tools.aha.list <url> [network name]')
        return 1

    s_common.setlogging(logger, 'WARNING')

    path = s_common.getSynPath('telepath.yaml')
    async with contextlib.AsyncExitStack() as ctx:

        telefini = await s_telepath.loadTeleEnv(path)
        if telefini is not None:
            ctx.push_async_callback(telefini)

        await _main(argv, outp)

    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
