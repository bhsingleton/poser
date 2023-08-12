import math

from abc import abstractmethod
from enum import IntEnum
from maya.api import OpenMaya as om
from mpy import mpynode, mpyfactory
from dcc.json import psonobject
from dcc.python import stringutils
from dcc.maya.libs import transformutils, ikutils
from dcc.maya.decorators.animate import animate
from dcc.collections import notifylist
from dcc.generators.inclusiverange import inclusiveRange

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class RetargetType(IntEnum):
    """
    Collection of all the available retarget types.
    """

    Unknown = -1
    Root = 0
    Hips = 1
    Leg = 2
    Toe = 3
    Spine = 4
    Clavicle = 5
    Arm = 6
    Finger = 7
    Neck = 8
    Head = 9


class RetargetSide(IntEnum):
    """
    Collection of all the available retarget sides.
    """

    Unknown = -1
    Center = 0
    Left = 1
    Right = 2


class RetargetBinder(psonobject.PSONObject):
    """
    Overload of `PSONObject` that defines the relationship between the source and target skeleton.
    """
    
    # region Dunderscores
    __slots__ = (
        '_scene',
        '_type',
        '_side',
        '_source',
        '_target',
        '_fkControls',
        '_ikControls',
        '_switchControl',
        '_fkHints',
        '_ikHints',
        '_poleHandle',
        '_offsets'
    )
    
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :key children: List[AbstractRetargeter]
        :rtype: None
        """

        # Declare private variables
        #
        self._scene = mpyfactory.MPyFactory.getInstance(asWeakReference=True)
        self._type = kwargs.get('type', RetargetType.Unknown)
        self._side = kwargs.get('side', RetargetSide.Unknown)
        self._source = []
        self._target = []
        self._fkControls = []
        self._ikControls = []
        self._switchControl = ''
        self._fkHints = kwargs.get('fkHints', {})
        self._ikHints = kwargs.get('ikHints', {})
        self._poleHandle = ''
        self._offsets = []
        
        # Call parent method
        #
        super(RetargetBinder, self).__init__(*args, **kwargs)
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
    def type(self):
        """
        Getter method that returns the type enumerator.

        :rtype: RetargetType
        """

        return self._type

    @type.setter
    def type(self, type):
        """
        Setter method that updates the type enumerator.

        :type type: Union[RetargetType, int]
        :rtype: None
        """

        self._type = RetargetType(type)

    @property
    def side(self):
        """
        Getter method that returns the side enumerator.

        :rtype: RetargetSide
        """

        return self._side

    @side.setter
    def side(self, side):
        """
        Setter method that updates the side enumerator.

        :type side: Union[RetargetSide, int]
        :rtype: None
        """

        self._side = RetargetSide(side)

    @property
    def source(self):
        """
        Getter method that returns the name of the source joints.

        :rtype: List[str]
        """

        return self._source

    @source.setter
    def source(self, source):
        """
        Setter method that updates the names of the source joints.

        :type source: List[str]
        :rtype: None
        """

        self._source.clear()
        self._source.extend(source)

        sourceCount = len(self._source)
        offsetCount = len(self._offsets)

        if sourceCount != offsetCount:

            self._offsets.clear()
            self._offsets.extend([om.MMatrix.kIdentity] * sourceCount)
        
    @property
    def target(self):
        """
        Getter method that returns the name of the target joints.

        :rtype: List[str]
        """

        return self._target

    @target.setter
    def target(self, target):
        """
        Setter method that updates the names of the target joints.

        :type target: List[str]
        :rtype: None
        """

        self._target.clear()
        self._target.extend(target)

        targetCount = len(self._target)
        offsetCount = len(self._offsets)

        if targetCount != offsetCount:

            self._offsets.clear()
            self._offsets.extend([om.MMatrix.kIdentity] * targetCount)

    @property
    def fkControls(self):
        """
        Getter method that returns the name of the controllers.

        :rtype: List[str]
        """

        return self._fkControls

    @fkControls.setter
    def fkControls(self, fkControls):
        """
        Setter method that updates the names of the controllers.

        :type fkControls: List[str]
        :rtype: None
        """

        self._fkControls.clear()
        self._fkControls.extend(fkControls)
    
    @property
    def ikControls(self):
        """
        Getter method that returns the name of the controllers.

        :rtype: List[str]
        """

        return self._ikControls

    @ikControls.setter
    def ikControls(self, ikControls):
        """
        Setter method that updates the names of the controllers.

        :type ikControls: List[str]
        :rtype: None
        """

        self._ikControls.clear()
        self._ikControls.extend(ikControls)

    @property
    def switchControl(self):
        """
        Getter method that returns the name of the switch controller.

        :rtype: str
        """

        return self._switchControl

    @switchControl.setter
    def switchControl(self, switchControl):
        """
        Setter method that updates the names of the switch controller.

        :type switchControl: str
        :rtype: None
        """

        self._switchControl = switchControl

    @property
    def fkHints(self):
        """
        Getter method that returns the attribute-value pairs to enable FK.

        :rtype: Dict[str, float]
        """

        return self._fkHints

    @fkHints.setter
    def fkHints(self, fkHints):
        """
        Setter method that updates the attribute-value pairs to enable FK.

        :type fkHints: Dict[str, float]
        :rtype: None
        """

        self._fkHints.clear()
        self._fkHints.update(fkHints)

    @property
    def ikHints(self):
        """
        Getter method that returns the attribute-value pairs to enable IK.

        :rtype: Dict[str, float]
        """

        return self._ikHints

    @ikHints.setter
    def ikHints(self, ikHints):
        """
        Setter method that updates the attribute-value pairs to enable IK.

        :type ikHints: Dict[str, float]
        :rtype: None
        """

        self._ikHints.clear()
        self._ikHints.update(ikHints)

    @property
    def poleHandle(self):
        """
        Getter method that returns the name of the pole handle.

        :rtype: str
        """

        return self._poleHandle

    @poleHandle.setter
    def poleHandle(self, poleHandle):
        """
        Setter method that updates the names of the pole handle.

        :type poleHandle: str
        :rtype: None
        """

        self._poleHandle = poleHandle

    @property
    def offsets(self):
        """
        Getter method that returns the offset matrices.

        :rtype: List[om.MMatrix]
        """

        return self._offsets

    @offsets.setter
    def offsets(self, offsets):
        """
        Setter method that updates the offset matrices.

        :type offsets: List[om.MMatrix]
        :rtype: None
        """

        self._offsets.clear()
        self._offsets.extend(offsets)
    # endregion
    
    # region Methods
    def getSource(self, firstOnly=False, namespace=''):
        """
        Returns the associated source nodes from the specified namespace.

        :type namespace: str
        :type firstOnly: bool
        :rtype: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        """

        # Collect source joints
        #
        source = []

        for name in self.source:

            absoluteName = f'{namespace}:{name}'

            if self.scene.doesNodeExist(absoluteName):

                source.append(mpynode.MPyNode(absoluteName))

            else:

                log.warning(f'Cannot locate source joint: {absoluteName}')

        # Check if first item should be returned
        #
        if firstOnly:

            return source[0] if len(source) > 0 else None

        else:

            return source

    def getTarget(self, firstOnly=False, namespace=''):
        """
        Returns the associated target nodes from the specified namespace.

        :type namespace: str
        :type firstOnly: bool
        :rtype: List[mpynode.MPyNode]
        """

        # Collect target joints
        #
        target = []

        for name in self.target:

            absoluteName = f'{namespace}:{name}'

            if self.scene.doesNodeExist(absoluteName):

                target.append(mpynode.MPyNode(absoluteName))

            else:

                log.warning(f'Cannot locate target joint: {absoluteName}')

        # Check if first item should be returned
        #
        if firstOnly:

            return target[0] if len(target) > 0 else None

        else:

            return target

    def getFKControls(self, firstOnly=False, namespace=''):
        """
        Returns the associated FK controls from the specified namespace.

        :type namespace: str
        :type firstOnly: bool
        :rtype: List[mpynode.MPyNode]
        """

        # Collect controls
        #
        controls = []

        for name in self.fkControls:

            absoluteName = f'{namespace}:{name}'

            if self.scene.doesNodeExist(absoluteName):

                controls.append(mpynode.MPyNode(absoluteName))

            else:

                log.warning(f'Cannot locate FK controller: {absoluteName}')

        # Check if first item should be returned
        #
        if firstOnly:

            return controls[0] if len(controls) > 0 else None

        else:

            return controls

    def getIKControls(self, firstOnly=False, namespace=''):
        """
        Returns the associated IK controls from the specified namespace.

        :type namespace: str
        :type firstOnly: bool
        :rtype: List[mpynode.MPyNode]
        """

        # Collect controls
        #
        controls = []

        for name in self.ikControls:

            absoluteName = f'{namespace}:{name}'

            if self.scene.doesNodeExist(absoluteName):

                controls.append(mpynode.MPyNode(absoluteName))

            else:

                log.warning(f'Cannot locate IK controller: {absoluteName}')

        # Check if first item should be returned
        #
        if firstOnly:

            return controls[0] if len(controls) > 0 else None

        else:

            return controls

    def getSwitchControl(self, namespace=''):
        """
        Returns the associated pole handle from the specified namespace.

        :type namespace: str
        :rtype: Union[mpynode.MPyNode, None]
        """

        absoluteName = f'{namespace}:{self.switchControl}'

        if self.scene.doesNodeExist(absoluteName):

            return mpynode.MPyNode(absoluteName)

        else:

            log.warning(f'Cannot locate switch control: {absoluteName}')
            return None

    def getPoleHandle(self, namespace=''):
        """
        Returns the associated pole handle from the specified namespace.

        :type namespace: str
        :rtype: Union[mpynode.MPyNode, None]
        """

        absoluteName = f'{namespace}:{self.poleHandle}'

        if self.scene.doesNodeExist(absoluteName):

            return mpynode.MPyNode(absoluteName)

        else:

            log.warning(f'Cannot locate pole handle: {absoluteName}')
            return None
    # endregion


class AbstractRetargeter(psonobject.PSONObject):
    """
    Overload of `PSONObject` that outlines retargeting behaviour.
    """

    # region Dunderscores
    __slots__ = (
        '__weakref__',
        '_scene',
        '_binder', 
        '_parent', 
        '_children'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :key binder: RetargetBinder
        :key children: List[AbstractRetargeter]
        :rtype: None
        """

        # Declare private variables
        #
        self._scene = mpyfactory.MPyFactory.getInstance(asWeakReference=True)
        self._binder = RetargetBinder()
        self._parent = self.nullWeakReference
        self._children = notifylist.NotifyList()

        # Setup notifies
        #
        self._children.addCallback('itemAdded', self.childAdded)
        self._children.addCallback('itemRemoved', self.childRemoved)

        children = kwargs.get('children', None)

        if not stringutils.isNullOrEmpty(children):

            self.children = children

        # Call parent method
        #
        super(AbstractRetargeter, self).__init__(*args, **kwargs)
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
    def binder(self):
        """
        Getter method that returns the retargeting binder.

        :rtype: RetargetBinder
        """

        return self._binder

    @binder.setter
    def binder(self, binder):
        """
        Setter method that updates the retargeting binder.

        :type binder: RetargetBinder
        :rtype: None
        """

        self._binder.update(binder)
        
    @property
    def parent(self):
        """
        Getter method that returns the parent retargeter.

        :rtype: Union[AbstractRetargeter, None]
        """

        return self._parent()

    @property
    def children(self):
        """
        Getter method that returns the child retargeters.

        :rtype: List[AbstractRetargeter]
        """

        return self._children

    @children.setter
    def children(self, children):
        """
        Setter method that updates the child retargeters.

        :type children: List[AbstractRetargeter]
        :rtype: None
        """

        self._children.clear()
        self._children.extend(children)
    # endregion

    # region Callbacks
    def childAdded(self, index, child):
        """
        Callback method to whenever a child is added to this retargeter.

        :type index: int
        :type child: AbstractRetargeter
        :rtype: None
        """

        child._parent = self.weakReference()

    def childRemoved(self, child):
        """
        Callback method to whenever a child is remove from this retargeter.

        :type child: AbstractRetargeter
        :rtype: None
        """

        child._parent = self.nullWeakReference
    # endregion

    # region Methods
    @abstractmethod
    def isValid(self):
        """
        Evaluates if this retargeter is valid.

        :rtype: bool
        """

        pass

    @abstractmethod
    def prepareToRetarget(self, **kwargs):
        """
        Allows the instance to make any preparations before retargeting.

        :key sourceNamespace: str
        :key targetNamespace: str
        :rtype: None
        """

        # Iterate through children
        #
        for child in self.children:

            child.prepareToRetarget(**kwargs)

    @abstractmethod
    def retarget(self, **kwargs):
        """
        Retargets the animation from the source skeleton to the target skeleton.

        :rtype: None
        """

        # Iterate through children
        #
        for child in self.children:

            # Check if child is valid
            #
            if child.isValid():

                child.retarget(**kwargs)

            else:

                continue
    # endregion


