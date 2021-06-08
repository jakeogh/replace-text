#!/usr/bin/env python3
'''
# Replace the given text in file(s) or stdin.
'''

# pylint: disable=C0111     # docstrings are always outdated and wrong
# pylint: disable=W0511     # todo is encouraged
# pylint: disable=C0301     # line too long
# pylint: disable=R0902     # too many instance attributes
# pylint: disable=C0302     # too many lines in module
# pylint: disable=C0103     # single letter var names, func name too descriptive
# pylint: disable=R0911     # too many return statements
# pylint: disable=R0912     # too many branches
# pylint: disable=R0915     # too many statements
# pylint: disable=R0913     # too many arguments
# pylint: disable=R1702     # too many nested blocks
# pylint: disable=R0914     # too many local variables
# pylint: disable=R0903     # too few public methods
# pylint: disable=E1101     # no member for base
# pylint: disable=W0201     # attribute defined outside __init__


import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

#from icecream import ic  # too many deps
import click
from asserttool import maxone
from colorama import Fore
from colorama import Style

#note adding deps requires changes to sendgentoo


def eprint(*args, **kwargs):
    if 'file' in kwargs.keys():
        kwargs.pop('file')
    print(*args, file=sys.stderr, **kwargs)


try:
    from icecream import ic  # https://github.com/gruns/icecream
except ImportError:
    ic = eprint


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
    yield p.absolute()
    for sub in p.iterdir():
        # eprint("sub:", sub)  # todo: read by terminal, so bell etc happens.... eprint bug?
        if sub.is_symlink():  # must be before is_dir()
            yield sub.absolute()
        elif sub.is_dir():
            yield from all_files_iter(sub)
        else:
            yield sub.absolute()


def replace_text_line(*,
                      file_to_modify: Path,
                      match: str,
                      replacement: str,
                      verbose: bool,
                      debug: bool,
                      ):

    assert isinstance(file_to_modify, Path)
    if verbose:
        eprint(file_to_modify)

    #file_to_modify_basename = os.path.basename(file_to_modify)
    file_to_modify_dir = os.path.dirname(file_to_modify)
    temp_file = tempfile.NamedTemporaryFile(mode='w',
                                            prefix='tmp-',
                                            dir=file_to_modify_dir,
                                            delete=False)

    # this cant handle binary files... or files with mixed newlines
    modified = False
    with open(file_to_modify, 'rU') as file_to_modify_fh:
        try:
            for line in file_to_modify_fh:
                if match in line:
                    modified = True
                new_line = line.replace(match, replacement)
                temp_file.write(new_line)
                #if file_to_modify_fh.newlines == '\n':      # LF (Unix)
                #    temp_file.write("%s\n" % new_line)
                #    continue
                #elif file_to_modify_fh.newlines == '\r\n':  # CR+LF (DOS/Win)
                #    temp_file.write("%s\r\n" % new_line)
                #    continue
                #elif file_to_modify_fh.newlines == '\r':    # CR (Mac OS <= v9)
                #    temp_file.write("%s\r" % new_line)
        except UnicodeDecodeError as e:
            print("UnicodeDecodeError:", file_to_modify, file=sys.stderr)
            raise e

        temp_file_name = temp_file.name
        temp_file.close()
        if modified:
            shutil.copystat(file_to_modify, temp_file_name)
            shutil.move(temp_file_name, file_to_modify)
        else:
            os.unlink(temp_file_name)


def replace_text_bytes(*,
                       file_to_modify: Path,
                       match: bytes,
                       replacement: bytes,
                       verbose: bool,
                       debug: bool,
                       ):

    assert isinstance(file_to_modify, Path)
    if verbose:
        ic(file_to_modify)

    assert isinstance(match, bytes)
    assert isinstance(replacement, bytes)

    window_size = len(match) # need to expand a matching block by an arb amount, replacement can be any size

    #file_to_modify_basename = os.path.basename(file_to_modify)
    file_to_modify_dir = os.path.dirname(file_to_modify)
    temp_file = tempfile.NamedTemporaryFile(mode='wb',
                                            prefix='tmp-',
                                            dir=file_to_modify_dir,
                                            delete=False)

    # this cant handle binary files... or files with mixed newlines
    modified = False
    location_read = 0
    location_write = 0
    with open(file_to_modify, 'rb') as fh:
        while True:
            fh.seek(location_read)
            location_read += 1
            window = fh.read(window_size)

            #ic(len(window))
            print('\n')
            eprint('match :', repr(match))
            eprint('window:', repr(window))
            #ic(window)
            if not window:
                break
            if match in window:
                window = window.split(match)
                window = replacement.join(window)
                modified = True
            temp_file.write(bytes([window[0]]))

        temp_file_name = temp_file.name
        temp_file.close()
        if modified:
            shutil.copystat(file_to_modify, temp_file_name)
            shutil.move(temp_file_name, file_to_modify)
        else:
            os.unlink(temp_file_name)

        ic(modified)

