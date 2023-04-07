#!/bin/bash

if [ -d /build/synapse ]; then
    python -m pip install /build/synapse
fi

rm -rf /build
