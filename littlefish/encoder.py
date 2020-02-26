"""
Shamelessly stolen from stack overflow.  Maps integer values onto
strings of characters - useful for generating things like voucher codes
"""

import logging

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class Encoder:
    def __init__(self, alphabet):
        """
        Creates an encoder which maps integers onto characters from
        the string alphabet.  Similar to base64 encoding but with a
        custom set of characters

        :param alphabet: The characters to use to encode the numeric
                         values, i.e.:
                         "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        """
        self.alphabet = alphabet
        self.size = len(alphabet)
        # Map from char -> value
        self.mapping = dict((ch, i) for (i, ch) in enumerate(alphabet))
        if len(self.mapping) != self.size:
            raise Exception("Duplicate characters in alphabet string")

    def encode(self, x):
        # Only needed if don't want '' for 0
        if x == 0:
            return self.alphabet[0]
        
        out = []
        while x > 0:
            out.append(self.alphabet[x % self.size])
            x //= self.size
        return ''.join(out)

    def decode(self, s):
        return sum(self.mapping[ch] * self.size ** i for (i, ch) in enumerate(s))
