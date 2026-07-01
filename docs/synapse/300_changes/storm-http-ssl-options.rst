.. _vtx_300_storm-http-ssl-options:

HTTP/Axon SSL Option Changes
============================

The ``$lib.inet.http`` request methods no longer accept the separate ``ssl_verify``
boolean and ``ssl_opts`` dictionary arguments. All TLS settings are now passed through
a single ``ssl`` dictionary argument.

What changed
    In 2.x, the ``$lib.inet.http`` request methods (``get``, ``post``, ``head``,
    ``request``, ``connect``) accepted a ``ssl_verify`` boolean keyword argument and a
    separate ``ssl_opts`` dictionary keyword argument. In 3.0.0 both are removed and
    replaced by a single ``ssl`` dictionary argument. The boolean previously passed as
    ``ssl_verify`` is now the ``verify`` key inside that dictionary.

    The ``ssl`` dictionary supports the following keys: ``verify`` (boolean, default
    ``true``), ``client_cert`` (PEM encoded full chain certificate for mTLS),
    ``client_key`` (PEM encoded key for mTLS, may instead be included in
    ``client_cert``), and ``ca_cert`` (PEM encoded full chain CA certificate used when
    verifying the request). The same ``ssl`` dictionary is forwarded to the Axon when a
    request includes a ``fields`` entry containing a ``sha256`` (the request is sent from
    the Axon to upload the corresponding file as the field value).

Why
    Consolidating the TLS settings into one dictionary removes the overlap between the
    old ``ssl_verify`` boolean and the ``ssl_opts`` dictionary (where ``ssl_verify``
    overrode the dictionary's ``verify`` key) and provides a single extensible argument
    for current and future SSL/TLS options.

What you need to do
    Replace every ``ssl_verify=$x`` with ``ssl=({"verify": $x})`` in your
    ``$lib.inet.http.*`` calls in Storm, macros, and power-ups. If you previously passed
    a ``ssl_opts`` dictionary, pass those same keys in the ``ssl`` dictionary instead
    (and fold any ``ssl_verify`` value into its ``verify`` key).

    ::

        // 2.x -- boolean argument
        $resp = $lib.inet.http.get($url, ssl_verify=$verify)

        // 3.x -- ssl options dict
        $resp = $lib.inet.http.get($url, ssl=({"verify": $verify}))

    To disable verification:

    ::

        // 2.x
        $resp = $lib.inet.http.get($url, ssl_verify=(false))

        // 3.x
        $resp = $lib.inet.http.get($url, ssl=({"verify": (false)}))

    To migrate a 2.x ``ssl_opts`` dictionary, merge it (and any ``ssl_verify`` value)
    into the new ``ssl`` argument:

    ::

        // 2.x
        $resp = $lib.inet.http.get($url, ssl_verify=(true), ssl_opts=({"ca_cert": $ca}))

        // 3.x
        $resp = $lib.inet.http.get($url, ssl=({"verify": (true), "ca_cert": $ca}))
