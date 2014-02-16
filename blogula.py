#!/usr/bin/env python

import cStringIO as StringIO
import collections
import datetime
import os
import re
import shutil

import yaml
import Cheetah.Template as template

import errors
import output

def QuickRead(path):
    try:
        f = open(path)
        t = f.read()
        f.close()

        return t
    except IOError as e:
        raise errors.Error(str(e))

def Extract(yaml_dict, field_name, type_constraint):
    if field_name not in yaml_dict:
        raise errors.Error('Entry %s is missing' % field_name)

    if not isinstance(yaml_dict[field_name], type_constraint):
        raise errors.Error('Invalid %s entry' % field_name)

    return yaml_dict[field_name]

def UniformName(string):
    return ' '.join(string.split())

def UniformPath(path):
    return '_'.join(path.lower().split(' '))

def UniformTags(tags):
    return [UniformName(t) for t in tags.split(',')]

class Config(object):
    def __init__(self):
        self._blog_info_path = None
        self._blog_posts_dir = None
        self._template_homepage_path = None
        self._template_postpage_path = None
        self._template_foundation_dir = None
        self._template_img_dir = None
        self._output_base_dir = None
        self._output_homepage_path = None
        self._output_posts_dir = None

    @property
    def blog_info_path(self):
        return self._blog_info_path

    @property
    def blog_posts_dir(self):
        return self._blog_posts_dir

    @property
    def template_homepage_path(self):
        return self._template_homepage_path

    @property
    def template_postpage_path(self):
        return self._template_postpage_path

    @property
    def template_foundation_dir(self):
        return self._template_foundation_dir

    @property
    def template_img_dir(self):
        return self._template_img_dir

    @property
    def output_base_dir(self):
        return self._output_base_dir

    @property
    def output_homepage_path(self):
        return self._output_homepage_path

    @property
    def output_posts_dir(self):
        return self._output_posts_dir

    @staticmethod
    def Load(config_path):
        assert isinstance(config_path, str)

        config_text = QuickRead(config_path)

        try:
            config_raw = yaml.safe_load(config_text)
        except yaml.YAMLError as e:
            raise errors.Error(str(e))

        if not isinstance(config_raw, dict):
            raise errors.Error('Invalid config file structure')

        config = Config()
        config._blog_info_path = Extract(config_raw, 'BlogInfoPath', str)
        config._blog_posts_dir = Extract(config_raw, 'BlogPostsDir', str)

        templates_raw = Extract(config_raw, 'Templates', dict)

        config._template_homepage_path = Extract(templates_raw, 'HomePagePath', str)
        config._template_postpage_path = Extract(templates_raw, 'PostPagePath', str)
        config._template_foundation_dir = Extract(templates_raw, 'FoundationDir', str)
        config._template_img_dir = Extract(templates_raw, 'ImgDir', str)

        output_raw = Extract(config_raw, 'Output', dict)

        config._output_base_dir = Extract(output_raw, 'BaseDir', str)
        config._output_homepage_path = Extract(output_raw, 'HomePagePath', str)
        config._output_posts_dir = Extract(output_raw, 'PostsDir', str)

        return config

class Info(object):
    def __init__(self):
        self._title = None
        self._author = None
        self._email = None
        self._avatar_path = None
        self._description = None
        self._series = None

    @property
    def title(self):
        return self._title

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

    @staticmethod
    def Load(info_path):
        assert isinstance(info_path, str)

        info_text = QuickRead(info_path)

        try:
            info_raw = yaml.safe_load(info_text)
        except yaml.YAMLError as e:
            raise errors.Error(str(e))

        if not isinstance(info_raw, dict):
            raise errors.Error('Invalid info file structure')

        info = Info()
        info._title = UniformName(Extract(info_raw, 'Title', str))
        info._author = UniformName(Extract(info_raw, 'Author', str))
        info._email = Extract(info_raw, 'Email', str).strip()
        info._avatar_path = Extract(info_raw, 'AvatarPath', str)
        info._description = Extract(info_raw, 'Description', str)

        series_raw = Extract(info_raw, 'Series', list)

        if not all(isinstance(s, str) for s in series_raw):
            raise errors.Error('Invalid Series entry')

        info._series = frozenset(UniformName(s) for s in series_raw)

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

        post_text = QuickRead(post_path_full)

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
            series = UniformTags(post_raw[0]['Series'])

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
        post._title = UniformName(match_obj.group(5))

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
	post._tags = UniformTags(tags_raw)
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

