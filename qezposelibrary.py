import os
import time
import subprocess
import webbrowser

from PySide2 import QtCore, QtWidgets, QtGui
from win32 import win32security
from dcc import fnscene
from dcc.ui import quicwindow, qrollout
from dcc.ui.models import qfileitemmodel, qfileitemfiltermodel

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QEzPoseLibrary(quicwindow.QUicWindow):
    """
    Overload of QUicWindow used to interface with animation poses.
    """

    cwdChanged = QtCore.Signal(str)

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :keyword parent: QtWidgets.QWidget
        :keyword flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Declare private variables
        #
        self._cwd = fnscene.FnScene().currentProjectDirectory()
        self._currentPath = None
        self._sidCache = {}

        # Declare public variables
        #
        self.directoryItemModel = None
        self.directoryItemFilterModel = None
        self.fileItemModel = None
        self.fileItemFilterModel = None

        # Call parent method
        #
        super(QEzPoseLibrary, self).__init__(*args, **kwargs)
    # endregion

    # region Methods
    @classmethod
    def customWidgets(cls):
        """
        Returns a dictionary of custom widgets used by this class.

        :rtype: dict[str, type]
        """

        customWidgets = super(QEzPoseLibrary, cls).customWidgets()
        customWidgets['QRollout'] = qrollout.QRollout

        return customWidgets

    def postLoad(self):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Initialize the directory item model
        #
        self.directoryItemModel = qfileitemmodel.QFileItemModel(self._cwd, parent=self)
        self.cwdChanged.connect(self.directoryItemModel.setCwd)

        self.directoryItemFilterModel = qfileitemfiltermodel.QFileItemFilterModel(parent=self)
        self.directoryItemFilterModel.setSourceModel(self.directoryItemModel)
        self.directoryItemFilterModel.setIgnoreFiles(True)

        self.directoryTreeView.setModel(self.directoryItemFilterModel)

        # Initialize the file item model
        #
        self.fileItemModel = qfileitemmodel.QFileItemModel(self._cwd, parent=self)
        self.fileItemModel.setUniformSize(128)

        self.fileItemFilterModel = qfileitemfiltermodel.QFileItemFilterModel(parent=self)
        self.fileItemFilterModel.setSourceModel(self.fileItemModel)

        self.fileListView.setModel(self.fileItemFilterModel)

    def cwd(self):

        return self._cwd

    def setCwd(self, cwd):

        self._cwd = cwd
        self.cwdChanged.emit(self._cwd)

    def currentPath(self):

        return self.pathLineEdit.text()

    def currentDirectory(self):
        """
        Returns the current directory path.

        :rtype: str
        """

        path = self.currentPath()

        if os.path.isfile(path) and os.path.exists(path):

            return os.path.dirname(path)

        else:

            return path

    def currentFilePath(self):
        """
        Returns the current file path.
        If the current path does not represent a file then a empty string is returned!

        :rtype: str
        """

        path = self.currentPath()

        if os.path.isfile(path) and os.path.exists(path):

            return path

        else:

            return ''

    def getFileOwner(self, filePath):
        """
        Returns the owner name for the supplied file path.
        See the following for details: https://stackoverflow.com/questions/66248783/getting-the-owner-of-the-file-for-windows-with-python-faster

        :type filePath: str
        :rtype: str
        """

        securityInfo = win32security.GetFileSecurity(filePath, win32security.OWNER_SECURITY_INFORMATION)
        ownerInfo = securityInfo.GetSecurityDescriptorOwner()

        if str(ownerInfo) not in self._sidCache:

            name, domain, accountType = win32security.LookupAccountSid(None, ownerInfo)
            self._sidCache[str(ownerInfo)] = name

        return self._sidCache[str(ownerInfo)]

    def invalidateThumbnail(self):
        """
        Updates the displayed thumbnail image.

        :rtype: None
        """

        pass

    def invalidateDetails(self):
        """
        Updates the displayed pose details.

        :rtype: None
        """

        path = self.currentPath()
        filename = os.path.basename(path)
        owner = self.getFileOwner(path)
        lastModified = time.ctime(os.stat(path).st_mtime)

        self.nameLineEdit.setText(filename)
        self.ownerLineEdit.setText(owner)
        self.lastModifiedLineEdit.setText(str(lastModified))
        self.containsLineEdit.setText('')
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_setProjectFolderAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for updating the current working directory.

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
        Triggered slot method responsible for updating the current working directory.

        :type checked: bool
        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/ezposelibrary')

    @QtCore.Slot()
    def on_pathLineEdit_editingFinished(self):
        """
        Editing finished slot method responsible for updating the pose details.

        :rtype: None
        """

        lineEdit = self.sender()
        path = lineEdit.text()
        print(path)

    @QtCore.Slot(QtCore.QModelIndex)
    def on_directoryTreeView_clicked(self, index):
        """
        Clicked slot method responsible for updating the file list view's cwd.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        sourceIndex = self.directoryItemFilterModel.mapToSource(index)
        path = self.directoryItemModel.pathFromIndex(sourceIndex)

        self.pathLineEdit.setText(str(path))
        self.fileItemModel.setCwd(str(path))
        self.fileItemFilterModel.invalidate()

    @QtCore.Slot(QtCore.QModelIndex)
    def on_fileListView_clicked(self, index):
        """
        Clicked slot method responsible for updating the active pose.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        sourceIndex = self.fileItemFilterModel.mapToSource(index)
        path = self.fileItemModel.pathFromIndex(sourceIndex)

        self.pathLineEdit.setText(str(path))
        self.invalidateThumbnail()
        self.invalidateDetails()

    @QtCore.Slot(bool)
    def on_newFolderPushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for creating a new folder.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_newPosePushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for creating a new pose file.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_newAnimPushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for creating a new animation file.

        :type checked: bool
        :rtype: None
        """

        pass

    @QtCore.Slot(bool)
    def on_openInExplorerPushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for opening the current path in a new explorer window.

        :type checked: bool
        :rtype: None
        """

        # Check if user path exists
        #
        path = self.currentDirectory()

        if not os.path.exists(path):

            log.warning('Unable to locate path: %s' % path)
            return

        # Open new subprocess
        #
        subprocess.Popen(r'explorer /select, "{path}"'.format(path=path))

    @QtCore.Slot(bool)
    def on_applyPushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for applying the current pose to the active selection

        :type checked: bool
        :rtype: None
        """

        pass
    # endregion
