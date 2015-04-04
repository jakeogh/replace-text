replace-text

PUBLIC DOMAIN

Replace the given text in a file or stdin.

* No need to escape text.
* Handles arbitrary large files and/or stdin/stdout.
* Perserves existing [line endings](https://en.wikipedia.org/wiki/Newline) LF Unix/OSX, CR+LF DOS/Windows and CR Mac OS <= version 9).
* Perserves [file metadata](https://docs.python.org/3/library/shutil.html#shutil.copystat).

Example:
```
$ replace-text 'c1:12345:respawn:/sbin/agetty 38400 tty1 linux' \
	       'c1:12345:respawn:/sbin/agetty 38400 tty1 linux --noclear' /etc/inittab

$./replace-text -h
usage: replace-text [-h] match replacement [file]

positional arguments:
  match        the string to match
  replacement  the string to replace the match with
  file         optional file to parse

optional arguments:
  -h, --help   show this help message and exit
```

Tip: Use [strong quoting](http://wiki.bash-hackers.org/syntax/quoting).

