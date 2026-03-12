# Synapse Type System & Storage Layer Skill

TRIGGER: When the user is implementing, modifying, or debugging Synapse data model types, storage encodings, index operations, or property normalization. This includes adding new Type subclasses, modifying normalization behavior, working with StorType encoders, changing index/lift logic, or working with poly types.

## Instructions

1. Read the relevant source files before making changes. The type system spans several tightly coupled files and changes in one area frequently require coordinated changes in others.

2. Use this reference to understand how the pieces connect. The sections below describe the Type class hierarchy, the normalization pipeline, the storage encoding layer, and the poly type system.

---

## Type Base Class (`synapse/lib/types.py`)

The `Type` class is the base for all data model types. Every form's primary value and every secondary property value is handled by a Type instance.

### Class Attributes

| Attribute | Default | Purpose |
|-----------|---------|---------|
| `stortype` | `None` | `STOR_TYPE_*` constant identifying the storage encoder |
| `ispoly` | `False` | Set only on `Poly` |
| `isarray` | `False` | Set only on `Array` |
| `ismutable` | `False` | Set on types whose normalized values can be modified in place (e.g., `Data`) |
| `_opt_defs` | `()` | Tuple of `(name, default)` pairs defining type-specific options |

### Instance Attributes

| Attribute | Purpose |
|-----------|---------|
| `modl` | The `Model` instance this type belongs to |
| `name` | Type name string (e.g., `'inet:fqdn'`, `'int'`, `'poly'`) |
| `info` | Metadata dict (bases, doc, interfaces, etc.) |
| `opts` | Merged options dict from `_opt_defs` + caller-supplied opts |
| `form` | Reference to the `Form` if this type is a form's primary type |
| `subof` | Parent type name if this type was created via `extend()` |
| `types` | Tuple of `(self.name,) + reversed(bases)` for type hierarchy |
| `typehash` | Interned GUID derived from class + normalized options; used as a stable identity for comparator dispatch |
| `locked` | Whether the type is locked (deprecated and blocked) |
| `deprecated` | Whether the type is deprecated (warns but still functional) |

### Initialization: Two-Phase Pattern

```
__init__(modl, name, info, opts, skipinit=False)
  1. Set instance fields, merge opts from _opt_defs
  2. Initialize empty dicts: _type_norms, _cmpr_ctors, virts, virtindx, virtstor, virtlifts
  3. Register default comparator constructors: =, !=, ~=, ^=, in=, range=
  4. Register default norm functions for Node and NodeRef
  5. Initialize storlifts dict with default lift functions
  6. If not skipinit: call postTypeInit(), then compute typehash

postTypeInit()
  - Override point for subclasses
  - Register type-specific norm functions via setNormFunc()
  - Set up virtual properties in self.virts
  - Configure custom comparators via setCmprCtor()
  - Validate/process options
```

`skipinit=True` is used during `clone()` and `extend()` to defer `postTypeInit()` until after options are fully merged.

### Normalization Pipeline

Normalization converts an arbitrary input value into the canonical storage form.

**Registration:** `setNormFunc(pytype, func)` maps a Python type to an async normalizer.

**Dispatch:** `async norm(valu, view=None)` looks up `type(valu)` in `_type_norms` and calls the matching function. If no match, raises `BadTypeValu`.

**Return value:** Always a tuple `(normalized_value, info_dict)` where info may contain:
- `'subs'` -- Sub-property values: `{name: (typehash, norm, info)}`
- `'adds'` -- Form nodes to create: `((formname, norm, forminfo), ...)`
- `'virts'` -- Virtual property values: `{name: (count_or_value,)}`
- `'skipadd'` -- Boolean; skip automatic form node creation

**Example from `Str`:**
```python
def postTypeInit(self):
    self.setNormFunc(str, self._normPyStr)
    self.setNormFunc(int, self._normPyInt)  # coerce int to str

async def _normPyStr(self, valu, view=None):
    # apply lower/upper/strip/onespace/replace transforms
    # validate against enums/regex
    # extract regex capture groups as subs
    return valu, info
```

### Options Pattern (`_opt_defs`)

Each Type subclass declares its options as a tuple of `(name, default)` pairs:

```python
class Int(IntBase):
    _opt_defs = (
        ('size', 8),
        ('signed', True),
        ('min', None),
        ('max', None),
        ('enums', None),
        ('enums:strict', True),
        ('fmt', '%d'),
        ('ismin', False),
        ('ismax', False),
    )
```

