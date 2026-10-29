"""Tests of render_readme.py's leftover detector (standard library only; no renderer needed)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_readme  # noqa: E402


class LeftoversTest(unittest.TestCase):

    def test_rendered_markdown_has_no_leftovers(self):
        self.assertEqual(render_readme.leftovers('<p><strong>Bold</strong> and <a href="a.md">a link</a></p>'), [])

    def test_unrendered_bold_and_links_are_found(self):
        found = render_readme.leftovers('<details><summary>More</summary>**Bold** and [a](a.md)</details>')
        self.assertEqual(len(found), 2)

    def test_an_unrendered_alert_is_found_in_githubs_rendering_only(self):
        quote = '<blockquote><p>[!WARNING]\nRead this</p></blockquote>'
        self.assertTrue(render_readme.leftovers(quote, alerts=True))
        self.assertEqual(render_readme.leftovers(quote), [])

    def test_code_is_not_inspected(self):
        self.assertEqual(render_readme.leftovers('<pre><code>**not bold** [a](b)</code></pre>'), [])


if __name__ == '__main__':
    unittest.main()
