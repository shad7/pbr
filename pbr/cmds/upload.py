# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import unicode_literals

from distutils.command import upload as orig
from distutils import log
import glob
import os
import sys


PY_MAJOR = sys.version[:3]

DIST_EXTENSIONS = {
    '.whl': ('bdist_wheel', PY_MAJOR),
    '.egg': ('bdist_egg', PY_MAJOR),
    '.tar.bz2': ('sdist', None),
    '.tar.gz': ('sdist', None),
    '.zip': ('sdist', None),
}


class LocalUpload(orig.upload):
    """Add secure upload to pypi that works even sdist, bdist_egg,
    and wheel.
    """

    command_name = 'upload'

    def run(self):
        """Extend upload to support generating distribution(s) and then
        as part of a separate release step upload the distribution(s)
        to index.
        """
        for filename in glob.glob(os.path.join(self.dist_dir, '*')):

            self.announce('[%s] checking distribution %s' % (
                self.get_command_name(), os.path.basename(filename)),
                log.DEBUG)
            command = pyver = None

            for ext, dist in DIST_EXTENSIONS.items():
                if filename.endswith(ext):
                    command, pyver = dist
                    self.announce('[%s] distribution type %s pyver %s' % (
                        self.get_command_name(), command, pyver),
                        log.DEBUG)
                    break

            if command is not None:
                self.announce('[%s] including distribution %s' % (
                    self.get_command_name(), os.path.basename(filename)),
                    log.INFO)
                getattr(self.distribution, 'dist_files', []).append(
                    (command, pyver, filename))

        orig.upload.run(self)
