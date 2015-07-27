import io
import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.neuron as s_neuron
import synapse.common as s_common

rsa1 = b'-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAnYfdMKg/QFAwoIV9yPCZXRAFeZzzdu/S8KsL7ncnvTvo2eST\nHchRm8xvk96XEY1GtvxOKchCRnRQD/zrK1Ux+VFq2UfwcFEpeZLCDj5F3c6xrWoU\nBAbAgdpbUU1IRCQPnhVGs8SPEjJ8JdBHVWOzEU1vYnpepWR97V2oCxDRHskXLHnZ\nwv997922KLDtknrog47w17ClQOuvPUHGMKyffc64YTcVyJ9T61G0OOjLxwc98IjP\nW6WRPPTdRSMGsHsbYlHhmzUf2GQtuDs4jmlE0RSkK7tIYKNHuOZBx6jbyMkZa+ef\nYNdqOvRYnCqZslr4qOJimNm9sDzyf5p8Ku6NVQIDAQABAoIBAENe4533lnVu1h0Q\neicBntVKEM1d7lGjZ1c+D7BAjWJEyOTG+JP4I865s85Nl9YN0XxYkyUTXCS9gbAU\nvo6dtO2ngEbEmXOvgklYFl35C/A8gYhkoYLHUHU4aW1v28Qol/VHrCEdowJpTObv\nGFLQfLidoVFAfFHHlIN7Vm7FFmpPcUwbF5SeOqAdY9bEhhTq01Irv6y9fg3w51vO\nyOhhlhp4ILpfaY5+zl4gHoyghPIojfLyDuBsCC1Aj3o2/WWoqcT606TJ04lZBiDQ\nH/uN7Oor0oiTx+s94MsCUMlJvbHHO+s+4T5xu9DZKk4zD50uGbnvakXg8c/wehfe\nB56SBdECgYEAtVo7W1hrwTW8SuF/Ix9G5d+NFPRf65+TlX+wcKv344SrMlfacE0n\n/iZyzZr1/kW/9U6HBpJe3ifUMBV+8xVHkMVThzFGIzBErYrKXRU6ejUihAlY7RRo\ncCV/cYHMypQKEHAY0fxz5ftkCC0VCUSt5s1heWjx0YGaQHM8vUcL9aMCgYEA3l9y\nqyM+lM8/YMqIvHGpEOFSQWCejjIIJnwT3d/NHew4uJ1Tsi3TgTNUWrfS210huZEX\nXBva4S2Gtjit1b8rXOSiD3KdjDW6KF4MV7HnbzwI9BHQEP6mXS0AoJk1jOrmlj3N\nAfQpsp/AStA30T03EnERJhQ4OqarFHhcujVOcKcCgYEAtBLzy4EiBgjIfgYpCwP8\njzcKTNtW/41Fq3XOCiMIExfiMiwAD/DdHESrTDNpveEeeYNPGhxvLOKZlGFT3CWu\nGTeG+D/aKAi+uR+OTx1MIpruOfNaJJdWGL1zLY84fZK/55CXZLLrllqn+mJheAGF\nOB+JgVfOfjzVoNeMYVnRq0cCgYEAlHRUMTxOQzo4rX2I24VlwQcrysmeEIAGQOsE\nuFL4tMlG9LjTb1h4owCJiCbAdgIuyZu7ZJqT/VBPZsdgBhqh8FoSdw2lcD1OEjT3\nOHRkdTY3I/ngVfgrSHkKuiyOO412c0a+3lcKn11XGpr3KJEdewpQ0IMfJsit3fSc\nsxNzUnECgYBOdJIxBDapd5LvKZUM4tyKUgXemPMuUxpNADpsClHJpJrfL4aawAoW\nnZwy81ObIUP2kHHzmAFkxmuQQNfy/KIQskUV5pw6DyuilPrwVIoGbu7YIEyO0SXN\nYE01jpjGBj7MVd8WZ41nUAaDq2J44Fp7rCrQZiVpHTKNUO1jJZmC1Q==\n-----END RSA PRIVATE KEY-----'

