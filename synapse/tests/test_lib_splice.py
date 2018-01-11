from synapse.tests.common import *
import synapse.lib.splice as s_splice


class SpliceTest(SynTest):

    def test_splice(self):

        expected = ('splice', {'mesg': ('foo', {'bar': 'baz', 'faz': 3})})
        actual = s_splice.splice('foo', bar='baz', faz=3)
        self.eq(actual, expected)

        expected = ('splice', {'mesg': ('foo', {})})
        actual = s_splice.splice('foo')
        self.eq(actual, expected)

        oldsplice = ('splice', {'act': 'node:prop:del', 'form': 'strform', 'valu': 'haha', 'prop': 'foo'})
        self.raises(TypeError, s_splice.splice(oldsplice))

        self.raises(TypeError, s_splice.splice(None))

    def test_convertOldSplice(self):

        oldsplice = ('splice', {'act': 'node:prop:del', 'form': 'strform', 'valu': 'haha', 'prop': 'foo'})
        expected = ('splice', {'mesg': ('node:prop:del', {'form': 'strform', 'valu': 'haha', 'prop': 'foo'})})
        actual = s_splice.convertOldSplice(oldsplice)
        self.eq(actual, expected)

        self.none(s_splice.convertOldSplice(None))
        self.none(s_splice.convertOldSplice(1))
        self.none(s_splice.convertOldSplice(('splice', {})))
        self.none(s_splice.convertOldSplice(('splicer', {})))
        self.none(s_splice.convertOldSplice(expected))

    def test_convertSpliceFd(self):

        oldsplicelog = b'\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa3com\xa5props\x82\xa4host\xa3com\xa3sfx\x01\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x05\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa5props\x82\xa4host\xa4woot\xa6domain\xa3com\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x05\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa8newp.com\xa5props\x82\xa4host\xa4newp\xa6domain\xa3com\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x05\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa7syn:tag\xa4valu\xa3foo\xa5props\x80\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xabsyn:tagform\xa4valu\xd9 3170943e0c6252b696418fffbda64b84\xa5props\x82\xa3tag\xa3foo\xa4form\xa9inet:fqdn\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa3tag\xa3foo\xa3act\xacnode:tag:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa7syn:tag\xa4valu\xa7foo.bar\xa5props\x80\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xabsyn:tagform\xa4valu\xd9 673ac84cb06689e6afb8534b5a8d98e6\xa5props\x82\xa3tag\xa7foo.bar\xa4form\xa9inet:fqdn\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa3tag\xa7foo.bar\xa3act\xacnode:tag:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x87\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa3tag\xa7foo.bar\xa4asof\xcf\x00\x00\x01`\xdb\x98$\x06\xa3act\xacnode:tag:del\xa4time\xcf\x00\x00\x01`\xdb\x98$\x07\xa4user\xaeroot@localhost\x92\xa6splice\x85\xa4form\xa9inet:fqdn\xa4valu\xa8newp.com\xa3act\xa8node:del\xa4time\xcf\x00\x00\x01`\xdb\x98$\x07\xa4user\xaeroot@localhost'

        actual = []
        expected = [
            ('node:add', {'form': 'inet:fqdn', 'valu': 'com', 'props': {'host': 'com', 'sfx': 1}, 'time': 1515512669189, 'user': 'root@localhost'}),
            ('node:add', {'form': 'inet:fqdn', 'valu': 'woot.com', 'props': {'host': 'woot', 'domain': 'com'}, 'time': 1515512669189, 'user': 'root@localhost'}),
            ('node:add', {'form': 'inet:fqdn', 'valu': 'newp.com', 'props': {'host': 'newp', 'domain': 'com'}, 'time': 1515512669189, 'user': 'root@localhost'}),
            ('node:add', {'form': 'syn:tag', 'valu': 'foo', 'props': {}, 'time': 1515512669190, 'user': 'root@localhost'}),
            ('node:add', {'form': 'syn:tagform', 'valu': '3170943e0c6252b696418fffbda64b84', 'props': {'tag': 'foo', 'form': 'inet:fqdn'}, 'time': 1515512669190, 'user': 'root@localhost'}),
            ('node:tag:add', {'form': 'inet:fqdn', 'valu': 'woot.com', 'tag': 'foo', 'time': 1515512669190, 'user': 'root@localhost'}),
            ('node:add', {'form': 'syn:tag', 'valu': 'foo.bar', 'props': {}, 'time': 1515512669190, 'user': 'root@localhost'}),
            ('node:add', {'form': 'syn:tagform', 'valu': '673ac84cb06689e6afb8534b5a8d98e6', 'props': {'tag': 'foo.bar', 'form': 'inet:fqdn'}, 'time': 1515512669190, 'user': 'root@localhost'}),
            ('node:tag:add', {'form': 'inet:fqdn', 'valu': 'woot.com', 'tag': 'foo.bar', 'time': 1515512669190, 'user': 'root@localhost'}),
            ('node:tag:del', {'form': 'inet:fqdn', 'valu': 'woot.com', 'tag': 'foo.bar', 'asof': 1515512669190, 'time': 1515512669191, 'user': 'root@localhost'}),
            ('node:del', {'form': 'inet:fqdn', 'valu': 'newp.com', 'time': 1515512669191, 'user': 'root@localhost'}),
        ]

        fname = 'old-savefile.mpk'
        with self.getTestDir() as path:
            fpath = path + '/' + fname

            # Populate and close the file
            with genfile(path, fname) as fd:
                fd.write(oldsplicelog)

            s_splice.convertSpliceFd(fpath)

            with open(fpath, 'rb') as fd:
                [actual.append(chnk) for chnk in s_msgpack.iterfd(fd)]

            self.eq(actual, expected)
