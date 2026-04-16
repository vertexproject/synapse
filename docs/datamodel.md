# Synapse Data Model

## Table of Contents

- [Forms](#forms)
- [Edges](#edges)
- [Tag Properties](#tag-properties)
- [Interfaces](#interfaces)

## Forms

### `auth:passwd`

A password string.

| Interface |
|-----------|
| `auth:credential` |
| `crypto:hashable` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:md5` | `crypto:hash:md5` | The MD5 hash of the password. |
| `:seen` | `ival` | The password was observed during the time interval. |
| `:sha1` | `crypto:hash:sha1` | The SHA1 hash of the password. |
| `:sha256` | `crypto:hash:sha256` | The SHA256 hash of the password. |

### `belief:system`

A belief system such as an ideology, philosophy, or religion.

| Interface |
|-----------|
| `meta:believable` |

| Property | Type | Doc |
|----------|------|-----|
| `:began` | `time` | The time that the belief system was first observed. |
| `:desc` | `text` | A description of the belief system. |
| `:name` | `base:name` | The name of the belief system. |
| `:type` | `belief:system:type:taxonomy` | A taxonometric type for the belief system. |

### `belief:system:type:taxonomy`

A hierarchical taxonomy of belief system types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `belief:system:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `belief:tenet`

A concrete tenet potentially shared by multiple belief systems.

| Interface |
|-----------|
| `meta:believable` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the tenet. |
| `:name` | `base:name` | The name of the tenet. |

### `biz:deal`

A sales or procurement effort in pursuit of a purchase.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |
| `meta:negotiable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this activity. |
| `:buyer` | `entity:actor` | The buyer. |
| `:buyer:name` | `entity:name` | The name of the buyer. |
| `:contacted` | `time` | The last time the contacts communicated about the deal. |
| `:id` | `base:id` | An identifier for the deal. |
| `:name` | `base:name` | The name of the deal. |
| `:period` | `ival` | The period over which the activity occurred. |
| `:seller` | `entity:actor` | The seller. |
| `:seller:name` | `entity:name` | The name of the seller. |
| `:status` | `biz:deal:status:taxonomy` | The status of the deal. |
| `:type` | `biz:deal:type:taxonomy` | The type of deal. |
| `:updated` | `time` | The last time the deal had a significant update. |

### `biz:deal:status:taxonomy`

A hierarchical taxonomy of deal status values.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `biz:deal:status:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `biz:deal:type:taxonomy`

A hierarchical taxonomy of deal types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `biz:deal:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `biz:listing`

A product or service being listed for sale.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this listing. |
| `:actor` | `entity:actor` | The actor who carried out the listing. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the listing. |
| `:count:remaining` | `int` | The current remaining number of instances for sale. |
| `:count:total` | `int` | The number of instances for sale. |
| `:name` | `base:name` | The name or title of the listing. |
| `:period` | `ival` | The period over which the listing occurred. |
| `:price` | `econ:price` | The asking price of the product or service. |

### `biz:model`

A model name or number for a product.

### `biz:product`

A type of product which is available for purchase.

| Interface |
|-----------|
| `entity:creatable` |
| `meta:havable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the product was created. |
| `:creator` | `entity:actor` | The primary actor which created the product. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the product. |
| `:desc` | `text` | A description of the product. |
| `:launched` | `time` | The time the product was first made available. |
| `:name` | `base:name` | The name of the product. |
| `:owner` | `entity:actor` | The current owner of the product. |
| `:owner:name` | `entity:name` | The name of the current owner of the product. |
| `:price` | `econ:price` | The price of the product. |
| `:type` | `biz:product:type:taxonomy` | The type of product. |

### `biz:product:type:taxonomy`

A hierarchical taxonomy of product types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `biz:product:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `biz:rfp`

An RFP (Request for Proposal) soliciting proposals.

| Interface |
|-----------|
| `doc:authorable` |
| `doc:document` |
| `doc:published` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:body` | `text` | The text of the RFP. |
| `:created` | `time` | The time that the RFP was created. |
| `:creator` | `entity:actor` | The primary actor which created the RFP. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the RFP. |
| `:desc` | `text` | A description of the RFP. |
| `:due:proposal` | `time` | The date/time that proposals are due. |
| `:due:questions` | `time` | The date/time that questions are due. |
| `:file` | `file:bytes` | The file containing the RFP contents. |
| `:file:captured` | `time` | The time when the file content was captured. |
| `:file:name` | `file:base` | The name of the file containing the RFP contents. |
| `:id` | `base:id` | The RFP ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the RFP. |
| `:public` | `bool` | Set to true if the RFP is publicly available. |
| `:published` | `time` | The time the RFP was published. |
| `:publisher` | `entity:actor` | The entity which published the RFP. |
| `:publisher:name` | `entity:name` | The name of the entity which published the RFP. |
| `:status` | `biz:deal:status:taxonomy` | The status of the RFP. |
| `:supersedes` | `array of biz:rfp` | An array of RFP versions which are superseded by this RFP. |
| `:title` | `str` | The title of the RFP. |
| `:topics` | `array of meta:topic` | The topics discussed in the RFP. |
| `:type` | `biz:rfp:type:taxonomy` | The type of RFP. |
| `:updated` | `time` | The time that the RFP was last updated. |
| `:url` | `inet:url` | The URL where the RFP is available. |
| `:version` | `it:version` | The version of the RFP. |

### `biz:rfp:type:taxonomy`

A hierarchical taxonomy of RFP types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `biz:rfp:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `biz:service`

A service offered by an actor.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this service offering. |
| `:actor` | `entity:actor` | The actor who carried out the service offering. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the service offering. |
| `:desc` | `text` | A description of the service. |
| `:name` | `base:name` | The name of the service being performed. |
| `:period` | `ival` | The period of time when the actor made the service available. |
| `:type` | `biz:service:type:taxonomy` | A taxonomy of service types. |

### `biz:service:type:taxonomy`

A hierarchical taxonomy of service types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `biz:service:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `crypto:algorithm`

A cryptographic algorithm name.

### `crypto:currency:address`

An individual crypto currency address.

| Interface |
|-----------|
| `econ:pay:instrument` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The account contains the funds used by the instrument. |
| `:coin` | `econ:currency` | The crypto coin to which the address belongs. |
| `:contact` | `entity:contactable` | The primary contact information associated with the crypto currency address. |
| `:desc` | `str` | A free-form description of the address. |
| `:iden` | `str` | The coin specific address identifier. |
| `:seed` | `crypto:key` | The cryptographic key and or password used to generate the address. |
| `:seen` | `ival` | The crypto currency address was observed during the time interval. |

### `crypto:currency:block`

An individual crypto currency block record on the blockchain.

| Property | Type | Doc |
|----------|------|-----|
| `:coin` | `econ:currency` | The coin/blockchain this block resides on. |
| `:hash` | `hex` | The unique hash for the block. |
| `:minedby` | `crypto:currency:address` | The address which mined the block. |
| `:offset` | `int` | The index of this block. |
| `:time` | `time` | Time timestamp embedded in the block by the miner. |

### `crypto:currency:client`

A fused node representing a crypto currency address used by an Internet client.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:coinaddr` | `crypto:currency:address` | The crypto currency address observed in use by the Internet client. |
| `:inetaddr` | `inet:client` | The Internet client address observed using the crypto currency address. |
| `:seen` | `ival` | The crypto currency address and Internet client was observed during the time interval. |

### `crypto:currency:transaction`

An individual crypto currency transaction recorded on the blockchain.

| Property | Type | Doc |
|----------|------|-----|
| `:block` | `crypto:currency:block` | The block which records the transaction. |
| `:contract:input` | `file:bytes` | Input value to a smart contract call. |
| `:contract:output` | `file:bytes` | Output value of a smart contract call. |
| `:desc` | `str` | An analyst specified description of the transaction. |
| `:eth:gaslimit` | `int` | The ETH gas limit specified for this transaction. |
| `:eth:gasprice` | `econ:price` | The gas price (in ETH) specified for this transaction. |
| `:eth:gasused` | `int` | The amount of gas used to execute this transaction. |
| `:fee` | `econ:price` | The total fee paid to execute the transaction. |
| `:from` | `crypto:currency:address` | The source address of the transaction. |
| `:hash` | `hex` | The unique transaction hash for the transaction. |
| `:status:code` | `int` | A coin specific status code which may represent an error reason. |
| `:status:message` | `str` | A coin specific status message which may contain an error reason. |
| `:success` | `bool` | Set to true if the transaction was successfully executed and recorded. |
| `:time` | `time` | The time this transaction was initiated. |
| `:to` | `crypto:currency:address` | The destination address of the transaction. |
| `:value` | `econ:price` | The total value of the transaction. |

### `crypto:hash:md5`

A hex encoded MD5 hash.

| Interface |
|-----------|
| `crypto:hash` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The MD5 was observed during the time interval. |

### `crypto:hash:sha1`

A hex encoded SHA1 hash.

| Interface |
|-----------|
| `crypto:hash` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The SHA1 was observed during the time interval. |

### `crypto:hash:sha256`

A hex encoded SHA256 hash.

| Interface |
|-----------|
| `crypto:hash` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The SHA256 was observed during the time interval. |

### `crypto:hash:sha384`

A hex encoded SHA384 hash.

| Interface |
|-----------|
| `crypto:hash` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The SHA384 was observed during the time interval. |

### `crypto:hash:sha512`

A hex encoded SHA512 hash.

| Interface |
|-----------|
| `crypto:hash` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The SHA512 was observed during the time interval. |

### `crypto:key:base`

A generic cryptographic key.

| Interface |
|-----------|
| `crypto:key` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:algorithm` | `crypto:algorithm` | The cryptographic algorithm which uses the key material. |
| `:bits` | `int:min1` | The number of bits of key material. |
| `:private:hashes` | `array of crypto:hash` | An array of hashes for the private key. |
| `:public:hashes` | `array of crypto:hash` | An array of hashes for the public key. |
| `:seen` | `ival` | The key was observed during the time interval. |

### `crypto:key:dsa`

A DSA public/private key pair.

| Interface |
|-----------|
| `crypto:key` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:algorithm` | `crypto:algorithm` | The cryptographic algorithm which uses the key material. |
| `:bits` | `int:min1` | The number of bits of key material. |
| `:private` | `hex` | The HEX encoded private portion of the DSA key. |
| `:private:hashes` | `array of crypto:hash` | An array of hashes for the private key. |
| `:public` | `hex` | The HEX encoded public portion of the DSA key. |
| `:public:g` | `hex` | The HEX encoded generator or "G" component of the DSA key. |
| `:public:hashes` | `array of crypto:hash` | An array of hashes for the public key. |
| `:public:p` | `hex` | The HEX encoded public modulus or "P" component of the DSA key. |
| `:public:q` | `hex` | The HEX encoded subgroup order or "Q" component of the DSA key. |
| `:seen` | `ival` | The DSA key pair was observed during the time interval. |

### `crypto:key:ecdsa`

An ECDSA public/private key pair.

| Interface |
|-----------|
| `crypto:key` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:algorithm` | `crypto:algorithm` | The cryptographic algorithm which uses the key material. |
| `:bits` | `int:min1` | The number of bits of key material. |
| `:curve` | `base:name` | The curve standard in use. |
| `:private` | `hex` | The HEX encoded private portion of the ECDSA key. |
| `:private:hashes` | `array of crypto:hash` | An array of hashes for the private key. |
| `:public` | `hex` | The HEX encoded public portion of the ECDSA key. |
| `:public:a` | `hex` | The HEX encoded first coefficient or "a" component of the ECDSA key. |
| `:public:b` | `hex` | The HEX encoded second coefficient or "b" component of the ECDSA key. |
| `:public:gx` | `hex` | The HEX encoded x-coordinate of the generator or "Gx" component of the ECDSA key. |
| `:public:gy` | `hex` | The HEX encoded y-coordinate of the generator or "Gy" component of the ECDSA key. |
| `:public:h` | `hex` | The HEX encoded cofactor or "h" component of the ECDSA key. |
| `:public:hashes` | `array of crypto:hash` | An array of hashes for the public key. |
| `:public:n` | `hex` | The HEX encoded order of the generator or "n" component of the ECDSA key. |
| `:public:p` | `hex` | The HEX encoded prime modulus or "p" component of the ECDSA key. |
| `:public:x` | `hex` | The HEX encoded x-coordinate of the public key point or "x" component of the ECDSA key. |
| `:public:y` | `hex` | The HEX encoded y-coordinate of the public key point or "y" component of the ECDSA key. |
| `:seen` | `ival` | The ECDSA key pair was observed during the time interval. |

### `crypto:key:rsa`

An RSA public/private key pair.

| Interface |
|-----------|
| `crypto:key` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:algorithm` | `crypto:algorithm` | The cryptographic algorithm which uses the key material. |
| `:bits` | `int:min1` | The number of bits of key material. |
| `:private:coefficient` | `hex` | The private coefficient of the RSA key. |
| `:private:exponent` | `hex` | The private exponent of the RSA key. |
| `:private:hashes` | `array of crypto:hash` | An array of hashes for the private key. |
| `:private:primes` | `array of crypto:key:rsa:prime` | The prime number and exponent combinations used to generate the RSA key. |
| `:public:exponent` | `hex` | The public exponent of the RSA key. |
| `:public:hashes` | `array of crypto:hash` | An array of hashes for the public key. |
| `:public:modulus` | `hex` | The public modulus of the RSA key. |
| `:seen` | `ival` | The RSA key pair was observed during the time interval. |

### `crypto:key:rsa:prime`

A prime value and exponent used to generate an RSA key.

| Property | Type | Doc |
|----------|------|-----|
| `:exponent` | `hex` | The hex encoded exponent. |
| `:value` | `hex` | The hex encoded prime number. |

### `crypto:key:secret`

A secret key with an optional initialiation vector.

| Interface |
|-----------|
| `crypto:key` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:algorithm` | `crypto:algorithm` | The cryptographic algorithm which uses the key material. |
| `:bits` | `int:min1` | The number of bits of key material. |
| `:iv` | `hex` | The hex encoded initialization vector. |
| `:mode` | `base:name` | The algorithm specific mode in use. |
| `:seed:algorithm` | `crypto:algorithm` | The algorithm used to generate the key from the seed password. |
| `:seed:passwd` | `auth:passwd` | The seed password used to generate the key material. |
| `:seen` | `ival` | The secret key was observed during the time interval. |
| `:value` | `hex` | The hex encoded secret key. |

### `crypto:payment:input`

A payment made into a transaction.

| Property | Type | Doc |
|----------|------|-----|
| `:address` | `crypto:currency:address` | The address which paid into the transaction. |
| `:transaction` | `crypto:currency:transaction` | The transaction the payment was input to. |
| `:value` | `econ:price` | The value of the currency paid into the transaction. |

### `crypto:payment:output`

A payment received from a transaction.

| Property | Type | Doc |
|----------|------|-----|
| `:address` | `crypto:currency:address` | The address which received payment from the transaction. |
| `:transaction` | `crypto:currency:transaction` | The transaction the payment was output from. |
| `:value` | `econ:price` | The value of the currency received from the transaction. |

### `crypto:salthash`

A salted hash computed for a value.

| Interface |
|-----------|
| `auth:credential` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:hash` | `crypto:hash` | The hash value. |
| `:salt` | `hex` | The salt value encoded as a hexadecimal string. |
| `:seen` | `ival` | The salted hash was observed during the time interval. |
| `:value` | `crypto:hashable` | The value that was used to compute the salted hash. |

### `crypto:smart:contract`

A smart contract.

| Property | Type | Doc |
|----------|------|-----|
| `:address` | `crypto:currency:address` | The address of the contract. |
| `:bytecode` | `file:bytes` | The bytecode which implements the contract. |
| `:token:name` | `str` | The ERC-20 token name. |
| `:token:symbol` | `str` | The ERC-20 token symbol. |
| `:token:totalsupply` | `hugenum` | The ERC-20 totalSupply value. |
| `:transaction` | `crypto:currency:transaction` | The transaction which created the contract. |

### `crypto:smart:effect:burntoken`

A smart contract effect which destroys a non-fungible token.

| Interface |
|-----------|
| `crypto:smart:effect` |

| Property | Type | Doc |
|----------|------|-----|
| `:index` | `int` | The order of the effect within the effects of one transaction. |
| `:token` | `crypto:smart:token` | The non-fungible token that was destroyed. |
| `:transaction` | `crypto:currency:transaction` | The transaction where the smart contract was called. |

### `crypto:smart:effect:edittokensupply`

A smart contract effect which increases or decreases the supply of a fungible token.

| Interface |
|-----------|
| `crypto:smart:effect` |

| Property | Type | Doc |
|----------|------|-----|
| `:amount` | `hugenum` | The number of tokens added or removed if negative. |
| `:contract` | `crypto:smart:contract` | The contract which defines the tokens. |
| `:index` | `int` | The order of the effect within the effects of one transaction. |
| `:totalsupply` | `hugenum` | The total supply of tokens after this modification. |
| `:transaction` | `crypto:currency:transaction` | The transaction where the smart contract was called. |

### `crypto:smart:effect:minttoken`

A smart contract effect which creates a new non-fungible token.

| Interface |
|-----------|
| `crypto:smart:effect` |

| Property | Type | Doc |
|----------|------|-----|
| `:index` | `int` | The order of the effect within the effects of one transaction. |
| `:token` | `crypto:smart:token` | The non-fungible token that was created. |
| `:transaction` | `crypto:currency:transaction` | The transaction where the smart contract was called. |

### `crypto:smart:effect:proxytoken`

A smart contract effect which grants a non-owner address the ability to manipulate a specific non-fungible token.

| Interface |
|-----------|
| `crypto:smart:effect` |

| Property | Type | Doc |
|----------|------|-----|
| `:index` | `int` | The order of the effect within the effects of one transaction. |
| `:owner` | `crypto:currency:address` | The address granting proxy authority to manipulate non-fungible tokens. |
| `:proxy` | `crypto:currency:address` | The address granted proxy authority to manipulate non-fungible tokens. |
| `:token` | `crypto:smart:token` | The specific token being granted access to. |
| `:transaction` | `crypto:currency:transaction` | The transaction where the smart contract was called. |

### `crypto:smart:effect:proxytokenall`

A smart contract effect which grants a non-owner address the ability to manipulate all non-fungible tokens of the owner.

| Interface |
|-----------|
| `crypto:smart:effect` |

| Property | Type | Doc |
|----------|------|-----|
| `:approval` | `bool` | The approval status. |
| `:contract` | `crypto:smart:contract` | The contract which defines the tokens. |
| `:index` | `int` | The order of the effect within the effects of one transaction. |
| `:owner` | `crypto:currency:address` | The address granting/denying proxy authority to manipulate all non-fungible tokens of the owner. |
| `:proxy` | `crypto:currency:address` | The address granted/denied proxy authority to manipulate all non-fungible tokens of the owner. |
| `:transaction` | `crypto:currency:transaction` | The transaction where the smart contract was called. |

### `crypto:smart:effect:proxytokens`

A smart contract effect which grants a non-owner address the ability to manipulate fungible tokens.

| Interface |
|-----------|
| `crypto:smart:effect` |

| Property | Type | Doc |
|----------|------|-----|
| `:amount` | `hex` | The hex encoded amount of tokens the proxy is allowed to manipulate. |
| `:contract` | `crypto:smart:contract` | The contract which defines the tokens. |
| `:index` | `int` | The order of the effect within the effects of one transaction. |
| `:owner` | `crypto:currency:address` | The address granting proxy authority to manipulate fungible tokens. |
| `:proxy` | `crypto:currency:address` | The address granted proxy authority to manipulate fungible tokens. |
| `:transaction` | `crypto:currency:transaction` | The transaction where the smart contract was called. |

### `crypto:smart:effect:transfertoken`

A smart contract effect which transfers ownership of a non-fungible token.

| Interface |
|-----------|
| `crypto:smart:effect` |

| Property | Type | Doc |
|----------|------|-----|
| `:from` | `crypto:currency:address` | The address the NFT was transferred from. |
| `:index` | `int` | The order of the effect within the effects of one transaction. |
| `:to` | `crypto:currency:address` | The address the NFT was transferred to. |
| `:token` | `crypto:smart:token` | The non-fungible token that was transferred. |
| `:transaction` | `crypto:currency:transaction` | The transaction where the smart contract was called. |

### `crypto:smart:effect:transfertokens`

A smart contract effect which transfers fungible tokens.

| Interface |
|-----------|
| `crypto:smart:effect` |

| Property | Type | Doc |
|----------|------|-----|
| `:amount` | `hugenum` | The number of tokens transferred. |
| `:contract` | `crypto:smart:contract` | The contract which defines the tokens. |
| `:from` | `crypto:currency:address` | The address the tokens were transferred from. |
| `:index` | `int` | The order of the effect within the effects of one transaction. |
| `:to` | `crypto:currency:address` | The address the tokens were transferred to. |
| `:transaction` | `crypto:currency:transaction` | The transaction where the smart contract was called. |

### `crypto:smart:token`

A token managed by a smart contract.

| Property | Type | Doc |
|----------|------|-----|
| `:contract` | `crypto:smart:contract` | The smart contract which defines and manages the token. |
| `:nft:meta` | `data` | The raw NFT metadata. |
| `:nft:meta:description` | `text` | The description field from the NFT metadata. |
| `:nft:meta:image` | `inet:url` | The image URL from the NFT metadata. |
| `:nft:meta:name` | `base:name` | The name field from the NFT metadata. |
| `:nft:url` | `inet:url` | The URL which hosts the NFT metadata. |
| `:owner` | `crypto:currency:address` | The address which currently owns the token. |
| `:tokenid` | `hugenum` | The token ID. |

### `crypto:x509:cert`

A unique X.509 certificate.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:algo` | `iso:oid` | The X.509 signature algorithm OID. |
| `:crl:urls` | `array of inet:url` | The extracted URL values from the CRLs extension. |
| `:ext:crls` | `array of crypto:x509:san` | A list of Subject Alternate Names (SANs) for Distribution Points. |
| `:ext:sans` | `array of crypto:x509:san` | The Subject Alternate Names (SANs) listed in the certificate. |
| `:file` | `file:bytes` | The file that the certificate metadata was parsed from. |
| `:identities:emails` | `array of inet:email` | The fused list of email addresses identified by the cert CN and SANs. |
| `:identities:fqdns` | `array of inet:fqdn` | The fused list of FQDNs identified by the cert CN and SANs. |
| `:identities:ips` | `array of inet:ip` | The fused list of IP addresses identified by the cert CN and SANs. |
| `:identities:urls` | `array of inet:url` | The fused list of URLs identified by the cert CN and SANs. |
| `:issuer` | `str` | The Distinguished Name (DN) of the Certificate Authority (CA) which issued the certificate. |
| `:issuer:cert` | `crypto:x509:cert` | The certificate used by the issuer to sign this certificate. |
| `:key` | `crypto:key:dsa`, `crypto:key:rsa` | The public key embedded in the certificate. |
| `:md5` | `crypto:hash:md5` | The MD5 fingerprint for the certificate. |
| `:seen` | `ival` | The X.509 certificate was observed during the time interval. |
| `:selfsigned` | `bool` | Whether this is a self-signed certificate. |
| `:serial` | `crypto:x509:serial` | The certificate serial number as a big endian hex value. |
| `:sha1` | `crypto:hash:sha1` | The SHA1 fingerprint for the certificate. |
| `:sha256` | `crypto:hash:sha256` | The SHA256 fingerprint for the certificate. |
| `:signature` | `hex` | The hexadecimal representation of the digital signature. |
| `:subject` | `str` | The subject identifier, commonly in X.500/LDAP format, to which the certificate was issued. |
| `:subject:cn` | `str` | The Common Name (CN) attribute of the x509 Subject. |
| `:validity:notafter` | `time` | The timestamp for the end of the certificate validity period. |
| `:validity:notbefore` | `time` | The timestamp for the beginning of the certificate validity period. |
| `:version` | `crypto:x509:version` | The version integer in the certificate. (ex. 2 == v3 ). |

### `crypto:x509:crl`

A unique X.509 Certificate Revocation List.

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file containing the CRL. |
| `:url` | `inet:url` | The URL where the CRL was published. |

### `crypto:x509:revoked`

A revocation relationship between a CRL and an X.509 certificate.

| Property | Type | Doc |
|----------|------|-----|
| `:cert` | `crypto:x509:cert` | The certificate revoked by the CRL. |
| `:crl` | `crypto:x509:crl` | The CRL which revoked the certificate. |

### `crypto:x509:signedfile`

A digital signature relationship between an X.509 certificate and a file.

| Property | Type | Doc |
|----------|------|-----|
| `:cert` | `crypto:x509:cert` | The certificate for the key which signed the file. |
| `:file` | `file:bytes` | The file which was signed by the certificates key. |

### `doc:contract`

A contract between multiple entities.

| Interface |
|-----------|
| `base:activity` |
| `doc:authorable` |
| `doc:document` |
| `doc:signable` |
| `entity:action` |
| `entity:activity` |
| `entity:creatable` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this contract. |
| `:actor` | `entity:actor` | The actor who carried out the contract. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the contract. |
| `:body` | `text` | The text of the contract. |
| `:created` | `time` | The time that the contract was created. |
| `:creator` | `entity:actor` | The primary actor which created the contract. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the contract. |
| `:desc` | `text` | A description of the contract. |
| `:file` | `file:bytes` | The file containing the contract contents. |
| `:file:captured` | `time` | The time when the file content was captured. |
| `:file:name` | `file:base` | The name of the file containing the contract contents. |
| `:id` | `base:id` | The contract ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the contract. |
| `:period` | `ival` | The period over which the contract occurred. |
| `:signed` | `time` | The date that the contract signing was complete. |
| `:supersedes` | `array of doc:contract` | An array of contract versions which are superseded by this contract. |
| `:title` | `str` | The title of the contract. |
| `:type` | `doc:contract:type:taxonomy` | The type of contract. |
| `:updated` | `time` | The time that the contract was last updated. |
| `:url` | `inet:url` | The URL where the contract is available. |
| `:version` | `it:version` | The version of the contract. |

### `doc:contract:type:taxonomy`

A hierarchical taxonomy of contract types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `doc:contract:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `doc:policy`

Guiding principles used to reach a set of goals.

| Interface |
|-----------|
| `doc:authorable` |
| `doc:document` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:body` | `text` | The text of the policy. |
| `:created` | `time` | The time that the policy was created. |
| `:creator` | `entity:actor` | The primary actor which created the policy. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the policy. |
| `:desc` | `text` | A description of the policy. |
| `:file` | `file:bytes` | The file containing the policy contents. |
| `:file:captured` | `time` | The time when the file content was captured. |
| `:file:name` | `file:base` | The name of the file containing the policy contents. |
| `:id` | `base:id` | The policy ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the policy. |
| `:supersedes` | `array of doc:policy` | An array of policy versions which are superseded by this policy. |
| `:title` | `str` | The title of the policy. |
| `:type` | `doc:policy:type:taxonomy` | The type of policy. |
| `:updated` | `time` | The time that the policy was last updated. |
| `:url` | `inet:url` | The URL where the policy is available. |
| `:version` | `it:version` | The version of the policy. |

### `doc:policy:type:taxonomy`

A taxonomy of policy types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `doc:policy:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `doc:reference`

A reference included in a source.

| Property | Type | Doc |
|----------|------|-----|
| `:doc` | `doc:document` | The document which the reference refers to. |
| `:doc:url` | `inet:url` | A URL for the reference. |
| `:source` | `doc:report`, `entity:campaign`, `meta:technique`, `plan:phase`, `risk:threat`, `risk:tool:software`, `risk:vuln` | The source which contains the reference. |
| `:text` | `str` | A reference string included in the source. |

### `doc:report`

A report.

| Interface |
|-----------|
| `doc:authorable` |
| `doc:document` |
| `doc:published` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:body` | `text` | The text of the report. |
| `:created` | `time` | The time that the report was created. |
| `:creator` | `entity:actor` | The primary actor which created the report. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the report. |
| `:desc` | `text` | A description of the report. |
| `:file` | `file:bytes` | The file containing the report contents. |
| `:file:captured` | `time` | The time when the file content was captured. |
| `:file:name` | `file:base` | The name of the file containing the report contents. |
| `:id` | `base:id` | The report ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the report. |
| `:public` | `bool` | Set to true if the report is publicly available. |
| `:published` | `time` | The time the report was published. |
| `:publisher` | `entity:actor` | The entity which published the report. |
| `:publisher:name` | `entity:name` | The name of the entity which published the report. |
| `:supersedes` | `array of doc:report` | An array of report versions which are superseded by this report. |
| `:title` | `str` | The title of the report. |
| `:topics` | `array of meta:topic` | The topics discussed in the report. |
| `:type` | `doc:report:type:taxonomy` | The type of report. |
| `:updated` | `time` | The time that the report was last updated. |
| `:url` | `inet:url` | The URL where the report is available. |
| `:version` | `it:version` | The version of the report. |

### `doc:report:type:taxonomy`

A taxonomy of report types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `doc:report:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `doc:requirement`

A single requirement, often defined by a standard.

| Interface |
|-----------|
| `doc:authorable` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the requirement was created. |
| `:creator` | `entity:actor` | The primary actor which created the requirement. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the requirement. |
| `:desc` | `text` | A description of the requirement. |
| `:id` | `base:id` | The requirement ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the requirement. |
| `:optional` | `bool` | Set to true if the requirement is optional as defined by the standard. |
| `:priority` | `meta:score` | The priority of the requirement as defined by the standard. |
| `:standard` | `doc:standard` | The standard which defined the requirement. |
| `:supersedes` | `array of doc:requirement` | An array of requirement versions which are superseded by this requirement. |
| `:text` | `text` | The requirement definition. |
| `:updated` | `time` | The time that the requirement was last updated. |
| `:url` | `inet:url` | The URL where the requirement is available. |
| `:version` | `it:version` | The version of the requirement. |

### `doc:resume`

A CV/resume document.

| Interface |
|-----------|
| `doc:authorable` |
| `doc:document` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:achievements` | `array of entity:achieved` | Achievements described in the resume. |
| `:body` | `text` | The text of the resume. |
| `:contact` | `entity:individual` | Contact information for subject of the resume. |
| `:created` | `time` | The time that the resume was created. |
| `:creator` | `entity:actor` | The primary actor which created the resume. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the resume. |
| `:desc` | `text` | A description of the resume. |
| `:education` | `array of entity:studied` | Education experience described in the resume. |
| `:file` | `file:bytes` | The file containing the resume contents. |
| `:file:captured` | `time` | The time when the file content was captured. |
| `:file:name` | `file:base` | The name of the file containing the resume contents. |
| `:id` | `base:id` | The resume ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the resume. |
| `:skills` | `array of ps:skill` | The skills described in the resume. |
| `:summary` | `text` | The summary of qualifications from the resume. |
| `:supersedes` | `array of doc:resume` | An array of resume versions which are superseded by this resume. |
| `:title` | `str` | The title of the resume. |
| `:type` | `doc:resume:type:taxonomy` | The type of resume. |
| `:updated` | `time` | The time that the resume was last updated. |
| `:url` | `inet:url` | The URL where the resume is available. |
| `:version` | `it:version` | The version of the resume. |
| `:workhist` | `array of ps:workhist` | Work history described in the resume. |

### `doc:resume:type:taxonomy`

A taxonomy of resume types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `doc:resume:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `doc:standard`

A group of requirements which define how to implement a policy or goal.

| Interface |
|-----------|
| `doc:authorable` |
| `doc:document` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:body` | `text` | The text of the standard. |
| `:created` | `time` | The time that the standard was created. |
| `:creator` | `entity:actor` | The primary actor which created the standard. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the standard. |
| `:desc` | `text` | A description of the standard. |
| `:file` | `file:bytes` | The file containing the standard contents. |
| `:file:captured` | `time` | The time when the file content was captured. |
| `:file:name` | `file:base` | The name of the file containing the standard contents. |
| `:id` | `base:id` | The standard ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the standard. |
| `:policy` | `doc:policy` | The policy which was used to derive the standard. |
| `:supersedes` | `array of doc:standard` | An array of standard versions which are superseded by this standard. |
| `:title` | `str` | The title of the standard. |
| `:type` | `doc:standard:type:taxonomy` | The type of standard. |
| `:updated` | `time` | The time that the standard was last updated. |
| `:url` | `inet:url` | The URL where the standard is available. |
| `:version` | `it:version` | The version of the standard. |

### `doc:standard:type:taxonomy`

A taxonomy of standard types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `doc:standard:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `econ:balance`

The balance of funds available to a financial instrument at a specific time.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The financial account holding the balance. |
| `:amount` | `econ:price` | The available funds at the time. |
| `:time` | `time` | The time the balance was recorded. |

### `econ:bank:aba:account`

An ABA routing number and bank account number.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The financial account which stores currency for this ABA account number. |
| `:issuer` | `entity:actor` | The bank which issued the account number. |
| `:issuer:name` | `entity:name` | The name of the bank which issued the account number. |
| `:number` | `econ:invoice:number` | The account number. |
| `:routing` | `econ:bank:aba:rtn` | The routing number. |
| `:seen` | `ival` | The ABA account was observed during the time interval. |
| `:type` | `econ:bank:aba:account:type:taxonomy` | The type of ABA account. |

### `econ:bank:aba:account:type:taxonomy`

A type taxonomy for ABA bank account numbers.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `econ:bank:aba:account:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `econ:bank:aba:rtn`

An American Bank Association (ABA) routing transit number (RTN).

| Interface |
|-----------|
| `entity:identifier` |

| Property | Type | Doc |
|----------|------|-----|
| `:bank` | `ou:org` | The bank which was issued the ABA RTN. |
| `:bank:name` | `entity:name` | The name which is registered for this ABA RTN. |

### `econ:bank:check`

A check written out to a recipient.

| Interface |
|-----------|
| `econ:pay:instrument` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The account contains the funds used by the check. |
| `:account:number` | `econ:acct:number` | The bank account number. |
| `:amount` | `econ:price` | The amount the check is written for. |
| `:payto` | `entity:name` | The name of the intended recipient. |
| `:routing` | `econ:bank:aba:rtn` | The ABA routing number on the check. |
| `:seen` | `ival` | The check was observed during the time interval. |

### `econ:bank:iban`

An International Bank Account Number.

| Interface |
|-----------|
| `entity:identifier` |

### `econ:bank:swift:bic`

A Society for Worldwide Interbank Financial Telecommunication (SWIFT) Business Identifier Code (BIC).

| Interface |
|-----------|
| `entity:identifier` |

| Property | Type | Doc |
|----------|------|-----|
| `:business` | `ou:org` | The business which is the registered owner of the SWIFT BIC. |
| `:office` | `geo:place` | The branch or office which is specified in the last 3 digits of the SWIFT BIC. |

### `econ:cash:deposit`

A cash deposit event to a financial account.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The account the cash was deposited to. |
| `:actor` | `entity:actor` | The entity which deposited the cash. |
| `:amount` | `econ:price` | The amount of cash deposited. |
| `:time` | `time` | The time the cash was deposited. |

### `econ:cash:withdrawal`

A cash withdrawal event from a financial account.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The account the cash was withdrawn from. |
| `:actor` | `entity:actor` | The entity which withdrew the cash. |
| `:amount` | `econ:price` | The amount of cash withdrawn. |
| `:time` | `time` | The time the cash was withdrawn. |

### `econ:currency`

The name of a system of money in general use.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The full name of the currency. |

### `econ:fin:account`

A financial account which contains a balance of funds.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:balance` | `econ:price` | The most recently known balance of the account. |
| `:holder` | `entity:contactable` | The contact information of the account holder. |
| `:seen` | `ival` | The financial account was observed during the time interval. |
| `:type` | `econ:fin:account:type:taxonomy` | The type of financial account. |

### `econ:fin:account:type:taxonomy`

A financial account type taxonomy.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `econ:fin:account:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `econ:fin:bar`

A sample of the open, close, high, low prices of a security in a specific time window.

| Property | Type | Doc |
|----------|------|-----|
| `:period` | `ival` | The interval of measurement. |
| `:price:close` | `econ:price` | The closing price of the security. |
| `:price:high` | `econ:price` | The high price of the security. |
| `:price:low` | `econ:price` | The low price of the security. |
| `:price:open` | `econ:price` | The opening price of the security. |
| `:security` | `econ:fin:security` | The security measured by the bar. |

### `econ:fin:exchange`

A financial exchange where securities are traded.

| Property | Type | Doc |
|----------|------|-----|
| `:currency` | `econ:currency` | The currency used for all transactions in the exchange. |
| `:name` | `entity:name` | A simple name for the exchange. |
| `:org` | `ou:org` | The organization that operates the exchange. |

### `econ:fin:security`

A financial security which is typically traded on an exchange.

| Property | Type | Doc |
|----------|------|-----|
| `:exchange` | `econ:fin:exchange` | The exchange on which the security is traded. |
| `:price` | `econ:price` | The last known/available price of the security. |
| `:ticker` | `str:lower` | The identifier for this security within the exchange. |
| `:time` | `time` | The time of the last know price sample. |
| `:type` | `econ:fin:security:type:taxonomy` | The type of security. |

### `econ:fin:security:type:taxonomy`

A hierarchical taxonomy of financial security types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `econ:fin:security:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `econ:fin:tick`

A sample of the price of a security at a single moment in time.

| Property | Type | Doc |
|----------|------|-----|
| `:price` | `econ:price` | The price of the security at the time. |
| `:security` | `econ:fin:security` | The security measured by the tick. |
| `:time` | `time` | The time the price was sampled. |

### `econ:invoice`

An invoice issued requesting payment.

| Property | Type | Doc |
|----------|------|-----|
| `:amount` | `econ:price` | The balance due. |
| `:due` | `time` | The time by which the payment is due. |
| `:issued` | `time` | The time that the invoice was issued to the recipient. |
| `:issuer` | `entity:actor` | The contact information for the entity which issued the invoice. |
| `:paid` | `bool` | Set to true if the invoice has been paid in full. |
| `:purchase` | `econ:purchase` | The purchase that the invoice is requesting payment for. |
| `:recipient` | `entity:actor` | The contact information for the intended recipient of the invoice. |

### `econ:lineitem`

A line item included as part of a purchase.

| Property | Type | Doc |
|----------|------|-----|
| `:count` | `int` | The number of items included in this line item. |
| `:item` | `biz:service`, `meta:havable` | The product or service. |
| `:price` | `econ:price` | The total cost of this receipt line item. |

### `econ:pay:card`

A single payment card.

| Interface |
|-----------|
| `econ:pay:instrument` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The account contains the funds used by the payment card. |
| `:cvv` | `econ:pay:cvv` | The Card Verification Value on the card. |
| `:expr` | `time` | The expiration date for the card. |
| `:name` | `entity:name` | The name as it appears on the card. |
| `:pan` | `econ:pay:pan` | The payment card number. |
| `:pan:iin` | `econ:pay:iin` | The payment card IIN. |
| `:pan:mii` | `econ:pay:mii` | The payment card MII. |
| `:pin` | `econ:pay:pin` | The Personal Identification Number on the card. |
| `:seen` | `ival` | The payment card was observed during the time interval. |

### `econ:pay:iin`

An Issuer Id Number (IIN).

| Interface |
|-----------|
| `entity:identifier` |

| Property | Type | Doc |
|----------|------|-----|
| `:issuer` | `ou:org` | The issuer organization. |
| `:issuer:name` | `entity:name` | The registered name of the issuer. |

### `econ:payment`

A payment, crypto currency transaction, or account withdrawal.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `geo:locatable` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this payment event. |
| `:actor` | `entity:actor` | The actor who carried out the payment event. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the payment event. |
| `:amount` | `econ:price` | The amount of money transferred in the payment. |
| `:cash` | `bool` | The payment was made with physical currency. |
| `:crypto:transaction` | `crypto:currency:transaction` | A crypto currency transaction that initiated the payment. |
| `:fee` | `econ:price` | The transaction fee paid by the recipient to the payment processor. |
| `:id` | `base:id` | A payment processor specific transaction ID. |
| `:instrument` | `econ:pay:instrument` | The payment instrument used by the actor to make the payment. |
| `:payee` | `entity:actor` | The entity which received the payment. |
| `:payee:instrument` | `econ:pay:instrument` | The payment instrument used by the payee to receive payment. |
| `:place` | `geo:place` | The place where the payment event was located. |
| `:place:address` | `geo:address` | The postal address where the payment event was located. |
| `:place:address:city` | `base:name` | The city where the payment event was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the payment event was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the payment event was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the payment event was located. |
| `:place:country` | `pol:country` | The country where the payment event was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the payment event was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the payment event was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the payment event was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the payment event was located. |
| `:place:loc` | `loc` | The geopolitical location where the payment event was located. |
| `:place:name` | `geo:name` | The name where the payment event was located. |
| `:status` | `str:lower` | The status of the payment. |
| `:time` | `time` | The time the payment was made. |

### `econ:purchase`

An event where an actor made a purchase.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `geo:locatable` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this purchase. |
| `:actor` | `entity:actor` | The actor who carried out the purchase. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the purchase. |
| `:paid` | `time` | The time when the purchase was paid in full. |
| `:place` | `geo:place` | The place where the purchase was located. |
| `:place:address` | `geo:address` | The postal address where the purchase was located. |
| `:place:address:city` | `base:name` | The city where the purchase was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the purchase was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the purchase was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the purchase was located. |
| `:place:country` | `pol:country` | The country where the purchase was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the purchase was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the purchase was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the purchase was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the purchase was located. |
| `:place:loc` | `loc` | The geopolitical location where the purchase was located. |
| `:place:name` | `geo:name` | The name where the purchase was located. |
| `:price` | `econ:price` | The price of the purchase. |
| `:seller` | `entity:actor` | The actor who sold the items. |
| `:seller:name` | `entity:name` | The name of the actor who sold the items. |
| `:time` | `time` | The time that the purchase occurred. |

### `econ:receipt`

A receipt issued as proof of payment.

| Property | Type | Doc |
|----------|------|-----|
| `:amount` | `econ:price` | The price that the receipt confirms was paid. |
| `:issued` | `time` | The time the receipt was issued. |
| `:issuer` | `entity:actor` | The contact information for the entity which issued the receipt. |
| `:purchase` | `econ:purchase` | The purchase that the receipt confirms payment for. |
| `:recipient` | `entity:actor` | The contact information for the entity which received the receipt. |

### `econ:statement`

A statement of starting/ending balance and payments for a financial instrument over a time period.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The financial account described by the statement. |
| `:balance` | `econ:price` | The balance at the end of the statement period. |
| `:period` | `ival` | The period that the statement includes. |
| `:prev` | `econ:statement` | The statement for the previous period. |

### `edu:class`

An instance of an edu:course taught at a given time.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `meta:causal` |
| `meta:recordable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this class. |
| `:assistants` | `array of entity:individual` | An array of assistant/co-instructor contacts. |
| `:course` | `edu:course` | The course being taught in the class. |
| `:desc` | `text` | A description of the class. |
| `:instructor` | `entity:individual` | The primary instructor for the class. |
| `:isvirtual` | `bool` | Set if the class is virtual. |
| `:name` | `base:name` | The name of the class. |
| `:period` | `ival` | The period over which the class was run. |
| `:recording:file` | `file:bytes` | A file containing a recording of the class. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the class. |
| `:type` | `meta:event:type:taxonomy` | The type of activity. |
| `:virtual:provider` | `entity:actor` | Contact info for the virtual infrastructure provider. |
| `:virtual:url` | `inet:url` | The URL a student would use to attend the virtual class. |

### `edu:course`

A course of study taught by an org.

| Interface |
|-----------|
| `doc:authorable` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the course was created. |
| `:creator` | `entity:actor` | The primary actor which created the course. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the course. |
| `:desc` | `str` | A brief course description. |
| `:id` | `base:id` | The course catalog number or ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the course. |
| `:institution` | `ou:org` | The org or department which teaches the course. |
| `:name` | `base:name` | The name of the course. |
| `:prereqs` | `array of edu:course` | The pre-requisite courses for taking this course. |
| `:supersedes` | `array of edu:course` | An array of course versions which are superseded by this course. |
| `:updated` | `time` | The time that the course was last updated. |
| `:url` | `inet:url` | The URL where the course is available. |
| `:version` | `it:version` | The version of the course. |

### `entity:achieved`

An event where an actor achieved a goal or was given an award.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:achievement` | `meta:achievable` | The achievement that the actor reached. |
| `:activity` | `meta:activity` | A parent activity which includes this achieved. |
| `:actor` | `entity:actor` | The actor who carried out the achieved. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the achieved. |
| `:time` | `time` | The time that the achieved occurred. |

### `entity:asked`

An event where an actor made an ask as part of a negotiation.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `entity:stance` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:negotiable` | The negotiation activity this ask was part of. |
| `:actor` | `entity:actor` | The actor who carried out the ask. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the ask. |
| `:expires` | `time` | The time that the ask expires. |
| `:time` | `time` | The time that the ask occurred. |
| `:value` | `econ:price` | The value of the ask. |

### `entity:attended`

A period where an actor attended an event or activity.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | The activity attended by the actor. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:period` | `ival` | The period over which the activity occurred. |
| `:role` | `base:name` | The role the actor played in attending the activity. |

### `entity:believed`

A period where an actor held a belief.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this believed. |
| `:actor` | `entity:actor` | The actor who carried out the believed. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the believed. |
| `:belief` | `meta:believable` | The belief held by the actor. |
| `:period` | `ival` | The period over which the believed occurred. |

### `entity:campaign`

Activity in pursuit of a goal.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `entity:participable` |
| `entity:supportable` |
| `meta:causal` |
| `meta:observable` |
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this campaign. |
| `:actor` | `entity:actor` | The actor who carried out the campaign. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the campaign. |
| `:budget` | `econ:price` | The budget allocated to execute the campaign. |
| `:cost` | `econ:price` | The actual cost of the campaign. |
| `:created` | `time` | The time when the campaign was created. |
| `:desc` | `text` | A description of the campaign. |
| `:id` | `base:id` | A unique ID given to the campaign. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the campaign. |
| `:name` | `base:name` | The primary name of the campaign. |
| `:names` | `array of base:name` | A list of alternate names for the campaign. |
| `:period` | `ival` | The period over which the campaign occurred. |
| `:published` | `time` | The time when the reporter published the campaign. |
| `:reporter` | `entity:actor` | The entity which reported on the campaign. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the campaign. |
| `:resolved` | `entity:campaign` | The authoritative campaign which this reporting is about. |
| `:seen` | `ival` | The campaign was observed during the time interval. |
| `:slogan` | `lang:phrase` | The slogan used by the campaign. |
| `:sophistication` | `meta:score` | The assessed sophistication of the campaign. |
| `:success` | `bool` | Set to true if the campaign achieved its goals. |
| `:superseded` | `time` | The time when the campaign was superseded. |
| `:supersedes` | `array of entity:campaign` | An array of campaign nodes which are superseded by this campaign. |
| `:tag` | `syn:tag` | The tag used to annotate nodes that are associated with the campaign. |
| `:type` | `entity:campaign:type:taxonomy` | A type taxonomy entry for the campaign. |
| `:updated` | `time` | The time when the campaign was last updated. |
| `:url` | `inet:url` | The URL for the campaign. |

### `entity:campaign:type:taxonomy`

A hierarchical taxonomy of campaign types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `entity:campaign:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `entity:conflict`

Represents a conflict where two or more campaigns have mutually exclusive goals.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this conflict. |
| `:adversaries` | `array of entity:actor` | The primary adversaries in conflict with one another. |
| `:name` | `event:name` | The name of the conflict. |
| `:period` | `ival` | The period over which the conflict occurred. |

### `entity:contact`

A set of contact information which is used by an entity.

| Interface |
|-----------|
| `entity:actor` |
| `entity:contactable` |
| `entity:multiple` |
| `entity:resolvable` |
| `entity:singular` |
| `geo:locatable` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:banner` | `file:bytes` | A banner or hero image used on the profile page. |
| `:bio` | `text` | A tagline or bio provided for the contact. |
| `:birth:place` | `geo:place` | The place where the contact was born. |
| `:birth:place:address` | `geo:address` | The postal address where the contact was born. |
| `:birth:place:address:city` | `base:name` | The city where the contact was born. |
| `:birth:place:altitude` | `geo:altitude` | The altitude where the contact was born. |
| `:birth:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the contact was born. |
| `:birth:place:bbox` | `geo:bbox` | A bounding box which encompasses where the contact was born. |
| `:birth:place:country` | `pol:country` | The country where the contact was born. |
| `:birth:place:country:code` | `iso:3166:alpha2` | The country code where the contact was born. |
| `:birth:place:geojson` | `geo:json` | A GeoJSON representation of where the contact was born. |
| `:birth:place:latlong` | `geo:latlong` | The latlong where the contact was born. |
| `:birth:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the contact was born. |
| `:birth:place:loc` | `loc` | The geopolitical location where the contact was born. |
| `:birth:place:name` | `geo:name` | The name where the contact was born. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the contact. |
| `:death:place` | `geo:place` | The place where the contact died. |
| `:death:place:address` | `geo:address` | The postal address where the contact died. |
| `:death:place:address:city` | `base:name` | The city where the contact died. |
| `:death:place:altitude` | `geo:altitude` | The altitude where the contact died. |
| `:death:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the contact died. |
| `:death:place:bbox` | `geo:bbox` | A bounding box which encompasses where the contact died. |
| `:death:place:country` | `pol:country` | The country where the contact died. |
| `:death:place:country:code` | `iso:3166:alpha2` | The country code where the contact died. |
| `:death:place:geojson` | `geo:json` | A GeoJSON representation of where the contact died. |
| `:death:place:latlong` | `geo:latlong` | The latlong where the contact died. |
| `:death:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the contact died. |
| `:death:place:loc` | `loc` | The geopolitical location where the contact died. |
| `:death:place:name` | `geo:name` | The name where the contact died. |
| `:desc` | `text` | A description of the contact. |
| `:email` | `inet:email` | The primary email address for the contact. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the contact. |
| `:id` | `base:id` | A type or source specific ID for the contact. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:lang` | `lang:language` | The primary language of the contact. |
| `:langs` | `array of lang:language` | An array of alternate languages for the contact. |
| `:lifespan` | `ival` | The lifespan of the contact. |
| `:name` | `entity:name` | The primary entity name of the contact. |
| `:names` | `array of entity:name` | An array of alternate entity names for the contact. |
| `:org` | `ou:org` | An associated organization listed as part of the contact information. |
| `:org:name` | `entity:name` | The name of an associated organization listed as part of the contact information. |
| `:phone` | `tel:phone` | The primary phone number for the contact. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the contact. |
| `:photo` | `file:bytes` | The profile picture or avatar for this contact. |
| `:place` | `geo:place` | The place where the contact was located. |
| `:place:address` | `geo:address` | The postal address where the contact was located. |
| `:place:address:city` | `base:name` | The city where the contact was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the contact was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the contact was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the contact was located. |
| `:place:country` | `pol:country` | The country where the contact was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the contact was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the contact was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the contact was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the contact was located. |
| `:place:loc` | `loc` | The geopolitical location where the contact was located. |
| `:place:name` | `geo:name` | The name where the contact was located. |
| `:resolved` | `ou:org`, `ps:person` | The resolved entity to which this contact belongs. |
| `:seen` | `ival` | The contact was observed during the time interval. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the contact. |
| `:title` | `entity:title` | The entity title or role for this contact. |
| `:titles` | `array of entity:title` | An array of alternate entity titles or roles for this contact. |
| `:type` | `entity:contact:type:taxonomy` | The contact type. |
| `:user` | `inet:user` | The primary user name for the contact. |
| `:users` | `array of inet:user` | An array of alternate user names for the contact. |
| `:websites` | `array of inet:url` | Web sites listed for the contact. |

### `entity:contact:type:taxonomy`

A hierarchical taxonomy of entity contact types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `entity:contact:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `entity:contactlist`

A list of contacts.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The name of the contact list. |
| `:source` | `file:bytes`, `inet:service:account`, `it:host` | The source that the contact list was extracted from. |

### `entity:contribution`

Represents a specific instance of contributing material support to a campaign.

| Interface |
|-----------|
| `entity:action` |

| Property | Type | Doc |
|----------|------|-----|
| `:actor` | `entity:actor` | The actor who carried out the contribution. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the contribution. |
| `:campaign` | `entity:campaign` | The campaign receiving the contribution. |
| `:time` | `time` | The time the contribution occurred. |
| `:value` | `econ:price` | The assessed value of the contribution. |

### `entity:created`

An activity where an actor helped to create an item.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this activity. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:item` | `entity:creatable` | The item which the actor helped to create. |
| `:period` | `ival` | The period over which the activity occurred. |
| `:role` | `entity:title` | The role which the actor played in creating the item. |

### `entity:discovered`

An event where an entity made a discovery.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this discovery. |
| `:actor` | `entity:actor` | The actor who carried out the discovery. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the discovery. |
| `:item` | `meta:discoverable` | The item discovered by the actor. |
| `:time` | `time` | The time that the discovery occurred. |

### `entity:discovery`

A discovery made by an actor.

| Property | Type | Doc |
|----------|------|-----|
| `:actor` | `entity:actor` | The actor who made the discovery. |
| `:item` | `meta:discoverable` | The item which was discovered. |
| `:time` | `time` | The time when the discovery was made. |

### `entity:goal`

A stated or assessed goal.

| Interface |
|-----------|
| `meta:achievable` |
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time when the goal was created. |
| `:desc` | `text` | A description of the goal. |
| `:id` | `base:id` | A unique ID given to the goal. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the goal. |
| `:name` | `base:name` | A terse name for the goal. |
| `:names` | `array of base:name` | Alternative names for the goal. |
| `:published` | `time` | The time when the reporter published the goal. |
| `:reporter` | `entity:actor` | The entity which reported on the goal. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the goal. |
| `:resolved` | `entity:goal` | The authoritative goal which this reporting is about. |
| `:superseded` | `time` | The time when the goal was superseded. |
| `:supersedes` | `array of entity:goal` | An array of goal nodes which are superseded by this goal. |
| `:type` | `entity:goal:type:taxonomy` | A type taxonomy entry for the goal. |
| `:updated` | `time` | The time when the goal was last updated. |
| `:url` | `inet:url` | The URL for the goal. |

### `entity:goal:type:taxonomy`

A hierarchical taxonomy of goal types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `entity:goal:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `entity:had`

An item which was possessed by an actor.

| Property | Type | Doc |
|----------|------|-----|
| `:actor` | `entity:actor` | The entity which possessed the item. |
| `:item` | `meta:havable` | The item owned by the entity. |
| `:percent` | `hugenum` | The percentage of the item owned by the owner. |
| `:period` | `ival` | The time period when the entity had the item. |
| `:type` | `entity:had:type:taxonomy` | A taxonomy for different types of possession. |

### `entity:had:type:taxonomy`

A hierarchical taxonomy of types of possession.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `entity:had:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `entity:history`

Historical contact information about another contact.

| Interface |
|-----------|
| `entity:contactable` |
| `geo:locatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:banner` | `file:bytes` | A banner or hero image used on the profile page. |
| `:bio` | `text` | A tagline or bio provided for the contact history. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the contact history. |
| `:current` | `entity:contactable` | The current version of this historical contact. |
| `:desc` | `text` | A description of the contact history. |
| `:email` | `inet:email` | The primary email address for the contact history. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the contact history. |
| `:id` | `base:id` | A type or source specific ID for the contact history. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:lang` | `lang:language` | The primary language of the contact history. |
| `:langs` | `array of lang:language` | An array of alternate languages for the contact history. |
| `:lifespan` | `ival` | The lifespan of the contact history. |
| `:name` | `entity:name` | The primary entity name of the contact history. |
| `:names` | `array of entity:name` | An array of alternate entity names for the contact history. |
| `:phone` | `tel:phone` | The primary phone number for the contact history. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the contact history. |
| `:photo` | `file:bytes` | The profile picture or avatar for this contact history. |
| `:place` | `geo:place` | The place where the contact history was located. |
| `:place:address` | `geo:address` | The postal address where the contact history was located. |
| `:place:address:city` | `base:name` | The city where the contact history was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the contact history was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the contact history was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the contact history was located. |
| `:place:country` | `pol:country` | The country where the contact history was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the contact history was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the contact history was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the contact history was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the contact history was located. |
| `:place:loc` | `loc` | The geopolitical location where the contact history was located. |
| `:place:name` | `geo:name` | The name where the contact history was located. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the contact history. |
| `:user` | `inet:user` | The primary user name for the contact history. |
| `:users` | `array of inet:user` | An array of alternate user names for the contact history. |
| `:websites` | `array of inet:url` | Web sites listed for the contact history. |

### `entity:motive`

A goal held by an actor for a period of time.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this activity. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:goal` | `entity:goal` | The goal which motivated the actor. |
| `:period` | `ival` | The period over which the activity occurred. |

### `entity:name`

A name used to refer to an entity.

### `entity:offered`

An event where an actor made an offer as part of a negotiation.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `entity:stance` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:negotiable` | The negotiation activity this offer was part of. |
| `:actor` | `entity:actor` | The actor who carried out the offer. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the offer. |
| `:expires` | `time` | The time that the offer expires. |
| `:time` | `time` | The time that the offer occurred. |
| `:value` | `econ:price` | The value of the offer. |

### `entity:participated`

A period where an actor participated in an activity.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `entity:participable` | The activity which the actor participated in. |
| `:actor` | `entity:actor` | The actor who carried out the participation. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the participation. |
| `:period` | `ival` | The period over which the participation occurred. |
| `:role` | `entity:title` | The role which the actor played in the activity. |

### `entity:proficiency`

A period of time where an actor had proficiency with a skill.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this activity. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:level` | `meta:score` | The level of proficiency. |
| `:period` | `ival` | The period over which the activity occurred. |
| `:skill` | `edu:learnable` | The topic or skill in which the contact is proficient. |

### `entity:registered`

An event where an actor registered for an event or activity.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `entity:participable` | The activity which the actor registered for. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:request` | `inet:proto:request` | The request which the actor sent in order to register. |
| `:role` | `entity:title` | The role which the actor registered for. |
| `:time` | `time` | The time that the event occurred. |

### `entity:relationship`

A directional relationship between two actor entities.

| Interface |
|-----------|
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time when the relationship was created. |
| `:desc` | `text` | A description of the relationship. |
| `:id` | `base:id` | A unique ID given to the relationship. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the relationship. |
| `:name` | `base:name` | The primary name of the relationship. |
| `:names` | `array of base:name` | A list of alternate names for the relationship. |
| `:period` | `ival` | The time period when the relationship existed. |
| `:published` | `time` | The time when the reporter published the relationship. |
| `:reporter` | `entity:actor` | The entity which reported on the relationship. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the relationship. |
| `:resolved` | `entity:relationship` | The authoritative relationship which this reporting is about. |
| `:source` | `entity:actor` | The source entity in the relationship. |
| `:superseded` | `time` | The time when the relationship was superseded. |
| `:supersedes` | `array of entity:relationship` | An array of relationship nodes which are superseded by this relationship. |
| `:target` | `entity:actor` | The target entity in the relationship. |
| `:type` | `entity:relationship:type:taxonomy` | The type of relationship. |
| `:updated` | `time` | The time when the relationship was last updated. |
| `:url` | `inet:url` | The URL for the relationship. |

### `entity:relationship:type:taxonomy`

A hierarchical taxonomy of entity relationship types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `entity:relationship:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `entity:said`

A statement made by an actor.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |
| `meta:recordable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this statement. |
| `:actor` | `entity:actor` | The actor who carried out the statement. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the statement. |
| `:period` | `ival` | The period over which the statement occurred. |
| `:recording:file` | `file:bytes` | A file containing a recording of the statement. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the statement. |
| `:text` | `str` | The transcribed text of what the actor said. |

### `entity:signed`

An event where an actor signed a document.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this signed. |
| `:actor` | `entity:actor` | The actor who carried out the signed. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the signed. |
| `:doc` | `doc:signable` | The document which the actor signed. |
| `:time` | `time` | The time that the signed occurred. |

### `entity:studied`

A period when an actor studied or was educated.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this studied. |
| `:actor` | `entity:actor` | The actor who carried out the studied. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the studied. |
| `:institution` | `ou:org` | The organization providing educational services. |
| `:period` | `ival` | The period over which the studied occurred. |

### `entity:supported`

A period where an actor supported, sponsored, or materially contributed to an activity or cause.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `entity:supportable` | The activity which the actor supported. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:desc` | `text` | A description of the actors support of the activity. |
| `:period` | `ival` | The period over which the activity occurred. |
| `:role` | `entity:title` | The role the actor played in supporting the activity. |
| `:value` | `econ:price` | The financial value of the support given by the actor. |

### `entity:title`

A title or position name used by an entity.

| Interface |
|-----------|
| `risk:targetable` |

### `file:archive:entry`

A file entry contained by an archive file.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:archived:size` | `int` | The storage size of the file within the archive. |
| `:created` | `time` | The created time of the file. |
| `:file` | `file:bytes` | The file contained by the archive file entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:offset` | `int` | The offset to the beginning of the file within the parent file. |
| `:parent` | `file:bytes` | The parent file which contains the archive file entry. |
| `:path` | `file:path` | The path to the file in the archive file entry. |
| `:seen` | `ival` | The archive file entry was observed during the time interval. |

### `file:attachment`

A file attachment.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file which was attached. |
| `:path` | `file:path` | The name of the attached file. |
| `:seen` | `ival` | The file attachment was observed during the time interval. |
| `:text` | `text` | Any text associated with the file such as alt-text for images. |

### `file:base`

A file name with no path.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:ext` | `str` | The file extension (if any). |
| `:seen` | `ival` | The file name was observed during the time interval. |

### `file:bytes`

A file.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:md5` | `crypto:hash:md5` | The MD5 hash of the file. |
| `:mime` | `file:mime` | The "best" mime type name for the file. |
| `:mimes` | `array of file:mime` | An array of alternate mime types for the file. |
| `:name` | `file:base` | The best known base name for the file. |
| `:seen` | `ival` | The file was observed during the time interval. |
| `:sha1` | `crypto:hash:sha1` | The SHA1 hash of the file. |
| `:sha256` | `crypto:hash:sha256` | The SHA256 hash of the file. |
| `:sha512` | `crypto:hash:sha512` | The SHA512 hash of the file. |
| `:size` | `int` | The file size in bytes. |

### `file:entry`

A file entry containing a file and metadata.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file contained by the file entry. |
| `:path` | `file:path` | The path to the file in the file entry. |
| `:seen` | `ival` | The file entry was observed during the time interval. |

### `file:exemplar:entry`

An exemplar file entry used model behavior.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file contained by the file entry. |
| `:path` | `file:path` | The path to the file in the file entry. |
| `:seen` | `ival` | The file entry was observed during the time interval. |

### `file:mime`

A file mime name string.

### `file:mime:elf`

Metadata about an ELF executable file.

| Interface |
|-----------|
| `file:mime:exe` |
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:compiler` | `it:software` | The software used to compile the ELF executable. |
| `:compiler:name` | `it:softwarename` | The name of the software used to compile the ELF executable. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:packer` | `it:software` | The software used to pack the ELF executable. |
| `:packer:name` | `it:softwarename` | The name of the software used to pack the ELF executable. |

### `file:mime:gif`

The GUID of a set of mime metadata for a .gif file.

| Interface |
|-----------|
| `file:mime:image` |
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:altitude` | `geo:altitude` | MIME specific altitude information extracted from metadata. |
| `:author` | `entity:contact` | MIME specific contact information extracted from metadata. |
| `:comment` | `str` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `str` | MIME specific description field extracted from metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `base:name` | The text contained within the image. |

### `file:mime:jpg`

The GUID of a set of mime metadata for a .jpg file.

| Interface |
|-----------|
| `file:mime:image` |
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:altitude` | `geo:altitude` | MIME specific altitude information extracted from metadata. |
| `:author` | `entity:contact` | MIME specific contact information extracted from metadata. |
| `:comment` | `str` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `str` | MIME specific description field extracted from metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `base:name` | The text contained within the image. |

### `file:mime:lnk`

The GUID of the metadata pulled from a Windows shortcut or LNK file.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:arguments` | `it:cmd` | The command line arguments passed to the target file when the LNK file is activated. |
| `:desc` | `text` | The description of the LNK file contained within the StringData section of the LNK file. |
| `:driveserial` | `int` | The drive serial number of the volume the link target is stored on. |
| `:entry:extended` | `file:path` | The extended file path contained within the extended FileEntry structure of the LNK file. |
| `:entry:icon` | `file:path` | The icon file path contained within the StringData structure of the LNK file. |
| `:entry:localized` | `file:path` | The localized file path reconstructed from references within the extended FileEntry structure of the LNK file. |
| `:entry:primary` | `file:path` | The primary file path contained within the FileEntry structure of the LNK file. |
| `:entry:secondary` | `file:path` | The secondary file path contained within the FileEntry structure of the LNK file. |
| `:environment:icon` | `file:path` | The icon file path contained within the IconEnvironmentDataBlock structure of the LNK file. |
| `:environment:path` | `file:path` | The target file path contained within the EnvironmentVariableDataBlock structure of the LNK file. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:flags` | `int` | The flags specified by the LNK header that control the structure of the LNK file. |
| `:iconindex` | `int` | A resource index for an icon within an icon location. |
| `:machineid` | `it:hostname` | The NetBIOS name of the machine where the link target was last located. |
| `:relative` | `str` | The relative target path string contained within the StringData structure of the LNK file. |
| `:target:accessed` | `time` | The access time of the target file according to the LNK header. |
| `:target:attrs` | `int` | The attributes of the target file according to the LNK header. |
| `:target:created` | `time` | The creation time of the target file according to the LNK header. |
| `:target:size` | `int` | The size of the target file according to the LNK header. The LNK format specifies that this is only the lower 32 bits of the target file size. |
| `:target:written` | `time` | The write time of the target file according to the LNK header. |
| `:working` | `file:path` | The working directory used when activating the link target. |

### `file:mime:macho`

Metadata about a Mach-O executable file.

| Interface |
|-----------|
| `file:mime:exe` |
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:compiler` | `it:software` | The software used to compile the Mach-O executable. |
| `:compiler:name` | `it:softwarename` | The name of the software used to compile the Mach-O executable. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:packer` | `it:software` | The software used to pack the Mach-O executable. |
| `:packer:name` | `it:softwarename` | The name of the software used to pack the Mach-O executable. |

### `file:mime:macho:loadcmd`

A generic load command pulled from the Mach-O headers.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:type` | `file:macho:loadcmd:type` | The type of the load command. |

### `file:mime:macho:section`

A section inside a Mach-O binary denoting a named region of bytes inside a segment.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:name` | `str` | Name of the section. |
| `:segment` | `file:mime:macho:segment` | The Mach-O segment that contains this section. |
| `:sha256` | `crypto:hash:sha256` | The sha256 hash of the bytes of the Mach-O section. |
| `:type` | `file:macho:section:type` | The type of the section. |

### `file:mime:macho:segment`

A named region of bytes inside a Mach-O binary.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:disksize` | `int` | The size of the segment in bytes, when on disk, according to the load command structure. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:memsize` | `int` | The size of the segment in bytes, when resident in memory, according to the load command structure. |
| `:name` | `str` | The name of the Mach-O segment. |
| `:sha256` | `crypto:hash:sha256` | The sha256 hash of the bytes of the segment. |
| `:type` | `file:macho:loadcmd:type` | The type of the load command. |

### `file:mime:macho:uuid`

A specific load command denoting a UUID used to uniquely identify the Mach-O binary.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:type` | `file:macho:loadcmd:type` | The type of the load command. |
| `:uuid` | `guid` | The UUID of the Mach-O application (as defined in an LC_UUID load command). |

### `file:mime:macho:version`

A specific load command used to denote the version of the source used to build the Mach-O binary.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:type` | `file:macho:loadcmd:type` | The type of the load command. |
| `:version` | `str` | The version of the Mach-O file encoded in an LC_VERSION load command. |

### `file:mime:msdoc`

Metadata about a Microsoft Word file.

| Interface |
|-----------|
| `file:mime:meta` |
| `file:mime:msoffice` |

| Property | Type | Doc |
|----------|------|-----|
| `:application` | `str` | The creating_application extracted from Microsoft Office metadata. |
| `:author` | `str` | The author extracted from Microsoft Office metadata. |
| `:created` | `time` | The create_time extracted from Microsoft Office metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:lastsaved` | `time` | The last_saved_time extracted from Microsoft Office metadata. |
| `:subject` | `str` | The subject extracted from Microsoft Office metadata. |
| `:title` | `str` | The title extracted from Microsoft Office metadata. |

### `file:mime:msppt`

Metadata about a Microsoft Powerpoint file.

| Interface |
|-----------|
| `file:mime:meta` |
| `file:mime:msoffice` |

| Property | Type | Doc |
|----------|------|-----|
| `:application` | `str` | The creating_application extracted from Microsoft Office metadata. |
| `:author` | `str` | The author extracted from Microsoft Office metadata. |
| `:created` | `time` | The create_time extracted from Microsoft Office metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:lastsaved` | `time` | The last_saved_time extracted from Microsoft Office metadata. |
| `:subject` | `str` | The subject extracted from Microsoft Office metadata. |
| `:title` | `str` | The title extracted from Microsoft Office metadata. |

### `file:mime:msxls`

Metadata about a Microsoft Excel file.

| Interface |
|-----------|
| `file:mime:meta` |
| `file:mime:msoffice` |

| Property | Type | Doc |
|----------|------|-----|
| `:application` | `str` | The creating_application extracted from Microsoft Office metadata. |
| `:author` | `str` | The author extracted from Microsoft Office metadata. |
| `:created` | `time` | The create_time extracted from Microsoft Office metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:lastsaved` | `time` | The last_saved_time extracted from Microsoft Office metadata. |
| `:subject` | `str` | The subject extracted from Microsoft Office metadata. |
| `:title` | `str` | The title extracted from Microsoft Office metadata. |

### `file:mime:pdf`

Metadata extracted from a Portable Document Format (PDF) file.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:author:name` | `entity:name` | The "Author" field extracted from PDF metadata. |
| `:created` | `time` | The "CreatedDate" field extracted from PDF metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:id` | `str` | The "DocumentID" field extracted from PDF metadata. |
| `:keywords` | `array of meta:topic` | The "Keywords" field extracted from PDF metadata. |
| `:language:name` | `lang:name` | The "Language" field extracted from PDF metadata. |
| `:producer:name` | `it:softwarename` | The "Producer" field extracted from PDF metadata. |
| `:subject` | `text` | The "Subject" field extracted from PDF metadata. |
| `:title` | `text` | The "Title" field extracted from PDF metadata. |
| `:tool:name` | `it:softwarename` | The "CreatorTool" field extracted from PDF metadata. |
| `:updated` | `time` | The "ModifyDate" field extracted from PDF metadata. |

### `file:mime:pe`

Metadata about a Microsoft Portable Executable (PE) file.

| Interface |
|-----------|
| `file:mime:exe` |
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:compiled` | `time` | The PE compile time of the file. |
| `:compiler` | `it:software` | The software used to compile the PE executable. |
| `:compiler:name` | `it:softwarename` | The name of the software used to compile the PE executable. |
| `:exports:libname` | `file:path` | The export library name according to the PE. |
| `:exports:time` | `time` | The export time of the file. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:imphash` | `crypto:hash:md5` | The PE import hash of the file as calculated by pefile; https://github.com/erocarrera/pefile . |
| `:packer` | `it:software` | The software used to pack the PE executable. |
| `:packer:name` | `it:softwarename` | The name of the software used to pack the PE executable. |
| `:pdbpath` | `file:path` | The PDB file path. |
| `:richheader` | `crypto:hash:sha256` | The sha256 hash of the rich header bytes. |
| `:size` | `int` | The size of the executable file according to the PE file header. |
| `:versioninfo` | `array of file:mime:pe:vsvers:keyval` | The VS_VERSIONINFO key/value data from the PE file. |

### `file:mime:pe:export`

A named PE export contained in a file.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:name` | `it:dev:str` | The name of the export in the file. |
| `:rva` | `int` | The Relative Virtual Address of the exported function entry point. |

### `file:mime:pe:resource`

A PE resource contained in a file.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:langid` | `pe:langid` | The language code for the resource. |
| `:sha256` | `crypto:hash:sha256` | The SHA256 hash of the resource bytes. |
| `:type` | `pe:resource:type` | The typecode for the resource. |

### `file:mime:pe:section`

A PE section contained in a file.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:name` | `str` | The textual name of the section. |
| `:sha256` | `crypto:hash:sha256` | The sha256 hash of the section. Relocations must be zeroed before hashing. |

### `file:mime:pe:vsvers:keyval`

A key value pair found in a PE VS_VERSIONINFO structure.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `str` | The key for the VS_VERSIONINFO keyval pair. |
| `:value` | `str` | The value for the VS_VERSIONINFO keyval pair. |

### `file:mime:png`

The GUID of a set of mime metadata for a .png file.

| Interface |
|-----------|
| `file:mime:image` |
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:altitude` | `geo:altitude` | MIME specific altitude information extracted from metadata. |
| `:author` | `entity:contact` | MIME specific contact information extracted from metadata. |
| `:comment` | `str` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `str` | MIME specific description field extracted from metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `base:name` | The text contained within the image. |

### `file:mime:rar:entry`

A file entry contained by a RAR archive file.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:archived:size` | `int` | The storage size of the file within the archive. |
| `:created` | `time` | The created time of the file. |
| `:extra:posix:perms` | `int` | The POSIX permissions mask of the archived file. |
| `:file` | `file:bytes` | The file contained by the RAR archive file entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:offset` | `int` | The offset to the beginning of the file within the parent file. |
| `:parent` | `file:bytes` | The parent file which contains the RAR archive file entry. |
| `:path` | `file:path` | The path to the file in the RAR archive file entry. |
| `:seen` | `ival` | The RAR archive file entry was observed during the time interval. |

### `file:mime:rtf`

The GUID of a set of mime metadata for a .rtf file.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:guid` | `guid` | The parsed GUID embedded in the .rtf file. |

### `file:mime:tif`

The GUID of a set of mime metadata for a .tif file.

| Interface |
|-----------|
| `file:mime:image` |
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:altitude` | `geo:altitude` | MIME specific altitude information extracted from metadata. |
| `:author` | `entity:contact` | MIME specific contact information extracted from metadata. |
| `:comment` | `str` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `str` | MIME specific description field extracted from metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `base:name` | The text contained within the image. |

### `file:mime:zip:entry`

A file entry contained by a ZIP archive file.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:archived:size` | `int` | The storage size of the file within the archive. |
| `:comment` | `str` | The comment field from the CDFH in the ZIP archive. |
| `:created` | `time` | The created time of the file. |
| `:extra:posix:gid` | `int` | A POSIX GID extracted from a ZIP Extra Field. |
| `:extra:posix:uid` | `int` | A POSIX UID extracted from a ZIP Extra Field. |
| `:file` | `file:bytes` | The file contained by the ZIP archive file entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:offset` | `int` | The offset to the beginning of the file within the parent file. |
| `:parent` | `file:bytes` | The parent file which contains the ZIP archive file entry. |
| `:path` | `file:path` | The path to the file in the ZIP archive file entry. |
| `:seen` | `ival` | The ZIP archive file entry was observed during the time interval. |

### `file:path`

A normalized file path.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The file path was observed during the time interval. |

### `file:stored:entry`

A stored file entry.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:created` | `time` | The created time of the file. |
| `:file` | `file:bytes` | The file contained by the file entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:path` | `file:path` | The path to the file in the file entry. |
| `:seen` | `ival` | The file entry was observed during the time interval. |

### `file:subfile:entry`

A file entry contained by a parent file.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:created` | `time` | The created time of the file. |
| `:file` | `file:bytes` | The file contained by the subfile entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:offset` | `int` | The offset to the beginning of the file within the parent file. |
| `:parent` | `file:bytes` | The parent file which contains the subfile entry. |
| `:path` | `file:path` | The path to the file in the subfile entry. |
| `:seen` | `ival` | The subfile entry was observed during the time interval. |

### `file:system:entry`

A file entry contained by a host filesystem.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:created` | `time` | The created time of the file. |
| `:creator` | `it:host:account` | The host account which created the file. |
| `:file` | `file:bytes` | The file contained by the file entry. |
| `:host` | `it:host` | The host which contains the filesystem. |
| `:modified` | `time` | The last known modified time of the file. |
| `:owner` | `it:host:account` | The host account which owns the file. |
| `:path` | `file:path` | The path to the file in the file entry. |
| `:seen` | `ival` | The file entry was observed during the time interval. |

### `geo:name`

An unstructured place name or address.

### `geo:place`

A geographic place.

| Interface |
|-----------|
| `geo:locatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:address` | `geo:address` | The postal address where the place was located. |
| `:address:city` | `base:name` | The city where the place was located. |
| `:altitude` | `geo:altitude` | The altitude where the place was located. |
| `:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the place was located. |
| `:bbox` | `geo:bbox` | A bounding box which encompasses where the place was located. |
| `:country` | `pol:country` | The country where the place was located. |
| `:country:code` | `iso:3166:alpha2` | The country code where the place was located. |
| `:desc` | `text` | A description of the place. |
| `:geojson` | `geo:json` | A GeoJSON representation of where the place was located. |
| `:id` | `base:id` | A type specific identifier such as an airport ID. |
| `:latlong` | `geo:latlong` | The latlong where the place was located. |
| `:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the place was located. |
| `:loc` | `loc` | The geopolitical location where the place was located. |
| `:name` | `geo:name` | The name of the place. |
| `:names` | `array of geo:name` | An array of alternative place names. |
| `:photo` | `file:bytes` | The image file to use as the primary image of the place. |
| `:type` | `geo:place:type:taxonomy` | The type of place. |

### `geo:place:type:taxonomy`

A hierarchical taxonomy of place types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `geo:place:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `geo:telem`

The geospatial position and physical characteristics of a node at a given time.

| Interface |
|-----------|
| `geo:locatable` |
| `phys:tangible` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `str` | A description of the telemetry sample. |
| `:node` | `meta:observable` | The node that was observed at the associated time and place. |
| `:phys:height` | `geo:dist` | The physical height of the object. |
| `:phys:length` | `geo:dist` | The physical length of the object. |
| `:phys:mass` | `mass` | The physical mass of the object. |
| `:phys:volume` | `geo:dist` | The physical volume of the object. |
| `:phys:width` | `geo:dist` | The physical width of the object. |
| `:place` | `geo:place` | The place where the item was located. |
| `:place:address` | `geo:address` | The postal address where the item was located. |
| `:place:address:city` | `base:name` | The city where the item was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the item was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the item was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the item was located. |
| `:place:country` | `pol:country` | The country where the item was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the item was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the item was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the item was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the item was located. |
| `:place:loc` | `loc` | The geopolitical location where the item was located. |
| `:place:name` | `geo:name` | The name where the item was located. |
| `:time` | `time` | The time that the telemetry measurements were taken. |

### `gov:cn:icp`

A Chinese Internet Content Provider ID.

| Interface |
|-----------|
| `entity:identifier` |

### `gov:cn:mucd`

A Chinese PLA MUCD.

| Interface |
|-----------|
| `entity:identifier` |

### `gov:us:cage`

A Commercial and Government Entity (CAGE) code.

| Interface |
|-----------|
| `entity:identifier` |

| Property | Type | Doc |
|----------|------|-----|
| `:cc` | `iso:3166:alpha2` | The country code in the CAGE code record. |
| `:city` | `str:lower` | The city in the CAGE code record. |
| `:country` | `str:lower` | The country in the CAGE code record. |
| `:name0` | `entity:name` | The name of the organization. |
| `:name1` | `str:lower` | Name Part 1. |
| `:org` | `ou:org` | The organization which was issued the CAGE code. |
| `:phone0` | `tel:phone` | The primary phone number in the CAGE code record. |
| `:phone1` | `tel:phone` | The alternate phone number in the CAGE code record. |
| `:state` | `str:lower` | The state in the CAGE code record. |
| `:street` | `str:lower` | The street in the CAGE code record. |
| `:zip` | `gov:us:zip` | The zip code in the CAGE code record. |

### `gov:us:ssn`

A US Social Security Number (SSN).

| Interface |
|-----------|
| `entity:identifier` |

### `gov:us:zip`

A US Postal Zip Code.

### `inet:asn`

An Autonomous System Number (ASN).

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:owner` | `entity:actor` | The entity which registered the ASN. |
| `:owner:name` | `entity:name` | The name of the entity which registered the ASN. |
| `:seen` | `ival` | The ASN was observed during the time interval. |

### `inet:asnet`

An Autonomous System Number (ASN) and its associated IP address range.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:asn` | `inet:asn` | The Autonomous System Number (ASN) of the netblock. |
| `:net` | `inet:net` | The IP address range assigned to the ASN. |
| `:net:max` | `inet:ip` | The last IP in the range assigned to the ASN. |
| `:net:min` | `inet:ip` | The first IP in the range assigned to the ASN. |
| `:seen` | `ival` | The address range was observed during the time interval. |

### `inet:asnip`

A historical record of an IP address being assigned to an AS.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:asn` | `inet:asn` | The ASN that the IP was assigned to. |
| `:ip` | `inet:ip` | The IP that was assigned to the ASN. |
| `:seen` | `ival` | The IP ASN assignment was observed during the time interval. |

### `inet:banner`

A network protocol banner string presented by a server.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The banner was observed during the time interval. |
| `:server` | `inet:server` | The server which presented the banner string. |
| `:text` | `it:dev:str` | The banner text. |

### `inet:client`

A network client address.

| Interface |
|-----------|
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:proto` | `str:lower` | The network protocol of the client. |
| `:seen` | `ival` | The network client was observed during the time interval. |

### `inet:dns:a`

The result of a DNS A record lookup.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain queried for its DNS A record. |
| `:ip` | `inet:ip` | The IPv4 address returned in the A record. |
| `:seen` | `ival` | The time range where the record was observed. |

### `inet:dns:aaaa`

The result of a DNS AAAA record lookup.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain queried for its DNS AAAA record. |
| `:ip` | `inet:ip` | The IPv6 address returned in the AAAA record. |
| `:seen` | `ival` | The DNS AAAA record was observed during the time interval. |

### `inet:dns:answer`

A single answer from within a DNS reply.

| Property | Type | Doc |
|----------|------|-----|
| `:mx:priority` | `int` | The DNS MX record priority. |
| `:record` | `inet:dns:a`, `inet:dns:aaaa`, `inet:dns:cname`, `inet:dns:mx`, `inet:dns:ns`, `inet:dns:rev`, `inet:dns:soa`, `inet:dns:txt` | The DNS record returned by the lookup. |
| `:request` | `inet:dns:request` | The DNS request that was answered. |
| `:time` | `time` | The time that the DNS response was transmitted. |
| `:ttl` | `int` | The time to live value of the DNS record in the response. |

### `inet:dns:cname`

The result of a DNS CNAME record lookup.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:cname` | `inet:fqdn` | The domain returned in the CNAME record. |
| `:fqdn` | `inet:fqdn` | The domain queried for its CNAME record. |
| `:seen` | `ival` | The DNS CNAME record was observed during the time interval. |

### `inet:dns:dynreg`

A dynamic DNS registration.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:client` | `inet:client` | The network client address used to register the dynamic FQDN. |
| `:contact` | `entity:contact` | The contact information of the registrant. |
| `:created` | `time` | The time that the dynamic DNS registration was first created. |
| `:fqdn` | `inet:fqdn` | The FQDN registered within a dynamic DNS provider. |
| `:provider` | `ou:org` | The organization which provides the dynamic DNS FQDN. |
| `:provider:fqdn` | `inet:fqdn` | The FQDN of the organization which provides the dynamic DNS FQDN. |
| `:provider:name` | `entity:name` | The name of the organization which provides the dynamic DNS FQDN. |
| `:seen` | `ival` | The dynamic DNS registration was observed during the time interval. |

### `inet:dns:mx`

The result of a DNS MX record lookup.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain queried for its MX record. |
| `:mx` | `inet:fqdn` | The domain returned in the MX record. |
| `:seen` | `ival` | The DNS MX record was observed during the time interval. |

### `inet:dns:ns`

The result of a DNS NS record lookup.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:ns` | `inet:fqdn` | The domain returned in the NS record. |
| `:seen` | `ival` | The DNS NS record was observed during the time interval. |
| `:zone` | `inet:fqdn` | The domain queried for its DNS NS record. |

### `inet:dns:query`

A DNS query unique to a given client.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:client` | `inet:client` | The client that performed the DNS query. |
| `:name` | `inet:dns:name` | The DNS query name string. |
| `:name:fqdn` | `inet:fqdn` | The FQDN in the DNS query name string. |
| `:name:ip` | `inet:ip` | The IP address in the DNS query name string. |
| `:seen` | `ival` | The DNS query was observed during the time interval. |
| `:type` | `int` | The type of record that was queried. |

### `inet:dns:request`

A single instance of a DNS resolver request and optional reply info.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:request` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the link. |
| `:client:host` | `it:host` | The client host which initiated the link. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the link. |
| `:flow` | `inet:flow` | The network flow which contained the request. |
| `:query` | `inet:dns:query` | The DNS query contained in the request. |
| `:query:name` | `inet:dns:name` | The DNS query name string in the request. |
| `:query:name:fqdn` | `inet:fqdn` | The FQDN in the DNS query name string. |
| `:query:name:ip` | `inet:ip` | The IP address in the DNS query name string. |
| `:query:type` | `int` | The type of record requested in the query. |
| `:reply:code` | `dns:reply:code` | The DNS server response code. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the link. |
| `:server:host` | `it:host` | The server host which received the link. |
| `:server:proc` | `it:exec:proc` | The server process which received the link. |
| `:time` | `time` | The time that the event occurred. |

### `inet:dns:rev`

The transformed result of a DNS PTR record lookup.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain returned in the PTR record. |
| `:ip` | `inet:ip` | The IP address queried for its DNS PTR record. |
| `:seen` | `ival` | The Reverse DNS record was observed during the time interval. |

### `inet:dns:soa`

The result of a DNS SOA record lookup.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:email` | `inet:email` | The email address (RNAME) returned in the SOA record. |
| `:fqdn` | `inet:fqdn` | The domain queried for its SOA record. |
| `:ns` | `inet:fqdn` | The domain (MNAME) returned in the SOA record. |
| `:seen` | `ival` | The DNS SOA record was observed during the time interval. |

### `inet:dns:txt`

The result of a DNS TXT record lookup.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain queried for its TXT record. |
| `:seen` | `ival` | The DNS TXT record was observed during the time interval. |
| `:txt` | `str` | The string returned in the TXT record. |

### `inet:dns:wild:a`

A DNS A wild card record and the IPv4 it resolves to.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain containing a wild card record. |
| `:ip` | `inet:ip` | The IPv4 address returned by wild card resolutions. |
| `:seen` | `ival` | The DNS wildcard A record was observed during the time interval. |

### `inet:dns:wild:aaaa`

A DNS AAAA wild card record and the IPv6 it resolves to.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain containing a wild card record. |
| `:ip` | `inet:ip` | The IPv6 address returned by wild card resolutions. |
| `:seen` | `ival` | The DNS wildcard AAAA record was observed during the time interval. |

### `inet:egress`

A host using a specific network egress client address.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account` | The service account which used the client address to egress. |
| `:client` | `inet:client` | The client address the host used as a network egress. |
| `:host` | `it:host` | The host that used the network egress. |
| `:host:iface` | `inet:iface` | The interface which the host used to connect out via the egress. |
| `:seen` | `ival` | The egress client was observed during the time interval. |

### `inet:email`

An email address.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `inet:email` | The base email address which is populated if the email address contains a user with a +<tag>. |
| `:fqdn` | `inet:fqdn` | The domain of the email address. |
| `:plus` | `str:lower` | The optional email address "tag". |
| `:seen` | `ival` | The email address was observed during the time interval. |
| `:user` | `inet:user` | The username of the email address. |

### `inet:email:header`

A unique email message header.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `inet:email:header:name` | The name of the email header. |
| `:seen` | `ival` | The email header was observed during the time interval. |
| `:value` | `str` | The value of the email header. |

### `inet:email:message`

An individual email message delivered to an inbox.

| Property | Type | Doc |
|----------|------|-----|
| `:attachments` | `array of file:attachment` | An array of files attached to the email message. |
| `:body` | `text` | The body of the email message. |
| `:bytes` | `file:bytes` | The file bytes which contain the email message. |
| `:cc` | `array of inet:email` | Email addresses parsed from the "cc" header. |
| `:date` | `time` | The time the email message was delivered. |
| `:flow` | `inet:flow` | The inet:flow which delivered the message. |
| `:from` | `inet:email` | The email address of the sender. |
| `:headers` | `array of inet:email:header` | An array of email headers from the message. |
| `:id` | `base:id` | The ID parsed from the "message-id" header. |
| `:links` | `array of inet:hyperlink` | An array of links embedded in the email message. |
| `:received:from:fqdn` | `inet:fqdn` | The sending server FQDN, potentially from the Received: header. |
| `:received:from:ip` | `inet:ip` | The sending SMTP server IP, potentially from the Received: header. |
| `:replyto` | `inet:email` | The email address parsed from the "reply-to" header. |
| `:subject` | `str` | The email message subject parsed from the "subject" header. |
| `:to` | `inet:email` | The email address of the recipient. |

### `inet:flow`

A network connection between a client and server.

| Interface |
|-----------|
| `base:activity` |
| `inet:proto:link` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this network flow. |
| `:capture:host` | `it:host` | The host which captured the flow. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the network flow. |
| `:client:handshake` | `text` | A text representation of the initial handshake sent by the client. |
| `:client:host` | `it:host` | The client host which initiated the network flow. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the network flow. |
| `:client:software:cpes` | `array of it:sec:cpe` | An array of NIST CPEs identified on the client. |
| `:client:software:names` | `array of it:softwarename` | An array of software names identified on the client. |
| `:client:txbytes` | `int` | The number of bytes sent by the client. |
| `:client:txcount` | `int` | The number of packets sent by the client. |
| `:client:txfiles` | `array of file:attachment` | An array of files sent by the client. |
| `:ip:proto` | `int` | The IP protocol number of the flow. |
| `:ip:tcp:flags` | `int` | An aggregation of observed TCP flags commonly provided by flow APIs. |
| `:period` | `ival` | The period over which the network flow occurred. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the network flow. |
| `:server:handshake` | `text` | A text representation of the initial handshake sent by the server. |
| `:server:host` | `it:host` | The server host which received the network flow. |
| `:server:proc` | `it:exec:proc` | The server process which received the network flow. |
| `:server:software:cpes` | `array of it:sec:cpe` | An array of NIST CPEs identified on the server. |
| `:server:software:names` | `array of it:softwarename` | An array of software names identified on the server. |
| `:server:txbytes` | `int` | The number of bytes sent by the server. |
| `:server:txcount` | `int` | The number of packets sent by the server. |
| `:server:txfiles` | `array of file:attachment` | An array of files sent by the server. |
| `:tot:txbytes` | `int` | The number of bytes sent in both directions. |
| `:tot:txcount` | `int` | The number of packets sent in both directions. |

### `inet:fqdn`

A Fully Qualified Domain Name (FQDN).

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:domain` | `inet:fqdn` | The parent domain for the FQDN. |
| `:host` | `str:lower` | The host part of the FQDN. |
| `:issuffix` | `bool` | True if the FQDN is considered a suffix. |
| `:iszone` | `bool` | True if the FQDN is considered a zone. |
| `:seen` | `ival` | The FQDN was observed during the time interval. |
| `:zone` | `inet:fqdn` | The zone level parent for this FQDN. |

### `inet:http:cookie`

An individual HTTP cookie string.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `str` | The name of the cookie preceding the equal sign. |
| `:value` | `str` | The value of the cookie after the equal sign if present. |

### `inet:http:param`

An HTTP request path query parameter.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `str:lower` | The name of the HTTP query parameter. |
| `:value` | `str` | The value of the HTTP query parameter. |

### `inet:http:request`

A single HTTP request.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:request` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:body` | `file:bytes` | The body of the HTTP request. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the link. |
| `:client:host` | `it:host` | The client host which initiated the link. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the link. |
| `:cookies` | `array of inet:http:cookie` | An array of HTTP cookie values parsed from the "Cookies:" header in the request. |
| `:flow` | `inet:flow` | The network flow which contained the request. |
| `:header:host` | `inet:fqdn` | The FQDN parsed from the "Host:" header in the request. |
| `:header:referer` | `inet:url` | The referer URL parsed from the "Referer:" header in the request. |
| `:headers` | `array of inet:http:request:header` | An array of HTTP headers from the request. |
| `:method` | `str` | The HTTP request method string. |
| `:path` | `str` | The requested HTTP path (without query parameters). |
| `:query` | `str` | The HTTP query string which optionally follows the path. |
| `:response:body` | `file:bytes` | The HTTP response body received. |
| `:response:code` | `int` | The HTTP response code received. |
| `:response:headers` | `array of inet:http:response:header` | An array of HTTP headers from the response. |
| `:response:reason` | `str` | The HTTP response reason phrase received. |
| `:response:time` | `time` | The time a response to the request was received. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the link. |
| `:server:host` | `it:host` | The server host which received the link. |
| `:server:proc` | `it:exec:proc` | The server process which received the link. |
| `:session` | `inet:http:session` | The HTTP session this request was part of. |
| `:time` | `time` | The time that the event occurred. |
| `:url` | `inet:url` | The reconstructed URL for the request if known. |

### `inet:http:request:header`

An HTTP request header.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `inet:http:header:name` | The name of the HTTP request header. |
| `:seen` | `ival` | The HTTP request header was observed during the time interval. |
| `:value` | `str` | The value of the HTTP request header. |

### `inet:http:response:header`

An HTTP response header.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `inet:http:header:name` | The name of the HTTP response header. |
| `:value` | `str` | The value of the HTTP response header. |

### `inet:http:session`

An HTTP session.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:contact` | The entity contact which owns the session. |
| `:cookies` | `array of inet:http:cookie` | An array of cookies used to identify this specific session. |

### `inet:hyperlink`

A URL link embedded in a message.

| Property | Type | Doc |
|----------|------|-----|
| `:title` | `str` | The displayed hyperlink text if it was not the URL. |
| `:url` | `inet:url` | The URL target of the hyperlink. |

### `inet:iface`

A network interface with a set of associated protocol addresses.

| Property | Type | Doc |
|----------|------|-----|
| `:adid` | `it:adid` | An advertising ID associated with the interface. |
| `:host` | `it:host` | The guid of the host the interface is associated with. |
| `:ip` | `inet:ip` | The IP address of the interface. |
| `:mac` | `inet:mac` | The ethernet (MAC) address of the interface. |
| `:mob:imei` | `tel:mob:imei` | The IMEI of the interface. |
| `:mob:imsi` | `tel:mob:imsi` | The IMSI of the interface. |
| `:name` | `str` | The interface name. |
| `:network` | `it:network` | The guid of the it:network the interface connected to. |
| `:phone` | `tel:phone` | The telephone number of the interface. |
| `:type` | `inet:iface:type:taxonomy` | The interface type. |
| `:wifi:ap:bssid` | `inet:mac` | The BSSID of the Wi-Fi AP the interface connected to. |
| `:wifi:ap:ssid` | `inet:wifi:ssid` | The SSID of the Wi-Fi AP the interface connected to. |

### `inet:iface:type:taxonomy`

A hierarchical taxonomy of network interface types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `inet:iface:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `inet:ip`

An IPv4 or IPv6 address.

| Interface |
|-----------|
| `geo:locatable` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:asn` | `inet:asn` | The ASN to which the IP address is currently assigned. |
| `:dns:rev` | `inet:fqdn` | The most current DNS reverse lookup for the IP. |
| `:place` | `geo:place` | The place where the IP address was located. |
| `:place:address` | `geo:address` | The postal address where the IP address was located. |
| `:place:address:city` | `base:name` | The city where the IP address was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the IP address was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the IP address was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the IP address was located. |
| `:place:country` | `pol:country` | The country where the IP address was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the IP address was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the IP address was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the IP address was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the IP address was located. |
| `:place:loc` | `loc` | The geopolitical location where the IP address was located. |
| `:place:name` | `geo:name` | The name where the IP address was located. |
| `:scope` | `inet:ipscope` | The IPv6 scope of the address (e.g., global, link-local, etc.). |
| `:seen` | `ival` | The IP address was observed during the time interval. |
| `:type` | `str` | The type of IP address (e.g., private, multicast, etc.). |
| `:version` | `inet:ipversion` | The IP version of the address. |

### `inet:mac`

A 48-bit Media Access Control (MAC) address.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The MAC address was observed during the time interval. |
| `:vendor` | `ou:org` | The vendor associated with the 24-bit prefix of a MAC address. |
| `:vendor:name` | `entity:name` | The name of the vendor associated with the 24-bit prefix of a MAC address. |

### `inet:net`

An IPv4 or IPv6 address range.

| Property | Type | Doc |
|----------|------|-----|
| `:max` | `inet:ip` | The last IP address in the network range. |
| `:min` | `inet:ip` | The first IP address in the network range. |

### `inet:proto`

A network protocol name.

| Property | Type | Doc |
|----------|------|-----|
| `:port` | `inet:port` | The default port this protocol typically uses if applicable. |

### `inet:rdp:handshake`

An instance of an RDP handshake between a client and server.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:request` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the link. |
| `:client:host` | `it:host` | The client host which initiated the link. |
| `:client:hostname` | `it:hostname` | The hostname sent by the client as part of an RDP session setup. |
| `:client:keyboard:layout` | `base:name` | The keyboard layout sent by the client as part of an RDP session setup. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the link. |
| `:flow` | `inet:flow` | The network flow which contained the request. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the link. |
| `:server:host` | `it:host` | The server host which received the link. |
| `:server:proc` | `it:exec:proc` | The server process which received the link. |
| `:time` | `time` | The time that the event occurred. |

### `inet:rfc2822:addr`

An RFC 2822 Address field.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:email` | `inet:email` | The email field parsed from an RFC 2822 address string. |
| `:name` | `entity:name` | The name field parsed from an RFC 2822 address string. |
| `:seen` | `ival` | The RFC 2822 address was observed during the time interval. |

### `inet:search:query`

An instance of a search query issued to a search engine.

| Interface |
|-----------|
| `inet:service:action` |
| `inet:service:base` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account` | The account which initiated the action. |
| `:agent` | `inet:service:agent` | The service agent which performed the action potentially on behalf of an account. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software used to initiate the action. |
| `:engine` | `base:name` | A simple name for the search engine used. |
| `:error:code` | `str` | The platform specific error code if the action was unsuccessful. |
| `:error:reason` | `str` | The platform specific friendly error reason if the action was unsuccessful. |
| `:host` | `it:host` | The host that issued the query. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:request` | `inet:http:request` | The HTTP request used to issue the query. |
| `:rule` | `inet:service:rule` | The rule which allowed or denied the action. |
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:success` | `bool` | Set to true if the action was successful. |
| `:text` | `text` | The search query text. |
| `:time` | `time` | The time the web search was issued. |

### `inet:search:result`

A single result from a web search.

| Property | Type | Doc |
|----------|------|-----|
| `:query` | `inet:search:query` | The search query that produced the result. |
| `:rank` | `int` | The rank/order of the query result. |
| `:text` | `str:lower` | Extracted/matched text from the matched content. |
| `:title` | `str:lower` | The title of the matching web page. |
| `:url` | `inet:url` | The URL hosting the matching content. |

### `inet:server`

A network server address.

| Interface |
|-----------|
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:proto` | `str:lower` | The network protocol of the server. |
| `:seen` | `ival` | The network server was observed during the time interval. |

### `inet:serverfile`

A file hosted by a server.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that was hosted on the server. |
| `:seen` | `ival` | The host server and file was observed during the time interval. |
| `:server` | `inet:server` | The server which hosted the file. |

### `inet:service:access`

Represents a user access request to a service resource.

| Interface |
|-----------|
| `inet:service:action` |
| `inet:service:base` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account` | The account which initiated the action. |
| `:action` | `inet:service:access:action:taxonomy` | The platform specific action which this access records. |
| `:agent` | `inet:service:agent` | The service agent which performed the action potentially on behalf of an account. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software used to initiate the action. |
| `:error:code` | `str` | The platform specific error code if the action was unsuccessful. |
| `:error:reason` | `str` | The platform specific friendly error reason if the action was unsuccessful. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:resource` | `inet:service:resource` | The resource which the account attempted to access. |
| `:rule` | `inet:service:rule` | The rule which allowed or denied the action. |
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:success` | `bool` | Set to true if the action was successful. |
| `:time` | `time` | The time that the account initiated the action. |
| `:type` | `inet:svcaccess:type` | The type of access requested. |

### `inet:service:account`

An account within a service platform. Accounts may be instance specific.

| Interface |
|-----------|
| `econ:pay:instrument` |
| `entity:actor` |
| `entity:multiple` |
| `entity:resolvable` |
| `entity:singular` |
| `geo:locatable` |
| `inet:service:base` |
| `inet:service:object` |
| `inet:service:subscriber` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The account contains the funds used by the service account. |
| `:birth:place` | `geo:place` | The place where the service account was born. |
| `:birth:place:address` | `geo:address` | The postal address where the service account was born. |
| `:birth:place:address:city` | `base:name` | The city where the service account was born. |
| `:birth:place:altitude` | `geo:altitude` | The altitude where the service account was born. |
| `:birth:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the service account was born. |
| `:birth:place:bbox` | `geo:bbox` | A bounding box which encompasses where the service account was born. |
| `:birth:place:country` | `pol:country` | The country where the service account was born. |
| `:birth:place:country:code` | `iso:3166:alpha2` | The country code where the service account was born. |
| `:birth:place:geojson` | `geo:json` | A GeoJSON representation of where the service account was born. |
| `:birth:place:latlong` | `geo:latlong` | The latlong where the service account was born. |
| `:birth:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the service account was born. |
| `:birth:place:loc` | `loc` | The geopolitical location where the service account was born. |
| `:birth:place:name` | `geo:name` | The name where the service account was born. |
| `:creator` | `inet:service:account` | The service account which created the service account. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:death:place` | `geo:place` | The place where the service account died. |
| `:death:place:address` | `geo:address` | The postal address where the service account died. |
| `:death:place:address:city` | `base:name` | The city where the service account died. |
| `:death:place:altitude` | `geo:altitude` | The altitude where the service account died. |
| `:death:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the service account died. |
| `:death:place:bbox` | `geo:bbox` | A bounding box which encompasses where the service account died. |
| `:death:place:country` | `pol:country` | The country where the service account died. |
| `:death:place:country:code` | `iso:3166:alpha2` | The country code where the service account died. |
| `:death:place:geojson` | `geo:json` | A GeoJSON representation of where the service account died. |
| `:death:place:latlong` | `geo:latlong` | The latlong where the service account died. |
| `:death:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the service account died. |
| `:death:place:loc` | `loc` | The geopolitical location where the service account died. |
| `:death:place:name` | `geo:name` | The name where the service account died. |
| `:email` | `inet:email` | The primary email address for the service account. |
| `:id` | `base:id` | A platform specific ID which identifies the service account. |
| `:name` | `entity:name` | The primary entity name of the service account. |
| `:org` | `ou:org` | An associated organization listed as part of the contact information. |
| `:org:name` | `entity:name` | The name of an associated organization listed as part of the contact information. |
| `:parent` | `inet:service:account` | A parent account which owns this account. |
| `:period` | `ival` | The period when the service account existed. |
| `:platform` | `inet:service:platform` | The platform which defines the service account. |
| `:profile` | `entity:contact` | Current detailed contact information for the service account. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the service account. |
| `:resolved` | `ou:org`, `ps:person` | The resolved entity to which this service account belongs. |
| `:rules` | `array of inet:service:rule` | An array of rules associated with this account. |
| `:seen` | `ival` | The service account was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the service account. |
| `:tenant` | `inet:service:tenant` | The tenant which contains the account. |
| `:title` | `entity:title` | The entity title or role for this service account. |
| `:titles` | `array of entity:title` | An array of alternate entity titles or roles for this service account. |
| `:url` | `inet:url` | The primary URL associated with the service account. |
| `:user` | `inet:user` | The primary user name for the service account. |

### `inet:service:agent`

An instance of a deployed agent or software integration which is part of the service architecture.

| Interface |
|-----------|
| `entity:actor` |
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:desc` | `str` | A description of the deployed service agent instance. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:name` | `base:name` | The name of the service agent instance. |
| `:names` | `array of base:name` | An array of alternate names for the service agent instance. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:software` | `it:software` | The latest known software version running on the service agent instance. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:url` | `inet:url` | The primary URL associated with the object. |

### `inet:service:bucket`

A file/blob storage object within a service architecture.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the bucket. |
| `:desc` | `text` | A description of the service resource. |
| `:id` | `base:id` | A platform specific ID which identifies the bucket. |
| `:name` | `base:name` | The name of the service resource. |
| `:period` | `ival` | The period when the bucket existed. |
| `:platform` | `inet:service:platform` | The platform which defines the bucket. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the bucket. |
| `:seen` | `ival` | The bucket was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the bucket. |
| `:type` | `inet:service:resource:type:taxonomy` | The resource type. For example "rpc.endpoint". |
| `:url` | `inet:url` | The primary URL associated with the bucket. |

### `inet:service:bucket:item`

An individual file stored within a bucket.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:bucket` | `inet:service:bucket` | The bucket which contains the item. |
| `:creator` | `inet:service:account` | The service account which created the bucket item. |
| `:desc` | `text` | A description of the service resource. |
| `:file` | `file:bytes` | The bytes stored within the bucket item. |
| `:file:name` | `file:path` | The name of the file stored in the bucket item. |
| `:id` | `base:id` | A platform specific ID which identifies the bucket item. |
| `:name` | `base:name` | The name of the service resource. |
| `:period` | `ival` | The period when the bucket item existed. |
| `:platform` | `inet:service:platform` | The platform which defines the bucket item. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the bucket item. |
| `:seen` | `ival` | The bucket item was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the bucket item. |
| `:type` | `inet:service:resource:type:taxonomy` | The resource type. For example "rpc.endpoint". |
| `:url` | `inet:url` | The primary URL associated with the bucket item. |

### `inet:service:channel`

A channel used to distribute messages.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:joinable` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the channel. |
| `:id` | `base:id` | A platform specific ID which identifies the channel. |
| `:name` | `base:name` | The name of the channel. |
| `:period` | `ival` | The time period where the channel was available. |
| `:platform` | `inet:service:platform` | The platform which defines the channel. |
| `:profile` | `entity:contact` | Current detailed contact information for this channel. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the channel. |
| `:seen` | `ival` | The channel was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the channel. |
| `:topic` | `base:name` | The visible topic of the channel. |
| `:url` | `inet:url` | The primary URL associated with the channel. |

### `inet:service:emote`

An emote or reaction by an account.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:about` | `inet:service:object` | The node that the emote is about. |
| `:creator` | `inet:service:account` | The service account which created the emote. |
| `:id` | `base:id` | A platform specific ID which identifies the emote. |
| `:period` | `ival` | The period when the emote existed. |
| `:platform` | `inet:service:platform` | The platform which defines the emote. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the emote. |
| `:seen` | `ival` | The emote was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the emote. |
| `:text` | `str` | The unicode or emote text of the reaction. |
| `:url` | `inet:url` | The primary URL associated with the emote. |

### `inet:service:login`

A login event for a service account.

| Interface |
|-----------|
| `inet:service:action` |
| `inet:service:base` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account` | The account which initiated the action. |
| `:agent` | `inet:service:agent` | The service agent which performed the action potentially on behalf of an account. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software used to initiate the action. |
| `:creds` | `array of auth:credential` | The credentials that were used to login. |
| `:error:code` | `str` | The platform specific error code if the action was unsuccessful. |
| `:error:reason` | `str` | The platform specific friendly error reason if the action was unsuccessful. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:method` | `inet:service:login:method:taxonomy` | The type of authentication used for the login. For example "password" or "multifactor.sms". |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:rule` | `inet:service:rule` | The rule which allowed or denied the action. |
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:success` | `bool` | Set to true if the action was successful. |
| `:time` | `time` | The time that the account initiated the action. |
| `:url` | `inet:url` | The URL of the login endpoint used for this login attempt. |

### `inet:service:login:method:taxonomy`

A hierarchical taxonomy of service login methods.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `inet:service:login:method:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `inet:service:member`

Represents a service account being a member of a channel or group.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account` | The account that was a member of the channel or group. |
| `:creator` | `inet:service:account` | The service account which created the membership. |
| `:id` | `base:id` | A platform specific ID which identifies the membership. |
| `:of` | `inet:service:joinable` | The channel or group that the account was a member of. |
| `:period` | `ival` | The time period where the account was a member. |
| `:platform` | `inet:service:platform` | The platform which defines the membership. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the membership. |
| `:seen` | `ival` | The membership was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the membership. |
| `:url` | `inet:url` | The primary URL associated with the membership. |

### `inet:service:message`

A message or post created by an account.

| Interface |
|-----------|
| `inet:service:action` |
| `inet:service:base` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account` | The account which sent the message. |
| `:agent` | `inet:service:agent` | The service agent which performed the action potentially on behalf of an account. |
| `:attachments` | `array of file:attachment` | An array of files attached to the message. |
| `:channel` | `inet:service:channel` | The channel that the message was sent to. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software version used to send the message. |
| `:client:software:name` | `it:softwarename` | The name of the client software used to send the message. |
| `:error:code` | `str` | The platform specific error code if the action was unsuccessful. |
| `:error:reason` | `str` | The platform specific friendly error reason if the action was unsuccessful. |
| `:file` | `file:bytes` | The raw file that the message was extracted from. |
| `:hashtags` | `array of lang:hashtag` | An array of hashtags mentioned within the message. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:links` | `array of inet:hyperlink` | An array of links contained within the message. |
| `:mentions` | `array of inet:service:account, inet:service:role` | Contactable entities mentioned within the message. |
| `:place` | `geo:place` | The place that the message was sent from. |
| `:place:name` | `geo:name` | The name of the place that the message was sent from. |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:public` | `bool` | Set to true if the message is publicly visible. |
| `:replyto` | `inet:service:message` | The message that this message was sent in reply to. Used for message threading. |
| `:repost` | `inet:service:message` | The original message reposted by this message. |
| `:role` | `inet:service:role` | The role that the message was sent to. |
| `:rule` | `inet:service:rule` | The rule which allowed or denied the action. |
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:status` | `inet:service:object:status` | The message status. |
| `:success` | `bool` | Set to true if the action was successful. |
| `:text` | `text` | The text body of the message. |
| `:thread` | `inet:service:thread` | The thread which contains the message. |
| `:time` | `time` | The time that the account initiated the action. |
| `:title` | `base:name` | The message title. |
| `:to` | `inet:service:account` | The destination account. Used for direct messages. |
| `:type` | `inet:service:message:type:taxonomy` | The type of message. |
| `:url` | `inet:url` | The URL where the message may be viewed. |

### `inet:service:message:type:taxonomy`

A hierarchical taxonomy of message types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `inet:service:message:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `inet:service:permission`

A permission which may be granted to a service account or role.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the permission. |
| `:id` | `base:id` | A platform specific ID which identifies the permission. |
| `:name` | `base:name` | The name of the permission. |
| `:period` | `ival` | The period when the permission existed. |
| `:platform` | `inet:service:platform` | The platform which defines the permission. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the permission. |
| `:seen` | `ival` | The permission was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the permission. |
| `:type` | `inet:service:permission:type:taxonomy` | The type of permission. |
| `:url` | `inet:url` | The primary URL associated with the permission. |

### `inet:service:permission:type:taxonomy`

A hierarchical taxonomy of service permission types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `inet:service:permission:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `inet:service:platform`

A network platform which provides services.

| Interface |
|-----------|
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the platform. |
| `:desc` | `text` | A description of the service platform. |
| `:family` | `base:name` | A family designation for use with instanced platforms such as Slack, Discord, or Mastodon. |
| `:id` | `base:id` | An ID which identifies the platform. |
| `:name` | `base:name` | A friendly name for the platform. |
| `:names` | `array of base:name` | An array of alternate names for the platform. |
| `:parent` | `inet:service:platform` | A parent platform which owns this platform. |
| `:period` | `ival` | The period when the platform existed. |
| `:provider` | `ou:org` | The organization which operates the platform. |
| `:provider:name` | `entity:name` | The name of the organization which operates the platform. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the platform. |
| `:seen` | `ival` | The platform was observed during the time interval. |
| `:software` | `it:software` | The latest known software version that the platform is running. |
| `:status` | `inet:service:object:status` | The status of the platform. |
| `:type` | `inet:service:platform:type:taxonomy` | The type of service platform. |
| `:url` | `inet:url` | The primary URL of the platform. |
| `:urls` | `array of inet:url` | An array of alternate URLs for the platform. |
| `:zone` | `inet:fqdn` | The primary zone for the platform. |
| `:zones` | `array of inet:fqdn` | An array of alternate zones for the platform. |

### `inet:service:platform:type:taxonomy`

A service platform type taxonomy.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `inet:service:platform:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `inet:service:relationship`

A relationship between two service objects.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the relationship. |
| `:id` | `base:id` | A platform specific ID which identifies the relationship. |
| `:period` | `ival` | The period when the relationship existed. |
| `:platform` | `inet:service:platform` | The platform which defines the relationship. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the relationship. |
| `:seen` | `ival` | The relationship was observed during the time interval. |
| `:source` | `inet:service:object` | The source object. |
| `:status` | `inet:service:object:status` | The status of the relationship. |
| `:target` | `inet:service:object` | The target object. |
| `:type` | `inet:service:relationship:type:taxonomy` | The type of relationship between the source and the target. |
| `:url` | `inet:url` | The primary URL associated with the relationship. |

### `inet:service:relationship:type:taxonomy`

A service object relationship type taxonomy.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `inet:service:relationship:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `inet:service:resource`

A generic resource provided by the service architecture.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the resource. |
| `:desc` | `text` | A description of the service resource. |
| `:id` | `base:id` | A platform specific ID which identifies the resource. |
| `:name` | `base:name` | The name of the service resource. |
| `:period` | `ival` | The period when the resource existed. |
| `:platform` | `inet:service:platform` | The platform which defines the resource. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the resource. |
| `:seen` | `ival` | The resource was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the resource. |
| `:type` | `inet:service:resource:type:taxonomy` | The resource type. For example "rpc.endpoint". |
| `:url` | `inet:url` | The primary URL where the resource is available from the service. |

### `inet:service:resource:type:taxonomy`

A hierarchical taxonomy of service resource types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `inet:service:resource:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `inet:service:role`

A role which contains member accounts.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:joinable` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the service role. |
| `:id` | `base:id` | A platform specific ID which identifies the service role. |
| `:name` | `base:name` | The name of the role on this platform. |
| `:period` | `ival` | The period when the service role existed. |
| `:platform` | `inet:service:platform` | The platform which defines the service role. |
| `:profile` | `entity:contact` | Current detailed contact information for this role. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the service role. |
| `:rules` | `array of inet:service:rule` | An array of rules associated with this role. |
| `:seen` | `ival` | The service role was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the service role. |
| `:url` | `inet:url` | The primary URL associated with the service role. |

### `inet:service:rule`

A rule which grants or denies a permission to a service account or role.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the rule. |
| `:denied` | `bool` | Set to (true) to denote that the rule is an explicit deny. |
| `:grantee` | `inet:service:account`, `inet:service:role` | The user or role which is granted the permission. |
| `:id` | `base:id` | A platform specific ID which identifies the rule. |
| `:object` | `inet:service:object` | The object that the permission controls access to. |
| `:period` | `ival` | The period when the rule existed. |
| `:permission` | `inet:service:permission` | The permission which is granted. |
| `:platform` | `inet:service:platform` | The platform which defines the rule. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the rule. |
| `:seen` | `ival` | The rule was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the rule. |
| `:url` | `inet:url` | The primary URL associated with the rule. |

### `inet:service:session`

An authenticated session.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The account which authenticated to create the session. |
| `:http:session` | `inet:http:session` | The HTTP session associated with the service session. |
| `:id` | `base:id` | A platform specific ID which identifies the session. |
| `:period` | `ival` | The period where the session was valid. |
| `:platform` | `inet:service:platform` | The platform which defines the session. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the session. |
| `:seen` | `ival` | The session was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the session. |
| `:url` | `inet:url` | The primary URL associated with the session. |

### `inet:service:subscription`

A subscription to a service platform or instance.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the subscription. |
| `:id` | `base:id` | A platform specific ID which identifies the subscription. |
| `:level` | `inet:service:subscription:level:taxonomy` | A platform specific subscription level. |
| `:pay:instrument` | `econ:pay:instrument` | The primary payment instrument used to pay for the subscription. |
| `:period` | `ival` | The period when the subscription existed. |
| `:platform` | `inet:service:platform` | The platform which defines the subscription. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the subscription. |
| `:seen` | `ival` | The subscription was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the subscription. |
| `:subscriber` | `inet:service:subscriber` | The subscriber who owns the subscription. |
| `:url` | `inet:url` | The primary URL associated with the subscription. |

### `inet:service:subscription:level:taxonomy`

A taxonomy of platform specific subscription levels.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `inet:service:subscription:level:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `inet:service:tenant`

A tenant which groups accounts and instances.

| Interface |
|-----------|
| `entity:actor` |
| `entity:resolvable` |
| `inet:service:base` |
| `inet:service:object` |
| `inet:service:subscriber` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the tenant. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:email` | `inet:email` | The primary email address for the tenant. |
| `:id` | `base:id` | A platform specific ID which identifies the tenant. |
| `:name` | `entity:name` | The primary entity name of the tenant. |
| `:period` | `ival` | The period when the tenant existed. |
| `:platform` | `inet:service:platform` | The platform which defines the tenant. |
| `:profile` | `entity:contact` | Current detailed contact information for the tenant. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the tenant. |
| `:resolved` | `ou:org`, `ps:person` | The resolved entity to which this tenant belongs. |
| `:seen` | `ival` | The tenant was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the tenant. |
| `:url` | `inet:url` | The primary URL associated with the tenant. |
| `:user` | `inet:user` | The primary user name for the tenant. |

### `inet:service:thread`

A message thread.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:channel` | `inet:service:channel` | The channel that contains the thread. |
| `:creator` | `inet:service:account` | The service account which created the thread. |
| `:id` | `base:id` | A platform specific ID which identifies the thread. |
| `:message` | `inet:service:message` | The message which initiated the thread. |
| `:period` | `ival` | The period when the thread existed. |
| `:platform` | `inet:service:platform` | The platform which defines the thread. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the thread. |
| `:seen` | `ival` | The thread was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the thread. |
| `:title` | `base:name` | The title of the thread. |
| `:url` | `inet:url` | The primary URL associated with the thread. |

### `inet:ssh:handshake`

An instance of an SSH handshake between a client and server.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:request` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the link. |
| `:client:host` | `it:host` | The client host which initiated the link. |
| `:client:key` | `crypto:key` | The key used by the SSH client. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the link. |
| `:flow` | `inet:flow` | The network flow which contained the request. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the link. |
| `:server:host` | `it:host` | The server host which received the link. |
| `:server:key` | `crypto:key` | The key used by the SSH server. |
| `:server:proc` | `it:exec:proc` | The server process which received the link. |
| `:time` | `time` | The time that the event occurred. |

### `inet:tls:clientcert`

An x509 certificate sent by a client for TLS.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:cert` | `crypto:x509:cert` | The x509 certificate sent by the client. |
| `:client` | `inet:client` | The client associated with the x509 certificate. |
| `:seen` | `ival` | The TLS client certificate was observed during the time interval. |

### `inet:tls:handshake`

An instance of a TLS handshake between a client and server.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:request` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:cert` | `crypto:x509:cert` | The x509 certificate sent by the client during the handshake. |
| `:client:exe` | `file:bytes` | The client executable which initiated the link. |
| `:client:host` | `it:host` | The client host which initiated the link. |
| `:client:ja3` | `crypto:hash:md5` | The JA3 fingerprint of the client request. |
| `:client:ja4` | `inet:tls:ja4` | The JA4 fingerprint of the client request. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the link. |
| `:flow` | `inet:flow` | The network flow which contained the request. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:cert` | `crypto:x509:cert` | The x509 certificate sent by the server during the handshake. |
| `:server:exe` | `file:bytes` | The server executable which received the link. |
| `:server:host` | `it:host` | The server host which received the link. |
| `:server:ja3s` | `crypto:hash:md5` | The JA3S fingerprint of the server response. |
| `:server:ja4s` | `inet:tls:ja4s` | The JA4S fingerprint of the server response. |
| `:server:jarmhash` | `inet:tls:jarmhash` | The JARM hash computed from the server response. |
| `:server:proc` | `it:exec:proc` | The server process which received the link. |
| `:time` | `time` | The time that the event occurred. |

### `inet:tls:ja3:sample`

A JA3 sample taken from a client.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:client` | `inet:client` | The client that was sampled to produce the JA3 hash. |
| `:ja3` | `crypto:hash:md5` | The JA3 hash computed from the client's TLS hello packet. |
| `:seen` | `ival` | The JA3 sample was observed during the time interval. |

### `inet:tls:ja3s:sample`

A JA3 sample taken from a server.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:ja3s` | `crypto:hash:md5` | The JA3S hash computed from the server's TLS hello packet. |
| `:seen` | `ival` | The JA3S sample was observed during the time interval. |
| `:server` | `inet:server` | The server that was sampled to produce the JA3S hash. |

### `inet:tls:ja4`

A JA4 TLS client fingerprint.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The JA4 fingerprint was observed during the time interval. |

### `inet:tls:ja4:sample`

A JA4 TLS client fingerprint used by a client.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:client` | `inet:client` | The client which initiated the TLS handshake with a JA4 fingerprint. |
| `:ja4` | `inet:tls:ja4` | The JA4 TLS client fingerprint. |
| `:seen` | `ival` | The JA4 sample was observed during the time interval. |

### `inet:tls:ja4s`

A JA4S TLS server fingerprint.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The JA4S fingerprint was observed during the time interval. |

### `inet:tls:ja4s:sample`

A JA4S TLS server fingerprint used by a server.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:ja4s` | `inet:tls:ja4s` | The JA4S TLS server fingerprint. |
| `:seen` | `ival` | The JA4S sample was observed during the time interval. |
| `:server` | `inet:server` | The server which responded to the TLS handshake with a JA4S fingerprint. |

### `inet:tls:jarmhash`

A TLS JARM fingerprint hash.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:ciphers` | `inet:jarm:ciphers` | The encoded cipher and TLS version of the server. |
| `:extensions` | `inet:jarm:extensions` | The truncated SHA256 of the TLS server extensions. |
| `:seen` | `ival` | The JARM fingerprint was observed during the time interval. |

### `inet:tls:jarmsample`

A JARM hash sample taken from a server.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:jarmhash` | `inet:tls:jarmhash` | The JARM hash computed from the server responses. |
| `:seen` | `ival` | The JARM sample was observed during the time interval. |
| `:server` | `inet:server` | The server that was sampled to compute the JARM hash. |

### `inet:tls:servercert`

An x509 certificate sent by a server for TLS.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:cert` | `crypto:x509:cert` | The x509 certificate sent by the server. |
| `:seen` | `ival` | The TLS server certificate was observed during the time interval. |
| `:server` | `inet:server` | The server associated with the x509 certificate. |

### `inet:tunnel`

A specific sequence of hosts forwarding connections such as a VPN or proxy.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:anon` | `bool` | Indicates that this tunnel provides anonymization. |
| `:egress` | `inet:server` | The server where client traffic leaves the tunnel. |
| `:ingress` | `inet:server` | The server where client traffic enters the tunnel. |
| `:operator` | `entity:actor` | The contact information for the tunnel operator. |
| `:seen` | `ival` | The tunnel was observed during the time interval. |
| `:type` | `inet:tunnel:type:taxonomy` | The type of tunnel such as vpn or proxy. |

### `inet:tunnel:type:taxonomy`

A hierarchical taxonomy of tunnel types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `inet:tunnel:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `inet:url`

A Universal Resource Locator (URL).

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `str` | The base scheme, user/pass, fqdn, port and path w/o parameters. |
| `:fqdn` | `inet:fqdn` | The fqdn used in the URL (e.g., http://www.woot.com/page.html). |
| `:ip` | `inet:ip` | The IP address used in the URL (e.g., http://1.2.3.4/page.html). |
| `:params` | `str` | The URL parameter string. |
| `:passwd` | `auth:passwd` | The optional password used to access the URL. |
| `:path` | `str` | The path in the URL w/o parameters. |
| `:port` | `inet:port` | The port of the URL. URLs prefixed with http will be set to port 80 and URLs prefixed with https will be set to port 443 unless otherwise specified. |
| `:proto` | `str:lower` | The protocol in the URL. |
| `:seen` | `ival` | The URL was observed during the time interval. |
| `:user` | `inet:user` | The optional username used to access the URL. |

### `inet:url:mirror`

A URL mirror site.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:at` | `inet:url` | The URL of the mirror. |
| `:of` | `inet:url` | The URL being mirrored. |
| `:seen` | `ival` | The URL mirror was observed during the time interval. |

### `inet:url:redir`

A URL that redirects to another URL, such as via a URL shortening service or an HTTP 302 response.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The URL redirection was observed during the time interval. |
| `:source` | `inet:url` | The original/source URL before redirect. |
| `:target` | `inet:url` | The redirected/destination URL. |

### `inet:urlfile`

A file hosted at a specific Universal Resource Locator (URL).

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that was hosted at the URL. |
| `:seen` | `ival` | The hosted file and URL was observed during the time interval. |
| `:url` | `inet:url` | The URL where the file was hosted. |

### `inet:user`

A username string.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The username was observed during the time interval. |

### `inet:whois:ipquery`

Query details used to retrieve an IP record.

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The FQDN of the host server when using the legacy WHOIS Protocol. |
| `:ip` | `inet:ip` | The IP address queried. |
| `:rec` | `inet:whois:iprecord` | The resulting record from the query. |
| `:success` | `bool` | Whether the host returned a valid response for the query. |
| `:time` | `time` | The time the request was made. |
| `:url` | `inet:url` | The query URL when using the HTTP RDAP Protocol. |

### `inet:whois:iprecord`

An IPv4/IPv6 block registration record.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:asn` | `inet:asn` | The associated Autonomous System Number (ASN). |
| `:contacts` | `array of entity:contact` | The whois registration contacts. |
| `:country` | `iso:3166:alpha2` | The ISO 3166 Alpha-2 country code. |
| `:created` | `time` | The "created" time from the record. |
| `:desc` | `text` | The description of the network from the whois record. |
| `:id` | `base:id` | The registry unique identifier (e.g. NET-74-0-0-0-1). |
| `:links` | `array of inet:url` | URLs provided with the record. |
| `:name` | `base:id` | The name ID assigned to the network by the registrant. |
| `:net` | `inet:net` | The IP address range assigned. |
| `:parentid` | `base:id` | The registry unique identifier of the parent whois record (e.g. NET-74-0-0-0-0). |
| `:seen` | `ival` | The registration record was observed during the time interval. |
| `:status` | `str:lower` | The state of the registered network. |
| `:text` | `text:lower` | The full text of the record. |
| `:type` | `str:lower` | The classification of the registered network (e.g. direct allocation). |
| `:updated` | `time` | The "last updated" time from the record. |

### `inet:whois:record`

An FQDN whois registration record.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:contacts` | `array of entity:contact` | The whois registration contacts. |
| `:created` | `time` | The "created" time from the whois record. |
| `:expires` | `time` | The "expires" time from the whois record. |
| `:fqdn` | `inet:fqdn` | The domain associated with the whois record. |
| `:nameservers` | `array of inet:fqdn` | The DNS nameserver FQDNs for the registered FQDN. |
| `:registrant` | `entity:name` | The registrant name from the whois record. |
| `:registrar` | `entity:name` | The registrar name from the whois record. |
| `:seen` | `ival` | The registration record was observed during the time interval. |
| `:text` | `text:lower` | The full text of the whois record. |
| `:updated` | `time` | The "last updated" time from the whois record. |

### `inet:wifi:ap`

An SSID/MAC address combination for a wireless access point.

| Interface |
|-----------|
| `geo:locatable` |
| `meta:havable` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:bssid` | `inet:mac` | The MAC address for the wireless access point. |
| `:channel` | `int` | The WIFI channel that the AP was last observed operating on. |
| `:encryption` | `base:name` | The type of encryption used by the WIFI AP such as "wpa2". |
| `:owner` | `entity:actor` | The current owner of the Wi-Fi access point. |
| `:owner:name` | `entity:name` | The name of the current owner of the Wi-Fi access point. |
| `:place` | `geo:place` | The place where the Wi-Fi access point was located. |
| `:place:address` | `geo:address` | The postal address where the Wi-Fi access point was located. |
| `:place:address:city` | `base:name` | The city where the Wi-Fi access point was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the Wi-Fi access point was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the Wi-Fi access point was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the Wi-Fi access point was located. |
| `:place:country` | `pol:country` | The country where the Wi-Fi access point was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the Wi-Fi access point was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the Wi-Fi access point was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the Wi-Fi access point was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the Wi-Fi access point was located. |
| `:place:loc` | `loc` | The geopolitical location where the Wi-Fi access point was located. |
| `:place:name` | `geo:name` | The name where the Wi-Fi access point was located. |
| `:seen` | `ival` | The Wi-Fi access point was observed during the time interval. |
| `:ssid` | `inet:wifi:ssid` | The SSID for the wireless access point. |

### `inet:wifi:ssid`

A Wi-Fi service set identifier (SSID) name.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The Wi-Fi SSID was observed during the time interval. |

### `iso:3166:alpha2`

An ISO 3166 Alpha-2 country code.

### `iso:3166:alpha3`

An ISO 3166 Alpha-3 country code.

### `iso:3166:numeric3`

An ISO 3166 Numeric-3 country code.

### `iso:oid`

An ISO Object Identifier string.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `str` | A description of the value or meaning of the OID. |
| `:identifier` | `str` | The string identifier for the deepest tree element. |

### `it:adid`

An advertising identification string.

| Interface |
|-----------|
| `entity:identifier` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The advertising ID was observed during the time interval. |

### `it:app:snort:match`

An instance of a snort rule hit.

| Interface |
|-----------|
| `meta:matchish` |

| Property | Type | Doc |
|----------|------|-----|
| `:dropped` | `bool` | Set to true if the network traffic was dropped due to the match. |
| `:matched` | `time` | The time that the rule was evaluated to generate the match. |
| `:rule` | `it:app:snort:rule` | The rule which matched the target node. |
| `:sensor` | `it:host` | The sensor host node that produced the match. |
| `:target` | `inet:flow` | The target node which matched the Snort rule. |
| `:version` | `it:version` | The most recent version of the rule evaluated as a match. |

### `it:app:snort:rule`

A snort rule.

| Interface |
|-----------|
| `doc:authorable` |
| `entity:creatable` |
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the snort rule was created. |
| `:creator` | `entity:actor` | The primary actor which created the snort rule. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the snort rule. |
| `:desc` | `text` | A description of the snort rule. |
| `:enabled` | `bool` | The enabled status of the snort rule. |
| `:engine` | `int` | The snort engine ID which can parse and evaluate the rule text. |
| `:id` | `base:id` | The snort rule ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the snort rule. |
| `:name` | `base:id` | The rule name. |
| `:seen` | `ival` | The snort rule was observed during the time interval. |
| `:supersedes` | `array of it:app:snort:rule` | An array of snort rule versions which are superseded by this snort rule. |
| `:text` | `text` | The text of the snort rule. |
| `:type` | `meta:rule:type:taxonomy` | The rule type. |
| `:updated` | `time` | The time that the snort rule was last updated. |
| `:url` | `inet:url` | The URL where the snort rule is available. |
| `:version` | `it:version` | The version of the snort rule. |

### `it:app:yara:match`

A YARA rule which can match files, processes, or network traffic.

| Interface |
|-----------|
| `meta:matchish` |

| Property | Type | Doc |
|----------|------|-----|
| `:matched` | `time` | The time that the rule was evaluated to generate the match. |
| `:rule` | `it:app:yara:rule` | The rule which matched the target node. |
| `:target` | `it:app:yara:target` | The target node which matched the YARA rule. |
| `:version` | `it:version` | The most recent version of the rule evaluated as a match. |

### `it:app:yara:rule`

A YARA rule unique identifier.

| Interface |
|-----------|
| `doc:authorable` |
| `entity:creatable` |
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the YARA rule was created. |
| `:creator` | `entity:actor` | The primary actor which created the YARA rule. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the YARA rule. |
| `:desc` | `text` | A description of the YARA rule. |
| `:enabled` | `bool` | The enabled status of the YARA rule. |
| `:id` | `base:id` | The YARA rule ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the YARA rule. |
| `:name` | `base:id` | The rule name. |
| `:seen` | `ival` | The YARA rule was observed during the time interval. |
| `:supersedes` | `array of it:app:yara:rule` | An array of YARA rule versions which are superseded by this YARA rule. |
| `:text` | `text` | The text of the YARA rule. |
| `:type` | `meta:rule:type:taxonomy` | The rule type. |
| `:updated` | `time` | The time that the YARA rule was last updated. |
| `:url` | `inet:url` | The URL where the YARA rule is available. |
| `:version` | `it:version` | The version of the YARA rule. |

### `it:av:scan:result`

The result of running an antivirus scanner.

| Property | Type | Doc |
|----------|------|-----|
| `:categories` | `array of base:name` | A list of categories for the result returned by the scanner. |
| `:multi:count` | `int` | The total number of scanners which were run by a multi-scanner. |
| `:multi:count:benign` | `int` | The number of scanners which returned a benign verdict. |
| `:multi:count:malicious` | `int` | The number of scanners which returned a malicious verdict. |
| `:multi:count:suspicious` | `int` | The number of scanners which returned a suspicious verdict. |
| `:multi:count:unknown` | `int` | The number of scanners which returned a unknown/unsupported verdict. |
| `:multi:scan` | `it:av:scan:result` | Set if this result was part of running multiple scanners. |
| `:scanner` | `it:software` | The scanner software used to produce the result. |
| `:scanner:name` | `it:softwarename` | The name of the scanner software. |
| `:signame` | `it:av:signame` | The name of the signature returned by the scanner. |
| `:target` | `file:bytes`, `inet:fqdn`, `inet:ip`, `inet:url`, `it:exec:proc`, `it:host` | The target of the scan. |
| `:time` | `time` | The time the scan was run. |
| `:verdict` | `it:av:verdict` | The scanner provided verdict for the scan. |

### `it:av:signame`

An antivirus signature name.

### `it:cmd`

A unique command-line string.

### `it:cmd:history`

A single command executed within a session.

| Property | Type | Doc |
|----------|------|-----|
| `:cmd` | `it:cmd` | The command that was executed. |
| `:index` | `int` | Used to order the commands when times are not available. |
| `:session` | `it:cmd:session` | The session that contains this history entry. |
| `:time` | `time` | The time that the command was executed. |

### `it:cmd:session`

A command line session with multiple commands run over time.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account`, `it:host:account` | The account which executed the commands in the session. |
| `:file` | `file:bytes` | The file containing the command history such as a .bash_history file. |
| `:host` | `it:host` | The host where the command line session was executed. |
| `:period` | `ival` | The period over which the command line session was running. |
| `:proc` | `it:exec:proc` | The process which was interpreting this command line session. |

### `it:dev:function`

A function defined by code.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the function. |
| `:id` | `base:id` | An identifier for the function. |
| `:impcalls` | `array of str:lower` | Calls to imported library functions within the scope of the function. |
| `:name` | `it:dev:str` | The name of the function. |
| `:strings` | `array of it:dev:str` | An array of strings referenced within the function. |

### `it:dev:function:sample`

An instance of a function in an executable.

| Interface |
|-----------|
| `file:mime:meta` |

| Property | Type | Doc |
|----------|------|-----|
| `:calls` | `array of it:dev:function:sample` | Other function calls within the scope of the function. |
| `:complexity` | `meta:score` | The complexity of the function. |
| `:file` | `file:bytes` | The file which contains the function. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the function within the file. |
| `:file:size` | `int` | The size of the function within the file. |
| `:function` | `it:dev:function` | The function contained within the file. |
| `:va` | `int` | The virtual address of the first codeblock of the function. |

### `it:dev:int`

A developer selected integer constant.

### `it:dev:repo`

A version control system instance.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:desc` | `text` | A free-form description of the repository. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:name` | `str:lower` | The name of the repository. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:submodules` | `array of it:dev:repo:commit` | An array of other repos that this repo has as submodules, pinned at specific commits. |
| `:type` | `it:dev:repo:type:taxonomy` | The type of the version control system used. |
| `:url` | `inet:url` | The URL where the repository is hosted. |

### `it:dev:repo:branch`

A branch in a version control system instance.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:merged` | `time` | The time this branch was merged back into its parent. |
| `:name` | `str` | The name of the branch. |
| `:parent` | `it:dev:repo:branch` | The branch this branch was branched from. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:start` | `it:dev:repo:commit` | The commit in the parent branch this branch was created at. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:url` | `inet:url` | The URL where the branch is hosted. |

### `it:dev:repo:commit`

A commit to a repository.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:branch` | `it:dev:repo:branch` | The name of the branch the commit was made to. |
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:id` | `base:id` | The version control system specific commit identifier. |
| `:mesg` | `text` | The commit message describing the changes in the commit. |
| `:parents` | `array of it:dev:repo:commit` | The commit or commits this commit is immediately based on. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:repo` | `it:dev:repo` | The repository the commit lives in. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:url` | `inet:url` | The URL where the commit is hosted. |

### `it:dev:repo:diff`

A diff of a file being applied in a single commit.

| Property | Type | Doc |
|----------|------|-----|
| `:commit` | `it:dev:repo:commit` | The commit that produced this diff. |
| `:file` | `file:bytes` | The file after the commit has been applied. |
| `:path` | `file:path` | The path to the file in the repo that the diff is being applied to. |
| `:url` | `inet:url` | The URL where the diff is hosted. |

### `it:dev:repo:diff:comment`

A comment on a diff in a repository.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:diff` | `it:dev:repo:diff` | The diff the comment is being added to. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:line` | `int` | The line in the file that is being commented on. |
| `:offset` | `int` | The offset in the line in the file that is being commented on. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:replyto` | `it:dev:repo:diff:comment` | The comment that this comment is replying to. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:text` | `text` | The body of the comment. |
| `:updated` | `time` | The time the comment was updated. |
| `:url` | `inet:url` | The URL where the comment is hosted. |

### `it:dev:repo:entry`

A file included in a repository.

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file which the repository contains. |
| `:path` | `file:path` | The path to the file in the repository. |
| `:repo` | `it:dev:repo` | The repository which contains the file. |

### `it:dev:repo:issue`

An issue raised in a repository.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:desc` | `text` | The text describing the issue. |
| `:id` | `base:id` | The ID of the issue in the repository system. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:repo` | `it:dev:repo` | The repo where the issue was logged. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:title` | `str:lower` | The title of the issue. |
| `:updated` | `time` | The time the issue was updated. |
| `:url` | `inet:url` | The URL where the issue is hosted. |

### `it:dev:repo:issue:comment`

A comment on an issue in a repository.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:issue` | `it:dev:repo:issue` | The issue thread that the comment was made in. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:replyto` | `it:dev:repo:issue:comment` | The comment that this comment is replying to. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:text` | `text` | The body of the comment. |
| `:updated` | `time` | The time the comment was updated. |
| `:url` | `inet:url` | The URL where the comment is hosted. |

### `it:dev:repo:issue:label`

A label applied to a repository issue.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:issue` | `it:dev:repo:issue` | The issue the label was applied to. |
| `:label` | `it:dev:repo:label` | The label that was applied to the issue. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:url` | `inet:url` | The primary URL associated with the object. |

### `it:dev:repo:label`

A developer selected label.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | The description of the label. |
| `:id` | `base:id` | The ID of the label. |
| `:title` | `str:lower` | The human friendly name of the label. |

### `it:dev:repo:remote`

A remote repo that is tracked for changes/branches/etc.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The name the repo is using for the remote repo. |
| `:remote` | `it:dev:repo` | The instance of the remote repo. |
| `:repo` | `it:dev:repo` | The repo that is tracking the remote repo. |
| `:url` | `inet:url` | The URL the repo is using to access the remote repo. |

### `it:dev:repo:type:taxonomy`

A hierarchical taxonomy of repository types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `it:dev:repo:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `it:dev:str`

A developer selected string.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:norm` | `str:lower` | Lower case normalized version of the it:dev:str. |
| `:seen` | `ival` | The string was observed during the time interval. |

### `it:dns:resolver`

A server configured to resolve DNS requests.

| Interface |
|-----------|
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:proto` | `str:lower` | The network protocol of the server. |
| `:seen` | `ival` | The network server was observed during the time interval. |

### `it:exec:bind`

An instance of a host binding a listening port.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this bind event. |
| `:exe` | `file:bytes` | The specific file containing code that bound the listening port. |
| `:host` | `it:host` | The host running the process that bound the listening port. |
| `:proc` | `it:exec:proc` | The main process executing code that bound the listening port. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server when binding the port. |
| `:thread` | `it:exec:thread` | The thread which caused the bind event. |
| `:time` | `time` | The time the port was bound. |

### `it:exec:fetch`

An instance of a host requesting a URL using any protocol scheme.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this fetch event. |
| `:browser` | `it:software` | The software version of the browser. |
| `:client` | `inet:client` | The address of the client during the URL retrieval. |
| `:exe` | `file:bytes` | The specific file containing code that requested the URL. |
| `:host` | `it:host` | The host running the process that requested the URL. |
| `:http:request` | `inet:http:request` | The HTTP request made to retrieve the initial URL contents. |
| `:page:html` | `file:bytes` | The rendered DOM saved as an HTML file. |
| `:page:image` | `file:bytes` | The rendered DOM saved as an image. |
| `:page:pdf` | `file:bytes` | The rendered DOM saved as a PDF file. |
| `:proc` | `it:exec:proc` | The main process executing code that requested the URL. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the fetch event. |
| `:time` | `time` | The time the URL was requested. |
| `:url` | `inet:url` | The URL that was requested. |

### `it:exec:file:add`

An instance of a host adding a file to a filesystem.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this file add event. |
| `:exe` | `file:bytes` | The specific file containing code that created the new file. |
| `:file` | `file:bytes` | The file that was created. |
| `:host` | `it:host` | The host running the process that created the new file. |
| `:path` | `file:path` | The path where the file was created. |
| `:proc` | `it:exec:proc` | The main process executing code that created the new file. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the file add event. |
| `:time` | `time` | The time the file was created. |

### `it:exec:file:del`

An instance of a host deleting a file from a filesystem.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this file delete event. |
| `:exe` | `file:bytes` | The specific file containing code that deleted the file. |
| `:file` | `file:bytes` | The file that was deleted. |
| `:host` | `it:host` | The host running the process that deleted the file. |
| `:path` | `file:path` | The path where the file was deleted. |
| `:proc` | `it:exec:proc` | The main process executing code that deleted the file. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the file delete event. |
| `:time` | `time` | The time the file was deleted. |

### `it:exec:file:read`

An instance of a host reading a file from a filesystem.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this file read event. |
| `:exe` | `file:bytes` | The specific file containing code that read the file. |
| `:file` | `file:bytes` | The file that was read. |
| `:host` | `it:host` | The host running the process that read the file. |
| `:path` | `file:path` | The path where the file was read. |
| `:proc` | `it:exec:proc` | The main process executing code that read the file. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the file read event. |
| `:time` | `time` | The time the file was read. |

### `it:exec:file:write`

An instance of a host writing a file to a filesystem.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this file write event. |
| `:exe` | `file:bytes` | The specific file containing code that wrote to the file. |
| `:file` | `file:bytes` | The file that was modified. |
| `:host` | `it:host` | The host running the process that wrote to the file. |
| `:path` | `file:path` | The path where the file was written to/modified. |
| `:proc` | `it:exec:proc` | The main process executing code that wrote to / modified the existing file. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the file write event. |
| `:time` | `time` | The time the file was written to/modified. |

### `it:exec:lib:load`

A library load event in a process.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this library load event. |
| `:exe` | `file:bytes` | The executable file which caused the library load event. |
| `:file` | `file:bytes` | The library file that was loaded. |
| `:host` | `it:host` | The host on which the library load event occurred. |
| `:loaded` | `time` | The time the library was loaded. |
| `:path` | `file:path` | The path that the library was loaded from. |
| `:proc` | `it:exec:proc` | The process where the library was loaded. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the library load event. |
| `:time` | `time` | The time that the library load event occurred. |
| `:unloaded` | `time` | The time the library was unloaded. |
| `:va` | `int` | The base memory address where the library was loaded in the process. |

### `it:exec:mmap:add`

A memory mapped segment located in a process.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this memory map event. |
| `:created` | `time` | The time the memory map was created. |
| `:deleted` | `time` | The time the memory map was deleted. |
| `:exe` | `file:bytes` | The executable file which caused the memory map event. |
| `:hash:sha256` | `crypto:hash:sha256` | A SHA256 hash of the memory map. |
| `:host` | `it:host` | The host on which the memory map event occurred. |
| `:path` | `file:path` | The file path if the memory is a mapped view of a file. |
| `:perms:execute` | `bool` | True if the memory is mapped with execute permissions. |
| `:perms:read` | `bool` | True if the memory is mapped with read permissions. |
| `:perms:write` | `bool` | True if the memory is mapped with write permissions. |
| `:proc` | `it:exec:proc` | The process where the memory was mapped. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:size` | `int` | The size of the memory map in bytes. |
| `:thread` | `it:exec:thread` | The thread which caused the memory map event. |
| `:time` | `time` | The time that the memory map event occurred. |
| `:va` | `int` | The base memory address where the map was created in the process. |

### `it:exec:mutex:add`

An event where a process created a mutex.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this mutex creation event. |
| `:exe` | `file:bytes` | The specific file containing code that created the mutex. |
| `:host` | `it:host` | The host running the process that created the mutex. |
| `:name` | `it:dev:str` | The mutex string. |
| `:proc` | `it:exec:proc` | The process that created the mutex. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the mutex creation event. |
| `:time` | `time` | The time the mutex was created. |

### `it:exec:pipe:add`

A named pipe created by a process at runtime.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this pipe creation event. |
| `:exe` | `file:bytes` | The specific file containing code that created the named pipe. |
| `:host` | `it:host` | The host running the process that created the named pipe. |
| `:name` | `it:dev:str` | The named pipe string. |
| `:proc` | `it:exec:proc` | The main process executing code that created the named pipe. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the pipe creation event. |
| `:time` | `time` | The time the named pipe was created. |

### `it:exec:proc`

A process executing on a host.

| Interface |
|-----------|
| `base:activity` |
| `it:host:activity` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `it:host:account` | The account of the process owner. |
| `:activity` | `meta:activity` | A parent activity which includes this process. |
| `:cmd` | `it:cmd` | The command string used to launch the process. |
| `:cmd:history` | `it:cmd:history` | The command history entry which caused this process to be run. |
| `:exe` | `file:bytes` | The main executable file for the process. |
| `:exitcode` | `int` | The exit code for the process. |
| `:host` | `it:host` | The host that executed the process. |
| `:name` | `str` | The display name specified by the process. |
| `:path` | `file:path` | The path to the executable of the process. |
| `:period` | `ival` | The period over which the process occurred. |
| `:pid` | `int` | The process ID. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |

### `it:exec:proc:create`

A process creation event.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this process creation event. |
| `:exe` | `file:bytes` | The executable file which caused the process creation event. |
| `:host` | `it:host` | The host on which the process creation event occurred. |
| `:proc` | `it:exec:proc` | The process which caused the process creation event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:target` | `it:exec:proc` | The process which was created. |
| `:thread` | `it:exec:thread` | The thread which caused the process creation event. |
| `:time` | `time` | The time that the process creation event occurred. |

### `it:exec:proc:signal`

An event where a process was sent a POSIX signal.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this process signal event. |
| `:exe` | `file:bytes` | The executable file which caused the process signal event. |
| `:host` | `it:host` | The host on which the process signal event occurred. |
| `:proc` | `it:exec:proc` | The process which caused the process signal event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:signal` | `int` | The POSIX signal which was sent to the target process. |
| `:target` | `it:exec:proc` | The process which was sent the signal. |
| `:thread` | `it:exec:thread` | The thread which caused the process signal event. |
| `:time` | `time` | The time that the process signal event occurred. |

### `it:exec:proc:terminate`

A process termination event.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this process termination event. |
| `:exe` | `file:bytes` | The executable file which caused the process termination event. |
| `:host` | `it:host` | The host on which the process termination event occurred. |
| `:proc` | `it:exec:proc` | The process which caused the process termination event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:target` | `it:exec:proc` | The process which was terminated. |
| `:thread` | `it:exec:thread` | The thread which caused the process termination event. |
| `:time` | `time` | The time that the process termination event occurred. |

### `it:exec:query`

An instance of an executed query.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account`, `it:host:account`, `syn:user` | The account which executed the query. |
| `:activity` | `meta:activity` | A parent activity which includes this query event. |
| `:api:url` | `inet:url` | The URL of the API endpoint the query was sent to. |
| `:exe` | `file:bytes` | The executable file which caused the query event. |
| `:host` | `it:host` | The host on which the query event occurred. |
| `:language` | `base:name` | The name of the language that the query is expressed in. |
| `:offset` | `int` | The offset of the last record consumed from the query. |
| `:opts` | `data` | An opaque JSON object containing query parameters and options. |
| `:platform` | `inet:service:platform` | The service platform which was queried. |
| `:proc` | `it:exec:proc` | The process which caused the query event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:text` | `it:query` | The query string that was executed. |
| `:thread` | `it:exec:thread` | The thread which caused the query event. |
| `:time` | `time` | The time that the query event occurred. |

### `it:exec:screenshot`

A screenshot of a host.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this screenshot event. |
| `:desc` | `text` | A brief description of the screenshot. |
| `:exe` | `file:bytes` | The executable file which caused the screenshot event. |
| `:host` | `it:host` | The host on which the screenshot event occurred. |
| `:image` | `file:bytes` | The image file. |
| `:proc` | `it:exec:proc` | The process which caused the screenshot event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the screenshot event. |
| `:time` | `time` | The time that the screenshot event occurred. |

### `it:exec:thread`

A thread executing in a process.

| Interface |
|-----------|
| `base:activity` |
| `it:host:activity` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this thread. |
| `:exe` | `file:bytes` | The executable file which caused the thread. |
| `:exitcode` | `int` | The exit code or return value for the thread. |
| `:host` | `it:host` | The host on which the thread occurred. |
| `:period` | `ival` | The period over which the thread occurred. |
| `:proc` | `it:exec:proc` | The process which contains the thread. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |

### `it:exec:thread:create`

A thread creation event.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this thread creation event. |
| `:exe` | `file:bytes` | The executable file which caused the thread creation event. |
| `:host` | `it:host` | The host on which the thread creation event occurred. |
| `:proc` | `it:exec:proc` | The process which caused the thread creation event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:target` | `it:exec:thread` | The thread which was created. |
| `:thread` | `it:exec:thread` | The thread which caused the thread creation event. |
| `:time` | `time` | The time that the thread creation event occurred. |

### `it:exec:thread:terminate`

A thread termination event.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this thread termination event. |
| `:exe` | `file:bytes` | The executable file which caused the thread termination event. |
| `:host` | `it:host` | The host on which the thread termination event occurred. |
| `:proc` | `it:exec:proc` | The process which caused the thread termination event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:target` | `it:exec:thread` | The thread which was terminated. |
| `:thread` | `it:exec:thread` | The thread which caused the thread termination event. |
| `:time` | `time` | The time that the thread termination event occurred. |

### `it:exec:windows:registry:del`

An instance of a host deleting a registry key.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this registry delete event. |
| `:entry` | `it:os:windows:registry:entry` | The registry entry that was deleted. |
| `:exe` | `file:bytes` | The specific file containing code that deleted data from the registry. |
| `:host` | `it:host` | The host running the process that deleted data from the registry. |
| `:proc` | `it:exec:proc` | The main process executing code that deleted data from the registry. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the registry delete event. |
| `:time` | `time` | The time the data from the registry was deleted. |

### `it:exec:windows:registry:get`

An instance of a host getting a registry key.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this registry get event. |
| `:entry` | `it:os:windows:registry:entry` | The registry key or value that was read. |
| `:exe` | `file:bytes` | The specific file containing code that read the registry. |
| `:host` | `it:host` | The host running the process that read the registry. |
| `:proc` | `it:exec:proc` | The main process executing code that read the registry. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the registry get event. |
| `:time` | `time` | The time the registry was read. |

### `it:exec:windows:registry:set`

An instance of a host creating or setting a registry key.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this registry set event. |
| `:entry` | `it:os:windows:registry:entry` | The registry key or value that was written to. |
| `:exe` | `file:bytes` | The specific file containing code that wrote to the registry. |
| `:host` | `it:host` | The host running the process that wrote to the registry. |
| `:proc` | `it:exec:proc` | The main process executing code that wrote to the registry. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the registry set event. |
| `:time` | `time` | The time the registry was written to. |

### `it:hardware`

A specification for a piece of IT hardware.

| Interface |
|-----------|
| `meta:observable` |
| `meta:usable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:cpe` | `it:sec:cpe` | The NIST CPE 2.3 string specifying this hardware. |
| `:desc` | `text` | A brief description of the hardware. |
| `:manufacturer` | `entity:actor` | The organization that manufactures this hardware. |
| `:manufacturer:name` | `entity:name` | The name of the organization that manufactures this hardware. |
| `:model` | `biz:model` | The model name or number for this hardware specification. |
| `:name` | `base:name` | The name of this hardware specification. |
| `:parts` | `array of it:hardware` | An array of it:hardware parts included in this hardware specification. |
| `:released` | `time` | The initial release date for this hardware. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:type` | `it:hardware:type:taxonomy` | The type of hardware. |
| `:version` | `it:version` | Version string associated with this hardware specification. |

### `it:hardware:type:taxonomy`

A hierarchical taxonomy of IT hardware types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `it:hardware:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `it:host`

A GUID that represents a host or system.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `geo:locatable` |
| `inet:service:base` |
| `inet:service:object` |
| `meta:havable` |
| `meta:observable` |
| `phys:object` |
| `phys:tangible` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the host was created. |
| `:creator` | `entity:actor` | The primary actor which created the host. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the host. |
| `:desc` | `str` | A free-form description of the host. |
| `:hardware` | `it:hardware` | The hardware specification for this host. |
| `:id` | `str` | An external identifier for the host. |
| `:image` | `it:software:image` | The container image or OS image running on the host. |
| `:ip` | `inet:ip` | The last known IP address for the host. |
| `:keyboard:language` | `lang:language` | The primary keyboard input language configured on the host. |
| `:keyboard:layout` | `base:name` | The primary keyboard layout configured on the host. |
| `:model` | `biz:model` | The model number or name of the host. |
| `:name` | `it:hostname` | The name of the host or system. |
| `:operator` | `entity:contact` | The operator of the host. |
| `:org` | `ou:org` | The org that operates the given host. |
| `:os` | `it:software` | The operating system of the host. |
| `:os:name` | `it:softwarename` | A software product name for the host operating system. Used for entity resolution. |
| `:owner` | `entity:actor` | The current owner of the host. |
| `:owner:name` | `entity:name` | The name of the current owner of the host. |
| `:period` | `ival` | The period when the host existed. |
| `:phys:height` | `geo:dist` | The physical height of the host. |
| `:phys:length` | `geo:dist` | The physical length of the host. |
| `:phys:mass` | `mass` | The physical mass of the host. |
| `:phys:volume` | `geo:dist` | The physical volume of the host. |
| `:phys:width` | `geo:dist` | The physical width of the host. |
| `:place` | `geo:place` | The place where the host was located. |
| `:place:address` | `geo:address` | The postal address where the host was located. |
| `:place:address:city` | `base:name` | The city where the host was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the host was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the host was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the host was located. |
| `:place:country` | `pol:country` | The country where the host was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the host was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the host was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the host was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the host was located. |
| `:place:loc` | `loc` | The geopolitical location where the host was located. |
| `:place:name` | `geo:name` | The name where the host was located. |
| `:platform` | `inet:service:platform` | The platform which defines the host. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the host. |
| `:seen` | `ival` | The host was observed during the time interval. |
| `:serial` | `base:id` | The serial number of the host. |
| `:status` | `inet:service:object:status` | The status of the host. |
| `:url` | `inet:url` | The primary URL associated with the host. |

### `it:host:account`

A local account on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:contact` | Additional contact information associated with this account. |
| `:groups` | `array of it:host:group` | Groups that the account is a member of. |
| `:host` | `it:host` | The host where the account is registered. |
| `:period` | `ival` | The period where the account existed. |
| `:posix:gecos` | `int` | The GECOS field for the POSIX account. |
| `:posix:gid` | `int` | The primary group ID of the account. |
| `:posix:home` | `file:path` | The path to the POSIX account's home directory. |
| `:posix:shell` | `file:path` | The path to the POSIX account's default shell. |
| `:posix:uid` | `int` | The user ID of the account. |
| `:service:account` | `inet:service:account` | The optional service account which the local account maps to. |
| `:user` | `inet:user` | The username associated with the account. |
| `:windows:sid` | `it:os:windows:sid` | The Microsoft Windows Security Identifier of the account. |

### `it:host:component`

Hardware components which are part of a host.

| Property | Type | Doc |
|----------|------|-----|
| `:hardware` | `it:hardware` | The hardware specification of this component. |
| `:host` | `it:host` | The it:host which has this component installed. |
| `:serial` | `base:id` | The serial number of this component. |

### `it:host:group`

A local group on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A brief description of the group. |
| `:groups` | `array of it:host:group` | Groups that are a member of this group. |
| `:host` | `it:host` | The host where the group was created. |
| `:name` | `base:name` | The name of the group. |
| `:posix:gid` | `int` | The primary group ID of the account. |
| `:service:role` | `inet:service:role` | The optional service role which the local group maps to. |
| `:windows:sid` | `it:os:windows:sid` | The Microsoft Windows Security Identifier of the group. |

### `it:host:hosted:url`

A URL hosted on or served by a specific host.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:host` | `it:host` | Host serving a url. |
| `:seen` | `ival` | The host at this URL was observed during the time interval. |
| `:url` | `inet:url` | URL available on the host. |

### `it:host:installed`

Software installed on a specific host.

| Property | Type | Doc |
|----------|------|-----|
| `:host` | `it:host` | The host which the software was installed on. |
| `:period` | `ival` | The period when the software was installed on the host. |
| `:software` | `it:software` | The software installed on the host. |

### `it:host:login`

A host specific login session.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:request` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `it:host:account` | The account that logged in. |
| `:activity` | `meta:activity` | A parent activity which includes this login. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the login. |
| `:client:host` | `it:host` | The client host which initiated the login. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the login. |
| `:creds` | `array of auth:credential` | The credentials that were used to login. |
| `:flow` | `inet:flow` | The network flow which contained the login. |
| `:period` | `ival` | The period when the login session was active. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the login. |
| `:server:host` | `it:host` | The server host which received the login. |
| `:server:proc` | `it:exec:proc` | The server process which received the login. |
| `:success` | `bool` | Set to false to indicate an unsuccessful logon attempt. |
| `:time` | `time` | The time that the login occurred. |

### `it:host:tenancy`

A time window where a host was a tenant run by another host.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:lessor` | `it:host` | The host which provides runtime resources to the tenant host. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:tenant` | `it:host` | The host which is run within the resources provided by the lessor. |
| `:url` | `inet:url` | The primary URL associated with the object. |

### `it:hostname`

The name of a host or system.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The hostname was observed during the time interval. |

### `it:log:event`

A GUID representing an individual log event.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this log event. |
| `:data` | `data` | A raw JSON record of the log event. |
| `:exe` | `file:bytes` | The executable file which caused the log event. |
| `:host` | `it:host` | The host on which the log event occurred. |
| `:id` | `str` | An external id that uniquely identifies this log entry. |
| `:mesg` | `str` | The log message text. |
| `:proc` | `it:exec:proc` | The process which caused the log event. |
| `:product` | `it:software` | The software which produced the log entry. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:service:account` | `inet:service:account` | The service account which generated the log event. |
| `:service:platform` | `inet:service:platform` | The service platform which generated the log event. |
| `:severity` | `it:log:severity` | A log level integer that increases with severity. |
| `:thread` | `it:exec:thread` | The thread which caused the log event. |
| `:time` | `time` | The time that the log event occurred. |
| `:type` | `it:log:event:type:taxonomy` | The type of log event. |

### `it:log:event:type:taxonomy`

A hierarchical taxonomy of log event types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `it:log:event:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `it:mitre:attack:campaign:id`

A MITRE ATT&CK Campaign ID.

### `it:mitre:attack:group:id`

A MITRE ATT&CK Group ID.

| Interface |
|-----------|
| `entity:identifier` |

### `it:mitre:attack:mitigation:id`

A MITRE ATT&CK Mitigation ID.

### `it:mitre:attack:software:id`

A MITRE ATT&CK Software ID.

### `it:mitre:attack:tactic:id`

A MITRE ATT&CK Tactic ID.

### `it:mitre:attack:technique:id`

A MITRE ATT&CK Technique ID.

### `it:network`

A GUID that represents a logical network.

| Interface |
|-----------|
| `meta:havable` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A brief description of the network. |
| `:dns:resolvers` | `array of it:dns:resolver` | An array of DNS servers configured to resolve requests for hosts on the network. |
| `:name` | `base:name` | The name of the network. |
| `:net` | `inet:net` | The optional contiguous IP address range of this network. |
| `:owner` | `entity:actor` | The current owner of the item. |
| `:owner:name` | `entity:name` | The name of the current owner of the item. |
| `:period` | `ival` | The period when the network existed. |
| `:type` | `it:network:type:taxonomy` | The type of network. |

### `it:network:type:taxonomy`

A hierarchical taxonomy of network types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `it:network:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `it:os:android:ibroadcast`

The given software broadcasts the given Android intent.

| Property | Type | Doc |
|----------|------|-----|
| `:app` | `it:software` | The app software which broadcasts the android intent. |
| `:intent` | `it:os:android:intent` | The android intent which is broadcast by the app. |

### `it:os:android:ilisten`

The given software listens for an android intent.

| Property | Type | Doc |
|----------|------|-----|
| `:app` | `it:software` | The app software which listens for the android intent. |
| `:intent` | `it:os:android:intent` | The android intent which is listened for by the app. |

### `it:os:android:intent`

An android intent string.

### `it:os:android:perm`

An android permission string.

### `it:os:android:reqperm`

The given software requests the android permission.

| Property | Type | Doc |
|----------|------|-----|
| `:app` | `it:software` | The android app which requests the permission. |
| `:perm` | `it:os:android:perm` | The android permission requested by the app. |

### `it:os:windows:registry:entry`

A Windows registry key, name, and value.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:key` | `it:os:windows:registry:key` | The Windows registry key. |
| `:name` | `it:dev:str` | The name of the registry value within the key. |
| `:seen` | `ival` | The registry entry was observed during the time interval. |
| `:value` | `file:bytes`, `it:dev:int`, `it:dev:str` | The value assigned to the name within the key. |

### `it:os:windows:registry:key`

A Windows registry key.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:parent` | `it:os:windows:registry:key` | The parent key. |
| `:seen` | `ival` | The registry key was observed during the time interval. |

### `it:os:windows:service`

A Microsoft Windows service configuration on a host.

| Interface |
|-----------|
| `base:activity` |
| `it:host:activity` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this activity. |
| `:description` | `text` | The description of the service from the Description registry key. |
| `:displayname` | `base:name` | The friendly name of the service from the DisplayName registry key. |
| `:errorcontrol` | `int` | The service error handling behavior from the ErrorControl registry key. |
| `:exe` | `file:bytes` | The executable file which caused the activity. |
| `:host` | `it:host` | The host that the service was configured on. |
| `:imagepath` | `file:path` | The path to the service binary from the ImagePath registry key. |
| `:name` | `base:name` | The name of the service from the registry key within Services. |
| `:period` | `ival` | The period over which the activity occurred. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:start` | `int` | The start configuration of the service from the Start registry key. |
| `:type` | `int` | The type of service from the Type registry key. |

### `it:os:windows:service:add`

An event where a Microsoft Windows service configuration was added to a host.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:exe` | `file:bytes` | The executable file which caused the activity. |
| `:host` | `it:host` | The host on which the activity occurred. |
| `:proc` | `it:exec:proc` | The process which caused the event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:target` | `it:os:windows:service` | The service which was added. |
| `:thread` | `it:exec:thread` | The thread which caused the event. |
| `:time` | `time` | The time that the event occurred. |

### `it:os:windows:service:del`

An event where a Microsoft Windows service configuration was removed from a host.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:exe` | `file:bytes` | The executable file which caused the activity. |
| `:host` | `it:host` | The host on which the activity occurred. |
| `:proc` | `it:exec:proc` | The process which caused the event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:target` | `it:os:windows:service` | The service which was removed. |
| `:thread` | `it:exec:thread` | The thread which caused the event. |
| `:time` | `time` | The time that the event occurred. |

### `it:query`

A unique query string.

### `it:sec:c2:config`

An extracted C2 config from an executable.

| Property | Type | Doc |
|----------|------|-----|
| `:campaigncode` | `it:dev:str` | The operator selected string used to identify the campaign or group of targets. |
| `:connect:delay` | `duration` | The time delay from first execution to connecting to the C2 server. |
| `:connect:interval` | `duration` | The configured duration to sleep between connections to the C2 server. |
| `:crypto:key` | `crypto:key` | Static key material used to encrypt C2 communications. |
| `:decoys` | `array of inet:url` | An array of URLs used as decoy connections to obfuscate the C2 servers. |
| `:dns:resolvers` | `array of inet:server` | An array of inet:servers to use when resolving DNS names. |
| `:family` | `it:softwarename` | The name of the software family which uses the config. |
| `:file` | `file:bytes` | The file that the C2 config was extracted from. |
| `:http:headers` | `array of inet:http:header` | An array of HTTP headers that the sample should transmit to the C2 server. |
| `:listens` | `array of inet:url` | An array of listen URLs that the software should bind. |
| `:mutex` | `it:dev:str` | The mutex that the software uses to prevent multiple-installations. |
| `:proxies` | `array of inet:url` | An array of proxy URLs used to communicate with the C2 server. |
| `:raw` | `data` | A JSON blob containing the raw config extracted from the binary. |
| `:servers` | `array of inet:url` | An array of connection URLs built from host/port/passwd combinations. |

### `it:sec:cpe`

A NIST CPE 2.3 Formatted String.

| Property | Type | Doc |
|----------|------|-----|
| `:edition` | `str:lower` | The "edition" field from the CPE 2.3 string. |
| `:language` | `str:lower` | The "language" field from the CPE 2.3 string. |
| `:other` | `str:lower` | The "other" field from the CPE 2.3 string. |
| `:part` | `str:lower` | The "part" field from the CPE 2.3 string. |
| `:product` | `str:lower` | The "product" field from the CPE 2.3 string. |
| `:sw_edition` | `str:lower` | The "sw_edition" field from the CPE 2.3 string. |
| `:target_hw` | `str:lower` | The "target_hw" field from the CPE 2.3 string. |
| `:target_sw` | `str:lower` | The "target_sw" field from the CPE 2.3 string. |
| `:update` | `str:lower` | The "update" field from the CPE 2.3 string. |
| `:v2_2` | `it:sec:cpe:v2_2` | The CPE 2.2 string which is equivalent to the primary property. |
| `:vendor` | `entity:name` | The "vendor" field from the CPE 2.3 string. |
| `:version` | `str:lower` | The "version" field from the CPE 2.3 string. |

### `it:sec:cve`

A vulnerability as designated by a Common Vulnerabilities and Exposures (CVE) number.

### `it:sec:cwe`

NIST NVD Common Weaknesses Enumeration Specification.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | The CWE description field. |
| `:name` | `str` | The CWE description field. |
| `:parents` | `array of it:sec:cwe` | An array of ChildOf CWE Relationships. |
| `:url` | `inet:url` | A URL linking this CWE to a full description. |

### `it:sec:metrics`

A node used to track metrics of an organization's infosec program.

| Property | Type | Doc |
|----------|------|-----|
| `:alerts:count` | `int` | The total number of alerts generated within the time period. |
| `:alerts:falsepos` | `int` | The number of alerts generated within the time period that were determined to be false positives. |
| `:alerts:meantime:triage` | `duration` | The mean time to triage alerts generated within the time period. |
| `:assets:hosts` | `int` | The total number of hosts within scope for the information security program. |
| `:assets:users` | `int` | The total number of users within scope for the information security program. |
| `:assets:vulns:count` | `int` | The number of asset vulnerabilities being tracked at the end of the time period. |
| `:assets:vulns:discovered` | `int` | The number of asset vulnerabilities discovered during the time period. |
| `:assets:vulns:meantime:mitigate` | `duration` | The mean time to mitigate for vulnerable assets mitigated during the time period. |
| `:assets:vulns:mitigated` | `int` | The number of asset vulnerabilities mitigated during the time period. |
| `:assets:vulns:preexisting` | `int` | The number of asset vulnerabilities being tracked at the beginning of the time period. |
| `:org` | `ou:org` | The organization whose security program is being measured. |
| `:org:fqdn` | `inet:fqdn` | The organization FQDN. Used for entity resolution. |
| `:org:name` | `entity:name` | The organization name. Used for entity resolution. |
| `:period` | `ival` | The time period used to compute the metrics. |

### `it:sec:stix:bundle`

A STIX bundle.

| Property | Type | Doc |
|----------|------|-----|
| `:id` | `base:id` | The id field from the STIX bundle. |

### `it:sec:stix:indicator`

A STIX indicator pattern.

| Property | Type | Doc |
|----------|------|-----|
| `:confidence` | `int` | The confidence field from the STIX indicator. |
| `:created` | `time` | The time that the indicator pattern was first created. |
| `:desc` | `str` | The description field from the STIX indicator. |
| `:id` | `base:id` | The STIX id field from the indicator pattern. |
| `:labels` | `array of str` | The label strings embedded in the STIX indicator pattern. |
| `:name` | `str` | The name of the STIX indicator pattern. |
| `:pattern` | `str` | The STIX indicator pattern text. |
| `:pattern_type` | `it:av:pattern:type` | The STIX indicator pattern type. |
| `:revoked` | `bool` | The revoked field from the STIX indicator. |
| `:updated` | `time` | The time that the indicator pattern was last modified. |
| `:valid_from` | `time` | The valid_from field from the STIX indicator. |
| `:valid_until` | `time` | The valid_until field from the STIX indicator. |

### `it:sec:vuln:scan`

An instance of running a vulnerability scan.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | Description of the scan and scope. |
| `:ext:url` | `inet:url` | An external URL which documents the scan. |
| `:id` | `str` | An externally generated ID for the scan. |
| `:operator` | `entity:contact` | Contact information for the scan operator. |
| `:software` | `it:software` | The scanning software used. |
| `:software:name` | `it:softwarename` | The name of the scanner software. |
| `:time` | `time` | The time that the scan was started. |

### `it:sec:vuln:scan:result`

A vulnerability scan result for an asset.

| Property | Type | Doc |
|----------|------|-----|
| `:asset` | `risk:exploitable` | The node which is vulnerable. |
| `:desc` | `str` | A description of the vulnerability and how it was detected in the asset. |
| `:ext:url` | `inet:url` | An external URL which documents the scan result. |
| `:id` | `str` | An externally generated ID for the scan result. |
| `:mitigated` | `time` | The time that the vulnerability in the asset was mitigated. |
| `:mitigation` | `meta:technique` | The mitigation used to address this asset vulnerability. |
| `:priority` | `meta:score` | The priority of mitigating the vulnerability. |
| `:scan` | `it:sec:vuln:scan` | The scan that discovered the vulnerability in the asset. |
| `:severity` | `meta:score` | The severity of the vulnerability in the asset. Use "none" for no vulnerability discovered. |
| `:time` | `time` | The time that the scan result was produced. |
| `:vuln` | `risk:vuln` | The vulnerability detected in the asset. |

### `it:softid`

An identifier issued to a given host by a specific software application.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:host` | `it:host` | The host which was issued the ID by the software. |
| `:id` | `base:id` | The ID issued by the software to the host. |
| `:seen` | `ival` | The software identifier was observed during the time interval. |
| `:software` | `it:software` | The software which issued the ID to the host. |
| `:software:name` | `it:softwarename` | The name of the software which issued the ID to the host. |

### `it:software`

A software product, tool, or script.

| Interface |
|-----------|
| `doc:authorable` |
| `entity:creatable` |
| `meta:observable` |
| `meta:reported` |
| `meta:usable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:cpe` | `it:sec:cpe` | The NIST CPE 2.3 string specifying this software version. |
| `:created` | `time` | The time when the software was created. |
| `:creator` | `entity:actor` | The primary actor which created the software. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the software. |
| `:desc` | `text` | A description of the software. |
| `:id` | `base:id` | A unique ID given to the software. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the software. |
| `:name` | `it:softwarename` | The name of the software. |
| `:names` | `array of it:softwarename` | Observed/variant names for this software version. |
| `:parent` | `it:software` | The parent software version or family. |
| `:published` | `time` | The time when the reporter published the software. |
| `:released` | `time` | Timestamp for when the software was released. |
| `:reporter` | `entity:actor` | The entity which reported on the software. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the software. |
| `:resolved` | `it:software` | The authoritative software which this reporting is about. |
| `:risk:score` | `meta:score` | The risk posed by the software. |
| `:seen` | `ival` | The software was observed during the time interval. |
| `:superseded` | `time` | The time when the software was superseded. |
| `:supersedes` | `array of it:software` | An array of software nodes which are superseded by this software. |
| `:type` | `it:software:type:taxonomy` | The type of software. |
| `:updated` | `time` | The time when the software was last updated. |
| `:url` | `inet:url` | The URL for the software. |
| `:version` | `it:version` | The version of the software. |

### `it:software:image`

The base image used to create a container or OS.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:name` | `it:softwarename` | The name of the image. |
| `:parents` | `array of it:software:image` | An array of parent images in precedence order. |
| `:period` | `ival` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:published` | `time` | The time the image was published. |
| `:publisher` | `entity:contact` | The contact information of the org or person who published the image. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:type` | `it:software:image:type:taxonomy` | The type of software image. |
| `:url` | `inet:url` | The primary URL associated with the object. |

### `it:software:image:type:taxonomy`

A hierarchical taxonomy of software image types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `it:software:image:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `it:software:type:taxonomy`

A hierarchical taxonomy of software types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `it:software:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `it:softwarename`

The name of a software product or tool.

### `it:storage:mount`

A storage volume that has been attached to an image.

| Property | Type | Doc |
|----------|------|-----|
| `:host` | `it:host` | The host that has mounted the volume. |
| `:path` | `file:path` | The path where the volume is mounted in the host filesystem. |
| `:volume` | `it:storage:volume` | The volume that the host has mounted. |

### `it:storage:volume`

A physical or logical storage volume that can be attached to a physical/virtual machine or container.

| Property | Type | Doc |
|----------|------|-----|
| `:id` | `base:id` | The unique volume ID. |
| `:name` | `base:name` | The name of the volume. |
| `:size` | `int` | The size of the volume in bytes. |
| `:type` | `it:storage:volume:type:taxonomy` | The type of storage volume. |

### `it:storage:volume:type:taxonomy`

A hierarchical taxonomy of storage volume types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `it:storage:volume:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `lang:hashtag`

A hashtag used in written text.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The hashtag was observed during the time interval. |

### `lang:idiom`

An idiomatic use of a phrase.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the meaning and origin of the idiom. |
| `:phrase` | `lang:phrase` | The text of the idiom. |

### `lang:language`

A specific written or spoken language.

| Interface |
|-----------|
| `edu:learnable` |

| Property | Type | Doc |
|----------|------|-----|
| `:code` | `lang:code` | The language code for this language. |
| `:name` | `lang:name` | The primary name of the language. |
| `:names` | `array of lang:name` | An array of alternative names for the language. |

### `lang:name`

A name used to refer to a language.

### `lang:phrase`

A small group of words which stand together as a concept.

### `lang:translation`

A translation of text from one language to another.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the meaning of the output. |
| `:engine` | `it:software` | The translation engine version used. |
| `:input` | `text` | The input text. |
| `:input:lang` | `lang:language` | The input language. |
| `:output` | `text` | The output text. |
| `:output:lang` | `lang:language` | The output language. |
| `:time` | `time` | The time when the translation was completed. |
| `:translator` | `entity:actor` | The entity who translated the input. |

### `mat:item`

A GUID assigned to a material object.

| Interface |
|-----------|
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The name of the material item. |
| `:owner` | `entity:actor` | The current owner of the item. |
| `:owner:name` | `entity:name` | The name of the current owner of the item. |
| `:phys:height` | `geo:dist` | The physical height of the object. |
| `:phys:length` | `geo:dist` | The physical length of the object. |
| `:phys:mass` | `mass` | The physical mass of the object. |
| `:phys:volume` | `geo:dist` | The physical volume of the object. |
| `:phys:width` | `geo:dist` | The physical width of the object. |
| `:place` | `geo:place` | The place where the item was located. |
| `:place:address` | `geo:address` | The postal address where the item was located. |
| `:place:address:city` | `base:name` | The city where the item was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the item was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the item was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the item was located. |
| `:place:country` | `pol:country` | The country where the item was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the item was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the item was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the item was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the item was located. |
| `:place:loc` | `loc` | The geopolitical location where the item was located. |
| `:place:name` | `geo:name` | The name where the item was located. |
| `:spec` | `mat:spec` | The specification which defines this item. |
| `:type` | `mat:item:type:taxonomy` | The taxonomy type of the item. |

### `mat:spec`

A GUID assigned to a material specification.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The name of the material specification. |
| `:type` | `mat:item:type:taxonomy` | The taxonomy type for the specification. |

### `math:algorithm`

A mathematical algorithm.

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the algorithm was authored. |
| `:desc` | `text` | A description of the algorithm. |
| `:name` | `base:name` | The name of the algorithm. |
| `:type` | `math:algorithm:type:taxonomy` | The type of algorithm. |

### `math:algorithm:type:taxonomy`

A hierarchical taxonomy of algorithm types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `math:algorithm:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `meta:activity`

Analytically relevant activity.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this activity. |
| `:desc` | `text` | A description of the activity. |
| `:name` | `base:name` | The name of the activity. |
| `:period` | `ival` | The period over which the activity occurred. |
| `:type` | `meta:event:type:taxonomy` | The type of activity. |

### `meta:aggregate`

A node which represents an aggregate count of a specific type.

| Property | Type | Doc |
|----------|------|-----|
| `:count` | `int` | The number of items counted in aggregate. |
| `:time` | `time` | The time that the count was computed. |
| `:type` | `meta:aggregate:type:taxonomy` | The type of items being counted in aggregate. |

### `meta:aggregate:type:taxonomy`

A type of item being counted in aggregate.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `meta:aggregate:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `meta:award`

An award.

| Interface |
|-----------|
| `meta:achievable` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the award. |
| `:issuer` | `entity:actor` | The entity which issues the award. |
| `:issuer:name` | `entity:name` | The name of the entity which issues the award. |
| `:name` | `base:name` | The name of the award. |
| `:names` | `array of base:name` | An array of alternate names for the award. |
| `:period` | `ival` | The period of time when the issuer gave out the award. |
| `:type` | `meta:award:type:taxonomy` | The type of award. |

### `meta:event`

An analytically relevant event.

| Interface |
|-----------|
| `base:event` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:desc` | `text` | A description of the event. |
| `:time` | `time` | The time that the event occurred. |
| `:title` | `str` | A title for the event. |
| `:type` | `meta:event:type:taxonomy` | The type of event. |

### `meta:event:type:taxonomy`

A hierarchical taxonomy of event types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `meta:event:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `meta:feed`

A data feed provided by a specific source.

| Property | Type | Doc |
|----------|------|-----|
| `:cursor` | `str` | A cursor used to track ingest offset within the feed. |
| `:id` | `base:id` | An identifier for the feed. |
| `:latest` | `time` | The time of the last record consumed from the feed. |
| `:name` | `base:name` | A name for the feed. |
| `:offset` | `int` | The offset of the last record consumed from the feed. |
| `:opts` | `data` | An opaque JSON object containing feed parameters and options. |
| `:period` | `ival` | The time window over which results have been ingested. |
| `:query` | `str` | The query logic associated with generating the feed output. |
| `:source` | `meta:source` | The meta:source which provides the feed. |
| `:type` | `meta:feed:type:taxonomy` | The type of data feed. |
| `:url` | `inet:url` | The URL of the feed API endpoint. |

### `meta:feed:type:taxonomy`

A data feed type taxonomy.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `meta:feed:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `meta:note`

An analyst note about nodes linked with -(about)> edges.

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time the note was created. |
| `:creator` | `entity:actor` | The actor who authored the note. |
| `:replyto` | `meta:note` | The note is a reply to the specified note. |
| `:text` | `text` | The analyst authored note text. |
| `:type` | `meta:note:type:taxonomy` | The note type. |
| `:updated` | `time` | The time the note was updated. |

### `meta:note:type:taxonomy`

A hierarchical taxonomy of note types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `meta:note:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `meta:rule`

A generic rule linked to matches with -(matches)> edges.

| Interface |
|-----------|
| `doc:authorable` |
| `entity:creatable` |
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the rule was created. |
| `:creator` | `entity:actor` | The primary actor which created the rule. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the rule. |
| `:desc` | `text` | A description of the rule. |
| `:enabled` | `bool` | The enabled status of the rule. |
| `:id` | `base:id` | The rule ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the rule. |
| `:name` | `base:id` | The rule name. |
| `:seen` | `ival` | The rule was observed during the time interval. |
| `:supersedes` | `array of meta:rule` | An array of rule versions which are superseded by this rule. |
| `:text` | `text` | The text of the rule. |
| `:type` | `meta:rule:type:taxonomy` | The rule type. |
| `:updated` | `time` | The time that the rule was last updated. |
| `:url` | `inet:url` | A URL which documents the rule. |
| `:version` | `it:version` | The version of the rule. |

### `meta:rule:type:taxonomy`

A hierarchical taxonomy of rule types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `meta:rule:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `meta:ruleset`

A set of rules linked with -(has)> edges.

| Interface |
|-----------|
| `doc:authorable` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the ruleset was created. |
| `:creator` | `entity:actor` | The primary actor which created the ruleset. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the ruleset. |
| `:desc` | `text` | A description of the ruleset. |
| `:id` | `base:id` | The ruleset ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the ruleset. |
| `:name` | `base:id` | A name for the ruleset. |
| `:supersedes` | `array of meta:ruleset` | An array of ruleset versions which are superseded by this ruleset. |
| `:type` | `meta:ruleset:type:taxonomy` | The ruleset type. |
| `:updated` | `time` | The time that the ruleset was last updated. |
| `:url` | `inet:url` | The URL where the ruleset is available. |
| `:version` | `it:version` | The version of the ruleset. |

### `meta:source`

A data source unique identifier.

| Property | Type | Doc |
|----------|------|-----|
| `:ingest:cursor` | `str` | Used by ingest logic to capture the current ingest cursor within a feed. |
| `:ingest:latest` | `time` | Used by ingest logic to capture the last time a feed ingest ran. |
| `:ingest:offset` | `int` | Used by ingest logic to capture the current ingest offset within a feed. |
| `:name` | `base:name` | A human friendly name for the source. |
| `:type` | `meta:source:type:taxonomy` | The type of source. |
| `:url` | `inet:url` | A URL which documents the meta source. |

### `meta:source:type:taxonomy`

A hierarchical taxonomy of source types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `meta:source:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `meta:technique`

A specific technique used to achieve a goal.

| Interface |
|-----------|
| `meta:observable` |
| `meta:reported` |
| `meta:usable` |
| `risk:mitigatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time when the technique was created. |
| `:desc` | `text` | A description of the technique. |
| `:id` | `base:id` | A unique ID given to the technique. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the technique. |
| `:name` | `base:name` | The primary name of the technique. |
| `:names` | `array of base:name` | A list of alternate names for the technique. |
| `:parent` | `meta:technique` | The parent technique for the technique. |
| `:published` | `time` | The time when the reporter published the technique. |
| `:reporter` | `entity:actor` | The entity which reported on the technique. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the technique. |
| `:resolved` | `meta:technique` | The authoritative technique which this reporting is about. |
| `:seen` | `ival` | The technique was observed during the time interval. |
| `:sophistication` | `meta:score` | The assessed sophistication of the technique. |
| `:superseded` | `time` | The time when the technique was superseded. |
| `:supersedes` | `array of meta:technique` | An array of technique nodes which are superseded by this technique. |
| `:tag` | `syn:tag` | The tag used to annotate nodes where the technique was employed. |
| `:type` | `meta:technique:type:taxonomy` | The taxonomy classification of the technique. |
| `:updated` | `time` | The time when the technique was last updated. |
| `:url` | `inet:url` | The URL for the technique. |

### `meta:technique:type:taxonomy`

A hierarchical taxonomy of technique types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `meta:technique:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `meta:timeline`

A curated timeline of analytically relevant events.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the timeline. |
| `:title` | `str` | The title of the timeline. |
| `:type` | `meta:timeline:type:taxonomy` | The type of timeline. |

### `meta:timeline:type:taxonomy`

A hierarchical taxonomy of timeline types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `meta:timeline:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `meta:topic`

A topic string.

| Interface |
|-----------|
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the topic. |

### `ou:asset`

A node for tracking assets which belong to an organization.

| Interface |
|-----------|
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:id` | `base:id` | The ID of the asset. |
| `:name` | `base:name` | The name of the assset. |
| `:node` | `meta:havable` | The node which represents the asset. |
| `:operator` | `entity:contact` | The contact information of the user or operator of the asset. |
| `:org` | `ou:org` | The organization which owns the asset. |
| `:owner` | `entity:contact` | The contact information of the owner or administrator of the asset. |
| `:period` | `ival` | The period of time when the asset was being tracked. |
| `:place` | `geo:place` | The place where the asset is deployed. |
| `:priority` | `meta:score` | The overall priority of protecting the asset. |
| `:priority:availability` | `meta:score` | The priority of protecting the availability of the asset. |
| `:priority:confidentiality` | `meta:score` | The priority of protecting the confidentiality of the asset. |
| `:priority:integrity` | `meta:score` | The priority of protecting the integrity of the asset. |
| `:status` | `ou:asset:status:taxonomy` | The current status of the asset. |
| `:type` | `ou:asset:type:taxonomy` | The asset type. |

### `ou:asset:status:taxonomy`

An asset status taxonomy.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:asset:status:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:asset:type:taxonomy`

An asset type taxonomy.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:asset:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:candidate`

A candidate being considered for a role within an organization.

| Property | Type | Doc |
|----------|------|-----|
| `:agent` | `entity:contact` | The contact information of an agent who advocates for the candidate. |
| `:attachments` | `array of file:attachment` | An array of additional files submitted by the candidate. |
| `:contact` | `entity:contact` | The contact information of the candidate. |
| `:intro` | `str` | An introduction or cover letter text submitted by the candidate. |
| `:method` | `ou:candidate:method:taxonomy` | The method by which the candidate came under consideration. |
| `:opening` | `ou:opening` | The opening that the candidate is being considered for. |
| `:org` | `ou:org` | The organization considering the candidate. |
| `:recruiter` | `entity:contact` | The contact information of a recruiter who works on behalf of the organization. |
| `:resume` | `doc:resume` | The candidate's resume or CV. |
| `:submitted` | `time` | The time the candidate was submitted for consideration. |

### `ou:candidate:method:taxonomy`

A taxonomy of methods by which a candidate came under consideration.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:candidate:method:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:candidate:referral`

A candidate being referred by a contact.

| Property | Type | Doc |
|----------|------|-----|
| `:candidate` | `ou:candidate` | The candidate who was referred. |
| `:referrer` | `entity:contact` | The individual who referred the candidate to the opening. |
| `:submitted` | `time` | The time the referral was submitted. |
| `:text` | `str` | Text of any referrer provided context about the candidate. |

### `ou:conference`

A conference.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `entity:supportable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |
| `ou:promotable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this conference. |
| `:family` | `event:name` | The family name of the conference used to group recurring events. |
| `:name` | `event:name` | The name of the conference. |
| `:names` | `array of event:name` | An array of alternate names for the conference. |
| `:period` | `ival` | The period over which the conference occurred. |
| `:place` | `geo:place` | The place where the conference was located. |
| `:place:address` | `geo:address` | The postal address where the conference was located. |
| `:place:address:city` | `base:name` | The city where the conference was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the conference was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the conference was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the conference was located. |
| `:place:country` | `pol:country` | The country where the conference was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the conference was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the conference was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the conference was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the conference was located. |
| `:place:loc` | `loc` | The geopolitical location where the conference was located. |
| `:place:name` | `geo:name` | The name where the conference was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the conference. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the conference. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the conference. |
| `:website` | `inet:url` | The website of the conference website. |

### `ou:contest`

A competitive event resulting in a ranked set of participants.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `entity:supportable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |
| `ou:promotable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this contest. |
| `:name` | `event:name` | The name of the contest. |
| `:names` | `array of event:name` | An array of alternate names for the contest. |
| `:period` | `ival` | The period over which the contest occurred. |
| `:place` | `geo:place` | The place where the contest was located. |
| `:place:address` | `geo:address` | The postal address where the contest was located. |
| `:place:address:city` | `base:name` | The city where the contest was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the contest was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the contest was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the contest was located. |
| `:place:country` | `pol:country` | The country where the contest was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the contest was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the contest was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the contest was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the contest was located. |
| `:place:loc` | `loc` | The geopolitical location where the contest was located. |
| `:place:name` | `geo:name` | The name where the contest was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the contest. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the contest. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the contest. |
| `:type` | `ou:contest:type:taxonomy` | The type of contest. |
| `:website` | `inet:url` | The website of the contest website. |

### `ou:contest:result`

The results from a single contest participant.

| Property | Type | Doc |
|----------|------|-----|
| `:contest` | `ou:contest` | The contest that the participant took part in. |
| `:participant` | `entity:actor` | The participant in the contest. |
| `:period` | `ival` | The period of time when the participant competed in the contest. |
| `:rank` | `int` | The participant's rank order in the contest. |
| `:score` | `int` | The participant's final score in the contest. |
| `:url` | `inet:url` | A URL which documents the participant's results. |

### `ou:contest:type:taxonomy`

A hierarchical taxonomy of contest types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:contest:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:employment:type:taxonomy`

A hierarchical taxonomy of employment types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:employment:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:enacted`

An organization enacting a document.

| Interface |
|-----------|
| `meta:task` |

| Property | Type | Doc |
|----------|------|-----|
| `:assignee` | `entity:actor` | The actor who is assigned to complete the adoption task. |
| `:completed` | `time` | The time the adoption task was completed. |
| `:created` | `time` | The time the adoption task was created. |
| `:creator` | `entity:actor` | The actor who created the adoption task. |
| `:doc` | `doc:policy`, `doc:requirement`, `doc:standard` | The document enacted by the organization. |
| `:due` | `time` | The time the adoption task must be complete. |
| `:id` | `base:id` | The ID of the adoption task. |
| `:org` | `ou:org` | The organization which is enacting the document. |
| `:parent` | `meta:task` | The parent task which includes this adoption task. |
| `:priority` | `meta:score` | The priority of the adoption task. |
| `:project` | `proj:project` | The project containing the adoption task. |
| `:scope` | `ou:org`, `ou:team` | The scope of responsbility for the assignee to enact the document. |
| `:status` | `meta:task:status` | The status of the adoption task. |
| `:updated` | `time` | The time the adoption task was last updated. |

### `ou:enacted:status:taxonomy`

A taxonomy of enacted statuses.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:enacted:status:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:event`

An generic organized event.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `entity:supportable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |
| `ou:promotable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:name` | `event:name` | The name of the event. |
| `:names` | `array of event:name` | An array of alternate names for the event. |
| `:period` | `ival` | The period over which the event occurred. |
| `:place` | `geo:place` | The place where the event was located. |
| `:place:address` | `geo:address` | The postal address where the event was located. |
| `:place:address:city` | `base:name` | The city where the event was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the event was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the event was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the event was located. |
| `:place:country` | `pol:country` | The country where the event was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the event was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the event was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the event was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the event was located. |
| `:place:loc` | `loc` | The geopolitical location where the event was located. |
| `:place:name` | `geo:name` | The name where the event was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the event. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the event. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the event. |
| `:type` | `ou:event:type:taxonomy` | The type of event. |
| `:website` | `inet:url` | The website of the event website. |

### `ou:event:type:taxonomy`

A hierarchical taxonomy of event types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:event:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:id`

An ID value issued by an organization.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:expires` | `date` | The date when the ID expires. |
| `:issued` | `date` | The date when the ID was initially issued. |
| `:issuer` | `ou:org` | The organization which issued the ID. |
| `:issuer:name` | `entity:name` | The name of the issuer. |
| `:recipient` | `entity:actor` | The entity which was issued the ID. |
| `:seen` | `ival` | The ID was observed during the time interval. |
| `:status` | `ou:id:status:taxonomy` | The most recently known status of the ID. |
| `:type` | `ou:id:type:taxonomy` | The type of ID issued. |
| `:updated` | `date` | The date when the ID was most recently updated. |
| `:value` | `entity:identifier` | The ID value. |

### `ou:id:history`

Changes made to an ID over time.

| Property | Type | Doc |
|----------|------|-----|
| `:id` | `ou:id` | The current ID information. |
| `:status` | `ou:id:status:taxonomy` | The status of the ID at the time. |
| `:updated` | `date` | The time the ID was updated. |

### `ou:id:status:taxonomy`

A hierarchical taxonomy of ID status values.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:id:status:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:id:type:taxonomy`

A hierarchical taxonomy of ID types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:id:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:industry`

An industry classification type.

| Interface |
|-----------|
| `meta:reported` |
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time when the industry was created. |
| `:desc` | `text` | A description of the industry. |
| `:id` | `base:id` | A unique ID given to the industry. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the industry. |
| `:isic` | `array of ou:isic` | An array of ISIC codes that map to the industry. |
| `:naics` | `array of ou:naics` | An array of NAICS codes that map to the industry. |
| `:name` | `base:name` | The primary name of the industry. |
| `:names` | `array of base:name` | A list of alternate names for the industry. |
| `:published` | `time` | The time when the reporter published the industry. |
| `:reporter` | `entity:actor` | The entity which reported on the industry. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the industry. |
| `:resolved` | `ou:industry` | The authoritative industry which this reporting is about. |
| `:sic` | `array of ou:sic` | An array of SIC codes that map to the industry. |
| `:superseded` | `time` | The time when the industry was superseded. |
| `:supersedes` | `array of ou:industry` | An array of industry nodes which are superseded by this industry. |
| `:type` | `ou:industry:type:taxonomy` | A taxonomy entry for the industry. |
| `:updated` | `time` | The time when the industry was last updated. |
| `:url` | `inet:url` | The URL for the industry. |

### `ou:industry:type:taxonomy`

A hierarchical taxonomy of industry types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:industry:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:job:type:taxonomy`

A hierarchical taxonomy of job types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:job:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:meeting`

A meeting.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this meeting. |
| `:name` | `event:name` | The name of the meeting. |
| `:period` | `ival` | The period over which the meeting occurred. |
| `:place` | `geo:place` | The place where the meeting was located. |
| `:place:address` | `geo:address` | The postal address where the meeting was located. |
| `:place:address:city` | `base:name` | The city where the meeting was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the meeting was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the meeting was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the meeting was located. |
| `:place:country` | `pol:country` | The country where the meeting was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the meeting was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the meeting was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the meeting was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the meeting was located. |
| `:place:loc` | `loc` | The geopolitical location where the meeting was located. |
| `:place:name` | `geo:name` | The name where the meeting was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the meeting. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the meeting. |

### `ou:opening`

A job/work opening within an org.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:contact` | The contact details to inquire about the opening. |
| `:employment:type` | `ou:employment:type:taxonomy` | The type of employment. |
| `:job:type` | `ou:job:type:taxonomy` | The job type taxonomy. |
| `:loc` | `loc` | The geopolitical boundary of the opening. |
| `:org` | `ou:org` | The org which has the opening. |
| `:org:fqdn` | `inet:fqdn` | The FQDN of the organization as listed in the opening. |
| `:org:name` | `entity:name` | The name of the organization as listed in the opening. |
| `:pay:max` | `econ:price` | The maximum pay for the job. |
| `:pay:min` | `econ:price` | The minimum pay for the job. |
| `:pay:pertime` | `duration` | The duration over which the position pays. |
| `:period` | `ival` | The time period when the opening existed. |
| `:postings` | `array of inet:url` | URLs where the opening is listed. |
| `:remote` | `bool` | Set to true if the opening will allow a fully remote worker. |
| `:title` | `entity:title` | The title of the opening. |

### `ou:org`

An organization, such as a company or military unit.

| Interface |
|-----------|
| `entity:actor` |
| `entity:contactable` |
| `entity:multiple` |
| `geo:locatable` |
| `meta:havable` |
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:banner` | `file:bytes` | A banner or hero image used on the profile page. |
| `:bio` | `text` | A tagline or bio provided for the organization. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the organization. |
| `:desc` | `text` | A description of the organization. |
| `:dns:mx` | `array of inet:fqdn` | An array of MX domains used by email addresses issued by the org. |
| `:email` | `inet:email` | The primary email address for the organization. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the organization. |
| `:id` | `base:id` | A type or source specific ID for the organization. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:industries` | `array of ou:industry` | The industries associated with the org. |
| `:lang` | `lang:language` | The primary language of the organization. |
| `:langs` | `array of lang:language` | An array of alternate languages for the organization. |
| `:lifespan` | `ival` | The lifespan of the organization. |
| `:logo` | `file:bytes` | An image file representing the logo for the organization. |
| `:motto` | `lang:phrase` | The motto used by the organization. |
| `:name` | `entity:name` | The primary entity name of the organization. |
| `:names` | `array of entity:name` | An array of alternate entity names for the organization. |
| `:orgchart` | `ou:position` | The root node for an orgchart made up ou:position nodes. |
| `:owner` | `entity:actor` | The current owner of the organization. |
| `:owner:name` | `entity:name` | The name of the current owner of the organization. |
| `:parent` | `ou:org` | The parent organization. |
| `:phone` | `tel:phone` | The primary phone number for the organization. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the organization. |
| `:photo` | `file:bytes` | The profile picture or avatar for this organization. |
| `:place` | `geo:place` | The place where the organization was located. |
| `:place:address` | `geo:address` | The postal address where the organization was located. |
| `:place:address:city` | `base:name` | The city where the organization was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the organization was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the organization was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the organization was located. |
| `:place:country` | `pol:country` | The country where the organization was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the organization was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the organization was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the organization was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the organization was located. |
| `:place:loc` | `loc` | The geopolitical location where the organization was located. |
| `:place:name` | `geo:name` | The name where the organization was located. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the organization. |
| `:tag` | `syn:tag` | A base tag used to encode assessments made by the organization. |
| `:type` | `ou:org:type:taxonomy` | The type of organization. |
| `:user` | `inet:user` | The primary user name for the organization. |
| `:users` | `array of inet:user` | An array of alternate user names for the organization. |
| `:vitals` | `ou:vitals` | The most recent/accurate ou:vitals for the org. |
| `:websites` | `array of inet:url` | Web sites listed for the organization. |

### `ou:org:type:taxonomy`

A hierarchical taxonomy of organization types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ou:org:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ou:orgnet`

An IP address block which belongs to an organization.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The name that the organization assigns to this netblock. |
| `:net` | `inet:net` | Netblock owned by the organization. |
| `:org` | `ou:org` | The org guid which owns the netblock. |

### `ou:position`

A position within an org which can be organized into an org chart with replaceable contacts.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:individual` | The contact info for the person who holds the position. |
| `:org` | `ou:org` | The org which has the position. |
| `:reports` | `array of ou:position` | An array of positions which report to this position. |
| `:team` | `ou:team` | The team that the position is a member of. |
| `:title` | `entity:title` | The title of the position. |

### `ou:preso`

A webinar, conference talk, or other type of presentation.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `entity:supportable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |
| `ou:promotable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this presentation. |
| `:attendee:url` | `inet:url` | The URL visited by live attendees of the presentation. |
| `:deck:file` | `file:bytes` | A file containing the presentation materials. |
| `:deck:url` | `inet:url` | The URL hosting a copy of the presentation materials. |
| `:name` | `event:name` | The name of the presentation. |
| `:names` | `array of event:name` | An array of alternate names for the presentation. |
| `:period` | `ival` | The period over which the presentation occurred. |
| `:place` | `geo:place` | The place where the presentation was located. |
| `:place:address` | `geo:address` | The postal address where the presentation was located. |
| `:place:address:city` | `base:name` | The city where the presentation was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the presentation was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the presentation was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the presentation was located. |
| `:place:country` | `pol:country` | The country where the presentation was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the presentation was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the presentation was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the presentation was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the presentation was located. |
| `:place:loc` | `loc` | The geopolitical location where the presentation was located. |
| `:place:name` | `geo:name` | The name where the presentation was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the presentation. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the presentation. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the presentation. |
| `:website` | `inet:url` | The website of the presentation website. |

### `ou:team`

A GUID for a team within an organization.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `entity:name` | The name of the team. |
| `:org` | `ou:org` | The organization that the team is associated with. |

### `ou:vitals`

Vital statistics about an org for a given time period.

| Property | Type | Doc |
|----------|------|-----|
| `:budget` | `econ:price` | The budget allocated for the period. |
| `:costs` | `econ:price` | The costs/expenditures over the period. |
| `:delta:costs` | `econ:price` | The change in costs over last period. |
| `:delta:population` | `int` | The change in population over last period. |
| `:delta:profit` | `econ:price` | The change in profit over last period. |
| `:delta:revenue` | `econ:price` | The change in revenue over last period. |
| `:delta:valuation` | `econ:price` | The change in valuation over last period. |
| `:org` | `ou:org` | The resolved org. |
| `:org:fqdn` | `inet:fqdn` | The org FQDN as reported by the source of the vitals. |
| `:org:name` | `entity:name` | The org name as reported by the source of the vitals. |
| `:population` | `int` | The population of the org. |
| `:profit` | `econ:price` | The net profit over the period. |
| `:revenue` | `econ:price` | The gross revenue over the period. |
| `:shares` | `int` | The number of shares outstanding. |
| `:time` | `time` | The time that the vitals represent. |
| `:valuation` | `econ:price` | The assessed value of the org. |

### `phys:contained`

A node which represents a physical object containing another physical object.

| Property | Type | Doc |
|----------|------|-----|
| `:container` | `phys:object` | The container which held the object. |
| `:object` | `phys:object` | The object held within the container. |
| `:period` | `ival` | The period where the container held the object. |
| `:type` | `phys:contained:type:taxonomy` | The type of container relationship. |

### `phys:contained:type:taxonomy`

A taxonomy for types of contained relationships.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `phys:contained:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `plan:phase`

A phase within a planning system which may be used to group steps within a procedure.

| Interface |
|-----------|
| `doc:authorable` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the phase was created. |
| `:creator` | `entity:actor` | The primary actor which created the phase. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the phase. |
| `:desc` | `text` | A description of the definition of the phase. |
| `:id` | `base:id` | The phase ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the phase. |
| `:index` | `int` | The index of this phase within the phases of the system. |
| `:supersedes` | `array of plan:phase` | An array of phase versions which are superseded by this phase. |
| `:system` | `plan:system` | The planning system which defines this phase. |
| `:title` | `str` | The title of the phase. |
| `:updated` | `time` | The time that the phase was last updated. |
| `:url` | `inet:url` | A URL which links to the full documentation about the phase. |
| `:version` | `it:version` | The version of the phase. |

### `plan:procedure`

A procedure consisting of steps.

| Interface |
|-----------|
| `doc:authorable` |
| `doc:document` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:body` | `text` | The text of the procedure. |
| `:created` | `time` | The time that the procedure was created. |
| `:creator` | `entity:actor` | The primary actor which created the procedure. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the procedure. |
| `:desc` | `text` | A description of the procedure. |
| `:file` | `file:bytes` | The file containing the procedure contents. |
| `:file:captured` | `time` | The time when the file content was captured. |
| `:file:name` | `file:base` | The name of the file containing the procedure contents. |
| `:firststep` | `plan:procedure:step` | The first step in the procedure. |
| `:id` | `base:id` | The procedure ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the procedure. |
| `:inputs` | `array of plan:procedure:variable` | An array of inputs required to execute the procedure. |
| `:supersedes` | `array of plan:procedure` | An array of procedure versions which are superseded by this procedure. |
| `:system` | `plan:system` | The planning system which defines this procedure. |
| `:title` | `str` | The title of the procedure. |
| `:type` | `plan:procedure:type:taxonomy` | A type classification for the procedure. |
| `:updated` | `time` | The time that the procedure was last updated. |
| `:url` | `inet:url` | The URL where the procedure is available. |
| `:version` | `it:version` | The version of the procedure. |

### `plan:procedure:link`

A link between steps in a procedure.

| Property | Type | Doc |
|----------|------|-----|
| `:condition` | `bool` | Set to true/false if this link is conditional based on a decision step. |
| `:next` | `plan:procedure:step` | The next step in the plan. |
| `:procedure` | `plan:procedure` | The procedure which defines the link. |

### `plan:procedure:step`

A step within a procedure.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the tasks executed within the step. |
| `:links` | `array of plan:procedure:link` | An array of links to subsequent steps. |
| `:outputs` | `array of plan:procedure:variable` | An array of variables defined in this step. |
| `:phase` | `plan:phase` | The phase that the step belongs within. |
| `:procedure` | `plan:procedure` | The procedure which defines the step. |
| `:title` | `str` | The title of the step. |

### `plan:procedure:type:taxonomy`

A hierarchical taxonomy of procedure types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `plan:procedure:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `plan:procedure:variable`

A variable used by a procedure.

| Property | Type | Doc |
|----------|------|-----|
| `:default` | `data` | The optional default value if the procedure is invoked without the input. |
| `:name` | `str` | The name of the variable. |
| `:procedure` | `plan:procedure` | The procedure which defines the variable. |
| `:type` | `str` | The type for the input. Types are specific to the planning system. |

### `plan:system`

A planning or behavioral analysis system that defines phases and procedures.

| Interface |
|-----------|
| `doc:authorable` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:author` | `entity:actor` | The contact of the person or organization which authored the system. |
| `:created` | `time` | The time the planning system was first created. |
| `:creator` | `entity:actor` | The primary actor which created the planning system. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the planning system. |
| `:desc` | `text` | A description of the planning system. |
| `:id` | `base:id` | The planning system ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the planning system. |
| `:name` | `base:name` | The name of the planning system. |
| `:supersedes` | `array of plan:system` | An array of planning system versions which are superseded by this planning system. |
| `:updated` | `time` | The time the planning system was last updated. |
| `:url` | `inet:url` | The primary URL which documents the planning system. |
| `:version` | `it:version` | The version of the planning system. |

### `pol:candidate`

A candidate for office in a specific race.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this candidacy. |
| `:actor` | `entity:actor` | The actor who carried out the candidacy. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the candidacy. |
| `:campaign` | `entity:campaign` | The official campaign to elect the candidate. |
| `:id` | `base:id` | A unique ID for the candidate issued by an election authority. |
| `:incumbent` | `bool` | Set to true if the candidate is an incumbent in this race. |
| `:party` | `ou:org` | The declared political party of the candidate. |
| `:period` | `ival` | The period over which the candidacy occurred. |
| `:race` | `pol:race` | The race the candidate is participating in. |
| `:votes` | `int` | The total number of votes received by the candidate. |
| `:winner` | `bool` | Records the outcome of the race. |

### `pol:country`

A GUID for a country.

| Interface |
|-----------|
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:code` | `pol:country:code` | The country code. |
| `:codes` | `array of pol:country:code` | An array of country codes. |
| `:currencies` | `array of econ:currency` | The official currencies used in the country. |
| `:flag` | `file:bytes` | A thumbnail image of the flag of the country. |
| `:government` | `ou:org` | The government of the country. |
| `:iso:3166:alpha3` | `iso:3166:alpha3` | The ISO 3166 Alpha-3 country code. |
| `:iso:3166:numeric3` | `iso:3166:numeric3` | The ISO 3166 Numeric-3 country code. |
| `:name` | `geo:name` | The name of the country. |
| `:names` | `array of geo:name` | An array of alternate or localized names for the country. |
| `:period` | `ival` | The period over which the country existed. |
| `:place` | `geo:place` | The geospatial properties of the country. |
| `:tld` | `inet:fqdn` | The top-level domain for the country. |
| `:vitals` | `pol:vitals` | The most recent known vitals for the country. |

### `pol:election`

An election involving one or more races for office.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this election. |
| `:name` | `event:name` | The name of the election. |
| `:period` | `ival` | The period over which the election occurred. |
| `:time` | `time` | The date of the election. |

### `pol:immigration:status`

A node which tracks the immigration status of a contact.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:contact` | The contact information for the immigration status record. |
| `:country` | `pol:country` | The country that the contact is/has immigrated to. |
| `:period` | `ival` | The time period when the contact was granted the status. |
| `:state` | `pol:immigration:state` | The state of the immigration status. |
| `:type` | `pol:immigration:status:type:taxonomy` | A taxonomy entry for the immigration status type. |

### `pol:immigration:status:type:taxonomy`

A hierarchical taxonomy of immigration status types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `pol:immigration:status:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `pol:office`

An elected or appointed office.

| Property | Type | Doc |
|----------|------|-----|
| `:govbody` | `ou:org` | The governmental body which contains the office. |
| `:position` | `ou:position` | The position this office holds in the org chart for the governing body. |
| `:termlimit` | `int` | The maximum number of times a single person may hold the office. |
| `:title` | `entity:title` | The title of the political office. |

### `pol:pollingplace`

An official place where ballots may be cast for a specific election.

| Property | Type | Doc |
|----------|------|-----|
| `:closed` | `time` | The time that the polling place closed. |
| `:closes` | `time` | The time that the polling place is scheduled to close. |
| `:election` | `pol:election` | The election that the polling place is designated for. |
| `:name` | `geo:name` | The name of the polling place at the time of the election. This may differ from the official place name. |
| `:opened` | `time` | The time that the polling place opened. |
| `:opens` | `time` | The time that the polling place is scheduled to open. |
| `:place` | `geo:place` | The place where votes were cast. |

### `pol:race`

An individual race for office.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this political race. |
| `:election` | `pol:election` | The election that includes the race. |
| `:office` | `pol:office` | The political office that the candidates in the race are running for. |
| `:period` | `ival` | The period over which the political race occurred. |
| `:turnout` | `int` | The number of individuals who voted in this race. |
| `:voters` | `int` | The number of eligible voters for this race. |

### `pol:term`

A term in office held by a specific individual.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this term. |
| `:actor` | `entity:actor` | The actor who carried out the term. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the term. |
| `:office` | `pol:office` | The office held for the term. |
| `:party` | `ou:org` | The political party of the person who held office during the term. |
| `:period` | `ival` | The period over which the term occurred. |
| `:race` | `pol:race` | The race that determined who held office during the term. |

### `pol:vitals`

A set of vital statistics about a country.

| Property | Type | Doc |
|----------|------|-----|
| `:area` | `geo:area` | The area of the country. |
| `:country` | `pol:country` | The country that the statistics are about. |
| `:currency` | `econ:currency` | The national currency. |
| `:econ:gdp` | `econ:price` | The gross domestic product of the country. |
| `:population` | `int` | The total number of people living in the country. |
| `:time` | `time` | The time that the vitals were measured. |

### `proj:project`

A project in a tasking system.

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time the project was created. |
| `:creator` | `entity:actor` | The actor who created the project. |
| `:desc` | `text` | The project description. |
| `:name` | `str` | The project name. |
| `:platform` | `inet:service:platform` | The platform where the project is hosted. |
| `:type` | `proj:project:type:taxonomy` | The project type. |

### `proj:project:type:taxonomy`

A type taxonomy for projects.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `proj:project:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `proj:sprint`

A timeboxed period to complete a set amount of work.

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The date the sprint was created. |
| `:creator` | `entity:actor` | The actor who created the sprint. |
| `:desc` | `str` | A description of the sprint. |
| `:name` | `str` | The name of the sprint. |
| `:period` | `ival` | The interval for the sprint. |
| `:project` | `proj:project` | The project containing the sprint. |
| `:status` | `proj:sprint:status` | The sprint status. |

### `proj:ticket`

A ticket in a project management system.

| Interface |
|-----------|
| `meta:task` |

| Property | Type | Doc |
|----------|------|-----|
| `:assignee` | `entity:actor` | The actor who is assigned to complete the ticket. |
| `:completed` | `time` | The time the ticket was completed. |
| `:created` | `time` | The time the ticket was created. |
| `:creator` | `entity:actor` | The actor who created the ticket. |
| `:desc` | `text` | A description of the task. |
| `:due` | `time` | The time the ticket must be complete. |
| `:id` | `base:id` | The ID of the ticket. |
| `:name` | `str` | The name of the task. |
| `:parent` | `meta:task` | The parent task which includes this ticket. |
| `:points` | `int` | Optional SCRUM style story points value. |
| `:priority` | `meta:score` | The priority of the ticket. |
| `:project` | `proj:project` | The project containing the ticket. |
| `:status` | `meta:task:status` | The status of the ticket. |
| `:type` | `proj:ticket:type:taxonomy` | The type of task. |
| `:updated` | `time` | The time the ticket was last updated. |
| `:url` | `inet:url` | A URL which contains details about the task. |

### `proj:ticket:type:taxonomy`

A hierarchical taxonomy of project task types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `proj:ticket:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ps:person`

A person or persona.

| Interface |
|-----------|
| `entity:actor` |
| `entity:contactable` |
| `entity:singular` |
| `geo:locatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:banner` | `file:bytes` | A banner or hero image used on the profile page. |
| `:bio` | `text` | A tagline or bio provided for the person. |
| `:birth:place` | `geo:place` | The place where the person was born. |
| `:birth:place:address` | `geo:address` | The postal address where the person was born. |
| `:birth:place:address:city` | `base:name` | The city where the person was born. |
| `:birth:place:altitude` | `geo:altitude` | The altitude where the person was born. |
| `:birth:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the person was born. |
| `:birth:place:bbox` | `geo:bbox` | A bounding box which encompasses where the person was born. |
| `:birth:place:country` | `pol:country` | The country where the person was born. |
| `:birth:place:country:code` | `iso:3166:alpha2` | The country code where the person was born. |
| `:birth:place:geojson` | `geo:json` | A GeoJSON representation of where the person was born. |
| `:birth:place:latlong` | `geo:latlong` | The latlong where the person was born. |
| `:birth:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the person was born. |
| `:birth:place:loc` | `loc` | The geopolitical location where the person was born. |
| `:birth:place:name` | `geo:name` | The name where the person was born. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the person. |
| `:death:place` | `geo:place` | The place where the person died. |
| `:death:place:address` | `geo:address` | The postal address where the person died. |
| `:death:place:address:city` | `base:name` | The city where the person died. |
| `:death:place:altitude` | `geo:altitude` | The altitude where the person died. |
| `:death:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the person died. |
| `:death:place:bbox` | `geo:bbox` | A bounding box which encompasses where the person died. |
| `:death:place:country` | `pol:country` | The country where the person died. |
| `:death:place:country:code` | `iso:3166:alpha2` | The country code where the person died. |
| `:death:place:geojson` | `geo:json` | A GeoJSON representation of where the person died. |
| `:death:place:latlong` | `geo:latlong` | The latlong where the person died. |
| `:death:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the person died. |
| `:death:place:loc` | `loc` | The geopolitical location where the person died. |
| `:death:place:name` | `geo:name` | The name where the person died. |
| `:desc` | `text` | A description of the person. |
| `:email` | `inet:email` | The primary email address for the person. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the person. |
| `:id` | `base:id` | A type or source specific ID for the person. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:lang` | `lang:language` | The primary language of the person. |
| `:langs` | `array of lang:language` | An array of alternate languages for the person. |
| `:lifespan` | `ival` | The lifespan of the person. |
| `:name` | `entity:name` | The primary entity name of the person. |
| `:names` | `array of entity:name` | An array of alternate entity names for the person. |
| `:org` | `ou:org` | An associated organization listed as part of the contact information. |
| `:org:name` | `entity:name` | The name of an associated organization listed as part of the contact information. |
| `:phone` | `tel:phone` | The primary phone number for the person. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the person. |
| `:photo` | `file:bytes` | The profile picture or avatar for this person. |
| `:place` | `geo:place` | The place where the person was located. |
| `:place:address` | `geo:address` | The postal address where the person was located. |
| `:place:address:city` | `base:name` | The city where the person was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the person was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the person was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the person was located. |
| `:place:country` | `pol:country` | The country where the person was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the person was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the person was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the person was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the person was located. |
| `:place:loc` | `loc` | The geopolitical location where the person was located. |
| `:place:name` | `geo:name` | The name where the person was located. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the person. |
| `:title` | `entity:title` | The entity title or role for this person. |
| `:titles` | `array of entity:title` | An array of alternate entity titles or roles for this person. |
| `:user` | `inet:user` | The primary user name for the person. |
| `:users` | `array of inet:user` | An array of alternate user names for the person. |
| `:vitals` | `ps:vitals` | The most recent vitals for the person. |
| `:websites` | `array of inet:url` | Web sites listed for the person. |

### `ps:skill`

A specific skill which a person or organization may have.

| Interface |
|-----------|
| `edu:learnable` |

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The name of the skill. |
| `:type` | `ps:skill:type:taxonomy` | The type of skill as a taxonomy. |

### `ps:skill:type:taxonomy`

A hierarchical taxonomy of skill types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `ps:skill:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `ps:vitals`

Statistics and demographic data about a person.

| Interface |
|-----------|
| `geo:locatable` |
| `phys:tangible` |

| Property | Type | Doc |
|----------|------|-----|
| `:econ:annual:income` | `econ:price` | The yearly income of the contact. |
| `:econ:net:worth` | `econ:price` | The net worth of the contact. |
| `:individual` | `entity:individual` | The individual that the vitals are about. |
| `:phys:height` | `geo:dist` | The physical height of the person. |
| `:phys:length` | `geo:dist` | The physical length of the person. |
| `:phys:mass` | `mass` | The physical mass of the person. |
| `:phys:volume` | `geo:dist` | The physical volume of the person. |
| `:phys:width` | `geo:dist` | The physical width of the person. |
| `:place` | `geo:place` | The place where the person was located. |
| `:place:address` | `geo:address` | The postal address where the person was located. |
| `:place:address:city` | `base:name` | The city where the person was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the person was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the person was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the person was located. |
| `:place:country` | `pol:country` | The country where the person was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the person was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the person was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the person was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the person was located. |
| `:place:loc` | `loc` | The geopolitical location where the person was located. |
| `:place:name` | `geo:name` | The name where the person was located. |
| `:time` | `time` | The time the vitals were gathered or computed. |

### `ps:workhist`

An entry in a contact's work history.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:individual` | The contact which has the work history. |
| `:desc` | `str` | A description of the work done as part of the job. |
| `:employment:type` | `ou:employment:type:taxonomy` | The type of employment. |
| `:job:type` | `ou:job:type:taxonomy` | The type of job. |
| `:org` | `ou:org` | The org that this work history orgname refers to. |
| `:org:fqdn` | `inet:fqdn` | The reported fqdn of the org the contact worked for. |
| `:org:name` | `entity:name` | The reported name of the org the contact worked for. |
| `:pay` | `econ:price` | The average yearly income paid to the contact. |
| `:period` | `ival` | The period of time that the contact worked for the organization. |
| `:title` | `entity:title` | The title held by the contact. |

### `risk:alert`

An alert which indicates the presence of a risk.

| Interface |
|-----------|
| `meta:causal` |
| `meta:task` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account`, `it:host:account` | The account which generated the alert. |
| `:assignee` | `entity:actor` | The actor who is assigned to complete the alert. |
| `:benign` | `bool` | Set to true if the alert has been confirmed benign. Set to false if malicious. |
| `:completed` | `time` | The time the alert was completed. |
| `:created` | `time` | The time the alert was created. |
| `:creator` | `entity:actor` | The actor who created the alert. |
| `:desc` | `text` | A free-form description / overview of the alert. |
| `:due` | `time` | The time the alert must be complete. |
| `:engine` | `it:software` | The software that generated the alert. |
| `:host` | `it:host` | The host which generated the alert. |
| `:id` | `base:id` | The ID of the alert. |
| `:name` | `base:name` | A brief name for the alert. |
| `:parent` | `meta:task` | The parent task which includes this alert. |
| `:platform` | `inet:service:platform` | The service platform which generated the alert. |
| `:priority` | `meta:score` | The priority of the alert. |
| `:project` | `proj:project` | The project containing the alert. |
| `:severity` | `meta:score` | A severity rank for the alert. |
| `:status` | `risk:alert:status` | The status of the alert. |
| `:type` | `risk:alert:type:taxonomy` | A type for the alert, as a taxonomy entry. |
| `:updated` | `time` | The time the alert was last updated. |
| `:url` | `inet:url` | A URL which documents the alert. |
| `:verdict` | `risk:alert:verdict:taxonomy` | A verdict about why the alert is malicious or benign, as a taxonomy entry. |

### `risk:alert:type:taxonomy`

A hierarchical taxonomy of alert types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:alert:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:alert:verdict:taxonomy`

A hierarchical taxonomy of alert verdicts.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:alert:verdict:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:attack`

An instance of an actor attacking a target.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |
| `meta:discoverable` |
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this attack. |
| `:actor` | `entity:actor` | The actor who carried out the attack. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the attack. |
| `:compromise` | `risk:compromise` | A compromise that this attack contributed to. |
| `:created` | `time` | The time when the attack was created. |
| `:desc` | `text` | A description of the attack. |
| `:detected` | `time` | The first confirmed detection time of the attack. |
| `:discovered` | `time` | The earliest known time when the attack was discovered. |
| `:discoverer` | `entity:actor` | The earliest known actor which discovered the attack. |
| `:id` | `base:id` | A unique ID given to the attack. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the attack. |
| `:name` | `base:name` | The primary name of the attack. |
| `:names` | `array of base:name` | A list of alternate names for the attack. |
| `:prev` | `risk:attack` | The previous/parent attack in a list or hierarchy. |
| `:published` | `time` | The time when the reporter published the attack. |
| `:reporter` | `entity:actor` | The entity which reported on the attack. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the attack. |
| `:resolved` | `risk:attack` | The authoritative attack which this reporting is about. |
| `:severity` | `meta:score` | A severity rank for the attack. |
| `:sophistication` | `meta:score` | The assessed sophistication of the attack. |
| `:success` | `bool` | Set if the attack was known to have succeeded or not. |
| `:superseded` | `time` | The time when the attack was superseded. |
| `:supersedes` | `array of risk:attack` | An array of attack nodes which are superseded by this attack. |
| `:time` | `time` | Set if the time of the attack is known. |
| `:type` | `risk:attack:type:taxonomy` | A type for the attack, as a taxonomy entry. |
| `:updated` | `time` | The time when the attack was last updated. |
| `:url` | `inet:url` | The URL for the attack. |

### `risk:attack:type:taxonomy`

A hierarchical taxonomy of attack types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:attack:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:availability`

A taxonomy of availability status values.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:availability` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:compromise`

A compromise and its aggregate impact. The compromise is the result of a successful attack.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |
| `meta:discoverable` |
| `meta:reported` |
| `risk:victimized` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this compromise. |
| `:actor` | `entity:actor` | The actor who carried out the compromise. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the compromise. |
| `:cost` | `econ:price` | The total cost of the compromise, response, and mitigation efforts. |
| `:created` | `time` | The time when the compromise was created. |
| `:desc` | `text` | A description of the compromise. |
| `:discovered` | `time` | The earliest known time when the compromise was discovered. |
| `:discoverer` | `entity:actor` | The earliest known actor which discovered the compromise. |
| `:id` | `base:id` | A unique ID given to the compromise. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the compromise. |
| `:loss:bytes` | `int` | An estimate of the volume of data compromised. |
| `:loss:life` | `int` | The total loss of life due to the compromise. |
| `:loss:pii` | `int` | The number of records compromised which contain PII. |
| `:name` | `base:name` | The primary name of the compromise. |
| `:names` | `array of base:name` | A list of alternate names for the compromise. |
| `:period` | `ival` | The period over which the compromise occurred. |
| `:published` | `time` | The time when the reporter published the compromise. |
| `:reporter` | `entity:actor` | The entity which reported on the compromise. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the compromise. |
| `:resolved` | `risk:compromise` | The authoritative compromise which this reporting is about. |
| `:severity` | `meta:score` | A severity rank for the compromise. |
| `:superseded` | `time` | The time when the compromise was superseded. |
| `:supersedes` | `array of risk:compromise` | An array of compromise nodes which are superseded by this compromise. |
| `:tag` | `syn:tag` | A tag used to associate nodes with the compromise. |
| `:type` | `risk:compromise:type:taxonomy` | A type for the compromise, as a taxonomy entry. |
| `:updated` | `time` | The time when the compromise was last updated. |
| `:url` | `inet:url` | The URL for the compromise. |
| `:vector` | `risk:attack` | The attack assessed to be the initial compromise vector. |
| `:victim` | `entity:actor` | The victim of the compromise. |
| `:victim:name` | `entity:name` | The name of the victim of the compromise. |

### `risk:compromise:type:taxonomy`

A hierarchical taxonomy of compromise types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:compromise:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:extortion`

Activity where an attacker attempted to extort a victim.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |
| `meta:negotiable` |
| `meta:reported` |
| `risk:victimized` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this extortion. |
| `:actor` | `entity:actor` | The actor who carried out the extortion. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the extortion. |
| `:compromise` | `risk:compromise` | The compromise which allowed the attacker to extort the target. |
| `:created` | `time` | The time when the extortion was created. |
| `:desc` | `text` | A description of the extortion. |
| `:enacted` | `bool` | Set to true if attacker carried out the threat. |
| `:id` | `base:id` | A unique ID given to the extortion. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the extortion. |
| `:name` | `base:name` | The primary name of the extortion. |
| `:names` | `array of base:name` | A list of alternate names for the extortion. |
| `:paid:price` | `econ:price` | The total price paid by the target of the extortion. |
| `:period` | `ival` | The period over which the extortion occurred. |
| `:public` | `bool` | Set to true if the attacker publicly announced the extortion. |
| `:public:url` | `inet:url` | The URL where the attacker publicly announced the extortion. |
| `:published` | `time` | The time when the reporter published the extortion. |
| `:reporter` | `entity:actor` | The entity which reported on the extortion. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the extortion. |
| `:resolved` | `risk:extortion` | The authoritative extortion which this reporting is about. |
| `:success` | `bool` | Set to true if the victim met the attacker's demands. |
| `:superseded` | `time` | The time when the extortion was superseded. |
| `:supersedes` | `array of risk:extortion` | An array of extortion nodes which are superseded by this extortion. |
| `:target` | `entity:actor` | The extortion target identity. |
| `:type` | `risk:extortion:type:taxonomy` | A type taxonomy for the extortion event. |
| `:updated` | `time` | The time when the extortion was last updated. |
| `:url` | `inet:url` | The URL for the extortion. |
| `:victim` | `entity:actor` | The victim of the extortion. |
| `:victim:name` | `entity:name` | The name of the victim of the extortion. |

### `risk:extortion:type:taxonomy`

A hierarchical taxonomy of extortion event types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:extortion:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:leak`

An event where information was disclosed without permission.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |
| `meta:reported` |
| `risk:victimized` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this leak. |
| `:actor` | `entity:actor` | The actor who carried out the leak. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the leak. |
| `:created` | `time` | The time when the leak was created. |
| `:desc` | `text` | A description of the leak. |
| `:id` | `base:id` | A unique ID given to the leak. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the leak. |
| `:name` | `base:name` | The primary name of the leak. |
| `:names` | `array of base:name` | A list of alternate names for the leak. |
| `:public` | `bool` | Set to true if the leaked information was made publicly available. |
| `:published` | `time` | The time when the reporter published the leak. |
| `:recipient` | `entity:actor` | The identity which received the leaked information. |
| `:reporter` | `entity:actor` | The entity which reported on the leak. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the leak. |
| `:resolved` | `risk:leak` | The authoritative leak which this reporting is about. |
| `:size:bytes` | `int` | The total size of the leaked data in bytes. |
| `:size:count` | `int` | The number of files included in the leaked data. |
| `:size:percent` | `int` | The total percent of the data leaked. |
| `:superseded` | `time` | The time when the leak was superseded. |
| `:supersedes` | `array of risk:leak` | An array of leak nodes which are superseded by this leak. |
| `:time` | `time` | The time that the leak occurred. |
| `:type` | `risk:leak:type:taxonomy` | A type taxonomy for the leak. |
| `:updated` | `time` | The time when the leak was last updated. |
| `:url` | `inet:url` | The URL for the leak. |
| `:urls` | `array of inet:url` | URLs where the leaked information was made available. |
| `:victim` | `entity:actor` | The victim of the leak. |
| `:victim:name` | `entity:name` | The name of the victim of the leak. |

### `risk:leak:type:taxonomy`

A hierarchical taxonomy of leak event types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:leak:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:mitigation`

A mitigation for a specific vulnerability or technique.

| Interface |
|-----------|
| `meta:observable` |
| `meta:reported` |
| `meta:usable` |
| `risk:mitigatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time when the mitigation was created. |
| `:desc` | `text` | A description of the mitigation. |
| `:id` | `base:id` | A unique ID given to the mitigation. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the mitigation. |
| `:name` | `base:name` | The primary name of the mitigation. |
| `:names` | `array of base:name` | A list of alternate names for the mitigation. |
| `:parent` | `meta:technique` | The parent technique for the technique. |
| `:published` | `time` | The time when the reporter published the mitigation. |
| `:reporter` | `entity:actor` | The entity which reported on the mitigation. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the mitigation. |
| `:resolved` | `risk:mitigation` | The authoritative mitigation which this reporting is about. |
| `:seen` | `ival` | The mitigation was observed during the time interval. |
| `:sophistication` | `meta:score` | The assessed sophistication of the technique. |
| `:superseded` | `time` | The time when the mitigation was superseded. |
| `:supersedes` | `array of risk:mitigation` | An array of mitigation nodes which are superseded by this mitigation. |
| `:tag` | `syn:tag` | The tag used to annotate nodes where the technique was employed. |
| `:type` | `meta:technique:type:taxonomy` | The taxonomy classification of the technique. |
| `:updated` | `time` | The time when the mitigation was last updated. |
| `:url` | `inet:url` | The URL for the mitigation. |

### `risk:outage`

An outage event which affected resource availability.

| Interface |
|-----------|
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:attack` | `risk:attack` | An attack which caused the outage. |
| `:cause` | `risk:outage:cause:taxonomy` | The outage cause type. |
| `:created` | `time` | The time when the outage was created. |
| `:desc` | `text` | A description of the outage. |
| `:id` | `base:id` | A unique ID given to the outage. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the outage. |
| `:name` | `base:name` | The primary name of the outage. |
| `:names` | `array of base:name` | A list of alternate names for the outage. |
| `:period` | `ival` | The time period where the outage impacted availability. |
| `:provider` | `ou:org` | The organization which experienced the outage event. |
| `:provider:name` | `entity:name` | The name of the organization which experienced the outage event. |
| `:published` | `time` | The time when the reporter published the outage. |
| `:reporter` | `entity:actor` | The entity which reported on the outage. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the outage. |
| `:resolved` | `risk:outage` | The authoritative outage which this reporting is about. |
| `:superseded` | `time` | The time when the outage was superseded. |
| `:supersedes` | `array of risk:outage` | An array of outage nodes which are superseded by this outage. |
| `:type` | `risk:outage:type:taxonomy` | The type of outage. |
| `:updated` | `time` | The time when the outage was last updated. |
| `:url` | `inet:url` | The URL for the outage. |

### `risk:outage:cause:taxonomy`

An outage cause taxonomy.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:outage:cause:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:outage:type:taxonomy`

An outage type taxonomy.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:outage:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:theft`

An event where an actor stole from a victim.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |
| `meta:reported` |
| `risk:victimized` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this theft. |
| `:actor` | `entity:actor` | The actor who carried out the theft. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the theft. |
| `:created` | `time` | The time when the theft was created. |
| `:desc` | `text` | A description of the theft. |
| `:id` | `base:id` | A unique ID given to the theft. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the theft. |
| `:name` | `base:name` | The primary name of the theft. |
| `:names` | `array of base:name` | A list of alternate names for the theft. |
| `:published` | `time` | The time when the reporter published the theft. |
| `:reporter` | `entity:actor` | The entity which reported on the theft. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the theft. |
| `:resolved` | `risk:theft` | The authoritative theft which this reporting is about. |
| `:superseded` | `time` | The time when the theft was superseded. |
| `:supersedes` | `array of risk:theft` | An array of theft nodes which are superseded by this theft. |
| `:time` | `time` | The time that the theft occurred. |
| `:updated` | `time` | The time when the theft was last updated. |
| `:url` | `inet:url` | The URL for the theft. |
| `:value` | `econ:price` | The total value of the stolen items. |
| `:victim` | `entity:actor` | The victim of the theft. |
| `:victim:name` | `entity:name` | The name of the victim of the theft. |

### `risk:threat`

A threat cluster or subgraph of threat activity, as defined by a specific source.

| Interface |
|-----------|
| `entity:actor` |
| `entity:contactable` |
| `entity:resolvable` |
| `geo:locatable` |
| `meta:discoverable` |
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:active` | `ival` | An interval for when the threat cluster is assessed to have been active. |
| `:activity` | `meta:score` | The most recently assessed activity level of the threat cluster. |
| `:banner` | `file:bytes` | A banner or hero image used on the profile page. |
| `:bio` | `text` | A tagline or bio provided for the threat. |
| `:created` | `time` | The time when the threat was created. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the threat. |
| `:desc` | `text` | A description of the threat. |
| `:discovered` | `time` | The earliest known time when the threat was discovered. |
| `:discoverer` | `entity:actor` | The earliest known actor which discovered the threat. |
| `:email` | `inet:email` | The primary email address for the threat. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the threat. |
| `:id` | `base:id` | A unique ID given to the threat. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the threat. |
| `:lang` | `lang:language` | The primary language of the threat. |
| `:langs` | `array of lang:language` | An array of alternate languages for the threat. |
| `:lifespan` | `ival` | The lifespan of the threat. |
| `:name` | `entity:name` | The primary name of the threat according to the source. |
| `:names` | `array of entity:name` | A list of alternate names for the threat according to the source. |
| `:phone` | `tel:phone` | The primary phone number for the threat. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the threat. |
| `:photo` | `file:bytes` | The profile picture or avatar for this threat. |
| `:place` | `geo:place` | The place where the threat was located. |
| `:place:address` | `geo:address` | The postal address where the threat was located. |
| `:place:address:city` | `base:name` | The city where the threat was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the threat was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the threat was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the threat was located. |
| `:place:country` | `pol:country` | The country where the threat was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the threat was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the threat was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the threat was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the threat was located. |
| `:place:loc` | `loc` | The geopolitical location where the threat was located. |
| `:place:name` | `geo:name` | The name where the threat was located. |
| `:published` | `time` | The time when the reporter published the threat. |
| `:reporter` | `entity:actor` | The entity which reported on the threat. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the threat. |
| `:resolved` | `risk:threat` | The authoritative threat which this reporting is about. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the threat. |
| `:sophistication` | `meta:score` | The sources's assessed sophistication of the threat cluster. |
| `:superseded` | `time` | The time when the threat was superseded. |
| `:supersedes` | `array of risk:threat` | An array of threat nodes which are superseded by this threat. |
| `:tag` | `syn:tag` | The tag used to annotate nodes that are associated with the threat cluster. |
| `:type` | `risk:threat:type:taxonomy` | A type for the threat, as a taxonomy entry. |
| `:updated` | `time` | The time when the threat was last updated. |
| `:url` | `inet:url` | The URL for the threat. |
| `:user` | `inet:user` | The primary user name for the threat. |
| `:users` | `array of inet:user` | An array of alternate user names for the threat. |
| `:websites` | `array of inet:url` | Web sites listed for the threat. |

### `risk:threat:type:taxonomy`

A hierarchical taxonomy of threat types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:threat:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:tool:software`

A software tool used in threat activity, as defined by a specific source.

| Interface |
|-----------|
| `meta:observable` |
| `meta:reported` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:availability` | `risk:availability` | The source's assessed availability of the tool. |
| `:created` | `time` | The time when the tool was created. |
| `:desc` | `text` | A description of the tool. |
| `:id` | `base:id` | A unique ID given to the tool. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the tool. |
| `:name` | `it:softwarename` | The primary name of the tool according to the source. |
| `:names` | `array of it:softwarename` | A list of alternate names for the tool according to the source. |
| `:published` | `time` | The time when the reporter published the tool. |
| `:reporter` | `entity:actor` | The entity which reported on the tool. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the tool. |
| `:resolved` | `risk:tool:software` | The authoritative tool which this reporting is about. |
| `:seen` | `ival` | The tool was observed during the time interval. |
| `:software` | `it:software` | The authoritative software family for the tool. |
| `:sophistication` | `meta:score` | The source's assessed sophistication of the tool. |
| `:superseded` | `time` | The time when the tool was superseded. |
| `:supersedes` | `array of risk:tool:software` | An array of tool nodes which are superseded by this tool. |
| `:tag` | `syn:tag` | The tag used to annotate nodes that are associated with the tool. |
| `:type` | `risk:tool:software:type:taxonomy` | A type for the tool, as a taxonomy entry. |
| `:updated` | `time` | The time when the tool was last updated. |
| `:url` | `inet:url` | The URL for the tool. |

### `risk:tool:software:type:taxonomy`

A hierarchical taxonomy of software tool types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:tool:software:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:vuln`

A unique vulnerability.

| Interface |
|-----------|
| `meta:discoverable` |
| `meta:observable` |
| `meta:reported` |
| `meta:usable` |
| `risk:mitigatable` |
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time when the vulnerability was created. |
| `:cvss:v2` | `it:sec:cvss:v2` | The CVSS v2 vector for the vulnerability. |
| `:cvss:v2_0:score` | `float` | The CVSS v2.0 overall score for the vulnerability. |
| `:cvss:v3` | `it:sec:cvss:v3` | The CVSS v3 vector for the vulnerability. |
| `:cvss:v3_0:score` | `float` | The CVSS v3.0 overall score for the vulnerability. |
| `:cvss:v3_1:score` | `float` | The CVSS v3.1 overall score for the vulnerability. |
| `:cwes` | `array of it:sec:cwe` | MITRE CWE values that apply to the vulnerability. |
| `:desc` | `text` | A description of the vulnerability. |
| `:discovered` | `time` | The earliest known time when the vulnerability was discovered. |
| `:discoverer` | `entity:actor` | The earliest known actor which discovered the vulnerability. |
| `:exploited` | `time` | The earliest known time when the vulnerability was exploited in the wild. |
| `:id` | `risk:vuln:id` | A unique ID given to the vulnerability. |
| `:ids` | `array of risk:vuln:id` | An array of alternate IDs given to the vulnerability. |
| `:mitigated` | `bool` | Set to true if a mitigation/fix is available for the vulnerability. |
| `:name` | `base:name` | The primary name of the vulnerability. |
| `:names` | `array of base:name` | A list of alternate names for the vulnerability. |
| `:priority` | `meta:score` | The priority of the vulnerability. |
| `:published` | `time` | The earliest known time the vulnerability was published. |
| `:reporter` | `entity:actor` | The entity which reported on the vulnerability. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the vulnerability. |
| `:resolved` | `risk:vuln` | The authoritative vulnerability which this reporting is about. |
| `:seen` | `ival` | The vulnerability was observed during the time interval. |
| `:severity` | `meta:score` | The severity of the vulnerability. |
| `:superseded` | `time` | The time when the vulnerability was superseded. |
| `:supersedes` | `array of risk:vuln` | An array of vulnerability nodes which are superseded by this vulnerability. |
| `:tag` | `syn:tag` | A tag used to annotate the presence or use of the vulnerability. |
| `:type` | `risk:vuln:type:taxonomy` | A taxonomy type entry for the vulnerability. |
| `:updated` | `time` | The time when the vulnerability was last updated. |
| `:url` | `inet:url` | The URL for the vulnerability. |
| `:vendor` | `entity:actor` | The vendor whose product contains the vulnerability. |
| `:vendor:fixed` | `time` | The earliest known time the vendor issued a fix for the vulnerability. |
| `:vendor:name` | `entity:name` | The name of the vendor whose product contains the vulnerability. |
| `:vendor:notified` | `time` | The earliest known vendor notification time for the vulnerability. |

### `risk:vuln:type:taxonomy`

A hierarchical taxonomy of vulnerability types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `risk:vuln:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `risk:vulnerable`

Indicates that a node is susceptible to a vulnerability.

| Property | Type | Doc |
|----------|------|-----|
| `:mitigated` | `bool` | Set to true if the vulnerable node has been mitigated. |
| `:mitigations` | `array of meta:technique` | The mitigations which were used to address the vulnerable node. |
| `:node` | `risk:exploitable` | The node which is vulnerable. |
| `:period` | `ival` | The time window where the node was vulnerable. |
| `:to` | `risk:mitigatable` | The thing which the node is vulnerable to. |

### `sci:evidence`

An assessment of how an observation supports or refutes a hypothesis.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of how the observation supports or refutes the hypothesis. |
| `:hypothesis` | `sci:hypothesis` | The hypothesis which the evidence supports or refutes. |
| `:observation` | `sci:observation` | The observation which supports or refutes the hypothesis. |
| `:refutes` | `bool` | Set to true if the evidence refutes the hypothesis or false if it supports the hypothesis. |

### `sci:experiment`

An instance of running an experiment.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this activity. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:desc` | `text` | A description of the experiment. |
| `:name` | `base:name` | The name of the experiment. |
| `:period` | `ival` | The time period when the experiment was run. |
| `:type` | `sci:experiment:type:taxonomy` | The type of experiment as a user defined taxonomy. |

### `sci:experiment:type:taxonomy`

A taxonomy of experiment types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `sci:experiment:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `sci:hypothesis`

A hypothesis or theory.

| Interface |
|-----------|
| `meta:believable` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the hypothesis. |
| `:name` | `base:name` | The name of the hypothesis. |
| `:type` | `sci:hypothesis:type:taxonomy` | The type of hypothesis as a user defined taxonomy. |

### `sci:hypothesis:type:taxonomy`

A taxonomy of hypothesis types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `sci:hypothesis:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `sci:observation`

An observation which may have resulted from an experiment.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:desc` | `text` | A description of the observation. |
| `:experiment` | `sci:experiment` | The experiment which produced the observation. |
| `:time` | `time` | The time that the observation occurred. |

### `syn:cmd`

A Synapse storm command.

| Property | Type | Doc |
|----------|------|-----|
| `:deprecated` | `bool` | Set to true if this command is scheduled to be removed. |
| `:deprecated:date` | `time` | The date when this command will be removed. |
| `:deprecated:mesg` | `str` | Optional description of this deprecation. |
| `:deprecated:version` | `it:version` | The Synapse version when this command will be removed. |
| `:doc` | `text` | Description of the command. |
| `:package` | `str` | Storm package which provided the command. |
| `:svciden` | `guid` | Storm service iden which provided the package. |

### `syn:deleted`

A node present below the write layer which has been deleted.

| Property | Type | Doc |
|----------|------|-----|
| `:form` | `str` | The form for the node that was deleted. |
| `:nid` | `int` | The nid for the node that was deleted. |
| `:sodes` | `data` | The layer storage nodes for the node that was deleted. |
| `:value` | `data` | The primary property value for the node that was deleted. |

### `syn:form`

A Synapse form used for representing nodes in the graph.

| Property | Type | Doc |
|----------|------|-----|
| `:doc` | `str` | The docstring for the form. |
| `:runt` | `bool` | Whether or not the form is runtime only. |
| `:type` | `syn:type` | Synapse type for this form. |

### `syn:prop`

A Synapse property.

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `str` | Base name of the property. |
| `:computed` | `bool` | If the property is dynamically computed from other property values. |
| `:doc` | `str` | Description of the property definition. |
| `:extmodel` | `bool` | If the property is an extended model property or not. |
| `:form` | `syn:form` | The form of the property. |
| `:relname` | `str` | Relative property name. |
| `:type` | `syn:type` | The synapse type for this property. |
| `:univ` | `bool` | Specifies if a prop is universal. |

### `syn:tag`

The base type for a synapse tag.

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `str` | The tag base name. Eg baz for foo.bar.baz . |
| `:depth` | `int` | How deep the tag is in the hierarchy. |
| `:doc` | `text` | A short definition for the tag. |
| `:doc:url` | `inet:url` | A URL link to additional documentation about the tag. |
| `:isnow` | `syn:tag` | Set to an updated tag if the tag has been renamed. |
| `:title` | `str` | A display title for the tag. |
| `:up` | `syn:tag` | The parent tag for the tag. |

### `syn:tagprop`

A user defined tag property.

| Property | Type | Doc |
|----------|------|-----|
| `:doc` | `str` | Description of the tagprop definition. |
| `:type` | `syn:type` | The synapse type for this tagprop. |

### `syn:type`

A Synapse type used for normalizing nodes and properties.

| Property | Type | Doc |
|----------|------|-----|
| `:ctor` | `str` | The python ctor path for the type object. |
| `:doc` | `str` | The docstring for the type. |
| `:opts` | `data` | Arbitrary type options. |
| `:subof` | `syn:type` | Type which this inherits from. |

### `syn:user`

A Synapse user.

| Interface |
|-----------|
| `entity:actor` |

### `tel:call`

A telephone call.

| Interface |
|-----------|
| `lang:transcript` |

| Property | Type | Doc |
|----------|------|-----|
| `:caller` | `entity:actor` | The entity which placed the call. |
| `:caller:phone` | `tel:phone` | The phone number the caller placed the call from. |
| `:connected` | `bool` | Indicator of whether the call was connected. |
| `:period` | `ival` | The time period when the call took place. |
| `:recipient` | `entity:actor` | The entity which received the call. |
| `:recipient:phone` | `tel:phone` | The phone number the caller placed the call to. |

### `tel:mob:carrier`

The fusion of a MCC/MNC.

| Interface |
|-----------|
| `entity:identifier` |

| Property | Type | Doc |
|----------|------|-----|
| `:mcc` | `tel:mob:mcc` | The Mobile Country Code. |
| `:mnc` | `tel:mob:mnc` | The Mobile Network Code. |

### `tel:mob:cell`

A mobile cell site which a phone may connect to.

| Interface |
|-----------|
| `geo:locatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:carrier` | `tel:mob:carrier` | Mobile carrier which registered the cell tower. |
| `:cid` | `int` | The Cell ID. |
| `:lac` | `int` | Location Area Code. LTE networks may call this a TAC. |
| `:place` | `geo:place` | The place where the cell tower was located. |
| `:place:address` | `geo:address` | The postal address where the cell tower was located. |
| `:place:address:city` | `base:name` | The city where the cell tower was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the cell tower was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the cell tower was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the cell tower was located. |
| `:place:country` | `pol:country` | The country where the cell tower was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the cell tower was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the cell tower was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the cell tower was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the cell tower was located. |
| `:place:loc` | `loc` | The geopolitical location where the cell tower was located. |
| `:place:name` | `geo:name` | The name where the cell tower was located. |
| `:radio` | `tel:mob:cell:radio:type:taxonomy` | Cell radio type. |

### `tel:mob:cell:radio:type:taxonomy`

A hierarchical taxonomy of cell radio types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `tel:mob:cell:radio:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `tel:mob:imei`

An International Mobile Equipment Id.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The IMEI was observed during the time interval. |
| `:serial` | `int` | The serial number within the IMEI. |
| `:tac` | `tel:mob:tac` | The Type Allocate Code within the IMEI. |

### `tel:mob:imid`

Fused knowledge of an IMEI/IMSI used together.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:imei` | `tel:mob:imei` | The IMEI for the phone hardware. |
| `:imsi` | `tel:mob:imsi` | The IMSI for the phone subscriber. |
| `:seen` | `ival` | The IMEI and IMSI was observed during the time interval. |

### `tel:mob:imsi`

An International Mobile Subscriber Id.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:mcc` | `tel:mob:mcc` | The Mobile Country Code. |
| `:seen` | `ival` | The IMSI was observed during the time interval. |

### `tel:mob:imsiphone`

Fused knowledge of an IMSI assigned phone number.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:imsi` | `tel:mob:imsi` | The IMSI with the assigned phone number. |
| `:phone` | `tel:phone` | The phone number assigned to the IMSI. |
| `:seen` | `ival` | The IMSI and phone number was observed during the time interval. |

### `tel:mob:mcc`

ITU Mobile Country Code.

| Property | Type | Doc |
|----------|------|-----|
| `:place:country:code` | `iso:3166:alpha2` | The country code which the MCC is assigned to. |

### `tel:mob:tac`

A mobile Type Allocation Code.

| Interface |
|-----------|
| `meta:havable` |

| Property | Type | Doc |
|----------|------|-----|
| `:model` | `biz:model` | The TAC model name. |
| `:owner` | `entity:actor` | The current owner of the item. |
| `:owner:name` | `entity:name` | The name of the current owner of the item. |

### `tel:mob:tadig`

A Transferred Account Data Interchange Group number issued to a GSM carrier.

| Interface |
|-----------|
| `entity:identifier` |

### `tel:mob:telem`

A single mobile telemetry measurement.

| Interface |
|-----------|
| `geo:locatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account` | The service account which is associated with the tracked device. |
| `:adid` | `it:adid` | The advertising ID of the mobile telemetry sample. |
| `:app` | `it:software` | The app used to report the mobile telemetry sample. |
| `:cell` | `tel:mob:cell` | The mobile cell site where the telemetry sample was taken. |
| `:email` | `inet:email` | The email address associated with the mobile telemetry sample. |
| `:host` | `it:host` | The host that generated the mobile telemetry data. |
| `:http:request` | `inet:http:request` | The HTTP request that the telemetry was extracted from. |
| `:imei` | `tel:mob:imei` | The IMEI of the device associated with the mobile telemetry sample. |
| `:imsi` | `tel:mob:imsi` | The IMSI of the device associated with the mobile telemetry sample. |
| `:ip` | `inet:ip` | The IP address of the device associated with the mobile telemetry sample. |
| `:mac` | `inet:mac` | The MAC address of the device associated with the mobile telemetry sample. |
| `:name` | `entity:name` | The user name associated with the mobile telemetry sample. |
| `:phone` | `tel:phone` | The phone number of the device associated with the mobile telemetry sample. |
| `:place` | `geo:place` | The place where the telemetry sample was located. |
| `:place:address` | `geo:address` | The postal address where the telemetry sample was located. |
| `:place:address:city` | `base:name` | The city where the telemetry sample was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the telemetry sample was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the telemetry sample was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the telemetry sample was located. |
| `:place:country` | `pol:country` | The country where the telemetry sample was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the telemetry sample was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the telemetry sample was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the telemetry sample was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the telemetry sample was located. |
| `:place:loc` | `loc` | The geopolitical location where the telemetry sample was located. |
| `:place:name` | `geo:name` | The name where the telemetry sample was located. |
| `:time` | `time` | The time that the telemetry sample was taken. |
| `:wifi:ap` | `inet:wifi:ap` | The Wi-Fi AP associated with the mobile telemetry sample. |

### `tel:phone`

A phone number.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:loc` | `loc` | The location associated with the number. |
| `:seen` | `ival` | The phone number was observed during the time interval. |
| `:type` | `tel:phone:type:taxonomy` | The type of phone number. |

### `tel:phone:type:taxonomy`

A taxonomy of phone number types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `tel:phone:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `transport:air:craft`

An individual aircraft.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |
| `transport:vehicle` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the aircraft was created. |
| `:creator` | `entity:actor` | The primary actor which created the aircraft. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the aircraft. |
| `:max:cargo:mass` | `mass` | The maximum mass the aircraft can carry as cargo. |
| `:max:cargo:volume` | `geo:dist` | The maximum volume the aircraft can carry as cargo. |
| `:max:occupants` | `int:min0` | The maximum number of occupants the aircraft can hold. |
| `:model` | `biz:model` | The model of the aircraft. |
| `:name` | `base:name` | The name of the aircraft. |
| `:operator` | `entity:actor` | The contact information of the operator of the aircraft. |
| `:owner` | `entity:actor` | The current owner of the aircraft. |
| `:owner:name` | `entity:name` | The name of the current owner of the aircraft. |
| `:phys:height` | `geo:dist` | The physical height of the aircraft. |
| `:phys:length` | `geo:dist` | The physical length of the aircraft. |
| `:phys:mass` | `mass` | The physical mass of the aircraft. |
| `:phys:volume` | `geo:dist` | The physical volume of the aircraft. |
| `:phys:width` | `geo:dist` | The physical width of the aircraft. |
| `:place` | `geo:place` | The place where the aircraft was located. |
| `:place:address` | `geo:address` | The postal address where the aircraft was located. |
| `:place:address:city` | `base:name` | The city where the aircraft was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the aircraft was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the aircraft was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the aircraft was located. |
| `:place:country` | `pol:country` | The country where the aircraft was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the aircraft was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the aircraft was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the aircraft was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the aircraft was located. |
| `:place:loc` | `loc` | The geopolitical location where the aircraft was located. |
| `:place:name` | `geo:name` | The name where the aircraft was located. |
| `:serial` | `base:id` | The manufacturer assigned serial number of the aircraft. |
| `:tailnum` | `transport:air:tailnum` | The aircraft tail number. |
| `:type` | `transport:air:craft:type:taxonomy` | The type of aircraft. |

### `transport:air:craft:type:taxonomy`

A hierarchical taxonomy of aircraft types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `transport:air:craft:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `transport:air:flight`

An individual instance of a flight.

| Interface |
|-----------|
| `transport:schedule` |
| `transport:trip` |

| Property | Type | Doc |
|----------|------|-----|
| `:arrived` | `time` | The actual arrival time. |
| `:arrived:place` | `geo:place` | The actual arrival place. |
| `:arrived:point` | `transport:point` | The actual arrival point. |
| `:cargo:mass` | `mass` | The cargo mass carried by the aircraft on this flight. |
| `:cargo:volume` | `geo:dist` | The cargo volume carried by the aircraft on this flight. |
| `:departed` | `time` | The actual departure time. |
| `:departed:place` | `geo:place` | The actual departure place. |
| `:departed:point` | `transport:point` | The actual departure point. |
| `:duration` | `duration` | The actual duration. |
| `:num` | `transport:air:flightnum` | The flight number of this flight. |
| `:occupants` | `int:min0` | The number of occupants of the aircraft on this flight. |
| `:operator` | `entity:actor` | The contact information of the operator of the flight. |
| `:scheduled:arrival` | `time` | The scheduled arrival time. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival place. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival point. |
| `:scheduled:departure` | `time` | The scheduled departure time. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure place. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure point. |
| `:scheduled:duration` | `duration` | The scheduled duration. |
| `:status` | `transport:trip:status` | The status of the flight. |
| `:tailnum` | `transport:air:tailnum` | The tail/registration number at the time the aircraft flew this flight. |
| `:vehicle` | `transport:vehicle` | The aircraft which traveled the flight. |

### `transport:air:flightnum`

A commercial flight designator including airline and serial.

| Property | Type | Doc |
|----------|------|-----|
| `:carrier` | `ou:org` | The org which operates the given flight number. |
| `:from:port` | `transport:air:port` | The most recently registered origin for the flight number. |
| `:stops` | `array of transport:air:port` | An ordered list of aiport codes for the flight segments. |
| `:to:port` | `transport:air:port` | The most recently registered destination for the flight number. |

### `transport:air:port`

An IATA assigned airport code.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `geo:name` | The name of the airport. |
| `:place` | `geo:place` | The place where the IATA airport code is assigned. |

### `transport:air:tailnum`

An aircraft registration number or military aircraft serial number.

| Property | Type | Doc |
|----------|------|-----|
| `:loc` | `loc` | The geopolitical location that the tailnumber is allocated to. |
| `:type` | `transport:air:tailnum:type:taxonomy` | A type which may be specific to the country prefix. |

### `transport:air:tailnum:type:taxonomy`

A hierarchical taxonomy of aircraft registration number types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `transport:air:tailnum:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `transport:air:telem`

A telemetry sample from an aircraft in transit.

| Interface |
|-----------|
| `geo:locatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:airspeed` | `velocity` | The air speed of the aircraft at the time. |
| `:course` | `transport:direction` | The direction, in degrees from true North, that the aircraft is traveling. |
| `:flight` | `transport:air:flight` | The flight being measured. |
| `:heading` | `transport:direction` | The direction, in degrees from true North, that the nose of the aircraft is pointed. |
| `:place` | `geo:place` | The place where the telemetry sample was located. |
| `:place:address` | `geo:address` | The postal address where the telemetry sample was located. |
| `:place:address:city` | `base:name` | The city where the telemetry sample was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the telemetry sample was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the telemetry sample was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the telemetry sample was located. |
| `:place:country` | `pol:country` | The country where the telemetry sample was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the telemetry sample was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the telemetry sample was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the telemetry sample was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the telemetry sample was located. |
| `:place:loc` | `loc` | The geopolitical location where the telemetry sample was located. |
| `:place:name` | `geo:name` | The name where the telemetry sample was located. |
| `:speed` | `velocity` | The ground speed of the aircraft at the time. |
| `:time` | `time` | The time the telemetry sample was taken. |
| `:verticalspeed` | `velocity:relative` | The relative vertical speed of the aircraft at the time. |

### `transport:cargo`

Cargo being carried by a vehicle on a trip.

| Property | Type | Doc |
|----------|------|-----|
| `:container` | `transport:container` | The container in which the cargo was shipped. |
| `:loaded:place` | `geo:place` | The place where the cargo was loaded. |
| `:loaded:point` | `transport:point` | The point where the cargo was loaded such as an airport gate or train platform. |
| `:object` | `phys:object` | The physical object being transported. |
| `:period` | `ival` | The period when the cargo was loaded in the vehicle. |
| `:trip` | `transport:trip` | The trip being taken by the cargo. |
| `:unloaded:place` | `geo:place` | The place where the cargo was unloaded. |
| `:unloaded:point` | `transport:point` | The point where the cargo was unloaded such as an airport gate or train platform. |
| `:vehicle` | `transport:vehicle` | The vehicle used to transport the cargo. |

### `transport:land:drive`

A drive taken by a land vehicle.

| Interface |
|-----------|
| `transport:schedule` |
| `transport:trip` |

| Property | Type | Doc |
|----------|------|-----|
| `:arrived` | `time` | The actual arrival time. |
| `:arrived:place` | `geo:place` | The actual arrival place. |
| `:arrived:point` | `transport:point` | The actual arrival point. |
| `:cargo:mass` | `mass` | The cargo mass carried by the vehicle on this drive. |
| `:cargo:volume` | `geo:dist` | The cargo volume carried by the vehicle on this drive. |
| `:departed` | `time` | The actual departure time. |
| `:departed:place` | `geo:place` | The actual departure place. |
| `:departed:point` | `transport:point` | The actual departure point. |
| `:duration` | `duration` | The actual duration. |
| `:occupants` | `int:min0` | The number of occupants of the vehicle on this drive. |
| `:operator` | `entity:actor` | The contact information of the operator of the drive. |
| `:scheduled:arrival` | `time` | The scheduled arrival time. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival place. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival point. |
| `:scheduled:departure` | `time` | The scheduled departure time. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure place. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure point. |
| `:scheduled:duration` | `duration` | The scheduled duration. |
| `:status` | `transport:trip:status` | The status of the drive. |
| `:vehicle` | `transport:vehicle` | The vehicle which traveled the drive. |

### `transport:land:license`

A license to operate a land vehicle issued to a contact.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:actor` | The contact info of the licensee. |
| `:expires` | `time` | The time the license expires. |
| `:id` | `base:id` | The license ID. |
| `:issued` | `time` | The time the license was issued. |
| `:issuer` | `ou:org` | The org which issued the license. |
| `:issuer:name` | `entity:name` | The name of the org which issued the license. |

### `transport:land:registration`

Registration issued to a contact for a land vehicle.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:actor` | The contact info of the registrant. |
| `:expires` | `time` | The time the vehicle registration expires. |
| `:id` | `base:id` | The vehicle registration ID or license plate. |
| `:issued` | `time` | The time the vehicle registration was issued. |
| `:issuer` | `ou:org` | The org which issued the registration. |
| `:issuer:name` | `entity:name` | The name of the org which issued the registration. |
| `:license` | `transport:land:license` | The license used to register the vehicle. |
| `:vehicle` | `transport:land:vehicle` | The vehicle being registered. |

### `transport:land:vehicle`

An individual land based vehicle.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |
| `transport:vehicle` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the vehicle was created. |
| `:creator` | `entity:actor` | The primary actor which created the vehicle. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the vehicle. |
| `:desc` | `str` | A description of the vehicle. |
| `:max:cargo:mass` | `mass` | The maximum mass the vehicle can carry as cargo. |
| `:max:cargo:volume` | `geo:dist` | The maximum volume the vehicle can carry as cargo. |
| `:max:occupants` | `int:min0` | The maximum number of occupants the vehicle can hold. |
| `:model` | `biz:model` | The model of the vehicle. |
| `:name` | `base:name` | The name of the vehicle. |
| `:operator` | `entity:actor` | The contact information of the operator of the vehicle. |
| `:owner` | `entity:actor` | The current owner of the vehicle. |
| `:owner:name` | `entity:name` | The name of the current owner of the vehicle. |
| `:phys:height` | `geo:dist` | The physical height of the vehicle. |
| `:phys:length` | `geo:dist` | The physical length of the vehicle. |
| `:phys:mass` | `mass` | The physical mass of the vehicle. |
| `:phys:volume` | `geo:dist` | The physical volume of the vehicle. |
| `:phys:width` | `geo:dist` | The physical width of the vehicle. |
| `:place` | `geo:place` | The place where the vehicle was located. |
| `:place:address` | `geo:address` | The postal address where the vehicle was located. |
| `:place:address:city` | `base:name` | The city where the vehicle was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the vehicle was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the vehicle was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the vehicle was located. |
| `:place:country` | `pol:country` | The country where the vehicle was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the vehicle was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the vehicle was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the vehicle was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the vehicle was located. |
| `:place:loc` | `loc` | The geopolitical location where the vehicle was located. |
| `:place:name` | `geo:name` | The name where the vehicle was located. |
| `:registration` | `transport:land:registration` | The current vehicle registration information. |
| `:serial` | `str` | The serial number or VIN of the vehicle. |
| `:type` | `transport:land:vehicle:type:taxonomy` | The type of land vehicle. |

### `transport:land:vehicle:type:taxonomy`

A type taxonomy for land vehicles.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `transport:land:vehicle:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `transport:occupant`

An occupant of a vehicle on a trip.

| Property | Type | Doc |
|----------|------|-----|
| `:boarded:place` | `geo:place` | The place where the occupant boarded the vehicle. |
| `:boarded:point` | `transport:point` | The boarding point such as an airport gate or train platform. |
| `:contact` | `entity:individual` | Contact information of the occupant. |
| `:disembarked:place` | `geo:place` | The place where the occupant disembarked the vehicle. |
| `:disembarked:point` | `transport:point` | The disembarkation point such as an airport gate or train platform. |
| `:period` | `ival` | The period when the occupant was aboard the vehicle. |
| `:role` | `transport:occupant:role:taxonomy` | The role of the occupant such as captain, crew, passenger. |
| `:seat` | `str` | The seat which the occupant sat in. Likely in a vehicle specific format. |
| `:trip` | `transport:trip` | The trip, such as a flight or train ride, being taken by the occupant. |
| `:vehicle` | `transport:vehicle` | The vehicle that transported the occupant. |

### `transport:occupant:role:taxonomy`

A taxonomy of transportation occupant roles.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `transport:occupant:role:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `transport:rail:car`

An individual train car.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the train car was created. |
| `:creator` | `entity:actor` | The primary actor which created the train car. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the train car. |
| `:max:cargo:mass` | `mass` | The maximum mass the train car can carry as cargo. |
| `:max:cargo:volume` | `geo:dist` | The maximum volume the train car can carry as cargo. |
| `:max:occupants` | `int:min0` | The maximum number of occupants the train car can hold. |
| `:model` | `biz:model` | The model of the train car. |
| `:name` | `base:name` | The name of the train car. |
| `:owner` | `entity:actor` | The current owner of the train car. |
| `:owner:name` | `entity:name` | The name of the current owner of the train car. |
| `:phys:height` | `geo:dist` | The physical height of the train car. |
| `:phys:length` | `geo:dist` | The physical length of the train car. |
| `:phys:mass` | `mass` | The physical mass of the train car. |
| `:phys:volume` | `geo:dist` | The physical volume of the train car. |
| `:phys:width` | `geo:dist` | The physical width of the train car. |
| `:place` | `geo:place` | The place where the train car was located. |
| `:place:address` | `geo:address` | The postal address where the train car was located. |
| `:place:address:city` | `base:name` | The city where the train car was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the train car was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the train car was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the train car was located. |
| `:place:country` | `pol:country` | The country where the train car was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the train car was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the train car was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the train car was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the train car was located. |
| `:place:loc` | `loc` | The geopolitical location where the train car was located. |
| `:place:name` | `geo:name` | The name where the train car was located. |
| `:serial` | `base:id` | The manufacturer assigned serial number of the train car. |
| `:type` | `transport:rail:car:type:taxonomy` | The type of rail car. |

### `transport:rail:car:type:taxonomy`

A hierarchical taxonomy of rail car types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `transport:rail:car:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `transport:rail:consist`

A group of rail cars and locomotives connected together.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |
| `transport:vehicle` |

| Property | Type | Doc |
|----------|------|-----|
| `:cars` | `array of transport:rail:car` | The rail cars, including locomotives, which compose the consist. |
| `:created` | `time` | The time that the train was created. |
| `:creator` | `entity:actor` | The primary actor which created the train. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the train. |
| `:max:cargo:mass` | `mass` | The maximum mass the train can carry as cargo. |
| `:max:cargo:volume` | `geo:dist` | The maximum volume the train can carry as cargo. |
| `:max:occupants` | `int:min0` | The maximum number of occupants the train can hold. |
| `:model` | `biz:model` | The model of the train. |
| `:name` | `base:name` | The name of the train. |
| `:operator` | `entity:actor` | The contact information of the operator of the train. |
| `:owner` | `entity:actor` | The current owner of the train. |
| `:owner:name` | `entity:name` | The name of the current owner of the train. |
| `:phys:height` | `geo:dist` | The physical height of the train. |
| `:phys:length` | `geo:dist` | The physical length of the train. |
| `:phys:mass` | `mass` | The physical mass of the train. |
| `:phys:volume` | `geo:dist` | The physical volume of the train. |
| `:phys:width` | `geo:dist` | The physical width of the train. |
| `:place` | `geo:place` | The place where the train was located. |
| `:place:address` | `geo:address` | The postal address where the train was located. |
| `:place:address:city` | `base:name` | The city where the train was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the train was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the train was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the train was located. |
| `:place:country` | `pol:country` | The country where the train was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the train was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the train was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the train was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the train was located. |
| `:place:loc` | `loc` | The geopolitical location where the train was located. |
| `:place:name` | `geo:name` | The name where the train was located. |
| `:serial` | `base:id` | The manufacturer assigned serial number of the train. |

### `transport:rail:train`

An individual instance of a consist of train cars running a route.

| Interface |
|-----------|
| `transport:schedule` |
| `transport:trip` |

| Property | Type | Doc |
|----------|------|-----|
| `:arrived` | `time` | The actual arrival time. |
| `:arrived:place` | `geo:place` | The actual arrival place. |
| `:arrived:point` | `transport:point` | The actual arrival point. |
| `:cargo:mass` | `mass` | The cargo mass carried by the train on this train trip. |
| `:cargo:volume` | `geo:dist` | The cargo volume carried by the train on this train trip. |
| `:departed` | `time` | The actual departure time. |
| `:departed:place` | `geo:place` | The actual departure place. |
| `:departed:point` | `transport:point` | The actual departure point. |
| `:duration` | `duration` | The actual duration. |
| `:id` | `base:id` | The ID assigned to the train. |
| `:occupants` | `int:min0` | The number of occupants of the train on this train trip. |
| `:operator` | `entity:actor` | The contact information of the operator of the train trip. |
| `:scheduled:arrival` | `time` | The scheduled arrival time. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival place. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival point. |
| `:scheduled:departure` | `time` | The scheduled departure time. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure place. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure point. |
| `:scheduled:duration` | `duration` | The scheduled duration. |
| `:status` | `transport:trip:status` | The status of the train trip. |
| `:vehicle` | `transport:vehicle` | The train which traveled the train trip. |

### `transport:sea:telem`

A telemetry sample from a vessel in transit.

| Interface |
|-----------|
| `geo:locatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:airdraft` | `geo:dist` | The maximum height of the ship from the waterline. |
| `:course` | `transport:direction` | The direction, in degrees from true North, that the vessel is traveling. |
| `:destination` | `geo:place` | The fully resolved destination that the vessel has declared. |
| `:destination:eta` | `time` | The estimated time of arrival that the vessel has declared. |
| `:destination:name` | `geo:name` | The name of the destination that the vessel has declared. |
| `:draft` | `geo:dist` | The keel depth at the time. |
| `:heading` | `transport:direction` | The direction, in degrees from true North, that the bow of the vessel is pointed. |
| `:place` | `geo:place` | The place where the telemetry sample was located. |
| `:place:address` | `geo:address` | The postal address where the telemetry sample was located. |
| `:place:address:city` | `base:name` | The city where the telemetry sample was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the telemetry sample was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the telemetry sample was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the telemetry sample was located. |
| `:place:country` | `pol:country` | The country where the telemetry sample was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the telemetry sample was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the telemetry sample was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the telemetry sample was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the telemetry sample was located. |
| `:place:loc` | `loc` | The geopolitical location where the telemetry sample was located. |
| `:place:name` | `geo:name` | The name where the telemetry sample was located. |
| `:speed` | `velocity` | The speed of the vessel at the time. |
| `:time` | `time` | The time the telemetry was sampled. |
| `:vessel` | `transport:sea:vessel` | The vessel being measured. |

### `transport:sea:vessel`

An individual sea vessel.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |
| `transport:vehicle` |

| Property | Type | Doc |
|----------|------|-----|
| `:callsign` | `base:id` | The callsign of the vessel. |
| `:created` | `time` | The time that the vessel was created. |
| `:creator` | `entity:actor` | The primary actor which created the vessel. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the vessel. |
| `:flag` | `iso:3166:alpha2` | The country the vessel is flagged to. |
| `:imo` | `transport:sea:imo` | The International Maritime Organization number for the vessel. |
| `:max:cargo:mass` | `mass` | The maximum mass the vessel can carry as cargo. |
| `:max:cargo:volume` | `geo:dist` | The maximum volume the vessel can carry as cargo. |
| `:max:occupants` | `int:min0` | The maximum number of occupants the vessel can hold. |
| `:mmsi` | `transport:sea:mmsi` | The Maritime Mobile Service Identifier assigned to the vessel. |
| `:model` | `biz:model` | The model of the vessel. |
| `:name` | `base:name` | The name of the vessel. |
| `:operator` | `entity:actor` | The contact information of the operator. |
| `:owner` | `entity:actor` | The current owner of the vessel. |
| `:owner:name` | `entity:name` | The name of the current owner of the vessel. |
| `:phys:height` | `geo:dist` | The physical height of the vessel. |
| `:phys:length` | `geo:dist` | The physical length of the vessel. |
| `:phys:mass` | `mass` | The physical mass of the vessel. |
| `:phys:volume` | `geo:dist` | The physical volume of the vessel. |
| `:phys:width` | `geo:dist` | The physical width of the vessel. |
| `:place` | `geo:place` | The place where the vessel was located. |
| `:place:address` | `geo:address` | The postal address where the vessel was located. |
| `:place:address:city` | `base:name` | The city where the vessel was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the vessel was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the vessel was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the vessel was located. |
| `:place:country` | `pol:country` | The country where the vessel was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the vessel was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the vessel was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the vessel was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the vessel was located. |
| `:place:loc` | `loc` | The geopolitical location where the vessel was located. |
| `:place:name` | `geo:name` | The name where the vessel was located. |
| `:serial` | `base:id` | The manufacturer assigned serial number of the vessel. |
| `:type` | `transport:sea:vessel:type:taxonomy` | The type of vessel. |

### `transport:sea:vessel:type:taxonomy`

A hierarchical taxonomy of sea vessel types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `transport:sea:vessel:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

### `transport:shipping:container`

An individual shipping container.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the shipping container was created. |
| `:creator` | `entity:actor` | The primary actor which created the shipping container. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the shipping container. |
| `:max:cargo:mass` | `mass` | The maximum mass the shipping container can carry as cargo. |
| `:max:cargo:volume` | `geo:dist` | The maximum volume the shipping container can carry as cargo. |
| `:max:occupants` | `int:min0` | The maximum number of occupants the shipping container can hold. |
| `:model` | `biz:model` | The model of the shipping container. |
| `:name` | `base:name` | The name of the shipping container. |
| `:owner` | `entity:actor` | The current owner of the shipping container. |
| `:owner:name` | `entity:name` | The name of the current owner of the shipping container. |
| `:phys:height` | `geo:dist` | The physical height of the shipping container. |
| `:phys:length` | `geo:dist` | The physical length of the shipping container. |
| `:phys:mass` | `mass` | The physical mass of the shipping container. |
| `:phys:volume` | `geo:dist` | The physical volume of the shipping container. |
| `:phys:width` | `geo:dist` | The physical width of the shipping container. |
| `:place` | `geo:place` | The place where the shipping container was located. |
| `:place:address` | `geo:address` | The postal address where the shipping container was located. |
| `:place:address:city` | `base:name` | The city where the shipping container was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the shipping container was located. |
| `:place:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the shipping container was located. |
| `:place:bbox` | `geo:bbox` | A bounding box which encompasses where the shipping container was located. |
| `:place:country` | `pol:country` | The country where the shipping container was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the shipping container was located. |
| `:place:geojson` | `geo:json` | A GeoJSON representation of where the shipping container was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the shipping container was located. |
| `:place:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the shipping container was located. |
| `:place:loc` | `loc` | The geopolitical location where the shipping container was located. |
| `:place:name` | `geo:name` | The name where the shipping container was located. |
| `:serial` | `base:id` | The manufacturer assigned serial number of the shipping container. |

### `transport:stop`

A stop made by a vehicle on a trip.

| Interface |
|-----------|
| `transport:schedule` |

| Property | Type | Doc |
|----------|------|-----|
| `:arrived` | `time` | The actual arrival time. |
| `:arrived:place` | `geo:place` | The actual arrival place. |
| `:arrived:point` | `transport:point` | The actual arrival point. |
| `:departed` | `time` | The actual departure time. |
| `:departed:place` | `geo:place` | The actual departure place. |
| `:departed:point` | `transport:point` | The actual departure point. |
| `:duration` | `duration` | The actual duration. |
| `:scheduled:arrival` | `time` | The scheduled arrival time. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival place. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival point. |
| `:scheduled:departure` | `time` | The scheduled departure time. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure place. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure point. |
| `:scheduled:duration` | `duration` | The scheduled duration. |
| `:trip` | `transport:trip` | The trip which contains the stop. |

## Edges

| Source | Verb | Target | Doc |
|--------|------|--------|-----|
| `*` | `linked` | `*` | The source node is linked to the target node. |
| `*` | `refs` | `*` | The source node contains a reference to the target node. |
| `belief:system` | `has` | `belief:tenet` | The belief system includes the tenet. |
| `biz:deal` | `has` | `econ:lineitem` | The deal includes the line item. |
| `biz:deal` | `ledto` | `econ:purchase` | The deal led to the purchase. |
| `biz:listing` | `has` | `econ:lineitem` | The listing offers the line item. |
| `biz:listing` | `ledto` | `econ:purchase` | The listing led to the purchase. |
| `biz:rfp` | `has` | `doc:requirement` | The RFP lists the requirement. |
| `biz:rfp` | `ledto` | `biz:deal` | The RFP led to the deal being proposed. |
| `crypto:key:secret` | `decrypts` | `file:bytes` | The key is used to decrypt the file. |
| `doc:contract` | `has` | `doc:requirement` | The contract contains the requirement. |
| `econ:purchase` | `has` | `econ:lineitem` | The purchase included the line item. |
| `econ:purchase` | `ledto` | `econ:payment` | The purchase led to the payment. |
| `econ:receipt` | `has` | `econ:lineitem` | The receipt included the line item. |
| `econ:statement` | `has` | `econ:payment` | The financial statement includes the payment. |
| `entity:action` | `had` | `entity:goal` | The action was taken in pursuit of the goal. |
| `entity:action` | `targeted` | `risk:targetable` | The action represents the actor targeting based on the target node. |
| `entity:action` | `used` | `meta:observable` | The action was taken using the target node. |
| `entity:actor` | `targeted` | `risk:targetable` | The actor targets based on the target node. |
| `entity:actor` | `used` | `meta:observable` | The actor used the target node. |
| `entity:believed` | `followed` | `belief:tenet` | The actor followed the tenet during the period. |
| `entity:campaign` | `ledto` | `econ:purchase` | The campaign led to the purchase. |
| `entity:contactlist` | `has` | `entity:contact` | The contact list contains the contact. |
| `entity:contribution` | `had` | `econ:lineitem` | The contribution includes the line item. |
| `entity:contribution` | `had` | `econ:payment` | The contribution includes the payment. |
| `entity:studied` | `included` | `edu:class` | The class was taken by the student as part of their studies. |
| `entity:studied` | `included` | `edu:learnable` | The target node was included by the actor as part of their studies. |
| `file:bytes` | `refs` | `it:dev:str` | The source file contains the target string. |
| `file:bytes` | `uses` | `math:algorithm` | The file uses the algorithm. |
| `file:bytes` | `uses` | `meta:technique` | The source file uses the target technique. |
| `geo:place` | `contains` | `geo:place` | The source place completely contains the target place. |
| `inet:fqdn` | `uses` | `meta:technique` | The source FQDN was selected or created using the target technique. |
| `inet:net` | `has` | `inet:ip` | The IP address range contains the IP address. |
| `inet:proto:link` | `shows` | `risk:vulnerable` | The network activity shows that the vulnerability was present. |
| `inet:url` | `uses` | `meta:technique` | The source URL was created using the target technique. |
| `inet:whois:iprecord` | `has` | `inet:ip` | The IP whois record describes the IP address. |
| `it:app:snort:rule` | `detects` | `it:software` | The snort rule detects use of the software. |
| `it:app:snort:rule` | `detects` | `it:softwarename` | The snort rule detects the named software. |
| `it:app:snort:rule` | `detects` | `meta:technique` | The snort rule detects use of the technique. |
| `it:app:snort:rule` | `detects` | `risk:tool:software` | The snort rule detects use of the tool. |
| `it:app:snort:rule` | `detects` | `risk:vuln` | The snort rule detects use of the vulnerability. |
| `it:app:yara:rule` | `detects` | `it:software` | The YARA rule detects the software. |
| `it:app:yara:rule` | `detects` | `it:softwarename` | The YARA rule detects the named software. |
| `it:app:yara:rule` | `detects` | `meta:technique` | The YARA rule detects the technique. |
| `it:app:yara:rule` | `detects` | `risk:tool:software` | The YARA rule detects the tool. |
| `it:app:yara:rule` | `detects` | `risk:vuln` | The YARA rule detects the vulnerability. |
| `it:dev:repo` | `has` | `inet:url` | The repo has content hosted at the URL. |
| `it:dev:repo:commit` | `has` | `it:dev:repo:entry` | The file entry is present in the commit version of the repository. |
| `it:exec:query` | `found` | `*` | The target node was returned as a result of running the query. |
| `it:log:event` | `about` | `*` | The it:log:event is about the target node. |
| `it:os:windows:service` | `ledto` | `it:exec:proc` | The service configuration caused the process to be created. |
| `it:sec:stix:indicator` | `detects` | `*` | The STIX indicator can detect evidence of the target node. |
| `it:sec:stix:indicator` | `detects` | `entity:campaign` | The STIX indicator detects the campaign. |
| `it:sec:stix:indicator` | `detects` | `entity:contact` | The STIX indicator detects the entity. |
| `it:sec:stix:indicator` | `detects` | `it:software` | The STIX indicator detects the software. |
| `it:sec:stix:indicator` | `detects` | `meta:technique` | The STIX indicator detects the technique. |
| `it:sec:stix:indicator` | `detects` | `ou:org` | The STIX indicator detects the organization. |
| `it:software` | `creates` | `file:exemplar:entry` | The software creates the file entry. |
| `it:software` | `creates` | `it:os:windows:registry:entry` | The software creates the Microsoft Windows registry entry. |
| `it:software` | `creates` | `it:os:windows:service` | The software creates the Microsoft Windows service. |
| `it:software` | `has` | `it:software` | The source software directly includes the target software. |
| `it:software` | `runson` | `it:hardware` | The source software can be run on the target hardware. |
| `it:software` | `runson` | `it:software` | The source software can be run within the target software. |
| `it:software` | `uses` | `inet:service:platform` | The software uses the platform. |
| `it:software` | `uses` | `it:software` | The source software uses the target software. |
| `it:software` | `uses` | `math:algorithm` | The software uses the algorithm. |
| `it:software` | `uses` | `meta:technique` | The software uses the technique. |
| `it:software` | `uses` | `risk:vuln` | The software uses the vulnerability. |
| `math:algorithm` | `generates` | `*` | The target node was generated by the algorithm. |
| `meta:causal` | `ledto` | `meta:causal` | The source event led to the target event. |
| `meta:event` | `about` | `*` | The event is about the target node. |
| `meta:feed` | `found` | `*` | The meta:feed produced the target node. |
| `meta:note` | `about` | `*` | The meta:note is about the target node. |
| `meta:note` | `has` | `file:attachment` | The note includes the file attachment. |
| `meta:observable` | `resembles` | `meta:observable` | The source node resembles the target node. |
| `meta:rule` | `detects` | `meta:observable` | The rule is designed to detect the target node. |
| `meta:rule` | `generated` | `it:log:event` | The meta:rule generated the it:log:event node. |
| `meta:rule` | `generated` | `risk:alert` | The meta:rule generated the risk:alert node. |
| `meta:rule` | `matches` | `*` | The rule matched on the target node. |
| `meta:rule` | `shows` | `ou:enacted` | The source rule shows the status of the enacted document. |
| `meta:ruleset` | `has` | `meta:rule` | The ruleset includes the rule. |
| `meta:source` | `seen` | `*` | The meta:source observed the target node. |
| `meta:task` | `has` | `file:attachment` | The task includes the file attachment. |
| `meta:technique` | `addresses` | `meta:technique` | The technique addresses the technique. |
| `meta:technique` | `addresses` | `risk:vuln` | The technique addresses the vulnerability. |
| `meta:technique` | `meets` | `doc:requirement` | Use of the source technique meets the target requirement. |
| `meta:timeline` | `has` | `meta:event` | The timeline includes the event. |
| `meta:usable` | `uses` | `meta:usable` | The source node uses the target node. |
| `plan:phase` | `uses` | `meta:usable` | The plan phase makes use of the target node. |
| `plan:procedure:step` | `uses` | `meta:usable` | The step in the procedure makes use of the target node. |
| `proj:sprint` | `has` | `meta:task` | The task was worked on during the sprint. |
| `risk:alert` | `about` | `*` | The alert is about the target node. |
| `risk:attack` | `ledto` | `risk:outage` | The attack led to the outage. |
| `risk:extortion` | `ledto` | `econ:payment` | The attack led to the outage. |
| `risk:extortion` | `leveraged` | `meta:observable` | The extortion event was based on attacker access to the target node. |
| `risk:leak` | `leaked` | `meta:observable` | The leak included the disclosure of the target node. |
| `risk:outage` | `impacted` | `*` | The outage event impacted the availability of the target node. |
| `risk:theft` | `stole` | `meta:observable` | The target node was stolen during the theft. |
| `risk:theft` | `stole` | `phys:object` | The target node was stolen during the theft. |
| `risk:tool:software` | `uses` | `math:algorithm` | The tool uses the algorithm. |
| `sci:evidence` | `has` | `*` | The evidence includes observations from the target nodes. |
| `sci:experiment` | `used` | `*` | The experiment used the target nodes when it was run. |
| `sci:observation` | `has` | `*` | The observations are summarized from the target nodes. |

## Tag Properties

## Interfaces

### `auth:credential`

An interface inherited by authentication credential forms.

| Form |
|------|
| `auth:passwd` |
| `crypto:salthash` |

### `base:activity`

Properties common to activity which occurs over a period.

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this activity. |
| `:period` | `ival` | The period over which the activity occurred. |

| Form |
|------|
| `biz:deal` |
| `edu:class` |
| `entity:conflict` |
| `inet:flow` |
| `meta:activity` |
| `pol:election` |
| `pol:race` |

### `base:event`

Properties common to an event.

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:activity` | A parent activity which includes this event. |
| `:time` | `time` | The time that the event occurred. |

| Form |
|------|
| `meta:event` |

### `biz:manufactured`

Properties common to items being manufactured.

| Property | Type | Doc |
|----------|------|-----|
| `:model` | `biz:model` | The model number or name of the item. |
| `:name` | `base:name` | The name of the item. |

| Form |
|------|
| `it:host` |

### `crypto:hash`

An interface inherited by all cryptographic hashes.

| Form |
|------|
| `crypto:hash:md5` |
| `crypto:hash:sha1` |
| `crypto:hash:sha256` |
| `crypto:hash:sha384` |
| `crypto:hash:sha512` |

### `crypto:hashable`

An interface inherited by types which are frequently hashed.

| Form |
|------|
| `auth:passwd` |

### `crypto:key`

An interface inherited by all cryptographic keys.

| Property | Type | Doc |
|----------|------|-----|
| `:algorithm` | `crypto:algorithm` | The cryptographic algorithm which uses the key material. |
| `:bits` | `int:min1` | The number of bits of key material. |

| Form |
|------|
| `crypto:key:base` |
| `crypto:key:dsa` |
| `crypto:key:ecdsa` |
| `crypto:key:rsa` |
| `crypto:key:secret` |

### `crypto:smart:effect`

Properties common to the effects of a crypto smart contract transaction.

| Property | Type | Doc |
|----------|------|-----|
| `:index` | `int` | The order of the effect within the effects of one transaction. |
| `:transaction` | `crypto:currency:transaction` | The transaction where the smart contract was called. |

| Form |
|------|
| `crypto:smart:effect:burntoken` |
| `crypto:smart:effect:edittokensupply` |
| `crypto:smart:effect:minttoken` |
| `crypto:smart:effect:proxytoken` |
| `crypto:smart:effect:proxytokenall` |
| `crypto:smart:effect:proxytokens` |
| `crypto:smart:effect:transfertoken` |
| `crypto:smart:effect:transfertokens` |

### `doc:authorable`

Properties common to authorable forms.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the document. |
| `:id` | `base:id` | The document ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the document. |
| `:supersedes` | `array of doc:authorable` | An array of document versions which are superseded by this document. |
| `:updated` | `time` | The time that the document was last updated. |
| `:url` | `inet:url` | The URL where the document is available. |
| `:version` | `it:version` | The version of the document. |

| Form |
|------|
| `doc:requirement` |
| `edu:course` |
| `it:app:snort:rule` |
| `it:app:yara:rule` |
| `it:software` |
| `meta:rule` |
| `meta:ruleset` |
| `plan:phase` |
| `plan:system` |

### `doc:document`

A common interface for documents.

| Property | Type | Doc |
|----------|------|-----|
| `:body` | `text` | The text of the document. |
| `:file` | `file:bytes` | The file containing the document contents. |
| `:file:captured` | `time` | The time when the file content was captured. |
| `:file:name` | `file:base` | The name of the file containing the document contents. |
| `:title` | `str` | The title of the document. |
| `:type` | `doc:document:type:taxonomy` | The type of document. |

| Form |
|------|
| `biz:rfp` |
| `doc:contract` |
| `doc:policy` |
| `doc:report` |
| `doc:resume` |
| `doc:standard` |
| `plan:procedure` |

### `doc:published`

Properties common to published documents.

| Property | Type | Doc |
|----------|------|-----|
| `:public` | `bool` | Set to true if the report is publicly available. |
| `:published` | `time` | The time the report was published. |
| `:publisher` | `entity:actor` | The entity which published the report. |
| `:publisher:name` | `entity:name` | The name of the entity which published the report. |
| `:topics` | `array of meta:topic` | The topics discussed in the report. |

| Form |
|------|
| `biz:rfp` |
| `doc:report` |

### `doc:signable`

An interface implemented by documents which can be signed by actors.

| Property | Type | Doc |
|----------|------|-----|
| `:signed` | `time` | The date that the document signing was complete. |

| Form |
|------|
| `doc:contract` |

### `econ:pay:instrument`

An interface for forms which may act as a payment instrument.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:fin:account` | The account contains the funds used by the instrument. |

| Form |
|------|
| `crypto:currency:address` |
| `econ:bank:check` |
| `econ:pay:card` |
| `inet:service:account` |

### `edu:learnable`

An interface inherited by nodes which represent a skill which can be learned.

| Form |
|------|
| `lang:language` |
| `ps:skill` |

### `entity:action`

Properties which are common to actions taken by entities.

| Property | Type | Doc |
|----------|------|-----|
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |

| Form |
|------|
| `entity:contribution` |

### `entity:activity`

Properties common to activity carried out by an actor.

| Form |
|------|
| `biz:listing` |
| `biz:service` |
| `doc:contract` |
| `entity:attended` |
| `entity:believed` |
| `entity:campaign` |
| `entity:created` |
| `entity:motive` |
| `entity:participated` |
| `entity:proficiency` |
| `entity:said` |
| `entity:studied` |
| `entity:supported` |
| `pol:candidate` |
| `pol:term` |
| `risk:compromise` |
| `risk:extortion` |
| `sci:experiment` |

### `entity:actor`

An interface for entities which have initiative to act.

| Form |
|------|
| `entity:contact` |
| `inet:service:account` |
| `inet:service:agent` |
| `ou:org` |
| `ps:person` |
| `risk:threat` |
| `syn:user` |

### `entity:contactable`

An interface for forms which contain contact info.

| Property | Type | Doc |
|----------|------|-----|
| `:banner` | `file:bytes` | A banner or hero image used on the profile page. |
| `:bio` | `text` | A tagline or bio provided for the entity. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the entity. |
| `:desc` | `text` | A description of the entity. |
| `:email` | `inet:email` | The primary email address for the entity. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the entity. |
| `:id` | `base:id` | A type or source specific ID for the entity. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:lang` | `lang:language` | The primary language of the entity. |
| `:langs` | `array of lang:language` | An array of alternate languages for the entity. |
| `:lifespan` | `ival` | The lifespan of the entity. |
| `:name` | `entity:name` | The primary entity name of the entity. |
| `:names` | `array of entity:name` | An array of alternate entity names for the entity. |
| `:phone` | `tel:phone` | The primary phone number for the entity. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the entity. |
| `:photo` | `file:bytes` | The profile picture or avatar for this entity. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the entity. |
| `:user` | `inet:user` | The primary user name for the entity. |
| `:users` | `array of inet:user` | An array of alternate user names for the entity. |
| `:websites` | `array of inet:url` | Web sites listed for the entity. |

| Form |
|------|
| `entity:contact` |
| `entity:history` |
| `ou:org` |
| `ps:person` |
| `risk:threat` |

### `entity:creatable`

An interface implemented by forms which represent things made or created by an actor.

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the item was created. |
| `:creator` | `entity:actor` | The primary actor which created the item. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the item. |

| Form |
|------|
| `biz:product` |
| `it:host` |

### `entity:event`

Properties common to events carried out by an actor.

| Form |
|------|
| `econ:payment` |
| `econ:purchase` |
| `entity:achieved` |
| `entity:discovered` |
| `entity:registered` |
| `entity:signed` |
| `risk:attack` |
| `risk:leak` |
| `risk:theft` |
| `sci:observation` |

### `entity:identifier`

An interface which is inherited by entity identifier forms.

| Form |
|------|
| `econ:bank:aba:rtn` |
| `econ:bank:iban` |
| `econ:bank:swift:bic` |
| `econ:pay:iin` |
| `gov:cn:icp` |
| `gov:cn:mucd` |
| `gov:us:cage` |
| `gov:us:ssn` |
| `it:adid` |
| `it:mitre:attack:group:id` |
| `tel:mob:carrier` |
| `tel:mob:tadig` |

### `entity:multiple`

Properties which apply to entities which may represent a group or organization.

| Form |
|------|
| `entity:contact` |
| `inet:service:account` |
| `ou:org` |

### `entity:participable`

An interface implemented by activities which an actor may participate in.

| Form |
|------|
| `edu:class` |
| `entity:campaign` |
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:meeting` |
| `ou:preso` |

### `entity:resolvable`

An abstract entity which can be resolved to an organization or person.

| Property | Type | Doc |
|----------|------|-----|
| `:resolved` | `ou:org`, `ps:person` | The resolved entity to which this entity belongs. |

| Form |
|------|
| `entity:contact` |
| `risk:threat` |

### `entity:singular`

Properties which apply to entities which may represent a person.

| Property | Type | Doc |
|----------|------|-----|
| `:org` | `ou:org` | An associated organization listed as part of the contact information. |
| `:org:name` | `entity:name` | The name of an associated organization listed as part of the contact information. |
| `:title` | `entity:title` | The entity title or role for this item. |
| `:titles` | `array of entity:title` | An array of alternate entity titles or roles for this item. |

| Form |
|------|
| `entity:contact` |
| `inet:service:account` |
| `ps:person` |

### `entity:stance`

An interface for asks/offers in a negotiation.

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `meta:negotiable` | The negotiation activity this stance was part of. |
| `:expires` | `time` | The time that the stance expires. |
| `:value` | `econ:price` | The value of the stance. |

| Form |
|------|
| `entity:asked` |
| `entity:offered` |

### `entity:supportable`

An interface implemented by activities which may be supported in by an actor.

| Form |
|------|
| `entity:campaign` |
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:preso` |

### `file:mime:exe`

Properties common to executable file formats.

| Property | Type | Doc |
|----------|------|-----|
| `:compiler` | `it:software` | The software used to compile the executable. |
| `:compiler:name` | `it:softwarename` | The name of the software used to compile the executable. |
| `:packer` | `it:software` | The software used to pack the executable. |
| `:packer:name` | `it:softwarename` | The name of the software used to pack the executable. |

| Form |
|------|
| `file:mime:elf` |
| `file:mime:macho` |
| `file:mime:pe` |

### `file:mime:image`

Properties common to image file formats.

| Property | Type | Doc |
|----------|------|-----|
| `:altitude` | `geo:altitude` | MIME specific altitude information extracted from metadata. |
| `:author` | `entity:contact` | MIME specific contact information extracted from metadata. |
| `:comment` | `str` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `str` | MIME specific description field extracted from metadata. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `base:name` | The text contained within the image. |

| Form |
|------|
| `file:mime:gif` |
| `file:mime:jpg` |
| `file:mime:png` |
| `file:mime:tif` |

### `file:mime:meta`

Properties common to mime specific file metadata types.

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |

| Form |
|------|
| `file:mime:lnk` |
| `file:mime:macho:loadcmd` |
| `file:mime:macho:section` |
| `file:mime:macho:segment` |
| `file:mime:macho:uuid` |
| `file:mime:macho:version` |
| `file:mime:pdf` |
| `file:mime:pe:export` |
| `file:mime:pe:resource` |
| `file:mime:pe:section` |
| `file:mime:rtf` |
| `it:dev:function:sample` |

### `file:mime:msoffice`

Properties common to various microsoft office file formats.

| Property | Type | Doc |
|----------|------|-----|
| `:application` | `str` | The creating_application extracted from Microsoft Office metadata. |
| `:author` | `str` | The author extracted from Microsoft Office metadata. |
| `:created` | `time` | The create_time extracted from Microsoft Office metadata. |
| `:lastsaved` | `time` | The last_saved_time extracted from Microsoft Office metadata. |
| `:subject` | `str` | The subject extracted from Microsoft Office metadata. |
| `:title` | `str` | The title extracted from Microsoft Office metadata. |

| Form |
|------|
| `file:mime:msdoc` |
| `file:mime:msppt` |
| `file:mime:msxls` |

### `geo:locatable`

Properties common to items and events which may be geolocated.

| Property | Type | Doc |
|----------|------|-----|
| `:` | `geo:place` | The place where the item was located. |
| `:address` | `geo:address` | The postal address where the item was located. |
| `:address:city` | `base:name` | The city where the item was located. |
| `:altitude` | `geo:altitude` | The altitude where the item was located. |
| `:altitude:accuracy` | `geo:dist` | The accuracy of the altitude where the item was located. |
| `:bbox` | `geo:bbox` | A bounding box which encompasses where the item was located. |
| `:country` | `pol:country` | The country where the item was located. |
| `:country:code` | `iso:3166:alpha2` | The country code where the item was located. |
| `:geojson` | `geo:json` | A GeoJSON representation of where the item was located. |
| `:latlong` | `geo:latlong` | The latlong where the item was located. |
| `:latlong:accuracy` | `geo:dist` | The accuracy of the latlong where the item was located. |
| `:loc` | `loc` | The geopolitical location where the item was located. |
| `:name` | `geo:name` | The name where the item was located. |

| Form |
|------|
| `econ:payment` |
| `econ:purchase` |
| `geo:place` |
| `geo:telem` |
| `inet:ip` |
| `inet:wifi:ap` |
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:meeting` |
| `ou:preso` |
| `tel:mob:cell` |
| `tel:mob:telem` |
| `transport:air:telem` |
| `transport:sea:telem` |

### `inet:proto:link`

Properties common to network protocol requests and transports.

| Property | Type | Doc |
|----------|------|-----|
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the link. |
| `:client:host` | `it:host` | The client host which initiated the link. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the link. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the link. |
| `:server:host` | `it:host` | The server host which received the link. |
| `:server:proc` | `it:exec:proc` | The server process which received the link. |

| Form |
|------|
| `inet:flow` |

### `inet:proto:request`

Properties common to network protocol requests and responses.

| Property | Type | Doc |
|----------|------|-----|
| `:flow` | `inet:flow` | The network flow which contained the request. |

| Form |
|------|
| `inet:dns:request` |
| `inet:http:request` |
| `inet:rdp:handshake` |
| `inet:ssh:handshake` |
| `inet:tls:handshake` |
| `it:host:login` |

### `inet:service:action`

Properties common to events within a service platform.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account` | The account which initiated the action. |
| `:agent` | `inet:service:agent` | The service agent which performed the action potentially on behalf of an account. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software used to initiate the action. |
| `:error:code` | `str` | The platform specific error code if the action was unsuccessful. |
| `:error:reason` | `str` | The platform specific friendly error reason if the action was unsuccessful. |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:rule` | `inet:service:rule` | The rule which allowed or denied the action. |
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:success` | `bool` | Set to true if the action was successful. |
| `:time` | `time` | The time that the account initiated the action. |

| Form |
|------|
| `inet:search:query` |
| `inet:service:access` |
| `inet:service:login` |
| `inet:service:message` |

### `inet:service:base`

Properties common to most forms within a service platform.

| Property | Type | Doc |
|----------|------|-----|
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |

### `inet:service:joinable`

An interface common to nodes which can have accounts as members.

| Form |
|------|
| `inet:service:channel` |
| `inet:service:role` |

### `inet:service:object`

Properties common to objects within a service platform.

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the object. |
| `:period` | `ival` | The period when the object existed. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the object. |
| `:status` | `inet:service:object:status` | The status of the object. |
| `:url` | `inet:url` | The primary URL associated with the object. |

| Form |
|------|
| `inet:service:agent` |
| `inet:service:bucket` |
| `inet:service:bucket:item` |
| `inet:service:channel` |
| `inet:service:emote` |
| `inet:service:member` |
| `inet:service:permission` |
| `inet:service:relationship` |
| `inet:service:resource` |
| `inet:service:role` |
| `inet:service:rule` |
| `inet:service:session` |
| `inet:service:subscription` |
| `inet:service:thread` |
| `it:dev:repo` |
| `it:dev:repo:branch` |
| `it:dev:repo:commit` |
| `it:dev:repo:diff:comment` |
| `it:dev:repo:issue` |
| `it:dev:repo:issue:comment` |
| `it:dev:repo:issue:label` |
| `it:host` |
| `it:host:tenancy` |
| `it:software:image` |

### `inet:service:subscriber`

Properties common to the nodes which subscribe to services.

| Property | Type | Doc |
|----------|------|-----|
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:email` | `inet:email` | The primary email address for the subscriber. |
| `:name` | `entity:name` | The primary entity name of the subscriber. |
| `:profile` | `entity:contact` | Current detailed contact information for the subscriber. |
| `:user` | `inet:user` | The primary user name for the subscriber. |

| Form |
|------|
| `inet:service:account` |
| `inet:service:tenant` |

### `it:host:activity`

Activity which occurred on a host.

| Form |
|------|
| `it:exec:proc` |
| `it:exec:thread` |
| `it:os:windows:service` |

### `it:host:event`

An event which occurred on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:proc` | `it:exec:proc` | The process which caused the event. |
| `:thread` | `it:exec:thread` | The thread which caused the event. |

| Form |
|------|
| `it:exec:bind` |
| `it:exec:fetch` |
| `it:exec:file:add` |
| `it:exec:file:del` |
| `it:exec:file:read` |
| `it:exec:file:write` |
| `it:exec:lib:load` |
| `it:exec:mmap:add` |
| `it:exec:mutex:add` |
| `it:exec:pipe:add` |
| `it:exec:proc:create` |
| `it:exec:proc:signal` |
| `it:exec:proc:terminate` |
| `it:exec:query` |
| `it:exec:screenshot` |
| `it:exec:thread:create` |
| `it:exec:thread:terminate` |
| `it:exec:windows:registry:del` |
| `it:exec:windows:registry:get` |
| `it:exec:windows:registry:set` |
| `it:log:event` |
| `it:os:windows:service:add` |
| `it:os:windows:service:del` |

### `it:host:exec`

Properties common to runtime events and activity on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:exe` | `file:bytes` | The executable file which caused the activity. |
| `:host` | `it:host` | The host on which the activity occurred. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |

### `lang:transcript`

An interface which applies to forms containing speech.

| Form |
|------|
| `tel:call` |

### `meta:achievable`

An interface implemented by forms which are achievable.

| Form |
|------|
| `entity:goal` |
| `meta:award` |

### `meta:believable`

An interface implemented by forms which may be believed in by an actor.

| Form |
|------|
| `belief:system` |
| `belief:tenet` |
| `sci:hypothesis` |

### `meta:causal`

Implemented by events and activities which can lead to effects.

| Form |
|------|
| `risk:alert` |

### `meta:discoverable`

An interface for items which can be discovered by an actor.

| Property | Type | Doc |
|----------|------|-----|
| `:discovered` | `time` | The earliest known time when the item was discovered. |
| `:discoverer` | `entity:actor` | The earliest known actor which discovered the item. |

| Form |
|------|
| `risk:attack` |
| `risk:compromise` |
| `risk:threat` |
| `risk:vuln` |

### `meta:havable`

An interface used to describe items that can be possessed by an entity.

| Property | Type | Doc |
|----------|------|-----|
| `:owner` | `entity:actor` | The current owner of the item. |
| `:owner:name` | `entity:name` | The name of the current owner of the item. |

| Form |
|------|
| `biz:product` |
| `inet:wifi:ap` |
| `it:network` |
| `ou:org` |
| `tel:mob:tac` |

### `meta:matchish`

Properties which are common to matches based on rules.

| Property | Type | Doc |
|----------|------|-----|
| `:matched` | `time` | The time that the rule was evaluated to generate the match. |
| `:rule` | `rule:type` | The rule which matched the target node. |
| `:target` | `` | The target node which matched the rule. |
| `:version` | `it:version` | The most recent version of the rule evaluated as a match. |

| Form |
|------|
| `it:app:snort:match` |
| `it:app:yara:match` |

### `meta:negotiable`

An interface implemented by activities which involve negotiation.

| Form |
|------|
| `biz:deal` |
| `risk:extortion` |

### `meta:observable`

Properties common to forms which can be observed.

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The node was observed during the time interval. |

| Form |
|------|
| `auth:passwd` |
| `crypto:currency:address` |
| `crypto:currency:client` |
| `crypto:hash:md5` |
| `crypto:hash:sha1` |
| `crypto:hash:sha256` |
| `crypto:hash:sha384` |
| `crypto:hash:sha512` |
| `crypto:key:base` |
| `crypto:key:dsa` |
| `crypto:key:ecdsa` |
| `crypto:key:rsa` |
| `crypto:key:secret` |
| `crypto:salthash` |
| `crypto:x509:cert` |
| `econ:bank:aba:account` |
| `econ:bank:check` |
| `econ:fin:account` |
| `econ:pay:card` |
| `entity:campaign` |
| `entity:contact` |
| `file:archive:entry` |
| `file:attachment` |
| `file:base` |
| `file:bytes` |
| `file:entry` |
| `file:exemplar:entry` |
| `file:mime:rar:entry` |
| `file:mime:zip:entry` |
| `file:path` |
| `file:stored:entry` |
| `file:subfile:entry` |
| `file:system:entry` |
| `inet:asn` |
| `inet:asnet` |
| `inet:asnip` |
| `inet:banner` |
| `inet:client` |
| `inet:dns:a` |
| `inet:dns:aaaa` |
| `inet:dns:cname` |
| `inet:dns:dynreg` |
| `inet:dns:mx` |
| `inet:dns:ns` |
| `inet:dns:query` |
| `inet:dns:rev` |
| `inet:dns:soa` |
| `inet:dns:txt` |
| `inet:dns:wild:a` |
| `inet:dns:wild:aaaa` |
| `inet:egress` |
| `inet:email` |
| `inet:email:header` |
| `inet:fqdn` |
| `inet:http:request:header` |
| `inet:ip` |
| `inet:mac` |
| `inet:rfc2822:addr` |
| `inet:server` |
| `inet:serverfile` |
| `inet:service:platform` |
| `inet:tls:clientcert` |
| `inet:tls:ja3:sample` |
| `inet:tls:ja3s:sample` |
| `inet:tls:ja4` |
| `inet:tls:ja4:sample` |
| `inet:tls:ja4s` |
| `inet:tls:ja4s:sample` |
| `inet:tls:jarmhash` |
| `inet:tls:jarmsample` |
| `inet:tls:servercert` |
| `inet:tunnel` |
| `inet:url` |
| `inet:url:mirror` |
| `inet:url:redir` |
| `inet:urlfile` |
| `inet:user` |
| `inet:whois:iprecord` |
| `inet:whois:record` |
| `inet:wifi:ap` |
| `inet:wifi:ssid` |
| `it:adid` |
| `it:dev:str` |
| `it:dns:resolver` |
| `it:host:hosted:url` |
| `it:hostname` |
| `it:os:windows:registry:entry` |
| `it:os:windows:registry:key` |
| `it:softid` |
| `lang:hashtag` |
| `ou:id` |
| `tel:mob:imei` |
| `tel:mob:imid` |
| `tel:mob:imsi` |
| `tel:mob:imsiphone` |
| `tel:phone` |

### `meta:recordable`

Properties common to activities which may be recorded or transcribed.

| Property | Type | Doc |
|----------|------|-----|
| `:recording:file` | `file:bytes` | A file containing a recording of the event. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the event. |

| Form |
|------|
| `edu:class` |
| `entity:said` |
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:meeting` |
| `ou:preso` |

### `meta:reported`

Properties common to forms which are created on a per-source basis.

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time when the item was created. |
| `:desc` | `text` | A description of the item. |
| `:id` | `base:id` | A unique ID given to the item. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the item. |
| `:name` | `base:name` | The primary name of the item. |
| `:names` | `array of base:name` | A list of alternate names for the item. |
| `:published` | `time` | The time when the reporter published the item. |
| `:reporter` | `entity:actor` | The entity which reported on the item. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the item. |
| `:resolved` | `meta:reported` | The authoritative item which this reporting is about. |
| `:superseded` | `time` | The time when the item was superseded. |
| `:supersedes` | `array of meta:reported` | An array of item nodes which are superseded by this item. |
| `:updated` | `time` | The time when the item was last updated. |
| `:url` | `inet:url` | The URL for the item. |

| Form |
|------|
| `entity:campaign` |
| `entity:goal` |
| `entity:relationship` |
| `it:software` |
| `meta:technique` |
| `ou:industry` |
| `risk:attack` |
| `risk:compromise` |
| `risk:extortion` |
| `risk:leak` |
| `risk:mitigation` |
| `risk:outage` |
| `risk:theft` |
| `risk:threat` |
| `risk:tool:software` |
| `risk:vuln` |

### `meta:task`

A common interface for tasks.

| Property | Type | Doc |
|----------|------|-----|
| `:assignee` | `entity:actor` | The actor who is assigned to complete the task. |
| `:completed` | `time` | The time the task was completed. |
| `:created` | `time` | The time the task was created. |
| `:creator` | `entity:actor` | The actor who created the task. |
| `:due` | `time` | The time the task must be complete. |
| `:id` | `base:id` | The ID of the task. |
| `:parent` | `meta:task` | The parent task which includes this task. |
| `:priority` | `meta:score` | The priority of the task. |
| `:project` | `proj:project` | The project containing the task. |
| `:status` | `meta:task:status` | The status of the task. |
| `:updated` | `time` | The time the task was last updated. |

| Form |
|------|
| `ou:enacted` |
| `proj:ticket` |
| `risk:alert` |

### `meta:taxonomy`

Properties common to taxonomies.

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:parent` | `meta:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |
| `:title` | `str` | A brief title of the definition. |

| Form |
|------|
| `belief:system:type:taxonomy` |
| `biz:deal:status:taxonomy` |
| `biz:deal:type:taxonomy` |
| `biz:product:type:taxonomy` |
| `biz:rfp:type:taxonomy` |
| `biz:service:type:taxonomy` |
| `doc:contract:type:taxonomy` |
| `doc:policy:type:taxonomy` |
| `doc:report:type:taxonomy` |
| `doc:resume:type:taxonomy` |
| `doc:standard:type:taxonomy` |
| `econ:bank:aba:account:type:taxonomy` |
| `econ:fin:account:type:taxonomy` |
| `econ:fin:security:type:taxonomy` |
| `entity:campaign:type:taxonomy` |
| `entity:contact:type:taxonomy` |
| `entity:goal:type:taxonomy` |
| `entity:had:type:taxonomy` |
| `entity:relationship:type:taxonomy` |
| `geo:place:type:taxonomy` |
| `inet:iface:type:taxonomy` |
| `inet:service:login:method:taxonomy` |
| `inet:service:message:type:taxonomy` |
| `inet:service:permission:type:taxonomy` |
| `inet:service:platform:type:taxonomy` |
| `inet:service:relationship:type:taxonomy` |
| `inet:service:resource:type:taxonomy` |
| `inet:service:subscription:level:taxonomy` |
| `inet:tunnel:type:taxonomy` |
| `it:dev:repo:type:taxonomy` |
| `it:hardware:type:taxonomy` |
| `it:log:event:type:taxonomy` |
| `it:network:type:taxonomy` |
| `it:software:image:type:taxonomy` |
| `it:software:type:taxonomy` |
| `it:storage:volume:type:taxonomy` |
| `math:algorithm:type:taxonomy` |
| `meta:aggregate:type:taxonomy` |
| `meta:event:type:taxonomy` |
| `meta:feed:type:taxonomy` |
| `meta:note:type:taxonomy` |
| `meta:rule:type:taxonomy` |
| `meta:source:type:taxonomy` |
| `meta:technique:type:taxonomy` |
| `meta:timeline:type:taxonomy` |
| `ou:asset:status:taxonomy` |
| `ou:asset:type:taxonomy` |
| `ou:candidate:method:taxonomy` |
| `ou:contest:type:taxonomy` |
| `ou:employment:type:taxonomy` |
| `ou:enacted:status:taxonomy` |
| `ou:event:type:taxonomy` |
| `ou:id:status:taxonomy` |
| `ou:id:type:taxonomy` |
| `ou:industry:type:taxonomy` |
| `ou:job:type:taxonomy` |
| `ou:org:type:taxonomy` |
| `phys:contained:type:taxonomy` |
| `plan:procedure:type:taxonomy` |
| `pol:immigration:status:type:taxonomy` |
| `proj:project:type:taxonomy` |
| `proj:ticket:type:taxonomy` |
| `ps:skill:type:taxonomy` |
| `risk:alert:type:taxonomy` |
| `risk:alert:verdict:taxonomy` |
| `risk:attack:type:taxonomy` |
| `risk:availability` |
| `risk:compromise:type:taxonomy` |
| `risk:extortion:type:taxonomy` |
| `risk:leak:type:taxonomy` |
| `risk:outage:cause:taxonomy` |
| `risk:outage:type:taxonomy` |
| `risk:threat:type:taxonomy` |
| `risk:tool:software:type:taxonomy` |
| `risk:vuln:type:taxonomy` |
| `sci:experiment:type:taxonomy` |
| `sci:hypothesis:type:taxonomy` |
| `tel:mob:cell:radio:type:taxonomy` |
| `tel:phone:type:taxonomy` |
| `transport:air:craft:type:taxonomy` |
| `transport:air:tailnum:type:taxonomy` |
| `transport:land:vehicle:type:taxonomy` |
| `transport:occupant:role:taxonomy` |
| `transport:rail:car:type:taxonomy` |
| `transport:sea:vessel:type:taxonomy` |

### `meta:usable`

An interface implemented by forms which can be used by an actor.

| Form |
|------|
| `it:app:snort:rule` |
| `it:app:yara:rule` |
| `it:hardware` |
| `it:software` |
| `meta:rule` |
| `meta:technique` |
| `risk:mitigation` |
| `risk:tool:software` |
| `risk:vuln` |

### `ou:promotable`

Properties which are common to activities which are promoted by an organization.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `event:name` | The name of the event. |
| `:names` | `array of event:name` | An array of alternate names for the event. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the event. |
| `:website` | `inet:url` | The website of the event website. |

| Form |
|------|
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:preso` |

### `phys:object`

Properties common to physical objects.

| Form |
|------|
| `it:host` |
| `mat:item` |

### `phys:tangible`

Properties common to nodes which have or capture physical characteristics.

| Property | Type | Doc |
|----------|------|-----|
| `:phys:height` | `geo:dist` | The physical height of the object. |
| `:phys:length` | `geo:dist` | The physical length of the object. |
| `:phys:mass` | `mass` | The physical mass of the object. |
| `:phys:volume` | `geo:dist` | The physical volume of the object. |
| `:phys:width` | `geo:dist` | The physical width of the object. |

| Form |
|------|
| `geo:telem` |
| `ps:vitals` |

### `risk:exploitable`

An interface implemented by forms which may be exploited by an actor.

| Form |
|------|
| `inet:client` |
| `inet:server` |
| `inet:service:platform` |
| `it:dns:resolver` |
| `it:hardware` |
| `it:host` |
| `it:software` |
| `ou:asset` |

### `risk:mitigatable`

A common interface for risks which may be mitigated.

| Form |
|------|
| `meta:technique` |
| `risk:mitigation` |
| `risk:vuln` |

### `risk:targetable`

An interface implemented by forms which are targets of threats.

| Form |
|------|
| `entity:title` |
| `meta:topic` |
| `ou:industry` |
| `ou:org` |
| `pol:country` |
| `risk:vuln` |

### `risk:victimized`

An interface for malicious acts which directly impact a victim.

| Property | Type | Doc |
|----------|------|-----|
| `:victim` | `entity:actor` | The victim of the event. |
| `:victim:name` | `entity:name` | The name of the victim of the event. |

| Form |
|------|
| `risk:compromise` |
| `risk:extortion` |
| `risk:leak` |
| `risk:theft` |

### `transport:container`

Properties common to a container used to transport cargo or people.

| Property | Type | Doc |
|----------|------|-----|
| `:max:cargo:mass` | `mass` | The maximum mass the item can carry as cargo. |
| `:max:cargo:volume` | `geo:dist` | The maximum volume the item can carry as cargo. |
| `:max:occupants` | `int:min0` | The maximum number of occupants the item can hold. |
| `:model` | `biz:model` | The model of the item. |
| `:serial` | `base:id` | The manufacturer assigned serial number of the item. |

| Form |
|------|
| `transport:rail:car` |
| `transport:shipping:container` |

### `transport:schedule`

Properties common to travel schedules.

| Property | Type | Doc |
|----------|------|-----|
| `:arrived` | `time` | The actual arrival time. |
| `:arrived:place` | `geo:place` | The actual arrival place. |
| `:arrived:point` | `transport:point` | The actual arrival point. |
| `:departed` | `time` | The actual departure time. |
| `:departed:place` | `geo:place` | The actual departure place. |
| `:departed:point` | `transport:point` | The actual departure point. |
| `:duration` | `duration` | The actual duration. |
| `:scheduled:arrival` | `time` | The scheduled arrival time. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival place. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival point. |
| `:scheduled:departure` | `time` | The scheduled departure time. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure place. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure point. |
| `:scheduled:duration` | `duration` | The scheduled duration. |

| Form |
|------|
| `transport:stop` |

### `transport:trip`

Properties common to a specific trip taken by a vehicle.

| Property | Type | Doc |
|----------|------|-----|
| `:cargo:mass` | `mass` | The cargo mass carried by the vehicle on this trip. |
| `:cargo:volume` | `geo:dist` | The cargo volume carried by the vehicle on this trip. |
| `:occupants` | `int:min0` | The number of occupants of the vehicle on this trip. |
| `:operator` | `entity:actor` | The contact information of the operator of the trip. |
| `:status` | `transport:trip:status` | The status of the trip. |
| `:vehicle` | `transport:vehicle` | The vehicle which traveled the trip. |

| Form |
|------|
| `transport:air:flight` |
| `transport:land:drive` |
| `transport:rail:train` |

### `transport:vehicle`

Properties common to a vehicle.

| Property | Type | Doc |
|----------|------|-----|
| `:operator` | `entity:actor` | The contact information of the operator of the item. |

| Form |
|------|
| `transport:air:craft` |
| `transport:land:vehicle` |
| `transport:rail:consist` |
| `transport:sea:vessel` |

