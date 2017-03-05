#    Back In Time
#    Copyright (C) 2008-2017 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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


import os

import logger
from applicationinstance import ApplicationInstance

class GUIApplicationInstance(ApplicationInstance):
    '''class used to handle one application instance mechanism
    '''
    def __init__( self, base_control_file, raise_cmd = '' ):
        '''specify the base for control files
        '''
        self.raise_file = base_control_file + '.raise'
        self.raise_cmd = raise_cmd

        super(GUIApplicationInstance, self).__init__(base_control_file + '.pid', False, False)

        #remove raise_file is already exists
        if os.path.exists(self.raise_file):
            os.remove( self.raise_file )

        self.check(raise_cmd)
        self.start_application()

    def check(self, raise_cmd):
        '''check if the current application is already running
        '''
        ret = super(GUIApplicationInstance, self).check(False)
        if not ret:
            print("The application is already running! (pid: %s)" % self.pid)
            #notify raise
            try:
                with open( self.raise_file, 'wt' ) as f:
                    f.write(raise_cmd)
            except OSError as e:
                logger.error('Failed to write raise file %s: [%s] %s' %(e.filename, e.errno, e.strerror))

            exit(0) #exit raise an exception so don't put it in a try/except block
        else:
            return ret

    def raise_command( self ):
        '''check if the application must to be raised
           return None if no raise needed, or a string command to raise
        '''
        ret_val = None

        try:
            if os.path.isfile( self.raise_file ):
                with open( self.raise_file, 'rt' ) as f:
                    ret_val = f.read()
                os.remove( self.raise_file )
        except:
            pass

        return ret_val
