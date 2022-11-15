.. _adminguide:


Synapse Admin Guide
###################

This guide is designed for use by Synapse "global admins" who are typically power-users with ``admin=true`` permissions on
the Cortex and are responsible for non-devops configuration and management of a Synapse deployment. This guide focuses on
using Storm to accomplish administration tasks and discusses conventions and permissions details for the Cortex.

Common Admin Tasks
==================

Enabling Synapse Power-Ups
--------------------------

The Vertex Project provides a number of Power-Ups that extend the functionality of Synapse. For more information on
configuring your Cortex to use Rapid Power-Ups, see `the blog post on Synapse Power-Ups`_.

Configuring a Mirrored Layer
----------------------------

A Cortex may be configured to mirror a layer from a remote Cortex which will synchronize all edits from the remote layer
and use write-back support to facilitate edits originating from the downstream layer.  The mirrored layer will be an exact
copy of the layer on the remote system including all edit history and will only allow changes which are first sent to the
upstream layer.

When configuring a mirrored layer, you may choose to mirror from a remote layer *or* from the top layer of a remote view.
If you choose to mirror from the top layer of a remote view, that view will have the opportunity to fire triggers and enforce
model constraints on the changes being provided by the mirrored layer.

To specify a remote layer as the upstream, use a Telepath URL which includes the shared object ``*/layer/<layeriden>`` such as::

    aha://cortex.loop.vertex.link/*/layer/8ea600d1732f2c4ef593120b3226dea3

To specify a remote view, use the shared object ``*/view/<viewiden>`` such as::

     aha://cortex.loop.vertex.link/*/view/8ea600d1732f2c4ef593120b3226dea3

When you specify a ``--mirror`` option to the ``layer.add`` command or within a layer definition provided to the ``$lib.layer.add()``
Storm API the telepath URL will not be checked.  This allows configuration of a remote layer or view which is not yet provisioned
or is currently offline.

.. note::

    To allow write access, the telepath URL must allow admin access to the remote Cortex due to being able to fabricate edit
    origins. The telepath URL may use aliased names or TLS client side certs to prevent credential disclosure.

Once a mirrored layer is configured, it will need to stream down the entire history of events from the upstream layer.  During
this process, the layer will be readable but writes will hang due to needing to await the write-back to be fully caught up to
guarantee that edits are immediately observable like a normal layer.  During that process, you may track progress by calling
the ``getMirrorStatus()`` API on the ``storm:layer`` object within the Storm runtime.

Add Extended Model Elements
---------------------------

The Synapse data model in a Cortex can be extended with custom forms and properties 
by using the model extension Storm Library (:ref:`stormlibs-lib-model-ext`). Extended model
forms and properties must have names beginning with an underscore (``_``) to avoid potential
conflicts with built-in model elements.

When adding a form, ``$lib.model.ext.addForm`` takes the following arguments:

``formname``
    Name of the form, must begin with an underscore (``_``) and contain at least one colon (``:``).

``basetype``
    The `Synapse data model type`_ for the form.

``typeopts``
    A dictionary of type specific options.

``typeinfo``
    A dictionary of info values for the form.

To add a new form named ``_foocorp:name``, which contains string values which will be
normalized to lowercase, with whitespace stripped from the beginning/end::

    $typeopts = ({'lower': $lib.true, 'strip': $lib.true})
    $typeinfo = ({'doc': 'Foocorp name.'})

    $lib.model.ext.addForm(_foocorp:name, str, $typeopts, $typeinfo)

If the form is no longer in use and there are no nodes of this form in the Cortex, it can be removed with::

    $lib.model.ext.delForm(_foocorp:name)

When adding properties, ``$lib.model.ext.addFormProp`` takes the following arguments:

``formname``
    Name of the form to add the property to, may be a built-in or extended model form.

``propname``
    Relative name of the property, must begin with an underscore (``_``).

``typedef``
    A tuple of (``type``, ``typeopts``) which defines the type for the property

``propinfo``
    A dictionary of info values for the property.

To add a property named ``_score`` to the ``_foocorp:name`` form which contains
int values between 0 and 100::

    $typeopts = ({'min': 0, 'max': 100})
    $propinfo = ({'doc': 'Score for this name.'})

    $lib.model.ext.addFormProp(_foocorp:name, _score, (int, $typeopts), $propinfo)

To add a property named ``_aliases`` to the ``_foocorp:name`` form which contains a unique array
of ``ou:name`` values::

    $typeopts = ({'type': 'ou:name', 'uniq': $lib.true})
    $propinfo = ({'doc': 'Aliases for this name.'})

    $lib.model.ext.addFormProp(_foocorp:name, _aliases, (array, $typeopts), $propinfo)

Properties may also be added to existing forms, for example, to add a property named
``_classification`` to ``inet:fqdn`` which must contain a string from a predefined set of
values::

    $typeopts = ({'enums': 'unknown,benign,malicious'})
    $propinfo = ({'doc': 'Classification for this FQDN.'})

    $lib.model.ext.addFormProp(inet:fqdn, _classification, (str, $typeopts), $propinfo)


Similar to ``$lib.model.ext.addFormProp``, ``$lib.model.ext.addUnivProp`` takes the same
``propname``, ``typedef``, and ``propinfo`` arguments, but applies to all forms.

.. _Synapse data model type: autodocs/datamodel_types.html
.. _the blog post on Synapse Power-Ups: https://vertex.link/blogs/synapse-power-ups/
