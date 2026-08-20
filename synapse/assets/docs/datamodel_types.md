
# Synapse Data Model - Types


<a id="dm-base-types"></a>

## Base Types

Base types are defined via Python classes.


<a id="dm-type-array"></a>

### array

A typed array which indexes each field.
It is implemented by the following class: `synapse.lib.types.Array`.

This type has the following virtual properties:

- `size`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`

The base type `array` has the following default options set:

- type: `int`
- uniq: `True`
- split: `None`
- sorted: `True`
- typeopts: `None`

<a id="dm-type-auth-passwd"></a>

### auth:passwd

A password string.
It is implemented by the following class: `synapse.models.auth.Passwd`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `auth:passwd` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `False`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-bool"></a>

### bool

The base boolean type.
It is implemented by the following class: `synapse.lib.types.Bool`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`

<a id="dm-type-comp"></a>

### comp

The base type for compound node fields.
It is implemented by the following class: `synapse.lib.types.Comp`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`

The base type `comp` has the following default options set:

- sepr: `None`
- fields: `()`

<a id="dm-type-data"></a>

### data

Arbitrary json compatible data.
It is implemented by the following class: `synapse.lib.types.Data`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`

The base type `data` has the following default options set:

- schema: `None`

<a id="dm-type-duration"></a>

### duration

A duration value.
It is implemented by the following class: `synapse.lib.types.Duration`.

This type supports lifting using the following operators:

- `=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `duration` has the following default options set:

- signed: `False`
- precision: `microsecond`

<a id="dm-type-econ-price"></a>

### econ:price

The amount of money expected, required, or given in payment for something.
It is implemented by the following class: `synapse.lib.types.Price`.

An example of `econ:price`:

- `2.20`

This type has the following virtual properties:

- `currency`
- `adjusted`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `econ:price` has the following default options set:

- units: `None`
- modulo: `None`
- defunit: `None`
- min: `None`
- minisvalid: `True`
- max: `None`
- maxisvalid: `True`

<a id="dm-type-econ-pricechange"></a>

### econ:pricechange

A directional change of a price over an interval.
It is implemented by the following class: `synapse.lib.types.PriceChange`.

This type has the following virtual properties:

- `currency`
- `start`
- `end`
- `delta`
- `rate`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `start=`
- `start<`
- `start>`
- `start<=`
- `start>=`
- `end=`
- `end<`
- `end>`
- `end<=`
- `end>=`
- `delta=`
- `delta<`
- `delta>`
- `delta<=`
- `delta>=`
- `rate=`
- `rate<`
- `rate>`
- `rate<=`
- `rate>=`

The base type `econ:pricechange` has the following default options set:

- names: `None`

<a id="dm-type-econ-pricerange"></a>

### econ:pricerange

An inclusive range of prices.
It is implemented by the following class: `synapse.lib.types.PriceRange`.

An example of `econ:pricerange`:

- `1.50-2.20`

This type has the following virtual properties:

- `currency`
- `min`
- `max`
- `delta`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `min=`
- `min<`
- `min>`
- `min<=`
- `min>=`
- `max=`
- `max<`
- `max>`
- `max<=`
- `max>=`
- `delta=`
- `delta<`
- `delta>`
- `delta<=`
- `delta>=`

<a id="dm-type-file-base"></a>

### file:base

A file name with no path.
It is implemented by the following class: `synapse.models.files.FileBase`.

An example of `file:base`:

- `woot.exe`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `file:base` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `False`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-file-path"></a>

### file:path

A normalized file path.
It is implemented by the following class: `synapse.models.files.FilePath`.

An example of `file:path`:

- `c:/windows/system32/calc.exe`

This type has the following virtual properties:

- `dir`
- `base`
- `ext`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `file:path` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `False`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-float"></a>

### float

The base floating point type.
It is implemented by the following class: `synapse.lib.types.Float`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `float` has the following default options set:

- fmt: `%f`
- min: `None`
- minisvalid: `True`
- max: `None`
- maxisvalid: `True`

<a id="dm-type-geo-area"></a>

### geo:area

A geographic area (base unit is square mm).
It is implemented by the following class: `synapse.models.geospace.Area`.

An example of `geo:area`:

- `10 sq.km`

This type supports lifting using the following operators:

- `=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `geo:area` has the following default options set:

- size: `8`
- signed: `True`
- enums: `None`
- enums:strict: `True`
- fmt: `%d`
- min: `None`
- max: `None`
- ismin: `False`
- ismax: `False`

<a id="dm-type-geo-latlong"></a>

### geo:latlong

A Lat/Long string specifying a point on Earth.
It is implemented by the following class: `synapse.models.geospace.LatLong`.

An example of `geo:latlong`:

- `-12.45,56.78`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `near=`

<a id="dm-type-guid"></a>

### guid

The base GUID type.
It is implemented by the following class: `synapse.lib.types.Guid`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

<a id="dm-type-hex"></a>

### hex

The base hex type.
It is implemented by the following class: `synapse.lib.types.Hex`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `hex` has the following default options set:

- size: `0`
- zeropad: `0`

<a id="dm-type-hugenum"></a>

### hugenum

A potentially huge/tiny number. [x] <= 730750818665451459101842 with a fractional precision of 24 decimal digits.
It is implemented by the following class: `synapse.lib.types.HugeNum`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `hugenum` has the following default options set:

- units: `None`
- modulo: `None`
- defunit: `None`
- min: `None`
- minisvalid: `True`
- max: `None`
- maxisvalid: `True`

<a id="dm-type-inet-email"></a>

### inet:email

An email address.
It is implemented by the following class: `synapse.models.inet.Email`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `inet:email` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-inet-fqdn"></a>

### inet:fqdn

A Fully Qualified Domain Name (FQDN).
It is implemented by the following class: `synapse.models.inet.Fqdn`.

An example of `inet:fqdn`:

- `vertex.link`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`

<a id="dm-type-inet-http-cookie"></a>

### inet:http:cookie

An individual HTTP cookie string.
It is implemented by the following class: `synapse.models.inet.HttpCookie`.

An example of `inet:http:cookie`:

- `PHPSESSID=el4ukv0kqbvoirg7nkp4dncpk3`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `inet:http:cookie` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-inet-ip"></a>

### inet:ip

An IPv4 or IPv6 address.
It is implemented by the following class: `synapse.models.inet.IPAddr`.

An example of `inet:ip`:

- `1.2.3.4`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `inet:ip` has the following default options set:

- version: `None`

<a id="dm-type-inet-net"></a>

### inet:net

An IPv4 or IPv6 address range.
It is implemented by the following class: `synapse.models.inet.IPRange`.

An example of `inet:net`:

- `1.2.3.4-1.2.3.8`

This type has the following virtual properties:

- `mask`
- `size`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`

The base type `inet:net` has the following default options set:

- cidr: `False`
- type: `('inet:ip', {})`

<a id="dm-type-inet-rfc2822-addr"></a>

### inet:rfc2822:addr

An RFC 2822 Address field.
It is implemented by the following class: `synapse.models.inet.Rfc2822Addr`.

An example of `inet:rfc2822:addr`:

- `"Visi Kenshoto" <visi@vertex.link>`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `inet:rfc2822:addr` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-inet-sockaddr"></a>

### inet:sockaddr

A network layer URL-like format to represent tcp/udp/icmp clients and servers.
It is implemented by the following class: `synapse.models.inet.SockAddr`.

An example of `inet:sockaddr`:

- `tcp://1.2.3.4:80`

This type has the following virtual properties:

- `ip`
- `port`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `inet:sockaddr` has the following default options set:

- defport: `None`
- defproto: `tcp`
- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-inet-url"></a>

### inet:url

A Universal Resource Locator (URL).
It is implemented by the following class: `synapse.models.inet.Url`.

An example of `inet:url`:

- `http://www.woot.com/files/index.html`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `inet:url` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-int"></a>

### int

The base 64 bit signed integer type.
It is implemented by the following class: `synapse.lib.types.Int`.

This type supports lifting using the following operators:

- `=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `int` has the following default options set:

- size: `8`
- signed: `True`
- enums: `None`
- enums:strict: `True`
- fmt: `%d`
- min: `None`
- max: `None`
- ismin: `False`
- ismax: `False`

<a id="dm-type-it-sec-cpe"></a>

### it:sec:cpe

A NIST CPE 2.3 Formatted String.
It is implemented by the following class: `synapse.models.infotech.Cpe23Str`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `it:sec:cpe` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `True`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-it-sec-cpe-v2_2"></a>

### it:sec:cpe:v2_2

A NIST CPE 2.2 Formatted String.
It is implemented by the following class: `synapse.models.infotech.Cpe22Str`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `it:sec:cpe:v2_2` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `True`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-it-sec-cvss-v2"></a>

### it:sec:cvss:v2

A CVSS v2 vector string.
It is implemented by the following class: `synapse.models.risk.CvssV2`.

An example of `it:sec:cvss:v2`:

- `(AV:L/AC:L/Au:M/C:P/I:C/A:N)`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `it:sec:cvss:v2` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-it-sec-cvss-v3"></a>

### it:sec:cvss:v3

A CVSS v3.x vector string.
It is implemented by the following class: `synapse.models.risk.CvssV3`.

An example of `it:sec:cvss:v3`:

- `AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `it:sec:cvss:v3` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-it-semver"></a>

### it:semver

Semantic Version type.
It is implemented by the following class: `synapse.models.infotech.SemVer`.

This type supports lifting using the following operators:

- `=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `it:semver` has the following default options set:

- size: `8`
- signed: `True`
- enums: `None`
- enums:strict: `True`
- fmt: `%d`
- min: `None`
- max: `None`
- ismin: `False`
- ismax: `False`

<a id="dm-type-it-version"></a>

### it:version

A version string.
It is implemented by the following class: `synapse.models.infotech.ItVersion`.

This type has the following virtual properties:

- `semver`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `it:version` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-ival"></a>

### ival

A time window or interval.
It is implemented by the following class: `synapse.lib.types.Ival`.

This type has the following virtual properties:

- `min`
- `max`
- `duration`
- `precision`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `@=`
- `min@=`
- `max@=`
- `min=`
- `min<`
- `min>`
- `min<=`
- `min>=`
- `max=`
- `max<`
- `max>`
- `max<=`
- `max>=`
- `duration=`
- `duration<`
- `duration>`
- `duration<=`
- `duration>=`

The base type `ival` has the following default options set:

- precision: `microsecond`
- names: `None`

<a id="dm-type-lang-code"></a>

### lang:code

An IETF BCP-47 language tag.
It is implemented by the following class: `synapse.models.language.LangCode`.

An example of `lang:code`:

- `pt-BR`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `lang:code` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-loc"></a>

### loc

The base geopolitical location type.
It is implemented by the following class: `synapse.lib.types.Loc`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

<a id="dm-type-phys-distance"></a>

### phys:distance

A geographic distance (base unit is mm).
It is implemented by the following class: `synapse.models.geospace.Dist`.

An example of `phys:distance`:

- `10 km`

This type supports lifting using the following operators:

- `=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `phys:distance` has the following default options set:

- baseoff: `0`
- size: `8`
- signed: `True`
- enums: `None`
- enums:strict: `True`
- fmt: `%d`
- min: `None`
- max: `None`
- ismin: `False`
- ismax: `False`

<a id="dm-type-poly"></a>

### poly

A prop which can be of one or more types.
It is implemented by the following class: `synapse.lib.types.Poly`.

This type has the following virtual properties:

- `type`
- `value`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`

The base type `poly` has the following default options set:

- docs: `None`
- interfaces: `None`
- types: `None`

<a id="dm-type-range"></a>

### range

A base range type.
It is implemented by the following class: `synapse.lib.types.Range`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`

The base type `range` has the following default options set:

- type: `('int', {})`

<a id="dm-type-str"></a>

### str

The base string type.
It is implemented by the following class: `synapse.lib.types.Str`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `str` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-syn-role"></a>

### syn:role

A Synapse role.
It is implemented by the following class: `synapse.models.syn.SynRole`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

<a id="dm-type-syn-tag"></a>

### syn:tag

The base type for a synapse tag.
It is implemented by the following class: `synapse.lib.types.Tag`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `syn:tag` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-syn-tag-part"></a>

### syn:tag:part

A tag component string.
It is implemented by the following class: `synapse.lib.types.TagPart`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `syn:tag:part` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-syn-user"></a>

### syn:user

A Synapse user.
It is implemented by the following class: `synapse.models.syn.SynUser`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

<a id="dm-type-taxon"></a>

### taxon

A component of a hierarchical taxonomy.
It is implemented by the following class: `synapse.lib.types.Taxon`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `taxon` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-taxonomy"></a>

### taxonomy

A hierarchical taxonomy.
It is implemented by the following class: `synapse.lib.types.Taxonomy`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `taxonomy` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-tel-phone"></a>

### tel:phone

A phone number.
It is implemented by the following class: `synapse.models.telco.Phone`.

An example of `tel:phone`:

- `+15558675309`

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `tel:phone` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `True`

<a id="dm-type-text"></a>

### text

A multi-line, free form, case-preserving text string with case-insensitive comparison.
It is implemented by the following class: `synapse.lib.types.Text`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `text` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `False`
- upper: `False`
- replace: `()`
- mapping: `None`
- onespace: `False`
- globsuffix: `False`

<a id="dm-type-time"></a>

### time

A date/time value.
It is implemented by the following class: `synapse.lib.types.Time`.

This type has the following virtual properties:

- `precision`

This type supports lifting using the following operators:

- `=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`
- `@=`

The base type `time` has the following default options set:

- ismin: `False`
- ismax: `False`
- maxfill: `False`
- precision: `microsecond`

<a id="dm-type-timeprecision"></a>

### timeprecision

A time precision value.
It is implemented by the following class: `synapse.lib.types.TimePrecision`.

This type supports lifting using the following operators:

