import collections
import datetime
import os
import os.path
import re

import yaml

import errors
import model
import utils

class SourcePos(object):
    def __init__(self, start_line, end_line, start_char, end_char):
        assert isinstance(start_line, int)
        assert start_line >= 0
        assert isinstance(end_line, int)
        assert end_line >= start_line
        assert isinstance(start_char, int)
        assert start_char >= 0
        assert isinstance(end_char, int)
        assert end_char >= 0

        self._start_line = start_line
        self._end_line = end_line
        self._start_char = start_char
        self._end_char = end_char

    def __eq__(self, other):
        if not isinstance(other, SourcePos):
            return False

        return (self._start_line == other._start_line and
                self._end_line == other._end_line and
                self._start_char == other._start_char and
                self._end_char == other._end_char)

    @property
    def start_line(self):
        return self._start_line

    @property
    def end_line(self):
        return self._end_line

    @property
    def start_char(self):
        return self._start_char

    @property
    def end_char(self):
        return self._end_char

class Token(object):
    _TOKEN_TYPES = frozenset(['word', 'blob', 'slash', 'list-marker', 'cell-marker', 'section-marker', 'paragraph-end'])

    def __init__(self, token_type, content, source_pos):
        assert token_type in Token._TOKEN_TYPES
        assert isinstance(content, str)
        assert isinstance(source_pos, SourcePos)

        self._token_type = token_type
        self._content = content
        self._source_pos = source_pos

    def __repr__(self):
        return '%s (%s)' % (self._token_type , self._content) # , self._source_pos.start_line, self._source_pos.end_line, self._source_pos.start_char, self._source_pos.end_char)

    def __eq__(self, other):
        if not isinstance(other, Token):
            return False

        return (self._token_type == other._token_type and
                self._content == other._content and
                self._source_pos == other._source_pos)

    @property
    def token_type(self):
        return self._token_type

    @property
    def content(self):
        return self._content

    @property
    def source_pos(self):
        return self._source_pos

def ParseInfo(info_path):
    info_text = utils.QuickRead(info_path)

    try:
        info_raw = yaml.safe_load(info_text)
    except yaml.YAMLError as e:
        raise errors.Error(str(e))

    if not isinstance(info_raw, dict):
        raise errors.Error('Invalid info file structure')

    title_raw = utils.Extract(info_raw, 'Title', str)
    title = _ParseSmallText(title_raw)
    url = utils.Extract(info_raw, 'URL', str)
    author = ' '.join(utils.Extract(info_raw, 'Author', str).split())
    email = utils.Extract(info_raw, 'Email', str).strip()
    twitter = utils.Extract(info_raw, 'Twitter', str).strip()
    location = utils.Extract(info_raw, 'Location', str).strip()
    avatar_path = utils.Extract(info_raw, 'AvatarPath', str)
    description_raw = utils.Extract(info_raw, 'Description', str)
    description = _ParseSmallText(description_raw)

    series_raw = utils.Extract(info_raw, 'Series', list)

    if not all(isinstance(s, str) for s in series_raw):
        raise errors.Error('Invalid Series entry')

    series = frozenset(_ParseSmallText(s) for s in series_raw)

    nr_of_posts_in_feed = utils.Extract(info_raw, 'NrOfPostsInFeed', int)
    posts_dir = utils.Extract(info_raw, 'PostsDir', str)

    if os.path.isabs(posts_dir):
        posts_dir = os.path.normpath(posts_dir)
    else:
        posts_dir = os.path.join(os.path.dirname(info_path), os.path.normpath(posts_dir))

    output_dir = utils.Extract(info_raw, 'OutputDir', str)

    if os.path.isabs(output_dir):
        output_dir = os.path.normpath(output_dir)
    else:
        output_dir = os.path.join(os.path.dirname(info_path), os.path.normpath(output_dir))

    output_raw = utils.Extract(info_raw, 'Output', dict)

    output_homepage_path = utils.Extract(output_raw, 'HomePagePath', str)
    output_posts_dir = utils.Extract(output_raw, 'PostsDir', str)

    return model.Info(title=title, url=url, author=author, email=email, twitter=twitter, location=location,
                      avatar_path=avatar_path, description=description, series=series,
                      nr_of_posts_in_feed=nr_of_posts_in_feed, posts_dir=posts_dir, output_dir=output_dir,
                      output_homepage_path=output_homepage_path, output_posts_dir=output_posts_dir)

