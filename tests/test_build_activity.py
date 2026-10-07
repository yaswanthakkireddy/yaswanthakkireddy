"""Offline behavioral checks for the telemetry refresh. No network or packages."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from scripts import build_activity as activity


def snapshot():
    result = []
    for index, (repo, *_rest) in enumerate(activity.PROJECTS):
        head = f"{index + 1:040x}"
        configured = repo not in {"NeuroShield", "TOSCO"}
        result.append({
            "repo": repo,
            "head": head,
            "committed_at": "2026-10-06T20:51:12Z",
            "workflow": {"id": index + 1, "path": activity.CI_PATHS.get(repo, activity.CI_PATH), "state": "active"} if configured else None,
            "run": {"id": 100 + index, "head_sha": head, "head_branch": "main",
                    "status": "completed", "conclusion": "success"} if configured and repo != "cortexagent" else None,
        })
    return result


class TelemetryTests(unittest.TestCase):
    def test_api_dates_and_successful_reruns_do_not_change_output(self):
        first = snapshot()
        later = deepcopy(first)
        for row in later:
            row["fetched_at"] = "2035-01-01T00:00:00Z"
            row["pushed_at"] = "2035-01-01T00:00:00Z"
            if row["run"]:
                row["run"].update(id=999999, run_attempt=4,
                                  created_at="2035-01-01T00:00:00Z",
                                  updated_at="2035-01-02T00:00:00Z")
        for renderer in (activity.render, activity.render_mobile):
            self.assertEqual(renderer(first), renderer(later))
            self.assertNotIn("2035", renderer(later))

    def test_head_advance_does_not_reuse_old_success(self):
        rows = snapshot()
        before = activity.render(rows)
        rows[1]["head"] = "a" * 40
        self.assertEqual(activity.ci_status(rows[1])[0], "No run for this HEAD")
        self.assertNotEqual(before, activity.render(rows))

    def test_source_commit_date_changes_output_and_normalizes_to_utc(self):
        rows = snapshot()
        before = activity.render(rows)
        rows[0]["committed_at"] = "2026-10-08T02:00:00+05:30"
        self.assertEqual(activity.commit_date(rows[0]), "2026-10-07")
        self.assertNotEqual(before, activity.render(rows))
        rows[0]["committed_at"] = "2026-10-07"
        with self.assertRaises(ValueError):
            activity.render(rows)

    def test_non_main_run_cannot_be_presented_as_main_success(self):
        row = snapshot()[1]
        row["run"]["head_branch"] = "feature"
        self.assertEqual(activity.ci_status(row)[0], "No run for this HEAD")

    def test_meaningful_ci_outcome_changes_output(self):
        rows = snapshot()
        passing = activity.render(rows)
        rows[1]["run"]["conclusion"] = "failure"
        self.assertEqual(activity.ci_status(rows[1])[0], "Needs attention")
        self.assertNotEqual(passing, activity.render(rows))
        rows[1]["run"].update(status="in_progress", conclusion=None)
        self.assertEqual(activity.ci_status(rows[1])[0], "Pending on main")

    def test_missing_and_disabled_workflows_are_explicit(self):
        rows = snapshot()
        self.assertEqual(activity.ci_status(rows[2])[0], "No tracked CI workflow")
        rows[1]["workflow"]["state"] = "disabled_manually"
        self.assertEqual(activity.ci_status(rows[1])[0], "CI disabled")
        rows[1]["workflow"]["state"] = "active"
        rows[1]["run"] = None
        self.assertEqual(activity.ci_status(rows[1])[0], "No run for this HEAD")

    def test_svg_escapes_text_and_is_well_formed(self):
        projects = list(activity.PROJECTS)
        repo, _, tier, _ = projects[0]
        projects[0] = (repo, "<Cortex & Agent>", tier, ("A < B & C > D", "Scoped evidence"))
        with patch.object(activity, "PROJECTS", tuple(projects)):
            svg = activity.render(snapshot())
        ElementTree.fromstring(svg)
        self.assertIn("&lt;Cortex &amp; Agent&gt;", svg)
        self.assertIn("A &lt; B &amp; C &gt; D", svg)


    def test_mobile_preserves_evidence_and_ci_scope(self):
        rows = snapshot()
        svg = activity.render_mobile(rows)
        ElementTree.fromstring(svg)
        self.assertIn("20/20 single-LLM baseline", svg)
        self.assertIn("No tracked CI workflow", svg)
        self.assertIn("2026-10-06 UTC", svg)
        rows[1]["head"] = "a" * 40
        self.assertIn("No run for this HEAD", activity.render_mobile(rows))
        self.assertNotEqual(svg, activity.render_mobile(rows))

    def test_all_project_rows_fit_inside_both_svg_canvases(self):
        rows = snapshot()
        for renderer in (activity.render, activity.render_mobile):
            root = ElementTree.fromstring(renderer(rows))
            height = float(root.attrib["height"])
            for text in root.iter("{http://www.w3.org/2000/svg}text"):
                self.assertLess(float(text.attrib["y"]), height)
            self.assertIn("TOSCO", renderer(rows))
        self.assertIn("mock-bank prototype", activity.render(rows))

    def test_api_failure_preserves_last_good_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "activity.svg"
            output.write_text("last good asset", encoding="utf-8")
            with patch.object(activity, "_get", side_effect=OSError("rate limited")):
                with self.assertRaises(OSError):
                    activity.main(["--output", str(output)])
            self.assertEqual(output.read_text(encoding="utf-8"), "last good asset")

    def test_invalid_partial_snapshot_preserves_last_good_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "activity.svg"
            output.write_text("last good asset", encoding="utf-8")
            with patch.object(activity, "fetch", return_value=snapshot()[:-1]):
                with self.assertRaises(ValueError):
                    activity.main(["--output", str(output)])
            self.assertEqual(output.read_text(encoding="utf-8"), "last good asset")

    def test_identical_content_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "activity.svg"
            svg = activity.render(snapshot())
            self.assertTrue(activity.write_if_changed(output, svg))
            with patch.object(activity.os, "replace") as replace:
                self.assertFalse(activity.write_if_changed(output, svg))
                replace.assert_not_called()
            self.assertEqual(output.read_bytes(), svg.encode("utf-8"))

    def test_fetch_uses_latest_main_run_and_excludes_profile_repository(self):
        requested = []
        def fake_get(url):
            requested.append(url)
            if "/branches/main" in url:
                return {"commit": {"sha": "a" * 40, "commit": {
                    "committer": {"date": "2026-10-06T20:51:12Z"}}}}
            if "/actions/workflows?" in url:
                return {"total_count": 1, "workflows": [
                    {"id": 123, "path": activity.CI_PATHS.get(url.split("/")[5], activity.CI_PATH), "state": "active"}]}
            if "/actions/workflows/123/runs?" in url:
                return {"total_count": 1, "workflow_runs": [
                    {"id": 50, "head_sha": "a" * 40, "head_branch": "main",
                     "status": "completed", "conclusion": "success"}]}
            self.fail("Unexpected API request: " + url)
        with patch.object(activity, "_get", side_effect=fake_get):
            rows = activity.fetch()
        self.assertEqual(len(rows), 7)
        self.assertTrue(all("yaswanthakkireddy/yaswanthakkireddy/" not in u for u in requested))
        run_urls = [u for u in requested if "/runs?" in u]
        self.assertTrue(all("branch=main" in u and "per_page=1" in u for u in run_urls))
        self.assertTrue(all(activity.ci_status(row)[0] == "Passing on main" for row in rows))


if __name__ == "__main__":
    unittest.main()
