#! /usr/bin/python

import os
import sys
import tempfile
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common/'))

import configfile


class TestConfigFile(unittest.TestCase):
    '''Tests for the ConfigFile class in the configfile module'''
    def test_save(self):
        '''Saves the config file  in the tmp direcory '''
        filename = os.path.join(tempfile.gettempdir(), "test_save.cfg")
        print(filename)
        cf = configfile.ConfigFile()
        cf.save(filename)
        self.assertTrue(os.path.exists(filename))
        os.remove(filename)

    def test_save_None(self):
        '''
        The exception should be suppresed by the save function and no
        file should named None should be created
         '''
        filename = None
        cf = configfile.ConfigFile()
        try:
            cf.save(filename)
        except:
            self.fail(
                "The exception should have been suppressed by the " +
                "save function")
            return
        self.assertTrue(True)

    def test_load(self):
        '''
        ConfigFile should be able to load its content from a previously
        saved ConfigFile object.
        '''
        config_filename = os.path.join(
            tempfile.gettempdir(),
            "test_load.cfg")
        original_cf = configfile.ConfigFile()
        key = "config_key"
        value = "config_value"
        original_cf.set_str_value(key, value)
        original_cf.save(config_filename)

        cf = configfile.ConfigFile()
        cf.load(config_filename)

        self.assertEqual(len(cf.get_keys()), len(original_cf.get_keys()))
        for k in original_cf.get_keys():
            self.assertTrue(cf.has_value(k))

        os.remove(config_filename)

    def test_load_None(self):
        '''
        The load function should suppress the error if it is fed None as
        the filename.
        '''
        config_filename = None
        cf = configfile.ConfigFile()
        try:
            cf.load(config_filename)
        except:
            self.fail(
                "The exception should have been suppressed by the " +
                "load function")
        self.assertEqual(len(cf.get_keys()), 0)
