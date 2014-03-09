#!/usr/bin/env python

import datetime
import os
import re
import shutil
import StringIO
import urlparse

import pygments
import pygments.lexers
import yaml
import Cheetah.Template as template

import errors
import model
import model_parser
import output
import utils

class Config(object):
    def __init__(self, blog_info_path, blog_posts_dir, template_homepage_path, template_postpage_path,
                 template_feedpage_path, template_foundation_dir, template_blogula_css_path, 
                 template_img_dir, output_base_dir, output_homepage_path, output_posts_dir):
        assert isinstance(blog_info_path, str)
        assert isinstance(blog_posts_dir, str)
        assert isinstance(template_homepage_path, str)
        assert isinstance(template_postpage_path, str)
        assert isinstance(template_feedpage_path, str)
        assert isinstance(template_foundation_dir, str)
        assert isinstance(template_blogula_css_path, str)
        assert isinstance(template_img_dir, str)
        assert isinstance(output_base_dir, str)
        assert isinstance(output_homepage_path, str)
        assert isinstance(output_posts_dir, str)

        self._blog_info_path = blog_info_path
        self._blog_posts_dir = blog_posts_dir
        self._template_homepage_path = template_homepage_path
        self._template_postpage_path = template_postpage_path
        self._template_feedpage_path = template_feedpage_path
        self._template_foundation_dir = template_foundation_dir
        self._template_blogula_css_path = template_blogula_css_path
        self._template_img_dir = template_img_dir
        self._output_base_dir = output_base_dir
        self._output_homepage_path = output_homepage_path
        self._output_posts_dir = output_posts_dir
        self._presentation_title_heading_level = 1
        self._presentation_article_title_heading_level = 2
        self._presentation_article_subtitle_heading_level_min = 3
        self._presentation_article_subtitle_heading_level_max = 6

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
    def template_feedpage_path(self):
        return self._template_feedpage_path

    @property
    def template_foundation_dir(self):
        return self._template_foundation_dir

    @property
    def template_blogula_css_path(self):
        return self._template_blogula_css_path

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

    @property
    def presentation_title_heading_level(self):
        return self._presentation_title_heading_level

    @property
    def presentation_article_title_heading_level(self):
        return self._presentation_article_title_heading_level

    @property
    def presentation_article_subtitle_heading_level_min(self):
        return self._presentation_article_subtitle_heading_level_min

    @property
    def presentation_article_subtitle_heading_level_max(self):
        return self._presentation_article_subtitle_heading_level_max

def _ParseConfig(config_path):
    config_text = utils.QuickRead(config_path)

    try:
        config_raw = yaml.safe_load(config_text)
    except yaml.YAMLError as e:
        raise errors.Error(str(e))

    if not isinstance(config_raw, dict):
        raise errors.Error('Invalid config file structure')

    blog_info_path = utils.Extract(config_raw, 'BlogInfoPath', str)
    blog_posts_dir = utils.Extract(config_raw, 'BlogPostsDir', str)

    templates_raw = utils.Extract(config_raw, 'Templates', dict)

    template_homepage_path = utils.Extract(templates_raw, 'HomePagePath', str)
    template_postpage_path = utils.Extract(templates_raw, 'PostPagePath', str)
    template_feedpage_path = utils.Extract(templates_raw, 'FeedPagePath', str)
    template_foundation_dir = utils.Extract(templates_raw, 'FoundationDir', str)
    template_blogula_css_path = utils.Extract(templates_raw, 'BlogulaCSSPath', str)
    template_img_dir = utils.Extract(templates_raw, 'ImgDir', str)

    output_raw = utils.Extract(config_raw, 'Output', dict)

    output_base_dir = utils.Extract(output_raw, 'BaseDir', str)
    output_homepage_path = utils.Extract(output_raw, 'HomePagePath', str)
    output_posts_dir = utils.Extract(output_raw, 'PostsDir', str)

    return Config(blog_info_path=blog_info_path, blog_posts_dir=blog_posts_dir, 
                  template_homepage_path=template_homepage_path, template_postpage_path=template_postpage_path,
                  template_feedpage_path=template_feedpage_path, template_foundation_dir=template_foundation_dir,
                  template_blogula_css_path=template_blogula_css_path, template_img_dir=template_img_dir, 
                  output_base_dir=output_base_dir, output_homepage_path=output_homepage_path, 
                  output_posts_dir=output_posts_dir)

