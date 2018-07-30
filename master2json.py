#!/usr/bin/env python
# Convert master ballot from countify format to JSON dict.
# (c) 2018 Michał Górny
# Released under the terms of the 2-clause BSD license

import argparse
import json
import sys


def stream2dict(master_ballot_stream):
    """
    Process master ballot data and return a dict representing the votes.

    The dict structure:
    {confirmation-id: [[1st-preference, ...], [2nd-preference, ...], ...]}
    """

    out = {}
    curr = None

    for x in master_ballot_stream:
        if x.startswith('----'):
            curr = []
            voter = x[23:27]
            out[voter] = curr
        else:
            assert(curr is not None)
            curr.append(x.split())

    return out


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument('masterballot', type=argparse.FileType('r'))
    argp.add_argument('-o', '--output', type=argparse.FileType('w'),
            default=sys.stdout)
    vals = argp.parse_args()
    json.dump(stream2dict(vals.masterballot), vals.output,
              sort_keys=True)
    vals.output.write('\n')


if __name__ == '__main__':
    main()
