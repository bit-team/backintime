#    Copyright (C) 2015-2022 Germar Reitze
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

class BackInTimeException(Exception):
    pass

class MountException(BackInTimeException):
    pass

class NoPubKeyLogin(MountException):
    pass

class KnownHost(MountException):
    pass

class HashCollision(BackInTimeException):
    pass

class EncodeValueError(BackInTimeException):
    pass

class StopException(BackInTimeException):
    pass

class Timeout(BackInTimeException):
    pass

class LastSnapshotSymlink(BackInTimeException):
    pass

class InvalidChar(BackInTimeException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class InvalidCmd(BackInTimeException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class LimitExceeded(BackInTimeException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class PermissionDeniedByPolicy(BackInTimeException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
