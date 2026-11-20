import os
import sys
import shutil
import asyncio

import synapse.exc as s_exc
import synapse.cortex as s_cortex

import synapse.lib.modelrev as s_modelrev

import synapse.tools.service.backup as s_backup

import packcell

# inet:url values the 3.2.0 model migration repairs or quarantines. Each is stored by the
# pre-fix 3.x normalizer running under python -O (asserts stripped), which is how the
# Synapse docker images run. The comment on each value describes how it is stored.
COLLAPSE = (
    'http:////foo.com/x',               # known scheme, collapses to http://foo.com/x
    'https://///1.2.3.4:81/x',          # stored https:////1.2.3.4:81/x
    'smb:////s',                        # collapses to smb://s
)

UNKNOWN_SCHEME = (
    'c:////spam////eggs',               # c is a drive letter, not a known scheme
    'dvdnav:////dev/sr1',               # not a registered scheme
    'a:b:////foo.com/x',                # scheme contains a colon
)

FIXPROPS = (
    # the value is valid, but :proto and :host came from the embedded URL
    'http://foo.com/r?u=https:////evil.com/x',
    # as above, and the embedded auth part also set :username
    'http://foo.com/r?u=https:////u@evil.com/x',
)

BROKEN = (
    # :proto came from the embedded URL and the stored value no longer normalizes
    'smb:///.//c:////spam////eggs',
)

NOSCHEME = (
    # no valid scheme before the first ://
    '//www.example.com/submit?url=https://example.org/x',
    '/share?u=http://example.net/a',
    'www.example.com/submit?url=https://example.org/x',
    'mailto:visi@vertex.link?x=http://example.net',
    '1http://example.com',
    # normalizes to file:///foo?x=http://a once the scheme is validated
    'file:/foo?x=http://a',
)

AUTHORITY = (
    'file://user@/x',                   # userinfo and no host
    'http://u:pa#ss@b.example/x',       # the # ends the host, leaving no valid port
    # a # in the userinfo, so :host and :username came from the fragment
    'https://login.example.net#first.last@example.com',
    'https://a.example#u:p@b.example',
    # Windows WebDAV hosts, whose port was stored as an IPv4 host @0.0.x.y
    'file://1.2.3.4@80/t.htm',
    'file://host@SSL@443/x',
    'file://u@host@80/x',
    'file://host@ssl/x',                # no port, the SSL marker is normalized
)

UNTOUCHED = (
    'file://user@host.vertex.link/share/x',  # userinfo and a host, which is valid
    'file:////host/share/x',            # valid UNC file URL
    'FILE://///host2/share/x',          # valid UNC file URL, stored file:////host2/share/x
    'https://good.com/x',
    'git+ssh://vertex.link/x',
    'chrome-extension://vertex.link/x',
)

VALUS = COLLAPSE + UNKNOWN_SCHEME + FIXPROPS + BROKEN + NOSCHEME + AUTHORITY + UNTOUCHED

