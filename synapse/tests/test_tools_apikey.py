import datetime

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.time as s_time
import synapse.lib.output as s_output

import synapse.tests.utils as s_test
import synapse.tools.apikey as s_t_apikey

async def getApiKeyByName(core, name):
    keys = {k.get('name'): k async for k in core.getApiKeys()}
    return keys.get(name)

class ApiKeyTest(s_test.SynTest):

    async def test_tools_apikey(self):
        async with self.getTestCore() as core:

            await core.auth.addUser('blackout')

            rooturl = core.getLocalUrl()
            blckurl = core.getLocalUrl(user='blackout')

            # Add API keys
            argv = (
                '--svcurl', rooturl,
                'add',
                'rootkey00',
                '-d', '120',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))

            self.isin('Successfully added API key with name=rootkey00.', str(outp))
            rootkey00 = await getApiKeyByName(core, 'rootkey00')

            self.isin(f'Iden: {rootkey00.get("iden")}', str(outp))
            self.isin('  API Key: ', str(outp))
            self.isin('  Name: rootkey00', str(outp))
            self.isin(f'  Created: {s_time.repr(rootkey00.get("created"))}', str(outp))
            self.isin(f'  Updated: {s_time.repr(rootkey00.get("updated"))}', str(outp))
            self.isin(f'  Expires: {s_time.repr(rootkey00.get("expires"))}', str(outp))
            self.eq(rootkey00.get('expires'), rootkey00.get('created') + 120000)

            argv = (
                '--svcurl', rooturl,
                'add',
                '-u', 'blackout',
                'blckkey00',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))

            self.isin('Successfully added API key with name=blckkey00.', str(outp))
            blckkey00 = await getApiKeyByName(core, 'blckkey00')

            self.isin(f'Iden: {blckkey00.get("iden")}', str(outp))
            self.isin('  API Key: ', str(outp))
            self.isin('  Name: blckkey00', str(outp))
            self.isin(f'  Created: {s_time.repr(blckkey00.get("created"))}', str(outp))
            self.isin(f'  Updated: {s_time.repr(blckkey00.get("updated"))}', str(outp))
            self.notin('  Expires: ', str(outp))

            argv = (
                '--svcurl', blckurl,
                'add',
                'blckkey01',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))

            self.isin('Successfully added API key with name=blckkey01.', str(outp))
            blckkey01 = await getApiKeyByName(core, 'blckkey01')

            self.isin(f'Iden: {blckkey01.get("iden")}', str(outp))
            self.isin('  API Key: ', str(outp))
            self.isin('  Name: blckkey01', str(outp))
            self.isin(f'  Created: {s_time.repr(blckkey01.get("created"))}', str(outp))
            self.isin(f'  Updated: {s_time.repr(blckkey01.get("updated"))}', str(outp))
            self.notin('  Expires: ', str(outp))

            # List API keys
            argv = (
                '--svcurl', rooturl,
                'list',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))

            self.isin(f'Iden: {rootkey00.get("iden")}', str(outp))
            self.notin('  API Key: ', str(outp))
            self.isin('  Name: rootkey00', str(outp))
            self.isin(f'  Created: {s_time.repr(rootkey00.get("created"))}', str(outp))
            self.isin(f'  Updated: {s_time.repr(rootkey00.get("updated"))}', str(outp))
            self.isin(f'  Expires: {s_time.repr(rootkey00.get("expires"))}', str(outp))
            self.eq(rootkey00.get('expires'), rootkey00.get('created') + 120000)

            argv = (
                '--svcurl', rooturl,
                'list',
                '-u', 'blackout',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))

            self.isin(f'Iden: {blckkey00.get("iden")}', str(outp))
            self.notin('  API Key: ', str(outp))
            self.isin('  Name: blckkey00', str(outp))
            self.isin(f'  Created: {s_time.repr(blckkey00.get("created"))}', str(outp))
            self.isin(f'  Updated: {s_time.repr(blckkey00.get("updated"))}', str(outp))
            self.notin('  Expires: ', str(outp))

            self.isin(f'Iden: {blckkey01.get("iden")}', str(outp))
            self.notin('  API Key: ', str(outp))
            self.isin('  Name: blckkey01', str(outp))
            self.isin(f'  Created: {s_time.repr(blckkey01.get("created"))}', str(outp))
            self.isin(f'  Updated: {s_time.repr(blckkey01.get("updated"))}', str(outp))
            self.notin('  Expires: ', str(outp))

            argv = (
                '--svcurl', blckurl,
                'list',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))

            self.isin(f'Iden: {blckkey00.get("iden")}', str(outp))
            self.notin('  API Key: ', str(outp))
            self.isin('  Name: blckkey00', str(outp))
            self.isin(f'  Created: {s_time.repr(blckkey00.get("created"))}', str(outp))
            self.isin(f'  Updated: {s_time.repr(blckkey00.get("updated"))}', str(outp))
            self.notin('  Expires: ', str(outp))

            self.isin(f'Iden: {blckkey01.get("iden")}', str(outp))
            self.notin('  API Key: ', str(outp))
            self.isin('  Name: blckkey01', str(outp))
            self.isin(f'  Created: {s_time.repr(blckkey01.get("created"))}', str(outp))
            self.isin(f'  Updated: {s_time.repr(blckkey01.get("updated"))}', str(outp))
            self.notin('  Expires: ', str(outp))

            # Delete API keys
            rootiden00 = rootkey00.get('iden')
            argv = (
                '--svcurl', rooturl,
                'del',
                rootiden00,
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))
            self.isin(f'Successfully deleted API key with iden={rootiden00}.', str(outp))

            blckiden00 = blckkey00.get('iden')
            argv = (
                '--svcurl', rooturl,
                'del',
                blckiden00,
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))
            self.isin(f'Successfully deleted API key with iden={blckiden00}.', str(outp))

            blckiden01 = blckkey01.get('iden')
            argv = (
                '--svcurl', blckurl,
                'del',
                blckiden01,
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))
            self.isin(f'Successfully deleted API key with iden={blckiden01}.', str(outp))

            # List API keys again
            argv = (
                '--svcurl', rooturl,
                'list',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))
            self.isin('No API keys found.', str(outp))

            argv = (
                '--svcurl', rooturl,
                'list',
                '-u', 'blackout',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))
            self.isin('No API keys found.', str(outp))

            argv = (
                '--svcurl', blckurl,
                'list',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_apikey.main(argv, outp=outp))
            self.isin('No API keys found.', str(outp))

            # Check errors
            argv = (
                '--svcurl', rooturl,
                'list',
                '-u', 'newp',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_apikey.main(argv, outp=outp))
            self.isin('ERROR: NoSuchUser: No user named newp.', str(outp))

            argv = (
                '--svcurl', blckurl,
                'list',
                '-u', 'root',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_apikey.main(argv, outp=outp))
            self.isin('ERROR: AuthDeny: getUserInfo denied for non-admin and non-self', str(outp))

            newpiden = s_common.guid()
            argv = (
                '--svcurl', rooturl,
                'del',
                newpiden,
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_apikey.main(argv, outp=outp))
            self.isin(f"ERROR: NoSuchIden: User API key with iden='{newpiden}' does not exist.", str(outp))