class SiteBuilder(object):
    def __init__(self, config, info, post_db):
        # assert isinstance(config, Config)
        # assert isinstance(info, Info)
        # assert isinstance(post_db, PostDB)

        self._config = config
        self._info = info
        self._post_db = post_db

    def UrlForPost_(self, post):
        return os.path.join(
            '/',
            self._config.output_posts_dir,
            UniformPath(post.title)) + '.html'

    def UrlForImage_(self, image_path):
        return os.path.join('/', 'img', image_path)

    def PathForPost_(self, post):
        return os.path.join(
            self._config.output_base_dir,
            self._config.output_posts_dir,
            UniformPath(post.title)) + '.html'

    def PathForImage_(self, image_path):
        return os.path.join(
            self._config.output_base_dir,
            'img', image_path)

    def Generate(self):
        out_dir = output.Dir()

        # generate home page
        homepage_template_text = QuickRead(self._config.template_homepage_path)
        homepage_template = template.Template(homepage_template_text)
        homepage_template.info = {}
        homepage_template.info['title'] = self._info.title
        homepage_template.info['author'] = self._info.author
        homepage_template.info['avatar_url'] = '/img/avatar.jpg'
        homepage_template.info['description'] = self._info.description
        homepage_template.posts = []

        for post in self._post_db.post_map.itervalues():
            homepage_template.posts.append({})
            homepage_template.posts[-1]['title'] = post.title
            homepage_template.posts[-1]['description'] = post.paragraphs[0]
            homepage_template.posts[-1]['tags'] = post.tags
            homepage_template.posts[-1]['url'] = self.UrlForPost_(post)
            homepage_template.posts[-1]['date_str'] = post.date.strftime('%d %B %Y')

        homepage_template.posts.reverse()
        homepage_text = str(homepage_template)
        homepage_unit = output.File('text/html', homepage_text)

        out_dir.Add(self._config.output_homepage_path, homepage_unit)

        # generate one page for each article
        posts_dir = output.Dir()

        postpage_template_text = QuickRead(self._config.template_postpage_path)
        postpage_template = template.Template(postpage_template_text)

        postpage_template.info = {}
        postpage_template.info['title'] = self._info.title
        postpage_template.info['author'] = self._info.author
        postpage_template.info['avatar_url'] = self.UrlForImage_(self._info.avatar_path)
        postpage_template.info['description'] = self._info.description

        for post in self._post_db.post_map.itervalues():
            postpage_template.post = {}
            postpage_template.post['title'] = post.title
            postpage_template.post['description'] = post.paragraphs[0]
            postpage_template.post['paragraphs'] = post.paragraphs
            postpage_template.post['tags'] = post.tags

            if post.prev_post is not None:
                postpage_template.post['prev_post'] = {}
                postpage_template.post['prev_post']['url'] = self.UrlForPost_(post.prev_post)
                postpage_template.post['prev_post']['title'] = post.prev_post.title
            else:
                postpage_template.post['prev_post'] = None

            if post.next_post is not None:
                postpage_template.post['next_post'] = {}
                postpage_template.post['next_post']['url'] = self.UrlForPost_(post.next_post)
                postpage_template.post['next_post']['title'] = post.next_post.title
            else:
                postpage_template.post['next_post'] = None

            postpage_template.post['series'] = []

            for s in post.series:
                postpage_template.post['series'].append({})
                postpage_template.post['series'][-1]['title'] = s

                if post.prev_post_by_series[s] is not None:
                    postpage_template.post['series'][-1]['prev_post'] = {}
                    postpage_template.post['series'][-1]['prev_post']['url'] = self.UrlForPost_(post.prev_post_by_series[s])
                    postpage_template.post['series'][-1]['prev_post']['title'] = post.prev_post_by_series[s].title
                else:
                    postpage_template.post['series'][-1]['prev_post'] = None

                if post.next_post_by_series[s] is not None:
                    postpage_template.post['series'][-1]['next_post'] = {}
                    postpage_template.post['series'][-1]['next_post']['url'] = self.UrlForPost_(post.next_post_by_series[s])
                    postpage_template.post['series'][-1]['next_post']['title'] = post.next_post_by_series[s].title
                else:
                    postpage_template.post['series'][-1]['next_post'] = None

            postpage_text = str(postpage_template)
            postpage_unit = output.File('text/html', postpage_text)

            posts_dir.Add(UniformPath(post.title) + '.html', postpage_unit)

        out_dir.Add(self._config.output_posts_dir, posts_dir)

        # generate rss feed

        # generate projects page (from projects description)

        # generate about page?

        # copy extra scripts

        foundation_unit = output.Copy(self._config.template_foundation_dir)
        out_dir.Add('foundation', foundation_unit)

        # Copy avatar image

        image_dir = output.Dir()

        avatar_unit = output.Copy(os.path.join(os.path.dirname(self._config.blog_info_path), self._info.avatar_path))
        image_dir.Add('avatar.jpg', avatar_unit)

        out_dir.Add('img', image_dir)

        return out_dir

    @property
    def config(self):
        return self._config

    @property
    def info(self):
        return self._info

    @property
    def post_db(self):
        return self._post_db


def main():
    config = Config.Load('config')
    info = Info.Load(config.blog_info_path)
    post_db = PostDB.Load(info, config.blog_posts_dir)

    site_generator = SiteBuilder(config, info, post_db)
    out_dir = site_generator.Generate()

    output.WriteLocalOutput(config.output_base_dir, out_dir)

if __name__ == '__main__':
    main()
