import pygame
import time
import serial
import threading
import queue
import math

from joystick_functions import*
def foward_kinematics(joints): #left to implement
		pos = joints #placeholder
		return pos

def read_and_wait(ser, wait_time):
    #this function reads the information that the robot outputs to the computer and returns it as a string
    serString = "" # Used to hold data coming over UART
    output = ""
    flag = True
    start_time = time.time()
    while flag:
        # Wait until there is data waiting in the serial buffer
        if ser.in_waiting > 0:
            # Read data out of the buffer until a carriage return / new line is found
            serString = ser.readline()
            # Print the contents of the serial data
            try:
                output = output + serString.decode("Ascii")

            except:
                pass
        else:
            deltat = time.time() - start_time
            if deltat>wait_time:
                flag = False
    return output

def clean_buffer(ser):
    flag = True
    while flag:
        if ser.in_waiting > 0:
            ser.readline()          
        else:
            break   


class Robot():
	def __init__(self, joystick,FPS,info_computer_share=None,atHome=False, comPort='COM4', speedHigh=16, speedLow=8):
		#initialization of the robot class
		#this function opens the serial connection between the robot and the computer, defined the robot's speed % and calibrates the robot
		if not atHome:
			self.ser = serial.Serial(comPort, baudrate=9600, bytesize=8, timeout=2, parity='N', xonxoff=0) #change for lab ------------------------HERE FOR LAB
			print("COM port in use: {0}".format(self.ser.name))		
		else:
			self.ser=False
		
		self.define_initial_variables(info_computer_share,speedLow,speedHigh,joystick)
		self.info_computer_share['state'] = 0 #in calibration
		self.manual_mode ='J'

		self.go_to_initial_position()
		self.calculate_pos()
		self.update_bisturi_pos_shared()
		time.sleep(0.7)
		self.initial_manual_start(type=self.manual_mode)
		self.info_computer_share['state'] = 1 #robot is running

		""" while True:
			calibration_result = self.calibrate(FPS)
			if  calibration_result: #calibration finished successfully
				self.calibratedPos = self.pos
				break
			elif calibration_result ==False:#keyboard interrupt
				self.stop_program=True
				break
			else: 
				self.manual_end()
				print('Try calibration again')  """
		
	def go_to_initial_position(self):
		cartesian=['X','Y', 'Z', 'P', 'R']
		initial_pos=[0,0,0,0,0] #defined experimentally
		self.serial_write(b'DEFP A \r')
		for i, coordenate in  enumerate(initial_pos):	
			printToRobot=f'SETPVC A {cartesian[i]} {int(coordenate)}\r'
			self.serial_write(printToRobot.encode('utf-8'))
			time.sleep(0.2)
		self.serial_write(b'MOVE A 7000\r')
		time.sleep(8)


	def define_initial_variables(self, info_computer_share,speedLow,speedHigh,joystick  ):
		#for the function that shares information with other computer
		self.info_computer_share= info_computer_share 
			#List where self.sharedData[0] is the robot's calibration pos, self.sharedData[1] is the current position of the robot,
			#self.sharedData[2] is if joystick's square button state (to zero the coordenates shown on screen) 
		self.circle_Pressed = False 
		#Statements to use in the function update_speed
		self.speedLow = speedLow
		self.speed=self.speedHigh=speedHigh
		self.previousHighSpeed=True
		self.joystick = joystick
		self.x_Pressed=False
		self.tara_position =[0,0,0,0,0] #this is used to keep track of tara/zero 
		self.plan_to_cut_status =False
		self.triangle_Pressed = False 
		self.delta_cut=[0,0]
		self.stop_program=False

	def get_stop_program(self):
		return self.stop_program
	
	def get_serial(self):
		return self.ser

	def calibrate (self, FPS):	#function that is used to calibrate the robot in the begging of running the program
		CalibrationClock = pygame.time.Clock()
		print('Move the robot arm to the calibration position. Use the Joystick.\n', 'Click x when in calibration position')
		try:
			while True:
				# Handle events
				if pygame.event.peek(): #if there are events waiting in joystick queue
					axes, buttons, quit = get_joystick(self.joystick)
	
				if quit:
					return None #Calibration failed
				
				if buttons[0]: #x button pressed
					print('Calibration concluded with success')
					self.manual_end()
					self.calculate_pos()
					self.manual_start_midle()
					
					#self.sharedData[0]= self.calibratedPos = self.pos

					return True #Calibration ended
				
				self.manual_move(axes,buttons)
				CalibrationClock.tick(FPS)
		
		except KeyboardInterrupt:
			return False #Calibration Failed and exit program
		

	def initial_manual_start(self,  type='J',*speed):
		if not speed: #if speed argument is not given, use normal speed of robot
			speed=self.speed
		
		self.serial_write(b'\r')
		self.serial_write(b'~ \r')
		self.serial_write(b's \r')
		self.serial_write(f'{speed} \r'.encode('utf-8'))
		time.sleep(0.4)
		self.serial_write(f'{type} \r'.encode('utf-8'))
		time.sleep(0.2)

	def manual_start_midle(self, *speed):
		
		time.sleep(0.15)
		self.serial_write(b'\r')
		self.serial_write(b'~ \r')
		
		#time.sleep(0.05)

	def manual_end(self):
		self.serial_write(b'\r')
		#clean_buffer(serial)
		self.serial_write(b'~\r')
		time.sleep(0.05)
		self.serial_write(b'\r')

	
	def get_speed(self):
		return self.speed
	
	def update_speed(self, button_Is_Pressed):
		if self.x_Pressed and button_Is_Pressed: #x was pressed and still is - no changes to sensitivity
			return False
		elif not self.x_Pressed and button_Is_Pressed: #x was not pressed and now is pressed - change sensitivity from Low to high or High to low
			if not self.previousHighSpeed: #robot was previously with low speed - and will now have high speed
				self.manual_end()
				time.sleep(0.1)
				self.speed=self.speedHigh
				self.manual_mode = 'J'
				self.initial_manual_start(type = self.manual_mode)

				self.previousHighSpeed = True
				self.joystick.rumble(0.1, 1, 100)
				self.info_computer_share['Speed']='Speed High'
				print('High speed')


			else: #robot was previously with high speed and will now have low speed
				self.manual_end()
				time.sleep(0.1)
				self.speed=self.speedLow
				self.manual_mode = 'X'
				self.initial_manual_start(type = self.manual_mode)

				self.previousHighSpeed = False
				self.joystick.rumble(1, 0.2, 100)
				self.info_computer_share['Speed']='Speed Low'
				print('Low speed')

			self.x_Pressed=True
			return True
		else: 
			self.x_Pressed=False #button is not pressed - prepare to change sensitivity when button is pressed again
			return False

	def tara(self, circleButton):
		if not circleButton: #circle is not pressed
			self.circle_Pressed=False 
			return

		if self.circle_Pressed and circleButton: #circe was pressed and still is - no changes
			return None
		elif not self.circle_Pressed and circleButton:  #circle was not pressed and now is pressed - send information of current pos
			self.manual_end()
			time.sleep(0.15)
			old_pos=self.pos
			print('self.Pos estimated',old_pos)
			self.calculate_pos()
			delta_pose=[old_pos[i]-self.pos[i] for i in range(len(self.pos))]
			print('Difference between estimation and pose', delta_pose)
			self.joystick.rumble(0.4, 0.4, 200)
			self.manual_start_midle()
			self.tara_position=self.pos
			self.update_bisturi_pos_shared()
			self.circle_Pressed=True                              



	def evaluate_triangle(self, triangleButtons):
		if not triangleButtons: #triangle is not pressed
			self.triangle_Pressed=False
			return

		if self.triangle_Pressed and triangleButtons: #triangle was pressed and still is - no changes
			return None
		elif not self.triangle_Pressed and triangleButtons:  #triangle was not pressed and now is pressed - change plan_to_cut status
			self.triangle_Pressed=True
			if self.plan_to_cut_status:
				self.plan_to_cut_status =False
				self.delta_cut =[0,0]
				self.joystick.rumble(0.8, 0.8, 100)
				self.info_computer_share['state'] = 1 #robot is running normally

			else:
				self.plan_to_cut_status =True
				self.joystick.rumble(0.8, 0.8, 400)
				self.info_computer_share['state'] = 2 #robot is preaparing for cut
				self.calculate_pos() #while comunication of state with other computer, calculate position - which will be used when cutting


	def set_point(self,prefix, ptNumber, deltasXYZRP):
		cartesian=['X','Y', 'Z', 'P', 'R']
		self.serial_write(f'HERE {prefix}[{ptNumber}]\r'.encode('utf-8'))
		for i, delta in enumerate(deltasXYZRP):
			if delta!=0:
				self.serial_write(f'SETPVC {prefix}[{ptNumber}] {cartesian[i]} {self.pos[i]+delta}\r'.encode('utf-8'))
				time.sleep(0.2)


	def set_path(self,prefix ):
		#POINT 1 - here
		deltasXYZRP=[0]*5
		self.set_point(prefix, 1, deltasXYZRP)
		time.sleep(0.2)
		#POINT 2 - tilt blade to 50 degrees
		deltasXYZRP[3]=[50-self.pos[3]]
		self.set_point(prefix, 2, deltasXYZRP)
		time.sleep(0.2)	
		#POINT 3- down
		deltasXYZRP[2]=-abs(self.delta_cut[1])
		self.set_point(prefix, 3, deltasXYZRP)
		time.sleep(0.2)	
		#POINT 4 - tilt blade to 75 degrees
		deltasXYZRP[3]=[75-self.pos[3]]
		self.set_point(prefix, 4, deltasXYZRP)
		time.sleep(0.2)				
		#POINT 5 - move in x 
		deltasXYZRP[0]=-abs(self.delta_cut[0])
		self.set_point(prefix, 5, deltasXYZRP)
		time.sleep(0.2)	
		#POINT 6 - move to orignal z position 
		deltasXYZRP[2]=0
		self.set_point(prefix, 6, deltasXYZRP)
		time.sleep(0.2)	
		#POINT 7 - move upwards, 5 cm away from gelatine
		deltasXYZRP[2]=500
		self.set_point(prefix, 7, deltasXYZRP)
		time.sleep(0.2)	


	def perform_cut(self):
		print('Preparing to cut')
		path_comands = []
		prefix='AA'
		nrpoints=7
		#creating an array of points
		self.serial_write(f"DELP {prefix}\r".encode('utf-8'))
		self.serial_write(b"YES\r")
		self.serial_write(f"DIMP {prefix}[{nrpoints}]\r".encode('utf-8'))
		time.sleep(0.5)
		#defining the coordinates of the array of points:
		self.set_path(prefix)		
		time.sleep(1)
		#move through all positions
		self.serial_write(f'MOVES {prefix} 1 {nrpoints} {200 * nrpoints}\r'.encode('utf-8'))
		print('Cutting')
		time.sleep(2*nrpoints)
		print('Finished cutting')

	def plan_to_cut(self, axes, buttons):
		if buttons[15]: #touchpad clicked
			self.joystick.rumble(0.6, 0.9, 800)
			self.info_computer_share['state'] = 3 #robot is cutting
			self.perform_cut()
			self.plan_to_cut_status =False
			self.info_computer_share['state'] = 1 #robot is running normally
			return
		
		sensitivity=2
		show=False

		if abs(axes[0])>0.4:#length of cut
			self.delta_cut[0]+=axes[2]*sensitivity
			show=True
		if abs(axes[3])>0.4: #depth
			self.delta_cut[1]+=axes[3]*sensitivity
			show=True

		""" if abs(axes[0])>0.3: #direction in degrees
			self.delta_cut[2]+= axes[0]*sensitivity
			show=True """			

		if show:
			print('Delta to cut ',self.delta_cut)
			self.info_computer_share['cutting_plan'] = self.delta_cut

	def iterate(self,axes,buttons ):
		self.evaluate_triangle(buttons[3]) #enter or exit plan to cut mode if triangle is pressed
		if self.plan_to_cut_status:
			self.plan_to_cut(axes, buttons)
		else:
			self.tara(buttons[1]) #tara/zero the position shown on screen
			_ = self.update_speed(buttons[0]) #change speed if x is pressed
			self.manual_move(axes, buttons)
		


	def manual_move(self, axes,buttons ):
		message= {'Q':0, '1':0,  'W':0,'2':0, 'E':0,'3':0,  'R':0,'4':0, 'T':0,'5':0,}

		if axes[0] < -0.2:
			self.serial_write(b'Q \r')
			message['Q']+=1

		elif axes[0] > 0.2:
			self.serial_write(b'1 \r')
			message['1']+=1

		if axes[1] < -0.2:
			self.serial_write(b'2 \r')
			message['2']+=1

		elif axes[1] > 0.2:
			self.serial_write(b'W \r')
			message['W']+=1

		if axes[2] < -0.2:
			self.serial_write(b'4 \r')
			message['4']+=1

		elif axes[2] > 0.2:
			self.serial_write(b'R \r')
			message['R']+=1

		if axes[3] < -0.2:
			self.serial_write(b'T \r')
			message['T']+=1

		elif axes[3] > 0.2:
			self.serial_write(b'5 \r')
			message['5']+=1
		
		if buttons[9] ==1:
			self.serial_write(b'3 \r')
			message['3']+=1
		
		elif buttons[10] ==1:
			self.serial_write(b'E \r') 
			message['E']+=1
		

		
		self.predict_next_pos(message)#update the self.pos info with an estimation, based on the input of manual movement
		self.update_bisturi_pos_shared()

	def predict_next_pos(self, message):
		deltas=[]
		deltas.append(message['Q']-message['1'])
		deltas.append(message['W']-message['2'])
		deltas.append(message['E']-message['3'])
		deltas.append(message['R']-message['4'])
		deltas.append(message['T']-message['5'])

		if self.manual_mode =='X':
			XYZ_sensitivity =[-4.725378787878788,
							-4.739024390243903,
							-4.646980255516841,
							-0.49864498644986455,
							3.0248419150858177] #from data
			for i in self.pos:
				self.pos[i]+=deltas[i]*XYZ_sensitivity[i]

		elif self.manual_mode =='J':
			J_sensitivity = 35.79 #from data
			pitch_sensitivity=69.275 #from data
			for i in self.joints:
				if i ==3:
					self.joints[i]+=deltas[i]*pitch_sensitivity
				else:
					self.joints[i]+=deltas[i]*J_sensitivity
			self.pos =foward_kinematics(self.joints)


	
	

	def update_bisturi_pos_shared(self):
		self.info_computer_share['last_bisturi_pos']=[self.pos[i]-self.tara_position[i] for i in range(len(self.pos))]


	def go_home(self):
		self.serial_write(b'home\r')
		time.sleep(180) # homing takes a few minutes ...
	
	def calculate_pos(self):

		self.serial_write(b'LISTPV POSITION \r')
		time.sleep(0.05)
		if self.ser!=False:
			clean_buffer(self.ser)
			robot_output = read_and_wait(self.ser,0.15)
			print('ROBOT OUTPUT',robot_output )
			output_after = robot_output.replace(': ', ':').replace('>','')
			pairs=output_after.split() #separate in pairs of the form 'n:m'
			result_list=[]
			for pair in pairs:
				[key, value] = pair.split(':')
				result_list.append(int(value))
			self.joints = result_list[0:5]
			self.pos = result_list[5:10] 
		else:
			self.pos = [0,0,0,0,0] 


	def get_last_pos(self):
		#function to get axis position values
		#run calculate_pos before running get_pos to update the values
		return self.pos

	def get_last_joints(self):
		#function to get joint values
		#run calculate_pos before running get_joints to update the joint values
		return self.joints
	
	def housekeeping(self):
		self.manual_end()
		time.sleep(0.5)
		if self.ser!=False: #if not atHome
			self.ser.close()
		print('housekeeping completed - exiting')	

	def serial_write(self, toWrite):
		if self.ser!=False: #if not atHome
			self.ser.write(toWrite)
		print('bisturi', toWrite)
		

