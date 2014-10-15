import unittest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common/'))
import tools
import config
import configfile

##################################################
#             How run that test ?                #
#------------------------------------------------#
# use py.test-3 (sudo apt-get install py.test-3) #
#       py.test-3 -v test_tools.py               #
##################################################

################################################################
#                         Output                               #
#--------------------------------------------------------------#
# If something is red so something going wrong with BackInTime #
#         Otherwise all it's good ! you can commit !           #
################################################################

''' All funtions test here come from tools.py '''
class TestTools(unittest.TestCase):

    def test_read_file(self):
        ''' Test the function read_file '''
        self.assertNotEquals(tools.read_file("./test_tools.py"), None);
        self.assertEquals(tools.read_file("./notExistedFile"), None);

    def test_read_file_lines(self):
        ''' Test the function read_file_lines '''
        self.assertNotEquals(tools.read_file("./test_tools.py"), None);
        self.assertEquals(tools.read_file("./notExistedFile"), None);

    def test_read_command_output(self):
        ''' Test the function read_command_output '''
        self.assertEquals("Test, read command output", tools.read_command_output("echo 'Test, read command output'"));

    def test_check_command(self):
        ''' Test the function check_command '''
        self.assertFalse(tools.check_command("notExistedCommand"))
        self.assertTrue(tools.check_command("ls"))

    def test_which(self):
        ''' Test the function which '''
        assert tools.which("ls") is not None
        assert tools.which("notExistedCommand") is None

    def test_process_exists(self):
        ''' Test the function process_exists '''
        self.assertTrue(tools.process_exists("init"));
        self.assertFalse(tools.process_exists("notExistedProcess"));

    def test_load_env(self):
        ''' Test the function load_env '''
        dict = {}
        lines = []
        path_user = os.path.expanduser('~')
        path_cron_env = os.path.join(path_user, ".local/share/backintime/cron_env")
        try:
            with open( path_cron_env, 'rt' ) as file:
                lines = file.readlines()
        except :
            pass
        for line in lines:
            items = line.split( '=', 1)
            if len( items ) == 2:
                dict[ items[ 0 ] ] = items[ 1 ][ : -1 ]
        cfg = config.Config(None);
        tools.load_env(cfg)
        for key in dict.keys():
            self.assertEquals(os.environ[key], dict[key])

    def test_prepare_path(self):
        ''' Test the function load_env '''
        path_with_slash = "/test/path";
        path_without_slash = "test/path";
        self.assertEquals(tools.prepare_path(path_with_slash), path_with_slash);
        self.assertEquals(tools.prepare_path(path_without_slash), path_with_slash);
    
    def test_is_process_alive(self):
        ''' Test the function is_process_alive '''
        self.assertTrue(tools.is_process_alive(0))
        self.assertFalse(tools.is_process_alive(99999999999))
