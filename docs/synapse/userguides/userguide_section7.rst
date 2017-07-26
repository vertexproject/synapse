
Data Model - Node Types
=======================

In `Data Model - Node Concepts`__ we saw that nodes can represent data such objects, relationships, and events. Synapse uses a set of common node (form) types to represent a broad range of information.

Simple Nodes
------------

A "simple" node is one that represents an atomic object or entity. "Simple" is an informal descriptor meant to convey that these types of nodes have a primary property that consists of a single ``<form>=<value>``; the "uniqueness" or “thinghood” of a simple form can be represented by a single element. In addition, simple forms are typically the most readily understood from a modeling perspective.

Even for simple nodes, it may still be possible (and desirable) to break the node's "basic" primary property into component parts so that those components are queryable or pivotable within the hypergraph. If Synapse can parse relevant subcomponents from the primary property, the associated secondary properties can be created automatically during node creation.

Examples of simple nodes include:

- **IP addresses.** An IP address (IPv4 or IPv6) must be unique within its address space and can be defined by the address itself (``inet:ipv4=1.2.3.4``). Secondary properties (depending on need) may include things like the associated Autonomous System Number (ASN), geolocation data, and whether the IP belongs to a specialized or reserved group (e.g., private, multicast, etc.)

- **Domains.** Similarly, an Internet domain must be globally unique (the same domain cannot be registered by two different entities) and can be defined by the domain string (``inet:fqdn=woot.com``). In this case, Synapse can parse the primary property and automatically create secondary properties for ``:host=woot`` and ``:domain=com``. Additional secondary properties may include whether the domain is a top-level domain (TLD).

- **Files.** Files are unique based on their content. Instead of doing a byte-by-byte comparison of content, files are typically "compared" by generating a hash of the file and comparing the hash of one file with the hash of another file; if the hashes match, the files are considered to be the same. However, improvements in both cryptanalysis and computational power have made hash collisions more likely – that is, it is possible to not only find but in some cases to deliberately generate two files with different content that nonetheless result in the same hash. Thus, some hash algorithms (MD5, and increasingly SHA1) that were once considered unique no longer are, and there is no guarantee that this trend will not eventually hold true for additional hash algorithms. Because no hash can be considered reliably unique, the primary property of a file is represented by a GUID (``file:bytes=<guid>``; specifically, Synapse stores the various hashes (MD5, SHA1, SHA256, SHA512) as secondary properties (if known), and generates a stable (deterministic) GUID from those hashes. For this reason a Synapse file:bytes GUID is sometimes referred to as a “superhash”).

  Additional secondary properties may include the file size in bytes or the file type (PE executable, plain text, etc.). Depending on analytical need, file type-specific secondary properties may also be defined (e.g., a compile date for PE executable, file-specific metadata for a JPEG or Word document, etc.)\
  
- **Organizations.** It is difficult to determine a unique characteristic for an organization (business, non-profit, government department, NGO). The organization name is one possibility, but names are not universally deconflicted – it is possible for more than one Acme Corporation to exist globally. Some type of business identification number is another possibility – a tax ID number, or a Dun & Bradstreet number, for example – but those may be country-specific and / or entity-specific (applying to businesses but not to government departments, for example). For these reasons, the primary property of an organization in the Synapse data model is represented by a randomly-generated GUID (``ou:org=<guid>``). Secondary properties may include an organization's name, its location / country of origin, or the URL of the organization's web site.

- **People.** Similar to an organization, it is difficult to determine a universally unique characteristic for a person. Names are not guaranteed to be unique, as there can easily be more than one John Smith in the world. The same problem occurs with date of birth (multiple people can share the same birth date), and even the combination of name and date of birth cannot be guaranteed to be unique. For this reason, a person is also represented by a randomly-generated GUID (``ps:person=<guid>``). Secondary properties may include the person's given, middle, and family names, date of birth, and so on.

*Aliases*

