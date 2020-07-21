#!/bin/bash

cd /build/synapse && python setup.py install
if [ -d /build/synapse ]; then
    cd /build/synapse
    python setup.py build bdist_wheel
    cd dist
    python -m pip install *.whl
fi

rm -rf /build
