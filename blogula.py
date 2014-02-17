#!/usr/bin/env python

import os
import shutil

import yaml
import Cheetah.Template as template

import errors
import model
import names
import output
import utils

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

        config_text = utils.QuickRead(config_path)

        try:
            config_raw = yaml.safe_load(config_text)
        except yaml.YAMLError as e:
            raise errors.Error(str(e))

        if not isinstance(config_raw, dict):
            raise errors.Error('Invalid config file structure')

        config = Config()
        config._blog_info_path = utils.Extract(config_raw, 'BlogInfoPath', str)
        config._blog_posts_dir = utils.Extract(config_raw, 'BlogPostsDir', str)

        templates_raw = utils.Extract(config_raw, 'Templates', dict)

        config._template_homepage_path = utils.Extract(templates_raw, 'HomePagePath', str)
        config._template_postpage_path = utils.Extract(templates_raw, 'PostPagePath', str)
        config._template_foundation_dir = utils.Extract(templates_raw, 'FoundationDir', str)
        config._template_img_dir = utils.Extract(templates_raw, 'ImgDir', str)

        output_raw = utils.Extract(config_raw, 'Output', dict)

        config._output_base_dir = utils.Extract(output_raw, 'BaseDir', str)
        config._output_homepage_path = utils.Extract(output_raw, 'HomePagePath', str)
        config._output_posts_dir = utils.Extract(output_raw, 'PostsDir', str)

        return config

class SiteBuilder(object):
    def __init__(self, config, info, post_db):
        assert isinstance(config, Config)
        assert isinstance(info, model.Info)
        assert isinstance(post_db, model.PostDB)

        self._config = config
        self._info = info
        self._post_db = post_db

    def _UrlForPost(self, post):
        return os.path.join(
            '/',
            self._config.output_posts_dir,
            names.UniformPath(post.title)) + '.html'

    def GenerateHomepage_(self):
        homepage_template_text = utils.QuickRead(self._config.template_homepage_path)
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
            homepage_template.posts[-1]['url'] = self._UrlForPost(post)
            homepage_template.posts[-1]['date_str'] = post.date.strftime('%d %B %Y')

        homepage_template.posts.reverse()
        homepage_text = str(homepage_template)
        return output.File('text/html', homepage_text)

    def GeneratePostpage_(self, post):
        postpage_template_text = utils.QuickRead(self._config.template_postpage_path)
        postpage_template = template.Template(postpage_template_text)

        postpage_template.info = {}
        postpage_template.info['title'] = self._info.title
        postpage_template.info['author'] = self._info.author
        postpage_template.info['avatar_url'] = '/img/avatar.jpg'
        postpage_template.info['description'] = self._info.description

        postpage_template.post = {}
        postpage_template.post['title'] = post.title
        postpage_template.post['description'] = post.paragraphs[0]
        postpage_template.post['paragraphs'] = post.paragraphs
        postpage_template.post['tags'] = post.tags

        if post.prev_post is not None:
            postpage_template.post['prev_post'] = {}
            postpage_template.post['prev_post']['url'] = self._UrlForPost(post.prev_post)
            postpage_template.post['prev_post']['title'] = post.prev_post.title
        else:
            postpage_template.post['prev_post'] = None

        if post.next_post is not None:
            postpage_template.post['next_post'] = {}
            postpage_template.post['next_post']['url'] = self._UrlForPost(post.next_post)
            postpage_template.post['next_post']['title'] = post.next_post.title
        else:
            postpage_template.post['next_post'] = None

        postpage_template.post['series'] = []

        for s in post.series:
            postpage_template.post['series'].append({})
            postpage_template.post['series'][-1]['title'] = s

            if post.prev_post_by_series[s] is not None:
                postpage_template.post['series'][-1]['prev_post'] = {}
                postpage_template.post['series'][-1]['prev_post']['url'] = self._UrlForPost(post.prev_post_by_series[s])
                postpage_template.post['series'][-1]['prev_post']['title'] = post.prev_post_by_series[s].title
            else:
                postpage_template.post['series'][-1]['prev_post'] = None

            if post.next_post_by_series[s] is not None:
                postpage_template.post['series'][-1]['next_post'] = {}
                postpage_template.post['series'][-1]['next_post']['url'] = self._UrlForPost(post.next_post_by_series[s])
                postpage_template.post['series'][-1]['next_post']['title'] = post.next_post_by_series[s].title
            else:
                postpage_template.post['series'][-1]['next_post'] = None

        postpage_text = str(postpage_template)
        return output.File('text/html', postpage_text)

    def Generate(self):
        out_dir = output.Dir()

        # generate home page
        homepage_unit = self.GenerateHomepage_()
        out_dir.Add(self._config.output_homepage_path, homepage_unit)

        # generate one page for each article
        posts_dir = output.Dir()

        for post in self._post_db.post_map.itervalues():
            postpage_unit = self.GeneratePostpage_(post)
            posts_dir.Add(names.UniformPath(post.title) + '.html', postpage_unit)

        out_dir.Add(self._config.output_posts_dir, posts_dir)

        # generate rss feed

        # generate projects page (from projects description)

        # generate about page?

        # copy extra scripts

        foundation_unit = output.Copy(self._config.template_foundation_dir)
        out_dir.Add('foundation', foundation_unit)

        # Copy avatar image

        image_dir = output.Dir()

        avatar_unit = output.Copy(
            os.path.join(os.path.dirname(self._config.blog_info_path), self._info.avatar_path))
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
    info = model.Info.Load(config.blog_info_path)
    post_db = model.PostDB.Load(info, config.blog_posts_dir)

    site_generator = SiteBuilder(config, info, post_db)
    out_dir = site_generator.Generate()

    output.WriteLocalOutput(config.output_base_dir, out_dir)

if __name__ == '__main__':
    main()
