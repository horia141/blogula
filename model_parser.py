import collections
import datetime
import os
import re

import yaml

import errors
import model
import utils

def ParseInfoAndPostDB(info_path, blog_posts_dir):
    info = _ParseInfo(info_path)
    post_db = _ParsePostDB(info, blog_posts_dir)

    return (info, post_db)

def _ParseInfo(info_path):
    info_text = utils.QuickRead(info_path)

    try:
        info_raw = yaml.safe_load(info_text)
    except yaml.YAMLError as e:
        raise errors.Error(str(e))

    if not isinstance(info_raw, dict):
        raise errors.Error('Invalid info file structure')

    title = model.UniformName(utils.Extract(info_raw, 'Title', str))
    url = utils.Extract(info_raw, 'URL', str)
    author = model.UniformName(utils.Extract(info_raw, 'Author', str))
    email = utils.Extract(info_raw, 'Email', str).strip()
    avatar_path = utils.Extract(info_raw, 'AvatarPath', str)
    description = utils.Extract(info_raw, 'Description', str)

    series_raw = utils.Extract(info_raw, 'Series', list)

    if not all(isinstance(s, str) for s in series_raw):
        raise errors.Error('Invalid Series entry')

    series = frozenset(model.UniformName(s) for s in series_raw)

    nr_of_posts_in_feed = utils.Extract(info_raw, 'NrOfPostsInFeed', int)

    return model.Info(title=title, url=url, author=author, email=email, avatar_path=avatar_path,
                      description=description, series=series, nr_of_posts_in_feed=nr_of_posts_in_feed)

def _ParsePostDB(info, blog_posts_dir):
    post_map = collections.OrderedDict()
    post_maps_by_series = dict((s, collections.OrderedDict()) for s in info.series)
    post_list = []
    post_lists_by_series = dict((s, []) for s in info.series)

    try:
        for dirpath, subdirs, post_paths_last in os.walk(blog_posts_dir):
            for post_path_last in post_paths_last:
                post_path_full = os.path.join(dirpath, post_path_last)
                post_path = post_path_full[len(blog_posts_dir):]

                if not _PostValidPath(post_path):
                    continue

                post = _ParsePost(info, post_path, post_path_full)
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

    return model.PostDB(info=info, post_map=post_map, post_maps_by_series=post_maps_by_series)

_POST_PATH_RE = re.compile(r'^(\d\d\d\d).(\d\d).(\d\d)(-\d+)?\s*-\s*(.+)$')

def _PostValidPath(post_path):
    post_path_base = os.path.basename(post_path)
    match_obj = _POST_PATH_RE.match(post_path_base)

    return match_obj is not None

def _ParsePost(info, post_path, post_path_full):
    post_path_base = os.path.basename(post_path)
    match_obj = _POST_PATH_RE.match(post_path_base)

    if match_obj is None:
        raise errors.Error('Invalid blog post path')

    post_text = utils.QuickRead(post_path_full)

    title = model.UniformName(match_obj.group(5))

    try:
        year = int(match_obj.group(1), 10)
        month = int(match_obj.group(2), 10)
        day = int(match_obj.group(3), 10)
        date = datetime.date(year, month, day)
    except ValueError:
        raise errors.Error('Could not parse date')

    if match_obj.group(4) is not None:
        delta = int(match_obj.group(4)[1:], 10)
    else:
        delta = 0

    (series_raw, tags_raw, root_section) = _ParsePostText(post_text)

    series = [model.UniformName(t) for t in series_raw.split(',')] if series_raw else []
    tags = [model.UniformName(t) for t in tags_raw.split(',')] if tags_raw else []

    return model.Post(info=info, title=title, date=date, delta=delta, series=series, tags=tags, 
                      root_section=root_section, path=post_path)

def _ParsePostText(post_text):
    new_c_pos = _SkipWhiteSpace(post_text, 0)
    (new_c_pos, series_raw) = _ParseSeriesHeader(post_text, new_c_pos)
    new_c_pos = _SkipWhiteSpace(post_text, new_c_pos)
    (new_c_pos, tags_raw) = _ParseTagsHeader(post_text, new_c_pos)
    (new_c_pos, root_section) = _ParseSection(post_text, new_c_pos, 0, False)

    if new_c_pos < len(post_text):
        raise errors.Error('Could not parse post')

    return (series_raw, tags_raw, root_section)

def _SkipWhiteSpace(text, c_pos):
    new_c_pos = c_pos

    while new_c_pos < len(text):
        c = text[new_c_pos]

        if c == ' ' or c == '\t' or c == '\n':
            new_c_pos = new_c_pos + 1
        else:
            break

    return new_c_pos

_SERIES_HEADER_RE = re.compile('Series:\s*(.+)')

def _ParseSeriesHeader(text, c_pos):
    new_c_pos = c_pos

    series_match = _SERIES_HEADER_RE.match(text, c_pos)

    if series_match is None:
        return (c_pos, None)

    header_raw = series_match.group(1)
    new_c_pos = series_match.end(0) + 1

    return (new_c_pos, header_raw)

_TAGS_HEADER_RE = re.compile('Tags:\s*(.+)')

