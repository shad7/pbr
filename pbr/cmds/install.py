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

from distutils.command import install as du_install

from setuptools.command import install

from pbr import requirements


class LocalInstall(install.install):
    """Runs python setup.py install in a sensible manner.

    Force a non-egg installed in the manner of
    single-version-externally-managed, which allows us to install manpages
    and config files.

    Because non-egg installs bypass the depend processing machinery, we
    need to do our own. Because easy_install is evil, just use pip to
    process our requirements files directly, which means we don't have to
    do crazy extra processing.

    Bypass installation if --single-version-externally-managed is given,
    so that behavior for packagers remains the same.
    """

    command_name = 'install'

    def run(self):
        option_dict = self.distribution.get_option_dict('pbr')
        if (not self.single_version_externally_managed
                and self.distribution.install_requires):
            requirements.pip_install(
                self.distribution.dependency_links,
                self.distribution.install_requires, self.root,
                option_dict=option_dict)

        return du_install.install.run(self)
