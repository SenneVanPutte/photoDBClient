import sys
import cv2
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread,QPoint, QBuffer
import numpy as np
import time, datetime
import subprocess, os, signal
import IIHEPhotoDB

from PIL import Image
from pylibdmtx.pylibdmtx import decode


videoId     = 0

temp_dir    = "/tmp/"
storage_dir = "./storage/"
temp_db     = "./storage/database.csv"

def get_summary():
    try:
        output = subprocess.check_output(['gphoto2', '--summary'])

    except Exception as e:
        output = f"{e}"
    print(output)
    return output




class Capture(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.failed = False

    def run(self):
        # capture from web cam
        cap = None
        self.failed = False
        self._run_flag = True
        while self._run_flag:
            while cap == None or not cap.isOpened() and self._run_flag:
                time.sleep(0.1)
                cap = cv2.VideoCapture(videoId)
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
        print("Stopping liveview...")
        self._run_flag = False
        self.failed=False
        self.wait()
        print("Liveview stopped!")


class Stream(QThread):

    def __init__(self):
        super().__init__()
        self.run_flag = False

    def run(self):
        self.run_flag = True
        # pro = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
        #                shell=True) 


        # Send the signal to all the process group
        # self.p1 = subprocess.Popen(f"gphoto2 --stdout --capture-movie | ffmpeg -i - -vcodec rawvideo -pix_fmt yuv420p -threads 0 -f v4l2 /dev/video{videoId}", shell=True, preexec_fn=os.setsid)
        self.p1 = subprocess.Popen(["gphoto2", "--stdout", "--capture-movie"],stdout=subprocess.PIPE, preexec_fn=os.setsid)
        self.p2 = subprocess.Popen(f"ffmpeg -i - -vcodec rawvideo -pix_fmt yuv420p -threads 0 -f v4l2 /dev/video{videoId}",shell=True, stdin=self.p1.stdout, preexec_fn=os.setsid)


    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        try:
            # Send two Ctrl-C cmds...
            print("Sending Ctrl-C")
            # os.killpg(os.getpgid(self.p1.pid), signal.SIGTERM) 
            # os.killpg(os.getpgid(self.p2.pid), signal.SIGTERM) 
            # self.p1.terminate()
            # os.killpg(os.getpgid(self.p1.pid), signal.SIGTERM)
            self.p1.terminate()
            time.sleep(0.2)
            self.p2.terminate()
            # time.sleep(0.5)
            # self.p1.terminate()
            print("Waiting")
            self.wait()
            print("Done waiting")
            self.run_flag = False
            print("Done stopping video capture")

        except Exception as e:
            print("Error, unable to stop capture thread!")
            print(e)

class Command(QThread):
    restart_streaming = pyqtSignal()
    process_file      = pyqtSignal()
    def __init__(self, command):
        super().__init__()
        self.command = command
        self.running = True

    def run(self):
        os.system(self.command)
        time.sleep(0.5)
        print(self.command)
        if "download" in self.command:
            self.process_file.emit()
        self.stop()

    def stop(self):
        self.restart_streaming.emit()
        self.running = False
        print("Done")

class ManualFocus(QThread):
    cmd_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        print("Starting manual focus")
        self.cmd_signal.emit("stop_streaming")
        self.cmd_signal.emit("draw_bkg Stopping the stream...")
        time.sleep(3)
        self.cmd_signal.emit("draw_bkg Focussing ...")
        os.system("gphoto2 --wait-event 2s --set-config viewfinder=1 --set-config /main/actions/autofocusdrive=1 --wait-event=10s")
        self.cmd_signal.emit("draw_bkg Done Focussing!")
        # time.sleep(2)
        self.cmd_signal.emit("start_streaming")
        # print("Done manual focus")
        self.running = False

class ManualPicture(QThread):
    cmd_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        self.cmd_signal.emit("stop_streaming")
        time.sleep(0.5)
        self.cmd_signal.emit("draw_bkg Manual capture...")
        os.system("gphoto2 --wait-event 1s --set-config eosremoterelease=Immediate --set-config eosremoterelease='Release Full' --wait-event-and-download=2s")
        self.cmd_signal.emit("start_streaming")
        time.sleep(1)
        self.cmd_signal.emit("process_picture")
        print("Done manual picture")
        self.running = False



class TakePicture(QThread):
    cmd_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        self.cmd_signal.emit("stop_streaming")
        time.sleep(0.3)
        # self.cmd_signal.emit("draw_bkg Getting summary...")
        print(get_summary())
        # time.sleep(0.5)
        self.cmd_signal.emit("draw_bkg Taking picture...")
        os.system(f"gphoto2 --wait-event=1s --capture-image-and-download ")
        # time.sleep(0.5)
        self.cmd_signal.emit("draw_bkg restarting streaming...")
        self.cmd_signal.emit("start_streaming")
        # self.cmd_signal.emit("draw_bkg Done!")

        time.sleep(1)
        self.cmd_signal.emit("process_picture")
        self.cmd_signal.emit("unlock_interface")
        self.running = False
        self.stop()

    def stop(self):
        print("Done")

class QRAnalyzer(QThread):
    cmd_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.running = True


    def run(self):
        print("Opening file...")
        self.img = Image.open('IMG_8483.JPG')
        # for i in [10,5,2,1]:
        #     self.get_QR(i)
        self.get_QR(1)
        self.running = False
        

    def get_QR(self,scale_factor):
        # buffer = QBuffer()
        # buffer.open(QBuffer.ReadWrite)
        # self.label.full_img.save(buffer, "PNG")
        # img = Image.open(io.BytesIO(buffer.data()))

        print(f"Rescaling... {scale_factor}")
        img_scaled = self.img.resize((int(6000/scale_factor),int(4000/scale_factor)))
        # thresh = 200
        # fn = lambda x : 255 if x > thresh else 0
        # img_scaled = img_scaled.convert("L").point(fn, mode='L')
        
        # img_scaled = img.crop((min(x_0,x_1), min(y_0,y_1), max(x_0,x_1), max(y_0,y_1)))

        #qImage = ImageQt(img_scaled)
        #pixmap = QPixmap.fromImage(qImage)
        #self.label.setPixmap(pixmap)
        #self.label.updateImg = False
        img_scaled.show()
        print("decoding")
        data = decode(img_scaled)
        print(data)
class StorePicture(QThread):

    cmd_signal = pyqtSignal(str)
    def __init__(self,timestamp,object_type,object_id,module_id,comment,file_name):
        super().__init__()
        self.running = True
        self.timestamp = timestamp
        self.object_type = object_type
        self.object_id = object_id
        self.module_id = module_id
        self.comment = comment
        self.file_name = file_name

    def run(self):
        # Adding line to csv file:
        l0 = f"{self.file_name}"
        l1 = f"Connecting_to_db..."
        self.cmd_signal.emit(f"set_db_status_text {l0} {l1}")
        self.output_file = self.file_name.replace(temp_dir,storage_dir)
        line = f"{self.timestamp};{self.object_type};{self.object_id};{self.comment};{self.output_file}; {self.module_id}\n"
        tags = [self.object_id,self.module_id]
        with open(temp_db, 'a') as f:
            f.write(line)
        os.system(f"mv {self.file_name} {self.output_file}")

        try:
            db=IIHEPhotoDB.IIHEPhotoDB()
        except Exception as e:
            print(f"Cannot connect to DB : {e}\n")
        else:
            self.cmd_signal.emit(f"set_db_status_text {l0} connected_to_db...")
            cat_exist=0
            cat_list=db.getListOfFolder()
            folder_Name=self.object_type
            for i in cat_list:
                cell_list=i.split(" - ")
                if(cell_list[1]==folder_Name):
                    cat_id = cell_list[0]
                    cat_exist=1
            if(cat_exist==0):
                print("New Folder creating...")
                self.cmd_signal.emit(f"set_db_status_text {l0} creating_folder...")
                cat_id = db.createFolder(folder_Name)
            self.cmd_signal.emit(f"set_db_status_text {l0} uploading_to_db...")
            db.uploadImage(self.output_file, cat_id, tags,self.comment)

        self.cmd_signal.emit(f"set_db_status_text {l0} done!")
        time.sleep(2)
        self.cmd_signal.emit(f"set_db_status_text")
        self.running = False
        

