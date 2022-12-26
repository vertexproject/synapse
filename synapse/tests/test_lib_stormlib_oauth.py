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
