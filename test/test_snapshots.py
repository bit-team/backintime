import os
import sys
import tempfile
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common/'))

import configfile
import snapshots


class TestSnapShots(unittest.TestCase):

    def test_valid_config(self):
        '''
        Test if the config file use by the snapshots is correctly
        initialized if the function is fed a valid ConfigFile object.
        '''
        cf = configfile.ConfigFile()
        sp = snapshots.Snapshots(cf)
        self.assertEqual(sp.config, cf)

    def test_None_as_config(self):
        '''
        Test if the config file use by the snapshots is correctly
        initialized if the function is fed None as the ConfigFile.
        '''
        sp = snapshots.Snapshots(None)
        self.assertNotEqual(sp.config, None)
