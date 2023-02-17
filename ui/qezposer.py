import os
import json
import webbrowser

from maya.api import OpenMaya as om
from mpy import mpynode, mpyfactory
from PySide2 import QtCore, QtWidgets, QtGui
from dcc.python import stringutils
from dcc.ui import quicwindow
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

    # region Signals
    cwdChanged = QtCore.Signal(str)
    # endregion

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
        super(QEzPoser, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._scene = mpyfactory.MPyFactory.getInstance(asWeakReference=True)
        self._cwd = kwargs.get('cwd', self.scene.projectPath)
        self._customNamespace = ''
        self._controllerPatterns = kwargs.get('controllerPatterns', [])
        self._controllerPriorities = kwargs.get('controllerPriorities', [])
        self._callbackId = None
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

    # region Callbacks
    def sceneChanged(self, *args, **kwargs):
        """
        Callback method that notifies the tabs of a scene change.

        :key clientData: Any
        :rtype: None
        """

        for tab in self.iterTabs():

            tab.sceneChanged()
    # endregion

    # region Events
    def showEvent(self, event):
        """
        Event method called after the window has been shown.

        :type event: QtGui.QShowEvent
        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).showEvent(event)

        # Add scene callback
        #
        self._callbackId = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, self.sceneChanged)

    def closeEvent(self, event):
        """
        Event method called after the window has been closed.

        :type event: QtGui.QCloseEvent
        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).closeEvent(event)

        # Remove scene callback
        #
        om.MSceneMessage.removeCallback(self._callbackId)
    # endregion

    # region Methods
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
        self.tabControl.setCurrentIndex(self.settings.value('editor/currentTabIndex', default=0))
        self.setCwd(self.settings.value('editor/cwd', defaultValue=self.scene.projectPath))
        self.setNamespaceOption(self.settings.value('editor/namespaceOption', defaultValue=0))
        self.setCustomNamespace(self.settings.value('editor/customNamespace', defaultValue=''))

        # Check if controller patterns/priorities exist
        #
        controllerPatterns = self.settings.value('editor/controllerPatterns', defaultValue='')
        controllerPriorities = self.settings.value('editor/controllerPriorities', defaultValue='')

        if not stringutils.isNullOrEmpty(controllerPatterns) and not stringutils.isNullOrEmpty(controllerPriorities):

            self.setControllerPatterns(json.loads(controllerPatterns))
            self.setControllerPriorities(json.loads(controllerPriorities))

        # Load tab settings
        #
        for tab in self.iterTabs():

            tab.loadSettings(self.settings)

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
        self.settings.setValue('editor/currentTabIndex', self.currentTabIndex())
        self.settings.setValue('editor/cwd', self.cwd())
        self.settings.setValue('editor/namespaceOption', self.namespaceOption())
        self.settings.setValue('editor/customNamespace', self.customNamespace())
        self.settings.setValue('editor/controllerPatterns', json.dumps(self.controllerPatterns()))
        self.settings.setValue('editor/controllerPriorities', json.dumps(self.controllerPriorities()))

        # Save tab settings
        #
        for tab in self.iterTabs():

            tab.saveSettings(self.settings)

    def currentTab(self):
        """
        Returns the tab widget that is currently open.

        :rtype: QAbstractTab
        """

        return self.tabControl.currentWidget()

    def currentTabIndex(self):
        """
        Returns the tab index that currently open.

        :rtype: int
        """

        return self.tabControl.currentIndex()

    def iterTabs(self):
        """
        Returns a generator that yields tab widgets.

        :rtype: iter
        """

        for i in range(self.tabControl.count()):

            yield self.tabControl.widget(i)

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
            self.cwdChanged.emit(self._cwd)

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

    def customNamespace(self):
        """
        Returns the current custom namespace.

        :rtype: str
        """

        return self._customNamespace

    def setCustomNamespace(self, namespace):
        """
        Updates the current custom namespace.

        :type namespace: str
        :rtype: None
        """

        self._customNamespace = namespace

    def currentNamespace(self):
        """
        Returns the current namespace based on the user specified namespace option.

        :rtype: Union[str, None]
        """

        namespaceOption = self.namespaceOption()

        if namespaceOption == 0:  # Use pose namespace

            return None

        else:  # Use current namespace

            return self._customNamespace

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
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_changeNamespaceAction_triggered(self, checked=False):
        """
        Slot method for the changeNamespaceAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for namespace
        #
        namespace, response = QtWidgets.QInputDialog.getItem(
            self,
            'Select Namespace',
            'Namespaces:',
            om.MNamespace.getNamespaces(),
            editable=False
        )

        if response:

            self._customNamespace = namespace

        else:

            log.warning('Operation aborted...')

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
    def on_usingEzPoserAction_triggered(self, checked=False):
        """
        Slot method for the usingEzPoser's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/ezposer')
    # endregion
