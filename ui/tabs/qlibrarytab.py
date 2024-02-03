import os
import json
import subprocess

from maya.api import OpenMaya as om
from Qt import QtCore, QtWidgets, QtGui
from fnmatch import fnmatchcase
from dcc.python import stringutils
from dcc.ui import qrollout, qtimespinbox
from dcc.ui.models import qfileitemmodel, qfileitemfiltermodel
from dcc.maya.decorators.undo import undo
from . import qabstracttab
from ..dialogs import qaniminputdialog
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
        self.libraryGroupBox = None
        self.pathLineEdit = None
        self.directoryAction = None
        self.parentDirectoryAction = None
        self.refreshDirectoryAction = None
        self.fileListView = None
        self.fileItemModel = None
        self.fileItemFilterModel = None
        self.applyPoseSlider = None
        self.applyPosePushButton = None
        self.applyRelativePosePushButton = None

        self.createPoseMenu = None
        self.selectControlsAction = None
        self.selectVisibleControlsAction = None
        self.addFolderAction = None
        self.addPoseAction = None
        self.addAnimationAction = None

        self.editPoseMenu = None
        self.selectAssociatedNodesAction = None
        self.renameFileAction = None
        self.updateFileAction = None
        self.deleteFileAction = None
        self.openInExplorerAction = None

        self.applyPoseMenu = None
        self.applyAnimActionGroup = None
        self.insertAnimAction = None
        self.replaceAnimAction = None
        self.insertTimeSpinBox = None
        self.insertTimeAction = None
        self.applyRelativePoseMenu = None
        self.relativeTargetAction = None
        self.pickRelativeTargetAction = None

        self.quickSelectGroupBox = None
        self.selectVisiblePushButton = None
        self.selectAllPushButton = None
        self.selectAssociatedPushButton = None
        self.selectOppositePushButton = None

        self.quickPoseGroupBox = None
        self.copyPosePushButton = None
        self.pastePosePushButton = None
        self.zeroPosePushButton = None
        self.resetPosePushButton = None
        self.holdTransformPushButton = None
        self.fetchTransformPushButton = None
        self.leftFetchTransformPushButton = None
        self.rightFetchTransformPushButton = None
        self.matchWidget = None
        self.matchTranslateCheckBox = None
        self.matchRotateCheckBox = None
        self.matchScaleCheckBox = None
        self.matchButtonGroup = None

        self.quickMirrorGroupBox = None
        self.mirrorPosePushButton = None
        self.mirrorAnimationPushButton = None
        self.pullAnimationPushButton = None
        self.pullPosePushButton = None
        self.mirrorStartTimeWidget = None
        self.mirrorStartTimeCheckBox = None
        self.mirrorStartTimeSpinBox = None
        self.mirrorEndTimeWidget = None
        self.mirrorEndTimeCheckBox = None
        self.mirrorEndTimeSpinBox = None
        self.mirrorTimeWidget = None
        self.mirrorTimeCheckBox = None
        self.mirrorTimeSpinBox = None
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

        # Initialize file item model
        #
        self.fileItemModel = qfileitemmodel.QFileItemModel(cwd=self.cwd(), parent=self.fileListView)
        self.fileItemModel.setObjectName('fileItemModel')

        self.fileItemFilterModel = qfileitemfiltermodel.QFileItemFilterModel(parent=self.fileListView)
        self.fileItemFilterModel.setObjectName('fileItemFilterModel')
        self.fileItemFilterModel.setFileMasks(['pose', 'anim'])
        self.fileItemFilterModel.setSourceModel(self.fileItemModel)

        self.fileListView.setModel(self.fileItemFilterModel)
        self.fileListView.selectionModel().selectionChanged.connect(self.on_fileListView_selectionChanged)

        window = self.window()
        window.cwdChanged.connect(self.fileItemModel.setCwd)

        # Add "Create" menu actions
        #
        self.selectControlsAction = QtWidgets.QAction('Select Controls')
        self.selectControlsAction.setObjectName('selectControlsAction')
        self.selectControlsAction.triggered.connect(self.on_selectControlsAction_triggered)

        self.selectVisibleControlsAction = QtWidgets.QAction('Select Visible Controls')
        self.selectVisibleControlsAction.setObjectName('selectVisibleControlsAction')
        self.selectVisibleControlsAction.triggered.connect(self.on_selectVisibleControlsAction_triggered)

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
        self.createPoseMenu.addActions([self.selectControlsAction, self.selectVisibleControlsAction])
        self.createPoseMenu.addSeparator()
        self.createPoseMenu.addActions([self.addFolderAction, self.addPoseAction, self.addAnimationAction])

        # Add "Edit" menu actions
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

        # Add "Apply" menu actions
        #
        self.applyPoseMenu = QtWidgets.QMenu(parent=self.applyPosePushButton)
        self.applyPoseMenu.setObjectName('applyPoseMenu')

        self.insertTimeSpinBox = qtimespinbox.QTimeSpinBox(parent=self.applyPoseMenu)
        self.insertTimeSpinBox.setObjectName('insertTimeSpinBox')
        self.insertTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.insertTimeSpinBox.setDefaultType(self.insertTimeSpinBox.DefaultType.CurrentTime)
        self.insertTimeSpinBox.setRange(-9999, 9999)
        self.insertTimeSpinBox.setValue(self.scene.startTime)
        self.insertTimeSpinBox.setPrefix('Insert At: ')
        self.insertTimeSpinBox.setEnabled(False)

        self.insertTimeAction = QtWidgets.QWidgetAction(self.applyPoseMenu)
        self.insertTimeAction.setDefaultWidget(self.insertTimeSpinBox)

        self.replaceAnimAction = QtWidgets.QAction('Replace')
        self.replaceAnimAction.setObjectName('replaceAnimAction')
        self.replaceAnimAction.setCheckable(True)
        self.replaceAnimAction.setChecked(True)

        self.insertAnimAction = QtWidgets.QAction('Insert')
        self.insertAnimAction.setObjectName('insertAnimAction')
        self.insertAnimAction.setCheckable(True)
        self.insertAnimAction.setChecked(False)
        self.insertAnimAction.toggled.connect(self.insertTimeSpinBox.setEnabled)

        self.applyAnimActionGroup = QtWidgets.QActionGroup(self.applyPoseMenu)
        self.applyAnimActionGroup.setObjectName('applyAnimActionGroup')
        self.applyAnimActionGroup.setExclusive(True)
        self.applyAnimActionGroup.addAction(self.replaceAnimAction)
        self.applyAnimActionGroup.addAction(self.insertAnimAction)

        self.applyPoseMenu.addActions([self.replaceAnimAction, self.insertAnimAction, self.insertTimeAction])
        self.applyPosePushButton.setMenu(self.applyPoseMenu)

        # Add "Apply Relative" menu actions
        #
        self.applyRelativePoseMenu = QtWidgets.QMenu(parent=self.applyRelativePosePushButton)
        self.applyRelativePoseMenu.setObjectName('applyRelativePoseMenu')

        self.relativeTargetAction = QtWidgets.QAction('Target: None', parent=self.applyRelativePoseMenu)
        self.relativeTargetAction.setObjectName('relativeTargetAction')
        self.relativeTargetAction.setDisabled(True)

        self.pickRelativeTargetAction = QtWidgets.QAction('Pick Relative Target', parent=self.applyRelativePoseMenu)
        self.pickRelativeTargetAction.setObjectName('pickRelativeTargetAction')
        self.pickRelativeTargetAction.triggered.connect(self.on_pickRelativeTargetAction_triggered)

        self.applyRelativePoseMenu.addActions([self.relativeTargetAction, self.pickRelativeTargetAction])
        self.applyRelativePosePushButton.setMenu(self.applyRelativePoseMenu)

        # Initialize fetch menu
        #
        self.matchButtonGroup = QtWidgets.QButtonGroup(parent=self.matchWidget)
        self.matchButtonGroup.setObjectName('matchButtonGroup')
        self.matchButtonGroup.setExclusive(False)
        self.matchButtonGroup.addButton(self.matchTranslateCheckBox, id=0)
        self.matchButtonGroup.addButton(self.matchRotateCheckBox, id=1)
        self.matchButtonGroup.addButton(self.matchScaleCheckBox, id=2)

        # Edit time-range spin boxes
        #
        self.mirrorStartTimeSpinBox.setDefaultType(qtimespinbox.DefaultType.StartTime)
        self.mirrorStartTimeSpinBox.setValue(self.scene.startTime)

        self.mirrorEndTimeSpinBox.setDefaultType(qtimespinbox.DefaultType.EndTime)
        self.mirrorEndTimeSpinBox.setValue(self.scene.endTime)

        self.mirrorInsertTimeSpinBox.setDefaultType(qtimespinbox.DefaultType.CurrentTime)
        self.mirrorInsertTimeSpinBox.setValue(self.scene.startTime)

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

        return [action.isChecked() for action in self.matchButtonGroup.buttons()]

    def setTransformOptions(self, options):
        """
        Updates the transform options.

        :type options: Tuple[bool, bool, bool]
        :rtype: None
        """

        for (i, action) in enumerate(self.matchButtonGroup.buttons()):

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

    def getAnimationMode(self):
        """
        Returns the current animation mode.
        If the `insert` mode is checked then the time is also returned.

        :rtype: Tuple[int, int]
        """

        return self.applyAnimActionGroup.actions().index(self.applyAnimActionGroup.checkedAction())

    def getInsertTime(self):
        """
        Returns the current insert time.
        If `insert` mode is not enabled then none is returned!

        :rtype: Union[int, None]
        """

        return self.insertTimeSpinBox.value() if self.insertAnimAction.isChecked() else None

    def getMirrorRange(self):
        """
        Returns the current mirror range.

        :rtype: Tuple[int, int, int]
        """

        startTime = self.mirrorStartTimeSpinBox.value() if self.mirrorStartTimeCheckBox.isChecked() else self.scene.startTime
        endTime = self.mirrorEndTimeSpinBox.value() if self.mirrorEndTimeCheckBox.isChecked() else self.scene.endTime
        insertTime = self.mirrorInsertTimeSpinBox.value() if self.mirrorInsertTimeCheckBox.isChecked() else startTime

        return startTime, endTime, insertTime

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

    @undo(state=False)
    def addFolder(self):
        """
        Prompts the user to create a new folder.

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

            # Make new directory
            #
            os.mkdir(absolutePath)
            self.refresh()

    @undo(state=False)
    def addPose(self):
        """
        Prompts the user to create a new pose file.

        :rtype: None
        """

        # Prompt user for pose name
        #
        name, response = QtWidgets.QInputDialog.getText(
            self,
            'Create Pose',
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

        poseutils.exportPoseFromNodes(
            absolutePath,
            self.getSelection(),
            name=name
        )

        # Refresh file view
        #
        self.refresh()

    @undo(state=False)
    def addAnimation(self):
        """
        Prompts the user to create a new animation file.

        :rtype: None
        """

        # Prompt user for animation name
        #
        name, animationRange, response = qaniminputdialog.QAnimInputDialog.getText(
            self,
            'Create Animation',
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

        poseutils.exportPoseFromNodes(
            absolutePath,
            self.getSelection(),
            name=name,
            animationRange=animationRange,
            skipKeys=False,
            skipLayers=True
        )

        # Refresh file view
        #
        self.refresh()

    @undo(state=False)
    def openInExplorer(self):
        """
        Opens the selected file inside an explorer window.

        :rtype: None
        """

        # Check if user path exists
        #
        path = self.currentPath(absolute=True)

        if os.path.exists(path):

            subprocess.Popen(r'explorer /select, "{path}"'.format(path=path))

        else:

            log.warning(f'Cannot find directory: {path}')

    @undo(state=False)
    def renameFile(self):
        """
        Renames the selected file or folder.

        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            log.warning('No file selected to rename!')
            return

        # Prompt user for new name
        #
        name, response = QtWidgets.QInputDialog.getText(
            self,
            'Rename File',
            'Enter Name:',
            echo=QtWidgets.QLineEdit.Normal,
            text=path.basename
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

    @undo(state=False)
    def updateFile(self):
        """
        Updates the selected file.

        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            log.warning('No file selected to update!')
            return

        # Check which operation to perform
        #
        if path.extension == 'pose':

            poseutils.exportPoseFromNodes(str(path), self.getSelection())

        elif path.extension == 'anim':

            animationRange = poseutils.importPoseRange(str(path))
            poseutils.exportPoseFromNodes(
                str(path),
                self.getSelection(),
                skipKeys=False,
                skipLayers=False,
                animationRange=animationRange
            )

        else:

            log.warning(f'Cannot update file: {path}')

    @undo(state=False)
    def deleteFile(self):
        """
        Deletes the selected file or folder.

        :rtype: None
        """

        # Get selected file
        #
        path = self.selectedPath()

        if path is None:

            log.warning('No file selected to delete!')
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

    @undo(name='Apply Pose')
    def applyPose(self, pose):
        """
        Applies the supplied pose to the active selection.

        :type pose: pose.Pose
        :rtype: None
        """

        selection = self.getSelection()
        namespace = self.currentNamespace()

        pose.applyTo(*selection, namespace=namespace)

    @undo(state=False)
    def pickRelativeTarget(self):
        """
        Updates the relative target based on the active selection.

        :rtype: None
        """

        # Evaluate active selection
        #
        selection = self.getSelection()
        selectionCount = len(selection)

        if selectionCount == 1:

            node = selection[0]

            self.relativeTargetAction.setWhatsThis(node.fullPathName())
            self.relativeTargetAction.setText(f'Target: {node.name()}')

        else:

            log.warning('Please pick 1 node to set as a relative target!')

    @undo(name='Apply Relative Pose')
    def applyRelativePose(self, target, pose):
        """
        Applies the supplied pose, relative, the specified target.

        :type target: mpynode.MPyNode
        :type pose: pose.Pose
        :rtype: None
        """

        selection = self.getSelection(sort=True)
        namespace = self.currentNamespace()

        pose.applyRelativeTo(selection, target, namespace=namespace)

    @undo(name='Apply Animation')
    def applyAnimation(self, pose, insertAt=None):
        """
        Applies the supplied animation to the active selection.

        :type pose: pose.Pose
        :type insertAt: Union[int, None]
        :rtype: None
        """

        selection = self.getSelection()
        namespace = self.currentNamespace()

        pose.applyAnimationTo(*selection, insertAt=insertAt, namespace=namespace)

    @undo(name='Apply Relative Animation')
    def applyRelativeAnimation(self, insertAt, pose):
        """
        Applies the supplied animation to the active selection at the specified time.

        :type insertAt: int
        :type pose: pose.Pose
        :rtype: None
        """

        selection = self.getSelection()
        namespace = self.currentNamespace()

        pose.applyAnimationTo(*selection, insertAt=insertAt, namespace=namespace)

    @undo(state=False)
    def copyPose(self):
        """
        Copies the selected pose to the internal clipboard.

        :rtype: None
        """

        self._poseClipboard = poseutils.createPose(*self.getSelection())

    @undo(name='Paste Pose')
    def pastePose(self):
        """
        Pastes the pose from the internal clipboard onto the active selection.

        :rtype: None
        """

        # Check if clipboard is empty
        #
        if self._poseClipboard is None:

            log.warning('No pose to paste from clipboard!')
            return

        # Apply pose to selection
        #
        selection = self.getSelection()
        namespace = self.currentNamespace()

        self._poseClipboard.applyTo(*selection, namespace=namespace)

    @undo(name='Reset Pose')
    def resetPose(self, skipUserAttributes=False):
        """
        Resets the transforms on the active selection.

        :type skipUserAttributes: bool
        :rtype: None
        """

        for node in self.scene.iterSelection(apiType=om.MFn.kTransform):

            node.resetTransform(skipUserAttributes=skipUserAttributes)

    @undo(state=False)
    def holdPose(self):
        """
        Copies the pose transform values from the active selection.

        :rtype: None
        """

        self._matrixClipboard = poseutils.createPose(*self.getSelection())

    @undo(name='Fetch Pose')
    def fetchPose(self):
        """
        Applies the pose transforms to the active selection.

        :rtype: None
        """

        # Check if clipboard is empty
        #
        if self._matrixClipboard is None:

            log.warning('No pose to fetch from clipboard!')
            return

        # Apply transforms to active selection
        #
        translateEnabled, rotateEnabled, scaleEnabled = self.transformOptions()
        selection = self.getSelection(sort=True)

        self._matrixClipboard.applyTransformsTo(
            *selection,
            worldSpace=True,
            skipTranslate=(not translateEnabled),
            skipRotate=(not rotateEnabled),
            skipScale=(not scaleEnabled)
        )

    @undo(name='Mirror Pose')
    def mirrorPose(self, pull=False):
        """
        Mirrors the transforms on the active selection.

        :type pull: bool
        :rtype: None
        """

        # Create pose from selection
        #
        selection = self.getSelection()
        opposites = [node.getOppositeNode() for node in selection]
        extendedSelection = set(selection).union(set(opposites))

        pose = poseutils.createPose(*extendedSelection)

        # Evaluate mirror operation
        #
        if pull:

            pose.applyOppositeTo(*opposites)

        else:

            pose.applyOppositeTo(*selection)

    @undo(name='Mirror Animation')
    def mirrorAnimation(self, insertAt, animationRange, pull=False):
        """
        Mirrors the animation on the active selection.

        :type insertAt: Union[int, float]
        :type animationRange: Tuple[int, int]
        :type pull: bool
        :rtype: None
        """

        # Create pose from selection
        #
        selection = self.getSelection()
        opposites = [node.getOppositeNode() for node in selection]
        extendedSelection = set(selection).union(set(opposites))

        pose = poseutils.createPose(*extendedSelection, skipKeys=False)

        # Evaluate mirror operation
        #
        if pull:

            pose.applyAnimationOppositeTo(*opposites, insertAt=insertAt, animationRange=animationRange)

        else:

            pose.applyAnimationOppositeTo(*selection, insertAt=insertAt, animationRange=animationRange)

    @undo(state=False)
    def refresh(self):
        """
        Refreshes the file item model's current working directory.

        :rtype: None
        """

        self.fileItemModel.refresh()
    # endregion

    # region Slots
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

        self.selectControls(visible=False)

    @QtCore.Slot(bool)
    def on_selectVisibleControlsAction_triggered(self, checked=False):
        """
        Slot method for the selectVisibleControlsAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.selectControls(visible=True)

    @QtCore.Slot(bool)
    def on_addFolderAction_triggered(self, checked=False):
        """
        Slot method for the refreshDirectoryAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.addFolder()

    @QtCore.Slot(bool)
    def on_addPoseAction_triggered(self, checked=False):
        """
        Slot method for the addPoseAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.addPose()

    @QtCore.Slot(bool)
    def on_addAnimationAction_triggered(self, checked=False):
        """
        Slot method for the addAnimationAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.addAnimation()

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

        self.renameFile()

    @QtCore.Slot(bool)
    def on_updateFileAction_triggered(self, checked=False):
        """
        Slot method for the updateFileAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.updateFile()

    @QtCore.Slot(bool)
    def on_deleteFileAction_triggered(self, checked=False):
        """
        Slot method for the deleteFileAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.deleteFile()

    @QtCore.Slot(bool)
    def on_openInExplorerAction_triggered(self, checked=False):
        """
        Clicked slot method responsible for opening the current path in a new explorer window.

        :type checked: bool
        :rtype: None
        """

        self.openInExplorer()

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
            self.applyPose(pose)

        elif path.extension == 'anim':

            pose = poseutils.importPose(str(path))
            insertAt = self.getInsertTime()

            self.applyAnimation(pose, insertAt=insertAt)

        else:

            log.warning('No pose file selected!')

    @QtCore.Slot(bool)
    def on_applyRelativePosePushButton_clicked(self, checked=False):
        """
        Slot method for the applyRelativePosePushButton's `clicked` signal.

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
            self.applyRelativePose(target, pose)

        else:

            log.warning('No pose file selected!')

    @QtCore.Slot(bool)
    def on_pickRelativeTargetAction_triggered(self, checked=False):
        """
        Slot method for the pickRelativeTargetAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.pickRelativeTarget()

    @QtCore.Slot(bool)
    def on_selectVisiblePushButton_clicked(self, checked=False):
        """
        Slot method for the selectVisiblePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.selectControls(visible=True)

    @QtCore.Slot(bool)
    def on_selectAllPushButton_clicked(self, checked=False):
        """
        Slot method for the selectAllPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.selectControls(visible=False)

    @QtCore.Slot(bool)
    def on_selectAssociatedPushButton_clicked(self, checked=False):
        """
        Slot method for the selectLayerPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.selectAssociatedControls()

    @QtCore.Slot(bool)
    def on_selectOppositePushButton_clicked(self, checked=False):
        """
        Slot method for the selectPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        replace = not (modifiers == QtCore.Qt.ShiftModifier)
        print(replace)
        self.selectOppositeControls(replace=replace)

    @QtCore.Slot(bool)
    def on_copyPosePushButton_clicked(self, checked=False):
        """
        Slot method for the copyPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.copyPose()

    @QtCore.Slot(bool)
    def on_pastePosePushButton_clicked(self, checked=False):
        """
        Slot method for the pastePosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.pastePose()

    @QtCore.Slot(bool)
    def on_zeroPosePushButton_clicked(self, checked=False):
        """
        Slot method for the resetPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.resetPose(skipUserAttributes=True)

    @QtCore.Slot(bool)
    def on_resetPosePushButton_clicked(self, checked=False):
        """
        Slot method for the resetPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.resetPose(skipUserAttributes=False)

    @QtCore.Slot(bool)
    def on_holdTransformPushButton_clicked(self, checked=False):
        """
        Slot method for the holdTransformPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.holdPose()

    @QtCore.Slot(bool)
    def on_fetchTransformPushButton_clicked(self, checked=False):
        """
        Slot method for the fetchTransformPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.fetchPose()

    @QtCore.Slot(bool)
    def on_leftFetchTransformPushButton_clicked(self, checked=False):
        """
        Slot method for the leftFetchTransformPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.scene.time -= 1
        self.fetchPose()

    @QtCore.Slot(bool)
    def on_rightFetchTransformPushButton_clicked(self, checked=False):
        """
        Slot method for the rightFetchTransformPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.scene.time += 1
        self.fetchPose()

    @QtCore.Slot(bool)
    def on_mirrorPosePushButton_clicked(self, checked=False):
        """
        Slot method for the mirrorPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.mirrorPose(pull=False)

    @QtCore.Slot(bool)
    def on_pullPosePushButton_clicked(self, checked=False):
        """
        Slot method for the pullPosePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.mirrorPose(pull=True)

    @QtCore.Slot(bool)
    def on_mirrorAnimationPushButton_clicked(self, checked=False):
        """
        Slot method for the mirrorAnimationPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        startTime, endTime, insertAt = self.getMirrorRange()
        self.mirrorAnimation(insertAt, (startTime, endTime), pull=False)

    @QtCore.Slot(bool)
    def on_pullAnimationPushButton_clicked(self, checked=False):
        """
        Slot method for the pullAnimationPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        startTime, endTime, insertAt = self.getMirrorRange()
        self.mirrorAnimation(insertAt, (startTime, endTime), pull=True)
    # endregion
