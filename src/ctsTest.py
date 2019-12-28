import sys

import ctsSong

inFileName = sys.argv[1]
outFileName = sys.argv[2]

inMidi = ctsSong.Song()
inMidi.import_midi(inFileName)

print("Removing control notes")
inMidi.remove_control_notes()

# Print stats
print('%d notes' % (sum(len(t.notes) for t in inMidi.tracks)))
print('PPQ = %d' % (inMidi.ppq))

qTicksN, qTicksD = inMidi.estimate_quantization()
print("Estimated quantization = ", (qTicksN, qTicksD), "ticks")
inMidi.quantize()
inMidi.eliminate_polyphony()
#inMidi.modulate(3, 2)

print(inMidi.stats)

inMidi.exportMidi(outFileName)
