import datetime
import re

class Atom(object):
    pass

class Word(Atom):
    def __init__(self, text):
        assert isinstance(text, str)

        self._text = text

    def __hash__(self):
        return hash(self._text)

    def __eq__(self, other):
        if not isinstance(other, Word):
            return False

        return self._text == other._text

    def __ne__(self, other):
        return not (self == other)

    @property
    def text(self):
        return self._text

class Function(Atom):
    def __init__(self, name, arg_list):
        assert isinstance(name, str)
        assert isinstance(arg_list, list)
        assert all(isinstance(a, str) for a in arg_list)
        
        self._name = name
        self._arg_list = arg_list

    def __hash__(self):
        return hash((self._name, tuple(self._arg_list)))

    def __eq__(self, other):
        if not isinstance(other, Function):
            return False

        return self._name == other._name and len(self._arg_list) == len(other._arg_list) and \
            all(x == y for (x,y) in zip(self._arg_list, other._arg_list))

    def __ne__(self, other):
        return not (self == other)

    @property
    def name(self):
        return self._name

    @property
    def arg_list(self):
        return self._arg_list

class Text(object):
    def __init__(self, atoms):
        assert isinstance(atoms, list)
        assert all(isinstance(a, Atom) for a in atoms)

        self._atoms = atoms

    def __hash__(self):
        return hash(tuple(self._atoms))

    def __eq__(self, other):
        if not isinstance(other, Text):
            return False

        return len(self._atoms) == len(other._atoms) and \
            all(x == y for (x,y) in zip(self._atoms, other._atoms))

    def __ne__(self, other):
        return not (self == other)

    @property
    def atoms(self):
        return self._atoms

class Info(object):
    def __init__(self, title, url, author, email, twitter, location, avatar_path, description, 
                 series, nr_of_posts_in_feed, posts_dir, output_dir, output_homepage_path, 
                 output_posts_dir):
        assert isinstance(title, Text)
        assert isinstance(url, str)
        assert isinstance(author, str)
        assert isinstance(email, str)
        assert isinstance(twitter, str)
        assert isinstance(location, str)
        assert isinstance(avatar_path, str)
        assert isinstance(description, Text)
        assert isinstance(series, frozenset)
        assert all(isinstance(s, Text) for s in series)
        assert isinstance(nr_of_posts_in_feed, int)
        assert nr_of_posts_in_feed > 0
        assert isinstance(posts_dir, str)
        assert isinstance(output_dir, str)
        assert isinstance(output_homepage_path, str)
        assert isinstance(output_posts_dir, str)        

        self._title = title
        self._url = url
        self._author = author
        self._email = email
        self._twitter = twitter
        self._location = location
        self._avatar_path = avatar_path
        self._description = description
        self._series = series
        self._nr_of_posts_in_feed = nr_of_posts_in_feed
        self._posts_dir = posts_dir
        self._output_dir = output_dir
        self._output_homepage_path = output_homepage_path
        self._output_posts_dir = output_posts_dir

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
    def twitter(self):
        return self._twitter

    @property
    def location(self):
        return self._location

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

    @property
    def posts_dir(self):
        return self._posts_dir

    @property
    def output_dir(self):
        return self._output_dir

    @property
    def output_homepage_path(self):
        return self._output_homepage_path

    @property
    def output_posts_dir(self):
        return self._output_posts_dir

class Cell(object):
    pass

class Textual(Cell):
    def __init__(self, text):
        assert isinstance(text, Text)

        self._text = text

    @property
    def text(self):
        return self._text

class List(Cell):
    def __init__(self, header_text, items):
        assert header_text is None or isinstance(header_text, Text)
        assert isinstance(items, list)
        assert all(isinstance(l, Text) for l in items)

        self._header_text = header_text
        self._items = items

    @property
    def header_text(self):
        return self._header_text

    @property
    def items(self):
        return self._items

class Formula(Cell):
    def __init__(self, header_text, formula):
        assert header_text is None or isinstance(header_text, Text)
        assert isinstance(formula, str)

        self._header_text = header_text
        self._formula = formula

    @property
    def header_text(self):
        return self._header_text

    @property
    def formula(self):
        return self._formula

