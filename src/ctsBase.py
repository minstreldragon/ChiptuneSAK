import re
import collections
from dataclasses import dataclass
from fractions import Fraction
from ctsErrors import *
from ctsConstants import *
from ctsKey import ChirpKey


# Named tuple types for several lists throughout
TimeSignatureEvent = collections.namedtuple('TimeSignature', ['start_time', 'num', 'denom'])
KeySignatureEvent = collections.namedtuple('KeySignature', ['start_time', 'key'])
TempoEvent = collections.namedtuple('Tempo', ['start_time', 'bpm'])
OtherMidiEvent = collections.namedtuple('OtherMidi', ['start_time', 'msg'])
ProgramEvent = collections.namedtuple('Program', ['start_time', 'program'])
Beat = collections.namedtuple('Beat', ['start_time', 'measure', 'beat'])
Rest = collections.namedtuple('Rest', ['start_time', 'duration'])
MeasureMarker = collections.namedtuple('MeasureMarker', ['start_time', 'measure_number'])


@dataclass
class SongMetadata:
    ppq: int = 960
    name: str = ''
    composer: str = ''
    copyright: str = ''
    time_signature: TimeSignatureEvent = TimeSignatureEvent(0, 4, 4)
    key_signature: KeySignatureEvent = KeySignatureEvent(0, ChirpKey('C'))
    bpm: int = 112


# --------------------------------------------------------------------------------------
#
#  Utility functions
#
# --------------------------------------------------------------------------------------

def quantization_error(t_ticks, q_ticks):
    """
    Calculated the error, in ticks, for the given time for a quantization of q ticks.
    """
    j = t_ticks // q_ticks
    return int(min(abs(t_ticks - q_ticks * j), abs(t_ticks - q_ticks * (j + 1))))


def objective_error(notes, test_quantization):
    """
    This is the objective function for getting the error for the entire set of notes for a
    given quantization in ticks.  The function used here could be a sum, RMS, or other
    statistic, but empirical tests indicate that the max used here works well and is robust.
    """
    return max(quantization_error(n, test_quantization) for n in notes)


def find_quantization(time_series, ppq):
    """
    Find the optimal quantization in ticks to use for a given set of times.  The algorithm given
    here is by no means universal or guaranteed, but it usually gives a sensible answer.

    The algorithm works as follows:
    - Starting with quarter notes, obtain the error from quantization of the entire set of times.
    - Then obtain the error from quantization by 2/3 that value (i.e. triplets).
    - Then go to the next power of two (e.g. 8th notes, a6th notes, etc.) and repeat

    A minimum in quantization error will be observed at the "right" quantization.  In either case
    above, the next quantization tested will be incommensurate (either a factor of 2/3 or a factor
    of 3/4) which will make the quantization error worse.

    Thus, the first minimum that appears will be the correct value.

    The algorithm does not seem to work as well for note durations as it does for note starts, probably
    because performed music rarely has clean note cutoffs.
    """
    last_err = len(time_series) * ppq
    last_q = ppq
    note_value = 4
    while note_value <= 128:  # We have arbitrarily chosen 128th notes as the fastest possible
        test_quantization = ppq * 4 // note_value
        e = objective_error(time_series, test_quantization)
        # print(test_quantization, e) # This was useful for observing the behavior of real-world music
        if e == 0:  # Perfect quantization!  We are done.
            return test_quantization
        # If this is worse than the last one, the last one was the right one.
        elif e > last_err:
            return last_q
        last_q = test_quantization
        last_err = e

        # Now test the quantization for triplets of the current note value.
        test_quantization = test_quantization * 2 // 3
        e = objective_error(time_series, test_quantization)
        # print(test_quantization, e) # This was useful for observing the behavior of real-world music
        if e == 0:  # Perfect quantization!  We are done.
            return test_quantization
            # If this is worse than the last one, the last one was the right one.
        elif e > last_err:
            return last_q
        last_q = test_quantization
        last_err = e

        # Try the next power of two
        note_value *= 2
    return 1  # Return a 1 for failed quantization means 1 tick resolution


