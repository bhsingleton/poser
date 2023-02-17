import os
import re
import json
import subprocess

from maya.api import OpenMaya as om
from Qt import QtCore, QtWidgets, QtGui
from dcc.python import stringutils
from dcc.ui import qrollout, qtimespinbox
from dcc.ui.models import qfileitemmodel, qfileitemfiltermodel
from . import qabstracttab
from ...libs import poseutils

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QLibraryTab(qabstracttab.QAbstractTab):
    """
    Overload of `QAbstractTab` that interfaces with a pose library.
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
        super(QLibraryTab, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._currentPath = kwargs.get('currentPath', '')
        self._startPose = None
        self._blendPose = None
        self._endPose = None
        self._poseClipboard = None
        self._matrixClipboard = None

        # Declare public variables
        #
        self.directoryAction = None
        self.parentDirectoryAction = None
        self.refreshDirectoryAction = None

        self.fileItemModel = None
        self.fileItemFilterModel = None

        self.createPoseMenu = None
        self.selectControlsAction = None
        self.addFolderAction = None
        self.addPoseAction = None
        self.addAnimationAction = None

        self.editPoseMenu = None
        self.selectAssociatedNodesAction = None
        self.renameFileAction = None
        self.updateFileAction = None
        self.deleteFileAction = None
        self.openInExplorerAction = None

        self.applyRelativeMenu = None
        self.relativeTargetAction = None
        self.pickRelativeTargetAction = None

        self.fetchMenu = None
        self.transformActionGroup = None
        self.matchTranslateAction = None
        self.matchRotateAction = None
        self.matchScaleAction = None

        self.mirrorMenu = None
        self.startTimeWidget = None
        self.startTimeLayout = None
        self.startTimeCheckBox = None
        self.startTimeSpinBox = None
        self.startTimeAction = None
        self.endTimeWidget = None
        self.endTimeLayout = None
        self.endTimeCheckBox = None
        self.endTimeSpinBox = None
        self.endTimeAction = None
        self.insertTimeWidget = None
        self.insertTimeLayout = None
        self.insertTimeCheckBox = None
        self.insertTimeSpinBox = None
        self.insertTimeAction = None
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QLibraryTab, self).postLoad(*args, **kwargs)

        # Initialize path actions
        #
        self.directoryAction = QtWidgets.QAction(QtGui.QIcon(':/qt-project.org/styles/commonstyle/images/dirclosed-16.png'), '', parent=self.pathLineEdit)
        self.directoryAction.setObjectName('directoryAction')

        self.refreshDirectoryAction = QtWidgets.QAction(QtGui.QIcon(':/qt-project.org/styles/commonstyle/images/refresh-24.png'), '', parent=self.pathLineEdit)
        self.refreshDirectoryAction.setObjectName('refreshDirectoryAction')
        self.refreshDirectoryAction.triggered.connect(self.on_refreshDirectoryAction_triggered)

        self.parentDirectoryAction = QtWidgets.QAction(QtGui.QIcon(':/qt-project.org/styles/commonstyle/images/up-16.png'), '', parent=self.pathLineEdit)
        self.parentDirectoryAction.setObjectName('parentDirectoryAction')
        self.parentDirectoryAction.triggered.connect(self.on_parentDirectoryAction_triggered)

        self.pathLineEdit.addAction(self.directoryAction, QtWidgets.QLineEdit.LeadingPosition)
        self.pathLineEdit.addAction(self.refreshDirectoryAction, QtWidgets.QLineEdit.TrailingPosition)
        self.pathLineEdit.addAction(self.parentDirectoryAction, QtWidgets.QLineEdit.TrailingPosition)

        # Initialize file path model
        #
        self.fileItemModel = qfileitemmodel.QFileItemModel(cwd=self.cwd(), parent=self.fileListView)
        self.fileItemModel.setObjectName('fileItemModel')

        self.fileItemFilterModel = qfileitemfiltermodel.QFileItemFilterModel(parent=self.fileListView)
        self.fileItemFilterModel.setObjectName('fileItemFilterModel')
        self.fileItemFilterModel.setFileMasks(['pose', 'anim'])
        self.fileItemFilterModel.setSourceModel(self.fileItemModel)
        self.window().cwdChanged.connect(self.fileItemModel.setCwd)

        self.fileListView.setModel(self.fileItemFilterModel)
        self.fileListView.selectionModel().selectionChanged.connect(self.on_fileListView_selectionChanged)

        # Initialize create pose menu
        #
        self.selectControlsAction = QtWidgets.QAction('Select Controls')
        self.selectControlsAction.setObjectName('selectControlsAction')
        self.selectControlsAction.triggered.connect(self.on_selectControlsAction_triggered)

        self.addFolderAction = QtWidgets.QAction('Add Folder')
        self.addFolderAction.setObjectName('addFolderAction')
        self.addFolderAction.triggered.connect(self.on_addFolderAction_triggered)

        self.addPoseAction = QtWidgets.QAction('Add Pose')
        self.addPoseAction.setObjectName('addPoseAction')
        self.addPoseAction.triggered.connect(self.on_addPoseAction_triggered)

        self.addAnimationAction = QtWidgets.QAction('Add Animation')
        self.addAnimationAction.setObjectName('addAnimationAction')
        self.addAnimationAction.triggered.connect(self.on_addAnimationAction_triggered)

        self.createPoseMenu = QtWidgets.QMenu(parent=self.fileListView)
        self.createPoseMenu.setObjectName('createPoseMenu')
        self.createPoseMenu.addAction(self.selectControlsAction)
        self.createPoseMenu.addSeparator()
        self.createPoseMenu.addActions([self.addFolderAction, self.addPoseAction, self.addAnimationAction])

        # Initialize edit pose menu
        #
        self.selectAssociatedNodesAction = QtWidgets.QAction('Select Associated Nodes')
        self.selectAssociatedNodesAction.setObjectName('selectAssociatedNodesAction')
        self.selectAssociatedNodesAction.triggered.connect(self.on_selectAssociatedNodesAction_triggered)

        self.renameFileAction = QtWidgets.QAction('Rename File')
        self.renameFileAction.setObjectName('renameFileAction')
        self.renameFileAction.triggered.connect(self.on_renameFileAction_triggered)

        self.updateFileAction = QtWidgets.QAction('Update File')
        self.updateFileAction.setObjectName('updateFileAction')
        self.updateFileAction.triggered.connect(self.on_updateFileAction_triggered)

        self.deleteFileAction = QtWidgets.QAction('Delete File')
        self.deleteFileAction.setObjectName('deleteFileAction')
        self.deleteFileAction.triggered.connect(self.on_deleteFileAction_triggered)

        self.openInExplorerAction = QtWidgets.QAction('Open in Explorer')
        self.openInExplorerAction.setObjectName('openInExplorerAction')
        self.openInExplorerAction.triggered.connect(self.on_openInExplorerAction_triggered)

        self.editPoseMenu = QtWidgets.QMenu(parent=self.fileListView)
        self.editPoseMenu.setObjectName('editPoseMenu')
        self.editPoseMenu.addAction(self.selectAssociatedNodesAction)
        self.editPoseMenu.addSeparator()
        self.editPoseMenu.addActions([self.renameFileAction, self.updateFileAction, self.deleteFileAction])
        self.editPoseMenu.addSeparator()
        self.editPoseMenu.addAction(self.openInExplorerAction)

        # Initialize apply menu
        #
        self.relativeTargetAction = QtWidgets.QAction('Target: None')
        self.relativeTargetAction.setObjectName('relativeTargetAction')
        self.relativeTargetAction.setDisabled(True)

        self.pickRelativeTargetAction = QtWidgets.QAction('Pick Relative Target')
        self.pickRelativeTargetAction.setObjectName('pickRelativeTargetAction')
        self.pickRelativeTargetAction.triggered.connect(self.on_pickRelativeTargetAction_triggered)

        self.applyRelativeMenu = QtWidgets.QMenu(parent=self.applyRelativePushButton)
        self.applyRelativeMenu.setObjectName('applyRelativeMenu')
        self.applyRelativeMenu.addActions([self.relativeTargetAction, self.pickRelativeTargetAction])

        self.applyRelativePushButton.setMenu(self.applyRelativeMenu)

        # Initialize fetch menu
        #
        self.matchTranslateAction = QtWidgets.QAction('Translate')
        self.matchTranslateAction.setObjectName('matchTranslateAction')
        self.matchTranslateAction.setCheckable(True)
        self.matchTranslateAction.setChecked(True)

        self.matchRotateAction = QtWidgets.QAction('Rotate')
        self.matchRotateAction.setObjectName('matchRotateAction')
        self.matchRotateAction.setCheckable(True)
        self.matchRotateAction.setChecked(True)

        self.matchScaleAction = QtWidgets.QAction('Scale')
        self.matchScaleAction.setObjectName('matchScaleAction')
        self.matchScaleAction.setCheckable(True)
        self.matchScaleAction.setChecked(False)

        self.transformActionGroup = QtWidgets.QActionGroup(self.fetchTransformPushButton)
        self.transformActionGroup.setObjectName('transformActionGroup')
        self.transformActionGroup.setExclusive(False)
        self.transformActionGroup.addAction(self.matchTranslateAction)
        self.transformActionGroup.addAction(self.matchRotateAction)
        self.transformActionGroup.addAction(self.matchScaleAction)

        self.fetchMenu = QtWidgets.QMenu(parent=self.fetchTransformPushButton)
        self.fetchMenu.setObjectName('fetchMenu')
        self.fetchMenu.addActions([self.matchTranslateAction, self.matchRotateAction, self.matchScaleAction])

        self.fetchTransformPushButton.setMenu(self.fetchMenu)

        # Initialize start time widget
        #
        self.mirrorMenu = QtWidgets.QMenu(parent=self)
        self.mirrorMenu.setObjectName('mirrorMenu')

        self.startTimeLayout = QtWidgets.QHBoxLayout()
        self.startTimeLayout.setContentsMargins(4, 0, 0, 0)
        self.startTimeLayout.setSpacing(4)

        self.startTimeWidget = QtWidgets.QWidget(parent=self.mirrorMenu)
        self.startTimeWidget.setObjectName('startTimeWidget')
        self.startTimeWidget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.startTimeWidget.setFixedHeight(20)
        self.startTimeWidget.setLayout(self.startTimeLayout)

        self.startTimeSpinBox = qtimespinbox.QTimeSpinBox(parent=self.startTimeWidget)
        self.startTimeSpinBox.setObjectName('startTimeSpinBox')
        self.startTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.startTimeSpinBox.setDefaultType(self.startTimeSpinBox.DefaultType.StartTime)
        self.startTimeSpinBox.setRange(-9999, 9999)
        self.startTimeSpinBox.setValue(self.scene.startTime)
        self.startTimeSpinBox.setPrefix('Start: ')
        self.startTimeSpinBox.setEnabled(False)

        self.startTimeCheckBox = QtWidgets.QCheckBox('', parent=self.startTimeWidget)
        self.startTimeCheckBox.setObjectName('startTimeCheckBox')
        self.startTimeCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.startTimeCheckBox.toggled.connect(self.startTimeSpinBox.setEnabled)

        self.startTimeLayout.addWidget(self.startTimeCheckBox)
        self.startTimeLayout.addWidget(self.startTimeSpinBox)

        self.startTimeAction = QtWidgets.QWidgetAction(self.mirrorMenu)
        self.startTimeAction.setDefaultWidget(self.startTimeWidget)

        # Initialize end time widget
        #
        self.endTimeLayout = QtWidgets.QHBoxLayout()
        self.endTimeLayout.setContentsMargins(4, 0, 0, 0)
        self.endTimeLayout.setSpacing(4)

        self.endTimeWidget = QtWidgets.QWidget(parent=self.mirrorMenu)
        self.endTimeWidget.setObjectName('endTimeWidget')
        self.endTimeWidget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.endTimeWidget.setFixedHeight(20)
        self.endTimeWidget.setLayout(self.endTimeLayout)

        self.endTimeSpinBox = qtimespinbox.QTimeSpinBox(parent=self.endTimeWidget)
        self.endTimeSpinBox.setObjectName('endTimeSpinBox')
        self.endTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.endTimeSpinBox.setDefaultType(self.endTimeSpinBox.DefaultType.EndTime)
        self.endTimeSpinBox.setRange(-9999, 9999)
        self.endTimeSpinBox.setValue(self.scene.endTime)
        self.endTimeSpinBox.setPrefix('End: ')
        self.endTimeSpinBox.setEnabled(False)

        self.endTimeCheckBox = QtWidgets.QCheckBox('', parent=self.endTimeWidget)
        self.endTimeCheckBox.setObjectName('endTimeCheckBox')
        self.endTimeCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.endTimeCheckBox.toggled.connect(self.endTimeSpinBox.setEnabled)

        self.endTimeLayout.addWidget(self.endTimeCheckBox)
        self.endTimeLayout.addWidget(self.endTimeSpinBox)

        self.endTimeAction = QtWidgets.QWidgetAction(self.mirrorMenu)
        self.endTimeAction.setDefaultWidget(self.endTimeWidget)

        # Initialize insert time widget
        #
        self.insertTimeLayout = QtWidgets.QHBoxLayout()
        self.insertTimeLayout.setContentsMargins(4, 0, 0, 0)
        self.insertTimeLayout.setSpacing(4)

        self.insertTimeWidget = QtWidgets.QWidget(parent=self.mirrorMenu)
        self.insertTimeWidget.setObjectName('insertTimeWidget')
        self.insertTimeWidget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.insertTimeWidget.setFixedHeight(20)
        self.insertTimeWidget.setLayout(self.insertTimeLayout)

        self.insertTimeSpinBox = qtimespinbox.QTimeSpinBox(parent=self.insertTimeWidget)
        self.insertTimeSpinBox.setObjectName('insertTimeSpinBox')
        self.insertTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.insertTimeSpinBox.setDefaultType(self.insertTimeSpinBox.DefaultType.CurrentTime)
        self.insertTimeSpinBox.setRange(-9999, 9999)
        self.insertTimeSpinBox.setValue(self.scene.startTime)
        self.insertTimeSpinBox.setPrefix('Insert At: ')
        self.insertTimeSpinBox.setEnabled(False)

        self.insertTimeCheckBox = QtWidgets.QCheckBox('', parent=self.insertTimeWidget)
        self.insertTimeCheckBox.setObjectName('insertTimeCheckBox')
        self.insertTimeCheckBox.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.insertTimeCheckBox.toggled.connect(self.insertTimeSpinBox.setEnabled)

        self.insertTimeLayout.addWidget(self.insertTimeCheckBox)
        self.insertTimeLayout.addWidget(self.insertTimeSpinBox)

        self.insertTimeAction = QtWidgets.QWidgetAction(self.mirrorMenu)
        self.insertTimeAction.setDefaultWidget(self.insertTimeWidget)

        # Initialize mirror menus
        #
        self.mirrorMenu.addActions([self.startTimeAction, self.endTimeAction, self.insertTimeAction])

        self.mirrorAnimationPushButton.setMenu(self.mirrorMenu)
        self.pullAnimationPushButton.setMenu(self.mirrorMenu)

    def loadSettings(self, settings):
        """
        Loads the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QLibraryTab, self).loadSettings(settings)

        # Load user preferences
        #
        self.setCurrentPath(settings.value('tabs/library/currentPath', defaultValue=self.currentPath()))
        self.setTransformOptions(json.loads(settings.value('tabs/library/transformOptions', defaultValue='[true, true, false]')))

    def saveSettings(self, settings):
        """
        Saves the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QLibraryTab, self).saveSettings(settings)

        # Save user preferences
        #
        settings.setValue('tabs/library/currentPath', self.currentPath())
        settings.setValue('tabs/library/transformOptions', json.dumps(self.transformOptions()))

    def currentPath(self, absolute=False):
        """
        Returns the current relative path.

        :rtype: str
        """

        if absolute:

            return os.path.join(self.cwd(), self._currentPath)

        else:

            return self._currentPath

    def setCurrentPath(self, path):
        """
        Updates the current relative path.

        :type path: str
        :rtype: None
        """

        # Check if path is valid
        #
        if stringutils.isNullOrEmpty(path):

            return

        # Check if path is absolute
        #
        if os.path.isabs(path):

            path = os.path.relpath(path, self.cwd())

        # Check if path exists
        #
        cwd = self.cwd()
        absolutePath = os.path.join(cwd, path)

        if os.path.exists(absolutePath):

            self.pathLineEdit.setText(path)

    def transformOptions(self):
        """
        Returns the transform options.

        :rtype: Tuple[bool, bool, bool]
        """

        return [action.isChecked() for action in self.transformActionGroup.actions()]

    def setTransformOptions(self, options):
        """
        Updates the transform options.

        :type options: Tuple[bool, bool, bool]
        :rtype: None
        """

        for (i, action) in enumerate(self.transformActionGroup.actions()):

            action.setChecked(options[i])

    def selectedPath(self, asString=None):
        """
        Returns the selected file path.

        :rtype: Union[qfilepath.QFilePath, None]
        """

        # Evaluate model selection
        #
        path = None

        selectedIndices = self.fileListView.selectedIndexes()
        numSelectedIndices = len(selectedIndices)

        if numSelectedIndices == 1:

            index = self.fileItemFilterModel.mapToSource(selectedIndices[0])
            path = self.fileItemModel.pathFromIndex(index)

        # Check if a string should be returned
        #
        if asString:

            return str(path) if path is not None else ''

        else:

            return path

    def getTime(self):
        """
        Returns the current time.

        :rtype: int
        """

        return self.insertTimeSpinBox.value() if self.insertTimeCheckBox.isChecked() else self.scene.startTime

    def getAnimationRange(self):
        """
        Returns the current animation range.

        :rtype: Tuple[int, int]
        """

        startTime = self.startTimeSpinBox.value() if self.startTimeCheckBox.isChecked() else self.scene.startTime
        endTime = self.endTimeSpinBox.value() if self.endTimeCheckBox.isChecked() else self.scene.endTime

        return startTime, endTime

    def getSortPriority(self, node):
        """
        Returns the sort priority index for the supplied node.

        :type node: mpynode.MPyNode
        :rtype: int
        """

        priorities = self.controllerPriorities()
        lastIndex = len(priorities)

        matches = [i for (i, pattern) in enumerate(priorities) if re.match(pattern, node.name())]
        numMatches = len(matches)

        if numMatches > 0:

            return matches[0]

        else:

            return lastIndex

    def getSelection(self, sort=False):
        """
        Returns the active selection.
        If no nodes are selected then the controller patterns are queried instead!

        :type sort: bool
        :rtype: List[mpynode.MPyNode]
        """

        # Evaluate active selection
        #
        selection = self.scene.selection(apiType=om.MFn.kTransform)
        selectionCount = len(selection)

        if selectionCount == 0:

            selection = self.scene.getNodesByPattern(*self.controllerPatterns(), apiType=om.MFn.kTransform)

        # Check if selection requires sorting
        #
        if sort:

            return sorted(selection, key=self.getSortPriority)

        else:

            return selection

    def getRelativeTarget(self):
        """
        Returns the current relative target.

        :rtype: mpynode.MPyNode
        """

        nodeName = self.relativeTargetAction.whatsThis()

        if self.scene.doesNodeExist(nodeName):

            return self.scene(nodeName)

        else:

            return None

    def refresh(self):
        """
        Refreshes the file item model's current working directory.

        :rtype: None
        """

        self.fileItemModel.refresh()
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_setProjectFolderAction_triggered(self, checked=False):
        """
        Slot method for the setProjectFolderAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for save path
        #
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption='Select Project Folder',
            dir=self.cwd(),
            options=QtWidgets.QFileDialog.ShowDirsOnly
        )

        # Check if path is valid
        # A null value will be returned if the user exited
        #
        if os.path.isdir(directory) and os.path.exists(directory):

            self.setCwd(directory)

        else:

            log.info('Operation aborted.')

    @QtCore.Slot(str)
    def on_pathLineEdit_textChanged(self, text):
        """
        Slot method for the pathLineEdit's `textChanged` signal.

        :type text: str
        :rtype: None
        """

        absolutePath = os.path.join(self.cwd(), text)

        if os.path.isdir(absolutePath) and os.path.exists(absolutePath):

            self._currentPath = text
            self.fileItemModel.setCwd(absolutePath)

    @QtCore.Slot()
    def on_pathLineEdit_editingFinished(self):
        """
        Slot method for the pathLineEdit's `editingFinished` signal.

        :rtype: None
        """

        lineEdit = self.sender()
        text = lineEdit.text()

        absolutePath = os.path.join(self.cwd(), text)

        if not os.path.isdir(absolutePath) or not os.path.exists(absolutePath):

            lineEdit.setText(self._currentPath)

    @QtCore.Slot(bool)
    def on_parentDirectoryAction_triggered(self, checked=False):
        """
        Slot method for the parentDirectoryAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.pathLineEdit.setText(os.path.dirname(self._currentPath))

    @QtCore.Slot(bool)
    def on_refreshDirectoryAction_triggered(self, checked=False):
        """
        Slot method for the refreshDirectoryAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.refresh()

    @QtCore.Slot(bool)
    def on_selectControlsAction_triggered(self, checked=False):
        """
        Slot method for the selectControlsAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        nodes = self.scene.getNodesByPattern(*self.controllerPatterns())
        self.scene.setSelection([node.object() for node in nodes])

    @QtCore.Slot(bool)
    def on_addFolderAction_triggered(self, checked=False):
        """
        Slot method for the refreshDirectoryAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for folder name
        #
        name, response = QtWidgets.QInputDialog.getText(
            self,
            'Create New Folder',
            'Enter Name:',
            QtWidgets.QLineEdit.Normal
        )

        if not response:

            log.info('Operation aborted...')
            return

        # Check if name is unique
        # Be sure to slugify the name before processing!
        #
        name = stringutils.slugify(name)
        absolutePath = os.path.join(self.currentPath(absolute=True), name)

        if os.path.exists(absolutePath) or stringutils.isNullOrEmpty(name):

            # Notify user of invalid name
            #
            response = QtWidgets.QMessageBox.warning(
                self,
                'Create New Folder',
                'The supplied name is not unique!',
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
            )

            if response == QtWidgets.QMessageBox.Ok:

                self.addFolderAction.trigger()

        else:

            # Create new directory
            #
            os.mkdir(absolutePath)
            self.refresh()

    @QtCore.Slot(bool)
    def on_addPoseAction_triggered(self, checked=False):
        """
        Slot method for the addPoseAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for pose name
        #
        name, response = QtWidgets.QInputDialog.getText(
            self,
            'Create New Pose',
            'Enter Name:',
            QtWidgets.QLineEdit.Normal
        )

        if not response:

            log.info('Operation aborted...')
            return

        # Export pose
        #
        filename = '{name}.pose'.format(name=name)
        absolutePath = os.path.join(self.currentPath(absolute=True), filename)
        poseutils.exportPoseFromNodes(absolutePath, self.getSelection(), name=name)

        self.refresh()

    @QtCore.Slot(bool)
    def on_addAnimationAction_triggered(self, checked=False):
        """
        Slot method for the addAnimationAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for animation name
        #
        name, response = QtWidgets.QInputDialog.getText(
            self,
            'Create New Animation',
            'Enter Name:',
            QtWidgets.QLineEdit.Normal
        )

        if not response:

            log.info('Operation aborted...')
            return

        # Export animation
        #
        filename = '{name}.anim'.format(name=name)
        absolutePath = os.path.join(self.currentPath(absolute=True), filename)
        poseutils.exportPoseFromNodes(absolutePath, self.getSelection(), name=name, skipKeys=False, skipLayers=False)

        self.refresh()

    @QtCore.Slot(bool)
    def on_selectAssociatedNodesAction_triggered(self, checked=False):
        """
        Slot method for the selectNodesAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            log.warning('No file selected!')
            return

        # Select nodes from pose
        #
        if path.isFile():

            pose = poseutils.importPose(str(path))
            pose.selectAssociatedNodes(namespace=self.currentNamespace())

        else:

            log.warning('No file selected!')

    @QtCore.Slot(bool)
    def on_renameFileAction_triggered(self, checked=False):
        """
        Slot method for the renameFileAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            log.warning('No file selected!')
            return

        # Prompt user for new name
        #
        name, response = QtWidgets.QInputDialog.getText(
            self,
            'Rename File',
            'Enter Name:',
            echo=QtWidgets.QLineEdit.Normal,
            text=path.name
        )

        if not response:

            log.info('Operation aborted...')
            return

        # Check if name is unique
        #
        isUnique = all([sibling.basename.lower() != name.lower() for sibling in path.siblings])

        if not isUnique:

            QtWidgets.QMessageBox.warning(self, 'Rename File', 'File name already exists!')
            return

        # Rename file
        #
        source = str(path)

        filename = '{name}.{extension}'.format(name=name, extension=path.extension) if path.isFile() else name
        destination = os.path.join(str(path.parent), filename)

        os.rename(source, destination)
        self.refresh()

    @QtCore.Slot(bool)
    def on_updateFileAction_triggered(self, checked=False):
        """
        Slot method for the updateFileAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            log.warning('No file selected!')
            return

        # Check which operation to perform
        #
        if path.extension == 'pose':

            poseutils.exportPoseFromNodes(str(path), self.getSelection())

        elif path.extension == 'anim':

            poseutils.exportPoseFromNodes(str(path), self.getSelection(), skipKeys=False, skipLayers=False)

        else:

            pass

    @QtCore.Slot(bool)
    def on_deleteFileAction_triggered(self, checked=False):
        """
        Slot method for the deleteFileAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            log.warning('No file selected!')
            return

        # Confirm user wants to delete file
        #
        response = QtWidgets.QMessageBox.warning(
            self,
            'Delete File',
            'Are you sure you want to delete this file?',
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )

        if response != QtWidgets.QMessageBox.Ok:

            log.info('Operation aborted...')
            return

        # Check if this is a directory
        #
        if path.isDir():

            os.rmdir(str(path))
            self.refresh()

        else:

            os.remove(str(path))
            self.refresh()

    @QtCore.Slot(bool)
    def on_openInExplorerAction_triggered(self, checked=False):
        """
        Clicked slot method responsible for opening the current path in a new explorer window.

        :type checked: bool
        :rtype: None
        """

        # Check if user path exists
        #
        path = self.currentPath(absolute=True)

        if os.path.exists(path):

            subprocess.Popen(r'explorer /select, "{path}"'.format(path=path))

        else:

            log.warning('Cannot locate directory: %s' % path)

    @QtCore.Slot(QtCore.QModelIndex)
    def on_fileListView_doubleClicked(self, index):
        """
        Slot method for the fileListView's `doubleClicked` signal.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        sourceIndex = self.fileItemFilterModel.mapToSource(index)
        path = self.fileItemModel.pathFromIndex(sourceIndex)

        if path.isDir():

            relativePath = os.path.relpath(str(path), self.cwd())
            self.pathLineEdit.setText(relativePath)

    @QtCore.Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def on_fileListView_selectionChanged(self, selected, deselected):
        """
        Slot method for the fileListView's `selectionChanged` signal.

        :type selected: QtCore.QItemSelection
        :type deselected: QtCore.QItemSelection
        :rtype: None
        """

        self.applyPoseSlider.setValue(0.0)

    @QtCore.Slot(QtCore.QPoint)
    def on_fileListView_customContextMenuRequested(self, point):
        """
        Slot method for the fileListView's `customContextMenuRequested` signal.

        :type point: QtCore.QPoint
        :rtype: None
        """

        # Check if index is valid
        #
        index = self.sender().indexAt(point)
        globalPoint = self.sender().mapToGlobal(point)

        if index.isValid():

            self.editPoseMenu.exec_(globalPoint)

        else:

            self.createPoseMenu.exec_(globalPoint)

    @QtCore.Slot()
    def on_applyPoseSlider_sliderPressed(self):
        """
        Slot method for the applyPoseSlider's `sliderPressed` signal.

        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            return

        # Check if this is a pose file
        #
        if path.isFile():

            self._startPose = poseutils.createPose(*self.getSelection())
            self._endPose = poseutils.importPose(str(path))

    @QtCore.Slot(int)
    def on_applyPoseSlider_sliderMoved(self, value):
        """
        Slot method for the applyPoseSlider's `sliderMoved` signal.

        :type value: int
        :rtype: None
        """

        if self._startPose is not None and self._endPose is not None:

            self._blendPose = self._startPose.blendPose(self._endPose, weight=(float(value) / 100.0))
            self._blendPose.applyTo(*self.getSelection())

    @QtCore.Slot(bool)
    def on_applyPosePushButton_clicked(self, checked=False):
        """
        Slot method for the applyPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            log.warning('No file selected!')
            return

        # Apply pose to selection
        #
        if path.extension == 'pose':

            pose = poseutils.importPose(str(path))
            pose.applyTo(*self.getSelection())

        elif path.extension == 'anim':

            pose = poseutils.importPose(str(path))
            pose.applyAnimationTo(*self.getSelection())

        else:

            log.warning('No file selected!')

    @QtCore.Slot(bool)
    def on_applyRelativePushButton_clicked(self, checked=False):
        """
        Slot method for the applyRelativePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            log.warning('No file selected!')
            return

        # Check if file is valid
        #
        if path.extension == 'pose':

            # Check if relative target exists
            #
            target = self.getRelativeTarget()

            if target is None:

                log.warning('Cannot apply without a relative target!')
                return

            # Apply pose relative to target
            #
            pose = poseutils.importPose(str(path))
            pose.applyRelativeTo(self.getSelection(sort=True), target)

        elif path.extension == 'anim':

            # Insert at animation at current time
            #
            pose = poseutils.importPose(str(path))
            pose.applyAnimationTo(*self.getSelection(), insertAt=self.scene.time)

        else:

            log.warning('No file selected!')

    @QtCore.Slot(bool)
    def on_pickRelativeTargetAction_triggered(self, checked=False):
        """
        Slot method for the pickRelativeTargetAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        selection = self.getSelection()
        selectionCount = len(selection)

        if selectionCount == 1:

            node = selection[0]

            self.relativeTargetAction.setWhatsThis(node.fullPathName())
            self.relativeTargetAction.setText(f'Target: {node.name()}')

        else:

            log.warning('Please pick 1 node to set as a relative target!')

    @QtCore.Slot(bool)
    def on_copyPosePushButton_clicked(self, checked=False):
        """
        Slot method for the copyPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self._poseClipboard = poseutils.createPose(*self.getSelection())

    @QtCore.Slot(bool)
    def on_pastePosePushButton_clicked(self, checked=False):
        """
        Slot method for the pastePosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        if self._poseClipboard is not None:

            self._poseClipboard.applyTo(*self.getSelection())

    @QtCore.Slot(bool)
    def on_zeroPosePushButton_clicked(self, checked=False):
        """
        Slot method for the resetPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        for node in self.scene.iterSelection(apiType=om.MFn.kTransform):

            node.resetTransform(skipUserAttributes=True)


    @QtCore.Slot(bool)
    def on_resetPosePushButton_clicked(self, checked=False):
        """
        Slot method for the resetPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        for node in self.scene.iterSelection(apiType=om.MFn.kTransform):

            node.resetTransform()

    @QtCore.Slot(bool)
    def on_holdTransformPushButton_clicked(self, checked=False):
        """
        Slot method for the holdTransformPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self._matrixClipboard = poseutils.createPose(*self.getSelection())

    @QtCore.Slot(bool)
    def on_fetchTransformPushButton_clicked(self, checked=False):
        """
        Slot method for the fetchTransformPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        if self._matrixClipboard is not None:

            translateEnabled, rotateEnabled, scaleEnabled = self.transformOptions()

            self._matrixClipboard.applyMatricesTo(
                *self.getSelection(),
                worldSpace=True,
                skipTranslate=(not translateEnabled),
                skipRotate=(not rotateEnabled),
                skipScale=(not scaleEnabled)
            )

    @QtCore.Slot(bool)
    def on_mirrorPosePushButton_clicked(self, checked=False):
        """
        Slot method for the mirrorPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        for node in self.scene.iterSelection(apiType=om.MFn.kTransform):

            node.mirrorTransform()

    @QtCore.Slot(bool)
    def on_pullPosePushButton_clicked(self, checked=False):
        """
        Slot method for the pullPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        for node in self.scene.iterSelection(apiType=om.MFn.kTransform):

            node.mirrorTransform(pull=True)

    @QtCore.Slot(bool)
    def on_mirrorAnimationPushButton_clicked(self, checked=False):
        """
        Slot method for the mirrorAnimationPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        for node in self.scene.iterSelection(apiType=om.MFn.kTransform):

            node.mirrorTransform(
                includeKeys=True,
                animationRange=self.getAnimationRange(),
                insertAt=self.getTime()
            )

    @QtCore.Slot(bool)
    def on_pullAnimationPushButton_clicked(self, checked=False):
        """
        Slot method for the pullAnimationPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        for node in self.scene.iterSelection(apiType=om.MFn.kTransform):

            node.mirrorTransform(
                pull=True,
                includeKeys=True,
                animationRange=self.getAnimationRange(),
                insertAt=self.getTime()
            )
    # endregion
