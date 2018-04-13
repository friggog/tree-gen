"""L-System based tree generation system"""

from imp import reload
from time import time


def construct(modname, generate_leaves=True):
    """Construct the tree"""
    start_time = time()
    print('\n** Generating Tree **')
    mod = __import__(modname, fromlist=[''])
    reload(mod)
    mod.system().parse(generate_leaves)
    print('\nTree generated in %f seconds\n' % (time() - start_time))
