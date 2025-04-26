import tkinter as tk
from tkinter import filedialog, ttk, messagebox, font
import mido
import time
import threading
import math
import random
import sys
import os
import traceback

# ======================================================================================
# MIDI PLAYER | RIHA STUDIO | By Riha
# ======================================================================================

try:
    import rtmidi
    rtmidi_available = True
    print("[LIB]: python-rtmidi 라이브러리가 정상 설치 상태입니다.")
except ImportError:
    rtmidi_available = False
    print("[LIB]: python-rtmidi 라이브러리를 감지하지 못했습니다. 플레이어가 비활성화 됩니다.")
    print("[LIB]: 설치 오류 발생 시, 안내된 Visual C++ Build Tools 설치 후 다시 시도하세요.")

try:
    from ttkthemes import ThemedStyle
    _global_themed_style_imported = True
    print("[LIB]: ttkthemes 라이브러리가 정상 설치 상태입니다.")
except ImportError:
    _global_themed_style_imported = False
    print("[LIB]: ttkthemes 라이브러리를 감지하지 못했습니다. 기본 ttk 스타일을 사용합니다.")


class MidiPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("미디 플레이어 v1.0 (Made by 리하스튜디오)")
        self.root.geometry("550x550")
        self.root.option_add('*tearOff', False)
        self.root.resizable(False, False)

        self.midi_file_path = None
        self.mid = None
        self.is_playing = False
        self.is_paused = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.playback_thread = None
        self.current_playback_time = 0.0
        self.total_midi_time = 0.0
        self.cumulative_times = []

        self.notes_paused = []
        self.pedal_paused = []

        self.outport = None

        self.error_mode_enabled = tk.BooleanVar(value=False)
        self.error_percentage = tk.DoubleVar(value=5.0)
        self.error_pitch_range = tk.IntVar(value=3)
        self.active_notes = {}

        self.style = ttk.Style()

        self.app_font = None
        try:
            available_fonts = list(font.families())
            pretendard_names = ['Pretendard', 'Pretendard Regular', 'Pretendard-Regular']
            found_font_name = None
            for p_name in pretendard_names:
                if p_name in available_fonts:
                    found_font_name = p_name
                    break

            if found_font_name:
                self.app_font = font.Font(family=found_font_name, size=9)
                print(f"[FONT]: '{found_font_name}' 폰트 감지 및 적용을 시도하고 있습니다...")
                self.style.configure('.', font=self.app_font)
                self.style.configure('TCheckbutton', font=self.app_font)
            else:
                print("[FONT]: 시스템에 Pretendard 폰트가 설치되어있지 않습니다. 따라서 기본 폰트가 적용됩니다. 같은 폴더에 있는 Pretendard.otf 를 설치하여 주세요.")
        except Exception as e:
            print(f"[ERR]: 폰트 설정 중 오류 발생: {e}. 사용자 기본 폰트를 사용합니다.")
            self.app_font = None

        self.themed_style_available = False
        self.themed_style = None

        if _global_themed_style_imported:
             try:
                  self.themed_style = ThemedStyle(self.root)
                  self.themed_style_available = True
                  print("[TEM]: ttk 테마가 적용 준비 되었습니다.  >  기본 테마 적용 준비중...")
                  try:
                       self.themed_style.set_theme("clam")
                       print("[TEM]: 시스템 기본 테마 'clam' 이 적용되었습니다.")
                  except Exception as theme_apply_e:
                       print(f"[ERR]: 시스템 기본 테마 'clam' 를 적용하는 도중 오류가 발생했습니다: {theme_apply_e}, 테마 기능이 비활성화 됩니다.")
                       self.themed_style_available = False
                       self.themed_style = None
             except Exception as e:
                 print(f"[ERR]: ThemedStyle 객체 생성 중 오류 발생: {e}. 테마 기능이 비활성화 됩니다.")
                 self.themed_style_available = False
                 self.themed_style = None

        self.menubar = tk.Menu(root)
        self.root.config(menu=self.menubar)


        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="파일", menu=self.filemenu)
        self.filemenu.add_command(label="MIDI 파일 열기", command=self.open_midi_file,
                                  font=self.app_font if self.app_font else None)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="종료", command=self.on_closing,
                                  font=self.app_font if self.app_font else None)

        self.controlmenu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="재생", menu=self.controlmenu)
        self.controlmenu_play = self.controlmenu.add_command(label="재생", command=self.play_midi, font=self.app_font if self.app_font else None)
        self.controlmenu_pause = self.controlmenu.add_command(label="일시정지", command=self.pause_midi, font=self.app_font if self.app_font else None)
        self.controlmenu_stop = self.controlmenu.add_command(label="중지", command=self.stop_midi, font=self.app_font if self.app_font else None)

        self.settingsmenu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="설정", menu=self.settingsmenu)

        if self.themed_style_available and self.themed_style is not None:
            self.thememenu = tk.Menu(self.settingsmenu, tearoff=0)
            self.settingsmenu.add_cascade(label="테마 변경", menu=self.thememenu, font=self.app_font if self.app_font else None)
            try:
                available_themes = self.themed_style.get_themes()
                for theme_name in sorted(available_themes):
                     self.thememenu.add_command(label=theme_name, command=lambda name=theme_name: self.set_theme(name),
                                                font=self.app_font if self.app_font else None)
            except Exception as e:
                 try:
                      index = self.settingsmenu.index("테마 변경")
                      self.settingsmenu.entryconfig(index, state=tk.DISABLED, label="(테마 목록 로드 오류)")
                 except tk.TclError:
                      pass
        else:
             status_text = "(ttkthemes 미설치)" if not _global_themed_style_imported else "(테마 로드/적용 오류)"
             self.settingsmenu.add_command(label=status_text, state=tk.DISABLED, font=self.app_font if self.app_font else None)

        self.status_bar = ttk.Label(root, text="준비됨", relief=tk.SUNKEN, anchor=tk.W, font=self.app_font if self.app_font else None)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.file_frame = ttk.LabelFrame(root, text="MIDI 파일")
        self.file_frame.pack(pady=(15, 5), padx=15, fill=tk.X)

        self.open_button = ttk.Button(self.file_frame, text="MIDI 파일 열기", command=self.open_midi_file)
        self.open_button.pack(side=tk.LEFT, padx=10, pady=5)

        self.file_label = ttk.Label(self.file_frame, text="로드된 파일 없음", font=self.app_font if self.app_font else None)
        self.file_label.pack(side=tk.LEFT, padx=10, pady=5, expand=True, fill=tk.X)

        # 콤보박스, 저장버튼 쪽
        self.saved_midi_combo = ttk.Combobox(self.file_frame, state="readonly")
        self.saved_midi_combo.pack(side=tk.RIGHT, padx=5)
        self.saved_midi_combo.bind("<<ComboboxSelected>>", self.load_saved_midi_file)

        self.save_button = ttk.Button(self.file_frame, text="현재 파일 저장", command=self.save_current_midi)
        self.save_button.pack(side=tk.RIGHT, padx=5)

        # 콤보박스 리스트 갱신
        self.refresh_saved_midi_list()

        self.control_frame = ttk.LabelFrame(root, text="재생 제어")
        self.control_frame.pack(pady=5, padx=15, fill=tk.X)

        self.play_button = ttk.Button(self.control_frame, text="재생", command=self.play_midi, state=tk.DISABLED)
        self.play_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.pause_button = ttk.Button(self.control_frame, text="일시정지", command=self.pause_midi, state=tk.DISABLED)
        self.pause_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.stop_button = ttk.Button(self.control_frame, text="중지", command=self.stop_midi, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.control_frame.grid_columnconfigure(0, weight=1)
        self.control_frame.grid_columnconfigure(1, weight=1)
        self.control_frame.grid_columnconfigure(2, weight=1)

        self.port_frame = ttk.LabelFrame(root, text="MIDI 출력 포트")
        self.port_frame.pack(pady=5, padx=15, fill=tk.X)

        self.port_label = ttk.Label(self.port_frame, text="포트 선택:", font=self.app_font if self.app_font else None)
        self.port_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.output_ports = []
        self.selected_port_name = tk.StringVar()
        self.selected_port_name.trace_add("write", self._on_port_selected)
        self.port_menu = ttk.OptionMenu(self.port_frame, self.selected_port_name, "")
        self.port_menu.pack(side=tk.LEFT, padx=10, pady=5, expand=True, fill=tk.X)

        self.update_midi_ports()

        self.settings_frame = ttk.LabelFrame(root, text="설정")
        self.settings_frame.pack(pady=5, padx=15, fill=tk.X)

        self.speed_label = ttk.Label(self.settings_frame, text="속도:", font=self.app_font if self.app_font else None)
        self.speed_label.grid(row=0, column=0, padx=10, pady=3, sticky="w")
        self.speed_scale = ttk.Scale(self.settings_frame, from_=0.2, to=3.0, value=1.0, orient=tk.HORIZONTAL, command=self._update_speed_display_cmd)
        self.speed_scale.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        self.speed_value_label = ttk.Label(self.settings_frame, text="1.0x", width=5, font=self.app_font if self.app_font else None)
        self.speed_value_label.grid(row=0, column=2, padx=10, pady=3, sticky="w")
        self.speed_scale.bind("<Motion>", self._update_speed_display_event)

        self.velocity_label = ttk.Label(self.settings_frame, text="벨로서티:", font=self.app_font if self.app_font else None)
        self.velocity_label.grid(row=1, column=0, padx=10, pady=3, sticky="w")
        self.velocity_scale = ttk.Scale(self.settings_frame, from_=0, to=127, value=100, orient=tk.HORIZONTAL, command=self._update_velocity_display_cmd)
        self.velocity_scale.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
        self.velocity_value_label = ttk.Label(self.settings_frame, text="100", width=5, font=self.app_font if self.app_font else None)
        self.velocity_value_label.grid(row=1, column=2, padx=10, pady=3, sticky="w")
        self.velocity_scale.bind("<Motion>", self._update_velocity_display_event)

        self.settings_frame.grid_columnconfigure(1, weight=1)

        self.error_frame = ttk.LabelFrame(root, text="가상 오류 발생기")
        self.error_frame.pack(pady=5, padx=15, fill=tk.X)

        self.error_check = ttk.Checkbutton(self.error_frame, text="오타 모드 활성화", variable=self.error_mode_enabled)
        self.error_check.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        self.error_percent_label = ttk.Label(self.error_frame, text="오타 확률 (%):", font=self.app_font if self.app_font else None)
        self.error_percent_label.grid(row=1, column=0, padx=10, pady=3, sticky="w")
        self.error_percent_scale = ttk.Scale(self.error_frame, from_=0, to=100, value=5.0, orient=tk.HORIZONTAL, variable=self.error_percentage, command=self._update_error_percent_display_cmd)
        self.error_percent_scale.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
        self.error_percent_value_label = ttk.Label(self.error_frame, text="5.0%", width=5, font=self.app_font if self.app_font else None)
        self.error_percent_value_label.grid(row=1, column=2, padx=10, pady=3, sticky="w")
        self.error_percent_scale.bind("<Motion>", self._update_error_percent_display_event)

        self.error_pitch_label = ttk.Label(self.error_frame, text="음정 오차 (+/- 반음):", font=self.app_font if self.app_font else None)
        self.error_pitch_label.grid(row=2, column=0, padx=10, pady=3, sticky="w")
        self.error_pitch_scale = ttk.Scale(self.error_frame, from_=0, to=12, value=3, orient=tk.HORIZONTAL, variable=self.error_pitch_range, command=self._update_error_pitch_display_cmd)
        self.error_pitch_scale.grid(row=2, column=1, padx=5, pady=3, sticky="ew")
        self.error_pitch_value_label = ttk.Label(self.error_frame, text="3", width=5, font=self.app_font if self.app_font else None)
        self.error_pitch_value_label.grid(row=2, column=2, padx=10, pady=3, sticky="w")
        self.error_pitch_scale.bind("<Motion>", self._update_error_pitch_display_event)

        self.timing_variance = tk.DoubleVar(value=0.5)  # 기본 .5% 오차
        self.timing_variance_label = ttk.Label(self.error_frame, text="타이밍 오차 (%):", font=self.app_font if self.app_font else None)
        self.timing_variance_label.grid(row=3, column=0, padx=10, pady=3, sticky="w")
        self.timing_variance_scale = ttk.Scale(self.error_frame, from_=0, to=100, variable=self.timing_variance, orient=tk.HORIZONTAL)
        self.timing_variance_scale.grid(row=3, column=1, padx=5, pady=3, sticky="ew")
        self.timing_variance_value_label = ttk.Label(self.error_frame, text="0.5%", width=.5, font=self.app_font if self.app_font else None)
        self.timing_variance_value_label.grid(row=3, column=2, padx=10, pady=3, sticky="w")
        self.timing_variance_scale.bind("<Motion>", lambda e: self.timing_variance_value_label.config(text=f"{self.timing_variance.get():.1f}%"))

        self.error_frame.grid_columnconfigure(1, weight=1)

        self.pedal_mode_enabled = tk.BooleanVar(value=True)
        self.pedal_check = ttk.Checkbutton(self.settings_frame, text="페달 모드 사용", variable=self.pedal_mode_enabled)
        self.pedal_check.grid(row=2, column=0, columnspan=3, padx=10, pady=3, sticky="w")


        self.seek_frame = ttk.Frame(root)
        self.seek_frame.pack(pady=(10, 15), padx=15, fill=tk.X)

        self.seek_scale = ttk.Scale(self.seek_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.seek_midi_drag)
        self.seek_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.seek_scale.bind("<ButtonRelease-1>", self.on_seek_release)

        self.time_label = ttk.Label(self.seek_frame, text="00:00 / 00:00", font=self.app_font if self.app_font else None)
        self.time_label.pack(side=tk.RIGHT, padx=5)

        self._update_button_states()

    def update_midi_ports(self):
        if not rtmidi_available:
            self.output_ports = ["python-rtmidi 라이브러리 미감지로 비활성화."]
            if hasattr(self, 'port_menu'):
                self.port_menu.config(state=tk.DISABLED)
                self.selected_port_name.set(self.output_ports[0])
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text="python-rtmidi 라이브러리를 설치하지 않아 비활성화 되었습니다.")
            self._update_button_states()
            return

        try:
            self.output_ports = mido.get_output_names()
            if not self.output_ports:
                self.output_ports = ["출력 포트 없음"]
                if hasattr(self, 'port_menu'):
                    self.port_menu.config(state=tk.DISABLED)
                    self.selected_port_name.set(self.output_ports[0])
                    self._update_button_states()
                if hasattr(self, 'status_bar'):
                    self.status_bar.config(text="시스템에서 MIDI 포트를 찾을 수 없습니다.")
                self._update_button_states()
            else:
                display_ports = ["포트를 선택하세요..."] + self.output_ports
                if hasattr(self, 'port_menu'):
                    self.port_menu.config(state=tk.NORMAL)
                    menu = self.port_menu["menu"]
                    menu.delete(0, "end")
                    for port_name in display_ports:
                        menu.add_command(label=port_name,
                                       command=lambda name=port_name: self.selected_port_name.set(name),
                                       font=self.app_font if self.app_font else None)
                    self.selected_port_name.set(display_ports[0])
                    self._update_button_states()
                if hasattr(self, 'status_bar'):
                    self.status_bar.config(text=f"사용 가능한 MIDI 포트: {len(self.output_ports)}개")
                self._update_button_states()

        except Exception as e:
            self.output_ports = [f"포트 목록 오류: {e}"]
            if hasattr(self, 'port_menu'):
                self.port_menu.config(state=tk.DISABLED)
                self.selected_port_name.set(self.output_ports[0])
                self._update_button_states()
            print(f"MIDI 포트 목록 가져오기 오류: {e}")
            messagebox.showerror("MIDI 오류", f"MIDI 출력 포트 목록을 가져올 수 없습니다:\n{e}\n\nrtmidi 설치 및 가상 MIDI 포트 설정 설정을 확인하세요.")
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text=f"오류: 포트 목록 가져오기 실패 - {e}")
            self._update_button_states()

    def _on_port_selected(self, *args):
        selected_name = self.selected_port_name.get()
        print(f"포트 선택 변경 감지: {selected_name}")
        self.select_midi_port(selected_name)

    def select_midi_port(self, port_name):
        print(f"\n[포트 선택 시도] 선택된 포트: {port_name}")
        if port_name in ["포트를 선택하세요...", "출력 포트 없음"] or "오류" in port_name:
            print(f"유효하지 않은 포트 선택 무시: {port_name}")
            return

        self.close_midi_port()

        try:
            print(f"포트 열기 시도: {port_name}")
            self.outport = mido.open_output(port_name)
            print(f"포트 열기 성공: {self.outport}")
            self._update_button_states()
        except Exception as e:
            print(f"포트 열기 실패: {str(e)}")
            self.outport = None
            messagebox.showerror("오류", f"포트 열기 실패: {e}")

    def close_midi_port(self):
        if self.outport is not None:
            try:
                if not self.outport.closed:
                     print(f"MIDI 포트 닫는 중: {self.outport.name}")
                     self.outport.close()
            except Exception as e:
                print(f"MIDI 포트 닫기 오류: {e}")
            finally:
                self.outport = None
                self._update_button_states()

    def open_midi_file(self):
        self.stop_midi()

        file_path = filedialog.askopenfilename(
            initialdir=".",
            title="MIDI 파일 선택",
            filetypes=(("MIDI 파일", "*.mid *.midi"), ("모든 파일", "*.*"))
        )

        if file_path:
            if not os.path.exists(file_path):
                 if hasattr(self, 'file_label'):
                      self.file_label.config(text=f"오류: 파일을 찾을 수 없음")
                 if hasattr(self, 'status_bar'):
                      self.status_bar.config(text=f"오류: 파일을 찾을 수 없음: {file_path}")
                 messagebox.showerror("파일 오류", f"선택된 파일을 찾을 수 없습니다:\n{file_path}")
                 self._update_button_states()
                 return

            try:
                self.mid = mido.MidiFile(file_path)
                self.midi_file_path = file_path
                display_name = os.path.basename(file_path)
                if len(display_name) > 40:
                     display_name = display_name[:37] + "..."
                if hasattr(self, 'file_label'):
                     self.file_label.config(text=f"로드됨: {display_name}")

                self.total_midi_time = self.mid.length

                self.cumulative_times = []
                current_time = 0.0
                for msg in self.mid:
                    current_time += msg.time
                    self.cumulative_times.append(current_time)

                self.current_playback_time = 0.0
                if hasattr(self, 'seek_scale'):
                     self.seek_scale.set(0)

                if hasattr(self, 'time_label'):
                     self.update_time_label(0, self.total_midi_time)

                if hasattr(self, 'status_bar'):
                     self.status_bar.config(text=f"파일 로드됨: {os.path.basename(file_path)}")
                self._update_button_states()

            except Exception as e:
                if hasattr(self, 'file_label'):
                     self.file_label.config(text=f"파일 로드 오류")
                self.mid = None
                self.midi_file_path = None
                self.cumulative_times = []
                self.total_midi_time = 0.0
                if hasattr(self, 'time_label'):
                     self.update_time_label(0, 0)
                if hasattr(self, 'seek_scale'):
                     self.seek_scale.set(0)
                if hasattr(self, 'status_bar'):
                     self.status_bar.config(text=f"파일 로드 오류: {e}")
                print(f"[ERR]: MIDI 파일 로드 오류: {e}")
                messagebox.showerror("파일 오류", f"MIDI 파일을 로드할 수 없습니다:\n{e}\n\n파일 형식이 올바른지 확인하세요.")
                self._update_button_states()

    def play_midi(self):
        if self.mid is not None and rtmidi_available and self.outport is not None and not self.outport.closed and not self.is_playing:
            self.is_playing = True
            self.is_paused = False
            self.stop_event.clear()
            self.pause_event.clear()

            self._update_button_states()

            if hasattr(self, 'status_bar'):
                 self.status_bar.config(text="재생 중...")
            self.active_notes = {}

            self.playback_thread = threading.Thread(target=self._playback_loop)
            self.playback_thread.start()

        elif self.mid is None:
             if hasattr(self, 'status_bar'):
                  self.status_bar.config(text="경고: MIDI 파일이 로드되지 않았습니다.")
             messagebox.showwarning("재생 경고", "재생 전에 MIDI 파일을 로드하세요.")
        elif not rtmidi_available:
             if hasattr(self, 'status_bar'):
                  self.status_bar.config(text="경고: python-rtmidi가 설치되지 않아 MIDI 출력이 불가합니다.")
             messagebox.showwarning("재생 경고", "python-rtmidi 라이브러리를 설치해야 MIDI 출력이 가능합니다.")
        elif self.outport is None or self.outport.closed:
            if hasattr(self, 'status_bar'):
                 self.status_bar.config(text="경고: MIDI 출력 포트가 선택되지 않았거나 열리지 않았습니다.")
            messagebox.showwarning("재생 경고", "재생 전에 MIDI 출력 포트를 선택하고 여세요.")
        elif self.is_playing:
             if hasattr(self, 'status_bar'):
                  self.status_bar.config(text="정보: 이미 재생 중입니다.")

    def refresh_saved_midi_list(self):
        save_dir = "./midi"
        try:
            files = [f for f in os.listdir(save_dir) if f.endswith(".mid")]
            self.saved_midi_combo["values"] = files
            self.saved_midi_combo.set("저장된 파일 선택" if files else "MIDI 없음")
        except Exception as e:
            self.saved_midi_combo["values"] = []
            self.saved_midi_combo.set("목록 오류")

    def load_saved_midi_file(self, event=None):
        filename = self.saved_midi_combo.get()
        full_path = os.path.join("./midi", filename)
        if os.path.exists(full_path):
            self.open_midi_file_from_path(full_path)

    def open_midi_file_from_path(self, file_path):
        try:
            self.stop_midi()
            self.mid = mido.MidiFile(file_path)
            self.midi_file_path = file_path
            self.file_label.config(text=f"로드됨: {os.path.basename(file_path)}")
            self.total_midi_time = self.mid.length
            self.current_playback_time = 0.0
            self.cumulative_times = []
            current_time = 0.0
            for msg in self.mid:
                current_time += msg.time
                self.cumulative_times.append(current_time)
            self.update_time_label(0, self.total_midi_time)
            self.seek_scale.set(0)
            self.status_bar.config(text=f"파일 로드됨: {os.path.basename(file_path)}")
            self._update_button_states()
        except Exception as e:
            messagebox.showerror("파일 오류", f"MIDI 파일 로드 실패:\n{e}")


    def _playback_loop(self):
        print("재생 루프 스레드 시작.")
        if self.mid is None or not rtmidi_available or self.outport is None or self.outport.closed:
            print("재생 루프 시작 조건 미달.")
            self.root.after(0, self._reset_gui_state)
            return

        try:
            start_message_index = 0
            real_start_time = time.time()  # 진짜시작타임 변수 쪽에서 시간 재설정

            if self.current_playback_time > 0 and self.cumulative_times:
                try:
                    temp_mid = mido.MidiFile(self.midi_file_path)
                    messages = temp_mid.play()
                    import bisect
                    start_message_index = bisect.bisect_left(self.cumulative_times, self.current_playback_time - 0.01)

                    self.current_playback_time = self.cumulative_times[start_message_index-1] if start_message_index > 0 and start_message_index <= len(self.cumulative_times) else 0.0

                    if start_message_index >= len(self.cumulative_times) and self.total_midi_time > 0:
                        self.current_playback_time = self.total_midi_time - 0.001
                        start_message_index = len(self.cumulative_times) -1
                        if start_message_index < 0: start_message_index = 0

                    real_start_time = time.time() - self.current_playback_time / self.speed_scale.get()

                except Exception as e:
                    print(f"[ERR]: Bisect 탐색 중 오류 발생 ({e}). 선형 탐색 fallback.")
                    start_message_index = 0
                    for i, cum_time in enumerate(self.cumulative_times):
                        if cum_time >= self.current_playback_time - 0.01:
                            start_message_index = i
                            self.current_playback_time = self.cumulative_times[i-1] if i > 0 else 0.0
                            real_start_time = time.time() - self.current_playback_time / self.speed_scale.get()
                            break
                    if start_message_index >= len(self.cumulative_times) and self.total_midi_time > 0:
                        self.current_playback_time = self.total_midi_time - 0.001
                        start_message_index = len(self.cumulative_times) -1
                        if start_message_index < 0: start_message_index = 0

            try:
                temp_mid = mido.MidiFile(self.midi_file_path)
                msg_iter = iter(temp_mid)
                for _ in range(start_message_index):
                    try:
                        next(msg_iter)
                    except StopIteration:
                        print(f"경고: 시작 인덱스 {start_message_index}까지 메시지를 건너뛰는 중 파일 끝 도달.")
                        break
            except Exception as e:
                print(f"[ERR]: MIDI 파일 다시 열기 오류: {e}")
                self.root.after(0, lambda: messagebox.showerror("재생 오류", f"MIDI 파일을 다시 열 수 없습니다:\n{e}"))
                self.root.after(0, self.stop_midi)
                return

            if self.pedal_mode_enabled.get() is False:
                print("페달 모드 OFF 상태 - 모든 채널에 대해 sustain 해제 메시지 전송")
                for ch in range(16):
                    try:
                        self.outport.send(mido.Message('control_change', channel=ch, control=64, value=0))
                    except Exception as e:
                        print(f"초기 페달 해제 실패 (채널 {ch}): {e}")

            for i, msg in enumerate(msg_iter):
                if self.stop_event.is_set():
                    print("중지 이벤트 수신. 재생 루프 종료.")
                    break

                if self.pause_event.is_set():
                    if rtmidi_available and self.outport is not None and not self.outport.closed:
                        self.notes_paused = list(self.active_notes.items())
                        self.pedal_paused = []

                        for ch in range(16):
                            try:
                                self.outport.send(mido.Message('control_change', channel=ch, control=64, value=0))
                                self.pedal_paused.append(ch)
                            except Exception as e:
                                print(f"일시정지 중 페달 해제 실패 (채널 {ch}): {e}")

                        for (ch, note), real_note in self.notes_paused:
                            try:
                                self.outport.send(mido.Message('note_off', channel=ch, note=real_note, velocity=0))
                            except Exception as e:
                                print(f"일시정지 중 note_off 실패: {e}")
                        self.active_notes.clear()
                    print(f"일시정지됨. 현재 시간: {self.current_playback_time:.2f}s")
                    pause_start_time = time.time()
                    while self.pause_event.is_set() and not self.stop_event.is_set():
                        time.sleep(0.05)

                    if self.stop_event.is_set():
                        print("일시정지 중 중지 이벤트 수신. 재생 루프 종료.")
                        break

                    print("재생 재개.")
                    for ch in self.pedal_paused:
                        try:
                            self.outport.send(mido.Message('control_change', channel=ch, control=64, value=127))
                        except Exception as e:
                            print(f"페달 재설정 실패 (채널 {ch}): {e}")

                    for (ch, original_note), real_note in self.notes_paused:
                        try:
                            self.outport.send(mido.Message('note_on', channel=ch, note=real_note, velocity=int(self.velocity_scale.get())))
                            self.active_notes[(ch, original_note)] = real_note
                        except Exception as e:
                            print(f"note_on 재설정 실패: {e}")
                    pause_duration = time.time() - pause_start_time
                    real_start_time += pause_duration

                target_midi_time_after_msg = self.current_playback_time + msg.time
                target_real_time = real_start_time + target_midi_time_after_msg / self.speed_scale.get()

                timing_variance_ratio = self.timing_variance.get() / 100.0
                jitter = random.uniform(-timing_variance_ratio, timing_variance_ratio)
                adjusted_time = msg.time * (1.0 + jitter) if self.error_mode_enabled.get() else msg.time
                target_midi_time_after_msg = self.current_playback_time + adjusted_time
                target_real_time = real_start_time + target_midi_time_after_msg / self.speed_scale.get()
                sleep_duration = target_real_time - time.time()
                if sleep_duration > 0:
                    time.sleep(sleep_duration)

                if self.pause_event.is_set() or self.stop_event.is_set():
                    print("슬립 후 이벤트 확인 → 일시정지 or 중지 상태. 현재 시간:", self.current_playback_time)
                    if self.pause_event.is_set():
                        self.notes_paused = list(self.active_notes.items())
                        self.pedal_paused = []

                        for ch in range(16):
                            try:
                                self.outport.send(mido.Message('control_change', channel=ch, control=64, value=0))
                                self.pedal_paused.append(ch)
                            except Exception as e:
                                print(f"페달 해제 실패 (채널 {ch}): {e}")

                        for (ch, note), real_note in self.notes_paused:
                            try:
                                self.outport.send(mido.Message('note_off', channel=ch, note=real_note, velocity=0))
                            except Exception as e:
                                print(f"note_off 실패 (ch {ch}, note {note}): {e}")

                        self.active_notes.clear()

                        pause_start_time = time.time()
                        while self.pause_event.is_set() and not self.stop_event.is_set():
                            time.sleep(0.05)

                        if self.stop_event.is_set():
                            print("일시정지 중 중지 수신 → 루프 종료")
                            break

                        print("재생 재개됨")

                        # 다시 재생시 페달 복원
                        for ch in self.pedal_paused:
                            try:
                                self.outport.send(mido.Message('control_change', channel=ch, control=64, value=127))
                            except Exception as e:
                                print(f"[ERR]: 페달 복원 실패 (채널 {ch}): {e}")

                        for (ch, original_note), real_note in self.notes_paused:
                            try:
                                self.outport.send(mido.Message('note_on', channel=ch, note=real_note, velocity=int(self.velocity_scale.get())))
                                self.active_notes[(ch, original_note)] = real_note
                            except Exception as e:
                                print(f"[ERR]: note_on 복원 실패 (채널 {ch}, note {real_note}): {e}")

                        pause_duration = time.time() - pause_start_time
                        real_start_time += pause_duration
                        continue  # 현재 msg 쪽 그냥 넘기고 다음거
                    else:
                        print("중지 상태 도달 → 루프 종료")
                        break

                processed_msg = msg

                if self.error_mode_enabled.get() and (msg.type == 'note_on' or msg.type == 'note_off'):
                    error_chance = self.error_percentage.get()
                    pitch_range = self.error_pitch_range.get()

                    if msg.type == 'note_on' and msg.velocity > 0:
                        if random.random() * 100 < error_chance:
                            deviation = random.randint(-pitch_range, pitch_range)
                            while deviation == 0 and pitch_range > 0:
                                deviation = random.randint(-pitch_range, pitch_range)

                            new_note = msg.note + deviation
                            new_note = max(0, min(127, new_note))

                            if new_note != msg.note:
                                processed_msg = msg.copy(note=new_note)
                                print(f"오타 발생: 원래 음정 {msg.note} (Ch {msg.channel}), 변경된 음정 {new_note} (오차 {deviation}) / 시간: {self.current_playback_time + msg.time:.2f}s")
                                self.active_notes[(msg.channel, msg.note)] = new_note
                            else:
                                self.active_notes[(msg.channel, msg.note)] = msg.note

                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        original_note_on_key = (msg.channel, msg.note)
                        if original_note_on_key in self.active_notes:
                            errored_note = self.active_notes.pop(original_note_on_key)
                            if errored_note != msg.note:
                                processed_msg = msg.copy(note=errored_note)

                if (processed_msg.type == 'note_on' and processed_msg.velocity > 0):
                    scaled_velocity = int(self.velocity_scale.get())
                    processed_msg = processed_msg.copy(velocity=scaled_velocity)

                if rtmidi_available and self.outport is not None and not self.outport.closed:
                    try:
                        # 페달 비활성화 모드일 경우 무시.
                        if self.pedal_mode_enabled.get() is False and processed_msg.type == 'control_change' and processed_msg.control == 64:
                            continue  # sustain pedal

                        if not processed_msg.is_meta and processed_msg.type not in ('sysex', 'unknown_sysex'):
                            self.outport.send(processed_msg)
                    except Exception as e:
                        print(f"[ERR]: MIDI 메시지 전송 오류: {e}")
                        self.root.after(0, self.stop_midi)


                self.current_playback_time += msg.time

                if self.stop_event.is_set() or self.pause_event.is_set():
                    if self.pause_event.is_set():
                        print(f"루프 종료: 일시정지 상태. 현재 시간: {self.current_playback_time:.2f}s")
                    if self.stop_event.is_set():
                        print("루프 종료: 중지 상태.")
                        self.current_playback_time = 0.0
                    break

            if not self.stop_event.is_set() and not self.pause_event.is_set():
                self.current_playback_time = self.total_midi_time
                self.root.after(0, self.stop_midi)

        except Exception as e:
            print(f"[ERR]: 재생 중 예상치 못한 오류 발생: {e}")
            traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("재생 오류", f"재생 중 오류가 발생했습니다:\n{e}"))
            self.root.after(0, self.stop_midi)

        finally:
            self.is_playing = False
            self.is_paused = False
            self.active_notes = {}
            self.root.after(0, self._reset_gui_state)

    def _update_button_states(self):
        valid_port_selected = (
            self.selected_port_name.get() in self.output_ports and
            self.outport is not None and
            not self.outport.closed
        )
        can_play = (
            self.mid is not None and
            rtmidi_available and
            valid_port_selected and
            not self.is_playing and
            not self.is_paused
        )

        self.play_button['state'] = tk.NORMAL if can_play else tk.DISABLED
        self.pause_button['state'] = tk.NORMAL if self.is_playing and not self.is_paused else tk.DISABLED
        self.stop_button['state'] = tk.NORMAL if self.is_playing or self.is_paused else tk.DISABLED

    def _reset_gui_state(self):
        print("[UI]: UI 상태가 초기화 되고 있습니다...")
        self._update_button_states()

        seek_value = (self.current_playback_time / self.total_midi_time * 100) if self.total_midi_time > 0 else 0
        if hasattr(self, 'seek_scale'):
             self.seek_scale.set(seek_value)
        if hasattr(self, 'time_label'):
             self.update_time_label(self.current_playback_time, self.total_midi_time)

        if hasattr(self, 'status_bar'):
             if self.stop_event.is_set() or (self.mid is not None and self.total_midi_time > 0 and abs(self.current_playback_time - self.total_midi_time) < 0.1):
                  if self.stop_event.is_set():
                       status_text = "중지됨."
                  else:
                       status_text = "재생 완료."

                  self.status_bar.config(text=status_text)

                  self.current_playback_time = 0.0
                  if hasattr(self, 'time_label'):
                       self.update_time_label(0, self.total_midi_time)
                  if hasattr(self, 'seek_scale'):
                       self.seek_scale.set(0)

             elif self.is_paused:
                 self.status_bar.config(text="일시정지됨.")
             else:
                  status_text = "준비됨."
                  if self.mid is not None and hasattr(self, 'midi_file_path'):
                       display_name = os.path.basename(self.midi_file_path)
                       if len(display_name) > 40: display_name = display_name[:37] + "..."
                       status_text = f"파일 로드됨: {display_name}"
                  if rtmidi_available and self.outport is not None and not self.outport.closed:
                       status_text += f" | 포트: {self.outport.name}"
                  self.status_bar.config(text=status_text)

        if self.stop_event.is_set():
             self.stop_event.clear()
        if self.pause_event.is_set() and not self.is_playing:
             self.pause_event.clear()
        print("[UI]: UI 가 초기화 되었습니다.")

    def pause_midi(self):
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.is_playing = False
            self.stop_event.set()
            self.pause_event.set()
            self._update_button_states()
            if hasattr(self, 'status_bar'):
                 self.status_bar.config(text="일시정지됨.")

    def stop_midi(self):
        if self.is_playing or self.is_paused:
            print("재생 중지 신호 발생...")
            self.stop_event.set()
            self.pause_event.set()
            self._update_button_states()

            if rtmidi_available and self.outport is not None and not self.outport.closed:
                try:
                    print("중지 시 All Notes Off 및 note_off 메시지 전송 중...")
                    for channel in range(16):
                        # All Notes Off
                        try:
                            self.outport.send(mido.Message('control_change', channel=channel, control=64, value=0))
                        except Exception as e:
                            print(f"Sustain pedal 해제 실패 (채널 {channel}): {e}")
                    # 남아있는 note_off 강제 전송쪽
                    for (channel, note), _ in self.active_notes.items():
                        try:
                            self.outport.send(mido.Message('note_off', channel=channel, note=note, velocity=0))
                        except Exception as e:
                            print(f"[ERR]: note_off 오류: ch={channel}, note={note}, err={e}")
                    print("All Notes Off 완료.")
                except Exception as e:
                    print(f"[ERR]: 오류: All Notes Off 전송 실패: {e}")
            else:
                print("MIDI 포트가 닫혀 있거나 사용 불가.")

            if self.playback_thread is not None and self.playback_thread.is_alive():
                print("재생 스레드 종료 대기 (join)...")
                self.playback_thread.join(timeout=3.0)
                if self.playback_thread.is_alive():
                    print("경고: 재생 스레드가 종료되지 않았습니다.")

            self.playback_thread = None
            self.current_playback_time = 0.0
            self.active_notes.clear()
            self.root.after(0, self._reset_gui_state)


    def save_current_midi(self):
        if self.midi_file_path and os.path.exists(self.midi_file_path):
            title = tk.simpledialog.askstring("MIDI 저장", "저장할 제목을 입력하세요:")
            if title:
                filename = f"{title}.mid"
                save_dir = "./midi"
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename)
                try:
                    with open(self.midi_file_path, "rb") as src, open(save_path, "wb") as dst:
                        dst.write(src.read())
                    messagebox.showinfo("저장 완료", f"{filename} 저장 성공!")
                    self.refresh_saved_midi_list()
                except Exception as e:
                    messagebox.showerror("저장 실패", str(e))
        else:
            messagebox.showwarning("경고", "저장할 MIDI 파일이 없습니다.")



    def _update_speed_display_cmd(self, value):
         self._update_speed_display()
    def _update_speed_display_event(self, event=None):
         self._update_speed_display()
    def _update_speed_display(self):
         if hasattr(self, 'speed_scale') and hasattr(self, 'speed_value_label'):
              speed = self.speed_scale.get()
              self.speed_value_label.config(text=f"{speed:.1f}x")

    def _update_velocity_display_cmd(self, value):
        self._update_velocity_display()
    def _update_velocity_display_event(self, event=None):
        self._update_velocity_display()
    def _update_velocity_display(self):
         if hasattr(self, 'velocity_scale') and hasattr(self, 'velocity_value_label'):
              velocity = int(self.velocity_scale.get())
              self.velocity_value_label.config(text=str(velocity))

    def _update_error_percent_display_cmd(self, value):
        self._update_error_percent_display()
    def _update_error_percent_display_event(self, event=None):
        self._update_error_percent_display()
    def _update_error_percent_display(self):
         if hasattr(self, 'error_percent_scale') and hasattr(self, 'error_percent_value_label'):
              percent = self.error_percent_scale.get()
              self.error_percent_value_label.config(text=f"{percent:.1f}%")

    def _update_error_pitch_display_cmd(self, value):
        self._update_error_pitch_display()
    def _update_error_pitch_display_event(self, event=None):
        self._update_error_pitch_display()
    def _update_error_pitch_display(self):
         if hasattr(self, 'error_pitch_scale') and hasattr(self, 'error_pitch_value_label'):
              pitch = int(self.error_pitch_scale.get())
              self.error_pitch_value_label.config(text=str(pitch))

    def update_seek_bar(self):
        if self.mid is not None and self.total_midi_time > 0:
            display_time = min(self.current_playback_time, self.total_midi_time)
            progress = (display_time / self.total_midi_time) * 100.0

            if hasattr(self, 'seek_scale'):
                if not self.is_playing or abs(self.seek_scale.get() - progress) > 1.5:
                    self.seek_scale.set(progress)

            if hasattr(self, 'time_label'):
                self.update_time_label(display_time, self.total_midi_time)

        else:
            if hasattr(self, 'seek_scale'):
                self.seek_scale.set(0)
            if hasattr(self, 'time_label'):
                self.update_time_label(0, 0)
        self.root.after(100, self.update_seek_bar)


    def format_time(self, seconds):
        if seconds is None or seconds < 0:
             return "00:00"
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02}:{seconds:02}"

    def update_time_label(self, current_sec, total_sec):
         if hasattr(self, 'time_label'):
              self.time_label.config(text=f"{self.format_time(current_sec)} / {self.format_time(total_sec)}")

    def seek_midi_drag(self, value):
        if self.mid is not None and self.total_midi_time > 0:
            target_progress = float(value) / 100.0
            target_time = self.total_midi_time * target_progress
            if hasattr(self, 'time_label'):
                 self.update_time_label(target_time, self.total_midi_time)

    def on_seek_release(self, event):
        if self.mid is not None and self.total_midi_time > 0:
            if hasattr(self, 'seek_scale'):
                 target_progress = self.seek_scale.get() / 100.0
            else:
                 return

            target_time = self.total_midi_time * target_progress

            was_playing = self.is_playing
            was_paused = self.is_paused

            self.stop_midi()

            self.current_playback_time = target_time
            print(f"탐색 완료. 새 시작 시간: {self.current_playback_time:.2f}s")

            if hasattr(self, 'time_label'):
                 self.update_time_label(self.current_playback_time, self.total_midi_time)
            if hasattr(self, 'seek_scale'):
                 self.seek_scale.set(target_progress * 100)

            if was_playing or was_paused:
                 self.play_midi()

    def set_theme(self, theme_name):
        if self.themed_style_available and self.themed_style is not None:
            try:
                self.themed_style.set_theme(theme_name)
                if hasattr(self, 'status_bar'):
                     self.status_bar.config(text=f"테마 변경됨: {theme_name}")
                print(f"테마 변경됨: {theme_name}")
            except Exception as e:
                print(f"[ERR]: 테마 '{theme_name}' 적용 오류: {e}")
                if hasattr(self, 'status_bar'):
                     self.status_bar.config(text=f"테마 적용 오류: {theme_name} - {e}")
        else:
            print("ttkthemes 기능이 사용 불가능하여 테마를 변경할 수 없습니다.")

    def on_closing(self):
        print("애플리케이션 종료 시퀀스 시작.")
        self.stop_midi()
        self.close_midi_port()
        self.root.destroy()
        print("애플리케이션 종료 완료.")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(10, self.update_seek_bar)
        self.root.mainloop()

if __name__ == "__main__":
    def start_app():
        splash.destroy()  # 스플래시 창 destory
        root = tk.Tk()
        app = MidiPlayerApp(root)
        app.run()

    splash = tk.Tk()
    splash.title("Riha Studio")
    splash.geometry("300x100")
    splash.resizable(False, False)
    # ------------ 창 구성 ------------
    splash_label = ttk.Label(splash, text="잠시만 기다려주세요. 정보를 불러오고 있어요", anchor="center")
    splash_label.pack(pady=(15, 5))
    progress = ttk.Progressbar(splash, mode='indeterminate')
    progress.pack(padx=20, pady=10, fill=tk.X)
    progress.start(10)
    # ------------ 스플래시 After ------------
    splash.after(1000, start_app)  # 1초 후 main 앱 실행
    splash.mainloop()