During `__init__`, the base class copies defaults, validates that all caller-supplied keys exist in defaults, and merges. Access via `self.opts.get('name')`.

### Virtual Properties

Virtual properties are computed values exposed as sub-properties on a type. They are not stored directly but can be indexed and queried.

**Four dictionaries:**

| Dict | Key | Value | Purpose |
|------|-----|-------|---------|
| `virts` | prop name | `(Type, getter_func)` | Define the virtual property and how to compute it from a normalized value |
| `virtindx` | prop name | index name or `None` | Storage index name for this virt (None = not stored in its own index) |
| `virtstor` | prop name | setter_func | Only for editable virts; signature: `async setter(valu, newvirt) -> (new_norm, info)` |
| `virtlifts` | prop name | `{cmpr: lift_func}` | Storage-optimized lift functions for this virt's comparisons |

**Example from `Ival`:**
```python
self.virts |= {
    'min': (self.timetype, self._getMin),
    'max': (self.timetype, self._getMax),
}
self.virtindx |= {'min': None, 'max': None}
self.virtstor |= {'min': self._storVirtMin, 'max': self._storVirtMax}
self.virtlifts |= {
    'min': {'<': self._storLiftMin, '>': self._storLiftMin, ...},
}
```

### Comparator System

Comparators are registered via `setCmprCtor(name, func)` and retrieved via `getCmprCtor(name)`.

**Default comparators** (registered in `__init__`): `=`, `!=`, `~=`, `^=`, `in=`, `range=`

**Comparator constructor pattern:** An async function that takes the RHS value, normalizes it, and returns a closure that compares against any LHS value:

```python
async def _ctorCmprEq(self, text):
    norm, info = await self.norm(text)
    async def cmpr(valu):
        return norm == valu
    return cmpr
```

### Storage Lifts (`storlifts`)

The `storlifts` dict maps comparison operators to async functions that convert a filter expression into storage-layer comparison tuples:

```python
self.storlifts = {
    '=': self._storLiftNorm,
    '~=': self._storLiftRegx,
    '?=': self._storLiftSafe,
    'in=': self._storLiftIn,
    'range=': self._storLiftRange,
}
```

Each lift function returns a tuple of `(cmpr, norm_value, stortype)` triples. These are passed to the Layer for LMDB index scanning.

**`async getStorCmprs(cmpr, valu, virts=None)`** is the main entry point. If `virts` is provided, it delegates to the virtual property's lift functions or the virtual type's `getStorCmprs`.

### Key Methods

| Method | Purpose |
|--------|---------|
| `norm(valu, view=None)` | Normalize a value to canonical form |
| `repr(norm)` | Human-readable string from normalized value |
| `tostorm(valu)` | Make value safe for Storm runtime (deep-copy mutables, wrap poly in NodeRef) |
| `clone(opts)` | Create new instance of same type with different options |
| `extend(name, opts, info)` | Create a named sub-type inheriting from this type |
| `getStorType(valu)` | Return the stortype constant for a specific value (usually just `self.stortype`) |
| `getStorCmprs(cmpr, valu, virts)` | Convert a filter to storage comparisons |
| `getCmprCtor(name)` | Get comparator constructor by name |
| `getVirtType(virts)` | Walk virt chain and return the Type at the end |
| `getVirtIndx(virts)` | Get the storage index name for a virtual property |
| `getVirtGetr(virts)` | Get getter function chain for a virtual property |
| `pack()` | Serialize type definition for RPC/storage |

---

## Type Subclasses

### Complete List

