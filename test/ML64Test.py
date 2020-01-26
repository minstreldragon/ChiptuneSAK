import testingPath
import hashlib
import re
import unittest
import ctsSong
import ctsML64


def md5_hash_no_spaces(ml64_input):
    ml64 = re.sub('\\s', '', ml64_input)
    md5 = hashlib.md5(ml64.encode('ascii', 'ignore'))
    return md5.hexdigest()


class TestExportML64(unittest.TestCase):
    def test_ML64_output_measures(self):
        """
        Test ML64 export using "measures" mode against known good files made with our previous tools.
        """
        midi_file = 'jingleBellsSDG.mid'
        known_good_ml64_file = 'jingleBellsSDG.ml64'
        with open(known_good_ml64_file, 'r', encoding='ascii') as f:
            lines = [l.strip() for l in f.readlines() if not l.startswith('//')]
        known_good_ml64_hash = md5_hash_no_spaces(''.join(lines))

        song = ctsSong.Song(midi_file)
        song.quantize_from_note_name('16')  # Quantize to sixteenth notes
        song.remove_polyphony()
        test_ml64 = ctsML64.export_ml64(song, format='m')
        test_ml64_hash = md5_hash_no_spaces(test_ml64)

        self.assertEqual(known_good_ml64_hash, test_ml64_hash)

        midi_file = 'bach_invention_4.mid'
        known_good_ml64_file = 'bach_invention_4.ml64'
        with open(known_good_ml64_file, 'r', encoding='ascii') as f:
            lines = [l.strip() for l in f.readlines() if not l.startswith('//')]
        known_good_ml64_hash = md5_hash_no_spaces(''.join(lines))

        song = ctsSong.Song(midi_file)
        song.quantize_from_note_name('16')  # Quantize to sixteenth notes
        song.remove_polyphony()
        test_ml64 = ctsML64.export_ml64(song, format='m')
        test_ml64_hash = md5_hash_no_spaces(test_ml64)

        self.assertEqual(known_good_ml64_hash, test_ml64_hash)



    def test_ML64_compact_modulation(self):
        """
        Test ML64 export using "compact" mode against a known good file.
        """
        midi_file = 'tripletTest.mid'
        known_good_ml64_file = 'tripletTest.ml64'
        with open(known_good_ml64_file, 'r', encoding='ascii') as f:
            lines = [l.strip() for l in f.readlines() if not l.startswith('//')]
        known_good_ml64_hash = md5_hash_no_spaces(''.join(lines))

        song = ctsSong.Song(midi_file)
        song.modulate(3, 2)
        song.quantize_from_note_name('16')  # Quantize to sixteenth notes
        song.remove_polyphony()
        test_ml64 = ctsML64.export_ml64(song, format='c')
        test_ml64_hash = md5_hash_no_spaces(test_ml64)

        self.assertEqual(known_good_ml64_hash, test_ml64_hash)


if __name__ == '__main__':
    unittest.main()
