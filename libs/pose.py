from maya.api import OpenMaya as om
from mpy import mpyscene, mpynode
from copy import copy, deepcopy
from operator import neg
from itertools import chain
from dcc.json import psonobject
from dcc.python import stringutils
from dcc.dataclasses import keyframe
from dcc.collections import notifylist, notifydict
from dcc.generators.inclusiverange import inclusiveRange
from dcc.maya.libs import sceneutils, transformutils, plugutils, plugmutators, animutils
from dcc.maya.json import melsonobject
from dcc.maya.decorators import animate

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Pose(melsonobject.MELSONObject):
    """
    Overload of `MELSONObject` that interfaces with pose data.
    """

    # region Dunderscores
    __slots__ = (
        '__weakref__',
        '_scene',
        '_name',
        '_filePath',
        '_animationRange',
        '_nodes',
        '_animLayers',
        '_thumbnail'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :rtype: None
        """

        # Call parent method
        #
        super(Pose, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._scene = mpyscene.MPyScene.getInstance(asWeakReference=True)
        self._name = kwargs.pop('name', self.scene.name)
        self._filePath = kwargs.pop('filePath', self.scene.filePath)
        self._animationRange = kwargs.pop('animationRange', self.scene.animationRange)
        self._nodes = notifylist.NotifyList()
        self._animLayers = notifylist.NotifyList()
        self._thumbnail = kwargs.pop('thumbnail', None)

        # Initialize notifies
        #
        self._nodes.addCallback('itemAdded', self.nodeAdded)
        self._nodes.addCallback('itemRemoved', self.nodeRemoved)
        self._nodes.extend(kwargs.pop('nodes', []))

        self._animLayers.addCallback('itemAdded', self.animLayerAdded)
        self._animLayers.addCallback('itemRemoved', self.animLayerRemoved)
        self._animLayers.extend(kwargs.pop('animLayers', []))
    # endregion

    # region Properties
    @property
    def scene(self):
        """
        Getter method that returns the scene interface.

        :rtype: mpyscene.MPyScene
        """

        return self._scene()

    @property
    def name(self):
        """
        Getter method that returns the name of this pose.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Setter method that updates the name for this pose.

        :type name: str
        :rtype: None
        """

        self._name = name

    @property
    def filePath(self):
        """
        Getter method that returns the source path of this pose.

        :rtype: str
        """

        return self._filePath

    @filePath.setter
    def filePath(self, filePath):
        """
        Setter method that updates the source path for this pose.

        :type filePath: str
        :rtype: None
        """

        self._filePath = filePath

    @property
    def animationRange(self):
        """
        Getter method that returns the animation range for this pose.

        :rtype: Tuple[int, int]
        """

        return self._animationRange

    @animationRange.setter
    def animationRange(self, animationRange):
        """
        Setter method that updates the animation range for this pose.

        :type animationRange: Tuple[int, int]
        :rtype: None
        """

        self._animationRange = animationRange

    @property
    def nodes(self):
        """
        Getter method that returns the nodes associated with this pose.

        :rtype: List[PoseNode]
        """

        return self._nodes

    @nodes.setter
    def nodes(self, nodes):
        """
        Setter method that updates the nodes associated with this pose.

        :type nodes: List[PoseNode]
        :rtype: None
        """

        self._nodes.clear()
        self._nodes.extend(nodes)

    @property
    def animLayers(self):
        """
        Getter method that returns the anim layers associated with this pose.

        :rtype: List[PoseAnimLayer]
        """

        return self._animLayers

    @animLayers.setter
    def animLayers(self, animLayers):
        """
        Setter method that updates the anim layers associated with this pose.

        :type animLayers: List[PoseAnimLayer]
        :rtype: None
        """

        self._animLayers.clear()
        self._animLayers.extend(animLayers)
    # endregion

    # region Callbacks
    def nodeAdded(self, index, node):
        """
        Node added callback.

        :type index: int
        :type node: PoseNode
        :rtype: None
        """

        node._pose = self.weakReference()

    def nodeRemoved(self, node):
        """
        Node removed callback.

        :type node: PoseNode
        :rtype: None
        """

        node._pose = self.nullWeakReference

    def animLayerAdded(self, index, animLayer):
        """
        Animation layer added callback.

        :type index: int
        :type animLayer: PoseAnimLayer
        :rtype: None
        """

        animLayer._pose = self.weakReference()

    def animLayerRemoved(self, animLayer):
        """
        Node removed callback.

        :type animLayer: PoseAnimLayer
        :rtype: None
        """

        animLayer._pose = self.nullWeakReference
    # endregion

    # region Methods
    def getAssociatedNodes(self, namespace=None):
        """
        Returns the nodes associated with this pose.

        :type namespace: Union[str, None]
        :rtype: List[mpynode.MPyNode]
        """

        nodes = [node.getAssociatedNode(namespace=namespace) for node in self.nodes]
        filteredNodes = list(filter(lambda node: node is not None, nodes))

        return filteredNodes

    def selectAssociatedNodes(self, namespace=None):
        """
        Selects the nodes associated with this pose.

        :type namespace: str
        :rtype: None
        """

        self.scene.setSelection(self.getAssociatedNodes(namespace=namespace))

    def getPoseByName(self, name, namespace='', ignoreCase=False):
        """
        Returns the pose node with the specified name.

        :type name: str
        :type namespace: str
        :type ignoreCase: bool
        :rtype: Union[PoseNode, None]
        """

        # Find poses with matching names
        #
        found = None

        if ignoreCase:

            found = [pose for pose in self.nodes if pose.name.lower() == name.lower()]

        else:

            found = [pose for pose in self.nodes if pose.name == name]

        # Inspect collected poses
        #
        numFound = len(found)

        if numFound == 0:

            return None

        elif numFound == 1:

            return found[0]

        else:

            filtered = [pose for pose in found if pose.namespace == namespace]
            numFiltered = len(filtered)

            return filtered[0] if numFiltered == 1 else None

    def iterAssociatedPoses(self, *nodes, **kwargs):
        """
        Returns a generator that yield node-pose pairs.

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :rtype: Iterator[Tuple[mpynode.MPyNode, PoseNode]]
        """

        # Iterate through nodes
        #
        for node in nodes:

            # Check if pose exists
            #
            name = node.name()
            namespace = node.namespace()

            pose = self.getPoseByName(name, namespace=namespace)

            if pose is not None:

                yield node, pose

            else:

                log.warning(f'Cannot find pose for "{name}" node!')
                continue

    def blendPose(self, otherPose, weight=0.0):
        """
        Blends this pose with the other pose.

        :type otherPose: Pose
        :type weight: float
        :rtype: Pose
        """

        # Iterate through nodes
        #
        blendPose = copy(self)

        for node in blendPose.nodes:

            # Check if node exists in other pose
            #
            otherNode = otherPose.getPoseByName(node.name)

            if otherNode is None:

                continue

            # Blend attributes with other node
            #
            for attribute in node.attributes:

                # Check if other node has attribute
                #
                otherAttribute = otherNode.getAttributeByName(attribute.name)

                if otherAttribute is None:

                    continue

                # Interpolate values
                #
                attribute.value = attribute.value + (otherAttribute.value - attribute.value) * weight

        return blendPose

    def applyTo(self, *nodes, **kwargs):
        """
        Applies this pose to the supplied nodes.

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :rtype: None
        """

        # Iterate through nodes
        #
        for (node, pose) in self.iterAssociatedPoses(*nodes, **kwargs):

            pose.applyValues(node, **kwargs)

    def applyOppositeTo(self, *nodes, **kwargs):
        """
        Applies this pose to the opposite nodes.

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :rtype: None
        """

        # Iterate through nodes
        #
        for (node, pose) in self.iterAssociatedPoses(*nodes, **kwargs):

            pose.mirrorValues(node, **kwargs)

    def applyRelativeTo(self, nodes, relativeTo, **kwargs):
        """
        Applies this pose relative to the specified node.
        This method expects the nodes to already be ordered based on priority!

        :type nodes: List[mpynode.MPyNode]
        :type relativeTo: mpynode.MPyNode
        :rtype: None
        """

        # Get world-matrix to reorient pose to
        #
        name = relativeTo.name()
        pose = self.getPoseByName(name)

        poseMatrix = None

        if pose is not None:

            poseMatrix = pose.worldMatrix

        else:

            log.error('Cannot locate pose from node: %s' % name)
            return

        # Iterate through nodes
        #
        worldMatrix = relativeTo.worldMatrix()

        for (node, pose) in self.iterAssociatedPoses(*nodes, **kwargs):

            # Calculate matrix based on offset matrix
            #
            offsetMatrix = pose.worldMatrix * poseMatrix.inverse()
            relativeMatrix = offsetMatrix * worldMatrix
            matrix = relativeMatrix * node.parentInverseMatrix()

            node.setMatrix(matrix, skipScale=True, **kwargs)

    def applyTransformsTo(self, *nodes, **kwargs):
        """
        Applies the matrix values to the supplied nodes.

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :key worldSpace: bool
        :rtype: None
        """

        # Iterate through nodes
        #
        worldSpace = kwargs.get('worldSpace', False)

        for (node, pose) in self.iterAssociatedPoses(*nodes, **kwargs):

            # Evaluate which transform space to use
            #
            if worldSpace:

                pose.applyWorldMatrix(node, **kwargs)

            else:

                pose.applyMatrix(node, **kwargs)

    @animate.Animate(state=True)
    def bakeTransformationsTo(self, *nodes, **kwargs):
        """
        Bakes the transform values to the supplied nodes.
        TODO: Implement support for decimal frames when preserving keys!

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :key animationRange: Union[Tuple[int, int], None]
        :key step: int
        :key snapKeys: bool
        :key preserveKeys: bool
        :rtype: None
        """

        # Evaluate bake method
        #
        preserveKeys = kwargs.get('preserveKeys', False)

        animationRange = kwargs.get('animationRange', self.animationRange)
        startTime, endTime = animationRange
        step = kwargs.get('step', 1)

        skipTranslate = kwargs.get('skipTranslate', False)
        skipRotate = kwargs.get('skipRotate', False)
        skipScale = kwargs.get('skipScale', True)

        if preserveKeys:

            # Iterate through nodes
            #
            for (node, pose) in self.iterAssociatedPoses(*nodes, **kwargs):

                # Get anim-curve inputs
                #
                animCurves = [node.findAnimCurve(plug) for plug in node.iterPlugs(channelBox=True, skipUserAttributes=True)]
                inputs = dict.fromkeys(chain(*[animCurve.inputs() for animCurve in animCurves if animCurve is not None]), True)

                # Iterate through time-range
                #
                for (i, time) in enumerate(inclusiveRange(startTime, endTime, step)):

                    # Check if input exists
                    #
                    hasInput = inputs.get(time, False)

                    if not hasInput:

                        continue

                    # Apply transform at time
                    #
                    self.scene.time = time

                    worldMatrix = pose.getTransformation(time)
                    matrix = worldMatrix * node.parentInverseMatrix()

                    node.setMatrix(matrix, skipTranslate=skipTranslate, skipRotate=skipRotate, skipScale=skipScale)

        else:

            # Iterate through time-range
            #
            for (i, time) in enumerate(inclusiveRange(startTime, endTime, step)):

                # Go to next frame
                #
                self.scene.time = time

                # Iterate through nodes
                #
                for (node, pose) in self.iterAssociatedPoses(*nodes, **kwargs):

                    # Check if keys should be cleared
                    #
                    if i == 0:

                        node.clearKeys(animationRange=animationRange, skipUserAttributes=True)

                    # Apply transform at time
                    #
                    worldMatrix = pose.getTransformation(time)
                    matrix = worldMatrix * node.parentInverseMatrix()

                    node.setMatrix(matrix, skipTranslate=skipTranslate, skipRotate=skipRotate, skipScale=skipScale)

    def applyAnimationRange(self):
        """
        Updates the animation range in the current scene file.

        :rtype: None
        """

        self.scene.animationRange = self.animationRange

    def applyAnimationTo(self, *nodes, insertAt=None, animationRange=None, **kwargs):
        """
        Updates the animation keys to the supplied nodes.

        :type insertAt: Union[int, None]
        :type animationRange: Union[Tuple[int, int], None]
        :rtype: None
        """

        # Iterate through nodes
        #
        for (node, pose) in self.iterAssociatedPoses(*nodes, **kwargs):

            pose.applyKeyframes(node, insertAt=insertAt, animationRange=animationRange)

    def applyAnimationOppositeTo(self, *nodes, insertAt=None, animationRange=None, **kwargs):
        """
        Updates the animation keys to the supplied nodes.

        :type insertAt: Union[int, None]
        :type animationRange: Union[Tuple[int, int], None]
        :rtype: None
        """

        # Iterate through nodes
        #
        for (node, pose) in self.iterAssociatedPoses(*nodes, **kwargs):

            pose.mirrorKeyframes(node, insertAt=insertAt, animationRange=animationRange)

    @classmethod
    def create(cls, *nodes, **kwargs):
        """
        Returns a new pose using the supplied nodes.

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :key animationRange: Tuple[int, int]
        :key step: int
        :key skipKeys: bool
        :key skipLayers: bool
        :key skipTransformation: bool
        :rtype: Pose
        """

        # Create new instance and add nodes
        #
        instance = cls(**kwargs)
        instance.nodes = [PoseNode.create(node, **kwargs) for node in nodes]

        # Check if anim layers should be added
        #
        baseLayer = animutils.getBaseAnimLayer()
        hasBaseLayer = not baseLayer.isNull()

        skipLayers = kwargs.get('skipLayers', True)

        if not skipLayers and hasBaseLayer:

            instance.animLayers = [PoseAnimLayer.create(mpynode.MPyNode(baseLayer), nodes=nodes)]

        return instance
    # endregion


class PoseNode(melsonobject.MELSONObject):
    """
    Overload of `MELSONObject` that interfaces with pose nodes.
    """

    # region Dunderscores
    __slots__ = (
        '_pose',
        '_name',
        '_namespace',
        '_uuid',
        '_path',
        '_attributes',
        '_matrix',
        '_worldMatrix',
        '_transformations'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :rtype: None
        """

        # Call parent method
        #
        super(PoseNode, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._pose = self.nullWeakReference
        self._name = kwargs.pop('name', '')
        self._namespace = kwargs.pop('namespace', '')
        self._uuid = kwargs.pop('uuid', '')
        self._path = kwargs.pop('path', '')
        self._attributes = kwargs.pop('attributes', [])
        self._matrix = kwargs.pop('matrix', om.MMatrix.kIdentity)
        self._worldMatrix = kwargs.pop('worldMatrix', om.MMatrix.kIdentity)
        self._transformations = kwargs.pop('transformations', {})
    # endregion

    # region Properties
    @property
    def pose(self):
        """
        Getter method that returns the associated pose.

        :rtype: Pose
        """

        return self._pose()

    @property
    def scene(self):
        """
        Getter method that returns the scene interface.

        :rtype: mpyscene.MPyScene
        """

        return self.pose.scene

    @property
    def name(self):
        """
        Getter method that returns the name of this node.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Setter method that updates the name for this node.

        :type name: str
        :rtype: None
        """

        self._name = name

    @property
    def namespace(self):
        """
        Getter method that returns the namespace of this node.

        :rtype: str
        """

        return self._namespace

    @namespace.setter
    def namespace(self, namespace):
        """
        Setter method that updates the namespace for this node.

        :type namespace: str
        :rtype: None
        """

        self._namespace = namespace

    @property
    def uuid(self):
        """
        Getter method that returns the uuid of this node.

        :rtype: str
        """

        return self._uuid

    @uuid.setter
    def uuid(self, uuid):
        """
        Setter method that updates the uuid for this node.

        :type uuid: str
        :rtype: None
        """

        self._uuid = uuid

    @property
    def path(self):
        """
        Getter method that returns the path to this node.

        :rtype: str
        """

        return self._path

    @path.setter
    def path(self, path):
        """
        Setter method that updates the path to this node.

        :type path: str
        :rtype: None
        """

        self._path = path

    @property
    def attributes(self):
        """
        Getter method that returns the attributes from this node.

        :rtype: List[PoseAttribute]
        """

        return self._attributes

    @attributes.setter
    def attributes(self, attributes):
        """
        Setter method that updates the attributes for this node.

        :type attributes: List[PoseAttribute]
        :rtype: None
        """

        self._attributes.clear()
        self._attributes.extend(attributes)

    @property
    def matrix(self):
        """
        Getter method that returns the matrix for this pose node.

        :rtype: om.MMatrix
        """

        return self._matrix

    @matrix.setter
    def matrix(self, matrix):
        """
        Setter method that updates the matrix for this pose node.

        :type matrix: om.MMatrix
        :rtype: None
        """

        self._matrix = om.MMatrix(matrix)

    @property
    def worldMatrix(self):
        """
        Getter method that returns the world-matrix for this pose node.

        :rtype: om.MMatrix
        """

        return self._worldMatrix

    @worldMatrix.setter
    def worldMatrix(self, worldMatrix):
        """
        Setter method that updates the world-matrix for this pose node.

        :type worldMatrix: om.MMatrix
        :rtype: None
        """

        self._worldMatrix = om.MMatrix(worldMatrix)

    @property
    def transformations(self):
        """
        Getter method that returns the transformations for this pose node.

        :rtype: Dict[int, om.MMatrix]
        """

        return self._transformations

    @transformations.setter
    def transformations(self, transformations):
        """
        Setter method that updates the transformations for this pose node.

        :type transformations: Dict[int, om.MMatrix]
        :rtype: None
        """

        self._transformations.clear()
        self._transformations.update({stringutils.eval(key): value for (key, value) in transformations.items()})
    # endregion

    # region Methods
    def getAssociatedNode(self, namespace=None):
        """
        Returns the scene node associated with this pose node.

        :type namespace: Union[str, None]
        :rtype: mpynode.MPyNode
        """

        namespace = self.namespace if namespace is None else namespace
        absoluteName = f'{namespace}:{self.name}'

        if self.scene.doesNodeExist(absoluteName):

            return self.scene(absoluteName)

        else:

            return None

    def getAttributeByName(self, name):
        """
        Returns the pose attribute with the specified name.

        :type name: str
        :rtype: Union[PoseAttribute, None]
        """

        found = [attribute for attribute in self.attributes if attribute.name == name]
        numFound = len(found)

        if numFound == 1:

            return found[0]

        else:

            return None

    def getKeyframeInputs(self):
        """
        Returns the keyframe inputs from this node.

        :rtype: List[int]
        """

        inputs = set()

        for attribute in self.attributes:

            inputs.update([key.time for key in attribute.keyframes])

        return list(inputs)

    def getTransformation(self, time):
        """
        Returns the transformation at the specified time.

        :type time: Union[int, float]
        :rtype: om.MMatrix
        """

        # Check if transformation exists
        #
        matrix = self.transformations.get(time, None)

        if matrix is not None:

            return matrix

        # Get time inputs
        #
        times = list(self.transformations.keys())
        numTimes = len(times)

        if numTimes == 0:

            return om.MMatrix.kIdentity

        # Check if time is in range
        #
        firstTime, lastTime = times[0], times[-1]

        if firstTime < time < lastTime:

            startTime, endTime = [(times[i], times[i + 1]) for i in range(numTimes - 1) if times[i] <= time <= times[i + 1]][0]
            weight = (time - startTime) / (endTime - startTime)

            return transformutils.lerpMatrix(self.transformations[startTime], self.transformations[endTime], weight)

        elif time <= firstTime:

            return self.transformations[firstTime]

        elif time >= lastTime:

            return self.transformations[lastTime]

        else:

            raise TypeError('getTransformation() cannot locate a valid transformation!')

    def applyValues(self, node, **kwargs):
        """
        Applies the attribute values to the supplied node.

        :type node: mpynode.MPyNode
        :rtype: None
        """

        # Iterate through attributes
        #
        for attribute in self.attributes:

            # Check if attribute exists
            #
            if node.hasAttr(attribute.name):

                node.setAttr(attribute.name, attribute.value)

            else:

                log.warning(f'Cannot locate "{attribute.name}" attribute on "{node.name()}" node!')
                continue

    def applyKeyframes(self, node, **kwargs):
        """
        Applies the attribute keyframes to the supplied node.

        :type node: mpynode.MPyNode
        :key insertAt: Union[int, None]
        :key skipUserAttributes: bool
        :rtype: None
        """

        # Iterate through attributes
        #
        nodeName = node.name()

        insertAt = kwargs.get('insertAt', None)
        animationRange = kwargs.get('animationRange', self.pose.animationRange)
        skipUserAttributes = kwargs.get('skipUserAttributes', False)

        for attribute in self.attributes:

            # Check if attribute exists
            #
            if not node.hasAttr(attribute.name):

                log.warning(f'Cannot locate "{attribute.name}" attribute from "{nodeName}" node!')
                continue

            # Check if plug is writable
            #
            plug = node.findPlug(attribute.name)
            isWritable = plugutils.isWritable(plug)

            if not isWritable:

                log.warning(f'Skipping non-writable "{attribute.name}" attribute on "{nodeName}" node!')
                continue

            # Check if plug is animatable
            #
            isAnimatable = plugutils.isAnimatable(plug)
            hasKeyframes = not stringutils.isNullOrEmpty(attribute.keyframes)

            if not isAnimatable or not hasKeyframes:

                node.setAttr(plug, attribute.value)  # Just update the value and continue to the next attribute
                continue

            # Check if user attributes should be skipped
            #
            isUserAttribute = bool(plug.isDynamic)

            if skipUserAttributes and isUserAttribute:

                log.debug(f'Skipping "{attribute.name}" user attribute on "{nodeName}" node!')
                continue

            # Apply keyframes to animation curve
            #
            animCurve = node.findAnimCurve(plug, create=True)
            animCurve.setIsWeighted(attribute.weighted)
            animCurve.setPreInfinityType(attribute.preInfinityType)
            animCurve.setPostInfinityType(attribute.postInfinityType)

            if insertAt is not None:

                difference = insertAt - self.pose.animationRange[0]
                keyframes = [key.copy(time=(key.time + difference)) for key in attribute.keyframes]
                
                animCurve.replaceKeys(keyframes, animationRange=animationRange)

            else:

                animCurve.replaceKeys(attribute.keyframes, animationRange=animationRange)

    def applyMatrix(self, node, **kwargs):
        """
        Applies the local matrix to the supplied node.

        :type node: mpynode.MPyNode
        :rtype: None
        """

        node.setMatrix(self.matrix, **kwargs)

    def applyWorldMatrix(self, node, **kwargs):
        """
        Applies the world matrix to the supplied node.

        :type node: mpynode.MPyNode
        :rtype: None
        """

        matrix = self.worldMatrix * node.parentInverseMatrix()
        node.setMatrix(matrix, **kwargs)

    def mirrorValues(self, node, **kwargs):
        """
        Applies the mirrored attribute values to the opposite node.

        :type node: mpynode.MPyNode
        :rtype: None
        """

        # Iterate through attributes
        #
        otherNode = node.getOppositeNode()

        for attribute in self.attributes:

            # Check if attribute exists
            #
            if not otherNode.hasAttr(attribute.name):

                log.warning(f'Cannot locate "{attribute.name}" attribute on "{node.name()}" node!')
                continue

            # Mirror attribute to other node
            #
            mirrorFlag = 'mirror{name}'.format(name=stringutils.titleize(attribute.name))
            mirrorEnabled = node.userProperties.get(mirrorFlag, False)

            if mirrorEnabled:

                otherNode.setAttr(attribute.name, -attribute.value)

            else:

                otherNode.setAttr(attribute.name, attribute.value)

    def mirrorKeyframes(self, node, **kwargs):
        """
        Applies the attribute keyframes to the supplied node.

        :type node: mpynode.MPyNode
        :key insertAt: Union[int, None]
        :key skipUserAttributes: bool
        :rtype: None
        """

        # Iterate through attributes
        #
        otherNode = node.getOppositeNode()

        insertAt = kwargs.get('insertAt', None)
        animationRange = kwargs.get('animationRange', self.pose.animationRange)
        skipUserAttributes = kwargs.get('skipUserAttributes', False)

        for attribute in self.attributes:

            # Check if attribute has animation
            #
            if len(attribute.keyframes) == 0:

                continue

            # Check if attribute exists
            #
            if not otherNode.hasAttr(attribute.name):

                log.warning(f'Cannot locate "{attribute.name}" attribute from "{node.name()}" node!')
                continue

            # Check if user attributes should be skipped
            #
            plug = otherNode.findPlug(attribute.name)

            if skipUserAttributes and plug.isDynamic:

                log.debug(f'Skipping "{attribute.name}" user attribute on "{node.name()}" node!')
                continue

            # Check if keyframes need to be inversed
            #
            mirrorFlag = 'mirror{name}'.format(name=stringutils.titleize(attribute.name))
            mirrorEnabled = node.userProperties.get(mirrorFlag, False)

            startTime, endTime = animationRange
            keyframes = attribute.getRange(startTime, endTime, invert=mirrorEnabled)

            # Apply keyframes to animation curve
            #
            animCurve = otherNode.findAnimCurve(plug, create=True)
            animCurve.replaceKeys(keyframes, insertAt=insertAt, animationRange=animationRange)

    @classmethod
    def create(cls, node, **kwargs):
        """
        Returns a new pose node using the supplied node.

        :type node: mpynode.MPyNode
        :key animationRange: Tuple[int, int]
        :key step: int
        :key skipKeys: bool
        :key skipLayers: bool
        :key skipTransformation: bool
        :rtype: PoseNode
        """

        # Check if transformations should be cached
        #
        skipKeys = kwargs.get('skipKeys', True)
        skipTransformations = kwargs.get('skipTransformations', True)

        transformations = {}

        if not (skipTransformations or skipKeys):

            animationRange = kwargs.get('animationRange', sceneutils.getAnimationRange())
            step = kwargs.get('step', 1)

            log.debug(f'Caching "{node.name()}" transformations!')
            transformations = node.cacheTransformations(animationRange=animationRange, step=step, worldSpace=True)

        # Return new pose node
        #
        return cls(
            name=node.name(),
            namespace=node.namespace(),
            uuid=node.uuid(asString=True),
            path=node.dagPath().fullPathName(),
            attributes=[PoseAttribute.create(plug, **kwargs) for plug in node.iterPlugs(channelBox=True)],
            matrix=node.matrix(),
            worldMatrix=node.worldMatrix(),
            transformations=transformations
        )
    # endregion


class PoseAttribute(melsonobject.MELSONObject):
    """
    Overload of `MELSONObject` that interfaces with pose attributes.
    """

    # region Dunderscores
    __slots__ = (
        '_name',
        '_value',
        '_preInfinityType',
        '_postInfinityType',
        '_weighted',
        '_keyframes'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :rtype: None
        """

        # Call parent method
        #
        super(PoseAttribute, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._name = kwargs.pop('name', '')
        self._value = kwargs.pop('value', 0.0)
        self._preInfinityType = kwargs.pop('preInfinityType', 0)
        self._postInfinityType = kwargs.pop('postInfinityType', 0)
        self._weighted = kwargs.pop('weighted', False)
        self._keyframes = kwargs.pop('keyframes', [])
    # endregion

    # region Properties
    @property
    def name(self):
        """
        Getter method that returns the name of this plug.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Setter method that updates the name of this plug.

        :type name: str
        :rtype: None
        """

        self._name = name

    @property
    def value(self):
        """
        Getter method that returns the value from this plug.

        :rtype: Union[int, float]
        """

        return self._value

    @value.setter
    def value(self, value):
        """
        Setter method that updates the value for this plug.

        :type value: Union[int, float]
        :rtype: None
        """

        self._value = value

    @property
    def preInfinityType(self):
        """
        Getter method that returns the pre-infinity type for this animation curve.

        :rtype: int
        """

        return self._preInfinityType

    @preInfinityType.setter
    def preInfinityType(self, preInfinityType):
        """
        Setter method that updates the pre-infinity type for this animation curve.

        :type preInfinityType: int
        :rtype: None
        """

        self._preInfinityType = preInfinityType

    @property
    def postInfinityType(self):
        """
        Getter method that returns the post-infinity type for this animation curve.

        :rtype: int
        """

        return self._postInfinityType

    @postInfinityType.setter
    def postInfinityType(self, postInfinityType):
        """
        Setter method that updates the post-infinity type for this animation curve.

        :type postInfinityType: int
        :rtype: None
        """

        self._postInfinityType = postInfinityType

    @property
    def weighted(self):
        """
        Getter method that returns the `weighted` flag for this animation curve.

        :rtype: bool
        """

        return self._weighted

    @weighted.setter
    def weighted(self, weighted):
        """
        Setter method that updates the `weighted` flag for this animation curve.

        :type weighted: bool
        :rtype: None
        """

        self._weighted = weighted

    @property
    def keyframes(self):
        """
        Getter method that returns the keyframes for this animation curve.

        :rtype: List[keyframe.Keyframe]
        """

        return self._keyframes

    @keyframes.setter
    def keyframes(self, keyframes):
        """
        Setter method that updates the keyframes for this animation curve.

        :type keyframes: List[keyframe.Keyframe]
        :rtype: None
        """

        self._keyframes.clear()
        self._keyframes.extend(keyframes)
    # endregion

    # region Methods
    def getRange(self, startTime, endTime, invert=False):
        """
        Returns a range of keys from this attribute.

        :type startTime: int
        :type endTime: int
        :type invert: bool
        :rtype: List[keyframe.Keyframe]
        """

        keyframes = [key for key in self.keyframes if startTime <= key.time <= endTime]

        if invert:

            return list(map(neg, keyframes))

        else:

            return keyframes

    @classmethod
    def create(cls, plug, **kwargs):
        """
        Returns a new pose attribute using the supplied plug.

        :type plug: om.MPlug
        :rtype: PoseAttribute
        """

        # Check if plug is animated
        #
        preInfinityType = 0
        postInfinityType = 0
        weighted = False
        keyframes = []

        node = mpynode.MPyNode(plug.node())
        animCurve = node.findAnimCurve(plug)
        skipKeys = kwargs.get('skipKeys', True)

        if animCurve is not None and not skipKeys:

            preInfinityType = animCurve.preInfinity
            postInfinityType = animCurve.postInfinity
            weighted = animCurve.isWeighted
            animationRange = kwargs.get('animationRange', None)
            keyframes = animCurve.getKeys(animationRange=animationRange)

        # Return new pose attribute
        #
        return cls(
            name=plug.partialName(useLongNames=True),
            value=plugmutators.getValue(plug),
            preInfinityType=preInfinityType,
            postInfinityType=postInfinityType,
            weighted=weighted,
            keyframes=keyframes
        )
    # endregion


class PoseMember(melsonobject.MELSONObject):
    """
    Overload of `MELSONObject` that interfaces with pose member data.
    """

    # region Dunderscores
    __slots__ = (
        '_animLayer',
        '_name',
        '_attribute',
        '_value',
        '_preInfinityType',
        '_postInfinityType',
        '_weighted',
        '_keyframes'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :rtype: None
        """

        # Call parent method
        #
        super(PoseMember, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._animLayer = self.nullWeakReference
        self._name = kwargs.pop('name', '')
        self._attribute = kwargs.pop('attribute', '')
        self._value = kwargs.pop('value', 0.0)
        self._preInfinityType = kwargs.pop('preInfinityType', 0)
        self._postInfinityType = kwargs.pop('postInfinityType', 0)
        self._weighted = kwargs.pop('weighted', False)
        self._keyframes = kwargs.pop('keyframes', [])
    # endregion

    # region Properties
    @property
    def animLayer(self):
        """
        Getter method that returns the associated anim layer.

        :rtype: PoseAnimLayer
        """

        return self._animLayer()

    @property
    def node(self):
        """
        Getter method that returns the name of this node.

        :rtype: str
        """

        return self._node

    @node.setter
    def node(self, node):
        """
        Setter method that updates the name of this node.

        :type node: str
        :rtype: None
        """

        self._node = node

    @property
    def attribute(self):
        """
        Getter method that returns the name of this attribute.

        :rtype: str
        """

        return self._node

    @attribute.setter
    def attribute(self, attribute):
        """
        Setter method that updates the name of this attribute.

        :type attribute: str
        :rtype: None
        """

        self._attribute = attribute

    @property
    def value(self):
        """
        Getter method that returns the value from this plug.

        :rtype: Union[int, float]
        """

        return self._value

    @value.setter
    def value(self, value):
        """
        Setter method that updates the value for this plug.

        :type value: Union[int, float]
        :rtype: None
        """

        self._value = value

    @property
    def preInfinityType(self):
        """
        Getter method that returns the pre-infinity type for this animation curve.

        :rtype: int
        """

        return self._preInfinityType

    @preInfinityType.setter
    def preInfinityType(self, preInfinityType):
        """
        Setter method that updates the pre-infinity type for this animation curve.

        :type preInfinityType: int
        :rtype: None
        """

        self._preInfinityType = preInfinityType

    @property
    def postInfinityType(self):
        """
        Getter method that returns the post-infinity type for this animation curve.

        :rtype: int
        """

        return self._postInfinityType

    @postInfinityType.setter
    def postInfinityType(self, postInfinityType):
        """
        Setter method that updates the post-infinity type for this animation curve.

        :type postInfinityType: int
        :rtype: None
        """

        self._postInfinityType = postInfinityType

    @property
    def weighted(self):
        """
        Getter method that returns the `weighted` flag for this animation curve.

        :rtype: bool
        """

        return self._weighted

    @weighted.setter
    def weighted(self, weighted):
        """
        Setter method that updates the `weighted` flag for this animation curve.

        :type weighted: bool
        :rtype: None
        """

        self._weighted = weighted

    @property
    def keyframes(self):
        """
        Getter method that returns the keyframes for this animation curve.

        :rtype: List[keyframe.Keyframe]
        """

        return self._keyframes

    @keyframes.setter
    def keyframes(self, keyframes):
        """
        Setter method that updates the keyframes for this animation curve.

        :type keyframes: List[keyframe.Keyframe]
        :rtype: None
        """

        self._keyframes.clear()
        self._keyframes.extend(keyframes)
    # endregion

    # region Methods
    @classmethod
    def create(cls, plug, animCurve, **kwargs):
        """
        Returns a new pose member using the supplied plug.

        :type plug: om.MPlug
        :type animCurve: mpynode.MPyNode
        :rtype: PoseMember
        """

        node = mpynode.MPyNode(plug.node())
        attribute = plug.partialName(useLongNames=True)
        value = plugmutators.getValue(plug),

        preInfinityType, postInfinityType = 0, 0
        weighted = False
        keyframes = []

        if animCurve is not None:

            preInfinityType, postInfinityType = animCurve.preInfinity, animCurve.postInfinity
            weighted = animCurve.isWeighted
            keyframes = animCurve.getKeys()

        instance = cls(
            node=node.name(),
            attribute=attribute,
            value=value,
            preInfinityType=preInfinityType,
            postInfinityType=postInfinityType,
            weighted=weighted,
            keyframes=keyframes
        )

        return instance
    # endregion


class PoseAnimLayer(melsonobject.MELSONObject):
    """
    Overload of `MELSONObject` that interfaces with pose anim layer data.
    """

    # region Dunderscores
    __slots__ = (
        '__weakref__',
        '_pose',
        '_name',
        '_parent',
        '_children',
        '_members',
        '_mute',
        '_solo',
        '_lock',
        '_ghost',
        '_ghostColor',
        '_override',
        '_passthrough',
        '_weight',
        '_rotationAccumulationMode',
        '_scaleAccumulationMode'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :rtype: None
        """

        # Call parent method
        #
        super(PoseAnimLayer, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._pose = self.nullWeakReference
        self._name = kwargs.pop('name', '')
        self._parent = kwargs.pop('parent', self.nullWeakReference)
        self._children = notifylist.NotifyList()
        self._members = notifylist.NotifyList()
        self._mute = kwargs.pop('mute', False)
        self._solo = kwargs.pop('solo', False)
        self._lock = kwargs.pop('lock', False)
        self._ghost = kwargs.pop('ghost', False)
        self._ghostColor = kwargs.pop('ghostColor', 5)
        self._override = kwargs.pop('override', False)
        self._passthrough = kwargs.pop('passthrough', True)
        self._weight = kwargs.pop('weight', 1.0)
        self._rotationAccumulationMode = kwargs.pop('rotationAccumulationMode', 0)
        self._scaleAccumulationMode = kwargs.pop('scaleAccumulationMode', 1)

        # Initialize notifies
        #
        self._children.addCallback('itemAdded', self.layerAdded)
        self._children.addCallback('itemRemoved', self.layerRemoved)
        self._children.extend(kwargs.pop('children', []))

        self._members.addCallback('itemAdded', self.memberAdded)
        self._members.addCallback('itemRemoved', self.memberRemoved)
        self._members.extend(kwargs.pop('members', []))
    # endregion

    # region Properties
    @property
    def name(self):
        """
        Getter method that returns the name of this layer.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Setter method that updates the name for this layer.

        :type name: str
        :rtype: None
        """

        self._name = name

    @property
    def parent(self):
        """
        Getter method that returns the parent of this layer.

        :rtype: PoseAnimLayer
        """

        return self._parent()

    @property
    def children(self):
        """
        Getter method that returns the children from this layer.

        :rtype: List[PoseAnimLayer]
        """

        return self._children

    @children.setter
    def children(self, children):
        """
        Setter method that updates the children for this layer.

        :type children: List[PoseAnimLayer]
        :rtype: None
        """

        self._children.clear()
        self._children.extend(children)

    @property
    def members(self):
        """
        Getter method that returns the members from this layer.

        :rtype: List[PoseMember]
        """

        return self._members

    @members.setter
    def members(self, members):
        """
        Setter method that updates the members for this layer.

        :type members: Dict[str, List[PoseMember]]
        :rtype: None
        """

        self._members.clear()
        self._members.update(members)

    @property
    def mute(self):
        """
        Getter method that returns the mute flag from this layer.

        :rtype: bool
        """

        return self._mute

    @mute.setter
    def mute(self, mute):
        """
        Setter method that updates the mute flag for this layer.

        :type mute: bool
        :rtype: None
        """

        self._mute = mute

    @property
    def solo(self):
        """
        Getter method that returns the solo flag from this layer.

        :rtype: bool
        """

        return self._solo

    @solo.setter
    def solo(self, solo):
        """
        Setter method that updates the solo flag for this layer.

        :type solo: bool
        :rtype: None
        """

        self._solo = solo

    @property
    def lock(self):
        """
        Getter method that returns the lock flag from this layer.

        :rtype: bool
        """

        return self._lock

    @lock.setter
    def lock(self, lock):
        """
        Setter method that updates the lock flag for this layer.

        :type lock: bool
        :rtype: None
        """

        self._lock = lock

    @property
    def ghost(self):
        """
        Getter method that returns the ghost flag from this layer.

        :rtype: bool
        """

        return self._ghost

    @ghost.setter
    def ghost(self, ghost):
        """
        Setter method that updates the ghost flag for this layer.

        :type ghost: bool
        :rtype: None
        """

        self._ghost = ghost

    @property
    def ghostColor(self):
        """
        Getter method that returns the ghost color from this layer.

        :rtype: int
        """

        return self._ghostColor

    @ghostColor.setter
    def ghostColor(self, ghostColor):
        """
        Setter method that updates the ghost color for this layer.

        :type ghostColor: int
        :rtype: None
        """

        self._ghostColor = ghostColor

    @property
    def override(self):
        """
        Getter method that returns the override flag from this layer.

        :rtype: bool
        """

        return self._override

    @override.setter
    def override(self, override):
        """
        Setter method that updates the override flag for this layer.

        :type override: bool
        :rtype: None
        """

        self._override = override

    @property
    def passthrough(self):
        """
        Getter method that returns the passthrough flag from this layer.

        :rtype: bool
        """

        return self._passthrough

    @passthrough.setter
    def passthrough(self, passthrough):
        """
        Setter method that updates the passthrough flag for this layer.

        :type passthrough: bool
        :rtype: None
        """

        self._passthrough = passthrough

    @property
    def weight(self):
        """
        Getter method that returns the blend weight from this layer.

        :rtype: float
        """

        return self._weight

    @weight.setter
    def weight(self, weight):
        """
        Setter method that updates the blend weight for this layer.

        :type weight: float
        :rtype: None
        """

        self._weight = weight

    @property
    def rotationAccumulationMode(self):
        """
        Getter method that returns the rotation-accumulation mode from this layer.

        :rtype: int
        """

        return self._rotationAccumulationMode

    @rotationAccumulationMode.setter
    def rotationAccumulationMode(self, rotationAccumulationMode):
        """
        Setter method that updates the rotation-accumulation mode for this layer.

        :type rotationAccumulationMode: int
        :rtype: None
        """

        self._rotationAccumulationMode = rotationAccumulationMode
        
    @property
    def scaleAccumulationMode(self):
        """
        Getter method that returns the scale-accumulation mode from this layer.

        :rtype: int
        """

        return self._scaleAccumulationMode

    @scaleAccumulationMode.setter
    def scaleAccumulationMode(self, scaleAccumulationMode):
        """
        Setter method that updates the scale-accumulation mode for this layer.

        :type scaleAccumulationMode: int
        :rtype: None
        """

        self._scaleAccumulationMode = scaleAccumulationMode
    # endregion

    # region Callbacks
    def layerAdded(self, index, layer):
        """
        Node added callback.

        :type index: int
        :type layer: PoseAnimLayer
        :rtype: None
        """

        layer._parent = self.weakReference()

    def layerRemoved(self, layer):
        """
        Node removed callback.

        :type layer: PoseAnimLayer
        :rtype: None
        """

        layer._parent = self.nullWeakReference

    def memberAdded(self, key, member):
        """
        Node added callback.

        :type key: Union[int, str]
        :type member: PoseMember
        :rtype: None
        """

        member._animLayer = self.weakReference()

    def memberRemoved(self, member):
        """
        Node removed callback.

        :type member: PoseMember
        :rtype: None
        """

        member._animLayer = self.nullWeakReference
    # endregion

    # region Methods
    @classmethod
    def create(cls, layer, nodes=None):
        """
        Returns a new pose layer using the supplied layer.

        :type layer: mpynode.MPyNode
        :type nodes: Union[List[mpynode.MPyNode], None]
        :rtype: PoseAnimLayer
        """

        # Create new layer
        #
        instance = cls(
            name=layer.name(),
            mute=layer.mute,
            solo=layer.solo,
            lock=layer.lock,
            ghost=layer.ghost,
            ghostColor=layer.ghostColor,
            override=layer.override,
            passthrough=layer.passthrough,
            weight=layer.weight,
            rotationAccumulationMode=layer.rotationAccumulationMode,
            scaleAccumulationMode=layer.scaleAccumulationMode
        )

        # Iterate through members
        #
        plugs = layer.members()

        for plug in plugs:

            # Check if member is in nodes
            #
            node = plug.node()

            if node in nodes:

                continue

            # Add member to layer
            #
            animCurve = layer.getAssociatedAnimCurve(plug)

            member = PoseMember.create(plug, animCurve)
            instance.members.append(member)

        # Check if layer has any children
        #
        children = layer.children()
        numChildren = len(children)

        if numChildren > 0:

            instance.children = [cls.create(child, nodes=nodes) for child in children]

        return instance
    # endregion
