import collections
import datetime
import os
import re

import yaml

import errors
import names
import utils

class Info(object):
    def __init__(self):
        self._title = None
        self._url = None
        self._author = None
        self._email = None
        self._avatar_path = None
        self._description = None
        self._series = None
        self._nr_of_posts_in_feed = -1

    @property
    def title(self):
        return self._title

    @property
    def url(self):
        return self._url

    @property
    def author(self):
        return self._author

    @property
    def email(self):
        return self._email

    @property
    def avatar_path(self):
        return self._avatar_path

    @property
    def description(self):
        return self._description

    @property
    def series(self):
        return self._series

    @property
    def nr_of_posts_in_feed(self):
        return self._nr_of_posts_in_feed

    @staticmethod
    def Load(info_path):
        assert isinstance(info_path, str)

        info_text = utils.QuickRead(info_path)

        try:
            info_raw = yaml.safe_load(info_text)
        except yaml.YAMLError as e:
            raise errors.Error(str(e))

        if not isinstance(info_raw, dict):
            raise errors.Error('Invalid info file structure')

        info = Info()
        info._title = names.UniformName(utils.Extract(info_raw, 'Title', str))
        info._url = utils.Extract(info_raw, 'URL', str)
        info._author = names.UniformName(utils.Extract(info_raw, 'Author', str))
        info._email = utils.Extract(info_raw, 'Email', str).strip()
        info._avatar_path = utils.Extract(info_raw, 'AvatarPath', str)
        info._description = utils.Extract(info_raw, 'Description', str)

        series_raw = utils.Extract(info_raw, 'Series', list)

        if not all(isinstance(s, str) for s in series_raw):
            raise errors.Error('Invalid Series entry')

        info._series = frozenset(names.UniformName(s) for s in series_raw)

        info._nr_of_posts_in_feed = utils.Extract(info_raw, 'NrOfPostsInFeed', int)

        return info

class Post(object):
    def __init__(self, info):
        assert isinstance(info, Info)

        self._info = info
        self._title = None
        self._date = None
        self._delta = None
        self._series = None
        self._tags = None
        self._paragraphs = None
        self._path = None
        self._next_post = None
        self._prev_post = None
        self._next_post_by_series = None
        self._prev_post_by_series = None

    def __cmp__(self, other):
        assert isinstance(other, Post)

        if self._date < other._date:
            return -1
        elif self._date == other._date:
            return cmp(self._delta, other._delta)
        else:
            return 1

    @property
    def info(self):
        return self._info

    @property
    def title(self):
        return self._title

    @property
    def date(self):
        return self._date

    @property
    def delta(self):
        return self._delta

    @property
    def series(self):
        return self._series

    @property
    def tags(self):
        return self._tags

    @property
    def paragraphs(self):
        return self._paragraphs

    @property
    def path(self):
        return self._path

    @property
    def next_post(self):
        return self._next_post

    @property
    def prev_post(self):
        return self._prev_post

    @property
    def next_post_by_series(self):
        return self._next_post_by_series

    @property
    def prev_post_by_series(self):
        return self._prev_post_by_series

    PATH_RE = re.compile(r'^(\d\d\d\d).(\d\d).(\d\d)(-\d+)?\s*-\s*(.+)$')

    @staticmethod
    def ValidPath(post_path):
        assert isinstance(post_path, str)

        post_path_base = os.path.basename(post_path)
        match_obj = Post.PATH_RE.match(post_path_base)

        return match_obj is not None

    @staticmethod
    def Load(info, post_path, post_path_full):
        assert isinstance(info, Info)
        assert isinstance(post_path, str)
        assert isinstance(post_path_full, str)

        post_path_base = os.path.basename(post_path)
        match_obj = Post.PATH_RE.match(post_path_base)

        if match_obj is None:
            raise errors.Error('Invalid blog post path')

        post_text = utils.QuickRead(post_path_full)

        try:
            post_raw = yaml.safe_load(post_text)
        except yaml.YAMLError as e:
            raise errors.Error(str(e))

        if not isinstance(post_raw, list):
            raise errors.Error('Invalid blog post structure')

        if len(post_raw) < 2:
            raise errors.Error('Invalid blog post structure')

        if not isinstance(post_raw[0], dict):
            raise errors.Error('Invalid blog post structure')

        if len(post_raw[0]) != 1:
            raise errors.Error('Invalid blog post structure')

        if 'Tags' not in post_raw[0]:
            raise errors.Error('Invalid blog post structure')

        tags_raw = post_raw[0]['Tags']
        post_raw = post_raw[1:]

        if isinstance(post_raw[0], dict) and \
                len(post_raw[0]) == 1 and \
                'Series' in post_raw[0]:
            series = [names.UniformName(t) for t in post_raw[0]['Series'].split(',')]

            for s in series:
                if s not in info.series:
                    raise errors.Error('Invalid series "%s"' % s)

            post_raw = post_raw[1:]
        else:
            series = []

        for p in post_raw:
            if not isinstance(p, str):
                raise errors.Error('Invalid paragraph')

        post = Post(info)
        post._title = names.UniformName(match_obj.group(5))

        if match_obj.group(4) is not None:
            post._delta = int(match_obj.group(4)[1:], 10)
        else:
            post._delta = 0

        try:
            year = int(match_obj.group(1), 10)
            month = int(match_obj.group(2), 10)
            day = int(match_obj.group(3), 10)
            post._date = datetime.date(year, month, day)
        except ValueError:
            raise errors.Error('Could not parse date')

        post._series = series
	post._tags = [names.UniformName(t) for t in tags_raw.split(',')]
        post._paragraphs = post_raw
        post._path = post_path
        post._next_post = None
        post._prev_post = None
        post._next_post_by_series = dict((s, None) for s in series)
        post._prev_post_by_series = dict((s, None) for s in series)

        return post

