import os
import yarl
import base64
import asyncio
import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.oauth as s_oauth
import synapse.lib.httpapi as s_httpapi
import synapse.tests.utils as s_test
import synapse.tools.backup as s_backup

logger = logging.getLogger(__name__)

ESECRET = 'secret'
ECLIENT = 'root'
EASSERTION = 'secretassertion'
EASSERTION_TYPE = 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer'

class HttpOAuth2Assertion(s_httpapi.Handler):
    async def get(self):
        self.set_header('Content-Type', 'application/json')
        reqv = [_s.decode() for _s in self.request.query_arguments.get('getassertion')]
        if reqv == ['valid']:
            self.set_status(200)
            self.write({'assertion': EASSERTION})
        elif reqv == ['invalid']:
            self.set_status(401)
            self.write({'error': 'not allowed'})
        else:
            self.set_status(200)
            self.write({'assertion': 'newp'})

class HttpOAuth2Token(s_httpapi.Handler):

    def checkAuth(self, body):
        # Assert client_secret or client_assertion is valid
        if 'client_assertion' in body:
            client_id = body['client_id'][0]
            assertion = body['client_assertion'][0]
            assertion_type = body['client_assertion_type'][0]
            if client_id != ECLIENT:
                self.set_status(400)
                self.write({
                    'error': 'invalid_request',
                    'error_description': f'invalid client_id {client_id}'
                })
                return False
            if assertion != EASSERTION:
                self.set_status(400)
                self.write({
                    'error': 'invalid_request',
                    'error_description': f'invalid client_assertion {assertion}'
                })
                return False
            if assertion_type != EASSERTION_TYPE:
                self.set_status(400)
                self.write({
                    'error': 'invalid_request',
                    'error_description': f'invalid client_assertion_type {assertion_type}'
                })
                return False
        else:
            auth = self.request.headers.get('Authorization')
            if auth is None:
                self.set_status(400)
                self.write({
                    'error': 'invalid_request',
                    'error_description': 'missing AUTHORIZATION header :('
                })
                return False

            if not auth.startswith('Basic '):
                self.set_status(400)
                self.write({
                    'error': 'invalid_request',
                    'error_description': f'basic auth missing Basic ?'
                })
                return False

            _, blob = auth.split(None, 1)

            try:
                text = base64.b64decode(blob).decode('utf8')
                name, secret = text.split(':', 1)
            except Exception as e:
                self.set_status(400)
                self.write({
                    'error': 'invalid_request',
                    'error_description': f'failed to decode auth {text=} {e=}'
                })
                return False
            if secret != ESECRET:
                self.set_status(400)
                self.write({
                    'error': 'invalid_request',
                    'error_description': f'bad client_secret {secret}'
                })
                return False

        return True

    async def post(self):

        body = {k: [vv.decode() for vv in v] for k, v in self.request.body_arguments.items()}

        grant_type = body['grant_type'][0]

        self.set_header('Content-Type', 'application/json')

        if grant_type == 'authorization_code':

            if not self.checkAuth(body):
                return

            if body.get('code_verifier') != ['legit']:
                self.set_status(400)
                return self.write({
                    'error': 'invalid_request',
                    'error_description': 'incorrect code_verifier'
                })

            code = body['code'][0]

            if code == 'itsagoodone':
                return self.write({
                    'access_token': 'accesstoken00',
                    'token_type': 'example',
                    'expires_in': 3,
                    'refresh_token': 'refreshtoken00',
                })

            if code == 'badrefresh':
                return self.write({
                    'access_token': 'accesstoken10',
                    'token_type': 'example',
                    'expires_in': 3,
                    'refresh_token': 'badrefresh',
                })

            if code == 'norefresh':
                return self.write({
                    'access_token': 'accesstoken20',
                    'token_type': 'example',
                    'expires_in': 1,
                })

            if code == 'itsafastone':
                return self.write({
                    'access_token': 'accesstoken30',
                    'token_type': 'example',
                    'expires_in': 3,
                    'refresh_token': 'refreshtoken10',
                })

            if code == 'itsaslowone':
                return self.write({
                    'access_token': 'accesstoken40',
                    'token_type': 'example',
                    'expires_in': 6,
                    'refresh_token': 'refreshtoken20',
                })

            if code == 'nonewrefresh':
                return self.write({
                    'access_token': 'accesstoken50',
                    'token_type': 'example',
                    'expires_in': 3,
                    'refresh_token': 'refreshpersist00',
                })

            if code == 'baddata':
                return self.write({'foo': 'bar'})

            if code == 'servererror':
                self.set_status(500)
                return

            self.set_status(400)
            return self.write({
                'error': 'invalid_request',
                'error_description': 'unknown code'
            })

        if grant_type == 'refresh_token':

            if not self.checkAuth(body):
                return

            tok = body['refresh_token'][0]

            if tok.startswith('refreshtoken'):
                return self.write({
                    'access_token': 'accesstoken01',
                    'token_type': 'example',
                    'expires_in': 3,
                    'refresh_token': 'refreshtoken01',
                })

            if tok.startswith('refreshpersist'):
                return self.write({
                    'access_token': 'accesstoken02',
                    'token_type': 'example',
                    'expires_in': 3,
                })

            self.set_status(400)
            return self.write({
                'error': 'invalid_request',
                'error_description': 'bad refresh token'
            })

