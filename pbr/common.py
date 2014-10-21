# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import unicode_literals

import distutils.errors
import os
import subprocess

TRUE_VALUES = ('true', '1', 'yes')


def get_boolean_option(option_dict, option_name, env_name):
    return ((option_name in option_dict
             and option_dict[option_name][1].lower() in TRUE_VALUES) or
            str(os.getenv(env_name)).lower() in TRUE_VALUES)


def run_shell_command(cmd, throw_on_error=False, buffer=True, env=None):
    if buffer:
        out_location = subprocess.PIPE
        err_location = subprocess.PIPE
    else:
        out_location = None
        err_location = None

    newenv = os.environ.copy()
    if env:
        newenv.update(env)

    error = None
    try:
        proc = subprocess.Popen(cmd,
                                stdout=out_location,
                                stderr=err_location,
                                env=newenv)
        results = proc.communicate()
    except Exception as ex:
        # capture the exception until we determine if the exception is needed
        error = ex

    if (proc.returncode or error) and throw_on_error:
        # exception exists and needed
        if error:
            raise error
        # exception not raised but an unsuccessful return code found and
        # but an exception was requested
        raise distutils.errors.DistutilsError(
            '%s returned %d' % (cmd, proc.returncode))

    if len(results) == 0 or not results[0] or not results[0].strip():
        return ''
    return results[0].strip().decode('utf-8')
