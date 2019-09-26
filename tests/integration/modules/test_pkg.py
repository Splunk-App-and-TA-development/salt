# -*- coding: utf-8 -*-

# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals
import os
import pprint

# Import Salt Testing libs
from tests.support.case import ModuleCase
from tests.support.mixins import SaltReturnAssertsMixin
from tests.support.helpers import (
    destructiveTest,
    requires_network,
    requires_salt_modules,
    requires_system_grains)

# Import Salt libs
import salt.utils.pkg
import salt.utils.platform


class PkgModuleTest(ModuleCase, SaltReturnAssertsMixin):
    '''
    Validate the pkg module
    '''

    @classmethod
    def setUpClass(cls):
        cls.ctx = {}
        cls.pkg = 'htop'
        if salt.utils.platform.is_windows():
            cls.pkg = 'putty'
        elif salt.utils.platform.is_darwin():
            os_release = cls.run_function('grains.get', ['osrelease'])
            if int(os_release.split('.')[1]) >= 13:
                cls.pkg = 'wget'

    def setUp(self):
        if 'refresh' not in self.ctx:
            self.run_function('pkg.refresh_db')
            self.ctx['refresh'] = True

    @requires_salt_modules('pkg.list_pkgs')
    def test_list(self):
        '''
        verify that packages are installed
        '''
        ret = self.run_function('pkg.list_pkgs')
        self.assertNotEqual(len(ret.keys()), 0)

    @requires_salt_modules('pkg.version_cmp')
    @requires_system_grains
    def test_version_cmp(self, grains):
        '''
        test package version comparison on supported platforms
        '''
        func = 'pkg.version_cmp'
        if grains['os_family'] == 'Debian':
            lt = ['0.2.4-0ubuntu1', '0.2.4.1-0ubuntu1']
            eq = ['0.2.4-0ubuntu1', '0.2.4-0ubuntu1']
            gt = ['0.2.4.1-0ubuntu1', '0.2.4-0ubuntu1']

        elif grains['os_family'] == 'Suse':
            lt = ['2.3.0-1', '2.3.1-15.1']
            eq = ['2.3.1-15.1', '2.3.1-15.1']
            gt = ['2.3.2-15.1', '2.3.1-15.1']
        else:
            self.skipTest('pkg.version_cmp test has not been configured for \'{}\''.format(grains['os_family']))

        self.assertEqual(self.run_function(func, lt), -1)
        self.assertEqual(self.run_function(func, eq), 0)
        self.assertEqual(self.run_function(func, gt), 1)

    @destructiveTest
    @requires_salt_modules('pkg.mod_repo', 'pkg.del_repo', 'pkg.get_repo')
    @requires_network()
    @requires_system_grains
    def test_mod_del_repo(self, grains):
        '''
        test modifying and deleting a software repository
        '''
        repo = None

        try:
            if grains['os'] == 'Ubuntu':
                repo = 'ppa:otto-kesselgulasch/gimp-edge'
                uri = 'http://ppa.launchpad.net/otto-kesselgulasch/gimp-edge/ubuntu'
                ret = self.run_function('pkg.mod_repo', [repo, 'comps=main'])
                self.assertNotEqual(ret, {})
                ret = self.run_function('pkg.get_repo', [repo])

                self.assertIsInstance(ret, dict,
                                      'The \'pkg.get_repo\' command did not return the excepted dictionary. '
                                      'Output:\n{}'.format(ret))

                self.assertEqual(
                    ret['uri'],
                    uri,
                    msg='The URI did not match. Full return:\n{}'.format(
                        pprint.pformat(ret)
                    )
                )
            elif grains['os_family'] == 'RedHat':
                repo = 'saltstack'
                name = 'SaltStack repo for RHEL/CentOS {0}'.format(grains['osmajorrelease'])
                baseurl = 'http://repo.saltstack.com/yum/redhat/{0}/x86_64/latest/'.format(grains['osmajorrelease'])
                gpgkey = 'https://repo.saltstack.com/yum/rhel{0}/SALTSTACK-GPG-KEY.pub'.format(
                    grains['osmajorrelease'])
                gpgcheck = 1
                enabled = 1
                ret = self.run_function(
                    'pkg.mod_repo',
                    [repo],
                    name=name,
                    baseurl=baseurl,
                    gpgkey=gpgkey,
                    gpgcheck=gpgcheck,
                    enabled=enabled,
                )
                # return data from pkg.mod_repo contains the file modified at
                # the top level, so use next(iter(ret)) to get that key
                self.assertNotEqual(ret, {})
                repo_info = ret[next(iter(ret))]
                self.assertIn(repo, repo_info)
                self.assertEqual(repo_info[repo]['baseurl'], baseurl)
                ret = self.run_function('pkg.get_repo', [repo])
                self.assertEqual(ret['baseurl'], baseurl)
        finally:
            if repo is not None:
                self.run_function('pkg.del_repo', [repo])

    @requires_salt_modules('pkg.owner')
    def test_owner(self):
        '''
        test finding the package owning a file
        '''
        func = 'pkg.owner'
        ret = self.run_function(func, ['/bin/ls'])
        self.assertNotEqual(len(ret), 0)

    @destructiveTest
    @requires_salt_modules('pkg.version', 'pkg.install', 'pkg.remove')
    @requires_network()
    def test_install_remove(self):
        '''
        successfully install and uninstall a package
        '''
        version = self.run_function('pkg.version', [self.pkg])

        def test_install():
            install_ret = self.run_function('pkg.install', [self.pkg])
            self.assertIn(self.pkg, install_ret)

        def test_remove():
            remove_ret = self.run_function('pkg.remove', [self.pkg])
            self.assertIn(self.pkg, remove_ret)

        if version and isinstance(version, dict):
            version = version[self.pkg]

        if version:
            test_remove()
            test_install()
        else:
            test_install()
            test_remove()

    @destructiveTest
    @requires_salt_modules('pkg.hold', 'pkg.unhold', 'pkg.install', 'pkg.version', 'pkg.remove')
    @requires_network()
    @requires_system_grains
    def test_hold_unhold(self, grains):
        '''
        test holding and unholding a package
        '''
        version_lock = None
        lock_pkg = 'yum-plugin-versionlock'

        self.run_function('pkg.install', [self.pkg])
        if grains['os_family'] == 'RedHat':
            version_lock = self.run_function('pkg.version', [lock_pkg])
            if not version_lock:
                self.run_function('pkg.install', [lock_pkg])

        hold_ret = self.run_function('pkg.hold', [self.pkg])
        self.assertIn(self.pkg, hold_ret)
        self.assertTrue(hold_ret[self.pkg]['result'])

        unhold_ret = self.run_function('pkg.unhold', [self.pkg])
        self.assertIn(self.pkg, unhold_ret)
        self.assertTrue(unhold_ret[self.pkg]['result'])

        if grains['os_family'] == 'RedHat':
            if not version_lock:
                self.run_function('pkg.remove', [lock_pkg])
        self.run_function('pkg.remove', [self.pkg])

    @destructiveTest
    @requires_salt_modules('pkg.refresh_db')
    @requires_network()
    @requires_system_grains
    def test_refresh_db(self, grains):
        '''
        test refreshing the package database
        '''
        func = 'pkg.refresh_db'

        rtag = salt.utils.pkg.rtag(self.minion_opts)
        salt.utils.pkg.write_rtag(self.minion_opts)
        self.assertTrue(os.path.isfile(rtag))

        ret = self.run_function(func)
        if not isinstance(ret, dict):
            self.skipTest('Upstream repo did not return coherent results: {}'.format(ret))

        if grains['os_family'] == 'RedHat':
            self.assertIn(ret, (True, None))
        elif grains['os_family'] == 'Suse':
            if not isinstance(ret, dict):
                self.skipTest('Upstream repo did not return coherent results. Skipping test.')
            self.assertNotEqual(ret, {})
        elif grains['os_family'] == 'Suse':
            self.assertNotEqual(ret, {})
            for source, state in ret.items():
                self.assertIn(state, (True, False, None))

        self.assertFalse(os.path.isfile(rtag))

    @requires_salt_modules('pkg.info_installed')
    @requires_system_grains
    def test_pkg_info(self, grains):
        '''
        Test returning useful information on Ubuntu systems.
        '''
        func = 'pkg.info_installed'

        if grains['os_family'] == 'Debian':
            ret = self.run_function(func, ['bash-completion', 'dpkg'])
            keys = ret.keys()
            self.assertIn('bash-completion', keys)
            self.assertIn('dpkg', keys)
        elif grains['os_family'] == 'RedHat':
            ret = self.run_function(func, ['rpm', 'bash'])
            keys = ret.keys()
            self.assertIn('rpm', keys)
            self.assertIn('bash', keys)
        elif grains['os_family'] == 'Suse':
            ret = self.run_function(func, ['less', 'zypper'])
            keys = ret.keys()
            self.assertIn('less', keys)
            self.assertIn('zypper', keys)

    @destructiveTest
    @requires_network()
    @requires_salt_modules('pkg.refresh_db', 'pkg.upgrade', 'pkg.install', 'pkg.list_repo_pkgs', 'pkg.list_upgrades')
    @requires_system_grains
    def test_pkg_upgrade_has_pending_upgrades(self, grains):
        '''
        Test running a system upgrade when there are packages that need upgrading
        '''
        if grains['os_family'] == 'Arch':
            self.skipTest('Arch moved to Python 3.8 and we\'re not ready for it yet')

        func = 'pkg.upgrade'

        # First make sure that an up-to-date copy of the package db is available
        self.run_function('pkg.refresh_db')

        if grains['os_family'] == 'Suse':
            # This test assumes that there are multiple possible versions of a
            # package available. That makes it brittle if you pick just one
            # target, as changes in the available packages will break the test.
            # Therefore, we'll choose from several packages to make sure we get
            # one that is suitable for this test.
            packages = ('hwinfo', 'avrdude', 'diffoscope', 'vim')
            available = self.run_function('pkg.list_repo_pkgs', packages)

            for package in packages:
                try:
                    new, old = available[package][:2]
                except (KeyError, ValueError):
                    # Package not available, or less than 2 versions
                    # available. This is not a suitable target.
                    continue
                else:
                    target = package
                    break
            else:
                # None of the packages have more than one version available, so
                # we need to find new package(s). pkg.list_repo_pkgs can be
                # used to get an overview of the available packages. We should
                # try to find packages with few dependencies and small download
                # sizes, to keep this test from taking longer than necessary.
                self.fail('No suitable package found for this test')

            # Make sure we have the 2nd-oldest available version installed
            ret = self.run_function('pkg.install', [target], version=old)
            if not isinstance(ret, dict):
                if ret.startswith('ERROR'):
                    self.skipTest(
                        'Could not install older {0} to complete '
                        'test.'.format(target)
                    )

            # Run a system upgrade, which should catch the fact that the
            # targeted package needs upgrading, and upgrade it.
            ret = self.run_function(func)

            # The changes dictionary should not be empty.
            if 'changes' in ret:
                self.assertIn(target, ret['changes'])
            else:
                self.assertIn(target, ret)
        else:
            ret = self.run_function('pkg.list_upgrades')
            if ret == '' or ret == {}:
                self.skipTest('No updates available for this machine.  Skipping pkg.upgrade test.')
            else:
                args = []
                if grains['os_family'] == 'Debian':
                    args = ['dist_upgrade=True']
                ret = self.run_function(func, args)
                self.assertNotEqual(ret, {})

    @destructiveTest
    @requires_salt_modules('pkg.remove', 'pkg.list_available', 'pkg.latest_version')
    @requires_system_grains
    def test_pkg_latest_version(self, grains):
        '''
        Check that pkg.latest_version returns the latest version of the uninstalled package.
        The package is not installed. Only the package version is checked.
        '''
        remove = False
        if salt.utils.platform.is_windows():
            cmd_info = self.run_function('pkg.version', [self.pkg])
            remove = False if cmd_info == '' else True
        else:
            cmd_info = self.run_function('pkg.info_installed', [self.pkg])
            if cmd_info != 'ERROR: package {0} is not installed'.format(self.pkg):
                remove = True

        # remove package if its installed
        if remove:
            self.run_function('pkg.remove', [self.pkg])

        cmd_pkg = []
        if grains['os_family'] == 'RedHat':
            cmd_pkg = self.run_function('cmd.run', ['yum list {0}'.format(self.pkg)])
        elif salt.utils.platform.is_windows():
            cmd_pkg = self.run_function('pkg.list_available', [self.pkg])
        elif grains['os_family'] == 'Debian':
            cmd_pkg = self.run_function('cmd.run', ['apt list {0}'.format(self.pkg)])
        elif grains['os_family'] == 'Arch':
            cmd_pkg = self.run_function('cmd.run', ['pacman -Si {0}'.format(self.pkg)])
        elif grains['os_family'] == 'Suse':
            cmd_pkg = self.run_function('cmd.run', ['zypper info {0}'.format(self.pkg)])
        pkg_latest = self.run_function('pkg.latest_version', [self.pkg])
        self.assertIn(pkg_latest, cmd_pkg)