async def main():

    # The bad values only exist in cortexes which ran the pre-fix inet:url
    # normalizer with asserts stripped, so refuse to run unless that is the case.
    if not sys.flags.optimize:
        mesg = 'This regression cortex MUST be generated with python -O.'
        raise s_exc.BadVersion(mesg=mesg)

    if s_modelrev.maxvers >= (3, 2, 0):
        mesg = f'This regression cortex MUST be generated before model revision 3.2.0, not {s_modelrev.maxvers}.'
        raise s_exc.BadVersion(mesg=mesg, curv=str(s_modelrev.maxvers))

    name = 'model-3.2.0'
    tmpdir = f'/tmp/v/{name}'
    bkupdir = f'/tmp/v/{name}.backup'

    regrdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tarpath = os.path.join(regrdir, 'cortexes', f'{name}.tar.gz')

    shutil.rmtree(tmpdir, ignore_errors=True)
    shutil.rmtree(bkupdir, ignore_errors=True)

    async with await s_cortex.Cortex.anit(tmpdir) as core:

        # The version check alone does not catch a checkout which already carries
        # the SYN-12067 fix, so check the normalizer directly.
        try:
            valu, _ = await core.model.type('inet:url').norm('http:////foo.com/x')
        except s_exc.BadTypeValu:
            valu = None

        if valu != 'http:////foo.com/x':
            mesg = 'This regression cortex MUST be generated with the pre-SYN-12067 inet:url normalizer.'
            raise s_exc.BadVersion(mesg=mesg)

        await core.addTagProp('_score', ('int', {}), {})

        for valu in VALUS:
            nodes = await core.nodes('[ inet:url=$valu ]', opts={'vars': {'valu': valu}})
            print(f'{valu!r} -> {nodes[0].ndef[1]!r} {dict(nodes[0].getProps())}')

        # A fully populated bad node, so the moved node can be checked for tags,
        # tag properties, nodedata, edges in both directions and references.
        await core.nodes('''
            inet:url="http:////foo.com/x"
            [ +#rep.test=(2020, 2021) +#rep.test:_score=10 ]
            $node.data.set(woot, hehe)
            [ <(seen)+ { [ meta:source=9e9a0e4d3e2b4b1e8f0a1c2d3e4f5a6b :name="migration test source" ] } ]
            [ +(refs)> { [ inet:fqdn=vertex.link ] } ]
            [ <(has)+ { [ it:dev:repo=* :name="migration test repo" ] } ]
        ''')

        # Scalar, array and poly references to the collapsing node.
        await core.nodes('''
            inet:url="http:////foo.com/x" $u=$node
            [( doc:report=* :title="scalar ref" :url=$u )]
            [( entity:contact=* :name="array ref" :websites=($u, https://good.com/x) )]
            [( it:av:scan:result=* :signame="poly ref" :target=$u )]
        ''')

        # Comps embedding the collapsing node: one with a tag, one which also embeds a
        # field of another type, one embedding it twice, one embedding two different
        # nodes which both move, and one embedding a node which is quarantined.
        await core.nodes('''
            [ inet:url:redir=("http:////foo.com/x", https://good.com/x) +#redir.one ]
            [ inet:url:redir=("http:////foo.com/x", "http:////foo.com/x") ]
            [ inet:url:redir=("http:////foo.com/x", "smb:////s") ]
            [ inet:url:mirror=("http:////foo.com/x", "c:////spam////eggs") ]
        ''')
        await core.nodes('''
            [ file:bytes=* ] $f=$node
            [( inet:urlfile=("http:////foo.com/x", $f) )]
        ''')
        await core.nodes('''
            [ it:host=* :name="migration test host" ] $h=$node
            [( it:host:hosted:url=($h, "http:////foo.com/x") )]
        ''')

        # A bad node whose collapsed value already exists, with conflicting tag
        # properties and nodedata, so the move has to merge.
        await core.nodes('''
            [ inet:url="http:////exists.com/y" +#rep.test=(2019, 2020) +#rep.test:_score=5 ]
            $node.data.set(woot, bad)
        ''')
        await core.nodes('''
            [ inet:url=http://exists.com/y +#rep.test=(2022, 2023) +#rep.test:_score=7 +#existing ]
            $node.data.set(woot, good)
        ''')

        # References to nodes which are quarantined, so the migration has to clear the
        # scalar and array references and quarantine the comp along with them.
        await core.nodes('''
            inet:url="c:////spam////eggs"
            [ <(seen)+ { meta:source=9e9a0e4d3e2b4b1e8f0a1c2d3e4f5a6b } ]
            $u=$node
            [( doc:report=* :title="queued ref" :url=$u )]
            [( entity:contact=* :name="queued array ref" :websites=($u, https://good.com/x) )]
        ''')
        await core.nodes('[ inet:url:redir=("c:////spam////eggs", https://good.com/x) ]')
        await core.nodes('''
            inet:url="//www.example.com/submit?url=https://example.org/x" $u=$node
            [( doc:report=* :title="noscheme ref" :url=$u )]
        ''')

        # A bad node, a tag and nodedata on an existing bad node, and a tombstone of a
        # base layer tag in a forked view, so the migration covers more than one layer,
        # including a layer which holds no primary value for the node it edits.
        fork = await core.callStorm('''
            $view = $lib.view.get().fork()
            $view.set(name, fork00)
            return($view.iden)
        ''')
        await core.nodes('[ inet:url="https:////fork.com/x" ]', opts={'view': fork})
        await core.nodes('''
            inet:url="http:////foo.com/x"
            [ +#fork.only -#rep.test ]
            $node.data.set(forkdata, yep)
        ''', opts={'view': fork})
        await core.nodes('inet:url="c:////spam////eggs" [ +#fork.queued ]', opts={'view': fork})

        # A bad node, and one which is quarantined, in a layer which is then made read
        # only. Model migrations run in migration mode, so they must still repair it.
        roview = await core.callStorm('''
            $layr = $lib.layer.add()
            $view = $lib.view.add(($layr.iden,))
            $view.set(name, roview)
            return($view.iden)
        ''')
        await core.nodes('[ inet:url="https:////ro.com/x" +#ro.tag ]', opts={'view': roview})
        await core.nodes('[ inet:url="dvdnav:////ro/sr1" +#ro.queued ]', opts={'view': roview})
        await core.callStorm('''
            $view = $lib.view.get($roview)
            $lib.layer.get($view.layers.0.iden).set(readonly, (true))
        ''', opts={'vars': {'roview': roview}})

    s_backup.backup(tmpdir, bkupdir)

    os.makedirs(os.path.dirname(tarpath), exist_ok=True)
    packcell.pack(bkupdir, tarpath)

    # Remove the expanded working copies; only the tar is checked in.
    shutil.rmtree(tmpdir, ignore_errors=True)
    shutil.rmtree(bkupdir, ignore_errors=True)

if __name__ == '__main__':
    asyncio.run(main())
