#    Back In Time
#    Copyright (C) 2012-2016 Germar Reitze
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

c_list = re.compile(r'.*?self\.(?!set)((?:profile)?)(List)Value ?\( ?[\'"](.*?)[\'"], ?((?:\(.*\)|[^,]*)), ?[\'"]?([^\'",\)]*)[\'"]?')
c =      re.compile(r'.*?self\.(?!set)((?:profile)?)(.*?)Value ?\( ?[\'"](.*?)[\'"] ?(%?[^,]*?), ?[\'"]?([^\'",\)]*)[\'"]?')
c_default = re.compile(r'(^DEFAULT[\w]*|CONFIG_VERSION)[\s]*= (.*)')

HEADER = '''.TH backintime-config 1 "%s" "version %s" "USER COMMANDS"
.SH NAME
config \- BackInTime configuration files.
.SH SYNOPSIS
~/.config/backintime/config
.br
/etc/backintime/config
.SH DESCRIPTION
Back In Time was developed as pure GUI program and so most functions are only
useable with backintime-qt. But it is possible to use
Back In Time e.g. on a headless server. You have to create the configuration file
(~/.config/backintime/config) manually. Look inside /usr/share/doc/backintime\-common/examples/ for examples.
.PP
The configuration file has the following format:
.br
keyword=arguments
.PP
Arguments don't need to be quoted. All characters are allowed except '='.
.PP
Run 'backintime check-config' to verify the configfile, create the snapshot folder and crontab entries.
.SH POSSIBLE KEYWORDS
''' % (strftime('%b %Y', gmtime()), VERSION)

FOOTER = '''.SH SEE ALSO
backintime, backintime-qt.
.PP
Back In Time also has a website: https://github.com/bit-team/backintime
.SH AUTHOR
This manual page was written by BIT Team(<bit\-team@lists.launchpad.net>).
'''

INSTANCE  = 'instance'
NAME      = 'name'
VALUES    = 'values'
DEFAULT   = 'default'
COMMENT   = 'comment'
REFERENCE = 'reference'
LINE      = 'line'

def output(instance = '', name = '', values = '', default = '', comment = '', reference = '', line = 0):
    if not default:
        default = "''"
    ret  = '.IP "\\fI%s\\fR" 6\n' % name
    ret += '.RS\n'
    ret += 'Type: %-10sAllowed Values: %s\n' %(instance.lower(), values)
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

def select_values(instance, values):
    if values:
        return values
    if instance.lower() == 'bool':
        return 'true|false'
    if instance.lower() == 'str':
        return 'text'
    if instance.lower() == 'int':
        return '0-99999'

def process_line(d, key, profile, instance, name, var, default, commentline, values, force_var, force_default, replace_default, counter):
    #Ignore commentlines with #?! and 'config.version'
    comment = None
    if not commentline.startswith('!') and not key in d:
        d[key] = {}
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

        if isinstance(force_default, str) and force_default.startswith('self.') and force_default[5:] in replace_default:
            force_default = replace_default[force_default[5:]]

        if instance.lower() == 'bool':
            default = default.lower()
        d[key][INSTANCE]  = instance
        d[key][NAME]      = re.sub(r'%[\S]', '<%s>' % select(force_var, var).upper(), name)
        d[key][VALUES]    = select_values(instance, values)
        d[key][DEFAULT]   = select(force_default, default)
        d[key][COMMENT]   = re.sub(r'\\n', '\n.br\n', comment)
        d[key][REFERENCE] = 'config.py'
        d[key][LINE]      = counter

def main():
    replace_default = {}
    d = {}
    d['profiles.version'] = {INSTANCE  : 'int',
                             NAME      : 'profiles.version',
                             VALUES    : '1',
                             DEFAULT   : '1',
                             COMMENT   : 'Internal version of profiles config.',
                             REFERENCE : 'configfile.py',
                             LINE      : 419}
    d['profiles'] = {INSTANCE  : 'str',
                     NAME      : 'profiles',
                     VALUES    : 'int separated by colon (e.g. 1:3:4)',
                     DEFAULT   : '1',
                     COMMENT   : 'All active Profiles (<N> in profile<N>.snapshots...).',
                     REFERENCE : 'configfile.py',
                     LINE      : 472}
    d['profile<N>.name'] = {INSTANCE  : 'str',
                            NAME      : 'profile<N>.name',
                            VALUES    : 'text',
                            DEFAULT   : 'Main profile',
                            COMMENT   : 'Name of this profile.',
                            REFERENCE : 'configfile.py',
                            LINE      : 704}
    with open(CONFIG, 'r') as f:
        commentline = ''
        values = force_var = force_default = instance = name = var = default = None
        for counter, line in enumerate(f, 1):
            line = line.lstrip()
            m_default = c_default.match(line)
            if m_default:
                replace_default[m_default.group(1)] = m_default.group(2).replace('\\$', '\\\$')
                continue
            if line.startswith('#?'):
                if commentline and not ';' in commentline and not commentline.endswith('\\n'):
                    commentline += ' '
                commentline += line.lstrip('#?').rstrip('\n')
                continue
            if line.startswith('#'):
                commentline = ''
                continue
            # m = c_list_tuple.match(line)
            # if not m:
            m = c_list.match(line)
            if not m:
                m = c.match(line)
            if m:
                profile, instance, name, var, default = m.groups()
                if profile == 'profile':
                    name = 'profile<N>.' + name
                var = var.lstrip('% ')
                if instance.lower() == 'list':
                    type_key = [x.strip('"\'') for x in re.findall(r'["\'].*?["\']', var)]
                    commentline_split = commentline.split('::')
                    for i, tk in enumerate(type_key):
                        t, k = tk.split(':', maxsplit = 1)
                        process_line(d, key, profile, 'int', '%s.size' %name, var, '\-1', 'Quantity of %s.<I> entries.' %name, values, force_var, force_default, replace_default, counter)
                        key = '%s.%s' %(name, k)
                        key = key.lower()
                        process_line(d, key, profile, t, '%s.<I>.%s' %(name, k), var, '', commentline_split[i], values, force_var, force_default, replace_default, counter)
                else:
                    key = re.sub(r'%[\S]', var, name).lower()
                process_line(d, key, profile, instance, name, var, default, commentline, values, force_var, force_default, replace_default, counter)

                values = force_var = force_default = instance = name = var = default = None
                commentline = ''

    with open(MAN, 'w') as f:
        f.write(HEADER)
        if SORT:
            s = lambda x: x
        else:
            s = lambda x: d[x][LINE]
        f.write('\n'.join(output(**d[key]) for key in sorted(d, key = s)))
        f.write(FOOTER)

if __name__ == '__main__':
    main()
