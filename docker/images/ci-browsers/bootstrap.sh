#!/bin/bash

set -ex

# Install xvfb; prepare a docker entrypoint to allow it to run
apt update
apt-get install -y \
  xvfb
printf '#!/bin/sh\nXvfb :99 -screen 0 1280x1024x24 &\nexec "$@"\n' | tee /docker-entrypoint.sh && \
  chmod +x /docker-entrypoint.sh

# Playwright chromium related dependencies
apt-get install -y \
  libnss3 \
  libxss1 \
  libasound2 \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libxcomposite1 \
  libcups2 \
  libgtk-3-0 \
  libdrm2 \
  libgbm1

# Track node aliases from circlci
ALIASES=/build/ci-browser/nodeAliases.txt
NODE_SRC=/build/ci-browser/nnode.tar.zx
curl -sSL "https://raw.githubusercontent.com/CircleCI-Public/cimg-node/main/ALIASES" -o ${ALIASES}

NODE_VERSION=$(grep "lts" ${ALIASES} | cut -d "=" -f 2-)

[[ $(uname -m) == "x86_64" ]] && ARCH="x64" || ARCH="arm64"

curl -L "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz" -o $NODE_SRC

tar -xJf ${NODE_SRC} -C /usr/local --strip-components=1
ln -s /usr/local/bin/node /usr/local/bin/nodejs
npm install -g yarn pnpm

apt-get purge

rm -rf /build
rm -r /var/lib/apt/lists/*
