#!/bin/bash

set -x
set -e

cd /build/

if [[ -v COMMIT ]]; then
  echo "Setting commit to >> ${COMMIT} <<"
  python ./setcommit.py $COMMIT /build/synapse/
else
  echo "Not setting commit in the build script."
fi

# Local install to get build dependencies for building
python -m pip install .[build]

# build wheel
python -m build --wheel

# show wheel contents
python -m zipfile -l dist/*.whl
