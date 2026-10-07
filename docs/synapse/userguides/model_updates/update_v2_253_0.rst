

.. _userguide_model_v2_253_0:

######################
v2.253.0 Model Updates
######################

The following model updates were made during the ``v2.253.0`` Synapse release.

**************
New Properties
**************

``transport:air:telem``
  The form had the following property added to it:

  ``vehicle``
    The aircraft being measured.



*************
Updated Types
*************

``inet:dns:query``
  The type has been modified from {'fields': [['client', 'inet:client'],
  ['name', 'inet:dns:name'], ['type', 'int']]} to {'fields': [['client',
  'inet:client'], ['name', 'inet:dns:name'], ['type', ['int', {'enums': [[1,
  'A'], [2, 'NS'], [3, 'MD'], [4, 'MF'], [5, 'CNAME'], [6, 'SOA'], [7, 'MB'],
  [8, 'MG'], [9, 'MR'], [10, 'NULL'], [11, 'WKS'], [12, 'PTR'], [13, 'HINFO'],
  [14, 'MINFO'], [15, 'MX'], [16, 'TXT'], [17, 'RP'], [18, 'AFSDB'], [19,
  'X25'], [20, 'ISDN'], [21, 'RT'], [22, 'NSAP'], [23, 'NSAP-PTR'], [24,
  'SIG'], [25, 'KEY'], [26, 'PX'], [27, 'GPOS'], [28, 'AAAA'], [29, 'LOC'],
  [30, 'NXT'], [31, 'EID'], [32, 'NIMLOC'], [33, 'SRV'], [34, 'ATMA'], [35,
  'NAPTR'], [36, 'KX'], [37, 'CERT'], [38, 'A6'], [39, 'DNAME'], [40, 'SINK'],
  [41, 'OPT'], [42, 'APL'], [43, 'DS'], [44, 'SSHFP'], [45, 'IPSECKEY'], [46,
  'RRSIG'], [47, 'NSEC'], [48, 'DNSKEY'], [49, 'DHCID'], [50, 'NSEC3'], [51,
  'NSEC3PARAM'], [52, 'TLSA'], [53, 'SMIMEA'], [55, 'HIP'], [56, 'NINFO'], [57,
  'RKEY'], [58, 'TALINK'], [59, 'CDS'], [60, 'CDNSKEY'], [61, 'OPENPGPKEY'],
  [62, 'CSYNC'], [63, 'ZONEMD'], [64, 'SVCB'], [65, 'HTTPS'], [99, 'SPF'],
  [100, 'UINFO'], [101, 'UID'], [102, 'GID'], [103, 'UNSPEC'], [104, 'NID'],
  [105, 'L32'], [106, 'L64'], [107, 'LP'], [108, 'EUI48'], [109, 'EUI64'],
  [249, 'TKEY'], [250, 'TSIG'], [251, 'IXFR'], [252, 'AXFR'], [253, 'MAILB'],
  [254, 'MAILA'], [255, 'ANY'], [256, 'URI'], [257, 'CAA'], [258, 'AVC'], [259,
  'DOA'], [260, 'AMTRELAY'], [261, 'RESINFO'], [262, 'WALLET'], [263, 'CLA'],
  [264, 'IPN'], [32768, 'TA'], [32769, 'DLV']], 'enums:strict': False}]]]}.



******************
Updated Properties
******************

``inet:dns:query``
  The form had the following property updated:


    The property ``type`` has been modified to add string enums for
    DNS query types.


``inet:dns:request``
  The form had the following property updated:


    The property ``query:type`` has been modified to add string enums for
    DNS query types.


``it:reveng:filefunc``
  The form had the following property updated:


    The property ``complexity`` has been modified to add string enums for
    common complexity labels.