def ParsePostDB(info):
    post_map = collections.OrderedDict()
    post_maps_by_series = dict((s, collections.OrderedDict()) for s in info.series)
    post_list = []
    post_lists_by_series = dict((s, []) for s in info.series)

    try:
        for dirpath, subdirs, post_paths_last in os.walk(info.posts_dir):
            for post_path_last in post_paths_last:
                post_path_full = os.path.join(dirpath, post_path_last)
                post_path = post_path_full[len(info.posts_dir):]

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

    for (series, post_list_by_series) in post_lists_by_series.items():
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

    title_raw = match_obj.group(5)
    title = _ParseSmallText(title_raw)

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

    (series, tags, root_section) = _ParsePostText(post_text)

    return model.Post(info=info, title=title, date=date, delta=delta, series=series, tags=tags, 
                      root_section=root_section, path=post_path)

def _ParseSmallText(small_text):
    tokens = _Tokenize(small_text)
    (new_pos, small) = _ParseText(tokens, 0)

    # The last element of tokens is a paragraph-end, so it is not considered.
    if new_pos < len(tokens) - 1 or small is None:
        raise errors.Error('J')

    return small

def _ParsePostText(post_text):
    new_pos = _SkipWS(post_text, 0, 0)
    (new_pos, series_raw) = _ParseSeriesHeader(post_text, new_pos)
    series = [_ParseSmallText(s) for s in series_raw.split(',')] if series_raw else []

    new_pos = _SkipWS(post_text, new_pos, 0)
    (new_pos, tags_raw) = _ParseTagsHeader(post_text, new_pos)
    tags = [_ParseSmallText(t) for t in tags_raw.split(',')] if tags_raw else []

    tokens = _Tokenize(post_text[new_pos:])
    (new_t_pos, root_section) = _ParseSection(tokens, 0, 0, False)

    if new_t_pos < len(tokens):
        print tokens[new_t_pos-30:new_t_pos+30]
        raise errors.Error('M')

    return (series, tags, root_section)

_SERIES_HEADER_RE = re.compile('Series:\s*(.+)')

def _ParseSeriesHeader(text, c_pos):
    new_pos = c_pos

    series_match = _SERIES_HEADER_RE.match(text, c_pos)

    if series_match is None:
        return (c_pos, None)

    header_raw = series_match.group(1)
    new_pos = series_match.end(0) + 1

    return (new_pos, header_raw)

_TAGS_HEADER_RE = re.compile('Tags:\s*(.+)')

def _ParseTagsHeader(text, c_pos):
    new_pos = c_pos

    tags_match = _TAGS_HEADER_RE.match(text, c_pos)

    if tags_match is None:
        return (c_pos, None)

    header_raw = tags_match.group(1)
    new_pos = tags_match.end(0) + 1

    return (new_pos, header_raw)

def _ParseSection(tokens, c_pos, level, has_title):
    new_pos = c_pos

    if has_title:
        if new_pos >= len(tokens):
            return (c_pos, None)

        if tokens[new_pos].token_type != 'section-marker':
            return (c_pos, None)

        if tokens[new_pos].content != ('=' * level):
            return (c_pos, None)

        new_pos = new_pos + 1
        (new_pos, title) = _ParseText(tokens, new_pos)

        if title is None:
            raise errors.Error('V')

        if new_pos >= len(tokens):
            raise errors.Error('X')

        if tokens[new_pos].token_type != 'section-marker':
            print tokens[new_pos-20:new_pos+20]
            raise errors.Error('Q')

        if tokens[new_pos].content != ('=' * level):
            raise errors.Error('Y')

        new_pos = new_pos + 1
    else:
        title = model.Text([model.Word('.root')])

    # Skip newlines after the title, represented as paragraph-ends.
    while new_pos < len(tokens) and tokens[new_pos].token_type == 'paragraph-end':
        new_pos = new_pos + 1

    (new_pos, paragraphs) = _ParseParagraphs(tokens, new_pos)
    sections = []

    while new_pos < len(tokens):
        (new_pos, section) = _ParseSection(tokens, new_pos, level + 1, True)

        if section is None:
            break

        sections.append(section)

    return (new_pos, model.Section(title, paragraphs, sections))

