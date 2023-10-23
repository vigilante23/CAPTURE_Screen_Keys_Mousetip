import os
import sys
import requests
import datetime
import threading
import base64
import uuid
import time
import socket
import shutil
import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
from pynput import mouse, keyboard
import mss
from PyQt5.QtCore import Qt, QTimer, QSettings
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, 
    QLineEdit, QPushButton, QSizePolicy, QStackedWidget,
    QHBoxLayout, QFormLayout,  QLCDNumber, QDesktopWidget
)

# # Replace this with your actual API endpoint
# if getattr(sys, 'frozen', False):
#     # If the script is bundled, use sys._MEIPASS to get the base path
#     INSTALL_DIR = os.path.join(sys._MEIPASS, "myapp")
#     # Check if the directory exists, if not, create it
#     if not os.path.exists(INSTALL_DIR):
#         os.makedirs(INSTALL_DIR)
# else:
#     INSTALL_DIR = os.path.expanduser("~/myapp")

INSTALL_DIR = os.path.expanduser("~/myapp/Mousetip")
signup_api_endpoint = "https://simranautomobiles.com/2023/mouse-click/public/api/register"
login_api_endpoint = "https://simranautomobiles.com/2023/mouse-click/public/api/login"
screenshot_api_endpoint = "https://simranautomobiles.com/2023/mouse-click/public/api/file_upload"