class PostDB(object):
    def __init__(self, info):
        assert isinstance(info, Info)

        self._info = info
        self._post_map = {}
        self._post_maps_by_series = {}

    @property
    def info(self):
        return self._info

    @property
    def post_map(self):
        return self._post_map

    @property
    def post_maps_by_series(self):
        return self._post_maps_by_series

    @staticmethod
    def Load(info, blog_posts_dir):
        assert isinstance(info, Info)
        assert isinstance(blog_posts_dir, str)

        post_map = collections.OrderedDict()
        post_maps_by_series = dict((s, collections.OrderedDict()) for s in info.series)
        post_list = []
        post_lists_by_series = dict((s, []) for s in info.series)

        try:
            for dirpath, subdirs, post_paths_last in os.walk(blog_posts_dir):
                for post_path_last in post_paths_last:
                    post_path_full = os.path.join(dirpath, post_path_last)
                    post_path = post_path_full[len(blog_posts_dir):]

                    if not Post.ValidPath(post_path):
                        continue

                    post = Post.Load(info, post_path, post_path_full)
                    post_list.append(post)

                    for s in post.series:
                        post_lists_by_series[s].append(post)
        except IOError as e:
            raise errors.Error(e)

        post_list.sort()

        for post in post_list:
            post_map[post.path] = post

        # TODO(horiacoman): Shouldn't access internal members here, maybe?
        for ii in range(1, len(post_list)):
            post_list[ii]._prev_post = post_list[ii-1]
            post_list[ii-1]._next_post = post_list[ii]

        for (series, post_list_by_series) in post_lists_by_series.iteritems():
            post_list_by_series.sort()

            for post in post_list_by_series:
                post_maps_by_series[series][post.path] = post

            for ii in range(1, len(post_list_by_series)):
                post_list_by_series[ii]._prev_post_by_series[series] = post_list_by_series[ii-1]
                post_list_by_series[ii-1]._next_post_by_series[series] = post_list_by_series[ii]

        post_db = PostDB(info)
        post_db._post_map = post_map
        post_db._post_maps_by_series = post_maps_by_series

        return post_db
