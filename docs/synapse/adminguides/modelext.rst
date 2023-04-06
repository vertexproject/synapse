.. _admin_extend_model:

Add Extended Model Elements
###########################

The Synapse data model in a Cortex can be extended with custom `forms`_ or `properties`_ by using the model
extension Storm Library (:ref:`stormlibs-lib-model-ext`). Extended model forms and properties must have names
beginning with an underscore (``_``) to avoid potential conflicts with built-in model elements.

Extended Forms
==============

When adding a form, ``$lib.model.ext.addForm`` takes the following arguments:

``formname``
    Name of the form, must begin with an underscore (``_``) and contain at least one colon (``:``).

``basetype``
    The `Synapse data model type`_ for the form.

``typeopts``
    A dictionary of type specific options.

``typeinfo``
    A dictionary of info values for the form.

To add a new form named ``_foocorp:name``, which contains string values which will be normalized to
lowercase, with whitespace stripped from the beginning/end::

    $typeopts = ({'lower': $lib.true, 'strip': $lib.true})
    $typeinfo = ({'doc': 'Foocorp name.'})

    $lib.model.ext.addForm(_foocorp:name, str, $typeopts, $typeinfo)

If the form is no longer in use and there are no nodes of this form in the Cortex, it can be removed with::

    $lib.model.ext.delForm(_foocorp:name)

Extended Properties
===================

When adding properties, ``$lib.model.ext.addFormProp`` takes the following arguments:

``formname``
    Name of the form to add the property to, may be a built-in or extended model form.

``propname``
    Relative name of the property, must begin with an underscore (``_``).

``typedef``
    A tuple of (``type``, ``typeopts``) which defines the type for the property

``propinfo``
    A dictionary of info values for the property.

To add a property named ``_score`` to the ``_foocorp:name`` form which contains int values between 0 and 100::

    $typeopts = ({'min': 0, 'max': 100})
    $propinfo = ({'doc': 'Score for this name.'})

    $lib.model.ext.addFormProp(_foocorp:name, _score, (int, $typeopts), $propinfo)

To add a property named ``_aliases`` to the ``_foocorp:name`` form which contains a unique array of
``ou:name`` values::

    $typeopts = ({'type': 'ou:name', 'uniq': $lib.true})
    $propinfo = ({'doc': 'Aliases for this name.'})

    $lib.model.ext.addFormProp(_foocorp:name, _aliases, (array, $typeopts), $propinfo)

Properties may also be added to existing forms, for example, to add a property named ``_classification`` to
``inet:fqdn`` which must contain a string from a predefined set of values::

    $typeopts = ({'enums': 'unknown,benign,malicious'})
    $propinfo = ({'doc': 'Classification for this FQDN.'})

    $lib.model.ext.addFormProp(inet:fqdn, _classification, (str, $typeopts), $propinfo)

Extended Universal Properties
=============================

Similar to ``$lib.model.ext.addFormProp``, ``$lib.model.ext.addUnivProp`` takes the same ``propname``,
``typedef``, and ``propinfo`` arguments, but applies to all forms.

.. _`forms`: https://synapse.docs.vertex.link/en/latest/synapse/glossary.html#form-extended
.. _`properties`: https://synapse.docs.vertex.link/en/latest/synapse/glossary.html#property-extended

.. _Synapse data model type: autodocs/datamodel_types.html