rsa2 = b'-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAwIxKyns1pIYz7Uq3h2DP7tSfXUGtNHz/eo9c/o29jrbmw4nf\nC/ZMk+nE8ze9ANMg/N/Mcx6By5ds4aXUF2YKDvVTWzzboXvE9AGO1zcCTqOy7urw\npouiKX9ugt5a1ykyruMm0BMVIOgVwXQVrX1rhIxpDaXdHk/rKFrRghGUbQ6zUBhj\nFU9/YyH0QoBCBMUQCLtHPGqMm2joox+QEfWWS/oV1N+VzasZl6BLMqwdTPcPL4En\nyD0DG7q4cc1ximnQdmYzxFIyQeaA9d4y2yu4LxAgjMDMDWBOOGcTtmTJz5mdamC8\nxTBNXcDi7fAtf6+IECNpviMomi83OLacrqE41wIDAQABAoIBAFGLWKVV9srdlyI4\nkW9A/e6sl21cQilHgr759i1MA+pr5WEMg6zCO34s8575jQ7LW14cva5HTjrVv2P0\n4dSi/0GEfi/Wn0FNdITOIBtfDZgWVdI/J3mxCxU+BaRg3OHgbbmJM8fNPRZ5k7Uh\nH4kg46b3/Amuo+2RdQrbI31NSqnAYisygMnTyKyxRavmzvy2+omhLZWluu0MK4OS\nigXVBnh98v5tYPZiDOcsyAHz/jK5DBxfSulfc57qpsgZ1k8lTnkac7vIcSMSWWg7\nyi9ndjei0G23kwCVhD7zmOaHucDbS5O2hLV+kLQFJBGFNOrjIOozjZ9vRKMqcLA8\nMzwkN5ECgYEAyj+TchwDk5c09sjmZGXcnstheSC5mknQXZgZ+eJZ+CZSLTI4nCdX\nkP2PiyFIl7RdNI2861qGr9egPfFMjfALlXumDQX4CpobktMQQaeOrU3Af6qbSNAh\nDxqDXhs+UvTyQ8eyVel7OCCAJZ3mglxTpam5tkALbZcRLP29sCCQiKkCgYEA87i7\ngg6y/WGruIlXWwm1OxUeyBPbhGmtfm/TXjt/IfJxWykvB0QRS+r8lfu2n/DzhJAe\nPwYCIj+lXEmw/HXt6Ms0LRGaOPac31908K7tMIVE0V3jzB9Ui5p7mro3+iokVatV\nAykeQedRgdLj0ffsu6h1YTpKkfQ/jO5mPMTlJX8CgYBiyI6x63Drw60A5LtzSjVp\n8hiX2x4MeAUn0cTOQnqDM+RrYt43lxe0H8TexdD5GAV2R8yAf+TNOlpwJs2nfhmK\nV6yRK9stAnx5SFHmX3rWtuVQ9fmGpPGguOh1LIVSa4VxCbbXM4UVsvokZW1TOtk4\nTyAAHmP2kRS4ju75ec5ekQKBgQDh3R4wbmzkMuLQNr91B+8jXPRU2UpDUShOl1Wb\n66lrDWKN6AHESwl4gMIqQMbDPKqA/Ip7P5c0pCUb/NL/dE7RwZeN+NUi2zEQNUeL\nUaFQqQDYwpk8bwCMC9Nm1hLQTMO1fP1g23dF/hhkJsuop4mFc52sSDgZQPCwK7Ml\nuBbgAwKBgBUmShpZDXyUVxutgo/9fRsxEXbRzN640DNzB8xrkIav3RWVxJcCCzQo\nn1I+F/4vjKNQFsGk1d6k3caia8626VJ0/8bV6TaW6ZAtJConLOh0XZ4JVrNYTEnM\n4YLZkOZ93vq277orD7h3EIFn9gW9z6/qhJnTviTdxG2pAPeWWeus\n-----END RSA PRIVATE KEY-----'

