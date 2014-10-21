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
import email
import io
import itertools
import operator
import os
import sys

import pkg_resources

from pbr import git
from pbr.pkgversion import semantic


def _is_int(string):
    try:
        int(string)
        return True
    except ValueError:
        return False


def _parse_type(segment):
    # Discard leading digits (the 0 in 0a1)
    isdigit = operator.methodcaller('isdigit')
    segment = ''.join(itertools.dropwhile(isdigit, segment))
    isalpha = operator.methodcaller('isalpha')
    prerelease_type = ''.join(itertools.takewhile(isalpha, segment))
    prerelease = segment[len(prerelease_type)::]
    return prerelease_type, int(prerelease)


def from_pip_string(version_string):
    """Create a SemanticVersion from a pip version string.

    This method will parse a version like 1.3.0 into a SemanticVersion.

    This method is responsible for accepting any version string that any
    older version of pbr ever created.

    Therefore: versions like 1.3.0a1 versions are handled, parsed into a
    canonical form and then output - resulting in 1.3.0.0a1.
    Pre pbr-semver dev versions like 0.10.1.3.g83bef74 will be parsed but
    output as 0.10.1.dev3.g83bef74.

    :raises ValueError: Never tagged versions sdisted by old pbr result in
        just the git hash, e.g. '1234567' which poses a substantial problem
        since they collide with the semver versions when all the digits are
        numerals. Such versions will result in a ValueError being thrown if
        any non-numeric digits are present. They are an exception to the
        general case of accepting anything we ever output, since they were
        never intended and would permanently mess up versions on PyPI if
        ever released - we're treating that as a critical bug that we ever
        made them and have stopped doing that.
    """
    input_components = version_string.split('.')
    # decimals first (keep pre-release and dev/hashes to the right)
    components = [c for c in input_components if c.isdigit()]
    digit_len = len(components)
    if digit_len == 0:
        raise ValueError('Invalid version %r' % version_string)
    elif digit_len < 3:
        if (digit_len < len(input_components) and
                input_components[digit_len][0].isdigit()):
            # Handle X.YaZ - Y is a digit not a leadin to pre-release.
            mixed_component = input_components[digit_len]
            last_component = ''.join(itertools.takewhile(
                lambda x: x.isdigit(), mixed_component))
            components.append(last_component)
            input_components[digit_len:digit_len + 1] = [
                last_component, mixed_component[len(last_component):]]
            digit_len += 1
        components.extend([0] * (3 - digit_len))
    components.extend(input_components[digit_len:])
    major = int(components[0])
    minor = int(components[1])
    dev_count = None
    prerelease_type = None
    prerelease = None
    githash = None

    if _is_int(components[2]):
        patch = int(components[2])
    else:
        # legacy version e.g. 1.2.0a1 (canonical is 1.2.0.0a1)
        # or 1.2.dev4.g1234 or 1.2.b4
        patch = 0
        components[2:2] = [0]
    remainder = components[3:]
    remainder_starts_with_int = False
    try:
        if remainder and int(remainder[0]):
            remainder_starts_with_int = True
    except ValueError:
        pass
    if remainder_starts_with_int:
        # old dev format - 0.1.2.3.g1234
        dev_count = int(remainder[0])
    else:
        if remainder and (remainder[0][0] == '0' or
                          remainder[0][0] in ('a', 'b', 'r')):
            # Current RC/beta layout
            prerelease_type, prerelease = _parse_type(remainder[0])
            remainder = remainder[1:]
        if remainder:
            component = remainder[0]
            if component.startswith('dev'):
                dev_count = int(component[3:])
            elif component.startswith('g'):
                # git hash - so use a dev_count of 1 as we have to have one
                dev_count = 1
                githash = component[1:]
            else:
                raise ValueError(
                    'Unknown remainder %r in %r'
                    % (remainder, version_string))
    if len(remainder) > 1:
            githash = remainder[1][1:]
    return semantic.SemanticVersion(
        major, minor, patch, prerelease_type=prerelease_type,
        prerelease=prerelease, dev_count=dev_count, githash=githash)


def _get_increment_kwargs(tag, git_dir=None):
    """Calculate the sort of semver increment needed from git history.

    Every commit from HEAD to tag is consider for Sem-Ver metadata lines.
    See the pbr docs for their syntax.

    :return: a dict of kwargs for passing into SemanticVersion.increment.
    """
    if tag:
        version_spec = tag + '..HEAD'
    else:
        version_spec = 'HEAD'
    changelog = git.get_changelog_by_spec(version_spec, git_dir)

    header_len = len('    sem-ver:')
    commands = [line[header_len:].strip() for line in changelog.split('\n')
                if line.lower().startswith('    sem-ver:')]
    symbols = set()
    for command in commands:
        symbols.update([symbol.strip() for symbol in command.split(',')])

    result = {}

    def _handle_symbol(symbol, symbols, impact):
        if symbol in symbols:
            result[impact] = True
            symbols.discard(symbol)

    _handle_symbol('bugfix', symbols, 'patch')
    _handle_symbol('feature', symbols, 'minor')
    _handle_symbol('deprecation', symbols, 'minor')
    _handle_symbol('api-break', symbols, 'major')
    for symbol in symbols:
        log.info('[pbr] Unknown Sem-Ver symbol %r' % symbol)
    # We don't want patch in the kwargs since it is not a keyword argument -
    # its the default minimum increment.
    result.pop('patch', None)
    return result


