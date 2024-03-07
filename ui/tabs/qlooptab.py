from maya.api import OpenMaya as om, OpenMayaAnim as oma
from Qt import QtCore, QtWidgets, QtGui
from enum import IntEnum
from dcc.python import stringutils
from dcc.maya.decorators.undo import undo, commit
from . import qabstracttab

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


INFINITY_TYPES = {
    0: oma.MFnAnimCurve.kConstant,
    1: oma.MFnAnimCurve.kLinear,
    2: oma.MFnAnimCurve.kCycle,
    3: oma.MFnAnimCurve.kCycleRelative,
    4: oma.MFnAnimCurve.kOscillate
}


class BakeType(IntEnum):
    """
    Enum class of all available bake types.
    """

    NONE = -1
    RANGE = 0
    OUT_OF_RANGE = 1


class QLoopTab(qabstracttab.QAbstractTab):
    """
    Overload of `QAbstractTab` that manipulates looping animations.
    """

    # region Dunderscores
    __labels__ = (
        'Enter the start and end frame of your loop.\nAny keys outside this range will be overwritten with baked keys!',
        'Enter the start and end frame of your animation.\nAny infinity curves inside this range will be baked down!'
    )

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QWidget
        :key flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QLoopTab, self).__init__(*args, **kwargs)

        # Declare public variables
        #
        self.infinityTypeGroupBox = None
        self.constantPushButton = None
        self.linearPushButton = None
        self.cyclePushButton = None
        self.cycleOffsetPushButton = None
        self.oscillatePushButton = None
        self.infinityTypeButtonGroup = None

        self.tangentsGroupBox = None
        self.flattenTangentsPushButton = None
        self.alignTangentsPushButton = None

        self.bakeGroupBox = None
        self.bakeLabel = None
        self.bakeTypeWidget = None
        self.bakeRangeRadioButton = None
        self.bakeOutOfRangeRadioButton = None
        self.bakeTypeButtonGroup = None
        self.startTimeWidget = None
        self.startTimeLabel = None
        self.startTimeSpinBox = None
        self.endTimeWidget = None
        self.endTimeLabel = None
        self.endTimeSpinBox = None
        self.alignEndTangentsCheckBox = None
        self.skipCustomAttributesCheckBox = None
        self.bakePushButton = None
    # endregion

    # region Properties
    @property
    def infinityType(self):
        """
        Getter method that returns the infinity type.

        :rtype: int
        """

        return INFINITY_TYPES.get(self.infinityTypeButtonGroup.checkedId(), 0)

    @infinityType.setter
    def infinityType(self, infinityType):
        """
        Setter method that updates the infinity type.

        :type infinityType: int
        :rtype: None
        """

        index = list(INFINITY_TYPES.values()).index(infinityType)
        self.infinityTypeButtonGroup.buttons()[index].setChecked(True)

    @property
    def alignEndTangents(self):
        """
        Getter method that returns the `alignEndTangents` flag.

        :rtype: bool
        """

        return self.alignEndTangentsCheckBox.isChecked()

    @alignEndTangents.setter
    def alignEndTangents(self, alignEndTangents):
        """
        Setter method that updates the `alignEndTangents` flag.

        :type alignEndTangents: bool
        :rtype: None
        """

        self.alignEndTangentsCheckBox.setChecked(alignEndTangents)

    @property
    def skipCustomAttributes(self):
        """
        Getter method that returns the `skipCustomAttributes` flag.

        :rtype: bool
        """

        return self.skipCustomAttributesCheckBox.isChecked()

    @skipCustomAttributes.setter
    def skipCustomAttributes(self, skipCustomAttributes):
        """
        Setter method that updates the `skipCustomAttributes` flag.

        :type skipCustomAttributes: bool
        :rtype: None
        """

        self.skipCustomAttributesCheckBox.setChecked(skipCustomAttributes)
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QLoopTab, self).postLoad(*args, **kwargs)

        # Initialize infinity button group
        #
        self.infinityTypeButtonGroup = QtWidgets.QButtonGroup(self.infinityTypeGroupBox)
        self.infinityTypeButtonGroup.setExclusive(True)
        self.infinityTypeButtonGroup.addButton(self.constantPushButton, id=0)
        self.infinityTypeButtonGroup.addButton(self.linearPushButton, id=1)
        self.infinityTypeButtonGroup.addButton(self.cyclePushButton, id=2)
        self.infinityTypeButtonGroup.addButton(self.cycleOffsetPushButton, id=3)
        self.infinityTypeButtonGroup.addButton(self.oscillatePushButton, id=4)

        # Initialize baking button group
        #
        self.bakeTypeButtonGroup = QtWidgets.QButtonGroup(self.bakeGroupBox)
        self.bakeTypeButtonGroup.setExclusive(True)
        self.bakeTypeButtonGroup.addButton(self.bakeRangeRadioButton, id=0)
        self.bakeTypeButtonGroup.addButton(self.bakeOutOfRangeRadioButton, id=1)
        self.bakeTypeButtonGroup.idClicked.connect(self.on_bakeTypeButtonGroup_idClicked)

        # Edit start/end time spin boxes
        #
        self.startTimeSpinBox.setDefaultType(self.startTimeSpinBox.DefaultType.StartTime)
        self.endTimeSpinBox.setDefaultType(self.endTimeSpinBox.DefaultType.EndTime)

    def loadSettings(self, settings):
        """
        Loads the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QLoopTab, self).loadSettings(settings)

        # Load user preferences
        #
        self.infinityType = int(settings.value('tabs/loop/infinityType', defaultValue=3))
        self.alignEndTangents = bool(settings.value('tabs/loop/alignEndTangents', defaultValue=1))
        self.skipCustomAttributes = bool(settings.value('tabs/loop/skipCustomAttributes', defaultValue=1))

        startTime = int(settings.value('tabs/loop/startTime', defaultValue=self.scene.startTime))
        endTime = int(settings.value('tabs/loop/endTime', defaultValue=self.scene.endTime))
        self.setAnimationRange((startTime, endTime))

        bakeType = int(settings.value('tabs/loop/bakeType', defaultValue=0))
        self.setBakeType(bakeType)

    def saveSettings(self, settings):
        """
        Saves the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QLoopTab, self).saveSettings(settings)

        # Save user preferences
        #
        settings.setValue('tabs/loop/infinityType', self.infinityType)
        settings.setValue('tabs/loop/alignEndTangents', int(self.alignEndTangents))
        settings.setValue('tabs/loop/skipCustomAttributes', int(self.skipCustomAttributes))
        settings.setValue('tabs/loop/bakeType', int(self.bakeType()))

        startTime, endTime = self.animationRange()
        settings.setValue('tabs/loop/startTime', startTime)
        settings.setValue('tabs/loop/endTime', endTime)

    def bakeType(self):
        """
        Returns the current bake type.

        :rtype: BakeType
        """

        return BakeType(self.bakeTypeButtonGroup.checkedId())

    def setBakeType(self, bakeType):
        """
        Updates the bake type.

        :type bakeType: Union[int, BakeType]
        :rtype: None
        """

        buttons = self.bakeTypeButtonGroup.buttons()
        numButtons = len(buttons)

        if 0 <= bakeType < numButtons:

            buttons[bakeType].click()

    def animationRange(self):
        """
        Returns the user specified animation range.

        :rtype: Tuple[int, int]
        """

        startTime = self.startTimeSpinBox.value()
        endTime = self.endTimeSpinBox.value()

        return startTime, endTime

    def setAnimationRange(self, animationRange):
        """
        Updates the user specified animation range.

        :type animationRange: Tuple[int, int]
        :rtype: None
        """

        startTime, endTime = animationRange
        self.startTimeSpinBox.setValue(startTime)
        self.endTimeSpinBox.setValue(endTime)

    @undo(name="Set Infinity Types")
    def setInfinityTypes(self, *nodes, pre=True, post=True, infinityType=0):
        """
        Updates the infinity type on the supplied node's animation curves.

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :type pre: bool
        :type post: bool
        :type infinityType: int
        :rtype: None
        """

        # Iterate through nodes
        #
        change = oma.MAnimCurveChange()

        for node in nodes:

            # Iterate through channel-box plugs
            #
            for plug in node.iterPlugs(channelBox=True, skipUserAttributes=self.skipCustomAttributes):

                # Check if plug is animated
                #
                animCurve = node.findAnimCurve(plug, create=False)

                if animCurve is None:

                    continue

                # Update infinity type
                #
                if pre:

                    animCurve.setPreInfinityType(infinityType, change=change)

                if post:

                    animCurve.setPostInfinityType(infinityType, change=change)

        # Cache changes
        #
        commit(change.redoIt, change.undoIt)

    @undo(name='Flatten Tangents')
    def flattenTangents(self, *nodes):
        """
        Flattens the start and end tangents on the supplied node's animation curves.

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :rtype: None
        """

        # Iterate through nodes
        #
        change = oma.MAnimCurveChange()

        for node in nodes:

            # Iterate through channel-box plugs
            #
            for plug in node.iterPlugs(channelBox=True, skipUserAttributes=self.skipCustomAttributes):

                # Check if plug is animated
                #
                animCurve = node.findAnimCurve(plug, create=False)

                if animCurve is None:

                    continue

                # Check if anim-curve has enough inputs
                #
                inputs = animCurve.inputs()
                numInputs = len(inputs)

                if not (numInputs >= 2):

                    continue

                # Edit in/out tangent types
                #
                animCurve.setInTangentType(0, oma.MFnAnimCurve.kTangentAuto, change=change)
                animCurve.setOutTangentType(0, oma.MFnAnimCurve.kTangentAuto, change=change)

                lastIndex = numInputs - 1
                animCurve.setInTangentType(lastIndex, oma.MFnAnimCurve.kTangentAuto, change=change)
                animCurve.setOutTangentType(lastIndex, oma.MFnAnimCurve.kTangentAuto, change=change)

        # Cache changes
        #
        commit(change.redoIt, change.undoIt)

    @undo(name='Align Tangents')
    def alignTangents(self, *nodes):
        """
        Aligns the start and end tangents on the supplied node's animation curves.

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :rtype: None
        """

        # Iterate through nodes
        #
        change = oma.MAnimCurveChange()

        for node in nodes:

            # Iterate through channel-box plugs
            #
            for plug in node.iterPlugs(channelBox=True, skipUserAttributes=self.skipCustomAttributes):

                # Check if plug is animated
                #
                animCurve = node.findAnimCurve(plug, create=False)

                if animCurve is None:

                    continue

                # Check if anim-curve has enough inputs
                #
                inputs = animCurve.inputs()
                numInputs = len(inputs)

                if not (numInputs >= 2):

                    continue

                # Edit tangent types
                #
                lastIndex = numInputs - 1

                inTangentType, outTangentType = animCurve.inTangentType(0), animCurve.outTangentType(0)
                animCurve.setInTangentType(lastIndex, inTangentType, change=change)
                animCurve.setOutTangentType(lastIndex, outTangentType, change=change)

                # Check if tangents are custom
                #
                if oma.MFnAnimCurve.kTangentFixed in (inTangentType, outTangentType):

                    isLocked = animCurve.tangentsLocked(0)
                    inTangentX, inTangentY = animCurve.getTangentXY(0, True)
                    outTangentX, outTangentY = animCurve.getTangentXY(0, False)

                    animCurve.setTangentsLocked(lastIndex, False, change=change)
                    animCurve.setTangent(lastIndex, inTangentX, inTangentY, True, convertUnits=False, change=change)
                    animCurve.setTangent(lastIndex, outTangentX, outTangentY, False, convertUnits=False, change=change)
                    animCurve.setTangentsLocked(lastIndex, isLocked, change=change)

        # Cache changes
        #
        commit(change.redoIt, change.undoIt)

    def ensureLoopable(self, animCurve, animationRange, change=None):
        """
        Ensures that the supplied anim-curve has keyframes on the specified start and end frame.

        :type animCurve: mpynode.MPyNode
        :type animationRange: Tuple[int, int]
        :type change: oma.MAnimCurveChange
        :rtype: None
        """

        startFrame, endFrame = animationRange

        startTime = om.MTime(startFrame, unit=om.MTime.uiUnit())
        startIndex = animCurve.insertKey(startTime, change=change)
        animCurve.setInTangentType(startIndex, oma.MFnAnimCurve.kTangentFixed, change=change)
        animCurve.setOutTangentType(startIndex, oma.MFnAnimCurve.kTangentFixed, change=change)

        endTime = om.MTime(endFrame, unit=om.MTime.uiUnit())
        endIndex = animCurve.insertKey(endTime, change=change)
        animCurve.setInTangentType(endIndex, oma.MFnAnimCurve.kTangentFixed, change=change)
        animCurve.setOutTangentType(endIndex, oma.MFnAnimCurve.kTangentFixed, change=change)

    def removeOutOfRangeKeys(self, animCurve, animationRange, change=None):
        """
        Removes any keyframes outside the specified start and end frame.

        :type animCurve: mpynode.MPyNode
        :type animationRange: Tuple[int, int]
        :type change: oma.MAnimCurveChange
        :rtype: None
        """

        startFrame, endFrame = animationRange

        for i in reversed(range(animCurve.numKeys)):

            frame = animCurve.input(i).value

            if not (startFrame <= frame <= endFrame):

                animCurve.remove(i, change=change)

            else:

                continue

    @undo(name='Bake Range')
    def bakeRange(self, nodes, loopRange):
        """
        Bakes the specified loop-range to the rest of the animation-range.

        :type nodes: List[mpynode.MPyNode]
        :type loopRange: Tuple[int, int]
        :rtype: None
        """

        # Iterate through nodes
        #
        startLoop, endLoop = loopRange
        animationRange = self.scene.animationRange

        change = oma.MAnimCurveChange()

        for node in nodes:

            # Iterate through channel-box plugs
            #
            for plug in node.iterPlugs(channelBox=True, skipUserAttributes=self.skipCustomAttributes):

                # Check if plug is animated
                #
                animCurve = node.findAnimCurve(plug, create=False)

                if animCurve is None:

                    continue

                # Iterate through infinity keyframes
                #
                self.ensureLoopable(animCurve, loopRange, change=change)
                self.removeOutOfRangeKeys(animCurve, loopRange, change=change)

                keyframes = animCurve.getInfinityKeys(animationRange, alignEndTangents=self.alignEndTangents)
                
                for keyframe in keyframes:

                    # Check if keyframe is out-of-range
                    #
                    if startLoop <= keyframe.time < endLoop:

                        continue

                    # Add keyframe
                    #
                    time = om.MTime(keyframe.time, unit=om.MTime.uiUnit())

                    index = animCurve.addKey(
                        time,
                        keyframe.value,
                        tangentInType=animCurve.kTangentAuto,
                        tangentOutType=animCurve.kTangentAuto,
                        change=change
                    )

                    # Update tangent handles
                    #
                    animCurve.setInTangentType(index, keyframe.inTangentType, change=change)
                    animCurve.setOutTangentType(index, keyframe.outTangentType, change=change)

                    if oma.MFnAnimCurve.kTangentFixed in (keyframe.inTangentType, keyframe.outTangentType):

                        animCurve.setTangentsLocked(index, False, change=change)
                        animCurve.setTangent(index, keyframe.inTangent.x, keyframe.inTangent.y, True, convertUnits=False, change=change)
                        animCurve.setTangent(index, keyframe.outTangent.x, keyframe.outTangent.y, False, convertUnits=False, change=change)
                        animCurve.setTangentsLocked(index, True, change=change)

        # Cache changes
        #
        commit(change.redoIt, change.undoIt)

    @undo(name='Bake Out-Of-Range')
    def bakeOutOfRange(self, nodes, animationRange):
        """
        Bakes the infinity curves inside the specified animation-range.

        :type nodes: List[mpynode.MPyNode]
        :type animationRange: Tuple[int, int]
        :rtype: None
        """

        # Iterate through nodes
        #
        animationRange = animationRange if not stringutils.isNullOrEmpty(animationRange) else self.scene.animationRange
        change = oma.MAnimCurveChange()

        for node in nodes:

            # Iterate through channel-box plugs
            #
            for plug in node.iterPlugs(channelBox=True, skipUserAttributes=self.skipCustomAttributes):

                # Check if plug is animated
                #
                animCurve = node.findAnimCurve(plug, create=False)

                if animCurve is None:

                    continue

                # Check if anim-curve has enough inputs
                #
                keyframes = animCurve.getInfinityKeys(animationRange, alignEndTangents=self.alignEndTangents)
                numKeyframes = len(keyframes)

                if not (numKeyframes >= 2):

                    continue

                # Iterate through keyframes
                #
                for keyframe in keyframes:

                    # Add keyframe
                    #
                    time = om.MTime(keyframe.time, unit=om.MTime.uiUnit())

                    index = animCurve.addKey(
                        time,
                        keyframe.value,
                        tangentInType=animCurve.kTangentAuto,
                        tangentOutType=animCurve.kTangentAuto,
                        change=change
                    )

                    # Update tangent handles
                    #
                    animCurve.setInTangentType(index, keyframe.inTangentType, change=change)
                    animCurve.setOutTangentType(index, keyframe.outTangentType, change=change)

                    if oma.MFnAnimCurve.kTangentFixed in (keyframe.inTangentType, keyframe.outTangentType):

                        animCurve.setTangentsLocked(index, False, change=change)
                        animCurve.setTangent(index, keyframe.inTangent.x, keyframe.inTangent.y, True, convertUnits=False, change=change)
                        animCurve.setTangent(index, keyframe.outTangent.x, keyframe.outTangent.y, False, convertUnits=False, change=change)
                        animCurve.setTangentsLocked(index, True, change=change)

                # Cleanup keys outside animation range
                #
                self.ensureLoopable(animCurve, animationRange, change=change)
                self.removeOutOfRangeKeys(animCurve, animationRange, change=change)

        # Cache changes
        #
        commit(change.redoIt, change.undoIt)
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_preInfinityPushButton_clicked(self, checked=False):
        """
        Slot method for the preInfinityPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        nodes = self.scene.selection(apiType=om.MFn.kTransform)
        self.setInfinityTypes(*nodes, pre=True, post=False, infinityType=self.infinityType)

    @QtCore.Slot(bool)
    def on_postInfinityPushButton_clicked(self, checked=False):
        """
        Slot method for the postInfinityPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        nodes = self.scene.selection(apiType=om.MFn.kTransform)
        self.setInfinityTypes(*nodes, pre=False, post=True, infinityType=self.infinityType)

    @QtCore.Slot(bool)
    def on_flattenTangentsPushButton_clicked(self, checked=False):
        """
        Slot method for the flattenTangentsPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        nodes = self.scene.selection(apiType=om.MFn.kTransform)
        self.flattenTangents(*nodes)

    @QtCore.Slot(bool)
    def on_alignTangentsPushButton_clicked(self, checked=False):
        """
        Slot method for the alignTangentsPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        nodes = self.scene.selection(apiType=om.MFn.kTransform)
        self.alignTangents(*nodes)

    @QtCore.Slot(int)
    def on_bakeTypeButtonGroup_idClicked(self, id):
        """
        Slot method for the bakeTypeButtonGroup's `idClicked` signal.

        :type id: int
        :rtype: None
        """

        numLabels = len(self.__labels__)

        if 0 <= id < numLabels:

            self.bakeLabel.setText(self.__labels__[id])

        else:

            self.bakeLabel.setText('')

    @QtCore.Slot(bool)
    def on_bakePushButton_clicked(self, checked=False):
        """
        Slot method for the bakePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        nodes = self.scene.selection(apiType=om.MFn.kTransform)
        animationRange = self.animationRange()

        bakeType = self.bakeType()

        if bakeType == BakeType.RANGE:

            self.bakeRange(nodes, animationRange)

        elif bakeType == BakeType.OUT_OF_RANGE:

            self.bakeOutOfRange(nodes, animationRange)

        else:

            pass
    # endregion
