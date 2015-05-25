#!/usr/bin/env python3
#    Back In Time
#    Copyright (C) 2012-2015 Germar Reitze
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

import re
import os
import sys
from time import strftime, gmtime

PATH = os.path.join(os.getcwd(), os.path.dirname(sys.argv[0]))

CONFIG = os.path.join(PATH, 'config.py')
MAN    = os.path.join(PATH, 'man/C/backintime-config.1')
with open(os.path.join(PATH, '../VERSION'), 'r') as f:
    VERSION = f.read().strip('\n')
SORT = True #True = sort by alphabet; False = sort by line numbering
c = re.compile(r'.*?self\.get((?:_profile)?)_(.*?)_value ?\( ?[\'"](.*?)[\'"] ?(%?[^,]*?), ?[\'"]?([^\'",\)]*)[\'"]?')
c_default = re.compile(r'(^DEFAULT[\w]*)[\s]*= ([\w]*)')

HEADER = '''.TH backintime-config 1 "%s" "version %s" "USER COMMANDS"
.SH NAME
config \- BackInTime configuration files.
.SH SYNOPSIS
~/.config/backintime/config
.br
/etc/backintime/config
.SH DESCRIPTION
Back In Time was developed as pure GUI program and so most functions are only 
useable with backintime-gnome or backintime-kde4. But it is possible to use 
Back In Time e.g. on a headless server. You have to create the configuration file
(~/.config/backintime/config) manually. Look inside /usr/share/doc/backintime\-common/examples/ for examples.
.PP
The configuration file has the following format:
.br
keyword=arguments
.PP
Arguments don't need to be quoted. All characters are allowed except '='.
.PP
The given path (\\fIprofile<N>.snapshots.path\\fR, \\fIprofile<N>.snapshots.local_encfs.path\\fR 
or \\fIprofile<N>.snapshots.ssh.path\\fR) must contain a folderstructure like 
backintime/<HOST>/<USER>/<PROFILE_ID>. This has to be created manually.
.PP
Also the crontab entry for automatic backup shedules has to be created manually.
.PP
crontab example:
.br
0 */2 * * * nice \-n 19 ionice \-c2 \-n7 /usr/bin/backintime \-\-backup-job >/dev/null 2>&1
.SH POSSIBLE KEYWORDS
''' % (strftime('%b %Y', gmtime()), VERSION)

FOOTER = '''.SH SEE ALSO
backintime, backintime-qt4.
.PP
Back In Time also has a website: http://backintime.le\-web.org
.SH AUTHOR
This manual page was written by BIT Team(<bit\-team@lists.launchpad.net>).
'''

TYPE      = 'type'
NAME      = 'name'
VALUES    = 'values'
DEFAULT   = 'default'
COMMENT   = 'comment'
REFERENCE = 'reference'
LINE      = 'line'

def output(type = '', name = '', values = '', default = '', comment = '', reference = '', line = 0):
    if not default:
        default = "''"
    ret  = '.IP "\\fI%s\\fR" 6\n' % name
    ret += '.RS\n'
    ret += 'Type: %-10sAllowed Values: %s\n' %(type, values)
    ret += '.br\n'
    ret += '%s\n' % comment
    ret += '.PP\n'
    if SORT:
        ret += 'Default: %s\n' % default
    else:
        ret += 'Default: %-18s %s line: %d\n' % (default, reference, line)
    ret += '.RE\n'
    return ret

def select(a, b):
    if a:
        return a
    return b

def select_values(type, values):
    if values:
        return values
    if type == 'bool':
        return 'true|false'
    if type == 'str':
        return 'text'
    if type == 'int':
        return '0-99999'

def main():
    replace_default = {}
    dict = {}
    dict['profiles.version'] = {TYPE      : 'int',
                                NAME      : 'profiles.version',
                                VALUES    : '1',
                                DEFAULT   : '1',
                                COMMENT   : 'Internal version of profiles config.',
                                REFERENCE : 'configfile.py',
                                LINE      : 180}
    dict['profiles'] = {TYPE      : 'str',
                        NAME      : 'profiles',
                        VALUES    : 'int separated by colon (e.g. 1:3:4)',
                        DEFAULT   : '1',
                        COMMENT   : 'All active Profiles (<N> in profile<N>.snapshots...).',
                        REFERENCE : 'configfile.py',
                        LINE      : 273}
    dict['profile<N>.name'] = {TYPE      : 'str',
                               NAME      : 'profile<N>.name',
                               VALUES    : 'text',
                               DEFAULT   : 'Main profile',
                               COMMENT   : 'Name of this profile.',
                               REFERENCE : 'configfile.py',
                               LINE      : 246}
    with open(CONFIG, 'r') as f:
        commentline = ''
        comment = values = force_var = force_default = type = name = var = default = None
        for counter, line in enumerate(f, 1):
            line = line.lstrip()
            m_default = c_default.match(line)
            if m_default:
                replace_default[m_default.group(1)] = m_default.group(2)
                continue
            if line.startswith('#?'):
                commentline += line.lstrip('#?').rstrip('\n')
                continue
            if line.startswith('#'):
                commentline = ''
                continue
            m = c.match(line)
            if not m is None:
                profile, type, name, var, default = m.groups()
                if profile == '_profile':
                    name = 'profile<N>.' + name
                var = var.lstrip('% ')
                key = re.sub(r'%[\S]', var, name).lower()
                #Ignore commentlines with #?! and 'config.version'
                if not commentline.startswith('!') and not name == 'config.version' and not key in dict:
                    dict[key] = {}
                    commentline = commentline.split(';')
                    try:
                        comment       = commentline[0]
                        values        = commentline[1]
                        force_default = commentline[2]
                        force_var     = commentline[3]
                    except IndexError:
                        pass

                    if default.startswith('self.') and default[5:] in replace_default:
                        default = replace_default[default[5:]]

                    if type == 'bool':
                        default = default.lower()
                    dict[key][TYPE]      = type
                    dict[key][NAME]      = re.sub(r'%[\S]', '<%s>' % select(force_var, var).upper(), name)
                    dict[key][VALUES]    = select_values(type, values)
                    dict[key][DEFAULT]   = select(force_default, default)
                    dict[key][COMMENT]   = re.sub(r'\\n', '\n.br\n', comment)
                    dict[key][REFERENCE] = 'config.py'
                    dict[key][LINE]      = counter

                comment = values = force_var = force_default = type = name = var = default = None
                commentline = ''

    with open(MAN, 'w') as f:
        f.write(HEADER)
        if SORT:
            s = lambda x: x
        else:
            s = lambda x: dict[x][LINE]
        f.write('\n'.join(output(**dict[key]) for key in sorted(dict, key = s)))
        f.write(FOOTER)

if __name__ == "__main__":
    main()
