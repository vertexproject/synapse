import synapse.lib.stormlib.mime as s_mime

import synapse.tests.utils as s_test

html00 = '''
<html>
    <head>
        <script>html5lib includes this</script>
        <title>a title</title>
    </head>
    <div>
        <p>hello there</p>
        other text
    </div>
</html>
'''

html01 = '''
<newp>
  <head>
  </head>
  <bzdy>
    a bad tag
  </body>
  <body>
    <div>
        another bad tag
    <dv>
        more text
    </dv>
  </body>
</newp>
for fun
'''

class StormlibMimeTest(s_test.SynTest):

    async def test_stormlib_mime_html(self):

        # this is mostly for coverage because it looks like code coverage doesn't work for code executed under semafork()
        self.eq('html5lib includes this\na title\nhello there\nother text', s_mime.htmlToText(html00))
        self.eq('html5lib includes this|a title|hello there|other text', s_mime.htmlToText(html00, separator='|'))
        self.eq('  foo  ', s_mime.htmlToText('<div> <p> foo </p> </div>', separator='', strip=False))

        async with self.getTestCore() as core:

            opts = {'vars': {'html': html00}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('html5lib includes this\na title\nhello there\nother text', ret)

            ret = await core.callStorm('return($lib.mime.html.totext($html, separator="|"))', opts=opts)
            self.eq('html5lib includes this|a title|hello there|other text', ret)

            opts = {'vars': {'html': html01}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('a bad tag\nanother bad tag\nmore text\nfor fun', ret)

            ret = await core.callStorm('return($lib.mime.html.totext($html, separator=", "))', opts=opts)
            self.eq('a bad tag, another bad tag, more text, for fun', ret)

            ret = await core.callStorm('return($lib.mime.html.totext($html, separator=(null), strip=(false)))', opts=opts)
            self.eq('\n  \n  \n  \n    a bad tag\n  \n  \n    \n        another bad tag\n    \n        more text\n    \n  \n\nfor fun\n', ret)

            opts = {'vars': {'html': '<div></div>'}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('', ret)

            opts = {'vars': {'html': '<div>    </div>'}}
            ret = await core.callStorm('return($lib.mime.html.totext($html, strip=(false)))', opts=opts)
            self.eq('    ', ret)

            opts = {'vars': {'html': '<div> <p> foo </p> </div>'}}
            ret = await core.callStorm('return($lib.mime.html.totext($html, separator=(null), strip=(false)))', opts=opts)
            self.eq('  foo  ', ret)

            opts = {'vars': {'html': '...'}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('...', ret)

            opts = {'vars': {'html': 'not html'}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('not html', ret)
