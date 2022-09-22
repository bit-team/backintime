import sys
import pathlib
import unittest
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut

# This workaround will become obsolet when migrating to src-layout
sys.path.append(str(pathlib.Path(__file__).parent))
import diagnostics  # testing target
import config


class Diagnostics(unittest.TestCase):
    """
    """

    def setUp(self):
        config.Config()

    def tearDown(self):
        config.Config._instance = None

    def test_minimal(self):
        """Minimal set of elements."""

        result = diagnostics.collect_diagnostics()

        # 1st level keys
        self.assertEqual(
            sorted(result.keys()),
            ['backintime', 'external-programs', 'host-setup', 'python-setup']
        )

        # 2nd level "backintime"
        minimal_keys = ['name', 'version', 'config-version',
                        'started-from', 'running_as_root']
        for key in minimal_keys:
            self.assertIn(key, result['backintime'], key)

        # 2nd level "host-setup"
        minimal_keys = ['platform', 'system', 'display-system',
                        'locale', 'PATH']
        for key in minimal_keys:
            self.assertIn(key, result['host-setup'], key)

        # 2nd level "python-setup"
        self.assertIn('python', result['python-setup'], 'python')

        # 2nd level "external-programs"
        minimal_keys = ['rsync', 'shell']
        for key in minimal_keys:
            self.assertIn(key, result['external-programs'], key)


    def test_no_ressource_warning(self):
        """No ResourceWarning's.

        Using subprocess.Popen() often cause ResourceWarning's when not used
        as a context manaager.
        """

        # an AssertionError must be raised! See next block for explanation.
        with self.assertRaises(AssertionError):

            # We expect NO ResourceWarnings. But Python doesn't offer
            # assertNoWarns().
            # This will raise an AssertionError bcause no ResourceWarning's
            # are raised.
            with self.assertWarns(ResourceWarning):

                diagnostics.collect_diagnostics()

    def test_no_extern_version(self):
        """Get version from not existing tool.
        """
        self.assertEqual(
            diagnostics._get_extern_versions(['fooXbar']),
            '(no fooXbar)'
        )


class Diagnostics_FakeFS(pyfakefs_ut.TestCase):
    """Tests using a fake filesystem.
    """

    def setUp(self):
        self.setUpPyfakefs(allow_root_user=False)

    def test_distro_package_folder(self):
        """Determin the folder of the project.
        """

        # real path
        path = pathlib.Path(diagnostics.__file__)

        # replicate that path in the fake fileystem
        path.mkdir(parents=True)
        path.touch()

        result = diagnostics._determine_distro_package_folder()

        self.assertEqual(result, path.parent.parent)

    def test_git_repo_info(self):
        """
        """

        # not a git repo
        self.assertEqual(diagnostics.get_git_repository_info(), None)

        # simulate a git repo
        path = pathlib.Path('.git')
        path.mkdir()

        # Branch folders and hash containing file
        foobar = path / 'refs' / 'heads' / 'fix' / 'foobar'
        foobar.parent.mkdir(parents=True)

        with foobar.open('w') as handle:
            handle.write('01234')

        # HEAD file
        head = path / 'HEAD'

        with head.open('w') as handle:
            handle.write('ref: refs/heads/fix/foobar')

        # Test
        self.assertEqual(
            diagnostics.get_git_repository_info(),
            {
                'hash': '01234',
                'branch': 'fix/foobar'
            }
        )
