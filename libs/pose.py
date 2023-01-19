from maya.api import OpenMaya as om
from mpy import mpynode, mpyfactory
from dcc.json import psonobject
from dcc.dataclasses import keyframe
from dcc.maya.libs import sceneutils, plugutils, plugmutators

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Pose(psonobject.PSONObject):
    """
    Overload of `PSONObject` that interfaces with pose data.
    """

    # region Dunderscores
    __slots__ = (
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

        # Declare private variables
        #
        self._scene = mpyfactory.MPyFactory.getInstance(asWeakReference=True)
        self._name = kwargs.get('name', sceneutils.currentFilename(includeExtension=False))
        self._filePath = kwargs.get('filePath', sceneutils.currentFilePath())
        self._animationRange = kwargs.get('animationRange', sceneutils.getAnimationRange())
        self._nodes = kwargs.get('nodes', [])
        self._animLayers = kwargs.get('animLayers', [])
        self._thumbnail = kwargs.get('thumbnail', None)

        # Call parent method
        #
        super(Pose, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def scene(self):
        """
        Getter method that returns the scene interface.

        :rtype: mpyfactory.MPyFactory
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

    # region Methods
    def selectAssociatedNodes(self, namespace=None):
        """
        Selects the nodes associated with this pose.

        :type namespace: str
        :rtype: None
        """

        # Iterate through nodes
        #
        selection = om.MSelectionList()

        for node in self.nodes:

            # Check if node exists
            #
            nodeName = f'{node.namespace}:{node.name}' if self.isNullOrEmpty(namespace) else f'{namespace}:{node.name}'

            if self.scene.doesNodeExist(nodeName):

                selection.add(self.scene(nodeName).object())

            else:

                continue

        # Update active selection
        #
        self.scene.setSelection(selection)

    def findAssociatedNode(self, node):
        """
        Returns the pose associated with the supplied node.

        :type node: mpynode.MPyNode
        :rtype: Union[PoseNode, None]
        """

        name = node.name()

        found = [pose for pose in self.nodes if pose.name == name]
        numFound = len(found)

        if numFound == 1:

            return found[0]

        else:

            return None

    def applyPose(self, *nodes):
        """
        Updates the values on the supplied nodes.

        :rtype: None
        """

        # Iterate through nodes
        #
        for node in nodes:

            # Check if pose exists for node
            #
            pose = self.findAssociatedNode(node)

            if pose is not None:

                pose.applyValues(node)

            else:

                continue

    def blendPose(self, otherPose, weight=0.0):
        """
        Blends this pose with the other pose.

        :type otherPose: Pose
        :type weight: float
        :rtype: Pose
        """

        pass

    def applyAnimationRange(self):
        """
        Updates the animation range in the current scene file.

        :rtype: None
        """

        sceneutils.setAnimationRange(*self.animationRange)

    def applyAnimation(self, *nodes):
        """
        Updates the animation on the supplied nodes.

        :rtype: None
        """

        # Iterate through nodes
        #
        for node in nodes:

            # Check if pose exists for node
            #
            pose = self.findAssociatedNode(node)

            if pose is not None:

                pose.applyKeyframes(node)

            else:

                continue

    @classmethod
    def create(cls, *nodes, **kwargs):
        """
        Returns a new pose using the supplied nodes.

        :type nodes: Union[mpynode.MPyNode, Tuple[mpynode.MPyNode]]
        :rtype: Pose
        """

        return cls(nodes=[PoseNode.create(node, **kwargs) for node in nodes], **kwargs)
    # endregion


class PoseNode(psonobject.PSONObject):
    """
    Overload of `PSONObject` that interfaces with pose nodes.
    """

    # region Dunderscores
    __slots__ = (
        '_name',
        '_namespace',
        '_uuid',
        '_path',
        '_attributes',
        '_matrix',
        '_worldMatrix'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :rtype: None
        """

        # Declare private variables
        #
        self._name = kwargs.get('name', '')
        self._namespace = kwargs.get('namespace', '')
        self._uuid = kwargs.get('uuid', '')
        self._path = kwargs.get('path', '')
        self._attributes = kwargs.get('attributes', [])
        self._matrix = kwargs.get('matrix', om.MMatrix.kIdentity)
        self._worldMatrix = kwargs.get('worldMatrix', om.MMatrix.kIdentity)

        # Call parent method
        #
        super(PoseNode, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
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

        self._matrix = matrix

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

        self._worldMatrix = worldMatrix
    # endregion

    # region Methods
    @classmethod
    def isJsonCompatible(cls, T):
        """
        Evaluates whether the given type is json compatible.

        :type T: Union[Callable, Tuple[Callable]]
        :rtype: bool
        """

        if T.__module__ == 'OpenMaya':

            return True

        else:

            return super(PoseNode, cls).isJsonCompatible(T)

    def applyValues(self, node):
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

    def applyKeyframes(self, node):
        """
        Applies the attribute keyframes to the supplied node.

        :type node: mpynode.MPyNode
        :rtype: None
        """

        # Iterate through attributes
        #
        for attribute in self.attributes:

            # Check if attribute had animation
            #
            if attribute.animCurve is None:

                continue

            # Check if attribute exists
            #
            if node.hasAttr(attribute.name):

                animCurve = node.keyAttr(attribute.name, attribute.value)
                animCurve.assumeCache(attribute.animCurve.keyframes)

            else:

                log.warning(f'Cannot locate "{attribute.name}" attribute on "{node.name()}" node!')
                continue

    def applyMatrix(self, node):
        """
        Applies the local matrix to the supplied node.

        :type node: mpynode.MPyNode
        :rtype: None
        """

        pass

    def applyWorldMatrix(self, node):
        """
        Applies the world matrix to the supplied node.

        :type node: mpynode.MPyNode
        :rtype: None
        """

        pass

    @classmethod
    def create(cls, node, **kwargs):
        """
        Returns a new pose node using the supplied node.

        :type node: mpynode.MPyNode
        :rtype: PoseNode
        """

        return cls(
            name=node.name(),
            namespace=node.namespace(),
            uuid=node.uuid(asString=True),
            path=node.dagPath().fullPathName(),
            attributes=[PoseAttribute.create(plug, **kwargs) for plug in node.iterPlugs(channelBox=True)],
            matrix=node.matrix(),
            worldMatrix=node.worldMatrix()
        )
    # endregion


class PoseAttribute(psonobject.PSONObject):
    """
    Overload of `PSONObject` that interfaces with pose attributes.
    """

    # region Dunderscores
    __slots__ = (
        '_name',
        '_value',
        '_animCurve'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :rtype: None
        """

        # Declare private variables
        #
        self._name = kwargs.get('name', '')
        self._value = kwargs.get('value', 0.0)
        self._animCurve = kwargs.get('animCurve', None)

        # Call parent method
        #
        super(PoseAttribute, self).__init__(*args, **kwargs)
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
    def animCurve(self):
        """
        Getter method that returns the anim curve from this plug.

        :rtype: PoseAnimCurve
        """

        return self._animCurve

    @animCurve.setter
    def animCurve(self, animCurve):
        """
        Setter method that updates the anim curve for this plug.

        :type animCurve: PoseAnimCurve
        :rtype: None
        """

        self._animCurve = animCurve
    # endregion

    # region Methods
    @classmethod
    def create(cls, plug, **kwargs):
        """
        Returns a new pose attribute using the supplied plug.

        :type plug: om.MPlug
        :rtype: PoseAttribute
        """

        # Check if plug is animated
        #
        animCurve = None
        skipKeys = kwargs.get('skipKeys', True)

        if plugutils.isAnimated(plug) and not skipKeys:

            node = mpynode.MPyNode(plug.source().node())
            animCurve = PoseAnimCurve.create(node)

        # Return new pose attribute
        #
        return cls(
            name=plug.partialName(useLongNames=True),
            value=plugmutators.getValue(plug),
            animCurve=animCurve
        )
    # endregion


class PoseAnimCurve(psonobject.PSONObject):
    """
    Overload of `PSONObject` that interfaces with pose anim curve data.
    """

    # region Dunderscores
    __slots__ = (
        '_tangentType',
        '_preInfinityType',
        '_postInfinityType',
        '_keyframes'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :rtype: None
        """

        # Declare private variables
        #
        self._tangentType = kwargs.get('tangentType', 0)
        self._preInfinityType = kwargs.get('preInfinityType', 0)
        self._postInfinityType = kwargs.get('postInfinityType', 0)
        self._keyframes = kwargs.get('keyframes', [])

        # Call parent method
        #
        super(PoseAnimCurve, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def tangentType(self):
        """
        Getter method that returns the tangent type for this animation curve.

        :rtype: int
        """

        return self._tangentType

    @tangentType.setter
    def tangentType(self, tangentType):
        """
        Setter method that updates the tangent type for this animation curve.

        :type tangentType: int
        :rtype: None
        """

        self._tangentType = tangentType

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
    def create(cls, animCurve):
        """
        Returns a new pose anim curve using the supplied anim curve.

        :type animCurve: mpynode.MPyNode
        :rtype: PoseAnimCurve
        """

        return cls(
            tangentType=animCurve.tangentType,
            preInfinityType=animCurve.preInfinity,
            postInfinityType=animCurve.postInfinity,
            keyframes=animCurve.cacheKeys()
        )
    # endregion


class PoseAnimLayer(psonobject.PSONObject):
    """
    Overload of `PSONObject` that interfaces with pose anim layer data.
    """

    __slots__ = ()