def _ParseParagraphs(tokens, c_pos):
    new_pos = c_pos
    paragraphs = []

    while new_pos < len(tokens):
        (new_pos, paragraph) = _ParseParagraph(tokens, new_pos)

        if paragraph is None:
            break

        paragraphs.append(paragraph)

    return (new_pos, paragraphs)

def _ParseParagraph(tokens, c_pos):
    (new_pos, textual) = _ParseTextual(tokens, c_pos)
    if textual:
        return (new_pos, model.Paragraph(textual))

    (new_pos, list_c) = _ParseList(tokens, c_pos)
    if list_c:
        return (new_pos, model.Paragraph(list_c))

    (new_pos, formula) = _ParseFormula(tokens, c_pos)
    if formula:
        return (new_pos, model.Paragraph(formula))

    (new_pos, code_block) = _ParseCodeBlock(tokens, c_pos)
    if code_block:
        return (new_pos, model.Paragraph(code_block))

    (new_pos, image) = _ParseImage(tokens, c_pos)
    if image:
        return (new_pos, model.Paragraph(image))

    return (c_pos, None)

def _ParseTextual(tokens, c_pos):
    (new_pos, text) = _ParseText(tokens, c_pos)

    if text is None:
        return (c_pos, None)

    if new_pos >= len(tokens):
        return (new_pos, model.Textual(text))
    elif tokens[new_pos].token_type == 'paragraph-end':
        return (new_pos + 1, model.Textual(text))
    else:
        # The List will have to fail here.
        return (c_pos, None)

def _ParseList(tokens, c_pos):
    # header_text can be None here.
    (new_pos, header_text) = _ParseText(tokens, c_pos)
    items = []

    while new_pos < len(tokens):
        if tokens[new_pos].token_type != 'list-marker':
            break

        (new_pos, item) = _ParseText(tokens, new_pos + 1)

        if item is None:
            break

        items.append(item)

    if len(items) == 0:
        return (c_pos, None)

    if new_pos >= len(tokens):
        return (new_pos, model.List(header_text, items))
    elif tokens[new_pos].token_type == 'paragraph-end':
        return (new_pos + 1, model.List(header_text, items))
    else:
        # Raise here for the list as well.
        print tokens[new_pos-20:new_pos+20]
        raise errors.Error('Q')

def _ParseFormula(tokens, c_pos):
    # header_text can be None here.
    (new_pos, header_text) = _ParseText(tokens, c_pos)

    if new_pos >= len(tokens):
        return (c_pos, None)

    if tokens[new_pos].token_type != 'cell-marker':
        return (c_pos, None)

    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        return (c_pos, None)

    if tokens[new_pos].token_type != 'word' or tokens[new_pos].content != 'formula':
        return (c_pos, None)

    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        raise errors.Error('F1')

    if tokens[new_pos].token_type != 'blob':
        raise errors.Error('F2')

    formula = tokens[new_pos].content
    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        return (new_pos, model.Formula(header_text, formula))
    elif tokens[new_pos].token_type == 'paragraph-end':
        return (new_pos + 1, model.Formula(header_text, formula))
    else:
        raise errors.Error('F3') 

def _ParseCodeBlock(tokens, c_pos):
    # header_text can be None here.
    (new_pos, header_text) = _ParseText(tokens, c_pos)

    if new_pos >= len(tokens):
        return (c_pos, None)

    if tokens[new_pos].token_type != 'cell-marker':
        return (c_pos, None)

    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        return (c_pos, None)

    if tokens[new_pos].token_type != 'word' or tokens[new_pos].content != 'code':
        return (c_pos, None)

    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        raise errors.Error('W1')

    if tokens[new_pos].token_type != 'blob':
        raise errors.Error('W2')

    language = tokens[new_pos].content
    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        raise errors.Error('W1')

    if tokens[new_pos].token_type != 'blob':
        raise errors.Error('W2')

    code = tokens[new_pos].content
    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        return (new_pos, model.CodeBlock(header_text, language, code))
    elif tokens[new_pos].token_type == 'paragraph-end':
        return (new_pos + 1, model.CodeBlock(header_text, language, code))
    else:
        raise errors.Error('W3')

