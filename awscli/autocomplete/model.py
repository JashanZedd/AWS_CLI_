# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Model based auto-completer.

This provides autocompletion based on information found
in the `service-2.json` files.

"""
from collections import namedtuple
from awscli.autocomplete import indexer

# This module and the awscli.autocomplete.indexer are imported
# when a user requests autocompletion.  We should avoid importing
# awscli.clidriver or botocore, which have substantial import
# times.  Autocompleting the command names only needs to load
# the sqlite3 cache file.


CLIArgument = namedtuple('CLIArgument', ['argname', 'type_name',
                                         'command', 'parent', 'nargs'])


class ModelIndex(object):
    """Retrieve command/param names through querying an index.

    This class provides methods for retrieving valid command
    and parameter names given some context.  It's used by
    the model based autocompleter.

    """
    def __init__(self, db_filename):
        self._db_filename = db_filename
        self._db_connection = None

    def _get_db_connection(self):
        if self._db_connection is None:
            self._db_connection = indexer.DatabaseConnection(
                self._db_filename)
        return self._db_connection

    def command_names(self, lineage):
        """Return command names given a lineage.

        This ``lineage`` is the same concept used in the
        AWS CLI command classes, except that it explicitly
        uses ``aws`` as the first parent.  This is the list of
        parent commands for a given CLI command.  For example,
        ``aws ec2 <here>`` has a lineage of ``['aws', 'ec2']``.  The
        command ``aws ec2 wait instance-running <here>`` has a lineage
        of ``['aws', 'ec2', 'wait', 'instance-running']``.

        :return: A list of available commands.
        """
        db = self._get_db_connection()
        parent = '.'.join(lineage)
        results = db.execute(
            'select command from command_table '
            'where parent = :parent',
            parent=parent,
        )
        return [row[0] for row in results]

    def arg_names(self, lineage, command_name):
        """Return arg names for a given lineage.

        The return values do not have the `--` added, e.g
        we'll return ``region``, not ``-region``.

        If you want the arg names for ``aws ec2 describe-instances``,
        you would provide
        ``lineage=['aws', 'ec2'], command_name='describe-instances'``.

        """
        db = self._get_db_connection()
        parent = '.'.join(lineage)
        results = db.execute(
            'select argname from param_table '
            'where parent = :parent and '
            'command = :command',
            parent=parent,
            command=command_name,
        )
        return [row[0] for row in results]

    def get_argument_data(self, lineage, command_name, arg_name):
        """Return all metadata for a single argument.

        For example, to get the arg data for::

            $ aws s3api list-objects --bucket

        You'd use:

            * ``lineage=['aws', 's3api']``
            * ``command_name='list-objects'``
            * ``arg_name='bucket'``

        :return: A CLIArgument object.

        """
        db = self._get_db_connection()
        parent = '.'.join(lineage)
        results = list(db.execute(
            'select * from param_table '
            'where parent = :parent and '
            'command = :command and '
            'argname = :argname',
            parent=parent,
            command=command_name,
            argname=arg_name,
        ))
        if len(results) == 1:
            return CLIArgument(*results[0])
