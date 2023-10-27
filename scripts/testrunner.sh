#!/usr/bin/env bash

##############################################################################
# Standalone test runner for synapse tests
# This will run unit tests using pytest and generate HTML coverage reports.
# The use of this script requires the installation of pytest, pytest-cov and
# pytest-xdist python packages, which are not required for other synapse
# developement or deployment.
##############################################################################

MODULE=synapse
HTML_DIR=./build/htmlcov
INDEX=$HTML_DIR/index.html
COVREQ=80

if [ -e $HTML_DIR ]; then
    echo "Removing existing coverage reports."
    rm -rf $HTML_DIR
fi

COVFAIL=""
if [ "$*" = '' ]; then
    COVFAIL="--cov-fail-under=$COVREQ"
fi

python -m pytest -v -s --durations 6 -n auto --maxfail 6 -rs $COVFAIL --cov $MODULE --no-cov-on-fail --cov-report=html:$HTML_DIR $*

if [ $? -eq 0 ]; then
    if [ -e $INDEX ]; then
        echo "Opening coverage report."
        xdg-open $INDEX &
    fi
fi