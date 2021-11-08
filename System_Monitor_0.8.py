import gc
import sys
import psutil
import threading
from os import *
from time import time
from re import sub, DOTALL
from math import log, trunc
from getpass import getuser 
from functools import partial
import matplotlib.pyplot as plt
from warnings import filterwarnings
import matplotlib.ticker as plticker
from yaml import safe_load, safe_dump
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as Navigation

del globals()['open']
filterwarnings('ignore')

class Ui_MainWindow(object):
    
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(820, 600)
        MainWindow.setMinimumSize(QtCore.QSize(560, 300))
        MainWindow.setMaximumSize(QtCore.QSize(820, 600))
        MainWindow.setStyleSheet("QMainWindow { background:rgb(144,118,98);}")
        MainWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        MainWindow.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        wndShadow = QtWidgets.QGraphicsDropShadowEffect()
        wndShadow.setBlurRadius(15.0)
        wndShadow.setColor(QtGui.QColor(0, 0, 0, 160))
        wndShadow.setOffset(4.0)
        MainWindow.setGraphicsEffect(wndShadow)

        self.cwd = getcwd()
        self.icon_dir = '\"' + self.cwd + '/Icons/'
        
        with open(self.cwd + '/setup.yaml', 'r') as file:
            self.defaults = safe_load(file)

        self.bgtheme = self.defaults['bgcolor'][1]
        self.pltheme = self.defaults['plcolor'][1]
        self.hltheme = self.defaults['hlcolor'][1]

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.layout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.layout.addWidget(MyBar(MainWindow))
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addStretch(-1)
        MainWindow.setLayout(self.layout)
        
        self.pressing = False
        self.coverLabel = QtWidgets.QLabel(self.centralwidget)
        self.coverLabel.setGeometry(QtCore.QRect(0, 35, 820, 565))
        self.coverLabel.setStyleSheet("QLabel {background:rgb(144,118,98); border: 1px solid rgb(85,75,74);}")

        self.tableWidget = QtWidgets.QTableWidget(self.centralwidget)
        self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 565)) 
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(6)
        self.tableWidget.setRowCount(30)
        self.tableWidget.setHorizontalHeaderLabels(['Process Name', 'User', 'CPU%', 'PID', 'Memory%', '        State'])
        self.tableWidget.setShowGrid(False)
        self.tableWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget.verticalScrollBar().setStyleSheet("QScrollBar:vertical{background: rgb(209,209,211);\n"
"       border-radius: 6px; width: 20px; margin: 20px 4px 20px 4px;}\n"
"       QScrollBar::handle:vertical{background:rgb(159,36,37); min-height:20px; border-radius: 6px; background-image: url(" + self.icon_dir + "navigation2.png\"); background-repeat: no-repeat; background-position: center;}\n"
"       QScrollBar::sub-line:vertical{border-image: url(" + self.icon_dir + "up_arrow2.png\"); margin: 3px 0px 3px 0px; height: 12px; width: 11px; subcontrol-position: top; subcontrol-origin: margin;}\n"
"       QScrollBar::add-line:vertical{border-image: url(" + self.icon_dir + "down_arrow4.png\"); margin: 3px 0px 3px 0px; height: 14px; width: 11px; subcontrol-position: bottom; subcontrol-origin: margin;}\n"                                                           
"       QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical{background:none;}\n"
"       QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{background:none;}")
        self.phheader = self.tableWidget.horizontalHeader()
        self.phheader.setDefaultAlignment(QtCore.Qt.AlignLeft)
        self.pvheader = self.tableWidget.verticalHeader()
        self.pvheader.setVisible(False)
        self.tableWidget.setColumnWidth(0, 220)
        self.tableWidget.setColumnWidth(1, 85)
        self.tableWidget.setColumnWidth(2, 75)
        self.tableWidget.setColumnWidth(3, 65)
        self.tableWidget.setColumnWidth(4, 100)
        self.tableWidget.setColumnWidth(5, 260)
        self.Edit = QTableWidgetDisabledItem(self.tableWidget)
        for i in range(6):
            self.tableWidget.setItemDelegateForColumn(i,self.Edit)
                
        self.tableWidget.setStyleSheet("QTableWidget{border: 1px solid rgb(85,75,74); selection-background-color: rgb(159,36,37);}\n"
"       QTableWidget::item:selected{color: rgb(0,0,0); background-color:transparent; selection-background-color:transparent;}")
        self.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.CHeader = 2
        self.switch = False
        self.selected = [-1]
        self.tableWidget.horizontalHeader().sectionClicked.connect(self.onHeaderClicked)
        self.tableWidget.keyPressEvent = self.keyPressEvent
        self.tableWidget.mouseReleaseEvent = self.preInfoGrab

        self.timeList = [float('nan')]*20
  
        self.fig1 = plt.figure()
        self.fig1.patch.set_facecolor('#9f2425')
        self.ax1 = self.fig1.add_subplot(1,1,1)
        self.ax1.set_facecolor('#9f2425')
        self.ax1.set_title('CPU Usage')
        self.ax1.set_xlabel('Time (seconds)')
        self.ax1.set_yticklabels(['0%', '50%', '100%'])
        plt.subplots_adjust(bottom=0.20) 
        plt.subplots_adjust(top=0.80)
        self.canvas1 = FigureCanvasQTAgg(self.fig1)

        self.layout1 = QtWidgets.QVBoxLayout()
        self.layout1.addWidget(self.canvas1)

        self.cpuPlot = QtWidgets.QWidget(self.centralwidget)
        self.cpuPlot.setGeometry(QtCore.QRect(22, 48, 770, 160))
        self.cpuPlot.setVisible(False)
        self.cpuPlot.setLayout(self.layout1)

        self.fig2 = plt.figure()
        self.fig2.patch.set_facecolor('#9f2425')
        self.ax2 = self.fig2.add_subplot(1,1,1)
        self.ax2.set_facecolor('#9f2425')
        self.ax2.set_title('Memory Usage')
        self.ax2.set_xlabel('Time (seconds)')
        self.ax2.set_yticklabels(['0%', '50%', '100%'])
        plt.subplots_adjust(bottom=0.32)
        plt.subplots_adjust(top=0.80)
        self.canvas2 = FigureCanvasQTAgg(self.fig2)

        self.layout2 = QtWidgets.QVBoxLayout()
        self.layout2.addWidget(self.canvas2)

        self.memPlot = QtWidgets.QWidget(self.centralwidget)
        self.memPlot.setGeometry(QtCore.QRect(22, 221, 770, 160))
        self.memPlot.setVisible(False)
        self.memPlot.setLayout(self.layout2)

        self.fig3 = plt.figure()
        self.fig3.patch.set_facecolor('#F3F3F5')
        self.ax3 = self.fig3.add_subplot(1,1,1)
        self.ax3.set_facecolor('#F3F3F5')
        self.ax3.set_title('Network Usage')
        self.ax3.set_xlabel('Time (seconds)')
        self.ax3.set_yticklabels(['0 bytes/s', '250 bytes/s', '500 bytes/s'], Fontsize=9)
        plt.subplots_adjust(bottom=0.32)
        plt.subplots_adjust(top=0.80)
        self.canvas3 = FigureCanvasQTAgg(self.fig3)

        self.layout3 = QtWidgets.QVBoxLayout()
        self.layout3.addWidget(self.canvas3)

        self.netPlot = QtWidgets.QWidget(self.centralwidget)
        self.netPlot.setGeometry(QtCore.QRect(22, 416, 770, 160))
        self.netPlot.setVisible(False)
        self.netPlot.setLayout(self.layout3)

        self.cores = float(popen('grep -c ^processor /proc/cpuinfo').read())
        self.cpuGrid = QtWidgets.QHBoxLayout()
        self.cpuWidget = QtWidgets.QWidget(self.centralwidget)
        self.cpuWidget.setGeometry(QtCore.QRect(22, 198, 750, 40))
        self.cpuGroup = QtWidgets.QButtonGroup(self.centralwidget)
        for i in range(int(self.cores)+1):
            b = QtWidgets.QPushButton()
            b.setMaximumSize(QtCore.QSize(15,15))
            b.setCheckable(True)
            b.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}\n"
"       QPushButton:checked{background-color:red;}")
            if i==0:
               b.setChecked(True) 
            l = QtWidgets.QLabel()
            l.setMinimumSize(QtCore.QSize(120,15))
            self.cpuGrid.addWidget(b)
            self.cpuGrid.addWidget(l)
            self.cpuGroup.addButton(b)

        self.cpuGroup.setExclusive(True)
        self.cpuWidget.setLayout(self.cpuGrid)
        self.cpuWidget.setVisible(False)

        self.memPtable = QtWidgets.QTableWidget(self.centralwidget)
        self.memPtable.setGeometry(QtCore.QRect(59, 386, 25, 26))
        self.memPtable.setColumnCount(1)
        self.memPtable.setRowCount(1)
        self.memPtable.horizontalHeader().setMaximumSectionSize(2)
        self.memPtable.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.memPtable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.memPtable.setShowGrid(False)
        self.mphheader = self.memPtable.horizontalHeader()
        self.mpvheader = self.memPtable.verticalHeader()
        self.mphheader.setVisible(False)
        self.mpvheader.setVisible(False)
        self.memPtable.setVisible(False)
        self.swapTable = QtWidgets.QTableWidget(self.centralwidget)
        self.swapTable.setGeometry(QtCore.QRect(432, 386, 35, 25))
        self.swapTable.setColumnCount(1)
        self.swapTable.setRowCount(1)
        self.swapTable.horizontalHeader().setMaximumSectionSize(2)
        self.swapTable.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.swapTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.swapTable.setShowGrid(False)
        self.shheader = self.swapTable.horizontalHeader()
        self.svheader = self.swapTable.verticalHeader()
        self.shheader.setVisible(False)
        self.svheader.setVisible(False)
        self.swapTable.setVisible(False)
        self.mem1Label = QtWidgets.QLabel(self.centralwidget)
        self.mem1Label.setGeometry(QtCore.QRect(48, 375, 70, 70))
        self.mem1Label.setStyleSheet("QLabel {color: #333;\n"
"    background-image: url(" + self.icon_dir + "memory3.png\");\n"
"    background-repeat: no-repeat;\n"
"    }")
        '''wndShadow = QtWidgets.QGraphicsDropShadowEffect()
        wndShadow.setBlurRadius(15.0)
        wndShadow.setColor(QtGui.QColor(0, 0, 0, 160))
        wndShadow.setOffset(4.0)
        self.mem1Label.setGraphicsEffect(wndShadow)'''
        
        self.mem2Label = QtWidgets.QLabel(self.centralwidget)
        self.mem2Label.setGeometry(QtCore.QRect(100, 375, 300, 48))
        self.mem3Label = QtWidgets.QLabel(self.centralwidget)
        self.mem3Label.setGeometry(QtCore.QRect(425, 375, 70, 70))
        self.mem3Label.setStyleSheet("QLabel {color: #333;\n"
"    background-image: url(" + self.icon_dir + "swap1.png\");\n"
"    background-repeat: no-repeat;\n"
"    }")
        self.mem4Label = QtWidgets.QLabel(self.centralwidget)
        self.mem4Label.setGeometry(QtCore.QRect(480, 375, 300, 48))
        self.mem1Label.setVisible(False)
        self.mem2Label.setVisible(False)
        self.mem3Label.setVisible(False)
        self.mem4Label.setVisible(False)
        self.memGroup = QtWidgets.QButtonGroup(self.centralwidget)
        self.memRdbtn = QtWidgets.QPushButton(self.centralwidget)
        self.memRdbtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}\n"
"       QPushButton:checked{background-color:red;}") 
        self.swapRdbtn = QtWidgets.QPushButton(self.centralwidget)
        self.swapRdbtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}\n"
"       QPushButton:checked{background-color:red;}") 
        self.memRdbtn.setCheckable(True)
        self.swapRdbtn.setCheckable(True)
        self.memGroup.addButton(self.memRdbtn)
        self.memGroup.addButton(self.swapRdbtn)
        self.memGroup.setExclusive(True)
        self.memRdbtn.setGeometry(QtCore.QRect(30, 392, 15, 15))
        self.swapRdbtn.setGeometry(QtCore.QRect(410, 392, 15, 15))
        self.memRdbtn.setVisible(False)
        self.swapRdbtn.setVisible(False)
        self.memRdbtn.setChecked(True)

        self.net1Label = QtWidgets.QLabel(self.centralwidget)
        self.net1Label.setGeometry(QtCore.QRect(50, 572, 70, 70))
        self.net1Label.setStyleSheet("QLabel {color: #333;\n"
"    background-image: url(" + self.icon_dir + "down_arrow3.png\");\n"
"    background-repeat: no-repeat;\n"
"    }")
        self.net2Label = QtWidgets.QLabel(self.centralwidget)
        self.net2Label.setGeometry(QtCore.QRect(90, 548, 170, 70))
        self.net3Label = QtWidgets.QLabel(self.centralwidget)
        self.net3Label.setGeometry(QtCore.QRect(400, 572, 70, 70))
        self.net3Label.setStyleSheet("QLabel {color: #333;\n"
"    background-image: url(" + self.icon_dir + "up_arrow.png\");\n"
"    background-repeat: no-repeat;\n"
"    }")
        self.net4Label = QtWidgets.QLabel(self.centralwidget)
        self.net4Label.setGeometry(QtCore.QRect(448, 548, 170, 70))
        self.net1Label.setVisible(False)
        self.net2Label.setVisible(False)
        self.net3Label.setVisible(False)
        self.net4Label.setVisible(False)
        self.netGroup = QtWidgets.QButtonGroup(self.centralwidget)
        self.downloadRdbtn = QtWidgets.QPushButton(self.centralwidget)
        self.downloadRdbtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}\n"
"       QPushButton:checked{background-color:red;}") 
        self.uploadRdbtn = QtWidgets.QPushButton(self.centralwidget)
        self.uploadRdbtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}\n"
"       QPushButton:checked{background-color:red;}") 
        self.downloadRdbtn.setCheckable(True)
        self.uploadRdbtn.setCheckable(True)
        self.netGroup.addButton(self.downloadRdbtn)
        self.netGroup.addButton(self.uploadRdbtn)
        self.netGroup.setExclusive(True)
        self.downloadRdbtn.setGeometry(QtCore.QRect(30, 575, 15, 15))
        self.uploadRdbtn.setGeometry(QtCore.QRect(380, 575, 15, 15))
        self.downloadRdbtn.setVisible(False)
        self.uploadRdbtn.setVisible(False)
        self.downloadRdbtn.setChecked(True)

        self.fig4 = plt.figure()
        self.fig4.patch.set_facecolor('#9f2425')
        self.ax4 = self.fig4.add_subplot(1,1,1)
        self.ax4.set_facecolor('#9f2425')
        self.ax4.set_title('CPU Temperature')
        self.ax4.set_xlabel('Time (seconds)')
        self.ax4.set_yticklabels(['0' + u"\N{DEGREE SIGN}" + 'C', '50' + u"\N{DEGREE SIGN}" + 'C', '100' + u"\N{DEGREE SIGN}" + 'C'])
        plt.subplots_adjust(bottom=0.32)
        plt.subplots_adjust(top=0.80)
        self.canvas4 = FigureCanvasQTAgg(self.fig4)

        self.layout4 = QtWidgets.QVBoxLayout()
        self.layout4.addWidget(self.canvas4)

        self.tempPlot = QtWidgets.QWidget(self.centralwidget)
        self.tempPlot.setGeometry(QtCore.QRect(22, 48, 770, 160))
        self.tempPlot.setVisible(False)
        self.tempPlot.setLayout(self.layout4)

        self.temptotLabel = QtWidgets.QLabel(self.centralwidget)
        self.fanLabel = QtWidgets.QLabel(self.centralwidget)
        self.temptotLabel.setGeometry(QtCore.QRect(50, 210, 160, 15))
        self.fanLabel.setGeometry(QtCore.QRect(220, 210, 150, 15))
        self.temptotLabel.setVisible(False)
        self.fanLabel.setVisible(False)
        self.tempGroup = QtWidgets.QButtonGroup(self.centralwidget)
        self.temptotRdbtn = QtWidgets.QPushButton(self.centralwidget)
        self.temptotRdbtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}\n"
"       QPushButton:checked{background-color:red;}") 
        self.fanRdbtn = QtWidgets.QPushButton(self.centralwidget)
        self.fanRdbtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}\n"
