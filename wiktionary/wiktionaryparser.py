from itertools import takewhile as _takewhile
from urllib2 import quote as _urlescape
import re

def _createSectionRegex(min_level, headers):
    template = r'''
        (?:^|\r|\n|\r\n)
        ={%(min_level)d,}
        (?:\{\{)?
        (%(headers)s)
        (?:\}\})?
        ={%(min_level)d,}
        \s*
        (?:^|\r|\n|\r\n)
        (.*?)
        (?:(?=(?:^|\r|\n|\r\n)=)|$)
    '''

    headers = '|'.join(re.escape(i) for i in headers)
    return re.compile(template % locals(),
                      re.VERBOSE | re.UNICODE | re.DOTALL | re.IGNORECASE)


RE_AUDIO_TAG = re.compile(r'\{\{audio\|([^|}]*)\|([^|}]*)\}\}')
RE_AUDIO_TYPE = re.compile(r'[A-Z](?:[-/\\A-Z]*[A-Z])\b')
RE_IPA = re.compile(r'\{\{IPA\|([^|}]*)', re.UNICODE)
RE_BULLET_ITEMS = re.compile(r'^\*(.+)$', re.MULTILINE | re.UNICODE)
RE_HASH_LINES = re.compile(r'^#(.+)$', re.MULTILINE | re.UNICODE)
RE_EXAMPLE_START = re.compile(r'^([*#]:?|:)')
RE_TAG = re.compile(r'<[^>]*>[^<>]*</[^>]*>')
RE_INNER_LINK = re.compile(r'\[\[(.+?)(?:\|.*?)?\]\]', re.UNICODE)
RE_STRONG = re.compile(r"'''(.*?)'''", re.UNICODE | re.DOTALL)
RE_EMPHASIS = re.compile(r"''(.*?)''", re.UNICODE | re.DOTALL)
RE_LINK = re.compile(r"\[\[(.*?)(?:\|(.*?))?\]\](\w*)", re.UNICODE)
RE_MULTISPACE = re.compile(r'\s{2,}', re.UNICODE)
RE_EXAMPLE_BREAK = re.compile(r".(?<=\W)(?=['\"\w])\s*(.+)", re.UNICODE)
RE_INIT_YEAR = re.compile(r"^\W*'''\d{4}'''", re.UNICODE)
RE_TEMPLATE = re.compile(r'\{\{(?:(?:context|(?:non-)?gloss definition)\|)?([^{}|]+)(\|.*?)?\}\}', re.UNICODE | re.DOTALL)
RE_ONLY_TEMPLATE = re.compile(r'^\W*\{\{(?:(?!\}\}).)*\}\}\W*$', re.UNICODE | re.DOTALL)

RE_SYNONYM_SECTIONS = _createSectionRegex(3, ['Synonyms'])
RE_ANTONYM_SECTIONS = _createSectionRegex(3, ['Antonyms'])

RELATED_HEADERS = ['See also', 'Related terms', 'Derived terms',
                   'Coordinate terms', 'Troponyms', 'Alternative forms']
RE_RELATED_SECTIONS = _createSectionRegex(3, RELATED_HEADERS)

MEANING_HEADERS = ['Acronym', 'Abbreviation', 'Initialism', 'Numeral', 'Letter',
                   'Symbol', 'Proper noun', 'Article', 'Prefix', 'Suffix',
                   'Preposition', 'Interjection', 'Conjunction', 'Determiner',
                   'Pronoun', 'Verb', 'Adverb', 'Adjective', 'Noun', 'Idiom',
                   'Proverb']
RE_MEANING_SECTIONS = _createSectionRegex(2, MEANING_HEADERS)


def _getLinksInSection(page, section_regex):
    raw_sections = section_regex.findall(page)
    related = []
    for title, content in raw_sections:
        content_lines = RE_BULLET_ITEMS.findall(content)
        for line in content_lines:
            related += RE_INNER_LINK.findall(line)
    return [i for i in related if ':' not in i]

