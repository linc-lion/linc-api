# LINC is an open source shared database and facial recognition
# system that allows for collaboration in wildlife monitoring.
# Copyright (C) 2016  Wildlifeguardians
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information or to contact visit linclion.org or email tech@linclion.org

import functools
# The _checkAuth should return a user object, and this
# configure which property from that objet get the 'role'
_userRolePropertyName = 'role'

def _checkRole(role, roles):
    ''' Check given role is inside or equals to roles '''
    # Roles is a list not a single element
    if isinstance(roles, list):
        found = False
        for r in roles:
            if r == role:
                found = True
                break
        if found == True:
            return True
    # Role is a single string
    else:
        if role == roles:
            return True
    return False

def allowedRole(roles = None):
    def decorator(func):
        def decorated(self, *args, **kwargs):
            user = self.current_user
            # User is refused
            if user is None:
                raise Exception('Cannot proceed role check: user not found')
            role = user[_userRolePropertyName]
            if _checkRole(role, roles) == False:
                self.set_status(403)
                self._transforms = []
                self.finish({'status':'error','message':'endpoint not allowed for the current user role'})
                return None
            return func(self, *args, **kwargs)
        return decorated
    return decorator

def refusedRole(roles = None):
    def decorator(func):
        def decorated(self, *args, **kwargs):
            user = self.current_user
            # User is refused
            if user is None:
                raise Exception('Cannot proceed role check: user not found')
            role = user[_userRolePropertyName]
            if _checkRole(role, roles) == True:
                self.set_status(403)
                self._transforms = []
                self.finish({'status':'error','message':'endpoint not allowed for the current user role'})
                return None
            return func(self, *args, **kwargs)
        return decorated
    return decorator

def api_authenticated(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if hasattr(self,'token_passed_but_invalid'):
                self.response(401,'Authentication token passed is invalid. You must do login again.')
            else:
                self.response(401,'Authentication required.')
            return
        return method(self, *args, **kwargs)
    return wrapper