| Class | stortype | Options | Notes |
|-------|----------|---------|-------|
| `Bool` | `STOR_TYPE_U8` | -- | Normalizes str/int/bool to 0 or 1 |
| `Str` | `STOR_TYPE_UTF8` | enums, regex, lower, strip, upper, replace, onespace, globsuffix | Broad coercion (int, bool, float all accepted) |
| `Taxon` | `STOR_TYPE_UTF8` | -- | Str subclass for taxonomy classifiers |
| `Taxonomy` | `STOR_TYPE_UTF8` | -- | Str subclass for full taxonomies |
| `Tag` | `STOR_TYPE_UTF8` | -- | Dot-separated tag string |
| `TagPart` | `STOR_TYPE_UTF8` | -- | Single tag component |
| `Hex` | `STOR_TYPE_UTF8` | size, zeropad | Hex string with optional fixed size |
| `Int` | dynamic | size, signed, min, max, enums, enums:strict, fmt, ismin, ismax | stortype from `intstors[(size, signed)]` |
| `Float` | `STOR_TYPE_FLOAT64` | min, max, minisvalid, maxisvalid | IEEE 754 double |
| `HugeNum` | `STOR_TYPE_HUGENUM` | units, modulo | Arbitrary precision decimal |
| `Bool` | `STOR_TYPE_U8` | -- | True/false |
| `Time` | `STOR_TYPE_TIME` / `MINTIME` / `MAXTIME` | ismin, ismax, maxfill, precision | Microsecond timestamps |
| `Duration` | `STOR_TYPE_U64` | signed | Microsecond duration |
| `Velocity` | `STOR_TYPE_I64` | relative | Meters per second |
| `Ival` | `STOR_TYPE_IVAL` | precision | Time interval (min, max); virts: min, max, duration, precision |
| `Loc` | `STOR_TYPE_LOC` | -- | Lat/lon coordinate |
| `Guid` | `STOR_TYPE_GUID` | -- | 16-byte GUID; `'*'` generates new |
| `Comp` | `STOR_TYPE_MSGP` | fields, sepr | Composite of named typed fields |
| `Ndef` | `STOR_TYPE_NDEF` | forms, interface | Node definition (form, value); virt: form |
| `Array` | `STOR_FLAG_ARRAY \| elem.stortype` | type, uniq, sorted, split, typeopts | Container; virt: size |
| `Poly` | `STOR_TYPE_POLY` | forms, interfaces, default_forms | Polymorphic; virts: form, value |
| `Data` | `STOR_TYPE_MSGP` | schema | Arbitrary JSON-safe data; `ismutable=True` |
| `NodeProp` | `STOR_TYPE_NODEPROP` | -- | Node property reference |
| `Range` | `STOR_TYPE_MSGP` | type, typeopts | Min/max range of a sub-type |
| `TimePrecision` | `STOR_TYPE_U8` | -- | Time precision enum |

### Int stortype Selection

The `Int` type dynamically selects its stortype based on `(size, signed)` via the module-level `intstors` dict:

```python
intstors = {
    (1, True): STOR_TYPE_I8,   (1, False): STOR_TYPE_U8,
    (2, True): STOR_TYPE_I16,  (2, False): STOR_TYPE_U16,
    (4, True): STOR_TYPE_I32,  (4, False): STOR_TYPE_U32,
    (8, True): STOR_TYPE_I64,  (8, False): STOR_TYPE_U64,
    (16, True): STOR_TYPE_I128, (16, False): STOR_TYPE_U128,
}
```

### Array Type and Poly Interaction

In `Array.postTypeInit()`, the element type name undergoes the same auto-detection as `processPropdefs()`: if the name matches a known form or interface (with no typeopts), it is converted to a poly type automatically. See the Poly Types section below.

```python
if not typeopts:
    if typename in self.modl.ifaces or \
       ((forminfo := self.modl.forminfos.get(typename)) is not None and not forminfo.get('runt')):
        typename = (typename,)

if isinstance(typename, tuple):
    typeopts['forms'] = tuple(tname for tname in typename if tname in self.modl.forminfos)
    typeopts['interfaces'] = tuple(tname for tname in typename if tname in self.modl.ifaces)
    typename = 'poly'
```

---

## Storage Layer (`synapse/lib/layer.py`)

The storage layer encodes normalized type values into LMDB index keys for efficient lifting (querying). The bridge between the type system and storage is the `stortype` integer constant.

### STOR_TYPE Constants

