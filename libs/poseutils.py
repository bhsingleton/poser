import json

from dcc.maya.json.mdataparser import MDataEncoder, MDataDecoder
from .pose import Pose

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def createPose(*nodes, **kwargs):
    """
    Returns a new pose using the supplied nodes.

    :key animationRange: Tuple[int, int]
    :key step: int
    :key skipKeys: bool
    :key skipTransformation: bool
    :rtype: Pose
    """

    return Pose.create(*nodes, **kwargs)


def dumpPose(pose):
    """
    Dumps the supplied pose into a string.

    :type pose: Union[Pose, List[Pose]]
    :rtype: str
    """

    return json.dumps(pose, cls=MDataEncoder)


def loadPose(string):
    """
    Loads the pose from the supplied string.

    :type string: str
    :rtype: Union[Pose, List[Pose]]
    """

    return json.loads(string, cls=MDataDecoder)


def exportPose(filePath, pose, **kwargs):
    """
    Exports the supplied pose to the specified path.

    :type filePath: str
    :type pose: Pose
    :key skipKeys: bool
    :key skipLayers: bool
    :key skipTransformations: bool
    :rtype: None
    """

    # Open file and serialize pose
    #
    with open(filePath, 'w') as jsonFile:

        log.info('Exporting pose to: %s' % filePath)
        json.dump(pose, jsonFile, cls=MDataEncoder, indent=4)


def exportPoseFromNodes(filePath, nodes, **kwargs):
    """
    Exports a pose using the supplied nodes to the specified path.

    :type filePath: str
    :type nodes: List[mpynode.MPyNode]
    :key skipKeys: bool
    :key skipLayers: bool
    :key skipTransformations: bool
    :rtype: None
    """

    pose = createPose(*nodes, **kwargs)
    exportPose(filePath, pose)


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
