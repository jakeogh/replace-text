#!/usr/bin/env python3
'''
# Replace the given text in file(s) or stdin.
'''
import click
import sys
import shutil
import tempfile
import os
import stat
from pathlib import Path


def is_regular_file(path):
    mode = os.stat(path, follow_symlinks=False)[stat.ST_MODE]
    if stat.S_ISREG(mode):
        return True
    return False


def all_files_iter(p):
    if isinstance(p, str):
        p = Path(p)
    elif isinstance(p, bytes):
        p = Path(p.decode())
    assert isinstance(p, Path)
    yield bytes(p.absolute())
    for sub in p.iterdir():
        # eprint("sub:", sub)  # todo: read by terminal, so bell etc happens.... eprint bug?
        if sub.is_symlink():  # must be before is_dir()
            yield bytes(sub.absolute())
        elif sub.is_dir():
            yield from all_files_iter(sub)
        else:
            yield bytes(sub.absolute())


def modify_file(file_to_modify, match, replacement, verbose):
    if verbose:
        print(file_to_modify, file=sys.stderr)

    if isinstance(file_to_modify, str):
        file_to_modify = file_to_modify.encode('utf8')
    file_to_modify_basename = os.path.basename(file_to_modify)
    file_to_modify_dir = os.path.dirname(file_to_modify)
    temp_file_name_suffix = b'-' + file_to_modify_basename + b'.tmp'
    temp_file = tempfile.NamedTemporaryFile(mode='w',
                                            suffix=temp_file_name_suffix,
                                            prefix=b'tmp-',
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
            print("UnicodeDecodeError:", file_to_modify, file=sys.stderr)
            raise e

        temp_file_name = temp_file.name
        temp_file.close()
        shutil.copystat(file_to_modify, temp_file_name)
        shutil.move(temp_file_name, file_to_modify)


@click.command()
@click.argument("match", nargs=1, required=False)
@click.argument("replacement", nargs=1, required=False)
@click.argument("files", nargs=-1, required=False)
@click.option('--recursive', '-r', is_flag=True)
@click.option('--recursive-dotfiles', '-d', is_flag=True)
@click.option('--verbose', '-v', is_flag=True)
@click.option('--ask', is_flag=True, help="escape from shell escaping")
def replace_text(match, replacement, files, recursive, recursive_dotfiles, verbose, ask):
    if match:
        assert replacement
    else:
        assert ask
        match = input("match: ")
        replacement = input("replacement: ")
    if not files:
        for line in sys.stdin:
            print(line.replace(match, replacement), end='')

    files = list(files)

    for file_to_modify in files:
        if os.path.isdir(file_to_modify):
            if not recursive:
                print("Warning: skipping folder:", file_to_modify, "specify --recursive to decend into it.", file=sys.stderr)
                continue

            for sub_file in all_files_iter(file_to_modify):
                if is_regular_file(sub_file):
                    modify_file(file_to_modify=sub_file, match=match, replacement=replacement, verbose=verbose)
        else:
            if is_regular_file(file_to_modify):
                modify_file(file_to_modify=file_to_modify, match=match, replacement=replacement, verbose=verbose)


if __name__ == '__main__':
    replace_text()
