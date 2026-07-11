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
| `base:activity` |
| `entity:participable` |
| `meta:believable` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this belief system. |
| `:desc` | `text` | A description of the belief system. |
| `:name` | `base:name` | The name of the belief system. |
| `:period` | `activity` | The period over which the belief system was active. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `belief:system:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `belief:tenet`

A concrete tenet potentially shared by multiple belief systems.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `meta:believable` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this tenet. |
| `:desc` | `text` | A description of the tenet. |
| `:name` | `base:name` | The name of the tenet. |
| `:period` | `activity` | The period over which the tenet was active. |

### `biz:deal`

A sales or procurement effort in pursuit of a purchase.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |
| `meta:negotiable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:buyer` | `entity:actor` | The buyer. |
| `:buyer:name` | `entity:name` | The name of the buyer. |
| `:contacted` | `time` | The last time the contacts communicated about the deal. |
| `:id` | `base:id` | An identifier for the deal. |
| `:name` | `base:name` | The name of the deal. |
| `:period` | `activity` | The period over which the activity occurred. |
| `:seller` | `entity:actor` | The seller. |
| `:seller:name` | `entity:name` | The name of the seller. |
| `:status` | `title` | The status of the deal. |
| `:type` | `biz:deal:type:taxonomy` | The type of deal. |
| `:updated` | `time` | The last time the deal had a significant update. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `biz:deal:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:activity` | `base:activity` | A parent activity which includes this listing. |
| `:actor` | `entity:actor` | The actor who posted the listing. |
| `:actor:name` | `entity:name` | The name of the actor who posted the listing. |
| `:count:remaining` | `size` | The current remaining number of instances for sale. |
| `:count:total` | `size` | The number of instances for sale. |
| `:name` | `base:name` | The name or title of the listing. |
| `:period` | `activity` | The period over which the listing occurred. |
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
| `:creator` | `entity:actor` | The primary actor which created the product. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the product. |
| `:desc` | `text` | A description of the product. |
| `:launched` | `time` | The time the product was first made available. |
| `:name` | `base:name` | The name of the product. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `biz:product:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:status` | `title` | The status of the RFP. |
| `:supersedes` | `array of biz:rfp` | An array of RFP versions which are superseded by this RFP. |
| `:title` | `title` | The title of the RFP. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `biz:rfp:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:activity` | `base:activity` | A parent activity which includes this service offering. |
| `:actor` | `entity:actor` | The actor who provided the service offering. |
| `:actor:name` | `entity:name` | The name of the actor who provided the service offering. |
| `:desc` | `text` | A description of the service. |
| `:name` | `base:name` | The name of the service being performed. |
| `:period` | `activity` | The period of time when the actor made the service available. |
| `:type` | `biz:service:type:taxonomy` | The type of service. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `biz:service:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `crypto:currency:address`

An individual crypto currency address.

| Interface |
|-----------|
| `econ:pay:instrument` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:account` | The account that contains the funds used by the crypto currency address. |
| `:chain` | `crypto:currency:chain` | The chain where the address is defined. |
| `:contact` | `entity:contactable` | The primary contact information associated with the crypto currency address. |
| `:desc` | `text` | A free-form description of the address. |
| `:iden` | `str` | The chain specific address identifier. |
| `:seed` | `crypto:key` | The cryptographic key and or password used to generate the address. |
| `:seen` | `ival` | The crypto currency address was observed during the time interval. |

### `crypto:currency:block`

An individual crypto currency block record on the blockchain.

| Property | Type | Doc |
|----------|------|-----|
| `:chain` | `crypto:currency:chain` | The chain where the block is recorded. |
| `:hash` | `hex` | The unique hash for the block. |
| `:minedby` | `crypto:currency:address` | The address which mined the block. |
| `:offset` | `int` | The index of this block. |
| `:time` | `time` | Time timestamp embedded in the block by the miner. |

### `crypto:currency:chain`

A crypto currency chain.

| Property | Type | Doc |
|----------|------|-----|
| `:id` | `base:id` | An ID for the chain. |
| `:name` | `base:name` | The name of the chain. |
| `:symbol` | `econ:currency` | The symbol associated with the native currency of the chain. |

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
| `:block:chain` | `crypto:currency:chain` | The chain where the transaction is recorded. |
| `:contract:input` | `file:bytes` | Input value to a smart contract call. |
| `:contract:output` | `file:bytes` | Output value of a smart contract call. |
| `:desc` | `text` | An analyst specified description of the transaction. |
| `:fee` | `econ:price` | The total fee paid to execute the transaction. |
| `:fee:asked` | `econ:price` | The fee requested to execute the transaction. |
| `:fee:limit` | `econ:price` | The maximum fee allowed to execute the transaction. |
| `:from` | `crypto:currency:address` | The source address of the transaction. |
| `:hash` | `hex` | The unique transaction hash for the transaction. |
| `:status:code` | `int` | A coin specific status code which may represent an error reason. |
| `:status:message` | `text` | A coin specific status message which may contain an error reason. |
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

### `crypto:hash:ssdeep`

A fuzzy hash of a file in ssdeep format.

| Interface |
|-----------|
| `crypto:hash` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The ssdeep was observed during the time interval. |

### `crypto:key:base`

A generic cryptographic key.

| Interface |
|-----------|
| `crypto:key` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:algorithm` | `meta:algorithm` | The algorithm which uses the key material. |
| `:bits` | `size` | The number of bits of key material. |
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
| `:algorithm` | `meta:algorithm` | The algorithm which uses the key material. |
| `:bits` | `size` | The number of bits of key material. |
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
| `:algorithm` | `meta:algorithm` | The algorithm which uses the key material. |
| `:bits` | `size` | The number of bits of key material. |
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
| `:algorithm` | `meta:algorithm` | The algorithm which uses the key material. |
| `:bits` | `size` | The number of bits of key material. |
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
| `:algorithm` | `meta:algorithm` | The algorithm which uses the key material. |
| `:bits` | `size` | The number of bits of key material. |
| `:iv` | `hex` | The hex encoded initialization vector. |
| `:mode` | `base:name` | The algorithm specific mode in use. |
| `:seed:algorithm` | `meta:algorithm` | The algorithm used to generate the key from the seed password. |
| `:seed:passwd` | `auth:passwd` | The seed password used to generate the key material. |
| `:seen` | `ival` | The secret key was observed during the time interval. |
| `:value` | `hex` | The hex encoded secret key. |

### `crypto:payment:input`

A payment made into a transaction.

| Property | Type | Doc |
|----------|------|-----|
| `:address` | `crypto:currency:address` | The address which paid into the transaction. |
| `:index` | `int` | The index of this input in the array of inputs for the transaction. |
| `:transaction` | `crypto:currency:transaction` | The transaction the payment was input to. |
| `:value` | `econ:price` | The value of the currency paid into the transaction. |

### `crypto:payment:output`

A payment received from a transaction.

| Property | Type | Doc |
|----------|------|-----|
| `:address` | `crypto:currency:address` | The address which received payment from the transaction. |
| `:index` | `int` | The index of this output in the array of outputs for the transaction. |
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
| `:token:name` | `base:name` | The ERC-20 token name. |
| `:token:symbol` | `econ:currency` | The ERC-20 token symbol. |
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
| `:amount` | `hugenum` | The amount of tokens the proxy is allowed to manipulate. |
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
| `:issuer` | `title` | The Distinguished Name (DN) of the Certificate Authority (CA) which issued the certificate. |
| `:issuer:cert` | `crypto:x509:cert` | The certificate used by the issuer to sign this certificate. |
| `:issuer:rdns` | `array of crypto:x509:rdn` | The decomposed RDN parts of the certificate issuer Distinguished Name (DN). |
| `:key` | `crypto:key:dsa`, `crypto:key:rsa` | The public key embedded in the certificate. |
| `:md5` | `crypto:hash:md5` | The MD5 fingerprint for the certificate. |
| `:seen` | `ival` | The X.509 certificate was observed during the time interval. |
| `:selfsigned` | `bool` | Set to true if the certificate is self-signed. |
| `:serial` | `crypto:x509:serial` | The certificate serial number as a big endian hex value. |
| `:sha1` | `crypto:hash:sha1` | The SHA1 fingerprint for the certificate. |
| `:sha256` | `crypto:hash:sha256` | The SHA256 fingerprint for the certificate. |
| `:signature` | `hex` | The hexadecimal representation of the digital signature. |
| `:subject` | `title` | The subject identifier, commonly in X.500/LDAP format, to which the certificate was issued. |
| `:subject:rdns` | `array of crypto:x509:rdn` | The decomposed RDN parts of the certificate subject Distinguished Name (DN). |
| `:validity:notafter` | `time` | The timestamp for the end of the certificate validity period. |
| `:validity:notbefore` | `time` | The timestamp for the beginning of the certificate validity period. |
| `:version` | `crypto:x509:version` | The version integer in the certificate. (ex. 2 == v3 ). |

### `crypto:x509:crl`

A unique X.509 Certificate Revocation List.

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file containing the CRL. |
| `:url` | `inet:url` | The URL where the CRL was published. |

### `crypto:x509:rdn`

An X.509 Relative Distinguished Name (RDN) attribute and value pair.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `str:upper` | The RDN attribute name. |
| `:value` | `title` | The RDN attribute value. |

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
| `:activity` | `base:activity` | A parent activity which includes this contract. |
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
| `:period` | `activity` | The period over which the contract occurred. |
| `:signed` | `time` | The date that the contract signing was complete. |
| `:supersedes` | `array of doc:contract` | An array of contract versions which are superseded by this contract. |
| `:title` | `title` | The title of the contract. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `doc:contract:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:title` | `title` | The title of the policy. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `doc:policy:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `doc:reference`

A reference included in a source.

| Property | Type | Doc |
|----------|------|-----|
| `:doc` | `doc:document` | The document which the reference refers to. |
| `:doc:url` | `inet:url` | A URL for the reference. |
| `:source` | `doc:report`, `entity:campaign`, `it:software`, `meta:technique`, `plan:phase`, `risk:threat`, `risk:vuln` | The source which contains the reference. |
| `:text` | `title` | A reference string included in the source. |

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
| `:title` | `title` | The title of the report. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `doc:report:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:title` | `title` | The title of the resume. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `doc:resume:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:title` | `title` | The title of the standard. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `doc:standard:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `econ:account`

A financial account which contains a balance of funds.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:balance` | `econ:price` | The most recently known balance of the account. |
| `:holder` | `entity:contactable` | The contact information of the account holder. |
| `:id` | `base:id` | The ID or account number of the account. |
| `:ids` | `array of base:id` | An array of IDs or account numbers for the account. |
| `:issuer` | `entity:actor` | The financial institution which issued the account. |
| `:issuer:name` | `entity:name` | The name of the financial institution which issued the account. |
| `:seen` | `ival` | The financial account was observed during the time interval. |
| `:type` | `econ:account:type:taxonomy` | The type of financial account. |

### `econ:account:type:taxonomy`

A financial account type taxonomy.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `econ:account:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `econ:balance`

The balance of funds available in an account at specific time.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:account` | The financial account holding the balance. |
| `:amount` | `econ:price` | The available funds at the time. |
| `:change` | `econ:pricechange` | The change in the account balance since the previous balance sample. |
| `:previous` | `econ:balance` | The previous balance sample for the account. |
| `:time` | `time` | The time the balance was recorded. |

### `econ:bank:aba:rtn`

An American Bank Association (ABA) routing transit number (RTN).

| Interface |
|-----------|
| `econ:bank:routing:code` |
| `entity:identifier` |

| Property | Type | Doc |
|----------|------|-----|
| `:bank` | `ou:org` | The bank or branch which the routing identifier refers to. |
| `:bank:name` | `entity:name` | The name of the bank or branch. |

### `econ:bank:account`

A bank account paired with the routing identifier that addresses it.

| Interface |
|-----------|
| `econ:pay:instrument` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:account` | The account that contains the funds used by the bank account. |
| `:id` | `base:id` | The account identifier within the routing system. |
| `:routing` | `econ:bank:routing:code` | The bank routing identifier portion of the account identifier. |

### `econ:bank:check`

A check written out to a recipient.

| Interface |
|-----------|
| `econ:pay:instrument` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:account` | The account that contains the funds used by the check. |
| `:amount` | `econ:price` | The amount the check is written for. |
| `:bank:account` | `econ:bank:account` | The bank account the check is drawn against. |
| `:payto` | `entity:name` | The name of the intended recipient. |
| `:seen` | `ival` | The check was observed during the time interval. |

### `econ:bank:iban`

An International Bank Account Number.

| Interface |
|-----------|
| `econ:pay:instrument` |
| `entity:identifier` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:account` | The account that contains the funds used by the IBAN account. |

### `econ:bank:routing:id`

A generic bank routing identifier for routing systems without a dedicated form.

| Interface |
|-----------|
| `econ:bank:routing:code` |
| `entity:identifier` |

| Property | Type | Doc |
|----------|------|-----|
| `:bank` | `ou:org` | The bank or branch which the routing identifier refers to. |
| `:bank:name` | `entity:name` | The name of the bank or branch. |
| `:type` | `econ:bank:routing:type:taxonomy` | The kind of bank routing system this identifier belongs to. |

### `econ:bank:routing:type:taxonomy`

A taxonomy of bank routing identifier systems.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `econ:bank:routing:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `econ:bank:swift:bic`

A Society for Worldwide Interbank Financial Telecommunication (SWIFT) Business Identifier Code (BIC).

| Interface |
|-----------|
| `econ:bank:routing:code` |
| `entity:identifier` |

| Property | Type | Doc |
|----------|------|-----|
| `:bank` | `ou:org` | The bank or branch which the routing identifier refers to. |
| `:bank:name` | `entity:name` | The name of the bank or branch. |
| `:office` | `entity:contact` | The branch or office which is specified in the last 3 digits of the SWIFT BIC. |

### `econ:budget`

A budget of funds allocated and spent over a period.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this budget. |
| `:actor` | `entity:actor` | The actor who managed the budget. |
| `:actor:name` | `entity:name` | The name of the actor who managed the budget. |
| `:funds` | `econ:allocation` | The funds allocated and spent over the period. |
| `:id` | `base:id` | The ID of the budget. |
| `:name` | `title` | The name of the budget. |
| `:period` | `activity` | The period over which the budget was in effect. |
| `:previous` | `econ:budget` | The budget for the previous period. |

### `econ:currency`

A currency. This should ideally be an ISO 4217 currency code when one is available.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The full name of the currency. |

### `econ:exchange`

A financial exchange where securities are traded.

| Property | Type | Doc |
|----------|------|-----|
| `:currency` | `econ:currency` | The currency used for all transactions in the exchange. |
| `:operator` | `entity:actor` | The entity which operates the exchange. |
| `:operator:name` | `entity:name` | The name of the entity which operates the exchange. |

### `econ:invoice`

An invoice issued requesting payment.

| Property | Type | Doc |
|----------|------|-----|
| `:amount` | `econ:price` | The balance due. |
| `:due` | `time` | The time by which the payment is due. |
| `:issued` | `time` | The time that the invoice was issued to the recipient. |
| `:issuer` | `entity:actor` | The entity which issued the invoice. |
| `:paid` | `bool` | Set to true if the invoice has been paid in full. |
| `:purchase` | `econ:purchase` | The purchase that the invoice is requesting payment for. |
| `:recipient` | `entity:actor` | The entity which received the invoice. |

### `econ:lineitem`

A line item included as part of a purchase.

| Property | Type | Doc |
|----------|------|-----|
| `:count` | `size` | The number of items included in this line item. |
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
| `:account` | `econ:account` | The account that contains the funds used by the payment card. |
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

### `econ:pay:pan`

A Primary Account Number (PAN) or card number.

| Property | Type | Doc |
|----------|------|-----|
| `:iin` | `econ:pay:iin` | The Issuer Identification Number (IIN) of the PAN. |
| `:mii` | `econ:pay:mii` | The Major Industry Identifier (MII) of the PAN. |

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
| `:activity` | `base:activity` | A parent activity which includes this payment event. |
| `:actor` | `entity:actor` | The actor who carried out the payment event. |
| `:actor:account` | `econ:account` | The account the payment was made from. |
| `:actor:instrument` | `econ:pay:instrument` | The payment instrument used by the actor to make the payment. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the payment event. |
| `:amount` | `econ:price` | The amount of money transferred in the payment. |
| `:cash` | `bool` | Set to true if the payment was made with physical currency. |
| `:crypto:transaction` | `crypto:currency:transaction` | A crypto currency transaction that initiated the payment. |
| `:fee` | `econ:price` | The transaction fee paid by the recipient to the payment processor. |
| `:id` | `base:id` | A payment processor specific transaction ID. |
| `:payee` | `entity:actor` | The entity which received the payment. |
| `:payee:account` | `econ:account` | The account the payment was received into. |
| `:payee:instrument` | `econ:pay:instrument` | The payment instrument used by the payee to receive payment. |
| `:place` | `geo:place` | The place where the payment event was located. |
| `:place:address` | `geo:address` | The postal address where the payment event was located. |
| `:place:address:city` | `base:name` | The city where the payment event was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the payment event was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the payment event was located. |
| `:place:country` | `pol:country` | The country where the payment event was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the payment event was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the payment event was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the payment event was located. |
| `:place:loc` | `loc` | The geopolitical location where the payment event was located. |
| `:place:name` | `geo:name` | The name of the place where the payment event was located. |
| `:status` | `title` | The status of the payment. |
| `:time` | `time` | The time the payment was made. |

### `econ:price:adjusted`

An inflation or currency adjusted price.

| Property | Type | Doc |
|----------|------|-----|
| `:currency` | `econ:currency` | The currency to which the price was adjusted. |
| `:time` | `time` | The time to which the price was adjusted. |
| `:value` | `econ:price` | The adjusted price value. |

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
| `:activity` | `base:activity` | A parent activity which includes this purchase. |
| `:actor` | `entity:actor` | The actor who made the purchase. |
| `:actor:name` | `entity:name` | The name of the actor who made the purchase. |
| `:paid` | `time` | The time when the purchase was paid in full. |
| `:place` | `geo:place` | The place where the purchase was located. |
| `:place:address` | `geo:address` | The postal address where the purchase was located. |
| `:place:address:city` | `base:name` | The city where the purchase was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the purchase was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the purchase was located. |
| `:place:country` | `pol:country` | The country where the purchase was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the purchase was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the purchase was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the purchase was located. |
| `:place:loc` | `loc` | The geopolitical location where the purchase was located. |
| `:place:name` | `geo:name` | The name of the place where the purchase was located. |
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
| `:issuer` | `entity:actor` | The entity which issued the receipt. |
| `:purchase` | `econ:purchase` | The purchase that the receipt confirms payment for. |
| `:recipient` | `entity:actor` | The entity which received the receipt. |

### `econ:security`

A financial security which is typically traded on an exchange.

| Property | Type | Doc |
|----------|------|-----|
| `:exchange` | `econ:exchange` | The exchange on which the security is traded. |
| `:price` | `econ:price` | The last known/available price of the security. |
| `:ticker` | `title` | The identifier for this security within the exchange. |
| `:time` | `time` | The time of the last know price sample. |
| `:type` | `econ:security:type:taxonomy` | The type of security. |

### `econ:security:ochlv`

A sample of the open, close, high, low prices and volume of a security in a specific time window.

| Property | Type | Doc |
|----------|------|-----|
| `:change` | `econ:pricechange` | The open to close price change of the security during the period. |
| `:exchange` | `econ:exchange` | The exchange on which the security was traded during the period. |
| `:period` | `ival` | The interval of measurement. |
| `:previous` | `econ:security:ochlv` | The preceding OCHLV sample. |
| `:range` | `econ:pricerange` | The low to high price range of the security during the period. |
| `:security` | `econ:security` | The security measured by the sample. |
| `:volume` | `hugenum` | The traded volume of the security during the period. |
| `:volume:delta` | `hugenum` | The change in traded volume since the previous sample. |
| `:volume:delta:rate` | `ratio` | The volume delta as a percent of the previous sample. |

### `econ:security:telem`

A sample of the price of a security at a single moment in time.

| Property | Type | Doc |
|----------|------|-----|
| `:exchange` | `econ:exchange` | The exchange on which the security was traded at the time. |
| `:price` | `econ:price` | The price of the security at the time. |
| `:security` | `econ:security` | The security measured by the telemetry sample. |
| `:time` | `time` | The time the price was sampled. |

### `econ:security:type:taxonomy`

A hierarchical taxonomy of financial security types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `econ:security:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `econ:statement`

A statement of starting/ending balance and payments for a financial instrument over a time period.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:account` | The financial account described by the statement. |
| `:balance` | `econ:price` | The balance at the end of the statement period. |
| `:period` | `ival` | The period that the statement includes. |
| `:previous` | `econ:statement` | The statement for the previous period. |

### `edu:class`

An instance of an edu:course taught at a given time.

| Interface |
|-----------|
| `base:activity` |
| `entity:attendable` |
| `entity:participable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this class. |
| `:assistants` | `array of entity:individual` | An array of assistant/co-instructor contacts. |
| `:course` | `edu:course` | The course being taught in the class. |
| `:desc` | `text` | A description of the class. |
| `:instructor` | `entity:individual` | The primary instructor for the class. |
| `:name` | `base:name` | The name of the class. |
| `:period` | `activity:day` | The period over which the class was run. |
| `:place` | `geo:place` | The place where the class was located. |
| `:place:address` | `geo:address` | The postal address where the class was located. |
| `:place:address:city` | `base:name` | The city where the class was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the class was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the class was located. |
| `:place:country` | `pol:country` | The country where the class was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the class was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the class was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the class was located. |
| `:place:loc` | `loc` | The geopolitical location where the class was located. |
| `:place:name` | `geo:name` | The name of the place where the class was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the class. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the class. |
| `:remote` | `percent` | The percentage of the class which may be attended remotely. |
| `:remote:provider` | `entity:actor` | Contact info for the remote infrastructure provider. |
| `:remote:provider:name` | `entity:name` | The name of the remote infrastructure provider. |
| `:remote:url` | `inet:url` | The URL a student would use to attend the class remotely. |
| `:type` | `edu:class:type:taxonomy` | The type of class. |

### `edu:class:type:taxonomy`

A hierarchical taxonomy of edu:class types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `edu:class:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:desc` | `text` | A brief course description. |
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
| `:activity` | `base:activity` | A parent activity which includes this achievement. |
| `:actor` | `entity:actor` | The actor who earned the achievement. |
| `:actor:name` | `entity:name` | The name of the actor who earned the achievement. |
| `:time` | `time` | The time that the achievement occurred. |

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
| `:actor` | `entity:actor` | The actor who made the ask. |
| `:actor:name` | `entity:name` | The name of the actor who made the ask. |
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
| `:activity` | `entity:attendable` | The activity attended by the actor. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:inperson` | `bool` | Set if the actor attended the activity in person. |
| `:period` | `activity` | The period over which the activity occurred. |
| `:role` | `entity:title` | The role the actor played in attending the activity. |

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
| `:activity` | `base:activity` | A parent activity which includes this belief. |
| `:actor` | `entity:actor` | The actor who held the belief. |
| `:actor:name` | `entity:name` | The name of the actor who held the belief. |
| `:belief` | `meta:believable` | The belief held by the actor. |
| `:period` | `activity` | The period over which the belief was held. |

### `entity:campaign`

Activity in pursuit of a goal.

| Interface |
|-----------|
| `base:activity` |
| `econ:budgetable` |
| `entity:action` |
| `entity:activity` |
| `entity:participable` |
| `entity:supportable` |
| `meta:causal` |
| `meta:observable` |
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this campaign. |
| `:actor` | `entity:actor` | The actor who carried out the campaign. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the campaign. |
| `:budget` | `econ:budget` | The budget for the campaign. |
| `:cost` | `econ:price` | The actual cost of the campaign. |
| `:desc` | `text` | A description of the campaign. |
| `:id` | `base:id`, `it:mitre:attack:campaign:id` | A unique ID given to the campaign. |
| `:ids` | `array of base:id, it:mitre:attack:campaign:id` | An array of alternate IDs given to the campaign. |
| `:name` | `entity:name` | The primary name of the campaign. |
| `:names` | `array of entity:name` | A list of alternate names for the campaign. |
| `:period` | `activity` | The period over which the campaign occurred. |
| `:reporter` | `entity:actor` | The entity which reported on the campaign. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the campaign. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the campaign. |
| `:reporter:period` | `reported` | The period when the campaign existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the campaign. |
| `:reporter:supersedes` | `array of entity:campaign` | An array of campaign nodes which are superseded by this campaign. |
| `:reporter:updated` | `time` | The time when the campaign was last updated. |
| `:reporter:url` | `inet:url` | The URL for the campaign provided by the reporter. |
| `:resolved` | `entity:campaign` | The authoritative campaign which this reporting is about. |
| `:seen` | `ival` | The campaign was observed during the time interval. |
| `:slogan` | `lang:phrase` | The slogan used by the campaign. |
| `:sophistication` | `meta:score` | The assessed sophistication of the campaign. |
| `:success` | `bool` | Set to true if the campaign achieved its goals. |
| `:tag` | `syn:tag` | The tag used to annotate nodes that are associated with the campaign. |
| `:type` | `entity:campaign:type:taxonomy` | A type taxonomy entry for the campaign. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `entity:campaign:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `entity:conflict`

Represents a conflict where two or more campaigns have mutually exclusive goals.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this conflict. |
| `:adversaries` | `array of entity:actor` | The primary adversaries in conflict with one another. |
| `:name` | `event:name` | The name of the conflict. |
| `:period` | `activity` | The period over which the conflict occurred. |

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
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:banner` | `file:bytes` | A banner or hero image used on the profile page. |
| `:bio` | `text` | A tagline or bio provided for the contact. |
| `:birth:place` | `geo:place` | The place where the contact was born. |
| `:birth:place:address` | `geo:address` | The postal address where the contact was born. |
| `:birth:place:address:city` | `base:name` | The city where the contact was born. |
| `:birth:place:altitude` | `geo:altitude` | The altitude where the contact was born. |
| `:birth:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the contact was born. |
| `:birth:place:country` | `pol:country` | The country where the contact was born. |
| `:birth:place:country:code` | `iso:3166:alpha2` | The country code where the contact was born. |
| `:birth:place:latlong` | `geo:latlong` | The latlong where the contact was born. |
| `:birth:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the contact was born. |
| `:birth:place:loc` | `loc` | The geopolitical location where the contact was born. |
| `:birth:place:name` | `geo:name` | The name of the place where the contact was born. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the contact. |
| `:death:place` | `geo:place` | The place where the contact died. |
| `:death:place:address` | `geo:address` | The postal address where the contact died. |
| `:death:place:address:city` | `base:name` | The city where the contact died. |
| `:death:place:altitude` | `geo:altitude` | The altitude where the contact died. |
| `:death:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the contact died. |
| `:death:place:country` | `pol:country` | The country where the contact died. |
| `:death:place:country:code` | `iso:3166:alpha2` | The country code where the contact died. |
| `:death:place:latlong` | `geo:latlong` | The latlong where the contact died. |
| `:death:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the contact died. |
| `:death:place:loc` | `loc` | The geopolitical location where the contact died. |
| `:death:place:name` | `geo:name` | The name of the place where the contact died. |
| `:desc` | `text` | A description of the contact. |
| `:email` | `inet:email` | The primary email address for the contact. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the contact. |
| `:id` | `base:id` | A type or source specific ID for the contact. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:lang` | `lang:language` | The primary language of the contact. |
| `:langs` | `array of lang:language` | An array of alternate languages for the contact. |
| `:lifespan` | `entity:lifespan` | The lifespan of the contact. |
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
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the contact was located. |
| `:place:country` | `pol:country` | The country where the contact was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the contact was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the contact was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the contact was located. |
| `:place:loc` | `loc` | The geopolitical location where the contact was located. |
| `:place:name` | `geo:name` | The name of the place where the contact was located. |
| `:resolved` | `ou:org`, `ps:person` | The resolved entity to which this contact belongs. |
| `:seen` | `ival` | The contact was observed during the time interval. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the contact. |
| `:title` | `entity:title` | The entity title or role for this contact. |
| `:titles` | `array of entity:title` | An array of alternate entity titles or roles for this contact. |
| `:type` | `entity:contact:type:taxonomy` | The contact type. |
| `:username` | `entity:name` | The primary user name for the contact. |
| `:usernames` | `array of entity:name` | An array of alternate user names for the contact. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `entity:contact:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `entity:contactlist`

A list of contacts.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the contact list. |
| `:name` | `base:name` | The name of the contact list. |
| `:source` | `file:bytes`, `inet:service:account`, `it:host` | The source that the contact list was extracted from. |

### `entity:contactlist:entry`

An entry in a contact list.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:contact` | The contact which was included in the list. |
| `:list` | `entity:contactlist` | The contact list which contains the entry. |
| `:period` | `ival` | The time period when the contact was included in the list. |

