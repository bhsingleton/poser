import os

from dcc.json import jsonutils
from ..libs import rigconfiguration

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def loadConfigurations():
    """
    Loads all the available rig configurations.

    :rtype: List[rigconfiguration.RigConfiguration]
    """

    # Get configuration directory
    #
    cwd = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.join(cwd, '..', 'configs')

    # Iterate through configuration files
    #
    filePaths = [os.path.join(directory, filename) for filename in os.listdir(directory) if filename.endswith('.config')]
    numFilePaths = len(filePaths)

    configs = [None] * numFilePaths

    for (i, filePath) in enumerate(filePaths):

        configs[i] = jsonutils.load(filePath)

    return configs
