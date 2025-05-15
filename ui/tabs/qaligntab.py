import json

from maya.api import OpenMaya as om
from mpy import mpyscene
from dcc.vendor.Qt import QtCore, QtWidgets, QtGui, QtCompat
from dcc.ui import qrollout, qdivider, qtimespinbox, qxyzwidget, qseparator
from dcc.ui.abstract import qabcmeta
from dcc.python import stringutils
from dcc.maya.libs import dagutils
from dcc.maya.decorators import undo
from . import qabstracttab

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QAlignRollout(qrollout.QRollout, metaclass=qabcmeta.QABCMeta):
    """
    Overload of `QRollout` that interfaces with alignment data.
    """

    # region Dunderscores
    def __init__(self, title, **kwargs):
        """
        Private method called after a new instance has been created.

        :type parent: QtWidgets.QWidget
        :type f: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QAlignRollout, self).__init__(title, **kwargs)

        # Declare private variables
        #
        self._scene = mpyscene.MPyScene.getInstance(asWeakReference=True)
        self._sourceNode = None
        self._targetNode = None

    def __post_init__(self, *args, **kwargs):
        """
        Private method called after an instance has initialized.

        :rtype: None
        """

        self.__setup_ui__()

    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that builds the user interface.

        :rtype: None
        """

        # Assign vertical layout
        #
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setObjectName('centralLayout')

        self.setLayout(centralLayout)

        # Create node widgets
        #
        self.sourcePushButton = QtWidgets.QPushButton('Parent')
        self.sourcePushButton.setObjectName('sourcePushButton')
        self.sourcePushButton.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        self.sourcePushButton.setFixedHeight(20)
        self.sourcePushButton.setMinimumWidth(48)
        self.sourcePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.sourcePushButton.setToolTip('Picks the node to align to.')
        self.sourcePushButton.clicked.connect(self.on_sourcePushButton_clicked)

        self.switchPushButton = QtWidgets.QPushButton(QtGui.QIcon(':dcc/icons/switch'), '')
        self.switchPushButton.setObjectName('switchPushButton')
        self.switchPushButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.switchPushButton.setFixedSize(QtCore.QSize(20, 20))
        self.switchPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.switchPushButton.clicked.connect(self.on_switchPushButton_clicked)

        self.targetPushButton = QtWidgets.QPushButton('Child')
        self.targetPushButton.setObjectName('targetPushButton')
        self.targetPushButton.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        self.targetPushButton.setFixedHeight(20)
        self.targetPushButton.setMinimumWidth(48)
        self.targetPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.targetPushButton.setToolTip('Picks the node to be aligned.')
        self.targetPushButton.clicked.connect(self.on_targetPushButton_clicked)

        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonLayout.setObjectName('buttonLayout')
        self.buttonLayout.addWidget(self.sourcePushButton)
        self.buttonLayout.addWidget(self.switchPushButton)
        self.buttonLayout.addWidget(self.targetPushButton)

        centralLayout.addLayout(self.buttonLayout)
        centralLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal))

        # Create time range widgets
        #
        self.startCheckBox = QtWidgets.QCheckBox('')
        self.startCheckBox.setObjectName('startCheckBox')
        self.startCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.startCheckBox.setFixedHeight(20)
        self.startCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.startCheckBox.setChecked(True)
        self.startCheckBox.stateChanged.connect(self.on_startCheckBox_stateChanged)

        self.startSpinBox = qtimespinbox.QTimeSpinBox()
        self.startSpinBox.setObjectName('startSpinBox')
        self.startSpinBox.setPrefix('Start: ')
        self.startSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.startSpinBox.setFixedHeight(20)
        self.startSpinBox.setMinimumWidth(20)
        self.startSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.startSpinBox.setDefaultType(qtimespinbox.DefaultType.START_TIME)
        self.startSpinBox.setRange(-9999, 9999)
        self.startSpinBox.setValue(0)

        self.endCheckBox = QtWidgets.QCheckBox('')
        self.endCheckBox.setObjectName('endCheckBox')
        self.endCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.endCheckBox.setFixedHeight(20)
        self.endCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.endCheckBox.setChecked(True)
        self.endCheckBox.stateChanged.connect(self.on_endCheckBox_stateChanged)

        self.endSpinBox = qtimespinbox.QTimeSpinBox()
        self.endSpinBox.setObjectName('endSpinBox')
        self.endSpinBox.setPrefix('End: ')
        self.endSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.endSpinBox.setFixedHeight(20)
        self.endSpinBox.setMinimumWidth(20)
        self.endSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.endSpinBox.setDefaultType(qtimespinbox.DefaultType.END_TIME)
        self.endSpinBox.setRange(-9999, 9999)
        self.endSpinBox.setValue(1)

        self.stepSpinBox = qtimespinbox.QTimeSpinBox()
        self.stepSpinBox.setObjectName('stepSpinBox')
        self.stepSpinBox.setPrefix('Step(s): ')
        self.stepSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.stepSpinBox.setFixedHeight(20)
        self.stepSpinBox.setMinimumWidth(20)
        self.stepSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.stepSpinBox.setRange(1, 100)
        self.stepSpinBox.setValue(1)

        self.timeRangeLayout = QtWidgets.QHBoxLayout()
        self.timeRangeLayout.setObjectName('timeRangeLayout')
        self.timeRangeLayout.addWidget(self.startCheckBox)
        self.timeRangeLayout.addWidget(self.startSpinBox)
        self.timeRangeLayout.addWidget(self.endCheckBox)
        self.timeRangeLayout.addWidget(self.endSpinBox)
        self.timeRangeLayout.addWidget(qdivider.QDivider(QtCore.Qt.Vertical))
        self.timeRangeLayout.addWidget(self.stepSpinBox)

        centralLayout.addLayout(self.timeRangeLayout)
        centralLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal))

        # Create align transform widgets
        #
        self.alignTranslateXYZWidget = qxyzwidget.QXyzWidget('Pos')
        self.alignTranslateXYZWidget.setObjectName('alignTranslateXYZWidget')
        self.alignTranslateXYZWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.alignTranslateXYZWidget.setFixedHeight(20)
        self.alignTranslateXYZWidget.setStyleSheet('QPushButton:hover:checked { background-color: green; }\nQPushButton:checked { background-color: darkgreen; border: none; }')
        self.alignTranslateXYZWidget.setToolTip('Specify which translate axes should be aligned.')
        self.alignTranslateXYZWidget.setCheckStates([True, True, True])

        self.alignRotateXYZWidget = qxyzwidget.QXyzWidget('Rot')
        self.alignRotateXYZWidget.setObjectName('alignRotateXYZWidget')
        self.alignRotateXYZWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.alignRotateXYZWidget.setFixedHeight(20)
        self.alignRotateXYZWidget.setStyleSheet('QPushButton:hover:checked { background-color: green; }\nQPushButton:checked { background-color: darkgreen; border: none; }')
        self.alignRotateXYZWidget.setToolTip('Specify which rotate axes should be aligned.')
        self.alignRotateXYZWidget.setCheckStates([True, True, True])

        self.alignScaleXYZWidget = qxyzwidget.QXyzWidget('Scale')
        self.alignScaleXYZWidget.setObjectName('alignScaleXYZWidget')
        self.alignScaleXYZWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.alignScaleXYZWidget.setFixedHeight(20)
        self.alignScaleXYZWidget.setStyleSheet('QPushButton:hover:checked { background-color: green; }\nQPushButton:checked { background-color: darkgreen; border: none; }')
        self.alignScaleXYZWidget.setToolTip('Specify which scale axes should be aligned.')
        self.alignScaleXYZWidget.setCheckStates([False, False, False])

        self.alignLayout = QtWidgets.QHBoxLayout()
        self.alignLayout.setObjectName('alignLayout')
        self.alignLayout.setContentsMargins(0, 0, 0, 0)
        self.alignLayout.addWidget(self.alignTranslateXYZWidget)
        self.alignLayout.addWidget(self.alignRotateXYZWidget)
        self.alignLayout.addWidget(self.alignScaleXYZWidget)

        centralLayout.addLayout(self.alignLayout)
        centralLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal))

        # Create maintain offset widgets
        #
        self.maintainLabel = QtWidgets.QLabel('Maintain:')
        self.maintainLabel.setObjectName('maintainOffsetLabel')
        self.maintainLabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.maintainLabel.setFixedHeight(20)
        self.maintainLabel.setAlignment(QtCore.Qt.AlignCenter)

        self.maintainTranslateCheckBox = QtWidgets.QCheckBox('Position')
        self.maintainTranslateCheckBox.setObjectName('maintainTranslateCheckBox')
        self.maintainTranslateCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.maintainTranslateCheckBox.setFixedHeight(20)
        self.maintainTranslateCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)

        self.maintainRotateCheckBox = QtWidgets.QCheckBox('Rotation')
        self.maintainRotateCheckBox.setObjectName('maintainRotateCheckBox')
        self.maintainRotateCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.maintainRotateCheckBox.setFixedHeight(20)
        self.maintainRotateCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)

        self.maintainScaleCheckBox = QtWidgets.QCheckBox('Scale')
        self.maintainScaleCheckBox.setObjectName('maintainScaleCheckBox')
        self.maintainScaleCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.maintainScaleCheckBox.setFixedHeight(20)
        self.maintainScaleCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)

        self.maintainLayout = QtWidgets.QHBoxLayout()
        self.maintainLayout.setObjectName('maintainLayout')
        self.maintainLayout.addWidget(self.maintainLabel)
        self.maintainLayout.addWidget(self.maintainTranslateCheckBox)
        self.maintainLayout.addWidget(self.maintainRotateCheckBox)
        self.maintainLayout.addWidget(self.maintainScaleCheckBox)

        centralLayout.addLayout(self.maintainLayout)

        # Insert additional menu actions
        #
        menu = self.menu()

        self.addAlignmentAction = QtWidgets.QAction('Add Alignment', menu)
        self.removeAlignmentAction = QtWidgets.QAction('Remove Alignment', menu)

        menu.insertActions(
            menu.actions()[0],
            [
                self.addAlignmentAction,
                self.removeAlignmentAction,
                qseparator.QSeparator('', parent=menu)
            ]
        )

    def __getstate__(self):
        """
        Private method that returns a state object for this instance.

        :rtype: dict
        """

        return {
            'isChecked': self.isChecked(),
            'isExpanded': self.isExpanded(),
            'sourceName': self.sourceName,
            'targetName': self.targetName,
            'startTime': self.startTime,
            'endTime': self.endTime,
            'step': self.step,
            'alignTranslate': self.alignTranslate,
            'alignRotate': self.alignRotate,
            'alignScale': self.alignScale,
            'maintainTranslate': self.maintainTranslate,
            'maintainRotate': self.maintainRotate,
            'maintainScale': self.maintainScale
        }

    def __setstate__(self, state):
        """
        Private method that updates this instance from a state object.

        :type state: dict
        :rtype: None
        """

        self.setChecked(state.get('isChecked', True))
        self.setExpanded(state.get('expanded', True))
        self.sourceName = state.get('sourceName', '')
        self.targetName = state.get('targetName', '')
        self.startTime = state.get('startTime', 0)
        self.endTime = state.get('endTime', 1)
        self.step = state.get('step', 1)
        self.alignTranslate = state.get('alignTranslate', [True, True, True])
        self.alignRotate = state.get('alignRotate', [True, True, True])
        self.alignScale = state.get('alignScale', [False, False, False])
        self.maintainTranslate = (state.get('maintainTranslate', False))
        self.maintainRotate = (state.get('maintainRotate', False))
        self.maintainScale = (state.get('maintainScale', False))
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
    def sourceName(self):
        """
        Getter method that returns the source node name.

        :rtype: str
        """

        return self.sourcePushButton.whatsThis()

    @sourceName.setter
    def sourceName(self, sourceName):
        """
        Setter method that updates the source node name.

        :type sourceName: str
        :rtype: None
        """

        if stringutils.isNullOrEmpty(sourceName):

            self.sourcePushButton.setWhatsThis('')
            self.sourcePushButton.setText('Parent')

        else:

            self.sourcePushButton.setWhatsThis(sourceName)
            self.sourcePushButton.setText(dagutils.stripAll(sourceName))

        self.invalidate()

    @property
    def targetName(self):
        """
        Getter method that returns the target node name.

        :rtype: str
        """

        return self.targetPushButton.whatsThis()

    @targetName.setter
    def targetName(self, targetName):
        """
        Setter method that updates the target node name.

        :type targetName: str
        :rtype: None
        """

        if stringutils.isNullOrEmpty(targetName):

            self.targetPushButton.setWhatsThis('')
            self.targetPushButton.setText('Child')

        else:

            self.targetPushButton.setWhatsThis(targetName)
            self.targetPushButton.setText(dagutils.stripAll(targetName))

        self.invalidate()

    @property
    def startTime(self):
        """
        Getter method that returns the start time.

        :rtype: int
        """

        if self.startCheckBox.isChecked():

            return self.startSpinBox.value()

        else:

            return self.scene.startTime

    @startTime.setter
    def startTime(self, startTime):
        """
        Setter method that updates the start time.

        :type startTime: int
        :rtype: None
        """

        self.startSpinBox.setValue(startTime)

    @property
    def endTime(self):
        """
        Getter method that returns the end time.

        :rtype: int
        """

        if self.endCheckBox.isChecked():

            return self.endSpinBox.value()

        else:

            return self.scene.endTime

    @endTime.setter
    def endTime(self, endTime):
        """
        Setter method that updates the end time.

        :type endTime: int
        :rtype: None
        """

        self.endSpinBox.setValue(endTime)

    @property
    def step(self):
        """
        Getter method that returns the step interval.

        :rtype: int
        """

        return self.stepSpinBox.value()

    @step.setter
    def step(self, step):
        """
        Setter method that updates the step interval.

        :type step: int
        :rtype: None
        """

        self.stepSpinBox.setValue(step)

    @property
    def alignTranslate(self):
        """
        Getter method that returns the translate alignment flags.

        :rtype: Tuple[bool, bool, bool]
        """

        return self.alignTranslateXYZWidget.checkStates()

    @alignTranslate.setter
    def alignTranslate(self, alignTranslate):
        """
        Setter method that updates the translate alignment flags.

        :type alignTranslate: Tuple[bool, bool, bool]
        :rtype: None
        """

        self.alignTranslateXYZWidget.setCheckStates(alignTranslate)

    @property
    def alignRotate(self):
        """
        Getter method that returns the rotate alignment flags.

        :rtype: Tuple[bool, bool, bool]
        """

        return self.alignRotateXYZWidget.checkStates()

    @alignRotate.setter
    def alignRotate(self, alignRotate):
        """
        Setter method that updates the rotate alignment flags.

        :type alignRotate: Tuple[bool, bool, bool]
        :rtype: None
        """

        self.alignRotateXYZWidget.setCheckStates(alignRotate)

    @property
    def alignScale(self):
        """
        Getter method that returns the scale alignment flags.

        :rtype: Tuple[bool, bool, bool]
        """

        return self.alignScaleXYZWidget.checkStates()

    @alignScale.setter
    def alignScale(self, alignScale):
        """
        Setter method that updates the scale alignment flags.

        :type alignScale: Tuple[bool, bool, bool]
        :rtype: None
        """

        self.alignScaleXYZWidget.setCheckStates(alignScale)

    @property
    def maintainTranslate(self):
        """
        Getter method that returns the `maintainTranslate` flag.

        :rtype: bool
        """

        return self.maintainTranslateCheckBox.isChecked()

    @maintainTranslate.setter
    def maintainTranslate(self, maintainTranslate):
        """
        Setter method that updates the `maintainTranslate` flag.

        :type maintainTranslate: bool
        :rtype: None
        """

        self.maintainTranslateCheckBox.setChecked(maintainTranslate)

    @property
    def maintainRotate(self):
        """
        Getter method that returns the `maintainRotate` flag.

        :rtype: bool
        """

        return self.maintainRotateCheckBox.isChecked()

    @maintainRotate.setter
    def maintainRotate(self, maintainRotate):
        """
        Setter method that updates the `maintainRotate` flag.

        :type maintainRotate: bool
        :rtype: None
        """

        self.maintainRotateCheckBox.setChecked(maintainRotate)

    @property
    def maintainScale(self):
        """
        Getter method that returns the `maintainScale` flag.

        :rtype: bool
        """

        return self.maintainScaleCheckBox.isChecked()

    @maintainScale.setter
    def maintainScale(self, maintainScale):
        """
        Setter method that updates the `maintainScale` flag.

        :type maintainScale: bool
        :rtype: None
        """

        self.maintainScaleCheckBox.setChecked(maintainScale)
    # endregion

    # region Methods
    def isValid(self):
        """
        Evaluates if the source and target are valid.

        :rtype: bool
        """

        isSourceValid = self.scene.doesNodeExist(self.sourceName)
        isTargetValid = self.scene.doesNodeExist(self.targetName)

        return isSourceValid and isTargetValid

    def invalidate(self):
        """
        Re-concatenates the title of this rollout.

        :rtype: None
        """

        title = 'Align "{child}" to "{parent}"'.format(
            child=self.targetPushButton.text(),
            parent=self.sourcePushButton.text()
        )

        self.setTitle(title)

    def apply(self):
        """
        Aligns the target node to the source node on the current frame.

        :rtype: None
        """

        # Check if alignment is valid
        #
        isValid = self.isValid()

        if not isValid:

            log.warning(f'Unable to locate both "{self.sourceName}" parent and "{self.targetName}" child!')
            return

        # Iterate through time range
        #
        sourceNode = self.scene(self.sourceName)
        targetNode = self.scene(self.targetName)

        skipTranslate = self.alignTranslateXYZWidget.flags(prefix='skipTranslate', inverse=True)
        skipRotate = self.alignRotateXYZWidget.flags(prefix='skipRotate', inverse=True)
        skipScale = self.alignScaleXYZWidget.flags(prefix='skipScale', inverse=True)

        currentTime = self.scene.time

        targetNode.alignTransformTo(
            sourceNode,
            startTime=currentTime,
            endTime=currentTime,
            maintainTranslate=self.maintainTranslate,
            maintainRotate=self.maintainRotate,
            maintainScale=self.maintainScale,
            **skipTranslate,
            **skipRotate,
            **skipScale
        )

    def applyRange(self):
        """
        Aligns the target node to the source node over the specified amount of time.

        :rtype: None
        """

        # Check if alignment is valid
        #
        isValid = self.isValid()

        if not isValid:

            log.warning(f'Unable to locate both "{self.sourceName}" parent and "{self.targetName}" child!')
            return

        # Iterate through time range
        #
        sourceNode = self.scene(self.sourceName)
        targetNode = self.scene(self.targetName)

        skipTranslate = self.alignTranslateXYZWidget.flags(prefix='skipTranslate', inverse=True)
        skipRotate = self.alignRotateXYZWidget.flags(prefix='skipRotate', inverse=True)
        skipScale = self.alignScaleXYZWidget.flags(prefix='skipScale', inverse=True)

        targetNode.alignTransformTo(
            sourceNode,
            startTime=self.startTime,
            endTime=self.endTime,
            step=self.step,
            maintainTranslate=self.maintainTranslate,
            maintainRotate=self.maintainRotate,
            maintainScale=self.maintainScale,
            **skipTranslate,
            **skipRotate,
            **skipScale
        )
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_sourcePushButton_clicked(self, checked=False):
        """
        Slot method for the sourcePushButton's `clicked` signal.
        This method updates the source name.

        :type checked: bool
        :rtype: None
        """

        selection = self.scene.selection(apiType=om.MFn.kTransform)
        selectionCount = len(selection)

        if selectionCount > 0:

            node = selection[0]
            text = node.name()
            path = node.fullPathName()

            self.sourcePushButton.setText(text)
            self.sourcePushButton.setWhatsThis(path)
            self.invalidate()

    @QtCore.Slot(bool)
    def on_switchPushButton_clicked(self, checked=False):
        """
        Slot method for the switchPushButton's `clicked` signal.
        This method switches the parent and child nodes.

        :type checked: bool
        :rtype: None
        """

        self.sourceName, self.targetName = self.targetName, self.sourceName

    @QtCore.Slot(bool)
    def on_targetPushButton_clicked(self, checked=False):
        """
        Slot method for the targetPushButton's `clicked` signal.
        This method updates the source name.

        :type checked: bool
        :rtype: None
        """

        selection = self.scene.selection(apiType=om.MFn.kTransform)
        selectionCount = len(selection)

        if selectionCount > 0:

            node = selection[0]
            text = node.name()
            path = node.fullPathName()

            self.targetPushButton.setText(text)
            self.targetPushButton.setWhatsThis(path)
            self.invalidate()

    @QtCore.Slot(bool)
    def on_startCheckBox_stateChanged(self, state):
        """
        Slot method for the startCheckBox's `stateChanged` signal.
        This method updates the enabled state for the associated spin box.

        :type state: bool
        :rtype: None
        """

        self.startSpinBox.setEnabled(state)

    @QtCore.Slot(bool)
    def on_endCheckBox_stateChanged(self, state):
        """
        Slot method for the endCheckBox's `stateChanged` signal.
        This method updates the enabled state for the associated spin box.

        :type state: bool
        :rtype: None
        """

        self.endSpinBox.setEnabled(state)
    # endregion


