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
# Custom Lib.: AnyScan — the shared provenance stamp
#   ../Vision/Utilities/Provenance
import Vision.Utilities.Provenance as Provenance

"""
Description:
    Initialization of constants.

    The per-analysis capture writer: on every completed analysis it writes four artefacts
    — the raw captured frame, the annotated image, the label mask and a '.txt' of the
    Scene-Understanding text — into a captures directory, each named so a set is obviously
    one analysis (<set_id>_raw.png / _annotated.png / _mask.png / _understanding.txt) and
    each stamped with the shared provenance stamp. It enforces a retention bound ON WRITE
    — keep the last N sets, evict the oldest first — so the directory can never grow
    without limit, and it reports what it evicted so a lost set is never silent.

    Qt-free: OpenCV and NumPy are injected (the images are rendered by the caller). It
    does file I/O and may raise on a full disk or a permission failure; the caller wraps
    the call so a write failure logs an ERROR and never breaks the analysis.

    The directory is 'captures', not 'tmp': the files persist (within the retention
    bound), and 'tmp' would wrongly imply the OS clears them.
"""
# How many analysis sets to keep. The oldest are evicted on write, so the directory is
# bounded: at ~8 MB/set (raw ~4 MB, annotated ~4 MB, mask + text negligible) this caps
# the store near 400 MB. Turning the raw frame off (CONST_CAPTURE_KEEP_RAW) roughly halves
# the per-set size, so the same disk holds about twice the history.
#   Unit [int]
CONST_CAPTURE_RETENTION_SETS = 50

# Whether the raw captured frame is one of the written artefacts. On by default; it is
# the largest artefact and the one reconstructible from nothing, so turning it off is the
# lever for keeping a longer history on the same disk.
#   Unit [bool]
CONST_CAPTURE_KEEP_RAW = True

# The artefact suffixes of one set. The raw suffix is separated so it can be skipped, and
# so a set id can be recovered from a filename by stripping any of these.
#   Unit [Vector<string>]
CONST_CAPTURE_RAW_SUFFIX = '_raw.png'
CONST_CAPTURE_SUFFIXES = ('_raw.png', '_annotated.png', '_mask.png', '_understanding.txt')


