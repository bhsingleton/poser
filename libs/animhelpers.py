from maya import cmds as mc, mel
from maya.api import OpenMaya as om
from collections import defaultdict
from dcc.python import stringutils
from dcc.maya.libs import sceneutils
from dcc.maya.decorators import undo
from ..ui import qezposer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


CUSTOM_QUAD_VIEW = 'Stacked Four View'
DEFAULT_QUAD_VIEWS = ('Top View', 'Persp View', 'Front View', 'Side View')


def selectControls(visible=False):
    """
    Selects any controls that match the active controller patterns.

    :type visible: bool
    :rtype: None
    """

    qezposer.QEzPoser.selectControls(visible=visible)


def selectAssociatedControls():
    """
    Selects any controls that are in the same display layer.

    :rtype: None
    """

    qezposer.QEzPoser.selectAssociatedControls()


def toggleWireframe():
    """
    Toggles wireframe mode on the focused panel.

    :rtype: None
    """

    # Get focused panel
    #
    modelPanels = mc.getPanel(type='modelPanel')
    focusedPanel = mc.getPanel(underPointer=True)

    if focusedPanel is None:

        focusedPanel = mc.getPanel(withFocus=True)  # Returns last focused view

    # Check if panel is valid
    #
    isValid = focusedPanel in modelPanels

    if isValid:

        # Toggle display appearance
        #
        displayAppearance = mc.modelEditor(focusedPanel, query=True, displayAppearance=True)

        if displayAppearance == 'wireframe':

            mc.modelEditor(focusedPanel, edit=True, displayAppearance='smoothShaded')

        else:

            mc.modelEditor(focusedPanel, edit=True, displayAppearance='wireframe')

    else:

        log.debug('Cannot locate a valid model panel!')


def toggleWireframeOnShaded():
    """
    Toggles wireframe mode on the focused panel.

    :rtype: None
    """

    # Get focused panel
    #
    modelPanels = mc.getPanel(type='modelPanel')
    focusedPanel = mc.getPanel(underPointer=True)

    if focusedPanel is None:

        focusedPanel = mc.getPanel(withFocus=True)  # Returns last focused view

    # Check if panel is valid
    #
    isValid = focusedPanel in modelPanels

    if isValid:

        # Toggle wireframe state
        #
        wireframeEnabled = mc.modelEditor(focusedPanel, query=True, wireframeOnShaded=True)
        mc.modelEditor(focusedPanel, edit=True, wireframeOnShaded=(not wireframeEnabled))

    else:

        log.debug('Cannot locate a valid model panel!')


def togglePlayback():
    """
    Toggles the playback.

    :rtype: None
    """

    state = mc.play(query=True, state=True)
    mc.play(state=(not state))


def togglePlaybackSpeed():
    """
    Toggles the playback speed between full, half and quarter.

    :rtype: None
    """

    speed = mc.playbackOptions(query=True, playbackSpeed=True)

    if speed == 1.0:

        log.info('Setting playback to half speed.')
        mc.playbackOptions(playbackSpeed=0.5)

    elif speed == 0.5:

        log.info('Setting playback to quarter speed.')
        mc.playbackOptions(playbackSpeed=0.25)

    else:

        log.info('Reverting playback back to full speed.')
        mc.playbackOptions(playbackSpeed=1.0)


def overrideGhosting(*nodes, state=True):
    """
    Overrides the ghosting state on the supplied nodes.

    :type nodes: Union[str List[str]]
    :type state: bool
    :rtype: None
    """

    # Iterate through nodes
    #
    for node in nodes:

        # Collect shapes from transform
        #
        shapes = mc.listRelatives(node, shapes=True, fullPath=True)

        if stringutils.isNullOrEmpty(shapes):

            continue

        # Iterate through shapes
        #
        for shape in shapes:

            mc.setAttr(f'{shape}.ghosting', state)


@undo.Undo(state=False)
def toggleGhosting():
    """
    Toggles the ghosting for the selected nodes.

    :rtype: None
    """

    # Get ghosted objects
    #
    ghostedShapes = mc.ls(ghost=True)
    ghostedObjects = [mc.listRelatives(shape, parent=True)[0] for shape in ghostedShapes]

    # Evaluate ghosting action
    #
    selectedObjects = mc.ls(selection=True, transforms=True)
    isGhosted = any([(obj in ghostedObjects) for obj in selectedObjects])

    if isGhosted:

        log.debug('Unghosting selection!')
        overrideGhosting(*selectedObjects, state=False)

    else:

        log.debug('Ghosting selection!')
        overrideGhosting(*selectedObjects, state=True)


