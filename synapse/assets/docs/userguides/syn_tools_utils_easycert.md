<a id="syn-tools-utils-easycert"></a>

# utils.easycert

The Synapse `utils.easycert` tool can be used to manage CA, host, and user certificates.

## Syntax

`utils.easycert` is executed using `python -m synapse.tools.utils.easycert`. The command usage is as follows:

```text
python -m synapse.tools.utils.easycert -h
usage: synapse.tools.utils.easycert [-h] [--certdir CERTDIR]
                                    [--importfile {cas,hosts,users}] [--ca]
                                    [--crl] [--p12] [--code] [--server]
                                    [--server-sans SERVER_SANS] [--csr]
                                    [--sign-csr] [--signas SIGNAS]
                                    [--revokeas REVOKEAS]
                                    name

Command line tool to generate simple x509 certs

positional arguments:
  name                  common name for the certificate (or filename for CSR
                        signing)

options:
  -h, --help            show this help message and exit
  --certdir CERTDIR     Directory for certs/keys
  --importfile {cas,hosts,users}
                        import certs and/or keys into local certdir
  --ca                  mark the certificate as a CA/CRL signer
  --crl                 Generate a new CRL for the given CA name.
  --p12                 mark the certificate as a p12 archive
  --code                mark the certificate for use in code signing.
  --server              mark the certificate as a server
  --server-sans SERVER_SANS
                        server cert subject alternate names
  --csr                 generate a cert signing request
  --sign-csr            sign a cert signing request
  --signas SIGNAS       sign the new cert with the given cert name
  --revokeas REVOKEAS   Revoke a cert as the given CA and add it to the CSR.
```

> [!NOTE]
> This tool was previously run using `synapse.tools.easycert`. It can still be run with that name.