class MouseTipApp:
    def __init__(self, system_page):
        self.system_page = system_page
        self.is_monitoring = False
        self.capture_interval = 300
        self.count = 0
        self.keyboard_listener = None
        self.mouse_listener = None
        self.key_press_count = 0  # To count key presses
        self.mouse_click_count = 0  # To count mouse clicks
        self.parent_folder_id = '1LotoWlYSh6FrVz6lhPj978fP_kJD6OX5'
        self.base_dir = os.path.join(INSTALL_DIR, "data")
        self.schedule_deletion_thread = threading.Thread(target=self.schedule_deletion)
        self.schedule_deletion_thread.start()

    def schedule_deletion(self):
        while True:
            try:
                # Schedule the deletion functions to run every 24 hours
                # Sleep for 24 hours
                time.sleep(24 * 3600)  # 24 hours * 3600 seconds/hour
                # Call the deletion functions
                drive = self.authenticate_google_drive()
                self.delete_old_google_drive_folders(self.parent_folder_id, drive)
                self.delete_old_local_folders()
            except Exception as e:
                # Handle any exceptions that may occur during the deletion process
                print(f"Error during scheduled deletion: {str(e)}")

    def delete_old_local_folders(self):
        # Specify the base directory where daily folders are created
        base_dir = self.base_dir
        # Calculate the date 1 day ago from the current date
        one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
        # List all subdirectories in the base directory
        subdirectories = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        for folder_name in subdirectories:
            try:
                # Convert the folder name to a datetime object
                folder_date = datetime.datetime.strptime(folder_name, "%Y-%m-%d")
                # Check if the folder date is older than 1 day
                if folder_date < one_day_ago:
                    folder_path = os.path.join(base_dir, folder_name)
                    # Remove the folder and its contents
                    shutil.rmtree(folder_path)
                    print(f"Deleted folder '{folder_name}' created on {folder_date}")
            except ValueError:
                # Handle any folder names that are not in the expected date format
                continue

    def delete_old_google_drive_folders(parent_folder_id, drive):
        # Calculate the date 7 days ago from the current date
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)

        # List all date folders inside the parent folder
        date_folder_query = drive.ListFile({'q': f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"}).GetList()

        for date_folder in date_folder_query:
            # Extract the creation date from the folder name
            folder_name_components = date_folder['title'].split('_')
            if len(folder_name_components) >= 2:
                folder_creation_date = datetime.datetime.strptime(folder_name_components[-1], '%Y-%m-%d')

                # Check if the date folder creation time is older than 7 days
                if folder_creation_date < seven_days_ago:
                    print(f"Deleting date folder '{date_folder['title']}' created on {folder_creation_date}")
                    date_folder.Delete()

    def authenticate_google_drive(self):
        credentials = ServiceAccountCredentials.from_json_keyfile_name("service.json", ['https://www.googleapis.com/auth/drive'])
        gauth = GoogleAuth()
        gauth.credentials = credentials
        drive = GoogleDrive(gauth)
        return drive

    def create_daily_folders(self):
        today = datetime.date.today()
        folder_name = today.strftime("%Y-%m-%d")
        daily_dir = os.path.join(self.base_dir, folder_name)
        os.makedirs(daily_dir, exist_ok=True)
        screenshot_folder = os.path.join(daily_dir, "screenshots")
        os.makedirs(screenshot_folder, exist_ok=True)
        return screenshot_folder

    def monitoring_loop(self):
        screenshot_folder = self.create_daily_folders()
  
        drive = self.authenticate_google_drive()
        while self.is_monitoring:
            self.count += 1
            self.capture_screenshot_and_save(self.count, screenshot_folder, drive)
            self.key_press_count = 0  # Reset key press count after each screenshot
            self.mouse_click_count = 0  # Reset mouse click count after each screenshot
            time.sleep(self.capture_interval)

    def capture_screenshot_and_save(self, count, screenshot_folder, drive):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        screenshot_filename = f"{timestamp}_k-{self.key_press_count}_m-{self.mouse_click_count}.jpg"
        self.screenshot_path = os.path.join(screenshot_folder, screenshot_filename)
        print(self.screenshot_path)
        with mss.mss() as sct:
            screenshot = sct.shot(output=self.screenshot_path)
        self.upload_to_google_drive(self.parent_folder_id, drive, self.screenshot_path, self.key_press_count, self.mouse_click_count)
        self.send_screenshot_to_api(self.screenshot_path, self.key_press_count, self.mouse_click_count, screenshot_filename)

    def upload_to_google_drive(self, parent_folder_id, drive, screenshot_path, key_press_count, mouse_click_count):
        # Extract the filename, date, and screenshot folder path from the screenshot_path
        screenshot_folder = os.path.dirname(screenshot_path)
        today_date = datetime.datetime.now().strftime("%Y-%m-%d")
        host_name = socket.gethostname()
        date_folder_name = f"{host_name}_{today_date}"

        # Search for the date folder inside the parent folder
        date_drive_folder_query = drive.ListFile({'q': f"'{parent_folder_id}' in parents and title='{date_folder_name}' and mimeType='application/vnd.google-apps.folder'"}).GetList()

        today_folder_exists = False
        today_folder_id = None

        for date_folder in date_drive_folder_query:
            if date_folder['title'] == date_folder_name:
                today_folder_exists = True
                today_folder_id = date_folder['id']
                break

        if not today_folder_exists:
            # Create the date folder if it doesn't exist
            date_drive_folder = drive.CreateFile({"title": date_folder_name, "mimeType": "application/vnd.google-apps.folder", "parents": [{"id": parent_folder_id}]})
            date_drive_folder.Upload()
            today_folder_id = date_drive_folder['id']

        # Rest of the code remains unchanged
        screenshots_drive_folder_query = drive.ListFile({'q': f"'{today_folder_id}' in parents and title='screenshots' and mimeType='application/vnd.google-apps.folder'"}).GetList()
        if not screenshots_drive_folder_query:
            screenshots_drive_folder = drive.CreateFile({"title": "screenshots", "mimeType": "application/vnd.google-apps.folder", "parents": [{"id": today_folder_id}]})
            screenshots_drive_folder.Upload()
        else:
            screenshots_drive_folder = screenshots_drive_folder_query[0]

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"k-{key_press_count}_m-{mouse_click_count}_{timestamp}.jpg"

        gdrive_screenshot = drive.CreateFile({"title": filename, "parents": [{"id": screenshots_drive_folder["id"]}]})
        gdrive_screenshot.SetContentFile(screenshot_path)
        gdrive_screenshot.Upload()

    def start_monitoring(self):
        self.is_monitoring = True
        self.start_event_listeners()
        self.monitoring_thread = threading.Thread(target=self.monitoring_loop)
        self.monitoring_thread.start()

    def stop_monitoring(self):
        self.is_monitoring = False
        self.stop_event_listeners()
        if self.monitoring_thread:
            self.monitoring_thread.join()  # Wait for the monitoring thread to finish

    def on_key_press_and_save(self, key):
        self.key_press_count += 1

    def on_mouse_click_and_save(self, x, y, button, pressed):
        if pressed:
            self.mouse_click_count += 1

    def start_event_listeners(self):
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press_and_save,
        )
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click_and_save
        )
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def stop_event_listeners(self):
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

    def send_screenshot_to_api(self, screenshot_path, key_press_count, mouse_click_count,  screenshot_filename):
        # id = self.settings.value("id", default="")
        data = {
        "company_id": 1,
        "k_click": key_press_count,
        "m_click": mouse_click_count,
        "user_id": global_id,
        }
        files = {'file_image': open(screenshot_path, 'rb')}
       
        try:
            response = requests.post(screenshot_api_endpoint, data=data, files=files)
            if response.status_code == 200:
                print("Screenshot sent to API successfully.")
            else:
                print("Failed to send screenshot to API.")
        except Exception as e:
            print("API request error:", e)

