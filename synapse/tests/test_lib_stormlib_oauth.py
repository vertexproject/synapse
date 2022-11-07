import yarl

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.httpapi as s_httpapi
import synapse.tests.utils as s_test
import synapse.tools.backup as s_backup

class HttpOAuth2Token(s_httpapi.Handler):

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

                    opts = {
                        'vars': {
                            'providerconf': providerconf00,
                            'authcode': 'itsagoodone',
                            'code_verifier': 'legit',
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
                    self.eq([(providerconf00['iden'], providerconf00)], ret)

                    # get a provider that doesn't exist
                    self.none(await core01.callStorm('$lib.inet.http.oauth.v2.getProvider($lib.guid())'))

                    # get the provider by iden
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getProvider($providerconf.iden))
                    ''', opts=opts)
                    self.eq(providerconf00, ret)

                    # try getAccessToken on non-configured provider
                    mesgs = await core01.stormlist('$lib.inet.http.oauth.v2.getUserAccessToken($lib.guid())')
                    self.stormIsInErr('OAuth V2 provider has not been configured', mesgs)

                    # try getAccessToken when the client hasn't been setup
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.none(ret)

                    # try setting the auth code when the provider isn't setup
                    mesgs = await core01.stormlist('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($lib.guid(), $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('OAuth V2 provider has not been configured', mesgs)

                    # try setting the auth code for a user that doesnt exist
                    # todo

                    # set the user auth code - SSL is always enabled
                    mesgs = await core01.stormlist('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($providerconf.iden, $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('certificate verify failed', mesgs)

                    core00.oauth.ssl = False
                    core01.oauth.ssl = False

                    # set the user auth code
                    await core01.nodes('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($providerconf.iden, $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    # access token refreshes in the background and refresh_token also gets updated
                    # todo

                    # background refresh is only happening on the leader
                    # todo

                    # if refresh window is missed during downtime token is refreshed on boot
                    # todo

                    # get the token
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq('accesstoken00', ret)

                    # can manually force token refresh
                    # todo: ??

                    # can get some refresh metadata from the client
                    # todo

                    # refresh / token fetch fails; new auth code needed
                    # todo

                    # try to delete provider that doesn't exist
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.delProvider($lib.guid()))
                    ''', opts=opts)
                    self.none(ret)

                    # delete the provider
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.delProvider($providerconf.iden))
                    ''', opts=opts)
                    self.eq(providerconf00, ret)

                    # deleted provider clients no longer exist
                    self.len(0, core01.oauth.clients.items())
                    # todo: not refreshing anymore either

                    # clients that dont get a refresh_token in response are skipped
                    # todo

                    # delete client
                    # todo

                    # background refresh fails
                    # todo

                    # manual refresh fails
                    # todo

                    # if a user gets locked the refresh should be disabled
                    # todo

                    # permissions
                    # todo

                    # promote mirror
                    # todo
