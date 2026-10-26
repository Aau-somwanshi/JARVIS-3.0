import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import cv2
import pyautogui
import speech_recognition as sr
import pyttsx3
import time
import os
from PIL import Image, ImageTk
import numpy as np
import keyboard

class JarvisUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS 3.0 - Multimodal Assistant")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0a0a1a')
        
        # Initialize core components
        self.voice_engine = pyttsx3.init()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Control flags
        self.voice_active = False
        self.motion_active = False
        self.camera_active = False
        self.cap = None
        
        # Gesture state
        self.last_gesture = "None"
        self.gesture_cooldown = 0
        
        # Screen dimensions for mouse mapping
        self.screen_w, self.screen_h = pyautogui.size()
        
        # Create UI
        self.setup_ui()
        
        # Start message queue for thread-safe UI updates
        self.message_queue = queue.Queue()
        self.process_messages()
        
        # Calibrate microphone
        self.calibrate_microphone()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = tk.Label(header_frame, text="JARVIS 3.0", 
                             font=('Arial', 32, 'bold'),
                             fg='#00ff00', bg='#0a0a1a')
        title_label.pack(side=tk.LEFT)

        subtitle_label = tk.Label(header_frame, text="Voice & Motion Controlled Assistant",
                                  font=('Arial', 14), fg='#cccccc', bg='#0a0a1a')
        subtitle_label.pack(side=tk.LEFT, padx=(20, 0))

        self.status_var = tk.StringVar(value="System Ready")
        status_label = tk.Label(header_frame, textvariable=self.status_var,
                               font=('Arial', 12), fg='#ffff00', bg='#0a0a1a')
        status_label.pack(side=tk.RIGHT)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        cam_frame = ttk.LabelFrame(left_frame, text="Motion Capture Feed", padding=10)
        cam_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.camera_label = tk.Label(cam_frame, text="Camera Feed\n[Click Start Camera]",
                                     bg='#000000', fg='#ffffff', font=('Arial', 12),
                                     width=60, height=20)
        self.camera_label.pack(fill=tk.BOTH, expand=True)

        controls_frame = ttk.Frame(left_frame)
        controls_frame.pack(fill=tk.X, pady=5)

        voice_frame = ttk.LabelFrame(controls_frame, text="Voice Control", padding=10)
        voice_frame.pack(fill=tk.X, pady=5)

        self.voice_btn = ttk.Button(voice_frame, text="Start Voice Control", 
                                    command=self.toggle_voice)
        self.voice_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.voice_status = tk.Label(voice_frame, text="Voice: OFF", 
                                     fg='red', bg='#0a0a1a', font=('Arial', 10, 'bold'))
        self.voice_status.pack(side=tk.LEFT)

        motion_frame = ttk.LabelFrame(controls_frame, text="Motion Control", padding=10)
        motion_frame.pack(fill=tk.X, pady=5)

        self.motion_btn = ttk.Button(motion_frame, text="Start Motion Control", 
                                     command=self.toggle_motion)
        self.motion_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.motion_status = tk.Label(motion_frame, text="Motion: OFF", 
                                     fg='red', bg='#0a0a1a', font=('Arial', 10, 'bold'))
        self.motion_status.pack(side=tk.LEFT)

        self.camera_btn = ttk.Button(motion_frame, text="Start Camera", 
                                     command=self.toggle_camera)
        self.camera_btn.pack(side=tk.RIGHT)

        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        console_frame = ttk.LabelFrame(right_frame, text="JARVIS Console", padding=10)
        console_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.console = scrolledtext.ScrolledText(console_frame, height=15, width=50,
                                                 bg='#000000', fg='#00ff00',
                                                 font=('Consolas', 10),
                                                 insertbackground='#00ff00')
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.insert(tk.END, "JARVIS 3.0 Initialized...\n")
        self.console.insert(tk.END, "System ready for voice and motion commands.\n\n")

        info_frame = ttk.LabelFrame(right_frame, text="Gesture Commands", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True)

        gesture_info = """
        Active Motion Controls:
        • Hand Movement: Moves Mouse Cursor
        • Closed Fist (Low area / close fingers): Left Click
        • Open Palm (Wide area): Play / Pause Media
        • Voice: "Open chrome", "Volume up", etc.
        """
        info_text = tk.Text(info_frame, height=12, width=50, bg='#0a0a1a', 
                            fg='#cccccc', font=('Arial', 10), wrap=tk.WORD)
        info_text.pack(fill=tk.BOTH, expand=True)
        info_text.insert(tk.END, gesture_info)
        info_text.config(state=tk.DISABLED)

        gesture_frame = ttk.Frame(right_frame)
        gesture_frame.pack(fill=tk.X, pady=5)

        self.current_gesture = tk.StringVar(value="Current Gesture: None")
        gesture_label = tk.Label(gesture_frame, textvariable=self.current_gesture,
                                font=('Arial', 12, 'bold'), fg='#00ffff', bg='#0a0a1a')
        gesture_label.pack()

    def calibrate_microphone(self):
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            self.log_message("Microphone calibrated successfully")
        except Exception as e:
            self.log_message(f"Microphone calibration failed: {str(e)}")

    def toggle_voice(self):
        if not self.voice_active:
            self.voice_active = True
            self.voice_btn.config(text="Stop Voice Control")
            self.voice_status.config(text="Voice: ON", fg='green')
            self.log_message("Voice control activated")
            threading.Thread(target=self.voice_listener, daemon=True).start()
        else:
            self.voice_active = False
            self.voice_btn.config(text="Start Voice Control")
            self.voice_status.config(text="Voice: OFF", fg='red')
            self.log_message("Voice control deactivated")

    def toggle_motion(self):
        if not self.motion_active:
            self.motion_active = True
            self.motion_btn.config(text="Stop Motion Control")
            self.motion_status.config(text="Motion: ON", fg='green')
            self.log_message("Motion control activated")
        else:
            self.motion_active = False
            self.motion_btn.config(text="Start Motion Control")
            self.motion_status.config(text="Motion: OFF", fg='red')
            self.log_message("Motion control deactivated")

    def toggle_camera(self):
        if not self.camera_active:
            self.start_camera()
        else:
            self.stop_camera()

    def start_camera(self):
        try:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(0)

            if self.cap.isOpened():
                self.camera_active = True
                self.camera_btn.config(text="Stop Camera")
                self.log_message("Camera started successfully")
                threading.Thread(target=self.update_camera_feed, daemon=True).start()
            else:
                self.log_message("Error: Could not open webcam.")
        except Exception as e:
            self.log_message(f"Failed to start camera: {str(e)}")

    def stop_camera(self):
        self.camera_active = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.camera_btn.config(text="Start Camera")
        self.camera_label.config(image='', text="Camera Feed\n[Click Start Camera]")
        self.log_message("Camera stopped")

    def voice_listener(self):
        with self.microphone as source:
            while self.voice_active:
                try:
                    self.status_var.set("Listening...")
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    self.status_var.set("Processing...")
                    
                    command = self.recognizer.recognize_google(audio).lower()
                    self.log_message(f"Voice command: {command}")
                    self.process_voice_command(command)
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self.log_message("Could not understand audio")
                except Exception as e:
                    self.log_message(f"Voice recognition error: {str(e)}")
                time.sleep(0.1)

    def process_voice_command(self, command):
        try:
            if "open" in command:
                app = command.replace("open", "").strip()
                self.open_application(app)
            elif "volume up" in command:
                self.volume_up()
            elif "volume down" in command:
                self.volume_down()
            elif "screenshot" in command:
                self.take_screenshot()
            else:
                self.speak(f"I heard: {command}")
        except Exception as e:
            self.log_message(f"Command error: {str(e)}")

    def open_application(self, app_name):
        apps = {'chrome': 'chrome', 'notepad': 'notepad', 'calculator': 'calc'}
        if app_name in apps:
            os.system(f"start {apps[app_name]}")
            self.speak(f"Opening {app_name}")
        else:
            self.speak(f"Application {app_name} not found")

    def volume_up(self):
        for _ in range(5):
            keyboard.press_and_release('volume up')
        self.speak("Volume increased")

    def volume_down(self):
        for _ in range(5):
            keyboard.press_and_release('volume down')
        self.speak("Volume decreased")

    def take_screenshot(self):
        screenshot = pyautogui.screenshot()
        filename = f"screenshot_{int(time.time())}.png"
        screenshot.save(filename)
        self.speak("Screenshot taken")

    def speak(self, text):
        def _speak():
            self.voice_engine.say(text)
            self.voice_engine.runAndWait()
        threading.Thread(target=_speak, daemon=True).start()

    def update_camera_feed(self):
        """Camera feed loop with active motion & contour tracking"""
        time.sleep(0.3)
        while self.camera_active and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            # Process gestures if motion control is active
            if self.motion_active:
                frame, gesture = self.process_motion(frame, h, w)
                if gesture != "None":
                    self.message_queue.put(('gesture', gesture))

            self.message_queue.put(('camera', frame))
            time.sleep(0.03)

    def process_motion(self, frame, h, w):
        """Detect motion, hand coordinates, and basic gestures using OpenCV contours"""
        if self.gesture_cooldown > 0:
            self.gesture_cooldown -= 1

        # Convert to grayscale and blur to remove noise
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (15, 15), 0)
        
        # Threshold to find moving/skin regions or high contrast areas
        _, thresh = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY_INV)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        gesture = "None"
        if contours:
            # Find the largest contour (representing the hand/motion)
            max_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(max_contour)
            
            if area > 3000:  # Minimum hand size threshold
                M = cv2.moments(max_contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # Draw tracking point on frame
                    cv2.circle(frame, (cx, cy), 8, (0, 255, 255), -1)
                    
                    # Map hand position to screen coordinates for mouse movement
                    if self.gesture_cooldown == 0:
                        target_x = np.interp(cx, (50, w - 50), (0, self.screen_w))
                        target_y = np.interp(cy, (50, h - 50), (0, self.screen_h))
                        pyautogui.moveTo(target_x, target_y, duration=0.05)
                    
                    # Gesture classification based on contour properties
                    hull = cv2.convexHull(max_contour)
                    hull_area = cv2.contourArea(hull)
                    if hull_area > 0:
                        solidity = float(area) / hull_area
                        
                        # Closed Fist / Pinch (Low solidity or compact area)
                        if area < 12000 and self.gesture_cooldown == 0:
                            gesture = "Click (Fist)"
                            pyautogui.click()
                            self.gesture_cooldown = 15
                            self.log_message("Gesture: Click executed")
                        # Open Palm
                        elif solidity > 0.75 and area > 20000 and self.gesture_cooldown == 0:
                            gesture = "Open Palm (Play/Pause)"
                            keyboard.press_and_release('play/pause media')
                            self.gesture_cooldown = 30
                            self.log_message("Gesture: Media Play/Pause")

        return frame, gesture

    def process_messages(self):
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                if msg_type == 'camera':
                    cv2image = cv2.cvtColor(data, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(cv2image)
                    img = img.resize((640, 480), Image.Resampling.LANCZOS)
                    imgtk = ImageTk.PhotoImage(image=img)
                    
                    self.camera_label.config(image=imgtk)
                    self.camera_label.image = imgtk
                elif msg_type == 'gesture':
                    self.current_gesture.set(f"Current Gesture: {data}")
        except queue.Empty:
            pass
        finally:
            self.root.after(10, self.process_messages)

    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        def update_console():
            self.console.insert(tk.END, formatted_message)
            self.console.see(tk.END)
        self.root.after(0, update_console)

    def on_closing(self):
        self.voice_active = False
        self.motion_active = False
        self.camera_active = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = JarvisUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()