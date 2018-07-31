#!/usr/bin/env python
# Run election results over all available tools and compare results.
# (c) 2018 Michał Górny
# Released under the terms of the 2-clause BSD license

from __future__ import print_function

import argparse
import json
import os
import os.path
import subprocess
import sys


TOOLS = ('countify', 'devotee')


def get_all_elections(repo):
    return sorted(os.listdir(os.path.join(repo, 'completed')))


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('election', help='Election name', nargs='*')
    argp.add_argument('--repo',
            default='elections',
            help='Location of elections repo')
    vals = argp.parse_args()

    if not vals.election:
        vals.election = get_all_elections(vals.repo)

    for election in vals.election:
        print('{}:'.format(election), end='')
        res = {}
        for tool in TOOLS:
            print(' {}'.format(tool), end='', flush=True)
            s = subprocess.Popen(['./run-{}.py'.format(tool),
                                 '--repo', vals.repo,
                                 election],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            stdout, stderr = s.communicate()
            retval = s.wait()
            if retval != 0:
                print()
                print('run-{} failed:'.format(tool))
                print(stderr.decode())
                sys.exit(1)
            res[tool] = json.loads(stdout)

        k1, v1 = res.popitem()
        for k2, v2 in res.items():
            if v1 != v2:
                print()
                print('MISMATCH FOUND:')
                print('  {}: {}'.format(k1, v1))
                print('  {}: {}'.format(k2, v2))
                sys.exit(1)

        print(' OK')


if __name__ == '__main__':
    main()
