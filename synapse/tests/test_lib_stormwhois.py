import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_test

class StormWhoisTest(s_test.SynTest):

    async def test_storm_whois_guid(self):

        async with self.getTestCore() as core:
            # IP netblock record
            props = {
                'net4': '10.0.0.0/28',
                'asof': 2554869000000,
                'id': 'NET-10-0-0-0-1',
                'status': 'validated',
            }
            stormcmd = '''
                [(inet:whois:iprec=$lib.inet.whois.guid($props, "iprec")
                    :net4=$props.net4
                    :asof=$props.asof
                    :id=$props.id
                    :status=$props.status)]
            '''
            opts = {'vars': {'props': props}}
            _ = await core.nodes(stormcmd, opts=opts)
            guid_exp = s_common.guid(sorted((props['net4'], str(props['asof']), props['id'])))
            self.len(1, await core.nodes(f'inet:whois:iprec={guid_exp}'))

            stormcmd = '''$props=({'net4':'10.0.0.0/28', 'asof':(2554869000000), 'id':'NET-10-0-0-0-1', 'status':'validated'})
            return ($lib.inet.whois.guid($props, 'iprec'))
            '''
            guid = await core.callStorm(stormcmd)
            self.eq(guid_exp, guid)

            # contact
            pscontact = s_common.guid()
            props = {
                'contact': pscontact,
                'asof': 2554869000000,
                'roles': ('abuse', 'technical', 'administrative'),
                'asn': 123456,
                'id': 'SPM-3',
                'links': ('http://myrdap.com/SPM3',),
                'status': 'active',
            }
            stormcmd = '''
                [(inet:whois:ipcontact=$lib.inet.whois.guid($props, "ipcontact")
                    :contact=$props.contact
                    :asof=$props.asof
                    :id=$props.id
                    :status=$props.status)]
            '''
            opts = {'vars': {'props': props}}
            _ = await core.nodes(stormcmd, opts=opts)
            guid_exp = s_common.guid(sorted((props['contact'], str(props['asof']), props['id'])))
            self.len(1, await core.nodes(f'inet:whois:ipcontact={guid_exp}'))

            # query
            props = {
                'time': 2554869000000,
                'url': 'http://myrdap/rdap/?query=3300%3A100%3A1%3A%3Affff',
                'ipv6': '3300:100:1::ffff',
                'success': False,
            }
            stormcmd = '''
                [(inet:whois:ipquery=$lib.inet.whois.guid($props, "ipquery")
                    :time=$props.time
                    :url=$props.url
                    :ipv6=$props.ipv6
                    :success=$props.success)]
            '''
            opts = {'vars': {'props': props}}
            _ = await core.nodes(stormcmd, opts=opts)
            guid_exp = s_common.guid(sorted((str(props['time']), props['url'], props['ipv6'])))
            self.len(1, await core.nodes(f'inet:whois:ipquery={guid_exp}'))

            # Random guid cases
            props = {
                'fqdn': 'foo.bar',
            }
            stormcmd = '''
                [(inet:whois:ipquery=$lib.inet.whois.guid($props, "ipquery")
                    :fqdn=$props.fqdn)]
            '''
            opts = {'vars': {'props': props}}
            mesgs = await core.stormlist(stormcmd, opts=opts)
            self.stormIsInWarn('$lib.inet.whois.guid() is deprecated', mesgs)
            self.stormIsInWarn('Insufficient guid vals identified, using random guid:', mesgs)
            self.len(1, await core.nodes(f'inet:whois:ipquery:fqdn={props["fqdn"]}'))

            props = {
                'asn': 9999,
            }
            stormcmd = '''
                [(inet:whois:ipcontact=$lib.inet.whois.guid($props, "ipcontact")
                    :asn=$props.asn)]
            '''
            opts = {'vars': {'props': props}}
            mesgs = await core.stormlist(stormcmd, opts=opts)
            self.stormIsInWarn('$lib.inet.whois.guid() is deprecated', mesgs)
            self.stormIsInWarn('Insufficient guid vals identified, using random guid:', mesgs)
            self.len(1, await core.nodes(f'inet:whois:ipcontact:asn={props["asn"]}'))

            # Failure cases
            stormcmd = '''
                [(inet:whois:ipcontact=$lib.inet.whois.guid($props, "foobar"))]
            '''
            opts = {'vars': {'props': {}}}
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(stormcmd, opts=opts))

            stormcmd = '''
                [(inet:whois:ipcontact=$lib.inet.whois.guid($props, "ipcontact"))]
            '''
            opts = {'vars': {'props': 123}}
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(stormcmd, opts=opts))
