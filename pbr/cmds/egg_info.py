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

from distutils import log
import io
import os
import sys

from setuptools.command import egg_info
from setuptools.command import sdist

from pbr import common
from pbr import extra_files
from pbr import git


class LocalManifestMaker(egg_info.manifest_maker):
    """Add any files that are in git and some standard sensible files."""

    def _add_pbr_defaults(self):
        for template_line in [
            'include AUTHORS',
            'include ChangeLog',
            'exclude .gitignore',
            'exclude .gitreview',
            'global-exclude *.pyc'
        ]:
            self.filelist.process_template_line(template_line)

    def add_defaults(self):
        option_dict = self.distribution.get_option_dict('pbr')

        sdist.sdist.add_defaults(self)
        self.filelist.append(self.template)
        self.filelist.append(self.manifest)
        self.filelist.extend(extra_files.get_extra_files())
        should_skip = common.get_boolean_option(option_dict, 'skip_git_sdist',
                                                'SKIP_GIT_SDIST')
        if not should_skip:
            for entry in git.find_git_files():
                if not self.filelist.exclude_pattern(entry):
                    self.filelist.append(entry)
        elif os.path.exists(self.manifest):
            self.read_manifest()
        ei_cmd = self.get_finalized_command('egg_info')
        self._add_pbr_defaults()
        self.filelist.include_pattern('*', prefix=ei_cmd.egg_info)


class LocalEggInfo(egg_info.egg_info):
    """Override the egg_info command to regenerate SOURCES.txt sensibly."""

    command_name = 'egg_info'

    def find_sources(self):
        """Generate SOURCES.txt only if there isn't one already.

        If we are in an sdist command, then we always want to update
        SOURCES.txt. If we are not in an sdist command, then it doesn't
        matter one flip, and is actually destructive.
        """
        manifest_filename = os.path.join(self.egg_info, 'SOURCES.txt')
        if not os.path.exists(manifest_filename) or 'sdist' in sys.argv:
            log.info('[pbr] Processing SOURCES.txt')
            mm = LocalManifestMaker(self.distribution)
            mm.manifest = manifest_filename
            mm.run()
            self.filelist = mm.filelist
        else:
            log.info('[pbr] Reusing existing SOURCES.txt')
            self.filelist = egg_info.FileList()
            for entry in io.open(manifest_filename, 'r').read().split('\n'):
                self.filelist.append(entry)
