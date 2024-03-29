#!/usr/bin/env python3

# PSPTrace - Correlate SPI captures created by a Saleae Logic Analyzer with PSP firmware from UEFI images
# Copyright (C) 2019 Christian Werling
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import pickle
import csv
import sys
import argparse
import pkg_resources

from signal import signal, SIGPIPE, SIG_DFL
from collections import deque

from prettytable import PrettyTable

from psptool import PSPTool
from psptool.entry import Entry

# from http://www.winbond.com.tw/resource-files/w25q128jv%20spi%20revb%2011082016.pdf
WINBOND_INSTRUCTIONS = {
    0x06: {
        'name': 'Write Enable',
        'size': 1,
        'expects_data': False
    },
    0x50: {
        'name': 'Volatile SR Write Enable',
        'size': 1,
        'expects_data': False
    },
    0x04: {
        'name': 'Write Disable',
        'size': 1,
        'expects_data': False
    },
    0xAB: {
        'name': 'Release Power-down / ID',
        'size': 4,
        'expects_data': True
    },
    0x90: {
        'name': 'Manufacturer/Device ID',
        'size': 4,
        'expects_data': True
    },
    0x9F: {
        'name': 'JEDEC ID',
        'size': 1,
        'expects_data': True
    },
    0x4B: {
        'name': 'Manufacturer/Device ID',
        'size': 5,
        'expects_data': True
    },
    0x03: {
        'name': 'Read Data',
        'size': 4,
        'expects_data': True
    },
    0x0B: {
        'name': 'Fast Read',
        'size': 5,
        'expects_data': True
    },
    0x02: {
        'name': 'Page Program',
        'size': 6,
        'expects_data': False
    },
    0x20: {
        'name': 'Sector Erase (4KB)',
        'size': 4,
        'expects_data': False
    },
    0x52: {
        'name': 'Block Erase (32KB)',
        'size': 4,
        'expects_data': False
    },
    0xD8: {
        'name': 'Block Erase (64KB)',
        'size': 4,
        'expects_data': False
    },
    0xC7: {
        'name': 'Chip Erase (0xC7)',
        'size': 1,
        'expects_data': False
    },
    0x60: {
        'name': 'Chip Erase (0x60)',
        'size': 1,
        'expects_data': False
    },
    0x05: {
        'name': 'Read Status Register-1 (0x05)',
        'size': 1,
        'expects_data': True
    },
    0x01: {
        'name': 'Read Status Register-1 (0x01)',
        'size': 1,
        'expects_data': True
    },
    0x35: {
        'name': 'Read Status Register-2 (0x35)',
        'size': 1,
        'expects_data': True
    },
    0x31: {
        'name': 'Read Status Register-2 (0x31)',
        'size': 1,
        'expects_data': True
    },
    0x15: {
        'name': 'Read Status Register-3 (0x15)',
        'size': 1,
        'expects_data': True
    },
    0x11: {
        'name': 'Read Status Register-3 (0x11',
        'size': 1,
        'expects_data': True
    },
    0x5A: {
        'name': 'Read SFDP Register',
        'size': 5,
        'expects_data': True
    },
    0x44: {
        'name': 'Erase Security Register',
        'size': 4,
        'expects_data': False
    },
    0x42: {
        'name': 'Program Security Register',
        'size': 6,
        'expects_data': False
    },
    0x48: {
        'name': 'Read Security Register',
        'size': 5,
        'expects_data': True
    },
    0x7E: {
        'name': 'Global Block Lock',
        'size': 1,
        'expects_data': False
    },
    0x98: {
        'name': 'Global Block Unlock',
        'size': 1,
        'expects_data': False
    },
    0x3D: {
        'name': 'Read Block Lock',
        'size': 4,
        'expects_data': True
    },
    0x36: {
        'name': 'Individual Block Lock',
        'size': 4,
        'expects_data': False
    },
    0x39: {
        'name': 'Individual Block Unlock',
        'size': 4,
        'expects_data': False
    },
    0x75: {
        'name': 'Erase / Program Suspend',
        'size': 1,
        'expects_data': False
    },
    0x7A: {
        'name': 'Erase / Program Resume',
        'size': 1,
        'expects_data': False
    },
    0xB9: {
        'name': 'Power-down',
        'size': 1,
        'expects_data': False
    },
    0x66: {
        'name': 'Enable Reset',
        'size': 1,
        'expects_data': False
    },
    0x99: {
        'name': 'Reset Device',
        'size': 1,
        'expects_data': False
    },
    0xEB: {
        'name': 'Fast Read Quad I/O',
        'size': 4,
        'expects_data': True
    },
    0xE7: {
        'name': 'Word Read Quad I/O',
        'size': 4,
        'expects_data': True
    },
    0xE3: {
        'name': 'Octal Word Read Quad I/O',
        'size': 4,
        'expects_data': True
    },
    0x94: {
        'name': 'Mftr./Device ID Quad I/O',
        'size': 4,
        'expects_data': True
    },
}


