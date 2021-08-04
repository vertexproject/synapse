import synapse.tests.utils as s_test

class SmtpTest(s_test.SynTest):

    async def test_storm_smtp(self):

        async with self.getTestCore() as core:
            retn = await core.callStorm('''
                $message = $lib.inet.smtp.message()
                $message.text = hi
                $message.sender = visi@vertex.link
                $message.headers.Subject = woot
                $message.recipients.append(visi@vertex.link)
                ($ok, $retn) = $message.send('smtp.gmail.com', port=465, usetls=true)
                return(($ok, $retn))
            ''')
            self.false(retn[0])
            self.true('Authentication Required' in retn[1])