def _ParseImage(tokens, c_pos):
    # header_text can be None here.
    (new_pos, header_text) = _ParseText(tokens, c_pos)

    if new_pos >= len(tokens):
        return (c_pos, None)

    if tokens[new_pos].token_type != 'cell-marker':
        return (c_pos, None)

    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        return (c_pos, None)

    if tokens[new_pos].token_type != 'word' or tokens[new_pos].content != 'image':
        return (c_pos, None)

    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        raise errors.Error('I1')

    if tokens[new_pos].token_type != 'blob':
        raise errors.Error('I2')

    path = tokens[new_pos].content
    new_pos = new_pos + 1

    if new_pos >= len(tokens):
        return (new_pos, model.Image(header_text, path))
    elif tokens[new_pos].token_type == 'paragraph-end':
        return (new_pos + 1, model.Image(header_text, path))
    else:
        raise errors.Error('I3') 

def _ParseText(tokens, c_pos):
    atoms = []
    new_pos = c_pos

    while new_pos < len(tokens):
        (new_pos, atom) = _ParseAtom(tokens, new_pos)

        if atom is None:
            break

        atoms.append(atom)

    if len(atoms) == 0:
        return (c_pos, None)

    return (new_pos, model.Text(atoms))

def _ParseAtom(tokens, c_pos):
    (new_pos, word) = _ParseWord(tokens, c_pos)

    if word is not None:
        return (new_pos, word)

    (new_pos, function) = _ParseFunction(tokens, c_pos)

    if function is not None:
        return (new_pos, function)

    return (c_pos, None)

def _ParseWord(tokens, c_pos):
    new_pos = c_pos

    if tokens[new_pos].token_type != 'word':
        return (new_pos, None)

    return (new_pos + 1, model.Word(tokens[new_pos].content))

def _ParseFunction(tokens, c_pos):
    new_pos = c_pos

    if tokens[new_pos].token_type != 'slash':
        return (new_pos, None)

    new_pos = new_pos + 1

    if new_pos > len(tokens):
        raise errors.Error('C')

    if tokens[new_pos].token_type != 'word':
        print tokens[c_pos-20:c_pos+20]
        raise errors.Error('D')

    name = tokens[new_pos].content
    new_pos = new_pos + 1
    arg_list = []

    while new_pos < len(tokens) and tokens[new_pos].token_type == 'blob':
        arg_list.append(tokens[new_pos].content)
        new_pos = new_pos + 1

    return (new_pos, model.Function(name, arg_list))

_WORD_RE = re.compile(r'([^{}\\*%=\s]+)', flags=re.UNICODE)
_WS_RE = re.compile(r'[ \t]+')
_SLASH_RE = re.compile(r'(\\)')
_LIST_MARKER_RE = re.compile(r'([*])')
_CELL_MARKER_RE = re.compile(r'(%)')
_SECTION_MARKER_RE = re.compile(r'(=+)')

