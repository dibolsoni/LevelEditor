from leveleditor.LevelEditor import LevelEditor

from pandac.PandaModules import *
from direct.directbase import DirectStart

loadPrcFileData('', 'window-title libpandaworld Level Editor')

base.startDirect(fWantDirect=True, fWantTk=True)

le = LevelEditor()

run()