rsa3 = b'-----BEGIN RSA PRIVATE KEY-----\nMIIEpQIBAAKCAQEAslA1xXQlrWffstn0a0SersrFGDo0UqwxdKcidMF6dTgWCHnG\nnPAS6QDinALtKAXTe0GHgC53aWm032C9gHUtp0XoB5e6Mqmmy37J4ZIzAFuCWqAf\nDavbb6xcbwZOpJuywhvGnBOHv3K2DP3V7IpDXXLfut3j5x88CWZxm+H0VKFxdg9w\n3UGCHux7/aqcDpFixZhrvj+Cnzs1CLJZiF7Dp5L2i/8CjfZ1pEEIXpL6qz1fvwxQ\n0ZaFRyiYMQam8xJw6kQ0BKkM589lzJVX9G2FBQyNBo2AJ5vfDrP1+a88l0cD9VSc\nKHkwR2iVirv9y+c1lRR0CTrHKQFSwBDLDB4WxwIDAQABAoIBADrw1oVZOicSodf9\nwZQ/j3BZqEK04py9PG/B21rapX7ftjDBCAzSMn4Ag+dr9DZ5jok8hOyy71fR0C7S\nTHGMyjVznxn7ZlneyDqVw2ejquYgWXtZWEptl1BXmgo8/Hve13zgL4thzUpUQacT\ntMXGgjP+h8O+GtpH8dFtonoTe28JjQYM4mVHP84UFjYlo98S359nbcBWw7RyW8fr\ni/h2gZPMhyR86WhsYEuu2hwMPAVaJwA6fTXb4RCcDmo1XEE1cmQCYs6iWTOTiTFy\n6Mv2GC64H17fCJn4ZPaMT62lR9jxBlYVeDucgeN7EGaXO7OLxB3SeE5/vd+/Te71\nQDt8WRECgYEAysno46bjmOhhYhO/vrIVxbknuNjjjLjrQLtuDSPv1OH2ComGixMS\nPpMYo6EHp2IaYAXi/ya16Kv9IpLxVImrfXNXOSb0fG0UO+bCCNm5efmeKe4IsmKI\n5d8dh3uv3Lw16HRuugijPME0f2V0PMzl2RC6zDOVsY1KWnF1AGVkEg8CgYEA4Rox\n9kFTZHz25V7yXlbuhHoa3gg56gVL+BqN9Rvnh1SsSQMkveVYUwCruPnVHL3U0p+n\nWKK46wVAxBHrgayumsUKj59/LOUsY4T+GMsLKMF5cnVc+T71azx0GXRtC7acmLgf\ndzYmaPEgshF6iqOFe9aCcpwCyrc5No7VeFKah8kCgYEAyTqs8GKmTRCjuhhQ2KGN\nO2Rth18qBnVldRnIrh9wGTaU2YX4zb8CBrge5higKLgP5iNRStIWBynMCmf4NGRc\nmSNAdYUzbNktD/f/qZqsE97g1UjQtntSz5Ckk9HoBEl70Qzg55g0q9ApERYSz1af\n6tNQGdxCeirzkmYtrVPvhn8CgYEAhMwWY4fgca0DXwfnhl5UslTy2sARoozjZ4gK\n7Wo76eu7BAvVti3CMJ15sVO6NQ2Mq4FCkZjV7NiZf9JulH7SNz49X8OhnFPLHx8L\nZIcMm0ugoTS519UbpdrxRz8XQczGj5Y4AfUxLcHrHwIOwBF+IzPGm2SMhRkYqKYV\nK7nXrnkCgYEAyWsXbnFWpIW41By9CMa9yRBvUpdo3ucH1nDNDzvXHjy6tIWUMGdo\nIPSUxfaEgbK3oSwpQpls7itzkX14DIX7B1FpUXl4gSGP395iMg2xyiRg5u2gMPfi\nqvJqMcniUvAitzDNWlz7fhPVAo1Su3oCFxx5VMCgZsuVVZFQ61uU/DA=\n-----END RSA PRIVATE KEY-----'