| Constant | Value | Encoder Class |
|----------|-------|---------------|
| `STOR_TYPE_UTF8` | 1 | `StorTypeUtf8` |
| `STOR_TYPE_U8` | 2 | `StorTypeInt(size=1, signed=False)` |
| `STOR_TYPE_U16` | 3 | `StorTypeInt(size=2, signed=False)` |
| `STOR_TYPE_U32` | 4 | `StorTypeInt(size=4, signed=False)` |
| `STOR_TYPE_U64` | 5 | `StorTypeInt(size=8, signed=False)` |
| `STOR_TYPE_I8` | 6 | `StorTypeInt(size=1, signed=True)` |
| `STOR_TYPE_I16` | 7 | `StorTypeInt(size=2, signed=True)` |
| `STOR_TYPE_I32` | 8 | `StorTypeInt(size=4, signed=True)` |
| `STOR_TYPE_I64` | 9 | `StorTypeInt(size=8, signed=True)` |
| `STOR_TYPE_GUID` | 10 | `StorTypeGuid` |
| `STOR_TYPE_TIME` | 11 | `StorTypeTime` (extends StorTypeInt I64) |
| `STOR_TYPE_IVAL` | 12 | `StorTypeIval` |
| `STOR_TYPE_MSGP` | 13 | `StorTypeMsgp` |
| `STOR_TYPE_LATLONG` | 14 | `StorTypeLatLon` |
| `STOR_TYPE_LOC` | 15 | `StorTypeLoc` |
| `STOR_TYPE_TAG` | 16 | `StorTypeTag` |
| `STOR_TYPE_FQDN` | 17 | `StorTypeFqdn` |
| `STOR_TYPE_U128` | 19 | `StorTypeInt(size=16, signed=False)` |
| `STOR_TYPE_I128` | 20 | `StorTypeInt(size=16, signed=True)` |
| `STOR_TYPE_MINTIME` | 21 | `StorTypeTime` (min variant) |
| `STOR_TYPE_FLOAT64` | 22 | `StorTypeFloat` |
| `STOR_TYPE_HUGENUM` | 23 | `StorTypeHugeNum` |
| `STOR_TYPE_MAXTIME` | 24 | `StorTypeTime` (max variant) |
| `STOR_TYPE_NDEF` | 25 | `StorTypeNdef` |
| `STOR_TYPE_IPADDR` | 26 | `StorTypeIPAddr` |
| `STOR_TYPE_ARRAY` | 27 | `StorTypeArray` |
| `STOR_TYPE_NODEPROP` | 28 | `StorTypeNodeProp` |
| `STOR_TYPE_POLY` | 29 | `StorTypePoly` |

### Flags and Masks

| Constant | Value | Purpose |
|----------|-------|---------|
| `STOR_FLAG_ARRAY` | `0x8000` | OR'd with element stortype for array properties |
| `STOR_FLAG_POLY` | `0x4000` | OR'd with real stortype for poly properties |
| `STOR_MASK_ARRAY` | `0x7fff` | Mask to extract element type from array stortype |
| `STOR_MASK_POLY` | `0xbfff` | Mask to extract real type from poly stortype |

### Dispatch Table

The Layer class builds `self.stortypes`, a list indexed by `STOR_TYPE_*` constant, during initialization. Each entry is a `StorType` subclass instance. Encoding dispatch is:

```python
self.stortypes[stortype].indx(valu)
```

### StorType Base Class

Every `StorType` subclass implements:

| Method | Purpose |
|--------|---------|
| `indx(valu)` | Encode a normalized value into a tuple of index byte strings |
| `decodeIndx(bytz)` | Reverse an index encoding back to a value (returns `novalu` if lossy) |
| `indxBy(liftby, cmpr, valu)` | Dispatch a lift operation to the appropriate lifter function |

Lifter functions are registered in `self.lifters` and map comparison operator strings to async generators that yield `(lkey, nid)` pairs from LMDB.

### Index Key Encoding Examples

**Strings (`StorTypeUtf8`):**
- UTF-8 encode, truncate to 256 bytes
- If longer than 256 bytes, append xxhash64 suffix for collision resistance
- `decodeIndx` returns `novalu` for truncated strings

**Signed Integers (`StorTypeInt`):**
- Add offset `2^(bits-1) - 1` to make negative values sort correctly in lexicographic order
- Encode as big-endian bytes
- Example (I8): -1 encodes as `0x7E`, 0 as `0x7F`, 1 as `0x80`

**FQDNs (`StorTypeFqdn`):**
- Reverse the domain string before UTF-8 encoding
- Enables efficient subdomain prefix matching (e.g., `^=com.google.` matches all `*.google.com`)

**Lat/Lon (`StorTypeLatLon`):**
- Scale to integers: `(value * 10^8) + space_offset`
- Encode as lon (5 bytes) + lat (5 bytes)
- Lon-first ordering enables spatial range queries

**Poly (`StorTypePoly`):**
- Prefix: 2-byte real stortype (big-endian) + 8-byte form abbreviation
- Suffix: the real type's encoded index bytes
- This structure enables both form-specific and cross-form queries

### LMDB Index Key Structure

Every index entry stored in LMDB follows this pattern:

```
KEY:   <abbreviation> + <encoded_value>
VALUE: <node_id (nid)>
```