class QAlignTab(qabstracttab.QAbstractTab):
    """
    Overload of `QAbstractTab` that aligns controls over a time interval.
    """

    # region Dunderscores
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

        # Declare public variables
        #
        self.scrollAreaContentLayout = QtWidgets.QVBoxLayout()
        self.scrollAreaContentLayout.setObjectName('scrollAreaContentLayout')
        self.scrollAreaContentLayout.setContentsMargins(0, 0, 0, 0)
        self.scrollAreaContentLayout.setSpacing(4)
        self.scrollAreaContentLayout.setAlignment(QtCore.Qt.AlignTop)

        self.scrollAreaContent = QtWidgets.QWidget()
        self.scrollAreaContent.setObjectName('scrollAreaContent')
        self.scrollAreaContent.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.scrollAreaContent.setLayout(self.scrollAreaContentLayout)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setObjectName('scrollArea')
        self.scrollArea.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.scrollAreaContent)

        self.alignPushButton = QtWidgets.QPushButton('Align')
        self.alignPushButton.setObjectName('alignPushButton')
        self.alignPushButton.setToolTip('LMB to align frame range and LMB+Shift to align just the current frame.')
        self.alignPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.alignPushButton.setFixedHeight(48)
        self.alignPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.alignPushButton.clicked.connect(self.on_alignPushButton_clicked)

        centralLayout.addWidget(self.scrollArea)
        centralLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal))
        centralLayout.addWidget(self.alignPushButton)
    # endregion

    # region Callback
    def sceneChanged(self):
        """
        Scene changed callback that refreshes the internal guides.

        :rtype: None
        """

        # Clear all previous alignments
        #
        self.clearAlignments()

        # Try and load alignments from scene properties
        #
        states = []

        try:

            states = json.loads(self.scene.properties.get('alignments', '[]'))

        except json.JSONDecodeError as exception:

            log.warning(exception)
            self.scene.properties['alignments'] = '[]'

        finally:

            numStates = len(states)

            if numStates > 0:

                for state in states:

                    alignment = self.addAlignment()
                    alignment.__setstate__(state)

            else:

                self.addAlignment()
    # endregion

    # region Methods
    def loadSettings(self, settings):
        """
        Loads the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        self.sceneChanged()

    def saveSettings(self, settings):
        """
        Saves the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        self.scene.properties['alignments'] = json.dumps([x.__getstate__() for x in self.iterAlignments()])

    def numAlignments(self):
        """
        Evaluates the number of alignments.

        :rtype: int
        """

        return self.scrollAreaContent.layout().count()

    def evaluateNumAlignments(self):
        """
        Evaluates the number of enabled alignments.

        :rtype: int
        """

        return len(self.alignments(skipUnchecked=True))

    def iterAlignments(self, skipUnchecked=False):
        """
        Returns a generator that yields alignment rollouts.

        :type skipUnchecked: bool
        :rtype: iter
        """

        # Iterate through layout items
        #
        layout = self.scrollAreaContent.layout()
        numItems = layout.count()

        for i in range(numItems):

            # Check if widget is still valid
            #
            widget = layout.itemAt(i).widget()

            if not QtCompat.isValid(widget):

                continue

            # Check if un-checked rollouts should be skipped
            #
            if skipUnchecked and not widget.isChecked():

                continue

            else:

                yield widget

    def alignments(self, skipUnchecked=False):
        """
        Returns a list of alignment rollouts.

        :type skipUnchecked: bool
        :rtype: list[QAlignRollout]
        """

        return list(self.iterAlignments(skipUnchecked=skipUnchecked))

    def addAlignment(self):
        """
        Adds a new alignment rollout to the scroll area.

        :rtype: QAlignRollout
        """

        rollout = QAlignRollout('')
        rollout.setCheckable(True)
        rollout.setGrippable(True)
        rollout.addAlignmentAction.triggered.connect(self.on_addAlignmentAction_triggered)
        rollout.removeAlignmentAction.triggered.connect(self.on_removeAlignmentAction_triggered)

        self.scrollAreaContent.layout().addWidget(rollout)

        return rollout

    def clearAlignments(self):
        """
        Removes all the current alignments.

        :rtype: None
        """

        # Remove layout items in reverse
        #
        layout = self.scrollAreaContent.layout()
        numItems = layout.count()

        for i in reversed(range(numItems)):

            item = layout.takeAt(i)
            item.widget().deleteLater()

    @undo.Undo(name='Align Transforms')
    def align(self):
        """
        Executes any active alignments.

        :rtype: None
        """

        # Check if any alignments are enabled
        #
        if self.evaluateNumAlignments() == 0:

            log.warning('No alignments enabled!')
            return

        # Iterate through alignments
        #
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        if modifiers == QtCore.Qt.ShiftModifier:

            for alignment in self.iterAlignments(skipUnchecked=True):

                alignment.apply()

        else:

            for alignment in self.iterAlignments(skipUnchecked=True):

                alignment.applyRange()
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_addAlignmentAction_triggered(self, checked=False):
        """
        Slot method for the addAlignmentAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.addAlignment()

    @QtCore.Slot(bool)
    def on_removeAlignmentAction_triggered(self, checked=False):
        """
        Slot method for the removeAlignmentAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        numAlignments = self.numAlignments()

        if numAlignments > 1:

            rollout = self.sender().parentWidget().parentWidget()
            rollout.deleteLater()

    @QtCore.Slot(bool)
    def on_alignPushButton_clicked(self, checked=False):
        """
        Slot method for the alignPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.align()
    # endregion
