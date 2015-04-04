replace-text

PUBLIC DOMAIN

Replace the given text in a file or stdin.

* No need to escape text.
* Handles arbitrary large files and/or stdin/stdout.
* Perserves existing [line endings](https://en.wikipedia.org/wiki/Newline) (LF (Unix/OSX), CR+LF (DOS/Windows) and CR (Mac OS <= version 9)).
* Perserves [file metadata](https://docs.python.org/3/library/shutil.html#shutil.copystat).

Example:
```
$ replace 'c1:12345:respawn:/sbin/agetty 38400 tty1 linux' 'c1:12345:respawn:/sbin/agetty 38400 tty1 linux --noclear' /etc/inittab
```

Tip: Use [strong quoting](http://wiki.bash-hackers.org/syntax/quoting).