# Function to authenticate the user
def authenticate_user(email, password):
    data = {
        "email": email,
        "password": password
    }
    try:
        response = requests.post(login_api_endpoint, json=data)
        if(response.status_code == 200):
            response_dict = response.json()
            id = response_dict['user']['id']
            print("successful")
            return id
    except Exception as e:
        print("API request error:", e)
        return None

class LoginPage(QWidget):
    def __init__(self, stacked_widget, settings, main_window):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.settings = settings
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        # Logo or banner
        logo_label = QLabel()
        pixmap = QPixmap("your_logo.png")  # Replace with your logo image file
        logo_label.setPixmap(pixmap)
        layout.addWidget(logo_label)

        # Email input
        email_label = QLabel("Email:")
        email_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(email_label)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Enter your email")
        self.email_edit.setStyleSheet(
            "padding: 10px; border: 2px solid #ccc; border-radius: 20px; font-size: 12px;"
        )
        layout.addWidget(self.email_edit)

        # Password input
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(password_label)
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet(
            "padding: 10px; border: 2px solid #ccc; border-radius: 20px; font-size: 12px;"
        )
        layout.addWidget(self.password_edit)

        # Login button
        login_button = QPushButton("Login")
        login_button.setStyleSheet(
            "background-color: #4CAF50; color: white; border: 2px solid #4CAF50; border-radius: 20px; padding: 10px 30px; font-weight: bold; font-size: 14px;"
        )
        login_button.clicked.connect(self.login)
        layout.addWidget(login_button)
        login_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Make the button expand horizontally

        # Sign Up text link
        signup_label = QLabel("<html><a href='#' style='color: blue; text-decoration: none;'>Sign Up</a></html>")
        signup_label.setAlignment(Qt.AlignCenter)
        signup_label.linkActivated.connect(self.show_signup_page)
        layout.addWidget(signup_label)

        # Paragraph 
        paragraph_text = "Your privacy is our top priority. This login page uses industry-standard security measures to safeguard your information"
        paragraph_label = QLabel(paragraph_text)
        paragraph_label.setStyleSheet("color: black; font-size: 10px; font-family: Arial, sans-serif; font-size: 10px")
        paragraph_label.setAlignment(Qt.AlignCenter)
        paragraph_label.setWordWrap(True)  # Allow text to wrap to multiple lines
        layout.addWidget(paragraph_label)


        self.setLayout(layout)

    def show_signup_page(self, link):
        self.stacked_widget.setCurrentIndex(1)  # Show SignUpPage

    def display_error_message(self, message):
        error_label = QLabel(message)
        error_label.setStyleSheet("color: red; font-size: 12px;")
        error_label.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(error_label)

    def login(self):
        email = self.email_edit.text()
        password = self.password_edit.text()

        # Authenticate the user
        # response = True
        # if email.lower() == "testing@gmail.com" and password.lower() == "testing":
        #     response = True
        # else:
        #     response = False

        response = authenticate_user(email, password)
        if response:
            self.settings.setValue("id", response)
            Qsetting_data(self.settings)
            self.main_window.on_login_success()
            self.stacked_widget.addWidget(SystemPage())
            self.stacked_widget.setCurrentIndex(2)
        else:
            # Authentication failed, display an error message
            self.display_error_message("Authentication failed. Please check your credentials.")

def Qsetting_data(settings):
    id = settings.value("id")
    global global_id
    global_id = id

class SystemPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(500, 200, 350, 550)
        self.init_ui()
        self.mouse_tip_app = MouseTipApp(self)  # Create an instance of MouseTipApp
        self.monitoring_started = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer_value = 0  # Timer value in seconds
        self.update_timer_display()
        self.start_monitoring()

    def init_ui(self):

        layout = QVBoxLayout()
        
        layout.setAlignment(Qt.AlignCenter)
        
        # Timer display
        self.timer_display = QLCDNumber(self)  # Set the number of digits in the display
        self.timer_display.setDigitCount(8)
        self.timer_display.setFixedHeight(300) 
        self.timer_display.setStyleSheet(
            "color:black; border: none; border-radius: 100px; padding: 20px;"
        )
        layout.addWidget(self.timer_display)
      
        # Start Monitoring button
        self.toggle_button = QPushButton("Start Monitoring")
        self.toggle_button.setStyleSheet(
            "background-color: #4CAF50; color: white; border: 2px solid #4CAF50; border-radius: 20px; padding: 10px 30px; font-weight: bold; font-size: 14px;"
        )
        self.toggle_button.clicked.connect(self.toggle_monitoring)
        self.toggle_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout.addWidget(self.toggle_button)
        # Add the button layout to the main layout
        self.setLayout(layout)

    def toggle_monitoring(self):
        if self.monitoring_started:
            # If monitoring is currently started, stop it
            print("toggle clicked on start monitoring")
            self.stop_monitoring()
        else:
            # If monitoring is currently stopped, start it
            print("toggle clicked on stop monitoring")
            self.start_monitoring()

    def start_monitoring(self):
        if not self.monitoring_started:
            self.toggle_button.setStyleSheet(
            "background-color: #007FFF; color: white; border: 2px solid #007FFF; border-radius: 20px; padding: 10px 30px; font-weight: bold; font-size: 14px;"
            )
            self.toggle_button.setText("Stop Monitoring")
            self.monitoring_started = True
            self.timer.start(1000)
            self.monitoring_thread = threading.Thread(target=self.mouse_tip_app.start_monitoring)
            self.monitoring_thread.start()
            print("clicked on start monitoring")

    def stop_monitoring(self):
        # Stop monitoring when the "Stop Monitoring" button is clicked
        self.toggle_button.setStyleSheet(
            "background-color: #4CAF50; color: white; border: 2px solid #4CAF50; border-radius: 20px; padding: 10px 30px; font-weight: bold; font-size: 14px;"
        )
        self.toggle_button.setText("Start Monitoring")
        self.monitoring_started = False
        self.timer.stop()
        self.monitoring_thread = threading.Thread(target=self.mouse_tip_app.stop_monitoring)
        self.monitoring_thread.start()
        print("clicked on stop monitoring")

    def update_timer(self):
        self.timer_value += 1  # Increment timer value by 1 second
        self.update_timer_display()
    
    def update_timer_display(self):
        # Format the timer value as HH:MM:SS and display it
        hours = self.timer_value // 3600
        minutes = (self.timer_value % 3600) // 60
        seconds = self.timer_value % 60
        timer_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.timer_display.display(timer_str)