class SiteBuilder(object):
    def __init__(self, config, info, post_db):
        assert isinstance(config, Config)
        assert isinstance(info, model.Info)
        assert isinstance(post_db, model.PostDB)

        self._config = config
        self._info = info
        self._post_db = post_db

    @staticmethod
    def _UniformPath(path):
        def EliminateNonAlpha(word):
            good_word_file = StringIO.StringIO()

            for ch in word:
                if re.match('[a-z0-9_]', ch):
                    good_word_file.write(ch)

            good_word = good_word_file.getvalue()
            good_word_file.close()

            return good_word

        return '_'.join(EliminateNonAlpha(w) for w in path.lower().split(' '))

    def _UrlForPost(self, post):
        return os.path.join(
            '/',
            self._config.output_posts_dir,
            SiteBuilder._UniformPath(SiteBuilder._EvaluateTextToText(post.title))) + '.html'

    def _GenerateHomepage(self):
        homepage_template_text = utils.QuickRead(self._config.template_homepage_path)
        homepage_template = template.Template(homepage_template_text)
        homepage_template.info = {}
        homepage_template.info['title_text'] = SiteBuilder._EvaluateTextToText(self._info.title)
        homepage_template.info['title_html'] = SiteBuilder._EvaluateTextToHTML(self._info.title)
        homepage_template.info['author'] = self._info.author
        homepage_template.info['avatar_url'] = '/img/avatar.jpg'
        homepage_template.info['description_text'] = SiteBuilder._EvaluateTextToText(self._info.description)
        homepage_template.info['description_html'] = SiteBuilder._EvaluateTextToHTML(self._info.description)
        homepage_template.posts = []

        for post in self._post_db.post_map.itervalues():
            homepage_template.posts.append({})
            homepage_template.posts[-1]['title_html'] = SiteBuilder._EvaluateTextToHTML(post.title)
            homepage_template.posts[-1]['description_html'] = SiteBuilder._EvaluateTextToHTML(post.description)
            homepage_template.posts[-1]['tags_html'] = [SiteBuilder._EvaluateTextToHTML(t) for t in post.tags]
            homepage_template.posts[-1]['url'] = self._UrlForPost(post)
            homepage_template.posts[-1]['date_str'] = post.date.strftime('%d %B %Y')

        homepage_template.posts.reverse()

        homepage_template.presentation = {}
        homepage_template.presentation['title_heading_level'] = \
            self._config.presentation_title_heading_level
        homepage_template.presentation['article_title_heading_level'] = \
            self._config.presentation_article_title_heading_level

        homepage_text = str(homepage_template)
        return output.File('text/html', homepage_text)

    def _GeneratePostpage(self, post):
        (line_units, extra_image_units) = SiteBuilder._LinearizeSectionToLineUnits(self._config, post.root_section, 0)
        postpage_template_text = utils.QuickRead(self._config.template_postpage_path)
        postpage_template = template.Template(postpage_template_text)

        postpage_template.info = {}
        postpage_template.info['title_text'] = SiteBuilder._EvaluateTextToText(self._info.title)
        postpage_template.info['title_html'] = SiteBuilder._EvaluateTextToHTML(self._info.title)
        postpage_template.info['author'] = self._info.author
        postpage_template.info['avatar_url'] = '/img/avatar.jpg'
        postpage_template.info['description_html'] = SiteBuilder._EvaluateTextToHTML(self._info.description)

        postpage_template.post = {}
        postpage_template.post['title_text'] = SiteBuilder._EvaluateTextToText(post.title)
        postpage_template.post['title_html'] = SiteBuilder._EvaluateTextToHTML(post.title)
        postpage_template.post['description_text'] = SiteBuilder._EvaluateTextToText(post.description)
        postpage_template.post['lineunits'] = line_units            
        postpage_template.post['tags_html'] = [SiteBuilder._EvaluateTextToHTML(t) for t in post.tags]

        if post.prev_post is not None:
            postpage_template.post['prev_post'] = {}
            postpage_template.post['prev_post']['url'] = self._UrlForPost(post.prev_post)
            postpage_template.post['prev_post']['title_html'] = SiteBuilder._EvaluateTextToHTML(post.prev_post.title)
        else:
            postpage_template.post['prev_post'] = None

        if post.next_post is not None:
            postpage_template.post['next_post'] = {}
            postpage_template.post['next_post']['url'] = self._UrlForPost(post.next_post)
            postpage_template.post['next_post']['title_html'] = SiteBuilder._EvaluateTextToHTML(post.next_post.title)
        else:
            postpage_template.post['next_post'] = None

        postpage_template.post['series'] = []

        for s in post.series:
            postpage_template.post['series'].append({})
            postpage_template.post['series'][-1]['title_html'] = SiteBuilder._EvaluateTextToHTML(s)

            if post.prev_post_by_series[s] is not None:
                postpage_template.post['series'][-1]['prev_post'] = {}
                postpage_template.post['series'][-1]['prev_post']['url'] = self._UrlForPost(post.prev_post_by_series[s])
                postpage_template.post['series'][-1]['prev_post']['title_html'] = SiteBuilder._EvaluateTextToHTML(post.prev_post_by_series[s].title)
            else:
                postpage_template.post['series'][-1]['prev_post'] = None

            if post.next_post_by_series[s] is not None:
                postpage_template.post['series'][-1]['next_post'] = {}
                postpage_template.post['series'][-1]['next_post']['url'] = self._UrlForPost(post.next_post_by_series[s])
                postpage_template.post['series'][-1]['next_post']['title_html'] = SiteBuilder._EvaluateTextToHTML(post.next_post_by_series[s].title)
            else:
                postpage_template.post['series'][-1]['next_post'] = None

        postpage_template.presentation = {}
        postpage_template.presentation['title_heading_level'] = \
            self._config.presentation_title_heading_level
        postpage_template.presentation['article_title_heading_level'] = \
            self._config.presentation_article_title_heading_level

        postpage_text = str(postpage_template)
        return (output.File('text/html', postpage_text), extra_image_units)

    def _GenerateFeed(self):
        feedpage_template_text = utils.QuickRead(self._config.template_feedpage_path)
        feedpage_template = template.Template(feedpage_template_text)
        feedpage_template.info = {}
        feedpage_template.info['title_text'] = SiteBuilder._EvaluateTextToText(self._info.title)
        feedpage_template.info['description_text'] = SiteBuilder._EvaluateTextToText(self._info.description)
        feedpage_template.info['url'] = self._info.url
        feedpage_template.info['copyright_year'] = datetime.datetime.now().year
        feedpage_template.info['author'] = self._info.author
        feedpage_template.info['email'] = self._info.email
        feedpage_template.info['build_date_str'] = datetime.datetime.now().strftime('%A, %d %B %Y %S:%M:%H %Z')
        feedpage_template.posts = []

        for post in self._post_db.post_map.values()[-self._info.nr_of_posts_in_feed:]:
            feedpage_template.posts.append({})
            feedpage_template.posts[-1]['title_text'] = SiteBuilder._EvaluateTextToText(post.title)
            feedpage_template.posts[-1]['url'] = self._UrlForPost(post)
            feedpage_template.posts[-1]['description_text'] = SiteBuilder._EvaluateTextToText(post.description)
            feedpage_template.posts[-1]['tags_text'] = [SiteBuilder._EvaluateTextToText(t) for t in post.tags]
            feedpage_template.posts[-1]['pub_date_str'] = post.date.strftime('%A, %d %B %Y 00:00:00 %Z')

        feedpage_template.posts.reverse()
        feedpage_text = str(feedpage_template)
        return output.File('application/xml', feedpage_text)

    def Generate(self):
        out_dir = output.Dir()

        # generate home page
        homepage_unit = self._GenerateHomepage()
        out_dir.Add(self._config.output_homepage_path, homepage_unit)

        # generate one page for each article
        posts_dir = output.Dir()
        extra_image_units = []

        for post in self._post_db.post_map.itervalues():
            (postpage_unit, post_extra_image_units) = self._GeneratePostpage(post)
            posts_dir.Add(SiteBuilder._UniformPath(SiteBuilder._EvaluateTextToText(post.title)) + '.html', postpage_unit)
            extra_image_units.extend(post_extra_image_units)

        out_dir.Add(self._config.output_posts_dir, posts_dir)

        # generate rss feed
        feed_unit = self._GenerateFeed()
        out_dir.Add('feed.xml', feed_unit)

        # generate projects page (from projects description)

        # generate about page?

        # copy extra scripts

        foundation_unit = output.Copy(self._config.template_foundation_dir)
        out_dir.Add('foundation', foundation_unit)

        # Copy CSS

        blogula_css_unit = output.Copy(self._config.template_blogula_css_path)
        out_dir.Add('blogula.css', blogula_css_unit)

        # Generate CSS for CodeBlock cell code highliting.

        code_highlight_css = pygments.formatters.HtmlFormatter().get_style_defs('.code-block-highlight')
        code_highlight_css_unit = output.File('text/css', code_highlight_css)
        out_dir.Add('code_highlight.css', code_highlight_css_unit)

        # Copy images image

        image_dir = output.Dir()

        ## Copy avatar image

        avatar_unit = output.Copy(
            os.path.join(os.path.dirname(self._config.blog_info_path), self._info.avatar_path))
        image_dir.Add('avatar.jpg', avatar_unit)

        ## Copy post extra images

        for (basename, unit) in extra_image_units:
            image_dir.Add(basename, unit)

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

    @staticmethod
    def _EvaluateTextToText(text):
        text_file = StringIO.StringIO()

        for atom in text.atoms:
            if isinstance(atom, model.Word):
                text_file.write(atom.text)
                text_file.write(' ')
            elif isinstance(atom, model.Function):
                if atom.name == 'slash':
                    text_file.write('\\')
                    text_file.write(' ')
                elif atom.name == 'brace-beg':
                    text_file.write('{')
                    text_file.write(' ')
                elif atom.name == 'brace-end':
                    text_file.write('}')
                    text_file.write(' ')
                elif atom.name == 'f':
                    text_file.write(atom.arg_list[0])
                    text_file.write(' ')
                elif atom.name == 'def':
                    text_file.write(atom.arg_list[0])
                    text_file.write(' ')
                elif atom.name == 'ref':
                    text_file.write(atom.arg_list[0])
                    text_file.write(' ')
                else:
                    print('Unknown function %s - skipping' % atom.name)
            else:
                raise errors.Error('Unknown atom')

        text_file.seek(-1, 2)
        text_str = text_file.getvalue()
        text_file.close()

        return text_str

    @staticmethod
    def _EvaluateTextToHTML(text):
        html_file = StringIO.StringIO()

        for atom in text.atoms:
            if isinstance(atom, model.Word):
                html_file.write(atom.text)
                html_file.write(' ')
            elif isinstance(atom, model.Function):
                if atom.name == 'slash':
                    html_file.write('&#92;')
                    html_file.write(' ')
                elif atom.name == 'brace-beg':
                    html_file.write('{')
                    html_file.write(' ')
                elif atom.name == 'brace-end':
                    html_file.write('}')
                    html_file.write(' ')
                elif atom.name == 'f':
                    html_file.write('\(')
                    html_file.write(atom.arg_list[0])
                    html_file.write('\)')
                    html_file.write(' ')
                elif atom.name == 'def':
                    html_file.write('<strong>')
                    html_file.write(atom.arg_list[0])
                    html_file.write('</strong>')
                    html_file.write(' ')
                elif atom.name == 'ref':
                    html_file.write('<a href="#">')
                    html_file.write(atom.arg_list[0])
                    html_file.write('</a>')
                    html_file.write(' ')
                else:
                    print('Unknown function %s - skipping' % atom.name)
            else:
                raise errors.Error('Unknown atom')

        html_file.seek(-1, 2)
        html_str = html_file.getvalue()
        html_file.close()

        return html_str

    @staticmethod
    def _LinearizeSectionToLineUnits(config, section, level):
        line_units = []
        extra_image_units = []

        if level >= 1:
            line_units.append({})
            line_units[-1]['type'] = 'header'
            line_units[-1]['level'] = \
                min(config.presentation_article_subtitle_heading_level_min + level - 1,
                    config.presentation_article_subtitle_heading_level_max)
            line_units[-1]['text_html'] = SiteBuilder._EvaluateTextToHTML(section.title)

        for paragraph in section.paragraphs:
            line_units.append({})

            if isinstance(paragraph.cell, model.Textual):
                line_units[-1]['type'] = 'textual'
                line_units[-1]['text_html'] = SiteBuilder._EvaluateTextToHTML(paragraph.cell.text)
            elif isinstance(paragraph.cell, model.List):
                line_units[-1]['type'] = 'list'
                if paragraph.cell.header_text is not None:
                    line_units[-1]['has_header'] = True
                    line_units[-1]['header_html'] = SiteBuilder._EvaluateTextToHTML(paragraph.cell.header_text)
                else:
                    line_units[-1]['has_header'] = False
                line_units[-1]['items'] = [SiteBuilder._EvaluateTextToHTML(l) for l in paragraph.cell.items]
            elif isinstance(paragraph.cell, model.Formula):
                line_units[-1]['type'] = 'formula'
                if paragraph.cell.header_text is not None:
                    line_units[-1]['has_header'] = True
                    line_units[-1]['header_html'] = SiteBuilder._EvaluateTextToHTML(paragraph.cell.header_text)
                else:
                    line_units[-1]['has_header'] = False
                line_units[-1]['formula'] = paragraph.cell.formula
            elif isinstance(paragraph.cell, model.CodeBlock):
                line_units[-1]['type'] = 'code-block'
                if paragraph.cell.header_text is not None:
                    line_units[-1]['has_header'] = True
                    line_units[-1]['header_html'] = SiteBuilder._EvaluateTextToHTML(paragraph.cell.header_text)
                else:
                    line_units[-1]['has_header'] = False

                try:
                    lexer = pygments.lexers.get_lexer_by_name(paragraph.cell.language)
                except pygments.util.ClassNotFound as e:
                    lexer = pygments.lexers.guess_lexer(paragraph.cell.code)

                formatter = pygments.formatters.HtmlFormatter(linenos=True, cssclass='code-block-highlight', cssstyles='font-size:0.75em;')

                line_units[-1]['code_html'] = pygments.highlight(paragraph.cell.code, lexer, formatter)
            elif isinstance(paragraph.cell, model.Image):
                line_units[-1]['type'] = 'image'
                if paragraph.cell.header_text is not None:
                    line_units[-1]['has_header'] = True
                    line_units[-1]['header_html'] = SiteBuilder._EvaluateTextToHTML(paragraph.cell.header_text)
                    line_units[-1]['alt_text'] = SiteBuilder._EvaluateTextToText(paragraph.cell.header_text)
                else:
                    line_units[-1]['has_header'] = False
                    line_units[-1]['alt_text'] = ''

                split_path = urlparse.urlparse(paragraph.cell.path)

                if split_path.scheme == 'http' or split_path.scheme == 'https':
                    line_units[-1]['path'] = paragraph.cell.path
                elif split_path.scheme == '':
                    image_basename = os.path.normpath(paragraph.cell.path).replace('/', '_')
                    line_units[-1]['path'] = '/img/%s' % image_basename

                    if os.path.isabs(paragraph.cell.path):
                        extra_image_path = paragraph.cell.path
                    else:
                        extra_image_path = os.path.join(config.blog_posts_dir, paragraph.cell.path)

                    extra_image_units.append((image_basename, output.Copy(extra_image_path)))
                else:
                    raise errors.Error('Unsupported path format')
            else:
                raise errors.Error('Q')

        for subsection in section.subsections:
            (sub_line_units, sub_extra_image_units) = SiteBuilder._LinearizeSectionToLineUnits(config, subsection, level+1)
            line_units.extend(sub_line_units)
            extra_image_units.extend(sub_extra_image_units)

        return (line_units, extra_image_units)

def main():
    config = _ParseConfig('config')
    (info, post_db) = model_parser.ParseInfoAndPostDB(config.blog_info_path, config.blog_posts_dir)

    site_generator = SiteBuilder(config, info, post_db)
    out_dir = site_generator.Generate()

    output.WriteLocalOutput(config.output_base_dir, out_dir)

if __name__ == '__main__':
    main()