### `entity:contributed`

Represents a specific instance of contributing material support to a campaign.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this contribution. |
| `:actor` | `entity:actor` | The actor who made the contribution. |
| `:actor:name` | `entity:name` | The name of the actor who made the contribution. |
| `:campaign` | `entity:campaign` | The campaign receiving the contribution. |
| `:time` | `time` | The time that the contribution occurred. |
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
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:item` | `entity:creatable` | The item which the actor helped to create. |
| `:period` | `activity` | The period over which the activity occurred. |
| `:role` | `entity:title` | The role which the actor played in creating the item. |

### `entity:destroyed`

An event where an actor destroyed an item.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this destruction. |
| `:actor` | `entity:actor` | The actor who carried out the destruction. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the destruction. |
| `:item` | `entity:destroyable` | The item destroyed by the actor. |
| `:time` | `time` | The time that the destruction occurred. |

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
| `:activity` | `base:activity` | A parent activity which includes this discovery. |
| `:actor` | `entity:actor` | The actor who made the discovery. |
| `:actor:name` | `entity:name` | The name of the actor who made the discovery. |
| `:item` | `meta:discoverable` | The item discovered by the actor. |
| `:time` | `time` | The time that the discovery occurred. |

### `entity:goal`

A stated or assessed goal.

| Interface |
|-----------|
| `meta:achievable` |
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the goal. |
| `:id` | `base:id` | A unique ID given to the goal. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the goal. |
| `:name` | `base:name` | A terse name for the goal. |
| `:names` | `array of base:name` | Alternative names for the goal. |
| `:reporter` | `entity:actor` | The entity which reported on the goal. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the goal. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the goal. |
| `:reporter:period` | `reported` | The period when the goal existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the goal. |
| `:reporter:supersedes` | `array of entity:goal` | An array of goal nodes which are superseded by this goal. |
| `:reporter:updated` | `time` | The time when the goal was last updated. |
| `:reporter:url` | `inet:url` | The URL for the goal provided by the reporter. |
| `:resolved` | `entity:goal` | The authoritative goal which this reporting is about. |
| `:type` | `entity:goal:type:taxonomy` | A type taxonomy entry for the goal. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `entity:goal:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `entity:had`

An item which was possessed by an actor.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this possession. |
| `:actor` | `entity:actor` | The entity which had the item. |
| `:actor:name` | `entity:name` | The name of the entity which had the item. |
| `:item` | `meta:havable` | The item possessed by the entity. |
| `:period` | `activity` | The time period when the entity had the item. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `entity:had:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:lifespan` | `entity:lifespan` | The lifespan of the contact history. |
| `:name` | `entity:name` | The primary entity name of the contact history. |
| `:names` | `array of entity:name` | An array of alternate entity names for the contact history. |
| `:phone` | `tel:phone` | The primary phone number for the contact history. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the contact history. |
| `:photo` | `file:bytes` | The profile picture or avatar for this contact history. |
| `:place` | `geo:place` | The place where the contact history was located. |
| `:place:address` | `geo:address` | The postal address where the contact history was located. |
| `:place:address:city` | `base:name` | The city where the contact history was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the contact history was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the contact history was located. |
| `:place:country` | `pol:country` | The country where the contact history was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the contact history was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the contact history was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the contact history was located. |
| `:place:loc` | `loc` | The geopolitical location where the contact history was located. |
| `:place:name` | `geo:name` | The name of the place where the contact history was located. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the contact history. |
| `:username` | `entity:name` | The primary user name for the contact history. |
| `:usernames` | `array of entity:name` | An array of alternate user names for the contact history. |
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
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:goal` | `entity:goal` | The goal which motivated the actor. |
| `:period` | `activity` | The period over which the activity occurred. |

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
| `:actor` | `entity:actor` | The actor who made the offer. |
| `:actor:name` | `entity:name` | The name of the actor who made the offer. |
| `:expires` | `time` | The time that the offer expires. |
| `:time` | `time` | The time that the offer occurred. |
| `:value` | `econ:price` | The value of the offer. |

### `entity:owned`

An item which was owned by an actor.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this ownership. |
| `:actor` | `entity:actor` | The entity which owned the item. |
| `:actor:name` | `entity:name` | The name of the entity which owned the item. |
| `:item` | `meta:havable` | The item possessed by the entity. |
| `:percent` | `percent` | The percentage of the item owned by the owner. |
| `:period` | `activity` | The period over which the ownership occurred. |
| `:type` | `entity:had:type:taxonomy` | A taxonomy for different types of possession. |

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
| `:actor` | `entity:actor` | The actor who participated in the activity. |
| `:actor:name` | `entity:name` | The name of the actor who participated in the activity. |
| `:period` | `activity` | The period over which the participation occurred. |
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
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:level` | `meta:score` | The level of proficiency. |
| `:period` | `activity` | The period over which the activity occurred. |
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
| `:desc` | `text` | A description of the relationship. |
| `:id` | `base:id` | A unique ID given to the relationship. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the relationship. |
| `:name` | `base:name` | The primary name of the relationship. |
| `:names` | `array of base:name` | A list of alternate names for the relationship. |
| `:period` | `ival` | The time period when the relationship existed. |
| `:reporter` | `entity:actor` | The entity which reported on the relationship. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the relationship. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the relationship. |
| `:reporter:period` | `reported` | The period when the relationship existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the relationship. |
| `:reporter:supersedes` | `array of entity:relationship` | An array of relationship nodes which are superseded by this relationship. |
| `:reporter:updated` | `time` | The time when the relationship was last updated. |
| `:reporter:url` | `inet:url` | The URL for the relationship provided by the reporter. |
| `:resolved` | `entity:relationship` | The authoritative relationship which this reporting is about. |
| `:source` | `entity:actor` | The source entity in the relationship. |
| `:target` | `entity:actor` | The target entity in the relationship. |
| `:type` | `entity:relationship:type:taxonomy` | The type of relationship. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `entity:relationship:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:activity` | `base:activity` | A parent activity which includes this statement. |
| `:actor` | `entity:actor` | The actor who made the statement. |
| `:actor:name` | `entity:name` | The name of the actor who made the statement. |
| `:period` | `activity` | The period over which the statement occurred. |
| `:recording:file` | `file:bytes` | A file containing a recording of the statement. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the statement. |
| `:text` | `text` | The transcribed text of what the actor said. |

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
| `:activity` | `base:activity` | A parent activity which includes this signing. |
| `:actor` | `entity:actor` | The actor who carried out the signing. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the signing. |
| `:doc` | `doc:signable` | The document which the actor signed. |
| `:time` | `time` | The time that the signing occurred. |

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
| `:activity` | `base:activity` | A parent activity which includes this study. |
| `:actor` | `entity:actor` | The actor who undertook the study. |
| `:actor:name` | `entity:name` | The name of the actor who undertook the study. |
| `:institution` | `ou:org` | The organization providing educational services. |
| `:period` | `activity` | The period over which the study occurred. |

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
| `:period` | `activity` | The period over which the activity occurred. |
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
| `file:entry` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:archived:size` | `size` | The storage size of the file within the archive. |
| `:created` | `time` | The created time of the file. |
| `:file` | `file:bytes` | The file associated with the archive file entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:offset` | `size` | The offset to the beginning of the file within the parent file. |
| `:parent` | `file:bytes` | The parent file which contains the archive file entry. |
| `:path` | `file:path` | The path of the file associated with the archive file entry. |
| `:seen` | `ival` | The archive file entry was observed during the time interval. |

### `file:attachment`

A file attachment.

| Interface |
|-----------|
| `file:entry` |
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file associated with the file attachment. |
| `:path` | `file:path` | The path of the file associated with the file attachment. |
| `:seen` | `ival` | The file attachment was observed during the time interval. |
| `:text` | `text` | Any text associated with the file such as alt-text for images. |

### `file:base`

A file name with no path.

| Interface |
|-----------|
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:ext` | `text` | The file extension (if any). |
| `:seen` | `ival` | The file name was observed during the time interval. |

### `file:bytes`

A file.

| Interface |
|-----------|
| `meta:observable` |
| `meta:usable` |

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
| `:ssdeeps` | `array of crypto:hash:ssdeep` | The ssdeep fuzzy hashes of the file. |

### `file:exemplar:entry`

An exemplar file entry used to model behavior.

| Interface |
|-----------|
| `file:entry` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file associated with the exemplar file entry. |
| `:path` | `file:path` | The path of the file associated with the exemplar file entry. |
| `:seen` | `ival` | The exemplar file entry was observed during the time interval. |

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
| `:author:name` | `entity:name` | MIME specific author name extracted from metadata. |
| `:comment` | `text` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `text` | MIME specific description field extracted from metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `text` | The text contained within the image. |

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
| `:author:name` | `entity:name` | MIME specific author name extracted from metadata. |
| `:comment` | `text` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `text` | MIME specific description field extracted from metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `text` | The text contained within the image. |

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
| `:relative` | `file:path` | The relative target path string contained within the StringData structure of the LNK file. |
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
| `:version` | `it:version` | The version of the Mach-O file encoded in an LC_VERSION load command. |

### `file:mime:msdoc`

Metadata about a Microsoft Word file.

| Interface |
|-----------|
| `file:mime:meta` |
| `file:mime:msoffice` |

| Property | Type | Doc |
|----------|------|-----|
| `:application` | `it:software` | The creating application extracted from Microsoft Office metadata. |
| `:application:name` | `it:softwarename` | The creating application name extracted from Microsoft Office metadata. |
| `:author` | `entity:contact` | The author extracted from Microsoft Office metadata. |
| `:author:name` | `entity:name` | The author name extracted from Microsoft Office metadata. |
| `:created` | `time` | The create_time extracted from Microsoft Office metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:lastsaved` | `time` | The last_saved_time extracted from Microsoft Office metadata. |
| `:subject` | `text` | The subject extracted from Microsoft Office metadata. |
| `:title` | `text` | The title extracted from Microsoft Office metadata. |

### `file:mime:msppt`

Metadata about a Microsoft Powerpoint file.

| Interface |
|-----------|
| `file:mime:meta` |
| `file:mime:msoffice` |

| Property | Type | Doc |
|----------|------|-----|
| `:application` | `it:software` | The creating application extracted from Microsoft Office metadata. |
| `:application:name` | `it:softwarename` | The creating application name extracted from Microsoft Office metadata. |
| `:author` | `entity:contact` | The author extracted from Microsoft Office metadata. |
| `:author:name` | `entity:name` | The author name extracted from Microsoft Office metadata. |
| `:created` | `time` | The create_time extracted from Microsoft Office metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:lastsaved` | `time` | The last_saved_time extracted from Microsoft Office metadata. |
| `:subject` | `text` | The subject extracted from Microsoft Office metadata. |
| `:title` | `text` | The title extracted from Microsoft Office metadata. |

### `file:mime:msxls`

Metadata about a Microsoft Excel file.

| Interface |
|-----------|
| `file:mime:meta` |
| `file:mime:msoffice` |

| Property | Type | Doc |
|----------|------|-----|
| `:application` | `it:software` | The creating application extracted from Microsoft Office metadata. |
| `:application:name` | `it:softwarename` | The creating application name extracted from Microsoft Office metadata. |
| `:author` | `entity:contact` | The author extracted from Microsoft Office metadata. |
| `:author:name` | `entity:name` | The author name extracted from Microsoft Office metadata. |
| `:created` | `time` | The create_time extracted from Microsoft Office metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:lastsaved` | `time` | The last_saved_time extracted from Microsoft Office metadata. |
| `:subject` | `text` | The subject extracted from Microsoft Office metadata. |
| `:title` | `text` | The title extracted from Microsoft Office metadata. |

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
| `:id` | `base:id` | The "DocumentID" field extracted from PDF metadata. |
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
| `:author:name` | `entity:name` | MIME specific author name extracted from metadata. |
| `:comment` | `text` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `text` | MIME specific description field extracted from metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `text` | The text contained within the image. |

### `file:mime:rar:entry`

A file entry contained by a RAR archive file.

| Interface |
|-----------|
| `file:entry` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:archived:size` | `size` | The storage size of the file within the archive. |
| `:created` | `time` | The created time of the file. |
| `:extra:posix:perms` | `int` | The POSIX permissions mask of the archived file. |
| `:file` | `file:bytes` | The file associated with the RAR archive file entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:offset` | `size` | The offset to the beginning of the file within the parent file. |
| `:parent` | `file:bytes` | The parent file which contains the RAR archive file entry. |
| `:path` | `file:path` | The path of the file associated with the RAR archive file entry. |
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
| `:author:name` | `entity:name` | MIME specific author name extracted from metadata. |
| `:comment` | `text` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `text` | MIME specific description field extracted from metadata. |
| `:file` | `file:bytes` | The file that the mime info was parsed from. |
| `:file:data` | `data` | A mime specific arbitrary data structure for non-indexed data. |
| `:file:offs` | `int` | The offset of the metadata within the file. |
| `:file:size` | `int` | The size of the metadata within the file. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `text` | The text contained within the image. |

### `file:mime:zip:entry`

A file entry contained by a ZIP archive file.

| Interface |
|-----------|
| `file:entry` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:archived:size` | `size` | The storage size of the file within the archive. |
| `:comment` | `text` | The comment field from the CDFH in the ZIP archive. |
| `:created` | `time` | The created time of the file. |
| `:extra:posix:gid` | `int` | A POSIX GID extracted from a ZIP Extra Field. |
| `:extra:posix:uid` | `int` | A POSIX UID extracted from a ZIP Extra Field. |
| `:file` | `file:bytes` | The file associated with the ZIP archive file entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:offset` | `size` | The offset to the beginning of the file within the parent file. |
| `:parent` | `file:bytes` | The parent file which contains the ZIP archive file entry. |
| `:path` | `file:path` | The path of the file associated with the ZIP archive file entry. |
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
| `file:entry` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:created` | `time` | The created time of the file. |
| `:file` | `file:bytes` | The file associated with the stored file entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:path` | `file:path` | The path of the file associated with the stored file entry. |
| `:seen` | `ival` | The stored file entry was observed during the time interval. |

### `file:subfile:entry`

A file entry contained by a parent file.

| Interface |
|-----------|
| `file:entry` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:created` | `time` | The created time of the file. |
| `:file` | `file:bytes` | The file associated with the subfile entry. |
| `:modified` | `time` | The last known modified time of the file. |
| `:offset` | `size` | The offset to the beginning of the file within the parent file. |
| `:parent` | `file:bytes` | The parent file which contains the subfile entry. |
| `:path` | `file:path` | The path of the file associated with the subfile entry. |
| `:seen` | `ival` | The subfile entry was observed during the time interval. |

### `file:system:entry`

A file entry contained by a host filesystem.

| Interface |
|-----------|
| `file:entry` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:accessed` | `time` | The last known accessed time of the file. |
| `:added` | `time` | The time that the file entry was added. |
| `:created` | `time` | The created time of the file. |
| `:creator` | `it:host:account` | The host account which created the file. |
| `:file` | `file:bytes` | The file associated with the stored file entry. |
| `:host` | `it:host` | The host which contains the filesystem. |
| `:modified` | `time` | The last known modified time of the file. |
| `:owner` | `it:host:account` | The host account which owns the file. |
| `:path` | `file:path` | The path of the file associated with the stored file entry. |
| `:seen` | `ival` | The stored file entry was observed during the time interval. |

### `geo:name`

An unstructured place name or address.

### `geo:place`

A geographic place.

| Interface |
|-----------|
| `geo:locatable` |
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:address` | `geo:address` | The postal address where the place was located. |
| `:address:city` | `base:name` | The city where the place was located. |
| `:addresses` | `array of geo:address` | An array of postal addresses for the place. |
| `:altitude` | `geo:altitude` | The altitude where the place was located. |
| `:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the place was located. |
| `:bbox` | `geo:bbox` | A bounding box which encompasses the place. |
| `:country` | `pol:country` | The country where the place was located. |
| `:country:code` | `iso:3166:alpha2` | The country code where the place was located. |
| `:desc` | `text` | A description of the place. |
| `:geojson` | `geo:json` | A GeoJSON representation of the place. |
| `:id` | `base:id` | A type specific identifier such as an airport ID. |
| `:latlong` | `geo:latlong` | The latlong where the place was located. |
| `:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the place was located. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `geo:place:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `geo:telem`

The geospatial position and physical characteristics of a node at a given time.

| Interface |
|-----------|
| `geo:locatable` |
| `phys:tangible` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the telemetry sample. |
| `:node` | `geo:locatable` | The node that was observed at the associated time and place. |
| `:phys:height` | `phys:distance` | The physical height of the item. |
| `:phys:length` | `phys:distance` | The physical length of the item. |
| `:phys:mass` | `phys:mass` | The physical mass of the item. |
| `:phys:volume` | `phys:volume` | The physical volume of the item. |
| `:phys:width` | `phys:distance` | The physical width of the item. |
| `:place` | `geo:place` | The place where the item was located. |
| `:place:address` | `geo:address` | The postal address where the item was located. |
| `:place:address:city` | `base:name` | The city where the item was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the item was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the item was located. |
| `:place:country` | `pol:country` | The country where the item was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the item was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the item was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the item was located. |
| `:place:loc` | `loc` | The geopolitical location where the item was located. |
| `:place:name` | `geo:name` | The name of the place where the item was located. |
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

### `gov:us:ssn`

A US Social Security Number (SSN).

| Interface |
|-----------|
| `entity:identifier` |

### `gov:us:zip`

A US Postal Zip Code.

### `ind:industry`

An industry.

| Interface |
|-----------|
| `meta:reported` |
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the industry. |
| `:id` | `ind:industry:id` | A unique ID given to the industry. |
| `:ids` | `array of ind:industry:id` | An array of alternate IDs given to the industry. |
| `:name` | `ind:name` | The name of the industry. |
| `:names` | `array of ind:name` | An array of alternative names for the industry. |
| `:reporter` | `entity:actor` | The entity which reported on the industry. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the industry. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the industry. |
| `:reporter:period` | `reported` | The period when the industry existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the industry. |
| `:reporter:supersedes` | `array of ind:industry` | An array of industry nodes which are superseded by this industry. |
| `:reporter:updated` | `time` | The time when the industry was last updated. |
| `:reporter:url` | `inet:url` | The URL for the industry provided by the reporter. |
| `:resolved` | `ind:industry` | The authoritative industry which this reporting is about. |
| `:type` | `ind:industry:type:taxonomy` | A taxonomy entry for the industry. |

### `ind:industry:type:taxonomy`

A hierarchical taxonomy of industry types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ind:industry:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `ind:name`

A name of an industry.

### `inet:asn`

An Autonomous System Number (ASN).

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:registrant` | `entity:actor` | The entity which registered the ASN. |
| `:registrant:name` | `entity:name` | The name of the entity which registered the ASN. |
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
| `:certificate` | `crypto:x509:cert` | The x509 certificate presented by the server along with the banner. |
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

### `inet:data:link`

A data link between two network interface cards.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this link. |
| `:period` | `activity` | The period over which the link occurred. |
| `:source` | `it:nic` | The source NIC of the link. |
| `:source:ip` | `inet:ip` | The IP address assigned to the source NIC. |
| `:source:mac` | `inet:mac` | The MAC address assigned to the source NIC. |
| `:source:network` | `it:network` | The source network which the link provides access to. |
| `:target` | `it:nic` | The target NIC of the link. |
| `:target:ip` | `inet:ip` | The IP address assigned to the target NIC. |
| `:target:mac` | `inet:mac` | The MAC address assigned to the target NIC. |
| `:target:network` | `it:network` | The target network which the link provides access to. |

### `inet:dns:a`

The result of a DNS A record lookup.

| Interface |
|-----------|
| `inet:dns:record` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain queried for its DNS A record. |
| `:ip` | `inet:ip` | The IPv4 address returned in the A record. |
| `:seen` | `ival` | The DNS A record was observed during the time interval. |

### `inet:dns:aaaa`

The result of a DNS AAAA record lookup.

| Interface |
|-----------|
| `inet:dns:record` |
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
| `:record` | `inet:dns:record` | The DNS record contained in the answer. |
| `:ttl` | `duration:seconds` | The time to live value of the DNS record in the response. |

### `inet:dns:cname`

The result of a DNS CNAME record lookup.

| Interface |
|-----------|
| `inet:dns:record` |
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
| `inet:dns:record` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain queried for its MX record. |
| `:mx` | `inet:fqdn` | The domain returned in the MX record. |
| `:seen` | `ival` | The DNS MX record was observed during the time interval. |

### `inet:dns:mx:answer`

A single MX answer from within a DNS reply.

| Property | Type | Doc |
|----------|------|-----|
| `:priority` | `int` | The DNS MX record priority. |
| `:record` | `inet:dns:mx` | The MX record in the answer. |
| `:ttl` | `duration:seconds` | The time to live value of the DNS record in the response. |

### `inet:dns:ns`

The result of a DNS NS record lookup.

| Interface |
|-----------|
| `inet:dns:record` |
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
| `:name` | `inet:dns:query:name` | The DNS query name string. |
| `:seen` | `ival` | The DNS query was observed during the time interval. |
| `:type` | `inet:dns:query:type` | The type of record that was queried. |

### `inet:dns:request`

A DNS protocol request.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:request` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the link. |
| `:client:host` | `it:host` | The client host which initiated the link. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the link. |
| `:flow` | `inet:flow` | The network flow which contained the request. |
| `:query:name` | `inet:dns:query:name` | The DNS query name string in the request. |
| `:query:type` | `inet:dns:query:type` | The type of record requested in the query. |
| `:response` | `inet:dns:response` | The response sent by the DNS server. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the link. |
| `:server:host` | `it:host` | The server host which received the link. |
| `:server:proc` | `it:exec:proc` | The server process which received the link. |
| `:time` | `time` | The time that the event occurred. |

### `inet:dns:response`

A DNS protocol response.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:response` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:answers` | `array of inet:dns:answer` | The DNS answers included in the response. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the link. |
| `:client:host` | `it:host` | The client host which initiated the link. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the link. |
| `:code` | `dns:reply:code` | The DNS server reply code. |
| `:flow` | `inet:flow` | The network flow which contained the response. |
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
| `inet:dns:record` |
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
| `inet:dns:record` |
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
| `inet:dns:record` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The domain queried for its TXT record. |
| `:seen` | `ival` | The DNS TXT record was observed during the time interval. |
| `:text` | `text` | The string returned in the TXT record. |

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
| `:host:nic` | `it:nic` | The interface which the host used to connect out via the egress. |
| `:seen` | `ival` | The egress client was observed during the time interval. |

### `inet:email`

An email address.

| Interface |
|-----------|
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `inet:email` | The base email address which is populated if the email address contains a user with a +<tag>. |
| `:fqdn` | `inet:fqdn` | The domain of the email address. |
| `:plus` | `str:lower` | The optional email address "tag". |
| `:seen` | `ival` | The email address was observed during the time interval. |
| `:username` | `entity:name` | The username of the email address. |

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

| Interface |
|-----------|
| `meta:usable` |

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
| `:subject` | `title` | The email message subject parsed from the "subject" header. |
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
| `:activity` | `base:activity` | A parent activity which includes this network flow. |
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
| `:ip:proto` | `uint8` | The IP protocol number of the flow. |
| `:ip:tcp:flags` | `uint8` | An aggregation of observed TCP flags commonly provided by flow APIs. |
| `:period` | `activity` | The period over which the network flow occurred. |
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
| `meta:usable` |

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
| `:activity` | `base:activity` | A parent activity which includes this HTTP request. |
| `:body` | `file:bytes` | The body of the HTTP request. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the HTTP request. |
| `:client:host` | `it:host` | The client host which initiated the HTTP request. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the HTTP request. |
| `:cookies` | `array of inet:http:cookie` | An array of HTTP cookie values parsed from the "Cookies:" header in the request. |
| `:flow` | `inet:flow` | The network flow which contained the HTTP request. |
| `:header:host` | `inet:fqdn` | The FQDN parsed from the "Host:" header in the request. |
| `:header:referer` | `inet:url` | The referer URL parsed from the "Referer:" header in the request. |
| `:headers` | `array of inet:http:request:header` | An array of HTTP headers from the request. |
| `:method` | `str:upper` | The HTTP request method string. |
| `:path` | `str` | The requested HTTP path (without query parameters). |
| `:query` | `str` | The HTTP query string which optionally follows the path. |
| `:response` | `inet:http:response` | The HTTP response sent by the server. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the HTTP request. |
| `:server:host` | `it:host` | The server host which received the HTTP request. |
| `:server:proc` | `it:exec:proc` | The server process which received the HTTP request. |
| `:session` | `inet:http:session` | The HTTP session this request was part of. |
| `:time` | `time` | The time that the HTTP request occurred. |
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

### `inet:http:response`

An HTTP response returned by a server.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:response` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this HTTP response. |
| `:body` | `file:bytes` | The HTTP response body received. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the HTTP response. |
| `:client:host` | `it:host` | The client host which initiated the HTTP response. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the HTTP response. |
| `:code` | `int` | The HTTP response code received. |
| `:flow` | `inet:flow` | The network flow which contained the HTTP response. |
| `:headers` | `array of inet:http:response:header` | An array of HTTP headers from the response. |
| `:reason` | `str` | The HTTP response reason phrase received. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the HTTP response. |
| `:server:host` | `it:host` | The server host which received the HTTP response. |
| `:server:proc` | `it:exec:proc` | The server process which received the HTTP response. |
| `:time` | `time` | The time that the HTTP response occurred. |

### `inet:http:response:header`

An HTTP response header.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `inet:http:header:name` | The name of the HTTP response header. |
| `:seen` | `ival` | The HTTP response header was observed during the time interval. |
| `:value` | `str` | The value of the HTTP response header. |

### `inet:http:session`

An HTTP session.

| Interface |
|-----------|
| `base:activity` |
| `inet:proto:session` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:client` | `inet:client` | The socket address of the client which initiated the protocol session. |
| `:client:host` | `it:host` | The host which initiated the protocol session. |
| `:contact` | `entity:contact` | The entity contact which owns the session. |
| `:cookies` | `array of inet:http:cookie` | An array of cookies used to identify this specific session. |
| `:period` | `activity` | The period over which the activity occurred. |
| `:server` | `inet:server` | The socket address of the server which received the protocol session. |
| `:server:host` | `it:host` | The host which received the protocol session. |

