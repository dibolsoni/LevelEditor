from pandac.PandaModules import *

from direct.showbase.DirectObject import DirectObject
from direct.directtools.DirectGlobals import *
from direct.directnotify.DirectNotifyGlobal import directNotify

from tkFileDialog import askopenfilename, askdirectory
from Tkinter import *
from Pmw import MegaToplevel, MenuBar, ComboBox
from Pmw import EntryField, NoteBook, Dialog

from libpandaworld.WorldCreator import WorldCreator

from collections import OrderedDict as odict
from getpass import getuser
from json import dumps

import time, os

class LevelEditor(NodePath, DirectObject):
    notify = directNotify.newCategory('LevelEditor')

    def __init__(self):
        NodePath.__init__(self, 'LevelEditor')

        self.modelPaths = set()
        self.nodePaths = {}

        self.window = LevelEditorWindow(self)
        self.window['title'] = 'libpandaworld Level Editor'

        self.hubParent = 'null'

        self.worldCreator = WorldCreator(self)

        self.actionEvents = [
            ('DIRECT_selectedNodePath', self.selectedNodePathHook),
            ('arrow_left', self.keyboardXformSelected, ['left', 'xlate']),
            ('arrow_right', self.keyboardXformSelected, ['right', 'xlate']),
            ('arrow_up', self.keyboardXformSelected, ['up','xlate']),
            ('arrow_down', self.keyboardXformSelected, ['down','xlate']),
            ('control-arrow_left', self.keyboardXformSelected, ['left', 'rotate']),
            ('control-arrow_right', self.keyboardXformSelected, ['right', 'rotate']),
            ('control-arrow_up', self.keyboardXformSelected, ['up', 'rotate']),
            ('control-arrow_down', self.keyboardXformSelected, ['down', 'rotate'])]

        self.selectedNode = None

        self.currentWorld = ()
        self.currentLocation = ()

        self.lastAngle = 0.0

        base.direct.enable()

        base.camLens.setNear(1.0)
        base.camLens.setFar(3000)
        base.direct.camera.setPos(0, -10, 10)

        self.reparentTo(base.direct.group)
        self.show()

        for event in self.actionEvents:
            if len(event) == 3:
                self.accept(event[0], event[1], event[2])
            else:
                self.accept(event[0], event[1])

    def createRegion(self, regionData):
        pass

    def createLocation(self, locData):
        pass

    def createObject(self, obj, objType, parent, parentUid, objKey, dynamic, actualParentObj, **kwargs):
        uid = objKey if type(objKey) == str else ''
        if not uid: return

        visual = obj.get('Visual') or {}
        model = visual.get('Model')
        if not model: return

        if not model[-4:] == '.bam' and not model[-4:] == '.egg':
            model += '.bam'

        pos = VBase3(*obj.get('Pos'))
        hpr = Point3(*obj.get('Hpr'))
        scale = VBase3(*obj.get('Scale'))

        self.window.showResources([model])

        node = loader.loadModel(model)
        node.setPos(pos)
        node.setHpr(hpr)
        node.setScale(scale)
        node.reparentTo(render)

        self.nodePaths[node] = [uid, node.getPos(), node.getHpr(), node.getScale(), set()]

        traverser = self.nodeTraverser(node)
        for n in traverser:
            self.nodePaths[node][4].add(n)

    def nodeTraverser(self, node):
        yield node

        for child in node.getChildren():
            for result in self.nodeTraverser(child):
                yield result

    def selectedNodePathHook(self, nodePath):
        if nodePath == self.selectedNode:
            return

        base.direct.deselect(nodePath)

        for node, dataList in self.nodePaths.iteritems():
            nodeSet = dataList[4]

            for childNode in nodeSet:
                if nodePath.getName() == childNode.getName():
                    self.selectedNode = node
                    base.direct.select(node)

    def getUid(self):
        return str(time.time()) + getuser()

    def setLastAngle(self, angle):
        self.lastAngle = angle

    def getLastAngle(self):
        return self.lastAngle

    def keyboardRotateSelected(self, arrowDirection):
        # Get snap angle
        if base.direct.fShift:
            oldSnapAngle = base.direct.grid.snapAngle
            base.direct.grid.setSnapAngle(1.0)

        snapAngle = base.direct.grid.snapAngle
        # Compute new angle
        if arrowDirection == 'left' or arrowDirection == 'up':
            self.setLastAngle(self.getLastAngle() + snapAngle)
        else:
            self.setLastAngle(self.getLastAngle() - snapAngle)

        if self.getLastAngle() < -180.0:
            self.setLastAngle(self.getLastAngle() + 360.0)
        elif self.getLastAngle() > 180.0:
            self.setLastAngle(self.getLastAngle() - 360.0)

        # Move selected objects
        for selectedNode in base.direct.selected:
            selectedNode.setHpr(self.getLastAngle(), 0, 0)

        # Snap objects to grid and update DNA if necessary
        self.updateSelectedPose(base.direct.selected.getSelectedAsList())
        if base.direct.fShift:
            base.direct.grid.setSnapAngle(oldSnapAngle)

    def keyboardTranslateSelected(self, arrowDirection):
        gridToCamera = base.direct.grid.getMat(base.direct.camera)
        camXAxis = gridToCamera.xformVec(X_AXIS)
        xxDot = camXAxis.dot(X_AXIS)
        xzDot = camXAxis.dot(Z_AXIS)

        # What is the current grid spacing?
        if base.direct.fShift:
            # If shift, divide grid spacing by 10.0
            oldGridSpacing = base.direct.grid.gridSpacing
            # Use back door to set grid spacing to avoid grid update
            base.direct.grid.gridSpacing = base.direct.grid.gridSpacing / 10.0
        deltaMove = base.direct.grid.gridSpacing

        # Compute the specified delta
        deltaPos = Vec3(0)
        if abs(xxDot) > abs(xzDot):
            if xxDot < 0.0:
                deltaMove = -deltaMove
            # Compute delta
            if arrowDirection == 'right':
                deltaPos.setX(deltaPos[0] + deltaMove)
            elif arrowDirection == 'left':
                deltaPos.setX(deltaPos[0] - deltaMove)
            elif arrowDirection == 'up':
                deltaPos.setY(deltaPos[1] + deltaMove)
            elif arrowDirection == 'down':
                deltaPos.setY(deltaPos[1] - deltaMove)
        else:
            if xzDot < 0.0:
                deltaMove = -deltaMove
            # Compute delta
            if arrowDirection == 'right':
                deltaPos.setY(deltaPos[1] - deltaMove)
            elif arrowDirection == 'left':
                deltaPos.setY(deltaPos[1] + deltaMove)
            elif arrowDirection == 'up':
                deltaPos.setX(deltaPos[0] + deltaMove)
            elif arrowDirection == 'down':
                deltaPos.setX(deltaPos[0] - deltaMove)

        # Move selected objects
        for selectedNode in base.direct.selected:
            selectedNode.setPos(base.direct.grid,
                                selectedNode.getPos(base.direct.grid) + deltaPos)

        # Snap objects to grid and update DNA if necessary
        self.updateSelectedPose(base.direct.selected.getSelectedAsList())
        # Restore grid spacing
        if base.direct.fShift:
            # Use back door to set grid spacing to avoid grid update
            base.direct.grid.gridSpacing = oldGridSpacing

    def updateSelectedPose(self, selected):
        for node in selected:
            self.nodePaths[node][1] = node.getPos()
            self.nodePaths[node][2] = node.getHpr()
            self.nodePaths[node][3] = node.getScale()

            self.worldCreator.updateObject(self.nodePaths[node][0], 'Pos', tuple(node.getPos()))
            self.worldCreator.updateObject(self.nodePaths[node][0], 'Hpr', tuple(node.getHpr()))
            self.worldCreator.updateObject(self.nodePaths[node][0], 'Scale', tuple(node.getScale()))

    def keyboardXformSelected(self, arrowDirection, mode):
        if mode == 'rotate':
            self.keyboardRotateSelected(arrowDirection)
        else:
            self.keyboardTranslateSelected(arrowDirection)

    def loadResources(self):
        resourceDirectory = askdirectory()
        if not resourceDirectory:
            return

        baseDirectory = os.path.basename(os.path.normpath(resourceDirectory)) + '/'

        for root, dirs, files in os.walk(resourceDirectory):
            for fname in filter(lambda n: n.endswith('.bam'), files):
                root = root.replace('\\', '/')

                path = root + '/' + fname
                path = path.split(baseDirectory)[-1]

                self.modelPaths.add(path)

        vfs = VirtualFileSystem.getGlobalPtr()
        vfs.mount(Filename(resourceDirectory), '', 0)

        # The way this would work is that instead of the user
        # having to enter a model, every model would be
        # automatically loaded. Unfortunately, this did
        # not work as well as it was predicted, since
        # resources can contain thousands of models.
        # self.window.showResources()

    def newWorld(self, button):
        self.window.newWorldDialog.deactivate(button)
        self.window.newWorldDialog.withdraw()

        worldName = self.window.newWorldField.getvalue()
        if not worldName:
            return

        worldUid = self.getUid()

        # Start off with a basic region
        newWorld = odict([(
            'Objects', odict([(
                worldUid, odict([
                    ('Name', worldName),
                    ('Type', 'Region'),
                    ('Objects', odict())])
            )])
        )])

        self.worldCreator.fileDicts[worldName + '.world'] = newWorld

        self.currentWorld = (worldUid, worldName)

    def newLocation(self, button):
        self.window.newLocationDialog.deactivate(button)
        self.window.newLocationDialog.withdraw()

        locName = self.window.newLocationNameField.getvalue()
        if not locName:
            return

        model = self.window.newLocationModelField.getvalue()
        if model not in self.modelPaths:
            return

        if not self.currentWorld:
            return

        locUid = self.getUid()
        locShortName = locName.replace(' ', '') + 'Location'

        # Start off with a basic location
        newLocation = odict([(
            'Objects', odict([(
                locUid, odict([
                    ('Name', locShortName),
                    ('File', ''),
                    ('Type', 'Location'),
                    ('Visual', odict([
                        ('Model', model)])),
                    ('Objects', odict())])
            )])
        )])

        self.worldCreator.fileDicts[locShortName + '.world'] = newLocation

        locationData = odict([
            ('Name', locName),
            ('File', locShortName),
            ('Type', 'Location'),
            ('Pos', (0, 0, 0)),
            ('Hpr', (0, 0, 0)),
            ('Scale', (0, 0, 0)),
            ('Visual', odict([
                ('Model', model)])),
            ('Objects', odict([(
                self.getUid(), odict([
                    ('Type', 'LOD Sphere'),
                    ('Pos', (0, 0, 0)),
                    ('Hpr', (0, 0, 0)),
                    ('Scale', (0, 0, 0)),
                    ('Radi', (1000.0, 1000.0, 1000))])
            )])
        )])

        self.worldCreator.addObject(self.currentWorld[1] + '.world', self.currentWorld[0], locUid, locationData)

        self.currentLocation = (locUid, locShortName)

    def loadModel(self, model):
        node = loader.loadModel(model)
        node.reparentTo(render)

        self.nodePaths[node] = [self.getUid(), node.getPos(), node.getHpr(), node.getScale(), set()]

        traverser = self.nodeTraverser(node)
        for n in traverser:
            self.nodePaths[node][4].add(n)

    def loadWorld(self):
        worldFilename = askopenfilename(
            defaultextension = '.world',
            filetypes = (('World Files', '*.world'),),
            initialdir = 'worldData',
            title = 'Load World File',
            parent = self.window.component('hull'))
        if not worldFilename:
            return

        worldFilename = os.path.basename(os.path.normpath(worldFilename))

        self.worldCreator.makeRegion(worldFilename)

    def saveWorld(self):
        for name in self.worldCreator.fileDicts:
            fileData = self.worldCreator.fileDicts[name]

            name = name[:-6] + '.json'

            with open(name, 'w+') as f:
                f.write(dumps(fileData, indent=3))