"       QPushButton:checked{background-color:red;}")
        self.temptotRdbtn.setCheckable(True)
        self.fanRdbtn.setCheckable(True)
        self.tempGroup.addButton(self.temptotRdbtn)
        self.tempGroup.addButton(self.fanRdbtn)
        self.tempGroup.setExclusive(True)
        self.temptotRdbtn.setGeometry(QtCore.QRect(30, 210, 15, 15))
        self.fanRdbtn.setGeometry(QtCore.QRect(200, 210, 15, 15))
        self.temptotRdbtn.setVisible(False)
        self.fanRdbtn.setVisible(False)
        self.temptotRdbtn.setChecked(True)

        self.diskTable = QtWidgets.QTableWidget(self.centralwidget)
        self.diskTable.setGeometry(QtCore.QRect(30, 240, 754, 327))
        self.diskTable.setColumnCount(6)
        self.diskTable.setRowCount(2)
        self.Dedit = QDiskTableDisabledItem(self.diskTable)
        for i in range(6):
            self.diskTable.setItemDelegateForColumn(i,self.Dedit)
        self.diskTable.setHorizontalHeaderLabels(['Device', 'Directory', 'Type', 'Total', 'Available', 'Used'])
        self.diskTable.setShowGrid(False)
        self.diskTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.diskTable.verticalScrollBar().setStyleSheet("QScrollBar:vertical{background: rgb(209,209,211);\n"
"       border-radius: 6px; width: 20px; margin: 20px 4px 20px 4px;}\n"
"       QScrollBar::handle:vertical{background:rgb(159,36,37); min-height:20px; border-radius: 6px; background-image: url(" + self.icon_dir + "navigation2.png\"); background-repeat: no-repeat; background-position: center;}\n"
"       QScrollBar::sub-line:vertical{border-image: url(" + self.icon_dir + "up_arrow2.png\"); margin: 3px 0px 3px 0px; height: 12px; width: 11px; subcontrol-position: top; subcontrol-origin: margin;}\n"
"       QScrollBar::add-line:vertical{border-image: url(" + self.icon_dir + "down_arrow4.png\"); margin: 3px 0px 3px 0px; height: 14px; width: 11px; subcontrol-position: bottom; subcontrol-origin: margin;}\n"                                                           
"       QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical{background:none;}\n"
"       QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{background:none;}")
        self.dhheader = self.diskTable.horizontalHeader()
        self.dhheader.setDefaultAlignment(QtCore.Qt.AlignLeft)
        self.dvheader = self.diskTable.verticalHeader()
        self.dvheader.setVisible(False)
        self.diskTable.setVisible(False)
        self.diskTable.setColumnWidth(0, 132)
        self.diskTable.setColumnWidth(1, 172)
        self.diskTable.setColumnWidth(2, 90)
        self.diskTable.setColumnWidth(3, 120)
        self.diskTable.setColumnWidth(4, 120)
        self.diskTable.setColumnWidth(5, 120)
        self.diskTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows) 
        self.diskTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.diskTable.itemDoubleClicked.connect(self.diskDblClick)
        self.diskTable.horizontalHeader().sectionClicked.connect(self.onHeaderClicked)

        self.Procs = QtWidgets.QPushButton(self.centralwidget)
        self.Procs.setGeometry(QtCore.QRect(260, 0, 101, 31))
        self.Procs.setObjectName("Procs")
        self.Procs.setStyleSheet("QPushButton{color:rgb(245,235,245);\n"
"    border-bottom-left-radius: 10px; border: 1px solid rgb(56, 52, 48);\n"                                
"    background-color: rgb(94, 90, 96);\n"
"    background-repeat: no-repeat;}\n"
"    QPushButton:hover {\n"
"    background-color: rgb(76, 72, 68); border: transparent;}")
        self.Procs.clicked.connect(self.chk_proc)
        
        self.Resources = QtWidgets.QPushButton(self.centralwidget)
        self.Resources.setGeometry(QtCore.QRect(360, 0, 91, 31))
        self.Resources.setObjectName("Resources")
        self.Resources.setStyleSheet("QPushButton{color:rgb(245,235,245);\n"                             
"    background-color: rgb(94, 90, 96); border: 1px solid rgb(56, 52, 48);\n"
"    background-repeat: no-repeat;}\n"
"    QPushButton:hover {\n"
"    background-color: rgb(76, 72, 68); border: transparent;}")
        self.Resources.clicked.connect(self.chk_res)
        
        self.Ancillary = QtWidgets.QPushButton(self.centralwidget)
        self.Ancillary.setGeometry(QtCore.QRect(450, 0, 91, 31))
        self.Ancillary.setObjectName("Ancillary")
        self.Ancillary.setStyleSheet("QPushButton{color:rgb(245,235,245);\n"
"    border-bottom-right-radius: 10px; border: 1px solid rgb(56, 52, 48);\n"                                
"    background-color: rgb(94, 90, 96);\n"
"    background-repeat: no-repeat;}\n"
"    QPushButton:hover {\n"
"    background-color: rgb(76, 72, 68); border: transparent;}")
        self.Ancillary.clicked.connect(self.anc_proc)
        
        self.Search = QtWidgets.QPushButton(self.centralwidget)
        self.Search.setGeometry(QtCore.QRect(0, 0, 32, 31))
        self.Search.setObjectName("Search")
        self.Search.setStyleSheet("QPushButton{color:rgb(245,235,245);\n"
"    border-top-left-radius: 10px; border: 1px solid rgb(56, 52, 48);\n"                                
"    background-color: rgb(94, 90, 96);\n"
"    background-image: url(" + self.icon_dir + "search8.png\");\n"
"    background-position: center; background-repeat: no-repeat;}\n"
"    QPushButton:hover {\n"
"    background-color: rgb(76, 72, 68); border: transparent;}")
        self.Search.clicked.connect(self.find_proc)
        self.searching = QtWidgets.QLineEdit(self.centralwidget)
        self.searching.setGeometry(QtCore.QRect(0, 40, 250, 30))
        self.searching.setVisible(False)
        self.searching.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.searching.setStyleSheet("QLineEdit{padding-left: 25px; border: 3px solid rgb(135,108,90);\n"
"    background-image: url(" + self.icon_dir + "search3.png\");\n"
"    background-position: left; background-repeat: no-repeat;}\n")
        
        self.Sort = QtWidgets.QPushButton(self.centralwidget)
        self.Sort.setGeometry(QtCore.QRect(32, 0, 32, 31))
        self.Sort.setObjectName("Sort")
        self.Sort.setStyleSheet("QPushButton{color:rgb(245,235,245);\n"
"    border-bottom-right-radius: 10px; border: 1px solid rgb(56, 52, 48);\n"                                
"    background-color: rgb(94, 90, 96);\n"
"    background-image: url(" + self.icon_dir + "sort3.png\");\n"
"    background-position: center; background-repeat: no-repeat;}\n"  
"    QPushButton:hover {\n"
"    background-color: rgb(76, 72, 68); border: transparent;}")
        self.sort_menu = QtWidgets.QMenu(self.centralwidget)
        self.CUser = getuser() 
        refresh = self.sort_menu.addAction(QtWidgets.QAction('Refresh', self.sort_menu, checkable=False))
        sort_action1 = QtWidgets.QAction('GUI Processes', self.sort_menu, checkable=True)
        sort_action2 = QtWidgets.QAction('All Processes', self.sort_menu, checkable=True)
        sort_action3 = QtWidgets.QAction(self.CUser + "'s Processes", self.sort_menu, checkable=True)
        self.sort_menu.addSeparator()
        self.sort_menu.addAction(sort_action1)
        self.sort_menu.addAction(sort_action2)
        self.sort_menu.addAction(sort_action3)
        self.sort_menu.addSeparator()
        pref1 = self.sort_menu.addAction(QtWidgets.QAction('Preferences', self.sort_menu, checkable=False))
        self.sort_GAction = QtWidgets.QActionGroup(self.sort_menu)
        self.sort_GAction.addAction(sort_action1)
        self.sort_GAction.addAction(sort_action2)
        self.sort_GAction.addAction(sort_action3) 
        self.Sort.clicked.connect(self.sort_proc)

        self.Sort2 = QtWidgets.QPushButton(self.centralwidget)
        self.Sort2.setGeometry(QtCore.QRect(0, 0, 32, 31))
        self.Sort2.setObjectName("Sort2")
        self.Sort2.setStyleSheet("QPushButton{color:rgb(245,235,245);\n"
"    border-top-left-radius: 10px; border-bottom-right-radius: 10px;\n"
"    border: 1px solid rgb(56, 52, 48); background-color: rgb(94, 90, 96);\n"
"    background-image: url(" + self.icon_dir + "sort3.png\");\n"
"    background-position: center; background-repeat: no-repeat;}\n"
"    QPushButton:hover {\n"
"    background-color: rgb(76, 72, 68); border: transparent;}")
        self.Sort2.setVisible(False)
        self.sort_menu2 = QtWidgets.QMenu(self.centralwidget)
        self.sort_menu2.addAction(QtWidgets.QAction('CPU Stats', self.sort_menu2, checkable=False))
        self.sort_menu2.addAction(QtWidgets.QAction('Memory Stats', self.sort_menu2, checkable=False))
        netMenu = QtWidgets.QMenu('Network Stats', self.centralwidget)
        netMenu.addAction(QtWidgets.QAction('Connections', netMenu, checkable=False))
        netMenu.addAction(QtWidgets.QAction('NIC && IO Counters', netMenu, checkable=False))
        netMenu.addAction(QtWidgets.QAction('Network Addresses', netMenu, checkable=False))
        self.sort_menu2.addMenu(netMenu) 
        self.sort_menu2.addSeparator()
        pref2 = self.sort_menu2.addAction(QtWidgets.QAction('Preferences', self.sort_menu2, checkable=False)) 
        self.Sort2.clicked.connect(self.sort_proc2)

        self.Sort3 = QtWidgets.QPushButton(self.centralwidget)
        self.Sort3.setGeometry(QtCore.QRect(0, 0, 32, 31))
        self.Sort3.setStyleSheet("QPushButton{color:rgb(245,235,245);\n"
"    border-top-left-radius: 10px; border-bottom-right-radius: 10px;\n"
"    border: 1px solid rgb(56, 52, 48); background-color: rgb(94, 90, 96);\n"
"    background-image: url(" + self.icon_dir + "sort3.png\");\n"
"    background-position: center; background-repeat: no-repeat;}\n"
"    QPushButton:hover {\n"
"    background-color: rgb(76, 72, 68); border: transparent;}")
        self.Sort3.setVisible(False)
        self.sort_menu3 = QtWidgets.QMenu(self.centralwidget)
        pref2 = self.sort_menu3.addAction(QtWidgets.QAction('Preferences', self.sort_menu2, checkable=False)) 
        self.Sort3.clicked.connect(self.sort_proc3)
        
        self.PEnd = QtWidgets.QPushButton(self.centralwidget)
        self.PEnd.setGeometry(QtCore.QRect(15, 565, 125, 30))
        self.PEnd.setText('   End Process')
        self.PEnd.setVisible(False)
        self.PEnd.setStyleSheet("QPushButton{color:rgb(245,235,245);\n"                             
"       background-color: rgb(124,98,78); border: 1px solid rgb(104,78,58);\n"
"       border-radius: 14px; Text-align:left;\n"
"       background-image: url(" + self.icon_dir + "close3.png\");\n"
"       background-position: right; background-repeat: no-repeat;}\n"
"       QPushButton:hover {\n"
"       background-color: rgb(164,138,118);}")
        self.PEnd.clicked.connect(partial(self.promptAction, prompt=0))
        
        self.PSet = QtWidgets.QPushButton(self.centralwidget)
        self.PSet.setGeometry(QtCore.QRect(565, 565, 180, 30))
        self.PSet.setText('   Process Information')
        self.PSet.setVisible(False)
        self.PSet.setStyleSheet("QPushButton{color:rgb(245,235,245);\n"                             
"       background-color: rgb(124,98,78); border: 1px solid rgb(104,78,58);\n"
"       border-radius: 12px; Text-align:left;\n"
"       background-image: url(" + self.icon_dir + "info2.png\");\n"
"       background-position: right; background-repeat: no-repeat;}\n"
"       QPushButton:hover {\n"
"       background-color: rgb(164,138,118);}")
        self.set_event = False
        self.PSet.clicked.connect(partial(self.on_context_menu, event=self.set_event))

        self.cpuList = [0.0]*19
        self.memList = [0.0]*19
        self.netList = [0.0]*19
        self.tempList = [0.0]*19

        self.command1 = "top -i -b -n 2 | awk '{print $1}''{print $9}'"
        self.command2 =  'ps -e -o pcpu,pid --sort=pcpu | tail -n 25'
        self.stcommand = 0 
        self.proc = False
        self.OldSet = False
        self.Unselected = False
        self.terminated = False
        self.LeftUpdate = True
        self.header_indx = 2 
        self.sorter = False
        self.changetbl1 = 2
        self.changetbl2 = 1
        self.switch1 = False
        self.switch2 = False
        self.recieved = psutil.net_io_counters().bytes_recv
        self.sent = psutil.net_io_counters().bytes_sent
        self.trace_pid = -1
        self.stime = time()
        self.plottime = time()
        self.tup = 0 
        self.ccpuselect = 0
        self.memselect = 0
        self.netselect = 0
        self.tempselect = 0
        self.mainView = True
        self.search_change = False
        self.reader = '' 
        self.seeing = self.defaults['procview'][1]
        if self.seeing==0:
            sort_action3.setChecked(True)
        elif self.seeing==1:
            sort_action2.setChecked(True)
        else:
            sort_action1.setChecked(True)
        self.set_event = False 
        self.nofan = True
        self.ptime = 0.5
        self.rtime = self.defaults['pg2time'][1]
        self.atime = self.defaults['pg3time'][1]
        self.tblswitch = False
        self.memvis = self.defaults['memview'][1] 
        self.ptrack = self.defaults['proctrack'][1]
        self.baselist = ['0', '0', '250', '500'] 
        self.cpustyle = self.defaults['cpuplt'][1] 
        self.memstyle = self.defaults['memplt'][1] 
        self.netstyle = self.defaults['netplt'][1] 
        self.tempstyle = self.defaults['templt'][1]
        self.pltgrid = self.defaults['gridplot'][1]
        self.tfchoice = 0 
        self.tcrit = 100 
        self.thigh = 75 
        self.tunit = self.defaults['tempunit'][1] 
        self.diskwarn = self.defaults['diskwarning'][1] 
        self.disklimit = False 
        
        self.tableWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu) 
        self.tableWidget.customContextMenuRequested.connect(self.on_context_menu)
        self.diskTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu) 
        self.diskTable.customContextMenuRequested.connect(self.disk_context_menu)
        
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 805, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.statusbar.hide()

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        self.stat_update()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LuminOS System Monitor"))
        self.Procs.setText(_translate("MainWindow", "Processes"))
        self.Resources.setText(_translate("MainWindow", "Resources"))
        self.Ancillary.setText(_translate("MainWindow", "Ancillary"))

    def onHeaderClicked(self, logicalIndex):
        
        self.header_indx = logicalIndex
        if self.CHeader == logicalIndex:
            self.switch = not self.switch
        else:
            self.CHeader = logicalIndex
            self.switch = False
        self.sorter = self.switch

        if self.tableWidget.isVisible():
            self.changetbl1 = logicalIndex
            self.switch1 = self.switch 
            icon1 = QtWidgets.QTableWidgetItem("Process Name")
            icon2 = QtWidgets.QTableWidgetItem("CPU%")
            icon3 = QtWidgets.QTableWidgetItem("PID")
            if self.memvis==0:
                icon4 = QtWidgets.QTableWidgetItem("Memory%")
            else:
                icon4 = QtWidgets.QTableWidgetItem("Memory")
            icon5 = QtWidgets.QTableWidgetItem("        State")
            icon6 = QtWidgets.QTableWidgetItem("User")
            self.tableWidget.setHorizontalHeaderItem(0, icon1)
            self.tableWidget.setHorizontalHeaderItem(1, icon6)
            self.tableWidget.setHorizontalHeaderItem(2, icon2)
            self.tableWidget.setHorizontalHeaderItem(3, icon3)
            self.tableWidget.setHorizontalHeaderItem(4, icon4)
            self.tableWidget.setHorizontalHeaderItem(5, icon5) 
            if (logicalIndex==2):
                icon = QtWidgets.QTableWidgetItem("CPU%")
            elif(logicalIndex==0):
                icon = QtWidgets.QTableWidgetItem("Process Name")
            elif(logicalIndex==4):
                if self.memvis==0:
                    icon = QtWidgets.QTableWidgetItem("Memory%")
                else:
                    icon = QtWidgets.QTableWidgetItem("Memory")
            elif(logicalIndex==5):
                icon = QtWidgets.QTableWidgetItem("   State")
            elif(logicalIndex==3):
                icon = QtWidgets.QTableWidgetItem("PID")
            elif(logicalIndex==1):
                icon = QtWidgets.QTableWidgetItem("User")
            try:
                if self.switch:
                    icon.setIcon(QtGui.QIcon(self.icon_dir[1:] + "down_arrow4.png"))
                else:
                    icon.setIcon(QtGui.QIcon(self.icon_dir[1:] + "up_arrow2.png"))
                self.tableWidget.setHorizontalHeaderItem(logicalIndex, icon)
            except:
                pass

        else:
            self.changetbl2 = logicalIndex
            self.switch2 = self.switch 
            icon1 = QtWidgets.QTableWidgetItem("Device")
            icon2 = QtWidgets.QTableWidgetItem("Directory")
            icon3 = QtWidgets.QTableWidgetItem("Type")
            icon4 = QtWidgets.QTableWidgetItem("Total")
            icon5 = QtWidgets.QTableWidgetItem("Available")
            icon6 = QtWidgets.QTableWidgetItem("Used")
            self.diskTable.setHorizontalHeaderItem(0, icon1)
            self.diskTable.setHorizontalHeaderItem(1, icon2)
            self.diskTable.setHorizontalHeaderItem(2, icon3)
            self.diskTable.setHorizontalHeaderItem(3, icon4)
            self.diskTable.setHorizontalHeaderItem(4, icon5)
            self.diskTable.setHorizontalHeaderItem(5, icon6) 
            if (logicalIndex==0):
                icon = QtWidgets.QTableWidgetItem("Device")
            elif(logicalIndex==1):
                icon = QtWidgets.QTableWidgetItem("Directory")
            elif(logicalIndex==2):
                icon = QtWidgets.QTableWidgetItem("Type")
            elif(logicalIndex==3):
                icon = QtWidgets.QTableWidgetItem("Total")
            elif(logicalIndex==4):
                icon = QtWidgets.QTableWidgetItem("Available")
            elif(logicalIndex==5):
                icon = QtWidgets.QTableWidgetItem("Used")
            try:
                if self.switch:
                    icon.setIcon(QtGui.QIcon(self.icon_dir[1:] + "down_arrow4.png"))
                else:
                    icon.setIcon(QtGui.QIcon(self.icon_dir[1:] + "up_arrow2.png"))
                self.diskTable.setHorizontalHeaderItem(logicalIndex, icon)
            except:
                pass

    def preInfoGrab(self, event):

        if not self.search_change:
            self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 525))
        else:
            self.tableWidget.setGeometry(QtCore.QRect(0, 70, 820, 490))
            
        self.PEnd.setVisible(True)
        self.PSet.setVisible(True)
        self.set_event = self.PSet.pos()

        try:
            item = self.tableWidget.indexAt(event.pos())
        except:
            item = self.tableWidget.indexAt(event)
            
        if item.row()==-1:
            return None 
        try:
            self.proc = psutil.Process(pids[item.row()])
        except (IndexError, TypeError) as e:
            return None
        
        self.trace_pid = pids[item.row()]
        self.terminated = False
        
        if (self.OldSet == item.row()) & (not self.LeftUpdate):
            self.Unselected = not self.Unselected
            
        if self.OldSet != item.row():
            self.Unselected = False
        
        if self.Unselected:
            self.tableWidget.clearSelection()
            if not self.search_change:
                self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 565))
            else:
                self.tableWidget.setGeometry(QtCore.QRect(0, 70, 820, 535))
            self.PEnd.setVisible(False)
            self.PSet.setVisible(False)
   
        self.OldSet = item.row()
        self.LeftUpdate = False  

        gc.collect()

    def animate(self, wlist, ax, canvas, style):

        ax.clear()
        if self.pltgrid:
            ax.grid(True, color='#C8C8C8')
        
        if ((style==0) or (style==2)) & ((wlist!=self.netList) & (wlist!=self.tempList)):
            ax.set_ylim([0, 100])
            base = 50
        else:
            if max(wlist)>2.0:
                base = int(max(wlist)/2)
                ax.set_ylim([0, max(wlist)*1.1])
            else:
                base = 1
        if (wlist==self.tempList) & (self.tfchoice==0):
            ax.set_ylim([0, self.tcrit])
            base = int(self.tcrit/2)
            ax.plot(self.timeList, [self.thigh]*20, color="red")
            
        loc = plticker.MultipleLocator(base=base)
        ax.yaxis.set_major_locator(loc)
        
        if wlist==self.cpuList:
            fmt = '%.0f%%'
            yticks = plticker.FormatStrFormatter(fmt)
            ax.yaxis.set_major_formatter(yticks)
            ax.set_title('CPU Usage')
            ax.set_xlabel('Time (seconds)') 
        elif wlist==self.memList:
            fmt = '%.0f%%'
            yticks = plticker.FormatStrFormatter(fmt)
            ax.yaxis.set_major_formatter(yticks)
            ax.set_title('Memory Usage')
            ax.set_xlabel('Time (seconds)')
        elif wlist==self.netList:
            fmtlist = self.Memstring(self.baselist)
            ax.set_yticklabels([fmt + "/s" for fmt in fmtlist], Fontsize=9)
            ax.set_title('Network Usage')
            ax.set_xlabel('Time (seconds)')
        elif wlist==self.tempList:
            if self.tfchoice==0:
                ax.set_title('CPU Temperature')
                if self.tunit==0:
                    cel = u"\N{DEGREE SIGN}" + 'C'
                    ax.set_yticklabels(['', '0'+cel, str(int(self.tcrit/2))+cel, str(int(self.tcrit))+cel])
                else:
                    far = u"\N{DEGREE SIGN}" + 'F'
                    ax.set_yticklabels(['', '0'+far, str(int(self.tcrit/2))+far, str(int(self.tcrit))+far])
            else:
                ax.set_title('Fan Speed')
                ax.set_yticklabels(['', '0'+' rpm', str(int(max(wlist)/2))+' rpm', str(max(wlist))+' rpm'])
            ax.set_xlabel('Time (seconds)')

        ax.set_xlim([0,60])
        ax.invert_xaxis()
        wlist = wlist[::-1]

        if (style==0) or ((style==1) & ((wlist!=self.netList) & (wlist!=self.tempList))):
            ax.plot(self.timeList, wlist, color="black")
        else:
            ax.bar(self.timeList, wlist, width=1.8, color="black")
        canvas.draw()

        wlist = wlist[::-1]

        if wlist==self.netList:
            ticklist = list(ax.yaxis.get_majorticklabels())
            self.baselist = ['0']
            for i in range(len(ticklist)-2):
                rip = str(ticklist[i+1]).split("0, ")[1]
                self.baselist.append(rip.replace('.',''))

    def popWindow(self, size, label, table):

        Window = QtWidgets.QMainWindow(self.centralwidget)
        Window.setStyleSheet("QMainWindow { background:rgb(144,118,98);}")
        
        if size==0:
            Window.resize(500, 200)
            Window.setMinimumSize(QtCore.QSize(500, 200))
            Window.setMaximumSize(QtCore.QSize(500, 200))
            mainWidget = QtWidgets.QWidget(Window)
            mainWidget.setGeometry(QtCore.QRect(0, 0, 500, 200))
        else:
            Window.resize(500, 300)
            Window.setMinimumSize(QtCore.QSize(500, 300))
            Window.setMaximumSize(QtCore.QSize(500, 300))
            mainWidget = QtWidgets.QWidget(Window)
            mainWidget.setGeometry(QtCore.QRect(0, 0, 500, 300))

        if label:
            mainLbl = QtWidgets.QLabel(mainWidget)
            xFont = QtGui.QFont('5', 12)
            xFont.setBold(True)
            mainLbl.setFont(xFont) 
            mainLbl.setAlignment(QtCore.Qt.AlignCenter)
        else:
            mainLbl = False

        if table:
            mainTable = QtWidgets.QTableWidget(mainWidget)
            mainTable.setGeometry(QtCore.QRect(0, 0, 500, 300)) 
            mainTable.setShowGrid(False)
            mhheader = mainTable.horizontalHeader()
            mhheader.setDefaultAlignment(QtCore.Qt.AlignLeft)
            mvheader = mainTable.verticalHeader()
            mvheader.setVisible(False)
            mainTable.setStyleSheet("QTableWidget{color:rgb(0,0,0)}")
        else:
            mainTable = False

        return Window, mainWidget, mainLbl, mainTable
        
        
    def procExists(self):

        ExWindow, exWidget, xLbl, xTable = self.popWindow(0, True, False)

        ExWindow.setWindowTitle('Cancel Action')
        xLbl.setGeometry(QtCore.QRect(0, 0, 500, 90))
        exLbl = QtWidgets.QLabel(exWidget)
        exLbl.setGeometry(QtCore.QRect(0, 70, 500, 50))
        exLbl.setFont(QtGui.QFont('5', 10))
        exLbl.setAlignment(QtCore.Qt.AlignCenter)
        imLbl = QtWidgets.QLabel(exWidget)
        imLbl.setGeometry(QtCore.QRect(20, 70, 50, 50))
        imLbl.setStyleSheet("QLabel{background-color:transparent;\n"
"       background-image: url(" + self.icon_dir + "warning2.png\");\n"
"       background-position: center; background-repeat: no-repeat;}")
        xLbl.setText('Process No Longer Exists!')
        exLbl.setText('This may be due to the thread being terminated \nor a new process has been called')
                               
        ExWindow.show()

        gc.collect()

    def procDenied(self):

        deniedWindow, deniedWidget, permisLbl, dTable = self.popWindow(1, True, False)

        deniedWindow.setWindowTitle('Cancel Action')
        permisLbl.setGeometry(QtCore.QRect(0, 50, 500, 90))
        permisLbl.setText("PERMISSION DENIED!")
        propLbl = QtWidgets.QLabel(deniedWidget)
        propLbl.setGeometry(QtCore.QRect(0, 90, 500, 90))
        propLbl.setFont(QtGui.QFont('5', 11))
        propLbl.setAlignment(QtCore.Qt.AlignCenter)
        propLbl.setText('for process:\n"' + self.proc.name() + '" with PID: ' + str(self.proc.pid))
        imageLbl = QtWidgets.QLabel(deniedWidget)
        imageLbl.setGeometry(QtCore.QRect(80, 78, 50, 50))
        imageLbl.setStyleSheet("QLabel{background-color:transparent;\n"
"           background-image: url(" + self.icon_dir + "warning2.png\");\n"
"           background-position: center; background-repeat: no-repeat;}")

        deniedWindow.show()

        gc.collect()
        

    def procSudo(self, **kwargs):

        nice = 30
        for key, component in kwargs.items():
            if key == 'nice':
                nice = component
            elif key == 'button':
                button = component

        SudoWindow = QtWidgets.QMainWindow(self.centralwidget)
        SudoWindow.resize(500, 300)
        SudoWindow.setMinimumSize(QtCore.QSize(500, 300))
        SudoWindow.setMaximumSize(QtCore.QSize(500, 300))
        SudoWindow.setWindowTitle('Authentication Required')
        sudoWidget = QtWidgets.QWidget(SudoWindow)
        sudoWidget.setGeometry(QtCore.QRect(0, 0, 500, 300))

        sudoLbl = QtWidgets.QLabel(sudoWidget)
        sudoLbl.setGeometry(QtCore.QRect(0, 30, 500, 90))
        sudoFont = QtGui.QFont('5', 13)
        sudoFont.setBold(True)  
        sudoLbl.setFont(sudoFont)
        sudoLbl.setAlignment(QtCore.Qt.AlignCenter)
        sudoLbl.setText("Authentication Required")
        propLbl = QtWidgets.QLabel(sudoWidget)
        propLbl.setGeometry(QtCore.QRect(0, 80, 500, 90))
        propLbl.setFont(QtGui.QFont('5', 11))
        propLbl.setAlignment(QtCore.Qt.AlignCenter)
        propLbl.setText('Root privileges are required for process:\n"' + self.proc.name() + '" with PID: ' + str(self.proc.pid) + '\n and user: ' + str(self.proc.username()))
        imageLbl = QtWidgets.QLabel(sudoWidget)
        imageLbl.setGeometry(QtCore.QRect(55, 40, 70, 70))
        imageLbl.setStyleSheet("QLabel{background-color:transparent;\n"
"           background-image: url(" + self.icon_dir + "key3.png\");\n"
"           background-position: center; background-repeat: no-repeat;}")

        passLbl = QtWidgets.QLabel(sudoWidget)
        passLbl.setGeometry(QtCore.QRect(60, 170, 70, 30))
        passLbl.setAlignment(QtCore.Qt.AlignCenter)
        passLbl.setText("Password:")
        sudoEdit = QtWidgets.QLineEdit(sudoWidget)
        sudoEdit.setGeometry(QtCore.QRect(140, 170, 260, 30))
        sudoEdit.setFont(sudoFont)
        sudoEdit.setFocusPolicy(QtCore.Qt.StrongFocus)
        sudoEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        sudoEdit.setStyleSheet("QLineEdit {color: rgb(0,0,0); background: rgb(124,98,78); selection-background-color: rgb(159,36,37); }\n"
"       QLineEdit:hover{background: rgb(159,36,37);}\n"
"       QLineEdit[echoMode='2'] {lineedit-password-character: 9679;}")

        Cancel = QtWidgets.QPushButton(sudoWidget)
        Cancel.setGeometry(QtCore.QRect(0, 260, 250, 40))
        Cancel.setText('Cancel')
        Cancel.setStyleSheet("QPushButton{background-color:rgb(209,209,211);}\n"
"       QPushButton:hover{background-color:rgb(229,229,231);}\n")
        Cancel.clicked.connect(partial(self.pclose, Window=SudoWindow))
         
        Action = QtWidgets.QPushButton(sudoWidget)
        Action.setGeometry(QtCore.QRect(250, 260, 250, 40))
        Action.setText('Authenticate')
        Action.setStyleSheet("QPushButton{background-color:rgb(159,36,37);}\n"
"       QPushButton:hover{background-color:rgb(179,56,57);}\n")
        if nice!=30:
            Action.clicked.connect(partial(self.authenticate, Window=SudoWindow, Text=sudoEdit, nice=nice, button=button))
        else:
            Action.clicked.connect(partial(self.authenticate, Window=SudoWindow, Text=sudoEdit))
        SudoWindow.show()

        gc.collect()
        
    def promptAction(self,prompt):

        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None
            
        wproc = self.proc.name()

        EndWindow, endWidget, procLbl, endTable = self.popWindow(0, True, False)
        
        EndWindow.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)
        EndWindow.setWindowTitle('Prompt Process Action')
        procLbl.setGeometry(QtCore.QRect(0, 0, 500, 90))
        warningLbl = QtWidgets.QLabel(endWidget)
        warningLbl.setGeometry(QtCore.QRect(0, 70, 500, 50))
        warningLbl.setFont(QtGui.QFont('5', 10))
        warningLbl.setAlignment(QtCore.Qt.AlignCenter)
        imageLbl = QtWidgets.QLabel(endWidget)
        imageLbl.setGeometry(QtCore.QRect(20, 70, 50, 50))
        imageLbl.setStyleSheet("QLabel{background-color:transparent;\n"
"       background-image: url(" + self.icon_dir + "warning2.png\");\n"
"       background-position: center; background-repeat: no-repeat;}")
        Cancel = QtWidgets.QPushButton(endWidget)
        Cancel.setGeometry(QtCore.QRect(0, 160, 250, 40))
        Cancel.setText('Cancel')
        Cancel.setStyleSheet("QPushButton{background-color:rgb(209,209,211);}\n"
"       QPushButton:hover{background-color:rgb(229,229,231);}\n")
        Cancel.clicked.connect(partial(self.pclose, Window=EndWindow))
         
        Action = QtWidgets.QPushButton(endWidget)
        Action.setGeometry(QtCore.QRect(250, 160, 250, 40))
        Action.setStyleSheet("QPushButton{background-color:rgb(159,36,37);}\n"
"       QPushButton:hover{background-color:rgb(179,56,57);}\n") 
        if prompt==0:
            Action.setText('End Process')
            if len(self.proc.name())<30:
                procLbl.setText('CONFIRM TO END PROCESS: \n"' + str(wproc) + '" with PID: ' + str(self.trace_pid))
            else:
                procLbl.setText('CONFIRM TO END PROCESS: \n"' + str(wproc) + '"\nwith PID: ' + str(self.trace_pid))
            warningLbl.setText('Ending a process may cause data loss or corruption,\nbreak the session, or raise a security risk.\nPlease reconsider if the proccess is still responsive.')
            Action.clicked.connect(partial(self.end, Window=EndWindow))
        if prompt==1:
            Action.setText('Kill Process')
            if len(self.proc.name())<30:
                procLbl.setText('CONFIRM TO KILL PROCESS: \n"' + str(wproc) + '" with PID: ' + str(self.trace_pid))
            else:
                procLbl.setText('CONFIRM TO KILL PROCESS: \n"' + str(wproc) + '"\nwith PID: ' + str(self.trace_pid))
            warningLbl.setText('Killing a process may cause data loss or corruption,\nbreak the session, or raise a security risk.\nPlease reconsider if the proccess is still responsive.')
            Action.clicked.connect(partial(self.end, Window=EndWindow))
                    
        EndWindow.show()

        gc.collect()

    def warnAction(self, wname, wdir, opts):

        WarnWindow, warnWidget, procLbl, warnTable = self.popWindow(0, True, False)
        
        WarnWindow.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)
        WarnWindow.setWindowTitle('Long Action Warning')
        procLbl.setGeometry(QtCore.QRect(0, 0, 500, 90))
        warningLbl = QtWidgets.QLabel(warnWidget)
        warningLbl.setGeometry(QtCore.QRect(0, 70, 500, 80))
        warningLbl.setFont(QtGui.QFont('5', 10))
        warningLbl.setAlignment(QtCore.Qt.AlignCenter)
        imageLbl = QtWidgets.QLabel(warnWidget)
        imageLbl.setGeometry(QtCore.QRect(80, 30, 50, 50))
        imageLbl.setStyleSheet("QLabel{background-color:transparent;\n"
"       background-image: url(" + self.icon_dir + "warning2.png\");\n"
"       background-position: center; background-repeat: no-repeat;}")

        warnRdbtn = QtWidgets.QCheckBox(warnWidget)
        warnRdbtn.setGeometry(QtCore.QRect(368, 133, 15, 15))
        warnRdbtn.setStyleSheet("QCheckBox{border: 2px solid rgb(138,108,88); color:rgb(169,46,47); background-color:rgb(178,148,128);}\n"
"       QCheckBox:indicator{color:rgb(169,46,47); width: 15px; height: 15px;}")        
        if not self.disklimit:
            warnRdbtn.setChecked(True)
        else:
            warnRdbtn.setChecked(False)
        warnRdbtn.stateChanged.connect(partial(self.warnlookup, btn=warnRdbtn))
        
        Cancel = QtWidgets.QPushButton(warnWidget)
        Cancel.setGeometry(QtCore.QRect(0, 160, 250, 40))
        Cancel.setText('Cancel')
        Cancel.setStyleSheet("QPushButton{background-color:rgb(209,209,211);}\n"
"       QPushButton:hover{background-color:rgb(229,229,231);}\n")
        Cancel.clicked.connect(partial(self.pclose, Window=WarnWindow))
         
        Action = QtWidgets.QPushButton(warnWidget)
        Action.setGeometry(QtCore.QRect(250, 160, 250, 40))
        Action.setText('Continue')
        Action.setStyleSheet("QPushButton{background-color:rgb(159,36,37);}\n"
"       QPushButton:hover{background-color:rgb(179,56,57);}\n") 
        procLbl.setText('Time Required Action!')
        warningLbl.setText('Properties will attempt to find \nthe number of directories and files for the selected device.\nThis process may take longer than > 1 minute \nand may cause the program to hang until completion. \n Look for directory and file count?')
        Action.clicked.connect(partial(self.diskProp, wname=wname, wdir=wdir, opts=opts))
        Action.clicked.connect(partial(self.pclose, Window=WarnWindow))
                   
        WarnWindow.show()

        gc.collect()


    def Memstring(self, memlist):

        for i in range(len(memlist)):
            try:
                val = float(memlist[i])
            except:
                memlist[i] = str(memlist[i])
                continue
            if val<2**10:
                memlist[i] = str(int(val)) + ' bytes'
            elif val<2**20:
                memlist[i] = str(round((val/2**10),1)) + ' KiB' 
            elif val<2**30:
                memlist[i] = str(round((val/2**20),1)) + ' MiB'
            elif val<2**40:
                memlist[i] = str(round((val/2**30),1)) + ' GiB'
            else:
                memlist[i] = str(round((val/2**40),1)) + ' TiB'

        return memlist
    
    def Memstring2(self, memlist):
        
        for i in range(len(memlist)):
            try:
                val = float(memlist[i])
            except:
                memlist[i] = str(memlist[i])
                continue
            if val<10e2:
                memlist[i] = str(int(val)) + ' bytes'
            elif val<10e5:
                memlist[i] = str(round((val/10e2),1)) + ' KiB' 
            elif val<10e8:
                memlist[i] = str(round((val/10e5),1)) + ' MiB'
            elif val<10e11:
                memlist[i] = str(round((val/10e8),1)) + ' GiB'
            else:
                memlist[i] = str(round((val/10e11),1)) + ' TiB'

        return memlist

    def Timestring(self, memlist):
        
        for i in range(len(memlist)):
            val = float(memlist[i])
            if val<60:
                memlist[i] = str(round(val,2)) + ' s'
            elif val<3600:
                minutes = val/60
                seconds = (minutes%1)*60
                memlist[i] = str(int(minutes)) + ' m ' + str(int(seconds)) + ' s'
            elif val<86400:
                hours = val/3600
                minutes = (hours%1)/60
                seconds = (minutes%1)*60
                memlist[i] = str(int(hours)) + ' h ' + str(int(minutes)) + ' m ' + str(int(seconds)) + ' s'
            else:
                days = val/86400
                hours = (days%1)/3600
                minutes = (hours%1)/60
                seconds = (minutes%1)*60
                memlist[i] = str(int(days)) + ' d ' +str(int(hours)) + ' h ' + str(int(minutes)) + ' m ' + str(int(seconds)) + ' s'

        return memlist
        
    def Properties(self):

        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None
  
        try:
            PropWindow, propWidget, Lbl, propTable = self.popWindow(1, False, True)
            PropWindow.setWindowTitle('Properties')
            
            with self.proc.oneshot():
                wproc = self.proc.name()
                wuser = self.proc.username()
                wstat = self.proc.status()
                mfi = self.proc.memory_full_info()
                wmpercent = self.proc.memory_percent()
                waffinity = self.proc.cpu_affinity()
                ct = self.proc.cpu_times()
                wnthreads = self.proc.num_threads()
                wfds = self.proc.num_fds()
                ic = self.proc.io_counters()
                sw = self.proc.num_ctx_switches()
                wterm = self.proc.terminal()
                wnice = self.proc.nice()
                wionice = self.proc.ionice() 
                wpid = self.proc.pid
                wcwd = self.proc.cwd()
                wexe = self.proc.exe()
                wcmdline = self.proc.cmdline()
                wvmslim = self.proc.rlimit(psutil.RLIMIT_AS)
                wcore = self.proc.rlimit(psutil.RLIMIT_CORE)
                wcpu = self.proc.rlimit(psutil.RLIMIT_CPU)
                wdatalim = self.proc.rlimit(psutil.RLIMIT_DATA)
                wfsize = self.proc.rlimit(psutil.RLIMIT_FSIZE)
                wlocks = self.proc.rlimit(psutil.RLIMIT_LOCKS)
                wmemlock = self.proc.rlimit(psutil.RLIMIT_MEMLOCK)
                wmsgqueue = self.proc.rlimit(psutil.RLIMIT_MSGQUEUE)
                wnicelim = self.proc.rlimit(psutil.RLIMIT_NICE)
                wnofile = self.proc.rlimit(psutil.RLIMIT_NOFILE)
                wnproc = self.proc.rlimit(psutil.RLIMIT_NPROC)
                wrsslim = self.proc.rlimit(psutil.RLIMIT_RSS)
                wrtprio = self.proc.rlimit(psutil.RLIMIT_RTPRIO)
                wrttime = self.proc.rlimit(psutil.RLIMIT_RTTIME)
                wpending = self.proc.rlimit(psutil.RLIMIT_SIGPENDING)
                wstack = self.proc.rlimit(psutil.RLIMIT_STACK)

            wvolunt = sw.voluntary
            winvolunt = sw.involuntary
        
            wrss = mfi.rss
            wvms = mfi.vms
            wswap = mfi.swap
            wshared = mfi.shared
            wpss = mfi.pss
            wtext = mfi.text
            wlib = mfi.lib
            wdata = mfi.data
            wdirty = mfi.dirty 
        
            wstarted = (str(self.proc).split("started='")[1]).split("'")[0]
            wcmdline = ' '.join(wcmdline)
            wcmdline = sub("(.{32})", "\\1\n", wcmdline, 0, DOTALL)
            wexe = sub("(.{32})", "\\1\n", wexe, 0, DOTALL)

            wcputime = self.Timestring([int(sum(ct))])[0]
            wusertime = self.Timestring([ct.user])[0]
            wsystime = self.Timestring([ct.system])[0]
            wchildUtime = self.Timestring([ct.children_user])[0]
            wchildStime = self.Timestring([ct.children_system])[0]
            wiotime = self.Timestring([ct.iowait])[0]
        
            wioread = ic.read_count
            wiowrite = ic.write_count
            wioreadb = ic.read_bytes
            wiowriteb = ic.write_bytes
            wioreadc = ic.read_chars
            wiowritec = ic.write_chars

            policy = sched_getscheduler(wpid)
            param = str(sched_getparam(wpid))
            param = param.replace(')', '').split('=')[1]
            rrquantum = sched_rr_get_interval(wpid)
            rrquantum = self.Timestring([rrquantum])[0]

            if policy==SCHED_OTHER:
                policy = 'Default'
                
            elif policy==SCHED_BATCH:
                policy = 'CPU-intensive'

            elif policy==SCHED_IDLE:
                policy = 'Low Priority'

            elif policy==SCHED_FIFO:
                policy = 'Fist-In-First-Out'

            elif policy==SCHED_RR:
                policy = 'Round-robin'

            wrss = self.Memstring([wrss])[0]
            wvms = self.Memstring([wvms])[0]
            wswap = self.Memstring([wswap])[0]
            wshared = self.Memstring([wshared])[0]
            wpss = self.Memstring([wpss])[0]
            wtext = self.Memstring([wtext])[0]
            wlib = self.Memstring([wlib])[0]
            wdata = self.Memstring([wdata])[0]
            wdirty = self.Memstring([wdirty])[0]
            wioreadb = self.Memstring([wioreadb])[0]
            wiowriteb = self.Memstring([wiowriteb])[0]
            queries = ['Process Name', 'User', 'PID', 'Status', 'Started','Using', 'Resident [RSS]', 'Virtual [VMS]', 'Swap', 'Shared', 'Proportional [PRS]', 'Text [TRS]', 'Data [DRS]', 'Shared Libraries ', 'Dirty', 'Affinity', 'Overall Time', 'User Time', 'System Time', 'Children User Time', 'Children System Time', 'IOwait Time', 'Location', 'Executable', 'Terminal', 'Cmdline', 'Threads', 'Voluntary Switches', 'Involuntary Switches', 'FDs', 'Nice', 'IONice', 'IO Read Count', 'IO Write Count', 'IO Read Bytes', 'IO Write Bytes', 'IO Read Chars', 'IO Write Chars', 'Max Virtual Memory', 'Max Core File Size', 'CPU Time Limit', 'Max Data Segment Size', 'Max Create File Size', 'Combined Locks', 'Max Locked Ram Memory', 'POSIX Message Queues', 'Nice', 'Max FDs', 'Max Threads', 'Max Resident Memory', 'Priority Ceiling', 'CPU Scheduled Time', 'Pending Signals', 'Max Stack Size', 'Policy', 'Priority', 'Round-Robin Quantum']
            results = [wproc, wuser, wpid, wstat, wstarted, str(round(wmpercent,2))+'%', wrss, wvms, wswap, wshared, wpss, wtext, wlib, wdata, wdirty, len(waffinity), wcputime, wusertime, wsystime, wchildUtime, wchildStime, wiotime, wcwd, wexe, wterm, wcmdline, wnthreads, wvolunt, winvolunt, wfds, wnice, wionice.value, wioread, wiowrite, wioreadb, wiowriteb, wioreadc, wiowritec, wvmslim, wcore, wcpu, wdatalim, wfsize, wlocks, wmemlock, wmsgqueue, wnicelim, wnofile, wnproc, wrsslim, wrtprio, wrttime, wpending, wstack, policy, param, rrquantum] 
            collection = [queries, results]

            propTable.setColumnCount(2)
            propTable.setRowCount(64)
            propTable.setColumnWidth(0, 200)
            propTable.setColumnWidth(1, 300)
            propTable.setRowHeight(27, int(len(wexe)))
            propTable.setRowHeight(29, int(len(wcmdline)))
            phheader = propTable.horizontalHeader()
            phheader.setVisible(False)

            slices = ['Main:', 'Memory:', 'CPU:', 'General:', 'Nice & IO:', 'Resource Limits:', 'Scheduler:']
            sliceFont = QtGui.QFont('5', 10.5)
            sliceFont.setBold(True)
            sliceFont.setUnderline(True)
            count = 0

            for i in range(2):
                count1 = 0
                for j in range(64):
                    item_prop = QtWidgets.QTableWidgetItem()
                    item_prop.setFlags(QtCore.Qt.NoItemFlags)
                    propTable.setItem(j, i, item_prop)
                    if (j==0) or (j==6) or (j==17) or (j==25) or (j==34) or (j==43) or (j==60):
                        item_prop.setBackground(QtGui.QColor(209,209,211))
                        propTable.setRowHeight(j,1)
                        if i==0:
                            item_prop.setFont(sliceFont)
                            item_prop.setText(slices[count])
                            count += 1
                        count1 += 1
                    else:
                        try:
                            item_prop.setText(str(collection[i][j-count1]))
                        except IndexError: 
                            item_prop.setText('')
                    del item_prop

            PropWindow.show()

        except:
            self.procDenied()

        gc.collect()
            
    def Memapper(self):
        
        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None

        try:

            wproc = self.proc.name()

            MapWindow, mapWidget, mapLbl, mapTable = self.popWindow(1, True, True)
        
            MapWindow.setWindowTitle('Memory Maps')
            mapLbl = QtWidgets.QLabel(mapWidget)
        
            memap = self.proc.memory_maps()
            path = []
            rss = []
            pss = []
            size = []
            pclean = []
            pdirty = []
            sclean = []
            sdirty = []
            ref = []
            anon = []
            swap = []

            for i in range(len(memap)):
                path.append(memap[i].path)
                rss.append(memap[i].rss)
                pss.append(memap[i].pss)
                pclean.append(memap[i].private_clean)
                pdirty.append(memap[i].private_dirty)
                sclean.append(memap[i].shared_clean)
                sdirty.append(memap[i].shared_dirty)
                ref.append(memap[i].referenced)
                anon.append(memap[i].anonymous)
                swap.append(memap[i].swap)
 
            mapLbl.setGeometry(QtCore.QRect(0, 5, 500, 23))
            mapLbl.setAlignment(QtCore.Qt.AlignLeft)
            mapLbl.setFont(QtGui.QFont('5', 10))
            mapLbl.setText('memap for process "' + wproc + '" with PID: ' + str(self.proc.pid))                
            mapTable.setGeometry(QtCore.QRect(0, 23, 500, 277))
            mapTable.setColumnCount(11)
            mapTable.setRowCount(len(memap))
            mapTable.setColumnWidth(0, 300)
            mapTable.setHorizontalHeaderLabels(['Path', 'RSS', 'PSS', 'Size', 'Private Clean', 'Private Dirty', 'Shared Clean', 'Shared Dirty', 'Referenced', 'Anonymous', 'Swap'])

            rss = self.Memstring(rss)
            pss = self.Memstring(pss)
            size = self.Memstring(size)
            pclean = self.Memstring(pclean)
            pdirty = self.Memstring(pdirty)
            sclean = self.Memstring(sclean)
            sdirty = self.Memstring(sdirty)
            ref = self.Memstring(ref)
            anon = self.Memstring(anon)
            swap = self.Memstring(swap)
            collection = [path, rss, pss, size, pclean, pdirty, sclean, sdirty, ref, anon, swap]

            for i in range(11): 
                for j in range(len(path)):
                    item_map = QtWidgets.QTableWidgetItem()
                    item_map.setFlags(QtCore.Qt.NoItemFlags)
                    mapTable.setItem(j, i, item_map)
                    try:
                        item_map.setText(str(collection[i][j]))
                    except IndexError: 
                        item_map.setText('')
                    del item_map

            MapWindow.show()

        except:
            self.procDenied()

        gc.collect()

    def Openfile(self):
        
        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None

        try:
            wproc = self.proc.name()

            OpnWindow, opnWidget, opnLbl, opnTable = self.popWindow(1, False, True)
        
            OpnWindow.setWindowTitle('Open Files')
            opnLbl = QtWidgets.QLabel(opnWidget)
        
            opnfile = self.proc.open_files()
            path = []
            fd = []
            position = []
            mode = []
            flags = []

            for i in range(len(opnfile)):
                path.append(opnfile[i].path)
                fd.append(opnfile[i].fd)
                position.append(opnfile[i].position)
                mode.append(opnfile[i].mode)
                flags.append(opnfile[i].flags)
 
            opnLbl.setGeometry(QtCore.QRect(0, 5, 500, 23))
            opnLbl.setFont(QtGui.QFont('5', 10))
            opnLbl.setAlignment(QtCore.Qt.AlignLeft)
            opnLbl.setText('open files for process "' + wproc + '" with PID: ' + str(self.proc.pid))                
            opnTable.setGeometry(QtCore.QRect(0, 23, 500, 277))
            opnTable.setColumnCount(5)
            opnTable.setRowCount(len(opnfile))
            opnTable.setColumnWidth(0, 200)
            opnTable.setHorizontalHeaderLabels(['Path', 'FD', 'Position', 'Mode', 'Flags', 'Private Dirty'])

            collection = [path, fd, position, mode, flags]

            for i in range(5): 
                for j in range(len(path)):
                    item_opn = QtWidgets.QTableWidgetItem()
                    item_opn.setFlags(QtCore.Qt.NoItemFlags)
                    opnTable.setItem(j, i, item_opn)
                    try:
                        item_opn.setText(str(collection[i][j]))
                    except IndexError: 
                        item_opn.setText('')
                    del item_opn

            OpnWindow.show()

        except:
            self.procDenied()

        gc.collect()

    def procThreads(self):

        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None

        try:
            wproc = self.proc.name()

            ThreadWindow, threadWidget, threadLbl, threadTable = self.popWindow(1, False, True)
        
            ThreadWindow.setWindowTitle('Process Threads')
            threadLbl = QtWidgets.QLabel(threadWidget)

            threads = self.proc.threads()

            threadLbl.setFont(QtGui.QFont('5', 10))
            threadLbl.setAlignment(QtCore.Qt.AlignLeft)
            threadLbl.setText('open threads for process "' + wproc + '" with PID: ' + str(self.proc.pid))                
            threadTable.setGeometry(QtCore.QRect(0, 23, 500, 277))
            threadTable.setColumnCount(3)
            threadTable.setRowCount(len(threads))
            threadTable.setColumnWidth(0, 170)
            threadTable.setColumnWidth(1, 165)
            threadTable.setColumnWidth(2, 165)
            threadTable.setHorizontalHeaderLabels(['PID', 'User Time', 'System Time'])

            thread_id = []
            utime = []
            systime = []
            for item in threads:
                thread_id.append(item.id)
                utime.append(self.Timestring([item.user_time])[0])
                systime.append(self.Timestring([item.system_time])[0])

            collection = [thread_id, utime, systime]

            for i in range(3): 
                for j in range(len(threads)):
                    item_thread = QtWidgets.QTableWidgetItem()
                    item_thread.setFlags(QtCore.Qt.NoItemFlags)
                    threadTable.setItem(j, i, item_thread)
                    try:
                        item_thread.setText(str(collection[i][j]))
                    except IndexError: 
                        item_thread.setText('')
                    del item_thread

            ThreadWindow.show()
                
        except:
            self.procDenied()

        gc.collect()

    def procPC(self):

        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None

        try:
            wproc = self.proc.name()

            PCWindow, pcWidget, pcLbl, pcTable = self.popWindow(1, False, True)
        
            PCWindow.setWindowTitle('Parents & Children Processes')
            pcLbl = QtWidgets.QLabel(pcWidget)

            parents = self.proc.parents()
            children = self.proc.children()

            nrows = len(parents)+len(children)+3 

            pcLbl.setGeometry(QtCore.QRect(0, 5, 500, 23))
            pcLbl.setFont(QtGui.QFont('5', 10))
            pcLbl.setAlignment(QtCore.Qt.AlignLeft)
            pcLbl.setText('P&C processes for process "' + wproc + '" with PID: ' + str(self.proc.pid))                
            pcTable.setGeometry(QtCore.QRect(0, 23, 500, 277))
            pcTable.setColumnCount(4)
            pcTable.setRowCount(nrows) 
            pcTable.setColumnWidth(0, 200)
            pcTable.setHorizontalHeaderLabels(['Name', 'PID', 'Started', 'Status'])

            named = []
            pided= []
            started = []
            status = []
            for i in range(len(parents)+1):
                if i==0:
                    named.append('Parent Processes')
                    pided.append('')
                    started.append('')
                    status.append('')
                else:
                    named.append(parents[i-1].name())
                    pided.append(parents[i-1].pid)
                    start = str(parents[i-1]).split("started='")[1]
                    start = start.split("'")[0]
                    started.append(start)
                    status.append(parents[i-1].status())
                
            for i in range(len(children)+2):
                if i==0:
                    named.append('')
                    pided.append('')
                    started.append('')
                    status.append('')
                elif i==1:
                    named.append('Children Processes')
                    pided.append('')
                    started.append('')
                    status.append('')
                else:
                    named.append(children[i-2].name())
                    pided.append(children[i-2].pid)
                    start = str(children[i-2]).split("started='")[1]
                    start = start.split("'")[0]
                    started.append(start)
                    status.append(children[i-2].status())

            collection = [named, pided, started, status]

            headingFont = QtGui.QFont('5', 10.5)
            headingFont.setBold(True)
            headingFont.setUnderline(True)

            for i in range(4): 
                for j in range(nrows):
                    item_pc = QtWidgets.QTableWidgetItem()
                    item_pc.setFlags(QtCore.Qt.NoItemFlags)
                    pcTable.setItem(j, i, item_pc)
                    try:
                        if (j==0) or (j==(len(parents)+2)):
                            item_pc.setFont(headingFont)
                        item_pc.setText(str(collection[i][j]))
                    except IndexError: 
                        item_pc.setText('')
                    del item_pc

            PCWindow.show()
                
        except:
            self.procDenied()

        gc.collect()

    def procEnv(self):

        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None

        try:
            wproc = self.proc.name()

            EnvWindow, envWidget, envLbl, envTable = self.popWindow(1, False, True)
        
            EnvWindow.setWindowTitle('Process Environment Variables')
            envLbl = QtWidgets.QLabel(envWidget)

            env = self.proc.environ()
            keys = list(env.keys())
            vals = list(env.values())

            envLbl.setGeometry(QtCore.QRect(0, 5, 500, 23))
            envLbl.setFont(QtGui.QFont('5', 10))
            envLbl.setAlignment(QtCore.Qt.AlignLeft)
            envLbl.setText('env variables for process "' + wproc + '" with PID: ' + str(self.proc.pid))                
            envTable.setGeometry(QtCore.QRect(0, 23, 500, 277))
            envTable.setColumnCount(2)
            envTable.setRowCount(len(keys))
            envTable.setColumnWidth(0, 200)
            envTable.setColumnWidth(1, 400)
            envTable.setHorizontalHeaderLabels(['Name', 'Value'])
            
            collection = [keys, vals]

            for i in range(2):
                for j in range(len(keys)):
                    item_env = QtWidgets.QTableWidgetItem()
                    item_env.setFlags(QtCore.Qt.NoItemFlags)
                    envTable.setItem(j, i, item_env)
                    try:
                        item_env.setText(str(collection[i][j]))
                    except IndexError: 
                        item_env.setText('')
                    del item_env

            EnvWindow.show()
                
        except:
            self.procDenied()

        gc.collect()

    def procNice(self, button):

        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None

        try:
        
            NiceWindow = QtWidgets.QMainWindow(self.centralwidget)
            NiceWindow.resize(480, 160)
            NiceWindow.setMinimumSize(QtCore.QSize(480, 160))
            NiceWindow.setMaximumSize(QtCore.QSize(480, 160))
            NiceWindow.setWindowTitle('Set Custom Priority')
            niceWidget = QtWidgets.QWidget(NiceWindow)
            niceWidget.setGeometry(QtCore.QRect(0, 0, 480, 160))
            niceLbl = QtWidgets.QLabel(niceWidget)
            niceLbl.setGeometry(QtCore.QRect(0, 5, 480, 40))
            niceLbl.setFont(QtGui.QFont('5', 10))
            niceLbl.setAlignment(QtCore.Qt.AlignLeft)
            niceLbl.setText('set niceness for process "' + self.proc.name() + '" \nwith PID: ' + str(self.proc.pid)) 

            cnice = self.proc.nice()

            nice2Lbl = QtWidgets.QLabel(niceWidget)
            nice2Lbl.setGeometry(QtCore.QRect(5, 45, 100, 30))
            nice2Lbl.setText("Nice Value:")
            niceSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal, niceWidget)
            niceSlider.setGeometry(QtCore.QRect(93, 40, 300, 45))
            niceSlider.setMinimum(-20)
            niceSlider.setMaximum(19)
            niceSlider.setValue(cnice)
            niceSlider.setStyleSheet("QSlider::groove:horizontal{background-color: rgb(147,24,25); height: 6px;\n"
"       border: 1px solid rgb(147,24,25); border-radius: 4px;}\n"
"       QSlider::handle:horizontal{background-color: transparent;\n"
"       background-image: url(" + self.icon_dir + "nicetip2.png\");\n"
"       background-position: center; background-repeat: no-repeat;\n"
"       height: 20px; width: 15px; margin: -20px 0;}")

            if (cnice>=-2) & (cnice<=2):
                status = ' Is Normal Priority'
            elif (cnice>2) & (cnice<8):
                status = ' Is Low Priority'
            elif (cnice<-2) & (cnice>-8):
                status = ' Is High Priority'
            elif (cnice>=8):
                status = ' Is Very Low Priority'
            elif (cnice<=-8):
                status = ' Is Very High Priority'
                
            nice3Lbl = QtWidgets.QLabel(niceWidget)
            nice3Lbl.setGeometry(QtCore.QRect(110, 70, 270, 30))
            nice3Lbl.setText("Current Value: " + str(cnice) + status)
            niceSlider.valueChanged.connect(partial(self.niceIndicate, slider=niceSlider, lbl=nice3Lbl))

            Cancel = QtWidgets.QPushButton(niceWidget)
            Cancel.setGeometry(QtCore.QRect(0, 120, 240, 40))
            Cancel.setText('Cancel')
            Cancel.setStyleSheet("QPushButton{background-color:rgb(209,209,211);}\n"
"           QPushButton:hover{background-color:rgb(229,229,231);}\n")
            Cancel.clicked.connect(partial(self.pclose, Window=NiceWindow))
         
            Action = QtWidgets.QPushButton(niceWidget)
            Action.setGeometry(QtCore.QRect(240, 120, 240, 40))
            Action.setText('Set Priority')
            Action.setStyleSheet("QPushButton{background-color:rgb(159,36,37);}\n"
"           QPushButton:hover{background-color:rgb(179,56,57);}\n")
            Action.clicked.connect(partial(self.niceSet, value=niceSlider, button=button, Window=NiceWindow))
                
            NiceWindow.show()

        except:
            self.procDenied()

        gc.collect()

    def procRlim(self):

        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None

        try:
        
            RlimWindow = QtWidgets.QMainWindow(self.centralwidget)
            RlimWindow.resize(320, 340)
            RlimWindow.setMinimumSize(QtCore.QSize(320, 340))
            RlimWindow.setMaximumSize(QtCore.QSize(320, 340))
            RlimWindow.setWindowTitle('Set Resource Limits')
            rlimWidget = QtWidgets.QWidget(RlimWindow)
            rlimWidget.setGeometry(QtCore.QRect(0, 0, 320, 340))
            rlimLbl = QtWidgets.QLabel(rlimWidget)

            with self.proc.oneshot():
                wproc = self.proc.name()
                wpid = self.proc.pid
                wvmslim = self.proc.rlimit(psutil.RLIMIT_AS)
                wcore = self.proc.rlimit(psutil.RLIMIT_CORE)
                wcpu = self.proc.rlimit(psutil.RLIMIT_CPU)
                wdatalim = self.proc.rlimit(psutil.RLIMIT_DATA)
                wfsize = self.proc.rlimit(psutil.RLIMIT_FSIZE)
                wlocks = self.proc.rlimit(psutil.RLIMIT_LOCKS)
                wmemlock = self.proc.rlimit(psutil.RLIMIT_MEMLOCK)
                wmsgqueue = self.proc.rlimit(psutil.RLIMIT_MSGQUEUE)
                wnicelim = self.proc.rlimit(psutil.RLIMIT_NICE)
                wnofile = self.proc.rlimit(psutil.RLIMIT_NOFILE)
                wnproc = self.proc.rlimit(psutil.RLIMIT_NPROC)
                wrsslim = self.proc.rlimit(psutil.RLIMIT_RSS)
                wrtprio = self.proc.rlimit(psutil.RLIMIT_RTPRIO)
                wrttime = self.proc.rlimit(psutil.RLIMIT_RTTIME)
                wpending = self.proc.rlimit(psutil.RLIMIT_SIGPENDING)
                wstack = self.proc.rlimit(psutil.RLIMIT_STACK)

            rlim = [wvmslim, wcore, wcpu, wdatalim, wfsize, wlocks, wmemlock, wmsgqueue, wnicelim, wnofile, wnproc, wrsslim, wrtprio, wrttime, wpending, wstack]   
            rcommand = [psutil.RLIMIT_AS, psutil.RLIMIT_CORE, psutil.RLIMIT_CPU, psutil.RLIMIT_DATA, psutil.RLIMIT_FSIZE, psutil.RLIMIT_LOCKS, psutil.RLIMIT_MEMLOCK, psutil.RLIMIT_MSGQUEUE, psutil.RLIMIT_NICE, psutil.RLIMIT_NOFILE, psutil.RLIMIT_NPROC, psutil.RLIMIT_RSS, psutil.RLIMIT_RTPRIO, psutil.RLIMIT_RTTIME, psutil.RLIMIT_SIGPENDING, psutil.RLIMIT_STACK]
            
            rlimLbl.setGeometry(QtCore.QRect(0, 5, 500, 60))
            rlimLbl.setFont(QtGui.QFont('5', 10))
            rlimLbl.setAlignment(QtCore.Qt.AlignLeft)
            rlimLbl.setText('resource limits for process \n"' + wproc + '"\nwith PID: ' + str(wpid))

            separatorLine = QtWidgets.QFrame(rlimWidget)
            separatorLine.setFrameShape(QtWidgets.QFrame.HLine)
            separatorLine.setFrameShadow(QtWidgets.QFrame.Raised)
            separatorLine.setGeometry(QtCore.QRect(0, 65, 320, 1))
            separatorLine.setStyleSheet("QFrame{background: rgb(124,98,78);}")

            nameLbl = QtWidgets.QLabel(rlimWidget)
            nameLbl.setGeometry(QtCore.QRect(5, 75, 110, 30))
            nameLbl.setText("Resources:")

            nameMenu = QtWidgets.QComboBox(rlimWidget)
            nameMenu.setGeometry(QtCore.QRect(5, 100, 220, 30))
            nameMenu.setStyleSheet("QComboBox{background:rgb(144,118,98);} QComboBox::item{background:rgb(209,209,211);}\n"
"           QComboBox::item:selected{background:rgb(159,36,37);}")
            nameMenu.addItems(['Max Virtual Memory', 'Max Core File Size', 'CPU Time Limit', 'Max Data Segment Size', 'Max Create File Size', 'Combined Locks', 'Max Locked Ram Memory', 'POSIX Message Queues', 'Nice', 'Max FDs', 'Max Threads', 'Max Resident Memory', 'Priority Ceiling', 'CPU Scheduled Time', 'Pending Signals', 'Max Stack Size'])
            nameMenu.setCurrentIndex(0)
            
            curLbl = QtWidgets.QLabel(rlimWidget)
            curLbl.setGeometry(QtCore.QRect(8, 150, 110, 30))
            curLbl.setText("Current Limits:")
            currentLbl = QtWidgets.QLabel(rlimWidget)
            currentLbl.setGeometry(QtCore.QRect(120, 150, 200, 30))
            currentLbl.setText(str(wvmslim))
            
            nameMenu.currentIndexChanged.connect(partial(self.rlimCurrent, lbl=currentLbl, limits=rlim))

            onlyInt = QtGui.QIntValidator()
            softLbl = QtWidgets.QLabel(rlimWidget)
            softLbl.setGeometry(QtCore.QRect(5, 200, 110, 30))
            softLbl.setAlignment(QtCore.Qt.AlignCenter)
            softLbl.setText("New Soft Limit:")
            softEdit = QtWidgets.QLineEdit(rlimWidget)
            softEdit.setGeometry(QtCore.QRect(120, 200, 150, 30))
            softEdit.setValidator(onlyInt)
            softEdit.setStyleSheet("QLineEdit {color: rgb(0,0,0); background: rgb(124,98,78); selection-background-color: rgb(159,36,37); }\n"
"       QLineEdit:hover{background: rgb(159,36,37);}")

            hardLbl = QtWidgets.QLabel(rlimWidget)
            hardLbl.setGeometry(QtCore.QRect(5, 250, 110, 30))
            hardLbl.setAlignment(QtCore.Qt.AlignCenter)
            hardLbl.setText("New Hard Limit:")
            hardEdit = QtWidgets.QLineEdit(rlimWidget)
            hardEdit.setGeometry(QtCore.QRect(120, 250, 150, 30))
            hardEdit.setValidator(onlyInt)
            hardEdit.setStyleSheet("QLineEdit {color: rgb(0,0,0); background: rgb(124,98,78); selection-background-color: rgb(159,36,37); }\n"
"       QLineEdit:hover{background: rgb(159,36,37);}")

            Cancel = QtWidgets.QPushButton(rlimWidget)
            Cancel.setGeometry(QtCore.QRect(0, 300, 160, 40))
            Cancel.setText('Cancel')
            Cancel.setStyleSheet("QPushButton{background-color:rgb(209,209,211);}\n"
"           QPushButton:hover{background-color:rgb(229,229,231);}\n")
            Cancel.clicked.connect(partial(self.pclose, Window=RlimWindow))
         
            Action = QtWidgets.QPushButton(rlimWidget)
            Action.setGeometry(QtCore.QRect(160, 300, 160, 40))
            Action.setText('Set New Limits')
            Action.setStyleSheet("QPushButton{background-color:rgb(159,36,37);}\n"
"           QPushButton:hover{background-color:rgb(179,56,57);}\n")
            Action.clicked.connect(partial(self.rlimSet, index=nameMenu, command=rcommand, soft=softEdit, hard=hardEdit, lbl=currentLbl))

            RlimWindow.show()

        except:
            self.procDenied()

        gc.collect()

    def procSchedule(self):

        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None

        try:
        
            SchedWindow = QtWidgets.QMainWindow(self.centralwidget)
            SchedWindow.resize(320, 340)
            SchedWindow.setMinimumSize(QtCore.QSize(320, 340))
            SchedWindow.setMaximumSize(QtCore.QSize(320, 340))
            SchedWindow.setWindowTitle('Set Scheduler')
            schedWidget = QtWidgets.QWidget(SchedWindow)
            schedWidget.setGeometry(QtCore.QRect(0, 0, 320, 340))
            
            wpid = self.proc.pid
            wproc = self.proc.name()
            policy = sched_getscheduler(wpid)
            param = str(sched_getparam(wpid))
            param = param.replace(')', '').split('=')[1]

            if policy==SCHED_OTHER:
                policy = 'Default'
                minp = sched_get_priority_min(SCHED_OTHER)
                maxp = sched_get_priority_max(SCHED_OTHER)
                
            elif policy==SCHED_BATCH:
                policy = 'CPU-intensive'
                minp = sched_get_priority_min(SCHED_BATCH)
                maxp = sched_get_priority_max(SCHED_BATCH)

            elif policy==SCHED_IDLE:
                policy = 'Low Priority'
                minp = sched_get_priority_min(SCHED_IDLE)
                maxp = sched_get_priority_max(SCHED_IDLE)

            elif policy==SCHED_FIFO:
                policy = 'Fist-In-First-Out'
                minp = sched_get_priority_min(SCHED_FIFO)
                maxp = sched_get_priority_max(SCHED_FIFO)

            elif policy==SCHED_RR:
                policy = 'Round-robin'
                minp = sched_get_priority_min(SCHED_RR)
                maxp = sched_get_priority_max(SCHED_RR)
            
            schedLbl = QtWidgets.QLabel(schedWidget)
            schedLbl.setGeometry(QtCore.QRect(0, 5, 500, 60))
            schedLbl.setFont(QtGui.QFont('5', 10))
            schedLbl.setAlignment(QtCore.Qt.AlignLeft)
            schedLbl.setText('scheduler for process \n"' + wproc + '"\nwith PID: ' + str(wpid))

            separatorLine = QtWidgets.QFrame(schedWidget)
            separatorLine.setFrameShape(QtWidgets.QFrame.HLine)
            separatorLine.setFrameShadow(QtWidgets.QFrame.Raised)
            separatorLine.setGeometry(QtCore.QRect(0, 65, 320, 1))
            separatorLine.setStyleSheet("QFrame{background: rgb(124,98,78);}")

            nameLbl = QtWidgets.QLabel(schedWidget)
            nameLbl.setGeometry(QtCore.QRect(5, 75, 110, 30))
            nameLbl.setText("Policies:")

            nameMenu = QtWidgets.QComboBox(schedWidget)
            nameMenu.setGeometry(QtCore.QRect(5, 100, 220, 30))
            nameMenu.setStyleSheet("QComboBox{background:rgb(144,118,98);} QComboBox::item{background:rgb(209,209,211);}\n"
"           QComboBox::item:selected{background:rgb(159,36,37);}")
            nameMenu.addItems(['Default', 'CPU-intensive', 'Low Priority', 'First-In-First-Out', 'Round-Robin'])

            currentLbl = QtWidgets.QLabel(schedWidget)
            currentLbl.setGeometry(QtCore.QRect(5, 125, 300, 90))
            currentLbl.setText('Current Policy: '+ policy + '\nCurrent Priority: ' + param)

            limLbl = QtWidgets.QLabel(schedWidget)
            limLbl.setGeometry(QtCore.QRect(5, 220, 300, 90))
            limLbl.setText('Allowed Minimum Priority: ' + str(minp) + '\nAllowed Maximum Priority: ' + str(maxp))

            sLbl = QtWidgets.QLabel(schedWidget)
            sLbl.setGeometry(QtCore.QRect(5, 200, 140, 30))
            sLbl.setAlignment(QtCore.Qt.AlignCenter)
            sLbl.setText("New Schedule Value")

            schedEdit = QtWidgets.QSpinBox(schedWidget)
            schedEdit.setGeometry(QtCore.QRect(150, 200, 150, 30))
            schedEdit.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            schedEdit.setRange(minp,maxp)
            schedEdit.setValue(int(param))
            schedEdit.setStyleSheet("QSpinBox{border: 1px solid rgb(0,0,0);\n"
"            color: rgb(0,0,0); background: rgb(124,98,78); selection-background-color: rgb(159,36,37); }")

            nameMenu.currentIndexChanged.connect(partial(self.schedCurrent, lbl=limLbl, editor=schedEdit))

            Cancel = QtWidgets.QPushButton(schedWidget)
            Cancel.setGeometry(QtCore.QRect(0, 300, 160, 40))
            Cancel.setText('Cancel')
            Cancel.setStyleSheet("QPushButton{background-color:rgb(209,209,211);}\n"
"           QPushButton:hover{background-color:rgb(229,229,231);}\n")
            Cancel.clicked.connect(partial(self.pclose, Window=SchedWindow))
         
            Action = QtWidgets.QPushButton(schedWidget)
            Action.setGeometry(QtCore.QRect(160, 300, 160, 40))
            Action.setText('Set New Schedule')
            Action.setStyleSheet("QPushButton{background-color:rgb(159,36,37);}\n"
"           QPushButton:hover{background-color:rgb(179,56,57);}\n")
            Action.clicked.connect(partial(self.schedSet, index=nameMenu, lbl1=currentLbl, lbl2=limLbl, editor=schedEdit))

            SchedWindow.show()

        except:
            self.procDenied()

        gc.collect()
            
    def procSockets(self):

        running = self.proc.is_running()
        if not running:
            self.procExists()
            return None

        try:
            wproc = self.proc.name()

            SocketWindow, socketWidget, socketLbl, socketTable = self.popWindow(1, False, True)
        
            SocketWindow.setWindowTitle('Process Socket Connections')
            socketLbl = QtWidgets.QLabel(socketWidget)

            con = self.proc.connections()

            socketLbl.setGeometry(QtCore.QRect(0, 5, 500, 23))
            socketLbl.setFont(QtGui.QFont('5', 10))
            socketLbl.setAlignment(QtCore.Qt.AlignLeft)
            socketLbl.setText('open socket connections for process "' + wproc + '" with PID: ' + str(self.proc.pid))                
            socketTable.setGeometry(QtCore.QRect(0, 23, 500, 277))
            socketTable.setColumnCount(8)
            socketTable.setRowCount(len(con))
            socketTable.setColumnWidth(0, 50)
            socketTable.setColumnWidth(1, 200)
            socketTable.setColumnWidth(2, 220)
            socketTable.setColumnWidth(3, 150)
            socketTable.setColumnWidth(5, 150)
            socketTable.setHorizontalHeaderLabels(['FD', 'Family', 'Type', 'Local IP', 'Local Port', 'Remote IP', 'Remote Port', 'Status'])

            fd = []
            family = []
            typer = []
            lip = []
            lport = []
            rip = []
            rport = []
            status = []
            for i in range(len(con)):
                fd.append(con[i].fd)
                family.append(con[i].family)
                typer.append(con[i].type)
                lip.append(con[i].laddr.ip)
                lport.append(con[i].laddr.port)
                try:
                    rip.append(con[i].raddr.ip)
                    rport.append(con[i].raddr.port)
                except:
                    rip.append('')
                    rport.append('')
                status.append(con[i].status)

            collection = [fd, family, typer, lip, lport, rip, rport, status]

            for i in range(8): 
                for j in range(len(con)):
                    item_socket = QtWidgets.QTableWidgetItem()
                    item_socket.setFlags(QtCore.Qt.NoItemFlags)
                    socketTable.setItem(j, i, item_socket)
                    try:
                        item_socket.setText(str(collection[i][j]))
                    except IndexError: 
                        item_socket.setText('')
                    del item_socket

            SocketWindow.show()
                
        except:
            self.procDenied()

        gc.collect()

    def cpuStats(self):

        try:
            CstatWindow, cstatWidget, cstatLbl, cstatTable = self.popWindow(1, False, True)
            
            CstatWindow.setWindowTitle('CPU Properties')

            cputimes = psutil.cpu_times(percpu=False)
            cpucount1 = psutil.cpu_count()
            cpucount2 = psutil.cpu_count(logical=True)
            cpustats = psutil.cpu_stats()
            cpufreq = psutil.cpu_freq(percpu=False)
            cpuload = psutil.getloadavg()

            cstatTable.setGeometry(QtCore.QRect(0, 0, 500, 300))
            cstatTable.setColumnCount(2)
            cstatTable.setRowCount(27)
            cstatTable.setColumnWidth(0, 250)
            cstatTable.setColumnWidth(1, 250) 
            chheader = cstatTable.horizontalHeader()
            chheader.setVisible(False)

            properties = ['Logical Cores', 'Physical Cores', 'User', 'System', 'Idle', 'Nice', 'IOwait', 'Service Hardware Interrupts', 'Service Software Interrupts', 'Steal {Alternate OS Env}', 'Guest', 'Guest Nice', 'Context Switches', 'Interrupts', 'Software Interrupts', 'System Calls', 'Current', 'Minimum', 'Maximum', '1 Minute', '5 Minutes', '15 Minutes']
            vals = [cpucount1, cpucount2, self.Timestring([cputimes.user])[0], self.Timestring([cputimes.system])[0], self.Timestring([cputimes.idle])[0], self.Timestring([cputimes.nice])[0], self.Timestring([cputimes.iowait])[0], self.Timestring([cputimes.irq])[0], self.Timestring([cputimes.softirq])[0], self.Timestring([cputimes.steal])[0], self.Timestring([cputimes.guest])[0], self.Timestring([cputimes.guest_nice])[0], cpustats.ctx_switches, cpustats.interrupts, cpustats.soft_interrupts, cpustats.syscalls, str(round(cpufreq.current,1))+' MHz', str(round(cpufreq.min,1))+' MHz', str(round(cpufreq.max,1))+' MHz', cpuload[0], cpuload[1], cpuload[2]]
            
            collection = [properties, vals]

            slices = ['CPU Count', 'CPU Times', 'CPU Statistics', 'CPU Frequencies', 'CPU Load']
            sliceFont = QtGui.QFont('5', 10.5)
            sliceFont.setBold(True)
            sliceFont.setUnderline(True)
            count = 0

            for i in range(2):
                count1 = 0
                for j in range(27):
                    item_cstat = QtWidgets.QTableWidgetItem()
                    item_cstat.setFlags(QtCore.Qt.NoItemFlags)
                    cstatTable.setItem(j, i, item_cstat)
                    if (j==0) or (j==3) or (j==14) or (j==19) or (j==23):
                        item_cstat.setBackground(QtGui.QColor(209,209,211))
                        cstatTable.setRowHeight(j,1)
                        if i==0:
                            item_cstat.setFont(sliceFont)
                            item_cstat.setText(slices[count])
                            count += 1
                        count1 += 1
                    else:
                        try:
                            item_cstat.setText(str(collection[i][j-count1]))
                        except IndexError: 
                            item_cstat.setText('')
                    del item_cstat
            
            CstatWindow.show()
                
        except:
            pass

        gc.collect()

    def memStats(self):

        try:

            MstatWindow, mstatWidget, mstatLbl, mstatTable = self.popWindow(1, False, True)            
            MstatWindow.setWindowTitle('Memory Properties')

            vmem = psutil.virtual_memory()
            smem = psutil.swap_memory()

            vmemory = []
            smemory = []

            for i in range(len(vmem)):
                if i!=2:
                    vmemory.append(self.Memstring([vmem[i]])[0])
                else:
                    vmemory.append(str(vmem[i])+'%')
            for i in range(len(smem)):
                if i!=3:
                    smemory.append(self.Memstring([smem[i]])[0])
                else:
                    smemory.append(str(smem[i])+'%')

            mstatTable.setGeometry(QtCore.QRect(0, 0, 500, 300))
            mstatTable.setColumnCount(2)
            mstatTable.setRowCount(19)
            mstatTable.setColumnWidth(0, 250)
            mstatTable.setColumnWidth(1, 250) 
            mhheader = mstatTable.horizontalHeader()
            mhheader.setVisible(False)

            properties = ['Total', 'Available', 'Percent', 'Used', 'Free', 'Active', 'Inactive', 'Buffers', 'Cached', 'Shared', 'Slab', 'Total', 'Used', 'Free', 'Percent', 'Swapped In', 'Swapped Out']
            vals = vmemory + smemory

            collection = [properties, vals]

            slices = ['Virtual Memory', 'Swap Memory']
            sliceFont = QtGui.QFont('5', 10.5)
            sliceFont.setBold(True)
            sliceFont.setUnderline(True)
            count = 0

            for i in range(2):
                count1 = 0
                for j in range(19):
                    item_mstat = QtWidgets.QTableWidgetItem()
                    item_mstat.setFlags(QtCore.Qt.NoItemFlags)
                    mstatTable.setItem(j, i, item_mstat)
                    if (j==0) or (j==12):
                        item_mstat.setBackground(QtGui.QColor(209,209,211))
                        mstatTable.setRowHeight(j,1)
                        if i==0:
                            item_mstat.setFont(sliceFont)
                            item_mstat.setText(slices[count])
                            count += 1
                        count1 += 1
                    else:
                        try:
                            item_mstat.setText(str(collection[i][j-count1]))
                        except IndexError: 
                            item_mstat.setText('')
                    del item_mstat
            
            MstatWindow.show()
                
        except:
            pass
            
        gc.collect()

    def netConnect(self):
        
        try:

            SocketWindow, socketWidget, socketLbl, socketTable = self.popWindow(1, False, True)
            SocketWindow.setWindowTitle('Socket Connections')

            con = psutil.net_connections()
        
            socketTable.setGeometry(QtCore.QRect(0, 0, 500, 300))
            socketTable.setColumnCount(9)
            socketTable.setRowCount(len(con))
            socketTable.setColumnWidth(0, 80)
            socketTable.setColumnWidth(1, 50)
            socketTable.setColumnWidth(2, 200)
            socketTable.setColumnWidth(3, 220)
            socketTable.setColumnWidth(4, 150)
            socketTable.setColumnWidth(6, 150)
            socketTable.setHorizontalHeaderLabels(['PID', 'FD', 'Family', 'Type', 'Local IP', 'Local Port', 'Remote IP', 'Remote Port', 'Status'])

            pid = []
            fd = []
            family = []
            typer = []
            lip = []
            lport = []
            rip = []
            rport = []
            status = []
            for i in range(len(con)):
                pid.append(con[i].pid)
                fd.append(con[i].fd)
                family.append(con[i].family)
                typer.append(con[i].type)
                lip.append(con[i].laddr.ip)
                lport.append(con[i].laddr.port)
                try:
                    rip.append(con[i].raddr.ip)
                    rport.append(con[i].raddr.port)
                except:
                    rip.append('')
                    rport.append('')
                status.append(con[i].status)

            collection = [pid, fd, family, typer, lip, lport, rip, rport, status]

            for i in range(9): 
                for j in range(len(con)):
                    item_socket = QtWidgets.QTableWidgetItem()
                    item_socket.setFlags(QtCore.Qt.NoItemFlags)
                    socketTable.setItem(j, i, item_socket)
                    try:
                        item_socket.setText(str(collection[i][j]))
                    except IndexError: 
                        item_socket.setText('')
                    del item_socket

            SocketWindow.show()
                
        except:
            pass

        gc.collect()

    def netStat(self):
        
        try:

            NetioWindow, netioWidget, netioLbl, netioTable = self.popWindow(1, False, True)
            NetioWindow.setWindowTitle('Network Interface Card/s Stats &  IO Counters')

            netio = psutil.net_io_counters(pernic=True, nowrap=True)
            stats = psutil.net_if_stats()
            nic = list(netio.keys())
            netio = list(netio.values())
            stats = list(stats.values())
        
            netioTable.setGeometry(QtCore.QRect(0, 0, 500, 300))
            netioTable.setColumnCount(13)
            netioTable.setRowCount(len(netio))
            netioTable.setColumnWidth(0, 160)
            netioTable.setColumnWidth(2, 270)
            netioTable.setColumnWidth(4, 170)
            netioTable.setColumnWidth(6, 120)
            netioTable.setColumnWidth(7, 100)
            netioTable.setColumnWidth(8, 140)
            netioTable.setColumnWidth(9, 140)
            netioTable.setColumnWidth(10, 140)
            netioTable.setColumnWidth(11, 230)
            netioTable.setColumnWidth(12, 230)
            netioTable.setHorizontalHeaderLabels(['Network Interface', 'Connected', 'Duplex Type', 'Speed', 'Max Transmission Unit', 'Bytes Sent', 'Bytes Recived', 'Packets Sent', 'Packets Recieved', 'Recieving Errors', 'Sending Errors', 'Dropped Incomming Packets', 'Dropped Outgoing Packets'])

            con = []
            duplex = []
            speed = []
            trans = []
            bsend = []
            brec = []
            psend = []
            prec = []
            erec = []
            esend = []
            drec = []
            dsend = []
            for i in range(len(netio)):
                con.append(stats[i].isup)
                duplex.append(stats[i].duplex)
                speed.append(str(stats[i].speed)+' MB')
                trans.append(self.Memstring([stats[i].mtu])[0])
                bsend.append(self.Memstring([netio[i].bytes_sent])[0])
                brec.append(self.Memstring([netio[i].bytes_recv])[0])
                psend.append(netio[i].packets_sent)
                prec.append(netio[i].packets_recv)
                erec.append(netio[i].errin)
                esend.append(netio[i].errout)
                drec.append(netio[i].dropin)
                dsend.append(netio[i].dropout)
                
            collection = [nic, con, duplex, speed, trans, bsend, brec, psend, prec, erec, esend, drec, dsend]

            for i in range(13): 
                for j in range(len(netio)):
                    item_netio = QtWidgets.QTableWidgetItem()
                    item_netio.setFlags(QtCore.Qt.NoItemFlags)
                    netioTable.setItem(j, i, item_netio)
                    try:
                        item_netio.setText(str(collection[i][j]))
                    except IndexError: 
                        item_netio.setText('')
                    del item_netio

            NetioWindow.show()
                
        except:
            pass

        gc.collect()

    def netAddress(self):
        
        try:

            AddrWindow, addrWidget, addrLbl, addrTable = self.popWindow(1, False, True)
            AddrWindow.setWindowTitle('Network Interface Card/s Associated Addresses')

            addr = psutil.net_if_addrs()
            nic = list(addr.keys())
            adrs = list(addr.values())

            fadrs = [] 
            fnic = []
            fam = []
            prim = []
            mask = []
            broad = []
            ptp = []
            for sublist in adrs:
                for item in sublist:
                    fadrs.append(item)
                    fam.append(item.family)
                    prim.append(item.address)
                    mask.append(item.netmask)
                    broad.append(item.broadcast)
                    ptp.append(item.ptp)

            count1 = 0
            count2 = 0
            
            for i in range(len(fadrs)):
                if (i==0):
                    fnic.append(nic[count1])
                elif (i==len(adrs[count1])+count2):
                    count2 += len(adrs[count1])
                    count1 += 1
                    fnic.append(nic[count1])
                else:
                    fnic.append('')
        
            addrTable.setGeometry(QtCore.QRect(0, 0, 500, 300))
            addrTable.setColumnCount(6)
            addrTable.setRowCount(len(fadrs))
            addrTable.setColumnWidth(0, 150)
            addrTable.setColumnWidth(1, 210)
            addrTable.setColumnWidth(2, 210)
            addrTable.setColumnWidth(3, 140)
            addrTable.setColumnWidth(4, 140)
            addrTable.setColumnWidth(5, 140)
            addrTable.setHorizontalHeaderLabels(['Network Interface', 'Family', 'Primary', 'Netmask', 'Broadcast', 'Point-to-Point'])
                
            collection = [fnic, fam, prim, mask, broad, ptp]

            for i in range(6): 
                for j in range(len(fadrs)):
                    item_addr = QtWidgets.QTableWidgetItem()
                    item_addr.setFlags(QtCore.Qt.NoItemFlags)
                    addrTable.setItem(j, i, item_addr)
                    try:
                        item_addr.setText(str(collection[i][j]))
                    except IndexError: 
                        item_addr.setText('')
                    del item_addr

            AddrWindow.show()
                
        except:
            pass

        gc.collect()

    def diskProp(self, wname, wdir, opts):

        try:

            IoWindow, ioWidget, ioLbl, ioTable = self.popWindow(1, False, True)
            IoWindow.setWindowTitle('Disk Properties')
            ioLbl = QtWidgets.QLabel(ioWidget)

            wname = wname.split('/')[-1]
            info = statvfs(wdir)
            namemax = self.Memstring([info.f_namemax])[0]
            pathmax = pathconf(wdir, 'PC_PATH_MAX')
            pathmax = self.Memstring([pathmax])[0]
            
            io = psutil.disk_io_counters(perdisk=True, nowrap=True)
            io_count = io.get(wname)

            ds = 0
            fs = 0

            if not self.disklimit:

                for (root,dirs,files) in walk(wdir, topdown=True): 

                    ds += len(dirs)
                    fs += len(files)
                    
            else:
                ds = 'N/A'
                fs = 'N/A'

            ioLbl.setGeometry(QtCore.QRect(0, 5, 500, 23))
            ioLbl.setFont(QtGui.QFont('5', 10))
            ioLbl.setAlignment(QtCore.Qt.AlignLeft)
            ioLbl.setText('Properties for device "' + wname + '" located in dir ' + wdir)                
            ioTable.setGeometry(QtCore.QRect(0, 23, 500, 277))
            ioTable.setColumnCount(2)
            ioTable.setRowCount(23)
            ioTable.setColumnWidth(0, 230)
            ioTable.setColumnWidth(1, 270)
            ihheader = ioTable.horizontalHeader()
            ihheader.setVisible(False)

            rbytes = self.Memstring([io_count.read_bytes])[0]
            wbytes = self.Memstring([io_count.write_bytes])[0]
            f_bsize = self.Memstring([info.f_bsize])[0]
            f_frsize = self.Memstring([info.f_frsize])[0]
            rtime = self.Timestring([float(io_count.read_time)/1000])[0]
            wtime = self.Timestring([float(io_count.write_time)/1000])[0]
            btime = self.Timestring([float(io_count.busy_time)/1000])[0]

            properties = ['Directories', 'Files', 'Preferred Block Size', 'Fundamental Block Size', 'Block Count', 'Free Blocks', 'Available Blocks', 'Total File Nodes', 'Free File Nodes', 'Available File Nodes', 'Flags', 'Max Filename Length', 'Max Directory Length', 'Mount Options', 'IO Read Count', 'IO Write Count', 'IO Read Merged Count', 'IO Write Merged Count', 'IO Read Bytes', 'IO Write Bytes', 'IO Read Time', 'IO Write Time', 'IO Busy Time']
            vals = [ds, fs, f_bsize, f_frsize, info.f_blocks, info.f_bfree, info.f_bavail, info.f_files, info.f_ffree, info.f_favail, info.f_flag, namemax, pathmax, opts, io_count.read_count, io_count.write_count, io_count.read_merged_count, io_count.write_merged_count, rbytes, wbytes, rtime, wtime, btime]

            collection = [properties, vals]

            for i in range(2): 
                for j in range(23):
                    item_io = QtWidgets.QTableWidgetItem()
                    item_io.setFlags(QtCore.Qt.NoItemFlags)
                    ioTable.setItem(j, i, item_io)
                    try:
                        item_io.setText(str(collection[i][j]))
                    except IndexError: 
                        item_io.setText('')
                    del item_io
            
            IoWindow.show()
                
        except:
            pass

        gc.collect()

    def diskConf(self, wname, wdir):
        
        try:
        
            ConfWindow = QtWidgets.QMainWindow(self.centralwidget)
            ConfWindow.resize(500, 300)
            ConfWindow.setMinimumSize(QtCore.QSize(500, 300))
            ConfWindow.setMaximumSize(QtCore.QSize(500, 300))
            ConfWindow.setWindowTitle('Disk Configuration Information')
            confWidget = QtWidgets.QWidget(ConfWindow)
            confWidget.setGeometry(QtCore.QRect(0, 0, 500, 300))
            confLbl = QtWidgets.QLabel(confWidget)

            wname = wname.split('/')[-1]

            command = 'getconf -a ' + wdir 
            conf = popen(command).read()
            conf = conf.split('\n')
            conftup = []

            for item in conf: 
                item = ' '.join(item.split())
                tup = tuple(item.split(' '))
                if len(tup)==2:
                    conftup.append(tup)

            cdic = dict(conftup)
        
            properties = ['Max File Links', 'Max Canonical Input Queue', 'Available Input Queue', 'Max Filename Size', 'Max Pathname Size', 'Max Write to Pipe', 'Restrictions to File Ownership', 'Max Filename Handler', 'Disable Special Character', 'Max Argument Length', 'Max Child Processes', 'Clock Intervals/s', 'Max Group IDs', 'Max Open Files Allowed', 'Max Open Streams Allowed', 'Max Time Zone Size', 'POSIX Job Control Support', 'POSIX Version', 'Max Ibase & Obase Values', 'Max Permitted Elements', 'Max Allowed Scale Size', 'Max String Characters', 'Max Weights Assignable to Entry', 'Max Expressions Nested in Parentheses', 'Max Characters Per Input Line', 'Standard EXE Path', 'Max Repeated Expressions Within {\}', 'C Bindings Option', 'C Dev Utilities Option', 'Fortran Dev Utilities Option', 'Fortran Runtime Utilities Option', 'Creation of Locales', 'Software Dev Utilities Option', 'User Portability Utilities Option', 'Terminal Support for UPUO', 'POSIX.2 Version', 'PTC MKS Toolkit EXE Dir', 'Configuration Dir', 'Development Utilities Dir', 'Default man Search Dir', 'Localization Dir', 'Infinite Data Source/Sink File', 'Default Shell', 'System Spool Dir', 'Temporary Files Dir', 'Terminal Access Control File']
            vals = [cdic.get("LINK_MAX", ""), cdic.get("MAX_CANON", ""), cdic.get("MAX_INPUT", ""), cdic.get("NAME_MAX", ""), cdic.get("PATH_MAX", ""), cdic.get("PIPE_BUF", ""), str(bool(int(cdic.get("_POSIX_CHOWN_RESTRICTED", "")))), str(bool(int(cdic.get("_POSIX_NO_TRUNC", "")))), str(bool(int(cdic.get("_POSIX_VDISABLE", "")))), cdic.get("ARG_MAX", ""), cdic.get("CHILD_MAX", ""), cdic.get("CLK_TCK", ""), cdic.get("NGROUPS_MAX", ""), cdic.get("OPEN_MAX", ""), cdic.get("STREAM_MAX", ""), cdic.get("TZNAME_MAX", ""), str(bool(int(cdic.get("_POSIX_JOB_CONTROL", "")))), cdic.get("_POSIX_VERSION", ""), cdic.get("BC_BASE_MAX", ""), cdic.get("BC_DIM_MAX", ""), cdic.get("BC_SCALE_MAX", ""), cdic.get("BC_STRING_MAX", ""), cdic.get("COLL_WEIGHTS_MAX", ""), cdic.get("EXPR_NEST_MAX", ""), cdic.get("LINE_MAX", ""), cdic.get("PATH", ""), cdic.get("RE_DUP_MAX", ""), cdic.get("POSIX2_C_BIND", ""),  cdic.get("POSIX2_C_DEV", ""),  cdic.get("POSIX2_FORT_DEV", ""),  cdic.get("POSIX2_FORT_RUN", ""), cdic.get("POSIX2_LOCALEDEF", ""), cdic.get("POSIX2_SW_DEV", ""), cdic.get("POSIX2_CHAR_TERM", ""), cdic.get("UPE", ""), cdic.get("POSIX2_VERSION", ""), cdic.get("_CS_BINDIR", ""), cdic.get("_CS_ETCDIR", ""), cdic.get("_CS_LIBDIR", ""), cdic.get("_CS_MANPATH", ""), cdic.get("_CS_NLSDIR", ""), cdic.get("_CS_NULLDEV", ""), cdic.get("_CS_SHELL", ""), cdic.get("_CS_SPOOLDIR", ""), cdic.get("_CS_TMPDIR", ""), cdic.get("_CS_TTYDEV", "")]

            rmlist = []
            for i in range(len(vals)):
                if vals[i]=='':
                    rmlist.append(i)

            properties = [i for n, i in enumerate(properties) if n not in rmlist]
            vals = [i for n, i in enumerate(vals) if n not in rmlist]
                    
                
            confLbl.setGeometry(QtCore.QRect(0, 5, 500, 23))
            confLbl.setFont(QtGui.QFont('5', 10))
            confLbl.setAlignment(QtCore.Qt.AlignLeft)
            confLbl.setText('Configurations for device "' + wname + '" located in dir ' + wdir)                
            confTable = QtWidgets.QTableWidget(confWidget)
            confTable.setGeometry(QtCore.QRect(0, 23, 500, 277))
            confTable.setColumnCount(2)
            confTable.setRowCount(len(properties))
            confTable.setColumnWidth(0, 300) 
            confTable.setShowGrid(False)
            chheader = confTable.horizontalHeader()
            chheader.setVisible(False)
            cvheader = confTable.verticalHeader()
            cvheader.setVisible(False)
            confTable.setStyleSheet("QTableWidget{color:rgb(0,0,0)}")

            collection = [properties, vals]

            for i in range(2): 
                for j in range(len(properties)):
                    item_conf = QtWidgets.QTableWidgetItem()
                    item_conf.setFlags(QtCore.Qt.NoItemFlags)
                    confTable.setItem(j, i, item_conf)
                    try:
                        item_conf.setText(str(collection[i][j]))
                    except IndexError: 
                        item_conf.setText('')
                    del item_conf
            
            ConfWindow.show()
                
        except:
            pass

        gc.collect()

    def Preferences(self):
    
        PrefWindow = QtWidgets.QMainWindow(self.centralwidget)
        PrefWindow.resize(500, 520)
        PrefWindow.setMinimumSize(QtCore.QSize(500, 520))
        PrefWindow.setMaximumSize(QtCore.QSize(500, 520))
        PrefWindow.setWindowTitle('Preferences')
        prefWidget = QtWidgets.QWidget(PrefWindow)
        prefWidget.setGeometry(QtCore.QRect(0, 0, 500, 520))
        separator1Line = QtWidgets.QFrame(prefWidget)
        separator1Line.setFrameShape(QtWidgets.QFrame.HLine)
        separator1Line.setFrameShadow(QtWidgets.QFrame.Raised)
        separator1Line.setGeometry(QtCore.QRect(0, 160, 500, 1))
        separator1Line.setStyleSheet("QFrame{background: rgb(124,98,78);}")
        separator2Line = QtWidgets.QFrame(prefWidget)
        separator2Line.setFrameShape(QtWidgets.QFrame.HLine)
        separator2Line.setFrameShadow(QtWidgets.QFrame.Raised)
        separator2Line.setGeometry(QtCore.QRect(0, 350, 500, 1))
        separator2Line.setStyleSheet("QFrame{background: rgb(124,98,78);}")
        separator3Line = QtWidgets.QFrame(prefWidget)
        separator3Line.setFrameShape(QtWidgets.QFrame.VLine)
        separator3Line.setFrameShadow(QtWidgets.QFrame.Raised)
        separator3Line.setGeometry(QtCore.QRect(249, 0, 1, 161))
        separator3Line.setStyleSheet("QFrame{background: rgb(124,98,78);}")

        headerFont = QtGui.QFont('5', 12)
        headerFont.setBold(True)
        headerFont.setUnderline(True)
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Highlight, QtCore.Qt.transparent)
        palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)

        procLbl = QtWidgets.QLabel(prefWidget)
        procLbl.setGeometry(QtCore.QRect(5, 0, 100, 30))
        procLbl.setFont(headerFont)
        procLbl.setText("Processes")

        procLbl = QtWidgets.QLabel(prefWidget)
        procLbl.setGeometry(QtCore.QRect(5, 35, 100, 30))
        procLbl.setText("Refresh Rate:")
        procRefresh = QtWidgets.QDoubleSpinBox(prefWidget)
        procRefresh.setGeometry(QtCore.QRect(108,39,110,24))
        procRefresh.setRange(0.5,10)
        procRefresh.setSingleStep(0.5)
        procRefresh.setLocale(QtCore.QLocale("C"))
        procRefresh.setDecimals(1)
        procRefresh.setValue(self.ptime)
        procRefresh.setSuffix("s")
        procRefresh.setPalette(palette)
        procRefresh.setFocusPolicy(QtCore.Qt.NoFocus)

        procRefresh.setStyleSheet("QDoubleSpinBox{padding-right: 0px; padding-left: 4px;\n"
"       border: 1px solid rgb(0,0,0); border-radius: 12px; background-color: rgb(209,209,211);}\n"
"       QDoubleSpinBox::up-button{min-width: 22px; min-height: 22px;\n"
"       border-bottom-right-radius: 11px; border-top-right-radius: 11px;\n"
"       background-color: rgb(159,36,37); subcontrol-position: center right;\n"
"       background-image: url(" + self.icon_dir + "plus4.png\");\n"
"       background-position: center; background-repeat: no-repeat;}\n"
"       QDoubleSpinBox::down-button{min-width: 22px; min-height: 22px;\n"
"       border-top-left-radius: 11px; border-bottom-left-radius: 11px;\n"
"       subcontrol-position: center left; background-color: rgb(159,36,37);\n"
"       background-image: url(" + self.icon_dir + "minus1.png\");\n"
"       background-position: center; background-repeat: no-repeat;}")
        
        procRefresh.valueChanged.connect(partial(self.procref, box=procRefresh))

        memLbl = QtWidgets.QLabel(prefWidget)
        memLbl.setGeometry(QtCore.QRect(5, 75, 100, 30))
        memLbl.setText("Memory View:")
        procMem = QtWidgets.QSlider(QtCore.Qt.Horizontal, prefWidget)
        procMem.setGeometry(QtCore.QRect(108, 80, 110, 25))
        procMem.setMinimum(0)
        procMem.setMaximum(1)
        procMem.setValue(self.memvis)
        self.memswitch(procMem)
        procMem.valueChanged.connect(partial(self.memswitch, slider=procMem))

        trackLbl = QtWidgets.QLabel(prefWidget)
        trackLbl.setGeometry(QtCore.QRect(5, 115, 100, 30))
        trackLbl.setText("Process Track:")
        procTrack = QtWidgets.QSlider(QtCore.Qt.Horizontal, prefWidget)
        procTrack.setGeometry(QtCore.QRect(108, 120, 110, 25))
        procTrack.setMinimum(0)
        procTrack.setMaximum(1)
        procTrack.setValue(self.ptrack)
        self.trackswitch(procTrack) 
        procTrack.valueChanged.connect(partial(self.trackswitch, slider=procTrack))

        schemeLbl = QtWidgets.QLabel(prefWidget)
        schemeLbl.setGeometry(QtCore.QRect(256, 0, 150, 30))
        schemeLbl.setFont(headerFont)
        schemeLbl.setText("Color Schemes")

        bgLbl = QtWidgets.QLabel(prefWidget)
        bgLbl.setGeometry(QtCore.QRect(280, 32, 150, 30))
        bgLbl.setText("Background Color")
        bgBtn = QtWidgets.QPushButton(prefWidget)
        bgBtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}")
        bgBtn.setGeometry(QtCore.QRect(256, 40, 15, 15))
        bgBtn.clicked.connect(partial(self.chg_theme, theme=self.bgtheme))

        hlLbl = QtWidgets.QLabel(prefWidget)
        hlLbl.setGeometry(QtCore.QRect(280, 62, 150, 30))
        hlLbl.setText("Highlighted Color")
        hlBtn = QtWidgets.QPushButton(prefWidget)
        hlBtn.setStyleSheet("QPushButton{background-color: " + str(self.hltheme) + ";}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}")
        hlBtn.setGeometry(QtCore.QRect(256, 70, 15, 15))
        hlBtn.clicked.connect(partial(self.chg_theme, theme=self.hltheme))

        plLbl = QtWidgets.QLabel(prefWidget)
        plLbl.setGeometry(QtCore.QRect(280, 92, 150, 30))
        plLbl.setText("Plotting Color")
        plBtn = QtWidgets.QPushButton(prefWidget)
        plBtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}")
        plBtn.setGeometry(QtCore.QRect(256, 100, 15, 15))
        plBtn.clicked.connect(partial(self.chg_theme, theme=self.pltheme))
    
        resLbl = QtWidgets.QLabel(prefWidget)
        resLbl.setGeometry(QtCore.QRect(5, 160, 100, 30))
        resLbl.setFont(headerFont)
        resLbl.setText("Resources")

        resLbl = QtWidgets.QLabel(prefWidget)
        resLbl.setGeometry(QtCore.QRect(5, 195, 100, 30))
        resLbl.setText("Refresh Rate:")
        resRefresh = QtWidgets.QDoubleSpinBox(prefWidget)
        resRefresh.setGeometry(QtCore.QRect(108,200,110,24))
        resRefresh.setRange(0.5,10)
        resRefresh.setSingleStep(0.5)
        resRefresh.setLocale(QtCore.QLocale("C"))
        resRefresh.setDecimals(1)
        resRefresh.setValue(self.rtime)
        resRefresh.setSuffix("s")
        resRefresh.setPalette(palette)
        resRefresh.setFocusPolicy(QtCore.Qt.NoFocus)

        resRefresh.setStyleSheet("QDoubleSpinBox{padding-right: 0px; padding-left: 4px;\n"
"       border: 1px solid rgb(0,0,0); border-radius: 12px; background-color: rgb(209,209,211);}\n"
"       QDoubleSpinBox::up-button{min-width: 22px; min-height: 22px;\n"
"       border-bottom-right-radius: 11px; border-top-right-radius: 11px;\n"
"       background-color: rgb(159,36,37); subcontrol-position: center right;\n"
"       background-image: url(" + self.icon_dir + "plus4.png\");\n"
"       background-position: center; background-repeat: no-repeat;}\n"
"       QDoubleSpinBox::down-button{min-width: 22px; min-height: 22px;\n"
"       border-top-left-radius: 11px; border-bottom-left-radius: 11px;\n"
"       subcontrol-position: center left; background-color: rgb(159,36,37);\n"
"       background-image: url(" + self.icon_dir + "minus1.png\");\n"
"       background-position: center; background-repeat: no-repeat;}")
        
        resRefresh.valueChanged.connect(partial(self.resref, box=resRefresh))

        gridLbl = QtWidgets.QLabel(prefWidget)
        gridLbl.setGeometry(QtCore.QRect(5, 250, 60, 30))
        gridLbl.setText("Plot Grid:")

        gridRdbtn = QtWidgets.QCheckBox(prefWidget)
        gridRdbtn.setGeometry(QtCore.QRect(75, 260, 15, 15))
        gridRdbtn.setStyleSheet("QCheckBox{border: 2px solid rgb(138,108,88); color:rgb(169,46,47); background-color:rgb(178,148,128);}\n"
"       QCheckBox:indicator{color:rgb(169,46,47); width: 15px; height: 15px;}")        
        if self.pltgrid:
            gridRdbtn.setChecked(True)
        else:
            gridRdbtn.setChecked(False)
        gridRdbtn.stateChanged.connect(partial(self.gridupdate, btn=gridRdbtn))

        groupBox = QtWidgets.QGroupBox(prefWidget)
        groupBox.setGeometry(QtCore.QRect(230, 200, 255, 140))
        groupBox.setTitle("Plot Style")
        groupBox.setStyleSheet("QGroupBox{border: 1px solid rgb(84,58,38); border-radius: 10px;}\n"
"       QGroupBox:title {subcontrol-origin: margib; subcontrol-position: top center;\n"
"       padding-left: 10px; padding-right: 10px;}")
        groupBox.show()

        cLbl = QtWidgets.QLabel(prefWidget)
        cLbl.setGeometry(QtCore.QRect(235, 225, 65, 30))
        cLbl.setText("CPU:")
        cpuMenu = QtWidgets.QComboBox(prefWidget)
        cpuMenu.setGeometry(QtCore.QRect(305, 225, 175, 30))
        cpuMenu.setStyleSheet("QComboBox{background:rgb(144,118,98);} QComboBox::item{background:rgb(209,209,211);}\n"
"       QComboBox::item:selected{background:rgb(159,36,37);}")
        cpuMenu.addItems(['Line Plot', 'Adaptive Line Plot', 'Bargraph', 'Adaptive Bargraph'])
        cpuMenu.setCurrentIndex(self.cpustyle)
        cpuMenu.currentIndexChanged.connect(self.cpuplotstyle)
        
        mLbl = QtWidgets.QLabel(prefWidget)
        mLbl.setGeometry(QtCore.QRect(235, 265, 65, 30))
        mLbl.setText("Memory:")
        memMenu = QtWidgets.QComboBox(prefWidget)
        memMenu.setGeometry(QtCore.QRect(305, 265, 175, 30))
        memMenu.setStyleSheet("QComboBox{background:rgb(144,118,98);} QComboBox::item{background:rgb(209,209,211);}\n"
"       QComboBox::item:selected{background:rgb(159,36,37);}")
        memMenu.addItems(['Line Plot', 'Adaptive Line Plot', 'Bargraph', 'Adaptive Bargraph'])
        memMenu.setCurrentIndex(self.memstyle)
        memMenu.currentIndexChanged.connect(self.memplotstyle)

        mLbl = QtWidgets.QLabel(prefWidget)
        mLbl.setGeometry(QtCore.QRect(235, 305, 65, 30))
        mLbl.setText("Network:")
        netMenu = QtWidgets.QComboBox(prefWidget)
        netMenu.setGeometry(QtCore.QRect(305, 305, 175, 30))
        netMenu.setStyleSheet("QComboBox{background:rgb(144,118,98);} QComboBox::item{background:rgb(209,209,211);}\n"
"       QComboBox::item:selected{background:rgb(159,36,37);}")
        netMenu.addItems(['Adaptive Line Plot', 'Adaptive Bargraph'])
        netMenu.setCurrentIndex(self.netstyle)
        netMenu.currentIndexChanged.connect(self.netplotstyle)
           
        ancLbl = QtWidgets.QLabel(prefWidget)
        ancLbl.setGeometry(QtCore.QRect(5, 350, 100, 30))
        ancLbl.setFont(headerFont)
        ancLbl.setText("Ancillary")

        ancLbl = QtWidgets.QLabel(prefWidget)
        ancLbl.setGeometry(QtCore.QRect(5, 385, 100, 30))
        ancLbl.setText("Refresh Rate:")
        ancRefresh = QtWidgets.QDoubleSpinBox(prefWidget)
        ancRefresh.setGeometry(QtCore.QRect(108,389,110,24))
        ancRefresh.setRange(0.5,10)
        ancRefresh.setSingleStep(0.5)
        ancRefresh.setLocale(QtCore.QLocale("C"))
        ancRefresh.setDecimals(1)
        ancRefresh.setValue(self.atime)
        ancRefresh.setSuffix("s")
        ancRefresh.setPalette(palette)
        ancRefresh.setFocusPolicy(QtCore.Qt.NoFocus)

        ancRefresh.setStyleSheet("QDoubleSpinBox{padding-right: 0px; padding-left: 4px;\n"
"       border: 1px solid rgb(0,0,0); border-radius: 12px; background-color: rgb(209,209,211);}\n"
"       QDoubleSpinBox::up-button{min-width: 22px; min-height: 22px;\n"
"       border-bottom-right-radius: 11px; border-top-right-radius: 11px;\n"
"       background-color: rgb(159,36,37); subcontrol-position: center right;\n"
"       background-image: url(" + self.icon_dir + "plus4.png\");\n"
"       background-position: center; background-repeat: no-repeat;}\n"
"       QDoubleSpinBox::down-button{min-width: 22px; min-height: 22px;\n"
"       border-top-left-radius: 11px; border-bottom-left-radius: 11px;\n"
"       subcontrol-position: center left; background-color: rgb(159,36,37);\n"
"       background-image: url(" + self.icon_dir + "minus1.png\");\n"
"       background-position: center; background-repeat: no-repeat;}")
        
        ancRefresh.valueChanged.connect(partial(self.ancref, box=ancRefresh))

        warnLbl = QtWidgets.QLabel(prefWidget)
        warnLbl.setGeometry(QtCore.QRect(5, 435, 170, 30))
        warnLbl.setText("Disk Properties Warning:")

        warnRdbtn = QtWidgets.QCheckBox(prefWidget)
        warnRdbtn.setGeometry(QtCore.QRect(185, 445, 15, 15))
        warnRdbtn.setStyleSheet("QCheckBox{border: 2px solid rgb(138,108,88); color:rgb(169,46,47); background-color:rgb(178,148,128);}\n"
"       QCheckBox:indicator{color:rgb(169,46,47); width: 15px; height: 15px;}")        
        if self.diskwarn:
            warnRdbtn.setChecked(True)
        else:
            warnRdbtn.setChecked(False)
        warnRdbtn.stateChanged.connect(partial(self.warnupdate, btn=warnRdbtn))

        groupBox = QtWidgets.QGroupBox(prefWidget)
        groupBox.setGeometry(QtCore.QRect(230, 390, 255, 110))
        groupBox.setTitle("Temperature && Fan")
        groupBox.setStyleSheet("QGroupBox{border: 1px solid rgb(84,58,38); border-radius: 10px;}\n"
"       QGroupBox:title {subcontrol-origin: margib; subcontrol-position: top center;\n"
"       padding-left: 10px; padding-right: 10px;}")
        groupBox.show()

        unitLbl = QtWidgets.QLabel(prefWidget)
        unitLbl.setGeometry(QtCore.QRect(235, 420, 185, 30))
        unitLbl.setText("Temperature Unit:")
        celLbl = QtWidgets.QLabel(prefWidget)
        celLbl.setGeometry(QtCore.QRect(390, 420, 40, 30))
        celLbl.setText(u"\N{DEGREE SIGN}" + "C")
        farLbl = QtWidgets.QLabel(prefWidget)
        farLbl.setGeometry(QtCore.QRect(450, 420, 40, 30))
        farLbl.setText(u"\N{DEGREE SIGN}" + "F")
        
        tfGroup = QtWidgets.QButtonGroup(prefWidget)
        celRdbtn = QtWidgets.QPushButton(prefWidget)
        celRdbtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}\n"