class OAuthTest(s_test.SynTest):

    async def test_storm_oauth_v1(self):
        async with self.getTestCore() as core:
            # super duper basic
            q = '''
            $url = https://127.0.0.1:40000
            $ckey = foo
            $csec = bar
            $atkn = biz
            $asec = baz
            $client = $lib.inet.http.oauth.v1.client($ckey, $csec, $atkn, $asec, $lib.inet.http.oauth.v1.SIG_QUERY)
            return($client.sign($url))
            '''
            url, headers, body = await core.callStorm(q)
            self.len(0, headers)

            uri = yarl.URL(url)
            self.nn(uri.query.get('oauth_signature'))
            self.nn(uri.query.get('oauth_nonce'))
            self.nn(uri.query.get('oauth_timestamp'))

            self.eq(uri.query.get('oauth_version'), '1.0')
            self.eq(uri.query.get('oauth_signature_method'), 'HMAC-SHA1')
            self.eq(uri.query.get('oauth_consumer_key'), 'foo')
            self.eq(uri.query.get('oauth_token'), 'biz')

            # headers should get populated
            q = '''
            $url = "https://vertex.link/fakeapi"
            $ckey = beep
            $csec = boop
            $atkn = neato
            $asec = burrito
            $headers = ({
                "content-type": "application/json"
            })
            $client = $lib.inet.http.oauth.v1.client($ckey, $csec, $atkn, $asec, $lib.inet.http.oauth.v1.SIG_HEADER)
            return($client.sign($url, headers=$headers))
            '''
            url, headers, body = await core.callStorm(q)
            uri = yarl.URL(url)
            self.eq(str(url), 'https://vertex.link/fakeapi')

            self.eq(headers.get('content-type'), 'application/json')
            auth = headers.get('Authorization')
            self.nn(auth)
            params = {}
            auth = auth.strip("OAuth ")
            for pair in auth.split(', '):
                k, v = pair.split('=')
                params[k] = v.strip('"')

            self.nn(params.get('oauth_nonce'))
            self.nn(params.get('oauth_timestamp'))
            self.nn(params.get('oauth_signature'))

            self.eq(params.get('oauth_version'), '1.0')
            self.eq(params.get('oauth_signature_method'), 'HMAC-SHA1')
            self.eq(params.get('oauth_consumer_key'), 'beep')
            self.eq(params.get('oauth_token'), 'neato')

            q = '''
            $url = "https://vertex.link/fakeapi"
            $ckey = beep
            $csec = boop
            $atkn = neato
            $asec = burrito
            $headers = ({
                "Content-Type": "application/json"
            })
            $body = ({
                'foo': 'bar',
                'biz': 'baz',
            })
            $client = $lib.inet.http.oauth.v1.client($ckey, $csec, $atkn, $asec, $lib.inet.http.oauth.v1.SIG_BODY)
            return($client.sign($url, method='POST', headers=$headers, body=$body))
            '''
            url, headers, body = await core.callStorm(q)
            uri = yarl.URL(url)
            self.eq(str(url), 'https://vertex.link/fakeapi')
            # it will override the content type header
            self.eq(headers, {'Content-Type': 'application/x-www-form-urlencoded'})
            self.isin('foo=bar', body)
            self.isin('biz=baz', body)
            self.isin('oauth_nonce=', body)
            self.isin('oauth_timestamp=', body)
            self.isin('oauth_version=1.0', body)
            self.isin('oauth_signature=', body)
            self.isin('oauth_consumer_key=beep', body)
            self.isin('oauth_token=neato', body)
            self.isin('oauth_signature_method=HMAC-SHA1', body)

            # headers should auto-populate if not given
            q = '''
            $url = "https://vertex.link/fakeapi"
            $ckey = beep
            $csec = boop
            $atkn = neato
            $asec = burrito
            $body = ({
                'awesome': 'possum',
            })
            $client = $lib.inet.http.oauth.v1.client($ckey, $csec, $atkn, $asec, $lib.inet.http.oauth.v1.SIG_BODY)
            return($client.sign($url, method='POST', headers=$lib.null, body=$body))
            '''
            url, headers, body = await core.callStorm(q)
            uri = yarl.URL(url)
            self.eq(str(url), 'https://vertex.link/fakeapi')
            self.eq(headers, {'Content-Type': 'application/x-www-form-urlencoded'})
            self.isin('awesome=possum', body)

            # body can't be used on GET requests (which is the default method)
            q = '''
            $url = "https://vertex.link/fakeapi"
            $ckey = beep
            $csec = boop
            $atkn = neato
            $asec = burrito
            $headers = ({
                "Content-Type": "application/json"
            })
            $body = ({
                'foo': 'bar',
                'biz': 'baz',
            })
            $client = $lib.inet.http.oauth.v1.client($ckey, $csec, $atkn, $asec, $lib.inet.http.oauth.v1.SIG_BODY)
            return($client.sign($url, headers=$headers, body=$body))
            '''
            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm(q)

    async def test_storm_oauth_v2_clientsecret(self):

        with self.getTestDir() as dirn:

            core00dirn = s_common.gendir(dirn, 'core00')
            core01dirn = s_common.gendir(dirn, 'core01')

            coreconf = {
                'nexslog:en': True,
            }

            async with self.getTestCore(dirn=core00dirn, conf=coreconf) as core00:
                pass

            s_backup.backup(core00dirn, core01dirn)

            async with self.getTestCore(dirn=core00dirn, conf=coreconf) as core00:

                conf = {'mirror': core00.getLocalUrl()}
                async with self.getTestCore(dirn=core01dirn, conf=conf) as core01:

                    root = await core00.auth.getUserByName('root')
                    await root.setPasswd('secret')

                    user = await core00.auth.addUser('user')
                    await user.setPasswd('secret')

                    core00.addHttpApi('/api/oauth/token', HttpOAuth2Token, {'cell': core00})

                    addr, port = await core00.addHttpsPort(0)
                    baseurl = f'https://127.0.0.1:{port}'

                    providerconf00 = {
                        'iden': s_common.guid('providerconf00'),
                        'name': 'providerconf00',
                        'client_id': 'root',
                        'client_secret': 'secret',
                        'scope': 'allthethings',
                        'auth_uri': baseurl + '/api/oauth/authorize',
                        'token_uri': baseurl + '/api/oauth/token',
                        'redirect_uri': 'https://opticnetloc/oauth2',
                        'extensions': {'pkce': True},
                        'extra_auth_params': {'include_granted_scopes': 'true'}
                    }

                    expconf00 = {
                        # default values
                        'ssl_verify': True,
                        **providerconf00,
                        # default values currently not configurable by the user
                        'flow_type': 'authorization_code',
                        'auth_scheme': 'basic',
                    }
                    # client secret is never returned
                    expconf00.pop('client_secret')

                    opts = {
                        'vars': {
                            'providerconf': providerconf00,
                            'authcode': 'itsagoodone',
                            'code_verifier': 'legit',
                            'lowuser': user.iden,
                        }
                    }

                    # add a provider with a bad conf
                    name = providerconf00.pop('name')
                    mesgs = await core01.stormlist('$lib.inet.http.oauth.v2.addProvider($providerconf)', opts=opts)
                    self.stormIsInErr('data must contain', mesgs)
                    providerconf00['name'] = name

                    # add a new provider
                    await core01.nodes('$lib.inet.http.oauth.v2.addProvider($providerconf)', opts=opts)

                    # cannot add duplicate iden
                    mesgs = await core01.stormlist('$lib.inet.http.oauth.v2.addProvider($providerconf)', opts=opts)
                    self.stormIsInErr('Duplicate OAuth V2 client iden', mesgs)

                    # list providers
                    ret = await core01.callStorm('''
                        $confs = ([])
                        for ($iden, $conf) in $lib.inet.http.oauth.v2.listProviders() {
                            $confs.append(($iden, $conf))
                        }
                        return($confs)
                    ''')
                    self.eq([(expconf00['iden'], expconf00)], ret)

                    # get a provider that doesn't exist
                    self.none(await core01.callStorm('$lib.inet.http.oauth.v2.getProvider($lib.guid())'))

                    # get the provider by iden
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getProvider($providerconf.iden))
                    ''', opts=opts)
                    self.eq(expconf00, ret)

                    # try getAccessToken on non-configured provider
                    mesgs = await core01.stormlist('$lib.inet.http.oauth.v2.getUserAccessToken($lib.guid())')
                    self.stormIsInErr('OAuth V2 provider has not been configured', mesgs)

                    # try getAccessToken when the client hasn't been setup
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((False, 'Auth code has not been set'), ret)

                    # try setting the auth code when the provider isn't setup
                    mesgs = await core01.stormlist('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($lib.guid(), $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('OAuth V2 provider has not been configured', mesgs)

                    # try setting the user auth code and encounter an error
                    mesgs = await core01.stormlist('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('certificate verify failed', mesgs)

                    providerconf00['ssl_verify'] = False
                    expconf00['ssl_verify'] = False
                    await core01.nodes('''
                        $lib.inet.http.oauth.v2.delProvider($providerconf.iden)
                        $lib.inet.http.oauth.v2.addProvider($providerconf)
                    ''', opts=opts)

                    # set the user auth code
                    core00._oauth_sched_ran.clear()
                    await core01.nodes('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    # the token is available immediately
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((True, 'accesstoken00'), ret)

                    # access token refreshes in the background and refresh_token also gets updated
                    self.true(await s_coro.event_wait(core00._oauth_sched_ran, timeout=15))
                    await core01.sync()
                    clientconf = await core01.getOAuthClient(providerconf00['iden'], core00.auth.rootuser.iden)
                    self.eq('accesstoken01', clientconf['access_token'])
                    self.eq('refreshtoken01', clientconf['refresh_token'])
                    self.eq(core00._oauth_sched_heap[0][0], clientconf['refresh_at'])

                    # background refresh is only happening on the leader
                    self.none(core01.activecoros[core01._oauth_actviden].get('task'))

                    # can clear the access token so new auth code will be needed
                    core00._oauth_sched_empty.clear()
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.clearUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq('accesstoken01', ret['access_token'])
                    self.eq('refreshtoken01', ret['refresh_token'])

                    await core01.sync()
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((False, 'Auth code has not been set'), ret)

                    # without the token data the refresh item gets popped out of the loop
                    self.true(await s_coro.event_wait(core00._oauth_sched_empty, timeout=5))
                    self.len(0, core00._oauth_sched_heap)

                    # background refresh fails; will require new auth code
                    opts['vars']['authcode'] = 'badrefresh'
                    core00._oauth_sched_empty.clear()
                    await core01.nodes('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((True, 'accesstoken10'), ret)

                    self.true(await s_coro.event_wait(core00._oauth_sched_empty, timeout=5))
                    self.len(0, core00._oauth_sched_heap)

                    await core01.sync()
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((False, 'invalid_request: bad refresh token (HTTP code 400)'), ret)

                    # clients that dont get a refresh_token in response are not added to background refresh
                    # but you can still get the token until it expires
                    core00._oauth_sched_ran.clear()

                    opts['vars']['authcode'] = 'norefresh'
                    core00._oauth_sched_ran.clear()
                    await core01.nodes('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((True, 'accesstoken20'), ret)

                    self.false(await s_coro.event_wait(core00._oauth_sched_ran, timeout=1))
                    self.len(0, core00._oauth_sched_heap)

                    await core01.sync()
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((False, 'Token is expired'), ret)

                    # token fetch when setting the auth code failure
                    opts['vars']['authcode'] = 'newp'
                    mesgs = await core01.stormlist('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('invalid_request: unknown code', mesgs)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((False, 'Auth code has not been set'), ret)

                    # a retryable error that still fails
                    opts['vars']['authcode'] = 'servererror'
                    mesgs = await core01.stormlist('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('returned HTTP code 500', mesgs)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((False, 'Auth code has not been set'), ret)

                    # token data fails validation
                    opts['vars']['authcode'] = 'baddata'
                    mesgs = await core01.stormlist('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('data must contain', mesgs)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((False, 'Auth code has not been set'), ret)

                    # original refresh_token is maintained if not provided in the refresh response
                    core00._oauth_sched_ran.clear()

                    opts['vars']['authcode'] = 'nonewrefresh'
                    await core01.nodes('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    self.true(await s_coro.event_wait(core00._oauth_sched_ran, timeout=5))
                    clientconf = await core00.getOAuthClient(providerconf00['iden'], core00.auth.rootuser.iden)
                    self.eq('accesstoken02', clientconf['access_token'])
                    self.eq('refreshpersist00', clientconf['refresh_token'])

                    await core01.nodes('$lib.inet.http.oauth.v2.clearUserAccessToken($providerconf.iden)', opts=opts)

                    # can interrupt a refresh wait if a new one gets scheduled that is sooner
                    core00._oauth_sched_ran.clear()

                    opts['vars']['authcode'] = 'itsaslowone'
                    await core01.nodes('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    opts['vars']['authcode'] = 'itsafastone'
                    await core01.nodes('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts={**opts, 'user': user.iden})

                    self.true(await s_coro.event_wait(core00._oauth_sched_ran, timeout=2))
                    await core01.sync()

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq((True, 'accesstoken40'), ret)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts={**opts, 'user': user.iden})
                    self.eq((True, 'accesstoken01'), ret)

                    # verify active<->passive handoff
                    numsched = len(core00._oauth_sched_map)
                    self.len(0, core01._oauth_sched_map)

                    await core00.handoff(core01.getLocalUrl())
                    await core00.sync()
                    self.true(core01.isactive)
                    self.false(core00.isactive)

                    self.nn(core01.activecoros[core01._oauth_actviden].get('task'))
                    self.len(numsched, core01._oauth_sched_heap)

                    self.none(core00.activecoros[core00._oauth_actviden].get('task'))

                    # try to delete provider that doesn't exist
                    ret = await core00.callStorm('''
                        return($lib.inet.http.oauth.v2.delProvider($lib.guid()))
                    ''', opts=opts)
                    self.none(ret)

                    # delete the provider
                    core01._oauth_sched_empty.clear()
                    ret = await core00.callStorm('''
                        return($lib.inet.http.oauth.v2.delProvider($providerconf.iden))
                    ''', opts=opts)
                    self.eq(expconf00, ret)

                    # deleted provider clients no longer exist
                    # and refresh items are lazily deleted
                    self.len(0, core01._oauth_clients.items())
                    self.true(await s_coro.event_wait(core01._oauth_sched_empty, timeout=6))
                    self.len(0, core01._oauth_sched_heap)

                    # permissions
                    lowopts = {**opts, 'user': user.iden}

                    with self.raises(s_exc.AuthDeny):
                        await core01.nodes('$lib.inet.http.oauth.v2.addProvider($providerconf)', opts=lowopts)

                    with self.raises(s_exc.AuthDeny):
                        await core01.nodes('$lib.inet.http.oauth.v2.delProvider($providerconf.iden)', opts=lowopts)

                    with self.raises(s_exc.AuthDeny):
                        await core01.nodes('$lib.inet.http.oauth.v2.getProvider($providerconf.iden)', opts=lowopts)

                    with self.raises(s_exc.AuthDeny):
                        await core01.nodes('$lib.inet.http.oauth.v2.listProviders()', opts=lowopts)

                    # if a user is locked their token goes into error state and will never be refreshed
                    await core00.nodes('$lib.inet.http.oauth.v2.addProvider($providerconf)', opts=opts)
                    lowopts['vars']['authcode'] = 'itsafastone'

                    core01._oauth_sched_ran.clear()
                    await core00.nodes('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=lowopts)

                    self.true(await s_coro.event_wait(core01._oauth_sched_ran, timeout=2))

                    await core00.sync()
                    ret = await core00.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=lowopts)
                    self.eq((True, 'accesstoken01'), ret)

                    core01._oauth_sched_empty.clear()
                    await user.setLocked(True)

                    self.true(await s_coro.event_wait(core01._oauth_sched_empty, timeout=5))
                    self.len(0, core01._oauth_sched_heap)
                    self.eq({'error': 'User is locked'}, await core01.getOAuthClient(expconf00['iden'], user.iden))

                    # if a user is deleted their token goes into error state and will never be refreshed
                    await user.setLocked(False)

                    core01._oauth_sched_ran.clear()
                    await core00.nodes('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=lowopts)

                    self.true(await s_coro.event_wait(core01._oauth_sched_ran, timeout=2))

                    await core00.sync()
                    ret = await core00.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=lowopts)
                    self.eq((True, 'accesstoken01'), ret)

                    core01._oauth_sched_empty.clear()
                    await core01.auth.delUser(user.iden)

                    self.true(await s_coro.event_wait(core01._oauth_sched_empty, timeout=5))
                    self.len(0, core01._oauth_sched_heap)
                    self.eq({'error': 'User does not exist'}, await core01.getOAuthClient(expconf00['iden'], user.iden))

    async def test_storm_oauth_v2_clientassertion_callstorm(self):

        with self.getTestDir() as dirn:

            core00dirn = s_common.gendir(dirn, 'core00')
            core01dirn = s_common.gendir(dirn, 'core01')

            coreconf = {
                'nexslog:en': True,
            }

            async with self.getTestCore(dirn=core00dirn, conf=coreconf) as core00:
                pass

            s_backup.backup(core00dirn, core01dirn)

            async with self.getTestCore(dirn=core00dirn, conf=coreconf) as core00:

                conf = {'mirror': core00.getLocalUrl()}
                async with self.getTestCore(dirn=core01dirn, conf=conf) as core01:

                    root = await core00.auth.getUserByName('root')
                    await root.setPasswd('secret')

                    user = await core00.auth.addUser('user')
                    await user.setPasswd('secret')
                    await core00.addUserRule(user.iden, (True, ('globals', 'get')))

                    core00.addHttpApi('/api/oauth/token', HttpOAuth2Token, {'cell': core00})
                    core00.addHttpApi('/api/oauth/assertion', HttpOAuth2Assertion, {'cell': core00})

                    addr, port = await core00.addHttpsPort(0)
                    baseurl = f'https://127.0.0.1:{port}'

                    view = await core01.callStorm('return($lib.view.get().iden)')
                    await core01.callStorm('$lib.globals.set(getassertion, valid)')

                    assert_q = '''
                    $url = `{$baseurl}/api/oauth/assertion`
                    $valid = $lib.globals.get(getassertion)
                    $raise = $lib.globals.get(raise, (false))
                    if $raise {
                        $lib.raise(BadAssertion, 'I am supposed to raise.')
                    }
                    $params = ({"getassertion": $valid})
                    $resp = $lib.inet.http.get($url, params=$params, ssl_verify=(false))
                    if ($resp.code = 200) {
                        $resp = ( (true), ({'token': $resp.json().assertion}))
                    } else {
                        $resp = ( (false), ({"error": `Failed to get assertion from {$url}`}) )
                    }
                    return ( $resp )
                    '''
                    assert_vars = {
                        'baseurl': baseurl,
                    }

                    providerconf00 = {
                        'iden': s_common.guid('providerconf00'),
                        'name': 'providerconf00',
                        'client_id': 'root',
                        'client_assertion': {
                            'cortex:callstorm': {
                                'query': assert_q,
                                'vars': assert_vars,
                                'view': view,
                            }
                        },
                        'auth_scheme': 'client_assertion',
                        'scope': 'allthethings',
                        'auth_uri': baseurl + '/api/oauth/authorize',
                        'token_uri': baseurl + '/api/oauth/token',
                        'redirect_uri': 'https://opticnetloc/oauth2',
                        'extensions': {'pkce': True},
                        'extra_auth_params': {'include_granted_scopes': 'true'}
                    }

                    self.notin('client_secret', providerconf00)

                    expconf00 = {
                        # default values
                        'ssl_verify': True,
                        **providerconf00,
                        # default values currently not configurable by the user
                        'flow_type': 'authorization_code',
                    }

                    opts = {
                        'vars': {
                            'providerconf': providerconf00,
                            'authcode': 'itsagoodone',
                            'code_verifier': 'legit',
                            'lowuser': user.iden,
                        },
                    }
                    lowopts = opts.copy()
                    lowopts['user'] = user.iden

                    # add a new provider
                    await core01.nodes('$lib.inet.http.oauth.v2.addProvider($providerconf)', opts=opts)

                    # list providers
                    ret = await core01.callStorm('''
                        $confs = ([])
                        for ($iden, $conf) in $lib.inet.http.oauth.v2.listProviders() {
                            $confs.append(($iden, $conf))
                        }
                        return($confs)
                    ''')
                    self.eq([(expconf00['iden'], expconf00)], ret)

                    # get the provider by iden
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getProvider($providerconf.iden))
                    ''', opts=opts)
                    self.eq(expconf00, ret)

                    providerconf00['ssl_verify'] = False
                    expconf00['ssl_verify'] = False
                    await core01.nodes('''
                        $lib.inet.http.oauth.v2.delProvider($providerconf.iden)
                        $lib.inet.http.oauth.v2.addProvider($providerconf)
                    ''', opts=opts)

                    # set the user auth code
                    core00._oauth_sched_ran.clear()
                    await core01.nodes('''
                        $iden = $providerconf.iden
                        $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                    ''', opts=lowopts)

                    # the token is available immediately
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=lowopts)
                    self.eq((True, 'accesstoken00'), ret)

                    # access token refreshes in the background and refresh_token also gets updated
                    self.true(await s_coro.event_wait(core00._oauth_sched_ran, timeout=15))
                    await core01.sync()
                    clientconf = await core01.getOAuthClient(providerconf00['iden'], user.iden)
                    self.eq('accesstoken01', clientconf['access_token'])
                    self.eq('refreshtoken01', clientconf['refresh_token'])
                    self.eq(core00._oauth_sched_heap[0][0], clientconf['refresh_at'])

                    # Refresh again but raise an exception from callStorm
                    await core00.callStorm('$lib.globals.set(raise, (true))')
                    core00._oauth_sched_ran.clear()
                    self.true(await s_coro.event_wait(core00._oauth_sched_ran, timeout=15))
                    await core01.sync()
                    clientconf = await core01.getOAuthClient(providerconf00['iden'], user.iden)
                    self.isin("Error executing callStorm: StormRaise: errname='BadAssertion'", clientconf.get('error'))
                    self.notin('access_token', clientconf)
                    self.notin('refresh_token', clientconf)
                    await core00.callStorm('$lib.globals.pop(raise)')
                    self.true(await s_coro.event_wait(core00._oauth_sched_empty, timeout=5))
                    self.len(0, core00._oauth_sched_heap)

                    # clear the access token so new auth code will be needed
                    core00._oauth_sched_empty.clear()
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.clearUserAccessToken($providerconf.iden))
                    ''', opts=lowopts)
                    self.isin('error', ret)
                    self.notin('access_token', ret)
                    self.notin('refresh_token', ret)

                    await core01.sync()
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=lowopts)
                    self.eq((False, 'Auth code has not been set'), ret)

                    # An invalid assertion when setting the token code will cause an error
                    await core01.callStorm('$lib.globals.set(getassertion, newpnewp)')
                    with self.raises(s_exc.SynErr) as cm:
                        await core01.nodes('''
                            $iden = $providerconf.iden
                            $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                        ''', opts=lowopts)
                    self.isin('Failed to get OAuth v2 token: invalid_request', cm.exception.get('mesg'))

                    # An assertion storm callback which fails to return a token as expected also produces an error
                    await core01.callStorm('$lib.globals.set(getassertion, invalid)')

                    with self.raises(s_exc.SynErr) as cm:
                        await core01.nodes('''
                            $iden = $providerconf.iden
                            $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                        ''', opts=lowopts)
                    # N.B. The message here comes from the caller defined Storm callback. Not the oauth.py code.
                    self.isin('Failed to get OAuth v2 token: Failed to get assertion from',
                              cm.exception.get('mesg'))

    async def test_storm_oauth_v2_clientassertion_azure_token(self):
        with self.getTestDir() as dirn:
            core00dirn = s_common.gendir(dirn, 'core00')
            core01dirn = s_common.gendir(dirn, 'core01')

            coreconf = {
                'nexslog:en': True,
            }

            async with self.getTestCore(dirn=core00dirn, conf=coreconf) as core00:
                pass

            s_backup.backup(core00dirn, core01dirn)

            async with self.getTestCore(dirn=core00dirn, conf=coreconf) as core00:
                conf = {'mirror': core00.getLocalUrl()}
                async with self.getTestCore(dirn=core01dirn, conf=conf) as core01:
                    root = await core00.auth.getUserByName('root')
                    await root.setPasswd('secret')

                    user = await core00.auth.addUser('user')
                    await user.setPasswd('secret')

                    core00.addHttpApi('/api/oauth/token', HttpOAuth2Token, {'cell': core00})
                    core00.addHttpApi('/api/oauth/assertion', HttpOAuth2Assertion, {'cell': core00})

                    addr, port = await core00.addHttpsPort(0)
                    baseurl = f'https://127.0.0.1:{port}'

                    isok, valu = s_oauth._getAzureTokenFile()
                    self.false(isok)
                    self.eq(valu, 'AZURE_FEDERATED_TOKEN_FILE environment variable is not set.')

                    isok, valu = s_oauth._getAzureClientId()
                    self.false(isok)
                    self.eq(valu, 'AZURE_CLIENT_ID environment variable is not set.')

                    tokenpath = s_common.genpath(dirn, 'tokenfile')

                    providerconf00 = {
                        'iden': s_common.guid('providerconf00'),
                        'name': 'providerconf00',
                        'client_assertion': {
                            'msft:azure:workloadidentity': {'token': True, 'client_id': True}
                        },
                        'auth_scheme': 'client_assertion',
                        'scope': 'allthethings',
                        'auth_uri': baseurl + '/api/oauth/authorize',
                        'token_uri': baseurl + '/api/oauth/token',
                        'redirect_uri': 'https://opticnetloc/oauth2',
                        'extensions': {'pkce': True},
                        'extra_auth_params': {'include_granted_scopes': 'true'}
                    }
                    opts = {
                        'vars': {
                            'providerconf': providerconf00,
                            'authcode': 'itsagoodone',
                            'code_verifier': 'legit',
                            'lowuser': user.iden,
                        },
                    }

                    # must be able to get the token value to create the provider
                    with self.raises(s_exc.BadArg) as cm:
                        await core01.nodes('$lib.inet.http.oauth.v2.addProvider($providerconf)', opts=opts)
                    self.isin('Failed to get the client_assertion data', cm.exception.get('mesg'))

                    with self.setTstEnvars(AZURE_CLIENT_ID=''):
                        isok, valu = s_oauth._getAzureClientId()
                        self.false(isok)
                        self.eq(valu, 'AZURE_CLIENT_ID is set to an empty string.')

                    with self.setTstEnvars(AZURE_FEDERATED_TOKEN_FILE=tokenpath, AZURE_CLIENT_ID='root'):
                        isok, valu = s_oauth._getAzureTokenFile()
                        self.false(isok)
                        self.eq(valu, f'AZURE_FEDERATED_TOKEN_FILE file does not exist {tokenpath}')

                        with s_common.genfile(tokenpath) as fd:
                            fd.write(EASSERTION.encode())

                        isok, valu = s_oauth._getAzureTokenFile()
                        self.true(isok)
                        self.eq(valu, EASSERTION)

                        isok, valu = s_oauth._getAzureClientId()
                        self.true(isok)
                        self.eq(valu, 'root')

                        expconf00 = {
                            # default values
                            'ssl_verify': True,
                            **providerconf00,
                            # default values currently not configurable by the user
                            'flow_type': 'authorization_code',
                        }

                        lowopts = opts.copy()
                        lowopts['user'] = user.iden

                        # add a new provider
                        await core01.nodes('$lib.inet.http.oauth.v2.addProvider($providerconf)', opts=opts)

                        # list providers
                        ret = await core01.callStorm('''
                                                $confs = ([])
                                                for ($iden, $conf) in $lib.inet.http.oauth.v2.listProviders() {
                                                    $confs.append(($iden, $conf))
                                                }
                                                return($confs)
                                            ''')
                        self.eq([(expconf00['iden'], expconf00)], ret)

                        # get the provider by iden
                        ret = await core01.callStorm('return($lib.inet.http.oauth.v2.getProvider($providerconf.iden))',
                                                     opts=opts)
                        self.eq(expconf00, ret)

                        providerconf00['ssl_verify'] = False
                        expconf00['ssl_verify'] = False
                        await core01.nodes('''
                            $lib.inet.http.oauth.v2.delProvider($providerconf.iden)
                            $lib.inet.http.oauth.v2.addProvider($providerconf)
                        ''', opts=opts)

                        # set the user auth code
                        core00._oauth_sched_ran.clear()
                        await core01.nodes('''
                            $iden = $providerconf.iden
                            $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                        ''', opts=lowopts)

                        # the token is available immediately
                        ret = await core01.callStorm('''
                            return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                        ''', opts=lowopts)
                        self.eq((True, 'accesstoken00'), ret)

                        # access token refreshes in the background and refresh_token also gets updated
                        self.true(await s_coro.event_wait(core00._oauth_sched_ran, timeout=15))
                        await core01.sync()
                        clientconf = await core01.getOAuthClient(providerconf00['iden'], user.iden)
                        self.eq('accesstoken01', clientconf['access_token'])
                        self.eq('refreshtoken01', clientconf['refresh_token'])
                        self.eq(core00._oauth_sched_heap[0][0], clientconf['refresh_at'])

                        # clear the auth code, delete the file and set the auth code
                        core00._oauth_sched_empty.clear()
                        ret = await core01.callStorm('''
                            return($lib.inet.http.oauth.v2.clearUserAccessToken($providerconf.iden))
                        ''', opts=lowopts)
                        self.eq('accesstoken01', ret['access_token'])
                        self.eq('refreshtoken01', ret['refresh_token'])

                        await core01.sync()
                        ret = await core01.callStorm('''
                            return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                        ''', opts=lowopts)
                        self.eq((False, 'Auth code has not been set'), ret)

                        self.true(await s_coro.event_wait(core00._oauth_sched_empty, timeout=5))
                        self.len(0, core00._oauth_sched_heap)

                        os.unlink(tokenpath)

                        core00._oauth_sched_empty.clear()
                        with self.raises(s_exc.SynErr) as cm:
                            await core01.nodes('''
                                $iden = $providerconf.iden
                                $lib.inet.http.oauth.v2.setUserAuthCode($iden, $authcode, code_verifier=$code_verifier)
                            ''', opts=lowopts)
                        self.isin('Failed to get OAuth v2 token: AZURE_FEDERATED_TOKEN_FILE file does not exist',
                                  cm.exception.get('mesg'))

    async def test_storm_oauth_v2_badconfigs(self):
        # Specifically test bad configs here
        async with self.getTestCore() as core:
            tokenfile = s_common.genpath(core.dirn, 'file.txt')
            with s_common.genfile(tokenfile) as fd:
                fd.write('token'.encode('utf-8'))

            # Coverage for invalid configs ( we should never get into this state though! )
            # These checks would be triggered during future addition of new auth_schemes or
            # additional client_assertion providers.
            conf = {'auth_scheme': 'dne'}
            isok, info = await core._getAuthData(conf, '')
            self.false(isok)
            self.eq(info.get('error'), 'Unknown authorization scheme: dne')

            conf = {'auth_scheme': 'client_assertion', 'client_id': '1234', 'client_assertion': {'key': 'dne'}}
            isok, info = await core._getAuthData(conf, '')
            self.false(isok)
            self.eq(info.get('error'), "Unknown client_assertions data: {'key': 'dne'}")

            # Coverage for a weird configuration of azure workload identity
            with self.setTstEnvars(AZURE_FEDERATED_TOKEN_FILE=tokenfile):
                conf = {'auth_scheme': 'client_assertion',
                        'client_assertion': {'msft:azure:workloadidentity': {
                            'token': True,
                            'client_id': True,
                        }}}
                isok, info = await core._getAuthData(conf, '')
                self.false(isok)
                self.eq(info.get('error'), "AZURE_CLIENT_ID environment variable is not set.")

            view = await core.callStorm('return($lib.view.get().iden)')

            providerconf00 = {
                'iden': s_common.guid('providerconf00'),
                'name': 'providerconf00',
                'client_id': 'root',
                'client_secret': 'secret',
                'scope': 'allthethings',
                'auth_uri': 'https://hehe.corp/api/oauth/authorize',
                'token_uri': 'https://hehe.corp/api/oauth/token',
                'redirect_uri': 'https://opticnetloc/oauth2',
                'extensions': {'pkce': True},
                'extra_auth_params': {'include_granted_scopes': 'true'}
            }
            opts = {
                'vars': {
                    'providerconf': providerconf00,
                }
            }
            q = '$lib.inet.http.oauth.v2.addProvider($providerconf)'

            providerconf00.pop('client_secret')
            with self.raises(s_exc.BadArg) as cm:
                await core.nodes(q, opts=opts)
            self.isin('client_assertion and client_secret missing', cm.exception.get('mesg'))

            providerconf00['client_assertion'] = {'msft:azure:workloadidentity': {'token': True}}
            with self.raises(s_exc.BadArg) as cm:
                await core.nodes(q, opts=opts)
            self.isin('Must provide client_secret for auth_scheme=basic', cm.exception.get('mesg'))

            providerconf00['client_secret'] = 'secret'
            providerconf00.pop('client_id')
            providerconf00.pop('client_assertion')
            with self.raises(s_exc.BadArg) as cm:
                await core.nodes(q, opts=opts)
            self.isin('Must provide client_id for auth_scheme=basic', cm.exception.get('mesg'))
            providerconf00['client_id'] = 'root'

            providerconf00['auth_scheme'] = 'client_assertion'

            callstormopts = {
                'query': 'version',
                'view': view,
            }
            assertions = {'msft:azure:workloadidentity': {'token': True}}
            providerconf00['client_secret'] = 'secret'
            providerconf00['client_assertion'] = assertions
            with self.raises(s_exc.BadArg) as cm:
                await core.nodes(q, opts=opts)
            self.isin('client_assertion and client_secret provided.', cm.exception.get('mesg'))

            providerconf00.pop('client_secret')
            assertions['msft:azure:workloadidentity'] = {'token': False}
            with self.raises(s_exc.BadArg) as cm:
                await core.nodes(q, opts=opts)
            self.eq('msft:azure:workloadidentity token key must be true', cm.exception.get('mesg'))

            with self.setTstEnvars(AZURE_FEDERATED_TOKEN_FILE=tokenfile):
                assertions['msft:azure:workloadidentity'] = {'token': True, 'client_id': True}

                with self.raises(s_exc.BadArg) as cm:
                    await core.nodes(q, opts=opts)
                m = 'Cannot specify a fixed client_id and a dynamic client_id value.'
                self.eq(m, cm.exception.get('mesg'))

                providerconf00.pop('client_id')
                with self.raises(s_exc.BadArg) as cm:
                    await core.nodes(q, opts=opts)
                m = 'Failed to get the client_id data: AZURE_CLIENT_ID environment variable is not set.'
                self.eq(m, cm.exception.get('mesg'))

            providerconf00['client_id'] = 'root'
            assertions['cortex:callstorm'] = callstormopts
            with self.raises(s_exc.SchemaViolation) as cm:
                await core.nodes(q, opts=opts)
            self.isin('data.client_assertion must be valid exactly by one definition', cm.exception.get('mesg'))

            assertions.pop('msft:azure:workloadidentity')
            callstormopts['view'] = s_common.guid()
            with self.raises(s_exc.BadArg) as cm:
                await core.nodes(q, opts=opts)
            self.eq(f'View {callstormopts["view"]} does not exist.', cm.exception.get('mesg'))

            callstormopts['view'] = view
            callstormopts['query'] = ' | | | '
            with self.raises(s_exc.BadArg) as cm:
                await core.nodes(q, opts=opts)
            self.isin('Bad storm query', cm.exception.get('mesg'))

            callstormopts['query'] = ' return ( ) '
            providerconf00.pop('client_id')
            with self.raises(s_exc.BadArg) as cm:
                await core.nodes(q, opts=opts)
            self.eq('Must provide client_id for with cortex:callstorm provider.', cm.exception.get('mesg'))

            class NotACortex(s_oauth.OAuthMixin, s_cell.Cell):
                async def initServiceStorage(self):
                    await self._initOAuthManager()

            async with self.getTestCell(NotACortex) as cell:
                with self.raises(s_exc.BadArg) as cm:
                    await cell.addOAuthProvider(providerconf00)
                self.eq('cortex:callstorm client assertion not supported by NotACortex', cm.exception.get('mesg'))
