

<a id="dev_adv_power_ups"></a>

# Advanced Power-Up Development

An Advanced Power-Up is standalone application that extends the capabilities of the Cortex by implementing a Storm Service (see [Service](../glossary.md#gloss-service)). One common use case for creating an Advanced Power-Up is to add a Storm command that will run custom Python to parse a file, translate the results into the Synapse datamodel, and then ingest them into the hypergraph.

In order to leverage core functionalities it is recommended that Storm services are created as Cell implementations. For additional details see the [advanced-power-example repository](https://github.com/vertexproject/advanced-powerup-example), which contains an example that can be used as a reference for building an Advanced Power-Up.

## Implementing the Service

A Storm service mixes `synapse.lib.stormsvc.StormSvc` into its Cell API and declares the single Storm package it delivers:

``` python
import synapse.lib.stormsvc as s_stormsvc
import synapse.tools.storm.pkg.gen as s_genpkg

pkgfile = my_assets.getAssetPath('my-power-up.yaml')

class MyPowerUpApi(s_cell.CellApi, s_stormsvc.StormSvc):

    _storm_svc_pkg = s_genpkg.reqSvcPkgProto(pkgfile)

    # only needed when the package ships a files directory
    _storm_svc_pkgfiles = s_genpkg.getPkgProtoFiles(pkgfile)

class MyPowerUp(s_cell.Cell):

    celltype = 'mypowerup'
    cellapi = MyPowerUpApi
    VERSION = my_version.version
```

A service delivers exactly one package. The Cortex identifies the service by its **cell type**, which must be declared explicitly so it is stable, and reports the service version from the cell's `VERSION`. A service is registered under that cell type name (`service.add mypowerup aha://mypowerup...`) and the Cortex refuses to connect to a service reporting a different cell type.

The package must declare `advanced: true`:

``` yaml
name: my-power-up
version: 1.0.0
advanced: true
```

`reqSvcPkgProto()` refuses to load a service package without it, so a service which forgets the flag fails to start rather than shipping a package the **Vertex Hub** would present as an installable Rapid Power-Up. The flag is a top level key, so it is covered by the package's code signature. The Hub lists an Advanced Power-Up in its catalog but refuses to serve the package definition for installation -- it is deployed as a container instead.

Because the package is delivered by the service, Storm inside it calls back into the service by naming it:

``` storm
$svc = $lib.service.get(mypowerup)
```

In a mirrored deployment the leader retrieves the package and replicates it, so a mirror loads and persists it without reaching the service itself.

If the package ships a `files` directory (see [Package Files](power-ups.md#package-files)), the Cortex retrieves each file from the service into its Axon before the package `onload` runs. A file is requested by the path it is served under rather than by its SHA256, so the service keeps serving it across rebuilds even as the contents change; the Cortex still verifies what it receives against the SHA256 the ( possibly signed ) package declares.
