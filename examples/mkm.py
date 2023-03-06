# This MKM converter is based on ChiptuneSAK.
# It will be able to read in a MIDI file and output MKM format.
# Typical order of processing:
#
# 1) Read in MIDI file and convert to Chirp representation
# 2) Do some preprocessing in Chirp (e.g. quantization)
# 3) Call to_file() on the exporter
# 4) Exporter creates an MKM object and fills it with data from Chirp:
#    - Iterate over all tracks, over all notes
#    - Convert chirp note to mkm note
#    - Add mkm note to mkm object (adds a note-on timestamp)
#    - Sort mkm notes within mkm object by timestamp
#    - Create event list from notes list
#    - Serialize event list to mkm data list
#    - Write mkm to file

# References:
# American Standard Pitch Notation (ASPN):
# https://open.library.okstate.edu/musictheory/chapter/aspn/#:~:text=The%20octaves%20are%20labeled%20from,is%20C4%20in%20ASPN.

import argparse
import os
import subprocess

import chiptunesak
from chiptunesak.base import *
from chiptunesak.chirp import Note, ChirpTrack, ChirpSong


class Mkm(ChiptuneSAKIO):

    def to_file(self, song, filename, **kwargs):
        print("to_file:", filename)
        mkm_song = MkmSong()
        t = 1
        for track in song.tracks:
            print("Track", t)
            print("qticks_notes:", track.qticks_notes)
            print("qticks_durations:", track.qticks_durations)
            for note in track.notes:
                #print("Note:", note.note_num, MkmNote.to_mkm_pitch(note.note_num))
                mkm_note = MkmNote(note.note_num, note.start_time//track.qticks_notes, note.duration//track.qticks_durations, t)
                #print("Note:", mkm_note.pitch, mkm_note.start_time, mkm_note.duration, mkm_note.voice)
                print("Note1:", mkm_note)
                mkm_song.add_note(mkm_note)
            t += 1

        ##print("Song unsorted:",mkm_song)
        ##mkm_song.sort()
        print("Song sorted:",mkm_song)
        mkm_song.to_event_list()
        ##mkm_song.print_event_list()
        data = bytes(mkm_song.to_data())
        print(data)
        with open(filename, 'wb') as f:
            f.write(data)


class MkmNote:
    midi_pitch_min = 36     # C2
    midi_pitch_max = 99     # D#7

    def __init__(self, pitch, start, duration, voice):
        self.pitch = pitch
        self.start_time = start
        self.duration = duration
        self.voice = voice

    def __str__(self):
        return str(self.pitch) + ' ' + str(self.start_time) + " " + str(self.duration) + " " + str(self.voice)

    @classmethod
    def to_mkm_pitch(cls, midi_pitch):
        while (midi_pitch < MkmNote.midi_pitch_min):
            print("raising pitch")
            midi_pitch += 12
        while (midi_pitch > MkmNote.midi_pitch_max):
            print("lowering pitch")
            midi_pitch -= 12
        return midi_pitch - MkmNote.midi_pitch_min
        #if (midi_pitch < MkmNote.midi_pitch_min):
        #    raise ValueError('MIDI pitch too low', midi_pitch)
        #elif (midi_pitch > MkmNote.midi_pitch_max):
        #    raise ValueError('MIDI pitch too high', midi_pitch)

class MkmEvent:
    def __init__(self, time):
        self.time = time

    def to_data(self):
        return []

class MkmNoteOn(MkmEvent):
    def __init__(self, note):
        super().__init__(note.start_time)
        self.pitch = note.pitch
        self.duration = note.duration
        self.voice = note.voice

    def __str__(self):
        return str(str(self.time) + ' Note On ' + str(self.pitch) + ' ' + str(self.duration) + ' ' + str(self.voice) + '\n')

    def to_data(self):
        if self.duration > 127:
            raise ValueError('NoteOn Event: Duration too long', self.duration)
        pitch = MkmNote.to_mkm_pitch(self.pitch)
        return [self.duration << 1, pitch << 2 | self.voice]

class MkmNoteOff(MkmEvent):
    def __init__(self, note):
        super().__init__(note.start_time + note.duration)
        self.voice = note.voice

    def __str__(self):
        return str(str(self.time) + ' Note Off ' + str(self.voice) + '\n')

    def to_data(self):
        return []

class MkmTimeDelay(MkmEvent):
    def __init__(self, time, delay):
        super().__init__(time)
        self.delay = delay

    def __str__(self):
        return str(str(self.time) + ' Time Delay ' + str(self.delay) + '\n')

    def to_data(self):
        if self.delay > 127:
            raise ValueError('Time Delay Event too long', self.delay)
        return [self.delay << 1 | 1,]

class MkmSongEnd(MkmEvent):
    def __init__(self, time):
        super().__init__(time)

    def __str__(self):
        return str(str(self.time) + ' Song End\n')

    def to_data(self):
        return [0,0]


class MkmSong:
    def __init__(self, name="mkm song"):
        self.notes = list()

    def add_note(self, note):
        self.notes.append(note)

    def sort(self):
        self.notes.sort(key=lambda note: note.start_time)

    def to_event_list(self):
         # creates an event list from the existing notes list
         # for all notes, add note-on and note-off events
         # iterate over event list, add time delay events, output events2
         events = list()
         time = 0
         for note in self.notes:
             events.append(MkmNoteOn(note))
             events.append(MkmNoteOff(note))
         # insert time delay events
         events.sort(key=lambda ev: ev.time)

         events2 = list()
         time = 0
         for ev in events:
             if ev.time > time:
                 events2.append(MkmTimeDelay(time, ev.time-time))
             events2.append(ev)
             time = ev.time
         events2.append(MkmSongEnd(time))

         self.event_list = events2

    def print_event_list(self):
        for ev in self.event_list:
            print(ev)

    def to_data(self):
        data = list()
        time = 0
        for ev in self.event_list:
            data.extend(ev.to_data())
            # fetch event time
            # add time delay events until time == ev.time
            # extend data with new event (may be empty list) (data.extend(ev.to_data()))

            #while note.start_time > time:
            #    dt = note.start_time - time
            #    if dt > 127:
            #        delay = 127
            #    else delay = dt
            #    # add time delay event (delay)
            #    time += delay
        
        return data
            

    def __str__(self):
        out = ""
        for n in self.notes:
            out = out + str(n) + "\n"
        return out

def parse_arguments():
    parser = argparse.ArgumentParser(description='MIDI to MKM file converter')
    parser.add_argument('input')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_arguments()
    input_midi_file = args.input
    print("Hello Nox!")
    print("Input file name:", args.input)

    # Read in the MIDI song and quantize
    chirp_song = chiptunesak.MIDI().to_chirp(input_midi_file, quantization='32', polyphony=False)
    mkm = Mkm()
    mkm.to_file(chirp_song, "squirrel_out.mkm")
