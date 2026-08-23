import sys
import os
import psutil
import threading
import speech_recognition as sr
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor
from julie import run_julie_query

class VoiceListenerThread(QThread):
    text_captured = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def run(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            self.status_signal.emit("[MIC] Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=10)
                self.status_signal.emit("[MIC] Processing Speech...")
                text = recognizer.recognize_google(audio)
                self.text_captured.emit(text)
            except sr.WaitTimeoutError:
                self.status_signal.emit("[MIC] Timeout - No speech detected.")
            except Exception as e:
                self.status_signal.emit(f"[MIC Error] {e}")

class JulieWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        res = run_julie_query(self.prompt)
        self.finished.emit(res)

class JulieJarvisHUD(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ JULIE CORE :: TACTICAL ASSISTANT HUD")
        self.resize(1100, 720)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #030712; }
            QWidget { color: #E2E8F0; font-family: 'Segoe UI', sans-serif; }
            QFrame#hudCard { 
                background-color: rgba(15, 23, 42, 0.85); 
                border: 1px solid #0284C7; 
                border-radius: 10px; 
            }
            QFrame#glowCore {
                background-color: rgba(2, 132, 199, 0.15);
                border: 2px solid #00F2FE;
                border-radius: 60px;
            }
            QTextEdit { 
                background-color: rgba(3, 7, 18, 0.9); 
                border: 1px solid #1E293B; 
                border-radius: 6px; 
                color: #38BDF8; 
                font-family: 'Consolas', monospace; 
                font-size: 13px;
            }
            QLineEdit { 
                background-color: #0F172A; 
                border: 1px solid #0284C7; 
                border-radius: 6px; 
                padding: 12px; 
                color: #F8FAFC; 
                font-size: 14px;
            }
            QPushButton#micBtn {
                background-color: #0369A1;
                border: 1px solid #00F2FE;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
            }
            QPushButton#micBtn:hover { background-color: #0284C7; }
            QPushButton#sendBtn {
                background-color: #0D9488;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 12px 24px;
            }
            QLabel#titleLabel { font-size: 18px; font-weight: bold; color: #00F2FE; letter-spacing: 2px; }
            QLabel#badge { background-color: rgba(6, 78, 59, 0.8); color: #34D399; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid #059669; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header Bar
        header_card = QFrame()
        header_card.setObjectName("hudCard")
        header_layout = QHBoxLayout(header_card)
        
        title_label = QLabel("⚡ JULIE CORE :: EXECUTIVE DESKTOP HUD")
        title_label.setObjectName("titleLabel")
        
        self.status_ollama = QLabel("● OLLAMA: gemma4:26b")
        self.status_ollama.setObjectName("badge")
        
        self.status_vram = QLabel("● RAM: " + str(round(psutil.virtual_memory().percent)) + "%")
        self.status_vram.setObjectName("badge")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_ollama)
        header_layout.addWidget(self.status_vram)
        main_layout.addWidget(header_card)

        # Middle Section - Visualizer & Dual Logs
        mid_layout = QHBoxLayout()

        # Left Column - Telemetry Log
        left_card = QFrame()
        left_card.setObjectName("hudCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.addWidget(QLabel("<b style='color:#00F2FE;'>SUB-ROUTINE LOGS</b>"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setText("[SYSTEM] Julie Jarvis HUD active.\n[VOICE] Microphone listener initialized.\n[MODEL] Local Ollama 127.0.0.1:11434 ready.\n")
        left_layout.addWidget(self.log_box)
        mid_layout.addWidget(left_card, 35)

        # Center Column - Glowing Arc Core Visualizer
        center_card = QFrame()
        center_card.setObjectName("hudCard")
        center_layout = QVBoxLayout(center_card)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.core_frame = QFrame()
        self.core_frame.setFixedSize(120, 120)
        self.core_frame.setObjectName("glowCore")
        core_inner_layout = QVBoxLayout(self.core_frame)
        core_inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.core_label = QLabel("🔊\nJULIE")
        self.core_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.core_label.setStyleSheet("color: #00F2FE; font-weight: bold; font-size: 14px;")
        core_inner_layout.addWidget(self.core_label)
        
        center_layout.addWidget(self.core_frame)
        self.status_desc = QLabel("STANDBY")
        self.status_desc.setStyleSheet("color: #64748B; font-weight: bold; margin-top: 10px;")
        center_layout.addWidget(self.status_desc, alignment=Qt.AlignmentFlag.AlignCenter)
        mid_layout.addWidget(center_card, 25)

        # Right Column - Chat Display
        right_card = QFrame()
        right_card.setObjectName("hudCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.addWidget(QLabel("<b style='color:#00F2FE;'>INTERACTIVE CHAT</b>"))
        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        right_layout.addWidget(self.chat_box)
        mid_layout.addWidget(right_card, 40)

        main_layout.addLayout(mid_layout)

        # Bottom Input Control Bar
        input_card = QFrame()
        input_card.setObjectName("hudCard")
        input_layout = QHBoxLayout(input_card)

        self.mic_btn = QPushButton("🎙️ VOICE INPUT")
        self.mic_btn.setObjectName("micBtn")
        self.mic_btn.clicked.connect(self.start_voice_input)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Speak via [VOICE INPUT] or type a command here...")
        self.input_field.returnPressed.connect(self.send_query)

        self.send_btn = QPushButton("EXECUTE")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.clicked.connect(self.send_query)

        input_layout.addWidget(self.mic_btn)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        main_layout.addWidget(input_card)

    def start_voice_input(self):
        self.mic_btn.setEnabled(False)
        self.status_desc.setText("LISTENING...")
        self.status_desc.setStyleSheet("color: #34D399; font-weight: bold;")
        self.log_box.append("[MIC] Activating voice input thread...")

        self.voice_thread = VoiceListenerThread()
        self.voice_thread.text_captured.connect(self.handle_voice_text)
        self.voice_thread.status_signal.connect(lambda msg: self.log_box.append(msg))
        self.voice_thread.finished.connect(lambda: self.mic_btn.setEnabled(True))
        self.voice_thread.start()

    def handle_voice_text(self, text):
        self.input_field.setText(text)
        self.status_desc.setText("STANDBY")
        self.status_desc.setStyleSheet("color: #64748B; font-weight: bold;")
        self.send_query()

    def send_query(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.chat_box.append(f"<b style='color:#38BDF8;'>Pierre:</b> {text}")
        self.log_box.append(f"[QUERY] Dispatched: '{text}'")
        self.status_desc.setText("PROCESSING...")
        self.status_desc.setStyleSheet("color: #F59E0B; font-weight: bold;")
        self.input_field.clear()
        self.send_btn.setEnabled(False)

        self.worker = JulieWorker(text)
        self.worker.finished.connect(self.handle_response)
        self.worker.start()

    def handle_response(self, response_text):
        self.chat_box.append(f"<b style='color:#34D399;'>Julie:</b> {response_text}\n")
        self.log_box.append("[COMPLETE] Execution and voice response finished.")
        self.status_desc.setText("STANDBY")
        self.status_desc.setStyleSheet("color: #64748B; font-weight: bold;")
        self.send_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JulieJarvisHUD()
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())