- `=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `timeprecision` has the following default options set:

- signed: `False`

<a id="dm-type-title"></a>

### title

A single line, free form, case-preserving title or name string with case-insensitive comparison.
It is implemented by the following class: `synapse.lib.types.Title`.

This type supports lifting using the following operators:

- `=`
- `~=`
- `?=`
- `in=`
- `range=`
- `^=`

The base type `title` has the following default options set:

- enums: `None`
- regex: `None`
- lower: `False`
- strip: `True`
- upper: `False`
- replace: `()`
- onespace: `True`
- globsuffix: `False`

<a id="dm-type-velocity"></a>

### velocity

A velocity with base units in mm/sec.
It is implemented by the following class: `synapse.lib.types.Velocity`.

This type supports lifting using the following operators:

- `=`
- `?=`
- `in=`
- `range=`
- `<`
- `>`
- `<=`
- `>=`

The base type `velocity` has the following default options set:

- relative: `False`

<a id="dm-types"></a>

## Types

Regular types are derived from BaseTypes.


<a id="dm-type-duration-seconds"></a>

### duration:seconds

A duration value with second resolution.
The `duration:seconds` type is derived from the base type: [`duration`](#dm-type-duration).

This type has the following options set:

- precision: `second`
- signed: `False`

<a id="dm-type-percent"></a>

### percent

A percentage value between 0 and 100.
The `percent` type is derived from the base type: [`hugenum`](#dm-type-hugenum).

An example of `percent`:

- `10.2%`

This type has the following options set:

- defunit: `%`
- max: `100`
- maxisvalid: `True`
- min: `0`
- minisvalid: `True`
- modulo: `None`
- units: `{'%': '1'}`

<a id="dm-type-ratio"></a>

### ratio

A ratio expressed as a percentage which may be negative or exceed 100.
The `ratio` type is derived from the base type: [`hugenum`](#dm-type-hugenum).

An example of `ratio`:

- `-10.2%`

This type has the following options set:

- defunit: `%`
- max: `None`
- maxisvalid: `True`
- min: `None`
- minisvalid: `True`
- modulo: `None`
- units: `{'%': '1'}`

<a id="dm-type-date"></a>

### date

A date precision time value.
The `date` type is derived from the base type: [`time`](#dm-type-time).

This type has the following options set:

- ismax: `False`
- ismin: `False`
- maxfill: `False`
- precision: `day`

<a id="dm-type-activity"></a>

### activity

A time interval with began and ended bounds.
The `activity` type is derived from the base type: [`ival`](#dm-type-ival).

This type has the following options set:

- names: `{'min': 'began', 'max': 'ended'}`
- precision: `microsecond`

<a id="dm-type-activity-day"></a>

### activity:day

A day precision time interval with began and ended bounds.
The `activity:day` type is derived from the base type: [`ival`](#dm-type-ival).

This type has the following options set:

- names: `{'min': 'began', 'max': 'ended'}`
- precision: `day`

<a id="dm-type-reported"></a>

### reported

A time interval with created and removed bounds.
The `reported` type is derived from the base type: [`ival`](#dm-type-ival).

This type has the following options set:

- names: `{'min': 'created', 'max': 'removed'}`
- precision: `microsecond`

<a id="dm-type-base-id"></a>

### base:id

A base type for ID strings.
The `base:id` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-base-name"></a>

### base:name

A base type for case insensitive, case preserving names.
The `base:name` type is derived from the base type: [`title`](#dm-type-title).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-event-name"></a>

### event:name

A name used to refer to a specific event or activity.
The `event:name` type is derived from the base type: [`base:name`](#dm-type-base-name).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-topic"></a>

### meta:topic

A topic string.
The `meta:topic` type is derived from the base type: [`base:name`](#dm-type-base-name).

This type implements the following interfaces:

- `('risk:targetable', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-feed"></a>

### meta:feed

A data feed provided by a specific source.
The `meta:feed` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-meta-feed-type-taxonomy"></a>

### meta:feed:type:taxonomy

A data feed type taxonomy.
The `meta:feed:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-source"></a>

### meta:source

A data source unique identifier.
The `meta:source` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-meta-note"></a>

### meta:note

An analyst note about nodes linked with -(about)> edges.
The `meta:note` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:creatable', {})`

<a id="dm-type-meta-note-type-taxonomy"></a>

### meta:note:type:taxonomy

A hierarchical taxonomy of note types.
The `meta:note:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-story-type-taxonomy"></a>

### meta:story:type:taxonomy

A hierarchical taxonomy of story types.
The `meta:story:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-story"></a>

### meta:story

A story document authored in markdown.
The `meta:story` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:document', {})`
- `('doc:published', {})`

<a id="dm-type-meta-source-type-taxonomy"></a>

### meta:source:type:taxonomy

A hierarchical taxonomy of source types.
The `meta:source:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-timeline"></a>

### meta:timeline

A curated timeline of analytically relevant events.
The `meta:timeline` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-meta-timeline-type-taxonomy"></a>

### meta:timeline:type:taxonomy

A hierarchical taxonomy of timeline types.
The `meta:timeline:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-event"></a>

### meta:event

An analytically relevant event.
The `meta:event` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:event', {})`

<a id="dm-type-meta-activity"></a>

### meta:activity

Analytically relevant activity.
The `meta:activity` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:attendable', {})`

<a id="dm-type-meta-event-type-taxonomy"></a>

### meta:event:type:taxonomy

A hierarchical taxonomy of event types.
The `meta:event:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-ruleset-type-taxonomy"></a>

### meta:ruleset:type:taxonomy

A taxonomy for meta:ruleset types.
The `meta:ruleset:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-ruleset"></a>

### meta:ruleset

A set of rules linked with -(has)> edges.
The `meta:ruleset` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:authorable', {})`

<a id="dm-type-meta-rule-type-taxonomy"></a>

### meta:rule:type:taxonomy

A hierarchical taxonomy of rule types.
The `meta:rule:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-rule"></a>

### meta:rule

A generic rule linked to matches with -(matches)> edges.
The `meta:rule` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('doc:authorable', {})`
- `('meta:observable', {})`

<a id="dm-type-meta-algorithm-type-taxonomy"></a>

### meta:algorithm:type:taxonomy

A hierarchical taxonomy of algorithm types.
The `meta:algorithm:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-algorithm"></a>

### meta:algorithm

A mathematical or cryptographic algorithm.
The `meta:algorithm` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`

<a id="dm-type-meta-score"></a>

### meta:score

A generic score enumeration.
The `meta:score` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 0 | none |
| 10 | lowest |
| 20 | low |
| 30 | medium |
| 40 | high |
| 50 | highest |

- enums:strict: `False`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-meta-aggregate-type-taxonomy"></a>

### meta:aggregate:type:taxonomy

A type of item being counted in aggregate.
The `meta:aggregate:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-aggregate"></a>

### meta:aggregate

A node which represents an aggregate count of a specific type.
The `meta:aggregate` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-meta-cluster-type-taxonomy"></a>

### meta:cluster:type:taxonomy

A type taxonomy for meta:cluster nodes.
The `meta:cluster:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-cluster"></a>

### meta:cluster

A cluster of analytically relevant nodes generated by a specific source.
The `meta:cluster` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:reported', {})`

<a id="dm-type-str-lower"></a>

### str:lower

A case insensitive string.
The `str:lower` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-str-upper"></a>

### str:upper

A case insensitive string normalized to upper case.
The `str:upper` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `True`

<a id="dm-type-size"></a>

### size

A non-negative size or count.
The `size` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `0`
- signed: `True`
- size: `8`

<a id="dm-type-int8"></a>

### int8

A signed 8-bit integer.
The `int8` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `1`

<a id="dm-type-int16"></a>

### int16

A signed 16-bit integer.
The `int16` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `2`

<a id="dm-type-int32"></a>

### int32

A signed 32-bit integer.
The `int32` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `4`

<a id="dm-type-int64"></a>

### int64

A signed 64-bit integer.
The `int64` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-uint8"></a>

### uint8

An unsigned 8-bit integer.
The `uint8` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `False`
- size: `1`

<a id="dm-type-uint16"></a>

### uint16

An unsigned 16-bit integer.
The `uint16` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `False`
- size: `2`

<a id="dm-type-uint32"></a>

### uint32

An unsigned 32-bit integer.
The `uint32` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `False`
- size: `4`

<a id="dm-type-uint64"></a>

### uint64

An unsigned 64-bit integer.
The `uint64` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `False`
- size: `8`

<a id="dm-type-meta-technique"></a>

### meta:technique

A specific technique used to achieve a goal.
The `meta:technique` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:reported', {})`
- `('meta:observable', {})`
- `('risk:mitigatable', {})`

<a id="dm-type-meta-technique-type-taxonomy"></a>

### meta:technique:type:taxonomy

A hierarchical taxonomy of technique types.
The `meta:technique:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-award-type-taxonomy"></a>

### meta:award:type:taxonomy

A hierarchical taxonomy of award types.
The `meta:award:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-meta-award"></a>

### meta:award

An award.
The `meta:award` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:achievable', {})`

<a id="dm-type-velocity-relative"></a>

### velocity:relative

A relative velocity value.
The `velocity:relative` type is derived from the base type: [`velocity`](#dm-type-velocity).

This type has the following options set:

- relative: `True`

<a id="dm-type-belief-system"></a>

### belief:system

A belief system such as an ideology, philosophy, or religion.
The `belief:system` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:believable', {})`
- `('entity:participable', {})`

<a id="dm-type-belief-system-type-taxonomy"></a>

### belief:system:type:taxonomy

A hierarchical taxonomy of belief system types.
The `belief:system:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-belief-tenet"></a>

### belief:tenet

A concrete tenet potentially shared by multiple belief systems.
The `belief:tenet` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:believable', {})`
- `('entity:participable', {})`

<a id="dm-type-biz-model"></a>

### biz:model

A model name or number for a product.
The `biz:model` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-biz-rfp-type-taxonomy"></a>

### biz:rfp:type:taxonomy

A hierarchical taxonomy of RFP types.
The `biz:rfp:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-biz-rfp"></a>

### biz:rfp

An RFP (Request for Proposal) soliciting proposals.
The `biz:rfp` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:document', {})`
- `('doc:published', {})`

<a id="dm-type-biz-deal"></a>

### biz:deal

A sales or procurement effort in pursuit of a purchase.
The `biz:deal` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:activity', {})`
- `('meta:negotiable', {})`

<a id="dm-type-biz-listing"></a>

### biz:listing

A product or service being listed for sale.
The `biz:listing` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-biz-product"></a>

### biz:product

A type of product which is available for purchase.
The `biz:product` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:havable', {})`
- `('entity:creatable', {})`

<a id="dm-type-biz-service"></a>

### biz:service

A service offered by an actor.
The `biz:service` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-biz-service-type-taxonomy"></a>

### biz:service:type:taxonomy

A hierarchical taxonomy of service types.
The `biz:service:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-biz-deal-type-taxonomy"></a>

### biz:deal:type:taxonomy

A hierarchical taxonomy of deal types.
The `biz:deal:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-biz-product-type-taxonomy"></a>

### biz:product:type:taxonomy

A hierarchical taxonomy of product types.
The `biz:product:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-crypto-currency-chain"></a>

### crypto:currency:chain

A crypto currency chain.
The `crypto:currency:chain` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-crypto-currency-transaction"></a>

### crypto:currency:transaction

An individual crypto currency transaction recorded on the blockchain.
The `crypto:currency:transaction` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-crypto-currency-block"></a>

### crypto:currency:block

An individual crypto currency block record on the blockchain.
The `crypto:currency:block` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('chain', 'crypto:currency:chain'), ('offset', 'int'))`
- sepr: `/`

<a id="dm-type-crypto-smart-contract"></a>

### crypto:smart:contract

A smart contract.
The `crypto:smart:contract` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-crypto-smart-effect-transfertoken"></a>

### crypto:smart:effect:transfertoken

A smart contract effect which transfers ownership of a non-fungible token.
The `crypto:smart:effect:transfertoken` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:smart:effect', {})`

<a id="dm-type-crypto-smart-effect-transfertokens"></a>

### crypto:smart:effect:transfertokens

A smart contract effect which transfers fungible tokens.
The `crypto:smart:effect:transfertokens` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:smart:effect', {})`

<a id="dm-type-crypto-smart-effect-edittokensupply"></a>

### crypto:smart:effect:edittokensupply

A smart contract effect which increases or decreases the supply of a fungible token.
The `crypto:smart:effect:edittokensupply` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:smart:effect', {})`

<a id="dm-type-crypto-smart-effect-minttoken"></a>

### crypto:smart:effect:minttoken

A smart contract effect which creates a new non-fungible token.
The `crypto:smart:effect:minttoken` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:smart:effect', {})`

<a id="dm-type-crypto-smart-effect-burntoken"></a>

### crypto:smart:effect:burntoken

A smart contract effect which destroys a non-fungible token.
The `crypto:smart:effect:burntoken` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:smart:effect', {})`

<a id="dm-type-crypto-smart-effect-proxytoken"></a>

### crypto:smart:effect:proxytoken

A smart contract effect which grants a non-owner address the ability to manipulate a specific non-fungible token.
The `crypto:smart:effect:proxytoken` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:smart:effect', {})`

<a id="dm-type-crypto-smart-effect-proxytokenall"></a>

### crypto:smart:effect:proxytokenall

A smart contract effect which grants a non-owner address the ability to manipulate all non-fungible tokens of the owner.
The `crypto:smart:effect:proxytokenall` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:smart:effect', {})`

<a id="dm-type-crypto-smart-effect-proxytokens"></a>

### crypto:smart:effect:proxytokens

A smart contract effect which grants a non-owner address the ability to manipulate fungible tokens.
The `crypto:smart:effect:proxytokens` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:smart:effect', {})`

<a id="dm-type-crypto-payment-input"></a>

### crypto:payment:input

A payment made into a transaction.
The `crypto:payment:input` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-crypto-payment-output"></a>

### crypto:payment:output

A payment received from a transaction.
The `crypto:payment:output` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-crypto-smart-token"></a>

### crypto:smart:token

A token managed by a smart contract.
The `crypto:smart:token` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('contract', 'crypto:smart:contract'), ('tokenid', 'hugenum'))`
- sepr: `None`

<a id="dm-type-crypto-currency-address"></a>

### crypto:currency:address

An individual crypto currency address.
The `crypto:currency:address` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('econ:pay:instrument', {})`
- `('meta:observable', {})`

This type has the following options set:

- fields: `(('chain', 'crypto:currency:chain'), ('iden', 'str'))`
- sepr: `/`

<a id="dm-type-crypto-currency-client"></a>

### crypto:currency:client

A fused node representing a crypto currency address used by an Internet client.
The `crypto:currency:client` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `crypto:currency:client`:

- `(1.2.3.4, (({"$as": "crypto:currency:chain", "symbol": "btc", "id": "bip122:000000000019d6689c085ae165831e93"}), 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2))`

This type has the following options set:

- fields: `(('inetaddr', 'inet:client'), ('coinaddr', 'crypto:currency:address'))`
- sepr: `None`

<a id="dm-type-crypto-hash-md5"></a>

### crypto:hash:md5

A hex encoded MD5 hash.
The `crypto:hash:md5` type is derived from the base type: [`hex`](#dm-type-hex).

This type implements the following interfaces:

- `('crypto:hash', {})`
- `('meta:usable', {})`
- `('meta:observable', {})`

An example of `crypto:hash:md5`:

- `d41d8cd98f00b204e9800998ecf8427e`

This type has the following options set:

- size: `32`
- zeropad: `0`

<a id="dm-type-crypto-hash-sha1"></a>

### crypto:hash:sha1

A hex encoded SHA1 hash.
The `crypto:hash:sha1` type is derived from the base type: [`hex`](#dm-type-hex).

This type implements the following interfaces:

- `('crypto:hash', {})`
- `('meta:usable', {})`
- `('meta:observable', {})`

An example of `crypto:hash:sha1`:

- `da39a3ee5e6b4b0d3255bfef95601890afd80709`

This type has the following options set:

- size: `40`
- zeropad: `0`

<a id="dm-type-crypto-hash-sha256"></a>

### crypto:hash:sha256

A hex encoded SHA256 hash.
The `crypto:hash:sha256` type is derived from the base type: [`hex`](#dm-type-hex).

This type implements the following interfaces:

- `('crypto:hash', {})`
- `('meta:usable', {})`
- `('meta:observable', {})`

An example of `crypto:hash:sha256`:

- `ad9f4fe922b61e674a09530831759843b1880381de686a43460a76864ca0340c`

This type has the following options set:

- size: `64`
- zeropad: `0`

<a id="dm-type-crypto-hash-sha384"></a>

### crypto:hash:sha384

A hex encoded SHA384 hash.
The `crypto:hash:sha384` type is derived from the base type: [`hex`](#dm-type-hex).

This type implements the following interfaces:

- `('crypto:hash', {})`
- `('meta:usable', {})`
- `('meta:observable', {})`

An example of `crypto:hash:sha384`:

- `d425f1394e418ce01ed1579069a8bfaa1da8f32cf823982113ccbef531fa36bda9987f389c5af05b5e28035242efab6c`

This type has the following options set:

- size: `96`
- zeropad: `0`

<a id="dm-type-crypto-hash-sha512"></a>

### crypto:hash:sha512

A hex encoded SHA512 hash.
The `crypto:hash:sha512` type is derived from the base type: [`hex`](#dm-type-hex).

This type implements the following interfaces:

- `('crypto:hash', {})`
- `('meta:usable', {})`
- `('meta:observable', {})`

An example of `crypto:hash:sha512`:

- `ca74fe2ff2d03b29339ad7d08ba21d192077fece1715291c7b43c20c9136cd132788239189f3441a87eb23ce2660aa243f334295902c904b5520f6e80ab91f11`

This type has the following options set:

- size: `128`
- zeropad: `0`

<a id="dm-type-crypto-hash-ssdeep"></a>

### crypto:hash:ssdeep

A fuzzy hash of a file in ssdeep format.
The `crypto:hash:ssdeep` type is derived from the base type: [`str`](#dm-type-str).

This type implements the following interfaces:

- `('crypto:hash', {})`
- `('meta:observable', {})`

An example of `crypto:hash:ssdeep`:

- `98304:PYZdVAWWlLuKn4messQdqSqkxbpYlXLL:iglLlsHSfxVYVL`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^([3-9]|[1-9]\d+):[A-Za-z0-9+/]{0,64}:[A-Za-z0-9+/]{0,64}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-crypto-salthash"></a>

### crypto:salthash

A salted hash computed for a value.
The `crypto:salthash` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('auth:credential', {})`
- `('meta:observable', {})`

<a id="dm-type-crypto-key-base"></a>

### crypto:key:base

A generic cryptographic key.
The `crypto:key:base` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:key', {})`
- `('meta:observable', {})`

<a id="dm-type-crypto-key-rsa"></a>

### crypto:key:rsa

An RSA public/private key pair.
The `crypto:key:rsa` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:key', {})`
- `('meta:observable', {})`

<a id="dm-type-crypto-key-rsa-prime"></a>

### crypto:key:rsa:prime

A prime value and exponent used to generate an RSA key.
The `crypto:key:rsa:prime` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-crypto-key-dsa"></a>

### crypto:key:dsa

A DSA public/private key pair.
The `crypto:key:dsa` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:key', {})`
- `('meta:observable', {})`

<a id="dm-type-crypto-key-ecdsa"></a>

### crypto:key:ecdsa

An ECDSA public/private key pair.
The `crypto:key:ecdsa` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:key', {})`
- `('meta:observable', {})`

<a id="dm-type-crypto-key-secret"></a>

### crypto:key:secret

A secret key with an optional initialiation vector.
The `crypto:key:secret` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('crypto:key', {})`
- `('meta:observable', {})`

<a id="dm-type-crypto-x509-cert"></a>

### crypto:x509:cert

A unique X.509 certificate.
The `crypto:x509:cert` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`

<a id="dm-type-crypto-x509-serial"></a>

### crypto:x509:serial

A certificate serial number as a big endian hex value.
The `crypto:x509:serial` type is derived from the base type: [`hex`](#dm-type-hex).

This type has the following options set:

- size: `0`
- zeropad: `40`

<a id="dm-type-crypto-x509-san"></a>

### crypto:x509:san

An X.509 Subject Alternative Name (SAN).
The `crypto:x509:san` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('type', 'str'), ('value', 'str'))`
- sepr: `None`

<a id="dm-type-crypto-x509-rdn"></a>

### crypto:x509:rdn

An X.509 Relative Distinguished Name (RDN) attribute and value pair.
The `crypto:x509:rdn` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('name', 'str:upper'), ('value', 'title'))`
- sepr: `=`

<a id="dm-type-crypto-x509-crl"></a>

### crypto:x509:crl

A unique X.509 Certificate Revocation List.
The `crypto:x509:crl` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-crypto-x509-revoked"></a>

### crypto:x509:revoked

A revocation relationship between a CRL and an X.509 certificate.
The `crypto:x509:revoked` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('crl', 'crypto:x509:crl'), ('cert', 'crypto:x509:cert'))`
- sepr: `None`

<a id="dm-type-crypto-x509-signedfile"></a>

### crypto:x509:signedfile

A digital signature relationship between an X.509 certificate and a file.
The `crypto:x509:signedfile` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('cert', 'crypto:x509:cert'), ('file', 'file:bytes'))`
- sepr: `None`

<a id="dm-type-crypto-x509-version"></a>

### crypto:x509:version

An X.509 certificate version.
The `crypto:x509:version` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 0 | v1 |
| 2 | v3 |

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-inet-dns-query-name"></a>

### inet:dns:query:name

A DNS query name.
The `inet:dns:query:name` type is derived from the base type: [`poly`](#dm-type-poly).

An example of `inet:dns:query:name`:

- `vertex.link`

This type has the following options set:

- docs: `None`
- interfaces: `None`
- types: `('inet:fqdn', 'it:dev:str')`

<a id="dm-type-inet-dns-a"></a>

### inet:dns:a

The result of a DNS A record lookup.
The `inet:dns:a` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('inet:dns:record', {})`

An example of `inet:dns:a`:

- `(vertex.link,1.2.3.4)`

This type has the following options set:

- fields: `(('fqdn', 'inet:fqdn'), ('ip', 'inet:ipv4'))`
- sepr: `None`

<a id="dm-type-inet-dns-aaaa"></a>

### inet:dns:aaaa

The result of a DNS AAAA record lookup.
The `inet:dns:aaaa` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('inet:dns:record', {})`

An example of `inet:dns:aaaa`:

- `(vertex.link,2607:f8b0:4004:809::200e)`

This type has the following options set:

- fields: `(('fqdn', 'inet:fqdn'), ('ip', 'inet:ipv6'))`
- sepr: `None`

<a id="dm-type-inet-dns-rev"></a>

### inet:dns:rev

The transformed result of a DNS PTR record lookup.
The `inet:dns:rev` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('inet:dns:record', {})`

An example of `inet:dns:rev`:

- `(1.2.3.4,vertex.link)`

This type has the following options set:

- fields: `(('ip', 'inet:ip'), ('fqdn', 'inet:fqdn'))`
- sepr: `None`

<a id="dm-type-inet-dns-ns"></a>

### inet:dns:ns

The result of a DNS NS record lookup.
The `inet:dns:ns` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('inet:dns:record', {})`

An example of `inet:dns:ns`:

- `(vertex.link,ns.dnshost.com)`

This type has the following options set:

- fields: `(('zone', 'inet:fqdn'), ('ns', 'inet:fqdn'))`
- sepr: `None`

<a id="dm-type-inet-dns-cname"></a>

### inet:dns:cname

The result of a DNS CNAME record lookup.
The `inet:dns:cname` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('inet:dns:record', {})`

An example of `inet:dns:cname`:

- `(foo.vertex.link,vertex.link)`

This type has the following options set:

- fields: `(('fqdn', 'inet:fqdn'), ('cname', 'inet:fqdn'))`
- sepr: `None`

<a id="dm-type-inet-dns-mx"></a>

### inet:dns:mx

The result of a DNS MX record lookup.
The `inet:dns:mx` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('inet:dns:record', {})`

An example of `inet:dns:mx`:

- `(vertex.link,mail.vertex.link)`

This type has the following options set:

- fields: `(('fqdn', 'inet:fqdn'), ('mx', 'inet:fqdn'))`
- sepr: `None`

<a id="dm-type-inet-dns-soa"></a>

### inet:dns:soa

The result of a DNS SOA record lookup.
The `inet:dns:soa` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('inet:dns:record', {})`

<a id="dm-type-inet-dns-txt"></a>

### inet:dns:txt

The result of a DNS TXT record lookup.
The `inet:dns:txt` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('inet:dns:record', {})`

An example of `inet:dns:txt`:

- `(hehe.vertex.link,"fancy TXT record")`

This type has the following options set:

- fields: `(('fqdn', 'inet:fqdn'), ('text', 'text'))`
- sepr: `None`

<a id="dm-type-inet-dns-query"></a>

### inet:dns:query

A DNS query unique to a given client.
The `inet:dns:query` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `inet:dns:query`:

- `(1.2.3.4, woot.com, 1)`

This type has the following options set:

- fields:

```json
[
  [
    "client",
    "inet:client"
  ],
  [
    "name",
    "inet:dns:query:name"
  ],
  [
    "type",
    "inet:dns:query:type"
  ]
]
```

- sepr: `None`

<a id="dm-type-inet-dns-request"></a>

### inet:dns:request

A DNS protocol request.
The `inet:dns:request` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:request', {})`

<a id="dm-type-inet-dns-response"></a>

### inet:dns:response

A DNS protocol response.
The `inet:dns:response` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:response', {})`

<a id="dm-type-inet-dns-answer"></a>

### inet:dns:answer

A single answer from within a DNS reply.
The `inet:dns:answer` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-inet-dns-mx-answer"></a>

### inet:dns:mx:answer

A single MX answer from within a DNS reply.
The `inet:dns:mx:answer` type is derived from the base type: [`inet:dns:answer`](#dm-type-inet-dns-answer).

<a id="dm-type-inet-dns-wild-a"></a>

### inet:dns:wild:a

A DNS A wild card record and the IPv4 it resolves to.
The `inet:dns:wild:a` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('fqdn', 'inet:fqdn'), ('ip', 'inet:ip'))`
- sepr: `None`

<a id="dm-type-inet-dns-wild-aaaa"></a>

### inet:dns:wild:aaaa

A DNS AAAA wild card record and the IPv6 it resolves to.
The `inet:dns:wild:aaaa` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('fqdn', 'inet:fqdn'), ('ip', 'inet:ip'))`
- sepr: `None`

<a id="dm-type-inet-dns-dynreg"></a>

### inet:dns:dynreg

A dynamic DNS registration.
The `inet:dns:dynreg` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`

<a id="dm-type-dns-reply-code"></a>

### dns:reply:code

A DNS reply code.
The `dns:reply:code` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 0 | NOERROR |
| 1 | FORMERR |
| 2 | SERVFAIL |
| 3 | NXDOMAIN |
| 4 | NOTIMP |
| 5 | REFUSED |
| 6 | YXDOMAIN |
| 7 | YXRRSET |
| 8 | NXRRSET |
| 9 | NOTAUTH |
| 10 | NOTZONE |
| 11 | DSOTYPENI |
| 16 | BADSIG |
| 17 | BADKEY |
| 18 | BADTIME |
| 19 | BADMODE |
| 20 | BADNAME |
| 21 | BADALG |
| 22 | BADTRUNC |
| 23 | BADCOOKIE |

- enums:strict: `False`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-inet-dns-query-type"></a>

### inet:dns:query:type

A DNS query type. The IANA assigned DNS record types are declared as enums.
The `inet:dns:query:type` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 1 | A |
| 2 | NS |
| 3 | MD |
| 4 | MF |
| 5 | CNAME |
| 6 | SOA |
| 7 | MB |
| 8 | MG |
| 9 | MR |
| 10 | NULL |
| 11 | WKS |
| 12 | PTR |
| 13 | HINFO |
| 14 | MINFO |
| 15 | MX |
| 16 | TXT |
| 17 | RP |
| 18 | AFSDB |
| 19 | X25 |
| 20 | ISDN |
| 21 | RT |
| 22 | NSAP |
| 23 | NSAP-PTR |
| 24 | SIG |
| 25 | KEY |
| 26 | PX |
| 27 | GPOS |
| 28 | AAAA |
| 29 | LOC |
| 30 | NXT |
| 31 | EID |
| 32 | NIMLOC |
| 33 | SRV |
| 34 | ATMA |
| 35 | NAPTR |
| 36 | KX |
| 37 | CERT |
| 38 | A6 |
| 39 | DNAME |
| 40 | SINK |
| 41 | OPT |
| 42 | APL |
| 43 | DS |
| 44 | SSHFP |
| 45 | IPSECKEY |
| 46 | RRSIG |
| 47 | NSEC |
| 48 | DNSKEY |
| 49 | DHCID |
| 50 | NSEC3 |
| 51 | NSEC3PARAM |
| 52 | TLSA |
| 53 | SMIMEA |
| 55 | HIP |
| 56 | NINFO |
| 57 | RKEY |
| 58 | TALINK |
| 59 | CDS |
| 60 | CDNSKEY |
| 61 | OPENPGPKEY |
| 62 | CSYNC |
| 63 | ZONEMD |
| 64 | SVCB |
| 65 | HTTPS |
| 99 | SPF |
| 100 | UINFO |
| 101 | UID |
| 102 | GID |
| 103 | UNSPEC |
| 104 | NID |
| 105 | L32 |
| 106 | L64 |
| 107 | LP |
| 108 | EUI48 |
| 109 | EUI64 |
| 249 | TKEY |
| 250 | TSIG |
| 251 | IXFR |
| 252 | AXFR |
| 253 | MAILB |
| 254 | MAILA |
| 255 | ANY |
| 256 | URI |
| 257 | CAA |
| 258 | AVC |
| 259 | DOA |
| 260 | AMTRELAY |
| 261 | RESINFO |
| 262 | WALLET |
| 263 | CLA |
| 264 | IPN |
| 32768 | TA |
| 32769 | DLV |

- enums:strict: `False`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-doc-policy-type-taxonomy"></a>

### doc:policy:type:taxonomy

A taxonomy of policy types.
The `doc:policy:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-doc-policy"></a>

### doc:policy

Guiding principles used to reach a set of goals.
The `doc:policy` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:document', {})`

<a id="dm-type-doc-standard-type-taxonomy"></a>

### doc:standard:type:taxonomy

A taxonomy of standard types.
The `doc:standard:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-doc-standard"></a>

### doc:standard

A group of requirements which define how to implement a policy or goal.
The `doc:standard` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:document', {})`

<a id="dm-type-doc-requirement"></a>

### doc:requirement

A single requirement, often defined by a standard.
The `doc:requirement` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:authorable', {})`

<a id="dm-type-doc-resume-type-taxonomy"></a>

### doc:resume:type:taxonomy

A taxonomy of resume types.
The `doc:resume:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-doc-resume"></a>

### doc:resume

A CV/resume document.
The `doc:resume` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:document', {})`

<a id="dm-type-doc-report-type-taxonomy"></a>

### doc:report:type:taxonomy

A taxonomy of report types.
The `doc:report:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-doc-report"></a>

### doc:report

A report.
The `doc:report` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:document', {})`
- `('doc:published', {})`

<a id="dm-type-doc-contract"></a>

### doc:contract

A contract between multiple entities.
The `doc:contract` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:document', {})`
- `('doc:signable', {})`
- `('entity:activity', {})`

<a id="dm-type-doc-contract-type-taxonomy"></a>

### doc:contract:type:taxonomy

A hierarchical taxonomy of contract types.
The `doc:contract:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-doc-reference"></a>

### doc:reference

A reference included in a source.
The `doc:reference` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-price-adjusted"></a>

### econ:price:adjusted

An inflation or currency adjusted price.
The `econ:price:adjusted` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-pay-cvv"></a>

### econ:pay:cvv

A Card Verification Value (CVV).
The `econ:pay:cvv` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{1,6}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-pay-pin"></a>

### econ:pay:pin

A Personal Identification Number (PIN).
The `econ:pay:pin` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{3,6}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-pay-mii"></a>

### econ:pay:mii

A Major Industry Identifier (MII).
The `econ:pay:mii` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `9`
- min: `0`
- signed: `True`
- size: `8`

<a id="dm-type-econ-pay-pan"></a>

### econ:pay:pan

A Primary Account Number (PAN) or card number.
The `econ:pay:pan` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^(?<iin>(?<mii>[0-9]{1})[0-9]{5})[0-9]{1,13}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-pay-iin"></a>

### econ:pay:iin

An Issuer Id Number (IIN).
The `econ:pay:iin` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{6,8}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-pay-card"></a>

### econ:pay:card

A single payment card.
The `econ:pay:card` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('econ:pay:instrument', {})`

<a id="dm-type-econ-bank-check"></a>

### econ:bank:check

A check written out to a recipient.
The `econ:bank:check` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('econ:pay:instrument', {})`

<a id="dm-type-econ-purchase"></a>

### econ:purchase

An event where an actor made a purchase.
The `econ:purchase` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`
- `('geo:locatable', {})`

<a id="dm-type-econ-lineitem"></a>

### econ:lineitem

A line item included as part of a purchase.
The `econ:lineitem` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-payment"></a>

### econ:payment

A payment, crypto currency transaction, or account withdrawal.
The `econ:payment` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`
- `('geo:locatable', {})`

<a id="dm-type-econ-balance"></a>

### econ:balance

The balance of funds available in an account at specific time.
The `econ:balance` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-statement"></a>

### econ:statement

A statement of starting/ending balance and payments for a financial instrument over a time period.
The `econ:statement` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-receipt"></a>

### econ:receipt

A receipt issued as proof of payment.
The `econ:receipt` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-invoice"></a>

### econ:invoice

An invoice issued requesting payment.
The `econ:invoice` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-allocation"></a>

### econ:allocation

An allocation of funds and the amount spent against it, with the variance between them.
The `econ:allocation` type is derived from the base type: [`econ:pricechange`](#dm-type-econ-pricechange).

This type has the following options set:

- names: `{'start': 'allocated', 'end': 'spent', 'delta': 'variance'}`

<a id="dm-type-econ-budget"></a>

### econ:budget

A budget of funds allocated and spent over a period.
The `econ:budget` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-econ-currency"></a>

### econ:currency

A currency. This should ideally be an ISO 4217 currency code when one is available.
The `econ:currency` type is derived from the base type: [`str`](#dm-type-str).

An example of `econ:currency`:

- `USD`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `{'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR', '₩': 'KRW', '₽': 'RUB', '₺': 'TRY', '฿': 'THB'}`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `True`

<a id="dm-type-econ-exchange"></a>

### econ:exchange

A financial exchange where securities are traded.
The `econ:exchange` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-security-type-taxonomy"></a>

### econ:security:type:taxonomy

A hierarchical taxonomy of financial security types.
The `econ:security:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-security"></a>

### econ:security

A financial security which is typically traded on an exchange.
The `econ:security` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-security-ochlv"></a>

### econ:security:ochlv

A sample of the open, close, high, low prices and volume of a security in a specific time window.
The `econ:security:ochlv` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-security-telem"></a>

### econ:security:telem

A sample of the price of a security at a single moment in time.
The `econ:security:telem` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-econ-account-type-taxonomy"></a>

### econ:account:type:taxonomy

A financial account type taxonomy.
The `econ:account:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-account"></a>

### econ:account

A financial account which contains a balance of funds.
The `econ:account` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`

<a id="dm-type-econ-bank-aba-rtn"></a>

### econ:bank:aba:rtn

An American Bank Association (ABA) routing transit number (RTN).
The `econ:bank:aba:rtn` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`
- `('econ:bank:routing:code', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{9}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-bank-iban"></a>

### econ:bank:iban

An International Bank Account Number.
The `econ:bank:iban` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`
- `('econ:pay:instrument', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[A-Z]{2}[0-9]{2}[a-zA-Z0-9]{1,30}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-bank-swift-bic"></a>

### econ:bank:swift:bic

A Society for Worldwide Interbank Financial Telecommunication (SWIFT) Business Identifier Code (BIC).
The `econ:bank:swift:bic` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`
- `('econ:bank:routing:code', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-bank-routing-type-taxonomy"></a>

### econ:bank:routing:type:taxonomy

A taxonomy of bank routing identifier systems.
The `econ:bank:routing:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-bank-routing-id"></a>

### econ:bank:routing:id

A generic bank routing identifier for routing systems without a dedicated form.
The `econ:bank:routing:id` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`
- `('econ:bank:routing:code', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-econ-bank-account"></a>

### econ:bank:account

A bank account paired with the routing identifier that addresses it.
The `econ:bank:account` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('econ:pay:instrument', {})`

This type has the following options set:

- fields: `(('routing', 'econ:bank:routing:code'), ('id', 'base:id'))`
- sepr: `:`

<a id="dm-type-entity-lifespan"></a>

### entity:lifespan

An interval representing the lifespan of an entity, from when it began until it ended.
The `entity:lifespan` type is derived from the base type: [`ival`](#dm-type-ival).

This type has the following options set:

- names: `{'min': 'began', 'max': 'ended'}`
- precision: `microsecond`

<a id="dm-type-entity-individual"></a>

### entity:individual

A singular entity such as a person.
The `entity:individual` type is derived from the base type: [`poly`](#dm-type-poly).

This type has the following options set:

- docs: `None`
- interfaces: `None`
- types: `('ps:person', 'entity:contact', 'inet:service:account')`

<a id="dm-type-entity-name"></a>

### entity:name

A name used to refer to an entity.
The `entity:name` type is derived from the base type: [`base:name`](#dm-type-base-name).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-entity-title"></a>

### entity:title

A title or position name used by an entity.
The `entity:title` type is derived from the base type: [`title`](#dm-type-title).

This type implements the following interfaces:

- `('risk:targetable', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-entity-contact-type-taxonomy"></a>

### entity:contact:type:taxonomy

A hierarchical taxonomy of entity contact types.
The `entity:contact:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-entity-contact"></a>

### entity:contact

A set of contact information which is used by an entity.
The `entity:contact` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:actor', {})`
- `('entity:singular', {})`
- `('entity:multiple', {})`
- `('risk:targetable', {})`
- `('entity:resolvable', {})`
- `('entity:contactable', {})`
- `('meta:observable', {})`

<a id="dm-type-entity-history"></a>

### entity:history

Historical contact information about another contact.
The `entity:history` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:contactable', {})`

<a id="dm-type-entity-contactlist"></a>

### entity:contactlist

A list of contacts.
The `entity:contactlist` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-entity-contactlist-entry"></a>

### entity:contactlist:entry

An entry in a contact list.
The `entity:contactlist:entry` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-entity-relationship-type-taxonomy"></a>

### entity:relationship:type:taxonomy

A hierarchical taxonomy of entity relationship types.
The `entity:relationship:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-entity-relationship"></a>

### entity:relationship

A directional relationship between two actor entities.
The `entity:relationship` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:reported', {})`

<a id="dm-type-entity-had-type-taxonomy"></a>

### entity:had:type:taxonomy

A hierarchical taxonomy of types of possession.
The `entity:had:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-entity-had"></a>

### entity:had

An item which was possessed by an actor.
The `entity:had` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-entity-owned"></a>

### entity:owned

An item which was owned by an actor.
The `entity:owned` type is derived from the base type: [`entity:had`](#dm-type-entity-had).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-entity-conversation"></a>

### entity:conversation

A conversation between entities.
The `entity:conversation` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-entity-goal-type-taxonomy"></a>

### entity:goal:type:taxonomy

A hierarchical taxonomy of goal types.
The `entity:goal:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-entity-goal"></a>

### entity:goal

A stated or assessed goal.
The `entity:goal` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:reported', {})`
- `('meta:achievable', {})`

<a id="dm-type-entity-motive"></a>

### entity:motive

A goal held by an actor for a period of time.
The `entity:motive` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-entity-campaign-type-taxonomy"></a>

### entity:campaign:type:taxonomy

A hierarchical taxonomy of campaign types.
The `entity:campaign:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-entity-campaign"></a>

### entity:campaign

Activity in pursuit of a goal.
The `entity:campaign` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('econ:budgetable', {})`
- `('entity:activity', {})`
- `('meta:reported', {})`
- `('meta:observable', {})`
- `('entity:supportable', {})`
- `('entity:participable', {})`

<a id="dm-type-entity-conflict"></a>

### entity:conflict

Represents a conflict where two or more campaigns have mutually exclusive goals.
The `entity:conflict` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:activity', {})`

<a id="dm-type-entity-contributed"></a>

### entity:contributed

Represents a specific instance of contributing material support to a campaign.
The `entity:contributed` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`

<a id="dm-type-entity-studied"></a>

### entity:studied

A period when an actor studied or was educated.
The `entity:studied` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-entity-achieved"></a>

### entity:achieved

An event where an actor achieved a goal or was given an award.
The `entity:achieved` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`

<a id="dm-type-entity-believed"></a>

### entity:believed

A period where an actor held a belief.
The `entity:believed` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-entity-discovered"></a>

### entity:discovered

An event where an entity made a discovery.
The `entity:discovered` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`

<a id="dm-type-entity-destroyed"></a>

### entity:destroyed

An event where an actor destroyed an item.
The `entity:destroyed` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`

<a id="dm-type-entity-signed"></a>

### entity:signed

An event where an actor signed a document.
The `entity:signed` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`

<a id="dm-type-entity-asked"></a>

### entity:asked

An event where an actor made an ask as part of a negotiation.
The `entity:asked` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:stance', {})`

<a id="dm-type-entity-offered"></a>

### entity:offered

An event where an actor made an offer as part of a negotiation.
The `entity:offered` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:stance', {})`

<a id="dm-type-entity-attended"></a>

### entity:attended

A period where an actor attended an event or activity.
The `entity:attended` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-entity-supported"></a>

### entity:supported

A period where an actor supported, sponsored, or materially contributed to an activity or cause.
The `entity:supported` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-entity-registered"></a>

### entity:registered

An event where an actor registered for an event or activity.
The `entity:registered` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`

<a id="dm-type-entity-participated"></a>

### entity:participated

A period where an actor participated in an activity.
The `entity:participated` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-entity-said"></a>

### entity:said

A statement made by an actor.
The `entity:said` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`
- `('meta:recordable', {})`

<a id="dm-type-entity-created"></a>

### entity:created

An activity where an actor helped to create an item.
The `entity:created` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-entity-proficiency"></a>

### entity:proficiency

A period of time where an actor had proficiency with a skill.
The `entity:proficiency` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-file-bytes"></a>

### file:bytes

A file.
The `file:bytes` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`

<a id="dm-type-file-exemplar-entry"></a>

### file:exemplar:entry

An exemplar file entry used to model behavior.
The `file:exemplar:entry` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('meta:observable', {})`

<a id="dm-type-file-stored-entry"></a>

### file:stored:entry

A stored file entry.
The `file:stored:entry` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('meta:observable', {})`

<a id="dm-type-file-system-entry"></a>

### file:system:entry

A file entry contained by a host filesystem.
The `file:system:entry` type is derived from the base type: [`file:stored:entry`](#dm-type-file-stored-entry).

This type implements the following interfaces:

- `('file:entry', {})`
- `('meta:observable', {})`

<a id="dm-type-file-subfile-entry"></a>

### file:subfile:entry

A file entry contained by a parent file.
The `file:subfile:entry` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('file:subfile', {})`

<a id="dm-type-file-archive-entry"></a>

### file:archive:entry

A file entry contained by an archive file.
The `file:archive:entry` type is derived from the base type: [`file:stored:entry`](#dm-type-file-stored-entry).

This type implements the following interfaces:

- `('file:entry', {})`
- `('meta:observable', {})`
- `('file:subfile', {})`

<a id="dm-type-file-mime-rar-entry"></a>

### file:mime:rar:entry

A file entry contained by a RAR archive file.
The `file:mime:rar:entry` type is derived from the base type: [`file:archive:entry`](#dm-type-file-archive-entry).

This type implements the following interfaces:

- `('file:entry', {})`
- `('meta:observable', {})`
- `('file:subfile', {})`

<a id="dm-type-file-mime-zip-entry"></a>

### file:mime:zip:entry

A file entry contained by a ZIP archive file.
The `file:mime:zip:entry` type is derived from the base type: [`file:archive:entry`](#dm-type-file-archive-entry).

This type implements the following interfaces:

- `('file:entry', {})`
- `('meta:observable', {})`
- `('file:subfile', {})`

<a id="dm-type-file-attachment"></a>

### file:attachment

A file attachment.
The `file:attachment` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('meta:usable', {})`
- `('meta:observable', {})`

<a id="dm-type-file-mime"></a>

### file:mime

A file mime name string.
The `file:mime` type is derived from the base type: [`str`](#dm-type-str).

An example of `file:mime`:

- `text/plain`

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-file-mime-pdf"></a>

### file:mime:pdf

Metadata extracted from a Portable Document Format (PDF) file.
The `file:mime:pdf` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-msdoc"></a>

### file:mime:msdoc

Metadata about a Microsoft Word file.
The `file:mime:msdoc` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:msoffice', {})`

<a id="dm-type-file-mime-msxls"></a>

### file:mime:msxls

Metadata about a Microsoft Excel file.
The `file:mime:msxls` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:msoffice', {})`

<a id="dm-type-file-mime-msppt"></a>

### file:mime:msppt

Metadata about a Microsoft Powerpoint file.
The `file:mime:msppt` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:msoffice', {})`

<a id="dm-type-file-mime-pe"></a>

### file:mime:pe

Metadata about a Microsoft Portable Executable (PE) file.
The `file:mime:pe` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:exe', {'template': {'executable': 'PE executable'}})`

<a id="dm-type-file-mime-elf"></a>

### file:mime:elf

Metadata about an ELF executable file.
The `file:mime:elf` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:exe', {'template': {'executable': 'ELF executable'}})`

<a id="dm-type-file-mime-macho"></a>

### file:mime:macho

Metadata about a Mach-O executable file.
The `file:mime:macho` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:exe', {'template': {'executable': 'Mach-O executable'}})`

<a id="dm-type-file-mime-rtf"></a>

### file:mime:rtf

The GUID of a set of mime metadata for a .rtf file.
The `file:mime:rtf` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-jpg"></a>

### file:mime:jpg

The GUID of a set of mime metadata for a .jpg file.
The `file:mime:jpg` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:image', {})`

<a id="dm-type-file-mime-tif"></a>

### file:mime:tif

The GUID of a set of mime metadata for a .tif file.
The `file:mime:tif` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:image', {})`

<a id="dm-type-file-mime-gif"></a>

### file:mime:gif

The GUID of a set of mime metadata for a .gif file.
The `file:mime:gif` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:image', {})`

<a id="dm-type-file-mime-png"></a>

### file:mime:png

The GUID of a set of mime metadata for a .png file.
The `file:mime:png` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:image', {})`

<a id="dm-type-file-mime-pe-section"></a>

### file:mime:pe:section

A PE section contained in a file.
The `file:mime:pe:section` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-pe-resource"></a>

### file:mime:pe:resource

A PE resource contained in a file.
The `file:mime:pe:resource` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-pe-export"></a>

### file:mime:pe:export

A named PE export contained in a file.
The `file:mime:pe:export` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-pe-vsvers-keyval"></a>

### file:mime:pe:vsvers:keyval

A key value pair found in a PE VS_VERSIONINFO structure.
The `file:mime:pe:vsvers:keyval` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('name', 'str'), ('value', 'str'))`
- sepr: `None`

<a id="dm-type-file-macho-loadcmd-type"></a>

### file:macho:loadcmd:type

A Mach-O load command type.
The `file:macho:loadcmd:type` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 1 | segment |
| 2 | symbol table |
| 3 | gdb symbol table |
| 4 | thread |
| 5 | unix thread |
| 6 | fixed VM shared library |
| 7 | fixed VM shared library identification |
| 8 | object identification |
| 9 | fixed VM file inclusion |
| 10 | prepage |
| 11 | dynamic link-edit symbol table |
| 12 | load dynamically linked shared library |
| 13 | dynamically linked shared library identifier |
| 14 | load dynamic linker |
| 15 | dynamic linker identification |
| 16 | prebound dynamically linked shared library |
| 17 | image routines |
| 18 | sub framework |
| 19 | sub umbrella |
| 20 | sub client |
| 21 | sub library |
| 22 | two level namespace lookup hints |
| 23 | prebind checksum |
| 24 | weak import dynamically linked shared library |
| 25 | 64bit segment |
| 26 | 64bit image routines |
| 27 | uuid |
| 28 | runpath additions |
| 29 | code signature |
| 30 | split segment info |
| 31 | load and re-export dynamic library |
| 32 | delay load of dynamic library |
| 33 | encrypted segment information |
| 34 | compressed dynamic library information |
| 35 | load upward dylib |
| 36 | minimum osx version |
| 37 | minimum ios version |
| 38 | compressed table of function start addresses |
| 39 | environment variable string for dynamic library |
| 40 | unix thread replacement |
| 41 | table of non-instructions in __text |
| 42 | source version used to build binary |
| 43 | Code signing DRs copied from linked dynamic libraries |

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-file-macho-section-type"></a>

### file:macho:section:type

A Mach-O section type.
The `file:macho:section:type` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 0 | regular |
| 1 | zero fill on demand |
| 2 | only literal C strings |
| 3 | only 4 byte literals |
| 4 | only 8 byte literals |
| 5 | only pointers to literals |
| 6 | only non-lazy symbol pointers |
| 7 | only lazy symbol pointers |
| 8 | only symbol stubs |
| 9 | only function pointers for init |
| 10 | only function pointers for fini |
| 11 | contains symbols to be coalesced |
| 12 | zero fill on demand (greater than 4gb) |
| 13 | only pairs of function pointers for interposing |
| 14 | only 16 byte literals |
| 15 | dtrace object format |
| 16 | only lazy symbols pointers to lazy dynamic libraries |

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-pe-resource-type"></a>

### pe:resource:type

The typecode for the resource.
The `pe:resource:type` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 1 | RT_CURSOR |
| 2 | RT_BITMAP |
| 3 | RT_ICON |
| 4 | RT_MENU |
| 5 | RT_DIALOG |
| 6 | RT_STRING |
| 7 | RT_FONTDIR |
| 8 | RT_FONT |
| 9 | RT_ACCELERATOR |
| 10 | RT_RCDATA |
| 11 | RT_MESSAGETABLE |
| 12 | RT_GROUP_CURSOR |
| 14 | RT_GROUP_ICON |
| 16 | RT_VERSION |
| 17 | RT_DLGINCLUDE |
| 19 | RT_PLUGPLAY |
| 20 | RT_VXD |
| 21 | RT_ANICURSOR |
| 22 | RT_ANIICON |
| 23 | RT_HTML |
| 24 | RT_MANIFEST |

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-pe-langid"></a>

### pe:langid

The PE language id.
The `pe:langid` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 0 | neutral |
| 1 | ar |
| 2 | bg |
| 3 | ca |
| 4 | zh-Hans |
| 5 | cs |
| 6 | da |
| 7 | de |
| 8 | el |
| 9 | en |
| 10 | es |
| 11 | fi |
| 12 | fr |
| 13 | he |
| 14 | hu |
| 15 | is |
| 16 | it |
| 17 | ja |
| 18 | ko |
| 19 | nl |
| 20 | no |
| 21 | pl |
| 22 | pt |
| 23 | rm |
| 24 | ro |
| 25 | ru |
| 26 | hr |
| 27 | sk |
| 28 | sq |
| 29 | sv |
| 30 | th |
| 31 | tr |
| 32 | ur |
| 33 | id |
| 34 | uk |
| 35 | be |
| 36 | sl |
| 37 | et |
| 38 | lv |
| 39 | lt |
| 40 | tg |
| 41 | fa |
| 42 | vi |
| 43 | hy |
| 44 | az |
| 45 | eu |
| 46 | hsb |
| 47 | mk |
| 48 | st |
| 49 | ts |
| 50 | tn |
| 51 | ve |
| 52 | xh |
| 53 | zu |
| 54 | af |
| 55 | ka |
| 56 | fo |
| 57 | hi |
| 58 | mt |
| 59 | se |
| 60 | ga |
| 61 | yi |
| 62 | ms |
| 63 | kk |
| 64 | ky |
| 65 | sw |
| 66 | tk |
| 67 | uz |
| 68 | tt |
| 69 | bn |
| 70 | pa |
| 71 | gu |
| 72 | or |
| 73 | ta |
| 74 | te |
| 75 | kn |
| 76 | ml |
| 77 | as |
| 78 | mr |
| 79 | sa |
| 80 | mn |
| 81 | bo |
| 82 | cy |
| 83 | km |
| 84 | lo |
| 85 | my |
| 86 | gl |
| 87 | kok |
| 88 | mni |
| 89 | sd |
| 90 | syr |
| 91 | si |
| 92 | chr |
| 93 | iu |
| 94 | am |
| 95 | tzm |
| 96 | ks |
| 97 | ne |
| 98 | fy |
| 99 | ps |
| 100 | fil |
| 101 | dv |
| 102 | bin |
| 103 | ff |
| 104 | ha |
| 105 | ibb |
| 106 | yo |
| 107 | quz |
| 108 | nso |
| 109 | ba |
| 110 | lb |
| 111 | kl |
| 112 | ig |
| 113 | kr |
| 114 | om |
| 115 | ti |
| 116 | gn |
| 117 | haw |
| 118 | la |
| 119 | so |
| 120 | ii |
| 121 | pap |
| 122 | arn |
| 123 | undefined and unreserved 0x007B |
| 124 | moh |
| 125 | undefined and unreserved 0x007D |
| 126 | br |
| 127 | invariant |
| 128 | ug |
| 129 | mi |
| 130 | oc |
| 131 | co |
| 132 | gsw |
| 133 | sah |
| 134 | quc |
| 135 | rw |
| 136 | wo |
| 137 | undefined and unreserved 0x0089 |
| 138 | undefined and unreserved 0x008A |
| 139 | undefined and unreserved 0x008B |
| 140 | prs |
| 141 | undefined and unreserved 0x008D |
| 142 | undefined and unreserved 0x008E |
| 143 | undefined and unreserved 0x008F |
| 144 | undefined and unreserved 0x0090 |
| 145 | gd |
| 146 | ku |
| 147 | quc, reserved |
| 1024 | default |
| 1025 | ar-SA |
| 1026 | bg-BG |
| 1027 | ca-ES |
| 1028 | zh-TW |
| 1029 | cs-CZ |
| 1030 | da-DK |
| 1031 | de-DE |
| 1032 | el-GR |
| 1033 | en-US |
| 1034 | es-ES_tradnl |
| 1035 | fi-FI |
| 1036 | fr-FR |
| 1037 | he-IL |
| 1038 | hu-HU |
| 1039 | is-IS |
| 1040 | it-IT |
| 1041 | ja-JP |
| 1042 | ko-KR |
| 1043 | nl-NL |
| 1044 | nb-NO |
| 1045 | pl-PL |
| 1046 | pt-BR |
| 1047 | rm-CH |
| 1048 | ro-RO |
| 1049 | ru-RU |
| 1050 | hr-HR |
| 1051 | sk-SK |
| 1052 | sq-AL |
| 1053 | sv-SE |
| 1054 | th-TH |
| 1055 | tr-TR |
| 1056 | ur-PK |
| 1057 | id-ID |
| 1058 | uk-UA |
| 1059 | be-BY |
| 1060 | sl-SI |
| 1061 | et-EE |
| 1062 | lv-LV |
| 1063 | lt-LT |
| 1064 | tg-Cyrl-TJ |
| 1065 | fa-IR |
| 1066 | vi-VN |
| 1067 | hy-AM |
| 1068 | az-Latn-AZ |
| 1069 | eu-ES |
| 1070 | hsb-DE |
| 1071 | mk-MK |
| 1072 | st-ZA |
| 1073 | ts-ZA |
| 1074 | tn-ZA |
| 1075 | ve-ZA |
| 1076 | xh-ZA |
| 1077 | zu-ZA |
| 1078 | af-ZA |
| 1079 | ka-GE |
| 1080 | fo-FO |
| 1081 | hi-IN |
| 1082 | mt-MT |
| 1083 | se-NO |
| 1085 | yi-001 |
| 1086 | ms-MY |
| 1087 | kk-KZ |
| 1088 | ky-KG |
| 1089 | sw-KE |
| 1090 | tk-TM |
| 1091 | uz-Latn-UZ |
| 1092 | tt-RU |
| 1093 | bn-IN |
| 1094 | pa-IN |
| 1095 | gu-IN |
| 1096 | or-IN |
| 1097 | ta-IN |
| 1098 | te-IN |
| 1099 | kn-IN |
| 1100 | ml-IN |
| 1101 | as-IN |
| 1102 | mr-IN |
| 1103 | sa-IN |
| 1104 | mn-MN |
| 1105 | bo-CN |
| 1106 | cy-GB |
| 1107 | km-KH |
| 1108 | lo-LA |
| 1109 | my-MM |
| 1110 | gl-ES |
| 1111 | kok-IN |
| 1112 | mni-IN |
| 1113 | sd-Deva-IN |
| 1114 | syr-SY |
| 1115 | si-LK |
| 1116 | chr-Cher-US |
| 1117 | iu-Cans-CA |
| 1118 | am-ET |
| 1119 | tzm-Arab-MA |
| 1120 | ks-Arab |
| 1121 | ne-NP |
| 1122 | fy-NL |
| 1123 | ps-AF |
| 1124 | fil-PH |
| 1125 | dv-MV |
| 1126 | bin-NG |
| 1127 | ff-NG |
| 1128 | ha-Latn-NG |
| 1129 | ibb-NG |
| 1130 | yo-NG |
| 1131 | quz-BO |
| 1132 | nso-ZA |
| 1133 | ba-RU |
| 1134 | lb-LU |
| 1135 | kl-GL |
| 1136 | ig-NG |
| 1137 | kr-Latn-NG |
| 1138 | om-ET |
| 1139 | ti-ET |
| 1140 | gn-PY |
| 1141 | haw-US |
| 1142 | la-VA |
| 1143 | so-SO |
| 1144 | ii-CN |
| 1145 | pap-029 |
| 1146 | arn-CL |
| 1148 | moh-CA |
| 1150 | br-FR |
| 1152 | ug-CN |
| 1153 | mi-NZ |
| 1154 | oc-FR |
| 1155 | co-FR |
| 1156 | gsw-FR |
| 1157 | sah-RU |
| 1158 | quc-Latn-GT |
| 1159 | rw-RW |
| 1160 | wo-SN |
| 1164 | prs-AF |
| 1165 | plt-MG |
| 1166 | zh-yue-HK |
| 1167 | tdd-Tale-CN |
| 1168 | khb-Talu-CN |
| 1169 | gd-GB |
| 1170 | ku-Arab-IQ |
| 1171 | quc-CO, reserved |
| 1281 | qps-ploc |
| 1534 | qps-ploca |
| 2048 | sys default |
| 2049 | ar-IQ |
| 2051 | ca-ES-Valencia |
| 2052 | zh-CN |
| 2055 | de-CH |
| 2057 | en-GB |
| 2058 | es-MX |
| 2060 | fr-BE |
| 2064 | it-CH |
| 2065 | ja-Ploc-JP |
| 2067 | nl-BE |
| 2068 | nn-NO |
| 2070 | pt-PT |
| 2072 | ro-MD |
| 2073 | ru-MD |
| 2074 | sr-Latn-CS |
| 2077 | sv-FI |
| 2080 | ur-IN |
| 2087 | undefined and unreserved 0x0827 |
| 2092 | az-Cyrl-AZ |
| 2094 | dsb-DE |
| 2098 | tn-BW |
| 2107 | se-SE |
| 2108 | ga-IE |
| 2110 | ms-BN |
| 2111 | kk-Latn-KZ |
| 2115 | uz-Cyrl-UZ |
| 2117 | bn-BD |
| 2118 | pa-Arab-PK |
| 2121 | ta-LK |
| 2128 | mn-Mong-CN |
| 2129 | bo-BT |
| 2137 | sd-Arab-PK |
| 2141 | iu-Latn-CA |
| 2143 | tzm-Latn-DZ |
| 2144 | ks-Deva-IN |
| 2145 | ne-IN |
| 2151 | ff-Latn-SN |
| 2155 | quz-EC |
| 2163 | ti-ER |
| 2559 | qps-plocm |
| 3072 | custom default |
| 3073 | ar-EG |
| 3076 | zh-HK |
| 3079 | de-AT |
| 3081 | en-AU |
| 3082 | es-ES |
| 3084 | fr-CA |
| 3098 | sr-Cyrl-CS |
| 3131 | se-FI |
| 3152 | mn-Mong-MN |
| 3153 | dz-BT |
| 3167 | tzm-MA |
| 3179 | quz-PE |
| 4096 | custom unspecified |
| 4097 | ar-LY |
| 4100 | zh-SG |
| 4103 | de-LU |
| 4105 | en-CA |
| 4106 | es-GT |
| 4108 | fr-CH |
| 4122 | hr-BA |
| 4155 | smj-NO |
| 4191 | tzm-Tfng-MA |
| 5120 | ui_custom_default |
| 5121 | ar-DZ |
| 5124 | zh-MO |
| 5127 | de-LI |
| 5129 | en-NZ |
| 5130 | es-CR |
| 5132 | fr-LU |
| 5146 | bs-Latn-BA |
| 5179 | smj-SE |
| 6145 | ar-MA |
| 6153 | en-IE |
| 6154 | es-PA |
| 6156 | fr-MC |
| 6170 | sr-Latn-BA |
| 6203 | sma-NO |
| 7169 | ar-TN |
| 7177 | en-ZA |
| 7178 | es-DO |
| 7180 | fr-029 |
| 7194 | sr-Cyrl-BA |
| 7227 | sma-SE |
| 8192 | custom transient 0x2000 |
| 8193 | ar-OM |
| 8200 | undefined and unreserved 0x2008 |
| 8201 | en-JM |
| 8202 | es-VE |
| 8204 | fr-RE |
| 8218 | bs-Cyrl-BA |
| 8251 | sms-FI |
| 9216 | custom transient 0x2400 |
| 9217 | ar-YE |
| 9225 | en-029 |
| 9226 | es-CO |
| 9228 | fr-CD |
| 9242 | sr-Latn-RS |
| 9275 | smn-FI |
| 10240 | custom transient 0x2800 |
| 10241 | ar-SY |
| 10249 | en-BZ |
| 10250 | es-PE |
| 10252 | fr-SN |
| 10266 | sr-Cyrl-RS |
| 11264 | custom transient 0x2C00 |
| 11265 | ar-JO |
| 11273 | en-TT |
| 11274 | es-AR |
| 11276 | fr-CM |
| 11290 | sr-Latn-ME |
| 12288 | custom transient 0x3000 |
| 12289 | ar-LB |
| 12297 | en-ZW |
| 12298 | es-EC |
| 12300 | fr-CI |
| 12314 | sr-Cyrl-ME |
| 13312 | custom transient 0x3400 |
| 13313 | ar-KW |
| 13321 | en-PH |
| 13322 | es-CL |
| 13324 | fr-ML |
| 14336 | custom transient 0x3800 |
| 14337 | ar-AE |
| 14345 | en-ID |
| 14346 | es-UY |
| 14348 | fr-MA |
| 15360 | custom transient 0x3C00 |
| 15361 | ar-BH |
| 15369 | en-HK |
| 15370 | es-PY |
| 15372 | fr-HT |
| 16384 | custom transient 0x4000 |
| 16385 | ar-QA |
| 16393 | en-IN |
| 16394 | es-BO |
| 17408 | custom transient 0x4400 |
| 17409 | ar-Ploc-SA |
| 17417 | en-MY |
| 17418 | es-SV |
| 18432 | custom transient 0x4800 |
| 18433 | ar-145 |
| 18441 | en-SG |
| 18442 | es-HN |
| 19456 | custom transient 0x4C00 |
| 19465 | en-AE |
| 19466 | es-NI |
| 20489 | en-BH |
| 20490 | es-PR |
| 21513 | en-EG |
| 21514 | es-US |
| 22537 | en-JO |
| 22538 | es-419 |
| 23561 | en-KW |
| 23562 | es-CU |
| 24585 | en-TR |
| 25609 | en-YE |
| 25626 | bs-Cyrl |
| 26650 | bs-Latn |
| 27674 | sr-Cyrl |
| 28698 | sr-Latn |
| 28731 | smn |
| 29740 | az-Cyrl |
| 29755 | sms |
| 30724 | zh |
| 30740 | nn |
| 30746 | bs |
| 30764 | az-Latn |
| 30779 | sma |
| 30783 | kk-Cyrl |
| 30787 | uz-Cyrl |
| 30800 | mn-Cyrl |
| 30813 | iu-Cans |
| 30815 | tzm-Tfng |
| 31748 | zh-Hant |
| 31764 | nb |
| 31770 | sr |
| 31784 | tg-Cyrl |
| 31790 | dsb |
| 31803 | smj |
| 31807 | kk-Latn |
| 31811 | uz-Latn |
| 31814 | pa-Arab |
| 31824 | mn-Mong |
| 31833 | sd-Arab |
| 31836 | chr-Cher |
| 31837 | iu-Latn |
| 31839 | tzm-Latn |
| 31847 | ff-Latn |
| 31848 | ha-Latn |
| 31890 | ku-Arab |
| 58380 | fr-015 |
| 61166 | reserved 0xEEEE |
| 62190 | reserved 0xF2EE |

- enums:strict: `False`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `65535`
- min: `0`
- signed: `True`
- size: `8`

<a id="dm-type-file-mime-macho-loadcmd"></a>

### file:mime:macho:loadcmd

A generic load command pulled from the Mach-O headers.
The `file:mime:macho:loadcmd` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-macho-version"></a>

### file:mime:macho:version

A specific load command used to denote the version of the source used to build the Mach-O binary.
The `file:mime:macho:version` type is derived from the base type: [`file:mime:macho:loadcmd`](#dm-type-file-mime-macho-loadcmd).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-macho-uuid"></a>

### file:mime:macho:uuid

A specific load command denoting a UUID used to uniquely identify the Mach-O binary.
The `file:mime:macho:uuid` type is derived from the base type: [`file:mime:macho:loadcmd`](#dm-type-file-mime-macho-loadcmd).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-macho-segment"></a>

### file:mime:macho:segment

A named region of bytes inside a Mach-O binary.
The `file:mime:macho:segment` type is derived from the base type: [`file:mime:macho:loadcmd`](#dm-type-file-mime-macho-loadcmd).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-macho-section"></a>

### file:mime:macho:section

A section inside a Mach-O binary denoting a named region of bytes inside a segment.
The `file:mime:macho:section` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-file-mime-lnk"></a>

### file:mime:lnk

The GUID of the metadata pulled from a Windows shortcut or LNK file.
The `file:mime:lnk` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:meta', {})`

<a id="dm-type-pol-country"></a>

### pol:country

A GUID for a country.
The `pol:country` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('risk:targetable', {})`

<a id="dm-type-pol-country-code"></a>

### pol:country:code

A country code.
The `pol:country:code` type is derived from the base type: [`poly`](#dm-type-poly).

This type has the following options set:

- docs: `None`
- interfaces: `None`
- types: `('iso:3166:alpha2', 'iso:3166:numeric3', 'iso:3166:alpha3', 'base:id')`

<a id="dm-type-pol-immigration-status"></a>

### pol:immigration:status

A node which tracks the immigration status of a contact.
The `pol:immigration:status` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-pol-immigration-status-type-taxonomy"></a>

### pol:immigration:status:type:taxonomy

A hierarchical taxonomy of immigration status types.
The `pol:immigration:status:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-pol-vitals"></a>

### pol:vitals

A set of vital statistics about a country.
The `pol:vitals` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-pol-election"></a>

### pol:election

An election involving one or more races for office.
The `pol:election` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:activity', {})`

<a id="dm-type-pol-race"></a>

### pol:race

An individual race for office.
The `pol:race` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:activity', {})`

<a id="dm-type-pol-office"></a>

### pol:office

An elected or appointed office.
The `pol:office` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-pol-term"></a>

### pol:term

A term in office held by a specific individual.
The `pol:term` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-pol-candidate"></a>

### pol:candidate

A candidate for office in a specific race.
The `pol:candidate` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-pol-pollingplace"></a>

### pol:pollingplace

An official place where ballots may be cast for a specific election.
The `pol:pollingplace` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-geo-telem"></a>

### geo:telem

The geospatial position and physical characteristics of a node at a given time.
The `geo:telem` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('phys:tangible', {})`

<a id="dm-type-geo-json"></a>

### geo:json

GeoJSON structured JSON data.
The `geo:json` type is derived from the base type: [`data`](#dm-type-data).

This type has the following options set:

- schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "BoundingBox": {
      "items": {
        "type": "number"
      },
      "minItems": 4,
      "type": "array"
    },
    "Feature": {
      "additionalProperties": true,
      "properties": {
        "bbox": {
          "$ref": "#/definitions/BoundingBox"
        },
        "geometry": {
          "oneOf": [
            {
              "type": "null"
            },
            {
              "$ref": "#/definitions/Point"
            },
            {
              "$ref": "#/definitions/LineString"
            },
            {
              "$ref": "#/definitions/Polygon"
            },
            {
              "$ref": "#/definitions/MultiPoint"
            },
            {
              "$ref": "#/definitions/MultiLineString"
            },
            {
              "$ref": "#/definitions/MultiPolygon"
            },
            {
              "$ref": "#/definitions/GeometryCollection"
            }
          ]
        },
        "properties": {
          "oneOf": [
            {
              "type": "null"
            },
            {
              "additionalProperties": true,
              "type": "object"
            }
          ]
        },
        "type": {
          "enum": [
            "Feature"
          ],
          "type": "string"
        }
      },
      "required": [
        "type",
        "properties",
        "geometry"
      ],
      "title": "GeoJSON Feature",
      "type": "object"
    },
    "FeatureCollection": {
      "additionalProperties": true,
      "properties": {
        "bbox": {
          "$ref": "#/definitions/BoundingBox"
        },
        "features": {
          "items": {
            "$ref": "#/definitions/Feature"
          },
          "type": "array"
        },
        "type": {
          "enum": [
            "FeatureCollection"
          ],
          "type": "string"
        }
      },
      "required": [
        "type",
        "features"
      ],
      "title": "GeoJSON FeatureCollection",
      "type": "object"
    },
    "GeometryCollection": {
      "additionalProperties": true,
      "properties": {
        "bbox": {
          "$ref": "#/definitions/BoundingBox"
        },
        "geometries": {
          "items": {
            "oneOf": [
              {
                "$ref": "#/definitions/Point"
              },
              {
                "$ref": "#/definitions/LineString"
              },
              {
                "$ref": "#/definitions/Polygon"
              },
              {
                "$ref": "#/definitions/MultiPoint"
              },
              {
                "$ref": "#/definitions/MultiLineString"
              },
              {
                "$ref": "#/definitions/MultiPolygon"
              }
            ]
          },
          "type": "array"
        },
        "type": {
          "enum": [
            "GeometryCollection"
          ],
          "type": "string"
        }
      },
      "required": [
        "type",
        "geometries"
      ],
      "title": "GeoJSON GeometryCollection",
      "type": "object"
    },
    "LineString": {
      "additionalProperties": true,
      "properties": {
        "bbox": {
          "$ref": "#/definitions/BoundingBox"
        },
        "coordinates": {
          "$ref": "#/definitions/LineStringCoordinates"
        },
        "type": {
          "enum": [
            "LineString"
          ],
          "type": "string"
        }
      },
      "required": [
        "type",
        "coordinates"
      ],
      "title": "GeoJSON LineString",
      "type": "object"
    },
    "LineStringCoordinates": {
      "items": {
        "$ref": "#/definitions/PointCoordinates"
      },
      "minItems": 2,
      "type": "array"
    },
    "LinearRingCoordinates": {
      "items": {
        "$ref": "#/definitions/PointCoordinates"
      },
      "minItems": 4,
      "type": "array"
    },
    "MultiLineString": {
      "additionalProperties": true,
      "properties": {
        "bbox": {
          "$ref": "#/definitions/BoundingBox"
        },
        "coordinates": {
          "items": {
            "$ref": "#/definitions/LineStringCoordinates"
          },
          "type": "array"
        },
        "type": {
          "enum": [
            "MultiLineString"
          ],
          "type": "string"
        }
      },
      "required": [
        "type",
        "coordinates"
      ],
      "title": "GeoJSON MultiLineString",
      "type": "object"
    },
    "MultiPoint": {
      "additionalProperties": true,
      "properties": {
        "bbox": {
          "$ref": "#/definitions/BoundingBox"
        },
        "coordinates": {
          "items": {
            "$ref": "#/definitions/PointCoordinates"
          },
          "type": "array"
        },
        "type": {
          "enum": [
            "MultiPoint"
          ],
          "type": "string"
        }
      },
      "required": [
        "type",
        "coordinates"
      ],
      "title": "GeoJSON MultiPoint",
      "type": "object"
    },
    "MultiPolygon": {
      "additionalProperties": true,
      "properties": {
        "bbox": {
          "$ref": "#/definitions/BoundingBox"
        },
        "coordinates": {
          "items": {
            "$ref": "#/definitions/PolygonCoordinates"
          },
          "type": "array"
        },
        "type": {
          "enum": [
            "MultiPolygon"
          ],
          "type": "string"
        }
      },
      "required": [
        "type",
        "coordinates"
      ],
      "title": "GeoJSON MultiPolygon",
      "type": "object"
    },
    "Point": {
      "additionalProperties": true,
      "properties": {
        "bbox": {
          "$ref": "#/definitions/BoundingBox"
        },
        "coordinates": {
          "$ref": "#/definitions/PointCoordinates"
        },
        "type": {
          "enum": [
            "Point"
          ],
          "type": "string"
        }
      },
      "required": [
        "type",
        "coordinates"
      ],
      "title": "GeoJSON Point",
      "type": "object"
    },
    "PointCoordinates": {
      "items": {
        "type": "number"
      },
      "minItems": 2,
      "type": "array"
    },
    "Polygon": {
      "additionalProperties": true,
      "properties": {
        "bbox": {
          "$ref": "#/definitions/BoundingBox"
        },
        "coordinates": {
          "$ref": "#/definitions/PolygonCoordinates"
        },
        "type": {
          "enum": [
            "Polygon"
          ],
          "type": "string"
        }
      },
      "required": [
        "type",
        "coordinates"
      ],
      "title": "GeoJSON Polygon",
      "type": "object"
    },
    "PolygonCoordinates": {
      "items": {
        "$ref": "#/definitions/LinearRingCoordinates"
      },
      "type": "array"
    }
  },
  "oneOf": [
    {
      "$ref": "#/definitions/Point"
    },
    {
      "$ref": "#/definitions/LineString"
    },
    {
      "$ref": "#/definitions/Polygon"
    },
    {
      "$ref": "#/definitions/MultiPoint"
    },
    {
      "$ref": "#/definitions/MultiLineString"
    },
    {
      "$ref": "#/definitions/MultiPolygon"
    },
    {
      "$ref": "#/definitions/GeometryCollection"
    },
    {
      "$ref": "#/definitions/Feature"
    },
    {
      "$ref": "#/definitions/FeatureCollection"
    }
  ]
}
```


<a id="dm-type-geo-name"></a>

### geo:name

An unstructured place name or address.
The `geo:name` type is derived from the base type: [`base:name`](#dm-type-base-name).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-geo-place"></a>

### geo:place

A geographic place.
The `geo:place` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('geo:locatable', {'prefix': ''})`
- `('risk:targetable', {})`

<a id="dm-type-geo-place-type-taxonomy"></a>

### geo:place:type:taxonomy

A hierarchical taxonomy of place types.
The `geo:place:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-geo-address"></a>

### geo:address

A street/mailing address string.
The `geo:address` type is derived from the base type: [`title`](#dm-type-title).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-geo-longitude"></a>

### geo:longitude

A longitude in floating point notation.
The `geo:longitude` type is derived from the base type: [`float`](#dm-type-float).

An example of `geo:longitude`:

- `31.337`

This type has the following options set:

- fmt: `%f`
- max: `180.0`
- maxisvalid: `True`
- min: `-180.0`
- minisvalid: `False`

<a id="dm-type-geo-latitude"></a>

### geo:latitude

A latitude in floating point notation.
The `geo:latitude` type is derived from the base type: [`float`](#dm-type-float).

An example of `geo:latitude`:

- `31.337`

This type has the following options set:

- fmt: `%f`
- max: `90.0`
- maxisvalid: `True`
- min: `-90.0`
- minisvalid: `True`

<a id="dm-type-geo-bbox"></a>

### geo:bbox

A geospatial bounding box in (xmin, xmax, ymin, ymax) format.
The `geo:bbox` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields:

```json
[
  [
    "xmin",
    "geo:longitude"
  ],
  [
    "xmax",
    "geo:longitude"
  ],
  [
    "ymin",
    "geo:latitude"
  ],
  [
    "ymax",
    "geo:latitude"
  ]
]
```

- sepr: `,`

<a id="dm-type-geo-altitude"></a>

### geo:altitude

A negative or positive offset from Mean Sea Level (6,371.0088km from Earth's core).
The `geo:altitude` type is derived from the base type: [`phys:distance`](#dm-type-phys-distance).

An example of `geo:altitude`:

- `10 km`

This type has the following options set:

- baseoff: `6371008800`
- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-gov-cn-icp"></a>

### gov:cn:icp

A Chinese Internet Content Provider ID.
The `gov:cn:icp` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^(皖|京|渝|闽|粤|甘|桂|黔|豫|鄂|冀|琼|港|黑|湘|吉|苏|赣|辽|澳|蒙|宁|青|川|鲁|沪|陕|晋|津|台|新|藏|滇|浙)ICP(备|证)[0-9]{8}号$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-gov-cn-mucd"></a>

### gov:cn:mucd

A Chinese PLA MUCD.
The `gov:cn:mucd` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{5}部队$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-iso-oid"></a>

### iso:oid

An ISO Object Identifier string.
The `iso:oid` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^([0-2])((\.0)|(\.[1-9][0-9]*))*$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-iso-3166-alpha2"></a>

### iso:3166:alpha2

An ISO 3166 Alpha-2 country code.
The `iso:3166:alpha2` type is derived from the base type: [`str`](#dm-type-str).

An example of `iso:3166:alpha2`:

- `us`

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^[a-z0-9]{2}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-iso-3166-alpha3"></a>

### iso:3166:alpha3

An ISO 3166 Alpha-3 country code.
The `iso:3166:alpha3` type is derived from the base type: [`str`](#dm-type-str).

An example of `iso:3166:alpha3`:

- `usa`

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^[a-z0-9]{3}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-iso-3166-numeric3"></a>

### iso:3166:numeric3

An ISO 3166 Numeric-3 country code.
The `iso:3166:numeric3` type is derived from the base type: [`str`](#dm-type-str).

An example of `iso:3166:numeric3`:

- `840`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{3}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-gov-intl-un-m49"></a>

### gov:intl:un:m49

UN M49 Numeric Country Code.
The `gov:intl:un:m49` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `999`
- min: `1`
- signed: `True`
- size: `8`

<a id="dm-type-gov-us-ssn"></a>

### gov:us:ssn

A US Social Security Number (SSN).
The `gov:us:ssn` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{3}-[0-9]{2}-[0-9]{4}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-gov-us-zip"></a>

### gov:us:zip

A US Postal Zip Code.
The `gov:us:zip` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `99999`
- min: `0`
- signed: `True`
- size: `8`

<a id="dm-type-gov-us-cage"></a>

### gov:us:cage

A Commercial and Government Entity (CAGE) code.
The `gov:us:cage` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ind-name"></a>

### ind:name

A name of an industry.
The `ind:name` type is derived from the base type: [`base:name`](#dm-type-base-name).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ind-industry-id"></a>

### ind:industry:id

An ID given to an industry.
The `ind:industry:id` type is derived from the base type: [`poly`](#dm-type-poly).

This type has the following options set:

- docs: `None`
- interfaces: `None`
- types: `('ou:naics', 'ou:sic', 'ou:isic', 'base:id')`

<a id="dm-type-ind-industry"></a>

### ind:industry

An industry.
The `ind:industry` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:reported', {})`
- `('risk:targetable', {})`

<a id="dm-type-ind-industry-type-taxonomy"></a>

### ind:industry:type:taxonomy

A hierarchical taxonomy of industry types.
The `ind:industry:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-cidr"></a>

### inet:cidr

An IPv4 or IPv6 address range aligned to a CIDR boundary.
The `inet:cidr` type is derived from the base type: [`inet:net`](#dm-type-inet-net).

An example of `inet:cidr`:

- `1.2.3.0/24`

This type has the following options set:

- cidr: `True`
- type: `('inet:ip', {})`

<a id="dm-type-inet-ipv4"></a>

### inet:ipv4

An IPv4 address.
The `inet:ipv4` type is derived from the base type: [`inet:ip`](#dm-type-inet-ip).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`
- `('geo:locatable', {})`

An example of `inet:ipv4`:

- `1.2.3.4`

This type has the following options set:

- version: `4`

<a id="dm-type-inet-ipv6"></a>

### inet:ipv6

An IPv6 address.
The `inet:ipv6` type is derived from the base type: [`inet:ip`](#dm-type-inet-ip).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`
- `('geo:locatable', {})`

An example of `inet:ipv6`:

- `1.2.3.4`

This type has the following options set:

- version: `6`

<a id="dm-type-inet-asn"></a>

### inet:asn

An Autonomous System Number (ASN).
The `inet:asn` type is derived from the base type: [`int`](#dm-type-int).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-inet-proto"></a>

### inet:proto

A network protocol name.
The `inet:proto` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^[a-z0-9+-]+$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-asnip"></a>

### inet:asnip

A historical record of an IP address being assigned to an AS.
The `inet:asnip` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `inet:asnip`:

- `(54959, 1.2.3.4)`

This type has the following options set:

- fields: `(('asn', 'inet:asn'), ('ip', 'inet:ip'))`
- sepr: `None`

<a id="dm-type-inet-asnet"></a>

### inet:asnet

An Autonomous System Number (ASN) and its associated IP address range.
The `inet:asnet` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `inet:asnet`:

- `(54959, (1.2.3.4, 1.2.3.20))`

This type has the following options set:

- fields: `(('asn', 'inet:asn'), ('net', 'inet:net'))`
- sepr: `None`

<a id="dm-type-inet-client"></a>

### inet:client

A network client address.
The `inet:client` type is derived from the base type: [`inet:sockaddr`](#dm-type-inet-sockaddr).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('risk:exploitable', {})`

An example of `inet:client`:

- `tcp://1.2.3.4:80`

This type has the following options set:

- defport: `None`
- defproto: `tcp`
- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-download"></a>

### inet:download

An instance of a file downloaded from a server.
The `inet:download` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-inet-flow"></a>

### inet:flow

A network connection between a client and server.
The `inet:flow` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:activity', {})`
- `('inet:proto:link', {})`

<a id="dm-type-inet-tunnel-type-taxonomy"></a>

### inet:tunnel:type:taxonomy

A hierarchical taxonomy of tunnel types.
The `inet:tunnel:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-tunnel"></a>

### inet:tunnel

A specific sequence of hosts forwarding connections such as a VPN or proxy.
The `inet:tunnel` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`
- `('meta:observable', {})`

<a id="dm-type-inet-egress"></a>

### inet:egress

A host using a specific network egress client address.
The `inet:egress` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`

<a id="dm-type-inet-data-link"></a>

### inet:data:link

A data link between two network interface cards.
The `inet:data:link` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:activity', {})`

<a id="dm-type-inet-wifi-link"></a>

### inet:wifi:link

A wireless link between two Wi-Fi network interface cards.
The `inet:wifi:link` type is derived from the base type: [`inet:data:link`](#dm-type-inet-data-link).

This type implements the following interfaces:

- `('base:activity', {})`

<a id="dm-type-inet-http-header-name"></a>

### inet:http:header:name

The name of an HTTP header.
The `inet:http:header:name` type is derived from the base type: [`str:lower`](#dm-type-str-lower).

An example of `inet:http:header:name`:

- `host`

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-http-header"></a>

### inet:http:header

An HTTP protocol header key/value.
The `inet:http:header` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('name', 'inet:http:header:name'), ('value', 'str'))`
- sepr: `None`

<a id="dm-type-inet-http-request-header"></a>

### inet:http:request:header

An HTTP request header.
The `inet:http:request:header` type is derived from the base type: [`inet:http:header`](#dm-type-inet-http-header).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('name', 'inet:http:header:name'), ('value', 'str'))`
- sepr: `None`

<a id="dm-type-inet-http-response-header"></a>

### inet:http:response:header

An HTTP response header.
The `inet:http:response:header` type is derived from the base type: [`inet:http:header`](#dm-type-inet-http-header).

This type implements the following interfaces:

- `('meta:observable', {'template': {'title': 'HTTP response header'}})`

This type has the following options set:

- fields: `(('name', 'inet:http:header:name'), ('value', 'str'))`
- sepr: `None`

<a id="dm-type-inet-http-param"></a>

### inet:http:param

An HTTP request path query parameter.
The `inet:http:param` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('name', 'str'), ('value', 'str'))`
- sepr: `None`

<a id="dm-type-inet-http-session"></a>

### inet:http:session

An HTTP session.
The `inet:http:session` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:session', {})`

<a id="dm-type-inet-http-request"></a>

### inet:http:request

A single HTTP request.
The `inet:http:request` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:request', {})`

<a id="dm-type-inet-http-response"></a>

### inet:http:response

An HTTP response returned by a server.
The `inet:http:response` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:response', {})`

<a id="dm-type-inet-hyperlink"></a>

### inet:hyperlink

A URL link embedded in a message.
The `inet:hyperlink` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-inet-mac"></a>

### inet:mac

A 48-bit Media Access Control (MAC) address.
The `inet:mac` type is derived from the base type: [`str`](#dm-type-str).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `inet:mac`:

- `aa:bb:cc:dd:ee:ff`

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-port"></a>

### inet:port

A network port.
The `inet:port` type is derived from the base type: [`int`](#dm-type-int).

An example of `inet:port`:

- `80`

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `65535`
- min: `0`
- signed: `True`
- size: `8`

<a id="dm-type-inet-server"></a>

### inet:server

A network server address.
The `inet:server` type is derived from the base type: [`inet:sockaddr`](#dm-type-inet-sockaddr).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('risk:exploitable', {})`

An example of `inet:server`:

- `tcp://1.2.3.4:80`

This type has the following options set:

- defport: `None`
- defproto: `tcp`
- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-banner"></a>

### inet:banner

A network protocol banner string presented by a server.
The `inet:banner` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`

<a id="dm-type-inet-serverfile"></a>

### inet:serverfile

A file hosted by a server.
The `inet:serverfile` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('server', 'inet:server'), ('file', 'file:bytes'))`
- sepr: `None`

<a id="dm-type-inet-urlfile"></a>

### inet:urlfile

A file hosted at a specific Universal Resource Locator (URL).
The `inet:urlfile` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`

This type has the following options set:

- fields: `(('url', 'inet:url'), ('file', 'file:bytes'))`
- sepr: `None`

<a id="dm-type-inet-url-redir"></a>

### inet:url:redir

A URL that redirects to another URL, such as via a URL shortening service or an HTTP 302 response.
The `inet:url:redir` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`

An example of `inet:url:redir`:

- `(http://foo.com/,http://bar.com/)`

This type has the following options set:

- fields: `(('source', 'inet:url'), ('target', 'inet:url'))`
- sepr: `None`

<a id="dm-type-inet-url-mirror"></a>

### inet:url:mirror

A URL mirror site.
The `inet:url:mirror` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('of', 'inet:url'), ('at', 'inet:url'))`
- sepr: `None`

<a id="dm-type-inet-search-query"></a>

### inet:search:query

An instance of a search query issued to a search engine.
The `inet:search:query` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:action', {})`

<a id="dm-type-inet-search-result"></a>

### inet:search:result

A single result from a web search.
The `inet:search:result` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-inet-whois-record"></a>

### inet:whois:record

An FQDN whois registration record.
The `inet:whois:record` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`

<a id="dm-type-inet-whois-ipquery"></a>

### inet:whois:ipquery

Query details used to retrieve an IP record.
The `inet:whois:ipquery` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-inet-whois-iprecord"></a>

### inet:whois:iprecord

An IPv4/IPv6 block registration record.
The `inet:whois:iprecord` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`

<a id="dm-type-inet-wifi-ap"></a>

### inet:wifi:ap

A wireless access point, typically defined by the combination of an SSID and a MAC address.
The `inet:wifi:ap` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:havable', {})`
- `('geo:locatable', {})`
- `('meta:observable', {})`

<a id="dm-type-inet-wifi-ssid"></a>

### inet:wifi:ssid

A Wi-Fi service set identifier (SSID) name.
The `inet:wifi:ssid` type is derived from the base type: [`str`](#dm-type-str).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `inet:wifi:ssid`:

- `The Vertex Project`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `False`
- upper: `False`

<a id="dm-type-inet-wifi-session"></a>

### inet:wifi:session

A Wi-Fi association session between a client and an access point.
The `inet:wifi:session` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:session', {})`

<a id="dm-type-inet-wifi-login"></a>

### inet:wifi:login

An authentication event for a Wi-Fi network.
The `inet:wifi:login` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:login', {})`

<a id="dm-type-inet-email-message"></a>

### inet:email:message

An individual email message delivered to an inbox.
The `inet:email:message` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`

<a id="dm-type-inet-email-header-name"></a>

### inet:email:header:name

An email header name.
The `inet:email:header:name` type is derived from the base type: [`str`](#dm-type-str).

An example of `inet:email:header:name`:

- `subject`

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-email-header"></a>

### inet:email:header

A unique email message header.
The `inet:email:header` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`

This type has the following options set:

- fields: `(('name', 'inet:email:header:name'), ('value', 'str'))`
- sepr: `None`

<a id="dm-type-inet-tls-jarmhash"></a>

### inet:tls:jarmhash

A TLS JARM fingerprint hash.
The `inet:tls:jarmhash` type is derived from the base type: [`str`](#dm-type-str).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^(?<ciphers>[0-9a-f]{30})(?<extensions>[0-9a-f]{32})$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-tls-jarmsample"></a>

### inet:tls:jarmsample

A JARM hash sample taken from a server.
The `inet:tls:jarmsample` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('server', 'inet:server'), ('jarmhash', 'inet:tls:jarmhash'))`
- sepr: `None`

<a id="dm-type-inet-service-platform-type-taxonomy"></a>

### inet:service:platform:type:taxonomy

A service platform type taxonomy.
The `inet:service:platform:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-service-platform"></a>

### inet:service:platform

A network platform which provides services.
The `inet:service:platform` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`
- `('risk:targetable', {})`
- `('risk:exploitable', {})`

<a id="dm-type-inet-service-agent"></a>

### inet:service:agent

An instance of a deployed agent or software integration which is part of the service architecture.
The `inet:service:agent` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:actor', {})`
- `('inet:service:object', {})`

<a id="dm-type-inet-service-account"></a>

### inet:service:account

An account within a service platform. Accounts may be instance specific.
The `inet:service:account` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:actor', {})`
- `('risk:targetable', {})`
- `('entity:resolvable', {})`
- `('econ:pay:instrument', {})`
- `('inet:service:subscriber', {})`

<a id="dm-type-inet-service-relationship-type-taxonomy"></a>

### inet:service:relationship:type:taxonomy

A service object relationship type taxonomy.
The `inet:service:relationship:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-service-relationship"></a>

### inet:service:relationship

A relationship between two service objects.
The `inet:service:relationship` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-permission-type-taxonomy"></a>

### inet:service:permission:type:taxonomy

A hierarchical taxonomy of service permission types.
The `inet:service:permission:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-service-permission"></a>

### inet:service:permission

A permission which may be granted to a service account or role.
The `inet:service:permission` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-rule"></a>

### inet:service:rule

A rule which grants or denies a permission to a service account or role.
The `inet:service:rule` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-error"></a>

### inet:service:error

An error generated by a service platform.
The `inet:service:error` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-inet-service-login"></a>

### inet:service:login

A login event for a service account.
The `inet:service:login` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:login', {})`
- `('inet:service:action:authorized', {})`

<a id="dm-type-inet-service-login-method-taxonomy"></a>

### inet:service:login:method:taxonomy

A hierarchical taxonomy of service login methods.
The `inet:service:login:method:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-service-session"></a>

### inet:service:session

An authenticated session.
The `inet:service:session` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:session', {})`
- `('inet:service:object', {})`

<a id="dm-type-inet-service-role"></a>

### inet:service:role

A role which contains member accounts.
The `inet:service:role` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`
- `('inet:service:joinable', {})`

<a id="dm-type-inet-service-channel"></a>

### inet:service:channel

A channel used to distribute messages.
The `inet:service:channel` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`
- `('inet:service:joinable', {})`

<a id="dm-type-inet-service-member"></a>

### inet:service:member

Represents a service account being a member of a channel or group.
The `inet:service:member` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-message"></a>

### inet:service:message

A message or post created by an account.
The `inet:service:message` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('inet:service:action', {})`

<a id="dm-type-inet-service-message-type-taxonomy"></a>

### inet:service:message:type:taxonomy

A hierarchical taxonomy of message types.
The `inet:service:message:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-service-comment"></a>

### inet:service:comment

A comment about a node created by an account.
The `inet:service:comment` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-label"></a>

### inet:service:label

A label which may be applied to objects within a service platform.
The `inet:service:label` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-labeled"></a>

### inet:service:labeled

Records a label applied to an object within a service platform.
The `inet:service:labeled` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-emote"></a>

### inet:service:emote

An emote or reaction by an account.
The `inet:service:emote` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:action', {})`

<a id="dm-type-inet-service-access-action-taxonomy"></a>

### inet:service:access:action:taxonomy

A hierarchical taxonomy of service actions.
The `inet:service:access:action:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-service-access"></a>

### inet:service:access

Represents a user access request to a service resource.
The `inet:service:access` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:action:authorized', {})`

<a id="dm-type-inet-service-tenant"></a>

### inet:service:tenant

A tenant which groups accounts and instances.
The `inet:service:tenant` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:subscriber', {})`

<a id="dm-type-inet-service-subscription-level-taxonomy"></a>

### inet:service:subscription:level:taxonomy

A taxonomy of platform specific subscription levels.
The `inet:service:subscription:level:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-service-subscription"></a>

### inet:service:subscription

A subscription to a service platform or instance.
The `inet:service:subscription` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-resource-type-taxonomy"></a>

### inet:service:resource:type:taxonomy

A hierarchical taxonomy of service resource types.
The `inet:service:resource:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-service-resource"></a>

### inet:service:resource

A generic resource provided by the service architecture.
The `inet:service:resource` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-bucket"></a>

### inet:service:bucket

A file/blob storage object within a service architecture.
The `inet:service:bucket` type is derived from the base type: [`inet:service:resource`](#dm-type-inet-service-resource).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-service-bucket-item"></a>

### inet:service:bucket:item

An individual file stored within a bucket.
The `inet:service:bucket:item` type is derived from the base type: [`inet:service:resource`](#dm-type-inet-service-resource).

This type implements the following interfaces:

- `('inet:service:object', {})`

<a id="dm-type-inet-rdp-handshake"></a>

### inet:rdp:handshake

An instance of an RDP handshake between a client and server.
The `inet:rdp:handshake` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:request', {})`

<a id="dm-type-inet-ssh-handshake"></a>

### inet:ssh:handshake

An instance of an SSH handshake between a client and server.
The `inet:ssh:handshake` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:request', {})`

<a id="dm-type-inet-tls-handshake"></a>

### inet:tls:handshake

An instance of a TLS handshake between a client and server.
The `inet:tls:handshake` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:request', {})`

<a id="dm-type-inet-tls-ja4"></a>

### inet:tls:ja4

A JA4 TLS client fingerprint.
The `inet:tls:ja4` type is derived from the base type: [`str`](#dm-type-str).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^([tqd])([sd\d]\d)([di])(\d{2})(\d{2})([a-zA-Z0-9]{2})_([0-9a-f]{12})_([0-9a-f]{12})$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-tls-ja4s"></a>

### inet:tls:ja4s

A JA4S TLS server fingerprint.
The `inet:tls:ja4s` type is derived from the base type: [`str`](#dm-type-str).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^([tq])([sd\d]\d)(\d{2})([a-zA-Z0-9]{2})_([0-9a-f]{4})_([0-9a-f]{12})$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-tls-ja4-sample"></a>

### inet:tls:ja4:sample

A JA4 TLS client fingerprint used by a client.
The `inet:tls:ja4:sample` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('client', 'inet:client'), ('ja4', 'inet:tls:ja4'))`
- sepr: `None`

<a id="dm-type-inet-tls-ja4s-sample"></a>

### inet:tls:ja4s:sample

A JA4S TLS server fingerprint used by a server.
The `inet:tls:ja4s:sample` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('server', 'inet:server'), ('ja4s', 'inet:tls:ja4s'))`
- sepr: `None`

<a id="dm-type-inet-tls-ja3s-sample"></a>

### inet:tls:ja3s:sample

A JA3 sample taken from a server.
The `inet:tls:ja3s:sample` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('server', 'inet:server'), ('ja3s', 'crypto:hash:md5'))`
- sepr: `None`

<a id="dm-type-inet-tls-ja3-sample"></a>

### inet:tls:ja3:sample

A JA3 sample taken from a client.
The `inet:tls:ja3:sample` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('client', 'inet:client'), ('ja3', 'crypto:hash:md5'))`
- sepr: `None`

<a id="dm-type-inet-tls-servercert"></a>

### inet:tls:servercert

An x509 certificate sent by a server for TLS.
The `inet:tls:servercert` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `inet:tls:servercert`:

- `(1.2.3.4:443, ({"$as": "crypto:x509:cert", "sha256": "0dc8e08cc5811311726a3313904a94747fbff36b6a2bde642dc4a1d9b28b26cf"}))`

This type has the following options set:

- fields: `(('server', 'inet:server'), ('cert', 'crypto:x509:cert'))`
- sepr: `None`

<a id="dm-type-inet-tls-clientcert"></a>

### inet:tls:clientcert

An x509 certificate sent by a client for TLS.
The `inet:tls:clientcert` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `inet:tls:clientcert`:

- `(1.2.3.4:443, ({"$as": "crypto:x509:cert", "sha256": "0dc8e08cc5811311726a3313904a94747fbff36b6a2bde642dc4a1d9b28b26cf"}))`

This type has the following options set:

- fields: `(('client', 'inet:client'), ('cert', 'crypto:x509:cert'))`
- sepr: `None`

<a id="dm-type-inet-ipscope"></a>

### inet:ipscope

An IP address scope.
The `inet:ipscope` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- enums:

| valu |
|------|
| reserved |
| interface-local |
| link-local |
| realm-local |
| admin-local |
| site-local |
| organization-local |
| global |
| unassigned |

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-ipversion"></a>

### inet:ipversion

An IP protocol version.
The `inet:ipversion` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 4 | 4 |
| 6 | 6 |

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-inet-jarm-ciphers"></a>

### inet:jarm:ciphers

A JARM cipher string.
The `inet:jarm:ciphers` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9a-f]{30}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-jarm-extensions"></a>

### inet:jarm:extensions

A JARM extensions string.
The `inet:jarm:extensions` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9a-f]{32}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-inet-svcaccess-type"></a>

### inet:svcaccess:type

A service access type.
The `inet:svcaccess:type` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 10 | create |
| 30 | read |
| 40 | update |
| 50 | delete |
| 60 | list |
| 70 | execute |

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-it-hostname"></a>

### it:hostname

The name of a host or system.
The `it:hostname` type is derived from the base type: [`base:name`](#dm-type-base-name).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-host"></a>

### it:host

A GUID that represents a host or system.
The `it:host` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:component', {})`
- `('risk:targetable', {})`

<a id="dm-type-it-physical-host"></a>

### it:physical:host

A host which consists of dedicated physical hardware.
The `it:physical:host` type is derived from the base type: [`it:host`](#dm-type-it-host).

This type implements the following interfaces:

- `('it:component', {})`
- `('risk:targetable', {})`
- `('phys:object', {})`
- `('biz:manufactured', {})`

<a id="dm-type-it-virtual-host"></a>

### it:virtual:host

A host which runs as a virtualized instance.
The `it:virtual:host` type is derived from the base type: [`it:host`](#dm-type-it-host).

This type implements the following interfaces:

- `('it:component', {})`
- `('risk:targetable', {})`

<a id="dm-type-it-cloud-host"></a>

### it:cloud:host

A virtual host instance which runs within a cloud service platform.
The `it:cloud:host` type is derived from the base type: [`it:virtual:host`](#dm-type-it-virtual-host).

This type implements the following interfaces:

- `('it:component', {})`
- `('risk:targetable', {})`
- `('inet:service:object', {})`

<a id="dm-type-it-log-event-type-taxonomy"></a>

### it:log:event:type:taxonomy

A hierarchical taxonomy of log event types.
The `it:log:event:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-log-event"></a>

### it:log:event

A GUID representing an individual log event.
The `it:log:event` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-log-severity"></a>

### it:log:severity

A log severity level.
The `it:log:severity` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 10 | debug |
| 20 | info |
| 30 | notice |
| 40 | warning |
| 50 | err |
| 60 | crit |
| 70 | alert |
| 80 | emerg |

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-it-network"></a>

### it:network

A GUID that represents a logical network.
The `it:network` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:havable', {})`

<a id="dm-type-it-network-type-taxonomy"></a>

### it:network:type:taxonomy

A hierarchical taxonomy of network types.
The `it:network:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-host-account"></a>

### it:host:account

A local account on a host.
The `it:host:account` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-host-posix-account"></a>

### it:host:posix:account

A POSIX account on a host.
The `it:host:posix:account` type is derived from the base type: [`it:host:account`](#dm-type-it-host-account).

<a id="dm-type-it-host-windows-account"></a>

### it:host:windows:account

A Windows account on a host.
The `it:host:windows:account` type is derived from the base type: [`it:host:account`](#dm-type-it-host-account).

<a id="dm-type-it-host-group"></a>

### it:host:group

A local group on a host.
The `it:host:group` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-host-posix-group"></a>

### it:host:posix:group

A POSIX group on a host.
The `it:host:posix:group` type is derived from the base type: [`it:host:group`](#dm-type-it-host-group).

<a id="dm-type-it-host-windows-group"></a>

### it:host:windows:group

A Windows group on a host.
The `it:host:windows:group` type is derived from the base type: [`it:host:group`](#dm-type-it-host-group).

<a id="dm-type-it-host-group-membership"></a>

### it:host:group:membership

A host account or group being a member of a host group during a period.
The `it:host:group:membership` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-host-login"></a>

### it:host:login

A login event on a host.
The `it:host:login` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:login', {})`

<a id="dm-type-it-host-session"></a>

### it:host:session

An authenticated session on a host.
The `it:host:session` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:proto:session', {})`

<a id="dm-type-it-host-hosted-url"></a>

### it:host:hosted:url

A URL hosted on or served by a specific host.
The `it:host:hosted:url` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- fields: `(('host', 'it:host'), ('url', 'inet:url'))`
- sepr: `None`

<a id="dm-type-it-exec-screenshot"></a>

### it:exec:screenshot

A screenshot of a host.
The `it:exec:screenshot` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-host-telem"></a>

### it:host:telem

A telemetry measurement taken from a host.
The `it:host:telem` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`
- `('geo:locatable', {})`

<a id="dm-type-it-sec-cve"></a>

### it:sec:cve

A vulnerability as designated by a Common Vulnerabilities and Exposures (CVE) number.
The `it:sec:cve` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `it:sec:cve`:

- `CVE-2012-0158`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `(?i)^CVE-[0-9]{4}-[0-9]{4,}$`
- replace: `(('‑', '-'), ('‒', '-'), ('–', '-'), ('—', '-'))`
- strip: `True`
- upper: `True`

<a id="dm-type-it-sec-cwe"></a>

### it:sec:cwe

NIST NVD Common Weaknesses Enumeration Specification.
The `it:sec:cwe` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `it:sec:cwe`:

- `CWE-120`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^CWE-[0-9]{1,8}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-sec-tlp"></a>

### it:sec:tlp

The US CISA Traffic-Light-Protocol used to designate information sharing boundaries.
The `it:sec:tlp` type is derived from the base type: [`int`](#dm-type-int).

An example of `it:sec:tlp`:

- `green`

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 10 | clear |
| 20 | green |
| 30 | amber |
| 40 | amber-strict |
| 50 | red |

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-it-sec-metrics"></a>

### it:sec:metrics

A node used to track metrics of an organization's infosec program.
The `it:sec:metrics` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-sec-vuln-scan"></a>

### it:sec:vuln:scan

An instance of running a vulnerability scan.
The `it:sec:vuln:scan` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-sec-vuln-scan-result"></a>

### it:sec:vuln:scan:result

A vulnerability scan result for an asset.
The `it:sec:vuln:scan:result` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-mitre-attack-group-id"></a>

### it:mitre:attack:group:id

A MITRE ATT&CK Group ID.
The `it:mitre:attack:group:id` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`

An example of `it:mitre:attack:group:id`:

- `G0100`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^G[0-9]{4}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-mitre-attack-tactic-id"></a>

### it:mitre:attack:tactic:id

A MITRE ATT&CK Tactic ID.
The `it:mitre:attack:tactic:id` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `it:mitre:attack:tactic:id`:

- `TA0040`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^TA[0-9]{4}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-mitre-attack-technique-id"></a>

### it:mitre:attack:technique:id

A MITRE ATT&CK Technique ID.
The `it:mitre:attack:technique:id` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `it:mitre:attack:technique:id`:

- `T1548`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^T[0-9]{4}(\.[0-9]{3})?$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-mitre-attack-mitigation-id"></a>

### it:mitre:attack:mitigation:id

A MITRE ATT&CK Mitigation ID.
The `it:mitre:attack:mitigation:id` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `it:mitre:attack:mitigation:id`:

- `M1036`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^M[0-9]{4}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-mitre-attack-software-id"></a>

### it:mitre:attack:software:id

A MITRE ATT&CK Software ID.
The `it:mitre:attack:software:id` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `it:mitre:attack:software:id`:

- `S0154`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^S[0-9]{4}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-mitre-attack-campaign-id"></a>

### it:mitre:attack:campaign:id

A MITRE ATT&CK Campaign ID.
The `it:mitre:attack:campaign:id` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `it:mitre:attack:campaign:id`:

- `C0028`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^C[0-9]{4}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-dev-function"></a>

### it:dev:function

A function defined by code.
The `it:dev:function` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-dev-function-sample"></a>

### it:dev:function:sample

An instance of a function in an executable.
The `it:dev:function:sample` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:mime:meta', {'template': {'metadata': 'function'}})`

<a id="dm-type-it-dev-str"></a>

### it:dev:str

A developer selected string.
The `it:dev:str` type is derived from the base type: [`str`](#dm-type-str).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `False`
- upper: `False`

<a id="dm-type-it-dev-int"></a>

### it:dev:int

A developer selected integer constant.
The `it:dev:int` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-it-os-windows-registry-key"></a>

### it:os:windows:registry:key

A Windows registry key.
The `it:os:windows:registry:key` type is derived from the base type: [`str`](#dm-type-str).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `it:os:windows:registry:key`:

- `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-os-windows-registry-entry"></a>

### it:os:windows:registry:entry

A Windows registry key, name, and value.
The `it:os:windows:registry:entry` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`

<a id="dm-type-it-dev-repo-type-taxonomy"></a>

### it:dev:repo:type:taxonomy

A hierarchical taxonomy of repository types.
The `it:dev:repo:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-lifespan"></a>

### it:lifespan

An interval representing the lifespan of an object, from creation to removal.
The `it:lifespan` type is derived from the base type: [`ival`](#dm-type-ival).

This type has the following options set:

- names: `{'min': 'created', 'max': 'removed'}`
- precision: `microsecond`

<a id="dm-type-it-dev-repo"></a>

### it:dev:repo

A version control system instance.
The `it:dev:repo` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {'template': {'service:base': 'repository'}})`

<a id="dm-type-it-dev-repo-remote"></a>

### it:dev:repo:remote

A remote repo that is tracked for changes/branches/etc.
The `it:dev:repo:remote` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-dev-repo-branch"></a>

### it:dev:repo:branch

A branch in a version control system instance.
The `it:dev:repo:branch` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {'template': {'service:base': 'repository branch'}})`

<a id="dm-type-it-dev-repo-commit"></a>

### it:dev:repo:commit

A commit to a repository.
The `it:dev:repo:commit` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {'template': {'service:base': 'repository commit'}})`

<a id="dm-type-it-dev-repo-diff"></a>

### it:dev:repo:diff

A diff of a file being applied in a single commit.
The `it:dev:repo:diff` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('inet:service:commentable', {})`

<a id="dm-type-it-dev-repo-entry"></a>

### it:dev:repo:entry

A file included in a repository.
The `it:dev:repo:entry` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`

<a id="dm-type-it-dev-repo-issue"></a>

### it:dev:repo:issue

An issue raised in a repository.
The `it:dev:repo:issue` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {'template': {'service:base': 'repository issue'}})`
- `('meta:task', {})`
- `('inet:service:labelable', {})`
- `('inet:service:commentable', {})`

<a id="dm-type-it-software"></a>

### it:software

A software product, tool, or script.
The `it:software` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:reported', {})`
- `('doc:authorable', {})`
- `('meta:observable', {})`
- `('risk:exploitable', {})`

<a id="dm-type-it-softwarename"></a>

### it:softwarename

The name of a software product or tool.
The `it:softwarename` type is derived from the base type: [`base:name`](#dm-type-base-name).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-software-type-taxonomy"></a>

### it:software:type:taxonomy

A hierarchical taxonomy of software types.
The `it:software:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-softid"></a>

### it:softid

An identifier issued to a given host by a specific software application.
The `it:softid` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`

<a id="dm-type-it-hardware"></a>

### it:hardware

A specification for a piece of IT hardware.
The `it:hardware` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:observable', {})`
- `('biz:manufactured', {})`
- `('risk:exploitable', {})`

<a id="dm-type-it-host-component"></a>

### it:host:component

Hardware components which are part of a host.
The `it:host:component` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-installed"></a>

### it:installed

The installation of a component or software on a host component.
The `it:installed` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-it-nic"></a>

### it:nic

A Network Interface Card (NIC).
The `it:nic` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:component', {})`

<a id="dm-type-it-wifi-nic"></a>

### it:wifi:nic

A wireless Network Interface Card (NIC).
The `it:wifi:nic` type is derived from the base type: [`it:nic`](#dm-type-it-nic).

This type implements the following interfaces:

- `('it:component', {})`

<a id="dm-type-it-sim-slot"></a>

### it:sim:slot

A SIM slot.
The `it:sim:slot` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:component', {})`

<a id="dm-type-it-sim-card"></a>

### it:sim:card

A SIM card.
The `it:sim:card` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:component', {})`

<a id="dm-type-it-hardware-type-taxonomy"></a>

### it:hardware:type:taxonomy

A hierarchical taxonomy of IT hardware types.
The `it:hardware:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-adid"></a>

### it:adid

An advertising identification string.
The `it:adid` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('entity:identifier', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-os-windows-service"></a>

### it:os:windows:service

A Microsoft Windows service configuration on a host.
The `it:os:windows:service` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:activity', {})`

<a id="dm-type-it-exec-windows-service-add"></a>

### it:exec:windows:service:add

An event where a Microsoft Windows service configuration was added to a host.
The `it:exec:windows:service:add` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-windows-service-del"></a>

### it:exec:windows:service:del

An event where a Microsoft Windows service configuration was removed from a host.
The `it:exec:windows:service:del` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-os-posix-id"></a>

### it:os:posix:id

A POSIX user or group ID.
The `it:os:posix:id` type is derived from the base type: [`uint32`](#dm-type-uint32).

An example of `it:os:posix:id`:

- `1001`

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `False`
- size: `4`

<a id="dm-type-it-os-posix-cron"></a>

### it:os:posix:cron

A cron job entry configured on a host.
The `it:os:posix:cron` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('meta:usable', {})`
- `('base:activity', {})`

<a id="dm-type-it-os-windows-sid"></a>

### it:os:windows:sid

A Microsoft Windows Security Identifier.
The `it:os:windows:sid` type is derived from the base type: [`str`](#dm-type-str).

An example of `it:os:windows:sid`:

- `S-1-5-21-1220945662-1202665555-839525555-5555`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^S-1-(?:\d{1,10}|0x[0-9a-fA-F]{12})(?:-(?:\d+|0x[0-9a-fA-F]{2,}))*$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-os-android-perm"></a>

### it:os:android:perm

An android permission string.
The `it:os:android:perm` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-os-android-intent"></a>

### it:os:android:intent

An android intent string.
The `it:os:android:intent` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-os-android-reqperm"></a>

### it:os:android:reqperm

The given software requests the android permission.
The `it:os:android:reqperm` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('app', 'it:software'), ('perm', 'it:os:android:perm'))`
- sepr: `None`

<a id="dm-type-it-os-android-ilisten"></a>

### it:os:android:ilisten

The given software listens for an android intent.
The `it:os:android:ilisten` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('app', 'it:software'), ('intent', 'it:os:android:intent'))`
- sepr: `None`

<a id="dm-type-it-os-android-ibroadcast"></a>

### it:os:android:ibroadcast

The given software broadcasts the given Android intent.
The `it:os:android:ibroadcast` type is derived from the base type: [`comp`](#dm-type-comp).

This type has the following options set:

- fields: `(('app', 'it:software'), ('intent', 'it:os:android:intent'))`
- sepr: `None`

<a id="dm-type-it-av-signame"></a>

### it:av:signame

An antivirus signature name.
The `it:av:signame` type is derived from the base type: [`base:name`](#dm-type-base-name).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-av-scan-result"></a>

### it:av:scan:result

The result of running an antivirus scanner.
The `it:av:scan:result` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-av-verdict"></a>

### it:av:verdict

An antivirus scan verdict.
The `it:av:verdict` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:

| int | valu |
|-----|------|
| 10 | benign |
| 20 | unknown |
| 30 | suspicious |
| 40 | malicious |

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-it-av-pattern-type"></a>

### it:av:pattern:type

An antivirus signature pattern type.
The `it:av:pattern:type` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- enums:

| valu |
|------|
| stix |
| pcre |
| sigma |
| snort |
| suricata |
| yara |

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-exec-proc"></a>

### it:exec:proc

A process executing on a host.
The `it:exec:proc` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:activity', {})`

<a id="dm-type-it-exec-proc-create"></a>

### it:exec:proc:create

A process creation event.
The `it:exec:proc:create` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-proc-signal"></a>

### it:exec:proc:signal

An event where a process was sent a POSIX signal.
The `it:exec:proc:signal` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-proc-terminate"></a>

### it:exec:proc:terminate

A process termination event.
The `it:exec:proc:terminate` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-thread"></a>

### it:exec:thread

A thread executing in a process.
The `it:exec:thread` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:activity', {})`

<a id="dm-type-it-exec-thread-create"></a>

### it:exec:thread:create

A thread creation event.
The `it:exec:thread:create` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-thread-terminate"></a>

### it:exec:thread:terminate

A thread termination event.
The `it:exec:thread:terminate` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-lib-load"></a>

### it:exec:lib:load

A library load event in a process.
The `it:exec:lib:load` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-lib-unload"></a>

### it:exec:lib:unload

A library unload event in a process.
The `it:exec:lib:unload` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-mmap-add"></a>

### it:exec:mmap:add

A memory mapped segment located in a process.
The `it:exec:mmap:add` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-cmd"></a>

### it:cmd

A unique command-line string.
The `it:cmd` type is derived from the base type: [`str`](#dm-type-str).

This type implements the following interfaces:

- `('meta:usable', {})`

An example of `it:cmd`:

- `foo.exe --dostuff bar`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-cmd-session"></a>

### it:cmd:session

A command line session with multiple commands run over time.
The `it:cmd:session` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-it-exec-command"></a>

### it:exec:command

A single command executed within a session.
The `it:exec:command` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:activity', {})`

<a id="dm-type-it-query"></a>

### it:query

A unique query string.
The `it:query` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-exec-query"></a>

### it:exec:query

An instance of an executed query.
The `it:exec:query` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-mutex-add"></a>

### it:exec:mutex:add

An event where a process created a mutex.
The `it:exec:mutex:add` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-pipe-add"></a>

### it:exec:pipe:add

A named pipe created by a process at runtime.
The `it:exec:pipe:add` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-fetch"></a>

### it:exec:fetch

An instance of a host requesting a URL using any protocol scheme.
The `it:exec:fetch` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-bind"></a>

### it:exec:bind

An instance of a host binding a listening port.
The `it:exec:bind` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-file-add"></a>

### it:exec:file:add

An instance of a host adding a file to a filesystem.
The `it:exec:file:add` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('it:host:event', {})`

<a id="dm-type-it-exec-file-del"></a>

### it:exec:file:del

An instance of a host deleting a file from a filesystem.
The `it:exec:file:del` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('it:host:event', {})`

<a id="dm-type-it-exec-file-read"></a>

### it:exec:file:read

An instance of a host reading a file from a filesystem.
The `it:exec:file:read` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('it:host:event', {})`

<a id="dm-type-it-exec-file-write"></a>

### it:exec:file:write

An instance of a host writing a file to a filesystem.
The `it:exec:file:write` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('file:entry', {})`
- `('it:host:event', {})`

<a id="dm-type-it-exec-windows-registry-get"></a>

### it:exec:windows:registry:get

An instance of a host getting a registry key.
The `it:exec:windows:registry:get` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-windows-registry-set"></a>

### it:exec:windows:registry:set

An instance of a host creating or setting a registry key.
The `it:exec:windows:registry:set` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-exec-windows-registry-del"></a>

### it:exec:windows:registry:del

An instance of a host deleting a registry key.
The `it:exec:windows:registry:del` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('it:host:event', {})`

<a id="dm-type-it-app-yara-rule"></a>

### it:app:yara:rule

A YARA rule.
The `it:app:yara:rule` type is derived from the base type: [`meta:rule`](#dm-type-meta-rule).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('doc:authorable', {})`
- `('meta:observable', {})`

<a id="dm-type-it-app-yara-target"></a>

### it:app:yara:target

A type which is limited to forms which YARA rules can match.
The `it:app:yara:target` type is derived from the base type: [`poly`](#dm-type-poly).

This type has the following options set:

- docs: `None`
- interfaces: `None`
- types: `('file:bytes', 'it:exec:proc', 'inet:ip', 'inet:fqdn', 'inet:url')`

<a id="dm-type-it-app-yara-matched"></a>

### it:app:yara:matched

An instance of a YARA rule matching a target.
The `it:app:yara:matched` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:matched', {'template': {'rule': 'YARA rule', 'rule:type': 'it:app:yara:rule', 'target:type': 'it:app:yara:target'}})`

<a id="dm-type-it-sec-stix-bundle"></a>

### it:sec:stix:bundle

A STIX bundle.
The `it:sec:stix:bundle` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-sec-stix-confidence"></a>

### it:sec:stix:confidence

A confidence score from STIX.
The `it:sec:stix:confidence` type is derived from the base type: [`int`](#dm-type-int).

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `100`
- min: `0`
- signed: `True`
- size: `8`

<a id="dm-type-it-sec-stix-indicator"></a>

### it:sec:stix:indicator

A STIX indicator pattern.
The `it:sec:stix:indicator` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-app-snort-rule"></a>

### it:app:snort:rule

A snort rule.
The `it:app:snort:rule` type is derived from the base type: [`meta:rule`](#dm-type-meta-rule).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('doc:authorable', {})`
- `('meta:observable', {})`

<a id="dm-type-it-app-snort-matched"></a>

### it:app:snort:matched

An instance of a snort rule hit.
The `it:app:snort:matched` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:matched', {'template': {'rule': 'Snort rule', 'rule:type': 'it:app:snort:rule', 'target:type': 'inet:flow'}})`

<a id="dm-type-it-app-suricata-rule"></a>

### it:app:suricata:rule

A suricata rule.
The `it:app:suricata:rule` type is derived from the base type: [`meta:rule`](#dm-type-meta-rule).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('doc:authorable', {})`
- `('meta:observable', {})`

<a id="dm-type-it-app-suricata-matched"></a>

### it:app:suricata:matched

An instance of a suricata rule hit.
The `it:app:suricata:matched` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:matched', {'template': {'rule': 'Suricata rule', 'rule:type': 'it:app:suricata:rule', 'target:type': 'inet:flow'}})`

<a id="dm-type-it-sec-c2-config"></a>

### it:sec:c2:config

An extracted C2 config from an executable.
The `it:sec:c2:config` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-host-tenancy"></a>

### it:host:tenancy

A time window where a host was a tenant run by another host.
The `it:host:tenancy` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-software-image-type-taxonomy"></a>

### it:software:image:type:taxonomy

A hierarchical taxonomy of software image types.
The `it:software:image:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-it-software-image"></a>

### it:software:image

The base image used to create a container or OS.
The `it:software:image` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('inet:service:object', {'template': {'service:base': 'software image'}})`

<a id="dm-type-it-storage-mount"></a>

### it:storage:mount

A storage volume that has been attached to an image.
The `it:storage:mount` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-storage-volume"></a>

### it:storage:volume

A physical or logical storage volume that can be attached to a physical/virtual machine or container.
The `it:storage:volume` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-it-storage-volume-type-taxonomy"></a>

### it:storage:volume:type:taxonomy

A hierarchical taxonomy of storage volume types.
The `it:storage:volume:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

An example of `it:storage:volume:type:taxonomy`:

- `network.smb`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-lang-phrase"></a>

### lang:phrase

A small group of words which stand together as a concept.
The `lang:phrase` type is derived from the base type: [`text`](#dm-type-text).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `False`
- upper: `False`

<a id="dm-type-lang-idiom"></a>

### lang:idiom

An idiomatic use of a phrase.
The `lang:idiom` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-lang-hashtag"></a>

### lang:hashtag

A hashtag used in written text.
The `lang:hashtag` type is derived from the base type: [`title`](#dm-type-title).

This type implements the following interfaces:

- `('meta:observable', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `^#[^\p{Z}#]+$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-lang-name"></a>

### lang:name

A name used to refer to a language.
The `lang:name` type is derived from the base type: [`base:name`](#dm-type-base-name).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-lang-translation"></a>

### lang:translation

A translation of text from one language to another.
The `lang:translation` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-lang-language"></a>

### lang:language

A specific written or spoken language.
The `lang:language` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('edu:learnable', {})`

<a id="dm-type-phys-lifespan"></a>

### phys:lifespan

An interval representing the lifespan of a physical object, from its creation until it is retired or destroyed.
The `phys:lifespan` type is derived from the base type: [`ival`](#dm-type-ival).

This type has the following options set:

- names: `{'min': 'created', 'max': 'retired'}`
- precision: `microsecond`

<a id="dm-type-mat-item-type-taxonomy"></a>

### mat:item:type:taxonomy

A hierarchical taxonomy of material object types.
The `mat:item:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-mat-spec-type-taxonomy"></a>

### mat:spec:type:taxonomy

A hierarchical taxonomy of material specification types.
The `mat:spec:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-phys-contained-type-taxonomy"></a>

### phys:contained:type:taxonomy

A taxonomy for types of contained relationships.
The `phys:contained:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-phys-contained"></a>

### phys:contained

A relationship in which one physical object contains another.
The `phys:contained` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-mat-item"></a>

### mat:item

A GUID assigned to a material object.
The `mat:item` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('phys:object', {})`

<a id="dm-type-mat-spec"></a>

### mat:spec

A GUID assigned to a material specification.
The `mat:spec` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-phys-mass"></a>

### phys:mass

A mass which converts to grams as a base unit.
The `phys:mass` type is derived from the base type: [`hugenum`](#dm-type-hugenum).

This type has the following options set:

- defunit: `None`
- max: `None`
- maxisvalid: `True`
- min: `None`
- minisvalid: `True`
- modulo: `None`
- units: `{'µg': '0.000001', 'microgram': '0.000001', 'micrograms': '0.000001', 'mg': '0.001', 'milligram': '0.001', 'milligrams': '0.001', 'g': '1', 'grams': '1', 'kg': '1000', 'kilogram': '1000', 'kilograms': '1000', 'lb': '453.592', 'lbs': '453.592', 'pound': '453.592', 'pounds': '453.592', 'stone': '6350.29'}`

<a id="dm-type-phys-volume"></a>

### phys:volume

A volume which converts to milliliters as a base unit.
The `phys:volume` type is derived from the base type: [`hugenum`](#dm-type-hugenum).

An example of `phys:volume`:

- `10 m^3`

This type has the following options set:

- defunit: `None`
- max: `None`
- maxisvalid: `True`
- min: `None`
- minisvalid: `True`
- modulo: `None`
- units: `{'ml': '1', 'milliliter': '1', 'milliliters': '1', 'cl': '10', 'centiliter': '10', 'centiliters': '10', 'dl': '100', 'deciliter': '100', 'deciliters': '100', 'l': '1000', 'liter': '1000', 'liters': '1000', 'kl': '1000000', 'kiloliter': '1000000', 'kiloliters': '1000000', 'mm^3': '0.001', 'cm^3': '1', 'cc': '1', 'dm^3': '1000', 'm^3': '1000000', 'floz': '29.5735', 'pint': '473.176', 'pints': '473.176', 'quart': '946.353', 'quarts': '946.353', 'gal': '3785.41', 'gallon': '3785.41', 'gallons': '3785.41', 'in^3': '16.3871', 'ft^3': '28316.8', 'yd^3': '764555', 'bbl': '158987', 'barrel': '158987', 'barrels': '158987'}`

<a id="dm-type-ou-sic"></a>

### ou:sic

A four digit Standard Industrial Classification (SIC) code.
The `ou:sic` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `ou:sic`:

- `0111`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{4}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-naics"></a>

### ou:naics

North American Industry Classification System (NAICS) codes and prefixes.
The `ou:naics` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `ou:naics`:

- `541715`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[1-9][0-9]{1,5}?$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-isic"></a>

### ou:isic

An International Standard Industrial Classification of All Economic Activities (ISIC) code.
The `ou:isic` type is derived from the base type: [`base:id`](#dm-type-base-id).

An example of `ou:isic`:

- `C1393`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[A-Z]([0-9]{2}[0-9]{0,2})?$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-org"></a>

### ou:org

An organization, such as a company or military unit.
The `ou:org` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('econ:budgetable', {})`
- `('meta:havable', {})`
- `('entity:actor', {})`
- `('entity:multiple', {})`
- `('risk:targetable', {})`
- `('entity:contactable', {})`

<a id="dm-type-ou-team"></a>

### ou:team

A GUID for a team within an organization.
The `ou:team` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ou-org-type-taxonomy"></a>

### ou:org:type:taxonomy

A hierarchical taxonomy of organization types.
The `ou:org:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-asset-type-taxonomy"></a>

### ou:asset:type:taxonomy

An asset type taxonomy.
The `ou:asset:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-asset"></a>

### ou:asset

A node for tracking assets which belong to an organization.
The `ou:asset` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('risk:exploitable', {})`

<a id="dm-type-ou-orgnet"></a>

### ou:orgnet

An IP address block which belongs to an organization.
The `ou:orgnet` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ou-position"></a>

### ou:position

A position within an org which can be organized into an org chart with replaceable contacts.
The `ou:position` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ou-meeting"></a>

### ou:meeting

A meeting.
The `ou:meeting` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('geo:locatable', {})`
- `('meta:recordable', {})`
- `('entity:attendable', {})`
- `('entity:participable', {})`

<a id="dm-type-ou-preso"></a>

### ou:preso

A webinar, conference talk, or other type of presentation.
The `ou:preso` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('ou:promotable', {})`
- `('geo:locatable', {})`
- `('meta:recordable', {})`
- `('entity:attendable', {})`
- `('entity:supportable', {})`
- `('entity:participable', {})`

<a id="dm-type-ou-conference"></a>

### ou:conference

A conference.
The `ou:conference` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('econ:budgetable', {})`
- `('ou:promotable', {})`
- `('geo:locatable', {})`
- `('meta:recordable', {})`
- `('entity:attendable', {})`
- `('entity:supportable', {})`
- `('entity:participable', {})`

<a id="dm-type-ou-event-type-taxonomy"></a>

### ou:event:type:taxonomy

A hierarchical taxonomy of event types.
The `ou:event:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-event"></a>

### ou:event

A generic organized event.
The `ou:event` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('econ:budgetable', {})`
- `('ou:promotable', {})`
- `('geo:locatable', {})`
- `('meta:recordable', {})`
- `('entity:attendable', {})`
- `('entity:supportable', {})`
- `('entity:participable', {})`

<a id="dm-type-ou-contest-type-taxonomy"></a>

### ou:contest:type:taxonomy

A hierarchical taxonomy of contest types.
The `ou:contest:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-contest"></a>

### ou:contest

A competitive event resulting in a ranked set of participants.
The `ou:contest` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('econ:budgetable', {})`
- `('ou:promotable', {})`
- `('geo:locatable', {})`
- `('meta:recordable', {})`
- `('entity:attendable', {})`
- `('entity:supportable', {})`
- `('entity:participable', {})`

<a id="dm-type-ou-contest-result"></a>

### ou:contest:result

The results from a single contest participant.
The `ou:contest:result` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ou-id"></a>

### ou:id

An ID value issued by an organization.
The `ou:id` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('entity:identifier', {})`

<a id="dm-type-ou-id-type-taxonomy"></a>

### ou:id:type:taxonomy

A hierarchical taxonomy of ID types.
The `ou:id:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-id-history"></a>

### ou:id:history

Changes made to an ID over time.
The `ou:id:history` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ou-vitals"></a>

### ou:vitals

Vital statistics about an org for a given time period.
The `ou:vitals` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ou-opening"></a>

### ou:opening

A job/work opening within an org.
The `ou:opening` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ou-job-type-taxonomy"></a>

### ou:job:type:taxonomy

A hierarchical taxonomy of job types.
The `ou:job:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

An example of `ou:job:type:taxonomy`:

- `it.dev.python`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-candidate-method-taxonomy"></a>

### ou:candidate:method:taxonomy

A taxonomy of methods by which a candidate came under consideration.
The `ou:candidate:method:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-candidate"></a>

### ou:candidate

A candidate being considered for a role within an organization.
The `ou:candidate` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ou-candidate-referral"></a>

### ou:candidate:referral

A candidate being referred by a contact.
The `ou:candidate:referral` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ou-employment-type-taxonomy"></a>

### ou:employment:type:taxonomy

A hierarchical taxonomy of employment types.
The `ou:employment:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

An example of `ou:employment:type:taxonomy`:

- `fulltime.salary`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ou-enacted"></a>

### ou:enacted

An organization enacting a document.
The `ou:enacted` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:task', {})`

<a id="dm-type-edu-course"></a>

### edu:course

A course of study taught by an org.
The `edu:course` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:authorable', {})`

<a id="dm-type-edu-class"></a>

### edu:class

An instance of an edu:course taught at a given time.
The `edu:class` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('geo:locatable', {})`
- `('meta:recordable', {})`
- `('entity:attendable', {})`
- `('entity:participable', {})`

<a id="dm-type-edu-class-type-taxonomy"></a>

### edu:class:type:taxonomy

A hierarchical taxonomy of edu:class types.
The `edu:class:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-ps-person"></a>

### ps:person

A person or persona.
The `ps:person` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:actor', {})`
- `('entity:singular', {})`
- `('risk:targetable', {})`
- `('entity:contactable', {})`

<a id="dm-type-ps-workhist"></a>

### ps:workhist

An entry in a contact's work history.
The `ps:workhist` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-ps-vitals"></a>

### ps:vitals

Statistics and demographic data about a person.
The `ps:vitals` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('phys:tangible', {})`

<a id="dm-type-ps-skill"></a>

### ps:skill

A specific skill which a person or organization may have.
The `ps:skill` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('edu:learnable', {})`

<a id="dm-type-ps-skill-type-taxonomy"></a>

### ps:skill:type:taxonomy

A hierarchical taxonomy of skill types.
The `ps:skill:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-plan-system"></a>

### plan:system

A planning or behavioral analysis system that defines phases and procedures.
The `plan:system` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:authorable', {})`

<a id="dm-type-plan-phase"></a>

### plan:phase

A phase within a planning system which may be used to group steps within a procedure.
The `plan:phase` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:authorable', {})`

<a id="dm-type-plan-procedure"></a>

### plan:procedure

A procedure consisting of steps.
The `plan:procedure` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('doc:document', {})`

<a id="dm-type-plan-procedure-type-taxonomy"></a>

### plan:procedure:type:taxonomy

A hierarchical taxonomy of procedure types.
The `plan:procedure:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-plan-procedure-variable"></a>

### plan:procedure:variable

A variable used by a procedure.
The `plan:procedure:variable` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-plan-procedure-step"></a>

### plan:procedure:step

A step within a procedure.
The `plan:procedure:step` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-plan-procedure-link"></a>

### plan:procedure:link

A link between steps in a procedure.
The `plan:procedure:link` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-proj-ticket-type-taxonomy"></a>

### proj:ticket:type:taxonomy

A hierarchical taxonomy of project task types.
The `proj:ticket:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-proj-ticket"></a>

### proj:ticket

A ticket in a project management system.
The `proj:ticket` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:task', {})`

<a id="dm-type-proj-project-type-taxonomy"></a>

### proj:project:type:taxonomy

A type taxonomy for projects.
The `proj:project:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-proj-sprint"></a>

### proj:sprint

A timeboxed period to complete a set amount of work.
The `proj:sprint` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:activity', {})`

<a id="dm-type-proj-project"></a>

### proj:project

A project in a tasking system.
The `proj:project` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('econ:budgetable', {})`
- `('entity:creatable', {})`
- `('entity:participable', {})`

<a id="dm-type-risk-vuln"></a>

### risk:vuln

A unique vulnerability.
The `risk:vuln` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:reported', {})`
- `('meta:observable', {})`
- `('risk:targetable', {})`
- `('risk:mitigatable', {})`
- `('meta:discoverable', {})`

<a id="dm-type-risk-vuln-id"></a>

### risk:vuln:id

A unique ID given to a vulnerability.
The `risk:vuln:id` type is derived from the base type: [`poly`](#dm-type-poly).

This type has the following options set:

- docs: `None`
- interfaces: `None`
- types: `('it:sec:cve', 'base:id')`

<a id="dm-type-risk-vuln-type-taxonomy"></a>

### risk:vuln:type:taxonomy

A hierarchical taxonomy of vulnerability types.
The `risk:vuln:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-risk-vulnerable"></a>

### risk:vulnerable

Indicates that a node is susceptible to a vulnerability.
The `risk:vulnerable` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:task', {})`

<a id="dm-type-risk-threat"></a>

### risk:threat

A threat cluster or subgraph of threat activity, as defined by a specific source.
The `risk:threat` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:resolvable', {})`
- `('meta:reported', {})`
- `('meta:observable', {})`
- `('meta:discoverable', {})`
- `('entity:actor', {})`
- `('entity:contactable', {})`

<a id="dm-type-risk-attack"></a>

### risk:attack

An instance of an actor attacking a target.
The `risk:attack` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:reported', {})`
- `('entity:activity', {})`
- `('risk:victimized', {})`
- `('meta:discoverable', {})`

<a id="dm-type-risk-alert-type-taxonomy"></a>

### risk:alert:type:taxonomy

A hierarchical taxonomy of alert types.
The `risk:alert:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-risk-alert"></a>

### risk:alert

An alert which indicates the presence of a risk.
The `risk:alert` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:task', {})`

<a id="dm-type-risk-compromise"></a>

### risk:compromise

A compromise and its aggregate impact. The compromise is the result of a successful attack.
The `risk:compromise` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:reported', {})`
- `('entity:activity', {})`
- `('risk:victimized', {})`
- `('meta:discoverable', {})`

<a id="dm-type-risk-mitigation"></a>

### risk:mitigation

A mitigation for a specific vulnerability or technique.
The `risk:mitigation` type is derived from the base type: [`meta:technique`](#dm-type-meta-technique).

This type implements the following interfaces:

- `('meta:usable', {})`
- `('meta:reported', {})`
- `('meta:observable', {})`
- `('risk:mitigatable', {})`

<a id="dm-type-risk-attack-type-taxonomy"></a>

### risk:attack:type:taxonomy

A hierarchical taxonomy of attack types.
The `risk:attack:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-risk-compromise-type-taxonomy"></a>

### risk:compromise:type:taxonomy

A hierarchical taxonomy of compromise types.
The `risk:compromise:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

An example of `risk:compromise:type:taxonomy`:

- `cno.breach`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-risk-alert-verdict-taxonomy"></a>

### risk:alert:verdict:taxonomy

A hierarchical taxonomy of alert verdicts.
The `risk:alert:verdict:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-risk-threat-type-taxonomy"></a>

### risk:threat:type:taxonomy

A hierarchical taxonomy of threat types.
The `risk:threat:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-risk-leak"></a>

### risk:leak

An event where information was disclosed without permission.
The `risk:leak` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`
- `('meta:reported', {})`
- `('risk:victimized', {})`

<a id="dm-type-risk-leak-type-taxonomy"></a>

### risk:leak:type:taxonomy

A hierarchical taxonomy of leak event types.
The `risk:leak:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-risk-extortion"></a>

### risk:extortion

Activity where an attacker attempted to extort a victim.
The `risk:extortion` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:reported', {})`
- `('entity:activity', {})`
- `('risk:victimized', {})`
- `('meta:negotiable', {})`

<a id="dm-type-risk-theft"></a>

### risk:theft

An event where an actor stole from a victim.
The `risk:theft` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`
- `('meta:reported', {})`
- `('risk:victimized', {})`

<a id="dm-type-risk-loss-life"></a>

### risk:loss:life

An aggregate loss of life.
The `risk:loss:life` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('risk:loss', {})`

<a id="dm-type-risk-loss-data"></a>

### risk:loss:data

An aggregate loss of data which is no longer available. This is not used to record data theft.
The `risk:loss:data` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('risk:loss', {})`

<a id="dm-type-risk-loss-funds"></a>

### risk:loss:funds

An aggregate loss of funds.
The `risk:loss:funds` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('risk:loss', {})`

<a id="dm-type-risk-outage-cause-taxonomy"></a>

### risk:outage:cause:taxonomy

An outage cause taxonomy.
The `risk:outage:cause:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-risk-outage-type-taxonomy"></a>

### risk:outage:type:taxonomy

An outage type taxonomy.
The `risk:outage:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-risk-outage"></a>

### risk:outage

An outage event which affected resource availability.
The `risk:outage` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:activity', {})`
- `('meta:reported', {})`

<a id="dm-type-risk-extortion-type-taxonomy"></a>

### risk:extortion:type:taxonomy

A hierarchical taxonomy of extortion event types.
The `risk:extortion:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-sci-hypothesis-type-taxonomy"></a>

### sci:hypothesis:type:taxonomy

A taxonomy of hypothesis types.
The `sci:hypothesis:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-sci-hypothesis"></a>

### sci:hypothesis

A hypothesis or theory.
The `sci:hypothesis` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('meta:believable', {})`

<a id="dm-type-sci-experiment-type-taxonomy"></a>

### sci:experiment:type:taxonomy

A taxonomy of experiment types.
The `sci:experiment:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-sci-experiment"></a>

### sci:experiment

An instance of running an experiment.
The `sci:experiment` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-sci-observation"></a>

### sci:observation

An observation which may have resulted from an experiment.
The `sci:observation` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:event', {})`

<a id="dm-type-sci-evidence"></a>

### sci:evidence

An assessment of how an observation supports or refutes a hypothesis.
The `sci:evidence` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-syn-type"></a>

### syn:type

A Synapse type used for normalizing nodes and properties.
The `syn:type` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-syn-form"></a>

### syn:form

A Synapse form used for representing nodes in the graph.
The `syn:form` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-syn-interface"></a>

### syn:interface

A Synapse interface which forms may implement to share common properties.
The `syn:interface` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-syn-prop"></a>

### syn:prop

A Synapse property.
The `syn:prop` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-syn-tagprop"></a>

### syn:tagprop

A user defined tag property.
The `syn:tagprop` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-syn-cmd"></a>

### syn:cmd

A Synapse storm command.
The `syn:cmd` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-syn-deleted"></a>

### syn:deleted

A node present below the write layer which has been deleted.
The `syn:deleted` type is derived from the base type: [`data`](#dm-type-data).

This type has the following options set:

- schema: `None`

<a id="dm-type-tel-mob-imei"></a>

### tel:mob:imei

An International Mobile Equipment Id.
The `tel:mob:imei` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `tel:mob:imei`:

- `490154203237518`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^(?<tac>[0-9]{8})(?<serial>[0-9]{6})[0-9]$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-tel-mob-imsi"></a>

### tel:mob:imsi

An International Mobile Subscriber Id.
The `tel:mob:imsi` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('entity:identifier', {})`

An example of `tel:mob:imsi`:

- `310150123456789`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^(?<mcc>[0-9]{3})[0-9]{2,12}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-tel-call"></a>

### tel:call

A telephone call.
The `tel:call` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('base:activity', {})`
- `('lang:transcript', {})`

<a id="dm-type-tel-phone-type-taxonomy"></a>

### tel:phone:type:taxonomy

A taxonomy of phone number types.
The `tel:phone:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-tel-mob-tac"></a>

### tel:mob:tac

A mobile Type Allocation Code.
The `tel:mob:tac` type is derived from the base type: [`int`](#dm-type-int).

This type implements the following interfaces:

- `('meta:havable', {})`

An example of `tel:mob:tac`:

- `49015420`

This type has the following options set:

- enums:strict: `True`
- fmt: `%d`
- ismax: `False`
- ismin: `False`
- max: `None`
- min: `None`
- signed: `True`
- size: `8`

<a id="dm-type-tel-mob-imid"></a>

### tel:mob:imid

Fused knowledge of an IMEI/IMSI used together.
The `tel:mob:imid` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`
- `('entity:identifier', {})`

An example of `tel:mob:imid`:

- `(490154203237518, 310150123456789)`

This type has the following options set:

- fields: `(('imei', 'tel:mob:imei'), ('imsi', 'tel:mob:imsi'))`
- sepr: `None`

<a id="dm-type-tel-mob-imsiphone"></a>

### tel:mob:imsiphone

Fused knowledge of an IMSI assigned phone number.
The `tel:mob:imsiphone` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('meta:observable', {})`

An example of `tel:mob:imsiphone`:

- `(310150123456789, "+7(495) 124-59-83")`

This type has the following options set:

- fields: `(('imsi', 'tel:mob:imsi'), ('phone', 'tel:phone'))`
- sepr: `None`

<a id="dm-type-tel-mob-mcc"></a>

### tel:mob:mcc

ITU Mobile Country Code.
The `tel:mob:mcc` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{3}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-tel-mob-mnc"></a>

### tel:mob:mnc

ITU Mobile Network Code.
The `tel:mob:mnc` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{2,3}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-tel-mob-carrier"></a>

### tel:mob:carrier

The fusion of a MCC/MNC.
The `tel:mob:carrier` type is derived from the base type: [`comp`](#dm-type-comp).

This type implements the following interfaces:

- `('entity:identifier', {})`

An example of `tel:mob:carrier`:

- `(310, 150)`

This type has the following options set:

- fields: `(('mcc', 'tel:mob:mcc'), ('mnc', 'tel:mob:mnc'))`
- sepr: `None`

<a id="dm-type-tel-mob-cell-radio-type-taxonomy"></a>

### tel:mob:cell:radio:type:taxonomy

A hierarchical taxonomy of cell radio types.
The `tel:mob:cell:radio:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-tel-mob-cell"></a>

### tel:mob:cell

A mobile cell site which a phone may connect to.
The `tel:mob:cell` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('geo:locatable', {})`

<a id="dm-type-tel-mob-tadig"></a>

### tel:mob:tadig

A Transferred Account Data Interchange Group number issued to a GSM carrier.
The `tel:mob:tadig` type is derived from the base type: [`base:id`](#dm-type-base-id).

This type implements the following interfaces:

- `('entity:identifier', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[A-Z0-9]{5}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-cargo"></a>

### transport:cargo

Cargo being carried by a vehicle on a trip.
The `transport:cargo` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-transport-point"></a>

### transport:point

A departure/arrival point such as an airport gate or train platform.
The `transport:point` type is derived from the base type: [`title`](#dm-type-title).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- onespace: `True`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-stop"></a>

### transport:stop

A stop made by a vehicle on a trip.
The `transport:stop` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:schedule', {})`

<a id="dm-type-transport-occupant"></a>

### transport:occupant

An occupant of a vehicle on a trip.
The `transport:occupant` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('entity:activity', {})`

<a id="dm-type-transport-occupant-role-taxonomy"></a>

### transport:occupant:role:taxonomy

A taxonomy of transportation occupant roles.
The `transport:occupant:role:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-direction"></a>

### transport:direction

A direction measured in degrees with 0.0 being true North.
The `transport:direction` type is derived from the base type: [`hugenum`](#dm-type-hugenum).

This type has the following options set:

- defunit: `None`
- max: `None`
- maxisvalid: `True`
- min: `None`
- minisvalid: `True`
- modulo: `360`
- units: `None`

<a id="dm-type-transport-land-vehicle-type-taxonomy"></a>

### transport:land:vehicle:type:taxonomy

A type taxonomy for land vehicles.
The `transport:land:vehicle:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-land-vehicle"></a>

### transport:land:vehicle

An individual land based vehicle.
The `transport:land:vehicle` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:vehicle', {})`

<a id="dm-type-transport-land-registration"></a>

### transport:land:registration

Registration issued to a contact for a land vehicle.
The `transport:land:registration` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-transport-land-license"></a>

### transport:land:license

A license to operate a land vehicle issued to a contact.
The `transport:land:license` type is derived from the base type: [`guid`](#dm-type-guid).

<a id="dm-type-transport-air-craft-type-taxonomy"></a>

### transport:air:craft:type:taxonomy

A hierarchical taxonomy of aircraft types.
The `transport:air:craft:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-land-drive"></a>

### transport:land:drive

A drive taken by a land vehicle.
The `transport:land:drive` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:trip', {})`

<a id="dm-type-transport-air-craft"></a>

### transport:air:craft

An individual aircraft.
The `transport:air:craft` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:vehicle', {})`

<a id="dm-type-transport-air-tailnum-type-taxonomy"></a>

### transport:air:tailnum:type:taxonomy

A hierarchical taxonomy of aircraft registration number types.
The `transport:air:tailnum:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-air-tailnum"></a>

### transport:air:tailnum

An aircraft registration number or military aircraft serial number.
The `transport:air:tailnum` type is derived from the base type: [`str`](#dm-type-str).

An example of `transport:air:tailnum`:

- `ff023`

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^[a-z0-9-]{2,}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-air-flightnum"></a>

### transport:air:flightnum

A commercial flight designator including airline and serial.
The `transport:air:flightnum` type is derived from the base type: [`str`](#dm-type-str).

An example of `transport:air:flightnum`:

- `ua2437`

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^[a-z0-9]{3,6}$`
- replace: `((' ', ''),)`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-air-telem"></a>

### transport:air:telem

A telemetry sample from an aircraft in transit.
The `transport:air:telem` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('geo:locatable', {})`

<a id="dm-type-transport-air-flight"></a>

### transport:air:flight

An individual instance of a flight.
The `transport:air:flight` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:trip', {})`

<a id="dm-type-transport-air-port"></a>

### transport:air:port

An IATA assigned airport code.
The `transport:air:port` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-sea-vessel-type-taxonomy"></a>

### transport:sea:vessel:type:taxonomy

A hierarchical taxonomy of sea vessel types.
The `transport:sea:vessel:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-sea-vessel"></a>

### transport:sea:vessel

An individual sea vessel.
The `transport:sea:vessel` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:vehicle', {})`

<a id="dm-type-transport-sea-mmsi"></a>

### transport:sea:mmsi

A Maritime Mobile Service Identifier.
The `transport:sea:mmsi` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `^[0-9]{9}$`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-sea-imo"></a>

### transport:sea:imo

An International Maritime Organization registration number.
The `transport:sea:imo` type is derived from the base type: [`str`](#dm-type-str).

This type has the following options set:

- globsuffix: `False`
- lower: `True`
- mapping: `None`
- onespace: `False`
- regex: `^imo[0-9]{7}$`
- replace: `((' ', ''),)`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-sea-telem"></a>

### transport:sea:telem

A telemetry sample from a vessel in transit.
The `transport:sea:telem` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('geo:locatable', {})`

<a id="dm-type-transport-rail-train"></a>

### transport:rail:train

An individual instance of a consist of train cars running a route.
The `transport:rail:train` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:trip', {})`

<a id="dm-type-transport-rail-car-type-taxonomy"></a>

### transport:rail:car:type:taxonomy

A hierarchical taxonomy of rail car types.
The `transport:rail:car:type:taxonomy` type is derived from the base type: [`taxonomy`](#dm-type-taxonomy).

This type implements the following interfaces:

- `('meta:taxonomy', {})`

An example of `transport:rail:car:type:taxonomy`:

- `engine.diesel`

This type has the following options set:

- globsuffix: `False`
- lower: `False`
- mapping: `None`
- onespace: `False`
- regex: `None`
- replace: `()`
- strip: `True`
- upper: `False`

<a id="dm-type-transport-rail-car"></a>

### transport:rail:car

An individual train car.
The `transport:rail:car` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:container', {})`

<a id="dm-type-transport-rail-consist"></a>

### transport:rail:consist

A group of rail cars and locomotives connected together.
The `transport:rail:consist` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:vehicle', {})`

<a id="dm-type-transport-shipping-container"></a>

### transport:shipping:container

An individual shipping container.
The `transport:shipping:container` type is derived from the base type: [`guid`](#dm-type-guid).

This type implements the following interfaces:

- `('transport:container', {})`

<a id="dm-interfaces"></a>

## Interfaces

Interfaces define common properties inherited by multiple forms.


<a id="dm-type-auth-credential"></a>

### auth:credential

An interface implemented by authentication credential forms.

<a id="dm-type-base-activity"></a>

### base:activity

Properties common to activity which occurs over a period.

This interface extends the following interfaces:

- [`meta:causal`](#dm-type-meta-causal)

This interface defines the following properties:

- `:activity` ([`base:activity`](#dm-type-base-activity)) - A parent activity which includes this activity.
- `:period` ([`activity`](#dm-type-activity)) - The period over which the activity occurred.

<a id="dm-type-base-event"></a>

### base:event

Properties common to an event.

This interface extends the following interfaces:

- [`meta:causal`](#dm-type-meta-causal)

This interface defines the following properties:

- `:activity` ([`base:activity`](#dm-type-base-activity)) - A parent activity which includes this event.
- `:time` ([`time`](#dm-type-time)) - The time that the event occurred.

<a id="dm-type-base-matched"></a>

### base:matched

Properties which are common to matches based on rules.

This interface extends the following interfaces:

- [`base:event`](#dm-type-base-event)

This interface defines the following properties:

- `:rule` (`rule:type`) - The rule which matched the target node.
- `:rule:version` ([`it:version`](#dm-type-it-version)) - The version of the rule which generated the match.
- `:target` (`unknown`) - The target node which matched the rule.

<a id="dm-type-biz-manufactured"></a>

### biz:manufactured

Properties common to items being manufactured.

This interface defines the following properties:

- `:model` ([`biz:model`](#dm-type-biz-model)) - The model number or name of the item.
- `:name` ([`base:name`](#dm-type-base-name)) - The name of the item.

<a id="dm-type-crypto-hash"></a>

### crypto:hash

An interface implemented by all cryptographic hashes.

<a id="dm-type-crypto-hashable"></a>

### crypto:hashable

An interface implemented by types which are frequently hashed.

<a id="dm-type-crypto-key"></a>

### crypto:key

An interface implemented by all cryptographic keys.

This interface defines the following properties:

- `:algorithm` ([`meta:algorithm`](#dm-type-meta-algorithm)) - The algorithm which uses the key material.
- `:bits` ([`size`](#dm-type-size)) - The number of bits of key material.

<a id="dm-type-crypto-smart-effect"></a>

### crypto:smart:effect

Properties common to the effects of a crypto smart contract transaction.

This interface defines the following properties:

- `:index` ([`int`](#dm-type-int)) - The order of the effect within the effects of one transaction.
- `:transaction` ([`crypto:currency:transaction`](#dm-type-crypto-currency-transaction)) - The transaction where the smart contract was called.

<a id="dm-type-doc-authorable"></a>

### doc:authorable

Properties common to authorable forms.

This interface extends the following interfaces:

- [`entity:creatable`](#dm-type-entity-creatable)

This interface defines the following properties:

- `:created` ([`time`](#dm-type-time)) - The time that the document was created.
- `:desc` ([`text`](#dm-type-text)) - A description of the document.
- `:id` ([`base:id`](#dm-type-base-id)) - The document ID.
- `:ids` ([`base:id`](#dm-type-base-id)) - An array of alternate IDs for the document.
- `:supersedes` ([`doc:authorable`](#dm-type-doc-authorable)) - An array of document versions which are superseded by this document.
- `:updated` ([`time`](#dm-type-time)) - The time that the document was last updated.
- `:url` ([`inet:url`](#dm-type-inet-url)) - The URL where the document is available.
- `:version` ([`it:version`](#dm-type-it-version)) - The version of the document.

<a id="dm-type-doc-document"></a>

### doc:document

A common interface for documents.

This interface extends the following interfaces:

- [`doc:authorable`](#dm-type-doc-authorable)

This interface defines the following properties:

- `:body` ([`text`](#dm-type-text)) - The text of the document.
- `:file` ([`file:bytes`](#dm-type-file-bytes)) - The file containing the document contents.
- `:file:captured` ([`time`](#dm-type-time)) - The time when the file content was captured.
- `:file:name` ([`file:base`](#dm-type-file-base)) - The name of the file containing the document contents.
- `:title` ([`title`](#dm-type-title)) - The title of the document.
- `:type` (`doc:document:type:taxonomy`) - The type of document.

<a id="dm-type-doc-published"></a>

### doc:published

Properties common to published documents.

This interface defines the following properties:

- `:public` ([`bool`](#dm-type-bool)) - Set to true if the report is publicly available.
- `:published` ([`time`](#dm-type-time)) - The time the report was published.
- `:publisher` ([`entity:actor`](#dm-type-entity-actor)) - The entity which published the report.
- `:publisher:name` ([`entity:name`](#dm-type-entity-name)) - The name of the entity which published the report.
- `:topics` ([`meta:topic`](#dm-type-meta-topic)) - The topics discussed in the report.

<a id="dm-type-doc-signable"></a>

### doc:signable

An interface implemented by documents which can be signed by actors.

This interface defines the following properties:

- `:signed` ([`time`](#dm-type-time)) - The date that the document signing was complete.

<a id="dm-type-econ-bank-routing-code"></a>

### econ:bank:routing:code

An interface for forms which identify a bank or branch for routing purposes.

This interface defines the following properties:

- `:bank` ([`ou:org`](#dm-type-ou-org)) - The bank or branch which the routing identifier refers to.
- `:bank:name` ([`entity:name`](#dm-type-entity-name)) - The name of the bank or branch.

<a id="dm-type-econ-budgetable"></a>

### econ:budgetable

An interface for forms which may have an associated budget.

This interface defines the following properties:

- `:budget` ([`econ:budget`](#dm-type-econ-budget)) - The budget for the item.

<a id="dm-type-econ-pay-instrument"></a>

### econ:pay:instrument

An interface for forms which may act as a payment instrument.

This interface defines the following properties:

- `:account` ([`econ:account`](#dm-type-econ-account)) - The account that contains the funds used by the instrument.

<a id="dm-type-edu-learnable"></a>

### edu:learnable

An interface implemented by nodes which represent a skill which can be learned.

<a id="dm-type-entity-action"></a>

### entity:action

Properties which are common to actions taken by entities.

This interface defines the following properties:

- `:actor` ([`entity:actor`](#dm-type-entity-actor)) - The actor who carried out the action.
- `:actor:name` ([`entity:name`](#dm-type-entity-name)) - The name of the actor who carried out the action.

<a id="dm-type-entity-activity"></a>

### entity:activity

Properties common to activity carried out by an actor.

This interface extends the following interfaces:

- [`base:activity`](#dm-type-base-activity)
- [`entity:action`](#dm-type-entity-action)

<a id="dm-type-entity-actor"></a>

### entity:actor

An interface for entities which have initiative to act.

<a id="dm-type-entity-attendable"></a>

### entity:attendable

An interface implemented by activities which an actor may attend.

This interface extends the following interfaces:

- [`base:activity`](#dm-type-base-activity)

<a id="dm-type-entity-contactable"></a>

### entity:contactable

An interface for forms which contain contact info.

This interface extends the following interfaces:

- [`geo:locatable`](#dm-type-geo-locatable)

This interface defines the following properties:

- `:banner` ([`file:bytes`](#dm-type-file-bytes)) - A banner or hero image used on the profile page.
- `:bio` ([`text`](#dm-type-text)) - A tagline or bio provided for the entity.
- `:creds` ([`auth:credential`](#dm-type-auth-credential)) - An array of non-ephemeral credentials.
- `:crypto:currency:addresses` ([`crypto:currency:address`](#dm-type-crypto-currency-address)) - Crypto currency addresses listed for the entity.
- `:desc` ([`text`](#dm-type-text)) - A description of the entity.
- `:email` ([`inet:email`](#dm-type-inet-email)) - The primary email address for the entity.
- `:emails` ([`inet:email`](#dm-type-inet-email)) - An array of alternate email addresses for the entity.
- `:id` ([`base:id`](#dm-type-base-id)) - A type or source specific ID for the entity.
- `:identifiers` ([`entity:identifier`](#dm-type-entity-identifier)) - Additional entity identifiers.
- `:lang` ([`lang:language`](#dm-type-lang-language)) - The primary language of the entity.
- `:langs` ([`lang:language`](#dm-type-lang-language)) - An array of alternate languages for the entity.
- `:lifespan` ([`entity:lifespan`](#dm-type-entity-lifespan)) - The lifespan of the entity.
- `:name` ([`entity:name`](#dm-type-entity-name)) - The primary entity name of the entity.
- `:names` ([`entity:name`](#dm-type-entity-name)) - An array of alternate entity names for the entity.
- `:phone` ([`tel:phone`](#dm-type-tel-phone)) - The primary phone number for the entity.
- `:phones` ([`tel:phone`](#dm-type-tel-phone)) - An array of alternate telephone numbers for the entity.
- `:photo` ([`file:bytes`](#dm-type-file-bytes)) - The profile picture or avatar for this entity.
- `:social:accounts` ([`inet:service:account`](#dm-type-inet-service-account)) - Social media or other online accounts listed for the entity.
- `:username` ([`entity:name`](#dm-type-entity-name)) - The primary user name for the entity.
- `:usernames` ([`entity:name`](#dm-type-entity-name)) - An array of alternate user names for the entity.
- `:websites` ([`inet:url`](#dm-type-inet-url)) - Web sites listed for the entity.

<a id="dm-type-entity-creatable"></a>

### entity:creatable

An interface implemented by forms which represent things made or created by an actor.

This interface defines the following properties:

- `:creator` ([`entity:actor`](#dm-type-entity-actor)) - The primary actor which created the item.
- `:creator:name` ([`entity:name`](#dm-type-entity-name)) - The name of the primary actor which created the item.

<a id="dm-type-entity-destroyable"></a>

### entity:destroyable

An interface implemented by forms which represent things which can be destroyed.

<a id="dm-type-entity-event"></a>

### entity:event

Properties common to events carried out by an actor.

This interface extends the following interfaces:

- [`base:event`](#dm-type-base-event)
- [`entity:action`](#dm-type-entity-action)

<a id="dm-type-entity-identifier"></a>

### entity:identifier

An interface which is implemented by entity identifier forms.

<a id="dm-type-entity-multiple"></a>

### entity:multiple

Properties which apply to entities which may represent a group or organization.

<a id="dm-type-entity-participable"></a>

### entity:participable

An interface implemented by activities which an actor may participate in.

This interface extends the following interfaces:

- [`base:activity`](#dm-type-base-activity)

<a id="dm-type-entity-resolvable"></a>

### entity:resolvable

An abstract entity which can be resolved to an organization or person.

This interface defines the following properties:

- `:resolved` (poly) - The resolved entity to which this entity belongs.

<a id="dm-type-entity-singular"></a>

### entity:singular

Properties which apply to entities which may represent a person.

This interface extends the following interfaces:

- [`geo:locatable`](#dm-type-geo-locatable)
- [`geo:locatable`](#dm-type-geo-locatable)

This interface defines the following properties:

- `:org` ([`ou:org`](#dm-type-ou-org)) - An associated organization listed as part of the contact information.
- `:org:name` ([`entity:name`](#dm-type-entity-name)) - The name of an associated organization listed as part of the contact information.
- `:title` ([`entity:title`](#dm-type-entity-title)) - The entity title or role for this item.
- `:titles` ([`entity:title`](#dm-type-entity-title)) - An array of alternate entity titles or roles for this item.

<a id="dm-type-entity-stance"></a>

### entity:stance

An interface for asks/offers in a negotiation.

This interface extends the following interfaces:

- [`entity:event`](#dm-type-entity-event)

This interface defines the following properties:

- `:activity` ([`meta:negotiable`](#dm-type-meta-negotiable)) - The negotiation activity this stance was part of.
- `:expires` ([`time`](#dm-type-time)) - The time that the stance expires.
- `:value` ([`econ:price`](#dm-type-econ-price)) - The value of the stance.

<a id="dm-type-entity-supportable"></a>

### entity:supportable

An interface implemented by activities which may be supported in by an actor.

<a id="dm-type-file-entry"></a>

### file:entry

Properties common to forms representing a file at a path.

This interface defines the following properties:

- `:file` ([`file:bytes`](#dm-type-file-bytes)) - The file associated with the file entry.
- `:path` ([`file:path`](#dm-type-file-path)) - The path of the file associated with the file entry.

<a id="dm-type-file-mime-exe"></a>

### file:mime:exe

Properties common to executable file formats.

This interface extends the following interfaces:

- [`file:mime:meta`](#dm-type-file-mime-meta)

This interface defines the following properties:

- `:compiler` ([`it:software`](#dm-type-it-software)) - The software used to compile the executable.
- `:compiler:name` ([`it:softwarename`](#dm-type-it-softwarename)) - The name of the software used to compile the executable.
- `:packer` ([`it:software`](#dm-type-it-software)) - The software used to pack the executable.
- `:packer:name` ([`it:softwarename`](#dm-type-it-softwarename)) - The name of the software used to pack the executable.

<a id="dm-type-file-mime-image"></a>

### file:mime:image

Properties common to image file formats.

This interface extends the following interfaces:

- [`file:mime:meta`](#dm-type-file-mime-meta)

This interface defines the following properties:

- `:altitude` ([`geo:altitude`](#dm-type-geo-altitude)) - MIME specific altitude information extracted from metadata.
- `:author` ([`entity:contact`](#dm-type-entity-contact)) - MIME specific contact information extracted from metadata.
- `:author:name` ([`entity:name`](#dm-type-entity-name)) - MIME specific author name extracted from metadata.
- `:comment` ([`text`](#dm-type-text)) - MIME specific comment field extracted from metadata.
- `:created` ([`time`](#dm-type-time)) - MIME specific creation timestamp extracted from metadata.
- `:desc` ([`text`](#dm-type-text)) - MIME specific description field extracted from metadata.
- `:id` ([`base:id`](#dm-type-base-id)) - MIME specific unique identifier extracted from metadata.
- `:latlong` ([`geo:latlong`](#dm-type-geo-latlong)) - MIME specific lat/long information extracted from metadata.
- `:text` ([`text`](#dm-type-text)) - The text contained within the image.

<a id="dm-type-file-mime-meta"></a>

### file:mime:meta

Properties common to mime specific file metadata types.

This interface defines the following properties:

- `:file` ([`file:bytes`](#dm-type-file-bytes)) - The file that the mime info was parsed from.
- `:file:data` ([`data`](#dm-type-data)) - A mime specific arbitrary data structure for non-indexed data.
- `:file:offs` ([`int`](#dm-type-int)) - The offset of the metadata within the file.
- `:file:size` ([`int`](#dm-type-int)) - The size of the metadata within the file.

<a id="dm-type-file-mime-msoffice"></a>

### file:mime:msoffice

Properties common to various microsoft office file formats.

This interface extends the following interfaces:

- [`file:mime:meta`](#dm-type-file-mime-meta)

This interface defines the following properties:

- `:application` ([`it:software`](#dm-type-it-software)) - The creating application extracted from Microsoft Office metadata.
- `:application:name` ([`it:softwarename`](#dm-type-it-softwarename)) - The creating application name extracted from Microsoft Office metadata.
- `:author` ([`entity:contact`](#dm-type-entity-contact)) - The author extracted from Microsoft Office metadata.
- `:author:name` ([`entity:name`](#dm-type-entity-name)) - The author name extracted from Microsoft Office metadata.
- `:created` ([`time`](#dm-type-time)) - The create_time extracted from Microsoft Office metadata.
- `:lastsaved` ([`time`](#dm-type-time)) - The last_saved_time extracted from Microsoft Office metadata.
- `:subject` ([`text`](#dm-type-text)) - The subject extracted from Microsoft Office metadata.
- `:title` ([`text`](#dm-type-text)) - The title extracted from Microsoft Office metadata.

<a id="dm-type-file-subfile"></a>

### file:subfile

Properties common to forms representing a file contained within another file.

This interface extends the following interfaces:

- [`meta:observable`](#dm-type-meta-observable)

This interface defines the following properties:

- `:file` ([`file:bytes`](#dm-type-file-bytes)) - The file contained within the parent file.
- `:offset` ([`size`](#dm-type-size)) - The offset to the beginning of the file within the parent file.
- `:parent` ([`file:bytes`](#dm-type-file-bytes)) - The parent file which contains the subfile.

<a id="dm-type-geo-locatable"></a>

### geo:locatable

Properties common to items and events which may be geolocated.

This interface defines the following properties:

- `:` ([`geo:place`](#dm-type-geo-place)) - The place where the item was located.
- `:address` ([`geo:address`](#dm-type-geo-address)) - The postal address where the item was located.
- `:address:city` ([`base:name`](#dm-type-base-name)) - The city where the item was located.
- `:altitude` ([`geo:altitude`](#dm-type-geo-altitude)) - The altitude where the item was located.
- `:altitude:accuracy` ([`phys:distance`](#dm-type-phys-distance)) - The accuracy of the altitude where the item was located.
- `:country` ([`pol:country`](#dm-type-pol-country)) - The country where the item was located.
- `:country:code` ([`iso:3166:alpha2`](#dm-type-iso-3166-alpha2)) - The country code where the item was located.
- `:latlong` ([`geo:latlong`](#dm-type-geo-latlong)) - The latlong where the item was located.
- `:latlong:accuracy` ([`phys:distance`](#dm-type-phys-distance)) - The accuracy of the latlong where the item was located.
- `:loc` ([`loc`](#dm-type-loc)) - The geopolitical location where the item was located.
- `:name` ([`geo:name`](#dm-type-geo-name)) - The name of the place where the item was located.

<a id="dm-type-inet-dns-record"></a>

### inet:dns:record

An interface for DNS records.

<a id="dm-type-inet-proto-link"></a>

### inet:proto:link

Properties common to network protocol requests and transports.

This interface defines the following properties:

- `:client` ([`inet:client`](#dm-type-inet-client)) - The socket address of the client.
- `:client:exe` ([`file:bytes`](#dm-type-file-bytes)) - The client executable which initiated the link.
- `:client:host` ([`it:host`](#dm-type-it-host)) - The client host which initiated the link.
- `:client:proc` ([`it:exec:proc`](#dm-type-it-exec-proc)) - The client process which initiated the link.
- `:sandbox:file` ([`file:bytes`](#dm-type-file-bytes)) - The initial sample given to a sandbox environment to analyze.
- `:server` ([`inet:server`](#dm-type-inet-server)) - The socket address of the server.
- `:server:exe` ([`file:bytes`](#dm-type-file-bytes)) - The server executable which received the link.
- `:server:host` ([`it:host`](#dm-type-it-host)) - The server host which received the link.
- `:server:proc` ([`it:exec:proc`](#dm-type-it-exec-proc)) - The server process which received the link.

<a id="dm-type-inet-proto-login"></a>

### inet:proto:login

Properties common to authentication login events.

This interface extends the following interfaces:

- [`inet:proto:request`](#dm-type-inet-proto-request)

This interface defines the following properties:

- `:credential` ([`auth:credential`](#dm-type-auth-credential)) - The credential presented during the login event.
- `:session` ([`inet:proto:session`](#dm-type-inet-proto-session)) - The protocol session established by the login event.
- `:success` ([`bool`](#dm-type-bool)) - Set to true if the login event was successful.

<a id="dm-type-inet-proto-request"></a>

### inet:proto:request

Properties common to network protocol requests.

This interface extends the following interfaces:

- [`base:event`](#dm-type-base-event)
- [`inet:proto:link`](#dm-type-inet-proto-link)

This interface defines the following properties:

- `:flow` ([`inet:flow`](#dm-type-inet-flow)) - The network flow which contained the request.

<a id="dm-type-inet-proto-response"></a>

### inet:proto:response

Properties common to network protocol responses.

This interface extends the following interfaces:

- [`base:event`](#dm-type-base-event)
- [`inet:proto:link`](#dm-type-inet-proto-link)

This interface defines the following properties:

- `:flow` ([`inet:flow`](#dm-type-inet-flow)) - The network flow which contained the response.

<a id="dm-type-inet-proto-session"></a>

### inet:proto:session

Properties common to network protocol sessions.

This interface extends the following interfaces:

- [`base:activity`](#dm-type-base-activity)

This interface defines the following properties:

- `:client` ([`inet:client`](#dm-type-inet-client)) - The socket address of the client which initiated the protocol session.
- `:client:host` ([`it:host`](#dm-type-it-host)) - The host which initiated the protocol session.
- `:server` ([`inet:server`](#dm-type-inet-server)) - The socket address of the server which received the protocol session.
- `:server:host` ([`it:host`](#dm-type-it-host)) - The host which received the protocol session.

<a id="dm-type-inet-service-action"></a>

### inet:service:action

Properties common to events within a service platform.

This interface extends the following interfaces:

- [`entity:event`](#dm-type-entity-event)
- [`inet:service:base`](#dm-type-inet-service-base)

This interface defines the following properties:

- `:actor` (poly) - The service account or agent which performed the action.
- `:client` ([`inet:client`](#dm-type-inet-client)) - The network address of the client which initiated the action.
- `:client:host` ([`it:host`](#dm-type-it-host)) - The client host which initiated the action.
- `:client:software` ([`it:software`](#dm-type-it-software)) - The client software used to initiate the action.
- `:platform` ([`inet:service:platform`](#dm-type-inet-service-platform)) - The platform where the action was initiated.
- `:server` ([`inet:server`](#dm-type-inet-server)) - The network address of the server which handled the action.
- `:server:host` ([`it:host`](#dm-type-it-host)) - The server host which handled the action.
- `:session` ([`inet:service:session`](#dm-type-inet-service-session)) - The session which initiated the action.
- `:time` ([`time`](#dm-type-time)) - The time that the actor initiated the action.

<a id="dm-type-inet-service-action-authorized"></a>

### inet:service:action:authorized

Properties common to service actions which may be allowed or denied.

This interface extends the following interfaces:

- [`inet:service:action`](#dm-type-inet-service-action)

This interface defines the following properties:

- `:error` ([`inet:service:error`](#dm-type-inet-service-error)) - The error generated if the action was unsuccessful.
- `:error:reason` ([`str`](#dm-type-str)) - The platform specific friendly error reason if the action was unsuccessful.
- `:rule` ([`inet:service:rule`](#dm-type-inet-service-rule)) - The rule which allowed or denied the action.
- `:success` ([`bool`](#dm-type-bool)) - Set to true if the action was successful.

<a id="dm-type-inet-service-base"></a>

### inet:service:base

Properties common to most forms within a service platform.

This interface defines the following properties:

- `:id` ([`base:id`](#dm-type-base-id)) - A platform specific ID which identifies the node.
- `:platform` ([`inet:service:platform`](#dm-type-inet-service-platform)) - The platform which defines the node.

<a id="dm-type-inet-service-commentable"></a>

### inet:service:commentable

An interface common to service objects which can have comments made about them.

<a id="dm-type-inet-service-joinable"></a>

### inet:service:joinable

An interface common to nodes which can have accounts as members.

<a id="dm-type-inet-service-labelable"></a>

### inet:service:labelable

An interface common to service objects which can have labels applied to them.

<a id="dm-type-inet-service-object"></a>

### inet:service:object

Properties common to objects within a service platform.

This interface extends the following interfaces:

- [`inet:service:base`](#dm-type-inet-service-base)
- [`meta:observable`](#dm-type-meta-observable)

This interface defines the following properties:

- `:creator` (poly) - The service account or agent which created the object.
- `:period` ([`it:lifespan`](#dm-type-it-lifespan)) - The period when the object existed.
- `:remover` (poly) - The service account or agent which removed or decommissioned the object.
- `:status` ([`title`](#dm-type-title)) - The status of the object.
- `:url` ([`inet:url`](#dm-type-inet-url)) - The primary URL associated with the object.

<a id="dm-type-inet-service-subscriber"></a>

### inet:service:subscriber

Properties common to the nodes which subscribe to services.

This interface extends the following interfaces:

- [`inet:service:object`](#dm-type-inet-service-object)

This interface defines the following properties:

- `:creds` ([`auth:credential`](#dm-type-auth-credential)) - An array of non-ephemeral credentials.
- `:email` ([`inet:email`](#dm-type-inet-email)) - The email address of the subscriber.
- `:name` ([`entity:name`](#dm-type-entity-name)) - The name of the subscriber.
- `:profile` ([`entity:contact`](#dm-type-entity-contact)) - Current detailed contact information for the subscriber.
- `:username` ([`entity:name`](#dm-type-entity-name)) - The primary user name for the subscriber.

<a id="dm-type-it-component"></a>

### it:component

Properties common to hardware components.

This interface extends the following interfaces:

- [`meta:havable`](#dm-type-meta-havable)
- [`geo:locatable`](#dm-type-geo-locatable)
- [`meta:observable`](#dm-type-meta-observable)
- [`entity:creatable`](#dm-type-entity-creatable)
- [`risk:exploitable`](#dm-type-risk-exploitable)

This interface defines the following properties:

- `:hardware` ([`it:hardware`](#dm-type-it-hardware)) - The hardware specification of the component.
- `:parent` ([`it:component`](#dm-type-it-component)) - The parent component which this component is part of.
- `:period` ([`phys:lifespan`](#dm-type-phys-lifespan)) - The period when the component existed, from its creation until it was retired or destroyed.
- `:serial` ([`base:id`](#dm-type-base-id)) - The serial number of the component.

<a id="dm-type-it-host-activity"></a>

### it:host:activity

Activity which occurred on a host.

This interface extends the following interfaces:

- [`base:activity`](#dm-type-base-activity)
- [`it:host:exec`](#dm-type-it-host-exec)

<a id="dm-type-it-host-event"></a>

### it:host:event

An event which occurred on a host.

This interface extends the following interfaces:

- [`base:event`](#dm-type-base-event)
- [`it:host:exec`](#dm-type-it-host-exec)

This interface defines the following properties:

- `:proc` ([`it:exec:proc`](#dm-type-it-exec-proc)) - The process which caused the event.
- `:thread` ([`it:exec:thread`](#dm-type-it-exec-thread)) - The thread which caused the event.

<a id="dm-type-it-host-exec"></a>

### it:host:exec

Properties common to runtime events and activity on a host.

This interface defines the following properties:

- `:exe` ([`file:bytes`](#dm-type-file-bytes)) - The executable file which caused the activity.
- `:host` ([`it:host`](#dm-type-it-host)) - The host on which the activity occurred.
- `:sandbox:file` ([`file:bytes`](#dm-type-file-bytes)) - The initial sample given to a sandbox environment to analyze.

<a id="dm-type-lang-transcript"></a>

### lang:transcript

An interface which applies to forms containing speech.

This interface defines the following properties:

- `:lang` ([`lang:language`](#dm-type-lang-language)) - The language of the transcript.
- `:text` ([`text`](#dm-type-text)) - The text of the transcript.

<a id="dm-type-meta-achievable"></a>

### meta:achievable

An interface implemented by forms which are achievable.

<a id="dm-type-meta-believable"></a>

### meta:believable

An interface implemented by forms which may be believed in by an actor.

This interface defines the following properties:

- `:desc` ([`text`](#dm-type-text)) - A description of the item.
- `:name` ([`base:name`](#dm-type-base-name)) - The name of the item.

<a id="dm-type-meta-causal"></a>

### meta:causal

Implemented by events and activities which can lead to effects.

<a id="dm-type-meta-discoverable"></a>

### meta:discoverable

An interface for items which can be discovered by an actor.

This interface defines the following properties:

- `:discovered` ([`time`](#dm-type-time)) - The earliest known time when the item was discovered.
- `:discoverer` ([`entity:actor`](#dm-type-entity-actor)) - The earliest known actor which discovered the item.

<a id="dm-type-meta-havable"></a>

### meta:havable

An interface used to describe items that can be possessed by an entity.

<a id="dm-type-meta-negotiable"></a>

### meta:negotiable

An interface implemented by activities which involve negotiation.

<a id="dm-type-meta-observable"></a>

### meta:observable

Properties common to forms which can be observed.

This interface defines the following properties:

- `:seen` ([`ival`](#dm-type-ival)) - The node was observed during the time interval.

<a id="dm-type-meta-recordable"></a>

### meta:recordable

Properties common to activities which may be recorded or transcribed.

This interface defines the following properties:

- `:recording:file` ([`file:bytes`](#dm-type-file-bytes)) - A file containing a recording of the event.
- `:recording:offset` ([`duration`](#dm-type-duration)) - The time offset of the activity within the recording.
- `:recording:url` ([`inet:url`](#dm-type-inet-url)) - The URL hosting a recording of the event.

<a id="dm-type-meta-reported"></a>

### meta:reported

Properties common to forms which are created on a per-source basis.

This interface defines the following properties:

- `:desc` ([`text`](#dm-type-text)) - A description of the item.
- `:id` ([`base:id`](#dm-type-base-id)) - A unique ID given to the item.
- `:ids` ([`base:id`](#dm-type-base-id)) - An array of alternate IDs given to the item.
- `:name` ([`base:name`](#dm-type-base-name)) - The primary name of the item.
- `:names` ([`base:name`](#dm-type-base-name)) - A list of alternate names for the item.
- `:reporter` ([`entity:actor`](#dm-type-entity-actor)) - The entity which reported on the item.
- `:reporter:deprecated` ([`time`](#dm-type-time)) - The time when the reporter retired the item.
- `:reporter:name` ([`entity:name`](#dm-type-entity-name)) - The name of the entity which reported on the item.
- `:reporter:period` ([`reported`](#dm-type-reported)) - The period when the item existed, according to the reporter.
- `:reporter:published` ([`time`](#dm-type-time)) - The time when the reporter published the item.
- `:reporter:supersedes` ([`meta:reported`](#dm-type-meta-reported)) - An array of item nodes which are superseded by this item.
- `:reporter:updated` ([`time`](#dm-type-time)) - The time when the item was last updated.
- `:reporter:url` ([`inet:url`](#dm-type-inet-url)) - The URL for the item provided by the reporter.
- `:resolved` ([`meta:reported`](#dm-type-meta-reported)) - The authoritative item which this reporting is about.

<a id="dm-type-meta-schedulable"></a>

### meta:schedulable

An interface implemented by activities which may be scheduled.

This interface extends the following interfaces:

- [`base:activity`](#dm-type-base-activity)

This interface defines the following properties:

- `:scheduled:period` ([`ival`](#dm-type-ival)) - The scheduled period over which the activity was expected to occur.

<a id="dm-type-meta-task"></a>

### meta:task

A common interface for tasks.

This interface extends the following interfaces:

- [`entity:participable`](#dm-type-entity-participable)

This interface defines the following properties:

- `:assignee` ([`entity:actor`](#dm-type-entity-actor)) - The actor who is assigned to complete the task.
- `:created` ([`time`](#dm-type-time)) - The time the task was created.
- `:creator` ([`entity:actor`](#dm-type-entity-actor)) - The actor who created the task.
- `:due` ([`time`](#dm-type-time)) - The time the task must be complete.
- `:id` ([`base:id`](#dm-type-base-id)) - The ID of the task.
- `:parent` ([`meta:task`](#dm-type-meta-task)) - The parent task which includes this task.
- `:period` ([`ival`](#dm-type-ival)) - The period when the task was being worked on.
- `:priority` ([`meta:score`](#dm-type-meta-score)) - The priority of the task.
- `:project` ([`proj:project`](#dm-type-proj-project)) - The project containing the task.
- `:status` ([`title`](#dm-type-title)) - The status of the task.
- `:updated` ([`time`](#dm-type-time)) - The time the task was last updated.

<a id="dm-type-meta-taxonomy"></a>

### meta:taxonomy

Properties common to taxonomies.

This interface defines the following properties:

- `:base` ([`taxon`](#dm-type-taxon)) - The base taxon.
- `:depth` ([`int`](#dm-type-int)) - The depth indexed from 0.
- `:desc` ([`text`](#dm-type-text)) - A definition of the taxonomy entry.
- `:name` ([`title`](#dm-type-title)) - A brief name for the definition.
- `:parent` ([`meta:taxonomy`](#dm-type-meta-taxonomy)) - The taxonomy parent.
- `:sort` ([`int`](#dm-type-int)) - A display sort order for siblings.

<a id="dm-type-meta-usable"></a>

### meta:usable

An interface implemented by forms which can be used by an actor.

<a id="dm-type-ou-promotable"></a>

### ou:promotable

Properties which are common to activities which are promoted by an organization.

This interface defines the following properties:

- `:name` ([`event:name`](#dm-type-event-name)) - The name of the event.
- `:names` ([`event:name`](#dm-type-event-name)) - An array of alternate names for the event.
- `:social:accounts` ([`inet:service:account`](#dm-type-inet-service-account)) - Social media accounts associated with the event.
- `:website` ([`inet:url`](#dm-type-inet-url)) - The website of the event.

<a id="dm-type-phys-object"></a>

### phys:object

Properties common to physical objects.

This interface extends the following interfaces:

- [`meta:havable`](#dm-type-meta-havable)
- [`phys:tangible`](#dm-type-phys-tangible)
- [`entity:destroyable`](#dm-type-entity-destroyable)

This interface defines the following properties:

- `:period` ([`phys:lifespan`](#dm-type-phys-lifespan)) - The period when the object existed, from its creation until it was retired or destroyed.

<a id="dm-type-phys-tangible"></a>

### phys:tangible

Properties common to nodes which have or capture physical characteristics.

This interface extends the following interfaces:

- [`geo:locatable`](#dm-type-geo-locatable)

This interface defines the following properties:

- `:phys:height` ([`phys:distance`](#dm-type-phys-distance)) - The physical height of the object.
- `:phys:length` ([`phys:distance`](#dm-type-phys-distance)) - The physical length of the object.
- `:phys:mass` ([`phys:mass`](#dm-type-phys-mass)) - The physical mass of the object.
- `:phys:volume` ([`phys:volume`](#dm-type-phys-volume)) - The physical volume of the object.
- `:phys:width` ([`phys:distance`](#dm-type-phys-distance)) - The physical width of the object.

<a id="dm-type-risk-exploitable"></a>

### risk:exploitable

An interface implemented by forms which may be exploited by an actor.

<a id="dm-type-risk-loss"></a>

### risk:loss

An interface for aggregate losses which occur over a period.

This interface extends the following interfaces:

- [`base:activity`](#dm-type-base-activity)

<a id="dm-type-risk-mitigatable"></a>

### risk:mitigatable

A common interface for risks which may be mitigated.

<a id="dm-type-risk-targetable"></a>

### risk:targetable

An interface implemented by forms which are targets of threats.

<a id="dm-type-risk-victimized"></a>

### risk:victimized

An interface for malicious acts which directly impact a victim.

This interface defines the following properties:

- `:victim` ([`entity:actor`](#dm-type-entity-actor)) - The victim of the event.
- `:victim:name` ([`entity:name`](#dm-type-entity-name)) - The name of the victim of the event.

<a id="dm-type-transport-container"></a>

### transport:container

Properties common to a container used to transport cargo or people.

This interface extends the following interfaces:

- [`phys:object`](#dm-type-phys-object)
- [`meta:havable`](#dm-type-meta-havable)
- [`biz:manufactured`](#dm-type-biz-manufactured)
- [`entity:creatable`](#dm-type-entity-creatable)

This interface defines the following properties:

- `:max:cargo:mass` ([`phys:mass`](#dm-type-phys-mass)) - The maximum mass the item can carry as cargo.
- `:max:cargo:volume` ([`phys:volume`](#dm-type-phys-volume)) - The maximum volume the item can carry as cargo.
- `:max:occupants` ([`size`](#dm-type-size)) - The maximum number of occupants the item can hold.
- `:model` ([`biz:model`](#dm-type-biz-model)) - The model of the item.
- `:serial` ([`base:id`](#dm-type-base-id)) - The manufacturer assigned serial number of the item.

<a id="dm-type-transport-schedule"></a>

### transport:schedule

Properties common to travel schedules.

This interface extends the following interfaces:

- [`meta:schedulable`](#dm-type-meta-schedulable)

This interface defines the following properties:

- `:arrived:place` ([`geo:place`](#dm-type-geo-place)) - The actual arrival place.
- `:arrived:point` ([`transport:point`](#dm-type-transport-point)) - The actual arrival point.
- `:departed:place` ([`geo:place`](#dm-type-geo-place)) - The actual departure place.
- `:departed:point` ([`transport:point`](#dm-type-transport-point)) - The actual departure point.
- `:scheduled:arrival:place` ([`geo:place`](#dm-type-geo-place)) - The scheduled arrival place.
- `:scheduled:arrival:point` ([`transport:point`](#dm-type-transport-point)) - The scheduled arrival point.
- `:scheduled:departure:place` ([`geo:place`](#dm-type-geo-place)) - The scheduled departure place.
- `:scheduled:departure:point` ([`transport:point`](#dm-type-transport-point)) - The scheduled departure point.

<a id="dm-type-transport-trip"></a>

### transport:trip

Properties common to a specific trip taken by a vehicle.

This interface extends the following interfaces:

- [`meta:usable`](#dm-type-meta-usable)
- [`transport:schedule`](#dm-type-transport-schedule)

This interface defines the following properties:

- `:cargo:mass` ([`phys:mass`](#dm-type-phys-mass)) - The cargo mass carried by the vehicle on this trip.
- `:cargo:volume` ([`phys:volume`](#dm-type-phys-volume)) - The cargo volume carried by the vehicle on this trip.
- `:occupants` ([`size`](#dm-type-size)) - The number of occupants of the vehicle on this trip.
- `:operator` ([`entity:actor`](#dm-type-entity-actor)) - The contact information of the operator of the trip.
- `:status` ([`title`](#dm-type-title)) - The status of the trip.
- `:vehicle` ([`transport:vehicle`](#dm-type-transport-vehicle)) - The vehicle which traveled the trip.

<a id="dm-type-transport-vehicle"></a>

### transport:vehicle

Properties common to a vehicle.

This interface extends the following interfaces:

- [`transport:container`](#dm-type-transport-container)

This interface defines the following properties:

- `:operator` ([`entity:actor`](#dm-type-entity-actor)) - The contact information of the operator of the item.
