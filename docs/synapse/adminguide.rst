.. _adminguide:


Synapse Admin Guide
###################

This guide is designed for use by Synapse "global admins" who are typically power-users with ``admin=true`` permissions on
the Cortex and are responsible for non-devops configuration and management of a Synapse deployment. This guide focuses on
using Storm to accomplish administration tasks and discusses conventions and permissions details for the Cortex.

Cortex Permissions
==================

The **Cortex** supports a highly granular permission system which can be used to control users ability to interact with
data and components within the system. Permissions are denied by default, but a small number of permissions are granted
to users by default:

* view.read is allowed by default on any view created with ``worldreadable=True`` such as the default view.

Glossary:

    * Auth Gate
        A scope where permissions are checked. Auth gates may

    * Permission
        A permission string which is used to control access. Permission strings are matched hierarchically, meaning that a
        check for the permission ``foo.bar.baz`` will match on ``foo.bar`` which allows permissions to be granted or revoked
        to whole areas of functionality at a time.

    * Rule
        A rule consists of an allow/deny specification and a **Permission** string. Rules assigned to users and roles within
        the scope of an **Auth Gate**. Rules are checked for a specific user before being checked for roles and are applied on
        a first-match basis. This allows a more specific deny rule to be applied before a less specific allow rule to create
        "allow everything except" cases.

    * Admin
        Admin status allows the user to bypass all permission checks. Admin status may be applied to individual **Auth Gates**
        or may apply globally to all permission checks within the Cortex. Having admin access to an **Auth Gate** also allows
        the user/role to add rules to the 

Permission checks are implemented with 

In any instance where a user encounters a permission error, an **AuthDeny** exception will be raised which includes the permission
string being checked.

AuthGates and Permissions
-------------------------

Cortex
~~~~~~

Preceidence: Cortex

    * power-ups.<name>.<various> Ex: ``power-up.shodan.user``

View
~~~~

Preceidence: View -> Cortex

Layer
~~~~~

Preceidence: Layer -> Cortex

    * node - Controlls access to all node edits within the layer.
    * node.add - Controlls 
    * node.add.<form> - Controlls access to a user/role's ability to add the given form to the layer. Ex: ``node.add.ou:org``
    * node.del - Controlls 
    * node.del.<form> - Controlls access to a user/role's ability to remove nodes of the given form from the layer. Ex: ``node.add.ou:org``

    * node.tag.add.<tag>
    * node.tag.del.<tag>
    * node.data.set.<name>
    * node.data.del.<name>

Examples

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

.. _the blog post on Synapse Power-Ups: https://vertex.link/blogs/synapse-power-ups/
