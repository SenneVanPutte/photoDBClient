from PyQt5 import QtGui
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QComboBox, QPushButton,QHBoxLayout,QVBoxLayout,QGroupBox, QLineEdit,QTextEdit
from PyQt5.QtGui import QPixmap
import sys
import cv2
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread,QPoint
import numpy as np
import time, datetime
import subprocess, os, signal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QFont, QImage
import IIHEPhotoDB
import gui_threads



object_types = ["sensor","kapton strip","bridge", "pigtail","FEH","SEH","hybrid","skeleton","module","other"]


temp_dir    = "/tmp/"
storage_dir = "./storage/"
temp_db     = "./storage/database.csv"

def button_creator(name, action, set_width = -1):
    button = QPushButton(name)
    button.clicked.connect(action)
    if set_width > 0:
        button.setFixedWidth( set_width )
    return button

def sanitize(input_txt):
    output_txt = input_txt.replace("\n","\\n")
    output_txt = output_txt.replace(";"," ")
    return output_txt


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IIHE camera stand")
        self.disply_width = 1280
        self.display_height = 848
        # create the label that holds the image
        self.image_label = QLabel(self)
        self.image_label.resize(self.disply_width, self.display_height)

        #Default image...
        self.default_img = cv2.imread('default_img.jpg', 1)
        self.draw_bkg("Starting camera...")
        self.pause_stream = False
        # create a text label
        self.timestamp = 0
        # create a vertical box layout and add the two labels
        hbox = QHBoxLayout()
        hbox.addWidget(self.image_label)
        side_bar = QGroupBox()
        v_box = QVBoxLayout(side_bar)
        hbox.addWidget(side_bar)
        self.title_label = QLabel("Actions")
        self.title_label.setFixedWidth(400)
        self.cmd_thread = None

        v_box.addWidget(self.title_label)
        v_box.addWidget(button_creator("Take picture"   , self.take_picture))
        v_box.addWidget(button_creator("Take manual picture", self.manual_picture))
        v_box.addWidget(button_creator("Trigger focus", self.trigger_focus))
        
        self.view_picture_button = button_creator("View picture"  , self.open_picture)
        v_box.addWidget(self.view_picture_button)
        self.store_picture_button = button_creator("Store picture"  , self.store_picture)
        v_box.addWidget(self.store_picture_button)
        self.store_picture_button.setDisabled(1)
        self.view_picture_button.setDisabled(1)

        v_box.addWidget(QLabel("Meta-data"))
        v_box.addWidget(QLabel("Type : "))
        self.type_selector = QComboBox()
        for ot in object_types:
            self.type_selector.addItem(ot)

        v_box.addWidget(self.type_selector)
        v_box.addWidget(QLabel("Part ID:"))
        self.part_name = QLineEdit("")
        v_box.addWidget(self.part_name)
        v_box.addWidget(QLabel("User Comment:"))
        self.user_comment = QTextEdit("")
        v_box.addWidget(self.user_comment)
        v_box.addWidget(QLabel("Local file:"))
        self.file_name_widget = QLabel()
        v_box.addWidget(self.file_name_widget)

        # set the vbox layout as the widgets layout
        self.setLayout(hbox)

        # create the video capture thread
        self.thread = gui_threads.Capture()
        # connect its signal to the update_image slot
        self.thread.change_pixmap_signal.connect(self.update_image)

        # self.take_picture_thread = gui_threads.TakePicture(self)

        self.stream_thread = gui_threads.Stream()
        self.start_streaming()
        self.title_label.resize(400, 50)
        self.streams = []
        self.methods = [func for func in dir(self) if callable(getattr(self, func))]

    def launch_stream(self,streamObj):
        for index,ss in enumerate(reversed(self.streams)):
            if type(ss) == type(streamObj):
                print("Already found a stream of that type...")
                if not ss.running:
                    print("Stream is no longer running, deleting it.")
                    self.streams.pop(-index-1)
                else:
                    print("Error, stream still running! Ignoring new stream request")
                    return

        self.streams.append(streamObj)
        streamObj.cmd_signal.connect(self.process_cmd)
        streamObj.start()

    def process_cmd(self,cmd_str):
        cmd = cmd_str.split(" ")
        args = []
        if len(cmd) > 1:
            args = cmd[1:]
        cmd = cmd[0]
        print(f"Received command : {cmd}, {args}")
        if cmd in self.methods:
            print(f"Launching method {cmd} with arguments {args}")
            getattr(self, cmd)(*args)
        else:
            print(f"{cmd} is not a method...")

    def draw_bkg(self,*text):
        tt = " ".join(text)
        if text != None:
            print(f"Background : {tt}")
            img_copy = self.default_img.copy()
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(img_copy, tt, (50,450), font, 3, (100, 0, 0), 2, cv2.LINE_AA)
            self.image_label.setPixmap(self.convert_cv_qt(img_copy))
            self.image_label.repaint()
        else:
            self.image_label.setPixmap(self.convert_cv_qt(self.default_img))
            self.image_label.repaint()

    def trigger_focus(self):
        self.launch_stream(gui_threads.ManualFocus())

    def stop_streaming(self):
        self.pause_stream = True
        print("Stop streaming 1/3")
        try:
            self.stream_thread.stop()
        except Exception as e:
            print(f"Error {e}")
        print("Stop streaming 2/3")
        try:
            self.thread.stop()
        except Exception as e:
            print(f"Error {e}")
        print("Stop streaming 3/3")
        try:
            self.stream_thread.stop()
        except Exception as e:
            print(f"Error {e}")
        print("Done stop streaming")

    def process_picture(self):
        f_name = datetime.datetime.now().strftime("%Y%d%m_%H%M%S")
        self.timestamp = time.time()

        file_name = f"{f_name}.jpeg"
        if file_name in os.listdir(temp_dir):
            suffix = 0
            while file_name in os.listdir(temp_dir):
                file_name = f"{f_name}_{suffix}.jpeg"
                suffix+=1
        os.system(f"mv capt0000.jpg {temp_dir}/{file_name}")
        self.last_picture = temp_dir+"/"+file_name
        self.file_name_widget.setText(self.last_picture)
        self.store_picture_button.setEnabled(1)
        self.view_picture_button.setEnabled(1)



    def start_streaming(self,param=""):
        self.stream_thread.start()
        self.thread.start()
        self.pause_stream = False

    def manual_picture(self):
        self.launch_stream(gui_threads.ManualPicture())

    def unlock_interface(self):
        self.store_picture_button.setEnabled(1)
        self.view_picture_button.setEnabled(1)

    def closeEvent(self, event):
        self.thread.stop()
        self.stream_thread.stop()
        event.accept()


    def store_picture(self):
        # Adding line to csv file:
        output_file = self.last_picture.replace(temp_dir,storage_dir)
        line = f"{self.timestamp};{self.type_selector.currentText()};{sanitize(self.part_name.text())};{sanitize(self.user_comment.toPlainText())}; {output_file}\n"
        print(line)
        with open(temp_db, 'a') as f:
            f.write(line)
        os.system(f"mv {self.last_picture} {output_file}")
        try:
            db=IIHEPhotoDB.IIHEPhotoDB()
        except Exception as e:
            print("Cannot connect to DB\n")
        else:
            cat_exist=0
            cat_list=db.getListOfFolder()
            folder_Name=self.type_selector.currentText()
            for i in cat_list:
                cell_list=i.split(" - ")
                if(cell_list[1]==folder_Name):
                    cat_id = cell_list[0]
                    cat_exist=1
            if(cat_exist==0):
                print("New Folder creating...")
                cat_id = db.createFolder(folder_Name)
            db.uploadImage(output_file, cat_id, line)

        #Upload to db here

        self.timestamp = 0
        self.last_picture = None
        self.store_picture_button.setDisabled(1)
        self.view_picture_button.setDisabled(1)
        self.file_name_widget.setText("")
        print("Done!")

    def open_picture(self):
        os.system(f"eog {self.last_picture} &")

    def take_picture(self):
        self.launch_stream(gui_threads.TakePicture())

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        if self.pause_stream == True:
            return
        """Updates the image_label with a new opencv image"""
        qt_img = self.convert_cv_qt(cv_img)
        self.image_label.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.disply_width, self.display_height, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)



if __name__=="__main__":
    app = QApplication(sys.argv)
    a = App()
    a.show()
    sys.exit(app.exec_())
