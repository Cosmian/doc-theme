import contextlib
import importlib.util
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name('generate-summary.py')
SPEC = importlib.util.spec_from_file_location('generate_summary', SCRIPT)
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


class StrictNavigationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.product_nav = self.root / 'product/documentation/nav.yml'
        files = {
            'docs/index.md': '# Home\n',
            'docs/product/guide.md': '# Guide\n',
            'nav.yml': 'nav:\n  - Home: index.md\n',
            'product/documentation/nav.yml': 'nav:\n  - Guide: guide.md\n',
        }
        for relative, content in files.items():
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content)
        patched = mock.patch.multiple(
            generator, ROOT=self.root,
            SECTIONS=[('Home', '', '.'), ('Product', 'product', 'product/documentation')],
            _ARTIFACTS=[])
        patched.start()
        self.addCleanup(patched.stop)

    def build(self, strict_nav=False):
        with contextlib.redirect_stdout(io.StringIO()):
            generator.build_combined(strict_nav=strict_nav)
        return (self.root / 'src/SUMMARY.md').read_text()

    def test_valid_navigation_is_unchanged(self):
        self.assertEqual(self.build(), self.build(strict_nav=True))

    def test_missing_nested_target_fails(self):
        self.product_nav.write_text('nav:\n  - Group:\n    - Missing: missing.md\n')
        with self.assertRaisesRegex(FileNotFoundError, 'product/missing.md'):
            self.build(strict_nav=True)

    def test_missing_root_target_fails(self):
        (self.root / 'docs/index.md').unlink()
        with self.assertRaisesRegex(FileNotFoundError, 'index.md'):
            self.build(strict_nav=True)

    def test_default_mode_warns_and_skips_missing_target(self):
        self.product_nav.write_text('nav:\n  - Missing: missing.md\n')
        warning = io.StringIO()
        with contextlib.redirect_stderr(warning):
            summary = self.build()
        self.assertIn('nav targets missing (skipped)', warning.getvalue())
        self.assertNotIn('missing.md', summary)

    def test_missing_nav_source_fails(self):
        shutil.rmtree(self.product_nav.parent)
        with self.assertRaisesRegex(FileNotFoundError, 'product/documentation'):
            self.build(strict_nav=True)

    def test_missing_nav_file_fails(self):
        self.product_nav.unlink()
        with self.assertRaises(FileNotFoundError):
            self.build(strict_nav=True)

    def test_empty_navigation_fails(self):
        self.product_nav.write_text('nav:\n')
        with self.assertRaisesRegex(ValueError, 'Empty navigation for product/'):
            self.build(strict_nav=True)

    def test_default_mode_still_skips_missing_section(self):
        self.product_nav.unlink()
        with contextlib.redirect_stderr(io.StringIO()):
            summary = self.build()
        self.assertNotIn('[Product]', summary)

    def test_standalone_default_remains_compatible(self):
        (self.root / 'nav.yml').write_text('nav:\n  - Missing: missing.md\n')
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            generator.build_standalone(self.root)
        self.assertTrue((self.root / 'src/SUMMARY.md').exists())
        with self.assertRaisesRegex(FileNotFoundError, 'missing.md'):
            with contextlib.redirect_stdout(io.StringIO()):
                generator.build_standalone(self.root, strict_nav=True)

    def test_cli_enables_strict_navigation(self):
        self.product_nav.write_text('nav:\n')
        with mock.patch.object(sys, 'argv', [str(SCRIPT), '--combined', '--strict-nav']):
            with self.assertRaisesRegex(ValueError, 'Empty navigation'):
                with contextlib.redirect_stdout(io.StringIO()):
                    generator.main()


if __name__ == '__main__':
    unittest.main()