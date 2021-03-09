# Run if not on zumi
import os
import rpyc
import numpy as np
import pandas as pd
import time
import math
from datetime import datetime
import matplotlib.pyplot as plt
import cv2
from Position import Position

rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True

from PIL import Image
class Zumi(object):
    def __init__(self,direction,port,ip = 'keuper-labs.org'):
        rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True
        self.Messwerte = None
        self.IP = ip
        self.Port = port
        conn = rpyc.connect(ip,port)
        self.zumi = conn.root
        self.directory = "Zumi_{}".format(port-9000)
        Number = int(int(self.Port)-9000)
        self.position = Position(Number,direction)
        try:
            os.stat(self.directory)
        except:
            os.mkdir(self.directory) 
        self.directory_two = "{}/Data_from_{}".format(self.directory,datetime.now().strftime("%m-%d-%Y"))
        try:
            os.stat(self.directory_two)
        except:
            os.mkdir(self.directory_two)
        self.csv_name = "{}/IR_from_{}.csv".format(self.directory_two,datetime.now().strftime("%H-%M-%S"))
        #self.csv_name = "{}/IR_from_{}.csv".format(self.directory,datetime.now().strftime("%H-%M-%S"))
        print("Zumi Initialised")
        
    def ping(self):
        return self.zumi.ping()
    def get_all_IR_data(self):
        Spaltennamen = ['year','month','day','hour','minute','second','front right','bottom right','back right','bottom left','back left','front left']
        now = datetime.now()
        time = [now.date().year,now.date().month,now.date().day,now.time().hour,now.time().minute,now.time().second]
        data = list(self.zumi.get_all_IR_data())
        time.extend(data)
        NeueZeile=pd.DataFrame([time], columns=Spaltennamen)
        for column in NeueZeile.columns:
            NeueZeile[column] = NeueZeile[column].astype('int16')
        if self.Messwerte is None:
            self.Messwerte = NeueZeile
            self.Messwerte.to_csv(self.csv_name,index=False)
        else:
            self.Messwerte = self.Messwerte.append(NeueZeile)
            NeueZeile.to_csv(self.csv_name,index=False,mode = 'a')
        return data
    def get_picture(self):
        frame = self.zumi.get_picture()
        jpg_name = "{}/Zumicam_{}.jpeg".format(self.directory_two,datetime.now().strftime("%H-%M-%S"))
        #jpg_name = "Zumicam_{}.jpeg".format(datetime.now().strftime("%H-%M-%S"))
        cv2.imwrite(jpg_name,img=np.array(frame))
        return frame
    def get_pos_and_dir(self):
        x = self.position.last_x
        y = self.position.last_y
        pos = [x,y]
        return pos, self.position.direction
    def calc_pos_and_dir(self):
        pos, direction = self.position.calc_current_position()
        return pos, direction
    def get_Sensors(self,recalculate_direction = False):
        frame = self.get_picture()
        data = self.get_all_IR_data()
        if recalculate_direction:
            pos, direction = self.calc_pos_and_dir()
        else:
            pos, direction = self.get_pos_and_dir()
        return frame, data, pos, direction
    def forward(self,speed=40,duration=1.0,correction = 4,repeat = 1,check_clearance = True):
        path_clear = True
        dist = self.get_distance_for_duration(duration*repeat,speed)
        end_point = self.position.predict_point_from_current_position(dist)
        self.position.set_prediction(end_point[0],end_point[1])
        if check_clearance:
            path_clear = self.position.check_path_in_front(dist)
        if(path_clear):
            for i in range(0,repeat):
                if correction != 0 :
                    self.turn(angle = correction, update_the_direction=False)
                self.zumi.forward(speed=speed,duration=duration)
            print("Zumi Forward")
        else:
            print("Obstacle in Path!")
        self.get_Sensors(recalculate_direction = True)
        return path_clear        
    def reverse(self,speed = 20):
        self.zumi.go_reverse(speed = speed)
        print("Zumi Reverse")
        self.get_Sensors(recalculate_direction = True)
        return

    def turn(self,angle,repeat=1,duration = 1.0,update_the_direction = True):
        if(angle<0):
            turn_left((-angle),repeat=repeat,duration = duration,update_the_direction = update_the_direction)
        else:
            turn_right(angle,repeat=repeat,duration = duration,update_the_direction = update_the_direction)
        return
    def turn_left(self,angle,repeat=1,duration = 1.0,update_the_direction = True):
        for i in range(0,repeat):
            if angle>90:
                duration = angle/90
            for i in range(0,repeat):
                self.zumi.turn_left(angle,duration = duration)
            print("Zumi Turn Left")
            if update_the_direction:
                self.position.update_direction((-angle))
            self.get_Sensors(recalculate_direction = False)
        return
    def turn_right(self,angle,repeat=1,duration = 1.0,update_the_direction = True):
        for i in range(0,repeat):
            if angle>90:
                duration = angle/90
            for i in range(0,repeat):
                self.zumi.turn_right(angle,duration = duration)
            print("Zumi Turn Right")
            if update_the_direction:
                self.position.update_direction(angle)
            self.get_Sensors(recalculate_direction = False)
        return
    def hard_brake(self):
        self.zumi.hard_brake()
        return
    def right_circle(self,speed=30, step=2):
        self.zumi.right_circle(speed, step)
        self.get_Sensors()
        return
    def left_circle(self,speed=30, step=2):
        self.zumi.left_circle(speed, step)
        self.get_Sensors()
        return
    def right_u_turn(self,speed=30, step=4, delay=0.02):
        self.zumi.right_u_turn(speed, step, delay)
        self.get_Sensors()
        return
    def left_u_turn(self,speed=30, step=4, delay=0.02):
        self.zumi.left_u_turn(speed, step, delay)
        self.get_Sensors()
        return
    def turn_towards(self,x,y):
        angle = self.position.calc_turnangle_towards(x,y)
        self.turn(angle)

    def get_duration_for_distance(self,distance,speed = 40):
        if(speed==40):
            duration = round(((distance+20)/130),1)
        else:
            duration = round(((distance+20)/130),1)
            print("calculation only for speed 40 possible")
        return duration
    def get_distance_for_duration(self,duration,speed = 40):
        if(speed==40):
            distance = 130*duration + 20
        else:
            distance = 130*duration + 20
            print("calculation only for speed 40 possible")
        return distance
    def drive_towards(self,x,y):
        self.turn_towards(x,y)
        distance = self.position.get_distance_to(x,y)
        duration = self.get_duration_for_distance(distance)
        self.forward(duration=duration,correction=4)
        distance = self.position.get_distance_to(x,y)
        return distance
    def drive_random(self,iterations = 30):
        for i in range(0,iterations):
            possible = self.forward()
            while not possible:
                angle = random.randint(-180,180)
                self.turn(angle)
                possible = self.forward()
        return
    

    def get_distance_to(self,x,y):
        return self.position.get_distance_to(x,y)
    def get_battery_percentage(self):
        battery_level = self.zumi.get_battery_percentage()
        print("Battery Percentage = {}".format(battery_level))
        return 
    def get_battery_voltage(self):
        battery_level = self.zumi.get_battery_voltage()
        print("Battery Voltage = {}".format(battery_level))
        return 
    

