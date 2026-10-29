"""Tests of check_readme.py: each check passes on a clean README and fails when broken once.

Standard library only:

    <python> -m unittest discover -s <this skill>/scripts -p 'test_*.py'
    <python with pytest> -m pytest <this skill>/scripts                # also works
"""

import io
import os
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_readme  # noqa: E402

ALT = 'A bar chart of the estimated cycle time per variant with the total above each bar'

CLEAN = textwrap.dedent('''\
    # Project

    One sentence on what it does and for whom.

    ![License: MIT](https://img.shields.io/badge/license-MIT-green)

    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="Media/a_dark.png">
      <img src="Media/a_light.png" alt="{alt}" width="80%">
    </picture>

    **Figure 1:** What it shows.

    > [!WARNING]
    > Read this first.

    ## Contents

    [About](#about) · [Usage](#usage-and-more)

    ## About

    See [the docs](docs/guide.md#install) and [usage](#usage-and-more).

    | Variant | Time [s] |
    |---|---:|
    | a | 1.50 |

    ## Usage and more

    ```bash
    ./run.sh
    ```

    <details>
    <summary>More</summary>

    ### Hidden

    ![{alt}](Media/b.png)

    **Figure 2:** The second figure.

    </details>
    ''').format(alt=ALT)


class CheckReadmeTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        for name in ('Media/a_dark.png', 'Media/a_light.png', 'Media/b.png'):
            self.write(name, 'png')
        self.write('docs/guide.md', '# Guide\n\n## Install\n')
        self.write('LICENSE', 'MIT License\n\nCopyright (c) 2026\n')

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = os.path.join(self.root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        return path

    def check(self, text=CLEAN, **options):
        findings, facts = check_readme.run(self.write('README.md', text), **options)
        return findings, facts

    def errors(self, text, check=None):
        findings, _ = self.check(text)
        return [f for f in findings if f.level == 'ERROR' and (check is None or f.check == check)]

    def warnings(self, text, check):
        findings, _ = self.check(text)
        return [f for f in findings if f.level == 'WARN' and f.check == check]

    # -- the project's exceptions (check_readme.json)

    def test_a_listed_brand_mark_needs_no_caption_and_others_still_do(self):
        text = CLEAN.replace('<picture>', ('<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="Media/logo_dark.png">\n'
                                                '  <img src="Media/logo.png" alt="{alt}" height="40">\n</picture>\n\n<picture>').format(alt=ALT), 1)
        self.write('Media/logo.png', 'png')
        self.write('Media/logo_dark.png', 'png')
        self.assertEqual(len(self.errors(text, 'caption')), 1)
        self.write(check_readme.CONFIG_RELATIVE, '{"uncaptioned_figures": [{"src": "Media/logo.png", "reason": "the header brand mark"}]}')
        findings, _ = self.check(text)
        self.assertEqual([f for f in findings if f.level == 'ERROR'], [])
        self.assertEqual([f.message for f in findings if f.check == 'caption'],
                         ['no caption needed (check_readme.json): the header brand mark'])
        self.write(check_readme.CONFIG_RELATIVE, '{"uncaptioned_figures": [{"src": "Media/other.png", "reason": "x"}]}')
        self.assertEqual(len(self.errors(text, 'caption')), 1)
        self.write(check_readme.CONFIG_RELATIVE, '{"uncaptioned_figures": [{"src": "Media/logo.png"}]}')
        self.assertEqual(len(self.errors(text, 'config')), 1)

    # -- the clean README

    def test_the_clean_readme_has_no_errors_or_warnings(self):
        findings, facts = self.check()
        self.assertEqual([f for f in findings if f.level != 'INFO'], [])
        self.assertEqual(facts['figures visible'], 1)
        self.assertEqual(facts['figures collapsed'], 1)

    def test_the_visible_line_count_excludes_details(self):
        _, facts = self.check()
        details = CLEAN.split('\n').index('<details>')
        self.assertEqual(facts['visible lines'], details + 1)

    def test_a_long_visible_part_is_a_warning(self):
        findings, _ = self.check(max_visible=10)
        self.assertTrue([f for f in findings if f.check == 'length'])

    # -- links and anchors

    def test_a_missing_file_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('docs/guide.md', 'docs/missing.md'), 'links'))

    def test_an_anchor_without_a_heading_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('(#about)', '(#abuot)'), 'anchors'))

    def test_an_anchor_in_another_markdown_file_is_checked(self):
        self.assertTrue(self.errors(CLEAN.replace('guide.md#install', 'guide.md#setup'), 'anchors'))

    def test_a_duplicate_heading_gets_githubs_suffix(self):
        text = CLEAN + '\n## About\n\n[second](#about-1)\n'
        self.assertEqual(self.errors(text, 'anchors'), [])
        self.assertTrue(self.errors(text.replace('#about-1', '#about-2'), 'anchors'))

    def test_a_root_absolute_link_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('(docs/guide.md#install)', '(/docs/guide.md)'), 'links'))

    def test_a_link_inside_inline_code_is_not_checked(self):
        self.assertEqual(self.errors(CLEAN + '\n`[x](missing.md)`\n', 'links'), [])

    def test_a_missing_html_image_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('Media/a_light.png', 'Media/gone.png'), 'links'))

    # -- pictures, alt text, captions

    def test_a_picture_without_a_dark_source_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('(prefers-color-scheme: dark)', '(min-width: 1px)'), 'picture'))

    def test_a_picture_without_width_is_a_warning(self):
        self.assertTrue(self.warnings(CLEAN.replace(' width="80%"', ''), 'picture'))

    def test_a_short_alt_text_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('alt="%s"' % ALT, 'alt="the chart"'), 'alt-text'))

    def test_a_figure_without_a_caption_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('**Figure 1:** What it shows.', 'What it shows.'), 'caption'))

    def test_captions_out_of_order_are_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('**Figure 2:**', '**Figure 3:**'), 'caption'))

    def test_an_html_caption_counts(self):
        text = CLEAN.replace('**Figure 1:** What it shows.', '<p><b>Figure 1:</b> What it shows.</p>')
        self.assertEqual(self.errors(text, 'caption'), [])

    def test_a_badge_needs_no_caption(self):
        self.assertEqual(self.errors(CLEAN, 'caption'), [])

    # -- fences, details, alerts

    def test_a_fence_without_a_language_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('```bash', '```'), 'fences'))

    def test_a_prompt_in_a_shell_block_is_a_warning(self):
        self.assertTrue(self.warnings(CLEAN.replace('./run.sh', '$ ./run.sh'), 'fences'))

    def test_markdown_right_after_summary_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('<summary>More</summary>\n\n', '<summary>More</summary>\n'), 'details'))

    def test_an_unclosed_details_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('</details>', ''), 'details'))

    def test_an_unknown_alert_type_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('[!WARNING]', '[!DANGER]'), 'alerts'))

    def test_text_on_the_alert_line_is_an_error(self):
        self.assertTrue(self.errors(CLEAN.replace('[!WARNING]\n> Read', '[!WARNING] Read'), 'alerts'))

    # -- contents

    def test_a_visible_section_missing_from_contents_is_a_warning(self):
        self.assertTrue(self.warnings(CLEAN.replace(' · [Usage](#usage-and-more)', ''), 'contents'))

    def test_contents_listing_a_collapsed_heading_is_a_warning(self):
        self.assertTrue(self.warnings(CLEAN.replace('(#usage-and-more)', '(#usage-and-more) · [Hidden](#hidden)'), 'contents'))

    # -- badges

    def test_a_licence_badge_must_match_the_licence(self):
        self.assertTrue(self.errors(CLEAN.replace('license-MIT-green', 'license-Apache%202.0-blue').replace('License: MIT', 'License'), 'badges'))

    def test_a_licence_badge_needs_a_licence_file(self):
        os.remove(os.path.join(self.root, 'LICENSE'))
        self.assertTrue(self.errors(CLEAN, 'badges'))

    def test_a_ci_badge_needs_its_workflow(self):
        badge = '![CI](https://github.com/o/r/actions/workflows/ci.yml/badge.svg)\n'
        text = CLEAN.replace('\n\n<picture>', '\n' + badge + '\n<picture>', 1)
        self.assertTrue(self.errors(text, 'badges'))
        self.write('.github/workflows/ci.yml', 'on: push\n')
        self.assertEqual(self.errors(text, 'badges'), [])

    # -- leaks and wording

    def test_an_absolute_local_path_is_an_error_even_in_code(self):
        self.assertTrue(self.errors(CLEAN.replace('./run.sh', '/Users/me/project/run.sh'), 'local-paths'))

    def test_a_machine_specific_temporary_path_is_an_error(self):
        for path in ('/private/tmp/claude-501/x/out.csv', '/var/folders/ab/xyz/T/out.csv'):
            self.assertTrue(self.errors(CLEAN.replace('./run.sh', path), 'local-paths'), path)

    def test_a_bare_tmp_path_is_a_warning_not_an_error(self):
        text = CLEAN.replace('./run.sh', './run.sh --out /tmp/demo')
        self.assertTrue(self.warnings(text, 'local-paths'))
        self.assertEqual(self.errors(text, 'local-paths'), [])

    def test_a_secret_is_an_error(self):
        self.assertTrue(self.errors(CLEAN + '\ntoken ghp_' + 'a' * 30 + '\n', 'secrets'))

    def test_an_ip_address_is_a_warning(self):
        self.assertTrue(self.warnings(CLEAN + '\nThe server is at 192.168.1.10.\n', 'hosts'))

    def test_filler_and_exclamation_are_warnings(self):
        self.assertEqual(len(self.warnings(CLEAN + '\nSimply run it!\n', 'wording')), 2)

    def test_a_semicolon_in_prose_is_an_error(self):
        broken = CLEAN.replace('One sentence on what it does and for whom.', 'It does one thing; it does it well.')
        self.assertEqual(len(self.errors(broken, 'semicolons')), 1)
        in_cell = CLEAN.replace('| a | 1.50 |', '| a; b | 1.50 |')
        self.assertEqual(len(self.errors(in_cell, 'semicolons')), 1)

    def test_a_semicolon_as_syntax_is_not_an_error(self):
        syntax = CLEAN.replace('./run.sh', './run.sh; ./run.sh --again').replace(
            'One sentence on what it does and for whom.',
            'Run `a; b`, see [it](https://example.org/a;b) or <https://example.org/c;d>, '
            '<img src="Media/b.png" width="120px;" alt="{alt}"> and&nbsp;more at https://example.org/e;f.'.format(alt=ALT))
        self.assertEqual(self.errors(syntax, 'semicolons'), [])

    # -- tables and image sizes

    def test_a_left_aligned_numeric_column_is_a_warning(self):
        self.assertTrue(self.warnings(CLEAN.replace('|---|---:|', '|---|---|'), 'tables'))

    def test_a_wide_visible_table_is_a_warning(self):
        wide = '\n| a | b | c | d | e | f | g |\n|---|---|---|---|---|---|---|\n| x | x | x | x | x | x | x |\n'
        self.assertTrue(self.warnings(CLEAN.replace('## Usage and more', wide + '\n## Usage and more'), 'tables'))

    def test_an_image_over_the_budget_is_a_warning(self):
        self.write('Media/b.png', 'x' * 3000)
        findings, _ = self.check(max_image_kb=2)
        self.assertTrue([f for f in findings if f.check == 'image-size'])

    # -- size budgets: defaults, check_readme.json, command line

    def _sizes(self, findings):
        return [(f.level, f.message) for f in findings if f.check == 'image-size']

    def test_without_budget_keys_the_default_budgets_apply_unchanged(self):
        self.write('Media/b.png', 'x' * (399 * 1024))
        findings, _ = self.check()
        self.assertEqual(self._sizes(findings), [])
        self.write('Media/b.png', 'x' * (401 * 1024))
        self.write(check_readme.CONFIG_RELATIVE, '{"uncaptioned_figures": []}')
        findings, _ = self.check()
        self.assertEqual(self._sizes(findings), [('WARN', 'Media/b.png is 401 KB (budget 400 KB)')])

    def test_a_file_budget_raises_the_limit_for_its_glob_only(self):
        self.write('Media/b.png', 'x' * (500 * 1024))
        self.write('Media/a_light.png', 'x' * (500 * 1024))
        self.write(check_readme.CONFIG_RELATIVE, '{"image_budgets": [{"glob": "Media/b.*", "max_kb": 600, '
                                                 '"reason": "an animated preview"}]}')
        findings, _ = self.check()
        self.assertEqual(self._sizes(findings), [
            ('WARN', 'Media/a_light.png is 500 KB (budget 400 KB)'),
            ('INFO', 'image budget 600 KB for Media/b.* (check_readme.json): an animated preview')])
        self.write('Media/b.png', 'x' * (601 * 1024))
        findings, _ = self.check()
        self.assertIn(('WARN', 'Media/b.png is 601 KB (budget 600 KB)'), self._sizes(findings))

    def test_a_file_media_budget_replaces_the_default_total(self):
        self.write('Media/b.png', 'x' * (7 * 1024 * 1024))
        self.write(check_readme.CONFIG_RELATIVE, '{"image_budgets": [{"glob": "Media/b.png", "max_kb": 8000, "reason": "r"}]}')
        findings, _ = self.check()
        self.assertIn(('WARN', 'images shown total 7.0 MB (budget 6.0 MB)'), self._sizes(findings))
        self.write(check_readme.CONFIG_RELATIVE, '{"image_budgets": [{"glob": "Media/b.png", "max_kb": 8000, "reason": "r"}], '
                                                 '"media_budget": {"max_mb": 8, "reason": "two previews"}}')
        findings, _ = self.check()
        messages = self._sizes(findings)
        self.assertFalse([m for m in messages if m[0] == 'WARN'])
        self.assertIn(('INFO', 'media budget 8.0 MB (check_readme.json): two previews'), messages)

    def test_an_invalid_budget_entry_is_a_config_error(self):
        for config in ('{"image_budgets": [{"glob": "Media/b.png", "max_kb": 600}]}',
                       '{"image_budgets": [{"glob": "Media/b.png", "max_kb": 0, "reason": "r"}]}',
                       '{"media_budget": {"max_mb": "8", "reason": "r"}}'):
            self.write(check_readme.CONFIG_RELATIVE, config)
            self.assertEqual(len(self.errors(CLEAN, 'config')), 1, config)

    def test_the_command_line_budget_wins_over_the_file(self):
        self.write('Media/b.png', 'x' * (500 * 1024))
        self.write(check_readme.CONFIG_RELATIVE, '{"image_budgets": [{"glob": "Media/b.png", "max_kb": 600, "reason": "r"}], '
                                                 '"media_budget": {"max_mb": 8, "reason": "r"}}')
        findings, _ = self.check(max_image_kb=450, max_media_mb=0.1)
        self.assertEqual(self._sizes(findings), [('WARN', 'images shown total 0.5 MB (budget 0.1 MB)'),
                                                 ('WARN', 'Media/b.png is 500 KB (budget 450 KB)')])
        path = self.write('README.md', CLEAN)
        printed = io.StringIO()
        stdout, sys.stdout = sys.stdout, printed
        try:
            self.assertEqual(check_readme.main([path, '--max-image-kb', '450']), 0)
        finally:
            sys.stdout = stdout
        self.assertIn('Media/b.png is 500 KB (budget 450 KB)', printed.getvalue())

    def test_the_command_line_without_a_budget_option_reads_the_file(self):
        self.write('Media/b.png', 'x' * (500 * 1024))
        self.write(check_readme.CONFIG_RELATIVE, '{"image_budgets": [{"glob": "Media/b.png", "max_kb": 600, "reason": "r"}]}')
        path = self.write('README.md', CLEAN)
        printed = io.StringIO()
        stdout, sys.stdout = sys.stdout, printed
        try:
            check_readme.main([path])
        finally:
            sys.stdout = stdout
        self.assertNotIn('Media/b.png is 500 KB', printed.getvalue())
        self.assertIn('image budget 600 KB for Media/b.png (check_readme.json): r', printed.getvalue())

    def test_the_command_line_exits_one_on_an_error(self):
        path = self.write('README.md', CLEAN.replace('```bash', '```'))
        with open(os.devnull, 'w') as sink:
            stdout, sys.stdout = sys.stdout, sink
            try:
                code = check_readme.main([path])
            finally:
                sys.stdout = stdout
        self.assertEqual(code, 1)


if __name__ == '__main__':
    unittest.main()
