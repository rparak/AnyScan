"""
Grab a window offscreen at DPR 1 and DPR 2.

    python shoot_both_densities.py <out_prefix> -- <python> <app.py> [app args ...]

Runs the app twice with QT_QPA_PLATFORM=offscreen, first with QT_SCALE_FACTOR=1 and then 2, appending
'--screenshot <out_prefix>_dpr1.png' and '..._dpr2.png'. The app must accept --screenshot (example_app.py does).
Then LOOK at both images: a test that compares regions does not see truncated text or a soft logo.
"""
import os
import subprocess
import sys


def main() -> int:
    if '--' not in sys.argv or sys.argv.index('--') != 2:
        print(__doc__)
        return 2
    prefix, command = sys.argv[1], sys.argv[3:]
    os.makedirs(os.path.dirname(os.path.abspath(prefix)), exist_ok=True)
    status = 0
    for ratio in ('1', '2'):
        out = os.path.abspath('%s_dpr%s.png' % (prefix, ratio))
        if os.path.exists(out):
            os.remove(out)
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_SCALE_FACTOR=ratio)
        run = subprocess.run(command + ['--screenshot', out], env=env, timeout=120)
        # A grab that saved nothing is a failure, whatever the exit status.
        written = os.path.isfile(out) and os.path.getsize(out) > 0
        print('DPR %s -> %s (exit %d%s)' % (ratio, out, run.returncode, '' if written else ', NO FILE WRITTEN'))
        status = status or run.returncode or (0 if written else 1)
    return status


if __name__ == '__main__':
    sys.exit(main())
