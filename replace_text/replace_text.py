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
from asserttool import nevd
from asserttool import nl_iff_tty
from colorama import Fore
from colorama import Style
from enumerate_input import enumerate_input

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
                      path: Path,
                      match: str,
                      replacement: str,
                      verbose: bool,
                      debug: bool,
                      ):

    match_count = 0
    assert isinstance(path, Path)
    if verbose:
        eprint(path)

    #path_basename = os.path.basename(path)
    path_dir = os.path.dirname(path)
    temp_file = tempfile.NamedTemporaryFile(mode='w',
                                            prefix='tmp-',
                                            dir=path_dir,
                                            delete=False)

    # this cant handle binary files... or files with mixed newlines
    modified = False
    with open(path, 'rU') as path_fh:
        try:
            for line in path_fh:
                if match in line:
                    modified = True
                    match_count += 1
                if replacement:
                    new_line = line.replace(match, replacement)
                    temp_file.write(new_line)
                    #if path_fh.newlines == '\n':      # LF (Unix)
                    #    temp_file.write("%s\n" % new_line)
                    #    continue
                    #elif path_fh.newlines == '\r\n':  # CR+LF (DOS/Win)
                    #    temp_file.write("%s\r\n" % new_line)
                    #    continue
                    #elif path_fh.newlines == '\r':    # CR (Mac OS <= v9)
                    #    temp_file.write("%s\r" % new_line)
        except UnicodeDecodeError as e:
            print("UnicodeDecodeError:", path, file=sys.stderr)
            raise e

        temp_file_name = temp_file.name
        temp_file.close()
        if modified:
            shutil.copystat(path, temp_file_name)
            shutil.move(temp_file_name, path)
        else:
            os.unlink(temp_file_name)

        return match_count


def replace_text_bytes(*,
                       path: Path,
                       match: bytes,
                       replacement: bytes,
                       verbose: bool,
                       debug: bool,
                       ):

    assert isinstance(path, Path)
    if verbose:
        ic(path)

    assert isinstance(match, bytes)
    if replacement:
        assert isinstance(replacement, bytes)

    window_size = len(match) # need to expand a matching block by an arb amount, replacement can be any size

    #path_basename = os.path.basename(path)
    path_dir = os.path.dirname(path)
    temp_file = tempfile.NamedTemporaryFile(mode='wb',
                                            prefix='tmp-',
                                            dir=path_dir,
                                            delete=False)

    # this cant handle binary files... or files with mixed newlines
    modified = False
    location_read = 0
    match_count = 0
    #location_write = 0
    window = []
    with open(path, 'rb') as fh:
        while True:
            # window starts off empty
            if verbose:
                eprint(len(match), len(window), location_read)
            fh.seek(location_read)
            next_byte = fh.read(1)
            if verbose:
                ic(next_byte)
            if next_byte == b'':
                break

            window.append(next_byte)
            location_read += 1
            # first byte in window, or EOF

            #ic(b''.join(window))

            if len(window) < len(match):
                # keep filling the window
                continue

            # window is too big
            if (len(window) - 1) == len(match):     # window needs to move
                temp_file.write(window[0])
                window = window[1:]
                assert len(window) == window_size   # only time window_size is used

            # if it's possible to do a match, see if there is one
            if len(window) == len(match):
                #ic(len(window))
                if verbose:
                    print('\n')
                    eprint('match :', repr(match))
                    eprint('window:', repr(b''.join(window)))
                #ic(window)
                # if there is a match, we know the whole window gets replaced, =>< the current window
                if b''.join(window) == match:
                    eprint("matched")
                    match_count += 1
                    if replacement:
                        window = replacement
                        ic(window)
                        modified = True
                        temp_file.write(window)  # flush the replacement to disk
                        window = []  # start a new window, dont want to match on the replacement

                    continue
                # here the window was full, but it did not match, so the window must be shifted by one byte, and the byte that fell off must be written


            assert len(window) <= len(match)

        ic('broke', modified)

        temp_file_name = temp_file.name
        temp_file.close()
        if modified:
            shutil.copystat(path, temp_file_name)
            shutil.move(temp_file_name, path)
        else:
            os.unlink(temp_file_name)

        ic(modified)
        return match_count


def replace_text(path: Path,
                 match,
                 replacement,
                 verbose: bool,
                 debug: bool,
                 ):

    if isinstance(match, bytes):
        match_count = \
            replace_text_bytes(path=path,
                               match=match,
                               replacement=replacement,
                               verbose=verbose,
                               debug=debug,
                               )
    else:
        match_count = \
            replace_text_line(path=path,
                              match=match,
                              replacement=replacement,
                              verbose=verbose,
                              debug=debug,
                              )
    return match_count


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
@click.option('--printn', is_flag=True)
@click.option('--paths', is_flag=True)
@click.option('--ask-match', is_flag=True, help="escape from shell escaping")
@click.option('--ask-replacement', is_flag=True, help="escape from shell escaping")
@click.pass_context
def cli(ctx,
        files,
        match: str,
        replacement: str,
        match_file: str,
        replacement_file: str,
        recursive: bool,
        recursive_dotfiles: bool,
        endswith: str,
        verbose: bool,
        debug: bool,
        printn: bool,
        paths: bool,
        ask_match: bool,
        ask_replacement: bool,
        ):

    match = get_thing(prompt='match',
                      match=match,
                      match_file=match_file,
                      ask=ask_match,
                      verbose=verbose,
                      debug=debug,)

    if (replacement or replacement_file or ask_replacement):
        replacement = get_thing(prompt='replacement',
                                match=replacement,
                                match_file=replacement_file,
                                ask=ask_replacement,
                                verbose=verbose,
                                debug=debug,)

    ctx.ensure_object(dict)
    null, end, verbose, debug = nevd(ctx=ctx,
                                     printn=printn,
                                     ipython=False,
                                     verbose=verbose,
                                     debug=debug,)

    match_count = 0
    iterator = files

    if paths:
        for index, path in enumerate_input(iterator=iterator,
                                           null=null,
                                           progress=False,
                                           skip=None,
                                           head=None,
                                           tail=None,
                                           debug=debug,
                                           verbose=verbose,):
            path = Path(path)

            if verbose:
                ic(index, path)

            path = Path(path).resolve()
            if verbose:
                ic(path)
            if endswith:
                if not path.endswith(endswith):
                    continue
            if os.path.isdir(path):
                if not recursive:
                    print("Warning: skipping folder:",
                          path,
                          "specify --recursive to decend into it.", file=sys.stderr)
                    continue

                for sub_file in all_files_iter(path):
                    if is_regular_file(sub_file):
                        if '.' in os.fsdecode(sub_file.parent):
                            if not recursive_dotfiles:
                                if verbose:
                                    eprint("skipping:", sub_file, "due to dot '.' in parent")
                                continue
                        match_count = replace_text(path=Path(sub_file),
                                                   match=match,
                                                   replacement=replacement,
                                                   verbose=verbose,
                                                   debug=debug,)

            else:
                if is_regular_file(path):
                    try:
                        match_count = replace_text(path=Path(path),
                                                   match=match,
                                                   replacement=replacement,
                                                   verbose=verbose,
                                                   debug=debug,)
                    except UnicodeDecodeError:
                        pass

            eprint("matches:", match_count, path)

    else:   # matching on stdin
        match_count = \
            replace_text_bytes(path=Path('/dev/stdin'),
                               match=match,
                               replacement=replacement,
                               verbose=verbose,
                               debug=debug,
                               )