def _get_revno_and_last_tag():
    """Return the commit data about the most recent tag.

    We use git-describe to find this out, but if there are no
    tags then we fall back to counting commits since the beginning
    of time.
    """
    changelog = git.iter_log_oneline()
    row_count = 0
    for row_count, (ignored, tag_set, ignored) in enumerate(changelog):
        version_tags = set()
        for tag in list(tag_set):
            try:
                version_tags.add(from_pip_string(tag))
            except Exception:
                pass
        if version_tags:
            return max(version_tags).release_string(), row_count
    return '', row_count


def _calculate_target_version(target_version=None):
    """Calculate a version from a target version in git_dir.

    This is used for untagged versions only. A new version is calculated as
    necessary based on git metadata - distance to tags, current hash, contents
    of commit messages.

    :param target_version: If None, the last tagged version (or 0 if there are
        no tags yet) is incremented as needed to produce an appropriate target
        version following semver rules. Otherwise target_version is used as a
        constraint - if semver rules would result in a newer version then an
        exception is raised.
    :return: A semver version object.
    """
    tag, distance = _get_revno_and_last_tag()
    last_semver = from_pip_string(tag or '0')

    if distance == 0:
        new_version = last_semver
    else:
        new_version = last_semver.increment(**_get_increment_kwargs(tag))

    if target_version is not None and new_version > target_version:
        raise ValueError(
            'git history requires a target version of %(new)s, but target '
            'version is %(target)s' % dict(new=new_version,
                                           target=target_version))

    if distance == 0:
        return last_semver

    if target_version is not None:
        return target_version.to_dev(distance, git.get_last_commit())
    else:
        return new_version.to_dev(distance, git.get_last_commit())


def get_version_from_git(pre_version=None):
    """Calculate a version string from git.

    If the revision is tagged, return that. Otherwise calculate a semantic
    version description of the tree.

    The number of revisions since the last tag is included in the dev counter
    in the version for untagged versions.

    :param pre_version: If supplied use this as the target version rather than
        inferring one from the last tag + commit messages.
    """
    if git.git_is_installed():
        try:
            target_version = from_pip_string(git.get_version_from_git())
        except Exception:
            if pre_version:
                # not released yet - use pre_version as the target
                target_version = from_pip_string(pre_version)
            else:
                # not released yet - just calculate from git history
                target_version = None

        result = _calculate_target_version(target_version)
        return result.release_string()
    # If we don't know the version, return an empty string so at least
    # the downstream users of the value always have the same type of
    # object to work with.
    try:
        return unicode()
    except NameError:
        return ''


def _get_version_from_pkg_metadata(package_name):
    """Get the version from package metadata if present.

    This looks for PKG-INFO if present (for sdists), and if not looks
    for METADATA (for wheels) and failing that will return None.
    """
    pkg_metadata_filenames = ['PKG-INFO', 'METADATA']
    pkg_metadata = {}
    for filename in pkg_metadata_filenames:
        try:
            with io.open(filename, 'r') as fp:
                pkg_metadata = email.message_from_file(fp)
        except (IOError, OSError):
            continue
        except email.MessageError:
            continue

    # Check to make sure we're in our own dir
    if pkg_metadata.get('Name', None) != package_name:
        return None
    return pkg_metadata.get('Version', None)


def get_package_version(package_name, pre_version=None):
    """Get the version of the project. First, try getting it from PKG-INFO or
    METADATA, if it exists. If it does, that means we're in a distribution
    tarball or that install has happened. Otherwise, if there is no PKG-INFO
    or METADATA file, pull the version from git.

    We do not support setup.py version sanity in git archive tarballs, nor do
    we support packagers directly sucking our git repo into theirs. We expect
    that a source tarball be made from our git repo - or that if someone wants
    to make a source tarball from a fork of our repo with additional tags in it
    that they understand and desire the results of doing that.

    :param pre_version: The version field from setup.cfg - if set then this
        version will be the next release.
    """
    prj_version = os.environ.get(
        'PBR_VERSION',
        os.environ.get('OSLO_PACKAGE_VERSION', None))
    if prj_version:
        return prj_version
    prj_version = _get_version_from_pkg_metadata(package_name)
    if prj_version:
        return prj_version
    prj_version = get_version_from_git(pre_version)
    # Handle http://bugs.python.org/issue11638
    # version will either be an empty unicode string or a valid
    # unicode version string, but either way it's unicode and needs to
    # be encoded.
    if sys.version_info[0] == 2:
        prj_version = prj_version.encode('utf-8')
    if prj_version:
        return prj_version
    raise Exception('Versioning for this project requires either an sdist'
                    ' tarball, or access to an upstream git repository.'
                    ' Are you sure that git is installed?')


def get_version(package):
    """Obtain a version from pkg_resources or setup-time logic if missing.

    This will try to get the version of the package from the pkg_resources
    record associated with the package, and if there is no such record
    falls back to the logic sdist would use.
    """
    try:
        requirement = pkg_resources.Requirement.parse(package)
        provider = pkg_resources.get_provider(requirement)
        result_string = provider.version
    except pkg_resources.DistributionNotFound:
        # The most likely cause for this is running tests in a tree
        # produced from a tarball where the package itself has not been
        # installed into anything. Revert to setup-time logic.
        result_string = get_package_version(package)
    return from_pip_string(result_string)