### `inet:hyperlink`

A URL link embedded in a message.

| Property | Type | Doc |
|----------|------|-----|
| `:title` | `title` | The displayed hyperlink text if it was not the URL. |
| `:url` | `inet:url` | The URL target of the hyperlink. |

### `inet:ip`

An IPv4 or IPv6 address.

| Interface |
|-----------|
| `geo:locatable` |
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:asn` | `inet:asn` | The ASN to which the IP address is currently assigned. |
| `:dns:rev` | `inet:fqdn` | The most current DNS reverse lookup for the IP. |
| `:place` | `geo:place` | The place where the IP address was located. |
| `:place:address` | `geo:address` | The postal address where the IP address was located. |
| `:place:address:city` | `base:name` | The city where the IP address was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the IP address was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the IP address was located. |
| `:place:country` | `pol:country` | The country where the IP address was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the IP address was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the IP address was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the IP address was located. |
| `:place:loc` | `loc` | The geopolitical location where the IP address was located. |
| `:place:name` | `geo:name` | The name of the place where the IP address was located. |
| `:scope` | `inet:ipscope` | The IPv6 scope of the address (e.g., global, link-local, etc.). |
| `:seen` | `ival` | The IP address was observed during the time interval. |
| `:type` | `str:lower` | The type of IP address (e.g., private, multicast, etc.). |
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
| `:activity` | `base:activity` | A parent activity which includes this event. |
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
| `base:event` |
| `entity:action` |
| `entity:event` |
| `inet:service:action` |
| `inet:service:base` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:actor` | `inet:service:account`, `inet:service:agent` | The service account or agent which performed the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software used to initiate the action. |
| `:engine` | `base:name` | A simple name for the search engine used. |
| `:host` | `it:host` | The host that issued the query. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:request` | `inet:proto:request` | The request used to issue the query. |
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:text` | `text` | The search query text. |
| `:time` | `time` | The time the web search was issued. |

### `inet:search:result`

A single result from a web search.

| Property | Type | Doc |
|----------|------|-----|
| `:query` | `inet:search:query` | The search query that produced the result. |
| `:rank` | `int` | The rank/order of the query result. |
| `:text` | `text` | Extracted/matched text from the matched content. |
| `:title` | `title` | The title of the matching web page. |
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
| `base:event` |
| `entity:action` |
| `entity:event` |
| `inet:service:action` |
| `inet:service:action:authorized` |
| `inet:service:base` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:action` | `inet:service:access:action:taxonomy` | The platform specific action which this access records. |
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:actor` | `inet:service:account`, `inet:service:agent` | The service account or agent which performed the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software used to initiate the action. |
| `:error` | `inet:service:error` | The error generated if the action was unsuccessful. |
| `:error:reason` | `str` | The platform specific friendly error reason if the action was unsuccessful. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:resource` | `inet:service:resource` | The resource which the account attempted to access. |
| `:rule` | `inet:service:rule` | The rule which allowed or denied the action. |
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:success` | `bool` | Set to true if the action was successful. |
| `:time` | `time` | The time that the actor initiated the action. |
| `:type` | `inet:svcaccess:type` | The type of access requested. |

### `inet:service:account`

An account within a service platform. Accounts may be instance specific.

| Interface |
|-----------|
| `econ:pay:instrument` |
| `entity:actor` |
| `entity:resolvable` |
| `inet:service:base` |
| `inet:service:object` |
| `inet:service:subscriber` |
| `meta:observable` |
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:account` | The account that contains the funds used by the account. |
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the account. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:email` | `inet:email` | The email address of the account. |
| `:id` | `base:id` | A platform specific ID which identifies the account. |
| `:name` | `entity:name` | The name of the account. |
| `:parent` | `inet:service:account` | A parent account which owns this account. |
| `:period` | `it:lifespan` | The period when the account existed. |
| `:platform` | `inet:service:platform` | The platform which defines the account. |
| `:profile` | `entity:contact` | Current detailed contact information for the account. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the account. |
| `:resolved` | `ou:org`, `ps:person` | The resolved entity to which this account belongs. |
| `:rules` | `array of inet:service:rule` | An array of rules associated with this account. |
| `:seen` | `ival` | The account was observed during the time interval. |
| `:status` | `title` | The status of the account. |
| `:tenant` | `inet:service:tenant` | The tenant which contains the account. |
| `:url` | `inet:url` | The primary URL associated with the account. |
| `:username` | `entity:name` | The primary user name for the account. |

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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the object. |
| `:desc` | `text` | A description of the deployed service agent instance. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:name` | `base:name` | The name of the service agent instance. |
| `:names` | `array of base:name` | An array of alternate names for the service agent instance. |
| `:period` | `it:lifespan` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:software` | `it:software` | The latest known software version running on the service agent instance. |
| `:status` | `title` | The status of the object. |
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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the bucket. |
| `:desc` | `text` | A description of the service resource. |
| `:id` | `base:id` | A platform specific ID which identifies the bucket. |
| `:name` | `base:name` | The name of the service resource. |
| `:period` | `it:lifespan` | The period when the bucket existed. |
| `:platform` | `inet:service:platform` | The platform which defines the bucket. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the bucket. |
| `:seen` | `ival` | The bucket was observed during the time interval. |
| `:status` | `title` | The status of the bucket. |
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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the bucket item. |
| `:desc` | `text` | A description of the service resource. |
| `:file` | `file:bytes` | The bytes stored within the bucket item. |
| `:file:name` | `file:path` | The name of the file stored in the bucket item. |
| `:id` | `base:id` | A platform specific ID which identifies the bucket item. |
| `:name` | `base:name` | The name of the service resource. |
| `:period` | `it:lifespan` | The period when the bucket item existed. |
| `:platform` | `inet:service:platform` | The platform which defines the bucket item. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the bucket item. |
| `:seen` | `ival` | The bucket item was observed during the time interval. |
| `:status` | `title` | The status of the bucket item. |
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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the channel. |
| `:id` | `base:id` | A platform specific ID which identifies the channel. |
| `:name` | `base:name` | The name of the channel. |
| `:period` | `it:lifespan` | The time period where the channel was available. |
| `:platform` | `inet:service:platform` | The platform which defines the channel. |
| `:profile` | `entity:contact` | Current detailed contact information for this channel. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the channel. |
| `:seen` | `ival` | The channel was observed during the time interval. |
| `:status` | `title` | The status of the channel. |
| `:topic` | `base:name` | The visible topic of the channel. |
| `:url` | `inet:url` | The primary URL associated with the channel. |

### `inet:service:comment`

A comment about a node created by an account.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:about` | `inet:service:commentable` | The node that the comment is about. |
| `:attachments` | `array of file:attachment` | An array of files attached to the comment. |
| `:client:software` | `it:software` | The client software version used to send the comment. |
| `:client:software:name` | `it:softwarename` | The name of the client software used to send the comment. |
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the comment. |
| `:hashtags` | `array of lang:hashtag` | An array of hashtags mentioned within the comment. |
| `:id` | `base:id` | A platform specific ID which identifies the comment. |
| `:links` | `array of inet:hyperlink` | An array of links contained within the comment. |
| `:mentions` | `array of inet:service:account, inet:service:role` | Contactable entities mentioned within the comment. |
| `:period` | `it:lifespan` | The period when the comment existed. |
| `:platform` | `inet:service:platform` | The platform which defines the comment. |
| `:public` | `bool` | Set to true if the comment is publicly visible. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the comment. |
| `:replyto` | `inet:service:comment` | The comment that this comment was made in reply to. Used for comment threading. |
| `:seen` | `ival` | The comment was observed during the time interval. |
| `:status` | `title` | The status of the comment. |
| `:text` | `text` | The text body of the comment. |
| `:title` | `title` | The comment title. |
| `:url` | `inet:url` | The primary URL associated with the comment. |

### `inet:service:emote`

An emote or reaction by an account.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `inet:service:action` |
| `inet:service:base` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:about` | `inet:service:object` | The node that the emote is about. |
| `:activity` | `base:activity` | A parent activity which includes this emote. |
| `:actor` | `inet:service:account`, `inet:service:agent` | The service account or agent which performed the action. |
| `:actor:name` | `entity:name` | The name of the actor who posted the emote. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software used to initiate the action. |
| `:id` | `base:id` | A platform specific ID which identifies the emote. |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:text` | `str` | The unicode or emote text of the reaction. |
| `:time` | `time` | The time that the actor initiated the action. |

### `inet:service:error`

An error generated by a service platform.

| Property | Type | Doc |
|----------|------|-----|
| `:code` | `base:id` | The platform specific error code. |
| `:desc` | `text` | A description of the error. |
| `:name` | `title` | The platform specific friendly name of the error. |
| `:platform` | `inet:service:platform` | The platform which defines the error code. |

### `inet:service:label`

A label which may be applied to objects within a service platform.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the label. |
| `:desc` | `text` | The description of the label. |
| `:id` | `base:id` | A platform specific ID which identifies the label. |
| `:name` | `title` | The name of the label. |
| `:period` | `it:lifespan` | The period when the label existed. |
| `:platform` | `inet:service:platform` | The platform which defines the label. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the label. |
| `:seen` | `ival` | The label was observed during the time interval. |
| `:status` | `title` | The status of the label. |
| `:url` | `inet:url` | The primary URL associated with the label. |

### `inet:service:labeled`

Records a label applied to an object within a service platform.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:about` | `inet:service:labelable` | The node which the label was applied to. |
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which applied the label. |
| `:id` | `base:id` | A platform specific ID which identifies the label application. |
| `:label` | `inet:service:label` | The label which was applied. |
| `:period` | `it:lifespan` | The period during which the label was applied to the object. |
| `:platform` | `inet:service:platform` | The platform which defines the label application. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed the label. |
| `:seen` | `ival` | The label application was observed during the time interval. |
| `:status` | `title` | The status of the label application. |
| `:url` | `inet:url` | The primary URL associated with the label application. |

### `inet:service:login`

A login event for a service account.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `inet:proto:link` |
| `inet:proto:login` |
| `inet:proto:request` |
| `inet:service:action` |
| `inet:service:action:authorized` |
| `inet:service:base` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:actor` | `inet:service:account`, `inet:service:agent` | The service account or agent which performed the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the link. |
| `:client:host` | `it:host` | The client host which initiated the link. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the link. |
| `:client:software` | `it:software` | The client software used to initiate the action. |
| `:credential` | `auth:credential` | The credential presented during the login event. |
| `:error` | `inet:service:error` | The error generated if the action was unsuccessful. |
| `:error:reason` | `str` | The platform specific friendly error reason if the action was unsuccessful. |
| `:flow` | `inet:flow` | The network flow which contained the request. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:method` | `inet:service:login:method:taxonomy` | The type of authentication used for the login. For example "password" or "multifactor.sms". |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:rule` | `inet:service:rule` | The rule which allowed or denied the action. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the link. |
| `:server:host` | `it:host` | The server host which received the link. |
| `:server:proc` | `it:exec:proc` | The server process which received the link. |
| `:session` | `inet:proto:session` | The protocol session established by the login event. |
| `:success` | `bool` | Set to true if the login event was successful. |
| `:time` | `time` | The time that the event occurred. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `inet:service:login:method:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the membership. |
| `:id` | `base:id` | A platform specific ID which identifies the membership. |
| `:of` | `inet:service:joinable` | The channel or group that the account was a member of. |
| `:period` | `it:lifespan` | The time period where the account was a member. |
| `:platform` | `inet:service:platform` | The platform which defines the membership. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the membership. |
| `:seen` | `ival` | The membership was observed during the time interval. |
| `:status` | `title` | The status of the membership. |
| `:url` | `inet:url` | The primary URL associated with the membership. |

### `inet:service:message`

A message or post created by an account.

| Interface |
|-----------|
| `base:event` |
| `entity:action` |
| `entity:event` |
| `inet:service:action` |
| `inet:service:base` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:actor` | `inet:service:account`, `inet:service:agent` | The service account or agent which performed the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:attachments` | `array of file:attachment` | An array of files attached to the message. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software version used to send the message. |
| `:client:software:name` | `it:softwarename` | The name of the client software used to send the message. |
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
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:status` | `title` | The message status. |
| `:text` | `text` | The text body of the message. |
| `:time` | `time` | The time that the actor initiated the action. |
| `:title` | `title` | The message title. |
| `:to` | `inet:service:account`, `inet:service:channel`, `inet:service:role` | The destination account, role, or channel which received the message. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `inet:service:message:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `inet:service:permission`

A permission which may be granted to a service account or role.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the permission. |
| `:id` | `base:id` | A platform specific ID which identifies the permission. |
| `:name` | `base:name` | The name of the permission. |
| `:period` | `it:lifespan` | The period when the permission existed. |
| `:platform` | `inet:service:platform` | The platform which defines the permission. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the permission. |
| `:seen` | `ival` | The permission was observed during the time interval. |
| `:status` | `title` | The status of the permission. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `inet:service:permission:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `inet:service:platform`

A network platform which provides services.

| Interface |
|-----------|
| `meta:observable` |
| `meta:usable` |
| `risk:exploitable` |
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account` | The service account which created the platform. |
| `:desc` | `text` | A description of the service platform. |
| `:family` | `base:name` | A family designation for use with instanced platforms such as Slack, Discord, or Mastodon. |
| `:id` | `base:id` | An ID which identifies the platform. |
| `:name` | `base:name` | A friendly name for the platform. |
| `:names` | `array of base:name` | An array of alternate names for the platform. |
| `:parent` | `inet:service:platform` | A parent platform which owns this platform. |
| `:period` | `it:lifespan` | The period when the platform existed. |
| `:provider` | `ou:org` | The organization which operates the platform. |
| `:provider:name` | `entity:name` | The name of the organization which operates the platform. |
| `:remover` | `inet:service:account` | The service account which removed or decommissioned the platform. |
| `:seen` | `ival` | The platform was observed during the time interval. |
| `:software` | `it:software` | The latest known software version that the platform is running. |
| `:status` | `title` | The status of the platform. |
| `:tenant` | `inet:service:tenant` | The tenant which owns the platform. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `inet:service:platform:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `inet:service:relationship`

A relationship between two service objects.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the relationship. |
| `:id` | `base:id` | A platform specific ID which identifies the relationship. |
| `:period` | `it:lifespan` | The period when the relationship existed. |
| `:platform` | `inet:service:platform` | The platform which defines the relationship. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the relationship. |
| `:seen` | `ival` | The relationship was observed during the time interval. |
| `:source` | `inet:service:object` | The source object. |
| `:status` | `title` | The status of the relationship. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `inet:service:relationship:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `inet:service:resource`

A generic resource provided by the service architecture.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the resource. |
| `:desc` | `text` | A description of the service resource. |
| `:id` | `base:id` | A platform specific ID which identifies the resource. |
| `:name` | `base:name` | The name of the service resource. |
| `:period` | `it:lifespan` | The period when the resource existed. |
| `:platform` | `inet:service:platform` | The platform which defines the resource. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the resource. |
| `:seen` | `ival` | The resource was observed during the time interval. |
| `:status` | `title` | The status of the resource. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `inet:service:resource:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the service role. |
| `:id` | `base:id` | A platform specific ID which identifies the service role. |
| `:name` | `base:name` | The name of the role on this platform. |
| `:period` | `it:lifespan` | The period when the service role existed. |
| `:platform` | `inet:service:platform` | The platform which defines the service role. |
| `:profile` | `entity:contact` | Current detailed contact information for this role. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the service role. |
| `:rules` | `array of inet:service:rule` | An array of rules associated with this role. |
| `:seen` | `ival` | The service role was observed during the time interval. |
| `:status` | `title` | The status of the service role. |
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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the rule. |
| `:denied` | `bool` | Set to true to denote that the rule is an explicit deny. |
| `:grantee` | `inet:service:account`, `inet:service:role` | The user or role which is granted the permission. |
| `:id` | `base:id` | A platform specific ID which identifies the rule. |
| `:object` | `inet:service:object` | The object that the permission controls access to. |
| `:period` | `it:lifespan` | The period when the rule existed. |
| `:permission` | `inet:service:permission` | The permission which is granted. |
| `:platform` | `inet:service:platform` | The platform which defines the rule. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the rule. |
| `:seen` | `ival` | The rule was observed during the time interval. |
| `:status` | `title` | The status of the rule. |
| `:url` | `inet:url` | The primary URL associated with the rule. |

### `inet:service:session`

An authenticated session.

| Interface |
|-----------|
| `base:activity` |
| `inet:proto:session` |
| `inet:service:base` |
| `inet:service:object` |
| `meta:causal` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this session. |
| `:client` | `inet:client` | The socket address of the client which initiated the session. |
| `:client:host` | `it:host` | The host which initiated the session. |
| `:creator` | `inet:service:account`, `inet:service:agent` | The account or agent which authenticated to create the session. |
| `:http:session` | `inet:http:session` | The HTTP session associated with the service session. |
| `:id` | `base:id` | A platform specific ID which identifies the session. |
| `:period` | `activity` | The period where the session was valid. |
| `:platform` | `inet:service:platform` | The platform which defines the session. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the session. |
| `:seen` | `ival` | The session was observed during the time interval. |
| `:server` | `inet:server` | The socket address of the server which received the session. |
| `:server:host` | `it:host` | The host which received the session. |
| `:status` | `title` | The status of the session. |
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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the subscription. |
| `:id` | `base:id` | A platform specific ID which identifies the subscription. |
| `:level` | `inet:service:subscription:level:taxonomy` | A platform specific subscription level. |
| `:pay:instrument` | `econ:pay:instrument` | The primary payment instrument used to pay for the subscription. |
| `:period` | `it:lifespan` | The period when the subscription existed. |
| `:platform` | `inet:service:platform` | The platform which defines the subscription. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the subscription. |
| `:seen` | `ival` | The subscription was observed during the time interval. |
| `:status` | `title` | The status of the subscription. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `inet:service:subscription:level:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `inet:service:tenant`

A tenant which groups accounts and instances.

| Interface |
|-----------|
| `inet:service:base` |
| `inet:service:object` |
| `inet:service:subscriber` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the tenant. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:email` | `inet:email` | The email address of the tenant. |
| `:id` | `base:id` | A platform specific ID which identifies the tenant. |
| `:name` | `entity:name` | The name of the tenant. |
| `:period` | `it:lifespan` | The period when the tenant existed. |
| `:platform` | `inet:service:platform` | The platform which defines the tenant. |
| `:profile` | `entity:contact` | Current detailed contact information for the tenant. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the tenant. |
| `:seen` | `ival` | The tenant was observed during the time interval. |
| `:status` | `title` | The status of the tenant. |
| `:url` | `inet:url` | The primary URL associated with the tenant. |
| `:username` | `entity:name` | The primary user name for the tenant. |

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
| `:activity` | `base:activity` | A parent activity which includes this event. |
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
| `:activity` | `base:activity` | A parent activity which includes this event. |
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
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this tunnel. |
| `:actor` | `entity:actor` | The actor who established the tunnel. |
| `:actor:name` | `entity:name` | The name of the actor who established the tunnel. |
| `:anon` | `bool` | Set to true if the tunnel provides anonymization. |
| `:egress` | `inet:server` | The server where client traffic leaves the tunnel. |
| `:ingress` | `inet:server` | The server where client traffic enters the tunnel. |
| `:period` | `activity` | The period over which the tunnel occurred. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `inet:tunnel:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `inet:url`

A Universal Resource Locator (URL).

