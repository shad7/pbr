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


class SemanticVersion(object):
    """A pure semantic version independent of serialisation.

    See the pbr doc 'semver' for details on the semantics.
    """

    def __init__(self, major, minor=0, patch=0, prerelease_type=None,
                 prerelease=None, dev_count=None, githash=None):
        """Create a SemanticVersion.

        :param major: Major component of the version.
        :param minor: Minor component of the version. Defaults to 0.
        :param patch: Patch level component. Defaults to 0.
        :param prerelease_type: What sort of prerelease version this is -
            one of a(alpha), b(beta) or rc(release candidate).
        :param prerelease: For prerelease versions, what number prerelease.
            Defaults to 0.
        :param dev_count: How many commits since the last release.
        :param githash: What tree hash is this version for.

        :raises: ValueError if both a prerelease version and dev_count or
        githash are supplied. This is because semver (see the pbr semver
        documentation) does not permit both a prerelease version and a dev
        marker at the same time.
        """
        self._major = major
        self._minor = minor
        self._patch = patch
        self._prerelease_type = prerelease_type
        self._prerelease = prerelease
        if self._prerelease_type and not self._prerelease:
            self._prerelease = 0
        self._dev_count = dev_count
        self._githash = githash
        if prerelease_type is not None and dev_count is not None:
            raise ValueError(
                'invalid version: cannot have prerelease and dev strings %s %s'
                % (prerelease_type, dev_count))

    def __eq__(self, other):
        if not isinstance(other, SemanticVersion):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return sum(map(hash, self.__dict__.values()))

    def __lt__(self, other):
        """Compare self and other, another Semantic Version."""
        # NB(lifeless) this could perhaps be rewritten as
        # lt (tuple_of_one, tuple_of_other) with a single check for
        # the typeerror corner cases - that would likely be faster
        # if this ever becomes performance sensitive.
        if not isinstance(other, SemanticVersion):
            raise TypeError('ordering to non-SemanticVersion is undefined')
        this_tuple = (self._major, self._minor, self._patch)
        other_tuple = (other._major, other._minor, other._patch)
        if this_tuple < other_tuple:
            return True
        elif this_tuple > other_tuple:
            return False
        if self._prerelease_type:
            if other._prerelease_type:
                # Use the a < b < rc cheat
                this_tuple = (self._prerelease_type, self._prerelease)
                other_tuple = (other._prerelease_type, other._prerelease)
                return this_tuple < other_tuple
            elif other._dev_count:
                raise TypeError(
                    'ordering pre-release with dev builds is undefined')
            else:
                return True
        elif self._dev_count:
            if other._dev_count:
                if self._dev_count < other._dev_count:
                    return True
                elif self._dev_count > other._dev_count:
                    return False
                elif self._githash == other._githash:
                    # == it not <
                    return False
                raise TypeError(
                    'same version with different hash has no defined order')
            elif other._prerelease_type:
                raise TypeError(
                    'ordering pre-release with dev builds is undefined')
            else:
                return True
        else:
            # This is not pre-release.
            # If the other is pre-release or dev, we are greater, which is ! <
            # If the other is not pre-release, we are equal, which is ! <
            return False

    def __le__(self, other):
        return self == other or self < other

    def __ge__(self, other):
        return not self < other

    def __gt__(self, other):
        return not self <= other

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return 'pbr.version.SemanticVersion(%s)' % self.release_string()

    def brief_string(self):
        """Return the short version minus any alpha/beta tags."""
        return '%s.%s.%s' % (self._major, self._minor, self._patch)

    def debian_string(self):
        """Return the version number to use when building a debian package.

        This translates the PEP440/semver precedence rules into Debian version
        sorting operators.
        """
        return self._long_version('~', '+g')

    def decrement(self, minor=False, major=False):
        """Return a decremented SemanticVersion.

        Decrementing versions doesn't make a lot of sense - this method only
        exists to support rendering of pre-release versions strings into
        serialisations (such as rpm) with no sort-before operator.

        The 9999 magic version component is from the spec on this - pbr-semver.

        :return: A new SemanticVersion object.
        """
        if self._patch:
            new_patch = self._patch - 1
            new_minor = self._minor
            new_major = self._major
        else:
            new_patch = 9999
            if self._minor:
                new_minor = self._minor - 1
                new_major = self._major
            else:
                new_minor = 9999
                if self._major:
                    new_major = self._major - 1
                else:
                    new_major = 0
        return SemanticVersion(
            new_major, new_minor, new_patch)

    def increment(self, minor=False, major=False):
        """Return an incremented SemanticVersion.

        The default behaviour is to perform a patch level increment. When
        incrementing a prerelease version, the patch level is not changed
        - the prerelease serial is changed (e.g. beta 0 -> beta 1).

        Incrementing non-pre-release versions will not introduce pre-release
        versions - except when doing a patch incremental to a pre-release
        version the new version will only consist of major/minor/patch.

        :param minor: Increment the minor version.
        :param major: Increment the major version.
        :return: A new SemanticVersion object.
        """
        if self._prerelease_type:
            new_prerelease_type = self._prerelease_type
            new_prerelease = self._prerelease + 1
            new_patch = self._patch
        else:
            new_prerelease_type = None
            new_prerelease = None
            new_patch = self._patch + 1
        if minor:
            new_minor = self._minor + 1
            new_patch = 0
            new_prerelease_type = None
            new_prerelease = None
        else:
            new_minor = self._minor
        if major:
            new_major = self._major + 1
            new_minor = 0
            new_patch = 0
            new_prerelease_type = None
            new_prerelease = None
        else:
            new_major = self._major
        return SemanticVersion(
            new_major, new_minor, new_patch,
            new_prerelease_type, new_prerelease)

    def _long_version(self, pre_separator, hash_separator, rc_marker=''):
        """Construct a long string version of this semver.

        :param pre_separator: What separator to use between components
            that sort before rather than after. If None, use . and lower the
            version number of the component to preserve sorting. (Used for
            rpm support)
        :param hash_separator: What separator to use to append the git hash.
        """
        if ((self._prerelease_type or self._dev_count)
                and pre_separator is None):
            segments = [self.decrement().brief_string()]
            pre_separator = '.'
        else:
            segments = [self.brief_string()]
        if self._prerelease_type:
            segments.append(
                '%s%s%s%s' % (pre_separator, rc_marker, self._prerelease_type,
                              self._prerelease))
        if self._dev_count:
            segments.append(pre_separator)
            segments.append('dev')
            segments.append(self._dev_count)
            if self._githash:
                segments.append(hash_separator)
                segments.append(self._githash)
        return ''.join(str(s) for s in segments)

    def release_string(self):
        """Return the full version of the package.

        This including suffixes indicating VCS status.
        """
        return self._long_version('.', '.g', '0')

    def rpm_string(self):
        """Return the version number to use when building an RPM package.

        This translates the PEP440/semver precedence rules into RPM version
        sorting operators. Because RPM has no sort-before operator (such as the
        ~ operator in dpkg),  we show all prerelease versions as being versions
        of the release before.
        """
        return self._long_version(None, '+g')

    def to_dev(self, dev_count, githash):
        """Return a development version of this semver.

        :param dev_count: The number of commits since the last release.
        :param githash: The git hash of the tree with this version.
        """
        return SemanticVersion(
            self._major, self._minor, self._patch, dev_count=dev_count,
            githash=githash)

    def to_release(self):
        """Discard any pre-release or dev metadata.

        :return: A new SemanticVersion with major/minor/patch the same as this
            one.
        """
        return SemanticVersion(self._major, self._minor, self._patch)

    def version_tuple(self):
        """Present the version as a version_info tuple.

        For documentation on version_info tuples see the Python
        documentation for sys.version_info.

        Since semver and PEP-440 represent overlapping but not subsets of
        versions, we have to have some heuristic / mapping rules:
         - a/b/rc take precedence.
         - if there is no pre-release version the dev version is used.
         - serial is taken from the dev/a/b/c component.
         - final non-dev versions never get serials.
        """
        segments = [self._major, self._minor, self._patch]
        if self._prerelease_type:
            type_map = {'a': 'alpha',
                        'b': 'beta',
                        'rc': 'candidate',
                        }
            segments.append(type_map[self._prerelease_type])
            segments.append(self._prerelease)
        elif self._dev_count:
            segments.append('dev')
            segments.append(self._dev_count - 1)
        else:
            segments.append('final')
            segments.append(0)
        return tuple(segments)