rsa4 = b'-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA1eR4zcoclHjTQyX3gyhzXPDs2FI+fid571NkVrVvNujdFckK\n+NsUWlFdMcizGlGMLoa0FWa6+b9BGniD3sWOlpo6nGtPuMH4A8qysej1MwMyiLJb\n/XNwrRj9QZ1DhKgXXFZdQhq9YfdKEGy/p5I9o9krhFuJiA4V6OF7+lGiF2fRlDpG\nLwXMQnJY/KkmiNbf8UIhweKrlfhAPc5x9Wa1iZjtFFyQASvWQZmLorYAviwb2hiN\nZCSDB6fs7nxETvXkqXapG+pZ0wm2AxRcZG7fUW7FBjfyYyKqNAiPNk1ixcQ8y+7M\nICDZQOX1kldU+9P3VNRD5cqIlKZmHhBFcW8IlwIDAQABAoIBAQC+7rI/0Xltt+Wu\nfUfTFtrUTmS+Pbx3VLnuP5zEIjXi6D/i4JIgzz/917+/Xw8yITVnmutKZ2fk5Ssy\ne/4LcIL2QTqswsZpgQzqJZkaY3/uR55mlAC14MTmX/ZDCiVpV7tyu82H4uLHfr3o\np4r2BP9tMcE855F/mENKnW3UZ+avyGSUL4VeaMw3OSuE8lSrA4BOCvhwzsmTKq94\nKQbE75mZ6ekc5tvKRroYQGwLKEnyLKUEktwn0gxkMYxE8RuFaK8KNSo8lxxMepxE\nyWAgl93HwYGsVwKQd6600A56JP1iwvQkBUS2Nf9/Dqy+TIVc1grzSvWLCILpDCFn\nmhmx/jlhAoGBANtpOCh+kq+EG9PRP30kJvTjs9pdTcV7FCjSBiR3Z3HQ2xYfTqsn\nwC8zLGNPeNbrIGM3FIaaGNYc/O+mFPoBU1bb47BHXl4pPT28WqnVDuoIZhnla+v+\nSahUBEhefNa+vejX/dzF4zCz3Hxbp572G9OkCIYEdSz7vkBpWNd2sboPAoGBAPmP\nqaeDdKrY1Ry9/TpliQ3jI4fVaeh8Wa2rOyhicdmZV5QmojDYZPAzLo3o2aH1dtRr\nJQAQmh6TYtiRFNrLORMmn4doUw6l1sI7YDS57SHlIn9lVp+1/l9eaEu8AytvOzqV\n92z2DjLOzmq+GRfn3FII1LwlupKzZyAvR4gcrfD5AoGAKKdLR32EUk8JFOstd1Nu\ngGt8VJZ7JX8TkiiwCKuzGAyZu3Sbj+zymAxESjZcbn3sZ1W6UOJWfb2rRAAi3NvI\nBE0D2BKxMoMznK+8oMEgXU6nFF9E6toX7b97d6lCOkvnRjBXEkP8P3bkAIq++R4i\ns8kt5x8GUwpmCus6EdolPhMCgYEA2jjIdkVZ0Ec42yA6/URp+u3CVPXF3VhXJqiT\nWzXyLf+LeG3r52BhqzRmIgsZuyikVwy11v+tdM0WYx9CKCwKZXehicsszaMwTrmS\n36gw9jGh39piS9fdbdFky8zEzMc/+HPIXswuEDmMgARoduH1Yvp742XuZndf1uHg\n3+GMLCkCgYBnEfH0vvRIeFTMXG/HiO92wSHy1Ubk5hZV5NopZM8DUas5F3ZLpxEx\ns64TdKkGMi0wIdE9PgZlqdqBFf3rcWH++FFnl6I3v2L21mWlHNG9m7drUnHsN4Xe\nF1/Ef7U7dsDdennWlvkj1G/pdaYfk08g/1Lza8s77qs4dP+BDrssSA==\n-----END RSA PRIVATE KEY-----'

class FakeAuth(s_daemon.AuthModule):
    pass

class FooBar:
    def __init__(self):
        pass

    def foo(self, x):
        return x + 20

    def bar(self, x):
        raise Exception('hi')