def find_duration_quantization(durations, qticks_note):
    """
    The duration quantization is determined from the shortest note length.
    The algorithm starts from the estimated quantization for note starts.
    """
    min_length = min(durations)
    if not (min_length > 0):
        raise ChiptuneSAKQuantizationError("Illegal minimum note length (%d)" % min_length)
    current_q = qticks_note
    ratio = min_length / current_q
    while ratio < 0.9:
        # Try a triplet
        tmp_q = current_q
        current_q = current_q * 3 // 2
        ratio = min_length / current_q
        if ratio > 0.9:
            break
        current_q = tmp_q // 2
        ratio = min_length / current_q
    return current_q


def quantize_fn(t, qticks):
    """
    This function quantizes a time to a certain number of ticks.
    """
    current = t // qticks
    next = current + 1
    current *= qticks
    next *= qticks
    if abs(t - current) <= abs(next - t):
        return current
    else:
        return next


def duration_to_note_name(duration, ppq, locale='US'):
    """
    Given a ppq (pulses per quaver) convert a duration to a human readable note length, e.g., 'eighth'
    Works for notes, dotted notes, and triplets down to sixty-fourth notes.
    """
    f = Fraction(duration / ppq).limit_denominator(64)
    return DURATIONS[locale.upper()].get(f, '<unknown>')


def pitch_to_note_name(note_num, octave_offset=0):
    """
    Gets note name for a given MIDI pitch
    """
    if not 0 <= note_num <= 127:
        raise ChiptuneSAKValueError("Illegal note number %d" % note_num)
    octave = (note_num // 12) + octave_offset
    pitch = note_num % 12
    return "%s%d" % (PITCHES[pitch], octave)


# Regular expression for matching note names
note_name_format = re.compile('^([A-G])(#|##|b|bb)?([0-7])$')


def note_name_to_pitch(note_name, octave_offset=0):
    """
    Returns MIDI note number for a named pitch.  C4 = 60
    Includes processing of enharmonic notes (double sharps or double flats)
        :param note_name:      A note name as a string, e.g. C#4
        :param octave_offset:  Octave offset
        :return:  Midi note number
    """
    if note_name_format.match(note_name) is None:
        raise ChiptuneSAKValueError('Illegal note name: "%s"' % note_name)
    m = note_name_format.match(note_name)
    note_name = m.group(1)
    accidentals = m.group(2)
    octave = int(m.group(3)) - octave_offset
    note_num = PITCHES.index(note_name) + 12 * (octave + 1)
    if accidentals is not None:
        note_num += accidentals.count('#')
        note_num -= accidentals.count('b')
    return note_num

    
def decompose_duration(duration, ppq, allowed_durations):
    """
    Decomposes a given duration into a sum of allowed durations.
    This function uses a greedy algorithm, which iteratively finds the largest allowed duration shorter than
    the remaining duration and subtracts it from the remaining
        :param duration:           Duration to be decomposed, in ticks.
        :param ppq:                Ticks per quarter note.
        :param allowed_durations:  Either a dictionary or a set of allowed durations.  Allowed durations are
                                   expressed as fractions of a quarter note.
        :return: List of fractions
    """
    ret_durations = []
    min_allowed_duration = min(allowed_durations)
    remainder = duration
    while remainder > 0:
        if remainder < min_allowed_duration * ppq:
            raise ChiptuneSAKValueError("Illegal note duration %d" % duration)
        for d in sorted(allowed_durations, reverse=True):
            if remainder >= d * ppq:
                ret_durations.append(d)
                remainder -= d * ppq
                break
    return ret_durations


def is_triplet(note, ppq):
    """
    Determine if note is a triplet
        :param note:
        :param ppq:
        :return:
    """
    f = Fraction(note.duration/ppq).limit_denominator(16)
    if f.denominator % 3 == 0:
        return True
    return False


def start_beat_type(time, ppq):
    """
    Gets the beat type that would have to be used to make this note an integral number of beats
    from the start of the measure

        :param time:  Time in ticks from the start of the measure.
        :param ppq:   ppq for the song
        :return:      Denominator that would have to be used to make this note an integral number of beats
                      from the start of the measure.  If the note is a triplet not starting on the beat it
                      will be a multiple of 3.
    """
    f = Fraction(time, ppq).limit_denominator(16)
    return f.denominator