class CodeBlock(Cell):
    def __init__(self, header_text, language, code):
        assert header_text is None or isinstance(header_text, Text)
        assert isinstance(language, str)
        assert isinstance(code, str)

        self._header_text = header_text
        self._language = language
        self._code = code

    @property
    def header_text(self):
        return self._header_text

    @property
    def language(self):
        return self._language

    @property
    def code(self):
        return self._code

class Image(Cell):
    def __init__(self, header_text, path):
        assert header_text is None or isinstance(header_text, Text)
        assert isinstance(path, str)

        self._header_text = header_text
        self._path = path

    @property
    def header_text(self):
        return self._header_text

    @property
    def path(self):
        return self._path

class Unit(object):
    pass

class Paragraph(Unit):
    def __init__(self, cell):
        assert isinstance(cell, Cell)

        self._cell = cell

    @property
    def cell(self):
        return self._cell

class Section(Unit):
    def __init__(self, title, paragraphs, subsections):
        assert isinstance(title, Text)
        assert isinstance(paragraphs, list)
        assert all(isinstance(p, Paragraph) for p in paragraphs)
        assert isinstance(subsections, list)
        assert all(isinstance(s, Section) for s in subsections)

        self._title = title
        self._paragraphs = paragraphs
        self._subsections = subsections

    @property
    def title(self):
        return self._title

    @property
    def paragraphs(self):
        return self._paragraphs

    @property
    def subsections(self):
        return self._subsections

class Post(object):
    def __init__(self, info, title, date, delta, series, tags, root_section, path):
        assert isinstance(info, Info)
        assert isinstance(title, Text)
        assert isinstance(date, datetime.date)
        assert isinstance(series, list)
        assert all(s in info.series for s in series)
        assert isinstance(tags, list)
        assert all(isinstance(t, Text) for t in tags)
        assert isinstance(root_section, Section)
        assert isinstance(path, str)

        self._info = info
        self._title = title
        self._date = date
        self._delta = delta
        self._series = series
        self._tags = tags
        self._root_section = root_section
        self._path = path
        self._next_post = None
        self._prev_post = None
        self._next_post_by_series = dict((s, None) for s in series)
        self._prev_post_by_series = dict((s, None) for s in series)
        self._description = Post._FindFirstTextualParagraph(root_section).cell.text

    def __lt__(self, other):
        assert isinstance(other, Post)

        if self._date < other._date:
            return True
        elif self._date == other._date:
            return self._delta < other._delta
        else:
            return False

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
    def root_section(self):
        return self._root_section

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

    @property
    def description(self):
        return self._description

    @staticmethod
    def _FindFirstTextualParagraph(section):
        if len(section.paragraphs) >= 1 and isinstance(section.paragraphs[0].cell, Textual):
            return section.paragraphs[0]
        elif len(section.subsections) >= 1:
            return Post._FindFirstTextualParagraph(section.subsections[0])
        else:
            raise errors.Error('Post without description paragraph')

class PostDB(object):
    def __init__(self, info, post_map, post_maps_by_series):
        assert isinstance(info, Info)
        assert isinstance(post_map, dict)
        assert all(isinstance(p, str) for p in post_map.keys())
        assert all(isinstance(p, Post) for p in post_map.values())
        assert isinstance(post_maps_by_series, dict)
        assert all(p in info.series for p in post_maps_by_series.keys())
        assert all(isinstance(ms, dict) for ms in post_maps_by_series.values())
        assert all(all(isinstance(ps, str) for ps in ms.keys()) for ms in post_maps_by_series.values())
        assert all(all(isinstance(ps, Post) for ps in ms.values()) for ms in post_maps_by_series.values())

        self._info = info
        self._post_map = post_map
        self._post_maps_by_series = post_maps_by_series

    @property
    def info(self):
        return self._info

    @property
    def post_map(self):
        return self._post_map

    @property
    def post_maps_by_series(self):
        return self._post_maps_by_series
