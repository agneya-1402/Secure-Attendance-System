import cv2
import numpy as np
import pandas as pd
from datetime import datetime
import os
import serial
import time
from deepface import DeepFace

class AttendanceSystem:
    #user data
    def __init__(self, known_faces_dir="Attendance-System/known_faces", database_path="Attendance-System/attendance.xlsx"):
        self.known_faces_dir = known_faces_dir
        self.database_path = database_path
        self.known_face_embeddings = {}

        #arduino serial connection
        self.arduino = serial.Serial('/dev/cu.usbmodem1101', 9600, timeout=1)  
        time.sleep(2) 
        
        # Load faces
        self.load_known_faces()
        
        # load database
        self.initialize_database()
    
    def load_known_faces(self):
        print("Loading known faces...")
        for filename in os.listdir(self.known_faces_dir):
            if filename.endswith((".jpg", ".png", ".jpeg")):
                name = os.path.splitext(filename)[0]
                image_path = os.path.join(self.known_faces_dir, filename)
                try:
                    embedding = DeepFace.represent(
                        img_path=image_path,
                        model_name="VGG-Face",
                        enforce_detection=True
                    )
                    self.known_face_embeddings[name] = embedding
                    print(f"Loaded face data for {name}")
                except Exception as e:
                    print(f"Error loading {name}: {str(e)}")
    
    # create attendance db
    def initialize_database(self):
        if not os.path.exists(self.database_path):
            df = pd.DataFrame(columns=['Name', 'Date', 'Time'])
            df.to_excel(self.database_path, index=False)

    # mark attendance
    def mark_attendance(self, name):
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        df = pd.read_excel(self.database_path)
        
        # Check entry exists for today
        today_entries = df[(df['Name'] == name) & (df['Date'] == date)]
        if len(today_entries) == 0:
            new_entry = pd.DataFrame({
                'Name': [name],
                'Date': [date],
                'Time': [time_str]
            })
            df = pd.concat([df, new_entry], ignore_index=True)
            df.to_excel(self.database_path, index=False)
            return True
        return False
    
    # arduino door
    def control_door(self, open=True):
        if open:
            self.arduino.write(b'1')  # Open door 
            time.sleep(5)
            self.arduino.write(b'0')  # Close door 
    
    # verify faces against db
    def verify_face(self, frame, threshold=0.3):
        try:
            current_embedding = DeepFace.represent(
                img_path=frame,
                model_name="VGG-Face",
                enforce_detection=True,
                detector_backend="opencv"
            )
            
            # compare with known faces
            for name, known_embedding in self.known_face_embeddings.items():
                distance = DeepFace.verify(
                    img1_path=frame,
                    img2_path=os.path.join(self.known_faces_dir, f"{name}.jpg"),
                    enforce_detection=False,
                    model_name="VGG-Face"
                )
                
                if distance['verified']:
                    return name
                    
            return None
            
        except Exception as e:
            print(f"Error in face verification: {str(e)}")
            return None
    
    def run(self):
        cap = cv2.VideoCapture(1)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
                face_frame = frame[y:y+h, x:x+w]
                name = self.verify_face(face_frame)
                
                if name:
                    # Mark attendance and Control door
                    if self.mark_attendance(name):
                        print(f"Welcome {name}! Attendance marked.")
                        self.control_door(True)
                    else:
                        print(f"Welcome back {name}! Already marked for today.")
                        self.control_door(True)
                    
                    cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
                else:
                    cv2.putText(frame, "Unknown", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,255), 2)
            
            cv2.imshow('Attendance System', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        self.arduino.close()

if __name__ == "__main__":
    system = AttendanceSystem()
    system.run()