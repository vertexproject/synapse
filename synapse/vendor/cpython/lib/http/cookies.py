##############################################################################
# Taken from the cpython 3.11 source branch after the 3.11.10 release.
##############################################################################
####
# Copyright 2000 by Timothy O'Malley <timo@alum.mit.edu>
#
#                All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software
# and its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Timothy O'Malley  not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# Timothy O'Malley DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS, IN NO EVENT SHALL Timothy O'Malley BE LIABLE FOR
# ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#

#
# Import our required modules
#
import re

_unquote_sub = re.compile(r'\\(?:([0-3][0-7][0-7])|(.))').sub

def _unquote_replace(m):
    if m[1]:
        return chr(int(m[1], 8))
    else:
        return m[2]

def _unquote(str):
    # If there aren't any doublequotes,
    # then there can't be any special characters.  See RFC 2109.
    if str is None or len(str) < 2:
        return str
    if str[0] != '"' or str[-1] != '"':
        return str

    # We have to assume that we must decode this string.
    # Down to work.

    # Remove the "s
    str = str[1:-1]

    # Check for special sequences.  Examples:
    #    \012 --> \n
    #    \"   --> "
    #
    return _unquote_sub(_unquote_replace, str)
