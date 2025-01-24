

.. _userguide_model_v2_195_0:

######################
v2.195.0 Model Updates
######################

The following model updates were made during the ``v2.195.0`` Synapse release.

**************
New Interfaces
**************

``transport:vehicle``
  Properties common to a vehicle.


``transport:container``
  Properties common to a container used to transport cargo or people.


``phys:object``
  Properties common to all physical objects.


``transport:schedule``
  Properties common to travel schedules.


``transport:trip``
  Properties common to a specific trip taken by a vehicle.


``geo:locatable``
  Properties common to items and events which may be geolocated.



*********
New Types
*********

``transport:vehicle``
  A vehicle such as an aircraft or sea vessel.


``transport:container``
  A container capable of transporting cargo or personnel.


``phys:object``
  A node which represents a physical object.


``transport:point``
  A departure/arrival point such as an airport gate or train platform.


``transport:trip``
  A trip such as a flight or train ride.



*********
New Forms
*********

``transport:rail:car:type:taxonomy``
  A hierarchical taxonomy of rail car types.


``phys:contained:type:taxonomy``
  A taxonomy for types of contained relationships.


``transport:rail:consist``
  A group of rail cars and locomotives connected together.


``transport:occupant:role:taxonomy``
  A taxonomy of transportation occupant roles.


``transport:sea:vessel:type:taxonomy``
  A hierarchical taxonomy of sea vessel types.


``transport:land:vehicle:type:taxonomy``
  A type taxonomy for land vehicles.


``transport:occupant``
  An occupant of a vehicle on a trip.


``transport:shipping:container``
  An individual shipping container.


``transport:rail:car``
  An individual train car.


``transport:rail:train``
  An individual instance of a consist of train cars running a route.


``phys:contained``
  A node which represents a physical object containing another physical object.


``transport:land:drive``
  A drive taken by a land vehicle.


``transport:stop``
  A stop made by a vehicle on a trip.


``transport:cargo``
  Cargo being carried by a vehicle on a trip.



**************
New Properties
**************

``geo:place``
  The form had the following property added to it:

  ``id``
    A type specific identifier such as an airport ID.


``geo:telem``
  The form had the following properties added to it:


  ``phys:height``
    The height of the object.


  ``phys:length``
    The length of the object.


  ``phys:mass``
    The mass of the object.


  ``phys:volume``
    The cubed volume of the object.


  ``phys:width``
    The width of the object.


  ``place:address``
    The postal address of the place where the object was located.


  ``place:country``
    The country where the object was located.


  ``place:country:code``
    The country code where the object was located.


  ``place:latlong``
    The latlong where the object was located.


  ``place:latlong:accuracy``
    The accuracy of the latlong where the object was located.


  ``place:loc``
    The geopolitical location of the object.


``it:host``
  The form had the following properties added to it:


  ``phys:height``
    The height of the physical host.


  ``phys:length``
    The length of the physical host.


  ``phys:mass``
    The mass of the physical host.


  ``phys:volume``
    The cubed volume of the physical host.


  ``phys:width``
    The width of the physical host.


``mat:item``
  The form had the following properties added to it:


  ``phys:height``
    The height of the item.


  ``phys:length``
    The length of the item.


  ``phys:mass``
    The mass of the item.


  ``phys:volume``
    The cubed volume of the item.


  ``phys:width``
    The width of the item.


  ``place:address``
    The postal address of the place where the item was located.


  ``place:country``
    The country where the item was located.


  ``place:country:code``
    The country code where the item was located.


  ``place:latlong``
    The latlong where the item was located.


  ``place:latlong:accuracy``
    The accuracy of the latlong where the item was located.


  ``place:loc``
    The geopolitical location of the item.


  ``place:name``
    The name of the place where the item was located.


``ou:id:type``
  The form had the following property added to it:

  ``names``
    An array of alternate names for the ID number type.


``ps:vitals``
  The form had the following properties added to it:


  ``phys:height``
    The height of the person.


  ``phys:length``
    The length of the person.


  ``phys:mass``
    The mass of the person.


  ``phys:volume``
    The cubed volume of the person.


  ``phys:width``
    The width of the person.


``transport:air:craft``
  The form had the following properties added to it:


  ``manufacturer``
    The organization which manufactured the aircraft.


  ``manufacturer:name``
    The name of the organization which manufactured the aircraft.


  ``max:cargo:mass``
    The maximum mass the aircraft can carry as cargo.


  ``max:cargo:volume``
    The maximum volume the aircraft can carry as cargo.


  ``max:occupants``
    The maximum number of occupants the aircraft can hold.


  ``owner``
    The contact information of the owner of the aircraft.


  ``phys:height``
    The height of the aircraft.


  ``phys:length``
    The length of the aircraft.


  ``phys:mass``
    The mass of the aircraft.


  ``phys:volume``
    The cubed volume of the aircraft.


  ``phys:width``
    The width of the aircraft.


``transport:air:flight``
  The form had the following properties added to it:


  ``arrived:place``
    The actual arrival airport.


  ``arrived:point``
    The actual arrival gate.


  ``cargo:mass``
    The cargo mass carried by the air craft on this flight.


  ``cargo:volume``
    The cargo volume carried by the air craft on this flight.


  ``departed:place``
    The actual departure airport.


  ``departed:point``
    The actual departure gate.


  ``duration``
    The actual duration.


  ``occupants``
    The number of occupants of the air craft on this flight.


  ``operator``
    The contact information of the operator of the flight.


  ``scheduled:arrival:place``
    The scheduled arrival airport.


  ``scheduled:arrival:point``
    The scheduled arrival gate.


  ``scheduled:departure:place``
    The scheduled departure airport.


  ``scheduled:departure:point``
    The scheduled departure gate.


  ``scheduled:duration``
    The scheduled duration.


  ``status``
    The status of the flight.


  ``vehicle``
    The air craft which traveled the flight.


