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

    @property
    def atoms(self):
        return self._atoms

class Info(object):
    def __init__(self, title, url, author, email, avatar_path, description, 
                 series, nr_of_posts_in_feed):
        assert isinstance(title, Text)
        assert isinstance(url, str)
        assert isinstance(author, str)
        assert isinstance(email, str)
        assert isinstance(avatar_path, str)
        assert isinstance(description, Text)
        assert isinstance(series, frozenset)
        assert all(isinstance(s, Text) for s in series)
        assert isinstance(nr_of_posts_in_feed, int)
        assert nr_of_posts_in_feed > 0

        self._title = title
        self._url = url
        self._author = author
        self._email = email
        self._avatar_path = avatar_path
        self._description = description
        self._series = series
        self._nr_of_posts_in_feed = nr_of_posts_in_feed

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

class Unit(object):
    pass

class Paragraph(Unit):
    def __init__(self, text):
        assert isinstance(text, str)

        self._text = text

    @property
    def text(self):
        return self._text

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
        self._description = Post._FindFirstParagraph(root_section).text

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
    def _FindFirstParagraph(section):
        if len(section.paragraphs) >= 1:
            return section.paragraphs[0]
        elif len(section.subsections) >= 1:
            return Post._FindFirstParagraph(section.subsections[0])
        else:
            raise errors.Error('Post without description paragraph')

class PostDB(object):
    def __init__(self, info, post_map, post_maps_by_series):
        assert isinstance(info, Info)
        assert isinstance(post_map, dict)
        assert all(isinstance(p, str) for p in post_map.iterkeys())
        assert all(isinstance(p, Post) for p in post_map.itervalues())
        assert isinstance(post_maps_by_series, dict)
        assert all(p in info.series for p in post_maps_by_series.iterkeys())
        assert all(isinstance(ms, dict) for ms in post_maps_by_series.itervalues())
        assert all(all(isinstance(ps, str) for ps in ms.iterkeys()) for ms in post_maps_by_series.itervalues())
        assert all(all(isinstance(ps, Post) for ps in ms.itervalues()) for ms in post_maps_by_series.itervalues())

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