@undo.Undo(state=False)
def selectGhosted():
    """
    Selects ghosted nodes from the scene.

    :rtype: None
    """

    ghostedShapes = mc.ls(ghost=True)
    ghostedObjects = [mc.listRelatives(shape, parent=True)[0] for shape in ghostedShapes]

    mc.select(ghostedObjects, replace=True)


@undo.Undo(state=False)
def toggleControllerVisibility():
    """
    Toggles the control visibility inside the viewport.

    :rtype: None
    """

    # Get panel with focus
    #
    panel = mc.getPanel(withFocus=True)
    panelLabel = mc.panel(panel, query=True, label=True)

    if panelLabel not in DEFAULT_QUAD_VIEWS:

        return

    # Edit model editor
    #
    state = not mc.modelEditor(panel, query=True, nurbsCurves=True)
    mc.modelEditor(panel, edit=True, nurbsCurves=state, locators=state)


@undo.Undo(state=False)
def toggleMoveManipMode():
    """
    Toggles the translate manipulator's mode between World and Object.

    :rtype: None
    """

    mode = mc.manipMoveContext('Move', query=True, mode=True)

    if mode == 0:

        mc.manipMoveContext('Move', edit=True, mode=2)

    else:

        mc.manipMoveContext('Move', edit=True, mode=0)


@undo.Undo(state=False)
def toggleRotateManipMode():
    """
    Toggles the rotate manipulator's mode between World, Object and Gimbal.

    :rtype: None
    """

    mode = mc.manipRotateContext('Rotate', query=True, mode=True)

    if mode == 0:

        mc.manipRotateContext('Rotate', edit=True, mode=1)

    elif mode == 1:

        mc.manipRotateContext('Rotate', edit=True, mode=2)

    else:

        mc.manipRotateContext('Rotate', edit=True, mode=0)


def goToSingleView(view):
    """
    Modifies the main pane into the single-view configuration.

    :type view: int
    :rtype: None
    """

    # Get panel associated with view index
    #
    panelNames = [panel for panel in mc.getPanel(allPanels=True) if mc.panel(panel, query=True, label=True) in DEFAULT_QUAD_VIEWS]
    panelLabels = [mc.panel(panelName, query=True, label=True) for panelName in panelNames]

    index = panelLabels.index(DEFAULT_QUAD_VIEWS[view])
    panelName = panelNames[index]

    # Update panel layout
    #
    mel.eval(f'doSwitchPanes(1, {{"single", "{panelName}"}});')


def goToQuadView():
    """
    Modifies the main pane into the quad-view configuration.

    :rtype: None
    """

    # Check if custom view exists
    #
    panelName = mc.getPanel(configWithLabel=CUSTOM_QUAD_VIEW)
    configExists = not stringutils.isNullOrEmpty(panelName)

    if configExists:

        # Update panel layout
        #
        mel.eval(f'setNamedPanelLayout("{CUSTOM_QUAD_VIEW}");')

    else:

        # Create panel configuration
        #
        configName = mc.panelConfiguration(
            label=CUSTOM_QUAD_VIEW,
            sceneConfig=False,
            configString='paneLayout -edit -configuration "left4" -paneSize 2 75 100 $gMainPane;',
            addPanel=[
                (
                    False,  # type isFixed: bool
                    'Top View',  # type panelLabel: str
                    'modelPanel',  # type panelType: str
                    '{global int $gUseMenusInPanels; modelPanel -mbv $gUseMenusInPanels -unParent -l "Top View" -cam "top";}',  # type createCommand: str
                    'modelPanel -edit -l "Top View"  -cam "top" $panelName;'  # type editCommand: str
                ),
                (
                    False,
                    'Persp View',
                    'modelPanel',
                    '{global int $gUseMenusInPanels; modelPanel -mbv $gUseMenusInPanels -unParent -l "Persp View" -cam "persp";}',
                    'modelPanel -edit -l "Persp View"  -cam "persp" $panelName;'
                ),
                (
                    False,
                    'Front View',
                    'modelPanel',
                    '{global int $gUseMenusInPanels; modelPanel -mbv $gUseMenusInPanels -unParent -l "Front View" -cam "front";}',
                    'modelPanel -edit -l "Front View"  -cam "front" $panelName;'
                ),
                (
                    False,
                    'Side View',
                    'modelPanel',
                    '{global int $gUseMenusInPanels; modelPanel -mbv $gUseMenusInPanels -unParent -l "Side View" -cam "side";}',
                    'modelPanel -edit -l "Side View"  -cam "side" $panelName;'
                )
            ]
        )

        log.info(f'Create {configName} panel configuration!')
        goToQuadView()


