#!/usr/bin/env bash

##############################################################################
# Standalone test runner for synapse tests
# This will run unit tests using nosetests and generate HTML coverage reports.
# The use of this script requires the installation of nose & coverage python
# packages, which are not required for other synapse developement/deployment.
##############################################################################

MODULE=synapse
HTML_DIR=./htmlcov
INDEX=$HTML_DIR/index.html

if [ -e $HTML_DIR ]; then
    echo "Removing existing coverage reports."
    rm -rf $HTML_DIR
fi

nosetests --verbosity=3 --with-coverage --cover-erase --cover-html --cover-html-dir=$HTML_DIR --cover-package=$MODULE $1

if [ $? -eq 0 ]; then
    if [ -e $INDEX ]; then
        echo "Opening coverage report."
        xdg-open $INDEX &
    fi
fi