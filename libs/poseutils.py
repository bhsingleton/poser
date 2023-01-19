import json

from .pose import Pose
from dcc.maya.json.mdataparser import MDataEncoder, MDataDecoder

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def createPose(*nodes, **kwargs):
    """
    Returns a new pose using the supplied nodes.

    :rtype: pose.Pose
    """

    return Pose.create(*nodes, **kwargs)


def exportPose(filePath, nodes, **kwargs):
    """
    Exports a pose for the supplied nodes to the specified path.

    :type filePath: str
    :type nodes: Union[List[om.MObject], om.MObjectArray, om.MSelectionList]
    :key skipKeys: bool
    :key skipLayers: bool
    :rtype: None
    """

    # Open file and serialize pose
    #
    pose = createPose(*nodes, **kwargs)

    with open(filePath, 'w') as jsonFile:

        log.info('Exporting pose to: %s' % filePath)
        json.dump(pose, jsonFile, cls=MDataEncoder, indent=4)


def importPose(filePath):
    """
    Imports the pose from the supplied path.

    :type filePath: str
    :rtype: pose.Pose
    """

    # Open file and deserialize data
    #
    with open(filePath, 'r') as jsonFile:

        return json.load(jsonFile, cls=MDataDecoder)
