import os
import json
import subprocess

from maya.api import OpenMaya as om
from Qt import QtCore, QtWidgets, QtGui
from fnmatch import fnmatchcase
from dcc.python import stringutils
from dcc.ui import qdropdownbutton, qtimespinbox, qxyzwidget, qpersistentmenu, qdivider
from dcc.ui.models import qfileitemmodel, qfileitemfiltermodel
from dcc.maya.decorators import undo
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

        # Initialize library group-box
        #
        self.libraryLayout = QtWidgets.QGridLayout()
        self.libraryLayout.setObjectName('libraryLayout')

        self.libraryGroupBox = QtWidgets.QGroupBox('')
        self.libraryGroupBox.setObjectName('libraryGroupBox')
        self.libraryGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.libraryGroupBox.setLayout(self.libraryLayout)

        self.pathLineEdit = QtWidgets.QLineEdit()
        self.pathLineEdit.setObjectName('pathLineEdit')
        self.pathLineEdit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.pathLineEdit.setFixedHeight(24)
        self.pathLineEdit.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.pathLineEdit.setToolTip('Current working directory.')
        self.pathLineEdit.textChanged.connect(self.on_pathLineEdit_textChanged)
        self.pathLineEdit.editingFinished.connect(self.on_pathLineEdit_editingFinished)

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

        self.fileListView = QtWidgets.QListView()
        self.fileListView.setObjectName('fileListView')
        self.fileListView.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.fileListView.setFocusPolicy(QtCore.Qt.NoFocus)
        self.fileListView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.fileListView.setStyleSheet('QListView::item { height: 24px; }')
        self.fileListView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.fileListView.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        self.fileListView.setAlternatingRowColors(True)
        self.fileListView.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.fileListView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.fileListView.setUniformItemSizes(True)
        self.fileListView.setItemAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.fileListView.doubleClicked.connect(self.on_fileListView_doubleClicked)
        self.fileListView.customContextMenuRequested.connect(self.on_fileListView_customContextMenuRequested)

        self.fileItemModel = qfileitemmodel.QFileItemModel(cwd=self.cwd(), parent=self.fileListView)
        self.fileItemModel.setObjectName('fileItemModel')

        self.fileItemFilterModel = qfileitemfiltermodel.QFileItemFilterModel(parent=self.fileListView)
        self.fileItemFilterModel.setObjectName('fileItemFilterModel')
        self.fileItemFilterModel.setFileMasks(['pose', 'anim'])
        self.fileItemFilterModel.setSourceModel(self.fileItemModel)

        self.fileListView.setModel(self.fileItemFilterModel)

        self.fileSelectionModel = self.fileListView.selectionModel()
        self.fileSelectionModel.setObjectName('fileSelectionModel')
        self.fileSelectionModel.selectionChanged.connect(self.on_fileListView_selectionChanged)

        self.applyPoseSlider = QtWidgets.QSlider()
        self.applyPoseSlider.setObjectName('applyPoseSlider')
        self.applyPoseSlider.setFocusPolicy(QtCore.Qt.NoFocus)
        self.applyPoseSlider.setToolTip('Blends the selected nodes towards the selected pose.')
        self.applyPoseSlider.setMinimum(0)
        self.applyPoseSlider.setMaximum(100)
        self.applyPoseSlider.setSingleStep(1)
        self.applyPoseSlider.setOrientation(QtCore.Qt.Horizontal)
        self.applyPoseSlider.setInvertedAppearance(False)
        self.applyPoseSlider.setInvertedControls(False)
        self.applyPoseSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.applyPoseSlider.setTickInterval(5)
        self.applyPoseSlider.sliderPressed.connect(self.on_applyPoseSlider_sliderPressed)
        self.applyPoseSlider.sliderMoved.connect(self.on_applyPoseSlider_sliderMoved)

        self.applyPosePushButton = qdropdownbutton.QDropDownButton('Apply')
        self.applyPosePushButton.setObjectName('applyPosePushButton')
        self.applyPosePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.applyPosePushButton.setFixedHeight(24)
        self.applyPosePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.applyPosePushButton.setToolTip('Applies the selected pose/animation onto the active selection.')
        self.applyPosePushButton.clicked.connect(self.on_applyPosePushButton_clicked)

        self.applyRelativePosePushButton = qdropdownbutton.QDropDownButton('Apply Relative')
        self.applyRelativePosePushButton.setObjectName('applyRelativePosePushButton')
        self.applyRelativePosePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.applyRelativePosePushButton.setFixedHeight(24)
        self.applyRelativePosePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.applyRelativePosePushButton.setToolTip('Applies the selected pose/animation, relative, to the current target.')
        self.applyRelativePosePushButton.clicked.connect(self.on_applyRelativePosePushButton_clicked)

        self.libraryLayout.addWidget(self.pathLineEdit, 0, 0, 1, 2)
        self.libraryLayout.addWidget(self.fileListView, 1, 0, 1, 2)
        self.libraryLayout.addWidget(self.applyPoseSlider, 2, 0, 1, 2)
        self.libraryLayout.addWidget(self.applyPosePushButton, 3, 0)
        self.libraryLayout.addWidget(self.applyRelativePosePushButton, 3, 1)

        centralLayout.addWidget(self.libraryGroupBox)

        # Initialize apply menu
        #
        self.applyPoseMenu = qpersistentmenu.QPersistentMenu(parent=self.applyPosePushButton)
        self.applyPoseMenu.setObjectName('applyPoseMenu')

        self.insertTimeSpinBox = qtimespinbox.QTimeSpinBox(parent=self.applyPoseMenu)
        self.insertTimeSpinBox.setObjectName('insertTimeSpinBox')
        self.insertTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.insertTimeSpinBox.setDefaultType(self.insertTimeSpinBox.DefaultType.CURRENT_TIME)
        self.insertTimeSpinBox.setRange(-9999999, 9999999)
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

        # Initialize apply-relative menu
        #
        self.applyRelativePoseMenu = qpersistentmenu.QPersistentMenu(parent=self.applyRelativePosePushButton)
        self.applyRelativePoseMenu.setObjectName('applyRelativePoseMenu')

        self.relativeTargetAction = QtWidgets.QAction('Target: None', parent=self.applyRelativePoseMenu)
        self.relativeTargetAction.setObjectName('relativeTargetAction')
        self.relativeTargetAction.setDisabled(True)

        self.pickRelativeTargetAction = QtWidgets.QAction('Pick Relative Target', parent=self.applyRelativePoseMenu)
        self.pickRelativeTargetAction.setObjectName('pickRelativeTargetAction')
        self.pickRelativeTargetAction.triggered.connect(self.on_pickRelativeTargetAction_triggered)

        self.applyRelativePoseMenu.addActions([self.relativeTargetAction, self.pickRelativeTargetAction])

        self.applyRelativePosePushButton.setMenu(self.applyRelativePoseMenu)

        # Initialize create-pose context menu
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

        # Initialize edit-pose context menu
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

        # Initialize quick-select group-box
        #
        self.quickSelectLayout = QtWidgets.QGridLayout()
        self.quickSelectLayout.setObjectName('quickSelectLayout')

        self.quickSelectGroupBox = QtWidgets.QGroupBox('Quick Select:')
        self.quickSelectGroupBox.setObjectName('quickSelectGroupBox')
        self.quickSelectGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.quickSelectGroupBox.setLayout(self.quickSelectLayout)

        self.selectVisiblePushButton = QtWidgets.QPushButton('Select Visible')
        self.selectVisiblePushButton.setObjectName('selectVisiblePushButton')
        self.selectVisiblePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.selectVisiblePushButton.setFixedHeight(24)
        self.selectVisiblePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.selectVisiblePushButton.setToolTip('Selects all visible controls.')
        self.selectVisiblePushButton.clicked.connect(self.on_selectVisiblePushButton_clicked)

        self.selectAllPushButton = QtWidgets.QPushButton('Select All')
        self.selectAllPushButton.setObjectName('selectAllPushButton')
        self.selectAllPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.selectAllPushButton.setFixedHeight(24)
        self.selectAllPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.selectAllPushButton.setToolTip('Selects all visible controls.')
        self.selectAllPushButton.clicked.connect(self.on_selectAllPushButton_clicked)

        self.selectAssociatedPushButton = QtWidgets.QPushButton('Select Associated')
        self.selectAssociatedPushButton.setObjectName('selectAssociatedPushButton')
        self.selectAssociatedPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.selectAssociatedPushButton.setFixedHeight(24)
        self.selectAssociatedPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.selectAssociatedPushButton.setToolTip('Selects controls in the same display layer.')
        self.selectAssociatedPushButton.clicked.connect(self.on_selectAssociatedPushButton_clicked)

        self.selectOppositePushButton = QtWidgets.QPushButton('Select Opposite')
        self.selectOppositePushButton.setObjectName('selectOppositePushButton')
        self.selectOppositePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.selectOppositePushButton.setFixedHeight(24)
        self.selectOppositePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.selectOppositePushButton.setToolTip('Selects the opposite controls.')
        self.selectOppositePushButton.clicked.connect(self.on_selectOppositePushButton_clicked)

        self.quickSelectLayout.addWidget(self.selectVisiblePushButton, 0, 0)
        self.quickSelectLayout.addWidget(self.selectAllPushButton, 0, 1)
        self.quickSelectLayout.addWidget(self.selectAssociatedPushButton, 1, 0)
        self.quickSelectLayout.addWidget(self.selectOppositePushButton, 1, 1)

        centralLayout.addWidget(self.quickSelectGroupBox)

        # Initialize quick-pose group-box
        #
        self.quickPoseLayout = QtWidgets.QGridLayout()
        self.quickPoseLayout.setObjectName('quickPoseLayout')

        self.quickPoseGroupBox = QtWidgets.QGroupBox('Quick Pose:')
        self.quickPoseGroupBox.setObjectName('quickPoseGroupBox')
        self.quickPoseGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.quickPoseGroupBox.setLayout(self.quickPoseLayout)

        self.copyPosePushButton = QtWidgets.QPushButton('Copy Pose')
        self.copyPosePushButton.setObjectName('copyPosePushButton')
        self.copyPosePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.copyPosePushButton.setFixedHeight(24)
        self.copyPosePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.copyPosePushButton.setToolTip('Copies a pose to the clipboard.')
        self.copyPosePushButton.clicked.connect(self.on_copyPosePushButton_clicked)

        self.pastePosePushButton = QtWidgets.QPushButton('Paste Pose')
        self.pastePosePushButton.setObjectName('pastePosePushButton')
        self.pastePosePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.pastePosePushButton.setFixedHeight(24)
        self.pastePosePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.pastePosePushButton.setToolTip('Pastes the pose from the clipboard.')
        self.pastePosePushButton.clicked.connect(self.on_pastePosePushButton_clicked)

        self.zeroPosePushButton = QtWidgets.QPushButton('Zero Pose')
        self.zeroPosePushButton.setObjectName('zeroPosePushButton')
        self.zeroPosePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.zeroPosePushButton.setFixedHeight(24)
        self.zeroPosePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.zeroPosePushButton.setToolTip('Resets all transform attributes to their default value.')
        self.zeroPosePushButton.clicked.connect(self.on_zeroPosePushButton_clicked)

        self.resetPosePushButton = QtWidgets.QPushButton('Reset Pose')
        self.resetPosePushButton.setObjectName('resetPosePushButton')
        self.resetPosePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.resetPosePushButton.setFixedHeight(24)
        self.resetPosePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.resetPosePushButton.setToolTip('Resets all attributes to their default value.')
        self.resetPosePushButton.clicked.connect(self.on_resetPosePushButton_clicked)

        self.holdTransformPushButton = QtWidgets.QPushButton('Hold Transform')
        self.holdTransformPushButton.setObjectName('holdTransformPushButton')
        self.holdTransformPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.holdTransformPushButton.setFixedHeight(24)
        self.holdTransformPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.holdTransformPushButton.setToolTip('Holds the transform matrices from the selected nodes.')
        self.holdTransformPushButton.clicked.connect(self.on_holdTransformPushButton_clicked)

        self.fetchTransformLayout = QtWidgets.QHBoxLayout()
        self.fetchTransformLayout.setObjectName('fetchTransformLayout')
        self.fetchTransformLayout.setContentsMargins(0, 0, 0, 0)
        self.fetchTransformLayout.setSpacing(1)

        self.fetchTransformWidget = QtWidgets.QWidget()
        self.fetchTransformWidget.setObjectName('fetchTransformWidget')
        self.fetchTransformWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.fetchTransformWidget.setFixedHeight(24)
        self.fetchTransformWidget.setLayout(self.fetchTransformLayout)

        self.leftFetchTransformPushButton = QtWidgets.QPushButton('<')
        self.leftFetchTransformPushButton.setObjectName('leftFetchTransformPushButton')
        self.leftFetchTransformPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.leftFetchTransformPushButton.setMinimumWidth(24)
        self.leftFetchTransformPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.leftFetchTransformPushButton.clicked.connect(self.on_leftFetchTransformPushButton_clicked)

        self.fetchTransformPushButton = QtWidgets.QPushButton('Fetch Transform')
        self.fetchTransformPushButton.setObjectName('fetchTransformPushButton')
        self.fetchTransformPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        self.fetchTransformPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.fetchTransformPushButton.setToolTip('Holds the transform matrices from the selected nodes.')
        self.fetchTransformPushButton.clicked.connect(self.on_fetchTransformPushButton_clicked)

        self.rightFetchTransformPushButton = QtWidgets.QPushButton('>')
        self.rightFetchTransformPushButton.setObjectName('rightFetchTransformPushButton')
        self.rightFetchTransformPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.rightFetchTransformPushButton.setMinimumWidth(24)
        self.rightFetchTransformPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.rightFetchTransformPushButton.clicked.connect(self.on_rightFetchTransformPushButton_clicked)

        self.fetchTransformLayout.addWidget(self.leftFetchTransformPushButton)
        self.fetchTransformLayout.addWidget(self.fetchTransformPushButton)
        self.fetchTransformLayout.addWidget(self.rightFetchTransformPushButton)

        self.alignLayout = QtWidgets.QHBoxLayout()
        self.alignLayout.setObjectName('alignLayout')
        self.alignLayout.setContentsMargins(0, 0, 0, 0)

        self.alignWidget = QtWidgets.QWidget()
        self.alignWidget.setObjectName('alignWidget')
        self.alignWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.alignWidget.setFixedHeight(24)
        self.alignWidget.setLayout(self.alignLayout)

        self.alignTranslateXYZWidget = qxyzwidget.QXyzWidget('Pos')
        self.alignTranslateXYZWidget.setObjectName('alignTranslateXYZWidget')
        self.alignTranslateXYZWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.alignTranslateXYZWidget.setStyleSheet('QPushButton:hover:checked { background-color: green; }\nQPushButton:checked { background-color: darkgreen; border: none; }')
        self.alignTranslateXYZWidget.setToolTip('Specify which translate axes should be aligned.')
        self.alignTranslateXYZWidget.setCheckStates([True, True, True])

        self.alignRotateXYZWidget = qxyzwidget.QXyzWidget('Rotate')
        self.alignRotateXYZWidget.setObjectName('alignRotateXYZWidget')
        self.alignRotateXYZWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.alignRotateXYZWidget.setStyleSheet('QPushButton:hover:checked { background-color: green; }\nQPushButton:checked { background-color: darkgreen; border: none; }')
        self.alignRotateXYZWidget.setToolTip('Specify which rotate axes should be aligned.')
        self.alignRotateXYZWidget.setCheckStates([True, True, True])

        self.alignScaleXYZWidget = qxyzwidget.QXyzWidget('Scale')
        self.alignScaleXYZWidget.setObjectName('alignScaleXYZWidget')
        self.alignScaleXYZWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.alignScaleXYZWidget.setStyleSheet('QPushButton:hover:checked { background-color: green; }\nQPushButton:checked { background-color: darkgreen; border: none; }')
        self.alignScaleXYZWidget.setToolTip('Specify which scale axes should be aligned.')
        self.alignScaleXYZWidget.setCheckStates([False, False, False])

        self.alignLayout.addWidget(self.alignTranslateXYZWidget)
        self.alignLayout.addWidget(self.alignRotateXYZWidget)
        self.alignLayout.addWidget(self.alignScaleXYZWidget)

        self.quickPoseLayout.addWidget(self.copyPosePushButton, 0, 0)
        self.quickPoseLayout.addWidget(self.pastePosePushButton, 0, 1)
        self.quickPoseLayout.addWidget(self.zeroPosePushButton, 1, 0)
        self.quickPoseLayout.addWidget(self.resetPosePushButton, 1, 1)
        self.quickPoseLayout.addWidget(qdivider.QDivider(QtCore.Qt.Horizontal), 2, 0, 1, 2)
        self.quickPoseLayout.addWidget(self.holdTransformPushButton, 3, 0)
        self.quickPoseLayout.addWidget(self.fetchTransformWidget, 3, 1)
        self.quickPoseLayout.addWidget(self.alignWidget, 4, 0, 1, 2)

        centralLayout.addWidget(self.quickPoseGroupBox)

        # Initialize quick-mirror group-box
        #
        self.quickMirrorLayout = QtWidgets.QGridLayout()
        self.quickMirrorLayout.setObjectName('quickMirrorLayout')

        self.quickMirrorGroupBox = QtWidgets.QGroupBox('Quick Mirror:')
        self.quickMirrorGroupBox.setObjectName('quickMirrorGroupBox')
        self.quickMirrorGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.quickMirrorGroupBox.setLayout(self.quickMirrorLayout)

        self.mirrorPosePushButton = QtWidgets.QPushButton('Mirror Pose')
        self.mirrorPosePushButton.setObjectName('mirrorPosePushButton')
        self.mirrorPosePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.mirrorPosePushButton.setFixedHeight(24)
        self.mirrorPosePushButton.setToolTip('Mirrors the pose to the opposite nodes.')
        self.mirrorPosePushButton.clicked.connect(self.on_mirrorPosePushButton_clicked)

        self.pullPosePushButton = QtWidgets.QPushButton('Pull Pose')
        self.pullPosePushButton.setObjectName('pullPosePushButton')
        self.pullPosePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.pullPosePushButton.setFixedHeight(24)
        self.pullPosePushButton.setToolTip('Pulls the pose from the opposite nodes.')
        self.pullPosePushButton.clicked.connect(self.on_pullPosePushButton_clicked)

        self.mirrorAnimationPushButton = QtWidgets.QPushButton('Mirror Animation')
        self.mirrorAnimationPushButton.setObjectName('mirrorAnimationPushButton')
        self.mirrorAnimationPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.mirrorAnimationPushButton.setFixedHeight(24)
        self.mirrorAnimationPushButton.setToolTip('Mirrors the animation to the opposite nodes.')
        self.mirrorAnimationPushButton.clicked.connect(self.on_mirrorAnimationPushButton_clicked)

        self.pullAnimationPushButton = QtWidgets.QPushButton('Pull Animation')
        self.pullAnimationPushButton.setObjectName('pullAnimationPushButton')
        self.pullAnimationPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.pullAnimationPushButton.setFixedHeight(24)
        self.pullAnimationPushButton.setToolTip('Pulls the animation from the opposite nodes.')
        self.pullAnimationPushButton.clicked.connect(self.on_pullAnimationPushButton_clicked)

        self.quickMirrorLayout.addWidget(self.mirrorPosePushButton, 0, 0)
        self.quickMirrorLayout.addWidget(self.pullPosePushButton, 0, 1)
        self.quickMirrorLayout.addWidget(self.mirrorAnimationPushButton, 1, 0)
        self.quickMirrorLayout.addWidget(self.pullAnimationPushButton, 1, 1)

        # Initialize mirror start-time group-box
        #
        self.mirrorStartTimeLayout = QtWidgets.QGridLayout()
        self.mirrorStartTimeLayout.setObjectName('mirrorStartTimeLayout')
        
        self.mirrorStartTimeGroupBox = QtWidgets.QGroupBox('Start-Frame')
        self.mirrorStartTimeGroupBox.setObjectName('mirrorStartTimeGroupBox')
        self.mirrorStartTimeGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.mirrorStartTimeGroupBox.setAlignment(QtCore.Qt.AlignCenter)
        self.mirrorStartTimeGroupBox.setLayout(self.mirrorStartTimeLayout)

        self.mirrorStartTimeSpinBox = qtimespinbox.QTimeSpinBox()
        self.mirrorStartTimeSpinBox.setObjectName('mirrorStartTimeSpinBox')
        self.mirrorStartTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.mirrorStartTimeSpinBox.setFixedHeight(24)
        self.mirrorStartTimeSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.mirrorStartTimeSpinBox.setDefaultType(qtimespinbox.QTimeSpinBox.DefaultType.START_TIME)
        self.mirrorStartTimeSpinBox.setMinimum(-9999999)
        self.mirrorStartTimeSpinBox.setMaximum(9999999)
        self.mirrorStartTimeSpinBox.setValue(self.scene.startTime)
        self.mirrorStartTimeSpinBox.setEnabled(False)

        self.mirrorStartTimeCheckBox = QtWidgets.QCheckBox('')
        self.mirrorStartTimeCheckBox.setObjectName('mirrorStartTimeLabel')
        self.mirrorStartTimeCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        self.mirrorStartTimeCheckBox.setFixedHeight(24)
        self.mirrorStartTimeCheckBox.toggled.connect(self.mirrorStartTimeSpinBox.setEnabled)

        self.mirrorStartTimeLayout.addWidget(self.mirrorStartTimeCheckBox, 0, 0)
        self.mirrorStartTimeLayout.addWidget(self.mirrorStartTimeSpinBox, 0, 1)
        
        # Initialize mirror end-time group-box
        #
        self.mirrorEndTimeLayout = QtWidgets.QGridLayout()
        self.mirrorEndTimeLayout.setObjectName('mirrorEndTimeLayout')

        self.mirrorEndTimeGroupBox = QtWidgets.QGroupBox('End-Frame')
        self.mirrorEndTimeGroupBox.setObjectName('mirrorEndTimeGroupBox')
        self.mirrorEndTimeGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.mirrorEndTimeGroupBox.setAlignment(QtCore.Qt.AlignCenter)
        self.mirrorEndTimeGroupBox.setLayout(self.mirrorEndTimeLayout)

        self.mirrorEndTimeSpinBox = qtimespinbox.QTimeSpinBox()
        self.mirrorEndTimeSpinBox.setObjectName('mirrorEndTimeSpinBox')
        self.mirrorEndTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.mirrorEndTimeSpinBox.setFixedHeight(24)
        self.mirrorEndTimeSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.mirrorEndTimeSpinBox.setDefaultType(qtimespinbox.QTimeSpinBox.DefaultType.END_TIME)
        self.mirrorEndTimeSpinBox.setMinimum(-9999999)
        self.mirrorEndTimeSpinBox.setMaximum(9999999)
        self.mirrorEndTimeSpinBox.setValue(self.scene.endTime)
        self.mirrorEndTimeSpinBox.setEnabled(False)

        self.mirrorEndTimeCheckBox = QtWidgets.QCheckBox('')
        self.mirrorEndTimeCheckBox.setObjectName('mirrorEndTimeLabel')
        self.mirrorEndTimeCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        self.mirrorEndTimeCheckBox.setFixedHeight(24)
        self.mirrorEndTimeCheckBox.toggled.connect(self.mirrorEndTimeSpinBox.setEnabled)
        
        self.mirrorEndTimeLayout.addWidget(self.mirrorEndTimeCheckBox, 0, 0)
        self.mirrorEndTimeLayout.addWidget(self.mirrorEndTimeSpinBox, 0, 1)
        
        # Initialize mirror insert-at group-box
        #
        self.mirrorInsertTimeLayout = QtWidgets.QGridLayout()
        self.mirrorInsertTimeLayout.setObjectName('mirrorInsertTimeLayout')

        self.mirrorInsertTimeGroupBox = QtWidgets.QGroupBox('Insert-At')
        self.mirrorInsertTimeGroupBox.setObjectName('mirrorInsertTimeGroupBox')
        self.mirrorInsertTimeGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.mirrorInsertTimeGroupBox.setAlignment(QtCore.Qt.AlignCenter)
        self.mirrorInsertTimeGroupBox.setLayout(self.mirrorInsertTimeLayout)

        self.mirrorInsertTimeSpinBox = qtimespinbox.QTimeSpinBox()
        self.mirrorInsertTimeSpinBox.setObjectName('mirrorInsertTimeSpinBox')
        self.mirrorInsertTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.mirrorInsertTimeSpinBox.setFixedHeight(24)
        self.mirrorInsertTimeSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.mirrorInsertTimeSpinBox.setDefaultType(qtimespinbox.QTimeSpinBox.DefaultType.CURRENT_TIME)
        self.mirrorInsertTimeSpinBox.setMinimum(-9999999)
        self.mirrorInsertTimeSpinBox.setMaximum(9999999)
        self.mirrorInsertTimeSpinBox.setValue(self.scene.time)
        self.mirrorInsertTimeSpinBox.setEnabled(False)

        self.mirrorInsertTimeCheckBox = QtWidgets.QCheckBox('')
        self.mirrorInsertTimeCheckBox.setObjectName('mirrorInsertTimeLabel')
        self.mirrorInsertTimeCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        self.mirrorInsertTimeCheckBox.setFixedHeight(24)
        self.mirrorInsertTimeCheckBox.toggled.connect(self.mirrorInsertTimeSpinBox.setEnabled)

        self.mirrorInsertTimeLayout.addWidget(self.mirrorInsertTimeCheckBox, 0, 0)
        self.mirrorInsertTimeLayout.addWidget(self.mirrorInsertTimeSpinBox, 0, 1)

        # Initialize mirror layout
        #
        self.mirrorLayout = QtWidgets.QGridLayout()
        self.mirrorLayout.setObjectName('mirrorLayout')
        self.mirrorLayout.setContentsMargins(0, 0, 0, 0)

        self.mirrorLayout.addWidget(self.quickMirrorGroupBox, 0, 0, 1, 3)
        self.mirrorLayout.addWidget(self.mirrorStartTimeGroupBox, 1, 0)
        self.mirrorLayout.addWidget(self.mirrorEndTimeGroupBox, 1, 1)
        self.mirrorLayout.addWidget(self.mirrorInsertTimeGroupBox, 1, 2)

        centralLayout.addLayout(self.mirrorLayout)
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
        super(QLibraryTab, self).loadSettings(settings)

        # Load user preferences
        #
        self.setCurrentPath(settings.value('tabs/library/currentPath', defaultValue=self.currentPath(), type=str))
        self._poseClipboard = poseutils.loadPose(settings.value('tabs/library/poseClipboard', defaultValue='null', type=str))
        self._matrixClipboard = poseutils.loadPose(settings.value('tabs/library/matrixClipboard', defaultValue='null', type=str))

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
        settings.setValue('tabs/library/poseClipboard', poseutils.dumpPose(self._poseClipboard))
        settings.setValue('tabs/library/matrixClipboard', poseutils.dumpPose(self._matrixClipboard))

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

    @undo.Undo(state=False)
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

    @undo.Undo(state=False)
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

    @undo.Undo(state=False)
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

    @undo.Undo(state=False)
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

    @undo.Undo(state=False)
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

    @undo.Undo(state=False)
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
                skipLayers=True,
                animationRange=animationRange
            )

        else:

            log.warning(f'Cannot update file: {path}')

    @undo.Undo(state=False)
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

    @undo.Undo(name='Apply Pose')
    def applyPose(self, pose):
        """
        Applies the supplied pose to the active selection.

        :type pose: pose.Pose
        :rtype: None
        """

        selection = self.getSelection()
        namespace = self.currentNamespace()

        pose.applyTo(*selection, namespace=namespace)

    @undo.Undo(state=False)
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

    @undo.Undo(name='Apply Relative Pose')
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

    @undo.Undo(name='Apply Animation')
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

    @undo.Undo(name='Apply Relative Animation')
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

    @undo.Undo(state=False)
    def copyPose(self):
        """
        Copies the selected pose to the internal clipboard.

        :rtype: None
        """

        self._poseClipboard = poseutils.createPose(*self.getSelection())

    @undo.Undo(name='Paste Pose')
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

    @undo.Undo(name='Reset Pose')
    def resetPose(self, skipUserAttributes=False):
        """
        Resets the transforms on the active selection.

        :type skipUserAttributes: bool
        :rtype: None
        """

        for node in self.scene.iterSelection(apiType=om.MFn.kTransform):

            node.resetTransform(skipUserAttributes=skipUserAttributes)

    @undo.Undo(state=False)
    def holdPose(self):
        """
        Copies the pose transform values from the active selection.

        :rtype: None
        """

        self._matrixClipboard = poseutils.createPose(*self.getSelection())

    @undo.Undo(name='Fetch Pose')
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
        selection = self.getSelection(sort=True)
        skipTranslate = self.alignTranslateXYZWidget.flags(prefix='skipTranslate', inverse=True)
        skipRotate = self.alignRotateXYZWidget.flags(prefix='skipRotate', inverse=True)
        skipScale = self.alignScaleXYZWidget.flags(prefix='skipScale', inverse=True)

        self._matrixClipboard.applyTransformsTo(*selection, worldSpace=True, **skipTranslate, **skipRotate, **skipScale)

    @undo.Undo(name='Mirror Pose')
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

    @undo.Undo(name='Mirror Animation')
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

    @undo.Undo(state=False)
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
