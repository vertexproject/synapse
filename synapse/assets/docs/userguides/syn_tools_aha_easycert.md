<a id="syn-tools-aha_easycert"></a>

# aha.easycert

The Synapse `aha.easycert` tool can be used to generate simple X509 certificates from an AHA server.

## Syntax

`aha.easycert` is executed using `python -m synapse.tools.aha.easycert`. The command usage is as follows:

```text
python -m synapse.tools.aha.easycert -h
usage: synapse.tools.aha.easycert [-h] -a AHA [--certdir CERTDIR] [--server]
                                  [--server-sans SERVER_SANS]
                                  name

CLI tool to generate simple x509 certificates from an Aha server.

positional arguments:
  name                  common name for the certificate (or filename for CSR
                        signing)

options:
  -h, --help            show this help message and exit
  -a, --aha AHA         Aha server to connect too.
  --certdir CERTDIR     Directory for certs/keys
  --server              mark the certificate as a server
  --server-sans SERVER_SANS
                        server cert subject alternate names

```
