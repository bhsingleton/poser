from maya.api import OpenMaya as om, OpenMayaAnim as oma
from Qt import QtCore, QtWidgets, QtGui
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


class QLoopTab(qabstracttab.QAbstractTab):
    """
    Overload of `QAbstractTab` that manipulates looping animations.
    """

    # region Dunderscores
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
        self.startTimeWidget = None
        self.startTimeCheckBox = None
        self.startTimeSpinBox = None
        self.endTimeWidget = None
        self.endTimeCheckBox = None
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

        startTimeEnabled = bool(settings.value('tabs/loop/startTimeEnabled', defaultValue=0))
        endTimeEnabled = bool(settings.value('tabs/loop/endTimeEnabled', defaultValue=0))
        self.startTimeCheckBox.setChecked(startTimeEnabled)
        self.endTimeCheckBox.setChecked(endTimeEnabled)

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

        startTime, endTime = self.animationRange()
        settings.setValue('tabs/loop/startTime', startTime)
        settings.setValue('tabs/loop/endTime', endTime)

        startTimeEnabled, endTimeEnabled = self.startTimeCheckBox.isChecked(), self.endTimeCheckBox.isChecked()
        settings.setValue('tabs/loop/startTimeEnabled', int(startTimeEnabled))
        settings.setValue('tabs/loop/endTimeEnabled', int(endTimeEnabled))

    def animationRange(self):
        """
        Returns the user specified animation range.

        :rtype: Tuple[int, int]
        """

        startTime = self.startTimeSpinBox.value() if self.startTimeCheckBox.isChecked() else self.scene.startTime
        endTime = self.endTimeSpinBox.value() if self.endTimeCheckBox.isChecked() else self.scene.endTime

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
                lastIndex = numInputs - 1

                animCurve.setInTangentType(0, oma.MFnAnimCurve.kTangentAuto, change=change)
                animCurve.setInTangentType(lastIndex, oma.MFnAnimCurve.kTangentAuto, change=change)

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

                    inTangentXY, outTangentXY = animCurve.getTangentXY(0, True), animCurve.getTangentXY(0, False)

                    animCurve.setTangentsLocked(lastIndex, False, change=change)
                    animCurve.setTangent(lastIndex, inTangentXY, True, convertUnits=False, change=change)
                    animCurve.setTangent(lastIndex, outTangentXY, False, convertUnits=False, change=change)
                    animCurve.setTangentsLocked(lastIndex, True, change=change)

        # Cache changes
        #
        commit(change.redoIt, change.undoIt)

    @undo(name='Bake Infinity Curves')
    def bakeInfinityCurves(self, *nodes, animationRange=None):
        """
        Bakes the infinity animation curves on the supplied nodes.

        :type nodes: Union[mpynode.MPyNode, List[mpynode.MPyNode]]
        :type animationRange: Tuple[int, int]
        :rtype: None
        """

        # Iterate through nodes
        #
        animationRange = animationRange if not stringutils.isNullOrEmpty(animationRange) else self.scene.animationRange
        startTime, endTime = animationRange

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
                startInput, endInput = animCurve.inputRange()

                for keyframe in keyframes:

                    # Check if keyframe is out-of-range
                    #
                    if not (startTime <= keyframe.time <= endTime) or (startInput <= keyframe.time < endInput):

                        continue

                    # Insert keyframe
                    #
                    time = om.MTime(keyframe.time, unit=om.MTime.uiUnit())
                    index = animCurve.insertKey(time, change=change)

                    animCurve.setValue(index, keyframe.value, change=change)

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

    @QtCore.Slot(bool)
    def on_bakePushButton_clicked(self, checked=False):
        """
        Slot method for the applyPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        nodes = self.scene.selection(apiType=om.MFn.kTransform)
        animationRange = self.animationRange()

        self.bakeInfinityCurves(*nodes, animationRange=animationRange)
    # endregion
