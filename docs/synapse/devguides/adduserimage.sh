#!/bin/bash
# Add a user to a debian based container with an arbitrary uid/gid value.
# default username: altuser
# default uid: 8888

set -e

if [ -z $1 ]
then
    echo "Usage: srcImage name id suffix"
    echo "srcImage required."
    exit 1
fi

SRC_IMAGE_NAME=$1
NEW_NAME=${2:-altuser}
NEW_ID=${3:-8888}
SUFFIX=-${4:-$NEW_NAME}

echo "Add user/group ${NEW_NAME} with ${NEW_ID} into ${SRC_IMAGE_NAME}, creating: ${SRC_IMAGE_NAME}${SUFFIX}"

printf "FROM $SRC_IMAGE_NAME \
\nRUN set -ex \\
    && groupadd -g $NEW_ID $NEW_NAME \\
    && useradd -r --home-dir=/home/$NEW_NAME -u $NEW_ID -g $NEW_NAME --shell /bin/bash $NEW_NAME \\
    && mkdir -p /home/$NEW_NAME \\
    && chown $NEW_ID:$NEW_ID /home/$NEW_NAME\n" > ./Dockerfile

docker build -t $SRC_IMAGE_NAME$SUFFIX -f ./Dockerfile .

rm ./Dockerfile

exit 0
