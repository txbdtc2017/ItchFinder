import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]


class WakeRefreshTemplateTests(unittest.TestCase):
    def _render_base(self) -> str:
        env = Environment(
            loader=FileSystemLoader(str(ROOT / "templates")),
            autoescape=select_autoescape(["html", "xml"]),
        )
        env.filters["abs_time"] = lambda value: "05-06 12:00"
        env.globals["recent_refreshes"] = lambda: []
        env.globals["parse_json"] = lambda value: {}
        template = env.get_template("base.html")
        return template.render()

    def test_base_template_refreshes_after_wake_or_long_hidden_period(self):
        html = self._render_base()

        self.assertIn("WAKE_RELOAD_AFTER_MS", html)
        self.assertIn("WAKE_CHECK_INTERVAL_MS", html)
        self.assertIn("function reloadAfterWake()", html)
        self.assertIn("document.addEventListener('visibilitychange'", html)
        self.assertIn("window.addEventListener('focus'", html)
        self.assertIn("window.addEventListener('pageshow'", html)
        self.assertIn("setInterval(reloadAfterWake, WAKE_CHECK_INTERVAL_MS)", html)
        self.assertIn("location.reload()", html)
        self.assertIn("window.__itchfinderRefreshing", html)


if __name__ == "__main__":
    unittest.main()
