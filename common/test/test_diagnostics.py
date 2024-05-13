"""Test related to diagnostics.py"""
import sys
import pathlib
import unittest

# This workaround will become obsolet when migrating to src-layout
sys.path.append(str(pathlib.Path(__file__).parent))
import diagnostics  # testing target


class Diagnostics(unittest.TestCase):
    """Test about collecting diagnostic infos."""

    def test_content_minimal(self):
        """Minimal set of elements."""

        sut = diagnostics.collect_minimal_diagnostics()

        # 1st level keys
        self.assertCountEqual(sut.keys(), ['backintime', 'host-setup'])

        # 2nd level "backintime"
        self.assertCountEqual(
            sut['backintime'].keys(),
            ['name', 'version', 'running-as-root'])

        # 2nd level "host-setup"
        self.assertCountEqual(sut['host-setup'].keys(), ['OS'])

    def test_some_content(self):
        """Some contained elements"""
        result = diagnostics.collect_diagnostics()

        # 1st level keys
        self.assertCountEqual(
            result.keys(),
            ['backintime', 'external-programs', 'host-setup', 'python-setup']
        )

        # 2nd level "backintime"
        minimal_keys = ['name', 'version', 'latest-config-version',
                        'started-from', 'running-as-root']
        for key in minimal_keys:
            self.assertIn(key, result['backintime'], key)

        # 2nd level "host-setup"
        minimal_keys = ['platform', 'system', 'display-system', 'locale',
                        'PATH', 'RSYNC_OLD_ARGS', 'RSYNC_PROTECT_ARGS']
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
            # This will raise an AssertionError because no ResourceWarning's
            # are raised.
            with self.assertWarns(ResourceWarning):

                diagnostics.collect_diagnostics()

    def test_no_extern_version(self):
        """Get version from not existing tool."""
        self.assertEqual(
            diagnostics._get_extern_versions(['fooXbar']),
            '(no fooXbar)'
        )

    def test_replace_user_path(self):
        """Replace users path."""
        d = {
            'foo': '/home/rsync',
            'bar': '~/rsync'
        }

        self.assertEqual(
            diagnostics._replace_username_paths(d, 'rsync'),
            {
                'foo': '/home/UsernameReplaced',
                'bar': '~/UsernameReplaced'
            }
        )

        self.assertEqual(
            diagnostics._replace_username_paths(d, 'user'),
            d
        )
