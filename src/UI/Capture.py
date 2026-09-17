## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: ../UI/Capture.py
## =========================================================================== ##

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    The per-analysis capture writer: on every completed analysis it writes a set of
    artefacts into the current session's directory under logger/captures/<session_id>/ —

        <set_id>_raw.png            the raw captured frame          (optional, keep_raw)
        <set_id>_annotated.png      the annotated image
        <set_id>_mask.png           the label mask
        <set_id>_understanding.txt  the Scene-Understanding text (shared formatter)
        <set_id>.txt                the YOLO region records, one line per object

    — each named so a set is obviously one analysis. The images carry NO provenance band:
    they are the image and nothing else (a band would corrupt the raw frame as a record of
    what the camera saw), and the set id already lives in the filename and in every related
    log line. The '_understanding.txt' keeps a one-line stamp header. A classes.txt inside
    the session directory lists the region ids in order.

    Retention is enforced ON WRITE and counts sets GLOBALLY across sessions: the oldest
    are evicted first regardless of which session they belong to (so one long session
    cannot starve the bound while a dozen short ones pile up), and a session directory is
    removed once it holds no more sets.

    Qt-free: OpenCV and NumPy are injected. It does file I/O and may raise on a full disk
    or a permission failure; the caller wraps the call so a write failure logs an ERROR
    and never breaks the analysis. The directory is 'captures', not 'tmp': the files
    persist within the retention bound.
