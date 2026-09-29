## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
## =========================================================================== ##
# Author   : JIC Smart Factory
# File Name: ../Example/Vision/evaluate_describer.py
## =========================================================================== ##

# System (Default)
import argparse
import dataclasses
import json
import os
import sys
import time
# Resolve the project folder from this file's own location (Example/Vision -> ..),
# so the script runs the same whether launched from Example/Vision/ or the repo root.
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
_SRC = os.path.join(CONST_PROJECT_FOLDER, 'src')
if _SRC not in sys.path:
    sys.path.append(_SRC)
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan vision — the pipeline the application analyses with
#   ../Vision/Core
from Vision.Core import Vision_Pipeline_Cls, Vision_Error_Cls
# Custom Lib.: AnyScan vision — the answer key's reader and the scoring
#   ../Vision/Utilities/Evaluation
from Vision.Utilities.Evaluation import (Load_Answer_Key, Score_Object, Tally, Evaluation_Error_Cls,
                                         CONST_ANSWER_KEY_FILE, CONST_ATTRIBUTES)
# Custom Lib.: AnyScan — the one configuration layer
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, Configuration_Error_Cls, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Score the configured describer against the confirmed answer key: run the application's path
    (Load_Configuration -> Configure -> Analyze) over the frames the key names, in the configuration's
    Evaluation.Frames (Data/Images/Test/All), score each object's description on part type, material
    and colour (Vision.Utilities.Evaluation; the rules and patterns are the key's), and print a
    per-object table and the totals, without and with the objects the key leaves out of them.

    It needs the model weights, so it is a tool, not part of the test suite. Greedy decoding makes a
    run repeatable on one machine: the same weights and prompts give the same totals.

        python Example/Vision/evaluate_describer.py
        python Example/Vision/evaluate_describer.py --describer-model models/gemma-4-12B-it-4bit
        python Example/Vision/evaluate_describer.py --output /tmp/describer.json
"""
# The width a description is cut to in the per-object table (the --output file keeps it whole).
#   Unit [int] (characters)
CONST_TEXT_WIDTH = 90


def Run_Frames(configuration: tp.Any, frames_dir: tp.Optional[str], frames: tp.List[str]) -> tp.Dict[str, tp.Any]:
    """
    Description:
        Put the configuration in force the way the application does (Configure: load and warm up)
        and analyse each frame.

    Args:
        (1) configuration [Configuration_Str(object)]: The configuration.
        (2) frames_dir [string]: The directory holding the frames.
        (3) frames [Vector<string>]: The frame names without extension (Image_001, ...).

    Returns:
        (1) parameter [Dict<string, Any>]: 'configure_s', and 'frames': frame -> list of
                                           (description, describe seconds) in object order.
    """

    backend = Vision_Pipeline_Cls(Configuration_Str=configuration)
    started = time.perf_counter()
    backend.Configure(configuration)
    run = {'configure_s': time.perf_counter() - started, 'frames': {}}
    for frame in frames:
        path = os.path.join(frames_dir, frame + '.png')
        image = cv2.imread(path)
        if image is None:
            raise Evaluation_Error_Cls('The frame "%s" named in the answer key could not be read.' % path)
        result = backend.Analyze(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        run['frames'][frame] = [(detection.Detail, timing.Describe_Ms / 1000.0)
                                for detection, timing in zip(result.Objects, result.Timing.Objects)]
        print('[INFO] %s: %d objects in %.2f s.' % (frame, len(result.Objects), result.Timing.Total_Ms / 1000.0))
    return run


def Score_Run(run: tp.Dict[str, tp.Any], key: tp.Dict[str, tp.Any]) -> tp.List[tp.Dict[str, tp.Any]]:
    """
    Description:
        Score every object of a run against the key. A frame whose object count differs from the key's
        stops the scoring: the key then describes another segmentation, and its numbering would not apply.

    Args:
        (1) run [Dict<string, Any>]: From Run_Frames.
        (2) key [Dict<string, Any>]: From Load_Answer_Key.

    Returns:
        (1) parameter [Vector<Dict<string, Any>>]: Per object, in key order: 'entry', 'text', 'seconds',
                                                   'scores'.
    """

    rows = []
    for frame in sorted({entry['frame'] for entry in key['objects']}):
        entries = sorted((entry for entry in key['objects'] if entry['frame'] == frame), key=lambda entry: entry['index'])
        found = run['frames'][frame]
        if len(found) != len(entries):
            raise Evaluation_Error_Cls('%s has %d objects in this run and %d in the answer key: the segmentation has changed, '
                                       'so the key\'s numbering no longer applies. Re-confirm the key before scoring.'
                                       % (frame, len(found), len(entries)))
        for entry in entries:
            text, seconds = found[entry['index'] - 1]
            rows.append({'entry': entry, 'text': text, 'seconds': seconds, 'scores': Score_Object(text, entry, key)})
    return rows


def Print_Report(rows: tp.List[tp.Dict[str, tp.Any]]) -> None:
    """
    Description:
        Print the per-object table, then the totals without and with the objects the key leaves out.

    Args:
        (1) rows [Vector<Dict<string, Any>>]: From Score_Run.
    """

    short = {'correct': 'C', 'wrong': 'W', 'not stated': '-', 'not decidable': '?'}
    print('\n%-12s %-26s %-8s %-4s %-4s %-4s %6s  %s' % ('object', 'key type', 'material', 'type', 'mat', 'col', 'sec', 'description'))
    for row in rows:
        entry = row['entry']
        flag = ' (excluded)' if entry.get('exclude_from_totals') else ''
        print('%-12s %-26s %-8s %-4s %-4s %-4s %6.2f  %s%s' % (
            '%s.%d' % (entry['frame'].replace('Image_', ''), entry['index']), entry['type'][:26], entry['material'],
            short[row['scores']['type']], short[row['scores']['material']], short[row['scores']['colour']], row['seconds'],
            row['text'][:CONST_TEXT_WIDTH], flag))
    excluded = [row['entry'] for row in rows if row['entry'].get('exclude_from_totals')]
    pairs = [(row['entry'], row['scores']) for row in rows]
    for label, include in (('without the %d excluded object(s)' % len(excluded), False), ('all %d objects' % len(rows), True)):
        counted = [row for row in rows if include or not row['entry'].get('exclude_from_totals')]
        totals = Tally(pairs, include_excluded=include)
        print('\nTotals, %s (%d scored):' % (label, len(counted)))
        for attribute in CONST_ATTRIBUTES:
            print('  %-9s correct %2d  wrong %2d  not stated %2d  not decidable %2d' % (
                attribute, totals[attribute]['correct'], totals[attribute]['wrong'], totals[attribute]['not stated'],
                totals[attribute]['not decidable']))
    for entry in excluded:
        print('Excluded %s object %d: %s' % (entry['frame'], entry['index'], entry['exclude_from_totals']))
    seconds = [row['seconds'] for row in rows]
    print('\nDescribe time: %.3f s per object (mean over %d).' % (sum(seconds) / len(seconds), len(seconds)))


def main() -> int:
    """
    Description:
        Parse the command line, load the configuration and the key, run and score the describer, print
        the report, and write the run to --output when given.

    Returns:
        (1) parameter [int]: The exit code.
    """

    parser = argparse.ArgumentParser(description='Score the configured describer against the confirmed answer key.')
    parser.add_argument('--config', default=CONST_DEFAULT_CONFIG_FILE, help='the configuration (default: the shipped one)')
    parser.add_argument('--describer-model', default=None,
                        help='replace Description.Model for this run only (the configuration file is not changed)')
    parser.add_argument('--output', default=None, help='also write every description and score to this JSON file')
    args = parser.parse_args()

    try:
        configuration = Load_Configuration(args.config)
        if args.describer_model:
            model = os.path.abspath(os.path.join(CONST_PROJECT_FOLDER, args.describer_model))
            configuration = dataclasses.replace(configuration, Description=dataclasses.replace(configuration.Description,
                                                                                               Model_Path=model))
        if not configuration.Evaluation.Frames:
            raise Evaluation_Error_Cls('The configuration "%s" does not set Evaluation.Frames, where the frames and '
                                       'the answer key are.' % args.config)
        key = Load_Answer_Key(os.path.join(configuration.Evaluation.Frames, CONST_ANSWER_KEY_FILE))
        print('[INFO] Describer %s; answer key with %d objects.' % (configuration.Description.Model_Path, len(key['objects'])))
        run = Run_Frames(configuration, configuration.Evaluation.Frames, sorted({entry['frame'] for entry in key['objects']}))
        rows = Score_Run(run, key)
    except (Configuration_Error_Cls, Vision_Error_Cls, Evaluation_Error_Cls) as error:
        print('[ERROR] %s' % error)
        return 1
    print('[INFO] Configure (load and warm-up): %.1f s.' % run['configure_s'])
    Print_Report(rows)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as handle:
            json.dump({'describer': configuration.Description.Model_Path, 'configure_s': run['configure_s'],
                       'objects': [{'frame': row['entry']['frame'], 'index': row['entry']['index'], 'text': row['text'],
                                    'seconds': row['seconds'], 'scores': row['scores']} for row in rows]},
                      handle, indent=2)
        print('[INFO] Wrote %s.' % args.output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
