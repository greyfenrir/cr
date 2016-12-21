#! /usr/bin/env python
"""
Copyright 2016 Taras Svirinovsky.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import sys
import logging
import yaml
from subprocess import Popen, PIPE, STDOUT

from optparse import OptionParser


class System(object):
    CLOUD = 'cloud'
    CLOUD_DIR = '/mnt/' + CLOUD + '/'
    PARTS_DIR = CLOUD_DIR + 'parts'
    RAID_DIR = CLOUD_DIR + 'raid'

    def __init__(self):
        self.home_path = os.getenv('HOME')
        self.wdav_parts = []
        self.sym_link = os.path.join(self.home_path, System.CLOUD)
        self.log = None
        self.set_logging()

    def set_logging(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler(sys.stdout)
        self.log.addHandler(console_handler)

    def check_soft(self):
        return True

    def _call(self, args):
        if not len(args):
            raise RuntimeError('No arguments for system call')
        process = Popen(args, stdout=PIPE, stderr=STDOUT)
        lines = process.stdout.readlines()
        return lines

    def check_dirs(self):
        if not os.path.isdir(System.RAID_DIR):
            print('Raid directory not found')
        else:
            print('\nRaid directory info:')
            self._dir_info(System.RAID_DIR)
        if not os.path.isdir(System.PARTS_DIR):
            print('Parts directory not found')
            return

        ls_parts = self._call(['ls', System.PARTS_DIR])
        if not(len(ls_parts)):
            print(System.PARTS_DIR + ' is empty')
            return
        print('\nFound parts:')
        for part in ls_parts:
            self._dir_info(os.path.join(System.PARTS_DIR, part.strip()))

    def _dir_info(self, directory):
        df = self._call(['df', '-h', directory])
        df_parts = [part for part in df[1].split(' ') if part]
        fs = df_parts[0].strip()
        s_total = df_parts[1].strip()
        s_free = df_parts[3].strip()
        print("%s\t%s\t%s\t%s" % (directory, fs, s_total, s_free))

    def mount(self, accounts):
        dirs = self._fill_secrets(accounts)
        self._mount_parts(dirs)
        self._make_raids(accounts, dirs)

    def _make_raids(self, accounts, dirs):
        for prov in accounts:
            parts = [directory for (web_dav, directory) in dirs if web_dav == prov['web-dav']]
            directory = System.RAID_DIR + '.' + prov
            self._call(['mkdir', '-p', directory])
            self._call(['mhddfs', ','.join(parts), directory, '-o', 'allow_other'])  # todo: remove allow_other?

    def _mount_parts(self, dirs):
        for (web_dav, directory) in dirs:
            self._call(['mount', '-t', 'davfs', '-o', 'rw', web_dav, directory])

    def _fill_secrets(self, accounts):
        res_list = []
        secrets_content = []
        for prov in sorted(accounts.keys()):
            for login in sorted(accounts[prov]['logins'].keys()):
                directory = os.path.join(System.PARTS_DIR, prov + '.' + login)
                secrets_content.append(' '.join([directory, login, accounts[prov]['logins'][login]]))
                res_list.append((prov['web-dav'], directory))

        with open('/etc/davfs2/secrets', 'w') as fds:
            fds.writelines(secrets_content)
            os.fchmod(fds, 0600)

        return res_list

    def umount(self):
        pass


class User(object):
    def __init__(self, options):
        self.options = options
        self.sys = System()
        self.config = {}

    def run(self):
        with open('cr.yml') as fds:
            self.config = yaml.load(fds)

        if self.options.status:
            print('status:')
            self.sys.check_dirs()
        if self.options.mount:
            print('mount:')
            self.sys.mount(self.config['accounts'])

    def service_note(self):
        # todo: write time into config
        pass

    def backup(self):
        pass

    def restore(self):
        pass


def main():
    usage = "Usage: cr [options]"
    dsc = "Cloud remember tool v0.1"
    parser = OptionParser(usage=usage, description=dsc)
    parser.add_option('-s', '--status', action='store_true', help="Just show help info")
    parser.add_option('-m', '--mount', action='store_true', help="Mount cloud storages")
    parser.add_option('-u', '--umount', action='store_true', help="Unmount cloud storages")
    parsed_options, parsed_configs = parser.parse_args()

    user_tool = User(parsed_options)
    user_tool.run()

    exit(0)


if __name__ == '__main__':
    main()
