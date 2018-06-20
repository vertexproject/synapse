#!/usr/bin/env bash

###############################################################################
#
# https://github.com/renskiy/cron-docker-image/blob/master/debian/start-cron
# license for the original code is below.
# fork of the repository it here
# https://github.com/vertexproject/cron-docker-image
###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Rinat Khabibiev
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
###############################################################################

# make link to custom location of /etc/cron.d if provided
if [ "${CRON_PATH}" ]; then
    echo "CRON_PATH provided, creating link: /etc/cron.d -> ${CRON_PATH}"
    ln -sf "${CRON_PATH}" /etc/cron.d
fi

# remove write permission for (g)roup and (o)ther (required by cron)
chmod -R go-w /etc/cron.d

# setting user for additional cron jobs
case $1 in
-u=*|--user=*)
    crontab_user="-u ${1#*=}"
    shift
    ;;
-u|--user)
    crontab_user="-u $2"
    shift 2
    ;;
-*)
    echo "Unknown option: ${1%=*}" > /dev/stderr
    exit 1
    ;;
*)
    crontab_user=""
    ;;
esac

# adding additional cron jobs passed by arguments
# every job must be a single quoted string and have standard crontab format,
# e.g.: start-cron --user user "0 \* \* \* \* env >> /var/log/cron.log 2>&1"
{ for cron_job in "$@"; do echo -e ${cron_job}; done } \
    | sed --regexp-extended 's/\\(.)/\1/g' \
    | crontab ${crontab_user} -

# update default values of PAM environment variables (used by CRON scripts)
env | while read -r line; do  # read STDIN by line
    # split LINE by "="
    IFS="=" read var val <<< ${line}
    # remove existing definition of environment variable, ignoring exit code
    sed --in-place "/^${var}[[:blank:]=]/d" /etc/security/pam_env.conf || true
    # append new default value of environment variable
    echo "${var} DEFAULT=\"${val}\"" >> /etc/security/pam_env.conf
done

# start cron
service cron start

# trap SIGINT and SIGTERM signals and gracefully exit
trap "service cron stop; kill \$!; exit" SIGINT SIGTERM

# start "daemon"
while true
do
    # watch /var/log/cron.log restarting if necessary
    cat /var/log/cron.log & wait $!
done
