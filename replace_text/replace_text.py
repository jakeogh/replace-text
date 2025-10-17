#!/usr/bin/env python3
"""
# Replace the given text in file(s) or stdin.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

import click
from asserttool import ic
from asserttool import maxone
from clicktool import click_add_options
from clicktool import click_global_options
from clicktool import tvicgvd
from eprint import eprint
from globalverbose import gvd
from mptool import output
from unmp import unmp

# from asserttool import ic  # too many deps

# note adding deps requires changes to sendgentoo


def remove_comments_from_bytes(
    line,
) -> bytes:  # todo check for (assert <=1 line break) multiple linebreaks?
    assert isinstance(line, bytes)
    uncommented_line = b""
    for char in line:
        char = bytes([char])
        if char != b"#":
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


def append_unique_bytes_to_file(
    path: Path,
    bytes_to_append: bytes,
) -> None:
    assert isinstance(bytes_to_append, bytes)
    match_count = None
    path = Path(path).expanduser()
    with open(path, "rb") as input_fh:
        match_count, modified = iterate_over_fh(
            input_fh=input_fh,
            match_bytes=bytes_to_append,
            replacement_bytes=None,
            output_fh=None,
        )

        assert not modified

    ic(path, match_count, modified)

    if match_count == 0:
        with open(path, "ab") as input_fh:
            input_fh.write(bytes_to_append)


def iterate_over_fh(
    *,
    input_fh,
    match_bytes: bytes,
    replacement_bytes: None | bytes,
    output_fh,
) -> tuple[int, bool]:
    assert isinstance(match_bytes, bytes)
    if replacement_bytes is not None:
        assert isinstance(replacement_bytes, bytes)
    modified = False
    location_read = 0
    match_count = 0
    window: list[bytes] = []
    window_size = len(
        match_bytes
    )  # need to expand a matching block by an arb amount, replacement_bytes can be any size

    ic(input_fh, output_fh)

    while True:
        # window starts off empty
        if gvd:
            ic(len(match_bytes), len(window), location_read)
        # fh.seek(location_read)  # unnecessary
        next_byte = input_fh.read(1)
        if gvd:
            ic(next_byte)
        if next_byte == b"":
            ic("done iterating, cant break here must write remaining window")
            # break
            assert (len(window) < len(match_bytes)) or (len(window) == len(match_bytes))
            _window = b"".join(window)
            # assert _window != match_bytes  # bug the last window may match
            if output_fh:
                output_fh.write(_window)
            break

        window.append(next_byte)
        location_read += 1
        # first byte in window, or EOF

        # ic(b''.join(window))

        if len(window) < len(match_bytes):
            # keep filling the window
            continue

        # window is too big
        if (len(window) - 1) == len(match_bytes):  # window needs to move
            if output_fh:
                output_fh.write(window[0])
            window = window[1:]
            assert len(window) == window_size  # only time window_size is used

        assert len(window) == len(match_bytes)
        if b"".join(window) == match_bytes:
            ic("matched")
            match_count += 1
            if replacement_bytes is not None:
                window = [replacement_bytes]
                ic(window)
                modified = True
                if output_fh:
                    output_fh.write(
                        replacement_bytes
                    )  # flush the replacement_bytes to disk
                window = []  # start a new window, dont want to match on the replacement
            else:
                # No replacement, just counting matches - slide window by one
                if output_fh:
                    output_fh.write(window[0])
                window = window[1:]
            continue
        else:
            if gvd:
                ic(len(window), "window was full, but didnt match")

        # here the window was full, but it did not match,
        # so the window must be shifted by one byte, and the byte that fell off must be written

        # assert len(window) <= len(match_bytes)  #
        # assert len(window) in [len(match_bytes), len(match_bytes) + 1]
        assert len(window) == len(match_bytes)

    ic("broke", modified)

    return match_count, modified


def replace_text_line(
    *,
    path: Path,
    match_bytes: str,
    replacement: str,
    temp_file,
):
    match_count = 0
    assert isinstance(path, Path)
    ic(path)

    # this cant handle binary files... or files with mixed newlines
    modified = False
    with open(path) as path_fh:
        try:
            for line in path_fh:
                if match_bytes in line:
                    modified = True
                    match_count += 1
                if replacement:
                    new_line = line.replace(match_bytes, replacement)
                    temp_file.write(new_line)
                    # if path_fh.newlines == '\n':      # LF (Unix)
                    #    temp_file.write("%s\n" % new_line)
                    #    continue
                    # elif path_fh.newlines == '\r\n':  # CR+LF (DOS/Win)
                    #    temp_file.write("%s\r\n" % new_line)
                    #    continue
                    # elif path_fh.newlines == '\r':    # CR (Mac OS <= v9)
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


def replace_text(
    path: Path,
    match_bytes,
    replacement,
    temp_file,
):
    if isinstance(match_bytes, bytes):
        assert False
        # match_count, modified = \
        #    replace_text_bytes(path=path,
        #                       match_bytes=match,
        #                       replacement=replacement,
        #                       temp_file=temp_file,
        #                       )
    else:
        match_count, modified = replace_text_line(
            path=path,
            match_bytes=match_bytes,
            replacement=replacement,
            temp_file=temp_file,
        )

    return match_count, modified


def get_thing(
    *,
    utf8: bool,
    prompt: str,
    match_bytes: None | bytes,
    match_file: None | str,
    ask: bool,
):
    result = None
    assert prompt in ["match", "replacement"]
    if not maxone([match_bytes, match_file, ask]):
        raise ValueError(
            "--{0} --{0}-file and --ask-{0} are mutually exclusive".format(prompt)
        )
    if match_bytes:
        assert len(match_bytes) > 0
        if utf8:
            result = match_bytes.decode("utf8")
        else:
            result = match_bytes

    if match_file:
        match_file = Path(match_file)
        with open(match_file.as_posix(), "rb") as fh:
            file_bytes = fh.read()
        assert len(file_bytes) > 0
        if utf8:
            result = file_bytes.decode("utf8")
        else:
            result = file_bytes
    if ask:
        match_bytes = input(prompt + ": ")
        assert len(match_bytes) > 0
        if utf8:
            result = match_bytes
        else:
            result = match_bytes.encode("utf8")

    if result:
        ic(result)
        return result

    raise ValueError(f"one of --{prompt} --{prompt}-file or --ask-{prompt} is required")


# called by byte-vector-replacer
def replace_text_in_file(
    path: Path,
    match_bytes: bytes,
    replacement_bytes: None | bytes,
    output_fh,
    read_mode: str,
    write_mode: str,
    remove_match: bool,
) -> None:
    ic(match_bytes)
    ic(replacement_bytes)
    path = Path(path).expanduser().resolve()
    assert isinstance(match_bytes, bytes)
    if replacement_bytes is not None:
        assert isinstance(replacement_bytes, bytes)
    assert isinstance(read_mode, str)
    assert isinstance(write_mode, str)

    if replacement_bytes == b"":
        assert remove_match

    if remove_match:
        assert replacement_bytes == b""

    with open(path, read_mode) as input_fh:
        if replacement_bytes is not None:
            output_fh = tempfile.NamedTemporaryFile(
                mode=write_mode,
                prefix="tmp-replace_text-",
                dir="/tmp",
                delete=False,
            )

        match_count, modified = iterate_over_fh(
            input_fh=input_fh,
            match_bytes=match_bytes,
            replacement_bytes=replacement_bytes,
            output_fh=output_fh,
        )

    ic(match_count, output_fh)
    ic(match_count, input_fh)
    output_fh.close()
    output_fh_path = output_fh.name
    ic(output_fh_path)
    if modified:
        bytes_difference = len(replacement_bytes) - len(match_bytes)
        bytes_difference = bytes_difference * match_count
        ic(bytes_difference)
        input_file_size = os.path.getsize(path)
        output_file_size = os.path.getsize(output_fh_path)
        ic(input_file_size)
        ic(output_file_size)
        assert (input_file_size + bytes_difference) == output_file_size
        shutil.copystat(path, output_fh_path)
        shutil.move(output_fh_path, path)
        eprint(match_count, path.as_posix())
    else:
        os.unlink(output_fh_path)
    return


@click.command()
@click.option("--match", "match_str", type=str)
@click.option("--replacement", "replacement_str", type=str)
@click.option("--match-file", type=str)
@click.option("--replacement-file", type=str)
@click.option("--remove-match", is_flag=True)
@click.option("--utf8", is_flag=True)
@click.option("--stdout", is_flag=True)
@click.option("--ask-match", is_flag=True)
@click.option("--ask-replacement", is_flag=True)
@click.option("--disable-newline-check", is_flag=True)
@click.option(
    "--path",
    "path_args",
    multiple=True,
    type=click.Path(exists=True),
    help="Path(s) to process directly instead of reading from stdin",
)
@click_add_options(click_global_options)
@click.pass_context
def cli(
    ctx,
    match_str: None | str,
    replacement_str: None | str,
    match_file: None | str,
    replacement_file: None | str,
    remove_match: bool,
    utf8: bool,
    stdout: bool,
    ask_match: bool,
    ask_replacement: bool,
    disable_newline_check: bool,
    path_args: tuple[str, ...],
    dict_output: bool,
    verbose_inf: bool,
    verbose: bool = False,
):
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    # ic(replacement)
    replacement_bytes = None
    if replacement_str is not None:
        replacement_bytes = replacement_str.encode("utf8")

    match_bytes = None
    if match_str:
        match_bytes = match_str.encode("utf8")
    else:
        match_bytes = None

    match_bytes = get_thing(
        utf8=utf8,
        prompt="match",
        match_bytes=match_bytes,
        match_file=match_file,
        ask=ask_match,
    )

    if replacement_bytes or replacement_file or ask_replacement:
        if remove_match:
            raise ValueError("--remove-match and --replacement* are mutually exclusive")

    if replacement_bytes or replacement_file or ask_replacement:
        replacement_bytes = get_thing(
            utf8=utf8,
            prompt="replacement",
            match_bytes=replacement_bytes,
            match_file=replacement_file,
            ask=ask_replacement,
        )

    if remove_match:
        assert replacement_bytes is None
        replacement_bytes = b""

    ic(match_bytes, replacement_bytes)
    assert match_bytes != replacement_bytes

    if match_bytes and len(match_bytes) > 0 and match_bytes[-1:] == b"\n":
        if replacement_bytes and (not replacement_bytes[-1:] == b"\n"):
            eprint(
                f"WARNING: match_bytes ends in newline but replacement_bytes does not"
            )
            if not disable_newline_check:
                eprint("use --disable-newline-check")
                sys.exit(1)

    if utf8:
        write_mode = "w"
        read_mode = "r"
    else:
        write_mode = "wb"
        read_mode = "rb"

    stdout = True

    output_fh = None
    if stdout:
        if utf8:
            output_fh = sys.stdout
        else:
            output_fh = sys.stdout.buffer

    if replacement_bytes is None:
        output_fh = None  # just print match_count and file_name

    ic(
        match_bytes,
        replacement_bytes,
        match_file,
        replacement_file,
        utf8,
        stdout,
        ask_match,
        ask_replacement,
    )

    def _process_path(
        *,
        path: bytes,
        match_bytes: bytes,
        replacement_bytes: None | bytes,
        output_fh,
        read_mode,
        write_mode,
        remove_match,
    ):
        _path = Path(os.fsdecode(path))
        if _path.name == "byte_vector_replacer.py":
            eprint("REFUSING TO EDIT byte_vector_replacer.py")
            raise ValueError("REFUSING TO EDIT byte_vector_replacer.py")
        ic(_path)

        replace_text_in_file(
            path=_path,
            match_bytes=match_bytes,
            replacement_bytes=replacement_bytes,
            output_fh=output_fh,
            read_mode=read_mode,
            write_mode=write_mode,
            remove_match=remove_match,
        )
        output(
            _path,
            reason=None,
            dict_output=False,
            tty=tty,
        )

    # If --path option(s) provided, process those paths directly
    if path_args:
        for path_arg in path_args:
            path_bytes = os.fsencode(path_arg)
            _process_path(
                path=path_bytes,
                match_bytes=match_bytes,
                replacement_bytes=replacement_bytes,
                output_fh=output_fh,
                read_mode=read_mode,
                write_mode=write_mode,
                remove_match=remove_match,
            )
    else:
        # Read messagepacked paths from stdin
        iterator = unmp(
            valid_types=[dict, bytes],
        )

        for _mpobject in iterator:
            if isinstance(_mpobject, dict):
                for _path in _mpobject.values():
                    _process_path(
                        path=_path,
                        match_bytes=match_bytes,
                        replacement_bytes=replacement_bytes,
                        output_fh=output_fh,
                        read_mode=read_mode,
                        write_mode=write_mode,
                        remove_match=remove_match,
                    )
            else:
                _process_path(
                    path=_mpobject,
                    match_bytes=match_bytes,
                    replacement_bytes=replacement_bytes,
                    output_fh=output_fh,
                    read_mode=read_mode,
                    write_mode=write_mode,
                    remove_match=remove_match,
                )
