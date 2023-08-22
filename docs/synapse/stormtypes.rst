.. _stormtypes_index:

Storm Library Documentation
###########################

This contains API documentation for Storm Libraries and Storm Types.

Storm Types (also called Storm Objects) are objects in the Storm Runtime that can represent values such as nodes in the
runtime or objects in the Cortex. Storm Types encompass objects from strings of characters
(:ref:`stormprims-str-f527`), to objects representing Cron Jobs in the Cortex (:ref:`stormprims-cronjob-f527`), to
nodes in the Cortex (:ref:`stormprims-node-f527`). These objects each have their own properties and methods defined on
them that can be used to inspect or edit that object. For instance, String Storm Types all have the ``upper()`` method
defined on them that returns a new instance of that String, except with every letter turned uppercase
(:ref:`stormprims-str-upper`). Storm Types help form the basis for programmatic manipulation of objects and data in the
Cortex.

Storm Libraries are ready-made tools in the Storm query language for creating, updating, or fetching data using Storm
Types. Storm libraries include functionality for making HTTP requests (via :ref:`stormlibs-lib-inet-http`), scraping
nodes from text (:ref:`stormlibs-lib-scrape`), manipulating Cortex objects such as Queues (:ref:`stormlibs-lib-queue`)
and StormDmons (:ref:`stormlibs-lib-dmon`), creating new Cron Jobs (:ref:`stormlibs-lib-cron`), and more. Many of these
libraries accept or return Storm Types as part of their usage. For instance, there is a library in Storm for
interacting with OAuthv1 servers (:ref:`stormlibs-lib-inet-http-oauth-v1-client`), and it accepts several String Storm
Types as parameters and returns an OAuthV1 client object for later usage
(:ref:`stormprims-inet-http-oauth-v1-client-f527`).

Storm Libraries form a powerful bench of tools for usage within the Storm query language.

The current sections are:

.. toctree::
    :titlesonly:

    autodocs/stormtypes_libs

    autodocs/stormtypes_prims
