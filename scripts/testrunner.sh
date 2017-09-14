#!/usr/bin/env bash

##############################################################################
# Standalone test runner for synapse tests
# This will run unit tests using pytest and generate HTML coverage reports.
# The use of this script requires the installation of pytest & pytest-cov
# python packages, which are not required for other synapse developement or
# deployment.
##############################################################################

MODULE=synapse
HTML_DIR=./build/htmlcov
INDEX=$HTML_DIR/index.html

if [ -e $HTML_DIR ]; then
    echo "Removing existing coverage reports."
    rm -rf $HTML_DIR
fi

pytest -v -s --durations 6 --cov $MODULE --no-cov-on-fail --cov-report=html:$HTML_DIR $1

if [ $? -eq 0 ]; then
    if [ -e $INDEX ]; then
        echo "Opening coverage report."
        xdg-open $INDEX &
    fi
fi