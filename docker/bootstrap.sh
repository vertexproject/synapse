#!/bin/bash

if [ -d /build/synapse ]; then
    python -m pip install --break-system-packages /build/synapse
fi

rm -rf /build
