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

import os
import sys

import pkg_resources
from setuptools.command import easy_install
from setuptools.command import install_scripts


_script_text = """# PBR Generated from %(group)r

import sys

from %(module_name)s import %(import_target)s


if __name__ == '__main__':
    sys.exit(%(invoke_target)s())
"""


def override_get_script_args(dist, executable=None, is_wininst=False):
    """Override entrypoints console_script."""
    if executable is None:
        executable = os.path.normpath(sys.executable)
    header = easy_install.get_script_header('', executable, is_wininst)
    for group in 'console_scripts', 'gui_scripts':
        for name, ep in dist.get_entry_map(group).items():
            if not ep.attrs or len(ep.attrs) > 2:
                raise ValueError('Script targets must be of the form '
                                 '"func" or "Class.class_method".')
            script_text = _script_text % dict(
                group=group,
                module_name=ep.module_name,
                import_target=ep.attrs[0],
                invoke_target='.'.join(ep.attrs),
            )
            yield (name, header + script_text)


class LocalInstallScripts(install_scripts.install_scripts):
    """Intercepts console scripts entry_points."""
    command_name = 'install_scripts'

    def run(self):
        if os.name != 'nt':
            get_script_args = override_get_script_args
        else:
            get_script_args = easy_install.get_script_args

        import distutils.command.install_scripts

        self.run_command('egg_info')
        if self.distribution.scripts:
            # run first to set up self.outfiles
            distutils.command.install_scripts.install_scripts.run(self)
        else:
            self.outfiles = []
        if self.no_ep:
            # don't install entry point scripts into .egg file!
            return

        ei_cmd = self.get_finalized_command('egg_info')
        dist = pkg_resources.Distribution(
            ei_cmd.egg_base,
            pkg_resources.PathMetadata(ei_cmd.egg_base, ei_cmd.egg_info),
            ei_cmd.egg_name, ei_cmd.egg_version,
        )
        bs_cmd = self.get_finalized_command('build_scripts')
        executable = getattr(
            bs_cmd, 'executable', easy_install.sys_executable)
        is_wininst = getattr(
            self.get_finalized_command('bdist_wininst'), '_is_running', False
        )
        for args in get_script_args(dist, executable, is_wininst):
            self.write_script(*args)
