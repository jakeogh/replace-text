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
from math import inf
from pathlib import Path
from typing import Optional

#from icecream import ic  # too many deps
import click
from asserttool import eprint
from asserttool import ic
from asserttool import maxone
from asserttool import tv
#from colorama import Fore
#from colorama import Style
from enumerate_input import iterate_input
from pathtool import get_file_size

#note adding deps requires changes to sendgentoo


def remove_comments_from_bytes(line) -> bytes: #todo check for (assert <=1 line break) multiple linebreaks?
    assert isinstance(line, bytes)
    uncommented_line = b''
    for char in line:
        char = bytes([char])
        if char != b'#':
            uncommented_line += char
        else:
            break
    return uncommented_line


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


def append_unique_bytes_to_file(path: Path,
                                bytes_to_append: bytes,
                                verbose: int,
                                ) -> None:

    assert isinstance(bytes_to_append, bytes)
    match_count = None
    path = Path(path).expanduser()
    with open(path, 'rb') as input_fh:
        match_count, modified = \
            iterate_over_fh(input_fh=input_fh,
                            bytes_to_match=bytes_to_append,
                            replacement=None,
                            output_fh=None,
                            verbose=verbose,
                            )

        assert not modified

    if verbose:
        ic(path, match_count, modified)

    if match_count == 0:
        with open(path, 'ab') as input_fh:
            input_fh.write(bytes_to_append)


def iterate_over_fh(*,
                    input_fh,
                    bytes_to_match: bytes,
                    replacement: Optional[bytes],
                    output_fh,
                    verbose: int,
                    ) -> tuple[int, bool]:

    assert isinstance(bytes_to_match, bytes)
    if replacement is not None:
        assert isinstance(replacement, bytes)
    modified = False
    location_read = 0
    match_count = 0
    window = []
    window_size = len(bytes_to_match) # need to expand a matching block by an arb amount, replacement can be any size

    if verbose == inf:
        ic(input_fh, output_fh)

    while True:
        # window starts off empty
        if verbose == inf:
            ic(len(bytes_to_match), len(window), location_read)
        #fh.seek(location_read)  # unecessary
        next_byte = input_fh.read(1)
        if verbose == inf:
            ic(next_byte)
        if next_byte == b'':
            if verbose == inf:
                ic('done iterating, cant break here must write remaining window')
            #break
            assert ((len(window) < len(bytes_to_match)) or (len(window) == len(bytes_to_match)))
            assert b''.join(window) != bytes_to_match
            window = b''.join(window)
            if output_fh:
                output_fh.write(window)
            break

        window.append(next_byte)
        location_read += 1
        # first byte in window, or EOF

        #ic(b''.join(window))

        if len(window) < len(bytes_to_match):
            # keep filling the window
            continue

        # window is too big
        if (len(window) - 1) == len(bytes_to_match):     # window needs to move
            if output_fh:
                output_fh.write(window[0])
            window = window[1:]
            assert len(window) == window_size   # only time window_size is used

        assert len(window) == len(bytes_to_match)
        # if it's possible to do a match, see if there is one
        if verbose == inf:
            print('\n')
            eprint('bytes_to_match :', repr(bytes_to_match))
            eprint('window:', repr(b''.join(window)))
        #ic(window)
        # if there is a match, we know the whole window gets replaced
        if b''.join(window) == bytes_to_match:
            if verbose:
                ic('matched')
            match_count += 1
            if replacement is not None:
                window = replacement
                if verbose:
                    ic(window)
                modified = True
                if output_fh:
                    output_fh.write(window)  # flush the replacement to disk
                window = []  # start a new window, dont want to match on the replacement
            continue
        else:
            if verbose == inf:
                ic(len(window), 'window was full, but didnt match')


        # here the window was full, but it did not match,
        # so the window must be shifted by one byte, and the byte that fell off must be written


        #assert len(window) <= len(bytes_to_match)  #
        #assert len(window) in [len(bytes_to_match), len(bytes_to_match) + 1]
        assert len(window) == len(bytes_to_match)

    if verbose == inf:
        ic('broke', modified)

    return match_count, modified


def replace_text_line(*,
                      path: Path,
                      bytes_to_match: str,
                      replacement: str,
                      temp_file,
                      verbose: int,
                      ):

    match_count = 0
    assert isinstance(path, Path)
    if verbose:
        eprint(path)


    # this cant handle binary files... or files with mixed newlines
    modified = False
    with open(path, 'rU') as path_fh:
        try:
            for line in path_fh:
                if bytes_to_match in line:
                    modified = True
                    match_count += 1
                if replacement:
                    new_line = line.replace(bytes_to_match, replacement)
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

        return match_count, modified


