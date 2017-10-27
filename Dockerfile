# vim:set ft=dockerfile:
FROM python:3.6

ENV DEBIAN_FRONTEND="noninteractive"

COPY . /root/git/synapse
RUN mkdir /syndata \
 && apt-get update -q \
 && apt-get install -yq --no-install-recommends \
    build-essential \
    cron \
    libffi-dev \
    libssl-dev \
    locales \
 && apt-get clean \
 && apt-get purge \
 && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
 && locale-gen en_US.UTF-8 \
 && dpkg-reconfigure locales \
 && /usr/sbin/update-locale LANG=en_US.UTF-8 \
 && cd /root/git/synapse && python setup.py install \
 && cp synapse/docker/cortex/ram_dmon.json /syndata/dmon.json
ENV LANG="en_US.UTF-8" LANGUAGE="en_US.UTF-8" LC_ALL="en_US.UTF-8"

VOLUME /syndata
VOLUME /root/git/synapse

WORKDIR /root/git/synapse
EXPOSE 47322
ENTRYPOINT ["python", "-m", "synapse.tools.dmon", "/syndata/dmon.json"]