"       QPushButton:checked{background-color:red;}") 
        farRdbtn = QtWidgets.QPushButton(prefWidget)
        farRdbtn.setStyleSheet("QPushButton{background-color:rgb(178,148,128);}\n"
"       QPushButton:hover{background-color:rgb(193,163,143);}\n"
"       QPushButton:checked{background-color:red;}")
        celRdbtn.setCheckable(True)
        farRdbtn.setCheckable(True)
        tfGroup.addButton(celRdbtn)
        tfGroup.addButton(farRdbtn)
        tfGroup.setExclusive(True)
        celRdbtn.setGeometry(QtCore.QRect(370, 430, 15, 15))
        farRdbtn.setGeometry(QtCore.QRect(430, 430, 15, 15))
        
        if self.tunit==0:
            celRdbtn.setChecked(True)
        else:
            farRdbtn.setChecked(True)
        tfGroup.buttonClicked.connect(partial(self.tempunits, tgroup=tfGroup))

        tLbl = QtWidgets.QLabel(prefWidget)
        tLbl.setGeometry(QtCore.QRect(235, 460, 125, 30))
        tLbl.setText("Plot Style:")   
        tempMenu = QtWidgets.QComboBox(prefWidget)
        tempMenu.setGeometry(QtCore.QRect(305, 460, 175, 30))
        tempMenu.setStyleSheet("QComboBox{background:rgb(144,118,98);} QComboBox::item{background:rgb(209,209,211);}\n"
"       QComboBox::item:selected{background:rgb(159,36,37);}")
        if self.tfchoice==0:
            tempMenu.addItems(['Line Plot', 'Bargraph'])
        else:
            tempMenu.addItems(['Adaptive Line Plot', 'Adaptive Bargraph'])
        tempMenu.setCurrentIndex(self.tempstyle)
        tempMenu.currentIndexChanged.connect(self.tempplotstyle)
        
        PrefWindow.show()

    def chg_defaults(self, key, val):

        self.defaults[key][1] = val

        with open(self.cwd + '/setup.yaml', 'r') as file:
            default = safe_load(file)
            default.update(self.defaults)

        with open(self.cwd + '/setup.yaml','w') as file:
            safe_dump(default, file)

    def rtn_defaults(self):

        for key, value in self.defaults.iteritems():
            self.defaults[key][1] = self.defaults[key][0]           

        with open(self.cwd + '/setup.yaml', 'r') as file:
            default = safe_load(file)
            default.update(self.defaults)

        with open(os.getcwd() + '/setup.yaml','w') as file:
            safe_dump(default, file)
        

    def chg_theme(self, theme):

        color = QtWidgets.QColorDialog(self.centralwidget)
        color = color.getColor()

        if color.isValid():

            if theme==self.bgtheme:
                self.bgtheme = color.name()
                self.chg_defaults("bgcolor", self.bgtheme)
            elif theme==self.pltheme:
                self.pltheme = color.name()
                self.chg_defaults("plcolor", self.pltheme)
            elif theme==self.hltheme:
                self.hltheme = color.name()
                self.chg_defaults("hlcolor", self.hltheme)

    def hex2rgb(self, color):
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        return rgb
        
    def refresh(self):
        
        for id, thread in threading._active.items(): 
            try:
                thread.cancel()
            except:
                pass
        self.stat_update()

    def pclose(self, Window):
        Window.close()

    def end(self, Window):
        self.proc.terminate()
        self.terminated = True
        self.pclose(Window)

    def kill(self, Window):
        self.proc.kill()
        self.terminated = True
        self.pclose(Window)

    def authenticate(self, Window, Text, **kwargs):
        nice = 30
        for key, component in kwargs.items():
            if key == 'nice':
                nice = component
            elif key == 'button':
                button = component
        if nice!=30:
            command = "sudo renice -n " + str(nice) + " -p " + str(self.proc.pid)
            system('echo %s|sudo -S %s' % (Text.text(), command))
            del command
            del Text
            if nice==self.proc.nice():
                button.setChecked(True)
        else:
            pass
        self.pclose(Window)
    
    def niceIndicate(self, slider, lbl):

        cnice = slider.value()
        if (cnice>=-2) & (cnice<=2):
            status = ' Is Normal Priority'
        elif (cnice>2) & (cnice<8):
            status = ' Is Low Priority'
        elif (cnice<-2) & (cnice>-8):
            status = ' Is High Priority'
        elif (cnice>=8):
            status = ' Is Very Low Priority'
        elif (cnice<=-8):
             status = ' Is Very High Priority'

        lbl.setText("Current Value: " + str(cnice) + status)

    def niceSet(self, value, button, **kwargs):

        for key, component in kwargs.items():
            if key == 'Window':
                window = component

        try:
            value = value.value()
            win = True
        except:
            win = False
        try:
            self.proc.nice(value)
            button.setChecked(True)
        except:
            self.procSudo(nice=value, button=button)

        if win:
            self.pclose(window)

    def rlimCurrent(self, index, lbl, limits):
        lbl.setText(str(limits[index]))

    def rlimSet(self, index, command, soft, hard, lbl):
        
        try:
            soft = soft.text().replace(" ", "")
            hard = hard.text().replace(" ", "")
            self.proc.rlimit(command[index.currentIndex()], (int(soft), int(hard)))
            lbl.setText(str(self.proc.rlimit(command[index.currentIndex()])))
        except:
            self.procDenied()

    def schedCurrent(self, index, lbl, editor):

        if index==0:
            minp = sched_get_priority_min(SCHED_OTHER)
            maxp = sched_get_priority_max(SCHED_OTHER)
                
        elif index==1:
            minp = sched_get_priority_min(SCHED_BATCH)
            maxp = sched_get_priority_max(SCHED_BATCH)

        elif index==2:
            minp = sched_get_priority_min(SCHED_IDLE)
            maxp = sched_get_priority_max(SCHED_IDLE)

        elif index==3:
            minp = sched_get_priority_min(SCHED_FIFO)
            maxp = sched_get_priority_max(SCHED_FIFO)

        elif index==4:
            minp = sched_get_priority_min(SCHED_RR)
            maxp = sched_get_priority_max(SCHED_RR)

        lbl.setText('Allowed Minimum Priority: ' + str(minp) + '\nAllowed Maximum Priority: ' + str(maxp))     
        editor.setRange(minp,maxp)

    def schedSet(self, index, lbl1, lbl2, editor):

        try:
            if index.currentIndex()==0:
                sched_setscheduler(self.proc.pid, SCHED_OTHER, sched_param(int(editor.value())))
                policy = 'Default'
                minp = sched_get_priority_min(SCHED_OTHER)
                maxp = sched_get_priority_max(SCHED_OTHER)
                
            elif index.currentIndex()==1:
                sched_setscheduler(self.proc.pid, SCHED_BATCH, sched_param(int(editor.value())))
                policy = 'CPU-intensive'
                minp = sched_get_priority_min(SCHED_BATCH)
                maxp = sched_get_priority_max(SCHED_BATCH)

            elif index.currentIndex()==2:
                sched_setscheduler(self.proc.pid, SCHED_IDLE, sched_param(int(editor.value())))
                policy = 'Low Priority'
                minp = sched_get_priority_min(SCHED_IDLE)
                maxp = sched_get_priority_max(SCHED_IDLE)

            elif index.currentIndex()==3:
                sched_setscheduler(self.proc.pid, SCHED_FIFO, sched_param(int(editor.value())))
                policy = 'Fist-In-First-Out'
                minp = sched_get_priority_min(SCHED_FIFO)
                maxp = sched_get_priority_max(SCHED_FIFO)

            elif index.currentIndex()==4:
                sched_setscheduler(self.proc.pid, SCHED_RR, sched_param(int(editor.value())))
                policy = 'Round-robin'
                minp = sched_get_priority_min(SCHED_RR)
                maxp = sched_get_priority_max(SCHED_RR)
                
            param = str(sched_getparam(self.proc.pid)).replace(')', '').split('=')[1]
            lbl1.setText('Current Policy: '+ policy + '\nCurrent Priority: ' + param)
            lbl2.setText('Allowed Minimum Priority: ' + str(minp) + '\nAllowed Maximum Priority: ' + str(maxp)) 
            
        except:
            self.procDenied()
        
    def procref(self, box):
        self.ptime = float(box.value())
        self.chg_defaults("pg1time", self.ptime)

    def resref(self, box):
        self.rtime = float(box.value())
        self.chg_defaults("pg2time", self.rtime)

    def ancref(self, box):
        self.atime = float(box.value())
        self.chg_defaults("pg3time", self.atime)

    def memswitch(self, slider):

        if slider.value()==0:
            self.memvis = 0
            icon = QtWidgets.QTableWidgetItem("Memory%")
            if self.header_indx!=4:
                self.tableWidget.setHorizontalHeaderItem(4, icon)
            else:
                try:
                    if self.switch:
                        icon.setIcon(QtGui.QIcon(self.icon_dir[1:] + "down_arrow4.png"))
                    else:
                        icon.setIcon(QtGui.QIcon(self.icon_dir[1:] + "up_arrow2.png"))
                    self.tableWidget.setHorizontalHeaderItem(4, icon)
                except:
                    pass
            slider.setStyleSheet("QSlider::groove:horizontal{border: 1px solid;\n"
"       background-color: rgb(147,24,25); height: 19px; margin: 0px;\n"
"       background-image: url(" + self.icon_dir + "memswitch1.png\");\n"
"       background-position: right; background-repeat: no-repeat;}\n"
"       QSlider::handle:horizontal{background-color: rgb(209,209,211); border: 1px solid;\n"
"       background-image: url(" + self.icon_dir + "navigation5.png\");\n"
"       background-position: center; background-repeat: no-repeat;\n"
"       height: 20px; width: 54px; margin: -15px 0px;}")
        else:
            self.memvis = 1
            icon = QtWidgets.QTableWidgetItem("Memory")
            self.tableWidget.setHorizontalHeaderItem(4, icon)
            if self.header_indx!=4:
                self.tableWidget.setHorizontalHeaderItem(4, icon)
            else:
                try:
                    if self.switch:
                        icon.setIcon(QtGui.QIcon(self.icon_dir[1:] + "down_arrow4.png"))
                    else:
                        icon.setIcon(QtGui.QIcon(self.icon_dir[1:] + "up_arrow2.png"))
                    self.tableWidget.setHorizontalHeaderItem(4, icon)
                except:
                    pass
            slider.setStyleSheet("QSlider::groove:horizontal{border: 1px solid;\n"
"       background-color: rgb(147,24,25); height: 19px; margin: 0px;\n"
"       background-image: url(" + self.icon_dir + "memswitch2.png\");\n"
"       background-position: left; background-repeat: no-repeat;}\n"
"       QSlider::handle:horizontal{background-color: rgb(209,209,211); border: 1px solid;\n"
"       background-image: url(" + self.icon_dir + "navigation5.png\");\n"
"       background-position: center; background-repeat: no-repeat;\n"
"       height: 20px; width: 54px; margin: -15px 0px;}")

        self.chg_defaults("memview", self.memvis)

    def trackswitch(self, slider):

        if slider.value()==0:
            self.ptrack = 0
            slider.setStyleSheet("QSlider::groove:horizontal{border: 1px solid;\n"
"       background-color: rgb(147,24,25); height: 19px; margin: 0px;\n"
"       background-image: url(" + self.icon_dir + "track1.png\");\n"
"       background-position: right; background-repeat: no-repeat;}\n"
"       QSlider::handle:horizontal{background-color: rgb(209,209,211); border: 1px solid;\n"
"       background-image: url(" + self.icon_dir + "navigation5.png\");\n"
"       background-position: center; background-repeat: no-repeat;\n"
"       height: 20px; width: 54px; margin: -15px 0px;}")
        else:
            self.ptrack = 1
            slider.setStyleSheet("QSlider::groove:horizontal{border: 1px solid;\n"
"       background-color: rgb(147,24,25); height: 19px; margin: 0px;\n"
"       background-image: url(" + self.icon_dir + "track2.png\");\n"
"       background-position: left; background-repeat: no-repeat;}\n"
"       QSlider::handle:horizontal{background-color: rgb(209,209,211); border: 1px solid;\n"
"       background-image: url(" + self.icon_dir + "navigation5.png\");\n"
"       background-position: center; background-repeat: no-repeat;\n"
"       height: 20px; width: 54px; margin: -15px 0px;}")

        self.chg_defaults("proctrack", self.ptrack)

    def cpuplotstyle(self,index):

        self.cpustyle = index
        self.chg_defaults("cpuplt", self.cpustyle)

    def memplotstyle(self,index):

        self.memstyle = index
        self.chg_defaults("memplt", self.memstyle)

    def netplotstyle(self,index):

        self.netstyle = index
        self.chg_defaults("netplt", self.netstyle)

    def tempplotstyle(self,index):

        self.tempstyle = index
        self.chg_defaults("templt", self.tempstyle)

    def gridupdate(self, btn):

        if btn.isChecked():
            self.pltgrid = True
        else:
            self.pltgrid = False

        self.chg_defaults("gridplot", self.pltgrid)

    def tempunits(self, tgroup):
        tempselected = tgroup.checkedId()

        try:
            self.tempList.clear()
            self.tempList = [0.0]*19
        except:
            pass
        
        if tempselected==-2:
            self.tunit=0

        elif tempselected==-3:
            self.tunit=1

        self.chg_defaults("tempunit", self.tunit)

    def warnupdate(self, btn):

        if btn.isChecked():
            self.diskwarn = True
        else:
            self.diskwarn = False
            self.disklimit = False

        self.chg_defaults("diskwarning", self.diskwarn)

    def warnlookup(self, btn):

        if btn.isChecked():
            self.disklimit = False
        else:
            self.disklimit = True

    def on_context_menu(self, event):
        
        self.popMenu = QtWidgets.QMenu(self.centralwidget)
        self.mMenu = QtWidgets.QMenu('More', self.centralwidget)
        self.pMenu = QtWidgets.QMenu('Change Priority', self.centralwidget)
        self.popMenu.setStyleSheet("QMenu{background:rgb(144,118,98);} QMenu::item:selected{background:rgb(159,36,37);}")
        self.mMenu.setStyleSheet("QMenu{background:rgb(144,118,98);} QMenu::item:selected{background:rgb(159,36,37);}")
        self.pMenu.setStyleSheet("QMenu{background:rgb(144,118,98);} QMenu::item:selected{background:rgb(159,36,37);}")
        prop = self.popMenu.addAction('Properties')
        self.popMenu.addSeparator()
        memap = self.popMenu.addAction('Memory Map')
        fdir = self.popMenu.addAction('Location')
        openf = self.popMenu.addAction('Open Files')
        more = self.popMenu.addMenu(self.mMenu)
        self.popMenu.addSeparator()
        prior = self.popMenu.addMenu(self.pMenu)
        self.popMenu.addSeparator()
        stop = self.popMenu.addAction('Stop')
        cont = self.popMenu.addAction('Continue')
        end = self.popMenu.addAction('End')
        kill = self.popMenu.addAction('Kill')

        opthreads = self.mMenu.addAction('Open Threads')
        pandc = self.mMenu.addAction('P&&C Processes')
        env = self.mMenu.addAction('Env Variables')
        try:
            con = self.proc.connections()
            if len(con)>0:
                connect = self.mMenu.addAction('Connections')
            else:
                connect = False
        except:
            connect = False
        rlim = self.mMenu.addAction('Resource Limits')
        schedule = self.mMenu.addAction('Scheduler')

        paction1 = QtWidgets.QAction('Very High', self.pMenu, checkable=True)
        paction2 = QtWidgets.QAction('High', self.pMenu, checkable=True)
        paction3 = QtWidgets.QAction("Normal", self.pMenu, checkable=True)
        paction4 = QtWidgets.QAction('Low', self.pMenu, checkable=True)
        paction5 = QtWidgets.QAction('Very Low', self.pMenu, checkable=True)
        paction6 = QtWidgets.QAction('Custom', self.pMenu, checkable=True)
        self.pMenu.addAction(paction1)
        self.pMenu.addAction(paction2)
        self.pMenu.addAction(paction3)
        self.pMenu.addAction(paction4)
        self.pMenu.addAction(paction5)
        self.pMenu.addSeparator()
        self.pMenu.addAction(paction6) 
        self.pGAction = QtWidgets.QActionGroup(self.pMenu)
        self.pGAction.addAction(paction1)
        self.pGAction.addAction(paction2)
        self.pGAction.addAction(paction3)
        self.pGAction.addAction(paction4)
        self.pGAction.addAction(paction5)
        self.pGAction.addAction(paction6)

        self.LeftUpdate = True
       
        if event==False:
            event = self.set_event
        else:
            self.preInfoGrab(event)

        prior = self.proc.nice()

        if prior==0:
            paction3.setChecked(True)
            
        elif prior==5:
            paction4.setChecked(True)

        elif prior==-5:
            paction2.setChecked(True)

        elif prior==-14:
            paction5.setChecked(True)
            
        elif prior==14:
            paction1.setChecked(True)
            
        else:
            paction6.setChecked(True)

        if event != self.set_event:
            event = QtCore.QPoint(event.x(), event.y()+65)
        else:
            event = QtCore.QPoint(event.x()-30, event.y()-260) 
        action = self.popMenu.exec_(self.Sort.mapToGlobal(event))

        if action==prop:
            self.Properties()

        elif action==memap:
            self.Memapper()

        elif action==fdir:
            file_dir = path.dirname(self.proc.exe())
            command = str('xdg-open ' + file_dir)
            system(command)

        elif action==openf:
            self.Openfile()

        elif action==stop:
            self.proc.suspend()

        elif action==cont:
            self.proc.resume()

        elif action==end:
            prompt = 0
            self.promptAction(prompt)

        elif action==kill:
            prompt = 1
            self.promptAction(prompt)

        elif action==opthreads:
            self.procThreads()
            
        elif action==pandc:
            self.procPC()

        elif action==env:
            self.procEnv()

        elif action==connect:
            self.procSockets()

        elif action==rlim:
            self.procRlim()

        elif action==schedule:
            self.procSchedule()

        elif action==paction1:
            self.niceSet(-14, paction1)

        elif action==paction2:
            self.niceSet(-5, paction2)

        elif action==paction3:
            self.niceSet(0, paction3)

        elif action==paction4:
            self.niceSet(5, paction4)

        elif action==paction5:
            self.niceSet(14, paction5)
                
        elif action==paction6:
            self.procNice(paction6)

        gc.collect()

    def disk_context_menu(self, event):
        
        self.diskMenu = QtWidgets.QMenu(self.centralwidget)
        self.diskMenu.setStyleSheet("QMenu{background:rgb(144,118,98);} QMenu::item:selected{background:rgb(159,36,37);}")
        prop = self.diskMenu.addAction('Properties')
        opener = self.diskMenu.addAction('Open')

        index = self.diskTable.indexAt(event)
        event = QtCore.QPoint(event.x(), event.y()+260)
        action = self.diskMenu.exec_(self.Sort.mapToGlobal(event))

        if action==opener:
            command = str('xdg-open ' + status[int(index.row())])
            system(command)

        elif action==prop:
            wdir = status[int(index.row())] 
            allpart = psutil.disk_partitions() 
            for item in allpart:
                if item.mountpoint == wdir:
                    wname = item.device
                    opts = item.opts
                    break
                
            if self.diskwarn:
                self.warnAction(wname,wdir,opts)
            else:
                self.diskProp(wname,wdir,opts)
            
        gc.collect()

    def diskDblClick(self, event):

        command = str('xdg-open ' + status[int(event.row())])
        system(command)
        

    def keyPressEvent(self, event):
        if event.key()  == QtCore.Qt.Key_Down:
            return None
        elif event.key() == QtCore.Qt.Key_Up:   
            return None

    def find_proc(self):
        
        if not self.search_change:
            if self.tableWidget.selectionModel().hasSelection():
                self.tableWidget.setGeometry(QtCore.QRect(0, 70, 820, 490))
            else:
                self.tableWidget.setGeometry(QtCore.QRect(0, 70, 820, 530))
            self.search_change = not self.search_change
            self.searching.clear() 
            self.searching.setVisible(True) 
            self.searching.setFocus()
        else:
            if self.tableWidget.selectionModel().hasSelection():
                self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 525))
            else:
                self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 565))
            self.search_change = not self.search_change
            self.searching.clear()
            self.searching.setVisible(False)

    def sort_proc(self):   

        event = QtCore.QPoint(2,33)
        action = self.sort_menu.exec_(self.Sort.mapToGlobal(event))

        if action==None:
            return action
        
        if action.text() == "Refresh":
            self.refresh()
        elif action.text() == "All Processes":
            self.seeing = 1
        elif action.text() == "GUI Processes":
            self.seeing = 2
        elif action.text() == "Preferences":
            self.Preferences()
        else:
            self.seeing = 0
            
        self.chg_defaults("procview", self.seeing)

        try:
            if (action.text()!="Refresh") & (action.text()!="Preferences"):
                self.tableWidget.clearSelection()
                if not self.search_change:
                    self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 565))
                else:
                    self.tableWidget.setGeometry(QtCore.QRect(0, 70, 820, 535))
                self.PEnd.setVisible(False)
                self.PSet.setVisible(False)
        except:
            pass
    def sort_proc2(self):

        event = QtCore.QPoint(0,33)
        action = self.sort_menu2.exec_(self.Sort2.mapToGlobal(event))

        if action==None:
            return action
        
        if action.text() == "CPU Stats":
            self.cpuStats()
        elif action.text() == "Memory Stats":
            self.memStats()
        elif action.text() == "Connections":
            self.netConnect()
        elif action.text() == "NIC && IO Counters":
            self.netStat()
        elif action.text() == "Network Addresses":
            self.netAddress()
        elif action.text() == "Preferences":
            self.Preferences()

    def sort_proc3(self):

        event = QtCore.QPoint(0,33)
        action = self.sort_menu3.exec_(self.Sort3.mapToGlobal(event))

        if action==None:
            return action
        
        if action.text() == "Preferences":
            self.Preferences()

    def chk_proc(self):
        if self.tblswitch:
            self.header_indx = self.changetbl1
            self.sorter = self.switch1
            self.tblswitch = False
        if not self.tableWidget.selectionModel().hasSelection():
            self.PEnd.setVisible(False)
            self.PSet.setVisible(False)
        else:
            self.PEnd.setVisible(True)
            self.PSet.setVisible(True)
            self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 525))
        
        self.mainView = True
        self.Search.setVisible(True)
        self.Sort.setVisible(True)
        self.Sort2.setVisible(False)
        self.Sort3.setVisible(False)
        self.tableWidget.setVisible(True)
        self.cpuPlot.setVisible(False)
        self.memPlot.setVisible(False)
        self.netPlot.setVisible(False)
        self.cpuWidget.setVisible(False)
        self.memPtable.setVisible(False)
        self.swapTable.setVisible(False)
        self.mem1Label.setVisible(False)
        self.mem2Label.setVisible(False)
        self.mem3Label.setVisible(False)
        self.mem4Label.setVisible(False)
        self.memRdbtn.setVisible(False)
        self.swapRdbtn.setVisible(False)
        self.net1Label.setVisible(False)
        self.net2Label.setVisible(False)
        self.net3Label.setVisible(False)
        self.net4Label.setVisible(False)
        self.downloadRdbtn.setVisible(False)
        self.uploadRdbtn.setVisible(False)
        self.tempPlot.setVisible(False)
        self.diskTable.setVisible(False)
        self.temptotLabel.setVisible(False)
        self.fanLabel.setVisible(False)
        self.temptotRdbtn.setVisible(False)
        self.fanRdbtn.setVisible(False)

    def chk_res(self):
        self.mainView = False
        self.Search.setVisible(False)
        if self.searching.isVisible(): 
            self.searching.setVisible(False)
            self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 565))
            self.search_change = not self.search_change
        self.PEnd.setVisible(False)
        self.PSet.setVisible(False)
        self.Sort.setVisible(False)
        self.Sort2.setVisible(True)
        self.Sort3.setVisible(False)
        self.tableWidget.setVisible(False)
        self.cpuPlot.setVisible(True)
        self.memPlot.setVisible(True)
        self.netPlot.setVisible(True)
        self.cpuWidget.setVisible(True)
        self.memPtable.setVisible(True)
        self.swapTable.setVisible(True)
        self.mem1Label.setVisible(True)
        self.mem2Label.setVisible(True)
        self.mem3Label.setVisible(True)
        self.mem4Label.setVisible(True)
        self.memRdbtn.setVisible(True)
        self.swapRdbtn.setVisible(True)
        self.net1Label.setVisible(True)
        self.net2Label.setVisible(True)
        self.net3Label.setVisible(True)
        self.net4Label.setVisible(True)
        self.downloadRdbtn.setVisible(True)
        self.uploadRdbtn.setVisible(True)
        self.tempPlot.setVisible(False)
        self.diskTable.setVisible(False)
        self.temptotLabel.setVisible(False)
        self.fanLabel.setVisible(False)
        self.temptotRdbtn.setVisible(False)
        self.fanRdbtn.setVisible(False)

    def anc_proc(self):
        if not self.tblswitch:
            self.header_indx = self.changetbl2
            self.sorter = self.switch2
            self.tblswitch = True
        self.mainView = False 
        self.Search.setVisible(False)
        if self.searching.isVisible(): 
            self.searching.setVisible(False)
            self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 565))
            self.search_change = not self.search_change
        self.PEnd.setVisible(False)
        self.PSet.setVisible(False)
        self.Sort.setVisible(False)
        self.Sort2.setVisible(False)
        self.Sort3.setVisible(True)
        self.tableWidget.setVisible(False)
        self.cpuPlot.setVisible(False)
        self.memPlot.setVisible(False)
        self.netPlot.setVisible(False)
        self.cpuWidget.setVisible(False)
        self.memPtable.setVisible(False)
        self.swapTable.setVisible(False)
        self.mem1Label.setVisible(False)
        self.mem2Label.setVisible(False)
        self.mem3Label.setVisible(False)
        self.mem4Label.setVisible(False)
        self.memRdbtn.setVisible(False)
        self.swapRdbtn.setVisible(False)
        self.net1Label.setVisible(False)
        self.net2Label.setVisible(False)
        self.net3Label.setVisible(False)
        self.net4Label.setVisible(False)
        self.downloadRdbtn.setVisible(False)
        self.uploadRdbtn.setVisible(False)
        self.tempPlot.setVisible(True)
        self.diskTable.setVisible(True)
        self.temptotLabel.setVisible(True)
        self.fanLabel.setVisible(True)
        if not self.nofan:
            self.temptotRdbtn.setVisible(True)
            self.fanRdbtn.setVisible(True)

    def lookup1(self):

        top_stats2 = popen(self.command1).read()
        top_stats2 = top_stats2.split('%CPU')[2]
        top_stats2 = top_stats2.split()
        PIDS = top_stats2[0::2]
        CPU = top_stats2[1::2]

        return PIDS,CPU

    def lookup2(self):

        ps_stats = popen(self.command2).read()
        ps_stats = ps_stats.split('\n')
        PIDS = []
        CPU = []
        for item in ps_stats: 
            item = ' '.join(item.split())
            item = item.split(' ')
            if len(item)==2:
                CPU.append(item[0])
                PIDS.append(item[1])
        self.stcommand = 1
        self.ptime = self.defaults['pg1time'][1]

        return PIDS,CPU

    def proc_update(self, PIDS, CPU):
        
        pids = []
        name = []
        memory = []
        cpu = []
        user = []
        status = []

        if (self.seeing==0):
            for proc in psutil.process_iter(['pid','name','username']):
                if proc.info['username']==self.CUser:
                    pids.append(proc.info['pid'])
                    name.append(proc.info['name'])
                    p = psutil.Process(proc.info['pid'])
                    if self.memvis==0:
                        mem = int(p.memory_percent())
                    else:
                        try:
                            mem = p.memory_info()
                            mem = mem.rss-mem.shared
                        except:
                            mem = 'N/A'
                    memory.append(mem)
                    user.append(self.CUser)
                    start = str(p).split("started='")[1]
                    start = start.split("'")[0]
                    cstatus = str(p.status() + '       started: ' + start)
                    status.append(cstatus)
                    found = False
                            
                    if str(proc.info['pid']) in PIDS:
                        cpu.append(trunc(float(CPU[PIDS.index(str(proc.info['pid']))])/self.cores))
                        found = True

                    if not found:
                        cpu.append(int(0))
                    
        elif (self.seeing==1):
            for proc in psutil.process_iter(['pid','name','username']):
                pids.append(proc.info['pid'])
                name.append(proc.info['name'])
                p = psutil.Process(proc.info['pid'])
                if self.memvis==0:
                    mem = int(p.memory_percent())
                else:
                    try:
                        mem = p.memory_info()
                        mem = mem.rss-mem.shared
                    except:
                        mem = 'N/A'
                memory.append(mem)
                user.append(p.username())
                start = str(p).split("started='")[1]
                start = start.split("'")[0]
                cstatus = str(p.status() + '       started: ' + start)
                status.append(cstatus)
                found = False
                if str(proc.info['pid']) in PIDS:
                    cpu.append(trunc(float(CPU[PIDS.index(str(proc.info['pid']))])/self.cores))
                    found = True
                if not found:
                    cpu.append(int(0))

        elif (self.seeing==2):

            windows = popen("xprop -root | grep '_NET_CLIENT_LIST(WINDOW)'").read().split('# ')
            windows = windows[1].split('\n')
            windows = windows[0].split(', ')

            for window in windows:
                openw = popen("xprop -id " + window + " | grep '_NET_WM_PID'").read().split('= ')
                try:
                    openw = openw[1].split('\n')[0]
                    pids.append(int(openw))
                    proc = psutil.Process(int(openw))
                    name.append(proc.name())
                    if self.memvis==0:
                        mem = int(proc.memory_percent())
                    else:
                        try:
                            mem = proc.memory_info()
                            mem = mem.rss-mem.shared
                        except:
                            mem = 'N/A'
                    memory.append(mem)
                    user.append(proc.username())
                    start = str(proc).split("started='")[1]
                    start = start.split("'")[0]
                    cstatus = str(proc.status() + '       started: ' + start)
                    status.append(cstatus)
                    found = False
                    if str(openw) in PIDS:
                        cpu.append(trunc(float(CPU[PIDS.index(str(openw))])/self.cores))
                        found = True
                    if not found:
                        cpu.append(int(0))
                except:
                    pass

        return name,user,cpu,pids,memory,status

    def cpu_update(self, PIDS, CPU):

        cusage = sum([float(i) for i in CPU])/self.cores
        first = 0
        second = 0
        third = 0
        fourth = 0
        fifth = 0
        sixth = 0
        seventh = 0
        eighth = 0

        for i in range(len(PIDS)):
            try:
                p = psutil.Process(int(PIDS[i]))
                cpu_num = p.cpu_num()
                if cpu_num==0:
                    first += float(CPU[i])
                elif cpu_num==1:
                    second += float(CPU[i])
                elif cpu_num==2:
                    third += float(CPU[i])
                elif cpu_num==3:
                    fourth += float(CPU[i])
                elif cpu_num==4:
                    fifth += float(CPU[i])
                elif cpu_num==5:
                    sixth += float(CPU[i])
                elif cpu_num==6:
                    seventh += float(CPU[i])
                elif cpu_num==7:
                    eighth += float(CPU[i])
            except:
                pass

        cpufound = [first, second, third, fourth, fifth, sixth, seventh, eighth]
        count = 1
        for i in range(int(self.cores)+1):
        
            cpulabel = self.cpuGrid.itemAt(i+count).widget()
            if i==0:
                cpulabel.setText('CPU Total: ' + str(round(cusage,1)) + '%')
            else:
                cpulabel.setText('CPU'+ str(i) + ': ' + str(min(round(cpufound[i-1],1),100.0)) + '%')
            count += 1

        cpuselected = self.cpuGroup.checkedId()
        if cpuselected != self.ccpuselect:
            self.cpuList.clear()
            self.cpuList = [0.0]*19
            self.ccpuselect = cpuselected
        if cpuselected==-2:
            self.cpuList.append(cusage)
        elif cpuselected==-3:
            self.cpuList.append(min(first,100.0))
        elif cpuselected==-4:
            self.cpuList.append(min(second,100.0))
        elif cpuselected==-5:
            self.cpuList.append(min(third,100.0))
        elif cpuselected==-6:
            self.cpuList.append(min(fourth,100.0))
        elif cpuselected==-7:
            self.cpuList.append(min(fifth,100.0))
        elif cpuselected==-8:
            self.cpuList.append(min(sixth,100.0))
        elif cpuselected==-9:
            self.cpuList.append(min(seventh,100.0))
        elif cpuselected==-10:
            self.cpuList.append(min(eighth,100.0))
        
        if len(self.cpuList)>20:
            self.cpuList.pop(0)

    def mem_update(self):

        mem = psutil.virtual_memory()
        mpercent = mem.percent
        Memory_Update.mpercent = mem.percent

        used_mem = self.Memstring([mem.total-mem.available])[0]
        mem_available = self.Memstring([mem.total])[0]
        self.mem2Label.setText('Memory Usage: ' + used_mem + ' (' + str(round(mem.percent,1)) + '%) of ' + mem_available)
        
        swap = psutil.swap_memory()
        spercent = swap.percent
        Swap_Update.spercent = swap.percent

        swap_mem = self.Memstring([swap.used])[0]
        swap_available = self.Memstring([swap.total])[0]
        self.mem4Label.setText('Swap Usage: ' + swap_mem + ' (' + str(round(swap.percent,1)) + '%) of ' + swap_available)   

        memselected = self.memGroup.checkedId()
        if memselected != self.memselect:
            self.memList.clear()
            self.memList = [0.0]*19
            self.memselect = memselected
        if memselected==-2:
            self.memList.append(mpercent)
        else:
            self.memList.append(spercent)
            
        if len(self.memList)>20:
            self.memList.pop(0)

    def net_update(self):

        net = psutil.net_io_counters()
        ftime = time()
        rtime = ftime - self.stime
        self.stime = ftime
        net_recieved = net.bytes_recv
        net_recieving = (net_recieved - self.recieved)/rtime 
        self.recieved = net_recieved
        net_sent = net.bytes_sent
        net_sending = (net_sent - self.sent)/rtime 
        self.sent = net_sent

        net_r = net_recieving
        net_s = net_sending
        
        net_recieving = self.Memstring([net_recieving])[0]
        net_recieved = self.Memstring([net_recieved])[0]
        net_sending = self.Memstring([net_sending])[0]
        net_sent = self.Memstring([net_sent])[0]

        self.net2Label.setText('Recieving: ' + net_recieving + '/s\nRecieved: ' + net_recieved) 
        self.net4Label.setText('Sending: ' + net_sending + '/s\nSent: ' + net_sent)
     
        netselected = self.netGroup.checkedId()
        if netselected != self.netselect:
            self.netList.clear()
            self.netList = [0.0]*19
            self.netselect = netselected
        if netselected==-2:
            try:
                self.netList.append(net_r)
            except:
                self.netList.append(0)
        else:
            try:
                self.netList.append(net_s)
            except:
                self.netList.append(0)
        
        if len(self.netList)>20:
            self.netList.pop(0)
            
    def temp_update(self):

        temp = psutil.sensors_temperatures()
        theat = 0
        thigh = 0
        tcrit = 0
        tempr = temp.get("coretemp", "")
        for i in range(len(tempr)):
            theat += float(tempr[i][1])
            thigh += float(tempr[i][2])
            tcrit += float(tempr[i][3])

        theat = theat/len(tempr)
        thigh = thigh/len(tempr)
        tcrit = tcrit/len(tempr)
        self.tcrit = tcrit
        self.thigh = thigh
        
        fan = psutil.sensors_fans()
        try:
            self.fanLabel.setText(fan.label + ': ' + fan.current + 'RPM')
            self.nofan = False
        except:
            self.fanLabel.setText('Fan Information: N/A')
            self.nofan = True
    
        tempselected = self.tempGroup.checkedId()
        if tempselected != self.tempselect:
            self.tempList.clear()
            self.tempList = [0.0]*19
            self.tempselect = tempselected
        if tempselected==-2:
            if self.tunit==0:
                self.temptotLabel.setText('Total Temp: ' + str(round(theat,1)) + u"\N{DEGREE SIGN}" + 'C')
                self.tempList.append(theat)
            else:
                self.temptotLabel.setText('Total Temp: ' + str(round(theat*(9/5)+32,1)) + u"\N{DEGREE SIGN}" + 'F')
                self.tempList.append(theat*(9/5)+32)
                self.thigh = thigh*(9/5)+32 
                self.tcrit = tcrit*(9/5)+32   
            self.tfchoice = 0
        elif tempselected==-3:
            self.tempList.append(fan.current)
            self.tfchoice = 1
        
        if len(self.tempList)>20:
            self.tempList.pop(0)

    def time_update(self):

        tchange = int(time() - self.plottime)
        self.timeList[self.tup] = tchange
        self.tup += 1

        if len(self.timeList)>20:
            self.timeList.pop(20)

        if self.tup>19:
            self.tup=0
            self.plottime = time()

    def disk_update(self):

        pids = []
        name = []
        memory = []
        cpu = []
        user = []
        status = []

        disk = psutil.disk_partitions()
        for i in range(len(disk)):

            path = disk[i].mountpoint
            usage = psutil.disk_usage(path)

            name.append(disk[i].device)
            user.append(disk[i].fstype)
            status.append(path)
            pids.append(int(usage.used))
            memory.append(int(usage.free))
            cpu.append(int(usage.total))

        return name,user,cpu,pids,memory,status

    def start_search(self, collection):

        name = collection[0]
        pids = collection[3]
    
        reader = self.searching.text()
        if reader!=self.reader:
            self.tableWidget.clearSelection()
            self.tableWidget.setGeometry(QtCore.QRect(0, 70, 820, 535))
            self.PEnd.setVisible(False)
            self.PSet.setVisible(False)
            self.reader = reader

        if reader.isdigit():
            string = [string for string in enumerate(pids) if reader in str(string[1])]

        else:
            reader = reader.lower()
            string = [string for string in enumerate(name) if reader in string[1].lower()]

        try:
            count = (list(list(zip(*string))[0]))
            
            name, user, cpu, pids, memory, status = [[x[i] for i in count] for x in collection]
            
        except:
            if reader!='':
                name, user, cpu, pids, memory, status = [[] for _ in range(6)]

        return name,user,cpu,pids,memory,status

    def stick_update(self, collection, choice):

        try:
            if not self.terminated:
                ymove = pids.index(self.trace_pid)
                row = choice[0].row()

                for item in collection:
                    grab_item = item[ymove]
                    del item[ymove]
                    item.insert(row, grab_item)

            else:
                self.tableWidget.clearSelection()
                if not self.search_change:
                    self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 565))
                else:
                    self.tableWidget.setGeometry(QtCore.QRect(0, 70, 820, 535))
                self.PEnd.setVisible(False)
                self.PSet.setVisible(False)
        except ValueError:
            pass
        
        return collection

    def trail_update(self, choice):

        try:
            if not self.terminated:
                ymove = pids.index(self.trace_pid)

                if ymove != choice[0].row():

                    self.tableWidget.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(choice[0].row(),0,choice[0].row(),5), False)
                    self.tableWidget.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(ymove,0,ymove,5), True)
                    self.tableWidget.scrollToItem(self.tableWidget.item(ymove, 0), QtWidgets.QAbstractItemView.PositionAtCenter)

            else: 
                self.tableWidget.clearSelection()
                if not self.search_change:
                    self.tableWidget.setGeometry(QtCore.QRect(0, 35, 820, 565))
                else:
                    self.tableWidget.setGeometry(QtCore.QRect(0, 70, 820, 535))
                self.PEnd.setVisible(False)
                self.PSet.setVisible(False)
        except ValueError:
            pass


    def stat_update(self):

        if self.mainView: 
            self.thread = threading.Timer(self.ptime, self.stat_update).start()
        elif self.memPtable.isVisible():
            self.thread = threading.Timer(self.rtime, self.stat_update).start()
        elif self.fanLabel.isVisible():
            self.thread = threading.Timer(self.atime, self.stat_update).start()

        global pids
        global status 

        if self.stcommand==1:
            PIDS, CPU = self.lookup1()

        else: 
            PIDS, CPU = self.lookup2()
            
        if self.mainView:

            name,user,cpu,pids,memory,status = self.proc_update(PIDS, CPU)

        elif self.memPtable.isVisible():

            self.time_update()
            self.cpu_update(PIDS, CPU)
            self.mem_update()
            self.net_update()

            self.temp_update()
            
            self.animate(self.cpuList, self.ax1, self.canvas1, self.cpustyle)
            self.animate(self.memList, self.ax2, self.canvas2, self.memstyle)
            self.animate(self.netList, self.ax3, self.canvas3, self.netstyle)
            Mupdate = Memory_Update()
            self.memPtable.setItemDelegate(Mupdate)
            Supdate = Swap_Update()
            self.swapTable.setItemDelegate(Supdate)

            gc.collect() 
                    
            return None 

        elif self.fanLabel.isVisible():

            self.time_update()
            self.cpu_update(PIDS, CPU)
            self.mem_update()
            self.net_update()

            self.temp_update()
            name,user,cpu,pids,memory,status = self.disk_update()

            self.animate(self.tempList, self.ax4, self.canvas4, self.tempstyle)
        
        if self.search_change:

            collection = [name,user,cpu,pids,memory,status]
            name,user,cpu,pids,memory,status = self.start_search(collection)

        try:
            clk = self.header_indx
            reverse = self.sorter
        except:
            clk = 2
            reverse = False

        if (clk==2) or (clk==4):

            if not reverse:
                reverse = True
            else:
                reverse = False
            
        sorted_lists = sorted(zip(name, user, cpu, pids, memory, status), reverse=reverse, key=lambda x: x[clk])
        name, user, cpu, pids, memory, status = [[x[i] for x in sorted_lists] for i in range(6)]

        if self.tableWidget.selectionModel().hasSelection():
                
            selModel = self.tableWidget.selectionModel()
            choice = selModel.selectedRows()

            if self.ptrack==0:
                collection = [name,user,cpu,pids,memory,status]
                name,user,cpu,pids,memory,status = self.stick_update(collection, choice)
            else:
                self.trail_update(choice)

        if self.fanLabel.isVisible():

            pids = self.Memstring2(pids)
            memory = self.Memstring2(memory)
            cpu = self.Memstring2(cpu)
            self.diskTable.setRowCount(len(name))

            collection = [name, status, user, cpu, memory, pids]
                    
            for i in range(6):
                for j in range(len(name)):
                    item_disk = QtWidgets.QTableWidgetItem()
                    self.diskTable.setItem(j, i, item_disk)
                    item_disk.setText(str(collection[i][j]))
                    del item_disk

            gc.collect()

            return None
        
        if self.memvis==1:
            memory = self.Memstring(memory)

        self.tableWidget.setRowCount(len(name))
        
        collection = [name, user, cpu, pids, memory, status]
                    
        for i in range(6):
            for j in range(len(name)):
                item_name = QtWidgets.QTableWidgetItem()
                item_name.setText(str(collection[i][j]))
                self.tableWidget.setItem(j, i, item_name)
                del item_name

        gc.collect()

