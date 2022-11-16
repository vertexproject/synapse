#!/bin/bash

PREBOOT_SCRIPT=/vertex/preboot/run
CONCURRENT_SCRIPT=/vertex/concurrent/run

if [ -f $PREBOOT_SCRIPT ]
then
    echo "Executing $PREBOOT_SCRIPT"
    ./$PREBOOT_SCRIPT
    if [ $? -ne 0 ]
    then
        echo "$PREBOOT_SCRIPT script failed with return value $?"
        exit 1
    fi
fi

if [ -f $CONCURRENT_SCRIPT ]
then
    echo "Executing and backgrounding $CONCURRENT_SCRIPT"
    ./$CONCURRENT_SCRIPT &
fi


exec python -O -m synapse.servers.axon /vertex/storage