@undo.Undo(state=False)
def toggleViewport():
    """
    Toggles the viewport between single and four-view.

    :rtype: None
    """

    # Evaluate current viewport configuration
    #
    visiblePanels = [panel for panel in mc.getPanel(visiblePanels=True) if mc.getPanel(typeOf=panel) == 'modelPanel']
    visiblePanelCount = len(visiblePanels)

    if visiblePanelCount > 1:  # Go to Single-View

        # Get focused panel
        #
        focusedPanel = mc.getPanel(underPointer=True)

        if focusedPanel is None:

            focusedPanel = mc.getPanel(withFocus=True)  # Returns last focused view

        # Go to focused view
        #
        label = mc.panel(focusedPanel, query=True, label=True)

        if label in DEFAULT_QUAD_VIEWS:

            index = DEFAULT_QUAD_VIEWS.index(label)
            goToSingleView(index)

    else:  # Go to Quad-View

        goToQuadView()


@undo.Undo(state=False)
def goToNextFrame():
    """
    Goes to the next frame while ignoring undo.

    :rtype: None
    """

    mc.currentTime(mc.currentTime(query=True) + 1, edit=True)


@undo.Undo(state=False)
def goToPreviousFrame():
    """
    Goes to the previous frame while ignoring undo.

    :rtype: None
    """

    mc.currentTime(mc.currentTime(query=True) - 1, edit=True)


@undo.Undo(state=False)
def goToNextKeyframe():
    """
    Goes to the next keyframe while ignoring undo.

    :rtype: None
    """

    mc.currentTime(mc.findKeyframe(timeSlider=True, which='next'), edit=True)


@undo.Undo(state=False)
def goToPreviousKeyframe():
    """
    Goes to the previous keyframe while ignoring undo.

    :rtype: None
    """

    mc.currentTime(mc.findKeyframe(timeSlider=True, which='previous'), edit=True)


@undo.Undo(state=False)
def goToStartFrame():
    """
    Interrupts playback and goes to the start frame.

    :rtype: None
    """

    state = mc.play(query=True, state=True)

    if state:

        mc.play(state=False)

    time = int(mc.playbackOptions(query=True, min=True))
    mc.currentTime(time, edit=True)


@undo.Undo(state=False)
def goToEndFrame():
    """
    Interrupts playback and goes to the end frame.

    :rtype: None
    """

    state = mc.play(query=True, state=True)

    if state:

        mc.play(state=False)

    time = int(mc.playbackOptions(query=True, max=True))
    mc.currentTime(time, edit=True)


@undo.Undo(name="Key Transforms")
def keyTransforms():
    """
    Keys the transform attributes on the selected nodes.

    :rtype: None
    """

    # Iterate through active selection
    #
    selection = mc.ls(selection=True, type='transform')

    for node in selection:

        # Iterate through transform attributes
        #
        for attribute in ('translate', 'rotate', 'scale'):

            # Iterate through children
            #
            children = mc.attributeQuery(attribute, node=node, listChildren=True)

            for child in children:

                # Check if child is keyable
                #
                isSettable = mc.getAttr(f'{node}.{child}', settable=True)

                if isSettable:

                    mc.setKeyframe(node, attribute=attribute)

                else:

                    continue


@undo.Undo(name="Key Selected Attributes")
def keySelectedAttributes():
    """
    Keys the selected attributes from the channel-box.
    If no attributes are selected then all channel-box attributes are keyed instead.

    :rtype: None
    """

    # Iterate through active selection
    #
    selection = mc.ls(selection=True)

    selectedAttributes = mc.channelBox('mainChannelBox', query=True, selectedMainAttributes=True)
    numAttributes = len(selectedAttributes)

    for node in selection:

        # Evaluate attribute selection
        #
        if numAttributes > 0:

            for attribute in selectedAttributes:

                mc.setKeyframe(node, attribute=attribute)

        else:

            mc.setKeyframe(node)


