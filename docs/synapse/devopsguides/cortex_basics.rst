Cortex: Synapse Hypergraph
==========================

Introduction
------------
Within Synapse, a Cortex is a "key-value based linkless hypergraph" implementation.
A Cortex allows the creation and retrieval of nodes which adhere to a data model
which is itself inspectable and represented within the Cortex.  Each node consists
of a Globally Unique Identifier (GUID) and a group of properties, all of which are
indexed to allow fast retrieval.  The Cortex API has a distinct storage-layer
separation which facilitates a modular approach to data persistence and indexing.
While each storage implementation may have unique advantages, users of a given Cortex
need not be aware of which type they are requesting information from.

Additionally, a Cortex is the fundamental hypergraph storage behind a Swarm 
cluster which allows many Cortexes to be queried in parallel and the results
to be intersected and fused as one.

Cortex Quick Start
------------------
A quick example of forming a RAM Cortex and creating a few nodes::

    import synapse.cortex as s_cortex

    core = s_cortex.openurl('ram://')

    tufo0 = core.formTufoByProp('foo:bar','woot', baz=30)
    tufo1 = core.formTufoByProp('foo:bar','haha', baz=10)

    # Access a primary property from a tufo
    if tufo0[1].get('foo:bar') == 'woot':
        print('woot')

    # Access a secondary property from a tufo
    if tufo0[1].get('foo:bar:baz') == 30:
        print('woot')

    # retrieve all foo:bar tufos
    tufs = core.getTufosByProp('foo:bar')

    # retrieve all tufos where foo:bar:baz=30, but no more than 100
    tufs = core.getTufosByProp('foo:bar:baz', valu=30, limit=100)

Various storage backings may be accessed with different URL schemes.
To create a Cortex which is backed by an SQLite3 file::

    core = s_cortex.openurl('sqlite://myfile.db')

To create a cortex which is backed by a local PostgreSQL table::

    core = s_cortex.openurl('postgres:///mydbname/mytable')

To create a cortex which is backed by a remote PostgreSQL table::

    core = s_cortex.openurl('postgres://visi:SecretSauce@db.vertex.link/mydbname/mytable')

Introducing the TuFo
--------------------
A Cortex represents hypergraph nodes in a data structure we call a "tuple form" or tufo.
A tufo data structure consists of an identifier and a dictionary of properties::

    ( <guid>, { "prop":"valu", ... } )

Each tufo contains a single primary property frequently referred to as the "form" of the tufo.
Additional secondary properties which are specific to the form (or type) of tufo are prefixed with the form to create a specific name space for each property.
For example, if the model contained a form named "foo:bar", the additional properties would all begin with "foo:bar:"::

    ( <guid>, {"foo:bar":"woot", "foo:bar:len":4 })

Universal TuFo Properties
~~~~~~~~~~~~~~~~~~~~~~~~~
Tufos created by a Cortex have several "universal" properties which are automatically populated during creation.
For example, each tufo will contain a "tufo:form"=<name> property which allows tufo consumers to know which property is primary and how to determine the prefix for secondary properties::

    ( <guid>, {"foo:bar":"woot","tufo:form":"foo:bar"})

TuFo Secondary Properties
~~~~~~~~~~~~~~~~~~~~~~~~~
Secondary properties for a given tufo will be prefixed with the form to create a unique name space for the secondary property.
The data model for a Cortex may enforce that all secondary properties must adhere to specific type normalization and may optionally include a default value if the property is not specified during formTufoByProp.
For example, within the inet:fqdn form, the secondary property "sfx" will default to 0 if unspecified during formation::

    formTufoByProp('inet:fqdn','vertex.link') -> ( <guid>, {'inet:fqdn':'vertex.link','inet:fqdn:sfx':0, ...} )

Secondary properties may be used to lift nodes from the Cortex using the getTufosByProp API which is discussed below.

TuFo Ephemeral Properties
~~~~~~~~~~~~~~~~~~~~~~~~~
It is occasionally useful for a tufo to carry properties which are ephemeral and do not represent
data which is stored or indexed within the Cortex.  These ephemeral properties are often used to
represent run time knowledge or context and rarely have anything to do with the "truth" of the form.
Ephemeral properties may be identified by beginning with the "." character.

