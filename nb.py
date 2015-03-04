__author__ = 'bmordue'

import sys
import os

import constants

from populate import populate
from prune import prune_starred

if __name__ == "__main__":
    import sys
    import os

#    sys.stdout = open("nb.log", "w")
    if sys.argv[0]:
        constants.MAX_PARSE = sys.argv[0]
    if not os.path.isfile(constants.DATABASE_FILENAME):
        populate()
#    add_comment_counts()
    prune_starred()
    print 'Done.'
    sys.stdout = sys.__stdout__
