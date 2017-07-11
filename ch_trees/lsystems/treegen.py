"""L-System based tree generation system"""

from imp import reload
from time import time


def construct(modname):
    """Construct the tree"""
    start_time = time()
    print('** Generating Tree **')
    mod = __import__(modname, fromlist=[''])
    reload(mod)
    mod.system().parse()
    print('Tree generated in %f seconds' % (time() - start_time))


# construct('ch_trees.lsystems.sys_defs.quaking_aspen')
