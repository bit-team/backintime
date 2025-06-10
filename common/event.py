# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Code originally from the "Feedybus" project. Author of that project is also
# the author of this file.
"""Module offering an event class do realize observer pattern.

It is not a classic textbook-accurate implementation of the observer pattern,
but rather a simple, pragmatic and pythonic solution. The solution is inspired
by discussion and code in https://stackoverflow.com/a/48339861/4865723 .

The subject owns an instance of the `Event` class and teh observer registers to
that instance. Thats it.

Example :

    .. python::
        class SomeData:
            def __init__(self):
                self.event_data_modified = Event()

            def do_modify_data(self):
                # ... modify data ...

                # Notify observers
                self.event_data_modified.notify()


        class ListWidget:
            def _init__(self, data):
                data.register(self._handle_data_modified)

            def _handle_data_modified(self):
                print('data was modified')
"""
from contextlib import contextmanager


class Event:
    """Pragmatic and pythonic implementation of Obserer pattern.

    Inspired by discussion and code in
    https://stackoverflow.com/a/48339861/4865723
    """
    def __init__(self):
        self._callbacks = []

    def notify(self, *args, **kwargs):
        """Notify registered observers.

        The args, and kwargs are given to te observers.
        """
        for callback in self._callbacks:
            callback(*args, **kwargs)

    def register(self, callback):
        """Register an observer (callback function)."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

        return callback

    def deregister(self, callback):
        """Deregister / remove an observer (callback function)."""
        self._callbacks.remove(callback)

    @contextmanager
    def keep_silent(self):
        """A context manager function to suppress notification of the
           observers."""
        silent_callbacks = []
        try:
            silent_callbacks = self._callbacks
            self._callbacks = []

            yield

        finally:
            if silent_callbacks:
                self._callbacks = silent_callbacks
