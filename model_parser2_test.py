#!/usr/bin/env python3

import re
import unittest

import errors
import model_parser2 as mp

class TestSourcePos(unittest.TestCase):
    def test_constructor(self):
        source_pos = mp.SourcePos(1, 3, 10, 20)

        self.assertEqual(1, source_pos.start_line)
        self.assertEqual(3, source_pos.end_line)
        self.assertEqual(10, source_pos.start_char)
        self.assertEqual(20, source_pos.end_char)

class TestToken(unittest.TestCase):
    def test_constructor(self):
        source_pos = mp.SourcePos(1, 3, 10, 20)

        token_word = mp.Token('word', 'abraccarda', source_pos)

        self.assertEqual('word', token_word.token_type)
        self.assertEqual('abraccarda', token_word.content)
        self.assertEqual(source_pos, token_word.source_pos)
        self.assertEqual('word (abraccarda)', repr(token_word))

        token_blob = mp.Token('blob', 'abraccarda', source_pos)

        self.assertEqual('blob', token_blob.token_type)
        self.assertEqual('abraccarda', token_blob.content)
        self.assertEqual(source_pos, token_blob.source_pos)
        self.assertEqual('blob (abraccarda)', repr(token_blob))

class TestTokenize(unittest.TestCase):
    pass

