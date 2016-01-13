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

# License

LINC is an open source shared database and facial recognition
system that allows for collaboration in wildlife monitoring.
Copyright (C) 2016  Wildlifeguardians

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

For more information or to contact visit linclion.org or email tech@linclion.org