class MyBar(QtWidgets.QWidget):

    def __init__(self, parent):
        super(MyBar, self).__init__()
        self.parent = parent
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.title = QtWidgets.QLabel("My Own Bar")

        btn_size = 16

        self.btn_close = QtWidgets.QPushButton("x")
        self.btn_close.clicked.connect(self.btn_close_clicked)
        self.btn_close.setFixedSize(btn_size, btn_size)
        self.btn_close.setFont(QtGui.QFont('Courier', 10))
        self.btn_close.setStyleSheet("QPushButton{background-color: #E95420;border-radius: 8px; Text-align:top;}\n"
"       QPushButton:hover {background-color: #F57C51}")

        self.btn_min = QtWidgets.QPushButton("\u2013")
        self.btn_min.clicked.connect(self.btn_min_clicked)
        self.btn_min.setFixedSize(btn_size, btn_size)
        self.btn_min.setFont(QtGui.QFont('Courier', 14))
        self.btn_min.setStyleSheet("QPushButton{background-color: rgb(129, 125, 121);border-radius: 8px; Text-align:bottom;}\n"
"       QPushButton:hover {background-color: rgb(190, 186, 182)}")

        self.title.setFixedHeight(35)
        self.title.setFixedWidth(820)
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.btn_min)
        self.layout.addWidget(self.btn_close)

        self.title.setStyleSheet("""
            background-color: rgb(86, 82, 78);
            color: white;
            border-top-right-radius: 10px;
            border-top-left-radius: 10px;
        """)
        self.setLayout(self.layout)

        self.start = QtCore.QPoint(0, 0)
        self.pressing = False

    def resizeEvent(self, QResizeEvent):
        super(MyBar, self).resizeEvent(QResizeEvent)
        self.title.setFixedWidth(820)

    def mousePressEvent(self, event):
        self.start = self.mapToGlobal(event.pos())
        self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing:
            self.end = self.mapToGlobal(event.pos())
            self.movement = self.end-self.start
            self.parent.setGeometry(self.mapToGlobal(self.movement).x(),
                                self.mapToGlobal(self.movement).y(),
                                self.parent.width(),
                                self.parent.height())
            self.start = self.end

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False

    def btn_close_clicked(self):
        self.parent.close()

    def btn_min_clicked(self):
        self.parent.showMinimized()

