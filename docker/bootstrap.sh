#!/bin/bash

if [ -d /build/synapse ]; then
    PIP_NO_CACHE_DIR=1 PIP_ROOT_USER_ACTION=ignore python -m pip install --verbose --break-system-packages /build/synapse
fi

if [ -f /build/synapse/rmlist.txt ]; then
    while read path; do
        if [ -e $path ]; then
            echo "Removing ${path}" && rm -rf $path;
        else
            echo "! Path not present: ${path}";
            exit 1
        fi
    done < /build/synapse/rmlist.txt
fi

rm -rf /build
