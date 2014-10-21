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
import re
import sys

import pkg_resources

from pbr import common


REQUIREMENTS_FILES = ('requirements.txt', 'tools/pip-requires')
TEST_REQUIREMENTS_FILES = ('test-requirements.txt', 'tools/test-requires')


def _any_existing(file_list):
    return [f for f in file_list if os.path.exists(f)]


def _get_requirements_files():
    files = os.environ.get('PBR_REQUIREMENTS_FILES')
    if files:
        return tuple(f.strip() for f in files.split(','))
    # Returns a list composed of:
    # - REQUIREMENTS_FILES with -py2 or -py3 in the name
    #   (e.g. requirements-py3.txt)
    # - REQUIREMENTS_FILES
    return (list(map(('-py' + str(sys.version_info[0])).join,
                     map(os.path.splitext, REQUIREMENTS_FILES)))
            + list(REQUIREMENTS_FILES))


def _newer_requires_files(egg_info_dir):
    """Check to see if any of the requires files are newer than egg-info."""
    for target, sources in (('requires.txt', _get_requirements_files()),
                            ('test-requires.txt', TEST_REQUIREMENTS_FILES)):
        target_path = os.path.join(egg_info_dir, target)
        for src in _any_existing(sources):
            if (not os.path.exists(target_path) or
                    os.path.getmtime(target_path)
                    < os.path.getmtime(src)):
                return True
    return False


def _copy_test_requires_to(egg_info_dir):
    """Copy the requirements file to egg-info/test-requires.txt."""
    with io.open(os.path.join(egg_info_dir, 'test-requires.txt'), 'w') as dest:
        for source in _any_existing(TEST_REQUIREMENTS_FILES):
            with io.open(source, 'r') as src:
                dest.write(src.read().rstrip('\n') + '\n')


def _get_reqs_from_files(requirements_files):
    for requirements_file in _any_existing(requirements_files):
        with io.open(requirements_file, 'r') as fil:
            return fil.read().split('\n')
    return []


def parse_requirements(requirements_files=None):

    if requirements_files is None:
        requirements_files = _get_requirements_files()

    requirements = []
    try:
        import pip

        for req_file in _any_existing(requirements_files):
            pip_install_reqs = pip.req.parse_requirements(req_file)

            # parse_requirements returns a generator so need
            # get the full list of requirements back
            for pip_install_req in list(pip_install_reqs):

                # pip has a gap where some URLs are not processed through
                # initial go through so process the URL and convert to
                # package resource Requirement like pip normally does
                if not pip_install_req.req:
                    pip_install_req.req = pkg_resources.Requirement.parse(
                        pip.index.get_requirement_from_url(
                            pip_install_req.url).replace('==', '>='))

                name_spec = str(pip_install_req.req)
                project_name = pip_install_req.req.project_name

                # check to determine if the package name with spec is the
                # same as the package name; that could be perfectly normal
                # where requirement line is 'discover'. But that might not
                # be the case for other scenarios.
                if name_spec == project_name:
                    # if the package name with spec is not equal to the
                    # formatted package name (eg zip file discover-1.3.1)
                    # that would mean that no spec was found so package with
                    # spec had been same as package name. Override package
                    # name with spec to be the formatted package name.
                    formatted_prj_name = pip.index.package_to_requirement(
                        project_name)
                    if name_spec != formatted_prj_name:
                        # FIXME(kenjones):
                        # The default behavior by pip is to assume spec is
                        # equal to the version included in the filename from
                        # a url, but pbr has historically assume greater
                        # than or equal. To keep it backwards compatiable
                        # for the time being, replace default spec with
                        # pbr default
                        name_spec = formatted_prj_name.replace('==', '>=')

                        # also means the package name was mis-identified so
                        # update package name.
                        project_name = formatted_prj_name.split('==')[0]
                    else:
                        # if we made it this far that means all values were
                        # the same and now it appears that no specs had been
                        # found previously but a URL was found. So try to
                        # get package name and spec from the url
                        # (eg #egg=discover-1.3.1)
                        if (not pip_install_req.req.specs and
                                pip_install_req.url):

                            temp = str(pkg_resources.Requirement.parse(
                                pip.index.get_requirement_from_url(
                                    pip_install_req.url)))
                            # need to make sure what value came from the URL
                            # starts with the identified package name
                            # otherwise the URL already had the package name
                            # remove from it so avoid using that value.
                            # The editable flag results in different parsing
                            # such that information on the URL would provide
                            # complete package + op + version
                            if (any(i.isdigit() for i in temp) and
                                    temp.startswith(project_name) and
                                    pip_install_req.editable):
                                # FIXME(kenjones):
                                # The default behavior by pip is to assume
                                # spec is equal to the version included in the
                                # filename from a url, but pbr has
                                # historically assume greater than or equal.
                                # To keep it backwards compatiable for the
                                # time being, replace default spec with
                                # pbr default
                                name_spec = temp.replace('==', '>=')

                # if after all of that we check that package name from spec
                # starts with the identified package name, otherwise we have
                # and issue and should log it and skip
                if not name_spec.startswith(project_name):
                    log.info(
                        '[pbr] Excluding {0}: {1}'.format(
                            project_name, 'Requirement entry mal-formed.'))
                    continue

                # the -f entries are taken care by the pip parser such as
                # not to be included in the requirements list; resulting
                # in same functionality as existing pbr

                requirements.append(name_spec)

    except ImportError as imperr:
        # pip is listed in pbr requirements.txt but it is used
        # indirectly via shell command. Adding a direct dependency
        # could back fire so check for ImportError; log the issue
        # and return empty requirements list
        log.info('[pbr] pip required but not found: {0}'.format(imperr))

    return requirements


