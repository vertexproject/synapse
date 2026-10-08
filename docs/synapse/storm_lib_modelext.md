```mdstorm-setup
```

<a id="modelext"></a>


# Extended Model

<a id="modelext-overview"></a>


## Overview

The [`$lib.model.ext`](stormtypes_libs.md#stormlibs-lib-model-ext) Storm library extends the data model of a Cortex with custom elements. You can add:

- [Types](storm_lib_modelext.md#modelext-types), which set how values are normalized.
- [Forms](storm_lib_modelext.md#modelext-forms), which are new kinds of nodes.
- [Properties](storm_lib_modelext.md#modelext-props) on extended or built-in forms.
- [Tag properties](storm_lib_modelext.md#modelext-tagprops), which store a value with a tag on a node.
- [Edges](storm_lib_modelext.md#modelext-edges), which declare a light edge verb between two forms.

The names of extended model elements begin with an underscore (`_`), so they never conflict with built-in model elements. An extended type or form name also contains at least one colon (`:`), as in `_foocorp:name`.

You cannot remove an extended model element while it is in use. Remove the nodes, property values, tag property values, and edges which use it first (see [Removing Extended Elements](storm_lib_modelext.md#modelext-remove)).

Changing the extended model requires the `model.admin` permission. [`$lib.model.ext.addExtModel()`](stormtypes_libs.md#stormlibs-lib-model-ext-addExtModel) requires admin. Any user can read the extended model with [`$lib.model.ext.getExtModel()`](stormtypes_libs.md#stormlibs-lib-model-ext-getExtModel). See [Cortex Permissions](adminguide.md#admin_cortex_perms).

<a id="modelext-types"></a>


## Extended Types

[`$lib.model.ext.addType(typename, basetype, typeopts, typeinfo)`](stormtypes_libs.md#stormlibs-lib-model-ext-addType) adds a named type. It is derived from `basetype`, which may be any built-in or extended type except `array`. `typeopts` are the options of the base type (see [Types](datamodel_types.md)), and `typeinfo` is a dictionary of info values such as `doc`.

Add an integer type with values from 0 to 100, and a string type limited to a set of values:

```mdstorm --split
$lib.model.ext.addType(_foocorp:score, int, ({'min': 0, 'max': 100}), ({'doc': 'A Foocorp score between 0 and 100.'}))
$lib.model.ext.addType(_foocorp:classification, str, ({'enums': 'unknown,benign,malicious'}), ({'doc': 'A Foocorp classification.'}))
```

An extended type is how a property gets custom type options. A property typedef must name a type with empty options, so declare the options on an extended type and use its name in the property.

<a id="modelext-forms"></a>


## Extended Forms

[`$lib.model.ext.addForm(formname, basetype, typeopts, typeinfo)`](stormtypes_libs.md#stormlibs-lib-model-ext-addForm) adds a form. Its arguments work the same way as those of `addType()`, and `typeinfo` is a form info dictionary.

Add a form named `_foocorp:name` whose values are lowercased, with whitespace stripped from the beginning and end:

```mdstorm --split
$lib.model.ext.addForm(_foocorp:name, str, ({'lower': true, 'strip': true}), ({'doc': 'Foocorp name.'}))
```

<a id="modelext-props"></a>


## Extended Properties

[`$lib.model.ext.addFormProp(formname, propname, typedef, propinfo)`](stormtypes_libs.md#stormlibs-lib-model-ext-addFormProp) adds a property to a built-in or extended form.

- `propname` is the relative name of the property, such as `_score`.
- `typedef` is a `(typename, typeopts)` tuple. `typename` names a built-in or extended type, and `typeopts` must be empty (`({})`). To use type options, declare an [extended type](storm_lib_modelext.md#modelext-types).
- `propinfo` is a property info dictionary such as `({'doc': '...'})`.

An array property puts its element type in `typedef`, and its array options (`uniq`, `sorted`, or `split`) under the `array` key of `propinfo`.

Add a `_score` property and a unique `_aliases` array of `base:name` values to `_foocorp:name`, and a `_classification` property to the built-in `inet:fqdn` form:

```mdstorm --split
$lib.model.ext.addFormProp(_foocorp:name, _score, (_foocorp:score, ({})), ({'doc': 'Score for this name.'}))
$lib.model.ext.addFormProp(_foocorp:name, _aliases, (base:name, ({})), ({'doc': 'Aliases for this name.', 'array': {'uniq': true}}))
$lib.model.ext.addFormProp(inet:fqdn, _classification, (_foocorp:classification, ({})), ({'doc': 'Classification for this FQDN.'}))
```

The new form and properties are used like any other. The form value is normalized, and the duplicate alias is removed:

```mdstorm --split
[ _foocorp:name="  Visi " :_score=90 :_aliases=(visi, "visi stark", visi) ]
```

```mdstorm --split
[ inet:fqdn=vertex.link :_classification=benign ]
```

A value which is not valid for the property type is rejected:

```mdstorm --split --fail
_foocorp:name=visi [ :_score=101 ]
```

<a id="modelext-tagprops"></a>


## Extended Tag Properties

[`$lib.model.ext.addTagProp(propname, typedef, propinfo)`](stormtypes_libs.md#stormlibs-lib-model-ext-addTagProp) adds a tag property. `typedef` is a `(typename, typeopts)` tuple, and `propinfo` is a property info dictionary.

Add a `_score` tag property which uses the `_foocorp:score` type, then set and lift by it:

```mdstorm --split
$lib.model.ext.addTagProp(_score, (_foocorp:score, ({})), ({'doc': 'A Foocorp score for the tag.'}))
```

```mdstorm --split
inet:fqdn=vertex.link [ +#rep.foocorp:_score=80 ]
```

```mdstorm --split
#rep.foocorp:_score>50
```

A tag property must use an immutable type. `array` and `data` types, and any extended type based on them, are rejected:

```mdstorm --split --fail
$lib.model.ext.addTagProp(_notes, (data, ({})), ({}))
```

To store several values, set a tag property on more than one tag, or use an extended form property with an array type.

<a id="modelext-edges"></a>


## Extended Edges

[`$lib.model.ext.addEdge(n1form, verb, n2form, edgeinfo)`](stormtypes_libs.md#stormlibs-lib-model-ext-addEdge) declares a light edge. The verb must begin with an underscore (`_`). `n1form` and `n2form` are the source and target forms, and either may be `*` or `(null)` to allow any form. `edgeinfo` is an edge info dictionary.

Declare a `_seenon` edge from `_foocorp:name` nodes to `inet:fqdn` nodes, and use it:

```mdstorm --split
$lib.model.ext.addEdge(_foocorp:name, _seenon, inet:fqdn, ({'doc': 'The name was seen on the FQDN.'}))
```

```mdstorm --split
_foocorp:name=visi [ +(_seenon)> {[ inet:fqdn=vertex.link ]} ]
```

<a id="modelext-export"></a>


## Exporting and Importing

`$lib.model.ext.getExtModel()` returns a dictionary of every extended model element in the Cortex, with `types`, `forms`, `props`, `tagprops`, and `edges` keys. `$lib.model.ext.addExtModel(model)` adds the elements in such a dictionary to a Cortex, so you can copy an extended model from one Cortex to another.

```mdstorm --split
$model = $lib.model.ext.getExtModel()
for $key in (types, forms, props, tagprops, edges) {
    $lib.print(`{$key}: {$lib.len($model.$key)}`)
}
```

Run `addExtModel()` on the target Cortex with the dictionary from the source Cortex. Elements which already exist with the same definition are skipped. If an element exists with a different definition, nothing is added and an error is raised.

```mdstorm --split
$model = $lib.model.ext.getExtModel()
$lib.model.ext.addExtModel($model)
```

<a id="modelext-remove"></a>


## Removing Extended Elements

Remove extended elements in the reverse order they were added. An extended model element cannot be removed until all usage of it is removed from the graph.

Delete the edges, then the edge definition, with [`$lib.model.ext.delEdge(n1form, verb, n2form)`](stormtypes_libs.md#stormlibs-lib-model-ext-delEdge):

```mdstorm --split
_foocorp:name=visi [ -(_seenon)> {inet:fqdn=vertex.link} ]
```

```mdstorm --split
$lib.model.ext.delEdge(_foocorp:name, _seenon, inet:fqdn)
```

Remove the tag property values, then the tag property, with [`$lib.model.ext.delTagProp(propname, force=(false))`](stormtypes_libs.md#stormlibs-lib-model-ext-delTagProp):

```mdstorm --split
#rep.foocorp:_score [ -#rep.foocorp:_score ]
```

```mdstorm --split
$lib.model.ext.delTagProp(_score)
```

With `force=(true)`, `delTagProp()` first deletes the tag property from every node which has it.

[`$lib.model.ext.delFormProp(formname, propname, force=(false))`](stormtypes_libs.md#stormlibs-lib-model-ext-delFormProp) removes a property. With `force=(true)`, it first deletes the property from every node which has it:

```mdstorm --split
$lib.model.ext.delFormProp(inet:fqdn, _classification, force=(true))
```

Delete the nodes of an extended form, then remove its properties and the form with [`$lib.model.ext.delForm(formname)`](stormtypes_libs.md#stormlibs-lib-model-ext-delForm):

```mdstorm --split
_foocorp:name | delnode
```

```mdstorm --split
$lib.model.ext.delFormProp(_foocorp:name, _aliases)
$lib.model.ext.delFormProp(_foocorp:name, _score)
$lib.model.ext.delForm(_foocorp:name)
```

Remove the types last, with [`$lib.model.ext.delType(typename)`](stormtypes_libs.md#stormlibs-lib-model-ext-delType):

```mdstorm --split
$lib.model.ext.delType(_foocorp:classification)
$lib.model.ext.delType(_foocorp:score)
```