def replace_text(file_to_modify: Path,
                 match,
                 replacement,
                 verbose: bool,
                 debug: bool,
                 ):

    if isinstance(match, bytes):
        replace_text_bytes(file_to_modify=file_to_modify,
                           match=match,
                           replacement=replacement,
                           verbose=verbose,
                           debug=debug,
                           )
    else:
        replace_text_line(file_to_modify=file_to_modify,
                          match=match,
                          replacement=replacement,
                          verbose=verbose,
                          debug=debug,
                          )


def get_thing(*,
              prompt: str,
              match: str,
              match_file: str,
              ask: bool,
              verbose: bool,
              debug: bool,
              ):

    result = None
    assert prompt in ['match', 'replacement']
    if not maxone([match, match_file, ask]):
        raise ValueError('--{0} --{0}-file and --ask-{0} are mutually exclusive'.format(prompt))
    if match:
        assert len(match) > 0
        result = match
    if match_file:
        match_file = Path(match_file)
        with open(match_file.as_posix(), 'rb') as fh:
            file_bytes = fh.read()
        assert len(file_bytes) > 0
        #result = file_bytes.decode('utf8')
        result = file_bytes
    if ask:
        match = input(prompt)
        assert len(match) > 0
        result = match

    if result:
        if verbose:
            ic(result)
        return result

    raise ValueError('one of --{0} --{0}-file or --ask-{0} is required'.format(prompt))



@click.command()
@click.argument("files", nargs=-1, required=False)
@click.option("--match", type=str)
@click.option("--replacement", type=str)
@click.option('--match-file', type=str)
@click.option('--replacement-file', type=str)
@click.option('--recursive', '-r', is_flag=True)
@click.option('--endswith', type=str)
@click.option('--recursive-dotfiles', '-d', is_flag=True)
@click.option('--verbose', is_flag=True)
@click.option('--debug', is_flag=True)
@click.option('--ask-match', is_flag=True, help="escape from shell escaping")
@click.option('--ask-replacement', is_flag=True, help="escape from shell escaping")
def cli(files,
        match,
        replacement,
        match_file,
        replacement_file,
        recursive,
        recursive_dotfiles,
        endswith,
        verbose,
        debug,
        ask_match,
        ask_replacement,
        ):

    match = get_thing(prompt='match',
                      match=match,
                      match_file=match_file,
                      ask=ask_match,
                      verbose=verbose,
                      debug=debug,)

    replacement = get_thing(prompt='replacement',
                            match=replacement,
                            match_file=replacement_file,
                            ask=ask_replacement,
                            verbose=verbose,
                            debug=debug,)


    if isinstance(match, bytes):
        assert isinstance(replacement, bytes)

    if not files:  # todo: enumerate_input
        for line in sys.stdin:
            print(line.replace(match, replacement), end='')

    files = list(files)

    for file_to_modify in files:
        if verbose:
            ic(file_to_modify)
        if endswith:
            if not file_to_modify.endswith(endswith):
                continue
        if os.path.isdir(file_to_modify):
            if not recursive:
                print("Warning: skipping folder:",
                      file_to_modify,
                      "specify --recursive to decend into it.", file=sys.stderr)
                continue

            for sub_file in all_files_iter(file_to_modify):
                if is_regular_file(sub_file):
                    if '.' in os.fsdecode(sub_file.parent):
                        if not recursive_dotfiles:
                            if verbose:
                                eprint("skipping:", sub_file, "due to dot '.' in parent")
                            continue
                    replace_text(file_to_modify=Path(sub_file),
                                 match=match,
                                 replacement=replacement,
                                 verbose=verbose,
                                 debug=debug,)

        else:
            if is_regular_file(file_to_modify):
                try:
                    replace_text(file_to_modify=Path(file_to_modify),
                                 match=match,
                                 replacement=replacement,
                                 verbose=verbose,
                                 debug=debug,)
                except UnicodeDecodeError:
                    pass
