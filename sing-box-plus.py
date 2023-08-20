import ctypes
import os
import subprocess
import sys
import threading
import webbrowser
import customtkinter
import requests
from loguru import logger
import validators

VERSION = "v1.0.1"

LOG_FILE = "logs.log"
CORE_FILE = "sing-box-core.exe"
CONFIG_FILE = "config.json"
ICON_FILE = "icon.ico"


CORE_PATH = os.path.join(os.getcwd(), CORE_FILE)
CONFIG_PATH = os.path.join(os.getcwd(), CONFIG_FILE)
LOG_PATH = os.path.join(os.getcwd(), LOG_FILE)

# Configure logger
logger.add(LOG_PATH, format="{time} {level} {message}", level="INFO", rotation="10 MB", compression="zip")


# Main frame class
class SignBoxController():
    def __init__(self, root):
        logger.info("Initializing SignBoxPlus")
        logger.info(f"sing-box path: {CORE_PATH}")
        logger.info(f"Config path: {CONFIG_PATH}")
        logger.info(f"Log path: {LOG_PATH}")

        # Configure tkinter
        customtkinter.set_appearance_mode("system")
        self.root = root
        self.root.title("sing-box Plus | @B3H1")
        self.icon_path = resource_path(ICON_FILE)
        self.root.iconbitmap(self.icon_path)
        self.root.minsize(400, 300)
        self.root.resizable(False, False)

        is_it_admin = is_user_admin()
        logger.info(f"Is it admin: {is_it_admin}")

        if not is_config_exists():
            if is_it_admin:
                logger.info("Config file not found")
                # Url input widget
                self.url_entry = customtkinter.CTkEntry(self.root, placeholder_text="Subscription Link:")
                self.url_entry.pack(fill="both", expand=True, pady=10, padx=10)

                # Paste button
                self.paste_button = customtkinter.CTkButton(
                    master=self.root, text="Paste", fg_color="transparent", hover_color=None,
                    command=self.paste_url)
                self.paste_button.pack(pady=5)

                # Download config button
                self.download_config = customtkinter.CTkButton(
                    master=self.root, text="Download Config", fg_color="darkblue",
                    command=self.download_config_status)
                self.download_config.pack(pady=5)

        logger.info("Config file found, continuing...")
        # Start button
        self.start_button = customtkinter.CTkButton(root, text="Start sing-box",
                                                    command=self.start_sign_box)
        self.start_button.pack(pady=10)

        # Stop button
        self.stop_button = customtkinter.CTkButton(root, text="Stop sing-box", command=self.stop_sign_box)
        self.stop_button.pack(pady=10)

        # Log label
        self.log_label = LogFrame(master=self.root)

        # If config file not found, disable start and stop buttons
        if not is_config_exists():
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            self.log_label.set_log("Please set your subscription link, and download it.")

        # If user is not admin, disable start and stop buttons
        if not is_it_admin:
            logger.error("You must run this program as administrator!")
            self.log_label.set_log("You must run this program as administrator!")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")

    # Run command with args
    def send_command_to_application(self, command, args):
        logger.info(f"Starting sing-box with command: {command} {args}")
        try:
            os.chdir(os.path.dirname(command))
            logger.info("sing-box started successfully!")
            self.log_label.set_log("sing-box  is running...")
            self.start_button.configure(state="disabled")
            subprocess.run([command, *args], check=True)
        except subprocess.CalledProcessError as e:
            if e == 1:
                logger.info("sing-box stopped successfully!")
                self.log_label.set_log("sing-box stopped")
                self.start_button.configure(state="normal")

    # Force kill process
    def kill_process(self, process_name):
        logger.info(f"Stopping sing-box with command: taskkill /F /IM {process_name}")
        try:
            subprocess.run(["taskkill", "/F", "/IM", process_name], check=True)
            self.log_label.set_log("sing-box stopped successfully!")
            self.start_button.configure(state="normal")

        except subprocess.CalledProcessError as e:

            if e.returncode == 128:
                logger.info(f"sing-box is not running!:{e}")
                self.log_label.set_log("sing-box is not running!")
                self.start_button.configure(state="normal")
            else:
                logger.error(f"Failed to stop sing-box: {e}")
                self.log_label.set_log(f"Failed to stop sing-box.")

    # Start sing-box
    def start_sign_box(self):
        logger.info("Starting sing-box...")

        if not is_core_exists():
            logger.error("sing-box core not found")
            self.log_label.set_log("sing-box core not found!")
            return
        if not is_config_exists():
            logger.error("sing-box config not found")
            self.log_label.set_log("sing-box config not found!")
            return

        threading.Thread(target=self.send_command_to_application, args=(CORE_PATH, ["run"])).start()
        self.start_button.configure(state="disabled")

    def stop_sign_box(self):
        logger.info("Stopping sing-box...")
        self.kill_process(CORE_FILE)

    def download_config_status(self):
        logger.info("Downloading config file...")
        conf_url = self.url_entry.get()
        # check if the url is valid
        if not validators.url(conf_url):
            logger.error(f"Invalid url: {conf_url}")
            self.log_label.set_log("Invalid url!")
            return
        threading.Thread(target=self.download_config_proc, args=(conf_url,)).start()

    def download_config_proc(self, url):
        self.log_label.set_log("Downloading config file\nPlease wait...")
        self.download_config.configure(state="disabled")
        try:
            session = requests.Session()
            session.trust_env = False
            r = session.get(url, timeout=10)
            if r.status_code != 200:
                logger.error(f"Failed to download config file! Status code: {r.status_code}")
                self.log_label.set_log(f"Failed to download config file!\nStatus code: {r.status_code}")
                return False
            logger.info("Config file downloaded successfully!")
            self.log_label.set_log("Config file downloaded")
            self.download_config.configure(state="normal")
        except requests.exceptions.Timeout as e:
            logger.error(f"Failed to download config file! {e}")
            self.log_label.set_log(f"Failed to download config file!\ntime out error")
            self.download_config.configure(state="normal")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download config file! {e}")
            self.log_label.set_log(f"Failed to download config file!\nCheck your internet connection")
            self.download_config.configure(state="normal")
            return False

        with open(CONFIG_PATH, "wb") as f:
            # remove domains in rules
            f.write(r.content)
            if is_config_exists():
                logger.info("Config file saved successfully!")
                self.log_label.set_log("Config file saved")

                self.url_entry.destroy()
                self.download_config.destroy()
                self.paste_button.destroy()
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="normal")

                return True
            else:
                logger.error("Failed to save config file!")
                self.log_label.set_log("Failed to save config file!")
                return False

    def paste_url(self):
        self.url_entry.insert(0, self.root.clipboard_get())

    def run(self):
        logger.info("Running sing-box PLUS ...")
        self.root.mainloop()


