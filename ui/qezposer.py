import os
import json
import subprocess
import webbrowser

from maya.api import OpenMaya as om
from mpy import mpynode, mpyfactory
from PySide2 import QtCore, QtWidgets, QtGui
from dcc.python import stringutils
from dcc.maya.libs import dagutils, sceneutils, animutils
from dcc.ui import quicwindow, qrollout
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
        self._poseClipboard = None
        self._transformClipboard = None

        # Declare public variables
        #
        self.directoryAction = None
        self.parentDirectoryAction = None
        self.refreshDirectoryAction = None

        self.createMenu = None
        self.addFolderAction = None
        self.addPoseAction = None
        self.addAnimationAction = None

        self.editMenu = None
        self.selectNodesAction = None
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

        # Initialize the file item model
        #
        self.fileItemModel = qfileitemmodel.QFileItemModel(cwd=self._cwd, parent=self.fileListView)

        self.fileItemFilterModel = qfileitemfiltermodel.QFileItemFilterModel(parent=self.fileListView)
        self.fileItemFilterModel.setFileMasks(['pose', 'anim'])
        self.fileItemFilterModel.setSourceModel(self.fileItemModel)

        self.fileListView.setModel(self.fileItemFilterModel)

        # Initialize create menu
        #
        self.addFolderAction = QtWidgets.QAction('Add Folder')
        self.addFolderAction.setObjectName('addFolderAction')
        self.addFolderAction.triggered.connect(self.on_addFolderAction_triggered)

        self.addPoseAction = QtWidgets.QAction('Add Pose')
        self.addPoseAction.setObjectName('addPoseAction')
        self.addPoseAction.triggered.connect(self.on_addPoseAction_triggered)

        self.addAnimationAction = QtWidgets.QAction('Add Animation')
        self.addAnimationAction.setObjectName('addAnimationAction')
        self.addAnimationAction.triggered.connect(self.on_addAnimationAction_triggered)

        self.createMenu = QtWidgets.QMenu(parent=self.fileListView)
        self.createMenu.setObjectName('createMenu')
        self.createMenu.addAction(self.addFolderAction)
        self.createMenu.addSeparator()
        self.createMenu.addActions([self.addPoseAction, self.addAnimationAction])

        # Initialize edit menu
        #
        self.selectNodesAction = QtWidgets.QAction('Select Nodes')
        self.selectNodesAction.setObjectName('selectNodesAction')
        self.selectNodesAction.triggered.connect(self.on_selectNodesAction_triggered)

        self.openInExplorerAction = QtWidgets.QAction('Open in Explorer')
        self.openInExplorerAction.setObjectName('openInExplorerAction')
        self.openInExplorerAction.triggered.connect(self.on_openInExplorerAction_triggered)

        self.renameFileAction = QtWidgets.QAction('Rename File')
        self.renameFileAction.setObjectName('renameFileAction')
        self.renameFileAction.triggered.connect(self.on_renameFileAction_triggered)

        self.updateFileAction = QtWidgets.QAction('Update File')
        self.updateFileAction.setObjectName('updateFileAction')
        self.updateFileAction.triggered.connect(self.on_updateFileAction_triggered)

        self.deleteFileAction = QtWidgets.QAction('Delete File')
        self.deleteFileAction.setObjectName('deleteFileAction')
        self.deleteFileAction.triggered.connect(self.on_deleteFileAction_triggered)

        self.editMenu = QtWidgets.QMenu(parent=self.fileListView)
        self.editMenu.setObjectName('editMenu')
        self.editMenu.addActions([self.selectNodesAction, self.openInExplorerAction])
        self.editMenu.addSeparator()
        self.editMenu.addActions([self.renameFileAction, self.updateFileAction, self.deleteFileAction])

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
        self.setControllerPatterns(json.loads(self.settings.value('editor/controllerPatterns', defaultValue='[]')))
        self.setTransformOptions(json.loads(self.settings.value('editor/transformOptions', defaultValue='[true, true, false]')))

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

            self._cwd = cwd
            self.fileItemModel.setCwd(cwd)

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

    def selectedFile(self):
        """
        Returns the selected file path.

        :rtype: Union[qfilepath.QFilePath, None]
        """

        selectedIndices = self.fileListView.selectedIndexes()
        numSelectedIndices = len(selectedIndices)

        if numSelectedIndices == 1:

            index = self.fileItemFilterModel.mapToSource(selectedIndices[0])
            return self.fileItemModel.pathFromIndex(index)

        else:

            return None

    def activeSelection(self, asObjects=False):
        """
        Returns the active selection.

        :type asObjects: bool
        :rtype: List[om.MObject]
        """

        # Get active selection
        # Check if controller patterns should be used instead
        #
        selection = dagutils.getActiveSelection()
        selectionCount = len(selection)

        if selectionCount == 0:

            selection = list(dagutils.iterNodesByPattern(*self.controllerPatterns(), apiType=om.MFn.kTransform))

        # Check if objects should be returned
        #
        if asObjects:

            return selection

        else:

            return list(map(self.scene.__call__, selection))

    def currentNamespace(self):
        """
        Returns the current namespace based on the namespace option.

        :rtype: Union[str, None]
        """

        namespaceOption = self.namespaceOption()

        if namespaceOption == 0:  # Use pose namespace

            return None

        elif namespaceOption == 1:  # Use selected namespace

            selection = self.activeSelection()
            return selection[0].namespace() if len(selection) > 0 else ''

        else:  # Use current namespace

            return self.scene.namespace

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
    def on_usingEzPoseLibraryAction_triggered(self, checked=False):
        """
        Slot method for the usingEzPoseLibraryAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/ezposelibrary')

    @QtCore.Slot(bool)
    def on_changeControllerPatternsAction_triggered(self, checked=False):
        """
        Slot method for the changeControllerPatternsAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for patterns
        #
        dialog = qlistdialog.QListDialog('Change Controller Patterns', parent=self)
        dialog.setItems(self.controllerPatterns())

        response = dialog.exec_()

        if response:

            self.setControllerPatterns(dialog.items())

        else:

            log.info('Operation aborted...')

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
        absolutePath = os.path.join(self.currentPath(absolute=True), '{name}.pose'.format(name=name))
        poseutils.exportPose(absolutePath, self.activeSelection())

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
        absolutePath = os.path.join(self.currentPath(absolute=True), '{name}.anim'.format(name=name))
        poseutils.exportPose(absolutePath, self.activeSelection(), skipKeys=False, skipLayers=False)

        self.refresh()

    @QtCore.Slot(bool)
    def on_selectNodesAction_triggered(self, checked=False):
        """
        Slot method for the selectNodesAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected file
        #
        file = self.selectedFile()

        if file is None:

            log.warning('No file selected!')
            return

        # Select nodes from pose
        #
        if file.isFile():

            pose = poseutils.importPose(str(file))
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
        file = self.selectedFile()

        if file is None:

            log.warning('No file selected!')
            return

        # Check which operation to perform
        #
        if file.extension == '.pose':

            poseutils.exportPose(str(file), self.activeSelection())

        elif file.extension == '.anim':

            poseutils.exportPose(str(file), self.activeSelection(), skipKeys=False, skipLayers=False)

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

        if not os.path.exists(path):

            log.warning('Unable to locate path: %s' % path)
            return

        # Open new subprocess
        #
        subprocess.Popen(r'explorer /select, "{path}"'.format(path=path))

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

            self.editMenu.exec_(globalPoint)

        else:

            self.createMenu.exec_(globalPoint)

    @QtCore.Slot(bool)
    def on_applyPosePushButton_clicked(self, checked=False):
        """
        Slot method for the applyPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Get selected file
        #
        file = self.selectedFile()

        if file is None:

            log.warning('No file selected!')
            return

        # Apply pose to selection
        #
        file = self.selectedFile()

        if file.isFile():

            pose = poseutils.importPose(str(file))
            pose.applyPose(*self.activeSelection())

        else:

            log.warning('No file selected!')

    @QtCore.Slot(bool)
    def on_applyRelativePushButton_clicked(self, checked=False):
        """
        Slot method for the applyRelativePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_copyPosePushButton_clicked(self, checked=False):
        """
        Slot method for the copyPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        selection = self.activeSelection()
        self._poseClipboard = poseutils.createPose(*selection)

    @QtCore.Slot(bool)
    def on_pastePosePushButton_clicked(self, checked=False):
        """
        Slot method for the pastePosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        if self._poseClipboard is not None:

            selection = self.activeSelection()
            self._poseClipboard.applyPose(*selection)

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

            node.mirrorAnimation()

    @QtCore.Slot(bool)
    def on_pullAnimationPushButton_clicked(self, checked=False):
        """
        Slot method for the pullAnimationPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        for node in self.scene.iterSelection(apiType=om.MFn.kTransform):

            node.mirrorAnimation(pull=True)
    # endregion
