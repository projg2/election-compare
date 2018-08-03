#!/usr/bin/env python
# Get election results using devotee.
# (c) 2018 Michał Górny
# Released under the terms of the 2-clause BSD license

from __future__ import print_function

import argparse
import json
import os
import os.path
import re
import shutil
import subprocess
import sys
import tempfile

import master2json


class DevoteeWrapper(object):
    """
    Maintains a temporary directory for devotee.
    """

    OPTION_RE = re.compile(r'\s*Option (?P<index>\w+) "(?P<name>\w+)"\s*')

    def __init__(self, repo, election):
        self.repo = repo
        self.election = election
        self.datadir = os.path.join(repo, 'completed', self.election)
        assert os.path.isdir(self.datadir)

    def __enter__(self):
        self.tempdir = tempfile.mkdtemp()

        # devotee.conf
        with open(os.path.join(self.tempdir, 'devotee.conf'), 'w') as f:
            f.write('''
Top_Dir = {path};
Pass_Word = {name};
Vote_Name = {name};
Vote_Ref  = {name};
Secret = 0;
Encrypted_Ack = 0;
Vote_Taker_Name  = N/A;
Vote_Taker_EMAIL = na@example.com;
UUID = %REPLACE_UUID%;
Title = {name};
Start_Time = 0;
End_Time = 0;'''.format(name=self.election, path=self.tempdir))

            # now add the ballot
            with open(os.path.join(self.datadir, 'ballot-' + self.election),
                      'r') as ballotf:
                self.ballot = ballotf.read().splitlines()

            new_ballot = ''
            for i, cand in enumerate(self.ballot):
                new_ballot += '''
Majority_{n:1X} = 0;
Option_{n:1X} = {name};'''.format(n=i+1, name=cand)

            f.write(new_ballot.rstrip(';') + '\n')

        # quorum.txt
        with open(os.path.join(self.tempdir, 'quorum.txt'), 'w') as f:
            f.write('Quorum = 0')

        # read the master ballot
        with open(os.path.join(self.datadir, 'master-' + self.election),
                  'r') as f:
            self.master_ballot = master2json.stream2dict(f)

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        shutil.rmtree(self.tempdir)

    def run(self, repo):
        # devotee outputs only first choice, so we need to iterate it
        nominees_left = set(self.ballot)
        out = []

        while nominees_left:
            # write tally
            with open(os.path.join(self.tempdir, 'tally.txt'), 'w') as f:
                for k, v in self.master_ballot.items():
                    votes = []
                    for o in range(len(self.ballot)):
                        votes.append('-')
                    for i, cands in enumerate(v):
                        assert (i+1) < 16
                        for cand in cands:
                            if cand not in nominees_left:
                                continue
                            votes[self.ballot.index(cand)] = '{:1X}'.format(i+1)
                    f.write('V: {} {}\n'.format(''.join(votes), k))

            # run dvt-rslt
            s = subprocess.Popen(['perl', '-I' + os.path.join(repo, 'lib'),
                                  os.path.join(repo, 'dvt-rslt'),
                                  '--mkdir', '--nosign_ack', '--noneed_gpg',
                                  '--noneed_pgp', '--noneed_ldap',
                                  '--config_file',
                                  os.path.join(self.tempdir, 'devotee.conf')],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            stdout, stderr = s.communicate()
            ret = s.wait()

            if ret != 0:
                print('dvt-rslt failed:')
                print(stderr.decode())
                sys.exit(1)

            # results are written to file
            with open(os.path.join(self.tempdir, 'results.txt'), 'r') as f:
                in_list = False
                round_out = []
                for l in f:
                    if l.strip() == 'The winners are:':
                        in_list = True
                    elif in_list:
                        if not l.strip():
                            break
                        else:
                            m = self.OPTION_RE.match(l)
                            assert m is not None
                            round_out.append(m.group('name'))

            if not round_out:
                print('devotee did not print results (argv!)', file=sys.stderr)
                out.append('__error__')
                break
            print('Next winner: {}'.format(round_out), file=sys.stderr)
            out.append(round_out)
            for o in round_out:
                nominees_left.remove(o)

        return out


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('election', help='Election name')
    argp.add_argument('--devotee',
            default='devotee',
            help='Location of devotee repo')
    argp.add_argument('--repo',
            default='elections',
            help='Location of elections repo')
    argp.add_argument('-o', '--output', type=argparse.FileType('w'),
            default=sys.stdout,
            help='Output file (outputs to stdout by default)')
    vals = argp.parse_args()

    with DevoteeWrapper(vals.repo, vals.election) as devotee:
        json.dump(devotee.run(vals.devotee), vals.output)
        vals.output.write('\n')


if __name__ == '__main__':
    main()
