# -*- coding: utf-8 -*-
"""
replace-text - Replace text in files(s) or stdin.
"""
import re
import sys

from setuptools import find_packages
from setuptools import setup

if not sys.version_info[0] == 3:
    sys.exit("Sorry, Python 3 is required. Use: 'python3 setup.py install'")

dependencies = [
    "pathtool @ git+https://git@github.com/jakeogh/pathtool",
    "asserttool @ git+https://git@github.com/jakeogh/asserttool",
    "clicktool @ git+https://git@github.com/jakeogh/clicktool",
]
version = 0.01

setup(
    name="replace-text",
    version=version,
    url="https://github.com/jakeogh/replace-text",
    license="PUBLIC DOMAIN",
    author="jakeogh",
    author_email="github.com@v6y.net",
    description="Replace text in files(s) or stdin.",
    long_description=__doc__,
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    install_requires=dependencies,
    entry_points={
        "console_scripts": [
            "replace-text = replace_text.replace_text:cli",
        ],
    },
    classifiers=[
        # 'Development Status :: 1 - Planning',
        # 'Development Status :: 2 - Pre-Alpha',
        # 'Development Status :: 3 - Alpha',
        "Development Status :: 4 - Beta",
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: Unix",
        "Operating System :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