# Log status frame class
class LogFrame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Create log label
        self.label = customtkinter.CTkLabel(self)
        self.pack(fill="both", expand=True)
        self.label.pack(fill="both", expand=True)
        self.label.configure(text=f"sing-box Plus {VERSION}")

        # Create about label
        self.link = customtkinter.CTkLabel(
            self, text="ABOUT", font=('Helvetica', 12), cursor="hand2",
            padx="10"
        )
        self.link.pack(side='left')
        self.link.bind("<Button-1>", lambda e: self.callback("https://behnam.cloud"))

    # Update log label
    def set_log(self, text):
        self.label.configure(text=text)
        self.label.update()

    # Open url in browser
    def callback(self, url):
        webbrowser.open_new_tab(url)


# Check if app is running as admin
def is_user_admin():
    # type: () -> bool
    try:
        return os.getuid() == 0
    except AttributeError:
        pass
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except AttributeError:
        pass


# Resource path for PyInstaller
def resource_path(relative_path):
    base_path = getattr(
        sys,
        '_MEIPASS',
        os.path.dirname(os.path.abspath(__file__))
    )
    return os.path.join(base_path, relative_path)


# Check is core file exists
def is_config_exists():
    return os.path.exists(CONFIG_FILE)


# Check is core file exists
def is_core_exists():
    return os.path.exists(CORE_FILE)


if __name__ == "__main__":
    root = customtkinter.CTk()
    app = SignBoxController(root)
    app.run()
