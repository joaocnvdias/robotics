import cv2
import time

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
					print(output)
					print(serString.decode("Ascii"))
				except:
					pass
			else:
				deltat = time.time() - start_time
				if deltat>wait_time:
					flag = False
		return output	

# Create a VideoCapture object
vid = cv2.VideoCapture(0)

# Get the start time
start_time = time.time()

while True:
    # Capture the video frame by frame
    ret, frame = vid.read()

    # Get the current time
    current_time = time.time()

    # Calculate the running time in seconds
    elapsed_time = current_time - start_time

    # Display the running time on the top right corner
    cv2.putText(frame, f"Time: {elapsed_time:.2f} s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

    # Display the "Mode: -" text on the top right corner
    # We still need to define the modes and a new variable would be associated to it
    mode_text = "Mode: restricted"
    mode_text_size = cv2.getTextSize(mode_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    mode_text_position = (frame.shape[1] - mode_text_size[0] - 10, 30)
    cv2.putText(frame, mode_text, mode_text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

    # Display the bisturi position in the bottom center
    # position_text = "Position: " + read_and_wait(0.3)
    position_text = "Position: x y z" # Provisional text for home testing
    position_text_size = cv2.getTextSize(position_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    position_text_position = ((frame.shape[1] - position_text_size[0]) // 2, frame.shape[0] - 30)
    cv2.putText(frame, position_text, position_text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

    # Display the resulting frame
    cv2.imshow('frame', frame)

    # Check for the 'q' key to exit the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the VideoCapture object
vid.release()

# Destroy all the windows
cv2.destroyAllWindows()
