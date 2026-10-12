import numpy as np


def longest_clean_segment(t, max_gap_s=0.5):
    """Return (start, end) of the longest run where time strictly increases
    and no step is larger than max_gap_s. Removes junk frames and dropouts."""
    t = np.asarray(t, dtype="float64")
    if len(t) < 2:
        return 0, len(t)
    dt = np.diff(t)
    bad = (dt <= 0) | (dt > max_gap_s)
    cuts = np.concatenate(([0], np.where(bad)[0] + 1, [len(t)]))
    return max(zip(cuts[:-1], cuts[1:]), key=lambda se: se[1] - se[0])


def bits_to_float(value):
    """Betaflight stores some header floats as raw 32-bit integers."""
    import struct
    return struct.unpack("<f", struct.pack("<I", int(value) & 0xFFFFFFFF))[0]
