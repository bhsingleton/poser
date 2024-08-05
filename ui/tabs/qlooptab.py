from maya.api import OpenMaya as om, OpenMayaAnim as oma
from Qt import QtCore, QtWidgets, QtGui
from enum import IntEnum
from dcc.python import stringutils
from dcc.ui import qtimespinbox, qdivider
from dcc.maya.decorators import undo
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
    __bake_labels__ = {
        BakeType.RANGE: 'Enter the start and end frame of your loop.\nAny keys outside this range will be overwritten with baked keys!',
        BakeType.OUT_OF_RANGE: 'Enter the start and end frame of your animation.\nAny infinity curves inside this range will be baked down!'
    }

    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Initialize central layout
        #
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setObjectName('centralLayout')

        self.setLayout(centralLayout)

        # Initialize infinity group-box
        #
        self.infinityLayout = QtWidgets.QGridLayout()
        self.infinityLayout.setObjectName('infinityLayout')

        self.infinityGroupBox = QtWidgets.QGroupBox('Pre/Post Infinity:')
        self.infinityGroupBox.setObjectName('infinityGroupBox')
        self.infinityGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.infinityGroupBox.setLayout(self.infinityLayout)

        self.constantPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/ezposer/icons/ort_constant.png'), '')
        self.constantPushButton.setObjectName('constantPushButton')
        self.constantPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.constantPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.constantPushButton.setIconSize(QtCore.QSize(72, 72))
        self.constantPushButton.setCheckable(True)
        self.constantPushButton.setChecked(True)
        
        self.constantLabel = QtWidgets.QLabel('Constant')
        self.constantLabel.setObjectName('constantLabel')
        self.constantLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.constantLabel.setFixedHeight(24)
        self.constantLabel.setAlignment(QtCore.Qt.AlignCenter)

        self.linearPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/ezposer/icons/ort_linear.png'), '')
        self.linearPushButton.setObjectName('linearPushButton')
        self.linearPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.linearPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.linearPushButton.setIconSize(QtCore.QSize(72, 72))
        self.linearPushButton.setCheckable(True)

        self.linearLabel = QtWidgets.QLabel('Linear')
        self.linearLabel.setObjectName('linearLabel')
        self.linearLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.linearLabel.setFixedHeight(24)
        self.linearLabel.setAlignment(QtCore.Qt.AlignCenter)
        
        self.cyclePushButton = QtWidgets.QPushButton(QtGui.QIcon(':/ezposer/icons/ort_cycle.png'), '')
        self.cyclePushButton.setObjectName('cyclePushButton')
        self.cyclePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.cyclePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.cyclePushButton.setIconSize(QtCore.QSize(72, 72))
        self.cyclePushButton.setCheckable(True)

        self.cycleLabel = QtWidgets.QLabel('Cycle')
        self.cycleLabel.setObjectName('cycleLabel')
        self.cycleLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.cycleLabel.setFixedHeight(24)
        self.cycleLabel.setAlignment(QtCore.Qt.AlignCenter)
        
        self.cycleOffsetPushButton = QtWidgets.QPushButton(QtGui.QIcon(':/ezposer/icons/ort_cycle_offset.png'), '')
        self.cycleOffsetPushButton.setObjectName('cycleOffsetPushButton')
        self.cycleOffsetPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.cycleOffsetPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.cycleOffsetPushButton.setIconSize(QtCore.QSize(72, 72))
        self.cycleOffsetPushButton.setCheckable(True)

        self.cycleOffsetLabel = QtWidgets.QLabel('Cycle-Offset')
        self.cycleOffsetLabel.setObjectName('cycleOffsetLabel')
        self.cycleOffsetLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.cycleOffsetLabel.setFixedHeight(24)
        self.cycleOffsetLabel.setAlignment(QtCore.Qt.AlignCenter)
        
        self.oscillatePushButton = QtWidgets.QPushButton(QtGui.QIcon(':/ezposer/icons/ort_oscilate.png'), '')
        self.oscillatePushButton.setObjectName('oscillatePushButton')
        self.oscillatePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.oscillatePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.oscillatePushButton.setIconSize(QtCore.QSize(72, 72))
        self.oscillatePushButton.setCheckable(True)

        self.oscillateLabel = QtWidgets.QLabel('Oscillate')
        self.oscillateLabel.setObjectName('oscillateLabel')
        self.oscillateLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.oscillateLabel.setFixedHeight(24)
        self.oscillateLabel.setAlignment(QtCore.Qt.AlignCenter)

        self.infinityTypeButtonGroup = QtWidgets.QButtonGroup(self.infinityGroupBox)
        self.infinityTypeButtonGroup.setExclusive(True)
        self.infinityTypeButtonGroup.addButton(self.constantPushButton, id=0)
        self.infinityTypeButtonGroup.addButton(self.linearPushButton, id=1)
        self.infinityTypeButtonGroup.addButton(self.cyclePushButton, id=2)
        self.infinityTypeButtonGroup.addButton(self.cycleOffsetPushButton, id=3)
        self.infinityTypeButtonGroup.addButton(self.oscillatePushButton, id=4)

        self.preInfinityPushButton = QtWidgets.QPushButton('<<')
        self.preInfinityPushButton.setObjectName('preInfinityPushButton')
        self.preInfinityPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.preInfinityPushButton.setFixedHeight(24)
        self.preInfinityPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.preInfinityPushButton.clicked.connect(self.on_preInfinityPushButton_clicked)

        self.postInfinityPushButton = QtWidgets.QPushButton('>>')
        self.postInfinityPushButton.setObjectName('postInfinityPushButton')
        self.postInfinityPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.postInfinityPushButton.setFixedHeight(24)
        self.postInfinityPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.postInfinityPushButton.clicked.connect(self.on_postInfinityPushButton_clicked)

        self.infinityInteropLayout = QtWidgets.QHBoxLayout()
        self.infinityInteropLayout.setObjectName('infinityInteropLayout')
        self.infinityInteropLayout.setContentsMargins(0, 0, 0, 0)
        self.infinityInteropLayout.addWidget(self.preInfinityPushButton)
        self.infinityInteropLayout.addWidget(self.postInfinityPushButton)

        self.infinityLayout.addWidget(self.constantPushButton, 0, 0)
        self.infinityLayout.addWidget(self.constantLabel, 1, 0)
        self.infinityLayout.addWidget(self.linearPushButton, 0, 1)
        self.infinityLayout.addWidget(self.linearLabel, 1, 1)
        self.infinityLayout.addWidget(self.cyclePushButton, 2, 0)
        self.infinityLayout.addWidget(self.cycleLabel, 3, 0)
        self.infinityLayout.addWidget(self.cycleOffsetPushButton, 2, 1)
        self.infinityLayout.addWidget(self.cycleOffsetLabel, 3, 1)
        self.infinityLayout.addWidget(self.oscillatePushButton, 2, 2)
        self.infinityLayout.addWidget(self.oscillateLabel, 3, 2)
        self.infinityLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal), 4, 0, 1, 3)
        self.infinityLayout.addLayout(self.infinityInteropLayout, 5, 0, 1, 3)
        
        centralLayout.addWidget(self.infinityGroupBox)
        
        # Initialize tangents group-box
        #
        self.tangentsLayout = QtWidgets.QGridLayout()
        self.tangentsLayout.setObjectName('tangentsLayout')

        self.tangentsGroupBox = QtWidgets.QGroupBox('Start/End Tangents:')
        self.tangentsGroupBox.setObjectName('tangentsGroupBox')
        self.tangentsGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.tangentsGroupBox.setLayout(self.tangentsLayout)

        self.flattenTangentsPushButton = QtWidgets.QPushButton('Flatten')
        self.flattenTangentsPushButton.setObjectName('flattenTangentsPushButton')
        self.flattenTangentsPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.flattenTangentsPushButton.setFixedHeight(24)
        self.flattenTangentsPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.flattenTangentsPushButton.setToolTip('Sets the start and end tangent types to auto.')
        self.flattenTangentsPushButton.clicked.connect(self.on_flattenTangentsPushButton_clicked)

        self.alignTangentsPushButton = QtWidgets.QPushButton('Align')
        self.alignTangentsPushButton.setObjectName('alignTangentsPushButton')
        self.alignTangentsPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.alignTangentsPushButton.setFixedHeight(24)
        self.alignTangentsPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.alignTangentsPushButton.setToolTip('Copies the start tangent and pastes it onto the end tangent.')
        self.alignTangentsPushButton.clicked.connect(self.on_alignTangentsPushButton_clicked)

        self.tangentsLayout.addWidget(self.flattenTangentsPushButton, 0, 0)
        self.tangentsLayout.addWidget(self.alignTangentsPushButton, 0, 1)
        
        centralLayout.addWidget(self.tangentsGroupBox)
        
        # Initialize baking group-box
        #
        self.bakingLayout = QtWidgets.QGridLayout()
        self.bakingLayout.setObjectName('bakingLayout')

        self.bakingGroupBox = QtWidgets.QGroupBox('Baking:')
        self.bakingGroupBox.setObjectName('bakingGroupBox')
        self.bakingGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.bakingGroupBox.setLayout(self.bakingLayout)

        self.bakeLabel = QtWidgets.QLabel(self.__bake_labels__[BakeType.OUT_OF_RANGE])
        self.bakeLabel.setObjectName('bakeLabel')
        self.bakeLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.bakeLabel.setMinimumHeight(48)
        self.bakeLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.bakeLabel.setWordWrap(False)

        self.bakeRangeRadioButton = QtWidgets.QRadioButton('Range')
        self.bakeRangeRadioButton.setObjectName('bakeRangeRadioButton')
        self.bakeRangeRadioButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.bakeRangeRadioButton.setFixedHeight(24)
        self.bakeRangeRadioButton.setFocusPolicy(QtCore.Qt.NoFocus)

        self.bakeOutOfRangeRadioButton = QtWidgets.QRadioButton('Out-Of-Range')
        self.bakeOutOfRangeRadioButton.setObjectName('bakeOutOfRangeRadioButton')
        self.bakeOutOfRangeRadioButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.bakeOutOfRangeRadioButton.setFixedHeight(24)
        self.bakeOutOfRangeRadioButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.bakeOutOfRangeRadioButton.setChecked(True)

        self.bakeTypeButtonGroup = QtWidgets.QButtonGroup(self.bakingGroupBox)
        self.bakeTypeButtonGroup.setExclusive(True)
        self.bakeTypeButtonGroup.addButton(self.bakeRangeRadioButton, id=0)
        self.bakeTypeButtonGroup.addButton(self.bakeOutOfRangeRadioButton, id=1)
        self.bakeTypeButtonGroup.idClicked.connect(self.on_bakeTypeButtonGroup_idClicked)

        self.startTimeLayout = QtWidgets.QHBoxLayout()
        self.startTimeLayout.setObjectName('startTimeLayout')
        self.startTimeLayout.setContentsMargins(0, 0, 0, 0)

        self.startTimeWidget = QtWidgets.QWidget()
        self.startTimeWidget.setObjectName('startTimeWidget')
        self.startTimeWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.startTimeWidget.setFixedHeight(24)
        self.startTimeWidget.setLayout(self.startTimeLayout)

        self.startTimeLabel = QtWidgets.QLabel('Start:')
        self.startTimeLabel.setObjectName('startTimeLabel')
        self.startTimeLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.startTimeLabel.setFixedWidth(32)
        self.startTimeLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.startTimeSpinBox = qtimespinbox.QTimeSpinBox()
        self.startTimeSpinBox.setObjectName('startTimeSpinBox')
        self.startTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.startTimeSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.startTimeSpinBox.setToolTip('The start frame to sample from.')
        self.startTimeSpinBox.setDefaultType(qtimespinbox.QTimeSpinBox.DefaultType.START_TIME)
        self.startTimeSpinBox.setMinimum(-9999999)
        self.startTimeSpinBox.setMaximum(9999999)
        self.startTimeSpinBox.setValue(self.scene.startTime)

        self.startTimeLayout.addWidget(self.startTimeLabel)
        self.startTimeLayout.addWidget(self.startTimeSpinBox)

        self.endTimeLayout = QtWidgets.QHBoxLayout()
        self.endTimeLayout.setObjectName('endTimeLayout')
        self.endTimeLayout.setContentsMargins(0, 0, 0, 0)

        self.endTimeWidget = QtWidgets.QWidget()
        self.endTimeWidget.setObjectName('endTimeWidget')
        self.endTimeWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.endTimeWidget.setFixedHeight(24)
        self.endTimeWidget.setLayout(self.endTimeLayout)

        self.endTimeLabel = QtWidgets.QLabel('End:')
        self.endTimeLabel.setObjectName('endTimeLabel')
        self.endTimeLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.endTimeLabel.setFixedWidth(32)
        self.endTimeLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.endTimeSpinBox = qtimespinbox.QTimeSpinBox()
        self.endTimeSpinBox.setObjectName('endTimeSpinBox')
        self.endTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.endTimeSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.endTimeSpinBox.setToolTip('The end frame to sample from.')
        self.endTimeSpinBox.setDefaultType(qtimespinbox.QTimeSpinBox.DefaultType.END_TIME)
        self.endTimeSpinBox.setMinimum(-9999999)
        self.endTimeSpinBox.setMaximum(9999999)
        self.endTimeSpinBox.setValue(self.scene.endTime)

        self.endTimeLayout.addWidget(self.endTimeLabel)
        self.endTimeLayout.addWidget(self.endTimeSpinBox)

        self.alignEndTangentsCheckBox = QtWidgets.QCheckBox('Align End Tangents')
        self.alignEndTangentsCheckBox.setObjectName('alignEndTangentsCheckBox')
        self.alignEndTangentsCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.alignEndTangentsCheckBox.setFixedHeight(24)
        self.alignEndTangentsCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)

        self.skipCustomAttributesCheckBox = QtWidgets.QCheckBox('Skip Custom Attributes')
        self.skipCustomAttributesCheckBox.setObjectName('skipCustomAttributesCheckBox')
        self.skipCustomAttributesCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.skipCustomAttributesCheckBox.setFixedHeight(24)
        self.skipCustomAttributesCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)

        self.bakePushButton = QtWidgets.QPushButton('Bake')
        self.bakePushButton.setObjectName('bakePushButton')
        self.bakePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.bakePushButton.setFixedHeight(48)
        self.bakePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.bakePushButton.clicked.connect(self.on_bakePushButton_clicked)

        self.bakingLayout.addWidget(self.bakeLabel, 0, 0, 1, 2)
        self.bakingLayout.addWidget(self.bakeRangeRadioButton, 1, 0, alignment=QtCore.Qt.AlignCenter)
        self.bakingLayout.addWidget(self.bakeOutOfRangeRadioButton, 1, 1, alignment=QtCore.Qt.AlignCenter)
        self.bakingLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal), 2, 0, 1, 2)
        self.bakingLayout.addWidget(self.startTimeWidget, 3, 0)
        self.bakingLayout.addWidget(self.endTimeWidget, 3, 1)
        self.bakingLayout.addWidget(self.alignEndTangentsCheckBox, 4, 0)
        self.bakingLayout.addWidget(self.skipCustomAttributesCheckBox, 4, 1)
        self.bakingLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal), 5, 0, 1, 2)
        self.bakingLayout.addWidget(self.bakePushButton, 6, 0, 1, 2)

        centralLayout.addWidget(self.bakingGroupBox)
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
        self.infinityType = settings.value('tabs/loop/infinityType', defaultValue=3, type=int)
        self.alignEndTangents = settings.value('tabs/loop/alignEndTangents', defaultValue=1, type=int)
        self.skipCustomAttributes = settings.value('tabs/loop/skipCustomAttributes', defaultValue=1, type=int)

        startTime = settings.value('tabs/loop/startTime', defaultValue=self.scene.startTime, type=int)
        endTime = settings.value('tabs/loop/endTime', defaultValue=self.scene.endTime, type=int)
        self.setAnimationRange((startTime, endTime))

        bakeType = settings.value('tabs/loop/bakeType', defaultValue=0, type=int)
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

    @undo.Undo(name="Set Infinity Types")
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
        undo.commit(change.redoIt, change.undoIt)

    @undo.Undo(name='Flatten Tangents')
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
        undo.commit(change.redoIt, change.undoIt)

    @undo.Undo(name='Align Tangents')
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
        undo.commit(change.redoIt, change.undoIt)

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

    @undo.Undo(name='Bake Range')
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
        undo.commit(change.redoIt, change.undoIt)

    @undo.Undo(name='Bake Out-Of-Range')
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
        undo.commit(change.redoIt, change.undoIt)
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

        numLabels = len(self.__bake_labels__)

        if 0 <= id < numLabels:

            self.bakeLabel.setText(self.__bake_labels__[id])

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
