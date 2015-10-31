# Installation

## install nvm
curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.25.4/install.sh | bash

## install latest nodejs stable
nvm install stable
nvm use stable
nvm ls

## install aglio
npm install -g aglio --python=/usr/bin/python

## generate API
aglio -i docs/api.md -o index.html

## Notes:
# api.md contains current production API