def _Tokenize(text):
    tokens = []
    c_pos = _SkipWS(text, 0, 0)
    c_line = 0

    while c_pos < len(text):
        (new_pos, word) = _TryWord(text, c_pos, c_line)
        if word is not None:
            tokens.append(word)
            c_pos = _SkipWS(text, new_pos, c_line)
            continue

        (new_pos, new_line, blob) = _TryBlob(text, c_pos, c_line)
        if blob is not None:
            tokens.append(blob)
            c_pos = _SkipWS(text, new_pos, c_line)
            c_line = new_line
            continue

        (new_pos, slash) = _TrySpecialSequence(text, 'slash', _SLASH_RE, c_pos, c_line)
        if slash is not None:
            tokens.append(slash)
            c_pos = _SkipWS(text, new_pos, c_line)
            continue

        (new_pos, list_marker) = _TrySpecialSequence(text, 'list-marker', _LIST_MARKER_RE, c_pos, c_line)
        if list_marker is not None:
            tokens.append(list_marker)
            c_pos = _SkipWS(text, new_pos, c_line)
            continue

        (new_pos, cell_marker) = _TrySpecialSequence(text, 'cell-marker', _CELL_MARKER_RE, c_pos, c_line)
        if cell_marker is not None:
            tokens.append(cell_marker)
            c_pos = _SkipWS(text, new_pos, c_line)
            continue

        (new_pos, section_marker) = _TrySpecialSequence(text, 'section-marker', _SECTION_MARKER_RE, c_pos, c_line)
        if section_marker is not None:
            tokens.append(section_marker)
            c_pos = _SkipWS(text, new_pos, c_line)
            continue

        # Reached some form of newline.

        if text[c_pos] != '\n':
            print c_line
            print text[c_pos:c_pos+100]
            raise errors.Error('A')

        c_pos = c_pos + 1
        c_line = c_line + 1

        c_pos = _SkipWS(text, c_pos, c_line)
        (new_pos, new_line, paragraph_end) = _TryParagraphEnd(text, c_pos, c_line)

        if paragraph_end:
            tokens.append(paragraph_end)
            c_pos = _SkipWS(text, new_pos, c_line)
            c_line = new_line
            continue

    if len(tokens) >= 1 and tokens[-1].token_type != 'paragraph-end':
        tokens.append(Token('paragraph-end', '', SourcePos(c_line, c_line, c_pos, c_pos)))

    return tokens

def _TryWord(text, c_pos, c_line):
    word_match = _WORD_RE.match(text, c_pos)

    if word_match is None:
        return (c_pos, None)

    source_pos = SourcePos(c_line, c_line, word_match.start(0), word_match.end(0))
    token = Token('word', word_match.group(1), source_pos)

    return (word_match.end(0), token)

def _TryBlob(text, c_pos, c_line):
    if text[c_pos] != '{':
        return (c_pos, c_line, None)

    brace_counter = 1
    new_pos = c_pos + 1
    new_line = c_line

    while brace_counter > 0 and new_pos < len(text):
        if text[new_pos] == '{':
            brace_counter = brace_counter + 1
        elif text[new_pos] == '}':
            brace_counter = brace_counter - 1
        elif text[new_pos] == '\n':
            new_line = new_line + 1

        new_pos = new_pos + 1

    if brace_counter > 0:
        print text[c_pos:c_pos+150]
        print text[new_pos-150:new_pos+150]
        raise errors.Error('B')

    source_pos = SourcePos(c_line, new_line, c_pos, new_pos)
    token = Token('blob', text[c_pos+1:new_pos-1], source_pos)

    return (new_pos, new_line, token)

def _TrySpecialSequence(text, sequence_type, sequence_re, c_pos, c_line):
    sequence_match = sequence_re.match(text, c_pos)

    if sequence_match is None:
        return (c_pos, None)

    source_pos = SourcePos(c_line, c_line, sequence_match.start(0), sequence_match.end(0))
    token = Token(sequence_type, sequence_match.group(1), source_pos)

    return (sequence_match.end(0), token)

def _TryParagraphEnd(text, c_pos, c_line):
    new_pos = c_pos
    new_line = c_line
    saw_end = False

    while 1:
        new_new_pos = _SkipWS(text, new_pos, c_line)

        if text[new_new_pos:new_new_pos+1] == '\n':
            new_pos = new_new_pos + 1
            new_line = new_line + 1
            saw_end = True
        else:
            break

    if text[new_pos:new_pos+1] == '=':
        saw_end = True

    if not saw_end:
        return (c_pos, c_line, None)

    source_pos = SourcePos(c_line, new_line, c_pos, new_pos)
    token = Token('paragraph-end', text[c_pos:new_pos], source_pos)
    
    return (new_pos, new_line, token)

def _SkipWS(text, c_pos, c_line):
    ws_match = _WS_RE.match(text, c_pos)

    if ws_match is None:
        return c_pos

    return ws_match.end(0)
