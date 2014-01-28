#!/usr/bin/env python

import cStringIO as StringIO
import collections
import datetime
import os
import re
import shutil

import yaml
import Cheetah.Template as template

class Error(Exception):
    pass

def QuickRead(path):
    try:
        f = open(path)
        t = f.read()
        f.close()

        return t
    except IOError as e:
        raise Error(str(e))

def Extract(yaml_dict, field_name, type_constraint):
    if field_name not in yaml_dict:
        raise Error('Entry %s is missing' % field_name)

    if not isinstance(yaml_dict[field_name], type_constraint):
        raise Error('Invalid %s entry' % field_name)

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
            raise Error(str(e))

        if not isinstance(config_raw, dict):
            raise Error('Invalid config file structure')

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
        self._avatar_path = None
        self._description = None

    @property
    def title(self):
        return self._title

    @property
    def author(self):
        return self._author

    @property
    def avatar_path(self):
        return self._avatar_path

    @property
    def description(self):
        return self._description

    @staticmethod
    def Load(info_path):
        assert isinstance(info_path, str)

        info_text = QuickRead(info_path)

        try:
            info_raw = yaml.safe_load(info_text)
        except yaml.YAMLError as e:
            raise Error(str(e))

        if not isinstance(info_raw, dict):
            raise Error('Invalid info file structure')

        info = Info()
        info._title = UniformName(Extract(info_raw, 'Title', str))
        info._author = UniformName(Extract(info_raw, 'Author', str))
        info._avatar_path = Extract(info_raw, 'AvatarPath', str)
        info._description = Extract(info_raw, 'Description', str)

        return info

class Post(object):
    def __init__(self):
        self._title = None
        self._date = None
        self._delta = None
        self._tags = None
        self._paragraphs = None
        self._path = None
        self._next_post = None
        self._prev_post = None

    def __cmp__(self, other):
        assert isinstance(other, Post)

        if self._date < other._date:
            return -1
        elif self._delta < other._delta:
            return -1
        else:
            return 0

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

    PATH_RE = re.compile(r'^(\d\d\d\d).(\d\d).(\d\d)(-\d+)?\s*-\s*(.+)$')

    @staticmethod
    def ValidPath(post_path):
        assert isinstance(post_path, str)

        post_path_base = os.path.basename(post_path)
        match_obj = Post.PATH_RE.match(post_path_base)

        return match_obj is not None

    @staticmethod
    def Load(post_path, post_path_full):
        assert isinstance(post_path, str)
        assert isinstance(post_path_full, str)

        post_path_base = os.path.basename(post_path)
        match_obj = Post.PATH_RE.match(post_path_base)

        if match_obj is None:
            raise Error('Invalid blog post path')

        post_text = QuickRead(post_path_full)

        try:
            post_raw = yaml.safe_load(post_text)
        except yaml.YAMLError as e:
            raise Error(str(e))

        if not isinstance(post_raw, list):
            raise Error('Invalid blog post structure')

        if len(post_raw) < 2:
            raise Error('Invalid blog post structure')

        if not isinstance(post_raw[0], dict):
            raise Error('Invalid blog post structure')

        if len(post_raw[0]) != 1:
            raise Error('Invalid blog post structure')

        if 'Tags' not in post_raw[0]:
            raise Error('Invalid blog post structure')

        for p in post_raw[1:]:
            if not isinstance(p, str):
                raise Error('Invalid paragraph')

        post = Post()
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
            raise Error('Could not parse date')

	post._tags = UniformTags(post_raw[0]['Tags'])
        post._paragraphs = post_raw[1:]
        post._path = post_path
        post._next_post = None
        post._prev_post = None

        return post

class PostDB(object):
    def __init__(self):
        self._post_map = {}

    @property
    def post_map(self):
        return self._post_map

    @staticmethod
    def Load(blog_posts_dir):
        assert isinstance(blog_posts_dir, str)

        post_map = collections.OrderedDict()
        post_list = []

        try:
            for dirpath, subdirs, post_paths_last in os.walk(blog_posts_dir):
                for post_path_last in post_paths_last:
                    post_path_full = os.path.join(dirpath, post_path_last)
                    post_path = post_path_full[len(blog_posts_dir):]

                    if not Post.ValidPath(post_path):
                        continue

                    post = Post.Load(post_path, post_path_full)
                    post_list.append(post)
        except IOError as e:
            raise Error(e)

        post_list.sort()

        for post in post_list:
            post_map[post.path] = post

        # TODO(horiacoman): Shouldn't access internal members here, maybe?
        for ii in range(1, len(post_list)):
            post_list[ii]._prev_post = post_list[ii-1]
            post_list[ii-1]._next_post = post_list[ii]
            

        post_db = PostDB()
        post_db._post_map = post_map

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
        # test for output dir

        try:
            os.mkdir(self._config.output_base_dir)
        except OSError as e:
            # Decide what to do
            pass

        # generate home page

        homepage_template_text = QuickRead(self._config.template_homepage_path)
        homepage_template = template.Template(homepage_template_text)
        homepage_template.info = {}
        homepage_template.info['title'] = self._info.title
        homepage_template.info['author'] = self._info.author
        homepage_template.info['avatar_url'] = self.UrlForImage_(self._info.avatar_path)
        homepage_template.info['description'] = self._info.description
        homepage_template.posts = []

        for post in self._post_db.post_map.itervalues():
            homepage_template.posts.append({})
            homepage_template.posts[-1]['title'] = post.title
            homepage_template.posts[-1]['description'] = post.paragraphs[0]
            homepage_template.posts[-1]['tags'] = post.tags
            homepage_template.posts[-1]['url'] = self.UrlForPost_(post)
            homepage_template.posts[-1]['date_str'] = post.date.strftime('%d %B %Y')

        try:
            homepage_path = os.path.join(
                self._config.output_base_dir,
                self._config.output_homepage_path)

            homepage_file = open(homepage_path, 'w')
            homepage_file.write(str(homepage_template))
            homepage_file.close()
        except IOError as e:
            # Try to cleanup.
            raise Error(str(e))

        # generate one page for each article

        try:
            os.mkdir(os.path.join(
                self._config.output_base_dir,
                self._config.output_posts_dir))
        except OSError as e:
            # Cleanup or maybe continue?
            pass

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

            try:
                postpage_file = open(self.PathForPost_(post), 'w')
                postpage_file.write(str(postpage_template))
                postpage_file.close()
            except IOError as e:
                # Try to cleanup
                raise Error(str(e))

        # generate rss feed

        # generate projects page (from projects description)

        # generate about page?

        # copy extra scripts

        try:
            shutil.copytree(
                self._config.template_foundation_dir, 
                os.path.join(self._config.output_base_dir, 'foundation'))
        except OSError as e:
            # Try to fix something here
            pass

        try:
            os.mkdir(os.path.join(self._config.output_base_dir, 'img'))
        except OSError as e:
            # Try to fix something here
            pass

        try:
            shutil.copyfile(
                os.path.join(os.path.dirname(self._config.blog_info_path), self._info.avatar_path),
                self.PathForImage_(self._info.avatar_path))
        except OSError as e:
            # Try to fix something here
            pass

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
    post_db = PostDB.Load(config.blog_posts_dir)

    site_generator = SiteBuilder(config, info, post_db)
    site_generator.Generate()

if __name__ == '__main__':
    main()
