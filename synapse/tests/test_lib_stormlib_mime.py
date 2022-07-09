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

        async with self.getTestCore() as core:

            opts = {'vars': {'html': html00}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('html5lib includes this\na title\nhello there\nother text', ret)

            opts = {'vars': {'html': html01}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('a bad tag\nanother bad tag\nmore text\nfor fun', ret)

            opts = {'vars': {'html': '<div></div>'}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('', ret)

            opts = {'vars': {'html': '...'}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('...', ret)

            opts = {'vars': {'html': 'not html'}}
            ret = await core.callStorm('return($lib.mime.html.totext($html))', opts=opts)
            self.eq('not html', ret)