class Capture_Writer_Cls(object):
    """
    Description:
        Writes and retention-bounds the per-analysis capture sets in a directory.

    Initialization of the Class:
        Args:
            (1) captures_dir [string]: The directory the sets are written to.
            (2) retention_sets [int]: How many newest sets to keep (>= 1).
            (3) keep_raw [bool]: Whether to write the raw frame artefact.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Capture_Writer_Cls('logger/captures', 50, True)

            Features:
                # Write one set; returns the ids evicted by the retention bound.
                evicted = Cls.Write(set_id, raw, annotated, mask, text, stamp, cv2, np)
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
            The number of newest sets kept (the retention bound).

        Returns:
            (1) parameter [int]: The retention bound.
        """

        return self.__retention

    def Write(self, set_id: str, raw_bgr: tp.Any, annotated_bgr: tp.Any, mask_bgr: tp.Any,
              understanding_text: str, stamp: str, cv2: tp.Any, np: tp.Any) -> tp.List[str]:
        """
        Description:
            Write one analysis set — the annotated image, the label mask, the '.txt' and
            (when keep_raw) the raw frame — each stamped, then enforce the retention bound
            by evicting the oldest sets beyond it. Raises on a write failure (the caller
            logs it and continues); eviction is best-effort and never raises.

        Args:
            (1) set_id [string]: The set identifier (<timestamp>_<n>), the filename stem.
            (2) raw_bgr [Matrix<uint8> HxWx3]: The raw captured frame (BGR).
            (3) annotated_bgr [Matrix<uint8> HxWx3]: The annotated image (BGR).
            (4) mask_bgr [Matrix<uint8> HxWx3]: The label mask (BGR).
            (5) understanding_text [string]: The Scene-Understanding text (shared formatter).
            (6) stamp [string]: The provenance stamp appended to every artefact.
            (7) cv2 [module]: The OpenCV module, injected by the caller.
            (8) np [module]: The NumPy module, injected by the caller.

        Returns:
            (1) parameter [Vector<string>]: The set ids evicted by the retention bound.
        """

        os.makedirs(self.__dir, exist_ok=True)

        if self.__keep_raw:
            self.__Write_Png(set_id + CONST_CAPTURE_RAW_SUFFIX, raw_bgr, stamp, cv2, np)
        self.__Write_Png(set_id + '_annotated.png', annotated_bgr, stamp, cv2, np)
        self.__Write_Png(set_id + '_mask.png', mask_bgr, stamp, cv2, np)
        # The text carries the stamp as a leading comment, so a stale '.txt' is identifiable
        # on opening — the same header the harness writes.
        with open(os.path.join(self.__dir, set_id + '_understanding.txt'), 'w') as handle:
            handle.write('# ' + stamp + '\n')
            handle.write(understanding_text + '\n')

        return self.__Evict()

    def Write_Partial(self, set_id: str, raw_bgr: tp.Any, note: str, stamp: str,
                      cv2: tp.Any, np: tp.Any) -> tp.List[str]:
        """
        Description:
            Write a PARTIAL set for a failed analysis — the raw frame (when kept) and a
            '.txt' note saying the analysis failed and only the raw frame is present — so a
            crash leaves evidence (the frame that caused it) rather than nothing. The
            annotated image and the mask do not exist, because rendering happens only
            after a successful analysis. Retention is enforced as for a full set.

        Args:
            (1) set_id [string]: The set identifier (filename stem).
            (2) raw_bgr [Matrix<uint8> HxWx3]: The raw captured frame (BGR).
            (3) note [string]: The failure note written into the '.txt'.
            (4) stamp [string]: The provenance stamp.
            (5) cv2 [module]: The OpenCV module, injected by the caller.
            (6) np [module]: The NumPy module, injected by the caller.

        Returns:
            (1) parameter [Vector<string>]: The set ids evicted by the retention bound.
        """

        os.makedirs(self.__dir, exist_ok=True)
        if self.__keep_raw:
            self.__Write_Png(set_id + CONST_CAPTURE_RAW_SUFFIX, raw_bgr, stamp, cv2, np)
        with open(os.path.join(self.__dir, set_id + '_understanding.txt'), 'w') as handle:
            handle.write('# ' + stamp + '\n')
            handle.write(note + '\n')
        return self.__Evict()

    def __Write_Png(self, name: str, image_bgr: tp.Any, stamp: str, cv2: tp.Any, np: tp.Any) -> None:
        """
        Description:
            Write one stamped PNG, raising if the write does not land (a full disk or a
            permission failure returns False from cv2.imwrite, which must not pass as a
            success).

        Args:
            (1) name [string]: The file name within the captures directory.
            (2) image_bgr [Matrix<uint8> HxWx3]: The image (BGR).
            (3) stamp [string]: The provenance stamp.
            (4) cv2 [module]: The OpenCV module, injected by the caller.
            (5) np [module]: The NumPy module, injected by the caller.
        """

        path = os.path.join(self.__dir, name)
        if not cv2.imwrite(path, Provenance.Stamp_Image(image_bgr, stamp, cv2, np)):
            raise OSError('cv2.imwrite reported failure for %s' % path)

    def __Evict(self) -> tp.List[str]:
        """
        Description:
            Delete the oldest sets beyond the retention bound, newest kept. Sets are
            ordered by their newest file's modification time, so the eviction is
            oldest-first regardless of the id's text ordering. Best-effort: a delete that
            fails is skipped, never raised.

        Returns:
            (1) parameter [Vector<string>]: The evicted set ids, oldest first.
        """

        sets = self.__Sets()
        if len(sets) <= self.__retention:
            return []
        evict = sets[:len(sets) - self.__retention]                 # oldest first
        evicted = []
        for set_id, _mtime, files in evict:
            for name in files:
                try:
                    os.remove(os.path.join(self.__dir, name))
                except OSError:
                    pass
            evicted.append(set_id)
        return evicted

    def __Sets(self) -> tp.List[tp.Tuple[str, float, tp.List[str]]]:
        """
        Description:
            Every capture set currently in the directory as (set_id, newest_mtime, files),
            ordered oldest-first by the newest file each set holds.

        Returns:
            (1) parameter [Vector<Tuple>]: The sets, oldest first.
        """

        grouped = {}
        try:
            names = os.listdir(self.__dir)
        except OSError:
            return []
        for name in names:
            set_id = self.__Set_Id(name)
            if set_id is None:
                continue
            try:
                mtime = os.path.getmtime(os.path.join(self.__dir, name))
            except OSError:
                continue
            entry = grouped.setdefault(set_id, [0.0, []])
            entry[0] = max(entry[0], mtime)
            entry[1].append(name)
        sets = [(set_id, mtime, files) for set_id, (mtime, files) in grouped.items()]
        sets.sort(key=lambda item: item[1])
        return sets

    def __Set_Id(self, name: str) -> tp.Optional[str]:
        """
        Description:
            The set id a capture filename belongs to — the name with its artefact suffix
            stripped — or None when the name is not a capture artefact.

        Args:
            (1) name [string]: The file name.

        Returns:
            (1) parameter [string]: The set id, or None.
        """

        for suffix in CONST_CAPTURE_SUFFIXES:
            if name.endswith(suffix):
                return name[:-len(suffix)]
        return None
