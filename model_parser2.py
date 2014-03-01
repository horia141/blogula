import re

import errors

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
    _TOKEN_TYPES = frozenset(['word', 'blob', 'slash', 'section-marker', 'list-marker', 'paragraph-end'])

    def __init__(self, token_type, content, source_pos):
        assert token_type in Token._TOKEN_TYPES
        assert isinstance(content, str)
        assert isinstance(source_pos, SourcePos)

        self._token_type = token_type
        self._content = content
        self._source_pos = source_pos

    def __repr__(self):
        return '%s (%s)' % (self._token_type , self._content)

    @property
    def token_type(self):
        return self._token_type

    @property
    def content(self):
        return self._content

    @property
    def source_pos(self):
        return self._source_pos

_WORD_RE = re.compile(r'([^{}\\=*\s]+)', flags=re.UNICODE)
_WS_RE = re.compile(r'[ \t]+')
_SECTION_MARKER_RE = re.compile(r'(=+)')
_LIST_MARKER_RE = re.compile(r'([*]+)')

def _Tokenize(text):
    tokens = []
    c_pos = 0
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

        (new_pos, slash) = _TrySlash(text, c_pos, c_line)
        if slash is not None:
            tokens.append(slash)
            c_pos = _SkipWS(text, new_pos, c_line)
            continue

        (new_pos, section_marker) = _TryMarker(text, 'section-marker', _SECTION_MARKER_RE, c_pos, c_line)
        if section_marker is not None:
            tokens.append(section_marker)
            c_pos = _SkipWS(text, new_pos, c_line)
            continue

        (new_pos, list_marker) = _TryMarker(text, 'list-marker', _LIST_MARKER_RE, c_pos, c_line)
        if list_marker is not None:
            tokens.append(list_marker)
            c_pos = _SkipWS(text, new_pos, c_line)
            continue

        # Reached some form of newline.

        if text[c_pos] != '\n':
            raise errors.Error('A')

        c_pos = c_pos + 1
        c_line = c_line + 1

        (new_pos, new_line, paragraph_end) = _TryParagraphEnd(text, c_pos, c_line)

        if paragraph_end:
            tokens.append(paragraph_end)
            c_pos = _SkipWS(text, new_pos, c_line)
            c_line = new_line
            continue

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
        raise errors.Error('B')

    source_pos = SourcePos(c_line, new_line, c_pos, new_pos)
    token = Token('blob', text[c_pos:new_pos], source_pos)

    return (new_pos, c_pos, token)

def _TrySlash(text, c_pos, c_line):
    if text[c_pos] != '\\':
        return (c_pos, None)

    source_pos = SourcePos(c_line, c_line, c_pos, c_pos + 1)
    token = Token('slash', '\\', source_pos)

    return (c_pos + 1, token)

def _TryMarker(text, marker_type, marker_re, c_pos, c_line):
    marker_match = marker_re.match(text, c_pos)

    if marker_match is None:
        return (c_pos, None)

    source_pos = SourcePos(c_line, c_line, marker_match.start(0), marker_match.end(0))
    token = Token(marker_type, marker_match.group(1), source_pos)

    return (marker_match.end(0), token)

def _TryParagraphEnd(text, c_pos, c_line):
    new_pos = c_pos
    new_line = c_line
    saw_end = False

    while 1:
        new_pos = _SkipWS(text, new_pos, c_line)

        if text[new_pos:new_pos+1] == '\n':
            new_pos = new_pos + 1
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
