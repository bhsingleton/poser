import os
import json
import webbrowser

from maya.api import OpenMaya as om
from mpy import mpynode, mpyfactory
from PySide2 import QtCore, QtWidgets, QtGui
from six import string_types, integer_types
from dcc.python import stringutils
from dcc.json import jsonutils
from dcc.ui import quicwindow
from dcc.ui.dialogs import qlistdialog
from ..libs import rigconfiguration, poseutils

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
        self._configurations = self.loadConfigurations()
        self._currentConfiguration = None
        self._callbackId = None

        # Check if any configurations were loaded
        #
        numConfigurations = len(self.configurations)

        if numConfigurations > 0:

            self._currentConfiguration = self.configurations[-1]
    # endregion

    # region Properties
    @property
    def scene(self):
        """
        Returns the scene interface.

        :rtype: mpyfactory.MPyFactory
        """

        return self._scene()

    @property
    def configurations(self):
        """
        Returns a list of active rig configurations.

        :rtype: List[rigconfiguration.RigConfiguration]
        """

        return self._configurations
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
        self.setCurrentConfiguration(self.settings.value('editor/currentConfiguration', defaultValue=-1))

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
        self.settings.setValue('editor/currentConfiguration', self.configurations.index(self.currentConfiguration()))

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

        :rtype: str
        """

        namespaceOption = self.namespaceOption()

        if namespaceOption == 0:  # Use pose namespace

            return ''

        else:  # Use current namespace

            return self._customNamespace

    def loadConfigurations(self):
        """
        Loads all the available rig configurations.

        :rtype: None
        """

        # Get configuration directory
        #
        baseDirectory = os.path.dirname(os.path.abspath(__file__))
        directory = os.path.join(baseDirectory, '..', 'configs')

        # Iterate through configuration files
        #
        filePaths = [os.path.join(directory, filename) for filename in os.listdir(directory) if filename.endswith('.config')]
        numFilePaths = len(filePaths)

        configs = [None] * numFilePaths

        for (i, filePath) in enumerate(filePaths):

            configs[i] = jsonutils.load(filePath)

        return configs

    def currentConfiguration(self):
        """
        Returns the current rig configuration.

        :rtype: rigconfiguration.RigConfiguration
        """

        return self._currentConfiguration

    def setCurrentConfiguration(self, configuration):
        """
        Updates the current rig configuration.

        :type configuration: Union[int, str, rigconfiguration.RigConfiguration]
        :rtype: None
        """

        # Evaluate configuration type
        #
        if isinstance(configuration, integer_types):

            self._currentConfiguration = self.configurations[configuration]

        elif isinstance(configuration, string_types):

            configurations = [config.name for config in self.configurations]
            index = configurations.index(configuration)

            self._currentConfiguration = self.configurations[index]

        elif isinstance(configuration, rigconfiguration.RigConfiguration):

            self._currentConfiguration = configuration

        else:

            raise TypeError(f'setCurrentConfiguration() expects a valid configuration ({type(configuration).__name__} given)!')

    def controllerPatterns(self):
        """
        Returns the controller patterns used for saving poses.

        :rtype: List[str]
        """

        return self.currentConfiguration().controllerPatterns

    def controllerPriorities(self):
        """
        Returns the controller priorities for setting poses.

        :rtype: List[str]
        """

        return self.currentConfiguration().controllerPriorities
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
    def on_changeNamespaceAction_triggered(self, checked=False):
        """
        Slot method for the changeNamespaceAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for namespace
        #
        namespaces = om.MNamespace.getNamespaces(recurse=True)
        customNamespace = self.customNamespace()
        currentIndex = namespaces.index(customNamespace) if customNamespace in namespaces else 0

        namespace, response = QtWidgets.QInputDialog.getItem(
            self,
            'Select Namespace',
            'Namespaces:',
            namespaces,
            editable=False,
            current=currentIndex
        )

        if response:

            self._customNamespace = namespace

        else:

            log.warning('Operation aborted...')

    @QtCore.Slot(bool)
    def on_changeRigConfigurationAction_triggered(self, checked=False):
        """
        Slot method for the changeRigConfigurationAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for patterns
        #
        configurations = [config.name for config in self.configurations]
        currentConfiguration = self.currentConfiguration()
        current = configurations.index(currentConfiguration.name)

        configuration, response = QtWidgets.QInputDialog.getItem(
            self,
            'Select Rig Configuration',
            'Configurations:',
            configurations,
            editable=False,
            current=current
        )

        if response:

            self.setCurrentConfiguration(configuration)

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
