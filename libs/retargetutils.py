import os

from dcc.json import jsonutils
from dcc.maya.json.mdataparser import MDataDecoder
from .retargeter import Retargeter

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def loadBinders():
    """
    Loads the binders from the binder directory.

    :rtype: List[Retargeter]
    """

    # Get configuration directory
    #
    cwd = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.join(cwd, '..', 'binders')

    # Iterate through configuration files
    #
    filePaths = [os.path.join(directory, filename) for filename in os.listdir(directory) if filename.endswith('.json')]
    numFilePaths = len(filePaths)

    binders = [None] * numFilePaths

    for (i, filePath) in enumerate(filePaths):

        binders[i] = jsonutils.load(filePath, cls=MDataDecoder)

    return binders