class ObligingArgumentParser(argparse.ArgumentParser):
    """ Display the full help message whenever there is something wrong with the arguments.
        (from https://groups.google.com/d/msg/argparse-users/LazV_tEQvQw/xJhBOm1qS5IJ) """
    def error(self, message):
        sys.stderr.write('Error: %s\n' % message)
        self.print_help()
        sys.exit(2)


# from https://stackoverflow.com/a/39358140
class RangeDict(dict):
    def __getitem__(self, item):
        if type(item) != range:
            for key in self:
                if item in key:
                    return self[key]
        else:
            return super().__getitem__(item)


def count_data_bytes(base_addr, s):
    """ Count bytes until the next instruction byte pops up, because that's the number of s bytes sent back on the
    (to us invisible) MISO channel. This is a necessary heuristic as we also do not have Chip Select (CS) data in the
    csv yet. """

    data_bytes = 1
    try:
        while (s[base_addr + data_bytes]
               not in WINBOND_INSTRUCTIONS.keys()):
            data_bytes += 1
    except IndexError:
        pass

    return data_bytes


def get_database(csvfile, psptool):
    database_file = csvfile + '.pickle'

    if os.path.exists(database_file):
        print('Info: Found existing database in %s.' % database_file)
        print('Info: Loading database ...')

        with open(database_file, 'rb') as f:
            data = pickle.load(f)

        # (imperfect) check if this database is complete and up to date
        if 'raw' in data and 'read_accesses' in data:
            print('Info: Loaded a capture of %d rows.' % len(data['raw']['time']))
            return data
        else:
            print('Info: Loaded database is incomplete or outdated!')

    print('Info: Creating database in %s ...' % database_file)

    with open(csvfile, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')

        # Case 1: This CSV export comes from the standard Saleae SPI analyzer
        if reader.fieldnames == ['Time [s]', 'Packet ID' , 'MOSI' , 'MISO'] or \
            reader.fieldnames == ['Time [s]', 'Packet ID' , 'MOSI']:

            data = {
                'raw': {
                    'time': [],
                    'packet_id': [],
                    'mosi': []
                },
                'read_accesses': None,
            }

            for row in reader:
                try:
                    data['raw']['time'].append(float(row['Time [s]']))
                    data['raw']['packet_id'].append(int(row['Packet ID']))
                    data['raw']['mosi'].append(int(row['MOSI'], 16))
                    #data['raw']['miso'].append(int(row['MISO'], 16))
                except ValueError:
                    pass

        # Case 2: This CSV export comes from the Quad SPI analyzer at https://github.com/dedicatedcomputing/saleae_qspi
        elif reader.fieldnames == ['Time [s]', 'Value']:
            data = {
                'raw': {
                    'time': [],
                    'value': []
                },
                'read_accesses': None,
            }

            for row in reader:
                try:
                    data['raw']['time'].append(float(row['Time [s]']))
                    data['raw']['value'].append(int(row['Value'], 16))
                except ValueError:
                    pass

    # convert timestamp from s to ns
    data['raw']['time'] = [int(t * 10 ** 9) for t in data['raw']['time']]

    # parse read accesses from the raw data
    data['read_accesses'] = find_read_accesses(data['raw'], psptool)

    with open(database_file, 'wb') as f:
        pickle.dump(data, f)

    print('Info: Parsed and stored a database of %d rows.' % len(data['raw']['time']))

    return data


def find_read_accesses(data, psptool):
    """ Build up data structure containing all (fast) read accesses """

    read_accesses = {}

    # use psptool to correlate addresses to firmware directory entries
    directories = [directory for rom in psptool.blob.roms for directory in rom.directories]
    directory_entries = [directory.entries for directory in directories]

    # flatten list of lists
    all_entries = [entry for sublist in directory_entries for entry in sublist]

    # add directory headers as entries, too
    # all_entries += [{
    #     'address': directory.get_address(),
    #     'size': directory.buffer_size,
    #     'type': 'Header: ' + str(directory.magic, 'ascii')
    # } for directory in directories]

    # create RangeDict in order to find entry types for addresses
    type_at_address_range = RangeDict({
        ** {
            range(entry.get_address(), entry.get_address() + entry.buffer_size):  # key is start and end address of the entry
            entry.type
            for entry in all_entries if entry.buffer_size != 0xffffffff  # value is its type
        }, ** {
            range(directory.get_address(), directory.get_address() + len(directory)):
            'Directory: ' + str(directory.magic, 'ascii')
            for directory in directories
        }, range(0x20000, 0x20040): 'Firmware Entry Table'
    })

    last_start_time = 0
    last_end_time = 0
    unparsable_instructions = {
        instr['name']: 0 for instr in WINBOND_INSTRUCTIONS.values()
    }
    invalid_instructions = {}
    index = 0
    last_index = 0
    instr_index = 0
    end_time = data['time'][index]

    # Case 1: This CSV export comes from the standard Saleae SPI analyzer
    if 'mosi' in data:
        while index < len(data['mosi']):
            instr = data['mosi'][index]

            if instr == 0x03 or instr == 0x0b:  # i.e. instruction 'Read data' or 'Fast Read'
                instr_size = WINBOND_INSTRUCTIONS[instr]['size']
                data_bytes = count_data_bytes(index + instr_size, data['mosi'])

                start_time = data['time'][index]
                end_time = data['time'][index + data_bytes]
                duration = end_time - start_time
                latency = start_time - last_end_time

                address = int.from_bytes(bytes(data['mosi'][index + 1:index + 4]), byteorder='big')
                size = data_bytes
                type_ = type_at_address_range[address]

                read_accesses[start_time] = {
                    'instr_index':  instr_index,
                    'start_time':   start_time,
                    'end_time':     end_time,
                    'duration':     duration,
                    'latency':      latency,
                    'address':      address,
                    'size':         size,
                    'type':         type_,
                    'info':         []
                }

                # skip forward
                last_end_time = end_time
                index += WINBOND_INSTRUCTIONS[instr]['size'] + data_bytes
                instr_index += 1

            elif instr in WINBOND_INSTRUCTIONS:  # i.e. unparsable instructions
                unparsable_instructions[WINBOND_INSTRUCTIONS[instr]['name']] += 1

                data_bytes = 0
                if WINBOND_INSTRUCTIONS[instr]['expects_data']:
                    instr_size = WINBOND_INSTRUCTIONS[instr]['size']
                    data_bytes = count_data_bytes(index + instr_size, data['mosi'])

                last_end_time = end_time
                index += WINBOND_INSTRUCTIONS[instr]['size'] + data_bytes
                instr_index += 1

            else:  # i.e. unknown/invalid instructions
                if instr in invalid_instructions:
                    invalid_instructions[instr] += 1
                else:
                    invalid_instructions[instr] = 0

                index += 1  # we assume an instr_size of 1 and no return data
                instr_index += 1

    # Case 2: This CSV export comes from the Quad SPI analyzer at https://github.com/dedicatedcomputing/saleae_qspi
    elif 'value' in data:
        while index < len(data['value']) - 1:
            value = data['value'][index]
            next_value = data['value'][index + 1]

            if value in [0x03, 0x0B, 0xEB, 0xE7, 0xE3, 0xEC] and next_value > 0xFF:  # normal and Quad IO Read commands
                    address = next_value

                    start_time = data['time'][index]

                    type_ = type_at_address_range[address]

                    if instr_index > 0:
                        # set the read size of the previous read access based on the number of non-instruction values
                        #  before and deduct the instruction and address packets
                        read_accesses[last_start_time]['size'] = index - last_index - 2
                        # todo: identify dummy cycles
                        previous_start_time = read_accesses[last_start_time]['start_time']
                        previous_last_end_time = read_accesses[last_start_time]['last_end_time']

                        previous_end_time = data['time'][index - 1]
                        previous_duration = previous_end_time - previous_start_time
                        previous_latency = previous_start_time - previous_last_end_time

                        read_accesses[last_start_time]['end_time'] = previous_end_time
                        read_accesses[last_start_time]['duration'] = previous_duration
                        read_accesses[last_start_time]['latency'] = previous_latency

                    read_accesses[start_time] = {
                        'instr_index': instr_index,
                        'start_time': start_time,
                        'last_end_time': last_end_time,
                        'address': address,
                        'type': type_,
                        'info': ['QSPI'] if value in [0xEB, 0xE7, 0xE3] else []
                    }

                    # skip forward
                    last_start_time = start_time
                    last_end_time = previous_end_time if instr_index > 0 else 0
                    last_index = index
                    index += 2  # one address packet and at least one dummy packet (it seems)
                    instr_index += 1
            else:
                index += 1

        # set the read size of the previous read access based on the number of non-instruction values
        #  before and deduct the instruction and address packets
        read_accesses[last_start_time]['size'] = index - last_index - 2
        # todo: identify dummy cycles
        previous_start_time = read_accesses[last_start_time]['start_time']
        previous_last_end_time = read_accesses[last_start_time]['last_end_time']

        previous_end_time = data['time'][index - 1]
        previous_duration = previous_end_time - previous_start_time
        previous_latency = previous_start_time - previous_last_end_time

        read_accesses[last_start_time]['end_time'] = previous_end_time
        read_accesses[last_start_time]['duration'] = previous_duration
        read_accesses[last_start_time]['latency'] = previous_latency

    return read_accesses


"""
Data post-processing functions
"""


MAXIMUM_AGGREGATION_COUNT = 8  # todo: this comes from the number of PSPs – parametrize this somehow
TIME_BLOCK_LATENCY_THRESHOLD = 50  # microseconds


def aggregate_duplicates(read_accesses):
    """ Aggregate read accesses if they have the same address and size. In most cases, this comes from the fact that
     a multiprocessor or multicore system has more than one PSP (more precisely: no. of CCX PSPs) accessing the SPI
     simultaneously. """

    aggregated_accesses = read_accesses.copy()

    # Buffer recent addresses and the time of first occurrence
    # todo: find out if maxlen is reasonable
    recent_addresses = deque([], maxlen=200)
    recent_originals = deque([], maxlen=200)

    for time, values in sorted(read_accesses.items()):
        address = values['address']

        if address not in recent_addresses:
            aggregated_accesses[time].update({
                'duplicate_count': 1
            })

            recent_addresses.append(address)
            recent_originals.append(time)

        else:  # if address in recent_addresses
            index = recent_addresses.index(address)
            original_access_time = recent_originals[index]

            if aggregated_accesses[original_access_time]['duplicate_count'] < MAXIMUM_AGGREGATION_COUNT:
                aggregated_accesses[original_access_time]['duplicate_count'] += 1
            else:
                del recent_addresses[index]
                del recent_originals[index]

            # aggregated_accesses[original_access_time]['size'] += max(
            #     values['size'], aggregated_accesses[original_access_time]['size']
            # )

            del aggregated_accesses[time]

    for time, values in aggregated_accesses.items():
        # add a note about its aggregation
        # todo: extract this to a display function
        aggregated_accesses[time]['info'].append('x%d' % aggregated_accesses[time]['duplicate_count'])

    return aggregated_accesses


def collapse_entry_types(read_accesses):
    """ Aggregate ("collapse") consecutive read accesses to the same firmware entry (i.e. psptool's type). """

    # get a sorted list of dicts by key (i.e. start_time)
    read_accesses = sorted(read_accesses.items())
    collapsed_read_accesses = []

    last_access = {
        'type': None,
        'address': None,
        'size': None,
        'duplicate_count': None
    }

    for time, values in read_accesses:
        if (last_access['address'] is not None
                # only collapse accesses of the same type (e.g. PSP_FW_BOOT_LOADER)
                and values['type'] == last_access['type']
                # sometimes consecutive reads fetch a few bytes too much, so we also accept "overreads" (thus <=)
                and values['address'] <= last_access['address'] + last_access['size']):

            prev_values = collapsed_read_accesses[-1]
            collapsed_read_accesses[-1] = {
                'instr_index':  prev_values['instr_index'],
                'start_time':   prev_values['start_time'],
                'end_time':     values['end_time'],
                'duration':     prev_values['duration'] + values['duration'],
                'latency':      prev_values['latency'],
                'address':         prev_values['address'],
                'size':         prev_values['size'] + values['size'],
                'type':         prev_values['type'],
                'info':         prev_values['info']
            }

            if '[c]' not in collapsed_read_accesses[-1]['info']:
                collapsed_read_accesses[-1]['info'].append('[c]')

            # we don't require the same multiplicity (e.g. x8) of the collapsed rows, so append a warning if necessary
            if (values.get('duplicate_count') != last_access['duplicate_count']
                    and '~' not in collapsed_read_accesses[-1]['info']):

                collapsed_read_accesses[-1]['info'].append('~')

        else:
            collapsed_read_accesses.append(values)

        last_access = {
            'type': values['type'],
            'address': values['address'],
            'size': values['size'],
            'duplicate_count': values.get('duplicate_count')  # this may be missing (=> None)
        }

    # convert the list of dicts back to a dict
    return {values['start_time']: values for values in collapsed_read_accesses}


def do_normalize_timestamps(read_accesses):
    normalized_read_accesses = {}
    min_time = min((v['start_time'] for v in read_accesses.values()))

    for k, v in read_accesses.items():
        v['start_time'] -= min_time
        v['end_time'] -= min_time
        normalized_read_accesses[k] = v

    return normalized_read_accesses


"""
IO functions
"""


def get_overview_read_accesses(read_accesses):
    entry_types = Entry.DIRECTORY_ENTRY_TYPES
    overview_read_accesses = {}
    known_types = {}  # dict of (type, is_ccp) and original_access_time

    # step 1: take read_accesses chronologically and reduce them into overview_read_accesses
    for start_time, values in sorted(read_accesses.items()):
        latency_in_us = values['latency'] // 1000
        is_ccp = True if 'CCP' in values['info'] else False

        # reset known types when we are in a new time block
        if latency_in_us > TIME_BLOCK_LATENCY_THRESHOLD:
            known_types = {}

        if (values['type'], is_ccp) not in known_types:
            known_types[(values['type'], is_ccp)] = start_time

            overview_read_accesses[start_time] = {
                **values,
                'lowest_access': values['address'],
                'highest_access': values['address'] + values['size']
            }
        else:
            original_access_time = known_types[(values['type'], is_ccp)]

            lowest_access = overview_read_accesses[original_access_time]['lowest_access']
            overview_read_accesses[original_access_time]['lowest_access'] = min(lowest_access, values['address'])

            highest_access = overview_read_accesses[original_access_time]['highest_access']
            overview_read_accesses[original_access_time]['highest_access'] = max(highest_access,
                                                                                 values['address'] + values['size'])
    return overview_read_accesses


class PSPTrace:
    def __init__(self, csvfile, romfile, limit_rows=None):
        self.psptool = PSPTool.from_file(romfile)

        data = get_database(csvfile, self.psptool)
        self.read_accesses = data['read_accesses']

        if limit_rows:
            self.read_accesses = {k: v for k, v in sorted(self.read_accesses.items())[:limit_rows]}

        # annotate reads of size 0x40 with 'CCP' (heuristic!)
        for k, v in self.read_accesses.items():
            if v['size'] == 0x40:
                v['info'].append('CCP')

    def display_overview(self, verbose=False):
        entry_types = Entry.DIRECTORY_ENTRY_TYPES
        basic_fields = ['No.', 'Lowest access', 'Range', 'Type', 'Info']
        verbose_fields = ['Start [ns]', 'Highest access']
        all_fields = basic_fields + verbose_fields

        t = PrettyTable(all_fields)
        overview_read_accesses = get_overview_read_accesses(self.read_accesses)

        for k, v in sorted(overview_read_accesses.items()):
            size = v['highest_access'] - v['lowest_access']

            # Improve output of type # todo: remove code duplicate
            if v['type'] is None:
                v['type'] = 'Unknown area'
            elif v['type'] in entry_types:
                v['type'] = entry_types[v['type']]
            elif type(v['type']) == int:
                v['type'] = hex(v['type'])

            # todo: remove duplicate code here

            # Display significant latencies
            latency_in_us = v['latency'] // 1000

            if latency_in_us > TIME_BLOCK_LATENCY_THRESHOLD:
                t.add_row([''] * 7)
                t.add_row([''] * 3 + ['~ %d µs delay ~' % latency_in_us] + [''] * 3)
                t.add_row([''] * 7)

            v['info'] = ' '.join(v['info'])
            basic_values = [v['instr_index'], '0x%.6x' % v['lowest_access'], '0x%.6x' % size, v['type'], v['info']]
            verbose_values = [v['start_time'], '0x%.6x' % v['highest_access']]

            t.add_row(basic_values + verbose_values)

        fields = basic_fields

        if verbose:
            fields += verbose_fields

        print(t.get_string(fields=fields))

    def display_all(self, no_duplicates=False, collapse=False, normalize_timestamps=False, verbose=False):
        read_accesses = self.read_accesses
        if no_duplicates:
            read_accesses = aggregate_duplicates(read_accesses)
        if collapse:
            read_accesses = collapse_entry_types(read_accesses)
        if normalize_timestamps:
            read_accesses = do_normalize_timestamps(read_accesses)

        # display results
        basic_fields = ['No.', 'Address', 'Size', 'Type', 'Info']
        verbose_fields = ['Start [ns]', 'End [ns]', 'Duration [ns]', 'Latency [ns]']
        all_fields = basic_fields + verbose_fields
        all_keys = ['instr_index', 'address', 'size', 'type', 'info', 'start_time', 'end_time', 'duration', 'latency']

        t = PrettyTable(all_fields)
        t.align['Info'] = 'l'
        t.align['Start [ns]'] = 'r'
        t.align['End [ns]'] = 'r'
        t.align['Duration [ns]'] = 'r'
        t.align['Latency [ns]'] = 'r'

        entry_types = Entry.DIRECTORY_ENTRY_TYPES

        for start_time, values in sorted(read_accesses.items()):
            # Improve output of type
            if values['type'] is None:
                values['type'] = 'Unknown area'
            elif values['type'] in entry_types:
                values['type'] = entry_types[values['type']]
            elif type(values['type']) == int:
                values['type'] = hex(values['type'])

            values['info'] = ' '.join(values['info'])
            latency_in_us = values['latency'] // 1000

            # Display significant latencies
            if latency_in_us > TIME_BLOCK_LATENCY_THRESHOLD:
                t.add_row([''] * 9)
                t.add_row([''] * 3 + ['~ %d µs delay ~' % latency_in_us] + [''] * 5)
                t.add_row([''] * 9)

            values['size'] = '0x%.2x' % values['size']
            values['address'] = '0x%.6x' % values['address']

            t.add_row([values.get(key) for key in all_keys])

        # See which fields are actually demanded (depending on -v)
        fields = basic_fields

        if verbose:
            fields += verbose_fields

        print(t.get_string(fields=fields))


def main():
    # Ignore SIG_PIPE and don't throw exceptions on it
    # http://docs.python.org/library/signal.html
    signal(SIGPIPE, SIG_DFL)

    parser = ObligingArgumentParser(description='Read in an SPI capture created by a Saleae Logic Analyzer and a ROM '
                                                'file resembling the flash contents and display an access chronology. '
                                                'On first load, psptrace needs to parse a lot of raw data which will '
                                                'be saved on disk. All other loads will then be much faster.')
    parser.add_argument('csvfile', help='CSV file of SPI capture', nargs='?')
    parser.add_argument('romfile', help='ROM file of SPI contents', nargs='?')
    parser.add_argument('-o', '--overview-mode', help='aggregate accesses to the same firmware entry',
                        action='store_true')
    parser.add_argument('-n', '--no-duplicates', help='hide duplicate accesses (e.g. caused by multiple PSPs)',
                        action='store_true')
    parser.add_argument('-c', '--collapse', help='collapse consecutive reads to the same PSP entry type (denoted by '
                                                 '[c] and sometimes by ~ if collapsing was fuzzy)',
                        action='store_true')
    parser.add_argument('-t', '--normalize-timestamps', help='normalize all timestamps', action='store_true')
    parser.add_argument('-l', '--limit-rows', help='limit the processed rows to a maximum of n', type=int)
    parser.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')
    parser.add_argument('-V', '--version', action='store_true')

    args = parser.parse_args()

    if args.version:
        print(pkg_resources.get_distribution("psptrace").version)
        sys.exit(0)
    elif not args.csvfile or not args.romfile:
        parser.print_help(sys.stderr)
        sys.exit(0)

    psptrace = PSPTrace(args.csvfile, args.romfile, limit_rows=args.limit_rows)

    if args.overview_mode:
        psptrace.display_overview(verbose=args.verbose)
    else:
        psptrace.display_all(no_duplicates=args.no_duplicates, collapse=args.collapse,
                             normalize_timestamps=args.normalize_timestamps, verbose=args.verbose)


if __name__ == '__main__':
    main()
