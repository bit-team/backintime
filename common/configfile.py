#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey,
#    Germar Reitze
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

"""This module implements a generic configuration file and low level
operations on keys and their values.

Development info: This module will be replaced in the future by Python's
 own ``configparser`` module, or some alternative.
"""

import os
import collections
import re

import gettext
import logger

_ = gettext.gettext


class ConfigFile(object):
    """
    Store options in a plain text file in form of: key=value
    """

    def __init__(self):
        self.dict = {}
        self.errorHandler = None
        self.questionHandler = None

    def setErrorHandler(self, handler):
        """
        Register a function that should be called for notifying errors.

        handler (method):   callable function
        """
        self.errorHandler = handler

    def setQuestionHandler(self, handler):
        """
        Register a function that should be called for asking questions.

        handler (method):   callable function
        """
        self.questionHandler = handler

    def clearHandlers(self):
        """
        Reset error and question handlers.
        """
        self.errorHandler = None
        self.questionHandler = None

    def notifyError(self, message):
        """
        Call previously registered function to show an error.

        Args:
            message (str):  error message that should be shown
        """
        if self.errorHandler is None:
            return
        self.errorHandler(message)

    def askQuestion(self, message):
        """
        Call previously registered function to ask a question.

        Args:
            message (str):    question that should be shown
        """
        if self.questionHandler is None:
            return False
        return self.questionHandler(message)

    def save(self, filename):
        """
        Save all options to file.

        Args:
            filename (str): full path

        Returns:
            bool:           ``True`` if successful
        """
        def numsort(key):
            """
            Sort int in keys in nummeric order instead of alphabetical by adding
            leading zeros to int's
            """
            return re.sub(r'\d+', lambda m: m.group(0).zfill(6), key)
        try:
            with open(filename, 'wt') as f:
                keys = list(self.dict.keys())
                keys.sort(key = numsort)
                for key in keys:
                    f.write("%s=%s\n" % (key, self.dict[key]))
        except OSError as e:
            logger.error('Failed to save config: %s' %str(e), self)
            self.notifyError(_('Failed to save config: %s') %str(e))
            return False
        return True

    def load(self, filename, **kwargs):
        """
        Reset current options and load new options from file.

        Args:
            filename (str): full path
        """
        self.dict = {}
        self.append(filename, **kwargs)

    def append(self, filename, maxsplit=1):
        """
        Load options from file and append them to current options.

        Args:
            filename (str): full path
            maxsplit (int): split lines only n times on '='
        """
        lines = []

        if not os.path.isfile(filename):
            return
        try:
            with open(filename, 'rt') as f:
                lines = f.readlines()
        except OSError as e:
            logger.error('Failed to load config: %s' %str(e), self)
            self.notifyError(_('Failed to load config: %s') %str(e))

        for line in lines:
            items = line.strip('\n').split('=', maxsplit)
            if len(items) == 2:
                self.dict[items[ 0 ] ] = items[ 1]

    def remapKey(self, old_key, new_key):
        """
        Remap keys to a new key name.

        Args:
            old_key (str):  old key name
            new_key (str):  new key name
        """
        if old_key != new_key:
            if old_key in self.dict:
                if new_key not in self.dict:
                    self.dict[new_key ] = self.dict[ old_key]
                del self.dict[old_key]

    def remapKeyRegex(self, pattern, replace):
        """
        Remap keys to a new key name using :py:func:`re.sub`.

        Args:
            pattern (str):  part of key name that should be replaced
            replace (:py:class:`str`, method):
                            string or a callable function which will be used
                            to replace all matches of ``pattern``.
        """
        c = re.compile(pattern)
        for key in list(self.dict):
            newKey = c.sub(replace, key)
            if key != newKey:
                self.remapKey(key, newKey)

    def hasKey(self, key):
        """
        ``True`` if key is set.

        Args:
            key (str):  string used as key

        Returns:
            bool:       ``True`` if the ``key`` is set
        """
        return key in self.dict

    def strValue(self, key, default=''):
        """
        Return a 'str' instance of key's value.

        Args:
            key (str):              string used as key
            default (str):          return this if ``key`` is not set

        Returns:
            str:                    value of ``key`` or ``default``
                                    if ``key`` is not set.
        """
        if key in self.dict:
            return self.dict[key]
        else:
            return default

    def setStrValue(self, key, value):
        """
        Set a string value for key.

        Args:
            key (str):      string used as key
            value (str):    store this value
        """
        self.dict[key] = value

    def intValue(self, key, default=0):
        """
        Return a 'int' instance of key's value.

        Args:
            key (str):              string used as key
            default (int):          return this if ``key`` is not set

        Returns:
            int:                    value of ``key`` or ``default``
                                    if ``key`` is not set.
        """
        try:
            return int(self.dict[key])
        except:
            return default

    def setIntValue(self, key, value):
        """
        Set an integer value for key.

        Args:
            key (str):      string used as key
            value (int):    store this option
        """
        self.setStrValue(key, str(value))

    def boolValue(self, key, default=False):
        """
        Return a 'bool' instance of key's value.

        Args:
            key (str):              string used as key
            default (bool):         return this if key is not set

        Returns:
            bool:                   value of 'key' or 'default'
                                    if 'key' is not set.
        """
        try:
            val = self.dict[key]
            if "1" == val or "TRUE" == val.upper():
                return True
            return False
        except:
            return default

    def setBoolValue(self, key, value):
        """
        Set a bool value for key.

        Args:
            key (str):      string used as key
            value (bool):   store this option
        """
        if value:
            self.setStrValue(key, 'true')
        else:
            self.setStrValue(key, 'false')

    def listValue(self, key, type_key='str:value', default = []):
        """
        Return a list of values

        Size of the list must be stored in key.size

        Args:
            key (str):              used base-key
            type_key (str):         pattern of 'value-type:value-name'.
                                    See examples below.
            default (list):         default value

        Returns:
            list:                   value of ``key`` or ``default``
                                    if ``key`` is not set.

        ``type_key`` pattern examples::

            'str:value'               => return str values from key.value
            'int:type'                => return int values from key.type
            'bool:enabled'            => return bool values from key.enabled
            ('str:value', 'int:type') => return tuple of values

        """
        def typeKeySplit(tk):
            t, k = '', ''
            if isinstance(tk, str):
                t, k = tk.split(':', maxsplit = 1)
            return (t, k)

        def value(key, tk):
            t, k = typeKeySplit(tk)
            if t in ('str', 'int', 'bool'):
                func = getattr(self, '%sValue' %t)
                return func('%s.%s' %(key, k))
            raise TypeError('Invalid type_key: %s' %tk)

        size = self.intValue('%s.size' %key, -1)
        if size < 0:
            return default

        ret = []
        for i in range(1, size + 1):
            if isinstance(type_key, str):
                if not self.hasKey('%s.%s.%s' %(key, i, typeKeySplit(type_key)[1])):
                    continue
                ret.append(value('%s.%s' %(key, i), type_key))
            elif isinstance(type_key, tuple):
                if not self.hasKey('%s.%s.%s' %(key, i, typeKeySplit(type_key[0])[1])):
                    continue
                items = []
                for tk in type_key:
                    items.append(value('%s.%s' %(key, i), tk))
                ret.append(tuple(items))
            else:
                raise TypeError('Invalid type_key: %s' %type_key)
        return ret

    def setListValue(self, key, type_key, value):
        """
        Set a list of values.

        Size of the list will be stored in key.size

        Args:
            key (str):      used base-key
            type_key (str): pattern of 'value-type:value-name'. See examples below.
            value (list):   that should be stored

        ``type_key`` pattern examples::

            'str:value'               => return str values from key.value
            'int:type'                => return int values from key.type
            'bool:enabled'            => return bool values from key.enabled
            ('str:value', 'int:type') => return tuple of values

        """
        def setValue(key, tk, v):
            t = ''
            if isinstance(tk, str):
                t, k = tk.split(':', maxsplit = 1)
            if t in ('str', 'int', 'bool'):
                func = getattr(self, 'set%sValue' %t.capitalize())
                return func('%s.%s' %(key, k), v)
            raise TypeError('Invalid type_key: %s' %tk)

        if not isinstance(value, (list, tuple)):
            raise TypeError('value has wrong type: %s' %value)

        old_size = self.intValue('%s.size' %key, -1)
        self.setIntValue('%s.size' %key, len(value))

        for i, v in enumerate(value, start = 1):
            if isinstance(type_key, str):
                setValue('%s.%s' %(key, i), type_key, v)
            elif isinstance(type_key, tuple):
                for iv, tk in enumerate(type_key):
                    if len(v) > iv:
                        setValue('%s.%s' %(key, i), tk, v[iv])
                    else:
                        self.removeKey('%s.%s.%s' %(key, i, tk.split(':')[1]))
            else:
                raise TypeError('Invalid type_key: %s' %type_key)

        if len(value) < old_size:
            for i in range(len(value) + 1, old_size + 1):
                if isinstance(type_key, str):
                    self.removeKey('%s.%s.%s' %(key, i, type_key.split(':')[1]))
                elif isinstance(type_key, tuple):
                    for tk in type_key:
                        self.removeKey('%s.%s.%s' %(key, i, tk.split(':')[1]))

    def removeKey(self, key):
        """
        Remove key from options.

        Args:
            key (str):    string used as key
        """
        if key in self.dict:
            del self.dict[key]

    def removeKeysStartsWith(self, prefix):
        """
        Remove key from options which start with given prefix.

        Args:
            prefix (str):   prefix for keys (key starts with this string)
                            that should be removed
        """
        removeKeys = []

        for key in self.dict.keys():
            if key.startswith(prefix):
                removeKeys.append(key)

        for key in removeKeys:
            del self.dict[key]

    def keys(self):
        return list(self.dict.keys())


