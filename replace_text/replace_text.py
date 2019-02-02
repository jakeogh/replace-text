#!/usr/bin/env python3
'''
# Replace the given text in file(s) or stdin.
'''
import click
import sys
import shutil
import tempfile
import os


@click.argument("match", nargs=1)
@click.argument("replacement", nargs=1)
@click.argument("files", nargs=-1, required=False)
def replace_text(match, replacement, files):
    if not files:
        for line in sys.stdin:
            print(line.replace(match, replacement), end='')

    for file_to_modify in files:
        file_to_modify_basename = os.path.basename(file_to_modify)
        file_to_modify_dir = os.path.dirname(file_to_modify)
        temp_file_name_suffix = '-' + file_to_modify_basename + '.tmp'
        temp_file = tempfile.NamedTemporaryFile(mode='w',
                                                suffix=temp_file_name_suffix,
                                                prefix='tmp-',
                                                dir=file_to_modify_dir,
                                                delete=False)

        with open(file_to_modify, 'rU') as file_to_modify_fh:
            try:
                for line in file_to_modify_fh:
                    new_line = line.replace(match, replacement).rstrip()
                    if file_to_modify_fh.newlines == '\n':      # LF (Unix)
                        temp_file.write("%s\n" % new_line)
                        continue
                    elif file_to_modify_fh.newlines == '\r\n':  # CR+LF (DOS/Win)
                        temp_file.write("%s\r\n" % new_line)
                        continue
                    elif file_to_modify_fh.newlines == '\r':    # CR (Mac OS <= v9)
                        temp_file.write("%s\r" % new_line)
            except UnicodeDecodeError as e:
                print("UnicodeDecodeError:", file_to_modify)
                raise e

            temp_file_name = temp_file.name
            temp_file.close()
            shutil.copystat(file_to_modify, temp_file_name)
            shutil.move(temp_file_name, file_to_modify)


if __name__ == '__main__':
    replace_text()