class QTableWidgetDisabledItem(QtWidgets.QItemDelegate):
            
    def __init__(self, parent):

        QtWidgets.QItemDelegate.__init__(self, parent)

                
    def paint(self, parent, option, index):
        if (int(index.column())>1) & (int(index.column())<5):
            option.displayAlignment = (QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        elif(int(index.column())<=1):
            option.displayAlignment = (QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        else:
            option.displayAlignment = (QtCore.Qt.AlignCenter|QtCore.Qt.AlignVCenter)
        QtWidgets.QItemDelegate.paint(self, parent, option, index)

    def createEditor(self, parent, option, index):
        item = QtWidgets.QLineEdit(parent)
        item.setStyleSheet("QLineEdit{color:rgb(255,255,255); background-color:rgb(48,140,198); selection-background-color:rgb(48,140,198); border: transparent;} QLineEdit:focus{color:rgb(0,0,0); background-color:rgb(173,236,230);}")
        item.setReadOnly(True)
        item.setEnabled(False)
        return item

    def setEditorData(self, editor, index):
        editor.blockSignals(True)
        editor.setText(index.model().data(index))
        editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text())

class QDiskTableDisabledItem(QtWidgets.QItemDelegate):
            
    def __init__(self, parent):

        QtWidgets.QItemDelegate.__init__(self, parent)

                
    def paint(self, parent, option, index):
        if (int(index.column())>2): 
            option.displayAlignment = (QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        else:
            option.displayAlignment = (QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        QtWidgets.QItemDelegate.paint(self, parent, option, index)

    def createEditor(self, parent, option, index):
        item = QtWidgets.QLineEdit(parent)
        item.setStyleSheet("QLineEdit{color:rgb(255,255,255); background-color:rgb(48,140,198); selection-background-color:rgb(48,140,198); border: transparent;} QLineEdit:focus{color:rgb(0,0,0); background-color:rgb(173,236,230);}")
        item.setReadOnly(True)
        item.setEnabled(False)
        return item

    def setEditorData(self, editor, index):
        editor.blockSignals(True)
        editor.setText(index.model().data(index))
        editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text())
                    
class Memory_Update(QtWidgets.QStyledItemDelegate):
    def __init__(self):
         QtWidgets.QStyledItemDelegate.__init__(self)

    def paint(self, painter, option, index):
        painter.save()
        ratio_left = (Memory_Update.mpercent/100.0)*0.235
        left_rect = QtCore.QRect(option.rect.left(), option.rect.top(),option.rect.width()*ratio_left, option.rect.height())
        left_brush = QtGui.QBrush(QtGui.QColor(159, 36, 37))
        painter.fillRect(left_rect, left_brush)
        painter.restore() 
        adjusted_option = option
        adjusted_option.backgroundBrush = QtGui.QBrush(QtCore.Qt.NoBrush)
        QtWidgets.QStyledItemDelegate.paint(self, painter, adjusted_option, index)

class Swap_Update(QtWidgets.QStyledItemDelegate):
    def __init__(self):
        QtWidgets.QStyledItemDelegate.__init__(self)

    def paint(self, painter, option, index):
        painter.save()
        ratio_left = (Swap_Update.spercent/100.0)*0.235
        left_rect = QtCore.QRect(option.rect.left(), option.rect.top(),option.rect.width()*ratio_left, option.rect.height())
        left_brush = QtGui.QBrush(QtGui.QColor(159, 36, 37))
        painter.fillRect(left_rect, left_brush)
        painter.restore() 
        adjusted_option = option
        adjusted_option.backgroundBrush = QtGui.QBrush(QtCore.Qt.NoBrush)
        QtWidgets.QStyledItemDelegate.paint(self, painter, adjusted_option, index)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    global ui
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()

    def myExitHandler():
        for id, thread in threading._active.items(): 
            try:
                thread.cancel()
            except:
                pass
    
    app.aboutToQuit.connect(myExitHandler)

    sys.exit(app.exec_()) 