class SignUpPage(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Signup form title

        # Create a form layout for user input
        form_layout = QFormLayout()

        # self.pc_number_edit = QLineEdit()
        # self.pc_number_edit.setPlaceholderText("Pc_Number")
        # form_layout.addRow("Pc_number:", self.pc_number_edit)

        # Username input
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Username")
        form_layout.addRow("Username:", self.username_edit)

        # Email input
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Email")
        form_layout.addRow("Email:", self.email_edit)

        # Password input
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_edit)

        # Add the form layout to the main layout
        layout.addLayout(form_layout)

        # Create a horizontal layout for the buttons
        button_layout = QHBoxLayout()

        # Sign-up button
        signup_button = QPushButton("Sign Up")
        signup_button.setStyleSheet(
            "background-color: #4CAF50; color: white; border: 2px solid #4CAF50; border-radius: 20px; padding: 10px 30px; font-weight: bold; font-size: 14px;"
        )
        signup_button.clicked.connect(self.signup)
        button_layout.addWidget(signup_button)

        # Back button
        back_button = QPushButton("Back")
        back_button.setStyleSheet(
            "background-color: #ccc; color: #333; border: 2px solid #ccc; border-radius: 20px; padding: 10px 30px; font-weight: bold; font-size: 14px;"
        )
        back_button.clicked.connect(self.go_back)
        button_layout.addWidget(back_button)

        self.message_label = QLabel()
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        # Add the button layout to the main layout
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def signup(self):
        # Get user input
        username = self.username_edit.text()
        # pc_number = self.pc_number_edit.text()        # try:
        #     os.remove(screenshot_path)
        #     print(f"Screenshot {screenshot_path} deleted.")
        # except Exception as e:
        #     print(f"Failed to delete screenshot {screenshot_path}: {e}")
        email = self.email_edit.text()
        password = self.password_edit.text()

        # Validate input (You can add more validation as needed)
        # if not username or not pc_number or not email or not password:
        if not username or not email or not password:
            self.display_message("Please fill in all fields.")
            return

        # Implement your sign-up logic here, e.g., send a POST request to the API
        data = {
            # "pc_number":pc_number,
            "name": username,
            "email": email,
            "password": password
        }

        try:
            response = requests.post(signup_api_endpoint , json=data)
            if response.status_code == 200:
                self.display_message("Sign-up successful!", success=True)
                self.stacked_widget.setCurrentIndex(0)  # Show LoginPage on success
            else:
                self.display_message("Sign-up failed. Please try again.")
        except Exception as e:
            self.display_message(f"API request error: {str(e)}")

    def go_back(self):
        # Navigate back to the login page
        self.stacked_widget.setCurrentIndex(0)

    def display_message(self, message, success=False):
        # Display a message on the screen
        if success:
            self.message_label.setStyleSheet("color: green;")
        else:
            self.message_label.setStyleSheet("color: red;")
        self.message_label.setText(message)
        
