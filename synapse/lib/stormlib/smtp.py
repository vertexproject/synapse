import asyncio

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.stormtypes as s_stormtypes

import aiosmtplib

@s_stormtypes.registry.registerLib
class SmtpLib(s_stormtypes.Lib):
    '''
    A Storm Library for sending email messages via SMTP.
    '''
    _storm_locals = (
        {'name': 'message', 'desc': 'Construct a new email message.',
         'type': {'type': 'function', '_funcname': 'message',
                          'returns': {'type': 'storm:smtp:message',
                                      'desc': 'The newly constructed storm:smtp:message.'}}},
    )
    _storm_lib_path = ('inet', 'smtp',)

    def getObjLocals(self):
        return {
            'message': self.message,
        }

    async def message(self):
        return SmtpMessage(self.runt)

@s_stormtypes.registry.registerType
class SmtpMessage(s_stormtypes.StormType):
    '''
    An SMTP message to compose and send.
    '''
    _storm_typename = 'storm:smtp:message'

    _storm_locals = (

        {'name': 'text',
         'type': 'str',
         'desc': 'The text body of the email message.'},

        {'name': 'html',
         'type': 'str',
         'desc': 'The HTML body of the email message.'},

        {'name': 'sender',
         'type': 'str',
         'desc': 'The inet:email to use in the MAIL FROM request.'},

        {'name': 'recipients',
         'type': 'list',
         'desc': 'An array of RCPT TO email addresses.'},

        {'name': 'headers',
         'type': 'dict',
         'desc': 'A dictionary of email header values.'},

        {'name': 'send',
         'desc': 'Transmit a message over the web socket.',
         'type': {'type': 'function', '_funcname': 'send',
                  'args': (
                    {'name': 'host', 'type': 'str',
                        'desc': 'The hostname or IP address of the SMTP server.'},
                    {'name': 'port', 'type': 'int', 'default': 25,
                        'desc': 'The port that the SMTP server is listening on.'},
                    {'name': 'user', 'type': 'str', 'default': None,
                        'desc': 'The user name to use authenticating to the SMTP server.'},
                    {'name': 'passwd', 'type': 'str', 'default': None,
                        'desc': 'The password to use authenticating to the SMTP server.'},
                    {'name': 'usetls', 'type': 'bool', 'default': False,
                        'desc': 'Initiate a TLS connection to the SMTP server.'},
                    {'name': 'starttls', 'type': 'bool', 'default': False,
                        'desc': 'Use the STARTTLS directive with the SMTP server.'},
                    {'name': 'timeout', 'type': 'int', 'default': 60,
                        'desc': 'The timeout (in seconds) to wait for message delivery.'},
                  ),
                  'returns': {'type': 'list', 'desc': 'An ($ok, $valu) tuple.'}}},

    )

    def __init__(self, runt):
        s_stormtypes.StormType.__init__(self, None)
        self.runt = runt

        self.sender = None
        self.recipients = []
        self.headers = {}
        self.bodytext = None
        self.bodyhtml = None
        self.attachments = []

        self.locls.update({
            'send': self.send,
            'headers': self.headers,
            'recipients': self.recipients,
        })

        self.gtors['text'] = self._getEmailText
        self.gtors['html'] = self._getEmailHtml
        self.stors['text'] = self._setEmailText
        self.stors['html'] = self._setEmailHtml

        self.stors['sender'] = self._setSenderEmail
        self.gtors['sender'] = self._getSenderEmail

    async def _setSenderEmail(self, valu):
        # TODO handle inet:email and ps:contact Nodes
        self.sender = await s_stormtypes.tostr(valu)

    async def _getSenderEmail(self):
        return self.sender

    async def _setEmailText(self, text):
        self.bodytext = await s_stormtypes.tostr(text)

    async def _setEmailHtml(self, html):
        self.bodyhtml = await s_stormtypes.tostr(html)

    async def _getEmailText(self):
        return self.bodytext

    async def _getEmailHtml(self):
        return self.bodyhtml

    #TODO
    #async def attach(self, sha256, name, mime):

    async def send(self, host, port=25, user=None, passwd=None, usetls=False, starttls=False, timeout=60):

        self.runt.confirm(('storm', 'inet', 'smtp', 'send'))

        try:
            if self.bodytext is None and self.bodyhtml is None:
                mesg = 'The storm:smtp:message has no HTML or text body.'
                raise s_exc.StormRuntimeError(mesg=mesg)

            host = await s_stormtypes.tostr(host)
            port = await s_stormtypes.toint(port)
            usetls = await s_stormtypes.tobool(usetls)
            starttls = await s_stormtypes.tobool(starttls)

            timeout = await s_stormtypes.toint(timeout)

            user = await s_stormtypes.tostr(user, noneok=True)
            passwd = await s_stormtypes.tostr(passwd, noneok=True)

            message = MIMEMultipart('alternative')

            if self.bodytext is not None:
                message.attach(MIMEText(self.bodytext, 'plain', 'utf-8'))

            if self.bodyhtml is not None:
                message.attach(MIMEText(self.bodyhtml, 'html', 'utf-8'))

            for name, valu in self.headers.items():
                message[await s_stormtypes.tostr(name)] = await s_stormtypes.tostr(valu)

            recipients = [await s_stormtypes.tostr(e) for e in self.recipients]

            futu = aiosmtplib.send(message,
                    port=port,
                    hostname=host,
                    sender=self.sender,
                    recipients=recipients,
                    use_tls=usetls,
                    start_tls=starttls,
                    username=user,
                    password=passwd)

            await asyncio.wait_for(futu, timeout=timeout)

        except asyncio.CancelledError: # pragma: no cover
            raise

        except Exception as e:
            return (False, s_common.excinfo(e))

        return (True, {})