class LevelEditorWindow(MegaToplevel):
    notify = directNotify.newCategory('LevelEditorWindow')

    def __init__(self, editor, parent=None, **kwargs):
        MegaToplevel.__init__(self, parent)

        self.editor = editor

        self.hull = self.component('hull')
        self.hull.geometry('400x625')

        self.menuFrame = Frame(self.hull, relief=GROOVE, bd=2)
        self.menuFrame.pack(fill=X)

        self.menuBar = MenuBar(self.menuFrame, hotkeys=1)
        self.menuBar.pack(side=LEFT, expand=1, fill=X)
        self.menuBar.addmenu('File', 'File')
        self.menuBar.addmenuitem('File',
                                 'command',
                                 'Load resources from directory',
                                 label='Load resources',
                                 command=self.editor.loadResources)
        self.menuBar.addmenuitem('File',
                                 'command',
                                 'Create new world',
                                 label='New world',
                                 command=self.newWorld)
        self.menuBar.addmenuitem('File',
                                 'command',
                                 'Create new location',
                                 label='New location',
                                 command=self.newLocation)
        self.menuBar.addmenuitem('File',
                                 'command',
                                 'Open world',
                                 label='Open',
                                 command=self.editor.loadWorld)
        self.menuBar.addmenuitem('File',
                                 'command',
                                 'Save world',
                                 label='Save',
                                 command=self.editor.saveWorld)

        self.notebook = NoteBook(self.hull)
        self.notebook.pack(fill=BOTH, expand=1)

        self.currentModel = ''

        self.modelPage = self.notebook.add('Models')

        self.modelLabel = Label(self.modelPage,
                                text='Models',
                                font=('Segoe UI', 14, ''))
        self.modelLabel.pack(expand=0)

        self.loadModelButton = Button(self.modelPage,
                                      text='Load model',
                                      command=self.loadModel)
        self.loadModelButton.pack(padx=20, pady=10)

        self.modelSelector = ComboBox(self.modelPage,
                                      dropdown=0,
                                      listheight=200,
                                      entry_width=30,
                                      selectioncommand=self.setModel)
        self.modelSelector.pack(expand=1, fill=BOTH)

        self.newWorldDialog = Dialog(buttons=('Create World',),
                                     title='New World',
                                     command=self.editor.newWorld)
        self.newWorldDialog.geometry('250x100')
        self.newWorldDialog.withdraw()

        self.newWorldLabel = Label(self.newWorldDialog.interior(),
                                   text='Set the name of the world')
        self.newWorldLabel.pack()

        self.newWorldField = EntryField(self.newWorldDialog.interior())
        self.newWorldField.pack(fill=BOTH, expand=1)

        self.newLocationDialog = Dialog(buttons=('Create Location',),
                                     title='New Location',
                                     command=self.editor.newLocation)
        self.newLocationDialog.geometry('350x100')
        self.newLocationDialog.withdraw()

        self.newLocationLabel = Label(self.newLocationDialog.interior(),
                                   text='Set the name then model of the location')
        self.newLocationLabel.pack()

        self.newLocationNameField = EntryField(self.newLocationDialog.interior())
        self.newLocationNameField.pack(fill=BOTH, expand=1)

        self.newLocationModelField = EntryField(self.newLocationDialog.interior())
        self.newLocationModelField.pack(fill=BOTH, expand=1)

        self.initialiseoptions(LevelEditorWindow)

    def setModel(self, model):
        if not model:
            return

        if model not in self.editor.modelPaths:
            self.modelSelector.delete(self.modelSelector.curselection()[0])
            return

        self.currentModel = model

    def loadModel(self):
        if not self.currentModel:
            return

        self.editor.loadModel(self.currentModel)

    def newLocation(self):
        self.newLocationDialog.activate()

    def newWorld(self):
        self.newWorldDialog.activate()

    def showResources(self, paths=[]):
        if not paths:
            paths = self.editor.modelPaths
        else:
            for path in paths:
                self.editor.modelPaths.add(path)

        for resource in paths:
            oldItems = self.modelSelector.get()
            if isinstance(oldItems, str):
                oldItems = ()

            self.modelSelector.setlist(oldItems + (resource,))