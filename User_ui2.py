# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'User_ui2.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
import os
import sys
import time
from client_fridkin import *
#from PyQt5.QtPdf import QPdfWidget
#from docx import Document
#from PIL import Image
#from io import BytesIO

try:
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'C:\Users\יונתן\AppData\Local\Programs\Python\Python310\Lib\site-packages\PyQt5\Qt5\plugins'
except:
    pass


class Ui_MainWindow(object):
    def __init__(self):
        self.data = ""
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(240, 10, 421, 20))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(640, 60, 91, 20))
        self.label_2.setObjectName("label_2")
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.clicked.connect(lambda: self.upload_clicked(MainWindow, 1))
        self.pushButton.setGeometry(QtCore.QRect(210, 530, 371, 23))
        self.pushButton.setObjectName("pushButton")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(640, 110, 91, 20))
        self.label_3.setObjectName("label_3")
        self.textBrowser = QtWidgets.QTextBrowser(self.centralwidget)
        self.textBrowser.setGeometry(QtCore.QRect(530, 150, 256, 331))
        self.textBrowser.setObjectName("textBrowser")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(60, 110, 91, 20))
        self.label_4.setObjectName("label_4")
        self.textBrowser_2 = QtWidgets.QTextBrowser(self.centralwidget)
        self.textBrowser_2.setGeometry(QtCore.QRect(5, 150, 271, 331))
        self.textBrowser_2.setObjectName("textBrowser_2")
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setGeometry(QtCore.QRect(640, 490, 161, 20))
        self.label_5.setObjectName("label_5")
        
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setGeometry(QtCore.QRect(640, 520, 113, 20))
        self.lineEdit.setText("")
        self.lineEdit.setObjectName("lineEdit")
        self.lineEdit.returnPressed.connect(self.handle_input_text1)
        
        self.label_6 = QtWidgets.QLabel(self.centralwidget)
        self.label_6.setGeometry(QtCore.QRect(10, 490, 121, 20))
        self.label_6.setObjectName("label_6")
        
        self.lineEdit_2 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_2.setGeometry(QtCore.QRect(10, 520, 113, 20))
        self.lineEdit_2.setObjectName("lineEdit_2")
        self.lineEdit_2.returnPressed.connect(self.handle_input_text2)
        
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label.setText(_translate("MainWindow", "Python Project - Torrent Web - Yonathan Fridkin"))
        self.label_2.setText(_translate("MainWindow", "Active Clients: "))
        self.pushButton.setText(_translate("MainWindow", "Upload a File"))
        self.label_3.setText(_translate("MainWindow", "Files Uploaded:"))
        self.label_4.setText(_translate("MainWindow", "Files received:"))
        self.label_5.setText(_translate("MainWindow", "Insert file to view:"))
        self.label_6.setText(_translate("MainWindow", "Insert file to complete:"))

    def update_data(self, active_clients, files_uploaded, shared_files):
        """
        Update the data
        files uploaded -> list of all files shared and files that have been fully completed
        shared files -> files that are currently in parts. short names
        """  
        _translate = QtCore.QCoreApplication.translate
        self.label_2.setText(_translate("MainWindow", f"Active Clients: {active_clients}"))
        self.textBrowser.clear()
        self.textBrowser_2.clear() # first clear the text browsers, then write to them the data
        for file in files_uploaded:
            self.textBrowser.append(file[0].split('\\')[-1])
        for file in shared_files:
            self.textBrowser_2.append(file)

    def handle_input_text1(self):
        print("inside the view function")
        text = self.lineEdit.text()
        self.data = f"view {text}" 
        self.lineEdit.clear()

    def handle_input_text2(self):
        print("inside the parts function")
        text = self.lineEdit_2.text()
        self.data = f"parts {text}" 
        self.lineEdit_2.clear()

    def upload_clicked(self, a,b):
        file_name = QFileDialog.getOpenFileName(a,"Select File", "", "All Files (*)")
        if file_name:
            self.data = f"share {file_name[0]}" 
            print("the path is")
            print(file_name[0])
            parts = file_name[0].split('\n')
            print("parts")
            print(parts)
    
    def get_data(self):
        return self.data   

    def relapse_data(self):
        self.data = ""    

    def view(self,file_name, all_files):
        """
        Create a new window to view a file
        file name -> abbreviated form of file path -> test.txt
        """ 
        # path = "" # path of file, needs to be determined
        # for file in all_files:
        #     if file_name in all_files: path = file_name
        # print("the path of the selected file is")
        # print(path)   
        # f = open(r'{}'.format(path), 'r')
        # data = f.read()
        # app = QtWidgets.QApplication(sys.argv)
        # MainWindow = QtWidgets.QMainWindow()    


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
