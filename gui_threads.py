import sys
import cv2
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread,QPoint
import numpy as np
import time, datetime
import subprocess, os, signal

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
        cap = cv2.VideoCapture(videoId)
        self.failed = False
        self._run_flag = True
        while self._run_flag:
            while not cap.isOpened() and self._run_flag:
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
            # self.p1.kill()
            # self.p2.terminate()
            time.sleep(0.5)
            self.p1.terminate()
            time.sleep(0.5)
            self.p2.terminate()
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
        self.cmd_signal.emit("draw_bkg Manual capture...")
        time.sleep(3)
        os.system("gphoto2 --wait-event 2s --set-config eosremoterelease=Immediate --set-config eosremoterelease='Release Full' --wait-event-and-download=2s")
        self.cmd_signal.emit("start_streaming")
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
        time.sleep(0.1)
        self.cmd_signal.emit("draw_bkg Stopping the stream...")
        time.sleep(2)
        self.cmd_signal.emit("draw_bkg Getting summary...")
        get_summary()
        time.sleep(2)
        self.cmd_signal.emit("draw_bkg Taking picture...")
        os.system(f"gphoto2 --wait-event=2s --capture-image-and-download ")
        time.sleep(2)
        self.cmd_signal.emit("start_streaming")
        self.cmd_signal.emit("draw_bkg restarting streaming...")
        # self.cmd_signal.emit("draw_bkg Done!")
        self.cmd_signal.emit("unlock_interface")

        time.sleep(5)
        self.cmd_signal.emit("process_picture")
        self.running = False
        self.stop()

    def stop(self):
        print("Done")
