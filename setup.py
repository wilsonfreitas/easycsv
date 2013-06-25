#!/usr/bin/env python

from distutils.core import setup

setup(name="easycsv",
      version="0.8.0",
      py_modules=['easycsv'],
      author='Wilson Freitas',
      author_email='wilson.freitas@gmail.com',
      description='A module that permits to manage a database using csv files.',
      url='http://aboutwilson.net/easycsv',
      license='GPL',
      long_description='''\
That is a module which permits to execute simple database commands with csv statements.
The csv statements are rows in a csv file with special marks indicating
whether its content must to be inserted, deleted or updated in the database.
''',
      )

