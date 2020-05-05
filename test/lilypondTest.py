import testingPath
import unittest
import ctsMChirp
import ctsMidi
import ctsTestingTools
import ctsLilypond
from ctsConstants import project_to_absolute_path

MIDI_TEST_FILE = project_to_absolute_path('test/data/bach_invention_4.mid')
KNOWN_GOOD_LY_FILE_CLIP = project_to_absolute_path('test/data/bach_invention_4_clip_good.ly')

class TestExportLilypond(unittest.TestCase):
    def test_lilypond_(self):
        known_good_ly_hash = ctsTestingTools.md5_hash_no_spaces_file(KNOWN_GOOD_LY_FILE_CLIP)

        song = ctsMidi.import_midi_to_chirp(MIDI_TEST_FILE)
        song.quantize_from_note_name('16')  # Quantize to sixteenth notes
        song.remove_polyphony()

        m_song = ctsMChirp.MChirpSong(song)

        exporter = ctsLilypond.LilypondExporter()

        test_ly = exporter.export_clip_str(m_song, m_song.tracks[0].measures[3:8])
        test_ly_hash = ctsTestingTools.md5_hash_no_spaces(test_ly)

        #with open('data/test.ly', 'w') as f:
        #    f.write(test_ly)

        self.assertEqual(known_good_ly_hash, test_ly_hash)