The abbreviation encodes the index type, form, and property:

| Index Prefix | Constant | Components |
|-------------|----------|------------|
| `INDX_PROP` | `\x00\x00` | form abrv + prop abrv |
| `INDX_ARRAY` | `\x00\x02` | form abrv + prop abrv |
| `INDX_TAGPROP` | `\x00\x01` | form abrv + tag abrv + prop abrv |
| `INDX_TAG` | `\x00\x07` | form abrv + tag abrv |
| `INDX_IVAL_MAX` | `\x00\x0a` | form abrv + prop abrv |
| `INDX_IVAL_DURATION` | `\x00\x0b` | form abrv + prop abrv |

### Storage Flow (`_editPropSet`)

When a property value is stored:

1. `getStorIndx(stortype, valu, virts=virts)` dispatches to the StorType encoder
2. For arrays: recursively encodes each element, also stores array-level index with length
3. For poly: prepends 2-byte real stortype + 8-byte form abbreviation
4. Index entries are written to LMDB as `(abrv + indx_bytes, nid)` pairs

### Lift Flow

When a query filters or lifts by property value:

1. `Type.getStorCmprs(cmpr, valu)` produces `(cmpr, norm_value, stortype)` tuples
2. Layer dispatches to `stortypes[stortype].indxBy(liftby, cmpr, norm_value)`
3. The StorType's lifter encodes the value and calls the appropriate LMDB scan:
   - `keyNidsByDups(indx)` for exact match (`=`)
   - `keyNidsByPref(indx)` for prefix match (`^=`)
   - `keyNidsByRange(min, max)` for range queries (`<`, `>`, `range=`)
4. The LMDB Slab (`synapse/lib/lmdbslab.py`) executes the scan via `scanByDups`, `scanByPref`, or `scanByRange`

### IndxBy Classes

`IndxBy` subclasses encapsulate the LMDB abbreviation and database reference for a specific index path:

| Class | Index Type | Purpose |
|-------|-----------|---------|
| `IndxByForm` | `INDX_PROP[form][None]` | Lift all nodes of a form |
| `IndxByProp` | `INDX_PROP[form][prop]` | Lift by property value |
| `IndxByPropArray` | `INDX_ARRAY[form][prop]` | Lift by array element value |
| `IndxByPropArraySize` | `INDX_ARRAY` | Lift by array length |
| `IndxByPropIvalMin/Max` | `INDX_PROP` / `INDX_IVAL_MAX` | Lift by interval min or max |
| `IndxByPoly` | `INDX_PROP[form][prop] + type_bytes` | Lift poly values with type prefix |
| `IndxByPolyArray` | `INDX_ARRAY[form][prop] + type_bytes` | Lift poly array elements |
| `IndxByTagProp` | `INDX_TAGPROP[form][tag][prop]` | Lift by tag property value |
| `IndxByVirt` | varies | Virtual property index |

---

## Poly Types

Poly (polymorphic) types allow a single secondary property to hold a value from one of several different forms or interfaces. The `Poly` class is defined in `synapse/lib/types.py` and the automatic insertion logic lives in `synapse/datamodel.py`.

### Automatic Poly Insertion

When defining secondary properties in a model, you do NOT need to explicitly use the `poly` type name. The data model parser (`Model.processPropdefs()` in `datamodel.py`) automatically converts a property definition to a poly type when:

1. The type name matches a known **form** (non-runt) or **interface** and no type options are provided.
2. The type name is a **tuple** of form/interface names.

The same auto-detection logic exists in `Array.postTypeInit()` for array element types.

### Defining Poly Properties in Model Code

**Single form/interface (auto-detected):**
```python
# The parser sees 'inet:fqdn' is a form name and wraps it in poly.
('target', ('inet:fqdn', {}), {}),

# The parser sees 'test:interface' is an interface name and wraps it in poly.
('ref', ('test:interface', {}), {}),
```

**Multiple forms/interfaces (tuple syntax):**
```python
('poly', (('test:str', 'test:int', 'inet:server', 'test:interface'), {
    'default_forms': ('test:int', 'test:str'),
}), {}),
```

**Poly arrays:**
```python
('polyarry', ('array', {
    'type': ('test:str', 'test:int', 'inet:server'),
    'typeopts': {'default_forms': ('test:int', 'test:str')},
}), {}),
```

### Poly Type Options