@undo.Undo(name="Reset Transforms")
def resetTransforms():
    """
    Resets the selected transforms.

    :rtype: None
    """

    # Iterate through active selection
    #
    selection = mc.ls(selection=True, type='transform')

    for node in selection:

        # Iterate through transform attributes
        #
        for attribute in ('translate', 'rotate', 'scale'):

            # Iterate through children
            #
            children = mc.attributeQuery(attribute, node=node, listChildren=True)
            defaultValues = mc.attributeQuery(attribute, node=node, listDefault=True)

            for (child, defaultValue) in zip(children, defaultValues):

                # Get default value
                #
                isSettable = mc.getAttr(f'{node}.{child}', settable=True)

                if isSettable:

                    mc.setAttr(f'{node}.{child}', defaultValue)

                else:

                    continue


@undo.Undo(name="Delete Selected Animation")
def deleteSelectedAnimation():
    """
    Deletes any animation on the selected nodes.

    :rtype: None
    """

    # Iterate through active selection
    #
    selection = mc.ls(selection=True, type='transform')

    for node in selection:

        animCurves = mc.listConnections(node, type='animCurve')
        hasAnimCurves = not stringutils.isNullOrEmpty(animCurves)

        if hasAnimCurves:

            mc.delete(animCurves)

        else:

            continue


@undo.Undo(name="Delete Single Translate Key")
def deleteSingleTranslateKey():
    """
    Deletes any translate keys at the current time.

    :rtype: None
    """

    # Iterate through active selection
    #
    selection = mc.ls(selection=True, type='transform')
    time = mc.currentTime(query=True)

    for node in selection:

        mc.cutKey(node, attribute=('translateX', 'translateY', 'translateZ'), time=(time, time), option='keys', clear=True)


@undo.Undo(name="Delete Single Rotate Key")
def deleteSingleRotateKey():
    """
    Deletes any rotate keys at the current time.

    :rtype: None
    """

    # Iterate through active selection
    #
    selection = mc.ls(selection=True, type='transform')
    time = mc.currentTime(query=True)

    for node in selection:

        mc.cutKey(node, attribute=('rotateX', 'rotateY', 'rotateZ'), time=(time, time), option='keys', clear=True)


@undo.Undo(name="Delete Single Scale Key")
def deleteSingleScaleKey():
    """
    Deletes any scale keys at the current time.

    :rtype: None
    """

    # Iterate through active selection
    #
    selection = mc.ls(selection=True, type='transform')
    time = mc.currentTime(query=True)

    for node in selection:

        mc.cutKey(node, attribute=('scaleX', 'scaleY', 'scaleZ'), time=(time, time), option='keys', clear=True)


@undo.Undo(name="Delete Overlapping Keys")
def deleteOverlappingKeys():
    """
    Deletes any overlapping keyframes from the active selection.

    :rtype: None
    """

    # Evaluate active selection
    #
    selection = mc.ls(selection=True)
    selectionCount = len(selection)

    if selectionCount == 0:

        return

    # Iterate through selection
    #
    for obj in selection:

        # Iterate through keyable attributes
        #
        attributes = mc.listAttr(obj, keyable=True)

        for attribute in attributes:

            # Check if attribute contains keys
            #
            keys = mc.keyframe(f'{obj}.{attribute}', query=True)

            if stringutils.isNullOrEmpty(keys):

                continue

            # Round keyframes inputs
            #
            roundedKeys = list(map(lambda number: round(number, 1), keys))
            duplicates = defaultdict(list)

            for (i, key) in enumerate(roundedKeys):

                if key in roundedKeys[:i]:

                    duplicates[key].append(i)

            # Remove duplicate keyframes
            #
            for (time, indices) in reversed(duplicates.items()):

                log.info(f'Removing duplicate keys from: {obj}.{attribute} @ {time}f')
                mc.cutKey(obj, attribute=attribute, index=(indices[0], indices[-1]))


@undo.Undo(state=False)
def frameVisible(all=False):
    """
    Frames the camera around the current scene contents.

    :type all: bool
    :rtype: None
    """

    sceneutils.frameVisible(all=all)
