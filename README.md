# PSPTrace

PSPTrace can be used to **correlate an SPI capture** of an **AMD boot procedure** recorded with a Saleae Logic analyzer to the **PSP firmware** of a UEFI image. 

SPI captures must be exported from the Saleae Logic software via *Analyzers > SPI > Export as text/csv file*. Please make sure you sampled with an appropriate sample rate and the SPI analyzer is set to `Hex`.

PSPTrace requires [PSPTool](https://github.com/PSPReverse/PSPTool) to be installed.

```
$ python3 psptrace.py
Error: the following arguments are required: csvfile, romfile
usage: psptrace.py [-h] [-o] [-n] [-c] [-t] [-l LIMIT_ROWS] [-v] csvfile romfile

Read in an SPI capture created by a Saleae Logic Analyzer and a ROM file resembling the flash contents and display an access
chronology. On first load, psptrace needs to parse a lot of raw data which will be saved on disk. All other loads will then be
much faster.

positional arguments:
  csvfile               CSV file of SPI capture
  romfile               ROM file of SPI contents

optional arguments:
  -h, --help            show this help message and exit
  -o, --overview-mode   aggregate accesses to the same firmware entry
  -n, --no-duplicates   hide duplicate accesses (e.g. caused by multiple PSPs)
  -c, --collapse        collapse consecutive reads to the same PSP entry type (denoted by [c] and sometimes by ~ if collapsing
                        was fuzzy)
  -t, --normalize-timestamps
                        normalize all timestamps
  -l LIMIT_ROWS, --limit-rows LIMIT_ROWS
                        limit the processed rows to a maximum of n
  -v, --verbose         increase output verbosity
```

## Example usage

After recording the boot procedure of a Supermicro server system with an AMD Epyc CPU, PSPTrace outputs the following boot in overview mode (`-o`):

```
$ psptrace -o spi_trace.txt flash.bin

Info: Creating database in spi_trace.txt.pickle ...
Info: Parsed and stored a database of 14028942 rows.
+---------+---------------+----------+-----------------------------+------+
|   No.   | Lowest access |  Range   |             Type            | Info |
+---------+---------------+----------+-----------------------------+------+
|    0    |    0x820000   | 0x780007 |         Unknown area        |      |
|    22   |    0x020000   | 0x00001c |     Firmware Entry Table    |      |
|    33   |    0x077000   | 0x00012a |       Directory: $PSP       |      |
|    70   |    0x077000   | 0x000100 |       Directory: $PSP       | CCP  |
|   107   |    0x077400   | 0x000240 |        AMD_PUBLIC_KEY       | CCP  |
|   177   |    0x149400   | 0x00d780 |      PSP_FW_BOOT_LOADER     | CCP  |
|         |               |          |                             |      |
|         |               |          |      ~ 3410 µs delay ~      |      |
|         |               |          |                             |      |
|   7084  |    0x149000   | 0x000180 |       Directory: $PL2       | CCP  |
|   7090  |    0x000000   | 0x020046 |         Unknown area        |      |
|   7091  |    0x020000   | 0x000024 |     Firmware Entry Table    |      |
|         |               |          |                             |      |
|         |               |          |       ~ 66 µs delay ~       |      |
|         |               |          |                             |      |
|   7095  |    0x117000   | 0x000160 |       Directory: $BHD       |      |
|   7096  |    0x149000   | 0x000152 |       Directory: $PL2       |      |
|   7554  |    0x000000   | 0x117280 |         Unknown area        |      |
|   7581  |    0x020000   | 0x000022 |     Firmware Entry Table    |      |
|   7859  |    0x249000   | 0x0001c0 |       Directory: $BL2       | CCP  |
|   7880  |    0x1170c0   | 0x000080 |       Directory: $BHD       | CCP  |
|   7909  |    0x2491c0   | 0x000240 |         Unknown area        | CCP  |
|   8017  |    0x249010   | 0x00019a |       Directory: $BL2       |      |
|   8560  |    0x17c100   | 0x001932 |         DEBUG_UNLOCK        |      |
|   8939  |    0x17c200   | 0x001800 |         DEBUG_UNLOCK        | CCP  |
|  10144  |    0x177a00   | 0x0001c0 |      SEC_DBG_PUBLIC_KEY     |      |
|  10576  |    0x177bc0   | 0x000180 |      SEC_DBG_PUBLIC_KEY     | CCP  |
|         |               |          |                             |      |
|         |               |          |       ~ 178 µs delay ~      |      |
|         |               |          |                             |      |
|  10582  |    0x17e000   | 0x000080 |         TOKEN_UNLOCK        | CCP  |

[...]
```

