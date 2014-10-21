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

import distutils.errors
from distutils import log
import os

from pbr import requirements


try:
    from testrepository import setuptools_command

    class TestrTest(setuptools_command.Testr,
                    requirements.PipInstallTestRequires):
        """Make setup.py test do the right thing."""

        command_name = 'testr'

        user_options = setuptools_command.Testr.user_options + [
            ('coverage-package-name=', None,
             'Use this name for coverage package'),
            ('no-parallel', None, 'Run testr serially'),
            ('log-level=', 'l', 'Log level (default: info)'),
        ]

        boolean_options = setuptools_command.Testr.boolean_options + [
            'no_parallel']

        def initialize_options(self):
            setuptools_command.Testr.initialize_options(self)
            self.coverage_package_name = None
            self.no_parallel = None
            self.log_level = 1

        def finalize_options(self):
            log.set_verbosity(self.log_level)
            log.debug('finalize_options called')
            setuptools_command.Testr.finalize_options(self)
            log.debug('finalize_options: self.__dict__ = %r', self.__dict__)

        def run(self):
            """Set up testr repo, then run testr."""
            self.pre_run()

            log.debug('run called')
            if not os.path.isdir('.testrepository'):
                self._run_testr('init')

            if self.coverage:
                self._coverage_before()
            if not self.no_parallel:
                testr_ret = self._run_testr('run', '--parallel',
                                            *self.testr_args)
            else:
                testr_ret = self._run_testr('run', *self.testr_args)
            if testr_ret:
                raise distutils.errors.DistutilsError(
                    'testr failed (%d)' % testr_ret)
            if self.slowest:
                log.debug('Slowest Tests')
                self._run_testr('slowest')
            if self.coverage:
                self._coverage_after()

        def _coverage_before(self):
            log.debug('_coverage_before called')
            package = self.distribution.get_name()
            if package.startswith('python-'):
                package = package[7:]

            # Use this as coverage package name
            if self.coverage_package_name:
                package = self.coverage_package_name
            options = '--source %s --parallel-mode' % package
            os.environ['PYTHON'] = ('coverage run %s' % options)
            log.debug("os.environ['PYTHON'] = %r", os.environ['PYTHON'])

    _have_testr = True

except ImportError:
    _have_testr = False


def have_testr():
    return _have_testr

try:
    from nose import commands

    class NoseTest(commands.nosetests, requirements.PipInstallTestRequires):
        """Fallback test runner if testr is a no-go."""

        command_name = 'test'

        def run(self):
            self.pre_run()
            # Can't use super - base class old-style class
            commands.nosetests.run(self)

    _have_nose = True

except ImportError:
    _have_nose = False


def have_nose():
    return _have_nose
