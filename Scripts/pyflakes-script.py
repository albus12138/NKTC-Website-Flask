#!C:\Project\nktc\Scripts\python.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'pyflakes==0.7.3','console_scripts','pyflakes'
__requires__ = 'pyflakes==0.7.3'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('pyflakes==0.7.3', 'console_scripts', 'pyflakes')()
    )
