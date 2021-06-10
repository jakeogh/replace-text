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
from enumerate_input import iterate_input

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


def iterate_over_fh(input_fh,
                    match,
                    replacement,
                    output_fh,
                    verbose: bool,
                    debug: bool,
                    ):

    modified = False
    location_read = 0
    match_count = 0
    #location_write = 0
    window = []
    window_size = len(match) # need to expand a matching block by an arb amount, replacement can be any size

    if verbose:
        ic(input_fh, output_fh)

    while True:
        # window starts off empty
        if verbose:
            eprint(len(match), len(window), location_read)
        #fh.seek(location_read)  # unecessary
        next_byte = input_fh.read(1)
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
            if output_fh:
                output_fh.write(window[0])
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
                if verbose:
                    ic('matched')
                match_count += 1
                if replacement:
                    window = replacement
                    if verbose:
                        ic(window)
                    modified = True
                    if output_fh:
                        output_fh.write(window)  # flush the replacement to disk
                    window = []  # start a new window, dont want to match on the replacement

                continue
            # here the window was full, but it did not match, so the window must be shifted by one byte, and the byte that fell off must be written


        assert len(window) <= len(match)

    if verbose:
        ic('broke', modified)

    return match_count, modified


def replace_text_line(*,
                      path: Path,
                      match: str,
                      replacement: str,
                      temp_file,
                      verbose: bool,
                      debug: bool,
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

        return match_count, modified


#def replace_text_bytes(*,
#                       fh,
#                       match: bytes,
#                       replacement: bytes,
#                       temp_file,
#                       verbose: bool,
#                       debug: bool,
#                       ):
#
#    #assert isinstance(path, Path)
#    #if verbose:
#    #    ic(path)
#
#    assert isinstance(match, bytes)
#    if replacement:
#        assert isinstance(replacement, bytes)
#
#
#    ## this cant handle binary files... or files with mixed newlines
#    #if path.as_posix() == '/dev/stdin':
#    #    fh = sys.stdin.buffer
#    #    match_count, modified = iterate_over_fh(fh, match, replacement, temp_file, verbose, debug)
#    #else:
#    #    with open(path, 'rb') as fh:
#    #        match_count, modified = iterate_over_fh(fh, match, replacement, temp_file, verbose, debug)
#
#    match_count, modified = iterate_over_fh(fh, match, replacement, temp_file, verbose, debug)
#
#    return match_count, modified


def replace_text(path: Path,
                 match,
                 replacement,
                 temp_file,
                 verbose: bool,
                 debug: bool,
                 ):

    if isinstance(match, bytes):
        assert False
        #match_count, modified = \
        #    replace_text_bytes(path=path,
        #                       match=match,
        #                       replacement=replacement,
        #                       temp_file=temp_file,
        #                       verbose=verbose,
        #                       debug=debug,
        #                       )
    else:
        match_count, modified = \
            replace_text_line(path=path,
                              match=match,
                              replacement=replacement,
                              temp_file=temp_file,
                              verbose=verbose,
                              debug=debug,
                              )


    return match_count, modified


def get_thing(*,
              utf8: bool,
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
        if utf8:
            result = match
        else:
            result = match.encode('utf8')

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
        match = input(prompt)
        assert len(match) > 0
        if utf8:
            result = match
        else:
            result = match.encode('utf8')

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
@click.option('--utf8', is_flag=True)
@click.option('--printn', is_flag=True)
@click.option('--paths', is_flag=True)
@click.option('--stdout', is_flag=True)
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
        utf8: bool,
        printn: bool,
        paths: bool,
        stdout: bool,
        ask_match: bool,
        ask_replacement: bool,
        ):

    match = get_thing(utf8=utf8,
                      prompt='match',
                      match=match,
                      match_file=match_file,
                      ask=ask_match,
                      verbose=verbose,
                      debug=debug,)

    if (replacement or replacement_file or ask_replacement):
        replacement = get_thing(utf8=utf8,
                                prompt='replacement',
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

    if utf8:
        write_mode = 'w'
        read_mode = 'r'
    else:
        write_mode = 'wb'
        read_mode = 'rb'

    #if files:   # got files on command line, shouldnt be expeecting input on stdin
    disable_stdin = False
    if files:
        disable_stdin = True

    if not (files or paths):
        stdout = True

    if paths and not replacement:
        stdout = True

    output_fh = None
    if stdout:
        if utf8:
            output_fh = sys.stdout
        else:
            output_fh = sys.stdout.buffer

    if not replacement:
        output_fh = None    # just print match_count and file_name

    input_file_iterator = None
    if paths or files:
        input_file_iterator = iterate_input(iterator=files,
                                            null=null,
                                            dont_decode=False,  # yield strs that get passed to Path()
                                            disable_stdin=disable_stdin,
                                            skip=None,
                                            head=None,
                                            tail=None,
                                            random=False,
                                            loop=None,
                                            input_filter_function=None,
                                            debug=debug,
                                            verbose=verbose,)
        assert stdout
        for path in input_file_iterator:
            path = Path(path)

            with open(path, read_mode) as input_fh:
                if not output_fh:
                    if replacement:
                        output_fh = tempfile.NamedTemporaryFile(mode=write_mode,
                                                                prefix='tmp-replace_text-',
                                                                dir='/tmp',
                                                                delete=False)

                match_count, modified = iterate_over_fh(input_fh=input_fh,
                                                        match=match,
                                                        replacement=replacement,
                                                        output_fh=output_fh,
                                                        verbose=verbose,
                                                        debug=debug,)

            if verbose:
                ic(output_fh)

            if not stdout:
                output_fh.close()
                output_fh_path = output_fh.name
                if verbose:
                    ic(output_fh_path)
                if modified:
                    shutil.copystat(path, output_fh_path)
                    shutil.move(output_fh_path, path)
                else:
                    os.unlink(output_fh_path)


            if replacement is None:
                ic(match_count, input_fh)

        return

    else:   # reading input on stdin to match against
        if utf8:
            input_fh = sys.stdin
        else:
            input_fh = sys.stdin.buffer

        match_count, modified = iterate_over_fh(input_fh=input_fh,
                                                match=match,
                                                replacement=replacement,
                                                output_fh=output_fh,
                                                verbose=verbose,
                                                debug=debug,)

        if replacement is None:
            ic(match_count, input_fh)

        return


#    #    assert not paths    # need to iterate over files
#
#    if not (paths or files):
#        # read bytes from stdin and look for matches
#        if utf8:
#            input_fh = sys.stdin
#        else:
#            input_fh = sys.stdin.buffer
#
#    ic(utf8, read_mode, write_mode, input_fh, )
#
#
#
#
#
#
#
#    #path_basename = os.path.basename(path)
#    #path_dir = os.path.dirname(path)
#    mode = 'w'
#    if isinstance(match, bytes):
#        mode = 'wb'
#    ic(mode)
#    temp_file = tempfile.NamedTemporaryFile(mode=mode,
#                                            prefix='tmp-',
#                                            dir='/tmp',
#                                            delete=False)
#
#    match_count = 0
#    iterator = files
#
#    if paths:
#        for index, path in enumerate_input(iterator=iterator,
#                                           null=null,
#                                           progress=False,
#                                           skip=None,
#                                           head=None,
#                                           tail=None,
#                                           debug=debug,
#                                           verbose=verbose,):
#            path = Path(path)
#
#            if verbose:
#                ic(index, path)
#
#            path = Path(path).resolve()
#            if verbose:
#                ic(path)
#            if endswith:
#                if not path.endswith(endswith):
#                    continue
#            if os.path.isdir(path):
#                if not recursive:
#                    print("Warning: skipping folder:",
#                          path,
#                          "specify --recursive to decend into it.", file=sys.stderr)
#                    continue
#
#                for sub_file in all_files_iter(path):
#                    if is_regular_file(sub_file):
#                        if '.' in os.fsdecode(sub_file.parent):
#                            if not recursive_dotfiles:
#                                if verbose:
#                                    eprint("skipping:", sub_file, "due to dot '.' in parent")
#                                continue
#                        match_count, modified = \
#                            replace_text(path=Path(sub_file),
#                                         match=match,
#                                         replacement=replacement,
#                                         temp_file=temp_file,
#                                         verbose=verbose,
#                                         debug=debug,)
#
#            else:
#                if is_regular_file(path):
#                    try:
#                        match_count, modified = \
#                            replace_text(path=Path(path),
#                                         match=match,
#                                         replacement=replacement,
#                                         temp_file=temp_file,
#                                         verbose=verbose,
#                                         debug=debug,)
#                    except UnicodeDecodeError:
#                        pass
#
#            eprint("matches:", match_count, path)
#
#    else:   # matching on stdin
#        ic('stdin path')
#        match = match.encode('utf8')
#        if replacement:
#            replacement = replacement.encode('utf8')
#        ic(match, replacement)
#        mode='wb'
#        temp_file = tempfile.NamedTemporaryFile(mode=mode,
#                                                prefix='tmp-',
#                                                dir='/tmp',
#                                                delete=False)
#        ic(temp_file)
#        ic(temp_file.mode)
#        fh = sys.stdin.buffer
#        match_count, modified = \
#            iterate_over_fh(fh=fh,
#                            match=match,
#                            replacement=replacement,
#                            temp_file=temp_file,
#                            verbose=verbose,
#                            debug=debug,)
#
#    temp_file_name = temp_file.name
#    temp_file.close()
#    if modified:
#        shutil.copystat(path, temp_file_name)
#        shutil.move(temp_file_name, path)
#    else:
#        os.unlink(temp_file_name)