# Usage example:
# Create a stacked widget and pass it to SignUpPage along with the API endpoint
# stacked_widget = QStackedWidget()
# signup_page = SignUpPage(stacked_widget, api_endpoint)
# stacked_widget.addWidget(signup_page)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MouseTipApp", "screenshot")
        # self.settings.clear()
        self.logged_in_key = "logged_in"
        self.mac_addresses_key = "mac_addresses"
        self.unique_identifier = self.get_mac_address()
        self.init_ui()
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.hide_login_screen)
        
    def init_ui(self):
        self.setWindowTitle("MouseTipApp")
        # self.setGeometry(500, 200, 350, 550)
        self.center_window()
        base64_main_window_icon = "iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAACXBIWXMAAAsTAAALEwEAmpwYAAACKklEQVR4nO3WT2sTQRgG8KcFCwr2S2Q2YsGG0lPpJYWmFP98BcWTPVUrgrTQpgWbmSTSk1gFqTuTnPwaHjz1puBN7M7klN6kBRN4ZQsNG8km7GQGRPrCc5t99zfDMDPAVf3vxRrt6fxHsxhIvWybXNian/n0dWp8jNRrgTLngTI0bpgyOp6YNSYfRrOB1F0XmCTKeqWYijZcYnooqeesQIE0uz5AuUZUdAZiyrRZwzwduYlVa5UpU2NSd9yBjn7uBeEJ9UVGd7P0YNLUrUBUwywJrBPHy8scvn509PDg8HMyv6o3tpJj+iLwgipY6QOFZiUziCpYI44uCZCTcDQve8c/zwSiMqZJ4NwZRvRSsgNVsOABQySwaQfiKHoBcey6BLVJ4N7tt98quXffKZm+bwkTxFEgjmPfoPW0cyilR8EvqIqlTKAyJv2COIqpoDJNDuyTBgqjJa+gQEWFLKCLa8YrSOrjCxTRRLJPeweUTGvnOmdS32fKnHpeIeP3th8KUmbTC0jqBSsQU6bkHCTNWfxGtwLFFUjddIfR3SCMnmBYDQRV/npCKFNiUm8HUotBmZE/6tsHW5TM4zcfviTH5KV+fqt5cmcoJhUkUEOG6nA8+L0PSqbzCntZeowCdYijThWsEsfy0Ag8I47TtHPIFYhc3fY2oDlPoA07UBlTJKAdY7okMHoDp6L2segMxXEWv9GtMT3Ue1wjjvmRm3hY4olVcXNszFX96/UHvp6oCHPKNWQAAAAASUVORK5CYII=="       
        main_window_pixmap = QPixmap()
        main_window_pixmap.loadFromData(base64.b64decode(base64_main_window_icon), format="PNG")
        main_window_icon = QIcon(main_window_pixmap)
        self.setWindowIcon(main_window_icon)

        # Create a QStackedWidget to manage different pages
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        authenticated_mac_addresses = self.settings.value(self.mac_addresses_key, [], type=list)
        
        if self.unique_identifier in authenticated_mac_addresses:
            print(self.unique_identifier, authenticated_mac_addresses)
            system_page = SystemPage()
            self.stacked_widget.addWidget(system_page)
            self.stacked_widget.setCurrentWidget(system_page)
            system_page.start_monitoring()

        else:
            print(self.unique_identifier)
            login_page = LoginPage(self.stacked_widget, self.settings, self)
            self.stacked_widget.addWidget(login_page)
            self.stacked_widget.setCurrentWidget(login_page)
            self.show()

        # Add the sign-up page to the stacked widget
        signup_page = SignUpPage(self.stacked_widget)
        self.stacked_widget.addWidget(signup_page)
        
    # def closeEvent(self, event):
    #     # Prevent the window from closing and hide it instead
    #     # self.hide()
    #     event.ignore()

    def center_window(self):
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        window_width = int(screen_rect.width() * 0.23)
        window_height = int(screen_rect.height() * 0.65)
        self.setGeometry((screen_rect.width() - window_width) // 2, (screen_rect.height() - window_height) // 2, window_width, window_height)

    def closeEvent(self, event):
    # Check which page is currently displayed
        current_page = self.stacked_widget.currentWidget()
        if isinstance(current_page, SystemPage):
            # If the current page is the system page, hide the application
            self.hide()
            event.ignore()
        else:
            # For other pages, minimize the window when closed using the cut button
            self.showMinimized()
            event.ignore()

    # def hide_login_screen(self):
    #     self.timer.stop()
    #     self.hide()

    def on_login_success(self):
        # When a user successfully logs in, add the current PC's MAC address to the list
        authenticated_mac_addresses = self.settings.value(self.mac_addresses_key, [], type=list)
        if self.unique_identifier not in authenticated_mac_addresses:
            authenticated_mac_addresses.append(self.unique_identifier)
            # Update the list of authenticated MAC addresses in QSettingsself.logged_in_key = "logged_in"
            self.settings.setValue(self.mac_addresses_key, authenticated_mac_addresses)

    def get_mac_address(self):
        # Get the MAC address of the current PC
        try:
            # Use a platform-specific method to obtain the MAC address
            if sys.platform == "win32":
                # Windows
                mac = self.get_windows_mac_address()
            elif sys.platform == "darwin":
                # macOS
                mac = self.get_macos_mac_address()
            else:
                # Linux
                mac = self.get_linux_mac_address()

            return mac
        except Exception as e:
            print(f"Error getting MAC address: {str(e)}")
            return ""
    
    def get_windows_mac_address(self):
        # Retrieve MAC address on Windows
        import uuid
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        return ":".join([mac[e:e + 2] for e in range(0, 11, 2)])
    
    def get_macos_mac_address(self):
        # Retrieve MAC address on macOS
        mac = "00:00:00:00:00:00"  # Default value
        try:
            # Get the MAC address from the system
            mac = ":".join("%012x" % uuid.getnode())
        except Exception as e:
            print(f"Error getting MAC address on macOS: {str(e)}")

    def get_linux_mac_address(self):
        # Retrieve MAC address on Linux
        mac = "00:00:00:00:00:00"  # Default value
        try:
            # Use the 'ifconfig' command to obtain the MAC address
            import subprocess
            result = subprocess.check_output(["ifconfig"])
            result = result.decode("utf-8")
            mac_lines = [line for line in result.split("\n") if "ether" in line]
            if mac_lines:
                mac = mac_lines[0].strip().split(" ")[1]
        except Exception as e:
            print(f"Error getting MAC address on Linux: {str(e)}")
        return mac

def main():
    
    app = QApplication(sys.argv)
    window = MainWindow()
    # window.hide()
    # window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
