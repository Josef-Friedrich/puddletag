#!/usr/bin/env python

"""
puddletag.py

Copyright (C) 2008 concentricpuddle

This file is part of puddletag, a semi-good music tag editor.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""


from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys, audioinfo,os, copy, puddleobjects, findfunc, actiondlg, helperwin, pdb, puddlesettings, functions, resource, threading
from puddleobjects import ProgressWin, partial, safe_name, HeaderSetting
from os import path
from audioinfo import FILENAME, PATH
from optparse import OptionParser        

class FrameCombo(QGroupBox):
    """FrameCombo(self,tags,parent=None)
    
    A group box with combos that allow to edit
    tags individually if so inclined.
    
    tags should be a list with the tags
    that each combo box should hold specified
    in the form [(Display Value, internal tag)]
    .e.g [("Artist","artist"), ("Track Number", "track")]
    
    Individual comboboxes can be accessed by using FrameCombo.combos
    which is a dictionary key = tag, value = respective combobox.
    """
    
    def __init__(self,tags = None,parent= None):
        QGroupBox.__init__(self,parent)
        self.tags = tags
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        if tags is not None:
            self.setCombos(tags)
    
    def disableCombos(self):
        for z in self.combos:
            self.combos[z].clear()
            self.combos[z].setEnabled(False)
    
    def setCombos(self, tags, rows = None):
        """Creates a vertical column of comboboxes.
        tags are tags is usual in the (tag, backgroundvalue) case[should be enumerable].
        rows are a dictionary with each key being a list of the indexes of tags that should
        be one one row.
        
        E.g Say you wanted to have the artist, album, title, and comments on
        seperate rows. But then you want year, genre and track on one row. With that
        row being before the comments row. You'd do something like...
        
        >>>tags = [('Artist', 'artist'), ('Title', 'title'), ('Album', 'album'), 
        ...        ('Track', 'track'), ("Comments",'comment'), ('Genre', 'genre'), (u'Year', u'date')]
        >>>rows = {0:[0], 1:[1], 2:[2], 3[3,4,6],4:[5]
        >>>f = FrameCombo()
        >>>f.setCombo(tags,rows)"""
        
        #FIXME: This code is to change the comboboxes while the app is running.
        #But it doesn't work well. So, until I figure it out. You'll just
        #have to restart the app to see the results.
        #if hasattr(self, "combos"): # self.combos does not exist the first time this is called.
            #for z in range(self.vbox.count()):
                #x = self.vbox.itemAt(z)
                #y = x.layout()
                #if y is not None:
                    #while y.count() !=0:
                        #y.removeWidget(y.takeAt(0).widget())
                #del(y)
                #del(x)
        #else:
        self.combos = {}   
        self.labels = {}             

        j = 0
        hbox = [1] * (len(rows) * 2)
        for row in sorted(rows.values()):
            hbox[j] = QHBoxLayout()
            hbox[j + 1] = QHBoxLayout()
            for tag in [tags[z] for z in row]:
                tagval = tag[1]
                self.labels[tagval] = QLabel(tag[0])                
                self.combos[tagval] = QComboBox()
                self.combos[tagval].setInsertPolicy(QComboBox.NoInsert)
                hbox[j].addWidget(self.labels[tagval])
                hbox[j + 1].addWidget(self.combos[tagval])                
            self.vbox.addLayout(hbox[j])
            self.vbox.addLayout(hbox[j + 1])
            j+=2
                    
        self.vbox.addStretch()
        
    def initCombos(self):
        """Clears the comboboxes and adds two items, <keep> and <blank>.
        If <keep> is selected and the tags in the combos are saved, 
        then they remain unchanged. If <blank> is selected, then the tag is removed"""
        for combo in self.combos:
            self.combos[combo].clear()
            self.combos[combo].setEditable(True)
            self.combos[combo].addItems(["<keep>", "<blank>"])
            self.combos[combo].setEnabled(False)
        
        if 'genre' in self.combos:
            from mutagen.id3 import TCON
            self.combos['genre'].addItems(TCON.GENRES)
    
    def reloadCombos(self, tags):
        self.setCombos(tags)
        

class DirView(QTreeView):
    """The treeview used to select a directory."""
    def __init__(self,parent = None):
        QTreeView.__init__(self,parent)
        self.header().setStretchLastSection(True)
    
    def selectionChanged(self,selected,deselected):
        self.emit(SIGNAL("itemSelectionChanged()"))
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.reject()
        
    def mouseMoveEvent(self, event):
        pnt = QPoint(*self.StartPosition)
        if (event.pos() - pnt).manhattanLength()  < QApplication.startDragDistance():
            return
        drag = QDrag(self)
        mimedata = QMimeData()
        mimedata.setUrls([QUrl(self.model().filePath(self.currentIndex()))])
        drag.setMimeData(mimedata)
        drag.setHotSpot(event.pos() - self.rect().topLeft())
        dropAction = drag.start(Qt.MoveAction)
        
    def mousePressEvent(self, event):
        if event.buttons() == Qt.RightButton:
            self.contextMenuEvent(event)
        if event.buttons() == Qt.LeftButton:
            self.StartPosition = [event.pos().x(), event.pos().y()]
        QTreeView.mousePressEvent(self, event)

class TableHeader(QHeaderView):
    """A headerview put here simply to enable the contextMenuEvent
    so that I can show the edit columns menu.
    
    Call it with tags in the usual form, to set the top header."""
    def __init__(self, orientation, tags = None, parent = None):
        QHeaderView.__init__(self, orientation, parent)
        if tags is not None: self.tags = tags
        self.setClickable(True)
        self.setHighlightSections(True)
    
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        settings = menu.addAction("&Select Columns")
        self.connect(settings, SIGNAL('triggered()'), self.setTitles)
        menu.exec_(event.globalPos())
    
    def mousePressEvent(self,event):
        if event.button == Qt.RightButton:
            self.contextMenuEvent(event)
            return
        QHeaderView.mousePressEvent(self, event)
        
    def setTitles(self):
        if hasattr(self, "tags"):
            self.win = HeaderSetting(self.tags)
        else:
            self.win = HeaderSetting()
        self.win.setModal(True)
        self.win.show()
        self.connect(self.win, SIGNAL("headerChanged"), self.headerChanged)
    
    def headerChanged(self, val):
        self.emit(SIGNAL("headerChanged"), val)
    
        
class TableWindow(QSplitter):
    """It's called a TableWindow just because
    the main widget is a table even though it uses a splitter.
    
    The table allows the editing of tags and stuff like that. 
    
    Important methods are:
    inittable -> Creates table, gets defaults values and shit
    fillTable -> Fills the table with tags from the folder specified.
    setNewHeader -> Sets the header of the table to what you want. 
                    tags are specified in the usual way"""
    
    def __init__(self, headerdata = None, parent=None):
        QSplitter.__init__(self,parent)
        #I would really like to know why this doesn't work.
        self.gridvisible = property(self.getGridVisible, self.setGridVisible)

    def inittable(self, headerdata):
        """This is here, because I want to be able to initialize
        many of the tables values from other functions
        (like when the app starts and setting are being restored).
        
        Call it with headerdata(as usual) to set the titles."""
        self.table = puddleobjects.TableShit(headerdata, self)
        self.headerdata = headerdata
        header = TableHeader(Qt.Horizontal, self.headerdata, self)
        header.setSortIndicatorShown(True)
        self.table.setHorizontalHeader(header)
        self.tablemodel = self.table.model()
        
        grid = QGridLayout()
        grid.addWidget(self.table)
        self.setLayout(grid)        
        
        self.connect(self.table.horizontalHeader(), SIGNAL("sectionClicked(int)"),
             self.sortTable)
        self.connect(header, SIGNAL("headerChanged"), self.setNewHeader)
        
    def setNewHeader(self, tags):
        """Used for 'hotswapping' of the table header.
        
        If you want to set the table header while the app
        is running, then this is the methods you should use.
        
        tags are a list of tags defined as usual(See FrameCombo's docstring).
        
        Nothing is returned, if the function is successful, then you should
        see the correct results."""
        sortedtag = copy.copy(self.headerdata[self.sortColumn])
        model = self.table.model()
        
        if len(self.headerdata) < len(tags):
            model.insertColumns(len(self.headerdata) - 1, len(tags) - 1)
        
        columnwidths = [[tag, self.table.columnWidth(index)] for index, tag in enumerate(self.headerdata)]
        
        if len(self.headerdata) > len(tags):
            #I'm removing one column at a time, because removing many at a time, doesn't
            #seem work well all the time(I think this is a problem early versions of PyQt).
            #This works(All the time I think).
            [model.removeColumn(0) for z in xrange(len(tags), len(self.headerdata))]
        
        [model.setHeaderData(i, Qt.Horizontal, v, Qt.DisplayRole) for i,v in enumerate(tags)]            
        
        for z in columnwidths:
            if z[0] in self.headerdata:
                self.table.setColumnWidth(self.headerdata.index(z[0]), z[1])
        
        #self.headerdata = model.headerdata
        self.table.horizontalHeader().tags = self.headerdata
        
        if sortedtag in self.headerdata:
            self.sortTable(self.headerdata.index(sortedtag))
        else:
            self.sortTable(self.sortColumn)

    def sortTable(self,column):
        self.sortColumn = column
        self.table.sortByColumn(column)
        #FIXME: Using setFocus because the table isn't updated like it should be.
        #To see, load a folder, the load another folder with the same number of files.
        self.setFocus()
        
    def fillTable(self,folderpath, appendtags = False):
        """See TableShit's fillTable method for more details."""
        self.table.fillTable(folderpath, appendtags)
        self.sortTable(self.sortColumn)
        
    def setGridVisible(self, val):
        if (val is True) or (val > 0):
            self.table.setGridStyle(Qt.SolidLine)
        else:
            self.table.setGridStyle(Qt.NoPen)
            
    def getGridVisible(self):
        if self.table.gridStyle() > 0:
            return True
        else:
            return False
        

class MainWin(QMainWindow):
    """The brain of puddletag. Everything happens here.
    
    If you happen to"""
    def __init__(self):
        #Things to remember when editing this function:
        #1. If you add a QAction, add it to self.actions. 
        #It's a list that's disabled and enabled depending on state of the app.
        #I also have a pretty bad convention of having action names in lower
        #case and the action's triggered() slot being the action name in
        #camelCase
        
        QMainWindow.__init__(self)
        
        #Shows or doesn't show path in titlebar of current folder
        self.pathinbar = False
        
        self.setWindowTitle("puddletag")
        self.cenwid = TableWindow()
                
        self.dirmodel = QDirModel()
        self.dirmodel.setSorting(QDir.IgnoreCase)
        self.dirmodel.setFilter(QDir.Dirs | QDir.NoDotAndDotDot)
        self.dirmodel.setReadOnly(False)
        
        self.tree = DirView()
        self.tree.setModel(self.dirmodel)
        [self.tree.hideColumn(column) for column in range(1,4)]
        self.tree.setDragEnabled(True)
        
        #Action for opening a folder
        #self.opendir =  QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), '&Open Folder...', self)
        self.opendir =  QAction(QIcon(':/open.png'), '&Open Folder...', self)
        self.opendir.setShortcut('Ctrl+O')
        self.connect(self.opendir, SIGNAL('triggered()'), self.openFolder)
        
        #Action for adding another folder
        self.addfolder = QAction(QIcon(':/fileimport.png'), '&Add Folder...', self)
        self.connect(self.addfolder, SIGNAL('triggered()'), self.addFolder)
        
        #Action for saving tags in combos
        self.savecombotags = QAction(QIcon(':/save.png'), '&Save', self)
        self.savecombotags.setShortcut('Ctrl+S')
        self.connect(self.savecombotags,SIGNAL("triggered()"), 
                            self.saveCombos)
        
        #Action for importing tags from files
        self.tagfromfile = QAction(QIcon(':/filetotag.png'), 
                                    '&File -> Tag', self)
        self.connect(self.tagfromfile, SIGNAL("triggered()"), 
                                    self.getTagFromFile)
        self.tagfromfile.setShortcut('Ctrl+F')

        self.tagtofile = QAction(QIcon(':/tagtofile.png'), 
                                            'Tag -> &File', self)
        self.connect(self.tagtofile,SIGNAL("triggered()"), self.saveTagToFile)
        self.tagtofile.setShortcut('Ctrl+T')
        
        #Shows the Action editor.
        self.openactions = QAction(QIcon(':/cap.png'), 'Ac&tions...', self)
        self.connect(self.openactions, SIGNAL("triggered()"), self.openActions)
        
        #Autonumbering shit
        self.changetracks = QAction(QIcon(':/track.png'), 'Autonumbering &Wizard...', self)
        self.connect(self.changetracks, SIGNAL('triggered()'), self.trackWizard)
        
        #Action for quick actions
        self.actionvalue = partial(self.openActions, True)
        self.quickactions = QAction(QIcon(":/cap.png"), "&Quick Actions...", self)
        self.connect(self.quickactions, SIGNAL("triggered()"), self.actionvalue)
        
        #Renames a directory based on the pattern in self.patterncombo
        self.renamedir = QAction(QIcon(":/rename.png"), "&Rename Dir...",self)
        self.connect(self.renamedir, SIGNAL("triggered()"), self.renameFolder)
        
        #Imports a file to read tags from.
        self.importfile = QAction(QIcon(":/import.png"), "Te&xt File -> Tag",self)
        self.connect(self.importfile, SIGNAL("triggered()"), self.importFile)
        
        #Open's the preferences window.
        self.preferences = QAction("&Preferences...", self)
        self.connect(self.preferences, SIGNAL("triggered()"), self.openPrefs)
        
        #Format value
        self.formattag = QAction("&Format Selected...", self)
        self.connect(self.formattag, SIGNAL("triggered()"), self.formatValue)
        
        self.selectall = QAction("Select &All", self)
        self.selectall.setShortcut("Ctrl+A")
        
        self.undo = QAction("&Undo", self)
        self.undo.setShortcut("Ctrl+Z")
        
        self.cleartable = QAction("&Clear", self)
        self.connect(self.cleartable, SIGNAL("triggered()"),self.clearTable)
        
        self.reloaddir = QAction("Reload", self)
        
        self.invertselection = QAction("&Invert selection", self)
        self.invertselection.setShortcut('Meta+I')
        
        self.autotagging = QAction("Musicbrain&z", self)        
        self.connect(self.autotagging, SIGNAL("triggered()"), self.autoTagging)
        
        self.showfilter = QAction("Show Filter", self)
        self.showfilter.setCheckable(True)
        self.showfilter.setShortcut("F3")
        
        self.exttags = QAction("E&xtended Tags", self)

        
        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(self.opendir)
        file.addAction(self.addfolder)
        file.addSeparator()
        file.addAction(self.savecombotags)
        file.addAction(self.cleartable)
        file.addAction(self.reloaddir)
        
        edit = menubar.addMenu("&Edit")
        edit.addAction(self.undo)
        edit.addAction(self.showfilter)
        edit.addAction(self.selectall)
        edit.addAction(self.invertselection)
        edit.addAction(self.preferences)
        
        
        convert = menubar.addMenu("&Convert")
        convert.addAction(self.tagfromfile)
        convert.addAction(self.tagtofile)
        convert.addAction(self.renamedir)
        convert.addAction(self.importfile)
        
        actionmenu = menubar.addMenu("&Actions")
        actionmenu.addAction(self.openactions)
        actionmenu.addAction(self.quickactions)
        actionmenu.addAction(self.formattag)
        
        toolmenu = menubar.addMenu("&Tools")
        toolmenu.addAction(self.autotagging)
        toolmenu.addAction(self.exttags)
        
        
        self.patterncombo = QComboBox()
        self.patterncombo.setEditable(True)
        self.patterncombo.setToolTip("Enter a pattern here.")
        self.patterncombo.setStatusTip(self.patterncombo.toolTip())
        self.patterncombo.setMinimumWidth(500)
        self.patterncombo.setDuplicatesEnabled(False)
        
        self.toolbar = self.addToolBar("My Toolbar")
        self.actions = [self.opendir, self.savecombotags, self.undo, self.tagfromfile, self.tagtofile,
                        self.openactions, self.changetracks, self.addfolder, self.renamedir, self.importfile,
                        self.quickactions, self.formattag, self.reloaddir, self.autotagging]
                        
        [self.toolbar.addAction(action) for action in self.actions]
        self.toolbar.insertWidget(self.actions[3], self.patterncombo)
        
        self.statusbar = self.statusBar()
        self.label = QLabel()
        self.label.setFrameStyle(QFrame.NoFrame)
        self.statusbar.addPermanentWidget(self.label,1)
        self.connect(self.statusbar,SIGNAL("messageChanged (const QString&)"), self.label.setText)
        
        self.combogroup = FrameCombo()
        self.combogroup.setMinimumWidth(200)
                                         
        self.splitter = QSplitter(Qt.Horizontal)
        self.hsplitter = QSplitter(Qt.Vertical)
        self.hsplitter.addWidget(self.combogroup)
        self.hsplitter.addWidget(self.tree)
        self.hsplitter.setStretchFactor(1,1)
        
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Filter"))
        self.filtertable = QComboBox()
        self.filtertable.addItems(["None","__all"] + sorted([z for z in audioinfo.REVTAGS]))
        self.filtertable.setEditable(True)
        self.filtertext = QLineEdit()
        self.connect(self.filtertext, SIGNAL("textChanged(QString)"), self.filterTable)
        self.connect(self.filtertable, SIGNAL("editTextChanged(QString)"), self.filterTable)
        
        hbox.addWidget(self.filtertable,0)
        hbox.addWidget(self.filtertext,1)
        self.splitter.addWidget(self.hsplitter)
        self.splitter.addWidget(self.cenwid)
        self.splitter.setStretchFactor(1,1)
        self.filterframe = QWidget()
        self.filterframe.setLayout(hbox)
        self.filterframe.setMaximumHeight(self.filterframe.sizeHint().height())
        
        self.vsplitter = QSplitter(Qt.Vertical)
        self.vsplitter.addWidget(self.splitter)
        self.vsplitter.addWidget(self.filterframe)
        self.vsplitter.setStretchFactor(0,0)
        self.setCentralWidget(self.vsplitter)
        
        self.connect(self.showfilter, SIGNAL("toggled(bool)"), self.filterframe.setVisible) #frame.setVisible doesn't work when loading
        self.loadInfo()
        
        self.connect(self.exttags, SIGNAL("triggered()"), self.cenwid.table.editFile)
        self.connect(self.undo, SIGNAL("triggered()"), self.cenwid.table.model().undo)
        self.connect(self.selectall, SIGNAL("triggered()"), self.cenwid.table.selectAll)
        self.connect(self.invertselection, SIGNAL("triggered()"), self.cenwid.table.invertSelection)
        self.connect(self.patterncombo, SIGNAL("editTextChanged(QString)"), self.patternChanged)
        self.connect(self.tree, SIGNAL('itemSelectionChanged()'), self.openTree)
        self.connect(self.cenwid.table, SIGNAL('itemSelectionChanged()'), self.rowEmpty)
        self.connect(self.cenwid.table, SIGNAL('removedRow()'), self.rowEmpty)
        self.connect(self.tree, SIGNAL('addFolder'), self.openFolder)
        self.connect(self.cenwid.table, SIGNAL('itemSelectionChanged()'),
                                         self.fillCombos)
    
    def filterTable(self, text ,*args):
        tag = unicode(self.filtertable.currentText())
        text = unicode(self.filtertext.text())
        if text == u"":
            tag = u"None"
        table = self.cenwid.table
        if tag == u"None":
            [table.showRow(z) for z in range(table.rowCount())]
        elif tag == u"__all":
            for z in range(table.rowCount()):
                table.hideRow(z)
                for y in table.rowTags(z).values():
                    if (y is not None) and (text in unicode(y)):
                        table.showRow(z)
                        break
                    
        else:
            for z in range(table.rowCount()):
                if (tag in table.rowTags(z)) and (text in table.rowTags(z)[tag]):
                    table.showRow(z)
                else:
                    table.hideRow(z)
        
    def autoTagging(self):
        from webdb import MainWin
        win = MainWin(self.cenwid.table, self)
        win.show()
    
                                             
    def loadShortcuts(self):
        settings = QSettings()
        controls = {'table':self.cenwid.table,'patterncombo':self.patterncombo, 'main':self}
        size = settings.beginReadArray('Shortcuts')
        if size <= 0:            
            settings = QSettings(":/puddletag.conf", QSettings.IniFormat)
            size = settings.beginReadArray('Shortcuts')
        
        for z in xrange(size):
            settings.setArrayIndex(z)
            control = "" #So that if control is defined incorrectly, no error is raised.
            try:
                control = controls[unicode(settings.value("control").toString())]
            except KeyError:
                val = unicode(settings.value("control").toString())
                if val.startswith("combo") and val[len('combo'):] in self.combogroup.combos:
                    control = self.combogroup.combos[val[len('combo'):]]
            command = unicode(settings.value("command").toString())
            key = settings.value("key").toString()
            if hasattr(control, command):
                QShortcut(key, self, getattr(control,command))
        settings.endArray()
    
    def changefocus(self):
        controls = [self.cenwid.table, self.patterncombo]
        if self.combogroup.combos:
            #Found it by trial and error
            combo = self.combogroup.layout().itemAt(3).layout().itemAt(0).widget()
            controls.append(combo)
        if not hasattr(self, "currentfocus"):
            try:
                self.currentfocus = [i for i,control in enumerate(controls) if control.hasFocus()][0]
            except IndexError: #None of these control have focus
                self.currentfocus = len(controls) + 1
        if (self.currentfocus < (len(controls)-1)) :
            self.currentfocus +=1
        else:
            self.currentfocus = 0
        controls[self.currentfocus].setFocus()

    def loadInfo(self):
        """Loads the settings from puddletags settings and sets it."""
        settings = QSettings()
        defaultsettings = QSettings(":/puddletag.conf", QSettings.IniFormat)
        
        self.lastFolder = unicode(settings.value("main/lastfolder", QVariant(QDir.homePath())).toString())
        maximise = settings.value('main/maximized', QVariant(Qt.WindowMaximized)).toBool()
        if maximise:
            self.setWindowState(Qt.WindowMaximized)
        else:
            height = settings.value('main/height', QVariant(600)).toInt()[0]
            width = settings.value('main/width', QVariant(800)).toInt()[0]
            self.resize(width, height)
            self.setWindowState(Qt.WindowNoState)
        
        titles = list(settings.value("editor/titles").toStringList())
        tags = list(settings.value("editor/tags").toStringList())
        
        if len(titles) == 0:
            titles = list(defaultsettings.value("editor/titles").toStringList())
            tags = list(defaultsettings.value("editor/tags").toStringList())
        
        headerdata = []
        for title, tag in zip(titles, tags):
            headerdata.append((unicode(title),unicode(tag)))
        
        self.cenwid.inittable(headerdata)
        self.connect(self.cenwid.table.model(), SIGNAL('enableUndo'), self.undo.setEnabled)
        self.connect(self.cenwid.table.model(), SIGNAL('dataChanged (const QModelIndex&,const QModelIndex&)'), self.fillCombos)
        self.connect(self.cenwid.table.model(), SIGNAL('dataChanged (const QModelIndex&,const QModelIndex&)'), self.filterTable)
        
        columnwidths = settings.value("editor/Column").toStringList()
        if len(columnwidths) == 0:
            columnwidths = defaultsettings.value("editor/Column").toStringList()       
        [self.cenwid.table.setColumnWidth(i,int(z)) for i,z in enumerate(columnwidths)]
        
        sortColumn = settings.value("Table/sortColumn",QVariant(1)).toInt()[0]
        
        self.cenwid.sortTable(sortColumn)        
        
        self.cenwid.table.playcommand = [unicode(z) for z in
             settings.value("Table/PlayCommand",QVariant(["xmms"])).toStringList()]
        
        self.patterncombo.clear()
        self.patterncombo.addItems(settings.value("editor/patterns").toStringList())
        if self.patterncombo.count() == 0:
            self.patterncombo.addItems(defaultsettings.value("editor/patterns").toStringList())    
        
        self.splitter.restoreState(settings.value("splittersize").toByteArray())
        self.hsplitter.restoreState(settings.value("hsplittersize").toByteArray())
        
        win = puddlesettings.MainWin(self, readvalues = True)
        self.connect(self.reloaddir, SIGNAL("triggered()"),self.cenwid.table.reloadFiles)
        showfilter = settings.value("editor/showfilter",QVariant(False)).toBool()
        self.showfilter.setChecked(showfilter)
        self.filterframe.setVisible(showfilter)
        self.loadShortcuts()

        
    def clearTable(self):
        self.cenwid.table.model().taginfo = []
        self.cenwid.table.model().reset()
        self.fillCombos()

    def openFolder(self, filename = None, appenddir = False):
        """Opens a folder. If filename != None, then
        the table is filled with the folder.
        
        If filename is None, show the open folder dialog and open that.
        
        If appenddir = True, the folder is appended.
        Otherwise, the folder is just loaded."""
        selectionChanged = SIGNAL("itemSelectionChanged()")
        
        self.disconnect(self.tree, selectionChanged, self.openTree)
        self.disconnect(self.cenwid.table, selectionChanged, self.patternChanged)        
        if filename is None: 
            filedlg = QFileDialog()
            filedlg.setFileMode(filedlg.DirectoryOnly)
            filename = unicode(filedlg.getExistingDirectory(self,
                'OpenFolder', self.lastFolder ,QFileDialog.ShowDirsOnly))
        
        if len(filename) == 1:
            filename = filename[0]
        if type(filename) is unicode or type(filename) is str:
            if path.isdir(filename):
                #I'm doing this just to be safe.
                filename = path.realpath(filename)
                self.lastFolder = filename
                if not appenddir:
                    self.tree.setCurrentIndex(self.dirmodel.index(filename))
                self.cenwid.fillTable(filename, appenddir)
                if self.pathinbar:                
                    self.setWindowTitle("puddletag " + filename)
                else:
                    self.setWindowTitle("puddletag")
        else:
            self.cenwid.fillTable(filename, appenddir)
            self.setWindowTitle("Puddletag")

        self.connect(self.cenwid.table, selectionChanged, self.patternChanged)
        self.connect(self.tree, selectionChanged, self.openTree)
        self.cenwid.table.setFocus()
        self.fillCombos()
        
    def openTree(self, filename = None):
        """If a folder in self.tree is clicked then it should be opened.
        
        If filename is not None, then nothing is opened. The currently
        selected index is just set to that filename."""
        selectionChanged = SIGNAL("itemSelectionChanged()")
        if filename is None:
            filename = unicode(self.dirmodel.filePath(self.tree.selectedIndexes()[0]))
            self.openFolder(filename)
        else:
            self.disconnect(self.tree, selectionChanged, self.openTree)
            index = self.dirmodel.index(filename)
            self.tree.setCurrentIndex(index)
            self.connect(self.tree, selectionChanged, self.openTree)
        
    def addFolder(self, filename = None):
        """Appends a folder. If filename is None, then show a dialog to
        open a folder first. Otherwise open the folder, filename"""
        if filename is None:
            self.openFolder(None, True)
        else:
            self.openFolder(filename, True)
                    
    def setTag(self, row, tag = None, rename = False):
        if row is True:
            self.cenwid.table.model().undolevel += 1
            return
        level = self.cenwid.table.model().undolevel
        rowtags = self.cenwid.table.rowTags(row)
        mydict = {}
        try:
            for z in tag:
                if z not in rowtags:
                    mydict[z] = ""
                else:
                    mydict[z] = rowtags[z]
            tag[level] = mydict
        except TypeError: #If tag is none, or not a dictionary
            return
        self.cenwid.table.updateRow(row, tag, justrename = rename)

    def fillCombos(self, **args):
        """Fills the QComboBoxes in FrameCombo with
        the tags selected from self.table. """
        
        #import time
        #print "run"
        #print time.strftime("%H : %M : %S")
        table = self.cenwid.table
        combos = self.combogroup.combos
        
        if not hasattr(table, "selectedRows") or (table.rowCount() == 0) or not table.selectedRows:
            self.combogroup.disableCombos()
            return        
        self.combogroup.initCombos()        
        tags  = {}
        prevaudio = {}
        #Removes all duplicate entries for the combos
        #Using the set type doesn't seem to work all the time.
        for index,row in enumerate(table.selectedRows):
            audio = table.rowTags(row)
            [tags[tag].append("") for tag in tags if tag not in audio]
            for tag in audio:
                if tag not in tags:
                    tags[tag] = []
                    if index > 0:
                        tags[tag].append("")
                if prevaudio == {}:
                    tags[tag].append(audio[tag])
                else:
                    try:
                        if prevaudio[tag] != audio[tag]:
                            tags[tag].append(audio[tag])
                    except KeyError: #prevaudio doesn't have the tag in audio.
                        tags[tag].append(audio[tag])
            prevaudio = audio.copy()
        
        #Add values to combos
        for tagset in tags:
            [combos[tagset].addItem(unicode(z)) for z in sorted(tags[tagset])
                    if combos.has_key(tagset)]
            
            
        for combo in combos.values():
            combo.setEnabled(True)
            #If a QCombo has more than 3 it's not more than one artist, so we
            #set it to the defaultvalue. 
            if (combo.count() > 3) or (combo.count() < 2):
                combo.setCurrentIndex(0)
            else:                 
                combo.setCurrentIndex(2)
                
        if 'genre' in tags and len(tags['genre']) == 1:            
            combo = combos['genre']
            index = combo.findText(tags['genre'][0])
            if index > -1:
                combo.setCurrentIndex(index)
            else:
                combo.setCurrentIndex(0)
                        
    def saveCombos(self):
        """Writes the tags of the selected files to the values in self.combogroup.combos."""
        combos = self.combogroup.combos
        table = self.cenwid.table
        if (not hasattr(table,'selectedRows')) or (not table.selectedRows):
            return
        win = ProgressWin(self, len(table.selectedRows), table)
        model = table.model()
        showmessage = True
        
        self.disconnect(self.cenwid.table.model(), SIGNAL('dataChanged (const QModelIndex&,const QModelIndex&)'), self.fillCombos)
        for row in table.selectedRows:
            if win.wasCanceled(): break
            tags = {}
            for tag in combos:
                try:
                    curtext = unicode(combos[tag].currentText())
                    if curtext == "<blank>": tags[tag] = ""
                    elif curtext == "<keep>": pass
                    else:
                        tags[tag] = unicode(combos[tag].currentText())
                except KeyError:
                    pass
            win.updateVal()
            try:
                self.setTag(row, tags.copy())
            except (IOError, OSError):
                if showmessage:
                    win.show()
                    mb = QMessageBox('Error', "I couldn't write to:\n" + table.rowTags(row)[FILENAME]+ 
                    ", because it may be write-protected.\nDo you want me to continue writing tags to the rest?", 
                        QMessageBox.Critical,
                        QMessageBox.Yes  or QMessageBox.Default, QMessageBox.No or QMessageBox.Escape , QMessageBox.YesAll, self)
                    ret = mb.exec_()
                    if ret == QMessageBox.Yes:
                        continue
                    if ret == QMessageBox.YesAll:
                        showmessage = False
                    else:
                        break
        self.setTag(True)
        self.connect(self.cenwid.table.model(), SIGNAL('dataChanged (const QModelIndex&,const QModelIndex&)'), self.fillCombos)
        win.close()

    def formatValue(self):
        if hasattr(self, "prevfunc"):
            f = actiondlg.CreateFunction(prevfunc = self.prevfunc, parent = self, showcombo = False)
        else:
            f = actiondlg.CreateFunction(parent = self, showcombo = False)
        f.setModal(True)
        f.show()
        self.connect(f, SIGNAL("valschanged"), self.formatValueBuddy)
    
    def formatValueBuddy(self, func):
        self.prevfunc = func
        table = self.cenwid.table        
        win = ProgressWin(self, len(table.selectedRows), table)
        headerdata = self.cenwid.headerdata
        showmessage = True
        
        for row in table.selectedRows:
            if win.wasCanceled(): break
            tags = {}
            for column in table.selectedTags()[row]:
                try:
                    tags[headerdata[column][1]] = table.rowTags(row)[headerdata[column][1]]
                except KeyError: #The key doesn't consist of any text
                    pass                
            for tag in tags:
                try:
                    if func.function.func_code.co_varnames[0] == 'tags':
                        val = func.runFunction(table.rowTags(row))
                    else:
                        val = func.runFunction(tags[tag])
                    if val is not None:
                        tags[tag] = val
                except KeyError:
                    pass
            win.updateVal()
            try:
                self.setTag(row,tags)
            except (IOError, OSError):
                if showmessage:
                    win.show()
                    errormsg = "I couldn't write to:\n" + table.rowTags(row)[FILENAME] + "Do you want to continue formatting the rest?"
                    mb = QMessageBox('Error', errormsg , QMessageBox.Warning, QMessageBox.Yes or QMessageBox.Default,
                        QMessageBox.No or QMessageBox.Escape, QMessageBox.YesAll, self)
                    ret = mb.exec_()
                    if ret == QMessageBox.No:
                        break
                    elif ret == QMessageBox.YesAll:
                        showmessage = False
        self.setTag(True)
        win.close()
        self.fillCombos()
                        
    def importFile(self):
        """Opens a text file so that tags can be
        read from it."""
        filedlg = QFileDialog()
        foldername = self.cenwid.table.rowTags(self.cenwid.table.selectedRows[0])["__folder"]
        filename = unicode(filedlg.getOpenFileName(self,
                'OpenFolder',foldername))
        
        if filename != "":
            win = helperwin.ImportWindow(self, filename)
            win.setModal(True)
            patternitems = [self.patterncombo.itemText(z) for z in range(self.patterncombo.count())]
            win.patterncombo.addItems(patternitems)
            self.connect(win,SIGNAL("Newtags"), self.setSelectedTags)
            self.fillCombos()
            
    def setSelectedTags(self, taglist):
        """Sets the selected files' tags to the tags
        in taglist. This method, while useful isn't general enough
        to be used by other methods that do writing of many tags.
        """
        win = ProgressWin(self, len(self.cenwid.table.selectedRows))
        for i,z in enumerate(self.cenwid.table.selectedRows):
            if win.wasCanceled(): break
            try:
                self.setTag(z, taglist[i])
            except IndexError:
                break
            win.updateVal()
        self.setTag(True)
        win.close()
                                        
    def renameFolder(self, test = False):
        """This is best explained with an example.
        
        Okay, let's say that you've selected a file and want
        to rename the files directory based on that file.
        This function renames the directory using the
        pattern in self.patterncombo.
        
        If test is True then the new filename is returned
        and nothing else is done."""
        from findfunc import tagtofilename
        selectionChanged = SIGNAL('itemSelectionChanged()')
        table = self.cenwid.table
        currentdir = table.rowTags(table.selectedRows[0])
        oldir = os.path.dirname(currentdir['__folder'])
        newfolder = os.path.join(oldir, os.path.basename(tagtofilename(unicode(self.patterncombo.currentText()), currentdir)))
        
        if test == True:            
            return unicode("Rename: <b>") + currentdir["__folder"] + unicode("</b> to: <b>") + newfolder + u'</b>'
        
        dirname = os.path.dirname
        basename = os.path.basename
        path = os.path
        
        folders = [[row, table.rowTags(row)["__folder"]] for row in table.selectedRows]
        newdirs = []
        for z in folders:
            if z[1] not in (z[1] for z in newdirs):
                newdirs.append(z)

        self.disconnect(self.cenwid.table, selectionChanged, self.patternChanged)
        self.disconnect(self.tree, selectionChanged, self.openTree)            
        for z in newdirs:
            currentdir = z[1]
            newfolder = path.join(dirname(z[1]), (basename(tagtofilename(unicode(self.patterncombo.currentText()), table.rowTags(z[0])))))
            result = QMessageBox.question (None, unicode("Rename Folder?"), 
                        unicode("Are you sure you want to rename \n ") + currentdir + unicode("\n to \n") + newfolder, 
                        "&Yes", "&No","", 1, 1)
            
            if result == 0:
                try:
                    idx = self.dirmodel.index(currentdir)
                    os.rename(currentdir, newfolder)
                    self.cenwid.table.model().changeFolder(currentdir, newfolder)
                    self.dirmodel.refresh(self.dirmodel.parent(idx))
                    self.tree.setCurrentIndex(self.dirmodel.index(newfolder))
                except (IOError, OSError), detail:
                    QMessageBox.information(self, 'Message',
                    unicode( "I couldn't rename\n") + currentdir + unicode(" to \n") +
                        newfolder + unicode("\nError: ") + unicode(detail.strerror), QMessageBox.Ok)
        self.connect(self.tree, selectionChanged, self.openTree)
        self.connect(self.cenwid.table, selectionChanged, self.patternChanged)
        self.fillCombos()
            
    def rowEmpty(self):
        """If nothing's selected or if self.cenwid.table's empty, 
        disable what needs to be disabled."""
        #An error gets raised if the table's empty.
        #So we disable everything in that case
        try:
            if self.cenwid.table.selectedRows != []:
                [action.setEnabled(True) for action in self.actions[3:]]
                self.patterncombo.setEnabled(True)
                self.exttags.setEnabled(True)
                return
        except AttributeError:
                pass
        
        [action.setEnabled(False) for action in self.actions[3:]]
        self.exttags.setEnabled(False)
        self.patterncombo.setEnabled(False)
        
    def trackWizard(self):
        """Shows the autonumbering wizard and sets the tracks
            numbers should be filled in"""        
        
        row = self.cenwid.table.selectedRows[0]
        numtracks = len(self.cenwid.table.selectedRows)
        enablenumtracks = False
        
        try:
            mintrack = min([long(self.cenwid.table.rowTags(row)["track"]) \
                                for row in self.cenwid.table.selectedRows])
        except KeyError:
            #No track was specified, just set it to 1
            mintrack = 1
        except ValueError:
            #The tracks are probably in trackno/numtracks format
            mintrack = self.cenwid.table.rowTags(row)["track"]
            try:
                mintrack = long(mintrack[:mintrack.find("/")])
                enablenumtracks = True
            except ValueError:
                #Tracks are probably text, so we make them numbers
                mintrack = 1
                
        win = helperwin.TrackWindow(self, mintrack, numtracks, enablenumtracks)
        win.setModal(True)
        self.connect(win, SIGNAL("newtracks"), self.numberTracks)
        win.show()

    
    def numberTracks(self, indexes):
        """Numbers the selected tracks sequentially in the range
        between the indexes.
        The first item of indices is the starting track.
        The second item of indices is the number of tracks."""
        fromnum = indexes[0]
        if indexes[1] != "":
            num = "/" + indexes[1]
        else: num = ""
        rows = self.cenwid.table.selectedRows
        taglist = [{"track": unicode(z) + num} for z in range(fromnum, fromnum + len(rows) + 1)]
        showmessage = True
        win = ProgressWin(self, len(self.cenwid.table.selectedRows), self.cenwid.table)
        for i,z in enumerate(self.cenwid.table.selectedRows):
            if win.wasCanceled(): break
            try:
                self.setTag(z, taglist[i])
            except IndexError:
                break
            except (IOError, OSError), detail:
                if showmessage:
                    win.show()
                    errormsg = "".join(["I couldn't not write to ", table.rowTags(i)[FILENAME], "\nError: ",
                                                detail.strerror, ".\nDo you want to continue?"])
                    mb = QMessageBox('Error', errormsg, QMessageBox.Warning,
                        QMessageBox.Yes  or QMessageBox.Default, QMessageBox.No or QMessageBox.Escape , QMessageBox.YesAll, self)
                    ret = mb.exec_()
                    if ret == QMessageBox.No:
                        break
                    elif ret == QMessageBox.YesAll:
                        showmessage = False
            win.updateVal()
        self.setTag(True)
        win.close()
        self.fillCombos()
        
    def patternChanged(self):
        """This function is called everytime patterncombo changes.
        It sets the values of the StatusTips for various actions
        to a preview of the resulf if that action is hovered over."""
        #There's an error everytime an item is deleted, we account for that
        try:
            self.tagfromfile.setStatusTip(self.displayTag(self.getTagFromFile(True)))
            self.tagtofile.setStatusTip(unicode("New Filename: <b>") + self.saveTagToFile(True) + '</b>')
            self.renamedir.setStatusTip(self.renameFolder(True))
        except IndexError: pass
        
    def openActions(self, quickaction = False):
        """Shows the action window and calls the corresponding
        method depending on the value of quickaction."""
        self.qb = actiondlg.ActionWindow(self.cenwid.headerdata, self)
        self.qb.setModal(True)
        self.qb.show()
        if quickaction:
            self.connect(self.qb, SIGNAL("donewithmyshit"), self.runQuickAction)
        else:
            self.connect(self.qb, SIGNAL("donewithmyshit"), self.runAction)
            
    def runAction(self, funcs):
        """Runs the action selected in openActions.
        
        funcs is a list of list. Each list in turn containing
        actiondlg.Function objects. These are applied to
        the selected files.
        
        See the actiondlg module for more details on funcs."""
        table = self.cenwid.table
        win = ProgressWin(self, len(table.selectedRows), table)
        taglist = []
        showmessage = True
        for row in table.selectedRows:
            if win.wasCanceled(): break
            tags = copy.copy(table.rowTags(row))
            edited = []
            for func in funcs:
                for infunc in func:
                    tag = infunc.tag
                    val = {}
                    if tag == ["__all"]:
                        tag = [z for z in tag if z != "__image"]
                    if infunc.function.func_code.co_varnames[0] == 'tags':
                        for z in tag:
                            try:
                                val[z] = infunc.runFunction(tags)
                            except (AttributeError, TypeError, KeyError): 
                                "The tag doesn't exist or is empty. In either case we can do nothing"
                    else:
                        for z in tag:
                            try:
                                val[z] = infunc.runFunction(tags[z])                                    
                            except (AttributeError, TypeError, KeyError): 
                                "The tag doesn't exist or is empty. In either case we can do nothing"
                    if val is not None or val != {}:
                        tags.update([(z,i) for z,i in val.items() if i is not None])
                        edited.extend([z for z in tag if (z in val) and (val[z] is not None)])
            win.updateVal()
            mydict = dict([(z,tags[z]) for z in set(edited)])
            try:
                self.setTag(row, mydict)
            except (IOError, OSError):
                if showmessage:
                    win.show()
                    errormsg = "".join(["I couldn't not write to ", table.rowTags(row)[FILENAME], "\nError: ",
                                                detail.strerror, ".\nDo you want to continue?"])
                    mb = QMessageBox('Error writing to file', errormsg, QMessageBox.Warning,
                                    QMessageBox.Yes  or QMessageBox.Default, QMessageBox.No or QMessageBox.Escape , QMessageBox.YesAll, self)
                    ret = mb.exec_()
                    if ret == QMessageBox.No:
                        break
                    elif ret == QMessageBox.YesAll:
                        showmessage = False                    
        self.setTag(True)
        win.close()
        self.fillCombos()
    
    def runQuickAction(self, funcs):
        """Basically the same as runAction, except that
        all the functions in funcs are executed on the curently selected cells.
        
        Say you had a action that would convert "__path" to Mixed Case.
        If you ran it using runAction, it would do just that, but if you ran
        it using this function but had the title column selected, then 
        all the files selected in the title column would have their titles
        converted to Mixed Case.
        
        funcs is a list of actiondlg.Function objects.
        No error checking is done, so don't pass shitty values."""
        
        table = self.cenwid.table        
        win = ProgressWin(self, len(table.selectedRows), table)
        headerdata = self.cenwid.headerdata
        showmessage = True
        
        for row in table.selectedRows:
            if win.wasCanceled(): break
            try:
                #looks complicated, but it's just the selected tags.
                selectedtags = table.rowTags(row)
                tags = dict([(headerdata[column][1], selectedtags[headerdata[column][1]]) for column in table.selectedTags()[row]])
                for func in funcs:
                    for infunc in func:
                        for tag in tags:
                                if infunc.function.func_code.co_varnames[0] == 'tags':
                                    val = infunc.runFunction(table.rowTags(row))
                                else:
                                    val = infunc.runFunction(tags[tag])
                                if val is not None:
                                    tags[tag] = val
                try:
                    self.setTag(row, tags)
                except (IOError, OSError), detail:
                    if showmessage:
                        win.show()
                        errormsg = "".join(["I couldn't not write to ", table.rowTags(row)[FILENAME], "\nError: ",
                                                detail.strerror, ".\nDo you want to continue?"])
                        mb = QMessageBox('Error writing to file', errormsg, QMessageBox.Warning,
                                            QMessageBox.Yes  or QMessageBox.Default, QMessageBox.No or QMessageBox.Escape , QMessageBox.YesAll, self)
                        ret = mb.exec_()
                        if ret == QMessageBox.No:
                            break
                        if ret == QMessageBox.YesAll:
                            showmessage = False
            except KeyError: #A tag doesn't exist, but needs to be read.
                pass
            win.updateVal()
        self.setTag(True)
        win.close()        
        self.fillCombos()
        
    def getTagFromFile(self, test = False):
        """Get tags from the selected files using the pattern in
        self.pattercombo.
        If test = False then the tags are written.
        Otherwise the new tag of the first selected files is returned."""
        table = self.cenwid.table
        pattern = unicode(self.patterncombo.currentText())
        showmessage = True
        
        if test == False:
            win = ProgressWin(self, len(table.selectedRows), table)
            startval = 0
        else:
            row = table.selectedRows[0]
            return findfunc.filenametotag(pattern, path.basename(table.rowTags(row)["__filename"]), True)
                
        for row in table.selectedRows:
            if win.wasCanceled(): break            
            filename = table.rowTags(row)["__filename"]
            newtag = findfunc.filenametotag(pattern, path.basename(filename), True)            
            try:
                if newtag is not None:
                    self.setTag(row, newtag)
                    win.updateVal()
            except (IOError, OSError), detail:
                if showmessage:
                    win.show()
                    errormsg = "".join(["I couldn't not write to ", filename, "\nError: ",
                                                detail.strerror, ".\nDo you want to continue?"])
                    mb = QMessageBox('Error writing to file.', errormsg, QMessageBox.Warning,
                                        QMessageBox.Yes  or QMessageBox.Default, QMessageBox.No or QMessageBox.Escape , QMessageBox.YesAll, self)
                    ret = mb.exec_()
                    if ret == QMessageBox.No:
                        break
                    if ret == QMessageBox.YesAll:
                        showmessage = False
        self.setTag(True)
        win.close()
        self.fillCombos()
        
    
    def saveTagToFile(self, test = False):
        """Renames the selected files using the pattern
        in self.patterncombo.
        
        If test = True then the files are not renamed and
        the new filename of the first selected file is
        returned."""
        
        taginfo = self.cenwid.tablemodel.taginfo
        pattern = unicode(self.patterncombo.currentText())
        table = self.cenwid.table
        showmessage = True
        showoverwrite = True
        
        if test == False:
            win = ProgressWin(self, len(table.selectedRows), table)
        else:
            #Just return an example value.
            row = table.selectedRows[0]
            newfilename = (findfunc.tagtofilename(pattern, taginfo[row], True,
                                                        taginfo[row]["__ext"] ))
            return path.join(path.dirname(taginfo[row]["__filename"]), safe_name(newfilename))
            
        for row in table.selectedRows:
            filename = taginfo[row][FILENAME]
            tag = taginfo[row]
            newfilename = (findfunc.tagtofilename(pattern,tag, True, tag["__ext"]))
            newfilename = path.join(path.dirname(filename), safe_name(newfilename))
            renameFile = self.cenwid.table.model().renameFile
            
            if not test:
                if path.exists(newfilename) and (newfilename != filename):
                    win.show()
                    if showoverwrite:
                        mb = QMessageBox('Ovewrite existing file?', "The file: " + newfilename + " exists. Should I overwrite it?", 
                                        QMessageBox.Question, QMessageBox.Yes, 
                                        QMessageBox.No or QMessageBox.Escape or QMessageBox.Default, QMessageBox.NoAll, self)
                        ret = mb.exec_()
                        if ret == QMessageBox.No:
                            continue
                        if ret == QMessageBox.NoAll:
                            showoverwrite = False
                            continue
                    else:
                        continue
                try:
                    self.setTag(row, {"__path": path.basename(newfilename)}, True)
                except (IOError, OSError), detail:
                    if showmessage:
                        win.show()
                        errormsg = "".join(["I could not rename ", filename, "\nError: ",
                                                detail.strerror, ".\nDo you want to continue renaming the rest?"])
                        mb = QMessageBox('Renaming failed', errormsg,
                            QMessageBox.Warning, QMessageBox.Yes  or QMessageBox.Default, 
                            QMessageBox.No or QMessageBox.Escape , QMessageBox.YesAll, self)
                        ret = mb.exec_()
                        if ret == QMessageBox.No:
                            break
                        elif ret == QMessageBox.YesAll:
                            showmessage = False
            else:
                return newfilename
            win.updateVal()
        self.setTag(True)
        self.fillCombos()
        win.close()
    
    def openPrefs(self):
        """Nothing much. Just opens a preferences window and shows it.
        The preferences windows does everything like setting of values, updating
        and so forth."""
        win = puddlesettings.MainWin(self, self)
        win.setModal(True)
        win.show()
        
    def closeEvent(self, event):
        """Save settings and close."""
        settings = QSettings()
        table = self.cenwid.table
        columnwidths = QStringList([unicode(table.columnWidth(z)) for z in range(table.model().columnCount())])
        settings.setValue("editor/Column",QVariant(columnwidths))
        
        titles = [z[0] for z in self.cenwid.headerdata]
        tags = [z[1] for z in self.cenwid.headerdata]
        
        settings.setValue("editor/titles", QVariant(QStringList(titles)))
        settings.setValue("editor/tags", QVariant(QStringList(tags)))
        
        patterns = QStringList()
        for z in xrange(self.patterncombo.count()):
            patterns.append(self.patterncombo.itemText(z))
        settings.setValue("editor/patterns",QVariant(QStringList(patterns)))
        
        settings.setValue("splittersize", QVariant(self.splitter.saveState()))
        settings.setValue("hsplittersize", QVariant(self.hsplitter.saveState()))
                                    
        settings.setValue("Table/sortColumn", QVariant(self.cenwid.sortColumn))                
        settings.setValue("main/lastfolder", QVariant(self.lastFolder))
        settings.setValue("main/maximized", QVariant(self.isMaximized()))
        
        if not self.isMaximized():
            settings.setValue('main/height', QVariant(self.height()))
            settings.setValue('main/width', QVariant(self.width()))
        
        settings.setValue("editor/showfilter",QVariant(self.showfilter.isChecked()))
    
    def displayTag(self, tag):
        if tag is None:
            return "<b>Error in pattern</b>"
        s = "%s: <b>%s</b>, "
        return "".join([s % (z,v) for z,v in tag.items()])[:-2]
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    filename = sys.argv[1:]
    app.setOrganizationName("Puddle Inc.")
    app.setApplicationName("puddletag")   
        
    qb = MainWin()
    qb.rowEmpty()
    pdb.set_trace()
    print filename
    if filename:
        pdb.set_trace()
        pixmap = QPixmap(':/puddlelogo.png')
        splash = QSplash(pixmap)
        splash.show()
        QApplication.processEvents()
        qb.openFolder(filename)
        qb.show()
    app.exec_()