class cameraRobot():
	#this robot's y axis should be parallel to the table/jellow
	def __init__(self, shared_camera_pos=None,atHome=False, robotSpeed=2, comPort='COM4' ):
		if not atHome:
			self.ser = serial.Serial(comPort, baudrate=9600, bytesize=8, timeout=2, parity='N', xonxoff=0) #change for lab ------------------------HERE FOR LAB
			print("COM port in use: {0}".format(self.ser.name))	
		else:
			self.ser=False	
		self.speed=robotSpeed
		self.shared_camera_pos = shared_camera_pos
		self.square_pressed=False 

		time.sleep(2)
		self.serial_write(b'\r')
		time.sleep(0.2)
		self.go_to_initial_position()
		self.calculate_pos()

		self.serial_write(f'SPEED {robotSpeed}\r'.encode('utf-8'))
		time.sleep(0.5)
		self.initial_manual_start()
		print('Ready')

	def go_to_initial_position(self):
		cartesian=['X','Y', 'Z', 'P', 'R']
		initial_pos=[0,0,0,0,0] #defined experimentally
		self.serial_write(b'DEFP A \r')
		for i, coordenate in  enumerate(initial_pos):	
			printToRobot=f'SETPVC A {cartesian[i]} {int(coordenate)}\r'
			self.serial_write(printToRobot.encode('utf-8'))
			time.sleep(0.2)
		self.serial_write(b'MOVE A 7000\r')
		time.sleep(8)


	def move(self, axes,buttons ):
		self.update_pos(buttons[2])
		if max(buttons[11:15]):
			if not self.arrowsPressed: #if some arrow button has just been pressed
				self.manual_end()
				delta_z =0
				delta_x=0
				if buttons[11]-buttons[12]>0: #move up - arrow up pressed
					delta_z=400
				elif buttons[11]-buttons[12]<0: #move down - arrow down pressed
					delta_z=-400
				if buttons[13]-buttons[14]>0: #move backward - arrow left pressed
					delta_x=400
				elif buttons[13]-buttons[14]<0:#move foward - arrow right pressed
					delta_x=-400
				new_position = [self.pos[0]+delta_x, self.pos[1], self.pos[2]+delta_z, self.pos[3],self.pos[4] ]
				self.set_position(new_position)
				self.serial_write(b'Move A 200\r')
				time.sleep(0.5)
				self.pos = new_position
				self.shared_camera_pos = new_position   
				self.arrowsPressed = True
				self.manual_start_midle()
		else:
			self.arrowsPressed = False
			self.manual_move(axes, buttons)

	def update_pos(self, square_button):
		if not square_button: #square is not pressed
			self.square_pressed=False 
			return

		if self.square_pressed and square_button: #square was pressed and still is - no changes
			return None
		elif not self.square_pressed and square_button:  #square was not pressed and now is pressed - get current position of robot
			self.manual_end()
			self.calculate_pos()
			self.manual_start_midle()
			self.square_pressed=True 
			self.serial_write(b'con \r')
		


	def manual_move(self,axes, buttons):
		message= {'Q':0, '1':0,  'R':0,'4':0}
		#pitch:
		if axes[4] > 0:
			self.serial_write(b'R \r')
			message['R']+=1
		elif axes[5] > 0:
			self.serial_write(b'4 \r')
			message['4']+=1
		#base joint
		if buttons[4] - buttons[6] <0:
			self.serial_write(b'1 \r')
			message['1']+=1
		elif buttons[4] - buttons[6] >0:
			self.serial_write(b'Q \r')
			message['Q']+=1
		self.predict_next_pos(message)
		self.pos = foward_kinematics(self.joints)
		self.shared_camera_pos=self.pos


	def predict_next_pos(self, message):
		deltas=[]
		deltas.append(message['Q']-message['1'])
		deltas.append(message['R']-message['4'])
		base_sensitivity = 35.79 #from data
		pitch_sensitivity=69.275 #from data
		self.joints[0]+=deltas[0]*base_sensitivity#base
		self.joints[3]+=deltas[1]*pitch_sensitivity#pitch

		self.pos =foward_kinematics(self.joints)
			

	def set_position(self, position_values):
		
		cartesian=['X','Y', 'Z', 'P', 'R']

		for i,coordenate in enumerate(position_values) :
			if self.pos[i] != position_values[i]:
				#printToRobot=f'SHIFT AA BY {i+1} {int(delta)} \r'
				printToRobot=f'SETPVC A {cartesian[i]} {int(coordenate)}\r'
				self.serial_write(printToRobot.encode('utf-8'))
				time.sleep(0.5)


	def initial_manual_start(self):
		self.serial_write(b'\r')
		self.serial_write(b'~ \r')
		self.serial_write(b's \r')
		self.serial_write(f'{self.speed} \r'.encode('utf-8'))
		time.sleep(0.3)
		self.serial_write(b'J \r')
		time.sleep(0.1)

	def manual_start_midle(self):
		self.serial_write(b'\r')
		self.serial_write(b'~ \r')
		self.serial_write(b's \r')
		self.serial_write(f'{self.speed} \r'.encode('utf-8'))
		#time.sleep(0.05)


	def manual_end(self):
		self.serial_write(b'\r')
		#clean_buffer(serial)
		self.serial_write(b'~\r')
		time.sleep(0.05)
		self.serial_write(b'\r')

		
	def go_home(self):
		self.serial_write(b'home\r')
		time.sleep(180) # homing takes a few minutes ...
	
	def calculate_pos(self):
		self.serial_write(b'\r')
		time.sleep(0.3)
		self.serial_write(b'LISTPV POSITION \r')
		time.sleep(0.05)
		if self.ser!=False: #not at home - in the lab
			clean_buffer(self.ser)
			robot_output = read_and_wait(self.ser,0.15)
			output_after = robot_output.replace(': ', ':').replace('>','')
			pairs=output_after.split() #separate in pairs of the form 'n:m'
			result_list=[]
			for pair in pairs:
				[key, value] = pair.split(':')
				result_list.append(int(value))
			self.joints = result_list[0:5]
			self.pos = result_list[5:10]
		else:
			self.pos =[0,0,0,0,0]
		self.shared_camera_pos = self.pos

	def get_pos(self):
		#function to get axis position values
		#run calculate_pos before running get_pos to update the values
		return self.pos

	def get_joints(self):
		#function to get joint values
		#run calculate_pos before running get_joints to update the joint values
		return self.joints
	
	def serial_write(self, toWrite):
		if self.ser!=False: #if not atHome
			self.ser.write(toWrite)
		print('camera',toWrite)
	

	def housekeeping(self):
		self.manual_end()
		time.sleep(0.5)
		if self.ser!=False: #not at home
			self.ser.close()    
		print('housekeeping completed - exiting')	
		