class TestTokenizeHelpers(unittest.TestCase):
    def test_TryWord_OneWord(self):
        (new_pos, word) = mp._TryWord('hello', 0, 0)

        self.assertEqual(5, new_pos)
        self.assertEqual('word', word.token_type)
        self.assertEqual('hello', word.content)
        self.assertEqual(0, word.source_pos.start_line)
        self.assertEqual(0, word.source_pos.end_line)
        self.assertEqual(0, word.source_pos.start_char)
        self.assertEqual(5, word.source_pos.end_char)

    def test_TryWord_OneWord2(self):
        (new_pos, word) = mp._TryWord('hello \n   hello', 10, 1)

        self.assertEqual(15, new_pos)
        self.assertEqual('word', word.token_type)
        self.assertEqual('hello', word.content)
        self.assertEqual(1, word.source_pos.start_line)
        self.assertEqual(1, word.source_pos.end_line)
        self.assertEqual(10, word.source_pos.start_char)
        self.assertEqual(15, word.source_pos.end_char)

    def test_TryWord_OneWordSymbolsAndNonASCII(self):
        (new_pos, word) = mp._TryWord('hello-world-ε', 0, 0)

        self.assertEqual(13, new_pos)
        self.assertEqual('word', word.token_type)
        self.assertEqual('hello-world-ε', word.content)
        self.assertEqual(0, word.source_pos.start_line)
        self.assertEqual(0, word.source_pos.end_line)
        self.assertEqual(0, word.source_pos.start_char)
        self.assertEqual(13, word.source_pos.end_char)

    def test_TryWord_TwoWords(self):
        (new_pos, word) = mp._TryWord('hello world', 0, 0)

        self.assertEqual(5, new_pos)
        self.assertEqual('word', word.token_type)
        self.assertEqual('hello', word.content)
        self.assertEqual(0, word.source_pos.start_line)
        self.assertEqual(0, word.source_pos.end_line)
        self.assertEqual(0, word.source_pos.start_char)
        self.assertEqual(5, word.source_pos.end_char)

    def scaffold_TryWord_OneWordAndSomethingElse(self, something_else):
        (new_pos, word) = mp._TryWord('hello%s' % something_else, 0, 0)

        self.assertEqual(5, new_pos)
        self.assertEqual('word', word.token_type)
        self.assertEqual('hello', word.content)
        self.assertEqual(0, word.source_pos.start_line)
        self.assertEqual(0, word.source_pos.end_line)
        self.assertEqual(0, word.source_pos.start_char)
        self.assertEqual(5, word.source_pos.end_char)

    def test_TryWord_OneWordAndSomethingElse(self):
        self.scaffold_TryWord_OneWordAndSomethingElse('\n')
        self.scaffold_TryWord_OneWordAndSomethingElse('{')
        self.scaffold_TryWord_OneWordAndSomethingElse('{')
        self.scaffold_TryWord_OneWordAndSomethingElse('\\')
        self.scaffold_TryWord_OneWordAndSomethingElse('=')
        self.scaffold_TryWord_OneWordAndSomethingElse('*')

    def test_TryBlob_OneBlob(self):
        (new_pos, new_line, blob) = mp._TryBlob('{hello}', 0, 0)

        self.assertEqual(7, new_pos)
        self.assertEqual(0, new_line)
        self.assertEqual('blob', blob.token_type)
        self.assertEqual('{hello}', blob.content)
        self.assertEqual(0, blob.source_pos.start_line)
        self.assertEqual(0, blob.source_pos.end_line)
        self.assertEqual(0, blob.source_pos.start_char)
        self.assertEqual(7, blob.source_pos.end_char)

    def test_TryBlob_OneBlob2(self):
        (new_pos, new_line, blob) = mp._TryBlob('hello  \n  {hello}', 10, 1)

        self.assertEqual(17, new_pos)
        self.assertEqual(1, new_line)
        self.assertEqual('blob', blob.token_type)
        self.assertEqual('{hello}', blob.content)
        self.assertEqual(1, blob.source_pos.start_line)
        self.assertEqual(1, blob.source_pos.end_line)
        self.assertEqual(10, blob.source_pos.start_char)
        self.assertEqual(17, blob.source_pos.end_char)

    def test_TryBlob_ComplexBlob(self):
        (new_pos, new_line, blob) = mp._TryBlob('{hello world \n how are you today?}', 0, 0)

        self.assertEqual(34, new_pos)
        self.assertEqual(1, new_line)
        self.assertEqual('blob', blob.token_type)
        self.assertEqual('{hello world \n how are you today?}', blob.content)
        self.assertEqual(0, blob.source_pos.start_line)
        self.assertEqual(1, blob.source_pos.end_line)
        self.assertEqual(0, blob.source_pos.start_char)
        self.assertEqual(34, blob.source_pos.end_char)

    def test_TryBlob_EvenMoreComplexBlob(self):
        (new_pos, new_line, blob) = mp._TryBlob('{hello world {lala} \n how are you today{\n{\n}}?}', 0, 0)

        self.assertEqual(47, new_pos)
        self.assertEqual(3, new_line)
        self.assertEqual('blob', blob.token_type)
        self.assertEqual('{hello world {lala} \n how are you today{\n{\n}}?}', blob.content)
        self.assertEqual(0, blob.source_pos.start_line)
        self.assertEqual(3, blob.source_pos.end_line)
        self.assertEqual(0, blob.source_pos.start_char)
        self.assertEqual(47, blob.source_pos.end_char)

    def test_TryBlob_OneWordSymbolsandNonASCII(self):
        (new_pos, new_line, blob) = mp._TryBlob('{hello-world-ε}', 0, 0)

        self.assertEqual(15, new_pos)
        self.assertEqual(0, new_line)
        self.assertEqual('blob', blob.token_type)
        self.assertEqual('{hello-world-ε}', blob.content)
        self.assertEqual(0, blob.source_pos.start_line)
        self.assertEqual(0, blob.source_pos.end_line)
        self.assertEqual(0, blob.source_pos.start_char)
        self.assertEqual(15, blob.source_pos.end_char)

    def test_TryBlob_OneBlobAndSomethingElse(self):
        (new_pos, new_line, blob) = mp._TryBlob('{hello}  \n', 0, 0)

        self.assertEqual(7, new_pos)
        self.assertEqual(0, new_line)
        self.assertEqual('blob', blob.token_type)
        self.assertEqual('{hello}', blob.content)
        self.assertEqual(0, blob.source_pos.start_line)
        self.assertEqual(0, blob.source_pos.end_line)
        self.assertEqual(0, blob.source_pos.start_char)
        self.assertEqual(7, blob.source_pos.end_char)

    def test_TryBlob_ErrorWhenForgotBraceEnd(self):
        with self.assertRaises(errors.Error):
            mp._TryBlob('{hello-world-ε', 0, 0)

        with self.assertRaises(errors.Error):
            mp._TryBlob('{hello-world-ε{}', 0, 0)

    def test_TrySlash_OneSlash(self):
        (new_pos, slash) = mp._TrySlash('\\', 0, 0)

        self.assertEqual(1, new_pos)
        self.assertEqual('slash', slash.token_type)
        self.assertEqual('\\', slash.content)
        self.assertEqual(0, slash.source_pos.start_line)
        self.assertEqual(0, slash.source_pos.end_line)
        self.assertEqual(0, slash.source_pos.start_char)
        self.assertEqual(1, slash.source_pos.end_char)

    def test_TrySlash_OneSlash2(self):
        (new_pos, slash) = mp._TrySlash('hello  \n  \\', 10, 1)

        self.assertEqual(11, new_pos)
        self.assertEqual('slash', slash.token_type)
        self.assertEqual('\\', slash.content)
        self.assertEqual(1, slash.source_pos.start_line)
        self.assertEqual(1, slash.source_pos.end_line)
        self.assertEqual(10, slash.source_pos.start_char)
        self.assertEqual(11, slash.source_pos.end_char)

    def test_TrySlash_OneSlashAndSomethingElse(self):
        (new_pos, slash) = mp._TrySlash('\\  \n', 0, 0)

        self.assertEqual(1, new_pos)
        self.assertEqual('slash', slash.token_type)
        self.assertEqual('\\', slash.content)
        self.assertEqual(0, slash.source_pos.start_line)
        self.assertEqual(0, slash.source_pos.end_line)
        self.assertEqual(0, slash.source_pos.start_char)
        self.assertEqual(1, slash.source_pos.end_char)

    def test_TryMarker_OneMarker(self):
        re_marker = re.compile(r'(=+)')
        (new_pos, marker) = mp._TryMarker('=', 'section-marker', re_marker, 0, 0)

        self.assertEqual(1, new_pos)
        self.assertEqual('section-marker', marker.token_type)
        self.assertEqual('=', marker.content)
        self.assertEqual(0, marker.source_pos.start_line)
        self.assertEqual(0, marker.source_pos.end_line)
        self.assertEqual(0, marker.source_pos.start_char)
        self.assertEqual(1, marker.source_pos.end_char)

    def test_TryMarker_OneMarker2(self):
        re_marker = re.compile(r'(=+)')
        (new_pos, marker) = mp._TryMarker('hello  \n  =', 'section-marker', re_marker, 10, 1)

        self.assertEqual(11, new_pos)
        self.assertEqual('section-marker', marker.token_type)
        self.assertEqual('=', marker.content)
        self.assertEqual(1, marker.source_pos.start_line)
        self.assertEqual(1, marker.source_pos.end_line)
        self.assertEqual(10, marker.source_pos.start_char)
        self.assertEqual(11, marker.source_pos.end_char)

    def test_TryMarker_ManyMarkers(self):
        re_marker = re.compile(r'(=+)')
        (new_pos, marker) = mp._TryMarker('===', 'section-marker', re_marker, 0, 0)

        self.assertEqual(3, new_pos)
        self.assertEqual('section-marker', marker.token_type)
        self.assertEqual('===', marker.content)
        self.assertEqual(0, marker.source_pos.start_line)
        self.assertEqual(0, marker.source_pos.end_line)
        self.assertEqual(0, marker.source_pos.start_char)
        self.assertEqual(3, marker.source_pos.end_char)

    def test_TryMarker_OneMarkerAndSomethingElse(self):
        re_marker = re.compile(r'(=+)')
        (new_pos, marker) = mp._TryMarker('=  \n', 'section-marker', re_marker, 0, 0)

        self.assertEqual(1, new_pos)
        self.assertEqual('section-marker', marker.token_type)
        self.assertEqual('=', marker.content)
        self.assertEqual(0, marker.source_pos.start_line)
        self.assertEqual(0, marker.source_pos.end_line)
        self.assertEqual(0, marker.source_pos.start_char)
        self.assertEqual(1, marker.source_pos.end_char)

    def test_TryParagraphEnd_OneParagraphEndWithWS(self):
        (new_pos, new_line, paragraph_end) = mp._TryParagraphEnd('\n', 0, 0)

        self.assertEqual(1, new_pos)
        self.assertEqual('paragraph-end', paragraph_end.token_type)
        self.assertEqual('\n', paragraph_end.content)
        self.assertEqual(0, paragraph_end.source_pos.start_line)
        self.assertEqual(1, paragraph_end.source_pos.end_line)
        self.assertEqual(0, paragraph_end.source_pos.start_char)
        self.assertEqual(1, paragraph_end.source_pos.end_char)

    def test_TryParagraphEnd_OneParagraphEndWithSection(self):
        (new_pos, new_line, paragraph_end) = mp._TryParagraphEnd('=', 0, 0)

        self.assertEqual(0, new_pos)
        self.assertEqual('paragraph-end', paragraph_end.token_type)
        self.assertEqual('', paragraph_end.content)
        self.assertEqual(0, paragraph_end.source_pos.start_line)
        self.assertEqual(0, paragraph_end.source_pos.end_line)
        self.assertEqual(0, paragraph_end.source_pos.start_char)
        self.assertEqual(0, paragraph_end.source_pos.end_char)

    def test_TryParagraphEnd_ComplexParagraphEnd(self):
        (new_pos, new_line, paragraph_end) = mp._TryParagraphEnd('  \n\n\t  \n', 0, 0)

        self.assertEqual(8, new_pos)
        self.assertEqual('paragraph-end', paragraph_end.token_type)
        self.assertEqual('  \n\n\t  \n', paragraph_end.content)
        self.assertEqual(0, paragraph_end.source_pos.start_line)
        self.assertEqual(3, paragraph_end.source_pos.end_line)
        self.assertEqual(0, paragraph_end.source_pos.start_char)
        self.assertEqual(8, paragraph_end.source_pos.end_char)

    def test_TryParagraphEnd_ComplexParagraphEnd2(self):
        (new_pos, new_line, paragraph_end) = mp._TryParagraphEnd('  \n\n\t  ', 0, 0)

        self.assertEqual(4, new_pos)
        self.assertEqual('paragraph-end', paragraph_end.token_type)
        self.assertEqual('  \n\n', paragraph_end.content)
        self.assertEqual(0, paragraph_end.source_pos.start_line)
        self.assertEqual(2, paragraph_end.source_pos.end_line)
        self.assertEqual(0, paragraph_end.source_pos.start_char)
        self.assertEqual(4, paragraph_end.source_pos.end_char)

    def test_TryParagraphEnd_ComplexParagraphEnd3(self):
        (new_pos, new_line, paragraph_end) = mp._TryParagraphEnd('  \n\n\t  \n=', 0, 0)

        self.assertEqual(8, new_pos)
        self.assertEqual('paragraph-end', paragraph_end.token_type)
        self.assertEqual('  \n\n\t  \n', paragraph_end.content)
        self.assertEqual(0, paragraph_end.source_pos.start_line)
        self.assertEqual(3, paragraph_end.source_pos.end_line)
        self.assertEqual(0, paragraph_end.source_pos.start_char)
        self.assertEqual(8, paragraph_end.source_pos.end_char)

    def test_SkipWS(self):
        self.assertEqual(3, mp._SkipWS('  \t', 0, 0))
        self.assertEqual(3, mp._SkipWS('  \thello', 0, 0))
        self.assertEqual(3, mp._SkipWS('  \t\nhello', 0, 0))

if __name__ == '__main__':
    unittest.main()
