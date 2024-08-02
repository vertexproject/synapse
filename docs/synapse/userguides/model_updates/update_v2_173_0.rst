.. _userguide_model_v2_173_0:

######################
v2.173.0 Model Updates
######################

The following model updates were made during the ``v2.173.0`` Synapse release.

**************
New Interfaces
**************

``inet:service:base``
  Properties common to most forms within a service platform.

``inet:service:object``
  Properties common to objects within a service platform. This inherits
  from the ``inet:service:base`` interface.

*********
New Forms
*********

``inet:service:access``
  Represents a user access request to a service resource.

``inet:service:account``
  An account within a service platform. Accounts may be instance specific.

``inet:service:bucket``
  A file/blob storage object within a service architecture.

``inet:service:bucket:item``
  An individual file stored within a bucket.

``inet:service:channel``
  A channel used to distribute messages.

``inet:service:channel:member``
  Represents a service account being a member of a channel.

``inet:service:group``
  A group or role which contains member accounts.

``inet:service:group:member``
  Represents a service account being a member of a group.

``inet:service:instance``
  An instance of the platform such as Slack or Discord instances.

``inet:service:login``
  A login event for a service account.

``inet:service:message``
  A message or post created by an account.

``inet:service:message:link``
  A URL link included within a message.

``inet:service:message:attachment``
  A file attachment included within a message.

``inet:service:login:method:taxonomy``
  A taxonomy of inet service login methods.

``inet:service:object:status``
  An object status enumeration.

``inet:service:permission``
  A permission which may be granted to a service account or role.

``inet:service:permission:type:taxonomy``
  A permission type taxonomy.

``inet:service:platform``
  A network platform which provides services.

``inet:service:resource``
  A generic resource provided by the service architecture.

``inet:service:resource:type:taxonomy``
  A taxonomy of inet service resource types.

``inet:service:rule``
  A rule which grants or denies a permission to a service account or role.

``inet:service:session``
  An authenticated session.

``it:cmd:history``
  A single command executed within a session.

``it:cmd:session``
  A command line session with multiple commands run over time.

``it:host:tenancy``
  A time window where a host was a tenant run by another host.

``it:network:type:taxonomy``
  A taxonomy of network types.

``it:software:image:type:taxonomy``
  A taxonomy of software image types.

``it:software:image``
  The base image used to create a container or OS.

``it:storage:mount``
  A storage volume that has been attached to an image.

``it:storage:volume``
  A physical or logical storage volume that can be attached to a
  physical/virtual machine or container.

``it:storage:volume:type:taxonomy``
  A taxonomy of storage volume types.

**************
New Properties
**************

``biz:listing``
  The form had the following properties added to it:

  ``count:remaining``
    The current remaining number of instances for sale.

  ``count:total``
    The number of instances for sale.

``econ:purchase``
  The form had the following property added to it:

  ``listing``
    The purchase was made based on the given listing.

``it:exec:proc``
  The form had the following property added to it:

  ``cmd:history``
    The command history entry which caused this process to be run.

``it:exec:query``
  The form had the following property added to it:

  ``synuser``
    The synapse user who executed the query.

``it:host``
  The form had the following property added to it:

  ``image``
    The container image or OS image running on the host.

``it:network``
  The form had the following property added to it:

  ``type``
    The type of network.

``meta:note``
  The form had the following property added to it:

  ``replyto``
    The note is a reply to the specified note.

``ou:campaign``
  The form had the following property added to it:

  ``ext:id``
    An external identifier for the campaign.

``ou:org``
  The form had the following property added to it:

  ``ext:id``
    An external identifier for the organization.

``ou:technique``
  The form had the following property added to it:

  ``ext:id``
    An external identifier for the technique.

``risk:extortion``
  The form had the following properties added to it:

  ``paid:price``
    The total price paid by the target of the extortion.

  ``payments``
    Payments made from the target to the attacker.

``risk:leak``
  The form had the following properties added to it:

  ``size:count``
    The number of files included in the leaked data.

  ``size:percent``
    The total percent of the data leaked.

``risk:threat``
  The form had the following property added to it:

  ``ext:id``
    An external identifier for the threat.

*************
Updated Types
*************

``inet:web:hashtag``
  Update the regex to allow the middle dot (U+00B7) character to be part of
  the hashtag after the first unicode word character.

``transport:air:flightnum``
  Loosen the regex for flight number validation.

*************
Updated Forms
*************

``it:host``
  The form now inherits from the ``inet:service:object`` interface.
