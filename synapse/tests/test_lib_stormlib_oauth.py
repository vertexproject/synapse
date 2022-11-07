import yarl

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.httpapi as s_httpapi
import synapse.tests.utils as s_test
import synapse.tools.backup as s_backup

class HttpOAuth2Authorize(s_httpapi.Handler):
    async def post(self):
        print('foo')

class HttpOAuth2Token(s_httpapi.Handler):
    async def get(self): ...

    async def post(self):

        body = {k: [vv.decode() for vv in v] for k, v in self.request.body_arguments.items()}

        grant_type = body['grant_type'][0]

        self.set_header('Content-Type', 'application/json')

        if grant_type == 'authorization_code':
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
                    'expires_in': 3600,
                    'refresh_token': 'refreshtoken00',
                })
            self.set_status(400)
            return self.write({
                'error': 'invalid_request',
                'error_description': 'unknown code'
            })

        if grant_type == 'refresh_token':
            tok = body['refresh_token'][0]
            if tok.startswith('refreshtoken'):
                return self.write({
                    'access_token': 'accesstoken01',
                    'token_type': 'example',
                    'expires_in': 3600,
                    'refresh_token': 'refreshtoken01',
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
            $headers = $lib.dict(
                "content-type"="application/json"
            )
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
            $headers = $lib.dict(
                "Content-Type"="application/json"
            )
            $body = $lib.dict(
                foo = bar,
                biz = baz,
            )
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
            $body = $lib.dict(
                awesome = possum,
            )
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
            $headers = $lib.dict(
                "Content-Type"="application/json"
            )
            $body = $lib.dict(
                foo = bar,
                biz = baz,
            )
            $client = $lib.inet.http.oauth.v1.client($ckey, $csec, $atkn, $asec, $lib.inet.http.oauth.v1.SIG_BODY)
            return($client.sign($url, headers=$headers, body=$body))
            '''
            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm(q)

    async def test_storm_oauth_v2(self):

        with self.getTestDir() as dirn:

            core00dirn = s_common.gendir(dirn, 'core00')
            core01dirn = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=core00dirn, conf={'nexslog:en': True}) as core00:
                pass

            s_backup.backup(core00dirn, core01dirn)

            async with self.getTestCore(dirn=core00dirn, conf={'nexslog:en': True}) as core00:

                conf = {'mirror': core00.getLocalUrl()}
                async with self.getTestCore(dirn=core01dirn, conf=conf) as core01:

                    core01 = core00  # fixme: not ready for mirror stuff yet

                    root = await core00.auth.getUserByName('root')
                    await root.setPasswd('secret')

                    core00.addHttpApi('/api/oauth/token', HttpOAuth2Token, {'cell': core00})
                    # core00.addHttpApi('/api/oauth/authorize', HttpOAuth2Authorize, {'cell': core00})

                    addr, port = await core00.addHttpsPort(0)
                    baseurl = f'https://127.0.0.1:{port}'

                    iden = s_common.guid('oauth2')

                    cdef = {
                        'iden': iden,
                        'client_id': 'root',
                        'client_secret': 'secret',
                        'scope': 'profile',
                        'auth_uri': baseurl + '/api/oauth/authorize',
                        'token_uri': baseurl + '/api/oauth/token',
                        'redirect_uri': 'https://opticnetloc/oauth2',
                    }

                    expcdef = {
                        **cdef,
                        'response_type': 'code',
                        'state': {
                            'auth_code': None,
                            'expires_in': None,
                            'expires_at': None,
                            'access_token': None,
                            'refresh_token': None,
                            'code_verifier': None,
                        },
                        'extensions': {
                            'pkce': True,
                        },
                        'extra_auth_params': {},
                    }

                    opts = {'vars': {**cdef, 'auth_code': 'itsagoodone'}}

                    # add a new client
                    ret = await core01.callStorm('''
                        $client = $lib.inet.http.oauth.v2.add($iden, $client_id, $client_secret, $scope,
                                                                $auth_uri, $token_uri, $redirect_uri)
                        return($client.pack())
                    ''', opts=opts)
                    self.eq(expcdef, ret)

                    # cannot add duplicate iden
                    mesgs = await core01.stormlist('''
                        $client = $lib.inet.http.oauth.v2.add($iden, $client_id, $client_secret, $scope,
                                                                $auth_uri, $token_uri, $redirect_uri)
                    ''', opts=opts)
                    self.stormIsInErr('Duplicate OAuth V2 client iden', mesgs)

                    # list clients
                    ret = await core01.callStorm('''
                        $idens = ([])
                        for $client in $lib.inet.http.oauth.v2.list() {
                            $idens.append($client.pack().iden)
                        }
                        return($idens)
                    ''')
                    self.eq([iden], ret)

                    # get a client that doesn't exist
                    self.none(await core01.callStorm('$lib.inet.http.oauth.v2.get($lib.guid())'))

                    # get the client by iden
                    ret = await core01.callStorm('return($lib.inet.http.oauth.v2.get($iden).pack())', opts=opts)
                    self.eq(expcdef, ret)

                    # eq works on client type
                    ret = await core01.callStorm('''
                        $ret = ([])
                        $client00 = $lib.inet.http.oauth.v2.get($iden)
                        $client01 = $lib.inet.http.oauth.v2.get($iden)
                        $ret.append(($client00 = $client00))
                        $ret.append(($client00 = $client01))
                        $ret.append(($client00 = $lib.null))
                        return($ret)
                    ''', opts=opts)
                    self.eq([True, True, False], ret)

                    # try getAccessToken; raises for auth code
                    ret = await core01.callStorm('''
                        try {
                            $client = $lib.inet.http.oauth.v2.get($iden)
                            return($client.getToken())
                        } catch NeedAuthCode as err {
                            return($err.info.iden)
                        }
                    ''', opts=opts)
                    self.eq(iden, ret)

                    # use storm api to set the auth code
                    ret = await core01.callStorm('''
                        $client = $lib.inet.http.oauth.v2.get($iden)
                        $client.setAuthCode($auth_code, code_verifier="legit")
                        return($client.pack())
                    ''', opts=opts)
                    expcdef['state']['auth_code'] = 'itsagoodone'
                    expcdef['state']['code_verifier'] = 'legit'
                    self.eq(expcdef, ret)

                    # access token refreshes in the background
                    # and refresh_token also gets updated
                    # todo

                    # background refresh is only happening on the leader
                    # todo

                    # if refresh window is missed during downtime
                    # token is refreshed on boot
                    # todo

                    # get the token
                    ret = await core01.callStorm('''
                        try {
                            $client = $lib.inet.http.oauth.v2.get($iden)
                            return($client.getToken())
                        } catch NeedAuthCode as err {
                            return($err.info.iden)
                        }
                    ''', opts=opts)
                    self.eq('accesstoken00', ret)

                    # can manually force token refresh
                    ret = await core01.callStorm('''
                        $client = $lib.inet.http.oauth.v2.get($iden)
                        $ret00 = $client.refreshToken()
                        $ret01 = $client.getToken()
                        return(($ret00, $ret01))
                    ''', opts=opts)
                    self.eq(((True, None), 'accesstoken01'), ret)

                    # can get some refresh metadata from the client
                    # todo

                    # refresh / token fetch fails; new auth code needed
                    # todo

                    # can clear state from the client
                    # todo

                    # try to delete client that doesn't exist
                    # todo

                    # delete the client
                    await core01.nodes('$lib.inet.http.oauth.v2.del($iden)', opts=opts)
                    self.none(await core01.callStorm('$lib.inet.http.oauth.v2.get($iden)', opts=opts))

                    # deleted client is no longer refreshed in the background
                    # todo

                    # client without offline scope does not get refresh_token and should be skipped
                    # todo

                    # bad client causes background refresh to fail
                    # todo: retry every 12hrs anyway?

                    # bad client causes manual refresh to fail
                    # todo

                    # permissions
                    # todo
