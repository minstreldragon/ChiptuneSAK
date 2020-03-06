from fractions import Fraction
from dataclasses import dataclass, field

CHIPTUNESAK_VERSION = "0.13"

C0_MIDI_NUM = 12
C4_MIDI_NUM = 60
BIG_NUMBER = 0xFFFFFFFF

PITCHES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

KEYS = {'major': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'],
        'minor': ['Am', 'Bbm', 'Bm', 'Cm', 'C#m', 'Dm', 'Ebm', 'Em', 'Fm', 'F#m', 'Gm', 'G#m']
        }

DURATIONS = {
    'US': {
        Fraction(8, 1): 'double whole', Fraction(6, 1): 'dotted whole', Fraction(4, 1): 'whole',
        Fraction(3, 1): 'dotted half', Fraction(2, 1): 'half', Fraction(4, 3): 'half triplet',
        Fraction(3, 2): 'dotted quarter', Fraction(1, 1): 'quarter', Fraction(3, 4): 'dotted eighth',
        Fraction(2, 3): 'quarter triplet', Fraction(1, 2): 'eighth', Fraction(3, 8): 'dotted sixteenth',
        Fraction(1, 3): 'eighth triplet', Fraction(1, 4): 'sixteenth',
        Fraction(3, 16): 'dotted thirty-second',  Fraction(1, 6): 'sixteenth triplet',
        Fraction(1, 8): 'thirty-second', Fraction(3, 32): 'dotted sixty-fourth',
        Fraction(1, 12): 'thirty-second triplet', Fraction(1, 16): 'sixty-fourth',
        Fraction(1, 24): 'sixty-fourth triplet'
    },
    'UK': {
        Fraction(8, 1): 'breve', Fraction(6, 1): 'dotted semibreve', Fraction(4, 1): 'semibreve',
        Fraction(3, 1): 'dotted minim', Fraction(2, 1): 'minim', Fraction(4, 3): 'minim triplet',
        Fraction(3, 2): 'dotted crochet', Fraction(1, 1): 'crochet', Fraction(3, 4): 'dotted quaver',
        Fraction(2, 3): 'crochet triplet', Fraction(1, 2): 'quaver', Fraction(3, 8): 'dotted semiquaver',
        Fraction(1, 3): 'quaver triplet', Fraction(1, 4): 'semiquaver', Fraction(3, 16): 'dotted demisemiquaver',
        Fraction(1, 6): 'semiquaver triplet', Fraction(1, 8): 'demisemiquaver',
        Fraction(3, 32): 'dotted hemidemisemiquaver', Fraction(1, 12): 'demisemiquaver triplet',
        Fraction(1, 16): 'hemidemisemiquaver', Fraction(1, 24): 'hemidemisemiquaver triplet'
    }
}

# Duration fractions are defined in terms of quarter notes
DURATION_STR = {
    '1.': Fraction(6, 1), '1': Fraction(4, 1), '2.': Fraction(3, 1), '2': Fraction(2, 1), '2-3': Fraction(4, 3),
    '4.': Fraction(3, 2), '4': Fraction(1, 1), '8.': Fraction(3, 4), '4-3': Fraction(2, 3),
    '8': Fraction(1, 2), '16.': Fraction(3, 8), '8-3': Fraction(1, 3), '16': Fraction(1, 4),
    '32.': Fraction(3, 16), '16-3': Fraction(1, 6), '32': Fraction(1, 8), '64.': Fraction(3, 32),
    '32-3': Fraction(1, 12), '64': Fraction(1, 16), '64-3': Fraction(1, 24)
}

# Commodore Constants:

BASIC_START_C64 = 2049  # $0801
BASIC_START_C128 = 7169  # $1C01

BASIC_LINE_MAX_C64 = 80  # 2 lines of 40 col
BASIC_LINE_MAX_VIC20 = 88  # 4 lines of 22 col
BASIC_LINE_MAX_C128 = 160  # 4 lines of 40 col


# A traditional PAL tracker reasoning anchor point between temporally-unitless rows
# and BPM is that 6 frames per row (a fast speed) is easily tied to 125 BPM.
# This forms the basis of many PAL tracker defaults, and is used when giving simple
# concrete examples of computing tempos.
# Details: 6 frames per row * PAL 20msPerFrame = 0.12 sec per row
# that's 1/0.12 = x=8.333333 rows per sec, so 60 seconds / 0.12 sec per row = 500 rows per min
# 500 rows per min / 125 BPM = 4 rows per quarter note in 4/4
# so a row becomes a 16th note


@dataclass(frozen=True)
class ArchDescription:
    system_clock: int
    frame_rate: float = field(init=False)
    ms_per_frame: float = field(init=False)
    cycles_per_line: int
    lines_per_frame: int
    visible_lines: int
    blank_lines: int = field(init=False)

    def __post_init__(self):
        # Since we have made the object frozen, we can't just assign to the variables so we do it via a backdoor
        super().__setattr__('cycles_per_frame', self.lines_per_frame * self.cycles_per_line)
        super().__setattr__('frame_rate', self.system_clock / self.cycles_per_frame)
        super().__setattr__('ms_per_frame', 1000. / self.frame_rate)
        super().__setattr__('blank_lines', self.lines_per_frame - self.visible_lines)


# TODO:
# http://www.antimon.org/dl/c64/code/stable.txt
# https://www.lemon64.com/forum/viewtopic.php?t=36751
# - NTSC VIC-20 system_clock = 1022727, cycles_per_line=65, lines_per_frame=261   vertical blank 0 through 27
# - PAL VIC-20  system_clock = 1108405, cycles_per_line=71, lines_per_frame=312
# - NTSC/PAL C128 (defaults to 1Mhz mode) is same as C64 NTSC/PAL

ARCH = {
    'NTSC': ArchDescription(system_clock=1022727,  # The "new" NTSC 6567R8
                            cycles_per_line=65,
                            lines_per_frame=263,
                            visible_lines=235),
    'PAL': ArchDescription(system_clock=985248,   # 6569 chip
                           cycles_per_line=63,
                           lines_per_frame=312,
                           visible_lines=284),
    'NTSC-R56A': ArchDescription(system_clock=1022727,  # The "old" NTSC 6567R56A
                                 cycles_per_line=64,
                                 lines_per_frame=262,
                                 visible_lines=234),
    'NTSC-VIC20': ArchDescription(system_clock=1022727,   # 6560-101 chip
                                  cycles_per_line=65,
                                  lines_per_frame=261,
                                  visible_lines=233),
    'PAL-VIC20': ArchDescription(system_clock=1108405,   # 6561-101 chip
                                 cycles_per_line=71,
                                 lines_per_frame=312,
                                 visible_lines=284),
}
