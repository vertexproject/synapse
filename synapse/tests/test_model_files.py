import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.time as s_time

import synapse.tests.utils as s_t_utils

class FileTest(s_t_utils.SynTest):

    # FIXME decide about exe:packer et al
    # async def test_model_filebytes(self):

    #     async with self.getTestCore() as core:

    #         nodes = await core.nodes('''
    #             [ file:bytes=*
    #                 :exe:packer = {[ it:software=* :name="Visi Packer 31337" ]}
    #                 :exe:compiler = {[ it:software=* :name="Visi Studio 31337" ]}
    #             ]
    #         ''')
    #         self.nn(nodes[0].get('exe:packer'))
    #         self.nn(nodes[0].get('exe:compiler'))
    #         self.len(1, await core.nodes('file:bytes :exe:packer -> it:software +:name="Visi Packer 31337"'))
    #         self.len(1, await core.nodes('file:bytes :exe:compiler -> it:software +:name="Visi Studio 31337"'))

    async def test_model_file_entry(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ file:entry=* :path=foo/000.exe :file=* :seen=2022 ]')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.eq(nodes[0].get('path'), 'foo/000.exe')
            self.nn(nodes[0].get('seen'))
            self.len(1, await core.nodes('file:entry :path -> file:path'))
            self.len(1, await core.nodes('file:entry :file -> file:bytes'))

            nodes = await core.nodes('[ file:exemplar:entry=* :path=foo/001.exe :file={file:bytes} :seen=2022 ]')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.eq(nodes[0].get('path'), 'foo/001.exe')
            self.nn(nodes[0].get('seen'))
            self.len(1, await core.nodes('file:exemplar:entry :path -> file:path'))
            self.len(1, await core.nodes('file:exemplar:entry :file -> file:bytes'))

            nodes = await core.nodes('''[
                file:stored:entry=*
                    :file={file:bytes}
                    :path=foo/002.exe
                    :added=20260126
                    :created=20260126
                    :modified=20260126
                    :accessed=20260126
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.eq(nodes[0].get('path'), 'foo/002.exe')
            self.eq(nodes[0].get('added'), 1769385600000000)
            self.eq(nodes[0].get('created'), 1769385600000000)
            self.eq(nodes[0].get('modified'), 1769385600000000)
            self.eq(nodes[0].get('accessed'), 1769385600000000)
            self.len(1, await core.nodes('file:stored:entry :path -> file:path'))
            self.len(1, await core.nodes('file:stored:entry :file -> file:bytes'))

            nodes = await core.nodes('''[
                file:system:entry=*
                    :host={[ it:host=* ]}
                    :file={file:bytes}
                    :path=foo/003.exe
                    :added=20260126
                    :created=20260126
                    :modified=20260126
                    :accessed=20260126
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('host'))
            self.nn(nodes[0].get('file'))
            self.eq(nodes[0].get('path'), 'foo/003.exe')
            self.eq(nodes[0].get('added'), 1769385600000000)
            self.eq(nodes[0].get('created'), 1769385600000000)
            self.eq(nodes[0].get('modified'), 1769385600000000)
            self.eq(nodes[0].get('accessed'), 1769385600000000)
            self.len(1, await core.nodes('file:system:entry :host -> it:host'))
            self.len(1, await core.nodes('file:system:entry :path -> file:path'))
            self.len(1, await core.nodes('file:system:entry :file -> file:bytes'))

            nodes = await core.nodes('''[
                file:subfile:entry=*
                    :parent={file:bytes}
                    :file={file:bytes}
                    :path=foo/004.exe
                    :added=20260126
                    :created=20260126
                    :modified=20260126
                    :accessed=20260126
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('parent'))
            self.eq(nodes[0].get('path'), 'foo/004.exe')
            self.eq(nodes[0].get('added'), 1769385600000000)
            self.eq(nodes[0].get('created'), 1769385600000000)
            self.eq(nodes[0].get('modified'), 1769385600000000)
            self.eq(nodes[0].get('accessed'), 1769385600000000)
            self.len(1, await core.nodes('file:subfile:entry :path -> file:path'))
            self.len(1, await core.nodes('file:subfile:entry :file -> file:bytes'))
            self.len(1, await core.nodes('file:subfile:entry :parent -> file:bytes'))

            nodes = await core.nodes('''[
                file:archive:entry=*
                    :parent={file:bytes}
                    :file={file:bytes}
                    :path=foo/005.exe
                    :added=20260126
                    :created=20260126
                    :modified=20260126
                    :accessed=20260126
                    :archived:size=200
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('parent'))
            self.eq(nodes[0].get('path'), 'foo/005.exe')
            self.eq(nodes[0].get('added'), 1769385600000000)
            self.eq(nodes[0].get('created'), 1769385600000000)
            self.eq(nodes[0].get('modified'), 1769385600000000)
            self.eq(nodes[0].get('accessed'), 1769385600000000)
            self.eq(nodes[0].get('archived:size'), 200)
            self.len(1, await core.nodes('file:archive:entry :path -> file:path'))
            self.len(1, await core.nodes('file:archive:entry :file -> file:bytes'))
            self.len(1, await core.nodes('file:archive:entry :parent -> file:bytes'))

            nodes = await core.nodes('''[
                file:mime:zip:entry=*
                    :parent={file:bytes}
                    :file={file:bytes}
                    :path=foo/006.exe
                    :added=20260126
                    :created=20260126
                    :modified=20260126
                    :accessed=20260126
                    :archived:size=200
                    :comment=Hiya
                    :extra:posix:uid=0
                    :extra:posix:gid=0
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('parent'))
            self.eq(nodes[0].get('path'), 'foo/006.exe')
            self.eq(nodes[0].get('added'), 1769385600000000)
            self.eq(nodes[0].get('created'), 1769385600000000)
            self.eq(nodes[0].get('modified'), 1769385600000000)
            self.eq(nodes[0].get('accessed'), 1769385600000000)
            self.eq(nodes[0].get('archived:size'), 200)
            self.eq(nodes[0].get('comment'), 'Hiya')
            self.eq(nodes[0].get('extra:posix:uid'), 0)
            self.eq(nodes[0].get('extra:posix:gid'), 0)
            self.len(1, await core.nodes('file:mime:zip:entry :path -> file:path'))
            self.len(1, await core.nodes('file:mime:zip:entry :file -> file:bytes'))
            self.len(1, await core.nodes('file:mime:zip:entry :parent -> file:bytes'))

            self.len(7, await core.nodes('file:bytes -> file:entry:file :path -> file:path | uniq'))

    async def test_model_file_mime_exe(self):
        # test to make sure pe metadata is well formed
        async with self.getTestCore() as core:

            fileiden = s_common.guid()
            exp_time = '201801010233'

            imphash = 'e' * 32
            richheader = 'f' * 64

            q = '''
            [ file:mime:pe=*
                :file=$file
                :imphash=$imphash
                :richheader=$richheader
                :pdbpath=c:/this/is/my/pdbstring
                :exports:time=201801010233
                :exports:libname=ohgood
                :versioninfo=((foo, bar), (baz, faz))

                :packer = {[ it:software=({"name": "foobar"}) ]}
                :compiler = {[ it:software=({"name": "bazfaz"}) ]}
                :packer:name = foobar
                :compiler:name = bazfaz
            ]
            '''
            opts = {'vars': {
                'file': fileiden,
                'imphash': imphash,
                'richheader': richheader,
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('file'), fileiden)
            self.eq(nodes[0].get('imphash'), imphash)
            self.eq(nodes[0].get('richheader'), richheader)
            self.eq(nodes[0].get('pdbpath'), 'c:/this/is/my/pdbstring')
            self.eq(nodes[0].get('exports:time'), 1514773980000000)
            self.eq(nodes[0].get('exports:libname'), 'ohgood')
            self.eq(nodes[0].get('versioninfo'), (('baz', 'faz'), ('foo', 'bar')))
            self.len(2, await core.nodes('file:mime:pe -> file:mime:pe:vsvers:keyval'))

            self.eq(nodes[0].get('packer:name'), 'foobar')
            self.eq(nodes[0].get('compiler:name'), 'bazfaz')
            self.len(1, await core.nodes('file:mime:pe :packer -> it:software'))
            self.len(1, await core.nodes('file:mime:pe :compiler -> it:software'))

            q = '''
            [ file:mime:pe:resource=*
                :file=$file
                :langid=0x409
                :type=2
                :sha256=$sha256
            ]
            '''
            opts = {'vars': {'sha256': 'f' * 64, 'file': fileiden}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('type'), 2)
            self.eq(nodes[0].get('langid'), 0x409)
            self.eq(nodes[0].get('sha256'), 'f' * 64)
            self.eq(nodes[0].get('file'), fileiden)
            self.eq(nodes[0].repr('langid'), 'en-US')
            self.eq(nodes[0].repr('type'), 'RT_BITMAP')

            q = '''
            [ file:mime:pe:section=*
                :file=$file
                :name=wootwoot
                :sha256=$sha256
            ]
            '''
            opts = {'vars': {'sha256': 'f' * 64, 'file': fileiden}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'wootwoot')
            self.eq(nodes[0].get('sha256'), 'f' * 64)
            self.eq(nodes[0].get('file'), fileiden)

            # unknown langid
            nodes = await core.nodes('[file:mime:pe:resource=* :langid=0x1804]')
            self.len(1, nodes)
            rnode = nodes[0]
            self.eq(rnode.get('langid'), 0x1804)

            q = '''
            [ file:mime:pe:export=*
                :file=$file
                :name=WootWoot
                :rva=0x20202020
            ]
            '''
            opts = {'vars': {'file': fileiden}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('rva'), 0x20202020)
            self.eq(nodes[0].get('file'), fileiden)
            self.eq(nodes[0].get('name'), 'WootWoot')

            self.len(1, await core.nodes('file:mime:pe:export -> it:dev:str'))

            # invalid langid
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[file:mime:pe:resource=* :langid=0xfffff]')

            nodes = await core.nodes('''
                [ file:mime:macho=*
                    :file={ file:bytes | limit 1 }
                    :packer = {[ it:software=({"name": "foobar"}) ]}
                    :compiler = {[ it:software=({"name": "bazfaz"}) ]}
                    :packer:name = foobar
                    :compiler:name = bazfaz
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.eq(nodes[0].get('packer:name'), 'foobar')
            self.eq(nodes[0].get('compiler:name'), 'bazfaz')
            self.len(1, await core.nodes('file:mime:macho :packer -> it:software'))
            self.len(1, await core.nodes('file:mime:macho :compiler -> it:software'))

            nodes = await core.nodes('''
                [ file:mime:elf=*
                    :file={ file:bytes | limit 1 }
                    :packer = {[ it:software=({"name": "foobar"}) ]}
                    :compiler = {[ it:software=({"name": "bazfaz"}) ]}
                    :packer:name = foobar
                    :compiler:name = bazfaz
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.eq(nodes[0].get('packer:name'), 'foobar')
            self.eq(nodes[0].get('compiler:name'), 'bazfaz')
            self.len(1, await core.nodes('file:mime:elf :packer -> it:software'))
            self.len(1, await core.nodes('file:mime:elf :compiler -> it:software'))

    async def test_model_filebytes_macho(self):
        async with self.getTestCore() as core:

            fileguid = s_common.guid()
            opts = {'vars': {'file': fileguid}}

            nodes = await core.nodes('''[
                file:mime:macho:loadcmd=*
                    :file=$file
                    :type=27
                    :file:size=123456
            ]''', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('type'), 27)
            self.eq(nodes[0].get('file'), fileguid)
            self.eq(nodes[0].get('file:size'), 123456)

            # uuid
            nodes = await core.nodes('''[
                file:mime:macho:uuid=*
                    :file=$file
                    :type=27
                    :file:size=32
                    :uuid=BCAA4A0BBF703A5DBCF972F39780EB67
            ]''', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('file'), fileguid)
            self.eq(nodes[0].get('file:size'), 32)
            self.eq(nodes[0].get('uuid'), 'bcaa4a0bbf703a5dbcf972f39780eb67')

            # version
            nodes = await core.nodes('''[
                file:mime:macho:version=*
                    :file=$file
                    :file:size=32
                    :type=42
                    :version="7605.1.33.1.4"
            ]''', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('version'), '7605.1.33.1.4')
            self.eq(nodes[0].get('type'), 42)
            self.eq(nodes[0].get('file'), fileguid)
            self.eq(nodes[0].get('file:size'), 32)

            # segment
            seghash = 'e' * 64
            opts = {'vars': {'file': fileguid, 'sha256': seghash}}
            nodes = await core.nodes('''[
                file:mime:macho:segment=*
                    :file=$file
                    :file:size=48
                    :file:offs=1234
                    :type=1
                    :name="__TEXT"
                    :memsize=4092
                    :disksize=8192
                    :sha256=$sha256
            ]''', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('file'), fileguid)
            self.eq(nodes[0].get('type'), 1)
            self.eq(nodes[0].get('file:size'), 48)
            self.eq(nodes[0].get('file:offs'), 1234)
            self.eq(nodes[0].get('name'), '__TEXT')
            self.eq(nodes[0].get('memsize'), 4092)
            self.eq(nodes[0].get('disksize'), 8192)
            self.eq(nodes[0].get('sha256'), seghash)

            # section
            nodes = await core.nodes('''[
                file:mime:macho:section=*
                    :segment={ file:mime:macho:segment }
                    :name="__text"
                    :file:size=12
                    :type=0
                    :file:offs=5678
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('segment'))
            self.eq(nodes[0].get('name'), "__text")
            self.eq(nodes[0].get('type'), 0)
            self.eq(nodes[0].get('file:size'), 12)
            self.eq(nodes[0].get('file:offs'), 5678)

    async def test_model_file_types(self):

        async with self.getTestCore() as core:

            base = core.model.type('file:base')
            path = core.model.type('file:path')

            norm, info = await base.norm('FOO.EXE')
            subs = info.get('subs')

            self.eq('foo.exe', norm)
            self.eq((base.exttype.typehash, 'exe', {}), subs.get('ext'))

            await self.asyncraises(s_exc.BadTypeValu, base.norm('foo/bar.exe'))
            await self.asyncraises(s_exc.BadTypeValu, base.norm('/haha'))

            norm, info = await path.norm('../.././..')
            self.eq(norm, '')

            norm, info = await path.norm('c:\\Windows\\System32\\calc.exe')

            self.eq(norm, 'c:/windows/system32/calc.exe')
            self.eq(info['subs']['dir'][1], 'c:/windows/system32')
            self.eq(info['subs']['base'][1], 'calc.exe')

            norm, info = await path.norm(r'/foo////bar/.././baz.json')
            self.eq(norm, '/foo/baz.json')

            norm, info = await path.norm(r'./hehe/haha')
            self.eq(norm, 'hehe/haha')
            # '.' has no normable value.
            await self.asyncraises(s_exc.BadTypeValu, path.norm('.'))
            await self.asyncraises(s_exc.BadTypeValu, path.norm('..'))

            norm, info = await path.norm('c:')
            self.eq(norm, 'c:')
            subs = info.get('subs')
            self.none(subs.get('ext'))
            self.none(subs.get('dir'))
            self.eq(subs.get('base')[1], 'c:')

            norm, info = await path.norm('/foo')
            self.eq(norm, '/foo')
            subs = info.get('subs')
            self.none(subs.get('ext'))
            self.none(subs.get('dir'))
            self.eq(subs.get('base')[1], 'foo')

            nodes = await core.nodes('[file:path=$valu :seen=2022]', opts={'vars': {'valu': '/foo/bar/baz.exe'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('.base'), 'baz.exe')
            self.eq(node.get('.ext'), 'exe')
            self.eq(node.get('.dir'), '/foo/bar')
            self.nn(node.get('seen'))
            # FIXME virts need to autoadd!
            # self.len(1, await core.nodes('file:path="/foo/bar"'))
            # self.len(1, await core.nodes('file:path^="/foo/bar/b"'))
            # self.len(1, await core.nodes('file:base^=baz'))
            nodes = await core.nodes('[file:path=$valu]', opts={'vars': {'valu': '/'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], '')

            nodes = await core.nodes('[file:path=$valu]', opts={'vars': {'valu': ' /foo/bar'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], '/foo/bar')

            nodes = await core.nodes('[file:path=$valu]', opts={'vars': {'valu': '\\foo\\bar'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], '/foo/bar')

            nodes = await core.nodes('[file:path=$valu]', opts={'vars': {'valu': ' '}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], '')
            self.none(node.get('base'))
            self.none(node.get('base:ext'))
            self.none(node.get('dir'))

            nodes = await core.nodes('[file:path=$valu]', opts={'vars': {'valu': ''}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], '')
            self.none(node.get('base'))
            self.none(node.get('base:ext'))
            self.none(node.get('dir'))

            nodes = await core.nodes('[ file:bytes=* file:bytes=* +(uses)> {[ meta:technique=* ]} ]')
            self.len(2, nodes)

            self.len(1, await core.nodes('[ file:path="c:/www/woah/really" ]'))
            # FIXME virts need to autoadd
            # self.len(1, await core.nodes('file:path="c:/www"'))
            # self.len(1, await core.nodes('file:path=""'))
            # self.len(1, await core.nodes('file:base="sup.exe"'))

    async def test_model_file_mime_msoffice(self):

        async with self.getTestCore() as core:

            fileguid = s_common.guid()
            opts = {'vars': {'fileguid': fileguid}}

            def testmsoffice(n):
                self.eq('lolz', n.get('title'))
                self.eq('deep_value', n.get('author'))
                self.eq('GME stonks', n.get('subject'))
                self.eq('stonktrader3000', n.get('application'))
                self.eq(1611100800000000, n.get('created'))
                self.eq(1611187200000000, n.get('lastsaved'))

                self.eq(fileguid, n.get('file'))
                self.eq(0, n.get('file:offs'))
                self.eq(('foo', 'bar'), n.get('file:data'))

            nodes = await core.nodes('''[
                file:mime:msdoc=*
                    :file=$fileguid
                    :file:offs=0
                    :file:data=(foo, bar)
                    :title=lolz
                    :author=deep_value
                    :subject="GME stonks"
                    :application=stonktrader3000
                    :created=20210120
                    :lastsaved=20210121
            ]''', opts=opts)
            self.len(1, nodes)
            testmsoffice(nodes[0])

            nodes = await core.nodes('''[
                file:mime:msxls=*
                    :file=$fileguid
                    :file:offs=0
                    :file:data=(foo, bar)
                    :title=lolz
                    :author=deep_value
                    :subject="GME stonks"
                    :application=stonktrader3000
                    :created=20210120
                    :lastsaved=20210121
            ]''', opts=opts)
            self.len(1, nodes)
            testmsoffice(nodes[0])

            nodes = await core.nodes('''[
                file:mime:msppt=*
                    :file=$fileguid
                    :file:offs=0
                    :file:data=(foo, bar)
                    :title=lolz
                    :author=deep_value
                    :subject="GME stonks"
                    :application=stonktrader3000
                    :created=20210120
                    :lastsaved=20210121
            ]''', opts=opts)
            self.len(1, nodes)
            testmsoffice(nodes[0])

    async def test_model_file_mime_rtf(self):

        async with self.getTestCore() as core:

            fileguid = s_common.guid()
            opts = {'vars': {'fileguid': fileguid}}

            nodes = await core.nodes('''[
                file:mime:rtf=*
                    :file=$fileguid
                    :file:offs=0
                    :file:data=(foo, bar)
                    :guid=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            ]''', opts=opts)

            self.len(1, nodes)
            self.eq(fileguid, nodes[0].get('file'))
            self.eq(0, nodes[0].get('file:offs'))
            self.eq(('foo', 'bar'), nodes[0].get('file:data'))
            self.eq('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', nodes[0].get('guid'))

    async def test_model_file_meta_exif(self):

        async with self.getTestCore() as core:

            fileguid = s_common.guid()
            conguid = s_common.guid()
            opts = {'vars': {
                        'fileguid': fileguid,
                        'conguid': conguid
                }
            }

            def testexif(n):
                self.eq(fileguid, n.get('file'))
                self.eq(0, n.get('file:offs'))
                self.eq(('foo', 'bar'), n.get('file:data'))
                self.eq('aaaa', n.get('desc'))
                self.eq('bbbb', n.get('comment'))
                self.eq('foo bar', n.get('text'))
                self.eq(1578236238000000, n.get('created'))
                self.eq('a6b4', n.get('id'))
                self.eq(conguid, n.get('author'))
                self.eq((38.9582839, -77.358946), n.get('latlong'))
                self.eq(6371137800, n.get('altitude'))

            nodes = await core.nodes(f'''[
                entity:contact=$conguid
                    :name="Steve Rogers"
                    :title="Captain"
                    :place:address="569 Leaman Place, Brooklyn, NY, 11201, USA"
            ]''', opts=opts)

            props = '''
                :file=$fileguid
                :file:offs=0
                :file:data=(foo, bar)
                :desc=aaaa
                :comment=bbbb
                :text="  Foo   Bar   "
                :created="2020-01-05 14:57:18"
                :id=a6b4
                :author=$conguid
                :latlong="38.9582839,-77.358946"
                :altitude="129 meters"'''

            nodes = await core.nodes(f'''[
                file:mime:jpg=*
                    {props}
            ]''', opts=opts)

            self.len(1, nodes)
            testexif(nodes[0])

            nodes = await core.nodes(f'''[
                file:mime:tif=*
                    {props}
            ]''', opts=opts)

            self.len(1, nodes)
            testexif(nodes[0])

            nodes = await core.nodes(f'''[
                file:mime:gif=*
                    {props}
            ]''', opts=opts)

            self.len(1, nodes)
            testexif(nodes[0])

            nodes = await core.nodes(f'''[
                file:mime:png=*
                    {props}
            ]''', opts=opts)

            self.len(1, nodes)
            testexif(nodes[0])

    async def test_model_file_archive_entry(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ file:archive:entry=*
                    :parent=*
                    :file=*
                    :path=foo/bar.exe
                    :added=20230630
                    :created=20230629
                    :accessed=20230629
                    :modified=20230629
                    :archived:size=999
                ]
            ''')

            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('parent'))

            self.eq(nodes[0].get('added'), 1688083200000000)
            self.eq(nodes[0].get('created'), 1687996800000000)
            self.eq(nodes[0].get('accessed'), 1687996800000000)
            self.eq(nodes[0].get('modified'), 1687996800000000)

            self.len(1, await core.nodes('file:archive:entry :path -> file:path'))
            self.len(1, await core.nodes('file:archive:entry :file -> file:bytes'))
            self.len(1, await core.nodes('file:archive:entry :parent -> file:bytes'))

    async def test_model_file_lnk(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes(r'''[
                file:mime:lnk=*
                    :entry:primary="c:\\some\\stuff\\prog~2\\cmd.exe"
                    :entry:secondary="c:\\some\\stuff\\program files\\cmd.exe"
                    :entry:extended="c:\\some\\actual\\stuff\\I\\swear\\cmd.exe"
                    :entry:localized="c:\\some\\actual\\archivos\\I\\swear\\cmd.exe"
                    :entry:icon="%windir%\\system32\\notepad.exe"

                    :environment:path="%windir%\\system32\\cmd.exe"
                    :environment:icon="%some%%envvar%"
                    :working="%HOMEDRIVE%%HOMEPATH%"
                    :relative="..\\..\\..\\some\\foo.bar.txt"
                    :arguments="/q /c copy %systemroot%\\system32\\msh*.exe"
                    :desc="I've been here the whole time."

                    :flags=0x40df
                    :target:attrs=0x20
                    :target:size=12345
                    :target:created="2023/01/25 18:57:45.284"
                    :target:accessed="2023/01/25 18:57:45.284"
                    :target:written="2023/01/25 18:57:45.284"

                    :driveserial=0x6af54670
                    :machineid=stellarcollapse
                    :iconindex=1
            ]''')
            self.len(1, nodes)
            node = nodes[0]

            self.eq(node.get('entry:primary'), 'c:/some/stuff/prog~2/cmd.exe')
            self.eq(node.get('entry:secondary'), 'c:/some/stuff/program files/cmd.exe')
            self.eq(node.get('entry:extended'), 'c:/some/actual/stuff/i/swear/cmd.exe')
            self.eq(node.get('entry:localized'), 'c:/some/actual/archivos/i/swear/cmd.exe')

            self.eq(node.get('entry:icon'), '%windir%/system32/notepad.exe')
            self.eq(node.get('environment:path'), '%windir%/system32/cmd.exe')
            self.eq(node.get('environment:icon'), '%some%%envvar%')

            self.eq(node.get('working'), '%homedrive%%homepath%')
            self.eq(node.get('relative'), '..\\..\\..\\some\\foo.bar.txt')
            self.eq(node.get('arguments'), '/q /c copy %systemroot%\\system32\\msh*.exe')
            self.eq(node.get('desc'), "I've been here the whole time.")

            self.eq(node.get('flags'), 0x40df)
            self.eq(node.get('target:attrs'), 0x20)
            self.eq(node.get('target:size'), 12345)

            time = 1674673065284000
            self.eq(node.get('target:created'), time)
            self.eq(node.get('target:accessed'), time)
            self.eq(node.get('target:written'), time)

            self.eq(node.get('driveserial'), 0x6af54670)
            self.eq(node.get('machineid'), 'stellarcollapse')
            self.eq(node.get('iconindex'), 1)

            self.len(1, await core.nodes('file:mime:lnk -> it:hostname'))

    async def test_model_file_attachment(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ file:attachment=*
                    :path=Foo/Bar.exe
                    :text="foo bar"
                    :file=*
                    :seen=2022
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.eq(nodes[0].get('text'), 'foo bar')
            self.eq(nodes[0].get('path'), 'foo/bar.exe')
            self.nn(nodes[0].get('seen'))

            self.len(1, await core.nodes('file:attachment -> file:bytes'))
            self.len(1, await core.nodes('file:attachment -> file:path'))
