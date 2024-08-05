from Qt import QtCore, QtWidgets, QtGui
from maya.api import OpenMaya as om
from dcc.python import stringutils
from dcc.ui import qtimespinbox, qdivider
from dcc.maya.decorators import undo
from . import qabstracttab
from ...libs import poseutils

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QPlotterTab(qabstracttab.QAbstractTab):
    """
    Overload of `QAbstractTab` that plots keyframes to animation guides.
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
        super(QPlotterTab, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._guides = []

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

        # Initialize guides group-box
        #
        self.guidesLayout = QtWidgets.QGridLayout()
        self.guidesLayout.setObjectName('guidesLayout')

        self.guidesGroupBox = QtWidgets.QGroupBox('Guides:')
        self.guidesGroupBox.setObjectName('guidesGroupBox')
        self.guidesGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.guidesGroupBox.setLayout(self.guidesLayout)

        self.nameLineEdit = QtWidgets.QLineEdit()
        self.nameLineEdit.setObjectName('nameLineEdit')
        self.nameLineEdit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.nameLineEdit.setFixedHeight(24)
        self.nameLineEdit.returnPressed.connect(self.on_nameLineEdit_returnPressed)

        self.guideTreeView = QtWidgets.QTreeView()
        self.guideTreeView.setObjectName('guideTreeView')
        self.guideTreeView.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.guideTreeView.setFocusPolicy(QtCore.Qt.NoFocus)
        self.guideTreeView.setStyleSheet('QTreeView::item { height: 24px; }')
        self.guideTreeView.setAlternatingRowColors(True)
        self.guideTreeView.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.guideTreeView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.guideTreeView.setUniformRowHeights(True)
        self.guideTreeView.setItemsExpandable(True)
        self.guideTreeView.setAnimated(True)
        self.guideTreeView.setHeaderHidden(True)

        self.guideItemModel = QtGui.QStandardItemModel(0, 1, parent=self.guideTreeView)
        self.guideItemModel.setObjectName('guideItemModel')
        self.guideItemModel.setHorizontalHeaderLabels(['Name'])

        self.guideTreeView.setModel(self.guideItemModel)

        self.guideSelectionModel = self.guideTreeView.selectionModel()
        self.guideSelectionModel.selectionChanged.connect(self.on_guideTreeView_selectionChanged)

        self.createGuidePushButton = QtWidgets.QPushButton('Create')
        self.createGuidePushButton.setObjectName('createGuidePushButton')
        self.createGuidePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.createGuidePushButton.setFixedHeight(24)
        self.createGuidePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.createGuidePushButton.clicked.connect(self.on_createGuidePushButton_clicked)

        self.removeGuidePushButton = QtWidgets.QPushButton('Remove')
        self.removeGuidePushButton.setObjectName('removeGuidePushButton')
        self.removeGuidePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.removeGuidePushButton.setFixedHeight(24)
        self.removeGuidePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.removeGuidePushButton.clicked.connect(self.on_removeGuidePushButton_clicked)

        self.importGuidePushButton = QtWidgets.QPushButton('Import')
        self.importGuidePushButton.setObjectName('importGuidePushButton')
        self.importGuidePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.importGuidePushButton.setFixedHeight(24)
        self.importGuidePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.importGuidePushButton.clicked.connect(self.on_importGuidePushButton_clicked)

        self.exportGuidePushButton = QtWidgets.QPushButton('Export')
        self.exportGuidePushButton.setObjectName('exportGuidePushButton')
        self.exportGuidePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.exportGuidePushButton.setFixedHeight(24)
        self.exportGuidePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.exportGuidePushButton.clicked.connect(self.on_exportGuidePushButton_clicked)

        self.guidesLayout.addWidget(self.nameLineEdit, 0, 0, 1, 2)
        self.guidesLayout.addWidget(self.guideTreeView, 1, 0, 1, 2)
        self.guidesLayout.addWidget(self.createGuidePushButton, 2, 0)
        self.guidesLayout.addWidget(self.removeGuidePushButton, 2, 1)
        self.guidesLayout.addWidget(self.importGuidePushButton, 3, 0)
        self.guidesLayout.addWidget(self.exportGuidePushButton, 3, 1)

        centralLayout.addWidget(self.guidesGroupBox)

        # Initialize line-edit actions
        #
        self.guideAction = QtWidgets.QAction(QtGui.QIcon(':/animateSnapshot.png'), '', parent=self.nameLineEdit)
        self.guideAction.setObjectName('guideAction')

        self.removeGuideAction = QtWidgets.QAction(QtGui.QIcon(':/trash.png'), '', parent=self.nameLineEdit)
        self.removeGuideAction.setObjectName('removeGuideAction')
        self.removeGuideAction.triggered.connect(self.on_removeGuideAction_triggered)

        self.selectGuideAction = QtWidgets.QAction(QtGui.QIcon(':/aselect.png'), '', parent=self.nameLineEdit)
        self.selectGuideAction.setObjectName('selectGuideAction')
        self.selectGuideAction.triggered.connect(self.on_selectGuideAction_triggered)

        self.nameLineEdit.addAction(self.guideAction, QtWidgets.QLineEdit.LeadingPosition)
        self.nameLineEdit.addAction(self.removeGuideAction, QtWidgets.QLineEdit.TrailingPosition)
        self.nameLineEdit.addAction(self.selectGuideAction, QtWidgets.QLineEdit.TrailingPosition)

        # Initialize animation-range widgets
        #
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
        self.startTimeSpinBox.setEnabled(False)

        self.startTimeCheckBox = QtWidgets.QCheckBox('')
        self.startTimeCheckBox.setObjectName('startTimeCheckBox')
        self.startTimeCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.startTimeCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.startTimeCheckBox.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.startTimeCheckBox.toggled.connect(self.startTimeSpinBox.setEnabled)

        self.startTimeLayout.addWidget(self.startTimeLabel)
        self.startTimeLayout.addWidget(self.startTimeCheckBox)
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
        self.endTimeSpinBox.setEnabled(False)

        self.endTimeCheckBox = QtWidgets.QCheckBox('')
        self.endTimeCheckBox.setObjectName('endTimeCheckBox')
        self.endTimeCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.endTimeCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.endTimeCheckBox.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.endTimeCheckBox.toggled.connect(self.endTimeSpinBox.setEnabled)

        self.endTimeLayout.addWidget(self.endTimeLabel)
        self.endTimeLayout.addWidget(self.endTimeCheckBox)
        self.endTimeLayout.addWidget(self.endTimeSpinBox)

        # Initialize keyframe option widgets
        #
        self.stepLayout = QtWidgets.QHBoxLayout()
        self.stepLayout.setObjectName('stepLayout')
        self.stepLayout.setContentsMargins(0, 0, 0, 0)

        self.stepWidget = QtWidgets.QWidget()
        self.stepWidget.setObjectName('stepWidget')
        self.stepWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.stepWidget.setFixedHeight(24)
        self.stepWidget.setLayout(self.stepLayout)

        self.stepLabel = QtWidgets.QLabel('Step:')
        self.stepLabel.setObjectName('stepLabel')
        self.stepLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.stepLabel.setFixedWidth(32)
        self.stepLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.stepSpinBox = qtimespinbox.QTimeSpinBox()
        self.stepSpinBox.setObjectName('stepSpinBox')
        self.stepSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.stepSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.stepSpinBox.setToolTip('The step interval to bake transforms to.')
        self.stepSpinBox.setMinimum(1)
        self.stepSpinBox.setMaximum(100)
        self.stepSpinBox.setValue(1)
        self.stepSpinBox.setEnabled(False)

        self.stepCheckBox = QtWidgets.QCheckBox('')
        self.stepCheckBox.setObjectName('stepCheckBox')
        self.stepCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.stepCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.stepCheckBox.toggled.connect(self.stepSpinBox.setEnabled)

        self.stepLayout.addWidget(self.stepLabel)
        self.stepLayout.addWidget(self.stepCheckBox)
        self.stepLayout.addWidget(self.stepSpinBox)

        self.snapKeysCheckBox = QtWidgets.QCheckBox('Snap Keys to Nearest Frame')
        self.snapKeysCheckBox.setObjectName('snapKeysCheckBox')
        self.snapKeysCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.snapKeysCheckBox.setFixedHeight(24)
        self.snapKeysCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.snapKeysCheckBox.setEnabled(False)

        self.bakeKeysRadioButton = QtWidgets.QRadioButton('Bake Keys')
        self.bakeKeysRadioButton.setObjectName('bakeKeysRadioButton')
        self.bakeKeysRadioButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.bakeKeysRadioButton.setFixedHeight(24)
        self.bakeKeysRadioButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.bakeKeysRadioButton.setChecked(True)
        self.bakeKeysRadioButton.toggled.connect(self.stepWidget.setEnabled)

        self.preserveKeysRadioButton = QtWidgets.QRadioButton('Preserve Keys')
        self.preserveKeysRadioButton.setObjectName('preserveKeysRadioButton')
        self.preserveKeysRadioButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.preserveKeysRadioButton.setFixedHeight(24)
        self.preserveKeysRadioButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.preserveKeysRadioButton.toggled.connect(self.snapKeysCheckBox.setEnabled)

        self.plotButtonGroup = QtWidgets.QButtonGroup(parent=self)
        self.plotButtonGroup.addButton(self.bakeKeysRadioButton, id=0)
        self.plotButtonGroup.addButton(self.preserveKeysRadioButton, id=1)

        # Initialize align widgets
        #
        self.alignLayout = QtWidgets.QHBoxLayout()
        self.alignLayout.setObjectName('alignLayout')
        self.alignLayout.setContentsMargins(0, 0, 0, 0)

        self.alignWidget = QtWidgets.QWidget()
        self.alignWidget.setObjectName('alignWidget')
        self.alignWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.alignWidget.setFixedHeight(24)
        self.alignWidget.setLayout(self.alignLayout)
        
        self.alignLabel = QtWidgets.QLabel('Align:')
        self.alignLabel.setObjectName('alignLabel')
        self.alignLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.alignLabel.setFixedWidth(32)
        self.alignLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        
        self.alignTranslateCheckBox = QtWidgets.QCheckBox('Translate')
        self.alignTranslateCheckBox.setObjectName('alignTranslateCheckBox')
        self.alignTranslateCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.alignTranslateCheckBox.setFixedHeight(24)
        self.alignTranslateCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.alignTranslateCheckBox.setChecked(True)

        self.alignRotateCheckBox = QtWidgets.QCheckBox('Rotate')
        self.alignRotateCheckBox.setObjectName('alignRotateCheckBox')
        self.alignRotateCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.alignRotateCheckBox.setFixedHeight(24)
        self.alignRotateCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.alignRotateCheckBox.setChecked(True)

        self.alignScaleCheckBox = QtWidgets.QCheckBox('Scale')
        self.alignScaleCheckBox.setObjectName('alignScaleCheckBox')
        self.alignScaleCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.alignScaleCheckBox.setFixedHeight(24)
        self.alignScaleCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)

        self.alignButtonGroup = QtWidgets.QButtonGroup(parent=self)
        self.alignButtonGroup.setObjectName('alignButtonGroup')
        self.alignButtonGroup.setExclusive(False)
        self.alignButtonGroup.addButton(self.alignTranslateCheckBox, id=0)
        self.alignButtonGroup.addButton(self.alignRotateCheckBox, id=1)
        self.alignButtonGroup.addButton(self.alignScaleCheckBox, id=2)

        self.alignLayout.addWidget(self.alignLabel)
        self.alignLayout.addWidget(self.alignTranslateCheckBox, alignment=QtCore.Qt.AlignCenter)
        self.alignLayout.addWidget(self.alignRotateCheckBox, alignment=QtCore.Qt.AlignCenter)
        self.alignLayout.addWidget(self.alignScaleCheckBox, alignment=QtCore.Qt.AlignCenter)

        # Initialize settings group-box
        #
        self.settingsLayout = QtWidgets.QGridLayout()
        self.settingsLayout.setObjectName('settingsLayout')

        self.settingsGroupBox = QtWidgets.QGroupBox('Settings:')
        self.settingsGroupBox.setObjectName('settingsGroupBox')
        self.settingsGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.settingsGroupBox.setLayout(self.settingsLayout)

        self.settingsLayout.addWidget(self.startTimeWidget, 0, 0)
        self.settingsLayout.addWidget(self.endTimeWidget, 0, 2)
        self.settingsLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal), 1, 0, 1, 3)
        self.settingsLayout.addWidget(self.bakeKeysRadioButton, 2, 0)
        self.settingsLayout.addWidget(self.preserveKeysRadioButton, 3, 0)
        self.settingsLayout.addWidget(qdivider.QDivider(QtCore.Qt.Vertical), 2, 1, 2, 1)
        self.settingsLayout.addWidget(self.stepWidget, 2, 2)
        self.settingsLayout.addWidget(self.snapKeysCheckBox, 3, 2)
        self.settingsLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal), 4, 0, 1, 3)
        self.settingsLayout.addWidget(self.alignWidget, 5, 0, 1, 3)

        centralLayout.addWidget(self.settingsGroupBox)

        # Initialize plot button
        #
        self.plotGuidePushButton = QtWidgets.QPushButton('Plot')
        self.plotGuidePushButton.setObjectName('plotGuidePushButton')
        self.plotGuidePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.plotGuidePushButton.setFixedHeight(48)
        self.plotGuidePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.plotGuidePushButton.clicked.connect(self.on_plotGuidePushButton_clicked)

        centralLayout.addWidget(self.plotGuidePushButton)
    # endregion

    # region Properties
    @property
    def guides(self):
        """
        Getter method that returns the active guides.

        :rtype: List[pose.Pose]
        """

        return self._guides

    @guides.setter
    def guides(self, guides):
        """
        Setter method that updates the active guides.

        :rtype: List[pose.Pose]
        """

        self._guides.clear()
        self._guides.extend(guides)

        self.synchronize()
    # endregion

    # region Callback
    def sceneChanged(self, *args, clientData=None):
        """
        Scene changed callback that refreshes the internal guides.

        :type clientData: Any
        :rtype: None
        """

        # Load anim-guides from file properties
        #
        self.guides = poseutils.loadPose(self.scene.properties.get('animGuides', default='[]'))

        # Invalidate animation-range
        #
        startTimeEnabled = self.startTimeCheckBox.isChecked()

        if not startTimeEnabled:

            self.startTimeSpinBox.setValue(self.scene.startTime)

        endTimeEnabled = self.endTimeCheckBox.isChecked()

        if not endTimeEnabled:

            self.endTimeSpinBox.setValue(self.scene.endTime)
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
        super(QPlotterTab, self).loadSettings(settings)

        # Load user preferences
        #
        self.setPlotOption(settings.value('tabs/plotter/plotOption', defaultValue=0, type=int))
        self.setSnapKeys(bool(settings.value('tabs/plotter/snapKeys', defaultValue=0, type=int)))
        self.setStep(settings.value('tabs/plotter/step', defaultValue=1, type=int))
        self.setStepEnabled(bool(settings.value('tabs/plotter/stepEnabled', defaultValue=1, type=int)))

        # Load animation range
        #
        startTimeEnabled = bool(settings.value('tabs/plotter/startTimeEnabled', defaultValue=0, type=int))
        self.startTimeCheckBox.setChecked(startTimeEnabled)

        if startTimeEnabled:

            startTime = settings.value('tabs/plotter/startTime', defaultValue=self.scene.startTime, type=int)
            self.startTimeSpinBox.setValue(startTime)

        endTimeEnabled = bool(settings.value('tabs/plotter/endTimeEnabled', defaultValue=0, type=int))
        self.endTimeCheckBox.setChecked(endTimeEnabled)

        if endTimeEnabled:

            endTime = settings.value('tabs/plotter/endTime', defaultValue=self.scene.endTime, type=int)
            self.endTimeSpinBox.setValue(endTime)

        # Invalidate internal guides
        #
        self.sceneChanged()

    def saveSettings(self, settings):
        """
        Saves the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QPlotterTab, self).saveSettings(settings)

        # Save user preferences
        #
        settings.setValue('tabs/plotter/plotOption', int(self.plotOption()))
        settings.setValue('tabs/plotter/snapKeys', int(self.snapKeys()))
        settings.setValue('tabs/plotter/step', int(self.step()))
        settings.setValue('tabs/plotter/stepEnabled', int(self.stepEnabled()))

        startTime, startTimeEnabled = self.startTimeSpinBox.value(), self.startTimeCheckBox.isChecked()
        settings.setValue('tabs/plotter/startTime', int(startTime))
        settings.setValue('tabs/plotter/startTimeEnabled', int(startTimeEnabled))

        endTime, endTimeEnabled = self.endTimeSpinBox.value(), self.endTimeCheckBox.isChecked()
        settings.setValue('tabs/plotter/endTime', int(endTime))
        settings.setValue('tabs/plotter/endTimeEnabled', int(endTimeEnabled))

        # Save animation guides to scene properties
        #
        self.scene.properties['animGuides'] = poseutils.dumpPose(self.guides)

    def alignOptions(self):
        """
        Returns the transform options.

        :rtype: Tuple[bool, bool, bool]
        """

        return [button.isChecked() for button in self.alignButtonGroup.buttons()]

    def setAlignOptions(self, options):
        """
        Updates the transform options.

        :type options: Tuple[bool, bool, bool]
        :rtype: None
        """

        for (i, button) in enumerate(self.alignButtonGroup.buttons()):

            button.setChecked(options[i])

    def plotOption(self):
        """
        Returns the current keyframe option.

        :rtype: int
        """

        return self.plotButtonGroup.checkedId()

    def setPlotOption(self, option):
        """
        Updates the current keyframe option.

        :type option: int
        :rtype: None
        """

        self.plotButtonGroup.buttons()[option].setChecked(True)

    def snapKeys(self):
        """
        Returns the snap-frame state.

        :rtype: bool
        """

        return self.snapKeysCheckBox.isChecked()

    def setSnapKeys(self, state):
        """
        Updates the snap-frame state.

        :type state: bool
        :rtype: None
        """

        self.snapKeysCheckBox.setChecked(state)

    def step(self):
        """
        Returns the step interval.

        :rtype: int
        """

        return self.stepSpinBox.value()

    def setStep(self, interval):
        """
        Updates the step interval.

        :type interval: int
        :rtype: None
        """

        self.stepSpinBox.setValue(interval)

    def stepEnabled(self):
        """
        Returns the enabled state for frame steps.

        :rtype: bool
        """

        return self.stepCheckBox.isChecked()

    def setStepEnabled(self, enabled):
        """
        Updates the enabled state for frame steps.

        :type enabled: bool
        :rtype: None
        """

        self.stepCheckBox.setChecked(enabled)

    def animationRange(self):
        """
        Returns the current animation range.

        :rtype: Tuple[int, int]
        """

        startTime = self.startTimeSpinBox.value() if self.startTimeCheckBox.isChecked() else self.scene.startTime
        endTime = self.endTimeSpinBox.value() if self.endTimeCheckBox.isChecked() else self.scene.endTime

        return startTime, endTime

    def setAnimationRange(self, animationRange):
        """
        Updates the current animation range.

        :type animationRange: Tuple[int, int]
        :rtype: None
        """

        startTime, endTime = animationRange

        self.startTimeSpinBox.setValue(startTime)
        self.endTimeSpinBox.setValue(endTime)

    def isNameUnique(self, name):
        """
        Evaluates if the supplied guide name is unique.

        :type name: str
        :rtype: bool
        """

        return not any([guide.name == name for guide in self._guides])

    def createUniqueName(self):
        """
        Returns a unique guide name.

        :rtype: str
        """

        name = 'AnimGuide01'
        index = 1

        while not self.isNameUnique(name):

            index += 1
            name = 'AnimGuide{index}'.format(index=str(index).zfill(2))

        return name

    def getSelectedIndex(self, topLevel=False):
        """
        Returns the active selection index.

        :type topLevel: bool
        :rtype: QtCore.QModelIndex
        """

        # Evaluate model selection
        #
        selectedIndices = self.guideTreeView.selectedIndexes()
        numSelectedIndices = len(selectedIndices)

        if numSelectedIndices != 1:

            return QtCore.QModelIndex()

        # Check if top-level index is required
        #
        index = selectedIndices[0]
        parentIndex = index.parent()

        if topLevel and parentIndex.isValid():

            return parentIndex

        else:

            return index

    def hasSelection(self):
        """
        Evaluates if there is a valid selection.

        :rtype: bool
        """

        return self.getSelectedIndex().isValid()

    def getSelectedGuide(self, asModelItem=False):
        """
        Returns the current selected guide.

        :type asModelItem: bool
        :rtype: pose.Pose
        """

        # Evaluate model selection
        #
        selectedIndex = self.getSelectedIndex(topLevel=True)

        if not selectedIndex.isValid():

            return None

        # Check if the model item should be returned
        #
        if asModelItem:

            return self.guideItemModel.itemFromIndex(selectedIndex)

        else:

            return self.guides[selectedIndex.row()]

    @undo.Undo(name='Plot Transforms')
    def plot(self):
        """
        Plots the active selection to the selected guide.

        :rtype: None
        """

        # Get selected guide
        #
        guide = self.getSelectedGuide()

        if guide is None:

            log.warning('No guide selected to plot to!')
            return

        # Get selected nodes
        #
        selection = sorted(self.scene.selection(apiType=om.MFn.kTransform), key=self.getSortPriority)
        selectionCount = len(selection)

        if selectionCount == 0:

            log.warning('No nodes selected to plot to!')
            return

        # Check which operation to perform
        #
        option = self.plotOption()
        animationRange = self.animationRange()
        step = self.step() if self.stepEnabled() else 1
        preserveKeys = (option == 1)
        snapKeys = self.snapKeys()
        translateEnabled, rotateEnabled, scaleEnabled = self.alignOptions()

        guide.bakeTransformationsTo(
            *selection,
            animationRange=animationRange,
            step=step,
            snapKeys=snapKeys,
            preserveKeys=preserveKeys,
            skipTranslate=(not translateEnabled),
            skipRotate=(not rotateEnabled),
            skipScale=(not scaleEnabled)
        )
    
    @undo.Undo(state=False)
    def synchronize(self):
        """
        Synchronizes the tree view items with the internal guide objects.

        :rtype: None
        """

        # Update row count
        #
        numGuides = len(self.guides)
        self.guideItemModel.setRowCount(numGuides)

        # Iterate through guides
        #
        for (i, guide) in enumerate(self.guides):

            # Update guide name
            #
            index = self.guideItemModel.index(i, 0)

            guideItem = self.guideItemModel.itemFromIndex(index)
            guideItem.setIcon(QtGui.QIcon(':/animateSnapshot.png'))
            guideItem.setText(guide.name)
            guideItem.setEditable(False)

            # Iterate through nodes
            #
            numNodes = len(guide.nodes)
            guideItem.setRowCount(numNodes)

            for (j, node) in enumerate(guide.nodes):

                nodeItem = QtGui.QStandardItem(QtGui.QIcon(':/transform.svg'), node.name)
                nodeItem.setEditable(False)

                guideItem.setChild(j, nodeItem)
    # endregion

    # region Slots
    @QtCore.Slot()
    def on_nameLineEdit_returnPressed(self):
        """
        Slot method for the nameLineEdit's `editingFinished` signal.

        :rtype: None
        """

        guide = self.getSelectedGuide()
        sender = self.sender()
        
        if guide is not None:

            guide.name = self.nameLineEdit.text()
            self.synchronize()

        sender.clearFocus()

    @QtCore.Slot(bool)
    def on_selectGuideAction_triggered(self, checked=False):
        """
        Slot method for the selectGuidePushButton's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        guide = self.getSelectedGuide()

        if guide is not None:

            guide.selectAssociatedNodes(namespace=self.currentNamespace())

        else:

            log.warning('No guide selected!')

    @QtCore.Slot(bool)
    def on_removeGuideAction_triggered(self, checked=False):
        """
        Slot method for the removeGuideAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected guide
        #
        guide = self.getSelectedGuide()

        if guide is None:

            log.warning('No guide selected to delete!')
            return

        # Confirm user wants to delete guide
        #
        response = QtWidgets.QMessageBox.warning(
            self,
            'Delete Guide',
            'Are you sure you want to delete this guide?',
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if response == QtWidgets.QMessageBox.Ok:

            index = self.guides.index(guide)
            del self.guides[index]

            self.synchronize()

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def on_guideTreeView_selectionChanged(self, selected, deselected):
        """
        Slot method for the guideTreeView's `selectionChanged` signal.

        :type selected: QtCore.QItemSelection
        :type deselected: QtCore.QItemSelection
        :rtype: None
        """

        guide = self.getSelectedGuide()

        if guide is not None:

            self.nameLineEdit.setText(guide.name)

        else:

            self.nameLineEdit.setText('')

    @QtCore.Slot(bool)
    def on_createGuidePushButton_clicked(self, checked=False):
        """
        Slot method for the createGuidePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Check if a custom name was entered
        #
        name = self.nameLineEdit.text()

        if not self.isNameUnique(name) or stringutils.isNullOrEmpty(name):

            name = self.createUniqueName()

        # Create new pose and synchronize
        #
        selection = sorted(self.scene.selection(apiType=om.MFn.kTransform), key=self.getSortPriority)

        pose = poseutils.createPose(
            *selection,
            name=name,
            animationRange=self.scene.animationRange,
            skipKeys=False,
            skipTransformations=False
        )

        self.guides.append(pose)
        self.synchronize()

    @QtCore.Slot(bool)
    def on_removeGuidePushButton_clicked(self, checked=False):
        """
        Slot method for the removeGuidePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        guide = self.getSelectedGuide()

        if guide is not None:

            index = self.guides.index(guide)
            del self.guides[index]

            self.synchronize()

        else:

            log.warning('No guide selected to remove!')

    @QtCore.Slot(bool)
    def on_importGuidePushButton_clicked(self, checked=False):
        """
        Slot method for the importGuidePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for import path
        #
        importPath, selectedFilter = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption='Import From',
            dir=self.scene.directory,
            filter='Guide files (*.guide)'
        )

        # Check if path is valid
        #
        if not stringutils.isNullOrEmpty(importPath):

            guide = poseutils.importPose(importPath)
            self.guides.append(guide)

            self.synchronize()

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_exportGuidePushButton_clicked(self, checked=False):
        """
        Slot method for the exportGuidePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected guide
        #
        guide = self.getSelectedGuide()

        if guide is None:

            log.warning('No guide selected to export!')
            return

        # Prompt user for export path
        #
        exportPath, selectedFilter = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Export To',
            dir=self.scene.directory,
            filter='Guide files (*.guide)'
        )

        # Check if path is valid
        #
        if not stringutils.isNullOrEmpty(exportPath):

            poseutils.exportPose(exportPath, guide, indent=4)

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_plotGuidePushButton_clicked(self, checked=False):
        """
        Slot method for the plotGuidePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.plot()
    # endregion
