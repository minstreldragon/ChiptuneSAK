import copy
from ctsErrors import *
import ctsConstants
import ctsSong
import more_itertools as moreit

""" Utility functions for exporting to various formats from the ctsSong.Song representation """


def populate_measures(song, track):
    """
    Converts a track into measures, each of which is a sorted list of notes and other events
    """
    def sort_order(c):
        """
        Sort function for measure contents.
        Items are sorted by time and then, for equal times, in this order:
            Time Signature
            Key Signature
            Tempo
            Other MIDI message(s)
            Notes and rests
        """
        if isinstance(c, ctsSong.Note):
            return (c.start_time, 10)
        elif isinstance(c, ctsSong.Rest):
            return (c.start_time, 10)
        elif isinstance(c, ctsSong.MeasureMarker):
            return (c.start_time, 0)
        elif isinstance(c, ctsSong.TimeSignature):
            return (c.start_time, 1)
        elif isinstance(c, ctsSong.KeySignature):
            return (c.start_time, 2)
        elif isinstance(c, ctsSong.Tempo):
            return (c.start_time, 3)
        elif isinstance(c, ctsSong.Program):
            return (c.start_time, 4)
        else:
            return (c.start_time, 5)

    # Find all the measure positions in time; note that since this is song-based, all tracks will have the
    # same number of measures.
    measure_starts = song.measure_starts()
    # Artificially add an extra measure on the end to finish processing the notes in the last measure.
    measure_starts.append(2 * measure_starts[-1] - measure_starts[-2])
    n_notes = len(track.notes)
    retval = []
    inote = 0  # Index of current note
    carry = None  # Note carried over from previous measure
    last_note_end = 0  # Time that the previous note ended
    # First add in the notes to the measure
    imeasure = 0
    for start, end in moreit.pairwise(measure_starts):
        imeasure += 1
        current_measure = [ctsSong.MeasureMarker(start, imeasure)]  # Every measure starts out with a measure marker
        last_note_end = start
        if carry:  # Deal with any notes carried over from the previous measure
            carry.start_time = start
            carry_end = start + carry.duration
            if carry.duration <= 0:
                raise ChiptuneSAKValueError("Illegal carry note duration %d" % carry.duration, str(carry))
            if carry_end > end:  # Does the carried note extend past the end of this measure?
                current_measure.append(ctsSong.Note(carry.note_num, start, end-start, 100, tied=True))
                carry.duration -= end - start
                last_note_end = end
            else:  # Carried note ends during this measure
                current_measure.append(carry)
                last_note_end = start + carry.duration
                carry = None

        # Now iterate over the notes that begin during this measure
        while inote < n_notes and track.notes[inote].start_time < end:
            n = track.notes[inote]
            gap = n.start_time - last_note_end
            if gap > 0:  # Is there a rest before the note starts?
                current_measure.append(ctsSong.Rest(last_note_end, gap))
                last_note_end = n.start_time
            note_end = n.start_time + n.duration  # Time that this note ends
            if note_end <= end:  # Note fits within the current measure
                current_measure.append(n)
                last_note_end = note_end
            else:
                carry = copy.deepcopy(n)  # Make a copy of the note to use for the carry
                duration = end - n.start_time
                n.duration = duration  # truncate the note to the end of the measure
                n.tied = True  # And mark it as tied to the next note
                current_measure.append(n)
                last_note_end = end
                carry.duration -= duration  # Det the length of the carried note to the remaining time
            inote += 1  # Move to the next note

        gap = end - last_note_end
        if gap > 0:  # Is there a rest needed at the end of the measure?
            current_measure.append(ctsSong.Rest(last_note_end, gap))
            last_note_end = end

        # Add any additional track-specific messages to the measure:
        for m in track.other:
            if start <= m.start_time < end:
                # Leave the time of these messages alone
                if m.msg.type == 'program_change':  # Split out program changes
                    current_measure.append(ctsSong.Program(m.start_time, m.msg.program))
                else:
                    current_measure.append(m)

        #  Now add all the song-specific events to the measure.
        for ks in song.key_signature_changes:
            if start <= ks.start_time < end:
                # Key signature changes must occur at the start of the measure
                current_measure.append(ctsSong.KeySignature(start, ks.key))

        for ts in song.time_signature_changes:
            if start <= ts.start_time < end:
                # Time signature changes must occur at the start of the measure
                current_measure.append(ctsSong.TimeSignature(start, ts.num, ts.denom))

        for tm in song.tempo_changes:
            if start <= tm.start_time < end:
                # Tempo changes can happen anywhere in the measure
                current_measure.append(ctsSong.Tempo(tm.start_time, tm.bpm))

        for m in song.other:
            if start <= m.start_time < end:
                # Leave the time of these messages alone
                current_measure.append(m)

        current_measure = sorted(current_measure, key=sort_order)
        retval.append(current_measure)

    return retval


def count_notes(measure):
    """
    Counts the number of notes in a measure.  Ignores everything else.
    """
    return sum(1 for e in measure if isinstance(e, ctsSong.Note))


def trim_measures(measures_list):
    """
    Trims all note-free measures from the end of the song.
    """
    while all(count_notes(m[-1]) == 0 for m in measures_list):
        for i in range(len(measures_list)):
            measures_list[i].pop()
    return measures_list


def get_measures(song):
    """
    Gets all the measures from all the tracks in a song, and removes any extra measures from the end.
    """
    all_measures = [populate_measures(song, t) for t in song.tracks]
    return trim_measures(all_measures)
