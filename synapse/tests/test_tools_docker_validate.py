import base64

import unittest.mock as mock

import cryptography.hazmat.primitives.serialization as c_serialization

import synapse.lib.json as s_json
import synapse.lib.certdir as s_certdir

import synapse.tests.utils as s_t_utils
import synapse.tools.docker.validate as s_t_d_validate

class TestDockerValidate(s_t_utils.SynTest):

    def test_tool_docker_validate(self):

        # Check cosign
        outp = self.getTestOutp()
        with mock.patch('subprocess.run') as patch:

            mock_stdout = mock.MagicMock(stdout=b'Hhehe\nGitVersion:    v2.0.2\nhaha', stderr=b'')
            patch.return_value = mock_stdout
            ret = s_t_d_validate.checkCosign(outp)
            outp.expect('2.0.2')
            self.true(ret)

            outp.clear()
            mock_stdout = mock.MagicMock(stdout=b'Hhehe\nGitVersion:    v1.13.1\nhaha', stderr=b'')
            patch.return_value = mock_stdout
            ret = s_t_d_validate.checkCosign(outp)
            outp.expect('Did not find cosign version v2.x.x')
            self.false(ret)

            outp.clear()
            mock_stdout = mock.MagicMock(stdout=b'Hhehe\nnewp\n\nhaha', stderr=b'')
            patch.return_value = mock_stdout
            ret = s_t_d_validate.checkCosign(outp)
            outp.expect('Cannot find GitVersion')
            self.false(ret)

        with self.getTestDir() as dirn:
            certdir = s_certdir.CertDir(path=(dirn,))
            certdir.genCaCert('cosignTest')
            certdir.genCodeCert('signer', signas='cosignTest')

            sign_cert = certdir.getCodeCert('signer')
            der_byts = sign_cert.public_bytes(c_serialization.Encoding.DER)
            test_resp = {'Cert': {'Raw': base64.b64encode(der_byts).decode()}}

            # getCosignSignature
            outp = self.getTestOutp()
            with mock.patch('subprocess.run') as patch:
                test_stdout = s_json.dumps(test_resp)
                mock_stdout = mock.MagicMock(stdout=test_stdout)
                patch.return_value = mock_stdout
                ret = s_t_d_validate.getCosignSignature(outp, 'hehe/haha:tag')
                self.isinstance(ret, dict)

                outp.clear()
                mock_stdout = mock.MagicMock(stdout=b'["hehe"]')
                patch.return_value = mock_stdout
                ret = s_t_d_validate.getCosignSignature(outp, 'hehe/haha:tag')
                outp.expect('Expected dictionary')
                self.none(ret)

                outp.clear()
                mock_stdout = mock.MagicMock(stdout=b'newp')
                patch.return_value = mock_stdout
                ret = s_t_d_validate.getCosignSignature(outp, 'hehe/haha:tag')
                outp.expect('Error decoding blob')
                self.none(ret)

            # checkCRL
            outp = self.getTestOutp()

            pubk_byts = s_t_d_validate.checkCRL(outp, test_resp, certdir)
            self.isinstance(pubk_byts, bytes)

            outp.clear()
            crl = certdir.genCaCrl('cosignTest')
            crl.revoke(sign_cert)

            ret = s_t_d_validate.checkCRL(outp, test_resp, certdir)
            outp.expect('Signature has invalid certificate: certificate revoked')
            self.false(ret)

            # checkCosignSignature
            outp = self.getTestOutp()
            with mock.patch('subprocess.run') as patch:
                mock_stdout = mock.MagicMock(stdout=b'{"key": "valu"}')
                patch.return_value = mock_stdout

                ret = s_t_d_validate.checkCosignSignature(outp, pubk_byts, 'hehe://haha:tag')
                outp.expect('Cosign output:')
                self.true(ret)
