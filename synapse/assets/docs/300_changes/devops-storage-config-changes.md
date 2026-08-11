<a id="vtx_300_devops-storage-config-changes"></a>


# Removed and Changed Configuration Options

Synapse 3.0.0 removes several Cortex and base-Cell configuration options and changes the meaning of one layer cache option. An unknown configuration key is rejected at boot, so any removed key must be deleted from your `cell.yaml` (and `SYN_*` environment variables) before upgrading.

## Removed Cortex configuration keys

What changed

:   The Cortex `modules` option is removed -- Cortexes no longer support Core modules. The per-layer tuning options `layers:lockmemory` and `layers:logedits` are removed; the Cortex no longer seeds `lockmemory` or `logedits` onto new layer definitions, and a layer definition no longer carries those keys. Several previously-deprecated options are also fully removed from the confdefs: `cron:enable`, `trigger:enable`, `layer:lmdb:map_async`, `layer:lmdb:max_replay_log`, and `provenance:en`. The remaining layer-related Cortex options are `layers:cache:size` and `max:nodes`.

Why

:   Core modules could arbitrarily change Cortex behavior and are replaceable by Storm packages. `logedits` is obsolete now that there is no separate per-layer node-edit log (edits are tracked deconflicted in the Nexus log), and `lockmemory` is no longer applied to layer definitions. The other options had already been documented as deprecated/ignored in 2.x and are now gone entirely.

What you need to do

:   Remove these keys from any Cortex configuration before upgrading. If you tuned layer memory cache via `layers:lockmemory` / `layers:logedits`, there is no replacement for those; to tune the per-layer node cache use `layers:cache:size` (see the next section).

    ``` yaml
    # 2.x cortex cell.yaml
    modules:
      - myproj.mymodule.MyModule
    layers:lockmemory: true
    layers:logedits: true
    cron:enable: true
    trigger:enable: true
    provenance:en: false
    ```

    ``` yaml
    # 3.x cortex cell.yaml -- removed keys deleted
    layers:cache:size: 10000
    max:nodes: 0
    ```

## Changed semantics: `layers:cache:size`

What changed

:   The `layers:cache:size` Cortex option (and the per-layer `cache:size` option) still exists, but its description changed from "Default buid cache size for new layers" to "Default nid cache size for new layers". It now sizes the per-layer in-memory cache of NID-keyed storage nodes. The effective size is resolved with priority: per-layer `cache:size` \> Cortex `layers:cache:size` \> the default of 10000.

Why

:   Storage nodes are now keyed by NID rather than BUID, so the in-memory cache is keyed by NID and the option was relabeled to match.

What you need to do

:   No action is required to keep using `layers:cache:size`; existing values continue to work as a cache-entry count. Just be aware it now sizes the NID cache rather than the BUID cache.

    ``` yaml
    # 3.x cortex cell.yaml
    layers:cache:size: 10000
    ```

## Removed hidden Cell configuration keys

What changed

:   Three hidden base-Cell options are removed: `auth:ctor` (a Python path used to hook construction of the cell auth object), `auth:conf` (extended config for an alternate auth constructor), and `nexslog:async` (already deprecated and ignored). The `cell:ctor` option, used by the now-removed stemcell, is also gone.

Why

:   `auth:ctor` and `auth:conf` supported pluggable alternate auth backends that are no longer a supported extension point, and `nexslog:async` had already been marked deprecated and ignored.

What you need to do

:   Remove `auth:ctor`, `auth:conf`, and `nexslog:async` from any service `cell.yaml`. If you used a custom auth constructor via `auth:ctor`, that hook is gone -- manage auth through the standard auth subsystem (for example `moduser` / `modrole`).

    ``` yaml
    # 2.x cell.yaml
    auth:ctor: my.module.AuthCtor
    auth:conf: {}
    nexslog:async: true
    ```

    ``` yaml
    # 3.x cell.yaml -- auth:ctor / auth:conf / nexslog:async removed
    ```

## Removed Cell `inaugural` configuration option

What changed

:   The base-Cell `inaugural` option is removed. It accepted a `users` and `roles` structure that was
    applied to the service auth subsystem during first boot only.

Why

:   The option only ever ran on a service's first boot, so editing it afterward silently did nothing and
    it could not be used to manage the users and roles it created. The users and roles it did create were
    given idens derived from the service iden and the name, which cannot be reproduced by any other API. A
    name that collided with `aha:admin` failed the boot outright.

What you need to do

:   Remove `inaugural` from any service `cell.yaml` and unset any `SYN_<CELL>_INAUGURAL` environment
    variables before upgrading. Users and roles created by the option on a previous boot are unaffected and
    remain in the service auth subsystem. To provision users and roles on a new deployment, use
    `aha:admin` to establish an initial admin and then add users and roles explicitly with the
    `auth.user.add` and `auth.role.add` Storm commands, or with the `synapse.tools.service.moduser` and
    `synapse.tools.service.modrole` tools.

    ``` yaml
    # 2.x cell.yaml
    inaugural:
      roles:
        - name: analyst
          rules:
            - [true, [view, read]]
      users:
        - name: visi@vertex.link
          email: visi@vertex.link
          roles:
            - analyst
    ```

    ``` yaml
    # 3.x cell.yaml -- inaugural removed
    aha:admin: visi@vertex.link
    ```

    ``` storm
    // 3.x -- provision users and roles explicitly
    auth.role.add analyst
    auth.role.addrule analyst view.read
    auth.user.add visi@vertex.link --email visi@vertex.link
    auth.user.grant visi@vertex.link analyst
    ```

## Removed Cell `aha:svcinfo` configuration option

What changed

:   The hidden base-Cell `aha:svcinfo` option is removed. It supplied a static `urlinfo` (`host`, `port`,
    and `scheme`) which the service registered with AHA *instead of* the information describing its real
    listener.

Why

:   The option let a service advertise a host and port unrelated to what it actually bound, so the AHA
    registry could describe a listener that did not exist and every service resolving that entry would
    fail to connect. A service's registered `urlinfo` is now always derived from its own listener, and
    that property is what makes AHA service resolution dependable.

What you need to do

:   Remove `aha:svcinfo` from any service `cell.yaml` and `cell.mods.yaml`, and unset any
    `SYN_<CELL>_AHA_SVCINFO` environment variables before upgrading. The two are **not** equally
    noticeable: a leftover key in `cell.yaml` fails the boot with
    `BadArg: Key aha:svcinfo is not a valid config`, while a leftover environment variable is silently
    ignored -- the service starts and registers its real listener rather than the override. Unset the
    environment variable deliberately instead of relying on the boot to catch it.

:   There is no replacement. Advertising service information which differs from a service's real
    listener is not supported in Synapse 3.0.0.

    ``` yaml
    # 2.x cell.yaml -- delete this entry
    aha:svcinfo:
      urlinfo:
        host: cortex.example.com
        port: 27492
        scheme: ssl
    ```
