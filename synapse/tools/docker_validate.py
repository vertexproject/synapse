import os
import re
import sys
import json
import base64
import subprocess

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.output as s_outp
import synapse.lib.certdir as s_certdir

from OpenSSL import crypto

def checkCosign(outp):
    args = ('cosign', 'version')
    try:
        proc = subprocess.run(args, capture_output=True)
        proc.check_returncode()
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        outp.printf(f'Error calling {" ".join(args)}: {e}')
        return False

    stderr = proc.stderr.decode()
    if 'GitVersion' not in stderr:
        outp.printf('Cannot find GitVersion in output:')
        outp.printf(stderr)
        return 1

    vline = [line for line in stderr.splitlines() if line.startswith('GitVersion')][0]
    if re.search('v2\\.[0-9]+\\.[0-9]+', vline):
        outp.printf(f'Using Cosign with {vline}')
        return True

    outp.printf('Found cosign version 2.x.x in "{vline}"')
    return False

def getCosignSignature(outp, image):
    args = ('cosign', 'download', 'signature', image)
    try:
        proc = subprocess.run(args, capture_output=True)
        proc.check_returncode()
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        outp.printf(f'Error calling {" ".join(args)}: {e}')
        return None

    blob = proc.stdout
    try:
        sigd = json.loads(blob)
    except json.JSONDecodeError as e:
        outp.printf(f'Error decoding blob: {blob}: {e}')
        return None
    if not isinstance(sigd, dict):
        outp.printf(f'Expected dictionary, got {sigd} from {blob}')
        return None

    from pprint import pprint
    pprint(sigd)

    return sigd

def checkCRL(outp, sigd, certdir):
    # Extract signing certificate; ensure that it is not revoked according to our CRL

    byts = base64.b64decode(sigd.get('Cert', {}).get('Raw', ''))

    try:
        cert = crypto.load_certificate(crypto.FILETYPE_ASN1, byts)
        pem_byts = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    except crypto.Error as e:
        # Unwrap pyopenssl's exception_from_error_queue
        estr = ''
        for argv in e.args:
            if estr:  # pragma: no cover
                estr += ', '
            estr += ' '.join((arg for arg in argv[0] if arg))
        outp.printf(f'Failed to load signature bytes: {byts}')
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

    return pem_byts

def main(argv, outp=s_outp.stdout):
    outp.printf(f'{argv}')

    # image
    image_to_verify = argv[0]

    if not checkCosign(outp):
        outp.printf('Failed to confirm cosign v2.x.x is available.')
        return 1

    sigd = getCosignSignature(outp, image_to_verify)
    if sigd is None:
        outp.printf(f'Failed to get signature for {image_to_verify}')
        return 1

    syncerts = s_data.path('certs')
    certdir = s_certdir.CertDir(path=(syncerts,))

    cert_byts = checkCRL(outp, sigd, certdir)
    if not cert_byts:
        outp.printf(f'CRL check failed for {image_to_verify}')
        return 1

    # Save the data to disk, extract annotations, verify the image signature

    # Confirm we have cosign available?
    # consirm we have docker available?
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
