#!/bin/bash

# Shared helper for the service entrypoints. When the container is started as
# root it prepares the storage volume and re-execs the service as the
# unprivileged synuser (uid/gid 999) using setpriv. It always sets no_new_privs so
# child processes cannot regain privileges via setuid binaries or file
# capabilities.
#
# A bind mounted /vertex/storage inherits its ownership from the host and is not
# initialized from the image, so its ownership must be corrected at runtime.
# This preparation is only performed when we are started as root. If the
# container is started as another user (eg docker run --user ...) the operator
# is responsible for ensuring the storage volume is owned/writable by that user;
# we do not touch it and exec the service in place with only no_new_privs set.

runcell() {

    # If we are already running as a non-root user we cannot (and must not)
    # adjust the storage volume or drop privileges, so only set no_new_privs.
    if [ "$(id -u)" != "0" ]
    then
        exec setpriv --no-new-privs "$@"
    fi

    mkdir -p /vertex/storage
    chown -R synuser:synuser /vertex/storage

    export HOME=/home/synuser
    exec setpriv --reuid=synuser --regid=synuser --init-groups --no-new-privs "$@"
}