| Interface |
|-----------|
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `str` | The base scheme, user/pass, fqdn, port and path w/o parameters. |
| `:host` | `inet:fqdn`, `inet:ip` | The FQDN or IP address used in the URL (e.g., http://www.woot.com/page.html). |
| `:params` | `str` | The URL parameter string. |
| `:passwd` | `auth:passwd` | The optional password used to access the URL. |
| `:path` | `str` | The path in the URL w/o parameters. |
| `:port` | `inet:port` | The port of the URL. URLs prefixed with http will be set to port 80 and URLs prefixed with https will be set to port 443 unless otherwise specified. |
| `:proto` | `str:lower` | The protocol in the URL. |
| `:seen` | `ival` | The URL was observed during the time interval. |
| `:username` | `entity:name` | The optional username used to access the URL. |

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
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file that was hosted at the URL. |
| `:seen` | `ival` | The hosted file and URL was observed during the time interval. |
| `:url` | `inet:url` | The URL where the file was hosted. |

### `inet:whois:ipquery`

Query details used to retrieve an IP record.

| Property | Type | Doc |
|----------|------|-----|
| `:fqdn` | `inet:fqdn` | The FQDN of the host server when using the legacy WHOIS Protocol. |
| `:ip` | `inet:ip` | The IP address queried. |
| `:rec` | `inet:whois:iprecord` | The resulting record from the query. |
| `:success` | `bool` | Set to true if the host returned a valid response for the query. |
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
| `:registrant` | `entity:actor` | The actor who registered the network. |
| `:registrant:name` | `entity:name` | The name of the actor who registered the network. |
| `:registrar` | `entity:actor` | The actor who acted as the registrar for the network. |
| `:registrar:name` | `entity:name` | The name of the actor who acted as the registrar for the network. |
| `:seen` | `ival` | The IP WHOIS record was observed during the time interval. |
| `:status` | `title` | The state of the registered network. |
| `:text` | `text` | The full text of the record. |
| `:type` | `title` | The classification of the registered network (e.g. direct allocation). |
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
| `:registrant` | `entity:actor` | The actor who registered the FQDN. |
| `:registrant:name` | `entity:name` | The name of the actor who registered the FQDN. |
| `:registrar` | `entity:actor` | The actor who acted as the registrar for the FQDN. |
| `:registrar:name` | `entity:name` | The name of the actor who acted as the registrar for the FQDN. |
| `:seen` | `ival` | The WHOIS record was observed during the time interval. |
| `:text` | `text` | The full text of the whois record. |
| `:updated` | `time` | The "last updated" time from the whois record. |

### `inet:wifi:ap`

A wireless access point, typically defined by the combination of an SSID and a MAC address.

| Interface |
|-----------|
| `geo:locatable` |
| `meta:havable` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:bssid` | `inet:mac` | The MAC address for the wireless access point. |
| `:channel` | `int` | The WIFI channel that the AP was last observed operating on. |
| `:encryption:algorithm` | `meta:algorithm` | The encryption algorithm used by the WIFI AP. |
| `:encryption:algorithm:name` | `base:name` | The name of the encryption algorithm used by the WIFI AP, such as "wpa2". |
| `:place` | `geo:place` | The place where the Wi-Fi access point was located. |
| `:place:address` | `geo:address` | The postal address where the Wi-Fi access point was located. |
| `:place:address:city` | `base:name` | The city where the Wi-Fi access point was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the Wi-Fi access point was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the Wi-Fi access point was located. |
| `:place:country` | `pol:country` | The country where the Wi-Fi access point was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the Wi-Fi access point was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the Wi-Fi access point was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the Wi-Fi access point was located. |
| `:place:loc` | `loc` | The geopolitical location where the Wi-Fi access point was located. |
| `:place:name` | `geo:name` | The name of the place where the Wi-Fi access point was located. |
| `:seen` | `ival` | The Wi-Fi access point was observed during the time interval. |
| `:ssid` | `inet:wifi:ssid` | The SSID for the wireless access point. |

### `inet:wifi:link`

A wireless link between two Wi-Fi network interface cards.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this Wi-Fi link. |
| `:period` | `activity` | The period over which the Wi-Fi link occurred. |
| `:source` | `it:wifi:nic` | The source Wi-Fi NIC of the Wi-Fi link. |
| `:source:ip` | `inet:ip` | The IP address assigned to the source NIC. |
| `:source:mac` | `inet:mac` | The MAC address assigned to the source NIC. |
| `:source:network` | `it:network` | The source network which the Wi-Fi link provides access to. |
| `:target` | `it:wifi:nic` | The target Wi-Fi NIC of the Wi-Fi link. |
| `:target:ip` | `inet:ip` | The IP address assigned to the target NIC. |
| `:target:mac` | `inet:mac` | The MAC address assigned to the target NIC. |
| `:target:network` | `it:network` | The target network which the Wi-Fi link provides access to. |
| `:target:ssid` | `inet:wifi:ssid` | The SSID of the target Wi-Fi network. |

### `inet:wifi:login`

An authentication event for a Wi-Fi network.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:login` |
| `inet:proto:request` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this Wi-Fi login. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the Wi-Fi login. |
| `:client:host` | `it:host` | The client host which initiated the Wi-Fi login. |
| `:client:mac` | `inet:mac` | The MAC address of the client for the Wi-Fi login. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the Wi-Fi login. |
| `:credential` | `auth:credential` | The credential presented during the Wi-Fi login. |
| `:flow` | `inet:flow` | The network flow which contained the Wi-Fi login. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:ap` | `inet:wifi:ap` | The Wi-Fi access point which received the Wi-Fi login. |
| `:server:exe` | `file:bytes` | The server executable which received the Wi-Fi login. |
| `:server:host` | `it:host` | The server host which received the Wi-Fi login. |
| `:server:proc` | `it:exec:proc` | The server process which received the Wi-Fi login. |
| `:session` | `inet:wifi:session` | The Wi-Fi session established by the Wi-Fi login. |
| `:success` | `bool` | Set to true if the Wi-Fi login was successful. |
| `:time` | `time` | The time that the Wi-Fi login occurred. |

### `inet:wifi:session`

A Wi-Fi association session between a client and an access point.

| Interface |
|-----------|
| `base:activity` |
| `inet:proto:session` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this Wi-Fi session. |
| `:client` | `inet:client` | The socket address of the client which initiated the Wi-Fi session. |
| `:client:host` | `it:host` | The host which initiated the Wi-Fi session. |
| `:client:mac` | `inet:mac` | The MAC address of the client for the Wi-Fi session. |
| `:period` | `activity` | The period over which the Wi-Fi session occurred. |
| `:server` | `inet:server` | The socket address of the server which received the Wi-Fi session. |
| `:server:ap` | `inet:wifi:ap` | The Wi-Fi access point that hosted the Wi-Fi session. |
| `:server:host` | `it:host` | The host which received the Wi-Fi session. |

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
| `:desc` | `text` | A description of the value or meaning of the OID. |
| `:name` | `title` | The name for the deepest tree element. |

### `it:adid`

An advertising identification string.

| Interface |
|-----------|
| `entity:identifier` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The advertising ID was observed during the time interval. |

### `it:app:snort:matched`

An instance of a snort rule hit.

| Interface |
|-----------|
| `base:event` |
| `base:matched` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this match. |
| `:dropped` | `bool` | Set to true if the network traffic was dropped due to the match. |
| `:rule` | `it:app:snort:rule` | The rule which matched the target node. |
| `:rule:version` | `it:version` | The version of the rule which generated the match. |
| `:sensor` | `it:host` | The sensor host node that produced the match. |
| `:target` | `inet:flow` | The target node which matched the Snort rule. |
| `:time` | `time` | The time that the match occurred. |

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
| `:created` | `time` | The time that the Snort rule was created. |
| `:creator` | `entity:actor` | The primary actor which created the Snort rule. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the Snort rule. |
| `:desc` | `text` | A description of the Snort rule. |
| `:enabled` | `bool` | The enabled status of the Snort rule. |
| `:engine` | `int` | The snort engine ID which can parse and evaluate the rule text. |
| `:id` | `base:id` | The Snort rule ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the Snort rule. |
| `:name` | `base:name` | The rule name. |
| `:seen` | `ival` | The Snort rule was observed during the time interval. |
| `:status` | `title` | The status of the rule. |
| `:supersedes` | `array of it:app:snort:rule` | An array of Snort rule versions which are superseded by this Snort rule. |
| `:text` | `text` | The text of the Snort rule. |
| `:type` | `meta:rule:type:taxonomy` | The rule type. |
| `:updated` | `time` | The time that the Snort rule was last updated. |
| `:url` | `inet:url` | The URL where the Snort rule is available. |
| `:version` | `it:version` | The version of the Snort rule. |

### `it:app:yara:matched`

An instance of a YARA rule matching a target.

| Interface |
|-----------|
| `base:event` |
| `base:matched` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this match. |
| `:rule` | `it:app:yara:rule` | The rule which matched the target node. |
| `:rule:version` | `it:version` | The version of the rule which generated the match. |
| `:target` | `it:app:yara:target` | The target node which matched the YARA rule. |
| `:time` | `time` | The time that the match occurred. |

### `it:app:yara:rule`

A YARA rule.

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
| `:name` | `base:name` | The rule name. |
| `:seen` | `ival` | The YARA rule was observed during the time interval. |
| `:status` | `title` | The status of the rule. |
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
| `:multi:count` | `size` | The total number of scanners which were run by a multi-scanner. |
| `:multi:count:benign` | `size` | The number of scanners which returned a benign verdict. |
| `:multi:count:malicious` | `size` | The number of scanners which returned a malicious verdict. |
| `:multi:count:suspicious` | `size` | The number of scanners which returned a suspicious verdict. |
| `:multi:count:unknown` | `size` | The number of scanners which returned an unknown/unsupported verdict. |
| `:multi:scan` | `it:av:scan:result` | Set if this result was part of running multiple scanners. |
| `:scanner` | `it:software` | The scanner software used to produce the result. |
| `:scanner:name` | `it:softwarename` | The name of the scanner software. |
| `:signame` | `it:av:signame` | The name of the signature returned by the scanner. |
| `:target` | `file:bytes`, `inet:fqdn`, `inet:ip`, `inet:url`, `it:exec:proc`, `it:host` | The target of the scan. |
| `:time` | `time` | The time the scan was run. |
| `:verdict` | `it:av:verdict` | The scanner provided verdict for the scan. |

### `it:av:signame`

An antivirus signature name.

### `it:cloud:host`

A virtual host instance which runs within a cloud service platform.

| Interface |
|-----------|
| `entity:creatable` |
| `geo:locatable` |
| `inet:service:base` |
| `inet:service:object` |
| `it:component` |
| `meta:havable` |
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the cloud host. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the cloud host. |
| `:desc` | `text` | A free-form description of the host. |
| `:hardware` | `it:hardware` | The hardware specification of the cloud host. |
| `:id` | `base:id` | An external identifier for the host. |
| `:image` | `it:software:image` | The container image or OS image running on the host. |
| `:ip` | `inet:ip` | The last known IP address for the host. |
| `:keyboard:language` | `lang:language` | The primary keyboard input language configured on the host. |
| `:keyboard:layout` | `base:name` | The primary keyboard layout configured on the host. |
| `:name` | `it:hostname` | The name of the host or system. |
| `:operator` | `entity:contact` | The operator of the host. |
| `:org` | `ou:org` | The org that operates the given host. |
| `:os` | `it:software` | The operating system of the host. |
| `:os:name` | `it:softwarename` | A software product name for the host operating system. Used for entity resolution. |
| `:parent` | `it:component` | The parent cloud host which this cloud host is part of. |
| `:period` | `phys:lifespan` | The period when the cloud host existed, from its creation until it was retired or destroyed. |
| `:place` | `geo:place` | The place where the cloud host was located. |
| `:place:address` | `geo:address` | The postal address where the cloud host was located. |
| `:place:address:city` | `base:name` | The city where the cloud host was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the cloud host was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the cloud host was located. |
| `:place:country` | `pol:country` | The country where the cloud host was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the cloud host was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the cloud host was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the cloud host was located. |
| `:place:loc` | `loc` | The geopolitical location where the cloud host was located. |
| `:place:name` | `geo:name` | The name of the place where the cloud host was located. |
| `:platform` | `inet:service:platform` | The platform which defines the cloud host. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the cloud host. |
| `:seen` | `ival` | The cloud host was observed during the time interval. |
| `:serial` | `base:id` | The serial number of the cloud host. |
| `:status` | `title` | The status of the cloud host. |
| `:url` | `inet:url` | The primary URL associated with the cloud host. |

### `it:cmd`

A unique command-line string.

| Interface |
|-----------|
| `meta:usable` |

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

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this command line session. |
| `:actor` | `inet:service:account`, `inet:service:agent`, `it:host:account` | The account or agent which executed the commands in the session. |
| `:actor:name` | `entity:name` | The name of the actor who ran the command line session. |
| `:file` | `file:bytes` | The file containing the command history such as a .bash_history file. |
| `:host` | `it:host` | The host where the command line session was executed. |
| `:period` | `activity` | The period over which the command line session occurred. |
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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the object. |
| `:desc` | `text` | A free-form description of the repository. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:name` | `title` | The name of the repository. |
| `:period` | `it:lifespan` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `title` | The status of the object. |
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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the object. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:merged` | `time` | The time this branch was merged back into its parent. |
| `:name` | `base:name` | The name of the branch. |
| `:parent` | `it:dev:repo:branch` | The branch this branch was branched from. |
| `:period` | `it:lifespan` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:start` | `it:dev:repo:commit` | The commit in the parent branch this branch was created at. |
| `:status` | `title` | The status of the object. |
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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the object. |
| `:id` | `base:id` | The version control system specific commit identifier. |
| `:mesg` | `text` | The commit message describing the changes in the commit. |
| `:parents` | `array of it:dev:repo:commit` | The commit or commits this commit is immediately based on. |
| `:period` | `it:lifespan` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the object. |
| `:repo` | `it:dev:repo` | The repository the commit lives in. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `title` | The status of the object. |
| `:url` | `inet:url` | The URL where the commit is hosted. |

### `it:dev:repo:diff`

A diff of a file being applied in a single commit.

| Interface |
|-----------|
| `file:entry` |
| `inet:service:commentable` |

| Property | Type | Doc |
|----------|------|-----|
| `:commit` | `it:dev:repo:commit` | The commit that produced this diff. |
| `:file` | `file:bytes` | The file associated with the repo diff. |
| `:path` | `file:path` | The path of the file associated with the repo diff. |
| `:url` | `inet:url` | The URL where the diff is hosted. |

### `it:dev:repo:entry`

A file included in a repository.

| Interface |
|-----------|
| `file:entry` |

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file included in the repository. |
| `:path` | `file:path` | The path of the file included in the repository. |
| `:repo` | `it:dev:repo` | The repository which contains the file. |

### `it:dev:repo:issue`

An issue raised in a repository.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `inet:service:base` |
| `inet:service:commentable` |
| `inet:service:labelable` |
| `inet:service:object` |
| `meta:causal` |
| `meta:observable` |
| `meta:task` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this issue. |
| `:assignee` | `entity:actor` | The actor who is assigned to complete the issue. |
| `:created` | `time` | The time the issue was created. |
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the issue. |
| `:desc` | `text` | The text describing the issue. |
| `:due` | `time` | The time the issue must be complete. |
| `:id` | `base:id` | The ID of the issue in the repository system. |
| `:name` | `title` | The name of the issue. |
| `:parent` | `meta:task` | The parent task which includes this issue. |
| `:period` | `it:lifespan` | The period when the issue existed. |
| `:platform` | `inet:service:platform` | The platform which defines the issue. |
| `:priority` | `meta:score` | The priority of the issue. |
| `:project` | `proj:project` | The project containing the issue. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the issue. |
| `:repo` | `it:dev:repo` | The repo where the issue was logged. |
| `:seen` | `ival` | The issue was observed during the time interval. |
| `:status` | `title` | The status of the issue. |
| `:updated` | `time` | The time the issue was updated. |
| `:url` | `inet:url` | The URL where the issue is hosted. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `it:dev:repo:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `it:dev:str`

A developer selected string.

| Interface |
|-----------|
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The string was observed during the time interval. |

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
| `:activity` | `base:activity` | A parent activity which includes this bind event. |
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
| `:activity` | `base:activity` | A parent activity which includes this fetch event. |
| `:browser` | `it:software` | The software version of the browser. |
| `:client` | `inet:client` | The address of the client during the URL retrieval. |
| `:exe` | `file:bytes` | The specific file containing code that requested the URL. |
| `:host` | `it:host` | The host running the process that requested the URL. |
| `:page:components` | `array of it:softwarename` | The software components included in the rendered page. |
| `:page:favicon` | `file:bytes` | The favicon of the rendered page. |
| `:page:html` | `file:bytes` | The rendered DOM saved as an HTML file. |
| `:page:image` | `file:bytes` | The rendered DOM saved as an image. |
| `:page:pdf` | `file:bytes` | The rendered DOM saved as a PDF file. |
| `:page:title` | `it:dev:str` | The title of the rendered page. |
| `:proc` | `it:exec:proc` | The main process executing code that requested the URL. |
| `:request` | `inet:proto:request` | The request made to retrieve the initial URL contents. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the fetch event. |
| `:time` | `time` | The time the URL was requested. |
| `:url` | `inet:url` | The URL that was requested. |

### `it:exec:file:add`

An instance of a host adding a file to a filesystem.

| Interface |
|-----------|
| `base:event` |
| `file:entry` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this file add event. |
| `:exe` | `file:bytes` | The specific file containing code that created the new file. |
| `:file` | `file:bytes` | The file associated with the file add event. |
| `:host` | `it:host` | The host running the process that created the new file. |
| `:path` | `file:path` | The path of the file associated with the file add event. |
| `:proc` | `it:exec:proc` | The main process executing code that created the new file. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the file add event. |
| `:time` | `time` | The time the file was created. |

### `it:exec:file:del`

An instance of a host deleting a file from a filesystem.

| Interface |
|-----------|
| `base:event` |
| `file:entry` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this file delete event. |
| `:exe` | `file:bytes` | The specific file containing code that deleted the file. |
| `:file` | `file:bytes` | The file associated with the file delete event. |
| `:host` | `it:host` | The host running the process that deleted the file. |
| `:path` | `file:path` | The path of the file associated with the file delete event. |
| `:proc` | `it:exec:proc` | The main process executing code that deleted the file. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the file delete event. |
| `:time` | `time` | The time the file was deleted. |

### `it:exec:file:read`

An instance of a host reading a file from a filesystem.

| Interface |
|-----------|
| `base:event` |
| `file:entry` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this file read event. |
| `:exe` | `file:bytes` | The specific file containing code that read the file. |
| `:file` | `file:bytes` | The file associated with the file read event. |
| `:host` | `it:host` | The host running the process that read the file. |
| `:path` | `file:path` | The path of the file associated with the file read event. |
| `:proc` | `it:exec:proc` | The main process executing code that read the file. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the file read event. |
| `:time` | `time` | The time the file was read. |

### `it:exec:file:write`

An instance of a host writing a file to a filesystem.

| Interface |
|-----------|
| `base:event` |
| `file:entry` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this file write event. |
| `:exe` | `file:bytes` | The specific file containing code that wrote to the file. |
| `:file` | `file:bytes` | The file associated with the file write event. |
| `:host` | `it:host` | The host running the process that wrote to the file. |
| `:path` | `file:path` | The path of the file associated with the file write event. |
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
| `:activity` | `base:activity` | A parent activity which includes this library load event. |
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
| `:activity` | `base:activity` | A parent activity which includes this memory map event. |
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
| `:activity` | `base:activity` | A parent activity which includes this mutex creation event. |
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
| `:activity` | `base:activity` | A parent activity which includes this pipe creation event. |
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
| `:activity` | `base:activity` | A parent activity which includes this process. |
| `:cmd` | `it:cmd` | The command string used to launch the process. |
| `:cmd:history` | `it:cmd:history` | The command history entry which caused this process to be run. |
| `:exe` | `file:bytes` | The main executable file for the process. |
| `:exitcode` | `int` | The exit code for the process. |
| `:host` | `it:host` | The host that executed the process. |
| `:name` | `str` | The display name specified by the process. |
| `:parent` | `it:exec:proc` | The parent process which created this process. |
| `:path` | `file:path` | The path to the executable of the process. |
| `:period` | `activity` | The period over which the process occurred. |
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
| `:activity` | `base:activity` | A parent activity which includes this process creation event. |
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
| `:activity` | `base:activity` | A parent activity which includes this process signal event. |
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
| `:activity` | `base:activity` | A parent activity which includes this process termination event. |
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
| `:activity` | `base:activity` | A parent activity which includes this query event. |
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
| `:activity` | `base:activity` | A parent activity which includes this screenshot event. |
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
| `:activity` | `base:activity` | A parent activity which includes this thread. |
| `:exe` | `file:bytes` | The executable file which caused the thread. |
| `:exitcode` | `int` | The exit code or return value for the thread. |
| `:host` | `it:host` | The host on which the thread occurred. |
| `:period` | `activity` | The period over which the thread occurred. |
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
| `:activity` | `base:activity` | A parent activity which includes this thread creation event. |
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
| `:activity` | `base:activity` | A parent activity which includes this thread termination event. |
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
| `:activity` | `base:activity` | A parent activity which includes this registry delete event. |
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
| `:activity` | `base:activity` | A parent activity which includes this registry get event. |
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
| `:activity` | `base:activity` | A parent activity which includes this registry set event. |
| `:entry` | `it:os:windows:registry:entry` | The registry key or value that was written to. |
| `:exe` | `file:bytes` | The specific file containing code that wrote to the registry. |
| `:host` | `it:host` | The host running the process that wrote to the registry. |
| `:proc` | `it:exec:proc` | The main process executing code that wrote to the registry. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the registry set event. |
| `:time` | `time` | The time the registry was written to. |

### `it:exec:windows:service:add`

An event where a Microsoft Windows service configuration was added to a host.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:exe` | `file:bytes` | The executable file which caused the activity. |
| `:host` | `it:host` | The host on which the activity occurred. |
| `:proc` | `it:exec:proc` | The process which caused the event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:target` | `it:os:windows:service` | The service which was added. |
| `:thread` | `it:exec:thread` | The thread which caused the event. |
| `:time` | `time` | The time that the event occurred. |

### `it:exec:windows:service:del`

An event where a Microsoft Windows service configuration was removed from a host.

| Interface |
|-----------|
| `base:event` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:exe` | `file:bytes` | The executable file which caused the activity. |
| `:host` | `it:host` | The host on which the activity occurred. |
| `:proc` | `it:exec:proc` | The process which caused the event. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:target` | `it:os:windows:service` | The service which was removed. |
| `:thread` | `it:exec:thread` | The thread which caused the event. |
| `:time` | `time` | The time that the event occurred. |

### `it:hardware`

A specification for a piece of IT hardware.

| Interface |
|-----------|
| `biz:manufactured` |
| `meta:observable` |
| `meta:usable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:cpe` | `it:sec:cpe` | The NIST CPE 2.3 string specifying this hardware. |
| `:desc` | `text` | A brief description of the hardware. |
| `:manufacturer` | `entity:actor` | The organization that manufactures this hardware. |
| `:manufacturer:name` | `entity:name` | The name of the organization that manufactures this hardware. |
| `:model` | `biz:model` | The model number or name of the hardware. |
| `:name` | `base:name` | The name of the hardware. |
| `:parts` | `array of it:hardware` | An array of it:hardware parts included in this hardware specification. |
| `:released` | `time` | The initial release date for this hardware. |
| `:seen` | `ival` | The hardware was observed during the time interval. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `it:hardware:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `it:host`

A GUID that represents a host or system.

| Interface |
|-----------|
| `entity:creatable` |
| `geo:locatable` |
| `it:component` |
| `meta:havable` |
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the host. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the host. |
| `:desc` | `text` | A free-form description of the host. |
| `:hardware` | `it:hardware` | The hardware specification of the host. |
| `:id` | `base:id` | An external identifier for the host. |
| `:image` | `it:software:image` | The container image or OS image running on the host. |
| `:ip` | `inet:ip` | The last known IP address for the host. |
| `:keyboard:language` | `lang:language` | The primary keyboard input language configured on the host. |
| `:keyboard:layout` | `base:name` | The primary keyboard layout configured on the host. |
| `:name` | `it:hostname` | The name of the host or system. |
| `:operator` | `entity:contact` | The operator of the host. |
| `:org` | `ou:org` | The org that operates the given host. |
| `:os` | `it:software` | The operating system of the host. |
| `:os:name` | `it:softwarename` | A software product name for the host operating system. Used for entity resolution. |
| `:parent` | `it:component` | The parent host which this host is part of. |
| `:period` | `phys:lifespan` | The period when the host existed, from its creation until it was retired or destroyed. |
| `:place` | `geo:place` | The place where the host was located. |
| `:place:address` | `geo:address` | The postal address where the host was located. |
| `:place:address:city` | `base:name` | The city where the host was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the host was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the host was located. |
| `:place:country` | `pol:country` | The country where the host was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the host was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the host was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the host was located. |
| `:place:loc` | `loc` | The geopolitical location where the host was located. |
| `:place:name` | `geo:name` | The name of the place where the host was located. |
| `:seen` | `ival` | The host was observed during the time interval. |
| `:serial` | `base:id` | The serial number of the host. |

### `it:host:account`

A local account on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:home` | `file:path` | The path to the account's home directory. |
| `:host` | `it:host` | The host where the account is registered. |
| `:id` | `base:id` | The unique OS specific identifier for the account. |
| `:period` | `ival` | The period where the account existed. |
| `:profile` | `entity:contact` | Current contact information for the account. |
| `:service:account` | `inet:service:account` | The optional service account which the local account maps to. |
| `:username` | `entity:name` | The username associated with the account. |

### `it:host:component`

Hardware components which are part of a host.

| Property | Type | Doc |
|----------|------|-----|
| `:hardware` | `it:hardware` | The hardware specification of this component. |
| `:host` | `it:host` | The it:host which has this component installed. |
| `:period` | `ival` | The time period when the component was part of the host. |
| `:serial` | `base:id` | The serial number of this component. |

### `it:host:group`

A local group on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A brief description of the group. |
| `:host` | `it:host` | The host where the group was created. |
| `:id` | `base:id` | The unique OS specific identifier for the group. |
| `:name` | `base:name` | The name of the group. |
| `:service:role` | `inet:service:role` | The optional service role which the local group maps to. |

### `it:host:group:membership`

A host account or group being a member of a host group during a period.

| Property | Type | Doc |
|----------|------|-----|
| `:group` | `it:host:group` | The group which had the member. |
| `:member` | `it:host:account`, `it:host:group` | The account or group that was a member of the group. |
| `:period` | `ival` | The time period where the membership was active. |

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

### `it:host:login`

A login event on a host.

| Interface |
|-----------|
| `base:event` |
| `inet:proto:link` |
| `inet:proto:login` |
| `inet:proto:request` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `it:host:account` | The account that logged in. |
| `:activity` | `base:activity` | A parent activity which includes this host login. |
| `:client` | `inet:client` | The socket address of the client. |
| `:client:exe` | `file:bytes` | The client executable which initiated the host login. |
| `:client:host` | `it:host` | The client host which initiated the host login. |
| `:client:proc` | `it:exec:proc` | The client process which initiated the host login. |
| `:credential` | `auth:credential` | The credential presented during the host login. |
| `:flow` | `inet:flow` | The network flow which contained the host login. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:server` | `inet:server` | The socket address of the server. |
| `:server:exe` | `file:bytes` | The server executable which received the host login. |
| `:server:host` | `it:host` | The server host which received the host login. |
| `:server:proc` | `it:exec:proc` | The server process which received the host login. |
| `:session` | `inet:proto:session` | The protocol session established by the host login. |
| `:success` | `bool` | Set to true if the host login was successful. |
| `:time` | `time` | The time that the host login occurred. |

### `it:host:posix:account`

A POSIX account on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:gecos` | `title` | The GECOS field for the account. |
| `:gid` | `it:os:posix:id` | The primary group ID of the account. |
| `:home` | `file:path` | The path to the account's home directory. |
| `:host` | `it:host` | The host where the account is registered. |
| `:id` | `it:os:posix:id` | The POSIX user ID of the account. |
| `:period` | `ival` | The period where the account existed. |
| `:profile` | `entity:contact` | Current contact information for the account. |
| `:service:account` | `inet:service:account` | The optional service account which the local account maps to. |
| `:shell` | `file:path` | The path to the account's default shell. |
| `:username` | `entity:name` | The username associated with the account. |

### `it:host:posix:group`

A POSIX group on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A brief description of the group. |
| `:host` | `it:host` | The host where the group was created. |
| `:id` | `it:os:posix:id` | The POSIX ID of the group. |
| `:name` | `base:name` | The name of the group. |
| `:service:role` | `inet:service:role` | The optional service role which the local group maps to. |

### `it:host:session`

An authenticated session on a host.

| Interface |
|-----------|
| `base:activity` |
| `inet:proto:session` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `it:host:account` | The account whose host login session this is. |
| `:activity` | `base:activity` | A parent activity which includes this host login session. |
| `:client` | `inet:client` | The socket address of the client which initiated the host login session. |
| `:client:host` | `it:host` | The host which initiated the host login session. |
| `:period` | `activity` | The period over which the host login session occurred. |
| `:server` | `inet:server` | The socket address of the server which received the host login session. |
| `:server:host` | `it:host` | The host which received the host login session. |

### `it:host:telem`

A telemetry measurement taken from a host.

| Interface |
|-----------|
| `base:event` |
| `geo:locatable` |
| `it:host:event` |
| `it:host:exec` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account`, `it:host:account` | The service or host account associated with the telemetry sample. |
| `:activity` | `base:activity` | A parent activity which includes this telemetry sample. |
| `:app` | `it:software` | The app used to report the telemetry sample. |
| `:contact` | `entity:contact` | The contact information associated with the telemetry sample. |
| `:contact:email` | `inet:email` | The email address associated with the telemetry sample. |
| `:contact:identifiers` | `array of entity:identifier` | Identifiers associated with the telemetry sample. |
| `:contact:name` | `entity:name` | The user name associated with the telemetry sample. |
| `:contact:phone` | `tel:phone` | The phone number of the device associated with the telemetry sample. |
| `:exe` | `file:bytes` | The executable file which caused the telemetry sample. |
| `:host` | `it:host` | The host on which the telemetry sample occurred. |
| `:nic` | `it:nic` | The NIC associated with the telemetry sample. |
| `:nic:ip` | `inet:ip` | The IP address of the device associated with the telemetry sample. |
| `:nic:link` | `inet:data:link` | The data link associated with the telemetry sample. |
| `:nic:mac` | `inet:mac` | The MAC address of the device associated with the telemetry sample. |
| `:place` | `geo:place` | The place where the telemetry sample was located. |
| `:place:address` | `geo:address` | The postal address where the telemetry sample was located. |
| `:place:address:city` | `base:name` | The city where the telemetry sample was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the telemetry sample was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the telemetry sample was located. |
| `:place:country` | `pol:country` | The country where the telemetry sample was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the telemetry sample was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the telemetry sample was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the telemetry sample was located. |
| `:place:loc` | `loc` | The geopolitical location where the telemetry sample was located. |
| `:place:name` | `geo:name` | The name of the place where the telemetry sample was located. |
| `:proc` | `it:exec:proc` | The process which caused the telemetry sample. |
| `:request` | `inet:proto:request` | The request that the telemetry was extracted from. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:thread` | `it:exec:thread` | The thread which caused the telemetry sample. |
| `:time` | `time` | The time that the telemetry sample occurred. |

### `it:host:tenancy`

A time window where a host was a tenant run by another host.

| Property | Type | Doc |
|----------|------|-----|
| `:parent` | `it:host` | The host which provides runtime resources to the tenant host. |
| `:period` | `ival` | The period when the host tenancy was active. |
| `:tenant` | `it:host` | The host which is run within the resources provided by the parent. |

### `it:host:windows:account`

A Windows account on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:home` | `file:path` | The path to the account's home directory. |
| `:host` | `it:host` | The host where the account is registered. |
| `:id` | `it:os:windows:sid` | The Microsoft Windows Security Identifier of the account. |
| `:period` | `ival` | The period where the account existed. |
| `:profile` | `entity:contact` | Current contact information for the account. |
| `:service:account` | `inet:service:account` | The optional service account which the local account maps to. |
| `:username` | `entity:name` | The username associated with the account. |

### `it:host:windows:group`

A Windows group on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A brief description of the group. |
| `:host` | `it:host` | The host where the group was created. |
| `:id` | `it:os:windows:sid` | The Microsoft Windows Security Identifier of the group. |
| `:name` | `base:name` | The name of the group. |
| `:service:role` | `inet:service:role` | The optional service role which the local group maps to. |

### `it:hostname`

The name of a host or system.

| Interface |
|-----------|
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:seen` | `ival` | The hostname was observed during the time interval. |

### `it:installed`

The installation of a component or software on a host component.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this installation. |
| `:actor` | `entity:actor` | The actor who performed the installation. |
| `:actor:name` | `entity:name` | The name of the actor who performed the installation. |
| `:item` | `it:component`, `it:software` | The component or software which was installed. |
| `:on` | `it:component` | The component which the item was installed on. |
| `:period` | `activity` | The period over which the installation occurred. |

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
| `:activity` | `base:activity` | A parent activity which includes this log event. |
| `:data` | `data` | A raw JSON record of the log event. |
| `:exe` | `file:bytes` | The executable file which caused the log event. |
| `:host` | `it:host` | The host on which the log event occurred. |
| `:id` | `base:id` | An external id that uniquely identifies this log entry. |
| `:mesg` | `text` | The log message text. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `it:log:event:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:dns:resolvers` | `array of inet:server` | An array of DNS servers configured to resolve requests for hosts on the network. |
| `:name` | `base:name` | The name of the network. |
| `:net` | `inet:net` | The optional contiguous IP address range of this network. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `it:network:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `it:nic`

A Network Interface Card (NIC).

| Interface |
|-----------|
| `entity:creatable` |
| `geo:locatable` |
| `it:component` |
| `meta:havable` |
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the NIC. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the NIC. |
| `:hardware` | `it:hardware` | The hardware specification of the NIC. |
| `:ip` | `inet:ip` | The IP address of the NIC. |
| `:mac` | `inet:mac` | The ethernet (MAC) address of the NIC. |
| `:name` | `title` | The name of the NIC. |
| `:network` | `it:network` | The network that the NIC is connected to. |
| `:parent` | `it:component` | The parent NIC which this NIC is part of. |
| `:period` | `phys:lifespan` | The period when the NIC existed, from its creation until it was retired or destroyed. |
| `:place` | `geo:place` | The place where the NIC was located. |
| `:place:address` | `geo:address` | The postal address where the NIC was located. |
| `:place:address:city` | `base:name` | The city where the NIC was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the NIC was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the NIC was located. |
| `:place:country` | `pol:country` | The country where the NIC was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the NIC was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the NIC was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the NIC was located. |
| `:place:loc` | `loc` | The geopolitical location where the NIC was located. |
| `:place:name` | `geo:name` | The name of the place where the NIC was located. |
| `:seen` | `ival` | The NIC was observed during the time interval. |
| `:serial` | `base:id` | The serial number of the NIC. |

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
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:description` | `text` | The description of the service from the Description registry key. |
| `:displayname` | `base:name` | The friendly name of the service from the DisplayName registry key. |
| `:errorcontrol` | `uint32` | The service error handling behavior from the ErrorControl registry key. |
| `:exe` | `file:bytes` | The executable file which caused the activity. |
| `:host` | `it:host` | The host that the service was configured on. |
| `:imagepath` | `file:path` | The path to the service binary from the ImagePath registry key. |
| `:name` | `base:name` | The name of the service from the registry key within Services. |
| `:period` | `activity` | The period over which the activity occurred. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |
| `:start` | `uint32` | The start configuration of the service from the Start registry key. |
| `:type` | `uint32` | The type of service from the Type registry key. |

### `it:physical:host`

A host which consists of dedicated physical hardware.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `entity:destroyable` |
| `geo:locatable` |
| `it:component` |
| `meta:havable` |
| `meta:observable` |
| `phys:object` |
| `phys:tangible` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the host. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the host. |
| `:desc` | `text` | A free-form description of the host. |
| `:hardware` | `it:hardware` | The hardware specification of the host. |
| `:id` | `base:id` | An external identifier for the host. |
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
| `:parent` | `it:component` | The parent host which this host is part of. |
| `:period` | `phys:lifespan` | The period when the host existed, from its creation until it was retired or destroyed. |
| `:phys:height` | `phys:distance` | The physical height of the host. |
| `:phys:length` | `phys:distance` | The physical length of the host. |
| `:phys:mass` | `phys:mass` | The physical mass of the host. |
| `:phys:volume` | `phys:volume` | The physical volume of the host. |
| `:phys:width` | `phys:distance` | The physical width of the host. |
| `:place` | `geo:place` | The place where the host was located. |
| `:place:address` | `geo:address` | The postal address where the host was located. |
| `:place:address:city` | `base:name` | The city where the host was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the host was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the host was located. |
| `:place:country` | `pol:country` | The country where the host was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the host was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the host was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the host was located. |
| `:place:loc` | `loc` | The geopolitical location where the host was located. |
| `:place:name` | `geo:name` | The name of the place where the host was located. |
| `:seen` | `ival` | The host was observed during the time interval. |
| `:serial` | `base:id` | The serial number of the host. |

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
| `:name` | `title` | The CWE name. |
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
| `:confidence` | `it:sec:stix:confidence` | The confidence field from the STIX indicator. |
| `:created` | `time` | The time that the indicator pattern was first created. |
| `:desc` | `text` | The description field from the STIX indicator. |
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
| `:id` | `base:id` | An externally generated ID for the scan. |
| `:operator` | `entity:contact` | Contact information for the scan operator. |
| `:software` | `it:software` | The scanning software used. |
| `:software:name` | `it:softwarename` | The name of the scanner software. |
| `:time` | `time` | The time that the scan was started. |

### `it:sec:vuln:scan:result`

A vulnerability scan result for an asset.

| Property | Type | Doc |
|----------|------|-----|
| `:asset` | `risk:exploitable` | The node which is vulnerable. |
| `:desc` | `text` | A description of the vulnerability and how it was detected in the asset. |
| `:ext:url` | `inet:url` | An external URL which documents the scan result. |
| `:id` | `base:id` | An externally generated ID for the scan result. |
| `:mitigated` | `time` | The time that the vulnerability in the asset was mitigated. |
| `:mitigation` | `meta:technique` | The mitigation used to address this asset vulnerability. |
| `:priority` | `meta:score` | The priority of mitigating the vulnerability. |
| `:scan` | `it:sec:vuln:scan` | The scan that discovered the vulnerability in the asset. |
| `:severity` | `meta:score` | The severity of the vulnerability in the asset. Use "none" for no vulnerability discovered. |
| `:time` | `time` | The time that the scan result was produced. |
| `:vuln` | `risk:vuln` | The vulnerability detected in the asset. |

### `it:sim:card`

A SIM card.

| Interface |
|-----------|
| `entity:creatable` |
| `geo:locatable` |
| `it:component` |
| `meta:havable` |
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the SIM card. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the SIM card. |
| `:hardware` | `it:hardware` | The hardware specification of the SIM card. |
| `:imsi` | `tel:mob:imsi` | The IMSI of the subscriber associated with the SIM card. |
| `:parent` | `it:component` | The parent SIM card which this SIM card is part of. |
| `:period` | `phys:lifespan` | The period when the SIM card existed, from its creation until it was retired or destroyed. |
| `:place` | `geo:place` | The place where the SIM card was located. |
| `:place:address` | `geo:address` | The postal address where the SIM card was located. |
| `:place:address:city` | `base:name` | The city where the SIM card was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the SIM card was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the SIM card was located. |
| `:place:country` | `pol:country` | The country where the SIM card was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the SIM card was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the SIM card was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the SIM card was located. |
| `:place:loc` | `loc` | The geopolitical location where the SIM card was located. |
| `:place:name` | `geo:name` | The name of the place where the SIM card was located. |
| `:seen` | `ival` | The SIM card was observed during the time interval. |
| `:serial` | `base:id` | The serial number of the SIM card. |

### `it:sim:slot`

A SIM slot.

| Interface |
|-----------|
| `entity:creatable` |
| `geo:locatable` |
| `it:component` |
| `meta:havable` |
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the SIM slot. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the SIM slot. |
| `:hardware` | `it:hardware` | The hardware specification of the SIM slot. |
| `:imei` | `tel:mob:imei` | The IMEI of the device associated with the SIM slot. |
| `:parent` | `it:component` | The parent SIM slot which this SIM slot is part of. |
| `:period` | `phys:lifespan` | The period when the SIM slot existed, from its creation until it was retired or destroyed. |
| `:place` | `geo:place` | The place where the SIM slot was located. |
| `:place:address` | `geo:address` | The postal address where the SIM slot was located. |
| `:place:address:city` | `base:name` | The city where the SIM slot was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the SIM slot was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the SIM slot was located. |
| `:place:country` | `pol:country` | The country where the SIM slot was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the SIM slot was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the SIM slot was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the SIM slot was located. |
| `:place:loc` | `loc` | The geopolitical location where the SIM slot was located. |
| `:place:name` | `geo:name` | The name of the place where the SIM slot was located. |
| `:seen` | `ival` | The SIM slot was observed during the time interval. |
| `:serial` | `base:id` | The serial number of the SIM slot. |

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
| `:availability` | `title` | The source's assessed availability of the software. |
| `:cpe` | `it:sec:cpe` | The NIST CPE 2.3 string specifying this software version. |
| `:created` | `time` | The time that the software was created. |
| `:creator` | `entity:actor` | The primary actor which created the software. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the software. |
| `:desc` | `text` | A description of the software. |
| `:id` | `base:id`, `it:mitre:attack:software:id` | A unique ID given to the software. |
| `:ids` | `array of base:id, it:mitre:attack:software:id` | An array of alternate IDs given to the software. |
| `:name` | `it:softwarename` | The name of the software. |
| `:names` | `array of it:softwarename` | Observed/variant names for this software version. |
| `:parent` | `it:software` | The parent software version or family. |
| `:released` | `time` | Timestamp for when the software was released. |
| `:reporter` | `entity:actor` | The entity which reported on the software. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the software. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the software. |
| `:reporter:period` | `reported` | The period when the software existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the software. |
| `:reporter:supersedes` | `array of it:software` | An array of software nodes which are superseded by this software. |
| `:reporter:updated` | `time` | The time when the software was last updated. |
| `:reporter:url` | `inet:url` | The URL for the software provided by the reporter. |
| `:resolved` | `it:software` | The authoritative software which this reporting is about. |
| `:risk:score` | `meta:score` | The risk posed by the software. |
| `:seen` | `ival` | The software was observed during the time interval. |
| `:sophistication` | `meta:score` | The source's assessed sophistication of the software. |
| `:supersedes` | `array of it:software` | An array of software versions which are superseded by this software. |
| `:tag` | `syn:tag` | The tag used to annotate nodes that are associated with the software. |
| `:type` | `it:software:type:taxonomy` | The type of software. |
| `:updated` | `time` | The time that the software was last updated. |
| `:url` | `inet:url` | The URL where the software is available. |
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
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the object. |
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:name` | `it:softwarename` | The name of the image. |
| `:parents` | `array of it:software:image` | An array of parent images in precedence order. |
| `:period` | `it:lifespan` | The period when the object existed. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |
| `:published` | `time` | The time the image was published. |
| `:publisher` | `entity:contact` | The contact information of the org or person who published the image. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the object. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:status` | `title` | The status of the object. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `it:software:image:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `it:software:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:size` | `size` | The size of the volume in bytes. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `it:storage:volume:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `it:virtual:host`

A host which runs as a virtualized instance.

| Interface |
|-----------|
| `entity:creatable` |
| `geo:locatable` |
| `it:component` |
| `meta:havable` |
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the virtual host. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the virtual host. |
| `:desc` | `text` | A free-form description of the host. |
| `:hardware` | `it:hardware` | The hardware specification of the virtual host. |
| `:id` | `base:id` | An external identifier for the host. |
| `:image` | `it:software:image` | The container image or OS image running on the host. |
| `:ip` | `inet:ip` | The last known IP address for the host. |
| `:keyboard:language` | `lang:language` | The primary keyboard input language configured on the host. |
| `:keyboard:layout` | `base:name` | The primary keyboard layout configured on the host. |
| `:name` | `it:hostname` | The name of the host or system. |
| `:operator` | `entity:contact` | The operator of the host. |
| `:org` | `ou:org` | The org that operates the given host. |
| `:os` | `it:software` | The operating system of the host. |
| `:os:name` | `it:softwarename` | A software product name for the host operating system. Used for entity resolution. |
| `:parent` | `it:host` | The host which runs the virtual host. |
| `:period` | `phys:lifespan` | The period when the virtual host existed, from its creation until it was retired or destroyed. |
| `:place` | `geo:place` | The place where the virtual host was located. |
| `:place:address` | `geo:address` | The postal address where the virtual host was located. |
| `:place:address:city` | `base:name` | The city where the virtual host was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the virtual host was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the virtual host was located. |
| `:place:country` | `pol:country` | The country where the virtual host was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the virtual host was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the virtual host was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the virtual host was located. |
| `:place:loc` | `loc` | The geopolitical location where the virtual host was located. |
| `:place:name` | `geo:name` | The name of the place where the virtual host was located. |
| `:seen` | `ival` | The virtual host was observed during the time interval. |
| `:serial` | `base:id` | The serial number of the virtual host. |

### `it:wifi:nic`

A wireless Network Interface Card (NIC).

| Interface |
|-----------|
| `entity:creatable` |
| `geo:locatable` |
| `it:component` |
| `meta:havable` |
| `meta:observable` |
| `risk:exploitable` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the Wi-Fi NIC. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the Wi-Fi NIC. |
| `:hardware` | `it:hardware` | The hardware specification of the Wi-Fi NIC. |
| `:ip` | `inet:ip` | The IP address of the Wi-Fi NIC. |
| `:mac` | `inet:mac` | The ethernet (MAC) address of the Wi-Fi NIC. |
| `:name` | `title` | The name of the Wi-Fi NIC. |
| `:network` | `it:network` | The network that the Wi-Fi NIC is connected to. |
| `:parent` | `it:component` | The parent Wi-Fi NIC which this Wi-Fi NIC is part of. |
| `:period` | `phys:lifespan` | The period when the Wi-Fi NIC existed, from its creation until it was retired or destroyed. |
| `:place` | `geo:place` | The place where the Wi-Fi NIC was located. |
| `:place:address` | `geo:address` | The postal address where the Wi-Fi NIC was located. |
| `:place:address:city` | `base:name` | The city where the Wi-Fi NIC was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the Wi-Fi NIC was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the Wi-Fi NIC was located. |
| `:place:country` | `pol:country` | The country where the Wi-Fi NIC was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the Wi-Fi NIC was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the Wi-Fi NIC was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the Wi-Fi NIC was located. |
| `:place:loc` | `loc` | The geopolitical location where the Wi-Fi NIC was located. |
| `:place:name` | `geo:name` | The name of the place where the Wi-Fi NIC was located. |
| `:seen` | `ival` | The Wi-Fi NIC was observed during the time interval. |
| `:serial` | `base:id` | The serial number of the Wi-Fi NIC. |
| `:ssid` | `inet:wifi:ssid` | The SSID associated with the Wi-Fi NIC. |

### `lang:code`

An IETF BCP-47 language tag.

| Property | Type | Doc |
|----------|------|-----|
| `:language` | `str:lower` | The primary language subtag. |
| `:region` | `str:upper` | The region subtag. |
| `:script` | `str` | The script subtag. |

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
| `entity:destroyable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The name of the material item. |
| `:period` | `phys:lifespan` | The period when the item existed, from its creation until it was retired or destroyed. |
| `:phys:height` | `phys:distance` | The physical height of the item. |
| `:phys:length` | `phys:distance` | The physical length of the item. |
| `:phys:mass` | `phys:mass` | The physical mass of the item. |
| `:phys:volume` | `phys:volume` | The physical volume of the item. |
| `:phys:width` | `phys:distance` | The physical width of the item. |
| `:place` | `geo:place` | The place where the item was located. |
| `:place:address` | `geo:address` | The postal address where the item was located. |
| `:place:address:city` | `base:name` | The city where the item was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the item was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the item was located. |
| `:place:country` | `pol:country` | The country where the item was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the item was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the item was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the item was located. |
| `:place:loc` | `loc` | The geopolitical location where the item was located. |
| `:place:name` | `geo:name` | The name of the place where the item was located. |
| `:spec` | `mat:spec` | The specification which defines this item. |
| `:type` | `mat:item:type:taxonomy` | The taxonomy type of the item. |

### `mat:spec`

A GUID assigned to a material specification.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `base:name` | The name of the material specification. |
| `:type` | `mat:spec:type:taxonomy` | The taxonomy type for the specification. |

### `mat:spec:type:taxonomy`

A hierarchical taxonomy of material specification types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `mat:spec:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `meta:activity`

Analytically relevant activity.

| Interface |
|-----------|
| `base:activity` |
| `entity:attendable` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:desc` | `text` | A description of the activity. |
| `:name` | `base:name` | The name of the activity. |
| `:period` | `activity` | The period over which the activity occurred. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:aggregate:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `meta:algorithm`

A mathematical or cryptographic algorithm.

| Interface |
|-----------|
| `meta:observable` |
| `meta:usable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time that the algorithm was authored. |
| `:desc` | `text` | A description of the algorithm. |
| `:name` | `base:name` | The name of the algorithm. |
| `:seen` | `ival` | The node was observed during the time interval. |
| `:type` | `meta:algorithm:type:taxonomy` | The type of algorithm. |

### `meta:algorithm:type:taxonomy`

A hierarchical taxonomy of algorithm types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:algorithm:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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

### `meta:cluster`

A cluster of analytically relevant nodes generated by a specific source.

| Interface |
|-----------|
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the cluster. |
| `:id` | `base:id` | A unique ID given to the cluster. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the cluster. |
| `:name` | `base:name` | The primary name of the cluster. |
| `:names` | `array of base:name` | A list of alternate names for the cluster. |
| `:reporter` | `entity:actor` | The entity which reported on the cluster. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the cluster. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the cluster. |
| `:reporter:period` | `reported` | The period when the cluster existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the cluster. |
| `:reporter:supersedes` | `array of meta:cluster` | An array of cluster nodes which are superseded by this cluster. |
| `:reporter:updated` | `time` | The time when the cluster was last updated. |
| `:reporter:url` | `inet:url` | The URL for the cluster provided by the reporter. |
| `:resolved` | `meta:cluster` | The authoritative cluster which this reporting is about. |
| `:tag` | `syn:tag` | The tag used to annotate nodes that are associated with the cluster. |
| `:type` | `meta:cluster:type:taxonomy` | The type of cluster. |

### `meta:cluster:type:taxonomy`

A type taxonomy for meta:cluster nodes.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:cluster:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `meta:event`

An analytically relevant event.

| Interface |
|-----------|
| `base:event` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:desc` | `text` | A description of the event. |
| `:time` | `time` | The time that the event occurred. |
| `:title` | `title` | A title for the event. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:event:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:feed:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `meta:note`

An analyst note about nodes linked with -(about)> edges.

| Interface |
|-----------|
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:created` | `time` | The time the note was created. |
| `:creator` | `entity:actor` | The primary actor which created the note. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the note. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:note:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:name` | `base:name` | The rule name. |
| `:seen` | `ival` | The rule was observed during the time interval. |
| `:status` | `title` | The status of the rule. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:rule:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:name` | `base:name` | A name for the ruleset. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:source:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `meta:story`

A story document authored in markdown.

| Interface |
|-----------|
| `doc:authorable` |
| `doc:document` |
| `entity:creatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:body` | `text` | The text of the story. |
| `:created` | `time` | The time that the story was created. |
| `:creator` | `entity:actor` | The primary actor which created the story. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the story. |
| `:desc` | `text` | A description of the story. |
| `:file` | `file:bytes` | The file containing the story contents. |
| `:file:captured` | `time` | The time when the file content was captured. |
| `:file:name` | `file:base` | The name of the file containing the story contents. |
| `:id` | `base:id` | The story ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the story. |
| `:status` | `title` | The status of the story. |
| `:supersedes` | `array of meta:story` | An array of story versions which are superseded by this story. |
| `:title` | `title` | The title of the story. |
| `:type` | `meta:story:type:taxonomy` | The type of story. |
| `:updated` | `time` | The time that the story was last updated. |
| `:url` | `inet:url` | The URL where the story is available. |
| `:version` | `it:version` | The version of the story. |

### `meta:story:type:taxonomy`

A hierarchical taxonomy of story types.

| Interface |
|-----------|
| `meta:taxonomy` |

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:story:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:desc` | `text` | A description of the technique. |
| `:id` | `base:id`, `it:mitre:attack:technique:id` | A unique ID given to the technique. |
| `:ids` | `array of base:id, it:mitre:attack:technique:id` | An array of alternate IDs given to the technique. |
| `:name` | `base:name` | The primary name of the technique. |
| `:names` | `array of base:name` | A list of alternate names for the technique. |
| `:parent` | `meta:technique` | The parent technique for the technique. |
| `:reporter` | `entity:actor` | The entity which reported on the technique. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the technique. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the technique. |
| `:reporter:period` | `reported` | The period when the technique existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the technique. |
| `:reporter:supersedes` | `array of meta:technique` | An array of technique nodes which are superseded by this technique. |
| `:reporter:updated` | `time` | The time when the technique was last updated. |
| `:reporter:url` | `inet:url` | The URL for the technique provided by the reporter. |
| `:resolved` | `meta:technique` | The authoritative technique which this reporting is about. |
| `:seen` | `ival` | The technique was observed during the time interval. |
| `:sophistication` | `meta:score` | The assessed sophistication of the technique. |
| `:tag` | `syn:tag` | The tag used to annotate nodes where the technique was employed. |
| `:type` | `meta:technique:type:taxonomy` | The taxonomy classification of the technique. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:technique:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `meta:timeline`

A curated timeline of analytically relevant events.

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the timeline. |
| `:title` | `title` | The title of the timeline. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:timeline:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:name` | `base:name` | The name of the asset. |
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
| `:status` | `title` | The current status of the asset. |
| `:type` | `ou:asset:type:taxonomy` | The asset type. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ou:asset:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `ou:candidate`

A candidate being considered for a role within an organization.

| Property | Type | Doc |
|----------|------|-----|
| `:agent` | `entity:contact` | The contact information of an agent who advocates for the candidate. |
| `:attachments` | `array of file:attachment` | An array of additional files submitted by the candidate. |
| `:contact` | `entity:contact` | The contact information of the candidate. |
| `:intro` | `text` | An introduction or cover letter text submitted by the candidate. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ou:candidate:method:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `ou:candidate:referral`

A candidate being referred by a contact.

| Property | Type | Doc |
|----------|------|-----|
| `:candidate` | `ou:candidate` | The candidate who was referred. |
| `:referrer` | `entity:contact` | The individual who referred the candidate to the opening. |
| `:submitted` | `time` | The time the referral was submitted. |
| `:text` | `text` | Text of any referrer provided context about the candidate. |

### `ou:conference`

A conference.

| Interface |
|-----------|
| `base:activity` |
| `econ:budgetable` |
| `entity:attendable` |
| `entity:participable` |
| `entity:supportable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |
| `ou:promotable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this conference. |
| `:budget` | `econ:budget` | The budget for the conference. |
| `:family` | `event:name` | The family name of the conference used to group recurring events. |
| `:name` | `event:name` | The name of the conference. |
| `:names` | `array of event:name` | An array of alternate names for the conference. |
| `:period` | `activity` | The period over which the conference occurred. |
| `:place` | `geo:place` | The place where the conference was located. |
| `:place:address` | `geo:address` | The postal address where the conference was located. |
| `:place:address:city` | `base:name` | The city where the conference was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the conference was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the conference was located. |
| `:place:country` | `pol:country` | The country where the conference was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the conference was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the conference was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the conference was located. |
| `:place:loc` | `loc` | The geopolitical location where the conference was located. |
| `:place:name` | `geo:name` | The name of the place where the conference was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the conference. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the conference. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the conference. |
| `:website` | `inet:url` | The website of the conference. |

### `ou:contest`

A competitive event resulting in a ranked set of participants.

| Interface |
|-----------|
| `base:activity` |
| `econ:budgetable` |
| `entity:attendable` |
| `entity:participable` |
| `entity:supportable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |
| `ou:promotable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this contest. |
| `:budget` | `econ:budget` | The budget for the contest. |
| `:name` | `event:name` | The name of the contest. |
| `:names` | `array of event:name` | An array of alternate names for the contest. |
| `:period` | `activity` | The period over which the contest occurred. |
| `:place` | `geo:place` | The place where the contest was located. |
| `:place:address` | `geo:address` | The postal address where the contest was located. |
| `:place:address:city` | `base:name` | The city where the contest was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the contest was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the contest was located. |
| `:place:country` | `pol:country` | The country where the contest was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the contest was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the contest was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the contest was located. |
| `:place:loc` | `loc` | The geopolitical location where the contest was located. |
| `:place:name` | `geo:name` | The name of the place where the contest was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the contest. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the contest. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the contest. |
| `:type` | `ou:contest:type:taxonomy` | The type of contest. |
| `:website` | `inet:url` | The website of the contest. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ou:contest:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ou:employment:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `ou:enacted`

An organization enacting a document.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `meta:causal` |
| `meta:task` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this adoption task. |
| `:assignee` | `entity:actor` | The actor who is assigned to complete the adoption task. |
| `:created` | `time` | The time the adoption task was created. |
| `:creator` | `entity:actor` | The actor who created the adoption task. |
| `:doc` | `doc:policy`, `doc:requirement`, `doc:standard` | The document enacted by the organization. |
| `:due` | `time` | The time the adoption task must be complete. |
| `:id` | `base:id` | The ID of the adoption task. |
| `:org` | `ou:org` | The organization which is enacting the document. |
| `:parent` | `meta:task` | The parent task which includes this adoption task. |
| `:period` | `ival` | The period when the adoption task was being worked on. |
| `:priority` | `meta:score` | The priority of the adoption task. |
| `:project` | `proj:project` | The project containing the adoption task. |
| `:scope` | `ou:org`, `ou:team` | The scope of responsibility for the assignee to enact the document. |
| `:status` | `title` | The status of the adoption task. |
| `:updated` | `time` | The time the adoption task was last updated. |

### `ou:event`

A generic organized event.

| Interface |
|-----------|
| `base:activity` |
| `econ:budgetable` |
| `entity:attendable` |
| `entity:participable` |
| `entity:supportable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |
| `ou:promotable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:budget` | `econ:budget` | The budget for the event. |
| `:name` | `event:name` | The name of the event. |
| `:names` | `array of event:name` | An array of alternate names for the event. |
| `:period` | `activity` | The period over which the event occurred. |
| `:place` | `geo:place` | The place where the event was located. |
| `:place:address` | `geo:address` | The postal address where the event was located. |
| `:place:address:city` | `base:name` | The city where the event was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the event was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the event was located. |
| `:place:country` | `pol:country` | The country where the event was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the event was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the event was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the event was located. |
| `:place:loc` | `loc` | The geopolitical location where the event was located. |
| `:place:name` | `geo:name` | The name of the place where the event was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the event. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the event. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the event. |
| `:type` | `ou:event:type:taxonomy` | The type of event. |
| `:website` | `inet:url` | The website of the event. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ou:event:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `ou:id`

An ID value issued by an organization.

| Interface |
|-----------|
| `entity:identifier` |
| `meta:observable` |

| Property | Type | Doc |
|----------|------|-----|
| `:expires` | `date` | The date the ID expires. |
| `:issued` | `date` | The date the ID was initially issued. |
| `:issuer` | `ou:org` | The organization which issued the ID. |
| `:issuer:name` | `entity:name` | The name of the issuer. |
| `:recipient` | `entity:actor` | The entity which was issued the ID. |
| `:seen` | `ival` | The ID was observed during the time interval. |
| `:status` | `title` | The most recently known status of the ID. |
| `:type` | `ou:id:type:taxonomy` | The type of ID issued. |
| `:updated` | `time` | The time when the ID was most recently updated. |
| `:value` | `base:id` | The ID value. |

### `ou:id:history`

Changes made to an ID over time.

| Property | Type | Doc |
|----------|------|-----|
| `:id` | `ou:id` | The current ID information. |
| `:status` | `title` | The status of the ID at the time. |
| `:updated` | `time` | The time the ID was updated. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ou:id:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `ou:isic`

An International Standard Industrial Classification of All Economic Activities (ISIC) code.

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ou:job:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `ou:meeting`

A meeting.

| Interface |
|-----------|
| `base:activity` |
| `entity:attendable` |
| `entity:participable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this meeting. |
| `:name` | `event:name` | The name of the meeting. |
| `:period` | `activity` | The period over which the meeting occurred. |
| `:place` | `geo:place` | The place where the meeting was located. |
| `:place:address` | `geo:address` | The postal address where the meeting was located. |
| `:place:address:city` | `base:name` | The city where the meeting was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the meeting was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the meeting was located. |
| `:place:country` | `pol:country` | The country where the meeting was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the meeting was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the meeting was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the meeting was located. |
| `:place:loc` | `loc` | The geopolitical location where the meeting was located. |
| `:place:name` | `geo:name` | The name of the place where the meeting was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the meeting. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the meeting. |

### `ou:naics`

North American Industry Classification System (NAICS) codes and prefixes.

### `ou:opening`

A job/work opening within an org.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:contact` | The contact details to inquire about the opening. |
| `:employment:type` | `ou:employment:type:taxonomy` | The type of employment. |
| `:job:type` | `ou:job:type:taxonomy` | The job type taxonomy. |
| `:org` | `ou:org` | The org which has the opening. |
| `:org:fqdn` | `inet:fqdn` | The FQDN of the organization as listed in the opening. |
| `:org:name` | `entity:name` | The name of the organization as listed in the opening. |
| `:pay:max` | `econ:price` | The maximum pay for the job. |
| `:pay:min` | `econ:price` | The minimum pay for the job. |
| `:pay:pertime` | `duration` | The duration over which the position pays. |
| `:period` | `ival` | The time period when the opening existed. |
| `:postings` | `array of inet:url` | URLs where the opening is listed. |
| `:remote` | `percent` | The percentage of the role which may be performed remotely. |
| `:title` | `entity:title` | The title of the opening. |

### `ou:org`

An organization, such as a company or military unit.

| Interface |
|-----------|
| `econ:budgetable` |
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
| `:budget` | `econ:budget` | The budget for the organization. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the organization. |
| `:desc` | `text` | A description of the organization. |
| `:dns:mx` | `array of inet:fqdn` | An array of MX domains used by email addresses issued by the org. |
| `:email` | `inet:email` | The primary email address for the organization. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the organization. |
| `:id` | `base:id` | A type or source specific ID for the organization. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:industries` | `array of ind:industry` | The industries associated with the org. |
| `:lang` | `lang:language` | The primary language of the organization. |
| `:langs` | `array of lang:language` | An array of alternate languages for the organization. |
| `:lifespan` | `entity:lifespan` | The lifespan of the organization. |
| `:logo` | `file:bytes` | An image file representing the logo for the organization. |
| `:motto` | `lang:phrase` | The motto used by the organization. |
| `:name` | `entity:name` | The primary entity name of the organization. |
| `:names` | `array of entity:name` | An array of alternate entity names for the organization. |
| `:orgchart` | `ou:position` | The root node for an orgchart made up ou:position nodes. |
| `:parent` | `ou:org` | The parent organization. |
| `:phone` | `tel:phone` | The primary phone number for the organization. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the organization. |
| `:photo` | `file:bytes` | The profile picture or avatar for this organization. |
| `:place` | `geo:place` | The place where the organization was located. |
| `:place:address` | `geo:address` | The postal address where the organization was located. |
| `:place:address:city` | `base:name` | The city where the organization was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the organization was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the organization was located. |
| `:place:country` | `pol:country` | The country where the organization was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the organization was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the organization was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the organization was located. |
| `:place:loc` | `loc` | The geopolitical location where the organization was located. |
| `:place:name` | `geo:name` | The name of the place where the organization was located. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the organization. |
| `:tag` | `syn:tag` | A base tag used to encode assessments made by the organization. |
| `:type` | `ou:org:type:taxonomy` | The type of organization. |
| `:username` | `entity:name` | The primary user name for the organization. |
| `:usernames` | `array of entity:name` | An array of alternate user names for the organization. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ou:org:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `entity:attendable` |
| `entity:participable` |
| `entity:supportable` |
| `geo:locatable` |
| `meta:causal` |
| `meta:recordable` |
| `ou:promotable` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this presentation. |
| `:attendee:url` | `inet:url` | The URL visited by live attendees of the presentation. |
| `:deck:file` | `file:bytes` | A file containing the presentation materials. |
| `:deck:url` | `inet:url` | The URL hosting a copy of the presentation materials. |
| `:name` | `event:name` | The name of the presentation. |
| `:names` | `array of event:name` | An array of alternate names for the presentation. |
| `:period` | `activity` | The period over which the presentation occurred. |
| `:place` | `geo:place` | The place where the presentation was located. |
| `:place:address` | `geo:address` | The postal address where the presentation was located. |
| `:place:address:city` | `base:name` | The city where the presentation was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the presentation was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the presentation was located. |
| `:place:country` | `pol:country` | The country where the presentation was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the presentation was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the presentation was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the presentation was located. |
| `:place:loc` | `loc` | The geopolitical location where the presentation was located. |
| `:place:name` | `geo:name` | The name of the place where the presentation was located. |
| `:recording:file` | `file:bytes` | A file containing a recording of the presentation. |
| `:recording:offset` | `duration` | The time offset of the activity within the recording. |
| `:recording:url` | `inet:url` | The URL hosting a recording of the presentation. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the presentation. |
| `:website` | `inet:url` | The website of the presentation. |

### `ou:sic`

A four digit Standard Industrial Classification (SIC) code.

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

A relationship in which one physical object contains another.

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `phys:contained:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:desc` | `text` | A description of the phase. |
| `:id` | `base:id`, `it:mitre:attack:tactic:id` | The phase ID. |
| `:ids` | `array of base:id, it:mitre:attack:tactic:id` | An array of alternate IDs for the phase. |
| `:index` | `int` | The index of this phase within the phases of the system. |
| `:supersedes` | `array of plan:phase` | An array of phase versions which are superseded by this phase. |
| `:system` | `plan:system` | The planning system which defines this phase. |
| `:title` | `title` | The title of the phase. |
| `:updated` | `time` | The time that the phase was last updated. |
| `:url` | `inet:url` | The URL where the phase is documented. |
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
| `:title` | `title` | The title of the procedure. |
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
| `:title` | `title` | The title of the step. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `plan:procedure:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:created` | `time` | The time that the planning system was created. |
| `:creator` | `entity:actor` | The primary actor which created the planning system. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the planning system. |
| `:desc` | `text` | A description of the planning system. |
| `:id` | `base:id` | The planning system ID. |
| `:ids` | `array of base:id` | An array of alternate IDs for the planning system. |
| `:name` | `base:name` | The name of the planning system. |
| `:supersedes` | `array of plan:system` | An array of planning system versions which are superseded by this planning system. |
| `:updated` | `time` | The time that the planning system was last updated. |
| `:url` | `inet:url` | The URL where the planning system is documented. |
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
| `:activity` | `base:activity` | A parent activity which includes this candidacy. |
| `:actor` | `entity:actor` | The actor who pursued the candidacy. |
| `:actor:name` | `entity:name` | The name of the actor who pursued the candidacy. |
| `:campaign` | `entity:campaign` | The official campaign to elect the candidate. |
| `:id` | `base:id` | A unique ID for the candidate issued by an election authority. |
| `:incumbent` | `bool` | Set to true if the candidate is an incumbent in this race. |
| `:party` | `ou:org` | The declared political party of the candidate. |
| `:period` | `activity` | The period over which the candidacy occurred. |
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
| `:activity` | `base:activity` | A parent activity which includes this election. |
| `:name` | `event:name` | The name of the election. |
| `:period` | `activity` | The period over which the election occurred. |
| `:time` | `time` | The date of the election. |

### `pol:immigration:status`

A node which tracks the immigration status of a contact.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:contact` | The contact information for the immigration status record. |
| `:country` | `pol:country` | The country that the contact is/has immigrated to. |
| `:period` | `ival` | The time period when the contact was granted the status. |
| `:state` | `title` | The state of the immigration status. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `pol:immigration:status:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:election` | `pol:election` | The election that the polling place is designated for. |
| `:place` | `geo:place` | The place where votes were cast. |
| `:place:name` | `geo:name` | The name of the polling place. |

### `pol:race`

An individual race for office.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this political race. |
| `:election` | `pol:election` | The election that includes the race. |
| `:office` | `pol:office` | The political office that the candidates in the race are running for. |
| `:period` | `activity` | The period over which the political race occurred. |
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
| `:activity` | `base:activity` | A parent activity which includes this term. |
| `:actor` | `entity:actor` | The actor who served the term. |
| `:actor:name` | `entity:name` | The name of the actor who served the term. |
| `:office` | `pol:office` | The office held for the term. |
| `:party` | `ou:org` | The political party of the person who held office during the term. |
| `:period` | `activity` | The period over which the term occurred. |
| `:race` | `pol:race` | The race that determined who held office during the term. |

### `pol:vitals`

A set of vital statistics about a country.

| Property | Type | Doc |
|----------|------|-----|
| `:area` | `geo:area` | The area of the country. |
| `:country` | `pol:country` | The country that the statistics are about. |
| `:currencies` | `array of econ:currency` | The national currencies. |
| `:econ:gdp` | `econ:price` | The gross domestic product of the country. |
| `:population` | `int` | The total number of people living in the country. |
| `:time` | `time` | The time that the vitals were measured. |

### `proj:project`

A project in a tasking system.

| Interface |
|-----------|
| `base:activity` |
| `econ:budgetable` |
| `entity:creatable` |
| `entity:participable` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this project. |
| `:assignee` | `entity:actor` | The actor who is assigned to manage the project. |
| `:budget` | `econ:budget` | The budget for the project. |
| `:creator` | `entity:actor` | The primary actor which created the project. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the project. |
| `:desc` | `text` | The project description. |
| `:name` | `base:name` | The project name. |
| `:period` | `activity` | The period over which the project occurred. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `proj:project:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `proj:sprint`

A timeboxed period to complete a set amount of work.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:created` | `time` | The date the sprint was created. |
| `:creator` | `entity:actor` | The actor who created the sprint. |
| `:desc` | `text` | A description of the sprint. |
| `:name` | `base:name` | The name of the sprint. |
| `:period` | `activity` | The interval for the sprint. |
| `:project` | `proj:project` | The project containing the sprint. |
| `:status` | `title` | The sprint status. |

### `proj:ticket`

A ticket in a project management system.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `meta:causal` |
| `meta:task` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this ticket. |
| `:assignee` | `entity:actor` | The actor who is assigned to complete the ticket. |
| `:created` | `time` | The time the ticket was created. |
| `:creator` | `entity:actor` | The actor who created the ticket. |
| `:desc` | `text` | A description of the task. |
| `:due` | `time` | The time the ticket must be complete. |
| `:id` | `base:id` | The ID of the ticket. |
| `:name` | `base:name` | The name of the task. |
| `:parent` | `meta:task` | The parent task which includes this ticket. |
| `:period` | `ival` | The period when the ticket was being worked on. |
| `:points` | `int` | Optional SCRUM style story points value. |
| `:priority` | `meta:score` | The priority of the ticket. |
| `:project` | `proj:project` | The project containing the ticket. |
| `:status` | `title` | The status of the ticket. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `proj:ticket:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `ps:person`

A person or persona.

| Interface |
|-----------|
| `entity:actor` |
| `entity:contactable` |
| `entity:singular` |
| `geo:locatable` |
| `risk:targetable` |

| Property | Type | Doc |
|----------|------|-----|
| `:banner` | `file:bytes` | A banner or hero image used on the profile page. |
| `:bio` | `text` | A tagline or bio provided for the person. |
| `:birth:place` | `geo:place` | The place where the person was born. |
| `:birth:place:address` | `geo:address` | The postal address where the person was born. |
| `:birth:place:address:city` | `base:name` | The city where the person was born. |
| `:birth:place:altitude` | `geo:altitude` | The altitude where the person was born. |
| `:birth:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the person was born. |
| `:birth:place:country` | `pol:country` | The country where the person was born. |
| `:birth:place:country:code` | `iso:3166:alpha2` | The country code where the person was born. |
| `:birth:place:latlong` | `geo:latlong` | The latlong where the person was born. |
| `:birth:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the person was born. |
| `:birth:place:loc` | `loc` | The geopolitical location where the person was born. |
| `:birth:place:name` | `geo:name` | The name of the place where the person was born. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the person. |
| `:death:place` | `geo:place` | The place where the person died. |
| `:death:place:address` | `geo:address` | The postal address where the person died. |
| `:death:place:address:city` | `base:name` | The city where the person died. |
| `:death:place:altitude` | `geo:altitude` | The altitude where the person died. |
| `:death:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the person died. |
| `:death:place:country` | `pol:country` | The country where the person died. |
| `:death:place:country:code` | `iso:3166:alpha2` | The country code where the person died. |
| `:death:place:latlong` | `geo:latlong` | The latlong where the person died. |
| `:death:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the person died. |
| `:death:place:loc` | `loc` | The geopolitical location where the person died. |
| `:death:place:name` | `geo:name` | The name of the place where the person died. |
| `:desc` | `text` | A description of the person. |
| `:email` | `inet:email` | The primary email address for the person. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the person. |
| `:id` | `base:id` | A type or source specific ID for the person. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:lang` | `lang:language` | The primary language of the person. |
| `:langs` | `array of lang:language` | An array of alternate languages for the person. |
| `:lifespan` | `entity:lifespan` | The lifespan of the person. |
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
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the person was located. |
| `:place:country` | `pol:country` | The country where the person was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the person was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the person was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the person was located. |
| `:place:loc` | `loc` | The geopolitical location where the person was located. |
| `:place:name` | `geo:name` | The name of the place where the person was located. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the person. |
| `:title` | `entity:title` | The entity title or role for this person. |
| `:titles` | `array of entity:title` | An array of alternate entity titles or roles for this person. |
| `:username` | `entity:name` | The primary user name for the person. |
| `:usernames` | `array of entity:name` | An array of alternate user names for the person. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `ps:skill:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:phys:height` | `phys:distance` | The physical height of the person. |
| `:phys:length` | `phys:distance` | The physical length of the person. |
| `:phys:mass` | `phys:mass` | The physical mass of the person. |
| `:phys:volume` | `phys:volume` | The physical volume of the person. |
| `:phys:width` | `phys:distance` | The physical width of the person. |
| `:place` | `geo:place` | The place where the person was located. |
| `:place:address` | `geo:address` | The postal address where the person was located. |
| `:place:address:city` | `base:name` | The city where the person was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the person was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the person was located. |
| `:place:country` | `pol:country` | The country where the person was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the person was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the person was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the person was located. |
| `:place:loc` | `loc` | The geopolitical location where the person was located. |
| `:place:name` | `geo:name` | The name of the place where the person was located. |
| `:time` | `time` | The time the vitals were gathered or computed. |

### `ps:workhist`

An entry in a contact's work history.

| Property | Type | Doc |
|----------|------|-----|
| `:contact` | `entity:individual` | The contact which has the work history. |
| `:desc` | `text` | A description of the work done as part of the job. |
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
| `base:activity` |
| `entity:participable` |
| `meta:causal` |
| `meta:task` |

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `inet:service:account`, `it:host:account` | The account which generated the alert. |
| `:activity` | `base:activity` | A parent activity which includes this alert. |
| `:assignee` | `entity:actor` | The actor who is assigned to complete the alert. |
| `:benign` | `bool` | Set to true if the alert has been confirmed benign. Set to false if malicious. |
| `:created` | `time` | The time the alert was created. |
| `:creator` | `entity:actor` | The actor who created the alert. |
| `:desc` | `text` | A free-form description / overview of the alert. |
| `:due` | `time` | The time the alert must be complete. |
| `:engine` | `it:software` | The software that generated the alert. |
| `:host` | `it:host` | The host which generated the alert. |
| `:id` | `base:id` | The ID of the alert. |
| `:name` | `base:name` | A brief name for the alert. |
| `:parent` | `meta:task` | The parent task which includes this alert. |
| `:period` | `ival` | The period when the alert was being worked on. |
| `:platform` | `inet:service:platform` | The service platform which generated the alert. |
| `:priority` | `meta:score` | The priority of the alert. |
| `:project` | `proj:project` | The project containing the alert. |
| `:severity` | `meta:score` | A severity rank for the alert. |
| `:status` | `title` | The status of the alert. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:alert:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:alert:verdict:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `risk:attack`

An instance of an actor attacking a target.

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
| `:activity` | `base:activity` | A parent activity which includes this attack. |
| `:actor` | `entity:actor` | The actor who carried out the attack. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the attack. |
| `:compromise` | `risk:compromise` | A compromise that this attack contributed to. |
| `:desc` | `text` | A description of the attack. |
| `:detected` | `time` | The first confirmed detection time of the attack. |
| `:discovered` | `time` | The earliest known time when the attack was discovered. |
| `:discoverer` | `entity:actor` | The earliest known actor which discovered the attack. |
| `:id` | `base:id` | A unique ID given to the attack. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the attack. |
| `:name` | `base:name` | The primary name of the attack. |
| `:names` | `array of base:name` | A list of alternate names for the attack. |
| `:period` | `activity` | The period over which the attack occurred. |
| `:previous` | `risk:attack` | The previous/parent attack in a list or hierarchy. |
| `:reporter` | `entity:actor` | The entity which reported on the attack. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the attack. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the attack. |
| `:reporter:period` | `reported` | The period when the attack existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the attack. |
| `:reporter:supersedes` | `array of risk:attack` | An array of attack nodes which are superseded by this attack. |
| `:reporter:updated` | `time` | The time when the attack was last updated. |
| `:reporter:url` | `inet:url` | The URL for the attack provided by the reporter. |
| `:resolved` | `risk:attack` | The authoritative attack which this reporting is about. |
| `:severity` | `meta:score` | A severity rank for the attack. |
| `:sophistication` | `meta:score` | The assessed sophistication of the attack. |
| `:success` | `bool` | Set if the attack was known to have succeeded or not. |
| `:type` | `risk:attack:type:taxonomy` | A type for the attack, as a taxonomy entry. |
| `:victim` | `entity:actor` | The victim of the attack. |
| `:victim:name` | `entity:name` | The name of the victim of the attack. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:attack:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:activity` | `base:activity` | A parent activity which includes this compromise. |
| `:actor` | `entity:actor` | The actor who carried out the compromise. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the compromise. |
| `:cost` | `econ:price` | The total cost of the compromise, response, and mitigation efforts. |
| `:desc` | `text` | A description of the compromise. |
| `:discovered` | `time` | The earliest known time when the compromise was discovered. |
| `:discoverer` | `entity:actor` | The earliest known actor which discovered the compromise. |
| `:id` | `base:id` | A unique ID given to the compromise. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the compromise. |
| `:name` | `base:name` | The primary name of the compromise. |
| `:names` | `array of base:name` | A list of alternate names for the compromise. |
| `:period` | `activity` | The period over which the compromise occurred. |
| `:reporter` | `entity:actor` | The entity which reported on the compromise. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the compromise. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the compromise. |
| `:reporter:period` | `reported` | The period when the compromise existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the compromise. |
| `:reporter:supersedes` | `array of risk:compromise` | An array of compromise nodes which are superseded by this compromise. |
| `:reporter:updated` | `time` | The time when the compromise was last updated. |
| `:reporter:url` | `inet:url` | The URL for the compromise provided by the reporter. |
| `:resolved` | `risk:compromise` | The authoritative compromise which this reporting is about. |
| `:severity` | `meta:score` | A severity rank for the compromise. |
| `:tag` | `syn:tag` | A tag used to associate nodes with the compromise. |
| `:type` | `risk:compromise:type:taxonomy` | A type for the compromise, as a taxonomy entry. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:compromise:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:activity` | `base:activity` | A parent activity which includes this extortion. |
| `:actor` | `entity:actor` | The actor who carried out the extortion. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the extortion. |
| `:compromise` | `risk:compromise` | The compromise which allowed the attacker to extort the target. |
| `:desc` | `text` | A description of the extortion. |
| `:enacted` | `bool` | Set to true if attacker carried out the threat. |
| `:id` | `base:id` | A unique ID given to the extortion. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the extortion. |
| `:name` | `base:name` | The primary name of the extortion. |
| `:names` | `array of base:name` | A list of alternate names for the extortion. |
| `:paid:price` | `econ:price` | The total price paid by the target of the extortion. |
| `:period` | `activity` | The period over which the extortion occurred. |
| `:public` | `bool` | Set to true if the attacker publicly announced the extortion. |
| `:public:url` | `inet:url` | The URL where the attacker publicly announced the extortion. |
| `:reporter` | `entity:actor` | The entity which reported on the extortion. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the extortion. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the extortion. |
| `:reporter:period` | `reported` | The period when the extortion existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the extortion. |
| `:reporter:supersedes` | `array of risk:extortion` | An array of extortion nodes which are superseded by this extortion. |
| `:reporter:updated` | `time` | The time when the extortion was last updated. |
| `:reporter:url` | `inet:url` | The URL for the extortion provided by the reporter. |
| `:resolved` | `risk:extortion` | The authoritative extortion which this reporting is about. |
| `:success` | `bool` | Set to true if the victim met the attacker's demands. |
| `:type` | `risk:extortion:type:taxonomy` | A type taxonomy for the extortion event. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:extortion:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:activity` | `base:activity` | A parent activity which includes this leak. |
| `:actor` | `entity:actor` | The actor who carried out the leak. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the leak. |
| `:desc` | `text` | A description of the leak. |
| `:id` | `base:id` | A unique ID given to the leak. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the leak. |
| `:name` | `base:name` | The primary name of the leak. |
| `:names` | `array of base:name` | A list of alternate names for the leak. |
| `:public` | `bool` | Set to true if the leaked information was made publicly available. |
| `:recipient` | `entity:actor` | The identity which received the leaked information. |
| `:reporter` | `entity:actor` | The entity which reported on the leak. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the leak. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the leak. |
| `:reporter:period` | `reported` | The period when the leak existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the leak. |
| `:reporter:supersedes` | `array of risk:leak` | An array of leak nodes which are superseded by this leak. |
| `:reporter:updated` | `time` | The time when the leak was last updated. |
| `:reporter:url` | `inet:url` | The URL for the leak provided by the reporter. |
| `:resolved` | `risk:leak` | The authoritative leak which this reporting is about. |
| `:size:bytes` | `size` | The total size of the leaked data in bytes. |
| `:size:count` | `size` | The number of files included in the leaked data. |
| `:size:percent` | `percent` | The total percent of the data leaked. |
| `:time` | `time` | The time that the leak occurred. |
| `:type` | `risk:leak:type:taxonomy` | A type taxonomy for the leak. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:leak:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `risk:loss:data`

An aggregate loss of data which is no longer available. This is not used to record data theft.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |
| `risk:loss` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this data loss. |
| `:period` | `activity` | The period over which the data loss occurred. |
| `:size` | `size` | The total size of the data which was lost. |

### `risk:loss:funds`

An aggregate loss of funds.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |
| `risk:loss` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this loss of funds. |
| `:period` | `activity` | The period over which the loss of funds occurred. |
| `:value` | `econ:price` | The total value of the funds which were lost. |

### `risk:loss:life`

An aggregate loss of life.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |
| `risk:loss` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this loss of life. |
| `:count` | `size` | The number of lives lost. |
| `:period` | `activity` | The period over which the loss of life occurred. |

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
| `:desc` | `text` | A description of the mitigation. |
| `:id` | `base:id`, `it:mitre:attack:mitigation:id` | A unique ID given to the mitigation. |
| `:ids` | `array of base:id, it:mitre:attack:mitigation:id` | An array of alternate IDs given to the mitigation. |
| `:name` | `base:name` | The primary name of the mitigation. |
| `:names` | `array of base:name` | A list of alternate names for the mitigation. |
| `:parent` | `meta:technique` | The parent technique for the technique. |
| `:reporter` | `entity:actor` | The entity which reported on the mitigation. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the mitigation. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the mitigation. |
| `:reporter:period` | `reported` | The period when the mitigation existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the mitigation. |
| `:reporter:supersedes` | `array of risk:mitigation` | An array of mitigation nodes which are superseded by this mitigation. |
| `:reporter:updated` | `time` | The time when the mitigation was last updated. |
| `:reporter:url` | `inet:url` | The URL for the mitigation provided by the reporter. |
| `:resolved` | `risk:mitigation` | The authoritative mitigation which this reporting is about. |
| `:seen` | `ival` | The mitigation was observed during the time interval. |
| `:sophistication` | `meta:score` | The assessed sophistication of the technique. |
| `:tag` | `syn:tag` | The tag used to annotate nodes where the technique was employed. |
| `:type` | `meta:technique:type:taxonomy` | The taxonomy classification of the technique. |

### `risk:outage`

An outage event which affected resource availability.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |
| `meta:reported` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this outage. |
| `:attack` | `risk:attack` | An attack which caused the outage. |
| `:cause` | `risk:outage:cause:taxonomy` | The outage cause type. |
| `:desc` | `text` | A description of the outage. |
| `:id` | `base:id` | A unique ID given to the outage. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the outage. |
| `:name` | `base:name` | The primary name of the outage. |
| `:names` | `array of base:name` | A list of alternate names for the outage. |
| `:period` | `activity` | The time period where the outage impacted availability. |
| `:provider` | `ou:org` | The organization which experienced the outage event. |
| `:provider:name` | `entity:name` | The name of the organization which experienced the outage event. |
| `:reporter` | `entity:actor` | The entity which reported on the outage. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the outage. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the outage. |
| `:reporter:period` | `reported` | The period when the outage existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the outage. |
| `:reporter:supersedes` | `array of risk:outage` | An array of outage nodes which are superseded by this outage. |
| `:reporter:updated` | `time` | The time when the outage was last updated. |
| `:reporter:url` | `inet:url` | The URL for the outage provided by the reporter. |
| `:resolved` | `risk:outage` | The authoritative outage which this reporting is about. |
| `:type` | `risk:outage:type:taxonomy` | The type of outage. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:outage:cause:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:outage:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:activity` | `base:activity` | A parent activity which includes this theft. |
| `:actor` | `entity:actor` | The actor who carried out the theft. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the theft. |
| `:desc` | `text` | A description of the theft. |
| `:id` | `base:id` | A unique ID given to the theft. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the theft. |
| `:name` | `base:name` | The primary name of the theft. |
| `:names` | `array of base:name` | A list of alternate names for the theft. |
| `:reporter` | `entity:actor` | The entity which reported on the theft. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the theft. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the theft. |
| `:reporter:period` | `reported` | The period when the theft existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the theft. |
| `:reporter:supersedes` | `array of risk:theft` | An array of theft nodes which are superseded by this theft. |
| `:reporter:updated` | `time` | The time when the theft was last updated. |
| `:reporter:url` | `inet:url` | The URL for the theft provided by the reporter. |
| `:resolved` | `risk:theft` | The authoritative theft which this reporting is about. |
| `:time` | `time` | The time that the theft occurred. |
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
| `:activity` | `meta:score` | The most recently assessed activity level of the threat cluster. |
| `:banner` | `file:bytes` | A banner or hero image used on the profile page. |
| `:bio` | `text` | A tagline or bio provided for the threat. |
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:crypto:currency:addresses` | `array of crypto:currency:address` | Crypto currency addresses listed for the threat. |
| `:desc` | `text` | A description of the threat. |
| `:discovered` | `time` | The earliest known time when the threat was discovered. |
| `:discoverer` | `entity:actor` | The earliest known actor which discovered the threat. |
| `:email` | `inet:email` | The primary email address for the threat. |
| `:emails` | `array of inet:email` | An array of alternate email addresses for the threat. |
| `:id` | `base:id`, `it:mitre:attack:group:id` | A unique ID given to the threat. |
| `:identifiers` | `array of entity:identifier` | Additional entity identifiers. |
| `:ids` | `array of base:id, it:mitre:attack:group:id` | An array of alternate IDs given to the threat. |
| `:lang` | `lang:language` | The primary language of the threat. |
| `:langs` | `array of lang:language` | An array of alternate languages for the threat. |
| `:lifespan` | `entity:lifespan` | The lifespan of the threat. |
| `:name` | `entity:name` | The primary name of the threat according to the source. |
| `:names` | `array of entity:name` | A list of alternate names for the threat according to the source. |
| `:phone` | `tel:phone` | The primary phone number for the threat. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the threat. |
| `:photo` | `file:bytes` | The profile picture or avatar for this threat. |
| `:place` | `geo:place` | The place where the threat was located. |
| `:place:address` | `geo:address` | The postal address where the threat was located. |
| `:place:address:city` | `base:name` | The city where the threat was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the threat was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the threat was located. |
| `:place:country` | `pol:country` | The country where the threat was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the threat was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the threat was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the threat was located. |
| `:place:loc` | `loc` | The geopolitical location where the threat was located. |
| `:place:name` | `geo:name` | The name of the place where the threat was located. |
| `:reporter` | `entity:actor` | The entity which reported on the threat. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the threat. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the threat. |
| `:reporter:period` | `reported` | The period when the threat existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the threat. |
| `:reporter:supersedes` | `array of risk:threat` | An array of threat nodes which are superseded by this threat. |
| `:reporter:updated` | `time` | The time when the threat was last updated. |
| `:reporter:url` | `inet:url` | The URL for the threat provided by the reporter. |
| `:resolved` | `ou:org`, `ps:person` | The resolved entity to which this threat belongs. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the threat. |
| `:sophistication` | `meta:score` | The sources's assessed sophistication of the threat cluster. |
| `:tag` | `syn:tag` | The tag used to annotate nodes that are associated with the threat cluster. |
| `:type` | `risk:threat:type:taxonomy` | A type for the threat, as a taxonomy entry. |
| `:username` | `entity:name` | The primary user name for the threat. |
| `:usernames` | `array of entity:name` | An array of alternate user names for the threat. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:threat:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:mitigated` | `time` | The earliest known time when a mitigation/fix became available for the vulnerability. |
| `:name` | `base:name` | The primary name of the vulnerability. |
| `:names` | `array of base:name` | A list of alternate names for the vulnerability. |
| `:priority` | `meta:score` | The priority of the vulnerability. |
| `:published` | `time` | The earliest known time the vulnerability was published. |
| `:reporter` | `entity:actor` | The entity which reported on the vulnerability. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the vulnerability. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the vulnerability. |
| `:reporter:period` | `reported` | The period when the vulnerability existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the vulnerability. |
| `:reporter:supersedes` | `array of risk:vuln` | An array of vulnerability nodes which are superseded by this vulnerability. |
| `:reporter:updated` | `time` | The time when the vulnerability was last updated. |
| `:reporter:url` | `inet:url` | The URL for the vulnerability provided by the reporter. |
| `:resolved` | `risk:vuln` | The authoritative vulnerability which this reporting is about. |
| `:seen` | `ival` | The vulnerability was observed during the time interval. |
| `:severity` | `meta:score` | The severity of the vulnerability. |
| `:tag` | `syn:tag` | A tag used to annotate the presence or use of the vulnerability. |
| `:type` | `risk:vuln:type:taxonomy` | A taxonomy type entry for the vulnerability. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `risk:vuln:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `risk:vulnerable`

Indicates that a node is susceptible to a vulnerability.

| Interface |
|-----------|
| `base:activity` |
| `entity:participable` |
| `meta:causal` |
| `meta:task` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this mitigation task. |
| `:assignee` | `entity:actor` | The actor who is assigned to complete the mitigation task. |
| `:created` | `time` | The time the mitigation task was created. |
| `:creator` | `entity:actor` | The actor who created the mitigation task. |
| `:due` | `time` | The time the mitigation task must be complete. |
| `:id` | `base:id` | The ID of the mitigation task. |
| `:mitigations` | `array of meta:technique` | The mitigations which were used to address the vulnerable node. |
| `:node` | `risk:exploitable` | The node which is vulnerable. |
| `:parent` | `meta:task` | The parent task which includes this mitigation task. |
| `:period` | `ival` | The time window where the node was vulnerable. |
| `:priority` | `meta:score` | The priority of the mitigation task. |
| `:project` | `proj:project` | The project containing the mitigation task. |
| `:status` | `title` | The status of the mitigation task. |
| `:to` | `risk:mitigatable` | The thing which the node is vulnerable to. |
| `:updated` | `time` | The time the mitigation task was last updated. |

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
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:desc` | `text` | A description of the experiment. |
| `:name` | `base:name` | The name of the experiment. |
| `:period` | `activity` | The time period when the experiment was run. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `sci:experiment:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `sci:hypothesis:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:activity` | `base:activity` | A parent activity which includes this event. |
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
| `:interfaces` | `array of syn:interface` | The fully resolved set of interfaces which this form implements. |
| `:parent` | `syn:form` | Form which this form extends. |
| `:runt` | `bool` | Specifies if the form is runtime only. |
| `:type` | `syn:type` | Synapse type for this form. |

### `syn:interface`

A Synapse interface which forms may implement to share common properties.

| Property | Type | Doc |
|----------|------|-----|
| `:doc` | `str` | The docstring for the interface. |
| `:interfaces` | `array of syn:interface` | The interfaces which this interface inherits from. |

### `syn:prop`

A Synapse property.

| Property | Type | Doc |
|----------|------|-----|
| `:array` | `bool` | If the property is an array of values. |
| `:base` | `str` | Base name of the property. |
| `:computed` | `bool` | Specifies if the property is dynamically computed from other property values. |
| `:doc` | `str` | Description of the property definition. |
| `:extmodel` | `bool` | Specifies if the property is an extended model property. |
| `:form` | `syn:form` | The form of the property. |
| `:relname` | `str` | Relative property name. |
| `:type` | `array of syn:type` | The synapse types allowed for this property. |
| `:typedocs` | `data` | A mapping of member type names to their documentation strings for this property. |
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
| `:title` | `title` | A display title for the tag. |
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
| `:parent` | `syn:type` | Type which this inherits from. |

### `syn:user`

A Synapse user.

| Interface |
|-----------|
| `entity:actor` |

### `tel:call`

A telephone call.

| Interface |
|-----------|
| `base:activity` |
| `lang:transcript` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:caller` | `entity:actor` | The entity which placed the call. |
| `:caller:phone` | `tel:phone` | The phone number the caller placed the call from. |
| `:connected` | `bool` | Specifies whether the call was successfully connected. |
| `:lang` | `lang:language` | The language of the transcript. |
| `:period` | `activity` | The time period when the call took place. |
| `:recipient` | `entity:actor` | The entity which received the call. |
| `:recipient:phone` | `tel:phone` | The phone number at which the recipient received the call. |
| `:text` | `text` | The text of the transcript. |

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
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the cell tower was located. |
| `:place:country` | `pol:country` | The country where the cell tower was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the cell tower was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the cell tower was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the cell tower was located. |
| `:place:loc` | `loc` | The geopolitical location where the cell tower was located. |
| `:place:name` | `geo:name` | The name of the place where the cell tower was located. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `tel:mob:cell:radio:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `entity:identifier` |
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
| `entity:identifier` |
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

### `tel:mob:tadig`

A Transferred Account Data Interchange Group number issued to a GSM carrier.

| Interface |
|-----------|
| `entity:identifier` |

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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `tel:phone:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `transport:air:craft`

An individual aircraft.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `entity:destroyable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |
| `transport:vehicle` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the aircraft. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the aircraft. |
| `:max:cargo:mass` | `phys:mass` | The maximum mass the aircraft can carry as cargo. |
| `:max:cargo:volume` | `phys:volume` | The maximum volume the aircraft can carry as cargo. |
| `:max:occupants` | `size` | The maximum number of occupants the aircraft can hold. |
| `:model` | `biz:model` | The model of the aircraft. |
| `:name` | `base:name` | The name of the aircraft. |
| `:operator` | `entity:actor` | The contact information of the operator of the aircraft. |
| `:period` | `phys:lifespan` | The period when the aircraft existed, from its creation until it was retired or destroyed. |
| `:phys:height` | `phys:distance` | The physical height of the aircraft. |
| `:phys:length` | `phys:distance` | The physical length of the aircraft. |
| `:phys:mass` | `phys:mass` | The physical mass of the aircraft. |
| `:phys:volume` | `phys:volume` | The physical volume of the aircraft. |
| `:phys:width` | `phys:distance` | The physical width of the aircraft. |
| `:place` | `geo:place` | The place where the aircraft was located. |
| `:place:address` | `geo:address` | The postal address where the aircraft was located. |
| `:place:address:city` | `base:name` | The city where the aircraft was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the aircraft was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the aircraft was located. |
| `:place:country` | `pol:country` | The country where the aircraft was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the aircraft was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the aircraft was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the aircraft was located. |
| `:place:loc` | `loc` | The geopolitical location where the aircraft was located. |
| `:place:name` | `geo:name` | The name of the place where the aircraft was located. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `transport:air:craft:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `transport:air:flight`

An individual instance of a flight.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |
| `meta:schedulable` |
| `meta:usable` |
| `transport:schedule` |
| `transport:trip` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this flight. |
| `:arrived:place` | `geo:place` | The actual arrival airport. |
| `:arrived:point` | `transport:point` | The actual arrival gate. |
| `:cargo:mass` | `phys:mass` | The cargo mass carried by the aircraft on this flight. |
| `:cargo:volume` | `phys:volume` | The cargo volume carried by the aircraft on this flight. |
| `:departed:place` | `geo:place` | The actual departure airport. |
| `:departed:point` | `transport:point` | The actual departure gate. |
| `:num` | `transport:air:flightnum` | The flight number of this flight. |
| `:occupants` | `size` | The number of occupants of the aircraft on this flight. |
| `:operator` | `entity:actor` | The contact information of the operator of the flight. |
| `:period` | `activity` | The period over which the flight occurred. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival airport. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival gate. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure airport. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure gate. |
| `:scheduled:period` | `ival` | The scheduled period over which the flight was expected to occur. |
| `:status` | `title` | The status of the flight. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `transport:air:tailnum:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

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
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the telemetry sample was located. |
| `:place:country` | `pol:country` | The country where the telemetry sample was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the telemetry sample was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the telemetry sample was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the telemetry sample was located. |
| `:place:loc` | `loc` | The geopolitical location where the telemetry sample was located. |
| `:place:name` | `geo:name` | The name of the place where the telemetry sample was located. |
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
| `base:activity` |
| `meta:causal` |
| `meta:schedulable` |
| `meta:usable` |
| `transport:schedule` |
| `transport:trip` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this drive. |
| `:arrived:place` | `geo:place` | The actual arrival place. |
| `:arrived:point` | `transport:point` | The actual arrival point. |
| `:cargo:mass` | `phys:mass` | The cargo mass carried by the vehicle on this drive. |
| `:cargo:volume` | `phys:volume` | The cargo volume carried by the vehicle on this drive. |
| `:departed:place` | `geo:place` | The actual departure place. |
| `:departed:point` | `transport:point` | The actual departure point. |
| `:occupants` | `size` | The number of occupants of the vehicle on this drive. |
| `:operator` | `entity:actor` | The contact information of the operator of the drive. |
| `:period` | `activity` | The period over which the drive occurred. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival place. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival point. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure place. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure point. |
| `:scheduled:period` | `ival` | The scheduled period over which the drive was expected to occur. |
| `:status` | `title` | The status of the drive. |
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
| `entity:destroyable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |
| `transport:vehicle` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the vehicle. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the vehicle. |
| `:desc` | `text` | A description of the vehicle. |
| `:max:cargo:mass` | `phys:mass` | The maximum mass the vehicle can carry as cargo. |
| `:max:cargo:volume` | `phys:volume` | The maximum volume the vehicle can carry as cargo. |
| `:max:occupants` | `size` | The maximum number of occupants the vehicle can hold. |
| `:model` | `biz:model` | The model of the vehicle. |
| `:name` | `base:name` | The name of the vehicle. |
| `:operator` | `entity:actor` | The contact information of the operator of the vehicle. |
| `:period` | `phys:lifespan` | The period when the vehicle existed, from its creation until it was retired or destroyed. |
| `:phys:height` | `phys:distance` | The physical height of the vehicle. |
| `:phys:length` | `phys:distance` | The physical length of the vehicle. |
| `:phys:mass` | `phys:mass` | The physical mass of the vehicle. |
| `:phys:volume` | `phys:volume` | The physical volume of the vehicle. |
| `:phys:width` | `phys:distance` | The physical width of the vehicle. |
| `:place` | `geo:place` | The place where the vehicle was located. |
| `:place:address` | `geo:address` | The postal address where the vehicle was located. |
| `:place:address:city` | `base:name` | The city where the vehicle was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the vehicle was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the vehicle was located. |
| `:place:country` | `pol:country` | The country where the vehicle was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the vehicle was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the vehicle was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the vehicle was located. |
| `:place:loc` | `loc` | The geopolitical location where the vehicle was located. |
| `:place:name` | `geo:name` | The name of the place where the vehicle was located. |
| `:registration` | `transport:land:registration` | The current vehicle registration information. |
| `:serial` | `base:id` | The serial number or VIN of the vehicle. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `transport:land:vehicle:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `transport:occupant`

An occupant of a vehicle on a trip.

| Interface |
|-----------|
| `base:activity` |
| `entity:action` |
| `entity:activity` |
| `meta:causal` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:actor` | `entity:actor` | The actor who carried out the action. |
| `:actor:name` | `entity:name` | The name of the actor who carried out the action. |
| `:boarded:place` | `geo:place` | The place where the occupant boarded the vehicle. |
| `:boarded:point` | `transport:point` | The boarding point such as an airport gate or train platform. |
| `:contact` | `entity:individual` | Contact information of the occupant. |
| `:disembarked:place` | `geo:place` | The place where the occupant disembarked the vehicle. |
| `:disembarked:point` | `transport:point` | The disembarkation point such as an airport gate or train platform. |
| `:period` | `activity` | The period when the occupant was aboard the vehicle. |
| `:role` | `transport:occupant:role:taxonomy` | The role of the occupant such as captain, crew, passenger. |
| `:seat` | `base:id` | The seat which the occupant sat in. Likely in a vehicle specific format. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `transport:occupant:role:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `transport:rail:car`

An individual train car.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `entity:destroyable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the train car. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the train car. |
| `:max:cargo:mass` | `phys:mass` | The maximum mass the train car can carry as cargo. |
| `:max:cargo:volume` | `phys:volume` | The maximum volume the train car can carry as cargo. |
| `:max:occupants` | `size` | The maximum number of occupants the train car can hold. |
| `:model` | `biz:model` | The model of the train car. |
| `:name` | `base:name` | The name of the train car. |
| `:period` | `phys:lifespan` | The period when the train car existed, from its creation until it was retired or destroyed. |
| `:phys:height` | `phys:distance` | The physical height of the train car. |
| `:phys:length` | `phys:distance` | The physical length of the train car. |
| `:phys:mass` | `phys:mass` | The physical mass of the train car. |
| `:phys:volume` | `phys:volume` | The physical volume of the train car. |
| `:phys:width` | `phys:distance` | The physical width of the train car. |
| `:place` | `geo:place` | The place where the train car was located. |
| `:place:address` | `geo:address` | The postal address where the train car was located. |
| `:place:address:city` | `base:name` | The city where the train car was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the train car was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the train car was located. |
| `:place:country` | `pol:country` | The country where the train car was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the train car was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the train car was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the train car was located. |
| `:place:loc` | `loc` | The geopolitical location where the train car was located. |
| `:place:name` | `geo:name` | The name of the place where the train car was located. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `transport:rail:car:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `transport:rail:consist`

A group of rail cars and locomotives connected together.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `entity:destroyable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |
| `transport:vehicle` |

| Property | Type | Doc |
|----------|------|-----|
| `:cars` | `array of transport:rail:car` | The rail cars, including locomotives, which compose the consist. |
| `:creator` | `entity:actor` | The primary actor which created the train. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the train. |
| `:max:cargo:mass` | `phys:mass` | The maximum mass the train can carry as cargo. |
| `:max:cargo:volume` | `phys:volume` | The maximum volume the train can carry as cargo. |
| `:max:occupants` | `size` | The maximum number of occupants the train can hold. |
| `:model` | `biz:model` | The model of the train. |
| `:name` | `base:name` | The name of the train. |
| `:operator` | `entity:actor` | The contact information of the operator of the train. |
| `:period` | `phys:lifespan` | The period when the train existed, from its creation until it was retired or destroyed. |
| `:phys:height` | `phys:distance` | The physical height of the train. |
| `:phys:length` | `phys:distance` | The physical length of the train. |
| `:phys:mass` | `phys:mass` | The physical mass of the train. |
| `:phys:volume` | `phys:volume` | The physical volume of the train. |
| `:phys:width` | `phys:distance` | The physical width of the train. |
| `:place` | `geo:place` | The place where the train was located. |
| `:place:address` | `geo:address` | The postal address where the train was located. |
| `:place:address:city` | `base:name` | The city where the train was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the train was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the train was located. |
| `:place:country` | `pol:country` | The country where the train was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the train was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the train was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the train was located. |
| `:place:loc` | `loc` | The geopolitical location where the train was located. |
| `:place:name` | `geo:name` | The name of the place where the train was located. |
| `:serial` | `base:id` | The manufacturer assigned serial number of the train. |

### `transport:rail:train`

An individual instance of a consist of train cars running a route.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |
| `meta:schedulable` |
| `meta:usable` |
| `transport:schedule` |
| `transport:trip` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this train trip. |
| `:arrived:place` | `geo:place` | The actual arrival station. |
| `:arrived:point` | `transport:point` | The actual arrival gate. |
| `:cargo:mass` | `phys:mass` | The cargo mass carried by the train on this train trip. |
| `:cargo:volume` | `phys:volume` | The cargo volume carried by the train on this train trip. |
| `:departed:place` | `geo:place` | The actual departure station. |
| `:departed:point` | `transport:point` | The actual departure gate. |
| `:id` | `base:id` | The ID assigned to the train. |
| `:occupants` | `size` | The number of occupants of the train on this train trip. |
| `:operator` | `entity:actor` | The contact information of the operator of the train trip. |
| `:period` | `activity` | The period over which the train trip occurred. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival station. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival gate. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure station. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure gate. |
| `:scheduled:period` | `ival` | The scheduled period over which the train trip was expected to occur. |
| `:status` | `title` | The status of the train trip. |
| `:vehicle` | `transport:vehicle` | The train which traveled the train trip. |

### `transport:sea:telem`

A telemetry sample from a vessel in transit.

| Interface |
|-----------|
| `geo:locatable` |

| Property | Type | Doc |
|----------|------|-----|
| `:airdraft` | `phys:distance` | The maximum height of the ship from the waterline. |
| `:course` | `transport:direction` | The direction, in degrees from true North, that the vessel is traveling. |
| `:destination` | `geo:place` | The fully resolved destination that the vessel has declared. |
| `:destination:eta` | `time` | The estimated time of arrival that the vessel has declared. |
| `:destination:name` | `geo:name` | The name of the destination that the vessel has declared. |
| `:draft` | `phys:distance` | The keel depth at the time. |
| `:heading` | `transport:direction` | The direction, in degrees from true North, that the bow of the vessel is pointed. |
| `:place` | `geo:place` | The place where the telemetry sample was located. |
| `:place:address` | `geo:address` | The postal address where the telemetry sample was located. |
| `:place:address:city` | `base:name` | The city where the telemetry sample was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the telemetry sample was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the telemetry sample was located. |
| `:place:country` | `pol:country` | The country where the telemetry sample was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the telemetry sample was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the telemetry sample was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the telemetry sample was located. |
| `:place:loc` | `loc` | The geopolitical location where the telemetry sample was located. |
| `:place:name` | `geo:name` | The name of the place where the telemetry sample was located. |
| `:speed` | `velocity` | The speed of the vessel at the time. |
| `:time` | `time` | The time the telemetry was sampled. |
| `:vessel` | `transport:sea:vessel` | The vessel being measured. |

### `transport:sea:vessel`

An individual sea vessel.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `entity:destroyable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |
| `transport:vehicle` |

| Property | Type | Doc |
|----------|------|-----|
| `:callsign` | `base:id` | The callsign of the vessel. |
| `:creator` | `entity:actor` | The primary actor which created the vessel. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the vessel. |
| `:imo` | `transport:sea:imo` | The International Maritime Organization number for the vessel. |
| `:max:cargo:mass` | `phys:mass` | The maximum mass the vessel can carry as cargo. |
| `:max:cargo:volume` | `phys:volume` | The maximum volume the vessel can carry as cargo. |
| `:max:occupants` | `size` | The maximum number of occupants the vessel can hold. |
| `:mmsi` | `transport:sea:mmsi` | The Maritime Mobile Service Identifier assigned to the vessel. |
| `:model` | `biz:model` | The model of the vessel. |
| `:name` | `base:name` | The name of the vessel. |
| `:operator` | `entity:actor` | The contact information of the operator. |
| `:period` | `phys:lifespan` | The period when the vessel existed, from its creation until it was retired or destroyed. |
| `:phys:height` | `phys:distance` | The physical height of the vessel. |
| `:phys:length` | `phys:distance` | The physical length of the vessel. |
| `:phys:mass` | `phys:mass` | The physical mass of the vessel. |
| `:phys:volume` | `phys:volume` | The physical volume of the vessel. |
| `:phys:width` | `phys:distance` | The physical width of the vessel. |
| `:place` | `geo:place` | The place where the vessel was located. |
| `:place:address` | `geo:address` | The postal address where the vessel was located. |
| `:place:address:city` | `base:name` | The city where the vessel was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the vessel was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the vessel was located. |
| `:place:country` | `pol:country` | The country where the vessel was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the vessel was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the vessel was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the vessel was located. |
| `:place:loc` | `loc` | The geopolitical location where the vessel was located. |
| `:place:name` | `geo:name` | The name of the place where the vessel was located. |
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
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `transport:sea:vessel:type:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

### `transport:shipping:container`

An individual shipping container.

| Interface |
|-----------|
| `biz:manufactured` |
| `entity:creatable` |
| `entity:destroyable` |
| `geo:locatable` |
| `meta:havable` |
| `phys:object` |
| `phys:tangible` |
| `transport:container` |

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `entity:actor` | The primary actor which created the shipping container. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the shipping container. |
| `:max:cargo:mass` | `phys:mass` | The maximum mass the shipping container can carry as cargo. |
| `:max:cargo:volume` | `phys:volume` | The maximum volume the shipping container can carry as cargo. |
| `:max:occupants` | `size` | The maximum number of occupants the shipping container can hold. |
| `:model` | `biz:model` | The model of the shipping container. |
| `:name` | `base:name` | The name of the shipping container. |
| `:period` | `phys:lifespan` | The period when the shipping container existed, from its creation until it was retired or destroyed. |
| `:phys:height` | `phys:distance` | The physical height of the shipping container. |
| `:phys:length` | `phys:distance` | The physical length of the shipping container. |
| `:phys:mass` | `phys:mass` | The physical mass of the shipping container. |
| `:phys:volume` | `phys:volume` | The physical volume of the shipping container. |
| `:phys:width` | `phys:distance` | The physical width of the shipping container. |
| `:place` | `geo:place` | The place where the shipping container was located. |
| `:place:address` | `geo:address` | The postal address where the shipping container was located. |
| `:place:address:city` | `base:name` | The city where the shipping container was located. |
| `:place:altitude` | `geo:altitude` | The altitude where the shipping container was located. |
| `:place:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the shipping container was located. |
| `:place:country` | `pol:country` | The country where the shipping container was located. |
| `:place:country:code` | `iso:3166:alpha2` | The country code where the shipping container was located. |
| `:place:latlong` | `geo:latlong` | The latlong where the shipping container was located. |
| `:place:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the shipping container was located. |
| `:place:loc` | `loc` | The geopolitical location where the shipping container was located. |
| `:place:name` | `geo:name` | The name of the place where the shipping container was located. |
| `:serial` | `base:id` | The manufacturer assigned serial number of the shipping container. |

### `transport:stop`

A stop made by a vehicle on a trip.

| Interface |
|-----------|
| `base:activity` |
| `meta:causal` |
| `meta:schedulable` |
| `transport:schedule` |

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this stop. |
| `:arrived:place` | `geo:place` | The actual arrival place. |
| `:arrived:point` | `transport:point` | The actual arrival point. |
| `:departed:place` | `geo:place` | The actual departure place. |
| `:departed:point` | `transport:point` | The actual departure point. |
| `:period` | `activity` | The period over which the stop occurred. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival place. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival point. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure place. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure point. |
| `:scheduled:period` | `ival` | The scheduled period over which the stop was expected to occur. |
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
| `biz:product` | `has` | `econ:lineitem` | The product is offered via the line item. |
| `biz:product` | `has` | `meta:havable` | The product includes the item. |
| `biz:rfp` | `has` | `doc:requirement` | The RFP lists the requirement. |
| `biz:rfp` | `ledto` | `biz:deal` | The RFP led to the deal being proposed. |
| `crypto:key:secret` | `decrypts` | `file:bytes` | The key is used to decrypt the file. |
| `doc:contract` | `has` | `doc:requirement` | The contract contains the requirement. |
| `econ:budget` | `had` | `econ:purchase` | The purchase was included as spent during the budget period. |
| `econ:purchase` | `had` | `econ:lineitem` | The purchase included the line item. |
| `econ:purchase` | `ledto` | `econ:payment` | The purchase led to the payment. |
| `econ:purchase` | `purchased` | `meta:havable` | The purchase was used to acquire the target node. |
| `econ:receipt` | `has` | `econ:lineitem` | The receipt included the line item. |
| `econ:statement` | `has` | `econ:payment` | The financial statement includes the payment. |
| `entity:action` | `targeted` | `risk:targetable` | The action represents the actor targeting based on the target node. |
| `entity:action` | `used` | `meta:usable` | The action was taken using the target node. |
| `entity:activity` | `supported` | `entity:goal` | The activity supported the goal. |
| `entity:actor` | `targeted` | `risk:targetable` | The actor targets based on the target node. |
| `entity:actor` | `used` | `meta:usable` | The actor used the target node. |
| `entity:believed` | `followed` | `belief:tenet` | The actor followed the tenet during the period. |
| `entity:campaign` | `ledto` | `econ:purchase` | The campaign led to the purchase. |
| `entity:contactlist` | `has` | `entity:contact` | The contact list contains the contact. |
| `entity:contributed` | `had` | `econ:lineitem` | The contribution includes the line item. |
| `entity:contributed` | `had` | `econ:payment` | The contribution includes the payment. |
| `entity:studied` | `included` | `edu:class` | The class was taken by the student as part of their studies. |
| `entity:studied` | `included` | `edu:learnable` | The target node was included by the actor as part of their studies. |
| `file:bytes` | `refs` | `it:dev:str` | The source file contains the target string. |
| `file:bytes` | `uses` | `meta:algorithm` | The file uses the algorithm. |
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
| `it:app:snort:rule` | `detects` | `risk:vuln` | The snort rule detects use of the vulnerability. |
| `it:app:yara:rule` | `detects` | `it:software` | The YARA rule detects the software. |
| `it:app:yara:rule` | `detects` | `it:softwarename` | The YARA rule detects the named software. |
| `it:app:yara:rule` | `detects` | `meta:technique` | The YARA rule detects the technique. |
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
| `it:software` | `uses` | `meta:algorithm` | The software uses the algorithm. |
| `it:software` | `uses` | `meta:technique` | The software uses the technique. |
| `it:software` | `uses` | `risk:vuln` | The software uses the vulnerability. |
| `meta:algorithm` | `generated` | `*` | The target node was generated by the algorithm. |
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
| `risk:extortion` | `ledto` | `econ:payment` | The extortion led to the payment. |
| `risk:extortion` | `leveraged` | `meta:observable` | The extortion event was based on attacker access to the target node. |
| `risk:leak` | `leaked` | `meta:observable` | The leak included the disclosure of the target node. |
| `risk:loss:data` | `had` | `file:attachment` | The loss of data included the file. |
| `risk:loss:funds` | `had` | `econ:payment` | The loss of funds included the payment. |
| `risk:loss:life` | `had` | `entity:singular` | The loss of life included the entity. |
| `risk:outage` | `impacted` | `*` | The outage event impacted the availability of the target node. |
| `risk:theft` | `stole` | `meta:observable` | The target node was stolen during the theft. |
| `risk:theft` | `stole` | `phys:object` | The target node was stolen during the theft. |
| `sci:evidence` | `has` | `*` | The evidence includes observations from the target nodes. |
| `sci:observation` | `has` | `*` | The observations are summarized from the target nodes. |

## Tag Properties

| Property | Type | Doc |
|----------|------|-----|
| `confidence` | `meta:score` | The analyst confidence that the tag assessment is accurate. |
| `tlp` | `it:sec:tlp` | The TLP designation used to communicate the information sharing boundaries for the tag. |

## Interfaces

### `auth:credential`

An interface implemented by authentication credential forms.

| Form |
|------|
| `auth:passwd` |
| `crypto:salthash` |

### `base:activity`

Properties common to activity which occurs over a period.

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this activity. |
| `:period` | `activity` | The period over which the activity occurred. |

| Form |
|------|
| `biz:deal` |
| `entity:conflict` |
| `inet:data:link` |
| `inet:flow` |
| `inet:wifi:link` |
| `pol:election` |
| `pol:race` |
| `proj:sprint` |
| `risk:outage` |
| `tel:call` |

### `base:event`

Properties common to an event.

| Property | Type | Doc |
|----------|------|-----|
| `:activity` | `base:activity` | A parent activity which includes this event. |
| `:time` | `time` | The time that the event occurred. |

| Form |
|------|
| `meta:event` |

### `base:matched`

Properties which are common to matches based on rules.

| Property | Type | Doc |
|----------|------|-----|
| `:rule` | `rule:type` | The rule which matched the target node. |
| `:rule:version` | `it:version` | The version of the rule which generated the match. |
| `:target` | `` | The target node which matched the rule. |

| Form |
|------|
| `it:app:snort:matched` |
| `it:app:yara:matched` |

### `biz:manufactured`

Properties common to items being manufactured.

| Property | Type | Doc |
|----------|------|-----|
| `:model` | `biz:model` | The model number or name of the item. |
| `:name` | `base:name` | The name of the item. |

| Form |
|------|
| `it:hardware` |
| `it:physical:host` |

### `crypto:hash`

An interface implemented by all cryptographic hashes.

| Form |
|------|
| `crypto:hash:md5` |
| `crypto:hash:sha1` |
| `crypto:hash:sha256` |
| `crypto:hash:sha384` |
| `crypto:hash:sha512` |
| `crypto:hash:ssdeep` |

### `crypto:hashable`

An interface implemented by types which are frequently hashed.

| Form |
|------|
| `auth:passwd` |

### `crypto:key`

An interface implemented by all cryptographic keys.

| Property | Type | Doc |
|----------|------|-----|
| `:algorithm` | `meta:algorithm` | The algorithm which uses the key material. |
| `:bits` | `size` | The number of bits of key material. |

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
| `:created` | `time` | The time that the document was created. |
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
| `:title` | `title` | The title of the document. |
| `:type` | `doc:document:type:taxonomy` | The type of document. |

| Form |
|------|
| `biz:rfp` |
| `doc:contract` |
| `doc:policy` |
| `doc:report` |
| `doc:resume` |
| `doc:standard` |
| `meta:story` |
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

### `econ:bank:routing:code`

An interface for forms which identify a bank or branch for routing purposes.

| Property | Type | Doc |
|----------|------|-----|
| `:bank` | `ou:org` | The bank or branch which the routing identifier refers to. |
| `:bank:name` | `entity:name` | The name of the bank or branch. |

| Form |
|------|
| `econ:bank:aba:rtn` |
| `econ:bank:routing:id` |
| `econ:bank:swift:bic` |

### `econ:budgetable`

An interface for forms which may have an associated budget.

| Property | Type | Doc |
|----------|------|-----|
| `:budget` | `econ:budget` | The budget for the item. |

| Form |
|------|
| `entity:campaign` |
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:org` |
| `proj:project` |

### `econ:pay:instrument`

An interface for forms which may act as a payment instrument.

| Property | Type | Doc |
|----------|------|-----|
| `:account` | `econ:account` | The account that contains the funds used by the instrument. |

| Form |
|------|
| `crypto:currency:address` |
| `econ:bank:account` |
| `econ:bank:check` |
| `econ:bank:iban` |
| `econ:pay:card` |
| `inet:service:account` |

### `edu:learnable`

An interface implemented by nodes which represent a skill which can be learned.

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

### `entity:activity`

Properties common to activity carried out by an actor.

| Form |
|------|
| `biz:listing` |
| `biz:service` |
| `doc:contract` |
| `econ:budget` |
| `entity:attended` |
| `entity:believed` |
| `entity:campaign` |
| `entity:created` |
| `entity:had` |
| `entity:motive` |
| `entity:owned` |
| `entity:participated` |
| `entity:proficiency` |
| `entity:said` |
| `entity:studied` |
| `entity:supported` |
| `inet:tunnel` |
| `it:cmd:session` |
| `it:installed` |
| `pol:candidate` |
| `pol:term` |
| `risk:attack` |
| `risk:compromise` |
| `risk:extortion` |
| `sci:experiment` |
| `transport:occupant` |

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

### `entity:attendable`

An interface implemented by activities which an actor may attend.

| Form |
|------|
| `edu:class` |
| `meta:activity` |
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:meeting` |
| `ou:preso` |

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
| `:lifespan` | `entity:lifespan` | The lifespan of the entity. |
| `:name` | `entity:name` | The primary entity name of the entity. |
| `:names` | `array of entity:name` | An array of alternate entity names for the entity. |
| `:phone` | `tel:phone` | The primary phone number for the entity. |
| `:phones` | `array of tel:phone` | An array of alternate telephone numbers for the entity. |
| `:photo` | `file:bytes` | The profile picture or avatar for this entity. |
| `:social:accounts` | `array of inet:service:account` | Social media or other online accounts listed for the entity. |
| `:username` | `entity:name` | The primary user name for the entity. |
| `:usernames` | `array of entity:name` | An array of alternate user names for the entity. |
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
| `:creator` | `entity:actor` | The primary actor which created the item. |
| `:creator:name` | `entity:name` | The name of the primary actor which created the item. |

| Form |
|------|
| `biz:product` |
| `meta:note` |
| `proj:project` |

### `entity:destroyable`

An interface implemented by forms which represent things which can be destroyed.

### `entity:event`

Properties common to events carried out by an actor.

| Form |
|------|
| `econ:payment` |
| `econ:purchase` |
| `entity:achieved` |
| `entity:contributed` |
| `entity:destroyed` |
| `entity:discovered` |
| `entity:registered` |
| `entity:signed` |
| `risk:leak` |
| `risk:theft` |
| `sci:observation` |

### `entity:identifier`

An interface which is implemented by entity identifier forms.

| Form |
|------|
| `econ:bank:aba:rtn` |
| `econ:bank:iban` |
| `econ:bank:routing:id` |
| `econ:bank:swift:bic` |
| `econ:pay:iin` |
| `gov:cn:icp` |
| `gov:cn:mucd` |
| `gov:us:cage` |
| `gov:us:ssn` |
| `it:adid` |
| `it:mitre:attack:group:id` |
| `ou:id` |
| `tel:mob:carrier` |
| `tel:mob:imid` |
| `tel:mob:imsi` |
| `tel:mob:tadig` |

### `entity:multiple`

Properties which apply to entities which may represent a group or organization.

| Form |
|------|
| `entity:contact` |
| `ou:org` |

### `entity:participable`

An interface implemented by activities which an actor may participate in.

| Form |
|------|
| `belief:system` |
| `belief:tenet` |
| `edu:class` |
| `entity:campaign` |
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:meeting` |
| `ou:preso` |
| `proj:project` |

### `entity:resolvable`

An abstract entity which can be resolved to an organization or person.

| Property | Type | Doc |
|----------|------|-----|
| `:resolved` | `ou:org`, `ps:person` | The resolved entity to which this entity belongs. |

| Form |
|------|
| `entity:contact` |
| `inet:service:account` |
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

### `file:entry`

Properties common to forms representing a file at a path.

| Property | Type | Doc |
|----------|------|-----|
| `:file` | `file:bytes` | The file associated with the file entry. |
| `:path` | `file:path` | The path of the file associated with the file entry. |

| Form |
|------|
| `file:archive:entry` |
| `file:attachment` |
| `file:exemplar:entry` |
| `file:mime:rar:entry` |
| `file:mime:zip:entry` |
| `file:stored:entry` |
| `file:subfile:entry` |
| `file:system:entry` |
| `it:dev:repo:diff` |
| `it:dev:repo:entry` |
| `it:exec:file:add` |
| `it:exec:file:del` |
| `it:exec:file:read` |
| `it:exec:file:write` |

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
| `:author:name` | `entity:name` | MIME specific author name extracted from metadata. |
| `:comment` | `text` | MIME specific comment field extracted from metadata. |
| `:created` | `time` | MIME specific creation timestamp extracted from metadata. |
| `:desc` | `text` | MIME specific description field extracted from metadata. |
| `:id` | `base:id` | MIME specific unique identifier extracted from metadata. |
| `:latlong` | `geo:latlong` | MIME specific lat/long information extracted from metadata. |
| `:text` | `text` | The text contained within the image. |

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
| `:application` | `it:software` | The creating application extracted from Microsoft Office metadata. |
| `:application:name` | `it:softwarename` | The creating application name extracted from Microsoft Office metadata. |
| `:author` | `entity:contact` | The author extracted from Microsoft Office metadata. |
| `:author:name` | `entity:name` | The author name extracted from Microsoft Office metadata. |
| `:created` | `time` | The create_time extracted from Microsoft Office metadata. |
| `:lastsaved` | `time` | The last_saved_time extracted from Microsoft Office metadata. |
| `:subject` | `text` | The subject extracted from Microsoft Office metadata. |
| `:title` | `text` | The title extracted from Microsoft Office metadata. |

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
| `:altitude:accuracy` | `phys:distance` | The accuracy of the altitude where the item was located. |
| `:country` | `pol:country` | The country where the item was located. |
| `:country:code` | `iso:3166:alpha2` | The country code where the item was located. |
| `:latlong` | `geo:latlong` | The latlong where the item was located. |
| `:latlong:accuracy` | `phys:distance` | The accuracy of the latlong where the item was located. |
| `:loc` | `loc` | The geopolitical location where the item was located. |
| `:name` | `geo:name` | The name of the place where the item was located. |

| Form |
|------|
| `econ:payment` |
| `econ:purchase` |
| `edu:class` |
| `geo:place` |
| `inet:ip` |
| `inet:wifi:ap` |
| `it:host:telem` |
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:meeting` |
| `ou:preso` |
| `tel:mob:cell` |
| `transport:air:telem` |
| `transport:sea:telem` |

### `inet:dns:record`

An interface for DNS records.

| Form |
|------|
| `inet:dns:a` |
| `inet:dns:aaaa` |
| `inet:dns:cname` |
| `inet:dns:mx` |
| `inet:dns:ns` |
| `inet:dns:rev` |
| `inet:dns:soa` |
| `inet:dns:txt` |

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

### `inet:proto:login`

Properties common to authentication login events.

| Property | Type | Doc |
|----------|------|-----|
| `:credential` | `auth:credential` | The credential presented during the login event. |
| `:session` | `inet:proto:session` | The protocol session established by the login event. |
| `:success` | `bool` | Set to true if the login event was successful. |

| Form |
|------|
| `inet:service:login` |
| `inet:wifi:login` |
| `it:host:login` |

### `inet:proto:request`

Properties common to network protocol requests.

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

### `inet:proto:response`

Properties common to network protocol responses.

| Property | Type | Doc |
|----------|------|-----|
| `:flow` | `inet:flow` | The network flow which contained the response. |

| Form |
|------|
| `inet:dns:response` |
| `inet:http:response` |

### `inet:proto:session`

Properties common to network protocol sessions.

| Property | Type | Doc |
|----------|------|-----|
| `:client` | `inet:client` | The socket address of the client which initiated the protocol session. |
| `:client:host` | `it:host` | The host which initiated the protocol session. |
| `:server` | `inet:server` | The socket address of the server which received the protocol session. |
| `:server:host` | `it:host` | The host which received the protocol session. |

| Form |
|------|
| `inet:http:session` |
| `inet:service:session` |
| `inet:wifi:session` |
| `it:host:session` |

### `inet:service:action`

Properties common to events within a service platform.

| Property | Type | Doc |
|----------|------|-----|
| `:actor` | `inet:service:account`, `inet:service:agent` | The service account or agent which performed the action. |
| `:client` | `inet:client` | The network address of the client which initiated the action. |
| `:client:host` | `it:host` | The client host which initiated the action. |
| `:client:software` | `it:software` | The client software used to initiate the action. |
| `:platform` | `inet:service:platform` | The platform where the action was initiated. |
| `:server` | `inet:server` | The network address of the server which handled the action. |
| `:server:host` | `it:host` | The server host which handled the action. |
| `:session` | `inet:service:session` | The session which initiated the action. |
| `:time` | `time` | The time that the actor initiated the action. |

| Form |
|------|
| `inet:search:query` |
| `inet:service:emote` |
| `inet:service:message` |

### `inet:service:action:authorized`

Properties common to service actions which may be allowed or denied.

| Property | Type | Doc |
|----------|------|-----|
| `:error` | `inet:service:error` | The error generated if the action was unsuccessful. |
| `:error:reason` | `str` | The platform specific friendly error reason if the action was unsuccessful. |
| `:rule` | `inet:service:rule` | The rule which allowed or denied the action. |
| `:success` | `bool` | Set to true if the action was successful. |

| Form |
|------|
| `inet:service:access` |
| `inet:service:login` |

### `inet:service:base`

Properties common to most forms within a service platform.

| Property | Type | Doc |
|----------|------|-----|
| `:id` | `base:id` | A platform specific ID which identifies the node. |
| `:platform` | `inet:service:platform` | The platform which defines the node. |

### `inet:service:commentable`

An interface common to service objects which can have comments made about them.

| Form |
|------|
| `it:dev:repo:diff` |
| `it:dev:repo:issue` |

### `inet:service:joinable`

An interface common to nodes which can have accounts as members.

| Form |
|------|
| `inet:service:channel` |
| `inet:service:role` |

### `inet:service:labelable`

An interface common to service objects which can have labels applied to them.

| Form |
|------|
| `it:dev:repo:issue` |

### `inet:service:object`

Properties common to objects within a service platform.

| Property | Type | Doc |
|----------|------|-----|
| `:creator` | `inet:service:account`, `inet:service:agent` | The service account or agent which created the object. |
| `:period` | `it:lifespan` | The period when the object existed. |
| `:remover` | `inet:service:account`, `inet:service:agent` | The service account or agent which removed or decommissioned the object. |
| `:status` | `title` | The status of the object. |
| `:url` | `inet:url` | The primary URL associated with the object. |

| Form |
|------|
| `inet:service:agent` |
| `inet:service:bucket` |
| `inet:service:bucket:item` |
| `inet:service:channel` |
| `inet:service:comment` |
| `inet:service:label` |
| `inet:service:labeled` |
| `inet:service:member` |
| `inet:service:permission` |
| `inet:service:relationship` |
| `inet:service:resource` |
| `inet:service:role` |
| `inet:service:rule` |
| `inet:service:session` |
| `inet:service:subscription` |
| `it:cloud:host` |
| `it:dev:repo` |
| `it:dev:repo:branch` |
| `it:dev:repo:commit` |
| `it:dev:repo:issue` |
| `it:software:image` |

### `inet:service:subscriber`

Properties common to the nodes which subscribe to services.

| Property | Type | Doc |
|----------|------|-----|
| `:creds` | `array of auth:credential` | An array of non-ephemeral credentials. |
| `:email` | `inet:email` | The email address of the subscriber. |
| `:name` | `entity:name` | The name of the subscriber. |
| `:profile` | `entity:contact` | Current detailed contact information for the subscriber. |
| `:username` | `entity:name` | The primary user name for the subscriber. |

| Form |
|------|
| `inet:service:account` |
| `inet:service:tenant` |

### `it:component`

Properties common to hardware components.

| Property | Type | Doc |
|----------|------|-----|
| `:hardware` | `it:hardware` | The hardware specification of the component. |
| `:parent` | `it:component` | The parent component which this component is part of. |
| `:period` | `phys:lifespan` | The period when the component existed, from its creation until it was retired or destroyed. |
| `:serial` | `base:id` | The serial number of the component. |

| Form |
|------|
| `it:cloud:host` |
| `it:host` |
| `it:nic` |
| `it:physical:host` |
| `it:sim:card` |
| `it:sim:slot` |
| `it:virtual:host` |
| `it:wifi:nic` |

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
| `it:exec:windows:service:add` |
| `it:exec:windows:service:del` |
| `it:host:telem` |
| `it:log:event` |

### `it:host:exec`

Properties common to runtime events and activity on a host.

| Property | Type | Doc |
|----------|------|-----|
| `:exe` | `file:bytes` | The executable file which caused the activity. |
| `:host` | `it:host` | The host on which the activity occurred. |
| `:sandbox:file` | `file:bytes` | The initial sample given to a sandbox environment to analyze. |

### `lang:transcript`

An interface which applies to forms containing speech.

| Property | Type | Doc |
|----------|------|-----|
| `:lang` | `lang:language` | The language of the transcript. |
| `:text` | `text` | The text of the transcript. |

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

| Property | Type | Doc |
|----------|------|-----|
| `:desc` | `text` | A description of the item. |
| `:name` | `base:name` | The name of the item. |

| Form |
|------|
| `belief:system` |
| `belief:tenet` |
| `sci:hypothesis` |

### `meta:causal`

Implemented by events and activities which can lead to effects.

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

| Form |
|------|
| `biz:product` |
| `inet:wifi:ap` |
| `it:network` |
| `ou:org` |
| `tel:mob:tac` |

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
| `crypto:hash:ssdeep` |
| `crypto:key:base` |
| `crypto:key:dsa` |
| `crypto:key:ecdsa` |
| `crypto:key:rsa` |
| `crypto:key:secret` |
| `crypto:salthash` |
| `crypto:x509:cert` |
| `econ:account` |
| `econ:bank:check` |
| `econ:pay:card` |
| `entity:campaign` |
| `entity:contact` |
| `file:archive:entry` |
| `file:attachment` |
| `file:base` |
| `file:bytes` |
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
| `inet:http:response:header` |
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
| `inet:whois:iprecord` |
| `inet:whois:record` |
| `inet:wifi:ap` |
| `inet:wifi:ssid` |
| `it:adid` |
| `it:app:snort:rule` |
| `it:app:yara:rule` |
| `it:dev:str` |
| `it:hardware` |
| `it:host:hosted:url` |
| `it:hostname` |
| `it:os:windows:registry:entry` |
| `it:os:windows:registry:key` |
| `it:softid` |
| `it:software` |
| `lang:hashtag` |
| `meta:algorithm` |
| `meta:rule` |
| `meta:technique` |
| `ou:id` |
| `risk:mitigation` |
| `risk:vuln` |
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
| `:desc` | `text` | A description of the item. |
| `:id` | `base:id` | A unique ID given to the item. |
| `:ids` | `array of base:id` | An array of alternate IDs given to the item. |
| `:name` | `base:name` | The primary name of the item. |
| `:names` | `array of base:name` | A list of alternate names for the item. |
| `:reporter` | `entity:actor` | The entity which reported on the item. |
| `:reporter:deprecated` | `time` | The time when the reporter retired the item. |
| `:reporter:name` | `entity:name` | The name of the entity which reported on the item. |
| `:reporter:period` | `reported` | The period when the item existed, according to the reporter. |
| `:reporter:published` | `time` | The time when the reporter published the item. |
| `:reporter:supersedes` | `array of meta:reported` | An array of item nodes which are superseded by this item. |
| `:reporter:updated` | `time` | The time when the item was last updated. |
| `:reporter:url` | `inet:url` | The URL for the item provided by the reporter. |
| `:resolved` | `meta:reported` | The authoritative item which this reporting is about. |

| Form |
|------|
| `entity:campaign` |
| `entity:goal` |
| `entity:relationship` |
| `ind:industry` |
| `it:software` |
| `meta:cluster` |
| `meta:technique` |
| `risk:attack` |
| `risk:compromise` |
| `risk:extortion` |
| `risk:leak` |
| `risk:mitigation` |
| `risk:outage` |
| `risk:theft` |
| `risk:threat` |
| `risk:vuln` |

### `meta:schedulable`

An interface implemented by activities which may be scheduled.

| Property | Type | Doc |
|----------|------|-----|
| `:scheduled:period` | `ival` | The scheduled period over which the activity was expected to occur. |

### `meta:task`

A common interface for tasks.

| Property | Type | Doc |
|----------|------|-----|
| `:assignee` | `entity:actor` | The actor who is assigned to complete the task. |
| `:created` | `time` | The time the task was created. |
| `:creator` | `entity:actor` | The actor who created the task. |
| `:due` | `time` | The time the task must be complete. |
| `:id` | `base:id` | The ID of the task. |
| `:parent` | `meta:task` | The parent task which includes this task. |
| `:period` | `ival` | The period when the task was being worked on. |
| `:priority` | `meta:score` | The priority of the task. |
| `:project` | `proj:project` | The project containing the task. |
| `:status` | `title` | The status of the task. |
| `:updated` | `time` | The time the task was last updated. |

| Form |
|------|
| `it:dev:repo:issue` |
| `ou:enacted` |
| `proj:ticket` |
| `risk:alert` |
| `risk:vulnerable` |

### `meta:taxonomy`

Properties common to taxonomies.

| Property | Type | Doc |
|----------|------|-----|
| `:base` | `taxon` | The base taxon. |
| `:depth` | `int` | The depth indexed from 0. |
| `:desc` | `text` | A definition of the taxonomy entry. |
| `:name` | `title` | A brief name for the definition. |
| `:parent` | `meta:taxonomy` | The taxonomy parent. |
| `:sort` | `int` | A display sort order for siblings. |

| Form |
|------|
| `belief:system:type:taxonomy` |
| `biz:deal:type:taxonomy` |
| `biz:product:type:taxonomy` |
| `biz:rfp:type:taxonomy` |
| `biz:service:type:taxonomy` |
| `doc:contract:type:taxonomy` |
| `doc:policy:type:taxonomy` |
| `doc:report:type:taxonomy` |
| `doc:resume:type:taxonomy` |
| `doc:standard:type:taxonomy` |
| `econ:account:type:taxonomy` |
| `econ:bank:routing:type:taxonomy` |
| `econ:security:type:taxonomy` |
| `edu:class:type:taxonomy` |
| `entity:campaign:type:taxonomy` |
| `entity:contact:type:taxonomy` |
| `entity:goal:type:taxonomy` |
| `entity:had:type:taxonomy` |
| `entity:relationship:type:taxonomy` |
| `geo:place:type:taxonomy` |
| `ind:industry:type:taxonomy` |
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
| `mat:spec:type:taxonomy` |
| `meta:aggregate:type:taxonomy` |
| `meta:algorithm:type:taxonomy` |
| `meta:cluster:type:taxonomy` |
| `meta:event:type:taxonomy` |
| `meta:feed:type:taxonomy` |
| `meta:note:type:taxonomy` |
| `meta:rule:type:taxonomy` |
| `meta:source:type:taxonomy` |
| `meta:story:type:taxonomy` |
| `meta:technique:type:taxonomy` |
| `meta:timeline:type:taxonomy` |
| `ou:asset:type:taxonomy` |
| `ou:candidate:method:taxonomy` |
| `ou:contest:type:taxonomy` |
| `ou:employment:type:taxonomy` |
| `ou:event:type:taxonomy` |
| `ou:id:type:taxonomy` |
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
| `risk:compromise:type:taxonomy` |
| `risk:extortion:type:taxonomy` |
| `risk:leak:type:taxonomy` |
| `risk:outage:cause:taxonomy` |
| `risk:outage:type:taxonomy` |
| `risk:threat:type:taxonomy` |
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
| `file:attachment` |
| `file:base` |
| `file:bytes` |
| `inet:email` |
| `inet:email:message` |
| `inet:fqdn` |
| `inet:ip` |
| `inet:service:platform` |
| `inet:url` |
| `inet:urlfile` |
| `it:app:snort:rule` |
| `it:app:yara:rule` |
| `it:cmd` |
| `it:dev:str` |
| `it:hardware` |
| `it:software` |
| `meta:algorithm` |
| `meta:rule` |
| `meta:technique` |
| `risk:mitigation` |
| `risk:vuln` |

### `ou:promotable`

Properties which are common to activities which are promoted by an organization.

| Property | Type | Doc |
|----------|------|-----|
| `:name` | `event:name` | The name of the event. |
| `:names` | `array of event:name` | An array of alternate names for the event. |
| `:social:accounts` | `array of inet:service:account` | Social media accounts associated with the event. |
| `:website` | `inet:url` | The website of the event. |

| Form |
|------|
| `ou:conference` |
| `ou:contest` |
| `ou:event` |
| `ou:preso` |

### `phys:object`

Properties common to physical objects.

| Property | Type | Doc |
|----------|------|-----|
| `:period` | `phys:lifespan` | The period when the object existed, from its creation until it was retired or destroyed. |

| Form |
|------|
| `it:physical:host` |
| `mat:item` |

### `phys:tangible`

Properties common to nodes which have or capture physical characteristics.

| Property | Type | Doc |
|----------|------|-----|
| `:phys:height` | `phys:distance` | The physical height of the object. |
| `:phys:length` | `phys:distance` | The physical length of the object. |
| `:phys:mass` | `phys:mass` | The physical mass of the object. |
| `:phys:volume` | `phys:volume` | The physical volume of the object. |
| `:phys:width` | `phys:distance` | The physical width of the object. |

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
| `it:hardware` |
| `it:software` |
| `ou:asset` |

### `risk:loss`

An interface for aggregate losses which occur over a period.

| Form |
|------|
| `risk:loss:data` |
| `risk:loss:funds` |
| `risk:loss:life` |

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
| `entity:contact` |
| `entity:title` |
| `geo:place` |
| `ind:industry` |
| `inet:service:account` |
| `inet:service:platform` |
| `meta:topic` |
| `ou:org` |
| `pol:country` |
| `ps:person` |
| `risk:vuln` |

### `risk:victimized`

An interface for malicious acts which directly impact a victim.

| Property | Type | Doc |
|----------|------|-----|
| `:victim` | `entity:actor` | The victim of the event. |
| `:victim:name` | `entity:name` | The name of the victim of the event. |

| Form |
|------|
| `risk:attack` |
| `risk:compromise` |
| `risk:extortion` |
| `risk:leak` |
| `risk:theft` |

### `transport:container`

Properties common to a container used to transport cargo or people.

| Property | Type | Doc |
|----------|------|-----|
| `:max:cargo:mass` | `phys:mass` | The maximum mass the item can carry as cargo. |
| `:max:cargo:volume` | `phys:volume` | The maximum volume the item can carry as cargo. |
| `:max:occupants` | `size` | The maximum number of occupants the item can hold. |
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
| `:arrived:place` | `geo:place` | The actual arrival place. |
| `:arrived:point` | `transport:point` | The actual arrival point. |
| `:departed:place` | `geo:place` | The actual departure place. |
| `:departed:point` | `transport:point` | The actual departure point. |
| `:scheduled:arrival:place` | `geo:place` | The scheduled arrival place. |
| `:scheduled:arrival:point` | `transport:point` | The scheduled arrival point. |
| `:scheduled:departure:place` | `geo:place` | The scheduled departure place. |
| `:scheduled:departure:point` | `transport:point` | The scheduled departure point. |

| Form |
|------|
| `transport:stop` |

### `transport:trip`

Properties common to a specific trip taken by a vehicle.

| Property | Type | Doc |
|----------|------|-----|
| `:cargo:mass` | `phys:mass` | The cargo mass carried by the vehicle on this trip. |
| `:cargo:volume` | `phys:volume` | The cargo volume carried by the vehicle on this trip. |
| `:occupants` | `size` | The number of occupants of the vehicle on this trip. |
| `:operator` | `entity:actor` | The contact information of the operator of the trip. |
| `:status` | `title` | The status of the trip. |
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

