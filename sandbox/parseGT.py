# Code to parse goattracker .sng files
# Currently in sandbox folder.  Will be ultimately be refactored into a generalized chiptune-sak importer
#
# Must first install recordtype
#    pip install recordtype
#

import sys
from recordtype import recordtype

"""
Style notes to self (delete later):

    You should only use StudlyCaps for class names.
    Constants should be IN_ALL_CAPS with underscores separating words.
    Variable, method, and function names should always be snake_case.
"""

debug = False

# Define structures to parse data into

GtSongHeader = recordtype('GtSongHeader', [('id', ''), ('song_name', ''), ('author_name', ''), ('copyright', ''),
                                           ('num_subtunes', 0)])

GtSubtuneOrderList = recordtype('GtSubtuneOrderList',
                                [('ch1OrderList', b''), ('ch2OrderList', b''), ('ch3OrderList', b'')])

GtInstrument = recordtype('GtInstrument',
                          [('inst_num', 0), ('attack_decay', 0), ('sustain_release', 0), ('wave_ptr', 0),
                           ('pulse_ptr', 0), ('filter_ptr', 0), ('vib_speetable_ptr', 0), ('vib_delay', 0),
                           ('gateoff_timer', 0),
                           ('hard_restart_1st_frame_wave', 0), ('inst_name', '')])

GtTable = recordtype('GtTable', [('row_cnt', 0), ('left_col', b''), ('right_col', b'')])

GtPatternRow = recordtype('GtPatternRow', [('note_data', 0), ('inst_num', 0), ('command', 0), ('command_data', 0)])


def get_chars(in_bytes, trim_nulls=True):
    result = in_bytes.decode('Latin-1')
    if trim_nulls:
        result = result.strip('\0')  # no interpretation, preserve encoding
    return result


def get_order_list(an_index, file_bytes):
    length = file_bytes[an_index] + 1  # add one, since restart position not counted for some reason
    an_index += 1

    orderlist = file_bytes[an_index:an_index + length]
    an_index += length
    # check that next-to-last byte is $FF
    assert file_bytes[an_index - 2] == 255, "Error: Did not find expected $FF RST endmark in channel's orderlist"

    return orderlist


def get_table(an_index, file_bytes):
    rows = file_bytes[an_index]
    an_index += 1

    left_entries = file_bytes[an_index:an_index + rows]
    an_index += rows

    right_entries = file_bytes[an_index:an_index + rows]

    return GtTable(row_cnt=rows, left_col=left_entries, right_col=right_entries)