| Option | Purpose |
|--------|---------|
| `forms` | Tuple of allowed form names. Set automatically from the tuple of names during parsing. |
| `interfaces` | Tuple of allowed interface names. Forms implementing any listed interface are accepted. Set automatically from the tuple of names during parsing. |
| `default_forms` | Optional tuple of form names tried in order when normalizing a bare value. If only one form is allowed and no interfaces, it becomes the default automatically. |

### Poly Normalization (`Poly.norm()`)

1. If the value is a **Storm Node**, its ndef is used directly (if the node's form passes the filter).
2. If the value is a **NodeRef** `(form, value)` tuple and the form is valid, its ndef is used directly if the node already exists, otherwise the value is re-normalized via that form's type.
3. Otherwise, **default forms** are tried in order. The first form whose type successfully normalizes the value wins. If normalization succeeds, the Cortex checks the current view for an existing node to avoid duplicate creation.
4. If no default forms match, `BadTypeValu` is raised.

The normalized value is always a tuple: `(formname, normalizedvalue)`.

### Poly Virtual Properties

Every poly property exposes two virtual sub-properties:

- **`form`** -- returns the form name of the stored value (e.g., `'inet:fqdn'`).
- **`value`** -- returns the raw normalized value.

Additional virtual properties from the underlying form's type are accessible via deref on the Storm `NodeRef` object (e.g., `:poly.port` on an `inet:server` value).

### Poly Storage and Indexing

Poly values are stored with `STOR_FLAG_POLY | form.type.stortype`. The `getStorIndx` method in Layer prepends the 2-byte real stortype and 8-byte form abbreviation before the real type's encoded bytes. This enables:

- **Form-specific lifts**: filter by form abbreviation prefix
- **Cross-form comparisons**: `getStorCmprs()` fans out across all allowed types, collecting valid storage comparators and flagging them with `STOR_FLAG_POLY`

### Poly Comparisons (`getCmprCtor`)

Poly comparisons (e.g., `:poly > 2`, `:poly = somestr`) fan out across all allowed types. Each type's comparator constructor is called with the value; types that raise `BadTypeValu` are silently skipped. A match on any type's comparator returns true. When comparing against a `NodeRef`, an exact ndef match is checked first.

### Storm Representation: NodeRef (`synapse/lib/stormtypes.py`)

Poly values are exposed in Storm as `NodeRef` objects wrapping `(formname, formvalue)`. NodeRef provides:

- `.form` -- the form name string
- `.value` -- the raw value
- `.ndef` -- the `(form, value)` tuple
- `.isform(name)` -- returns true if the value is of the given form (or list of forms); checks `form.formtypes` so inherited types match
- Deref (`.propname`) -- resolves against virtual properties from the value's type, then falls back to primitive deref

### Polyprops Registration (`datamodel.py`)

When a poly-typed `Prop` is initialized, it registers itself in lookup dictionaries for reverse lookups ("which properties reference form X?"):

- `Model.propsbytype[formname]` -- for each explicitly allowed form
- `Model.polypropsbyiface[ifacename]` -- for each allowed interface
- `Model.polyarraysbyiface[ifacename]` -- for array-of-poly properties

`Model.getPropsByType(name)` and `Model.getArrayPropsByType(name)` merge direct type matches with interface-based poly matches, so pivots and reverse lookups include poly properties.

---

## Key Files

| File | What |
|------|------|
| `synapse/lib/types.py` | `Type` base class, all Type subclasses including `Poly`, `Array`, `Comp`, `Ndef` |
| `synapse/datamodel.py` | `Model`, `Prop`, `Form` classes; `processPropdefs()` (poly auto-insertion); polyprop registration and reverse lookups |
| `synapse/lib/layer.py` | `STOR_TYPE_*` / `STOR_FLAG_*` constants; `StorType` subclasses (encoding/decoding); `IndxBy` classes (lift dispatch); `getStorIndx()` and `_editPropSet()` (storage); `stortypes[]` dispatch table |
| `synapse/lib/lmdbslab.py` | `Slab` class wrapping LMDB; `scanByDups`, `scanByPref`, `scanByRange` |
| `synapse/lib/stormtypes.py` | `NodeRef` class (Storm representation of poly values) |
| `synapse/tests/test_datamodel.py` | `test_datamodel_polyprop` and related tests |
| `synapse/tests/test_types.py` | Type normalization and comparison tests |
| `synapse/tests/utils.py` | Test model definitions with poly property examples |