def _ParseTagsHeader(text, c_pos):
    new_c_pos = c_pos

    tags_match = _TAGS_HEADER_RE.match(text, c_pos)

    if tags_match is None:
        return (c_pos, None)

    header_raw = tags_match.group(1)
    new_c_pos = tags_match.end(0) + 1

    return (new_c_pos, header_raw)

# TODO(horia314): Should be a stack, not a dictionary.
_TITLE_RE_AT_LEVEL = {}

def _ParseSection(section_text, c_pos, level, has_title):
    if c_pos >= len(section_text):
        return (c_pos, None)

    if has_title:
        if level not in _TITLE_RE_AT_LEVEL:
            title_re = re.compile(r'={%d}([^=]+)={%d}' % (level, level))
            _TITLE_RE_AT_LEVEL[level] = title_re
        else:
            title_re = _TITLE_RE_AT_LEVEL[level]

        title_match = title_re.match(section_text, c_pos)

        if title_match is None:
            return (c_pos, None)

        title = title_match.group(1).strip()
        new_c_pos = title_match.end()
        new_c_pos = _SkipWhiteSpace(section_text, new_c_pos)
    else:
        title = '.root'
        new_c_pos = _SkipWhiteSpace(section_text, c_pos)

    (new_c_pos, paragraphs) = _ParseParagraphs(section_text, new_c_pos)
    sections = []
    
    while new_c_pos < len(section_text):
        (new_c_pos, section) = _ParseSection(section_text, new_c_pos, level+1, True)

        if section is None:
            break

        sections.append(section)

    return (new_c_pos, model.Section(title, paragraphs, sections))

def _ParseParagraphs(preamble_text, c_pos):
    new_c_pos = c_pos
    paragraphs = []

    while 1:
        (new_c_pos, paragraph) = _ParseParagraph(preamble_text, new_c_pos)

        if paragraph is None:
            break

        paragraphs.append(paragraph)

    return (new_c_pos, paragraphs)

def _ParseParagraph(paragraph_text, c_pos):
    if c_pos >= len(paragraph_text) or paragraph_text[c_pos] == '=':
        return (c_pos, None)

    new_c_pos = c_pos

    while new_c_pos < len(paragraph_text):
        if paragraph_text[new_c_pos:new_c_pos+2] == '\n\n':
            skip = 2
            break
        elif paragraph_text[new_c_pos:new_c_pos+2] == '\n=':
            skip = 1
            break
        else:
            new_c_pos = new_c_pos + 1
            skip = 0

    selected_text = paragraph_text[c_pos:new_c_pos]
    cleaned_text_lines = selected_text.split('\n')
    cleaned_text = ' '.join(l.strip() for l in cleaned_text_lines if l.strip())

    new_c_pos = _SkipWhiteSpace(paragraph_text, new_c_pos + skip)

    return (new_c_pos, model.Paragraph(cleaned_text))

def ParseText(text):
    atoms = []
    new_c_pos = _SkipWhiteSpace(text, 0)    

    while new_c_pos < len(text):
        (new_c_pos, atom) = _ParseAtom(text, new_c_pos)

        if atom is None:
            raise errors.Error('Could not parse text region')

        atoms.append(atom)
        new_c_pos = _SkipWhiteSpace(text, new_c_pos)

    return model.Text(atoms)

def _ParseAtom(text, c_pos):
    (new_c_pos, escape) = _ParseEscape(text, c_pos)

    if escape is not None:
        return (new_c_pos, escape)

    (new_c_pos, word) = _ParseWord(text, c_pos)

    if word is not None:
        return (new_c_pos, word)

    (new_c_pos, formula) = _ParseFormula(text, c_pos)

    if formula is not None:
        return (new_c_pos, formula)

    return (c_pos, None)

def _ParseEscape(text, c_pos):
    if text[c_pos:c_pos+6] == '\\slash':
        return (c_pos + 6, model.Escape('\\'))
    elif text[c_pos:c_pos+11] == '\\brace-beg':
        return (c_pos + 1, model.Escape('{'))
    elif text[c_pos:c_pos+11] == '\\brace-end':
        return (c_pos + 1, model.Escape('}'))
    else:
        return (c_pos, None)

_WORD_RE = re.compile(r'(\w+)', flags=re.UNICODE)

def _ParseWord(text, c_pos):
    word_match = _WORD_RE.match(text, c_pos)

    if word_match is None:
        return (c_pos, None)

    return (word_match.end(0), model.Word(word_match.group(1)))

def _ParseFormula(text, c_pos):
    print text[c_pos:]
    if text[c_pos:c_pos+2] != '\\f':
        return (c_pos, None)

    brace_counter = 0
    new_c_pos = c_pos + 2
    start_pos = None

    while new_c_pos < len(text):
        if text[new_c_pos] == '{':
            if brace_counter == 0:
                start_pos = new_c_pos + 1
                
            brace_counter = brace_counter + 1
        elif text[new_c_pos] == '}':
            if brace_counter > 1:
                brace_counter = brace_counter - 1
            elif brace_counter == 1:
                formula_text = text[start_pos:new_c_pos]
                return (new_c_pos + 1, model.Formula(formula_text))
            else:
                raise errors.Error('Invalid formula')
        elif brace_counter == 0:
            raise errors.Error('Invalid formula')
            
        new_c_pos = new_c_pos + 1

    raise errors.Error('Invalid formula')
