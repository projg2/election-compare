#!/usr/bin/env python
# Get election results using the Gentoo countify tool.
# (c) 2018 Michał Górny
# Released under the terms of the 2-clause BSD license

import argparse
import json
import os
import os.path
import shutil
import subprocess
import sys
import tempfile


class CountifyWrapper(object):
    """
    Maintains a temporary fake home directory for countify to use.
    """

    def __init__(self, repo, election):
        self.repo = repo
        self.election = election
        self.datadir = os.path.join(repo, 'completed', self.election)
        assert os.path.isdir(self.datadir)

    def __enter__(self):
        self.tempdir = tempfile.mkdtemp()
        self.newdatadir = os.path.join(self.tempdir, self.election)
        self.resdir = os.path.join(self.tempdir, 'results-' + self.election)
        os.mkdir(self.newdatadir)
        os.mkdir(self.resdir)

        # copy scripts
        shutil.copyfile(os.path.join(self.repo, 'countify'),
                        os.path.join(self.tempdir, 'countify'))
        shutil.copyfile(os.path.join(self.repo, 'Votify.pm'),
                        os.path.join(self.tempdir, 'Votify.pm'))

        # copy data
        shutil.copyfile(os.path.join(self.datadir, 'ballot-' + self.election),
                        os.path.join(self.newdatadir, 'ballot-' + self.election))

        # copy results
        shutil.copyfile(os.path.join(self.datadir, 'master-' + self.election),
                        os.path.join(self.resdir, 'master-' + self.election))

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        shutil.rmtree(self.tempdir)

    def run(self, verbose=False):
        s = subprocess.Popen(['perl', os.path.join(self.tempdir, 'countify'),
                              '--rank', self.election],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             env={'HOME': self.tempdir})
        stdout, stderr = s.communicate()
        ret = s.wait()

        if ret != 0:
            print('Countify failed:')
            print(stderr.decode())
            sys.exit(1)

        in_list = False
        out = []
        for l in stdout.decode().splitlines():
            if l == 'Final ranked list:':
                in_list = True
            elif in_list:
                out.append(l.split())
        if verbose:
            print(stdout.decode(), file=sys.stderr)

        return out


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('election', help='Election name')
    argp.add_argument('--repo',
            default='elections',
            help='Location of elections repo')
    argp.add_argument('-o', '--output', type=argparse.FileType('w'),
            default=sys.stdout,
            help='Output file (outputs to stdout by default)')
    argp.add_argument('-v', '--verbose', action='store_true',
            help='Print verbose countify output')
    vals = argp.parse_args()

    with CountifyWrapper(vals.repo, vals.election) as countify:
        json.dump(countify.run(verbose=vals.verbose), vals.output)
        vals.output.write('\n')


if __name__ == '__main__':
    main()
