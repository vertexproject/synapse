import yarl
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.coro as s_coro
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

            # todo: could shorten the 8s expires_in to make the tests run faster

            if code == 'itsagoodone':
                return self.write({
                    'access_token': 'accesstoken00',
                    'token_type': 'example',
                    'expires_in': 8,
                    'refresh_token': 'refreshtoken00',
                })

            if code == 'badrefresh':
                return self.write({
                    'access_token': 'accesstoken10',
                    'token_type': 'example',
                    'expires_in': 8,
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
                    'expires_in': 10,
                    'refresh_token': 'refreshtoken20',
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
                    'expires_in': 8,
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

                    user = await core00.auth.addUser('user')
                    await user.setPasswd('secret')

                    core00.addHttpApi('/api/oauth/token', HttpOAuth2Token, {'cell': core00})

                    addr, port = await core00.addHttpsPort(0)
                    baseurl = f'https://127.0.0.1:{port}'

                    providerconf00 = {
                        'iden': s_common.guid('providerconf00'),
                        'name': 'providerconf00',
                        'flow_type': 'authorization_code',
                        'client_id': 'root',
                        'client_secret': 'secret',
                        'scope': 'allthethings',
                        'auth_uri': baseurl + '/api/oauth/authorize',
                        'token_uri': baseurl + '/api/oauth/token',
                        'redirect_uri': 'https://opticnetloc/oauth2',
                        'extensions': {'pkce': True},
                        'extra_auth_params': {'include_granted_scopes': 'true'}
                    }
                    expconf00 = {k: v for k, v in providerconf00.items() if k != 'client_secret'}

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
                    self.none(ret)

                    # try setting the auth code when the provider isn't setup
                    mesgs = await core01.stormlist('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($lib.guid(), $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('OAuth V2 provider has not been configured', mesgs)

                    # set the user auth code - SSL is always enabled
                    mesgs = await core01.stormlist('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($providerconf.iden, $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('certificate verify failed', mesgs)

                    core00.oauth.ssl = False
                    core01.oauth.ssl = False

                    # set the user auth code
                    core00.oauth._schedule_item_ran.clear()
                    await core01.nodes('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($providerconf.iden, $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    # the token is available immediately
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq('accesstoken00', ret)

                    # access token refreshes in the background and refresh_token also gets updated
                    self.true(await s_coro.event_wait(core00.oauth._schedule_item_ran, timeout=15))
                    await core01.sync()
                    clientconf = core01.oauth.clients.get(providerconf00['iden'] + core00.auth.rootuser.iden)
                    self.eq('accesstoken01', clientconf['access_token'])
                    self.eq('refreshtoken01', clientconf['refresh_token'])
                    self.eq(core00.oauth.schedule_heap[0][0], clientconf['refresh_at'])

                    # background refresh is only happening on the leader
                    self.none(core01.oauth.schedule_task)

                    # can clear the access token so new auth code will be needed
                    core00.oauth._schedule_item_ran.clear()
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.clearUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq('accesstoken01', ret['access_token'])
                    self.eq('refreshtoken01', ret['refresh_token'])

                    await core01.sync()
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.none(ret)

                    # without the token data the refresh item gets popped out of the loop
                    self.true(await s_coro.event_wait(core00.oauth._schedule_item_ran, timeout=5))
                    self.len(0, core00.oauth.schedule_heap)

                    # background refresh fails; will require new auth code
                    opts['vars']['authcode'] = 'badrefresh'
                    core00.oauth._schedule_item_ran.clear()
                    await core01.nodes('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($providerconf.iden, $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq('accesstoken10', ret)

                    self.true(await s_coro.event_wait(core00.oauth._schedule_item_ran, timeout=5))
                    self.len(0, core00.oauth.schedule_heap)

                    await core01.sync()
                    mesgs = await core01.stormlist('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.stormIsInErr('bad refresh token', mesgs)

                    # clients that dont get a refresh_token in response are not added to background refresh
                    # but you can still get the token until it expires
                    core00.oauth._schedule_item_ran.clear()

                    opts['vars']['authcode'] = 'norefresh'
                    core00.oauth._schedule_item_ran.clear()
                    await core01.nodes('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($providerconf.iden, $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq('accesstoken20', ret)

                    self.false(await s_coro.event_wait(core00.oauth._schedule_item_ran, timeout=1))
                    self.len(0, core00.oauth.schedule_heap)

                    await core01.sync()
                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.none(ret)

                    # token fetch when setting the auth code failure
                    opts['vars']['authcode'] = 'newp'
                    mesgs = await core01.stormlist('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($providerconf.iden, $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)
                    self.stormIsInErr('invalid_request: unknown code', mesgs)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.none(ret)

                    # can interrupt a refresh wait if a new one gets scheduled that is sooner
                    core00.oauth._schedule_item_ran.clear()

                    opts['vars']['authcode'] = 'itsaslowone'
                    await core01.nodes('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($providerconf.iden, $lib.user.iden,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    opts['vars']['authcode'] = 'itsafastone'
                    await core01.nodes('''
                        $lib.inet.http.oauth.v2.setUserAuthCode($providerconf.iden, $lowuser,
                                                                    $authcode, code_verifier=$code_verifier)
                    ''', opts=opts)

                    self.true(await s_coro.event_wait(core00.oauth._schedule_item_ran, timeout=2))
                    await core01.sync()

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts=opts)
                    self.eq('accesstoken40', ret)

                    ret = await core01.callStorm('''
                        return($lib.inet.http.oauth.v2.getUserAccessToken($providerconf.iden))
                    ''', opts={**opts, 'user': user.iden})
                    self.eq('accesstoken01', ret)

                    # if a user gets locked the refresh is disabled
                    # todo

                    # user does not exist at runtime
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
                    for i in range(len(core00.oauth.schedule_heap)):
                        core00.oauth._schedule_item_ran.clear()
                        await s_coro.event_wait(core00.oauth._schedule_item_ran, timeout=2)
                    self.len(0, core00.oauth.schedule_heap)

                    # permissions
                    # todo

                    # promote mirror
                    # todo

                    # if refresh window is missed during downtime token is refreshed on boot
                    # todo