class JointRetargeter(AbstractRetargeter):
    """
    Overload of `AbstractRetargeter` that retargets a single skeletal joint.
    """

    # region Dunderscores
    __slots__ = (
        '_sizeHint',
        '_scaleFactor',
        '_sourceJoint',
        '_targetJoint',
        '_control',
        '_skipRotateX',
        '_skipRotateY',
        '_skipRotateZ'
    )
    
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :key sizeHint: str
        :key binder: RetargetBinder
        :key children: List[AbstractRetargeter]
        :rtype: None
        """
        
        # Declare private variables
        #
        self._sizeHint = kwargs.get('sizeHint', '')
        self._scaleFactor = 1.0
        self._sourceJoint = None
        self._targetJoint = None
        self._control = None
        self._skipRotateX = kwargs.get('skipRotateX', False)
        self._skipRotateY = kwargs.get('skipRotateY', False)
        self._skipRotateZ = kwargs.get('skipRotateZ', False)

        # Call parent method
        #
        super(JointRetargeter, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def sizeHint(self):
        """
        Getter method that returns the attribute that contains the size hint.

        :rtype: str
        """

        return self._sizeHint

    @sizeHint.setter
    def sizeHint(self, sizeHint):
        """
        Setter method that updates the attribute that contains the size hint.

        :type sizeHint: str
        :rtype: None
        """

        self._sizeHint = sizeHint

    @property
    def scaleFactor(self):
        """
        Getter method that returns the scale factor between the source and target skeleton.

        :rtype: float
        """

        return self._scaleFactor

    @property
    def sourceJoint(self):
        """
        Getter method that returns the source joint.

        :rtype: mpynode.MPyNode
        """

        return self._sourceJoint

    @property
    def targetJoint(self):
        """
        Getter method that returns the target joint.

        :rtype: mpynode.MPyNode
        """

        return self._targetJoint

    @property
    def control(self):
        """
        Getter method that returns the controller.

        :rtype: mpynode.MPyNode
        """

        return self._control

    @property
    def skipRotateX(self):
        """
        Getter method that returns the `skipRotateX` flag.

        :rtype: bool
        """

        return self._skipRotateX

    @skipRotateX.setter
    def skipRotateX(self, skipRotateX):
        """
        Setter method that updates the `skipRotateX` flag.

        :type skipRotateX: bool
        :rtype: None
        """

        self._skipRotateX = skipRotateX

    @property
    def skipRotateY(self):
        """
        Getter method that returns the `skipRotateY` flag.

        :rtype: bool
        """

        return self._skipRotateY

    @skipRotateY.setter
    def skipRotateY(self, skipRotateY):
        """
        Setter method that updates the `skipRotateY` flag.

        :type skipRotateY: bool
        :rtype: None
        """

        self._skipRotateY = skipRotateY

    @property
    def skipRotateZ(self):
        """
        Getter method that returns the `skipRotateZ` flag.

        :rtype: bool
        """

        return self._skipRotateZ

    @skipRotateZ.setter
    def skipRotateZ(self, skipRotateZ):
        """
        Setter method that updates the `skipRotateZ` flag.

        :type skipRotateZ: bool
        :rtype: None
        """

        self._skipRotateZ = skipRotateZ
    # endregion

    # region Methods
    def isValid(self):
        """
        Evaluates if this retargeter is valid.

        :rtype: bool
        """

        return None not in (self.sourceJoint, self.targetJoint, self.control)

    def prepareToRetarget(self, **kwargs):
        """
        Allows the instance to make any preparations before retargeting.

        :key sourceNamespace: str
        :key targetNamespace: str
        :rtype: None
        """

        # Get nodes from names
        #
        sourceNamespace = kwargs.get('sourceNamespace', '')
        self._sourceJoint = self.binder.getSource(firstOnly=True, namespace=sourceNamespace)

        targetNamespace = kwargs.get('targetNamespace', '')
        self._targetJoint = self.binder.getTarget(firstOnly=True, namespace=targetNamespace)
        self._control = self.binder.getFKControls(firstOnly=True, namespace=targetNamespace)

        # Calculate scale factor
        #
        if self.isValid() and not stringutils.isNullOrEmpty(self.sizeHint):
            
            sourceLength = om.MVector.kZaxisVector * self.sourceJoint.translation(time=0, space=om.MSpace.kWorld)
            targetLength = self.targetJoint.tryGetAttr(self.sizeHint, default=sourceLength)

            self._scaleFactor = targetLength / sourceLength
        
        else:
            
            self._scaleFactor = 1.0
            
        # Call parent method
        #
        super(JointRetargeter, self).prepareToRetarget(**kwargs)

    def retarget(self, **kwargs):
        """
        Retargets the animation from the source skeleton to the target skeleton.

        :rtype: None
        """

        # Compose source matrix
        #
        worldMatrix = self.binder.offsets[0] * self.sourceJoint.worldMatrix()
        translation = transformutils.decomposeTransformMatrix(worldMatrix)[0]
        scaledTranslation = translation.normal() * (translation.length() * self.scaleFactor)
        translateMatrix = transformutils.createTranslateMatrix(scaledTranslation)
        rotateMatrix = transformutils.createRotationMatrix(worldMatrix)

        sourceMatrix = rotateMatrix * translateMatrix

        # Compose target matrix
        #
        offsetMatrix = self.control.worldMatrix() * self.targetJoint.worldInverseMatrix()
        targetMatrix = offsetMatrix * sourceMatrix

        matrix = targetMatrix * self.control.parentInverseMatrix()

        # Update controller matrix
        #
        skipTranslate = stringutils.isNullOrEmpty(self.sizeHint)

        log.debug(f'{self.control.name()}.matrix = {matrix}')
        self.control.setMatrix(
            matrix,
            skipTranslate=skipTranslate,
            skipRotateX=self.skipRotateX,
            skipRotateY=self.skipRotateY,
            skipRotateZ=self.skipRotateZ,
            skipScale=True
        )

        # Call parent method
        #
        super(JointRetargeter, self).retarget(**kwargs)
    # endregion


class ChainRetargeter(AbstractRetargeter):
    """
    Overload of `AbstractRetargeter` that retargets a skeletal joint chain.
    """

    # region Dunderscores
    __slots__ = (
        '_sourceJoints',
        '_targetJoints',
        '_controls'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :key binder: RetargetBinder
        :key children: List[AbstractRetargeter]
        :rtype: None
        """

        # Declare private variables
        #
        self._sourceJoints = []
        self._targetJoints = []
        self._controls = []

        # Call parent method
        #
        super(ChainRetargeter, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def sourceJoints(self):
        """
        Getter method that returns the source joint.

        :rtype: List[mpynode.MPyNode]
        """

        return self._sourceJoints

    @property
    def targetJoints(self):
        """
        Getter method that returns the target joint.

        :rtype: List[mpynode.MPyNode]
        """

        return self._targetJoints

    @property
    def controls(self):
        """
        Getter method that returns the controller.

        :rtype: List[mpynode.MPyNode]
        """

        return self._controls
    # endregion

    # region Methods
    def isValid(self):
        """
        Evaluates if this retargeter is valid.

        :rtype: bool
        """

        sourceCount = len(self.sourceJoints)
        targetCount = len(self.targetJoints)
        controlCount = len(self.controls)

        return 0 not in (sourceCount, targetCount, controlCount)

    def prepareToRetarget(self, **kwargs):
        """
        Allows the instance to make any preparations before retargeting.

        :key sourceNamespace: str
        :key targetNamespace: str
        :rtype: None
        """

        # Get source joints
        #
        sourceNamespace = kwargs.get('sourceNamespace', '')
        self._sourceJoints = self.binder.getSource(namespace=sourceNamespace)

        # Get target joints and controls
        #
        targetNamespace = kwargs.get('targetNamespace', '')
        self._targetJoints = self.binder.getTarget(namespace=targetNamespace)
        self._controls = self.binder.getFKControls(namespace=targetNamespace)

        # Call parent method
        #
        super(ChainRetargeter, self).prepareToRetarget(**kwargs)

    def iterStartAndEnd(self):
        """
        Returns a generator that yields the source-target-control-offset pairs.

        :rtype: Iterator[mpynode.MPyNode, mpynode.MPyNode, mpynode.MPyNode, om.MMatrix]
        """

        return zip(
            (self.sourceJoints[0], self.sourceJoints[-1]),
            (self.targetJoints[0], self.targetJoints[-1]),
            (self.controls[0], self.controls[-1]),
            (self.binder.offsets[0], self.binder.offsets[-1])
        )

    def iterOneToOne(self):
        """
        Returns a generator that yields the source-target-control-offset pairs.

        :rtype: Iterator[mpynode.MPyNode, mpynode.MPyNode, mpynode.MPyNode, om.MMatrix]
        """

        return zip(self.sourceJoints, self.targetJoints, self.controls, self.binder.offsets)

    def retarget(self, **kwargs):
        """
        Retargets the animation from the source skeleton to the target skeleton.

        :rtype: None
        """

        # Evaluate which method to use
        #
        sourceCount = len(self.sourceJoints)
        targetCount = len(self.targetJoints)

        func = None

        if sourceCount == targetCount:

            func = self.iterOneToOne

        elif sourceCount >= 2 and targetCount == 2:

            func = self.iterStartAndEnd

        else:

            raise NotImplementedError('retarget() mismatch found in joint chain!')

        # Iterate through joint chain
        #
        for (sourceJoint, targetJoint, control, offset) in func():

            # Compose target matrix
            #
            sourceMatrix = offset * sourceJoint.worldMatrix()
            offsetMatrix = control.worldMatrix() * targetJoint.worldInverseMatrix()
            targetMatrix = offsetMatrix * sourceMatrix

            matrix = targetMatrix * control.parentInverseMatrix()

            # Update controller matrix
            #
            control.setMatrix(matrix, skipTranslate=True, skipScale=True)

        # Call parent method
        #
        super(ChainRetargeter, self).retarget(**kwargs)
    # endregion


class LimbRetargeter(AbstractRetargeter):
    """
    Overload of `AbstractRetargeter` that retargets a skeletal limb.
    """

    # region Dunderscores
    __slots__ = (
        '_sourceJoints',
        '_sourceMatrices',
        '_sourceLength',
        '_targetJoints',
        '_targetLength',
        '_fkControls',
        '_ikControls',
        '_switchControl',
        '_poleHandle',
        '_poleVector',
        '_scaleFactor',
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :key binder: RetargetBinder
        :key children: List[AbstractRetargeter]
        :rtype: None
        """

        # Declare private variables
        #
        self._sourceJoints = []
        self._sourceMatrices = []
        self._sourceLength = 0.0
        self._targetJoints = []
        self._targetLength = 0.0
        self._fkControls = []
        self._ikControls = []
        self._switchControl = None
        self._poleHandle = None
        self._poleVector = om.MVector.kZeroVector
        self._scaleFactor = 1.0

        # Call parent method
        #
        super(LimbRetargeter, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def sourceJoints(self):
        """
        Getter method that returns the source joints.

        :rtype: List[mpynode.MPyNode]
        """

        return self._sourceJoints

    @property
    def sourceMatrices(self):
        """
        Getter method that returns the matrices from the source limb.

        :rtype: List[om.MMatrix]
        """

        return self._sourceMatrices

    @property
    def sourceLength(self):
        """
        Getter method that returns the length of the source limb.

        :rtype: float
        """

        return self._sourceLength

    @property
    def targetJoints(self):
        """
        Getter method that returns the target joints.

        :rtype: List[mpynode.MPyNode]
        """

        return self._targetJoints

    @property
    def targetLength(self):
        """
        Getter method that returns the length of the target limb.

        :rtype: float
        """

        return self._targetLength

    @property
    def fkControls(self):
        """
        Getter method that returns the FK controllers.

        :rtype: List[mpynode.MPyNode]
        """

        return self._fkControls

    @property
    def ikControls(self):
        """
        Getter method that returns the IK controllers.

        :rtype: List[mpynode.MPyNode]
        """

        return self._ikControls

    @property
    def switchControl(self):
        """
        Getter method that returns the switch controller.

        :rtype: mpynode.MPyNode
        """

        return self._switchControl

    @property
    def poleHandle(self):
        """
        Getter method that returns the pole-handle.

        :rtype: mpynode.MPyNode
        """

        return self._poleHandle

    @property
    def poleVector(self):
        """
        Getter method that returns the pole-vector.

        :rtype: om.MVector
        """

        return self._poleVector

    @property
    def scaleFactor(self):
        """
        Getter method that returns the scale factor between the source and target limb.

        :rtype: float
        """

        return self._scaleFactor
    # endregion

    # region Methods
    def isValid(self):
        """
        Evaluates if this retargeter is valid.

        :rtype: bool
        """

        sourceCount = len(self.sourceJoints)
        targetCount = len(self.targetJoints)

        return (sourceCount == targetCount) and sourceCount == 3

    @staticmethod
    def getForwardAxis(vector, matrix):
        """
        Returns the forward axis from the transform matrix that is closest to the specified vector.

        :type vector: om.MVector
        :type matrix: om.MMatrix
        :rtype: Tuple[int, bool]
        """

        # Evaluate dot products of each axis
        #
        xAxis, yAxis, zAxis, position = transformutils.breakMatrix(matrix, normalize=True)
        axes = (xAxis, yAxis, zAxis)
        normalizedVector = vector.normal()

        dots = [normalizedVector * axis for axis in axes]

        # Sort magnitudes of dot products
        #
        magnitudes = list(map(abs, dots))
        sortedMagnitudes = sorted(magnitudes, reverse=True)

        axis = magnitudes.index(sortedMagnitudes[0])
        axisFlip = dots[axis] < 0.0

        return axis, axisFlip

    def cacheSource(self):
        """
        Caches a set of co-planar matrices using the current source joints.
        As far as I'm aware mocap data consistently uses the Z-axis as the designated up-axis.

        :rtype: None
        """

        # Decompose source matrices
        #
        startMatrix = self.sourceJoints[0].worldMatrix()
        midMatrix = self.sourceJoints[1].worldMatrix()
        endMatrix = self.sourceJoints[2].worldMatrix()
        averageMatrix = transformutils.lerpMatrix(startMatrix, midMatrix)

        origin = transformutils.breakMatrix(startMatrix)[3]
        mid = transformutils.breakMatrix(midMatrix)[3]
        goal = transformutils.breakMatrix(endMatrix)[3]

        # Calculate pole-vector
        # This is calculated by lerping desirable vectors based on the extension weight
        #
        startVector = mid - origin
        endVector = goal - mid
        startLength, endLength = startVector.length(), endVector.length()
        normalizedStartVector, normalizedEndVector = startVector.normal(), endVector.normal()

        dotProduct = normalizedStartVector * normalizedEndVector
        weight = max(min(dotProduct, 1.0), 0.0)

        upAxisSign = -1 if self.binder.type == RetargetType.Arm else 1
        upVector = transformutils.breakMatrix(averageMatrix, normalize=True)[2] * upAxisSign

        self._poleVector = ((normalizedStartVector * (1.0 - weight)) + (upVector * weight)).normal()

        # Solve 2-bone IK system
        #
        lengths = (startLength, endLength)
        matrices = ikutils.solve2Bone(origin, goal, lengths, self.poleVector)

        # Reorient IK solution to fit mocap skeleton
        #
        forwardAxis, forwardAxisFlip = self.getForwardAxis(startVector, startMatrix)
        forwardAxisSign = -1 if forwardAxisFlip else 1

        reorientedMatrices = [transformutils.reorientMatrix(forwardAxis, 2, matrix, forwardAxisSign=forwardAxisSign, upAxisSign=upAxisSign) for matrix in matrices]

        # Cache IK solution
        # Don't forget to maintain the orientation of the last element!
        #
        self._sourceMatrices = [None] * 3
        self._sourceMatrices[0] = reorientedMatrices[0]
        self._sourceMatrices[1] = reorientedMatrices[1]
        self._sourceMatrices[2] = transformutils.createRotationMatrix(endMatrix) * transformutils.createTranslateMatrix(reorientedMatrices[2])

    def enableFKControls(self):
        """
        Assigns the attribute hints to the switch controller to enable FK.

        :rtype: None
        """

        # Check if switch control exists
        #
        if self.switchControl is None:

            log.warning(f'Cannot locate "{self.binder.switchControl}" switch controller!')
            return

        # Iterate through FK hints
        #
        for (attribute, value) in self.binder.fkHints.items():

            self.switchControl.setAttr(attribute, value)

    def enableIKControls(self):
        """
        Assigns the attribute hints to the switch controller to enable IK.

        :rtype: None
        """

        # Check if switch control exists
        #
        if self.switchControl is None:

            log.warning(f'Cannot locate "{self.binder.switchControl}" switch controller!')
            return

        # Iterate through IK hints
        #
        for (attribute, value) in self.binder.ikHints.items():

            self.switchControl.setAttr(attribute, value)

    def updateKinematicMode(self, mode):
        """
        Updates the limb to the specified kinematic state.

        :type mode: int
        :rtype: None
        """

        # Redundancy check
        #
        if not self.isValid():

            return

        # Evaluate kinematic mode
        #
        if mode == 0:

            self.enableFKControls()

        else:

            self.enableIKControls()

    def prepareToRetarget(self, **kwargs):
        """
        Allows the instance to make any preparations before retargeting.

        :key sourceNamespace: str
        :key targetNamespace: str
        :rtype: None
        """

        # Get source joints
        #
        sourceNamespace = kwargs.get('sourceNamespace', '')
        self._sourceJoints = self.binder.getSource(namespace=sourceNamespace)
        self._sourceLength = sum([(endJoint.translation(space=om.MSpace.kWorld) - startJoint.translation(space=om.MSpace.kWorld)).length() for (startJoint, endJoint) in zip(self.sourceJoints[:-1], self.sourceJoints[1:])])

        # Get target joints
        #
        targetNamespace = kwargs.get('targetNamespace', '')
        self._targetJoints = self.binder.getTarget(namespace=targetNamespace)
        self._targetLength = sum([(endJoint.translation(space=om.MSpace.kWorld) - startJoint.translation(space=om.MSpace.kWorld)).length() for (startJoint, endJoint) in zip(self.targetJoints[:-1], self.targetJoints[1:])])

        self._scaleFactor = self.targetLength / self.sourceLength

        # Get controllers
        #
        self._ikControls = self.binder.getIKControls(namespace=targetNamespace)
        self._fkControls = self.binder.getFKControls(namespace=targetNamespace)
        self._switchControl = self.binder.getSwitchControl(namespace=targetNamespace)
        self._poleHandle = self.binder.getPoleHandle(namespace=targetNamespace)

        # Update kinematic mode
        #
        mode = kwargs.get('kinematicMode', 2)
        self.updateKinematicMode(mode)

        # Call parent method
        #
        super(LimbRetargeter, self).prepareToRetarget(**kwargs)

    def retargetFKControls(self, **kwargs):
        """
        Retargets the source skeleton onto the FK controls.

        :rtype: None
        """

        # Redundancy check
        #
        jointCount = len(self.targetJoints)
        controlCount = len(self.fkControls)

        if not (jointCount == controlCount and controlCount == 3):

            log.debug(f'Unable to retarget: {self.binder.source} > {self.binder.fkControls}')
            return

        # Iterate through source-target pairs
        #
        for (sourceMatrix, targetJoint, fkControl, offsetMatrix) in zip(self.sourceMatrices, self.targetJoints, self.fkControls, self.binder.offsets):

            # Calculate source matrix
            #
            worldMatrix = offsetMatrix * sourceMatrix
            translateMatrix = transformutils.createTranslateMatrix(targetJoint.worldMatrix())
            rotateMatrix = transformutils.createRotationMatrix(worldMatrix)

            sourceMatrix = rotateMatrix * translateMatrix

            # Remap source matrix onto target control
            #
            offsetMatrix = fkControl.worldMatrix() * targetJoint.worldInverseMatrix()
            targetMatrix = transformutils.createRotationMatrix(offsetMatrix) * sourceMatrix

            matrix = targetMatrix * fkControl.parentInverseMatrix()

            # Update controller matrix
            #
            log.debug(f'{fkControl.name()}.matrix = {matrix}')
            fkControl.setMatrix(matrix, skipTranslate=True, skipScale=True)

    def retargetIKControls(self, **kwargs):
        """
        Retargets the source skeleton onto the IK controls.

        :rtype: None
        """

        # Redundancy check
        #
        jointCount = len(self.targetJoints)
        controlCount = len(self.ikControls)

        if not (jointCount == 3 and controlCount >= 2):

            log.debug(f'Unable to retarget: {self.binder.source} > {self.binder.ikControls}')
            return

        # Calculate rotation matrix
        #
        sourceMatrix = self.binder.offsets[-1] * self.sourceMatrices[-1]
        rotateMatrix = transformutils.createRotationMatrix(sourceMatrix)

        # Calculate translation matrix
        #
        startPoint = transformutils.breakMatrix(self.sourceMatrices[0])[3]
        endPoint = transformutils.breakMatrix(self.sourceMatrices[2])[3]

        aimVector = endPoint - startPoint
        distance = aimVector.length()
        scaleDistance = distance * self.scaleFactor

        origin = self.targetJoints[0].translation(space=om.MSpace.kWorld)
        forwardVector = aimVector.normal()
        point = origin + (forwardVector * scaleDistance)

        translateMatrix = transformutils.createTranslateMatrix(point)

        # Compose transform matrix
        #
        startCtrl, endCtrl = self.ikControls[0], self.ikControls[-1]

        offsetMatrix = self.ikControls[-1].worldMatrix() * self.targetJoints[-1].worldInverseMatrix()
        targetMatrix = transformutils.createRotationMatrix(offsetMatrix) * (rotateMatrix * translateMatrix)
        matrix = targetMatrix * endCtrl.parentInverseMatrix()

        log.debug(f'{endCtrl.name()}.matrix = {matrix}')
        endCtrl.setMatrix(matrix, skipScale=True)

        # Calculate pole vector
        #
        if self.poleHandle is not None:

            rightVector = (forwardVector ^ self.poleVector).normal()
            upVector = (rightVector ^ forwardVector).normal()
            polePoint = origin + (forwardVector * (scaleDistance * 0.5)) + (upVector * self.targetLength)

            poleMatrix = transformutils.createTranslateMatrix(polePoint) * self.poleHandle.parentInverseMatrix()

            log.debug(f'{self.poleHandle.name()}.matrix = {poleMatrix}')
            self.poleHandle.setMatrix(poleMatrix, skipRotate=True, skipScale=True)

        else:

            log.debug(f'Unable to retarget: {self.binder.source} > {self.binder.poleHandle}')

    def retarget(self, **kwargs):
        """
        Retargets the animation from the source skeleton to the target skeleton.

        :key kinematicMode: int
        :rtype: None
        """

        # Evaluate kinematic mode
        #
        kinematicMode = kwargs.get('kinematicMode', 2)
        requiresIK = len(self.fkControls) == 0

        self.cacheSource()

        if kinematicMode == 0 and not requiresIK:  # FK

            self.retargetFKControls(**kwargs)

        elif kinematicMode == 1 or requiresIK:  # IK

            self.retargetIKControls(**kwargs)

        else:  # Both

            self.retargetFKControls(**kwargs)
            self.retargetIKControls(**kwargs)

        # Call parent method
        #
        super(LimbRetargeter, self).retarget(**kwargs)
    # endregion


class Retargeter(psonobject.PSONObject):
    """
    Overload of `PSONObject` that defines the relationship between a source and target skeleton.
    """

    # region Dunderscores
    __slots__ = (
        '_scene',
        '_name',
        '_root',
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :key name: str
        :key root: Union[AbstractRetargeter, None]
        :rtype: None
        """

        # Declare private variables
        #
        self._scene = mpyfactory.MPyFactory.getInstance(asWeakReference=True)
        self._name = kwargs.get('name', '')
        self._root = kwargs.get('root', None)

        # Call parent method
        #
        super(Retargeter, self).__init__(*args, **kwargs)
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
        Getter method that returns the name of this binder.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Getter method that returns the root pin.

        :type name: str
        :rtype: None
        """

        self._name = name

    @property
    def root(self):
        """
        Getter method that returns the root pin.

        :rtype: AbstractRetargeter
        """

        return self._root

    @root.setter
    def root(self, root):
        """
        Getter method that returns the root pin.

        :type root: AbstractRetargeter
        :rtype: None
        """

        self._root = root
    # endregion

    # region Methods
    def isValid(self):
        """
        Evaluates if this retargeter is valid.

        :rtype: bool
        """

        return self.root is not None

    @animate(state=True)
    def retarget(self, **kwargs):
        """
        Retargets the animation from the source skeleton to the target skeleton.

        :key sourceNamespace: str
        :key targetNamespace: str
        :key animationRange: Tuple[int, int]
        :rtype: None
        """

        # Redundancy check
        #
        if not self.isValid():

            log.warning('Cannot locate a valid retargeter!')
            return

        # Prepare to retarget
        #
        startTime, endTime = kwargs.get('animationRange', self.scene.animationRange)
        step = kwargs.get('step', 1)
        
        self.scene.time = startTime
        self.root.prepareToRetarget(**kwargs)

        if not self.root.isValid():

            log.warning('Unable to initialize root retargeter!')
            return

        # Retarget through requested range
        #
        for time in inclusiveRange(startTime, endTime, step):

            self.scene.time = time
            self.root.retarget(**kwargs)
    # endregion
