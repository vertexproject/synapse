from synapse.tests.common import *

import synapse.lib.pki as s_pki
import synapse.cortex as s_cortex
import synapse.tools.pkitool as s_pkitool

class PkiTest(SynTest):

    def test_pki_base(self):

        core0 = s_cortex.openurl('ram:///')
        pki0 = s_pki.PkiStor(core0)

        uidn = guidstr()

        root = pki0.genRootToken(bits=512, save=True)

        dork = pki0.genUserToken('dork@dork.com', bits=512, save=True)
        visi = pki0.genUserToken('visi@kenshoto.com', can=('sign:cert',), bits=512, save=True)

        iden = root[0]
        self.assertIsNotNone( iden )
        self.assertEqual(visi[1].get('user'), 'visi@kenshoto.com')

        vcrt = pki0.genTokenCert(visi, signas=iden)

        pki0.setTokenCert(visi[0], vcrt, save=True)

        dcrt = s_pki.initTokenCert(dork)
        dcrt = pki0.signTokenCert(visi[0], dcrt)

        core1 = s_cortex.openurl('ram:///')
        pki1 = s_pki.PkiStor(core1)

        self.assertIsNone( pki1.loadCertToken( dcrt ) )

        pki1.setTokenTufo(root)
        self.assertIsNotNone( pki1.loadCertToken( dcrt ) )

        foob = b'foob'

        iden = root[0]
        sign = pki0.genByteSign(iden, b'blob')

        toks = tuple( pki0.iterTokenTufos() )

        self.assertEqual( len(toks), 3)

        self.assertTrue( pki1.isValidSign(iden, sign, b'blob') )

        self.assertFalse( pki1.isValidSign(iden, sign, foob) )
        self.assertFalse( pki1.isValidSign(foob, sign, b'blob') )
        self.assertFalse( pki1.isValidSign(iden, foob, b'blob') )

        pki0.fini()
        core0.fini()
        pki1.fini()
        core1.fini()

    def test_pki_cli_gentok(self):
        cor = s_cortex.openurl('ram:///')

        pki = s_pki.PkiStor(cor)
        cli = s_pkitool.PkiCli(pki)

        tok = cli.runCmdLine('tokgen visi --root --bits 512 --can mesh:join,code:sign')

        token = pki.getTokenTufo( tok[0] )

        self.assertIsNotNone( token[0] )
        self.assertIsNotNone( token[1].get('pubkey') )

        self.assertTrue( token[1]['root'] )
        self.assertTrue( token[1]['can']['mesh:join'] )
        self.assertTrue( token[1]['can']['mesh:join'] )

        cli.fini()
        pki.fini()
        cor.fini()

    def test_pki_idenbyhost(self):
        cor = s_cortex.openurl('ram:///')

        pki = s_pki.PkiStor(cor)
        tokn = pki.genHostToken('visi.kenshoto.com', bits=512)

        self.assertIsNone( pki.getIdenByHost('newp.newp.com') )
        self.assertEqual( tokn[0], pki.getIdenByHost('visi.kenshoto.com') )

        pki.fini()
        cor.fini()

    def test_pki_idenbyuser(self):
        cor = s_cortex.openurl('ram:///')

        pki = s_pki.PkiStor(cor)
        tokn = pki.genUserToken('visi', bits=512)

        self.assertIsNone( pki.getIdenByUser('newp') )
        self.assertEqual( tokn[0], pki.getIdenByUser('visi') )

        pki.fini()
        cor.fini()