#def replace_text_bytes(*,
#                       fh,
#                       bytes_to_match: bytes,
#                       replacement: bytes,
#                       temp_file,
#                       verbose: int,
#                       ):
#
#    #assert isinstance(path, Path)
#    #if verbose:
#    #    ic(path)
#
#    assert isinstance(bytes_to_match, bytes)
#    if replacement:
#        assert isinstance(replacement, bytes)
#
#
#    ## this cant handle binary files... or files with mixed newlines
#    #if path.as_posix() == '/dev/stdin':
#    #    fh = sys.stdin.buffer
#    #    match_count, modified = iterate_over_fh(fh, bytes_to_match, replacement, temp_file, verbose)
#    #else:
#    #    with open(path, 'rb') as fh:
#    #        match_count, modified = iterate_over_fh(fh, bytes_to_match, replacement, temp_file, verbose)
#
#    match_count, modified = iterate_over_fh(fh, bytes_to_match, replacement, temp_file, verbose)
#
#    return match_count, modified


def replace_text(path: Path,
                 bytes_to_match,
                 replacement,
                 temp_file,
                 verbose: int,
                 ):

    if isinstance(bytes_to_match, bytes):
        assert False
        #match_count, modified = \
        #    replace_text_bytes(path=path,
        #                       bytes_to_match=match,
        #                       replacement=replacement,
        #                       temp_file=temp_file,
        #                       verbose=verbose,
        #                       )
    else:
        match_count, modified = \
            replace_text_line(path=path,
                              bytes_to_match=bytes_to_match,
                              replacement=replacement,
                              temp_file=temp_file,
                              verbose=verbose,
                              )


    return match_count, modified


def get_thing(*,
              utf8: bool,
              prompt: str,
              bytes_to_match: str,
              match_file: str,
              ask: bool,
              verbose: int,
              ):

    result = None
    assert prompt in ['match', 'replacement']
    if not maxone([bytes_to_match, match_file, ask]):
        raise ValueError('--{0} --{0}-file and --ask-{0} are mutually exclusive'.format(prompt))
    if bytes_to_match:
        assert len(bytes_to_match) > 0
        if utf8:
            result = bytes_to_match
        else:
            result = bytes_to_match.encode('utf8')

    if match_file:
        match_file = Path(match_file)
        with open(match_file.as_posix(), 'rb') as fh:
            file_bytes = fh.read()
        assert len(file_bytes) > 0
        if utf8:
            result = file_bytes.decode('utf8')
        else:
            result = file_bytes
    if ask:
        bytes_to_match = input(prompt + ': ')
        assert len(bytes_to_match) > 0
        if utf8:
            result = bytes_to_match
        else:
            result = bytes_to_match.encode('utf8')

    if result:
        if verbose == inf:
            ic(result)
        return result

    raise ValueError('one of --{0} --{0}-file or --ask-{0} is required'.format(prompt))


#        recursive: bool,
#        recursive_dotfiles: bool,
#        endswith: str,


def replace_text_in_file(path: Path,
                         bytes_to_match: bytes,
                         replacement: Optional[bytes],
                         output_fh,
                         stdout: bool,
                         read_mode: str,
                         write_mode: str,
                         remove_match: bool,
                         verbose: int,
                         ) -> None:

    path = Path(path).expanduser().resolve()
    assert isinstance(stdout, bool)
    assert isinstance(bytes_to_match, bytes)
    if replacement is not None:
        assert isinstance(replacement, bytes)
    assert isinstance(read_mode, str)
    assert isinstance(write_mode, str)

    if replacement == b'':
        assert remove_match

    if remove_match:
        assert replacement == b''

    with open(path, read_mode) as input_fh:
        if replacement is not None:
            output_fh = tempfile.NamedTemporaryFile(mode=write_mode,
                                                    prefix='tmp-replace_text-',
                                                    dir='/tmp',
                                                    delete=False)

        match_count, modified = iterate_over_fh(input_fh=input_fh,
                                                bytes_to_match=bytes_to_match,
                                                replacement=replacement,
                                                output_fh=output_fh,
                                                verbose=verbose,
                                                )

    if verbose == inf:
        ic(stdout, match_count, output_fh)

    if not stdout:
        output_fh.close()
        output_fh_path = output_fh.name
        if verbose == inf:
            ic(output_fh_path)
        if modified:
            bytes_difference = len(replacement) - len(bytes_to_match)
            bytes_difference = bytes_difference * match_count
            if verbose == inf:
                ic(bytes_difference)
            input_file_size = get_file_size(path)
            output_file_size = get_file_size(output_fh_path)
            if verbose == inf:
                ic(input_file_size)
                ic(output_file_size)
            assert (input_file_size + bytes_difference) == output_file_size
            shutil.copystat(path, output_fh_path)
            shutil.move(output_fh_path, path)
            eprint(match_count, path.as_posix())
        else:
            os.unlink(output_fh_path)
        return


    #if replacement is None:
    if verbose:
        ic(match_count, input_fh)
    if match_count > 0:
        sys.stdout.buffer.write(str(match_count).encode('utf8') + b' ')
        sys.stdout.buffer.write(str(input_fh.name).encode('utf8'))
        sys.stdout.buffer.write(b'\n')