class ConfigFileWithProfiles(ConfigFile):
    """
    Store options in profiles as 'profileX.key=value'.

    Args:
        default_profile_name (str): default name of the first profile.
    """

    def __init__(self, default_profile_name=''):
        ConfigFile.__init__(self)

        self.default_profile_name = default_profile_name
        self.current_profile_id = '1'

    def load(self, filename):
        """
        Reset current options and load new options from file.

        Args:
            filename (str): full path
        """
        self.current_profile_id = '1'
        super(ConfigFileWithProfiles, self).load(filename)

    def append(self, filename):
        """
        Load options from file and append them to current options.

        Args:
            filename (str): full path
        """
        super(ConfigFileWithProfiles, self).append(filename)

        found = False
        profiles = self.profiles()
        for profile_id in profiles:
            if profile_id == self.current_profile_id:
                found = True
                break

        if not found and profiles:
            self.current_profile_id = profiles[0]

        if self.intValue('profiles.version') <= 0:
            rename_keys = []

            for key in self.dict.keys():
                if key.startswith('profile.0.'):
                    rename_keys.append(key)

            for old_key in rename_keys:
                new_key = 'profile1.' + old_key[10 : ]
                self.dict[new_key ] = self.dict[ old_key]
                del self.dict[old_key]

        if self.intValue('profiles.version') != 1:
            self.setIntValue('profiles.version', 1)

    def profiles(self):
        """
        List of all available profile IDs. Profile IDs are strings!

        Returns:
            list:   all available profile IDs as strings
        """
        return self.strValue('profiles', '1').split(':')

    def profilesSortedByName(self):
        """
        List of available profile IDs alphabetically sorted by their names.
        Profile IDs are strings!

        Returns:
            list:   all available profile IDs as strings
        """
        profiles_unsorted = self.profiles()
        if len(profiles_unsorted) <= 1:
            return profiles_unsorted

        profiles_dict = {}

        for profile_id in profiles_unsorted:
            profiles_dict[self.profileName(profile_id).upper()] = profile_id

        # sort the dictionary by key (the profile name)
        profiles_sorted = collections.OrderedDict(sorted(profiles_dict.items()))

        # return the names as a list
        return list(profiles_sorted.values())

    def currentProfile(self):
        """
        Currently selected profile ID. Profile IDs are strings!

        Returns:
            str:    profile ID
        """
        return self.current_profile_id

    def setCurrentProfile(self, profile_id):
        """
        Change the current profile.

        Args:
            profile_id (str, int):  valid profile ID

        Returns:
            bool:                   ``True`` if successful
        """
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        profiles = self.profiles()

        for i in profiles:
            if i == profile_id:
                self.current_profile_id = profile_id
                logger.debug('change current profile: %s=%s'
                             % (profile_id, self.profileName(profile_id)),
                             self)
                logger.changeProfile(profile_id)
                return True

        return False

    def setCurrentProfileByName(self, name):
        """
        Change the current profile.

        Args:
            name (str): valid profile name

        Returns:
            bool:       ``True`` if successful
        """
        profiles = self.profiles()

        for profile_id in profiles:
            if self.profileName(profile_id) == name:
                self.current_profile_id = profile_id
                logger.debug('change current profile: %s' %name, self)
                logger.changeProfile(profile_id)
                return True

        return False

    def profileExists(self, profile_id):
        """
        ``True`` if the profile exists.

        Args:
            profile_id (str, int):  profile ID

        Returns:
            bool:                   ``True`` if ``profile_id`` exists.
        """
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        return profile_id in self.profiles()

    def profileExistsByName(self, name):
        """
        ``True`` if the profile exists.

        Args:
            name (str): profile name

        Returns:
            bool:       ``True`` if ``name`` exists.
        """
        profiles = self.profiles()

        for profile_id in profiles:
            if self.profileName(profile_id) == name:
                return True

        return False

    def profileName(self, profile_id=None):
        """
        Name of the profile.

        Args:
            profile_id (str, int):  valid profile ID

        Returns:
            str:                    name of profile
        """
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        if profile_id is None:
            profile_id = self.current_profile_id
        if profile_id == '1':
            default = self.default_profile_name
        else:
            default = 'Profile %s' % profile_id
        return self.profileStrValue('name', default, profile_id)

    def addProfile(self, name):
        """
        Add a new profile if the name is not already in use.

        Args:
            name (str): new profile name

        Returns:
            str:        new profile ID
        """
        profiles = self.profiles()

        for profile_id in profiles:
            if self.profileName(profile_id) == name:
                self.notifyError(_('Profile "%s" already exists !') % name)
                return None

        new_id = 1
        while True:
            ok = True

            if str(new_id) in profiles:
                ok = False

            if ok:
                break

            new_id = new_id + 1

        new_id = str(new_id)

        profiles.append(new_id)
        self.setStrValue('profiles', ':'.join(profiles))

        self.setProfileStrValue('name', name, new_id)
        return new_id

    def removeProfile(self, profile_id=None):
        """
        Remove profile and all its keys and values.

        Args:
            profile_id (str, int):  valid profile ID

        Returns:
            bool:   ``True`` if successful
        """
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        if profile_id == None:
            profile_id = self.current_profile_id

        profiles = self.profiles()
        if len(profiles) <= 1:
            self.notifyError(_('You can\'t remove the last profile !'))
            return False

        found = False
        index = 0
        for profile in profiles:
            if profile == profile_id:
                self.removeKeysStartsWith(self.profileKey('', profile_id))
                del profiles[index]
                self.setStrValue('profiles', ':'.join(profiles))
                found = True
                break
            index = index + 1

        if not found:
            return False

        if self.current_profile_id == profile_id:
            self.current_profile_id = '1'

        return True

    def setProfileName(self, name, profile_id=None):
        """
        Change the name of the profile.

        Args:
            name (str):             new profile name
            profile_id (str, int):  valid profile ID

        Returns:
            bool:                   ``True`` if successful.
        """
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        if profile_id == None:
            profile_id = self.current_profile_id

        profiles = self.profiles()

        for profile in profiles:
            if self.profileName(profile) == name:
                if profile[0] != profile_id:
                    self.notifyError(_('Profile "%s" already exists !') % name)
                    return False

        self.setProfileStrValue('name', name, profile_id)
        return True

    def profileKey(self, key, profile_id=None):
        """
        Prefix for keys with profile. e.g. 'profile1.key'

        Args:
            key (str):              key name
            profile_id (str, int):  valid profile ID

        Returns:
            str:                    key with prefix 'profile1.key'
        """
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        if profile_id is None:
            profile_id = self.current_profile_id
        return 'profile' + profile_id + '.' + key

    def removeProfileKey(self, key, profile_id=None):
        """
        Remove the key from profile.

        Args:
            key (str):              key name
            profile_id (str, int):  valid profile ID
        """
        self.removeKey(self.profileKey(key, profile_id))

    def removeProfileKeysStartsWith(self, prefix, profile_id=None):
        """
        Remove the keys starting with prefix from profile.

        Args:
            prefix (str):           prefix for keys (key starts with this
                                    string) that should be removed.
            profile_id (str, int):  valid profile ID
        """
        self.removeKeysStartsWith(self.profileKey(prefix, profile_id))

    def remapProfileKey(self, oldKey, newKey, profileId=None):
        """
        Remap profile keys to a new key name.

        Args:
            oldKey (str):           old key name
            newKey (str):           new key name
            profileId (str, int):   valid profile ID
        """
        self.remapKey(self.profileKey(oldKey, profileId),
                      self.profileKey(newKey, profileId))

    def hasProfileKey(self, key, profile_id=None):
        """
        ``True`` if key is set in profile.

        Args:
            key (str):              string used as key
            profile_id (str, int):  valid profile ID

        Returns:
            bool:                   ``True`` if ``key`` is set.
        """
        return self.profileKey(key, profile_id) in self.dict

    def profileStrValue(self, key, default='', profile_id=None):
        return self.strValue(self.profileKey(key, profile_id), default)

    def setProfileStrValue(self, key, value, profile_id=None):
        self.setStrValue(self.profileKey(key, profile_id), value)

    def profileIntValue(self, key, default=0, profile_id=None):
        return self.intValue(self.profileKey(key, profile_id), default)

    def setProfileIntValue(self, key, value, profile_id=None):
        self.setIntValue(self.profileKey(key, profile_id), value)

    def profileBoolValue(self, key, default=False, profile_id=None):
        return self.boolValue(self.profileKey(key, profile_id), default)

    def setProfileBoolValue(self, key, value, profile_id=None):
        self.setBoolValue(self.profileKey(key, profile_id), value)

    def profileListValue(self, key, type_key='str:value', default = [], profile_id = None):
        return self.listValue(self.profileKey(key, profile_id), type_key, default)

    def setProfileListValue(self, key, type_key, value, profile_id=None):
        self.setListValue(self.profileKey(key, profile_id), type_key, value)
