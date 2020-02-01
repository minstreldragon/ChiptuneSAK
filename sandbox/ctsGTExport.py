# Convert Chirp to GoatTracker2 and save as .sng file
#
# TODOs:
# -

import sys
import sandboxPath
from fractions import Fraction
import math
from functools import reduce, partial
from ctsErrors import *
from ctsConstants import *
import ctsChirp

def chirp_to_GT(song, out_filename, tracknums = [1, 2, 3], jiffy=PAL_FRAMES_PER_SEC):
    def midi_to_gt_tick(midi_ticks, offset, factor):
        return midi_ticks // factor + offset

    if not song.is_quantized():
        raise ChiptuneSAKQuantizationError("ChirpSong must be quantized for export to GT")
    if song.is_polyphonic():
        raise ChiptuneSAKPolyphonyError("ChirpSong must be non-polyphonic for export to GT")

    ###  For the following, I am currently IGNORING triplets!!!!

    # TODO: Algorithm design
    # Assertion: chirp ticks and goattracker rows are unitless (no mapping to time without tempo)
    # Find the unique set of note lengths in chirp ticks
    # reduce set to create most granular row length (e.g. 20, 30, 40, 80 -> 2, 3, 4, 8)
    #    this means finding the greatest common divisor, and divising it
    #    In other words, the minimum reduction that remains integers
    # From this, map BPM to what the tempo should be
    #    This creates the minimum number of rows necessary per note type


    # Count the number of jiffies per beat
    jiffies_per_beat = jiffy / (song.metadata.bpm / 60) # jiffies per sec / bpm / 60

    # Get distinct note lengths from the song
    note_lengths = set(n.duration for t in song.tracks for n in t.notes)

    required_granularity = reduce(math.gcd, sorted(note_lengths))
    note_lengths = set(n//required_granularity for n in note_lengths)
    # This is the minumum number of rows required to have all notes representable by an integer number of rows.
    min_rows_per_note = min(note_lengths)

    # Now we get into the weeds; given a tempo in bpm and number of rows per beat, we can come
    #  up with a tempo that is closest to the desired bpm and can still play all the notes in the song.
    print(jiffies_per_beat, required_granularity)
    maybe_rows_per_beat = 4
    maybe_jiffies_per_row = jiffies_per_beat / maybe_rows_per_beat  # note: this is a floating_point number

    # This is now a real number to convert between unitless midi ticks and unitless GT ticks
    # The complication is that you can multiply the min_rows_per_note by an integer to give better
    #   time resolution, which will result in a different set of GT tempos available
    midi_to_tick = partial(midi_to_gt_tick, offset=0, factor=song.metadata.ppq // min_rows_per_note)

    # Set the tempo at tick 0 for all three voices

    for itrack, tracknum in enumerate(tracknums):
        track = song.tracks[tracknum-1]
        for note in track.notes:
            tick_start = midi_to_tick(note.start_time)
            tick_end = midi_to_tick(note.start_time + note.duration)
            note_num = note.note_num
            ## Add the start and end of the note to the ticks for track itrack

    ## Clean up and write .sng file
    ##  And that should be it!


if __name__ == "__main__":
    song = ctsChirp.ChirpSong(sys.argv[1])
    song.quantize_from_note_name('16')
    song.remove_polyphony()

    chirp_to_GT(song, 'tmp.sng')