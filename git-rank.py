#!/usr/bin/env python
import subprocess
import sys
import re

MAX_NAME_LEN = 43


def trim_name(str):
    length = MAX_NAME_LEN - 4
    return str[:length] + (str[length:] and '..')


def get_stats():
    command = ['git', 'log', '--numstat', '--pretty=format:+%an (%ae)']
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    output = process.stdout
    return parse_log(output)


def parse_log(log):

    class parse_commit_data(object):
        # temp class for commit stats being parsed
        user = None
        added = 0
        removed = 0
        files = None

        @classmethod
        def commit_stat(cls):
            return CommitStat(cls.user, cls.added, cls.removed, cls.files)

        @classmethod
        def reset(cls, user):
            cls.user = user
            cls.added = 0
            cls.removed = 0
            cls.files = set()

    user_stats = User()

    for idx, line in enumerate(log):
        line = line.strip()
        if line == '':
            continue

        if line.startswith('+'):
            # process previous item commit data
            if parse_commit_data.user is not None and len(parse_commit_data.files) > 0:
                user_stats[parse_commit_data.user].add(parse_commit_data.commit_stat())
            # reset count and remove '+'
            parse_commit_data.reset(line[1:])
        else:
            # gather single file data
            match = re.match(r'^\s*(\d*)\t(\d*)\t(.*)', line, re.MULTILINE)
            if not match:
                raise ValueError('Could not parse commit data')

            added, removed, filename = match.group(1, 2, 3)
            parse_commit_data.removed += int(removed)
            parse_commit_data.added += int(added)
            parse_commit_data.files.add(filename)

            # final commit
            if parse_commit_data.user is not None and len(parse_commit_data.files) >= 1:
                user_stats[parse_commit_data.user].add(parse_commit_data.commit_stat())

    return user_stats


class User(object):
    # users and their CommitStats
    def __init__(self):
        self._stats = {}
        # sort by diff
        self._orderfield = 'diff'

    def __getitem__(self, user):
        # a users CommitStats
        if user not in self._stats:
            self._stats[user] = CommitStats(user)
        return self._stats[user]

    def __iter__(self):
        # iter for sorted keys of the User()
        def stat_key(stat):
            # sort CommitStats by this
            return stat.num_files_changed()

        # get CommitStats objects
        stats = self._stats.values()
        # get each CommitStat key (user)
        stats = map(lambda statset: statset.name(), stats)

        stats.reverse()
        return iter(stats)

    def __len__(self):
        return len(self._stats.keys())


class CommitStat(object):
    # the stats of one commit
    def __init__(self, user, added, removed, files):
        self._user = user
        self._removed = removed
        self._added = added
        self._files = files

    def num_files_changed(self):
        return len(self._files)

    def user(self):
        return self._user

    def added(self):
        return self._added

    def removed(self):
        return self._removed

    def diff(self):
        return self._added - self._removed


class CommitStats(object):
    # combined CommitStat
    def __init__(self, name=None):
        if name is None:
            name = ''

        self._name = name
        self._added = 0
        self._removed = 0
        self._commits = []
        self._files = set()

    def num_files_changed(self):
        return len(self._files)

    def commits(self):
        return len(self._commits)

    def added(self):
        return self._added

    def removed(self):
        return self._removed

    def diff(self):
        return self._added - self._removed

    def name(self):
        return self._name

    def add(self, commit_stat):
        # add to CommitStat, gather counts.
        if not isinstance(commit_stat, CommitStat):
            raise TypeError('add() requires CommitStat type')

        self._added += commit_stat._added
        self._removed += commit_stat._removed
        self._files.update(commit_stat._files)
        self._commits.append(commit_stat)

if __name__ == '__main__':
    stats = get_stats()

    if len(stats) < 1:
        print 'No commits found, exiting'
        sys.exit('0')

    # print heading
    print '\033[1m{0}{1}{2}{3}{4}{5}\033[0m'.format('{0: <{1}}'.format('user', MAX_NAME_LEN),
                                                    '{0: <8}'.format('commits'),
                                                    '{0: <8}'.format('files'),
                                                    '{0: <8}'.format('added'),
                                                    '{0: <8}'.format('removed'),
                                                    '{0: <8}'.format('diff'))
    # print stats
    for user in stats:
        print '{0}{1}{2}{3}{4}{5}'.format('{0: <{1}}'.format(trim_name(user), MAX_NAME_LEN),
                                          '{0: <8}'.format(stats[user].commits()),
                                          '{0: <8}'.format(stats[user].num_files_changed()),
                                          '{0: <8}'.format(stats[user].added()),
                                          '{0: <8}'.format(stats[user].removed()),
                                          '{0: <8}'.format(stats[user].diff()))