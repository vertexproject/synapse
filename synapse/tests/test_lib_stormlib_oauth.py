import asyncio

import yarl

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_test

class OAuthTest(s_test.SynTest):
    async def test_storm_oauth(self):
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
