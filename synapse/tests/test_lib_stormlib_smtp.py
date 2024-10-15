import ssl
import email.mime.multipart as e_muiltipart

from unittest import mock
import synapse.tests.utils as s_test

class SmtpTest(s_test.SynTest):

    async def test_storm_smtp(self):

        called_args = []
        async def send(*args, **kwargs):
            called_args.append((args, kwargs))
            return

        with mock.patch('aiosmtplib.send', send):

            async with self.getTestCore() as core:

                retn = await core.callStorm('return($lib.inet.smtp.message().send(127.0.0.1))')
                self.false(retn[0])
                self.eq(retn[1].get('err'), 'StormRuntimeError')
                self.isin('The inet:smtp:message has no HTML or text body.', retn[1].get('errmsg'))
                self.len(0, called_args)

                retn = await core.callStorm('''
                    $message = $lib.inet.smtp.message()
                    $message.text = "HELLO WORLD"
                    $message.html = "<html><body><h1>HI!</h1></body></html>"
                    $message.sender = visi@vertex.link
                    $message.headers.Subject = woot
                    $message.recipients.append(visi@vertex.link)

                    // test gtors...
                    if (not $message.sender ~= "visi") { $lib.exit() }
                    if (not $message.text ~= "HELLO") { $lib.exit() }
                    if (not $message.html ~= "HI") { $lib.exit() }

                    return($message.send('smtp.gmail.com', port=465, usetls=true))
                ''')
                self.eq(retn, (True, {}))
                mesg = called_args[-1][0][0]  # type: e_muiltipart.MIMEMultipart
                self.eq(mesg.get_all('subject'), ['woot'])
                payload = mesg.get_payload()
                self.len(2, payload)
                self.eq([pl.get_content_type() for pl in payload],
                        ['text/plain', 'text/html'])
                ctx = self.nn(called_args[-1][1].get('tls_context'))  # type: ssl.SSLContext
                self.eq(ctx.verify_mode, ssl.CERT_REQUIRED)
                self.eq(called_args[-1][1].get('port'), 465)
                self.true(called_args[-1][1].get('use_tls'))
                self.false(called_args[-1][1].get('start_tls'))

                retn = await core.callStorm('''
                    $message = $lib.inet.smtp.message()
                    $message.text = "HELLO WORLD"
                    $message.sender = visi@vertex.link
                    $message.headers.Subject = woot
                    $message.recipients.append(visi@vertex.link)
                    return($message.send('smtp.gmail.com', port=465, starttls=true, ssl_verify=(false)))
                ''')
                self.eq(retn, (True, {}))
                mesg = called_args[-1][0][0]  # type: e_muiltipart.MIMEMultipart
                payload = mesg.get_payload()
                self.len(1, payload)
                self.eq([pl.get_content_type() for pl in payload], ['text/plain'])
                ctx = self.nn(called_args[-1][1].get('tls_context'))  # type: ssl.SSLContext
                self.eq(ctx.verify_mode, ssl.CERT_NONE)
                self.false(called_args[-1][1].get('use_tls'))
                self.true(called_args[-1][1].get('start_tls'))

                retn = await core.callStorm('''
                    $message = $lib.inet.smtp.message()
                    $message.text = "HELLO WORLD"
                    $message.sender = visi@vertex.link
                    $message.headers.Subject = woot
                    $message.recipients.append(visi@vertex.link)
                    return($message.send('smtp.gmail.com', port=25))
                ''')
                self.eq(retn, (True, {}))
                self.none(called_args[-1][1].get('tls_context'))  # type: ssl.SSLContext
                self.eq(called_args[-1][1].get('port'), 25)
                self.false(called_args[-1][1].get('use_tls'))
                self.false(called_args[-1][1].get('start_tls'))

                isok, info = await core.callStorm('''
                    $message = $lib.inet.smtp.message()
                    $message.text = "HELLO WORLD"
                    return($message.send('smtp.newp.com', port=465, usetls=$lib.true, starttls=$lib.true))
                ''')
                self.false(isok)
                self.eq(info.get('err'), 'BadArg')