@click.command()
@click.argument("paths", nargs=-1)
@click.option("--match", 'match_str', type=str,)
@click.option("--replacement", type=str,)
@click.option('--match-file', type=str)
@click.option('--replacement-file', type=str,)
@click.option('--remove-match', is_flag=True,)
@click.option('--verbose', count=True,)
@click.option('--verbose-inf', is_flag=True,)
@click.option('--utf8', is_flag=True,)
@click.option('--stdout', is_flag=True,)
@click.option('--ask-match', is_flag=True, help="escape from shell escaping",)
@click.option('--ask-replacement', is_flag=True, help="escape from shell escaping",)
@click.option('--disable-newline-check', is_flag=True,)
@click.pass_context
def cli(ctx,
        paths: tuple[str],
        match_str: str,
        replacement: str,
        match_file: str,
        replacement_file: str,
        remove_match: bool,
        verbose: int,
        verbose_inf: bool,
        utf8: bool,
        stdout: bool,
        ask_match: bool,
        ask_replacement: bool,
        disable_newline_check: bool,
        ):

    tty, verbose = tv(ctx=ctx,
                      verbose=verbose,
                      verbose_inf=verbose_inf,
                      )

    #ic(replacement)
    if replacement is not None:
        replacement = replacement.encode('utf8')

    if match_str:
        bytes_to_match = match_str.decode('utf8')
    else:
        bytes_to_match = None

    bytes_to_match = get_thing(utf8=utf8,
                               prompt='match',
                               bytes_to_match=bytes_to_match,
                               match_file=match_file,
                               ask=ask_match,
                               verbose=verbose,
                               )

    if (replacement or replacement_file or ask_replacement):
        if remove_match:
            raise ValueError('--remove-match and --replacement* are mutually exclusive')

    if (replacement or replacement_file or ask_replacement):
        replacement = get_thing(utf8=utf8,
                                prompt='replacement',
                                bytes_to_match=replacement,
                                match_file=replacement_file,
                                ask=ask_replacement,
                                verbose=verbose,
                                )

    if remove_match:
        assert replacement is None
        replacement = b''

    if verbose == inf:
        ic(bytes_to_match, replacement)

    if bytes_to_match[-1] == b'\n':
        if not replacement[-1] == b'\n':
            eprint("WARNING: bytes_to_match ends in {} but replacement does not".format(bytes_to_match[-1]))
            if not disable_newline_check:
                eprint('use --disable-newline-check')
                sys.exit(1)

    if utf8:
        write_mode = 'w'
        read_mode = 'r'
    else:
        write_mode = 'wb'
        read_mode = 'rb'

    #if files:   # got files on command line, shouldnt be expeecting input on stdin
    disable_stdin = False
    if paths:
        disable_stdin = True

    if not paths:
        stdout = True

    if paths and not replacement:
        if not remove_match:
            stdout = True

    output_fh = None
    if stdout:
        if utf8:
            output_fh = sys.stdout
        else:
            output_fh = sys.stdout.buffer

    if replacement is None:
        output_fh = None    # just print match_count and file_name

    input_file_iterator = None

    if verbose:
        ic(paths, bytes_to_match, replacement, match_file, replacement_file, utf8, stdout, ask_match, ask_replacement,)

    if paths:
        input_file_iterator = iterate_input(iterator=paths,
                                            null=b'\0',
                                            dont_decode=True,  #  must iterate over bytes for null terminated input
                                            disable_stdin=disable_stdin,
                                            skip=None,
                                            head=None,
                                            tail=None,
                                            random=False,
                                            loop=None,
                                            input_filter_function=None,
                                            verbose=verbose,)
        for path in input_file_iterator:
            path = Path(os.fsdecode(path))
            if verbose:
                ic(path)

            replace_text_in_file(path=path,
                                 bytes_to_match=bytes_to_match,
                                 replacement=replacement,
                                 output_fh=output_fh,
                                 stdout=stdout,
                                 read_mode=read_mode,
                                 write_mode=write_mode,
                                 remove_match=remove_match,
                                 verbose=verbose,
                                 )

        return

    else:   # reading input on stdin to match against
        if utf8:
            input_fh = sys.stdin
        else:
            input_fh = sys.stdin.buffer

        match_count, modified = iterate_over_fh(input_fh=input_fh,
                                                bytes_to_match=bytes_to_match,
                                                replacement=replacement,
                                                output_fh=output_fh,
                                                verbose=verbose,
                                                )

        if replacement is None:
            if verbose:
                ic(match_count, input_fh)
            if match_count > 0:
                print(match_count, input_fh)

        return


