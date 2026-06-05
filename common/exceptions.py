# SPDX-FileCopyrightText: © 2015-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
from typing import Optional


class ApplicationError(Exception):
    """Base class for failures related to the application itself.

    The class distinguish between log errors and user errors presented in the
    GUI.  Log message is untranslated and UI message is translated. Against
    principels of clean architecture both messages are defined at the point of
    raising the exception. The intention is to avoid any runtime mapping layer
    or translation indirection. This is a deliberate design choice to keep the
    system simple, avoid error-code mapping tables and ensure that log output
    and UI messages can evolve independently while remaining close together in
    the code.
    """
    def __init__(
            self,
            log_msg: str,
            gui_msg: Optional[str] = None
    ):
        if type(self) is ApplicationError:
            raise TypeError(
                f'{type(self)} is an abstract base class not '
                'intended to get instantiated.'
            )

        self.log_msg = log_msg
        self.gui_msg = gui_msg if gui_msg else log_msg

        super().__init__(self.log_msg)


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
