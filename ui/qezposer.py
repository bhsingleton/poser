import os
import json
import subprocess
import webbrowser

from maya.api import OpenMaya as om
from mpy import mpynode, mpyfactory
from PySide2 import QtCore, QtWidgets, QtGui
from dcc.python import stringutils
from dcc.ui import quicwindow, qrollout, qtimespinbox
from dcc.ui.models import qfileitemmodel, qfileitemfiltermodel
from dcc.ui.dialogs import qlistdialog
from ..libs import poseutils

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QEzPoser(quicwindow.QUicWindow):
    """
    Overload of `QUicWindow` used to edit poses when animating.
    """

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QWidget
        :key flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Declare private variables
        #
        self._scene = mpyfactory.MPyFactory.getInstance(asWeakReference=True)
        self._cwd = kwargs.get('cwd', self.scene.projectPath)
        self._currentPath = kwargs.get('currentPath', '')
        self._controllerPatterns = kwargs.get('controllerPatterns', [])
        self._controllerPriorities = kwargs.get('controllerPriorities', [])
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

        self.fileItemModel = None
        self.fileItemFilterModel = None

        # Call parent method
        #
        super(QEzPoser, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def scene(self):
        """
        Returns the scene interface.

        :rtype: mpyfactory.MPyFactory
        """

        return self._scene()
    # endregion

    # region Methods
    @classmethod
    def customWidgets(cls):
        """
        Returns a dictionary of custom widgets used by this class.

        :rtype: Dict[str, Callable]
        """

        customWidgets = super(QEzPoser, cls).customWidgets()
        customWidgets['QRollout'] = qrollout.QRollout

        return customWidgets

    def postLoad(self):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Initialize path actions
        #
        self.directoryAction = QtWidgets.QAction(QtGui.QIcon(':/qt-project.org/styles/commonstyle/images/dirclosed-16.png'), '', parent=self.pathLineEdit)
        self.directoryAction.setObjectName('directoryAction')

        self.pathLineEdit.addAction(self.directoryAction, QtWidgets.QLineEdit.LeadingPosition)

        self.refreshDirectoryAction = QtWidgets.QAction(QtGui.QIcon(':/qt-project.org/styles/commonstyle/images/refresh-24.png'), '', parent=self.pathLineEdit)
        self.refreshDirectoryAction.setObjectName('refreshDirectoryAction')
        self.refreshDirectoryAction.triggered.connect(self.on_refreshDirectoryAction_triggered)

        self.pathLineEdit.addAction(self.refreshDirectoryAction, QtWidgets.QLineEdit.TrailingPosition)

        self.parentDirectoryAction = QtWidgets.QAction(QtGui.QIcon(':/qt-project.org/styles/commonstyle/images/up-16.png'), '', parent=self.pathLineEdit)
        self.parentDirectoryAction.setObjectName('parentDirectoryAction')
        self.parentDirectoryAction.triggered.connect(self.on_parentDirectoryAction_triggered)

        self.pathLineEdit.addAction(self.parentDirectoryAction, QtWidgets.QLineEdit.TrailingPosition)

        # Initialize file path model
        #
        self.fileItemModel = qfileitemmodel.QFileItemModel(cwd=self._cwd, parent=self.fileListView)

        self.fileItemFilterModel = qfileitemfiltermodel.QFileItemFilterModel(parent=self.fileListView)
        self.fileItemFilterModel.setFileMasks(['pose', 'anim'])
        self.fileItemFilterModel.setSourceModel(self.fileItemModel)

        self.fileListView.setModel(self.fileItemFilterModel)

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

        # Edit animation range spinners
        #
        self.startTimeSpinBox.setDefaultType(qtimespinbox.DefaultType.CurrentTime)
        self.startTimeSpinBox.setValue(self.scene.startTime)

        self.endTimeSpinBox.setDefaultType(qtimespinbox.DefaultType.CurrentTime)
        self.endTimeSpinBox.setValue(self.scene.endTime)

    def loadSettings(self):
        """
        Loads the user settings.

        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).loadSettings()

        # Load user preferences
        #
        self.setCwd(self.settings.value('editor/cwd', defaultValue=self.scene.projectPath))
        self.setCurrentPath(self.settings.value('editor/currentPath', defaultValue=self.currentPath()))
        self.setNamespaceOption(self.settings.value('editor/namespaceOption', defaultValue=0))
        self.setTransformOptions(json.loads(self.settings.value('editor/transformOptions', defaultValue='[true, true, false]')))

        # Check if controller patterns exist
        #
        controllerPatterns = self.settings.value('editor/controllerPatterns', defaultValue='')

        if not stringutils.isNullOrEmpty(controllerPatterns):

            self.setControllerPatterns(json.loads(controllerPatterns))

        # Check if controller priorities exist
        #
        controllerPriorities = self.settings.value('editor/controllerPriorities', defaultValue='')

        if not stringutils.isNullOrEmpty(controllerPriorities):

            self.setControllerPriorities(json.loads(controllerPriorities))

    def saveSettings(self):
        """
        Saves the user settings.

        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).saveSettings()

        # Save user preferences
        #
        self.settings.setValue('editor/cwd', self.cwd())
        self.settings.setValue('editor/currentPath', self.currentPath())
        self.settings.setValue('editor/namespaceOption', self.namespaceOption())
        self.settings.setValue('editor/transformOptions', json.dumps(self.transformOptions()))
        self.settings.setValue('editor/controllerPatterns', json.dumps(self.controllerPatterns()))
        self.settings.setValue('editor/controllerPriorities', json.dumps(self.controllerPriorities()))

    def cwd(self):
        """
        Returns the current working directory.

        :rtype: str
        """

        return self._cwd

    def setCwd(self, cwd):
        """
        Updates the current working directory.

        :type cwd: str
        :rtype: None
        """

        # Check if path is valid
        #
        if stringutils.isNullOrEmpty(cwd):

            return

        # Check if directory exists
        #
        if os.path.isdir(cwd) and os.path.isabs(cwd):

            self._cwd = os.path.normpath(cwd)
            self.fileItemModel.setCwd(self._cwd)

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

    def namespaceOption(self):
        """
        Returns the current namespace option.

        :rtype: int
        """

        return self.namespaceActionGroup.actions().index(self.namespaceActionGroup.checkedAction())

    def setNamespaceOption(self, index):
        """
        Updates the current namespace option.

        :type index: int
        :rtype: None
        """

        self.namespaceActionGroup.actions()[index].setChecked(True)

    def transformOptions(self):
        """
        Returns the transform options.

        :rtype: Tuple[bool, bool, bool]
        """

        return [button.isChecked() for button in self.transformButtonGroup.buttons()]

    def setTransformOptions(self, options):
        """
        Updates the transform options.

        :type options: Tuple[bool, bool, bool]
        :rtype: None
        """

        for (i, button) in enumerate(self.transformButtonGroup.buttons()):

            button.setChecked(options[i])

    def controllerPatterns(self):
        """
        Returns the controller patterns used for saving poses.

        :rtype: List[str]
        """

        return self._controllerPatterns

    def setControllerPatterns(self, patterns):
        """
        Updates the controller patterns used for saving poses.

        :type patterns: List[str]
        :rtype: None
        """

        self._controllerPatterns = patterns

    def controllerPriorities(self):
        """
        Returns the controller priorities for setting poses.

        :rtype: List[str]
        """

        return self._controllerPriorities

    def setControllerPriorities(self, priorities):
        """
        Updates the controller priorities for setting poses.

        :type priorities: List[str]
        :rtype: None
        """

        self._controllerPriorities = priorities

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

    def getNamespace(self):
        """
        Returns the current namespace based on the namespace option.

        :rtype: Union[str, None]
        """

        namespaceOption = self.namespaceOption()

        if namespaceOption == 0:  # Use pose namespace

            return None

        elif namespaceOption == 1:  # Use selected namespace

            selection = self.getSelection()
            return selection[0].namespace() if len(selection) > 0 else ''

        else:  # Use current namespace

            return self.scene.namespace

    def getAnimationRange(self):
        """
        Returns the current animation range.

        :rtype: Tuple[int, int]
        """

        startTime = self.startTimeSpinBox.value() if self.startTimeCheckBox.isChecked() else self.scene.startTime
        endTime = self.endTimeSpinBox.value() if self.endTimeCheckBox.isChecked() else self.scene.endTime

        return startTime, endTime

    def getSelection(self):
        """
        Returns the active selection.
        If no nodes are selected then the controller patterns are queried instead!

        :rtype: List[mpynode.MPyNode]
        """

        selection = self.scene.selection(apiType=om.MFn.kTransform)
        selectionCount = len(selection)

        if selectionCount == 0:

            return self.scene.getNodesByPattern(*self.controllerPatterns(), apiType=om.MFn.kTransform)

        else:

            return selection

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

    @QtCore.Slot(bool)
    def on_editControllerPatternsAction_triggered(self, checked=False):
        """
        Slot method for the editControllerPatternsAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for patterns
        #
        dialog = qlistdialog.QListDialog('Edit Controller Patterns', parent=self)
        dialog.setItems(self.controllerPatterns())

        response = dialog.exec_()

        if response:

            self.setControllerPatterns(dialog.items())

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_editControllerPriorityAction_triggered(self, checked=False):
        """
        Slot method for the editControllerPriorityAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for patterns
        #
        dialog = qlistdialog.QListDialog('Edit Controller Priority', parent=self)
        dialog.setItems(self.controllerPriorities())

        response = dialog.exec_()

        if response:

            self.setControllerPriorities(dialog.items())

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_usingEzPoseLibraryAction_triggered(self, checked=False):
        """
        Slot method for the usingEzPoseLibraryAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/ezposelibrary')

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
        poseutils.exportPose(absolutePath, self.getSelection(), name=name)

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
        poseutils.exportPose(absolutePath, self.getSelection(), name=name, skipKeys=False, skipLayers=False)

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
            pose.selectAssociatedNodes(namespace=self.getNamespace())

        else:

            log.warning('No file selected!')

    @QtCore.Slot(bool)
    def on_renameFileAction_triggered(self, checked=False):
        """
        Slot method for the renameFileAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

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

            poseutils.exportPose(str(path), self.getSelection())

        elif path.extension == 'anim':

            poseutils.exportPose(str(path), self.getSelection(), skipKeys=False, skipLayers=False)

        else:

            pass

    @QtCore.Slot(bool)
    def on_deleteFileAction_triggered(self, checked=False):
        """
        Slot method for the deleteFileAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        pass

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
            self._blendPose.applyPose(*self.getSelection())

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

            # Check if selection is valid
            #
            selection = self.getSelection()
            selectionCount = len(selection)

            if selectionCount == 1:

                # Organize controls into groups
                #
                controls = self.scene.getNodesByPattern(*self.controllerPatterns(), apiType=om.MFn.kTransform)

                priorityNodes = self.scene.getNodesByPattern(*self.controllerPriorities(), apiType=om.MFn.kTransform)
                remainingNodes = list(set(controls).difference(set(priorityNodes)))

                # Apply priority nodes followed by remaining nodes
                #
                pose = poseutils.importPose(str(path))
                pose.applyRelativeTo(priorityNodes, selection[0])
                pose.applyTo(*remainingNodes)

            else:

                log.warning('Invalid selection!')

        elif path.extension == 'anim':

            # Insert at animation at current time
            #
            pose = poseutils.importPose(str(path))
            pose.applyAnimationTo(*self.getSelection(), insertAt=self.scene.time)

        else:

            log.warning('No file selected!')

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

            self._matrixClipboard.applyTransformsTo(
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
                animationRange=self.getAnimationRange()
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
                animationRange=self.getAnimationRange()
            )
    # endregion
