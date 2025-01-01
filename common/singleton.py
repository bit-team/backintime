# SPDX-FileCopyrightText: © 2022 Mars Landis
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: CC0-1.0
#
# This file is released under Creative Commons Zero 1.0 (CC0-1.0) and part of
# the program "Back In Time". The program as a whole is released under GNU
# General Public License v2 or any later version (GPL-2.0-or-later).
# See file/folder LICENSE or
# go to <https://spdx.org/licenses/CC0-1.0.html>
# and <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Credits to Mr. Mars Landis describing that solution and comparing it to
# alternatives in his article 'Better Python Singleton with a Metaclass' at
# <https://python.plainenglish.io/better-python-singleton-with-a-metaclass-41fb8bfe2127>
# himself referring to this Stack Overflow
# <https://stackoverflow.com/q/6760685/4865723> question as his inspiration.
#
# Original code adapted by Christian Buhtz.

"""Flexible and pythonic singleton implementation.

Support inheritance and multiple classes. Multilevel inheritance is
theoretically possible if the '__allow_reinitialization' approach would be
implemented as described in the original article.

Example ::

    >>> from singleton import Singleton
    >>>
    >>> class Foo(metaclass=Singleton):
    ...     def __init__(self):
    ...          self.value = 'Alyssa Ogawa'
    >>>
    >>> class Bar(metaclass=Singleton):
    ...     def __init__(self):
    ...          self.value = 'Naomi Wildmann'
    >>>
    >>> f = Foo()
    >>> ff = Foo()
    >>> f'{f.value=} :: {ff.value=}'
    "f.value='Alyssa Ogawa' :: ff.value='Alyssa Ogawa'"
    >>> ff.value = 'Who?'
    >>> f'{f.value=} :: {ff.value=}'
    "f.value='Who?' :: ff.value='Who?'"
    >>>
    >>> b = Bar()
    >>> bb = Bar()
    >>> f'{b.value=} :: {bb.value=}'
    "b.value='Naomi Wildmann' :: bb.value='Naomi Wildmann'"
    >>> b.value = 'thinking ...'
    >>> f'{b.value=} :: {bb.value=}'
    "b.value='thinking ...' :: bb.value='thinking ...'"
    >>>
    >>> id(f) == id(ff)
    True
    >>> id(b) == id(bb)
    True
    >>> id(f) == id(b)
    False
"""


class Singleton(type):
    """Singleton implementation supporting inheritance and multiple classes."""

    _instances = {}
    """Hold single instances of multiple classes."""

    def __call__(cls, *args, **kwargs):

        try:
            # Reuse existing instance
            return cls._instances[cls]

        except KeyError:
            # Create new instance
            cls._instances[cls] = super().__call__(*args, **kwargs)

            return cls._instances[cls]