class TestNeuron(unittest.TestCase):

    def test_neuron_peering(self):
        neu1 = s_neuron.Daemon()
        neu2 = s_neuron.Daemon()
        neu3 = s_neuron.Daemon()

        neu1.setNeuInfo('rsakey',rsa1)
        neu2.setNeuInfo('rsakey',rsa2)
        neu3.setNeuInfo('rsakey',rsa3)

        cert1 = neu1.genPeerCert()
        cert2 = neu2.genPeerCert()
        cert3 = neu3.genPeerCert()

        neu1.addPeerCert(cert2)
        neu1.addPeerCert(cert3)

        neu2.addPeerCert(cert1)
        neu2.addPeerCert(cert3)

        neu3.addPeerCert(cert1)
        neu3.addPeerCert(cert2)

        link1 = s_link.chopLinkUrl('tcp://127.0.0.1:0')

        #link1 = s_common.tufo('tcp',listen=('0.0.0.0',0))
        neu1.runLinkServer(link1)

        evt1 = threading.Event()
        def peer1init(event):
            evt1.set()

        evt2 = threading.Event()
        def peer2init(event):
            evt2.set()

        evt3 = threading.Event()
        def peer3init(event):
            evt3.set()

        neu1.on('neu:peer:init',peer1init)
        neu2.on('neu:peer:init',peer2init)
        neu3.on('neu:peer:init',peer3init)

        neu2.runLinkPeer(link1)

        self.assertTrue( evt1.wait(3) )
        self.assertTrue( evt2.wait(3) )

        neu3.runLinkPeer(link1)
        self.assertTrue( evt3.wait(3) )

        rtt1 = neu1.syncPingPeer(neu2.ident)
        rtt2 = neu2.syncPingPeer(neu1.ident)

        # check that 3 can reach 2 via 1
        rtt3 = neu3.syncPingPeer(neu2.ident)

        self.assertIsNotNone(rtt1)
        self.assertIsNotNone(rtt2)
        self.assertIsNotNone(rtt3)

        neu1.fini()
        neu2.fini()
        neu3.fini()

    def test_neuron_keepstate(self):

        fd = io.BytesIO()
        neu = s_neuron.Daemon(statefd=fd)

        ident = neu.getNeuInfo('ident')

        neu.setNeuInfo('rsakey',rsa1)
        neu.addNeuCortex('woot.0','ram:///',tags='hehe,haha')
        neu.addNeuCortex('woot.1','ram:///')
        neu.delNeuCortex('woot.1')

        cert = neu.genPeerCert()

        neu.fini()

        fd.flush()
        fd.seek(0)

        neu = s_neuron.Daemon(statefd=fd)

        self.assertEqual( neu.getNeuInfo('ident'), ident )
        self.assertEqual( neu.getNeuInfo('rsakey'), rsa1 )
        self.assertEqual( neu.getNeuInfo('peercert'), cert )

        self.assertIsNone( neu.metacore.getCortex('woot.1') )
        self.assertIsNotNone( neu.metacore.getCortex('woot.0') )

        neu.fini()

    def test_neuron_route_basics(self):

        neuron = s_neuron.Daemon()

        ident = neuron.ident
        peers = [ s_common.guid() for i in range(3) ]

        neuron.addPeerGraphEdge( ident, peers[0] )
        neuron.addPeerGraphEdge( peers[0], ident )

        neuron.addPeerGraphEdge( peers[0], peers[1] )
        neuron.addPeerGraphEdge( peers[1], peers[0] )

        neuron.addPeerGraphEdge( peers[1], peers[2] )
        neuron.addPeerGraphEdge( peers[2], peers[1] )

        route = neuron._getPeerRoute( peers[2] )

        self.assertListEqual( route, [ ident, peers[0], peers[1], peers[2] ] )
        neuron.fini()

    def test_neuron_signer(self):
        neu1 = s_neuron.Daemon()
        neu2 = s_neuron.Daemon()
        neu3 = s_neuron.Daemon()

        neu1.setNeuInfo('rsakey',rsa1)
        neu2.setNeuInfo('rsakey',rsa2)
        neu3.setNeuInfo('rsakey',rsa3)

        cert1 = neu1.genPeerCert(signer=True)

        # make the new cert everybodys signer
        neu2.addPeerCert(cert1)
        neu3.addPeerCert(cert1)

        cert2 = neu2.genPeerCert()
        cert3 = neu3.genPeerCert()

        self.assertFalse( neu3.loadPeerCert( cert2 ) )
        self.assertFalse( neu2.loadPeerCert( cert3 ) )

        cert2 = neu1.signPeerCert( cert2 )
        cert3 = neu1.signPeerCert( cert3 )

        self.assertTrue( neu2.loadPeerCert( cert3 ) )
        self.assertTrue( neu3.loadPeerCert( cert2 ) )

    def test_neuron_authmod(self):
        neu1 = s_neuron.Daemon()
        self.assertTrue( neu1.getAuthAllow( 'hehe', 'haha' ) )

        authdef = ('synapse.tests.test_neuron.FakeAuth',(),{})
        neu1.setNeuInfo('authmod',authdef)

        self.assertFalse( neu1.getAuthAllow( 'hehe', 'haha' ) )

    def test_neuron_shares(self):
        neu1 = s_neuron.Daemon()
        foobar = 'synapse.tests.test_neuron.FooBar'
        neu1.addNeuShare('foobar',foobar,(),{})

    #def test_neuron_route_asymetric(self):
    #def test_neuron_route_teardown(self):
