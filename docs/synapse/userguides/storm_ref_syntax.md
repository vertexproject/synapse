```mdstorm-setup
```

<a id="storm-ref-syntax"></a>

# Storm Reference - Document Syntax Conventions

This section covers the following important conventions used within the Storm Reference Documents:

- [Storm and Layers](storm_ref_syntax.md#storm-and-layers)
- [Storm Syntax Conventions](storm_ref_syntax.md#storm-syntax-conventions)
- [Usage Statements vs. Specific Storm Queries](storm_ref_syntax.md#usage-statements-vs-example-storm-queries)
- [Type-Specific Behavior](data_model.md#type-specific-behavior)
- [Whitespace](storm_ref_syntax.md#whitespace)

## Storm and Layers

**The Storm Reference documentation provides basic syntax examples that assume a simple Storm environment - that is, a Cortex with a single Layer.** For multi-Layer Cortexes, the effects of specific Storm commands - particularly data modification commands - may vary based on the specific arrangement of read / write Layers, the Layer in which the command is executed, and the permissions of the user.

## Storm Syntax Conventions

The Storm Reference documentation provides numerous examples of both abstract Storm syntax (usage statements) and example Storm queries. The following conventions are used for Storm usage statements:

- Items that must be entered literally on the command line are in **bold.** These items include command names and literal characters.

- Items that represent "variables" that must be replaced with a name or value are placed within angle brackets ( `< >` ) in *italics*. Most "variables" are self-explanatory, however a few commonly used variable terms are defined here for convenience:
  
  - *\<form\>* refers to a form / node primary property, such as `inet:fqdn`. *\<form\>* includes forms that participate in [form inheritance](../glossary.md#form-inheritance) (e.g., parent forms, extended forms) unless otherwise noted. We may use *\<parent_form\>* to emphasize when an example specifically references usage or behavior related to form inheritance.
  - *\<interface\>* refers to an [interface](../glossary.md#interface).
  - *\<valu\>* refers to the value of a primary property, such as `woot.com` in `inet:fqdn=woot.com`.
  - *\<prop\>* refers to a node secondary property (including meta, virtual, and extended properties) such as `inet:ip:asn` or `inet:ip.created`.
  - *\<pval\>* refers to the value of a secondary property, such as `4808` in `inet:ip:asn=4808`.
  - *\<query\>* refers to a Storm query.
  - *\<inet:fqdn\>* refers to a Storm query whose results contain the specified form(s).
  - *\<tag\>* refers to a tag (`#sometag` as opposed to a `syn:tag` form).

- **Bold brackets** are literal characters. Parameters enclosed in non-bolded brackets are optional.

- Parameters **not** enclosed in brackets are required.

- A vertical bar signifies that you choose only one parameter. For example:
  
  - a | b indicates that you must choose a or b.
  - [ a | b ] indicates that you can choose a, b, or nothing (the non-bolded brackets indicate the parameter is optional).

- Ellipses ( <span class="title-ref">...</span> ) signify the parameter can be repeated on the command line.

**Example:**

**\[** *\<form\>* **=** *\<valu\>* \[ **:** | **.** | **:_** *\<prop\>* **=** *\<pval\>* ... \] **\]**

The Storm query above adds a new node.

- The outer brackets are in **bold** and are required literal characters to specify a data modification (add) operation. Similarly, the equals signs are in **bold** to indicate literal characters.
- *\<form\>* and *\<valu\>* need to be replaced by the specific form (such as `inet:ip`) and primary property value (such as `1.2.3.4`) for the node being created.
- The inner brackets are not bolded and indicate that one or more secondary properties can **optionally** be specified.
- The property separator characters are **bold** (as required literals), but appear between non-bolded pipe characters (indicating that you must use / choose one). The colon is used for "standard" secondary properties, the dot is used for virtual properties, and the colon/underscore is used for extended properties.
- *\<prop\>* and *\<pval\>* need to be replaced by the specific property name and value to add to the node, such as `:place:loc=us`.
- The ellipsis ( `...` ) indicate that additional secondary properties can optionally be specified.

## Usage Statements vs. Example Storm Queries

Example Storm queries may be presented in `code font`, but are typically displayed in query boxes. Example queries may be fully literal (e.g., they can be run exactly as shown), or they may be pseudo-code (e.g., where terms in angle brackets like `<query>` or `<inet:ip>` substitute for literals). Full queries are used where possible, but pseudo-code may be used to simplify a query in order to focus on syntax.

Example queries may or may not include results (the output of the query). Results are included where they help to illustrate the behavior of the query; they may be omitted where the emphasis of the example is on the query syntax.

**Example queries:**

``` text
  [ inet:ip=1.2.3.4 :place:loc=us ]
```

``` text
  <inet:dns:a> -> inet:ip
```

```mdstorm
  [ inet:ip=1.2.3.4 :place:loc=us ]
```

## Type-Specific Behavior

Some data types within the Synapse data model have been optimized in ways that impact their behavior within Storm queries (e.g., how types can be entered, lifted, filtered, etc.) See [Storm Reference - Type-Specific Storm Behavior](storm_ref_type_specific.md#storm-ref-type-specific) for details.

## Whitespace

Whitespace in Storm is required in some circumstances and optional in others. We may make use of optional whitespace in the examples for readability. See the section on [whitespace and literals](storm_ref_intro.md#whitespace-and-literals-in-storm) for details on whitespace requirements in Storm. 
