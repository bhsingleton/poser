import re

from dcc.json import jsonutils
from dcc.python import stringutils
from dcc.maya.json.mdataparser import MDataEncoder, MDataDecoder
from .pose import Pose

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


__animation_range__ = re.compile(r'"animationRange"\s*:\s*\[\s*([0-9]+),\s*([0-9]+)\s*\]')


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

    return jsonutils.dumps(pose, cls=MDataEncoder)


def loadPose(string):
    """
    Loads the pose from the supplied string.

    :type string: str
    :rtype: Union[Pose, List[Pose]]
    """

    return jsonutils.loads(string, cls=MDataDecoder)


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

    log.info('Exporting pose to: %s' % filePath)
    jsonutils.dump(filePath, pose, cls=MDataEncoder, indent=4)


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

    log.debug('Importing pose from: %s' % filePath)
    return jsonutils.load(filePath, cls=MDataDecoder)


def importPoseRange(filePath):
    """
    Returns the animation-range from the supplied pose.

    :type filePath: str
    :rtype: Union[Tuple[int, int], None]
    """

    # Read pose file
    #
    string = None

    with open(filePath, 'r') as jsonFile:

        string = ''.join(jsonFile.readlines())

    # Find all animation-range keys
    #
    groups = __animation_range__.findall(string)

    if len(groups) != 1:

        return None

    # Check if group is valid
    #
    startTime, endTime = groups[0]

    if not (stringutils.isNullOrEmpty(startTime) or stringutils.isNullOrEmpty(endTime)):

        return int(startTime), int(endTime)

    else:

        return None
