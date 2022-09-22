from PyQt5 import QtGui
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QComboBox, QPushButton,QHBoxLayout,QVBoxLayout,QGroupBox, QLineEdit,QTextEdit
from PyQt5.QtGui import QPixmap
import sys
from click import pass_context
import cv2
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread,QPoint
import numpy as np
import time, datetime
import subprocess, os, signal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QFont, QImage

object_types = ["kapton strip","bridge", "pigtail","FEH","SEH","hybrid","skeleton","module","other"]

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

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.failed = False

    def run(self):
        # capture from web cam
        cap = cv2.VideoCapture(0)
        self.failed = False
        self._run_flag = True
        while self._run_flag:
            while not cap.isOpened():
                time.sleep(0.1)
                cap = cv2.VideoCapture(0)
            ret, cv_img = cap.read()
            if ret == 0 and not self.failed:
                self.failed = True
                print("No input...")
                print(self._run_flag)
            if ret:
                self.failed = False
                self.change_pixmap_signal.emit(cv_img)
        print("Exiting...")
        # shut down capture system
        cap.release()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        print("Stopping liveview (?)")
        self._run_flag = False
        self.failed=False
        self.wait()
        print("Done")

class StreamThread(QThread):

    def __init__(self):
        super().__init__()
        self.run_flag = False

    def run(self):
        self.run_flag = True
        #self.pro = subprocess.Popen("gphoto2 --stdout --capture-movie | ffmpeg -i - -vcodec rawvideo -pix_fmt yuv420p -threads 0 -f v4l2 /dev/video0",shell=True)
        self.p1 = subprocess.Popen(["gphoto2", "--stdout", "--capture-movie"],stdout=subprocess.PIPE)
        self.p2 = subprocess.Popen("ffmpeg -i - -vcodec rawvideo -pix_fmt yuv420p -threads 0 -f v4l2 /dev/video0",shell=True, stdin=self.p1.stdout)
    

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""

        # out = subprocess.check_output(['ps', '-Aefj'])
        # for line in out.splitlines():
        #     line=line.decode("utf-8")
        #     print(line)
        #     if "streaming.py" in str(line):
        #         l = line.split(" ")
        #         while "" in l:
        #             l.remove("")
        #         # Get sid and pgid of child process (/bin/sh)
        #         sid = os.getsid(self.pro.pid)
        #         pgid  = os.getpgid(self.pro.pid)
        #         #only true for target process
        #         if l[4] == str(sid) and l[3] != str(pgid):
        #             os.kill(sid, signal.SIGINT)
        self.p1.terminate()
        self.p2.terminate()
        print("Done")
        #os.killpg(os.getpgid(self.pro.pid), signal.SIGTERM)  # Send the signal to all the process groups
        #self.pro.send_signal(signal.SIGTERM)

        self.run_flag = False

