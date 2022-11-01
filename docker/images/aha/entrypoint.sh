#!/bin/bash

PREBOOT_SCRIPT=/vertex/preboot/run
CONCURRENT_SCRIPT=/vertex/concurrent/run

# Preconditions
if [ -f $PREBOOT_SCRIPT ]
then
    if [ -x $PREBOOT_SCRIPT ]
    then
        echo "Executing $PREBOOT_SCRIPT"
        ./$PREBOOT_SCRIPT
        PREBOOT_CODE=$?
        if [ $PREBOOT_CODE -ne 0 ]
        then
            echo "$PREBOOT_SCRIPT script failed with return value $PREBOOT_CODE"
            exit 1
        fi
    else
        echo "$PREBOOT_SCRIPT exists but is not marked executable."
        exit 1
    fi
fi

if [ -f $CONCURRENT_SCRIPT ]
then
    if [ -x $CONCURRENT_SCRIPT ]
    then
        echo "Executing $CONCURRENT_SCRIPT"
        # FIXME is this correct?
        # Can we redirect stdout / stderr here?
#         nohup exec $CONCURRENT_SCRIPT
    else
        echo "$CONCURRENT_SCRIPT exists but is not marked executable."
        exit 1
    fi
fi

# Execute our service
exec python -O -m synapse.servers.aha /vertex/storage