def _evalWikiMarkup(text):
    # Order matters!
    text = RE_TAG.sub('', text)
    text = RE_STRONG.sub(r'<strong>\1</strong>', text)
    text = RE_EMPHASIS.sub(r'<em>\1</em>', text)

    def evalTemplate(match):
        template = match.group(1).strip()
        content = match.group(2)
        if template.endswith(' of') and content:
            if template == 'form of' and content.count('|') == 2 and ' form|' in content:
                template, content = content.strip('|').split('|')
                template += ' of'
            else:
                content = re.sub(r'\|[^|=]*=[^|=]*(\||$)', '', content)
                if '|' in content:
                    content = content[content.rindex('|') + 1:]
            return template.capitalize() + ' ' + content + '.'
        else:
          index = text.index(match.group(0))
          prefix = RE_TEMPLATE.sub('', text[:index]).strip()
          if not prefix:
            label = template + ', ' + content[1:] if content else template
            label = label.replace('|_|', ' ').replace('|', ' ')
            return '<span class="label">' + label + '</span>'
          else:
            return ''

    text = RE_TEMPLATE.sub(evalTemplate, text.lstrip())
    text = re.sub(r'</span>\s*<span class="label">', ', ', text)

    def formatLink(match):
        if match.group(1).startswith('w:'):
            return match.group(2) or ''
        if ':' in match.group(1):
            return ''
        
        escaped_term = _urlescape(match.group(1).encode('utf8')).decode('utf8')
        if match.group(2):
            link_text = match.group(2)
        else:
            link_text = match.group(1) + match.group(3)
        return (r'<a href="http://en.wiktionary.org/wiki/%s">%s</a>' %
                (escaped_term, link_text))
    
    text = RE_LINK.sub(formatLink, text)
    text = RE_MULTISPACE.sub(' ', text).strip()
    
    return text


def parseAudio(page):
    raw_audio_tags = RE_AUDIO_TAG.findall(page)
    audio_tags = []

    for audio_file, audio_type in raw_audio_tags:
        audio_type = audio_type.replace('Canadian', 'CA').replace('CAN', 'CA')
        audio_type = RE_AUDIO_TYPE.findall(audio_type) or None
        if audio_type:
            audio_type = audio_type[0]

        audio_tags.append({'file': audio_file, 'type': audio_type})
        
    return audio_tags

def parseIPA(page):
    return RE_IPA.findall(page)

def parseSynonyms(page):
    return _getLinksInSection(page, RE_SYNONYM_SECTIONS)

def parseAntonyms(page):
    return _getLinksInSection(page, RE_ANTONYM_SECTIONS)

def parseRelated(page):
    return _getLinksInSection(page, RE_RELATED_SECTIONS)

def parseMeanings(page):
    def isExampleLine(line):
        return RE_EXAMPLE_START.search(line) is not None
    
    raw_sections = RE_MEANING_SECTIONS.findall(page)
    meanings = []
    for title, content in raw_sections:
        hash_lines = RE_HASH_LINES.findall(content)
        while hash_lines:
            if isExampleLine(hash_lines[0]):
                raise Exception(u'Orphan example on page: ' + page)
            content = _evalWikiMarkup(hash_lines[0])
            hash_lines = hash_lines[1:]

            examples = list(_takewhile(isExampleLine, hash_lines))
            hash_lines = hash_lines[len(examples):]
            examples = [_evalWikiMarkup(RE_EXAMPLE_BREAK.findall(i)[0])
                        for i in examples
                        if (len(i.split()) > 1 and
                            RE_EXAMPLE_BREAK.search(i) and
                            not i.startswith('* ') and
                            not RE_ONLY_TEMPLATE.match(i) and
                            not RE_INIT_YEAR.search(i))]
            examples = filter(None, examples)

            if content:
                meanings.append({'type': title.capitalize(),
                                 'content': content,
                                 'examples': examples})

    return meanings