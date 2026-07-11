#!/bin/bash

# Shared helper for the service entrypoints. When the container is started as
# root it prepares the storage volume and re-execs the service as the
# unprivileged synuser (uid/gid 999).
#
# A bind mounted /vertex/storage inherits its ownership from the host and is not
# initialized from the image, so its ownership must be corrected at runtime.
# This preparation is only performed when we are started as root. If the
# container is started as another user (eg docker run --user ...) the operator
# is responsible for ensuring the storage volume is owned/writable by that user;
# we do not touch it and simply exec the service in place.

runcell() {

    # If we are already running as a non-root user we cannot (and must not)
    # adjust the storage volume or drop privileges, so exec the service as is.
    if [ "$(id -u)" != "0" ]
    then
        exec "$@"
    fi

    mkdir -p /vertex/storage
    chown -R synuser:synuser /vertex/storage

    exec gosu synuser "$@"
}
