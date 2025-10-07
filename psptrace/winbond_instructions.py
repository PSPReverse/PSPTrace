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
    0x13: {
        'name': 'Read Data with 4-Byte Address',
        'size': 5,
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
