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

from pbr.hooks import base
from pbr import requirements


class BackwardsCompatConfig(base.BaseConfig):

    section = 'backwards_compat'

    def hook(self):
        self.config['include_package_data'] = 'True'

        self.append_text_list('dependency_links',
                              requirements.parse_dependency_links())

        self.append_text_list('tests_require',
                              requirements.parse_requirements(
                                  requirements.TEST_REQUIREMENTS_FILES))