class TakePictureThread(QThread):

    def __init__(self,upper):
        super().__init__()
        self.upper = upper

    def run(self):
        time.sleep(0.5)
        f_name = datetime.datetime.now().strftime("%Y%d%m_%H%M%S")
        self.timestamp = time.time()

        file_name = f"{f_name}.jpeg"
        if file_name in os.listdir(temp_dir):
            suffix = 0    
            while file_name in os.listdir(temp_dir):
                file_name = f"{f_name}_{suffix}.jpeg"
                suffix+=1
        print(file_name)
        
        os.system(f"gphoto2 --wait-event=1s --capture-image-and-download ")
        os.system(f"mv capt0000.jpg {temp_dir}/{file_name}")
        self.upper.stream_thread.start()
        self.upper.thread.start()

        self.upper.store_picture_button.setEnabled(1)
        self.upper.view_picture_button.setEnabled(1)
        self.upper.last_picture = temp_dir+"/"+file_name
        self.upper.file_name_widget.setText(self.upper.last_picture)
        self.upper.pause_stream = False
        self.stop()

    def stop(self):
        print("Done")
        
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
        # self.textLabel = QLabel('Webcam')
        self.timestamp = 0
        # create a vertical box layout and add the two labels
        hbox = QHBoxLayout()
        hbox.addWidget(self.image_label)
        side_bar = QGroupBox()
        v_box = QVBoxLayout(side_bar)
        hbox.addWidget(side_bar)
        self.title_label = QLabel("Actions")
        self.title_label.setFixedWidth(400)

        v_box.addWidget(self.title_label)
        # v_box.addWidget(button_creator("Start interface", self.start_interface))
        v_box.addWidget(button_creator("Take picture"   , self.take_picture))
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
        self.thread = VideoThread()
        # connect its signal to the update_image slot
        self.thread.change_pixmap_signal.connect(self.update_image)


        self.take_picture_thread = TakePictureThread(self)

        self.stream_thread = StreamThread()
        self.start_interface()
        self.title_label.resize(400, 50)

    def draw_bkg(self,text = ""):
        if text != "":
            print(f"Background : {text}")
            img_copy = self.default_img.copy()
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(img_copy, text, (50,450), font, 3, (100, 0, 0), 2, cv2.LINE_AA)
            self.image_label.setPixmap(self.convert_cv_qt(img_copy))
            self.image_label.repaint()
        else:
            self.image_label.setPixmap(self.convert_cv_qt(self.default_img))
            self.image_label.repaint()


    def closeEvent(self, event):
        self.thread.stop()
        self.stream_thread.stop()
        event.accept()

    def start_interface(self):
        self.stream_thread.start()
        self.thread.start()

    def store_picture(self):
        # Adding line to csv file:
        output_file = self.last_picture.replace(temp_dir,storage_dir)
        line = f"{self.timestamp};{self.type_selector.currentText()};{sanitize(self.part_name.text())};{sanitize(self.user_comment.toPlainText())}; {output_file}\n"
        print(line)
        with open(temp_db, 'a') as f:
            f.write(line)
        os.system(f"mv {self.last_picture} {output_file}")

        #Upload to db here

        
        self.timestamp = 0
        self.last_picture = None
        self.store_picture_button.setDisabled(1)
        self.view_picture_button.setDisabled(1)
        self.file_name_widget.setText("")
        print("Done!")

    def open_picture(self):
        print("Opening picture!")
        os.system(f"gwenview {self.last_picture} &")

    def take_picture(self):
        try:
            self.stream_thread.stop()
        except:
            print("Error {e}")
        try:
            self.thread.stop()
        except:
            print("Error {e}")
            
        self.take_picture_thread.start()
        self.pause_stream = True
        self.draw_bkg("Taking picture...")
        # time.sleep(1)
        # f_name = datetime.datetime.now().strftime("%Y%d%m_%H%M%S")

        # self.timestamp = time.time()

        # file_name = f"{f_name}.jpeg"
        # if file_name in os.listdir(temp_dir):
        #     suffix = 0    
        #     while file_name in os.listdir(temp_dir):
        #         file_name = f"{f_name}_{suffix}.jpeg"
        #         suffix+=1
        # print(file_name)
        
        # os.system(f"gphoto2 --wait-event=2s --capture-image-and-download ")
        # os.system(f"mv capt0000.jpg {temp_dir}/{file_name}")
        # self.stream_thread.start()
        # self.thread.start()

        # self.store_picture_button.setEnabled(1)
        # self.view_picture_button.setEnabled(1)
        # self.last_picture = temp_dir+"/"+file_name
        # self.file_name_widget.setText(self.last_picture)


    
    # def take_picture(self):
    #     try:
    #         self.stream_thread.stop()
    #         self.thread.stop()
    #     except:
    #         pass
    #     time.sleep(1)
    #     os.system(f"gphoto2 --wait-event=2s --capture-image-and-download ")
    #     self.stream_thread.start()
    #     self.thread.start()
    
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