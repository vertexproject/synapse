from unittest import mock
import synapse.tests.utils as s_test

class SmtpTest(s_test.SynTest):

    async def test_storm_smtp(self):

        async def send(*args, **kwargs):
            return

        with mock.patch('aiosmtplib.send', send):

            async with self.getTestCore() as core:

                retn = await core.callStorm('return($lib.inet.smtp.message().send(127.0.0.1))')
                self.false(retn[0])

                retn = await core.callStorm('''
                    $message = $lib.inet.smtp.message()
                    $message.text = HI
                    $message.html = "<html><body><h1>HI!</h1></body></html>"
                    $message.sender = visi@vertex.link
                    $message.headers.Subject = woot
                    $message.recipients.append(visi@vertex.link)

                    // test gtors...
                    if (not $message.sender ~= "visi") { $lib.exit() }
                    if (not $message.text ~= "HI") { $lib.exit() }
                    if (not $message.html ~= "HI") { $lib.exit() }

                    return($message.send('smtp.gmail.com', port=465, usetls=true))
                ''')
                self.eq(retn, (True, {}))
