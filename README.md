replace-text

PUBLIC DOMAIN

Replace the given text in a file or stdin. Easier to use than sed because you dont need to escape text.

 Example:
'''
$ replace 'c1:12345:respawn:/sbin/agetty 38400 tty1 linux' 'c1:12345:respawn:/sbin/agetty 38400 tty1 linux --noclear' /etc/inittab
'''

Tip: Use [strong quoting](http://wiki.bash-hackers.org/syntax/quoting)

