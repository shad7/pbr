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

import os

from setuptools.command import easy_install

from pbr.cmds import build_doc
from pbr.cmds import install_scripts
from pbr.cmds import test
from pbr import common
from pbr.hooks import base


class CommandsConfig(base.BaseConfig):

    section = 'global'

    def __init__(self, config):
        super(CommandsConfig, self).__init__(config)
        self.commands = self.config.get('commands', "")

    def save(self):
        self.config['commands'] = self.commands
        super(CommandsConfig, self).save()

    def add_command(self, command):
        self.commands = "%s\n%s" % (self.commands, command)

    def hook(self):
        self.add_command('pbr.cmds.egg_info.LocalEggInfo')
        self.add_command('pbr.cmds.sdist.LocalSDist')
        self.add_command('pbr.cmds.install_scripts.LocalInstallScripts')
        if os.name != 'nt':
            easy_install.get_script_args = \
                install_scripts.override_get_script_args

        if build_doc.have_sphinx():
            self.add_command('pbr.cmds.build_doc.LocalBuildDoc')
            self.add_command('pbr.cmds.build_doc.LocalBuildLatex')

        if os.path.exists('.testr.conf') and test.have_testr():
            # There is a .testr.conf file. We want to use it.
            self.add_command('pbr.cmds.test.TestrTest')
        elif self.config.get('nosetests', False) and test.have_nose():
            # We seem to still have nose configured
            self.add_command('pbr.cmds.test.NoseTest')

        use_egg = common.get_boolean_option(
            self.pbr_config, 'use-egg', 'PBR_USE_EGG')
        # We always want non-egg install unless explicitly requested
        if 'manpages' in self.pbr_config or not use_egg:
            self.add_command('pbr.cmds.install.LocalInstall')

        self.add_command('pbr.cmds.upload.LocalUpload')
