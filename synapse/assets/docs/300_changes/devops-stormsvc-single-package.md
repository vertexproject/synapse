<a id="vtx_300_devops-stormsvc-single-package"></a>


# Storm Service Single Package

A Storm service delivers exactly one Storm package, is identified by its cell type rather than a generated iden, and its package is retrieved and persisted by the leader of a mirror set.

What changed

:   In 2.x a Storm service declared `_storm_svc_pkgs`, a tuple of package definitions, and the Cortex reconciled that list on every reconnect. It also declared `_storm_svc_name`, `_storm_svc_vers` and `_storm_svc_evts`, and served them all from a single `getStormSvcInfo()` handshake.

:   In 3.x a service declares one package as `_storm_svc_pkg` and serves it from `getStormSvcPkg()`. `getStormSvcInfo()` is removed. The service name is its cell type, taken from `getCellInfo()`, and its version is the cell's own `VERSION`. `_storm_svc_evts` and the `service.add` / `service.del` Storm event hooks are removed -- a package's `onload` and `inits` cover that ground.

:   A service is registered under, and addressed by, its **cell type**. `service.add <name> <url>` requires `<name>` to be the cell type the service reports, and the Cortex refuses the link otherwise. A name is unique for a Cortex, so adding a second service under an existing name raises `DupStormSvc`. There is no separate service iden: `service.del` takes a name instead of an iden prefix, `$lib.service.list()` definitions have no `iden`, and `$lib.service.get()` / `$lib.service.has()` / `$lib.service.wait()` resolve a cell type name only.

:   Consequently there is no `svciden`. The `svciden` key is gone from the package definition schema and from `commands[].cmdconf`, the `syn:cmd:svciden` property is removed, and `$modconf.svciden` / `$cmdconf.svciden` are no longer set. A package delivered by a service calls back into that service by naming it: `$lib.service.get(maxmind)`.

:   The Cortex tracks which service delivered a package itself rather than writing it into the package, so a signed service package is now stored byte-identical to what was signed. It reports the providing service as a `svcname` derived onto the definitions returned by `$lib.pkg.get()` and `$lib.pkg.list()`. A definition which was read may be pushed back unchanged; a `svcname` it carries is ignored, since the Cortex always reports what it tracks.

:   The leader of a mirror set retrieves the package and replicates it through the Nexus, so a follower loads and persists the package without connecting to the service. A follower still keeps a client to the service so that queries it runs may call the service directly.

:   A service package declares `advanced: true`, and `synapse.tools.storm.pkg.gen.reqSvcPkgProto()` -- which a service uses to load its own package -- refuses one without it. The flag marks the package an Advanced Power-Up: the Vertex Hub lists it but will not serve its definition for installation, since it is deployed as a service.

:   A service may ship files with its package. The Cortex retrieves each of them from the service into its Axon, before the package `onload` runs, using the new `getStormSvcPkgFile()` API. A file is requested by the path it is served under -- stable across rebuilds -- and verified against the SHA256 the package declares. A service builds the map of files to serve with `synapse.tools.storm.pkg.gen.getPkgProtoFiles()`.

Why

:   Every Advanced Power-Up already delivered exactly one package whose name matched its service name, so allowing N packages bought nothing and cost a reconciliation loop with a partial-delivery failure mode. Since a service is unique by cell type for a deployment, the cell type is a sufficient identity, which removes the generated iden, the split between a local and a remote service name, and the `svciden` plumbing threaded through package loading. Having the leader deliver the package means a follower which cannot reach the service still has it.

What you need to do

:   Rework any Storm service you maintain, and register it under the cell type name it reports -- the Cortex refuses to connect to a service registered under any other name.

    ``` python
    # 2.x -- N packages, an explicit name and version
    class MySvcApi(s_cell.CellApi, s_stormsvc.StormSvc):
        _storm_svc_name = 'my-storm-package'
        _storm_svc_vers = my_version.version
        _storm_svc_pkgs = (
            s_genpkg.tryLoadPkgProto(pkgfile, readonly=True),
        )

    # 3.x -- one package which must declare advanced: true; the name is the cell
    # type and the version is VERSION
    class MySvcApi(s_cell.CellApi, s_stormsvc.StormSvc):
        _storm_svc_pkg = s_genpkg.reqSvcPkgProto(pkgfile)

        # only needed when the package ships a files directory
        _storm_svc_pkgfiles = s_genpkg.getPkgProtoFiles(pkgfile)

    class MySvc(sc_cell.EnterpriseCell):
        celltype = 'mysvc'
        cellapi = MySvcApi
        VERSION = my_version.version
    ```

    ``` bash
    # 2.x -- any local name, then delete by iden prefix
    storm> service.add lolnotmaxmind tcp://maxmind:27492/
    storm> service.del 4a1f

    # 3.x -- the name is the cell type, and deletes use it
    storm> service.add maxmind aha://maxmind...
    storm> service.del maxmind
    ```

    Update any Storm which resolved its own service through `$modconf.svciden` or `$cmdconf.svciden` to name the service instead.

    ``` storm
    // 2.x
    $svc = $lib.service.get($modconf.svciden)

    // 3.x
    $svc = $lib.service.get(maxmind)
    ```
