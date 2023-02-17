from Qt import QtCore, QtWidgets, QtGui
from maya.api import OpenMaya as om
from dcc.python import stringutils
from dcc.ui import qtimespinbox
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

        # Declare public variables
        #
        self.guideItemModel = None
        self.guideAction = None
        self.removeGuideAction = None
        self.selectGuideAction = None
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

        self.guides = poseutils.loadPose(self.scene.properties.get('animGuides', default='[]'))
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QPlotterTab, self).postLoad(*args, **kwargs)

        # Initialize actions
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

        # Initialize guide item model
        #
        self.guideItemModel = QtGui.QStandardItemModel(0, 1, parent=self.guideTreeView)
        self.guideItemModel.setObjectName('guideItemModel')
        self.guideItemModel.setHorizontalHeaderLabels(['Name'])

        self.guideTreeView.setModel(self.guideItemModel)
        self.guideTreeView.selectionModel().selectionChanged.connect(self.on_guideTreeView_selectionChanged)

        # Edit animation range spinners
        #
        self.startTimeSpinBox.setDefaultType(qtimespinbox.DefaultType.CurrentTime)
        self.startTimeSpinBox.setValue(self.scene.startTime)

        self.endTimeSpinBox.setDefaultType(qtimespinbox.DefaultType.CurrentTime)
        self.endTimeSpinBox.setValue(self.scene.endTime)

        # Edit keyframe button group
        #
        self.plotButtonGroup.setId(self.bakeKeysRadioButton, 0)
        self.plotButtonGroup.setId(self.preserveKeysRadioButton, 1)
        self.plotButtonGroup.setId(self.resampleKeysRadioButton, 2)

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
        self.setPlotOption(int(settings.value('tabs/plotter/plotOption', defaultValue=0)))
        self.setSnapKeys(bool(settings.value('editor/snapKeys', defaultValue=0)))
        self.setStep(int(settings.value('editor/step', defaultValue=1)))
        self.setStepEnabled(bool(settings.value('editor/stepEnabled', defaultValue=1)))

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

        # Save animation guides to scene properties
        #
        self.scene.properties['animGuides'] = poseutils.dumpPose(self.guides)

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

    def getAnimationRange(self):
        """
        Returns the current animation range.

        :rtype: Tuple[int, int]
        """

        startTime = self.startTimeSpinBox.value() if self.startTimeCheckBox.isChecked() else self.scene.startTime
        endTime = self.endTimeSpinBox.value() if self.endTimeCheckBox.isChecked() else self.scene.endTime

        return startTime, endTime

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
    def on_nameLineEdit_editingFinished(self):
        """
        Slot method for the nameLineEdit's `editingFinished` signal.

        :rtype: None
        """

        guide = self.getSelectedGuide()

        if guide is not None:

            guide.name = self.nameLineEdit.text()
            self.synchronize()

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
    def on_addGuidePushButton_clicked(self, checked=False):
        """
        Slot method for the addGuidePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        pose = poseutils.createPose(
            *self.scene.selection(),
            animationRange=self.getAnimationRange(),
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

        # Get selected guide
        #
        guide = self.getSelectedGuide()

        if guide is None:

            log.warning('No guide selected to plot to!')
            return

        # Get selected nodes
        #
        selection = self.scene.selection(apiType=om.MFn.kTransform)
        selectionCount = len(selection)

        if selectionCount == 0:

            log.warning('No nodes selected to plot to!')
            return

        # Check which operation to perform
        #
        option = self.plotOption()
        step = self.step() if self.stepEnabled() else 1
        preserveKeys = option == 1
        snapKeys = self.snapKeys()

        if option == 0 or option == 1:  # Bake/Preserve keys

            guide.bakeTransformationsTo(*selection, step=step, snapKeys=snapKeys, preserveKeys=preserveKeys)

        elif option == 2:  # Revert keys

            guide.applyAnimationTo(*selection)

        else:  # Resample keys

            raise NotImplementedError('Resample keys has not been implemented!')
    # endregion
