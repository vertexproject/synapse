import os
import re
import sys
import base64
import pprint
import argparse
import subprocess

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.output as s_outp
import synapse.lib.certdir as s_certdir

import cryptography.x509 as c_x509
import cryptography.hazmat.primitives.serialization as c_serialization

def checkCosign(outp):
    args = ('cosign', 'version')
    try:
        proc = subprocess.run(args, capture_output=True)
        proc.check_returncode()
    except (FileNotFoundError, subprocess.CalledProcessError) as e:  # pragma: no cover
        outp.printf(f'Error calling {" ".join(args)}: {e}')
        return False
    data = '\n'.join((proc.stdout.decode(), proc.stderr.decode()))
    if 'GitVersion' not in data:
        outp.printf(f'Cannot find GitVersion in output: {data}')
        outp.printf(data)
        return False

    vline = [line for line in data.splitlines() if line.startswith('GitVersion')][0]
    if re.search('v2\\.[0-9]+\\.[0-9]+', vline):
        outp.printf(f'Using Cosign with {vline}')
        return True

    outp.printf(f'Did not find cosign version v2.x.x in "{vline}"')
    return False

def getCosignSignature(outp, image):
    args = ('cosign', 'download', 'signature', image)
    try:
        proc = subprocess.run(args, capture_output=True)
        proc.check_returncode()
    except (FileNotFoundError, subprocess.CalledProcessError) as e:  # pragma: no cover
        outp.printf(f'Error calling {" ".join(args)}: {e}')
        return None

    blob = proc.stdout
    try:
        sigd = s_json.loads(blob)
    except s_exc.BadJsonText as e:
        outp.printf(f'Error decoding blob: {blob}: {e}')
        return None
    if not isinstance(sigd, dict):
        outp.printf(f'Expected dictionary, got {sigd} from {blob}')
        return None

    return sigd

def checkCRL(outp, sigd, certdir):
    # Extract signing certificate; ensure that it is not revoked according to our CRL

    byts = base64.b64decode(sigd.get('Cert', {}).get('Raw', ''))

    try:
        cert = c_x509.load_der_x509_certificate(byts)
        pem_byts = cert.public_bytes(c_serialization.Encoding.PEM)
    except Exception as e:  # pragma: no cover
        # Unwrap pyopenssl's exception_from_error_queue
        outp.printf(f'Failed to load signature bytes: {e} {byts}')
        return False

    try:
        certdir.valCodeCert(pem_byts)
    except s_exc.BadCertVerify as e:
        mesg = e.get('mesg')
        if mesg:
            mesg = f'Signature has invalid certificate: {mesg}'
        else:
            mesg = 'Signature has invalid certificate!'
        outp.printf(mesg)
        return False

    # Return the pubkey bytes in PEM format
    return cert.public_key().public_bytes(encoding=c_serialization.Encoding.PEM,
                                          format=c_serialization.PublicFormat.SubjectPublicKeyInfo)

def checkCosignSignature(outp, pubk_byts, image_to_verify):
    with s_common.getTempDir() as dirn:
        # Write certificate out
        pubk_path = s_common.genpath(dirn, 'pubkey.pem')
        with s_common.genfile(pubk_path) as fd:
            fd.write(pubk_byts)

        # Do the image verification
        args = ('cosign', 'verify', "--rekor-url=''", '--insecure-ignore-sct', '--insecure-ignore-tlog',
                '--key', pubk_path, image_to_verify)
        try:
            proc = subprocess.run(args=args, capture_output=True)
            proc.check_returncode()
        except subprocess.CalledProcessError as e:  # pragma: no cover
            outp.printf(f'Error calling {" ".join(args)}: {e}')
            return None
        blob = s_json.loads(proc.stdout)
        outp.printf('Cosign output:')
        outp.printf(pprint.pformat(blob))
        return True

def main(argv, outp=s_outp.stdout):  # pragma: no cover
    pars = getArgParser()
    opts = pars.parse_args(argv)

    image_to_verify = opts.image
    outp.printf(f'Verifying: {image_to_verify}')

    if not checkCosign(outp):
        outp.printf('Failed to confirm cosign v2.x.x is available.')
        return 1

    sigd = getCosignSignature(outp, image_to_verify)
    if sigd is None:
        outp.printf(f'Failed to get signature for {image_to_verify}')
        return 1

    if opts.certdir:
        certpath = opts.certdir
    else:
        certpath = s_data.path('certs')
    outp.printf(f'Loading certdir from {certpath}')
    certdir = s_certdir.CertDir(path=(certpath,))

    pubk_byts = checkCRL(outp, sigd, certdir)
    if not pubk_byts:
        outp.printf(f'CRL check failed for {image_to_verify}')
        return 1
    outp.printf('Verified certificate embedded in the signature.')

    if not checkCosignSignature(outp, pubk_byts, image_to_verify):
        outp.printf(f'Failed to verify: {image_to_verify}')
        return 1
    outp.printf(f'Verified: {image_to_verify}')
    return 0

def getArgParser():  # pragma: no cover
    pars = argparse.ArgumentParser(description='Verify Docker images are signed by The Vertex Project.')
    pars.add_argument('--certdir', '-c', action='store', default=None,
                      help='Alternative certdir to use for signature verification.')
    pars.add_argument('image', help="Docker image to verify.")
    return pars

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
