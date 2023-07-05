import json

from maya.api import OpenMaya as om
from mpy import mpyfactory
from Qt import QtCore, QtWidgets, QtGui, QtCompat
from dcc.ui import qrollout, qdivider, qtimespinbox, qxyzwidget, qseparator
from dcc.python import stringutils
from dcc.maya.libs import dagutils
from dcc.maya.decorators.undo import undo
from . import qabstracttab

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QAlignRollout(qrollout.QRollout):
    """
    Overload of QRollout used to align transforms over time.
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
        self._scene = mpyfactory.MPyFactory.getInstance(asWeakReference=True)
        self._sourceNode = None
        self._targetNode = None

        # Build user interface
        #
        self.__build__()

    def __build__(self, *args, **kwargs):
        """
        Private method that builds the user interface.

        :rtype: None
        """

        # Assign vertical layout
        #
        self.centralLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.centralLayout)

        # Create node widgets
        #
        self.sourcePushButton = QtWidgets.QPushButton('Parent')
        self.sourcePushButton.setObjectName('sourcePushButton')
        self.sourcePushButton.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        self.sourcePushButton.setFixedHeight(20)
        self.sourcePushButton.setMinimumWidth(48)
        self.sourcePushButton.setToolTip('Picks the node to align to.')
        self.sourcePushButton.clicked.connect(self.on_sourcePushButton_clicked)

        self.switchPushButton = QtWidgets.QPushButton(QtGui.QIcon(':dcc/icons/switch'), '')
        self.switchPushButton.setObjectName('switchPushButton')
        self.switchPushButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.switchPushButton.setFixedSize(QtCore.QSize(20, 20))
        self.switchPushButton.clicked.connect(self.on_switchPushButton_clicked)

        self.targetPushButton = QtWidgets.QPushButton('Child')
        self.targetPushButton.setObjectName('targetPushButton')
        self.targetPushButton.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        self.targetPushButton.setFixedHeight(20)
        self.targetPushButton.setMinimumWidth(48)
        self.targetPushButton.setToolTip('Picks the node to be aligned.')
        self.targetPushButton.clicked.connect(self.on_targetPushButton_clicked)

        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonLayout.setObjectName('buttonLayout')
        self.buttonLayout.addWidget(self.sourcePushButton)
        self.buttonLayout.addWidget(self.switchPushButton)
        self.buttonLayout.addWidget(self.targetPushButton)

        self.centralLayout.addLayout(self.buttonLayout)
        self.centralLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal))

        # Create time range widgets
        #
        self.startCheckBox = QtWidgets.QCheckBox('')
        self.startCheckBox.setObjectName('startCheckBox')
        self.startCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.startCheckBox.setFixedHeight(20)
        self.startCheckBox.setChecked(True)
        self.startCheckBox.stateChanged.connect(self.on_startCheckBox_stateChanged)

        self.startSpinBox = qtimespinbox.QTimeSpinBox()
        self.startSpinBox.setObjectName('startSpinBox')
        self.startSpinBox.setPrefix('Start: ')
        self.startSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.startSpinBox.setFixedHeight(20)
        self.startSpinBox.setMinimumWidth(20)
        self.startSpinBox.setDefaultType(qtimespinbox.DefaultType.StartTime)
        self.startSpinBox.setRange(-9999, 9999)
        self.startSpinBox.setValue(0)

        self.endCheckBox = QtWidgets.QCheckBox('')
        self.endCheckBox.setObjectName('endCheckBox')
        self.endCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.endCheckBox.setFixedHeight(20)
        self.endCheckBox.setChecked(True)
        self.endCheckBox.stateChanged.connect(self.on_endCheckBox_stateChanged)

        self.endSpinBox = qtimespinbox.QTimeSpinBox()
        self.endSpinBox.setObjectName('endSpinBox')
        self.endSpinBox.setPrefix('End: ')
        self.endSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.endSpinBox.setFixedHeight(20)
        self.endSpinBox.setMinimumWidth(20)
        self.endSpinBox.setDefaultType(qtimespinbox.DefaultType.EndTime)
        self.endSpinBox.setRange(-9999, 9999)
        self.endSpinBox.setValue(1)

        self.stepSpinBox = QtWidgets.QSpinBox()
        self.stepSpinBox.setObjectName('stepSpinBox')
        self.stepSpinBox.setPrefix('Step: ')
        self.stepSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.stepSpinBox.setFixedHeight(20)
        self.stepSpinBox.setMinimumWidth(20)
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

        self.centralLayout.addLayout(self.timeRangeLayout)
        self.centralLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal))

        # Create match transform widgets
        #
        self.matchTranslateWidget = qxyzwidget.QXyzWidget('Pos')
        self.matchTranslateWidget.setObjectName('matchTranslateWidget')
        self.matchTranslateWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.matchTranslateWidget.setFixedHeight(20)
        self.matchTranslateWidget.setToolTip('Specify which translate axes should be aligned.')
        self.matchTranslateWidget.setMatches([True, True, True])

        self.matchRotateWidget = qxyzwidget.QXyzWidget('Rot')
        self.matchRotateWidget.setObjectName('matchRotateWidget')
        self.matchRotateWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.matchRotateWidget.setFixedHeight(20)
        self.matchRotateWidget.setToolTip('Specify which rotate axes should be aligned.')
        self.matchRotateWidget.setMatches([True, True, True])

        self.matchScaleWidget = qxyzwidget.QXyzWidget('Scale')
        self.matchScaleWidget.setObjectName('matchScaleWidget')
        self.matchScaleWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.matchScaleWidget.setFixedHeight(20)
        self.matchScaleWidget.setToolTip('Specify which scale axes should be aligned.')
        self.matchScaleWidget.setMatches([False, False, False])

        self.matchLayout = QtWidgets.QHBoxLayout()
        self.matchLayout.setObjectName('matchLayout')
        self.matchLayout.setContentsMargins(0, 0, 0, 0)
        self.matchLayout.addWidget(self.matchTranslateWidget)
        self.matchLayout.addWidget(self.matchRotateWidget)
        self.matchLayout.addWidget(self.matchScaleWidget)

        self.centralLayout.addLayout(self.matchLayout)
        self.centralLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal))

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

        self.maintainRotateCheckBox = QtWidgets.QCheckBox('Rotation')
        self.maintainRotateCheckBox.setObjectName('maintainRotateCheckBox')
        self.maintainRotateCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.maintainRotateCheckBox.setFixedHeight(20)

        self.maintainScaleCheckBox = QtWidgets.QCheckBox('Scale')
        self.maintainScaleCheckBox.setObjectName('maintainScaleCheckBox')
        self.maintainScaleCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.maintainScaleCheckBox.setFixedHeight(20)

        self.maintainLayout = QtWidgets.QHBoxLayout()
        self.maintainLayout.setObjectName('maintainLayout')
        self.maintainLayout.addWidget(self.maintainLabel)
        self.maintainLayout.addWidget(self.maintainTranslateCheckBox)
        self.maintainLayout.addWidget(self.maintainRotateCheckBox)
        self.maintainLayout.addWidget(self.maintainScaleCheckBox)

        self.centralLayout.addLayout(self.maintainLayout)

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
            'matchTranslate': self.matchTranslate,
            'matchRotate': self.matchRotate,
            'matchScale': self.matchScale,
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
        self.matchTranslate = state.get('matchTranslate', [True, True, True])
        self.matchRotate = state.get('matchRotate', [True, True, True])
        self.matchScale = state.get('matchScale', [False, False, False])
        self.maintainTranslate = (state.get('maintainTranslate', False))
        self.maintainRotate = (state.get('maintainRotate', False))
        self.maintainScale = (state.get('maintainScale', False))
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
    def matchTranslate(self):
        """
        Getter method that returns the match translate flag.

        :rtype: List[bool, bool, bool]
        """

        return self.matchTranslateWidget.matches()

    @matchTranslate.setter
    def matchTranslate(self, matchTranslate):
        """
        Setter method that updates the match translate flag.

        :rtype: List[bool, bool, bool]
        """

        self.matchTranslateWidget.setMatches(matchTranslate)

    @property
    def matchRotate(self):
        """
        Getter method that returns the match rotate flag.

        :rtype: List[bool, bool, bool]
        """

        return self.matchRotateWidget.matches()

    @matchRotate.setter
    def matchRotate(self, matchRotate):
        """
        Setter method that updates the match rotate flag.

        :rtype: List[bool, bool, bool]
        """

        self.matchRotateWidget.setMatches(matchRotate)

    @property
    def matchScale(self):
        """
        Getter method that returns the match scale flag.

        :rtype: List[bool, bool, bool]
        """

        return self.matchScaleWidget.matches()

    @matchScale.setter
    def matchScale(self, matchScale):
        """
        Setter method that updates the match scale flag.

        :rtype: List[bool, bool, bool]
        """

        self.matchScaleWidget.setMatches(matchScale)

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

        :rtype: bool
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

        :rtype: bool
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

        :rtype: bool
        """

        self.maintainScaleCheckBox.setChecked(maintainScale)
    # endregion

    # region Methods
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
        Aligns the target node to the source node over the specified amount of time.

        :rtype: None
        """

        # Initialize source interface
        #
        isSourceValid = self.scene.doesNodeExist(self.sourceName)

        if not isSourceValid:

            log.warning('Unable to locate parent node: %s!' % self.sourceName)
            return

        # Initialize target interface
        #
        isTargetValid = self.scene.doesNodeExist(self.targetName)

        if not isTargetValid:

            log.warning('Unable to locate child node: %s!' % self.sourceName)
            return

        # Collect skip flags
        #
        skipTranslateX, skipTranslateY, skipTranslateZ = (not x for x in self.matchTranslate)
        skipRotateX, skipRotateY, skipRotateZ = (not x for x in self.matchRotate)
        skipScaleX, skipScaleY, skipScaleZ = (not x for x in self.matchScale)

        # Iterate through time range
        #
        sourceNode = self.scene(self.sourceName)
        targetNode = self.scene(self.targetName)

        targetNode.alignTransformTo(
            sourceNode,
            startTime=self.startTime, endTime=self.endTime, step=self.step,
            maintainTranslate=self.maintainTranslate, maintainRotate=self.maintainRotate, maintainScale=self.maintainScale,
            skipTranslateX=skipTranslateX, skipTranslateY=skipTranslateY, skipTranslateZ=skipTranslateZ,
            skipRotateX=skipRotateX, skipRotateY=skipRotateY, skipRotateZ=skipRotateZ,
            skipScaleX=skipScaleX, skipScaleY=skipScaleY, skipScaleZ=skipScaleZ
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
    Overload of `QAbstractTab` that aligns controls over a time duration.
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
        super(QAlignTab, self).__init__(*args, **kwargs)

        # Declare public variables
        #
        self.alignPushButton = None
        self.scrollArea = None
        self.scrollAreaContents = None
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

        # Load alignment states
        # If there aren't any then create a default alignment
        #
        states = json.loads(self.scene.properties.get('alignments', '[]'))
        numStates = len(states)

        if numStates > 0:

            for state in states:

                alignment = self.addAlignment()
                alignment.__setstate__(state)

        else:

            self.addAlignment()
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QAlignTab, self).postLoad(*args, **kwargs)

        # Initialize scroll area layout
        #
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scrollAreaContents.setLayout(layout)

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

        return self.scrollAreaContents.layout().count()

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
        layout = self.scrollAreaContents.layout()
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

        self.scrollAreaContents.layout().addWidget(rollout)

        return rollout

    def clearAlignments(self):
        """
        Removes all the current alignments.

        :rtype: None
        """

        # Remove layout items in reverse
        #
        layout = self.scrollAreaContents.layout()
        numItems = layout.count()

        for i in reversed(range(numItems)):

            item = layout.takeAt(i)
            item.widget().deleteLater()

    @undo(name='Align Transforms')
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
        for alignment in self.iterAlignments(skipUnchecked=True):

            alignment.apply()
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
