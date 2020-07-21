#!/bin/bash

cd /build/synapse && python setup.py install
#if [ -d /build/synapse ]; then
#    cd /build/synapse
#    python -m pip -v install .
#fi

rm -rf /build