"""
# How many analysis sets to keep across ALL sessions. The oldest are evicted on write, so
# the store is bounded: at ~8 MB/set (raw ~4 MB, annotated ~4 MB, the rest negligible)
# this caps it near 400 MB. Turning the raw frame off (CONST_CAPTURE_KEEP_RAW) roughly
# halves the per-set size, so the same disk holds about twice the history.
#   Unit [int]
CONST_CAPTURE_RETENTION_SETS = 50

# Whether the raw captured frame is written. On by default; it is the largest artefact
# and the one reconstructible from nothing, so turning it off is the lever for a longer
# history on the same disk.
#   Unit [bool]
CONST_CAPTURE_KEEP_RAW = True

# The raw-frame suffix (separated so it can be skipped), and every artefact suffix of one
# set — longest first, so a set id is recovered from a filename by stripping the first
# suffix that matches ('_understanding.txt' before the bare YOLO '.txt').
#   Unit [Vector<string>]
CONST_CAPTURE_RAW_SUFFIX = '_raw.png'
CONST_CAPTURE_SUFFIXES = ('_raw.png', '_annotated.png', '_mask.png',
                          '_understanding.txt', '.txt')

# The classes file beside the captures. Its header says, in the file itself, that the ids
# are per-frame object indices and not classes — the warning travels with the data.
#   Unit [string]
CONST_CAPTURE_CLASSES_FILE = 'classes.txt'
CONST_CAPTURE_CLASSES_HEADER = (
    '# NOT class labels. Each id is a per-frame object INDEX: object N in the Scene\n'
    '# Understanding text is id N-1, a handle for finding and hand-correcting that\n'
    '# object. The SAME id means a DIFFERENT part in every frame, so the YOLO <set>.txt\n'
    '# files must NOT be used for training as-is (see docs/design-decisions.md). They\n'
    '# become a dataset only once ids are reassigned by real class.\n')


class Capture_Writer_Cls(object):
    """
    Description:
        Writes and retention-bounds the per-analysis capture sets, in per-session
        subdirectories of a captures root.

    Initialization of the Class:
        Args:
            (1) captures_dir [string]: The captures root (per-session subdirs live here).
            (2) retention_sets [int]: How many newest sets to keep across all sessions (>= 1).
            (3) keep_raw [bool]: Whether to write the raw frame artefact.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Capture_Writer_Cls('logger/captures', 50, True)

            Features:
                # Write one set into a session; returns (evicted ids, created dir or None).
                evicted, created = Cls.Write(session_id, set_id, raw, annotated, mask,
                                             text, yolo_lines, stamp, cv2, np)
    """

    def __init__(self, captures_dir: str, retention_sets: int = CONST_CAPTURE_RETENTION_SETS,
                 keep_raw: bool = CONST_CAPTURE_KEEP_RAW) -> None:
        # << PRIVATE >> #
        self.__dir = captures_dir
        self.__retention = max(1, int(retention_sets))
        self.__keep_raw = bool(keep_raw)

    @property
    def Retention(self) -> int:
        """
        Description:
            The number of newest sets kept across all sessions (the retention bound).

        Returns:
            (1) parameter [int]: The retention bound.
        """

        return self.__retention

    def Write(self, session_id: str, set_id: str, raw_bgr: tp.Any, annotated_bgr: tp.Any,
              mask_bgr: tp.Any, understanding_text: str, yolo_lines: tp.List[str], stamp: str,
              cv2: tp.Any, np: tp.Any) -> tp.Tuple[tp.List[str], tp.Optional[str]]:
        """
        Description:
            Write one analysis set into the session's directory — the annotated image, the
            label mask, the Scene-Understanding '.txt', the YOLO '<set>.txt' and (when
            keep_raw) the raw frame — refresh the classes file, then enforce the global
            retention bound. Raises on a write failure (the caller logs it and continues);
            eviction is best-effort and never raises.

        Args:
            (1) session_id [string]: The session the set belongs to (its subdirectory).
            (2) set_id [string]: The set identifier (<timestamp>_<n>), the filename stem.
            (3) raw_bgr [Matrix<uint8> HxWx3]: The raw captured frame (BGR).
            (4) annotated_bgr [Matrix<uint8> HxWx3]: The annotated image (BGR).
            (5) mask_bgr [Matrix<uint8> HxWx3]: The label mask (BGR).
            (6) understanding_text [string]: The Scene-Understanding text (shared formatter).
            (7) yolo_lines [Vector<string>]: The YOLO region lines, one per object, in order.
            (8) stamp [string]: The provenance stamp appended to every image.
            (9) cv2 [module]: The OpenCV module, injected by the caller.
            (10) np [module]: The NumPy module, injected by the caller.

        Returns:
            (1) parameter [Tuple]: (evicted set ids oldest-first, the session id if its
                                   directory was created by this write else None).
        """

        session_dir, created = self.__Ensure_Session_Dir(session_id)
        if self.__keep_raw:
            self.__Write_Png(session_dir, set_id + CONST_CAPTURE_RAW_SUFFIX, raw_bgr, cv2)
        self.__Write_Png(session_dir, set_id + '_annotated.png', annotated_bgr, cv2)
        self.__Write_Png(session_dir, set_id + '_mask.png', mask_bgr, cv2)
        # The Scene-Understanding text carries the stamp as a leading comment; the YOLO
        # file is a bare region record (its provenance is the set id in its filename).
        self.__Write_Text(session_dir, set_id + '_understanding.txt', '# ' + stamp + '\n'
                          + understanding_text + '\n')
        self.__Write_Text(session_dir, set_id + '.txt',
                          ''.join(line + '\n' for line in yolo_lines))
        self.__Refresh_Classes(session_dir, len(yolo_lines))
        return self.__Evict(), (session_id if created else None)

    def Write_Partial(self, session_id: str, set_id: str, raw_bgr: tp.Any, note: str,
                      stamp: str, cv2: tp.Any, np: tp.Any) -> tp.Tuple[tp.List[str], tp.Optional[str]]:
        """
        Description:
            Write a PARTIAL set into the session's directory for a FAILED analysis — the
            raw frame (when kept) and a '.txt' note saying the analysis failed and only the
            raw frame is present — so a crash leaves evidence (the frame that caused it)
            rather than nothing. The annotated image, mask and YOLO records do not exist,
            because they are produced only after a successful analysis. Retention is
            enforced as for a full set.

        Args:
            (1) session_id [string]: The session the set belongs to (its subdirectory).
            (2) set_id [string]: The set identifier (filename stem).
            (3) raw_bgr [Matrix<uint8> HxWx3]: The raw captured frame (BGR).
            (4) note [string]: The failure note written into the '_understanding.txt'.
            (5) stamp [string]: The provenance stamp.
            (6) cv2 [module]: The OpenCV module, injected by the caller.
            (7) np [module]: The NumPy module, injected by the caller.

        Returns:
            (1) parameter [Tuple]: (evicted set ids, the session id if its directory was
                                   created by this write else None).
        """

        session_dir, created = self.__Ensure_Session_Dir(session_id)
        if self.__keep_raw:
            self.__Write_Png(session_dir, set_id + CONST_CAPTURE_RAW_SUFFIX, raw_bgr, cv2)
        self.__Write_Text(session_dir, set_id + '_understanding.txt', '# ' + stamp + '\n'
                          + note + '\n')
        return self.__Evict(), (session_id if created else None)

    def __Ensure_Session_Dir(self, session_id: str) -> tp.Tuple[str, bool]:
        """
        Description:
            The session's capture directory, creating it if absent — so the caller can log
            an INFO line the first time a session writes a capture.

        Args:
            (1) session_id [string]: The session identifier.

        Returns:
            (1) parameter [Tuple]: (the directory path, True when it was created here).
        """

        session_dir = os.path.join(self.__dir, session_id)
        created = not os.path.isdir(session_dir)
        os.makedirs(session_dir, exist_ok=True)
        return session_dir, created

    def __Write_Png(self, session_dir: str, name: str, image_bgr: tp.Any, cv2: tp.Any) -> None:
        """
        Description:
            Write one PNG — the image and nothing else, no provenance band — raising if the
            write does not land (a full disk or a permission failure returns False from
            cv2.imwrite, which must not pass as a success).

        Args:
            (1) session_dir [string]: The session directory to write into.
            (2) name [string]: The file name.
            (3) image_bgr [Matrix<uint8> HxWx3]: The image (BGR).
            (4) cv2 [module]: The OpenCV module, injected by the caller.
        """

        path = os.path.join(session_dir, name)
        if not cv2.imwrite(path, image_bgr):
            raise OSError('cv2.imwrite reported failure for %s' % path)

    def __Write_Text(self, session_dir: str, name: str, content: str) -> None:
        """
        Description:
            Write one text artefact of a set.

        Args:
            (1) session_dir [string]: The session directory to write into.
            (2) name [string]: The file name.
            (3) content [string]: The full file content.
        """

        with open(os.path.join(session_dir, name), 'w') as handle:
            handle.write(content)

    def __Refresh_Classes(self, session_dir: str, count: int) -> None:
        """
        Description:
            Ensure the session's classes file lists at least `count` region ids
            (0..count-1) under its header — the ids grow monotonically as frames with more
            objects arrive. The file lives INSIDE the session directory, so each capture
            session is self-describing; its header, in the file, warns the ids are
            per-frame indices, not classes.

        Args:
            (1) session_dir [string]: The session directory to write the classes file into.
            (2) count [int]: The number of objects in the frame just written.
        """

        path = os.path.join(session_dir, CONST_CAPTURE_CLASSES_FILE)
        have = 0
        if os.path.isfile(path):
            with open(path, 'r') as handle:
                have = sum(1 for line in handle if line.strip() and not line.startswith('#'))
        if count <= have:
            return
        with open(path, 'w') as handle:
            handle.write(CONST_CAPTURE_CLASSES_HEADER)
            handle.write(''.join('%d\n' % i for i in range(count)))

    def __Evict(self) -> tp.List[str]:
        """
        Description:
            Delete the oldest sets beyond the retention bound, counted GLOBALLY across all
            session directories, newest kept. Sets are ordered by their newest file's
            modification time, so eviction is oldest-first regardless of the id's text.
            A session directory left with no sets is removed. Best-effort: a delete that
            fails is skipped, never raised.

        Returns:
            (1) parameter [Vector<string>]: The evicted set ids, oldest first.
        """

        sets = self.__Sets()
        if len(sets) <= self.__retention:
            return []
        evicted = []
        for set_id, _mtime, session_dir, files in sets[:len(sets) - self.__retention]:
            for name in files:
                try:
                    os.remove(os.path.join(session_dir, name))
                except OSError:
                    pass
            evicted.append(set_id)
            self.__Remove_If_Empty(session_dir)
        return evicted

    def __Remove_If_Empty(self, session_dir: str) -> None:
        """
        Description:
            Remove a session directory once it holds no more capture sets — the per-session
            classes file, being the only non-set artefact, is removed with it so an empty
            session leaves nothing behind. Best-effort.

        Args:
            (1) session_dir [string]: The session directory.
        """

        try:
            if any(self.__Set_Id(name) is not None for name in os.listdir(session_dir)):
                return
            for name in os.listdir(session_dir):            # only the classes file remains, if any
                os.remove(os.path.join(session_dir, name))
            os.rmdir(session_dir)
        except OSError:
            pass

    def __Sets(self) -> tp.List[tp.Tuple[str, float, str, tp.List[str]]]:
        """
        Description:
            Every capture set across all session directories as (set_id, newest_mtime,
            session_dir, files), ordered oldest-first by the newest file each set holds.

        Returns:
            (1) parameter [Vector<Tuple>]: The sets, oldest first.
        """

        grouped = {}
        for session_id in self.__Session_Dirs():
            session_dir = os.path.join(self.__dir, session_id)
            for name in os.listdir(session_dir):
                set_id = self.__Set_Id(name)
                if set_id is None:
                    continue
                try:
                    mtime = os.path.getmtime(os.path.join(session_dir, name))
                except OSError:
                    continue
                entry = grouped.setdefault((session_id, set_id), [0.0, session_dir, []])
                entry[0] = max(entry[0], mtime)
                entry[2].append(name)
        sets = [(set_id, mtime, session_dir, files)
                for (_session, set_id), (mtime, session_dir, files) in grouped.items()]
        sets.sort(key=lambda item: item[1])
        return sets

    def __Session_Dirs(self) -> tp.List[str]:
        """
        Description:
            The session subdirectory names under the captures root (the classes file and
            any stray file are skipped).

        Returns:
            (1) parameter [Vector<string>]: The session directory names.
        """

        try:
            names = os.listdir(self.__dir)
        except OSError:
            return []
        return [name for name in names if os.path.isdir(os.path.join(self.__dir, name))]

    def __Set_Id(self, name: str) -> tp.Optional[str]:
        """
        Description:
            The set id a capture filename belongs to — the name with its artefact suffix
            stripped — or None when the name is not a capture artefact. Suffixes are tried
            longest-first, so '<set>_understanding.txt' is matched before the bare YOLO
            '<set>.txt'.

        Args:
            (1) name [string]: The file name.

        Returns:
            (1) parameter [string]: The set id, or None.
        """

        if name == CONST_CAPTURE_CLASSES_FILE:               # the per-session classes file is not a set
            return None
        for suffix in CONST_CAPTURE_SUFFIXES:
            if name.endswith(suffix):
                return name[:-len(suffix)]
        return None
