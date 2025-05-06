# SPDX-FileCopyrightText: © 2015-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.

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