def parse_dependency_links(requirements_files=None):
    if requirements_files is None:
        requirements_files = _get_requirements_files()
    dependency_links = []
    # dependency_links inject alternate locations to find packages listed
    # in requirements
    for line in _get_reqs_from_files(requirements_files):
        # skip comments and blank lines
        if re.match(r'(\s*#)|(\s*$)', line):
            continue
        # lines with -e or -f need the whole line, minus the flag
        if re.match(r'\s*-[ef]\s+', line):
            dependency_links.append(re.sub(r'\s*-[ef]\s+', '', line))
        # lines that are only urls can go in unmolested
        elif re.match(r'\s*https?:', line):
            dependency_links.append(line)
    return dependency_links


def pip_install(links, requires, root=None, option_dict=None):
    if option_dict is None:
        option_dict = dict()
    if common.get_boolean_option(option_dict,
                                 'skip_pip_install',
                                 'SKIP_PIP_INSTALL'):
        return
    cmd = [sys.executable, '-m', 'pip.__init__', 'install']
    if root:
        cmd.append('--root=%s' % root)
    for link in links:
        cmd.append('-f')
        cmd.append(link)

    # NOTE(ociuhandu): popen on Windows does not accept unicode strings
    common.run_shell_command(
        cmd + requires,
        throw_on_error=True, buffer=False, env=dict(PIP_USE_WHEEL=b'true'))


class PipInstallTestRequires(object):
    """Mixin class to install test-requirements.txt before running tests."""

    def install_test_requirements(self):

        links = parse_dependency_links(TEST_REQUIREMENTS_FILES)
        if self.distribution.tests_require:
            option_dict = self.distribution.get_option_dict('pbr')
            pip_install(
                links, self.distribution.tests_require,
                option_dict=option_dict)

    def pre_run(self):
        self.egg_name = pkg_resources.safe_name(self.distribution.get_name())
        self.egg_info = '%s.egg-info' % pkg_resources.to_filename(
            self.egg_name)
        if (not os.path.exists(self.egg_info) or
                _newer_requires_files(self.egg_info)):
            ei_cmd = self.get_finalized_command('egg_info')
            ei_cmd.run()
            self.install_test_requirements()
            _copy_test_requires_to(self.egg_info)
