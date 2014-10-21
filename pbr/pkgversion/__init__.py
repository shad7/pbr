#    Copyright 2012 OpenStack Foundation
#    Copyright 2012-2013 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Utilities for consuming the version from pkg_resources.
"""
from __future__ import unicode_literals

from pbr.pkgversion import metadata


class VersionInfo(object):

    def __init__(self, package):
        """Object that understands versioning for a package

        :param package: name of the python package, such as glance, or
                        python-glanceclient
        """
        self.package = package
        self.version = None
        self._cached_version = None
        self._semantic = None

    def __str__(self):
        """Make the VersionInfo object behave like a string."""
        return self.version_string()

    def __repr__(self):
        """Include the name."""
        return 'pbr.version.VersionInfo(%s:%s)' % (
            self.package, self.version_string())

    def release_string(self):
        """Return the full version of the package.

        This including suffixes indicating VCS status.
        """
        return self.semantic_version().release_string()

    def semantic_version(self):
        """Return the SemanticVersion object for this version."""
        if self._semantic is None:
            self._semantic = metadata.get_version(self.package)
        return self._semantic

    def version_string(self):
        """Return the short version minus any alpha/beta tags."""
        return self.semantic_version().brief_string()

    # Compatibility functions
    canonical_version_string = version_string
    version_string_with_vcs = release_string

    def cached_version_string(self, prefix=''):
        """Return a cached version string.

        This will return a cached version string if one is already cached,
        irrespective of prefix. If none is cached, one will be created with
        prefix and then cached and returned.
        """
        if not self._cached_version:
            self._cached_version = '{0}{1}'.format(prefix,
                                                   self.version_string())
        return self._cached_version