def import_sng(gt_filename):
    with open(gt_filename, 'rb') as f:
        sng_bytes = f.read()

    header = GtSongHeader()

    header.id = sng_bytes[0:4]
    assert header.id == b'GTS5', "Error: Did not find magic header used by goattracker sng files"

    header.song_name = get_chars(sng_bytes[4:36])
    header.author_name = get_chars(sng_bytes[36:68])
    header.copyright = get_chars(sng_bytes[68:100])
    header.num_subtunes = sng_bytes[100]

    file_index = 101

    if debug: print("\nDebug: %s" % header)

    """ From goattracker documentation:
    
    3.1 Orderlist data
    ------------------
    
    A song can consist of up to 32 subtunes. For each subtune's each channel, there
    is an orderlist which determines in what order patterns are to be played. In
    addition to pattern numbers, there can be TRANSPOSE & REPEAT commands and
    finally there is a RST (RESTART) endmark followed by restart position. The
    maximum length of an orderlist is 254 pattern numbers/commands + the endmark.
   
    6.1.2 Song orderlists
    ---------------------

    The orderlist structure repeats first for channels 1,2,3 of first subtune,
    then for channels 1,2,3 of second subtune etc., until all subtunes
    have been gone thru.

    Offset  Size    Description
    +0      byte    Length of this channel's orderlist n, not counting restart pos.
    +1      n+1     The orderlist data:
                    Values $00-$CF are pattern numbers
                    Values $D0-$DF are repeat commands
                    Values $E0-$FE are transpose commands
                    Value $FF is the RST endmark, followed by a byte that indicates
                    the restart position
    """

    orderlists = []
    for subtune_index in range(header.num_subtunes):
        order_list = GtSubtuneOrderList()

        order_list.ch1OrderList = get_order_list(file_index, sng_bytes)
        file_index += len(order_list.ch1OrderList) + 1

        order_list.ch2OrderList = get_order_list(file_index, sng_bytes)
        file_index += len(order_list.ch2OrderList) + 1

        order_list.ch3OrderList = get_order_list(file_index, sng_bytes)
        file_index += len(order_list.ch3OrderList) + 1

        orderlists.append(order_list)

    if debug: print("\nDebug: %s" % orderlists)

    """ From goattracker documentation:

    6.1.3 Instruments
    -----------------

    Offset  Size    Description
    +0      byte    Amount of instruments n

    Then, this structure repeats n times for each instrument. Instrument 0 (the
    empty instrument) is not stored.

    Offset  Size    Description
    +0      byte    Attack/Decay
    +1      byte    Sustain/Release
    +2      byte    Wavepointer
    +3      byte    Pulsepointer
    +4      byte    Filterpointer
    +5      byte    Vibrato param. (speedtable pointer)
    +6      byte    Vibraro delay
    +7      byte    Gateoff timer
    +8      byte    Hard restart/1st frame waveform
    +9      16      Instrument name
    """

    instruments = []
    instruments.append(GtInstrument())  # start with empty instrument number 0

    nonzero_inst_count = sng_bytes[file_index]
    file_index += 1

    for i in range(nonzero_inst_count):
        an_instrument = GtInstrument(attack_decay=sng_bytes[file_index], sustain_release=sng_bytes[file_index + 1],
                                     wave_ptr=sng_bytes[file_index + 2], pulse_ptr=sng_bytes[file_index + 3],
                                     filter_ptr=sng_bytes[file_index + 4],
                                     vib_speetable_ptr=sng_bytes[file_index + 5], vib_delay=sng_bytes[file_index + 6],
                                     gateoff_timer=sng_bytes[file_index + 7],
                                     hard_restart_1st_frame_wave=sng_bytes[file_index + 8])
        file_index += 9

        an_instrument.inst_num = i + 1
        an_instrument.inst_name = get_chars(sng_bytes[file_index:file_index + 16])
        file_index += 16

        instruments.append(an_instrument)

    if debug: print("\nDebug: %s" % instruments)

    """ From goattracker documentation:
    6.1.4 Tables
    ------------

    This structure repeats for each of the 4 tables (wavetable, pulsetable,
    filtertable, speedtable).

    Offset  Size    Description
    +0      byte    Amount n of rows in the table
    +1      n       Left side of the table
    +1+n    n       Right side of the table

    @endnode
    @node 6.1.5Patternsheader "6.1.5 Patterns header"

    """

    tables = []
    for i in range(4):
        a_table = get_table(file_index, sng_bytes)
        tables.append(a_table)
        file_index += a_table.row_cnt * 2 + 1

    if debug: print("\nDebug: %s" % tables)
    (wave_table, pulse_table, filter_table, speed_table) = tables

    """ From goattracker documentation:
    
    3.2 Pattern data
    ----------------
    
    Patterns are single-channel only for flexibility & low memory use. They contain
    the actual notes, instrument changes & sound commands. A pattern can have
    variable length, up to 128 rows. There can be 208 different patterns in a song.

    6.1.5 Patterns header
    ---------------------

    Offset  Size    Description
    +0      byte    Number of patterns n
    
    6.1.6 Patterns
    --------------

    Repeat n times, starting from pattern number 0.

    Offset  Size    Description
    +0      byte    Length of pattern in rows m
    +1      m*4     Groups of 4 bytes for each row of the pattern:
                    1st byte: Notenumber
                              Values $60-$BC are the notes C-0 - G#7
                              Value $BD is rest
                              Value $BE is keyoff
                              Value $BF is keyon
                              Value $FF is pattern end
                    2nd byte: Instrument number ($00-$3F)
                    3rd byte: Command ($00-$0F)
                    4th byte: Command databyte
                    
    Notes on tempo:  tracker processes one pattern row per tempo 'beat'
    Tempo is a divisor; lower means faster; 3 seems to be the fastest available
    - Probably a screen refresh divisor (60 Hz or 50 Hz)
    Different tracks can have different tempos
    
    3.6 Miscellaneous tips
    ----------------------
    
    - Patterns will take less memory the less there are command changes. When the
      song is packed/relocated, for example a long vibrato or portamento command
      needs to be stored only once as long as the parameter stays the same on
      subsequent pattern rows.


                    
    """

    num_patterns = sng_bytes[file_index]
    file_index += 1
    patterns = []

    for pattern_num in range(num_patterns):
        a_pattern = []
        num_rows = sng_bytes[file_index]
        file_index += 1
        for row_num in range(num_rows):
            a_row = GtPatternRow(note_data=sng_bytes[file_index], inst_num=sng_bytes[file_index + 1],
                                 command=sng_bytes[file_index + 2], command_data=sng_bytes[file_index + 3])
            file_index += 4
            a_pattern.append(a_row)
        patterns.append(a_pattern)
        if debug: print(
            "\nDebug: pattern num: %d, pattern rows: %d, content: %s" % (pattern_num, len(a_pattern), a_pattern))

    assert file_index == len(sng_bytes), "Error: bytes parsed didn't match file bytes length"


def main():
    import_sng("consultant.sng")
    exit("Done")


if __name__ == "__main__":
    main()
