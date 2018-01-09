from synapse.tests.common import *
import synapse.lib.splice as s_splice

oldsplicelog = b'\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa3com\xa5props\x82\xa4host\xa3com\xa3sfx\x01\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x05\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa5props\x82\xa4host\xa4woot\xa6domain\xa3com\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x05\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa8newp.com\xa5props\x82\xa4host\xa4newp\xa6domain\xa3com\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x05\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa7syn:tag\xa4valu\xa3foo\xa5props\x80\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xabsyn:tagform\xa4valu\xd9 3170943e0c6252b696418fffbda64b84\xa5props\x82\xa3tag\xa3foo\xa4form\xa9inet:fqdn\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa3tag\xa3foo\xa3act\xacnode:tag:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa7syn:tag\xa4valu\xa7foo.bar\xa5props\x80\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xabsyn:tagform\xa4valu\xd9 673ac84cb06689e6afb8534b5a8d98e6\xa5props\x82\xa3tag\xa7foo.bar\xa4form\xa9inet:fqdn\xa3act\xa8node:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x86\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa3tag\xa7foo.bar\xa3act\xacnode:tag:add\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa6splice\x87\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa3tag\xa7foo.bar\xa4asof\xcf\x00\x00\x01`\xdb\x98$\x06\xa3act\xacnode:tag:del\xa4time\xcf\x00\x00\x01`\xdb\x98$\x07\xa4user\xaeroot@localhost\x92\xa6splice\x85\xa4form\xa9inet:fqdn\xa4valu\xa8newp.com\xa3act\xa8node:del\xa4time\xcf\x00\x00\x01`\xdb\x98$\x07\xa4user\xaeroot@localhost'

newsplicelog = b'\x92\xa8node:add\x85\xa4form\xa9inet:fqdn\xa4valu\xa3com\xa5props\x82\xa4host\xa3com\xa3sfx\x01\xa4time\xcf\x00\x00\x01`\xdb\x98$\x05\xa4user\xaeroot@localhost\x92\xa8node:add\x85\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa5props\x82\xa4host\xa4woot\xa6domain\xa3com\xa4time\xcf\x00\x00\x01`\xdb\x98$\x05\xa4user\xaeroot@localhost\x92\xa8node:add\x85\xa4form\xa9inet:fqdn\xa4valu\xa8newp.com\xa5props\x82\xa4host\xa4newp\xa6domain\xa3com\xa4time\xcf\x00\x00\x01`\xdb\x98$\x05\xa4user\xaeroot@localhost\x92\xa8node:add\x85\xa4form\xa7syn:tag\xa4valu\xa3foo\xa5props\x80\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa8node:add\x85\xa4form\xabsyn:tagform\xa4valu\xd9 3170943e0c6252b696418fffbda64b84\xa5props\x82\xa3tag\xa3foo\xa4form\xa9inet:fqdn\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xacnode:tag:add\x85\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa3tag\xa3foo\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa8node:add\x85\xa4form\xa7syn:tag\xa4valu\xa7foo.bar\xa5props\x80\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xa8node:add\x85\xa4form\xabsyn:tagform\xa4valu\xd9 673ac84cb06689e6afb8534b5a8d98e6\xa5props\x82\xa3tag\xa7foo.bar\xa4form\xa9inet:fqdn\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xacnode:tag:add\x85\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa3tag\xa7foo.bar\xa4time\xcf\x00\x00\x01`\xdb\x98$\x06\xa4user\xaeroot@localhost\x92\xacnode:tag:del\x86\xa4form\xa9inet:fqdn\xa4valu\xa8woot.com\xa3tag\xa7foo.bar\xa4asof\xcf\x00\x00\x01`\xdb\x98$\x06\xa4time\xcf\x00\x00\x01`\xdb\x98$\x07\xa4user\xaeroot@localhost\x92\xa8node:del\x84\xa4form\xa9inet:fqdn\xa4valu\xa8newp.com\xa4time\xcf\x00\x00\x01`\xdb\x98$\x07\xa4user\xaeroot@localhost'


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

        fname = 'old-savefile.mpk'
        with self.getTestDir() as path:
            fpath = path + '/' + fname

            # Populate and close the file
            with genfile(path, fname) as fd:
                fd.write(oldsplicelog)

            s_splice.convertSpliceFd(fpath)
            with genfile(path, fname) as fd:
                self.eq(fd.read(), newsplicelog)