For example, the Cortex API formTufoByProp will retrieve an existing tufo *or* create a new
instance if the requested <form>=<value> pair is not found.  It may be useful for an application
to know if the tufo was just created by the formTufoByProp call or already existed within the Cortex.
To prevent API users from needing to call getTufoByProp to pre-test for existence, the formTufoByProp
API adds the property ".new"=1 when the tufo did not previously exist.::

    ( <guid>, {"foo:bar":"woot",".new":1})

Form a TuFo
~~~~~~~~~~~
The formTufoByProp API facilitates the creation of tufos and implements tufo deconfliction.
The primary property of a tufo created using the formTufoByProp API is atomically deconflicted 
within the Cortex to ensure there is only ever one instance of that <form>=<value> pair.
Additionally, calling formTufoByProp on an existing <form>=<value> pair will retrieve and return
the already existing tufo if present.  This allows a single atomic mechanism for the
check-and-create primitive and provides a safe way to re-ingest data without worrying about
creating duplicate representations of the same knowledge::

    tuf0 = core.formTufoByProp('foo:bar','woot')

Additional secondary properties may be specified as kwargs to formTufoByProp::

    tuf0 = core.formTufoByProp('foo:bar','woot', baz=30)

.. #automethod:: synapse.cores.common.Cortex.formTufoByProp

Tufos may also be created for non-deconflicted forms which represent a unique occurrence or
observation in time.  Tufos which are not meant to be deconflicted are declared with a GUID
as their primary property and may be formed using the the value None.

    tuf0 = core.addTufoEvent('hurr:durr', blah=30, gronk='lol')

The addTufoEvent API handles the generation of a GUID for the tufo's primary property and
is able to insert the tufo without incurring the overhead of deconfliction.

Retrieving TuFos By Property
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A list of tufos which have a given property and optionally a specific value may be retrieved
from a Cortex using the getTufosByProp API::

    tufs = core.getTufosByProp('foo:bar:baz', valu=30)

.. #automethod:: synapse.cores.common.Cortex.getTufosByProp

Cortex Datamodels
-----------------
A Cortex may optionally store and enforce a data model which declares types, forms, and
properties.  The model's knowledge of types will be used to ensure that properties are
correctly normalized.  This knowledge is also used by the getTufosByPropType API to allow
the retrieval of tufos which contain a property type without knowing about the form in
advance.

The data model is stored as tufos within the Cortex which allows them to be inspected
like any other tufos::

    # gather all the forms with a property of type "inet:fqdn" and print the form name.
    for tufo in core.getTufosByProp('syn:prop:ptype', valu='inet:fqdn'):
        prop = tufo[1].get('syn:prop')
        form = tufo[1].get('syn:prop:form')
        print('tufo form: %s has prop: %s' % ( form, prop ))

syn:type
~~~~~~~~
The syn:type tufos are used to declare all types which the Cortex is aware of.  Each
type must either be implemented by an existing python class or extend an existing type.

syn:form
~~~~~~~~
The syn:form tufos are used to declare each form which the Cortex data model is aware of.
A syn:form tufo will contain knowledge about the type for the primary property.

syn:prop
~~~~~~~~
Every declared property for a given tufo form is represented via a syn:prop tufo which
contains knowledge of both the parent form as well as type information.

Cortex Rows
-----------
A row level API exists within the Cortex API to allow access to the underlying storage
abstraction for individual properties.

These APIs are detailed in `Cortex Storage Details`_.

Calculating Statistics
----------------------

INPROG

Cortex Storage Details
----------------------

The Cortex can be back by one of several different storage layers. Detail information about
storage layers which are available for Cortex can be found here `Cortex Storage Types`_.
Additional information about the Storage layer API itself can be found here `Cortex Storage Details`_.

.. _`Cortex Storage Types`: ./cortex_storage_types.html
.. _`Cortex Storage Details`: ./cortex_storage_details.html