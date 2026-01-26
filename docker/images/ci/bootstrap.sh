#!/bin/bash

apt-get update

# Install services that CircleCI requires in order to run.
apt-get install -y \
  git \
  git-lfs \
  ssh \
  tar \
  gzip \
  ca-certificates

# Additional packages in stalled in cimg:base that have been assumed to be present
apt-get install -y \
  build-essential \
  libarchive \
  libarchive-dev

# These items are installed as part of the cimg/python:3.x builds
apt-get install -y \
  libbz2-dev \
  liblzma-dev \
  libncurses5-dev \
  libncursesw5-dev \
  libreadline-dev \
  libffi-dev \
  libsqlite3-dev \
  libssl-dev \
  libxml2-dev \
  libxmlsec1-dev \
  llvm \
  make \
  tk-dev \
  wget \
  xz-utils \
  zlib1g-dev

# Additional convenience tools that we need or would be useful
# to have when debugging in a live CI session.
apt-get install -y \
  curl \
  tree \
  nano \
  net-tools

# Cleanup apt cache data; downstream users that need to install
# packages are expected to run apt-get update on their own.
apt-get purge

rm -rf /build
rm -r /var/lib/apt/lists/*
