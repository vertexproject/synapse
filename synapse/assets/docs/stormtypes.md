<a id="stormtypes_index"></a>

# Storm Library Documentation

This contains API documentation for Storm Libraries and Storm Types.

Storm Types (also called Storm Objects) are objects in the Storm Runtime that can represent values such as nodes in the runtime or objects in the Cortex. Storm Types encompass objects from strings of characters ([stormprims-str-f527](stormtypes_prims.md#stormprims-str-f527)), to objects representing Cron Jobs in the Cortex ([stormprims-cronjob-f527](stormtypes_prims.md#stormprims-cronjob-f527)), to nodes in the Cortex ([stormprims-node-f527](stormtypes_prims.md#stormprims-node-f527)). These objects each have their own properties and methods defined on them that can be used to inspect or edit that object. For instance, String Storm Types all have the `upper()` method defined on them that returns a new instance of that String, except with every letter turned uppercase ([stormprims-str-upper](stormtypes_prims.md#stormprims-str-upper)). Storm Types help form the basis for programmatic manipulation of objects and data in the Cortex.

Storm Libraries are ready-made tools in the Storm query language for creating, updating, or fetching data using Storm Types. Storm libraries include functionality for making HTTP requests (via [stormlibs-lib-inet-http](stormtypes_libs.md#stormlibs-lib-inet-http)), scraping nodes from text ([stormlibs-lib-scrape](stormtypes_libs.md#stormlibs-lib-scrape)), manipulating Cortex objects such as Queues ([stormlibs-lib-queue](stormtypes_libs.md#stormlibs-lib-queue)) and StormDmons ([stormlibs-lib-dmon](stormtypes_libs.md#stormlibs-lib-dmon)), creating new Cron Jobs ([stormlibs-lib-cron](stormtypes_libs.md#stormlibs-lib-cron)), and more. Many of these libraries accept or return Storm Types as part of their usage. For instance, there is a library in Storm for interacting with OAuthv1 servers ([stormlibs-lib-inet-http-oauth-v1-client](stormtypes_libs.md#stormlibs-lib-inet-http-oauth-v1-client)), and it accepts several String Storm Types as parameters and returns an OAuthV1 client object for later usage ([stormprims-inet-http-oauth-v1-client-f527](stormtypes_prims.md#stormprims-inet-http-oauth-v1-client-f527)).

Storm Libraries form a powerful bench of tools for usage within the Storm query language.

The current sections are:

- [Storm Libraries](stormtypes_libs.md)
- [Storm Types](stormtypes_prims.md)

