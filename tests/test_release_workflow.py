import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release-windows.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    def test_tagged_release_workflow_tests_builds_and_uploads_the_windows_setup(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('tags:\n      - "v*"', content)
        self.assertIn("installers\\build-windows-release.ps1", content)
        self.assertIn("py -3 -m unittest discover -s tests -v", content)
        self.assertIn("gh release create", content)
        self.assertIn("ExcaliFlow-Setup-windows.zip .\\dist\\update.json --clobber", content)
        self.assertIn("Release tag does not match VERSION", content)
        self.assertIn("signed-exe:", content)
        self.assertIn("WINDOWS_SIGNING_PFX_BASE64", content)
        self.assertIn("build-windows-exe.ps1", content)
        self.assertIn("ExcaliFlow-Setup-windows.exe --clobber", content)
        self.assertIn("contents: write", content)
