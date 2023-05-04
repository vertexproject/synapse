#!/bin/bash

if [ -d /build/synapse ]; then
    python -m pip install --break-system-packages /build/synapse
fi

if [ -f /build/synapse/rmlist.txt ]; then
    while read line; do
        if [ -f $line ]; then
            echo "Removing line ${line}" && rm $line;
        else
            echo "File not present: ${line}";
        fi
    done < /build/synapse/rmlist.txt
fi

rm -rf /build
