import enum
import mimetypes
import os
import re
import shutil

import errors

mime_types_set = frozenset(mimetypes.types_map.itervalues())

class CrawlMode(enum.Enum):
    CRAWLABLE = 1
    NON_CRAWLABLE = 2

class Unit(object):
    def __init__(self, mime_type, crawl_mode):
        assert mime_type is None or mime_type in mime_types_set
        assert isinstance(crawl_mode, CrawlMode)

        self._mime_type = mime_type
        self._crawl_mode = crawl_mode

    @property
    def mime_type(self):
        return self._mime_type

    @property
    def crawl_mode(self):
        return self._crawl_mode

class File(Unit):
    def __init__(self, mime_type, crawl_mode, content):
        assert mime_type in mime_types_set
        assert isinstance(crawl_mode, CrawlMode)
        assert isinstance(content, str)

        super(File, self).__init__(mime_type, crawl_mode)

        self._content = content

    @property
    def content(self):
        return self._content

class Copy(Unit):
    def __init__(self, crawl_mode, original_path):
        assert isinstance(crawl_mode, CrawlMode)
        assert isinstance(original_path, str)

        super(Copy, self).__init__(None, crawl_mode)

        # TODO(horia314): add mime-type detection.
        self._original_path = original_path

        self._is_dir = os.path.isdir(original_path)

    @property
    def original_path(self):
        return self._original_path

    @property
    def is_dir(self):
        return self._is_dir

class Dir(Unit):
    def __init__(self, crawl_mode):
        assert isinstance(crawl_mode, CrawlMode)

        super(Dir, self).__init__(None, crawl_mode)

        self._units = {}

    def Add(self, path, unit):
        assert isinstance(path, str)
        assert isinstance(unit, Unit)

        # if re.match(r'^[-a-zA-Z_0-9.]+$', path) is None:
        #    raise errors.Error('Invalid output path "%s"' % path)

        if path in self._units:
            raise errors.Error('Path "%s" already exists in directory' % path)

        self._units[path] = unit

    @property
    def units(self):
        return self._units

def WriteLocalOutput(base_dir_path, out_dir):
    assert isinstance(base_dir_path, str)
    assert isinstance(out_dir, Dir)

    def WriteUnit_(path, unit):
        if isinstance(unit, File):
            unit_file = open(path, 'w')
            unit_file.write(unit.content)
            unit_file.close()
        elif isinstance(unit, Copy):
            if unit.is_dir:
                shutil.copytree(unit.original_path, path)
            else:
                shutil.copy(unit.original_path, path)
        elif isinstance(unit, Dir):
            os.mkdir(path)

            for (subpath, subunit) in unit.units.iteritems():
                WriteUnit_(os.path.join(path, subpath), subunit)
        else:
            assert False

    # Create the base output dir.
    try:
        if os.path.exists(base_dir_path):
            print 'Output dir "%s" already exists' % base_dir_path
            action = raw_input('Continue? [Y/n] ')

            if action == '' or action.lower() == 'y':
                shutil.rmtree(base_dir_path)
            else:
                raise errors.Abort()

        # Paths are unique and the directory is fresh. No need to check for
        # the file already existing or access problems.
        WriteUnit_(base_dir_path, out_dir)
    except (IOError, OSError) as e:
        try:
            shutil.rmtree(base_dir_path)
        except OSError as e:
            print 'Warning: could not remove output directories'

        raise errors.Error(str(e))
