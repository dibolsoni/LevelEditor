from pandac.PandaModules import *

from direct.showbase.DirectObject import DirectObject
from direct.directnotify.DirectNotifyGlobal import directNotify

from tkFileDialog import askdirectory
from Tkinter import *
from Pmw import MegaToplevel, MenuBar, ComboBox
from Pmw import NoteBook

import os

class LevelEditor(NodePath, DirectObject):
    notify = directNotify.newCategory('LevelEditor')

    def __init__(self):
        NodePath.__init__(self, 'LevelEditor')

        self.modelPaths = set()

        self.window = LevelEditorWindow(self)
        self.window['title'] = 'libpandaworld Level Editor'

        base.direct.enable()

        self.reparentTo(base.direct.group)
        self.show()

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

    def loadModel(self, model):
        node = loader.loadModel(model)
        node.reparentTo(render)

class LevelEditorWindow(MegaToplevel):
    notify = directNotify.newCategory('LevelEditorWindow')

    def __init__(self, editor, parent=None, **kwargs):
        MegaToplevel.__init__(self, parent)

        self.editor = editor

        self.hull = self.component('hull')
        self.hull.geometry('400x625')

        self.resourceFrame = Frame(self.hull, relief=GROOVE, bd=2)
        self.resourceFrame.pack(fill=X)

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

    def showResources(self):
        for resource in self.editor.modelPaths:
            oldItems = self.modelSelector.get()
            self.modelSelector.setlist(oldItems + (resource,))