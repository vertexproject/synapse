#!/bin/bash

PREBOOT_SCRIPT=/vertex/scripts/preboot.sh
CONCURRENT_SCRIPT=/vertex/scripts/concurrent.sh

DO_PREBOOT=0
DO_CONCURRENT=0

echo $SHELL

# Preconditions
if [ -f $PREBOOT_SCRIPT ]
then
    if [ -x $PREBOOT_SCRIPT ]
    then
        DO_PREBOOT=1
        echo "Set DO_PREBOOT=$DO_PREBOOT"
    else
        echo "$PREBOOT_SCRIPT exists but is not marked executable."
        exit 1
    fi
fi

if [ -f $CONCURRENT_SCRIPT ]
then
    if [ -x $CONCURRENT_SCRIPT ]
    then
        DO_CONCURRENT=1
        echo "Set DO_CONCURRENT=$DO_CONCURRENT"
    else
        echo "$CONCURRENT_SCRIPT exists but is not marked executable."
        exit 1
    fi
fi


echo "preboot = $DO_PREBOOT"
echo "concurrent = $DO_CONCURRENT"

# Inline preboot script
if [ $DO_PREBOOT -eq 1 ]
then
    echo "Executing $PREBOOT_SCRIPT"
    ./$PREBOOT_SCRIPT
    PREBOOT_CODE=$?
    if [ $PREBOOT_CODE -ne 0 ]
    then
        echo "$PREBOOT_SCRIPT script failed with return value $PREBOOT_CODE"
        exit 1
    fi
fi

# Parallel script
if [ $DO_CONCURRENT -eq 1 ]
then
    echo "Executing $CONCURRENT_SCRIPT"
    nohup exec $CONCURRENT_SCRIPT
    echo "Done executing concurrent script"
fi

# Execute our service
exec python -O -m synapse.servers.aha /vertex/storage
