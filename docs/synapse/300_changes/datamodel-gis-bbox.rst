.. _vtx_300_datamodel-gis-bbox:

Geospatial lat/long and bbox Consistency
========================================

Synapse 3.0.0 clarifies the geospatial coordinate conventions, adds native DMS
(degree/minute/second) parsing for ``geo:latlong``, and moves common geolocation
properties onto the ``geo:locatable`` interface.

Coordinate ordering and DMS parsing
-----------------------------------

What changed
    The ``geo:latlong`` type now parses its string input through ``s_gis.parseLatLong``,
    which accepts a decimal ``lat,long`` pair (latitude first) as before and additionally
    accepts DMS coordinate strings such as ``45d46m52N, 13d30m45E``. The stored value
    remains a ``(latitude, longitude)`` tuple. ``geo:bbox`` remains a ``comp`` type ordered
    ``(xmin, xmax, ymin, ymax)`` where ``xmin``/``xmax`` are ``geo:longitude`` and
    ``ymin``/``ymax`` are ``geo:latitude`` -- that is, longitude first. The
    ``geo:latitude`` bounds remain ``[-90, 90]`` and the ``geo:longitude`` bounds remain
    ``(-180, 180]``.

Why
    Real-world geo feeds often supply DMS strings, and native parsing avoids brittle
    pre-conversion. Stating the ordering convention explicitly removes a long-standing
    point of ambiguity.

What you need to do
    Pass a decimal ``lat,long`` (latitude first) or a DMS string to any ``geo:latlong``-typed
    property; both normalize to a ``(lat, lon)`` tuple. When building a ``geo:bbox`` remember
    it is longitude first (``xmin,xmax,ymin,ymax``) and does NOT follow the latlong ordering.

    ::

        // 3.x -- decimal lat,long (latitude first), unchanged
        [ geo:place=* :latlong="-12.45,56.78" ]

        // 3.x -- DMS strings are now accepted
        [ geo:place=* :latlong="45d46m52N, 13d30m45E" ]

        // geo:bbox is longitude first: (xmin, xmax, ymin, ymax)
        // note geo:longitude is the half-open interval (-180, 180], so -180.0 is not valid
        [ geo:place=* :bbox=(-179.0, 179.0, -90.0, 90.0) ]

Geolocation props on the geo:locatable interface
-------------------------------------------------

What changed
    Common geolocation properties are now supplied through the ``geo:locatable``
    interface, whose default property prefix is ``place``. Forms that implement the
    interface therefore expose ``:place:latlong``, ``:place:latlong:accuracy``,
    ``:place:loc``, ``:place:name``, ``:place:address``, ``:place:address:city``,
    ``:place:altitude``, ``:place:altitude:accuracy``, ``:place:country`` and
    ``:place:country:code``. The ``geo:place`` form overrides the interface prefix to the
    empty string, so on ``geo:place`` itself those properties remain bare (``:latlong``,
    ``:loc``, ``:address``, and so on). The interface does not include ``bbox`` or
    geojson properties.

Why
    Routing the geolocation properties through a shared interface makes them consistent
    across every locatable form rather than being redefined per form.

What you need to do
    On ``geo:place``, continue to use the bare properties (``:latlong``, ``:loc``, ...).
    On other forms that implement ``geo:locatable``, use the ``place:``-prefixed
    properties.

    ::

        // 3.x -- geo:place keeps bare props (prefix overridden to '')
        [ geo:place=* :latlong="-12.45,56.78" ]

        // 3.x -- other locatable forms use the place: prefix
        [ transport:air:telem=* :place:latlong="-12.45,56.78" ]