GUIDs are used as primary properties for forms which are not easily deconflictable (that is, which do not have readily identified characteristics that can serve as a unique primary property). For commonly used node types that are represented by GUIDs (such as organizations or people), it is impractical for an analyst to have to type (or even copy / paste) a GUID at the CLI every time they want to reference a given node. While nodes can be retrieved based on a more "human-friendly" secondary ``<prop>=<valu>`` (e.g., ``ou:org:alias=vertex``), even the need to enter a full secondary property / value may be inconvenient.

Synapse allows an **alias** to be defined as part of the type for the form's primary property. The alias is typically one of the form's secondary properties. For example, the Synapse data model defines the property ``ps:person:guidname`` as an alias for a person, and ``ou:org:alias`` as an alias for an organization. An example of the alias definition can be seen in this snippet of source code that defines the ``ou:org`` type (from ``orgs.py`` - emphasis added):
::
  def getBaseModels():
    modl = {
      'types': (
        ('ou:org', {'subof': 'guid', **'alias': 'ou:org:alias',**
              'doc': 'A GUID for a human organization such
              as a company or military unit'
        }),

Once defined in the data model, the alias property’s value preceded by a dollar sign ( ``$`` ) can be used as shorthand to refer to the node. The following statements are equivalent:
::
  ou:org=2f92bc913918f6598bcf310972ebf32e
  ou:org:alias=vertex
  ou:org=$vertex

Composite (Comp) Nodes
----------------------

A composite (comp) node is one where the primary property (that which makes the node unique or gives it "thinghood") cannot be defined by a single element. However, in many cases a node can be defined as unique based on the combination of two or more elements. This is true for many relationship nodes (which makes sense, given that in a directed graph an edge is a relationship that joins two objects). However, it is also true for objects whose "uniqueness" can be defined by multiple components (or by elements that are better referenced as separate entities instead of being artificially conflated as a single "property"). Comp nodes provide additional flexibility to the data model in that:

- The elements of the comp node’s primary property can be any data or data type; that is, they can be GUIDs, lengthy blocks of text, or even other comp forms or seprarator (sepr) forms (described below).

- Comp nodes may have primary properties that consist of a set of **required** elements as well as **optional** elements that can be included if known, or if an additional degree of granularity / uniqueness is required. For example, there may be cases where a form is defined as fully unique by a combination of five specific elements, but we may not always have data available to include all five. A subset of elements may be “sufficient” to create the comp node in the absence of complete data.

Synapse uses the following conventions for comp nodes:

- The elements of a comp node’s primary property are specified as a comma-separated ordered list within parentheses (e.g., ``<form>=(<element_1>,<element_2>,...<element_n>)``).

- Those elements that are mandatory for a given form must be present and listed in the order in which they are defined within the model. Since the mandatory elements are listed in their specified order, they can be listed by ``<value>`` alone.

- Optional elements can be included at the end of the list in the form ``<prop>=<value>``.

- While the "primary property" is comprised of multiple elements, the elements can vary widely in number, length, and complexity. For performance reasons, the real primary property (used to store, index and reference a comp node) is a GUID that is generated as a function of the set of elements specified on node creation. Note that because the comp node GUID is "seeded" by the set of unique elements themselves, the GUID is deterministic: the same set of elements will result in the same GUID, including across different Cortexes. (Contrast this with node identifier GUIDs or randomly generated GUIDs used as primary properties, such as for ``ps:person`` nodes or ``ou:org`` nodes – such GUIDs are not deterministic and may vary across Cortexes.)

For comp nodes, it is common to break out the individual elements of the primary property as secondary properties on the node so that they are searchable / pivotable. If Synapse can parse the values from the primary property, the secondary properties can be created automatically during node creation.

Examples of comp nodes include:

- **Suborganization / subsidiary.** The concept of "organization / sub-organization" (``ou:suborg``) is a straightforward relationship whose uniqueness is defined by the two entities involved. The relationship is generic enough that it can apply to a range of situations, from corporation and subsidiary to government and ministry within the government. The primary property consists of two elements, the GUID of the parent org (``ou:org``) and the GUID of the sub-org (``ou:org``).

- **Social networks.** Social networks are comprised of individuals who establish relationships with other individuals. Such relationships may be "one-way" (you can "follow" someone on Twitter) or "two-way" (you can mutually connect with someone on LinkedIn). The uniqueness of a social networking relationship (``inet:follows``) is defined by the individual user accounts involved. Even though there are only two elements that comprise the primary property, each of those elements is a complex node type (specifically, a sepr node defined by the service name and the username - e.g., ``inet:netuser=twitter.com/joeuser``). (Note that instead of creating two separate node types for "one-way" vs "two-way" social network connections, a "two-way" connection is represented by two "one-way" ``inet:follows`` nodes, with each user "following" the other.)

- **Bank or financial accounts.** A bank or financial account is another candidate for a comp node. In considering what makes an account unique, an account number alone is insufficient, as the number is only guaranteed unique within a single financial institution. An account number combined with the account owner's name seems like a possibility, although account ownership may change (e.g., an account may be transferred, or change from an individual to a joint account) and it is possible (however unlikely) that identical account numbers with identical owner names could exist at two different financial institutions. One option would be to combine the individual account number with a number that uniquely identifies the financial institution. Within the United States, this could be the institution's ABA routing number combined with the individual account number (note that ABA numbers are specific to US financial institutions, though other countries or regions may use similar systems).

  In designing a form to represent a financial account it is worth considering the knowledge domain along with analytical need to decide whether a single form should represent any / all financial accounts (regardless of country of origin or account type – banking, investing, etc.), or whether it is preferable to create different forms for different account types (e.g., one form for US investment accounts, a different form for German banking accounts, etc.). Secondary properties for consideration may include the account type; date(s) the account was opened or closed; known minimum / maximum account balances (similar to ``:seen:min`` and ``:seen:max`` for date ranges); interest rate, if any; and so on.
  
An example of a comp type with optional properties would be:

- **Files on computers.** In cases of host-based computer forensics or cyber threat data analysis, it may be necessary to represent that a file was present on a specific computer (as opposed to representing the “location-less” existence of a file as a ``file:bytes`` node). “Interesting” files could include malware or tools used by threat actors, cached web content (such as a copy of a web-based exploit), host-specific logs, or files that provide other evidence of malicious or illegal activity (e.g., copies of stolen data).

  In considering what makes a “file on a computer” (``it:hostfile``) unique from all other files on all other computers (or the same computer), it is clear that multiple elements are involved:

  - The computer (host) itself (``it:host``).
  - The path and file name (``file:path`` and / or ``file:base``).
  - The file itself (``file:bytes``).
  - Timestamps associated with the file (created, modified, accessed), which may be operating-system and / or file system specific.
  
  While it is possible to create a comp node whose primary property is the combination of all of those elements, there is another challenge. In computer forensic or computer intrusion investigations, evidence is rarely perfect; that is, we are not guaranteed to have all of the above data available. Depending on the source of our evidence (forensic images, host-based logs, antivirus logs, network logs), we may have information about path and filename but no bytes; or a copy of the bytes (say from network data showing a file was downloaded to the host) but no path data; or the path and bytes but no timestamps.
  
  If we require all of the elements listed to form our primary property, we enforce high fidelity in our data model, but prevent ourselves from creating nodes with “partial” data that may still prove highly valuable for analysis. Alternatives include:
  
  - Limit our primary property elements (for example, to ``it:host`` and ``file:bytes``) and include the other components as secondary properties. However, this does not really solve our problem for several reasons: a given set of bytes could exist at two different locations on the same host, so the combination of ``it:host`` and ``file:bytes`` are not unique; we may not always have the bytes (or a hash that could be used to represent the bytes); and things like the path that truly help define the “uniqueness” of a specific file on a specific host don’t belong as secondary properties.
  - Create multiple node types to represent various combinations of the above data. However, this leads to a plethora of forms that are essentially duplicative.
  
  Instead of multiplying node types to account for different combinations of data, we can leverage a single comp type node (form) but make some of the elements of the primary property optional. In considering what element(s) are essential to the concept of “a file on a computer” (``it:hostfile``), the only element that is absolutely **required** is the computer (``it:host``). (This makes sense if you think about it; in the absence of a computer, a file is just a file (``file:bytes``).) While it would be rare to create an ``it:hostfile`` node without **any** reference to the file itself, the information we have on the file may vary - we may have the filename or path (``file:base``, ``file:path``), the actual bytes (a ``file:bytes`` node with a complete “superhash” GUID), or simply a hash value (a ``file:bytes:<hash>`` secondary property that will be used to create a GUID based on the available hash). So none of those other properties can be considered to be **required**, but they can be included if the data is available.

*Comp node optional elements and node uniqueness*

Recall that while a comp node’s “primary property” (that which makes it unique) is a combination of two or more elements, the actual primary property stored and referenced in Synapse is a GUID generated as a function of the individual elements specified at the time the node is created. So if you have ``<form>=(foo,bar,baz)`` the GUID is a function of ``foo``, ``bar``, and ``baz``. The function is deterministic, so the same set of elements will always generate the same GUID.
  
This has implications for the data model when some of the elements are optional. Let’s say you have a comp node ``<form>=(foo,bar,baz,hurr,derp)`` where ``foo`` is required but the remaining elements are **optional**. If, when you first create the node, you only know ``foo``, the node GUID will be based only on ``foo``.  Once created, a node’s primary property cannot be changed; so if you later identify ``baz``, you can’t simply “add” it to the existing comp node; you would need to create a second comp node comprised of ``foo`` and ``baz``, which would generate a different GUID based on the combination of the two elements. If you later learn ``bar`` and ``derp``, a node created from ``foo``, ``bar``, ``baz``, and ``derp`` would have yet another GUID.
  
To provide a more concrete example, consider the ``it:hostfile`` node described above. Let’s say initially you determine that a suspicious file existed at the path ``C:\WINDOWS\system32\scvhost.exe`` on host ``MYHOST``. You create the initial ``it:hostfile`` node based on those two properties, and Synapse generates the GUID ``671993b20eb292dbd1dec63cbd26d3ce`` based on those properties. In the course of your analysis, you tag the ``it:hostfile`` node as being associated with Threat Group 12 (``#tc.t12``).
  
You later recover the actual file bytes for ``somefile.dll``, a ``file:bytes`` node with the GUID (“superhash”) ``d385c823f1f5c64b5cec20c9e04adb32``. You can’t add the ``file:bytes`` element (an optional component of the ``it:hostfile`` node’s primary property) to the existing node, so a new ``it:hostfile`` node is created with a different GUID based on the combination of the host (the GUID from the ``it:host`` MYHOST), the path, and the ``file:bytes`` GUID. The new node has “higher resolution” (more information, greater specificity), but the two nodes are not automatically “combined” by Synapse, and tags on the existing node (such as the ``#tc.t12`` tag) are not automatically copied over to the new node.
  
(Note that **not** copying the tags may be a good thing; perhaps both Threat Group 12 and Threat Group 35 have used the path ``C:\WINDOWS\system32\scvhost.exe`` - not an unreasonable assumption, as use of ``scvhost.exe`` to masquerade as the legitimate ``svchost.exe`` is fairly common. Perhaps both groups even used the same path on the same host at different times during a three-year period. But only the specific file (``file:bytes``) located at that specific path on that specific host is associated with Threat Group 12. In that case, it might be reasonable to tag the ``it:hostfile`` node based on the host and path alone with both ``#tc.t12`` and ``#tc.t35`` (both groups have used that exact path on that exact host), but the ``it:hostfile`` node based on the host, path, and specific file with ``#tc.t12`` (only Threat Group 12 has used that exact file at that exact path on that exact host).
  
A similar issue exists for ``file:bytes`` nodes. While not a true comp type node, the primary property GUID of a ``file:bytes`` node is based on the combination of the file’s MD5, SHA1, SHA256, and SHA512 hashes. In other words, the GUID is generally meant to be generated based on having an actual copy of the file (the actual bytes) where the four hashes can be calculated and used to create a “complete” GUID.
  
However, in some cases you may know one of the hashes - say the ``file:bytes:md5`` hash referenced in third-party reporting or log data - but not have the actual bytes. Synapse will still create a ``file:bytes`` node but the GUID will be generated based on the MD5 hash alone. If the bytes are later obtained, Synapse will create a different node with a different GUID for the “actual” bytes based on all four hashes.

Analysts and developers should be aware of these restrictions. The use of optional elements in a comp node allows for the greatest flexibility, particularly in cases where available data for a given form may vary; but it does have implications for analysis, and in particular for tagging nodes, that must be taken into account.
  
Cross-Reference (Xref) Nodes
----------------------------

As noted in `Data Model Concepts`_, the model should be "self-evident" to the extent possible: nodes and tags should be well designed and unambiguous. In addition, it is preferable for data in the hypergraph to consist of original or verifiable source material where possible. This follows the general analytical principle of primary sources: you can best verify your own data (or other original data) and related analysis. Third-party reporting raises questions of source reliability, accuracy, and so on.

However, it is both impractical and unrealistic to assume that all data in a hypergraph can be originally sourced. Almost all analysis relies on some amount of research by others; this is why research papers provide references and cite sources. Synapse supports a similar concept, allowing an analyst to show that a data point or analytical observation came from a third-party source, and reference a copy of that source material within the hypergraph itself. This is done through a specialized type called an xref (short for "cross-reference"), which allows you to demonstrate that one object "references" another. Examples would be a photograph (``file:bytes``) "referencing" (containing) an image of a person (``ps:person``) or a particular place (``geo:place``); or a document (``file:bytes``) referencing anything from an atomic object (a security report referencing a malicious domain (``inet:fqdn``)) to a particular assertion (a news article noting that Acme Corporation was in merger talks with Widgets, Inc. in March 2016).

An xref node can be thought of as a specialized type of “relationship” node. The relationship nodes discussed previously can be clearly defined because the participants in the relationship are known in advance: a DNS A record consists of a domain (``inet:fqdn``) pointing to an IP address (``inet:ipv4``). Because those forms are known, they can be specified in the data model (form) for the ``inet:dns:a`` record, and that form can be represented as a sepr or comp node (in this case, a sepr node).

With a “references” relationship, the participants are not known in advance. A file (``file:bytes``) such as a report, a news article, or a photograph, can “reference” an unlimited number of things. The form of one of the participants (the “thing referenced”) may be arbitrary. One option is to create multiple comp nodes to define each possible type of relationship: ``file:bytes`` references ``inet:fqdn``, ``file:bytes`` references ``geo:place``, ``file:bytes`` references ``ps:person``, etc. However it should be clear that this becomes inefficient if a new form needs to be defined every time a new “thing” needs to be referenced.

A better solution is the xref node, which provides the flexibility to “reference” any type of object. An xref node’s primary property consists of:

- the primary property of the "thing" referencing another thing (e.g., ``file:bytes``);
- the **form** of the thing being referenced (so Synapse knows whether the referenced object is a domain, a hash, a person, an airplane, a specific airplane, etc.)
- the primary property of the "thing" being referenced.
 
The Synapse data model currently includes two predefined xref-type nodes:

- file:imgof (a file contains an image of something)
- file:txtref (a file contains a "text reference" to something)

Similar to comp nodes, the elements of an xref node’s primary property are specified as a comma-separated ordered list within parentheses (e.g., ``<form>=(<element_1>,<element_2>,...<element_n>)``).

Separator (sepr) Nodes
----------------------

**Separator (sepr) nodes pre-dated composite (comp) nodes and are subject to certain limitations that were addressed with the comp node type. While some legacy sepr forms exist within the Synapse data model, comp nodes are preferred for future development.**

Sepr nodes are an early type of node that was developed to represent nodes with multi-element primary properties. They can be considered a subset of comp nodes and have been superseded by comp nodes. They are described here for completeness and to address some of the legacy forms present within the Synapse data model.

Synapse uses the following conventions for sepr nodes:

- Sepr nodes have primary properties that consist of two or more elements. (Most, if not all, sepr forms defined within Synapse to date consist of two elements.)
- The elements of the primary property are separated with a designated character specified in the data model. Note that this imposes the restriction that whatever character is used as the separator cannot appear in any element of the primary property. (Comp nodes use  a comma-separated list, which removes this “special character” limitation.)
  
  By convention, Synapse most often uses a forward slash ( ``/`` ) as the separator character (though pipe ( ``|`` ) and at ( ``@`` ) are also used). If no character is specified, the model defaults to a comma ( ``,`` ).

- The elements of a sepr primary property should be "human readable" (and therefore "human type-able", such as at the CLI). The primary property of a sepr node is the string consisting of ``<value><separator_character><value>``. (Comp node elements can be any data or data type and the true primary property is a GUID generated from the individual elements).

Similar to comp nodes, it is common to break out the individual elements of the primary property of a sepr node as secondary properties on the node so that they are searchable / pivotable. If Synapse can parse the values from the primary property, the secondary properties can be created automatically during node creation.

Examples of sepr nodes include:

- **DNS A records.** A domain having a DNS A record for an IP address is a straightforward relationship. Within Synapse, this relationship has been defined as a sepr node (``inet:dns:a``) that consists of the unique combination of domain and IP address separated by a forward slash (``inet:dns:a=woot.com/1.2.3.4``). Synapse is able to parse the domain and IP address from the primary property and automatically create them as secondary properties (``inet:dns:a:fqdn=woot.com`` and ``inet:dns:a:ipv4=1.2.3.4``).

  In cases where secondary properties are themselves forms (``inet:dns:a:fqdn`` is form ``inet:fqdn``; ``inet:dns:a:ipv4`` is form ``inet:ipv4``), Synapse will automatically create nodes for those forms if they do not already exist. In other words, ``inet:fqdn=woot.com`` and ``inet:ipv4=1.2.3.4`` do not need to already exist in the Cortex or be created manually before you can create ``inet:dns:a=woot.com/1.2.3.4``.

- **Social media or Internet service accounts.** Service accounts are an example of an "object" type node that requires two components to uniquely define the node. A username by itself is not unique because someone (or two different people) could have the same username on two different services (such as LinkedIn and Twitter). However, usernames typically must be unique within a given service, so Synapse uses both elements (the service and the username, separated by a forward slash) to uniquely define an account (``inet:netuser=twitter.com/joeuser``). Similar to the previous example, Synapse is able to parse the service and username from the primary property and automatically create secondary properties for these elements (``inet:netuser:site=twitter.com``, ``inet:netuser:user=joeuser``).

  Other secondary properties may depend on the types of account(s) being tracked and the specific analytical need. User profile data available from a given service may vary widely depending on the service purpose (software development site vs. cloud storage service vs. social media) or on geography or culture. For example, some Asian web sites allow users to post their blood type, while western web sites may allow users to post their zodiacal sign; within different cultures, both are believed to reflect an individual's personality.




.. _Concepts: ../userguide_section5.html
__ Concepts_
.. _ModelConcepts: ../userguide_section4.html