``transport:land:vehicle``
  The form had the following properties added to it:


  ``desc``
    A description of the vehicle.


  ``manufacturer``
    The organization which manufactured the vehicle.


  ``manufacturer:name``
    The name of the organization which manufactured the vehicle.


  ``max:cargo:mass``
    The maximum mass the vehicle can carry as cargo.


  ``max:cargo:volume``
    The maximum volume the vehicle can carry as cargo.


  ``max:occupants``
    The maximum number of occupants the vehicle can hold.


  ``operator``
    The contact information of operator of the vehicle.


  ``phys:height``
    The height of the vehicle.


  ``phys:length``
    The length of the vehicle.


  ``phys:mass``
    The mass of the vehicle.


  ``phys:volume``
    The cubed volume of the vehicle.


  ``phys:width``
    The width of the vehicle.


  ``type``
    The type of land vehicle.


``transport:sea:vessel``
  The form had the following properties added to it:


  ``manufacturer``
    The organization which manufactured the vessel.


  ``manufacturer:name``
    The name of the organization which manufactured the vessel.


  ``max:cargo:mass``
    The maximum mass the vessel can carry as cargo.


  ``max:cargo:volume``
    The maximum volume the vessel can carry as cargo.


  ``max:occupants``
    The maximum number of occupants the vessel can hold.


  ``owner``
    The contact information of the owner of the vessel.


  ``phys:height``
    The height of the vessel.


  ``phys:length``
    The length of the vessel.


  ``phys:mass``
    The mass of the vessel.


  ``phys:volume``
    The cubed volume of the vessel.


  ``phys:width``
    The width of the vessel.


  ``serial``
    The manufacturer assigned serial number of the vessel.


  ``type``
    The type of vessel.



*************
Updated Types
*************

``geo:telem``
  The type interface has been modified to inherit from the ``phys:object``
  and ``geo:locatable`` interfaces.


``it:host``
  The type interface has been modified from ``inet:service:object'`` to
  inherit from the ``inet:service:object`` and ``phys:object`` interfaces.


``mat:item``
  The type interface has been modified to inherit from the ``phys:object``
  and ``geo:locatable`` interfaces.


``ps:vitals``
  The type interface has been modified to inherit from the ``phys:object``
  interface.


``transport:air:craft``
  The type interface has been modified to inherit from the ``transport:vehicle``
  interface.


``transport:air:flight``
  The type interface has been modified to inherit from the ``transport:trip``
  interface.


``transport:land:vehicle``
  The type interface has been modified to inherit from the ``transport:vehicle``
  interface.

``transport:sea:vessel``
  The type interface has been modified to inherit from the ``transport:vehicle``
  interface.


******************
Updated Properties
******************

``ou:id:type``
  The form had the following property updated:


    The property ``name`` had the alternative property names added to its definition.

``transport:air:craft``
  The form had the following property updated:


    The property ``model`` has been modified to ``onespace`` the strings.


``transport:sea:vessel``
  The form had the following property updated:


    The property ``model`` has been modified to ``onespace`` the strings.




****************
Deprecated Types
****************

The following types have been marked as deprecated:


* ``edge``
* ``timeedge``



****************
Deprecated Types
****************

The following forms have been marked as deprecated:


* ``transport:air:occupant``



*********************
Deprecated Properties
*********************

``geo:telem``
  The form had the following properties deprecated:


  ``accuracy``
    Deprecated. Please use ``:place:latlong:accuracy``.


  ``latlong``
    Deprecated. Please use ``:place:latlong``.


``mat:item``
  The form had the following properties deprecated:


  ``latlong``
    Deprecated. Please use ``:place:latlong``.


  ``loc``
    Deprecated. Please use ``:place:loc``.


``syn:cmd``
  The form had the following properties deprecated:


  ``input``
    The list of forms accepted by the command as input.


  ``nodedata``
    The list of nodedata that may be added by the command.


  ``output``
    The list of forms produced by the command as output.


``transport:air:craft``
  The form had the following property deprecated:

  ``make``
    Deprecated. Please use ``:manufacturer:name``.


``transport:air:flight``
  The form had the following properties deprecated:


  ``cancelled``
    Deprecated. Please use ``:status``.


  ``carrier``
    Deprecated. Please use ``:operator``.


  ``craft``
    Deprecated. Please use ``:vehicle``.


  ``from:port``
    Deprecated. Please use ``:departure:place``.


  ``stops``
    Deprecated. Please use ``transport:stop``.


  ``to:port``
    Deprecated. Please use ``:arrival:place``.


``transport:air:occupant``
  The form had the following properties deprecated:


  ``contact``
    Deprecated. Please use ``transport:occupant``.


  ``flight``
    Deprecated. Please use ``transport:occupant``.


  ``seat``
    Deprecated. Please use ``transport:occupant``.


  ``type``
    Deprecated. Please use ``transport:occupant``.


``transport:land:vehicle``
  The form had the following property deprecated:

  ``make``
    Deprecated. Please use ``:manufacturer:name``.


``transport:sea:vessel``
  The form had the following properties deprecated:


  ``length``
    Deprecated. Please use ``:phys:length``.


  ``make``
    Deprecated. Please use ``:manufacturer:name``.

