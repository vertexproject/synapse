#!/usr/bin/env bash
if [ -d ~/.pyenv ]; then
  exit 0
fi
# Install xz
brew install xz
# Clone repos
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
git clone https://github.com/pyenv/pyenv-virtualenv.git ~/.pyenv/plugins/pyenv-virtualenv
# Set envars
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
# Install shims
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bash_profile
# Source ~/.bash_profile
source ~/.bash_profile
# install python 3.6.5
pyenv install 3.6.5
