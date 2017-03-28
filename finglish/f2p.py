#!/usr/bin/env python3

import os
import re
import itertools
from functools import reduce

sep_regex = re.compile(r'[ \-_~!@#%$^&*\(\)\[\]\{\}/\:;"|,./?`]')

def get_portable_filename(filename):
    path, _ = os.path.split(__file__)
    filename = os.path.join(path, filename)
    return filename

def load_conversion_file(filename):
    filename = get_portable_filename(filename)
    with open(filename) as f:
        l = list(f)
        l = [i for i in l if i.strip()]
        l = [i.strip().split() for i in l]
    return {i[0]: i[1:] for i in l}

print('Loading converters...')
beginning = load_conversion_file('f2p-beginning.txt')
middle = load_conversion_file('f2p-middle.txt')
ending = load_conversion_file('f2p-ending.txt')

print('Loading persian word list...')
with open(get_portable_filename('persian-word-freq.txt')) as f:
    word_freq = list(f)
word_freq = [i.strip() for i in word_freq if i.strip()]
word_freq = [i.split() for i in word_freq if not i.startswith('#')]
word_freq = {i[0]: int(i[1]) for i in word_freq}

print('Loading dictionary...')
with open(get_portable_filename('f2p-dict.txt')) as f:
    dictionary = [i.strip().split(' ', 1) for i in f if i.strip()]
    dictionary = {k.strip(): v.strip() for k, v in dictionary}

def f2p_word_internal(word, original_word):
    # this function receives the word as separate letters
    persian = []
    for i, letter in enumerate(word):
        if i == 0:
            converter = beginning
        elif i == len(word) - 1:
            converter = ending
        else:
            converter = middle
        conversions = converter.get(letter)
        if conversions == None:
            return [(''.join(original_word), 0.0)]
        else:
            conversions = ['' if i == 'nothing' else i for i in conversions]
        persian.append(conversions)

    alternatives = itertools.product(*persian)
    alternatives = [''.join(i) for i in alternatives]

    alternatives = [(i, word_freq[i]) if i in word_freq else (i, 0)
                    for i in alternatives]

    if len(alternatives) > 0:
        max_freq = max(freq for _, freq in alternatives)
        alternatives = [(w, float(freq / max_freq)) if freq != 0 else (w, 0.0)
                        for w, freq in alternatives]
    else:
        alternatives = [(''.join(word), 1.0)]

    return alternatives

def variations(word):
    """Create variations of the word based on letter combinations like oo,
sh, etc."""

    if len(word) == 1:
        return [[word[0]]]
    elif word == 'aa':
        return [['A']]
    elif word == 'ee':
        return [['i']]
    elif word == 'ei':
        return [['ei']]
    elif word in ['oo', 'ou']:
        return [['u']]
    elif word == 'kha':
        return [['kha'], ['kh', 'a']]
    elif word in ['kh', 'gh', 'ch', 'sh', 'zh']:
        return [[word]]
    elif word in ["a'", "e'", "o'", "i'", "u'", "A'"]:
        return [[word[0] + "'"]]
    elif len(word) == 2 and word[0] == word[1]:
        return [[word[0]]]

    if word[:2] == 'aa':
        return [['A'] + i for i in variations(word[2:])]
    elif word[:2] == 'ee':
        return [['i'] + i for i in variations(word[2:])]
    elif word[:2] in ['oo', 'ou']:
        return [['u'] + i for i in variations(word[2:])]
    elif word[:3] == 'kha':
        return \
            [['kha'] + i for i in variations(word[3:])] + \
            [['kh', 'a'] + i for i in variations(word[3:])] + \
            [['k', 'h', 'a'] + i for i in variations(word[3:])]
    elif word[:2] in ['kh', 'gh', 'ch', 'sh', 'zh']:
        return \
            [[word[:2]] + i for i in variations(word[2:])] + \
            [[word[0]] + i for i in variations(word[1:])]
    elif word[:2] in ["a'", "e'", "o'", "i'", "u'", "A'"]:
        return [[word[:2]] + i for i in variations(word[2:])]
    elif len(word) >= 2 and word[0] == word[1]:
        return [[word[0]] + i for i in variations(word[2:])]
    else:
        return [[word[0]] + i for i in variations(word[1:])]

def f2p_word(word, max_word_size=15, cutoff=3):
    """Convert a single word from Finglish to Persian.

    max_word_size: Maximum size of the words to consider. Words larger
    than this will be kept unchanged.

    cutoff: The cut-off point. For each word, there could be many
    possibilities. By default 3 of these possibilities are considered
    for each word. This number can be changed by this argument.

    """

    c = dictionary.get(word)
    if c:
        return [(c, 1.0)]

    original_word = word

    if word == '':
        return []
    elif len(word) > max_word_size:
        return [(word, 1.0)]

    word = word.lower()

    results = []
    for w in variations(word):
        results.extend(f2p_word_internal(w, original_word))

    # sort results based on the confidence value
    results.sort(key=lambda r: r[1], reverse=True)

    # return the top three results in order to cut down on the number
    # of possibilities.
    return results[:cutoff]

def f2p(phrase, max_word_size=15, cutoff=3):
    """Convert a phrase from Finglish to Persian.

    phrase: The phrase to convert.

    max_word_size: Maximum size of the words to consider. Words larger
    than this will be kept unchanged.

    cutoff: The cut-off point. For each word, there could be many
    possibilities. By default 3 of these possibilities are considered
    for each word. This number can be changed by this argument.

    """

    # split the phrase into words
    results = [w for w in sep_regex.split(phrase) if w]

    # return an empty list if no words
    if results == []:
        return []

    # convert each word separately
    results = [f2p_word(w, max_word_size, cutoff) for w in results]

    # create the Cartesian product of the results
    results = list(itertools.product(*results))

    # the results now contain (word, confidence) pairs. re-group these
    # so that words are in one tuple and the confidence values are in
    # another
    results = [list(zip(*r)) for r in results]

    # join the words into phrases, while calculate the multiplication
    # product of the confidence values
    results = [(' '.join(words), reduce(lambda x, y: x * y, confs))
               for words, confs in results]

    # sort based on the confidence (product)
    results.sort(key=lambda r: r[1], reverse=True)

    return results

def main():
    print('finglish: ', end='')
    phrase = input()
    results = f2p(phrase)
    for p, c in results[:10]:
        print(c, p)

if __name__ == '__main__':
    main()
