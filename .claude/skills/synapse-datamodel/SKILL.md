# Synapse Data Model Skill

TRIGGER: When the user asks questions about the Synapse data model, needs help choosing forms or properties, is designing Storm queries that require knowledge of available forms/properties/edges, is building power-up ingest logic, or is authoring Storm code that creates or modifies nodes.

## Instructions

1. Run `python -m synapse.tools.cortex.docmodel` to generate the current data model documentation from a temporary Cortex. This produces a markdown reference of all forms, their properties (with types and descriptions), light edges, tag properties, and interfaces.

   For focused lookups, use the targeted flags instead of loading the entire model:
   - `--form <form>` — detailed docs for a single form: base type, interfaces, properties table, Referenced Types, and Source/Target Edges (with Storm `-(verb)>` notation).
   - `--interface <iface>` — detailed docs for a single interface: properties, implementing forms, and Referenced Types.

2. Read the generated output thoroughly to understand the available forms, properties, types, and edges before answering the user's question.

3. Use the data model output to:
   - **Answer data model questions**: Identify the correct forms, properties, and types for representing concepts. Explain what properties are available on a form and what types they expect.
   - **Design Storm ingest logic**: Select the appropriate forms and properties for mapping external API data into the Synapse data model. Follow the standard power-up ingest patterns from the `storm-syntax` skill (meta:source tracking, try-add with `?=`, tag prefixing, edit parens for inline node creation).
   - **Author Storm queries**: Write correct lift, filter, pivot, and edit operations using actual form and property names from the model. Validate that forms and properties referenced in queries exist in the model.
   - **Suggest edges**: Identify relevant light edges for linking nodes together based on the edges section of the model output.
   - **Recommend modeling approaches**: When the user describes a real-world concept, recommend which forms and properties best represent it, and how to connect related nodes via properties and edges.

4. Always cite specific form and property names from the generated model output. Do not guess or hallucinate form/property names -- if a form or property does not appear in the output, say so.

5. When the user is connected to a live Cortex, use `python -m synapse.tools.cortex.docmodel --cortex <url>` instead, to capture any extended model from loaded Storm packages.


## Example Invocation

```bash
# Generate full model docs from a temporary Cortex (default/base model)
python -m synapse.tools.cortex.docmodel

# Generate model docs from a live Cortex (includes extended model from packages)
python -m synapse.tools.cortex.docmodel --cortex tcp://cortex:27492

# Save to a file for reference
python -m synapse.tools.cortex.docmodel --save /tmp/datamodel.md

# Detailed docs for a specific form (properties, Referenced Types, edges)
python -m synapse.tools.cortex.docmodel --form inet:fqdn

# Detailed docs for a specific interface (properties, implementing forms)
python -m synapse.tools.cortex.docmodel --interface meta:observable

# Single form from a live Cortex
python -m synapse.tools.cortex.docmodel --cortex tcp://cortex:27492 --form risk:attack
```
