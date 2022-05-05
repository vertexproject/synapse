.. highlight:: none

.. _syn-tools-easycert:

easycert
========

The Synapse ``easycert`` tool can be used to manage CA, host, and user certificates.

Syntax
------

``easycert`` is executed using ``python -m synapse.tools.easycert``. The command usage is as follows::

    usage: easycert [-h] [--certdir CERTDIR] [--importfile {cas,hosts,users}] [--ca] [--p12] [--server] [--server-sans SERVER_SANS] [--csr] [--sign-csr] [--signas SIGNAS]
                    name

    Command line tool to generate simple x509 certs

    positional arguments:
      name                  common name for the certificate (or filename for CSR signing)

    optional arguments:
      -h, --help            show this help message and exit
      --certdir CERTDIR     Directory for certs/keys
      --importfile {cas,hosts,users}
                            import certs and/or keys into local certdir
      --ca                  mark the certificate as a CA/CRL signer
      --p12                 mark the certificate as a p12 archive
      --server              mark the certificate as a server
      --server-sans SERVER_SANS
                            server cert subject alternate names
      --csr                 generate a cert signing request
      --sign-csr            sign a cert signing request
      --signas SIGNAS       sign the new cert with the given cert name

