#!C:\Project\nktc\Scripts\python.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'flake8==2.0','console_scripts','flake8'
__requires__ = 'flake8==2.0'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('flake8==2.0', 'console_scripts', 'flake8')()
    )
