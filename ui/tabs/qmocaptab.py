import os

from maya.api import OpenMaya as om
from Qt import QtCore, QtWidgets, QtGui
from dcc.python import stringutils
from dcc.maya.libs import sceneutils
from . import qabstracttab
from ...libs import retargeter, retargetutils

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QMocapTab(qabstracttab.QAbstractTab):
    """
    Overload of `QAbstractTab` that interfaces with motion capture data.
    """

    # region Dunderscores
    __source__ = 'MocapRN'
    __namespace__ = 'Mocap'

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QWidget
        :key flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QMocapTab, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._source = None
        self._targets = []
        self._binders = self.loadBinders()

        # Declare public variables
        #
        self.sourceGroupBox = None
        self.sourceDescriptionLabel = None
        self.sourcePathWidget = None
        self.sourcePathLineEdit = None
        self.sourcePathPushButton = None
        self.sourceInteropWidget = None
        self.loadSourcePushButton = None
        self.unloadSourcePushButton = None
        self.sourceButtonGroup = None

        self.targetGroupBox = None
        self.targetDescriptionLabel = None
        self.targetWidget = None
        self.targetComboBox = None
        self.targetLabel = None
        self.binderWidget = None
        self.binderComboBox = None
        self.binderLabel = None
        self.stepWidget = None
        self.stepLabel = None
        self.startTimeSpinBox = None
        self.endTimeSpinBox = None
        self.stepSpinBox = None
        self.kinematicWidget = None
        self.kinematicLabel = None
        self.fkRadioButton = None
        self.ikRadioButton = None
        self.bothRadioButton = None
        self.kinematicButtonGroup = None

        self.batchRollout = None
        self.fileDividerWidget = None
        self.fileDividerLabel = None
        self.fileDividerLine = None
        self.fileInteropWidget = None
        self.addFilesPushButton = None
        self.removeFilesPushButton = None
        self.fileListWidget = None
        self.batchTargetWidget = None
        self.batchTargetLabel = None
        self.batchTargetLineEdit = None
        self.batchTargetPushButton = None
        self.batchPathWidget = None
        self.batchPathLabel = None
        self.batchPathLineEdit = None
        self.batchPathPushButton = None
        self.batchProgressBar = None
        self.batchPushButton = None

        self.retargetPushButton = None
    # endregion

    # region Callbacks
    def sceneChanged(self):
        """
        Callback method that notifies the tab of a scene change.

        :rtype: None
        """

        self.invalidateSource()
        self.invalidateTargets()
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QMocapTab, self).postLoad(*args, **kwargs)

        # Edit rollouts
        #
        self.batchRollout.setText('Batch')
        self.batchRollout.setExpanded(False)

        self.layout().setAlignment(QtCore.Qt.AlignTop)

        # Update binder combo-box
        #
        names = [binder.name for binder in self._binders]
        self.binderComboBox.addItems(names)

        # Update animation range spin boxes
        #
        self.startTimeSpinBox.setDefaultType(self.startTimeSpinBox.DefaultType.StartTime)
        self.startTimeSpinBox.setValue(self.scene.startTime)

        self.endTimeSpinBox.setDefaultType(self.startTimeSpinBox.DefaultType.EndTime)
        self.endTimeSpinBox.setValue(self.scene.endTime)

        # Update button group IDs
        #
        self.sourceButtonGroup = QtWidgets.QButtonGroup(parent=self.sourceGroupBox)
        self.sourceButtonGroup.addButton(self.unloadSourcePushButton, id=0)
        self.sourceButtonGroup.addButton(self.loadSourcePushButton, id=1)

        self.kinematicButtonGroup = QtWidgets.QButtonGroup(parent=self.sourceGroupBox)
        self.kinematicButtonGroup.addButton(self.fkRadioButton, id=0)
        self.kinematicButtonGroup.addButton(self.ikRadioButton, id=1)
        self.kinematicButtonGroup.addButton(self.bothRadioButton, id=2)

        # Force scene changed callback
        #
        self.sceneChanged()

    def loadSettings(self, settings):
        """
        Loads the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QMocapTab, self).loadSettings(settings)

        # Load user preferences
        #
        self.setKinematicMode(settings.value('tabs/mocap/kinematicMode', defaultValue=2))
        self.setStepInterval(settings.value('tabs/mocap/stepInterval', defaultValue=1))

        startTime = settings.value('tabs/mocap/startTime', defaultValue=self.scene.startTime)
        endTime = settings.value('tabs/mocap/endTime', defaultValue=self.scene.endTime)
        self.setAnimationRange((startTime, endTime))

    def saveSettings(self, settings):
        """
        Saves the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QMocapTab, self).saveSettings(settings)

        # Save user preferences
        #
        settings.setValue('tabs/mocap/kinematicMode', self.kinematicMode())
        settings.setValue('tabs/mocap/stepInterval', self.stepInterval())

        startTime, endTime = self.animationRange()
        settings.setValue('tabs/mocap/startTime', startTime)
        settings.setValue('tabs/mocap/endTime', endTime)

    def isValid(self):
        """
        Evaluates if the source and target are valid.

        :rtype: bool
        """

        source = self.currentSource()
        target = self.currentTarget()

        return source is not None and target is not None

    def loadBinders(self):
        """
        Loads the mocap binders from the binder directory.

        :rtype: List[retargetbinder.RetargetBinder]
        """

        return retargetutils.loadBinders()

    def currentSource(self):
        """
        Returns the current source reference.
        If the scene contains no references then none is returned!

        :rtype: Union[mpynode.MPyNode, None]
        """

        return self._source

    def currentTarget(self):
        """
        Returns the current target reference.
        If the scene contains no references then none is returned!

        :rtype: Union[mpynode.MPyNode, None]
        """

        index = self.targetComboBox.currentIndex()
        numTargets = len(self._targets)

        if 0 <= index < numTargets:

            return self._targets[index]

        else:

            return None

    def currentBinder(self):
        """
        Returns the current retarget binder.
        If the no binders exist then none is returned!

        :rtype: Union[retargetbinder.RetargetBinder, None]
        """

        index = self.binderComboBox.currentIndex()
        numBinders = len(self._binders)

        if 0 <= index < numBinders:

            return self._binders[index]

        else:

            return None

    def animationRange(self):
        """
        Returns the current animation range.

        :rtype: Tuple[int, int]
        """

        return self.startTimeSpinBox.value(), self.endTimeSpinBox.value()

    def setAnimationRange(self, animationRange):
        """
        Updates the current animation range.

        :type animationRange: Tuple[int, int]
        :rtype: None
        """

        startTime, endTime = animationRange
        self.startTimeSpinBox.setValue(startTime)
        self.endTimeSpinBox.setValue(endTime)

    def stepInterval(self):
        """
        Returns the current step interval.

        :rtype: int
        """

        return self.stepSpinBox.value()

    def setStepInterval(self, value):
        """
        Updates the current step interval.

        :type value: Union[int, float]
        :rtype: None
        """

        self.stepSpinBox.setValue(value)

    def kinematicMode(self):
        """
        Returns the current kinematic mode.

        :rtype: int
        """

        return self.kinematicButtonGroup.checkedId()

    def setKinematicMode(self, index):
        """
        Updates the current kinematic mode.

        :type index: int
        :rtype: None
        """

        self.kinematicButtonGroup.buttons()[index].setChecked(True)

    def invalidateAnimationRange(self):
        """
        Invalidates the current animation range.

        :rtype: None
        """

        self.startTimeSpinBox.setValue(self.scene.startTime)
        self.endTimeSpinBox.setValue(self.scene.endTime)

    def invalidateSource(self):
        """
        Invalidates the source mocap settings.

        :rtype: None
        """

        # Check if reference exists
        #
        if self.scene.doesNodeExist(self.__source__):

            self._source = self.scene(self.__source__)
            self.sourcePathLineEdit.setText(self._source.filePath())
            self.loadSourcePushButton.setChecked(True)

        else:

            self._source = None
            self.sourcePathLineEdit.setText('')
            self.unloadSourcePushButton.setChecked(True)

    def invalidateTargets(self):
        """
        Invalidates the target reference settings.

        :rtype: None
        """

        # Collect reference nodes
        #
        references = [reference for reference in self.scene.getReferenceNodes() if reference.isValidReference()]

        self._targets = [target for target in references if target is not self._source]
        items = [target.filePath() for target in self._targets]

        # Update target combo-box
        #
        self.targetComboBox.clear()
        self.targetComboBox.addItems(items)
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_sourcePathPushButton_clicked(self, checked=False):
        """
        Slot method for the sourcePathPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for FBX file
        #
        filePath, selectedFilter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Select source file',
            self.scene.directory,
            'FBX files (*.fbx)'
        )

        if stringutils.isNullOrEmpty(filePath):

            log.info('Operation aborted...')
            return

        # Check if source already exists
        #
        source = self.currentSource()

        if source is None:

            source = self.scene.createReference(filePath, namespace='Mocap')
            self.loadSourcePushButton.setChecked(True)

        else:

            source.setFilePath(filePath, clearEdits=True)

        # Update source path line-edit
        #
        self.sourcePathLineEdit.setText(source.filePath())

    @QtCore.Slot(bool)
    def on_unloadSourcePushButton_clicked(self, checked=False):
        """
        Slot method for the unloadSourcePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        source = self.currentSource()

        if source is not None:

            source.unload()

    @QtCore.Slot(bool)
    def on_loadSourcePushButton_clicked(self, checked=False):
        """
        Slot method for the loadSourcePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        source = self.currentSource()

        if source is not None:

            source.load()

    @QtCore.Slot(bool)
    def on_retargetPushButton_clicked(self, checked=False):
        """
        Slot method for the retargetPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Check if source and target are valid
        #
        if not self.isValid():

            return

        # Apply source to current target
        #
        source = self.currentSource()
        sourceNamespace = source.associatedNamespace()
        target = self.currentTarget()
        targetNamespace = target.associatedNamespace()
        animationRange = self.animationRange()
        step = self.stepInterval()
        kinematicMode = self.kinematicMode()

        binder = self.currentBinder()
        binder.retarget(
            sourceNamespace=sourceNamespace,
            targetNamespace=targetNamespace,
            kinematicMode=kinematicMode,
            animationRange=animationRange,
            step=step
        )

    @QtCore.Slot(bool)
    def on_addFilesPushButton_clicked(self, checked=False):
        """
        Slot method for the addFilesPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for scene files
        #
        filePaths, selectedFilter = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            'Select files to batch',
            self.scene.directory,
            'FBX files (*.fbx)'
        )

        if not stringutils.isNullOrEmpty(filePaths):

            # Add new scene files to list
            #
            currentPaths = [self.fileListWidget.item(i).text() for i in range(self.fileListWidget.count())]
            filteredPaths = [path for path in filePaths if path not in currentPaths]

            for path in filteredPaths:

                self.fileListWidget.addItem(path)

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_removeFilesPushButton_clicked(self, checked=False):
        """
        Slot method for the removeFilesPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Iterate through selected items
        #
        selectedItems = self.fileListWidget.selectedItems()

        for selectedItem in reversed(selectedItems):

            row = self.fileListWidget.row(selectedItem)
            self.fileListWidget.takeItem(row)

    @QtCore.Slot(bool)
    def on_batchTargetPushButton_clicked(self, checked=False):
        """
        Slot method for the batchPathPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for export directory
        #
        filePath, selectedFilter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Select rig file',
            self.scene.directory,
            'Maya files (*.mb *.ma)'
        )

        if not stringutils.isNullOrEmpty(filePath):

            self.batchTargetLineEdit.setText(filePath)

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_batchPathPushButton_clicked(self, checked=False):
        """
        Slot method for the batchPathPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for export directory
        #
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            'Select directory to export to',
            self.scene.currentDirectory(),
            QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        )

        if not stringutils.isNullOrEmpty(directory):

            self.batchPathLineEdit.setText(directory)

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_batchPushButton_clicked(self, checked=False):
        """
        Slot method for the batchPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Check if queue is valid
        #
        fileCount = self.fileListWidget.count()

        if fileCount == 0:

            QtWidgets.QMessageBox.warning(self, 'Batch Retarget', 'No files in queue to batch!')
            return

        # Check if target is valid
        #
        targetPath = self.batchTargetLineEdit.text()

        if not os.path.exists(targetPath):

            QtWidgets.QMessageBox.warning(self, 'Batch Retarget', 'Cannot locate rig file!')
            return

        # Iterate through files
        #
        directory = self.batchPathLineEdit.text()
        increment = (1.0 / float(fileCount)) * 100.0

        for i in range(fileCount):

            # Check if source file still exists
            #
            sourcePath = self.fileListWidget.item(i).text()
            progress = increment * float(i + 1)

            if not os.path.exists(sourcePath):

                log.warning(f'Unable to reference mocap file: {sourcePath}')
                self.batchProgressBar.setValue(progress)

                continue

            # Reference source and target files
            #
            sceneutils.newScene()
            self.scene.createReference(sourcePath, namespace=self.__namespace__)
            self.scene.createReference(targetPath, namespace='X')

            self.invalidateSource()
            self.invalidateTargets()
            self.invalidateAnimationRange()

            self.retargetPushButton.click()

            # Save scene file
            #
            currentDirectory, currentFilename = os.path.split(sourcePath)
            currentName = os.path.splitext(currentFilename)[0]

            savePath = os.path.join(directory, f'{currentName}.ma') if os.path.exists(directory) else os.path.join(currentDirectory, f'{currentName}.ma')
            sceneutils.saveSceneAs(savePath)

            self.batchProgressBar.setValue(progress)
    # endregion
