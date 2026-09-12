"""Offline regression checks for the scheduled citation updater."""

import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch

import update_citations as updater


PAGE = '''<ul>
    <li>
        <a href="/uncited" class="publication-title">Uncited systems paper</a>
        <span class="publication-authors">An Author</span>
    </li>
    <li>
        <a class="publication-title" href="/paper">Reasoning &amp; Learning</a>
        <span class="publication-authors">Another Author</span>
        <span class="publication-citations">100+ citations</span>
    </li>
</ul>'''


class CitationMatchingTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(redirect_stdout(StringIO()))

    def test_updates_only_the_matching_papers_count(self):
        updated = updater.update_citations(
            PAGE,
            {"Uncited systems paper": 9000, "Reasoning & Learning": 254},
        )
        self.assertEqual(updated, PAGE.replace("100+ citations", "250+ citations"))

    def test_preserves_unmatched_papers(self):
        updated = updater.update_citations(PAGE, {"Astronomical observations": 9000})
        self.assertEqual(updated, PAGE)

    def test_preserves_higher_existing_counts(self):
        updated = updater.update_citations(PAGE, {"Reasoning & Learning": 73})
        self.assertEqual(updated, PAGE)

    def test_preserves_counts_within_the_same_display_bucket(self):
        updated = updater.update_citations(PAGE, {"Reasoning & Learning": 105})
        self.assertEqual(updated, PAGE)

    def test_retains_existing_rounding_policy(self):
        cases = [(7, 7), (73, 70), (948, 950), (990, 1000), (4919, 4900), (10100, 10000)]
        for count, displayed in cases:
            with self.subTest(count=count):
                self.assertEqual(updater.round_citations(count), displayed)


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.page = Mock()
        self.page.read_text.return_value = PAGE
        self.proxy = Mock()
        self.fetch = Mock(return_value={"Reasoning & Learning": 254})
        for name, replacement in [
            ("HTML_FILE", self.page),
            ("setup_proxy", self.proxy),
            ("fetch_scholar_citations", self.fetch),
        ]:
            self.enterContext(patch.object(updater, name, replacement))
        self.enterContext(redirect_stdout(StringIO()))

    def test_writes_successful_updates_as_utf8(self):
        self.assertEqual(updater.main(), 0)
        self.page.write_text.assert_called_once_with(
            PAGE.replace("100+ citations", "250+ citations"), encoding="utf-8"
        )

    def test_does_not_write_when_nothing_changed(self):
        self.fetch.return_value = {"Reasoning & Learning": 100}
        self.assertEqual(updater.main(), 0)
        self.page.write_text.assert_not_called()

    def test_fetch_failure_returns_failure_without_writing(self):
        self.fetch.side_effect = RuntimeError("Scholar unavailable")
        self.assertEqual(updater.main(), 1)
        self.page.write_text.assert_not_called()

    def test_empty_response_returns_failure_without_writing(self):
        self.fetch.return_value = {}
        self.assertEqual(updater.main(), 1)
        self.page.write_text.assert_not_called()

    def test_proxy_failure_returns_failure_without_fetching_or_writing(self):
        self.proxy.side_effect = RuntimeError("Proxy unavailable")
        self.assertEqual(updater.main(), 1)
        self.fetch.assert_not_called()
        self.page.write_text.assert_not_called()


if __name__ == "__main__":
    unittest.main()
