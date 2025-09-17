import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from serial_controller import SerialController # serial_controller.py 파일 import
from datetime import datetime
import pandas as pd # pandas 라이브러리 import
import re # 정규표현식 라이브러리 import

class App:
    """애플리케이션 GUI와 비즈니스 로직을 담당하는 클래스"""
    def __init__(self, root):
        self.root = root
        self.root.title("LED & Group Control with Logging")
        self.root.geometry("760x800")
        
        # 데이터 모델
        self.nodes = []
        self.groups = list(range(0xF000, 0xFFFF))
        self.loop_running = False
        self.loop_state = False
        
        # 로깅 관련 속성
        self.is_capturing = False
        self.captured_led_res = []
        self.captured_test_res = []

        # 시리얼 컨트롤러 객체 생성 및 콜백 등록
        self.serial = SerialController(
            root, 
            log_callback=self.log_message, 
            data_callback=self.handle_serial_data # 데이터 처리 콜백 연결
        )

        # UI 생성
        self._create_widgets()
        self._populate_initial_data()
        
    def handle_serial_data(self, data):
        """SerialController로부터 구조화된 데이터를 받아 처리하는 콜백"""
        if not self.is_capturing:
            return

        cmd = data.get("command", "")
        
        # 'set_led' 명령 결과 저장
        if cmd.startswith("set_led"):
            self.captured_led_res.append(data)
        
        # 'test_all' 명령 결과 파싱 후 저장
        elif cmd.startswith("test_all"):
            response_str = data.get('filtered_response', '')
            parsed_results = self._parse_test_all_response(response_str)
            
            # 원본 데이터에 파싱된 결과 추가
            record = {**data, **parsed_results}
            self.captured_test_res.append(record)

        # 캡처 상태 레이블 업데이트
        total_records = len(self.captured_led_res) + len(self.captured_test_res)
        self.capture_status_label.config(text=f"Capturing... ({total_records} records)")

    # 응답 파싱을 위한 헬퍼 메소드
    def _parse_test_all_response(self, response_str):
        """test_all 명령어의 응답 문자열을 파싱하여 딕셔너리로 반환합니다."""
        if "no response" in response_str.lower():
            return {
                'rtt': -1,
                'latency': -1,
                'down_hop': -1,
                'up_hop': -1,
                'rssi': -1
            }

        results = {
            'rtt': -1,
            'latency': -1,
            'down_hop': -1,
            'up_hop': -1,
            'rssi': -1
        }
        
        # 정규표현식을 사용하여 값 추출
        rtt_match = re.search(r"rtt=([\d\.]+)", response_str)
        if rtt_match:
            results['rtt'] = float(rtt_match.group(1))

        latency_match = re.search(r"latency=([\d\.]+)", response_str)
        if latency_match:
            results['latency'] = float(latency_match.group(1))

        hop_match = re.search(r"down hop=(\d+), up hop=(\d+)", response_str)
        if hop_match:
            results['down_hop'] = int(hop_match.group(1))
            results['up_hop'] = int(hop_match.group(2))

        rssi_match = re.search(r"rssi=(-?\d+)", response_str)
        if rssi_match:
            results['rssi'] = int(rssi_match.group(1))
            
        return results

    def log_message(self, message):
        """SerialController로부터 메시지를 받아 로그 창에 표시"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _create_widgets(self):
        """애플리케이션의 모든 위젯을 생성하고 배치합니다."""
        main_canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        main_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollable_frame = ttk.Frame(main_canvas)
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(
                scrollregion=main_canvas.bbox("all")
            )
        )
        connection_frame = ttk.LabelFrame(scrollable_frame, text="Connection")
        node_frame = ttk.LabelFrame(scrollable_frame, text="Node Management")
        group_frame = ttk.LabelFrame(scrollable_frame, text="Group Management")
        control_frame = ttk.LabelFrame(scrollable_frame, text="LED Control")
        test_frame = ttk.LabelFrame(scrollable_frame, text="Test Commands")
        log_frame = ttk.LabelFrame(scrollable_frame, text="Log & Capture")
        connection_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        node_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        group_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        control_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        test_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        log_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        scrollable_frame.grid_rowconfigure(1, weight=1)
        scrollable_frame.grid_rowconfigure(4, weight=2)
        scrollable_frame.grid_columnconfigure(0, weight=1)
        scrollable_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.port_combo = ttk.Combobox(connection_frame, values=self.serial.scan_ports())
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(connection_frame, text="Baudrate:").grid(row=0, column=2, padx=5, pady=5)
        self.baud_entry = ttk.Entry(connection_frame)
        self.baud_entry.grid(row=0, column=3, padx=5, pady=5)
        self.baud_entry.insert(0, "115200")
        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self._connect_serial)
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)
        node_input_frame = ttk.Frame(node_frame)
        node_input_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(node_input_frame, text="Address (e.g., 45 or 45-50):").pack(side="left")
        self.node_entry = ttk.Entry(node_input_frame)
        self.node_entry.pack(side="left", fill="x", expand=True)
        node_btn_frame = ttk.Frame(node_frame)
        node_btn_frame.pack(fill="x", padx=5)
        ttk.Button(node_btn_frame, text="Add", command=self._add_node).pack(side="left", expand=True, fill="x")
        ttk.Button(node_btn_frame, text="Delete", command=self._delete_node).pack(side="left", expand=True, fill="x")
        list_frame_node = ttk.Frame(node_frame)
        list_frame_node.pack(fill="both", expand=True, padx=5, pady=5)
        self.node_listbox = tk.Listbox(list_frame_node, selectmode=tk.SINGLE, exportselection=False)
        self.node_listbox.pack(side="left", fill="both", expand=True)
        node_scrollbar = ttk.Scrollbar(list_frame_node, orient=tk.VERTICAL, command=self.node_listbox.yview)
        node_scrollbar.pack(side="right", fill="y")
        self.node_listbox.config(yscrollcommand=node_scrollbar.set)
        self.node_listbox.bind("<Button-1>", self._toggle_node_selection)
        self.group_listbox = tk.Listbox(group_frame, selectmode=tk.EXTENDED, exportselection=False)
        group_scrollbar = ttk.Scrollbar(group_frame, orient=tk.VERTICAL, command=self.group_listbox.yview)
        self.group_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        group_scrollbar.pack(side="right", fill="y")
        self.group_listbox.config(yscrollcommand=group_scrollbar.set)
        group_btn_frame = ttk.Frame(group_frame)
        group_btn_frame.pack(fill="x", padx=5, pady=(0,5))
        ttk.Button(group_btn_frame, text="Add Node to Group(s)", command=self._add_node_to_groups).pack(side="left", expand=True, fill="x")
        ttk.Button(group_btn_frame, text="Load TXT & Set", command=self._load_txt_and_set_groups).pack(side="left", expand=True, fill="x")
        ttk.Button(control_frame, text="LED ON", command=lambda: self._set_led_state(1)).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(control_frame, text="LED OFF", command=lambda: self._set_led_state(0)).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(control_frame, text="Interval (s):").grid(row=1, column=0)
        self.interval_entry = ttk.Entry(control_frame, width=10)
        self.interval_entry.grid(row=1, column=1)
        self.interval_entry.insert(0, "1")
        ttk.Button(control_frame, text="Start Loop", command=self._start_toggle_loop).grid(row=1, column=2, padx=5, sticky="ew")
        ttk.Button(control_frame, text="Stop Loop", command=self._stop_loop).grid(row=1, column=3, padx=5, sticky="ew")
        control_frame.grid_columnconfigure((0,1,2,3), weight=1)
        node_test_frame = ttk.LabelFrame(test_frame, text="Node Specific Tests")
        node_test_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        ttk.Label(node_test_frame, text="Node Addr:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.node_test_addr_entry = ttk.Entry(node_test_frame, width=15)
        self.node_test_addr_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=3, sticky="ew")
        ttk.Button(node_test_frame, text="test_rtt", command=self._run_test_rtt).grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        ttk.Button(node_test_frame, text="test_latency", command=self._run_test_latency).grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        ttk.Button(node_test_frame, text="test_hop", command=self._run_test_hop).grid(row=1, column=2, sticky="ew", padx=5, pady=2)
        ttk.Button(node_test_frame, text="test_rssi", command=self._run_test_rssi).grid(row=1, column=3, sticky="ew", padx=5, pady=2)
        ttk.Button(node_test_frame, text="get_node_txpower", command=self._run_get_node_txpower).grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        ttk.Button(node_test_frame, text="test_all", command=self._run_test_all).grid(row=2, column=2, columnspan=2, sticky="ew", padx=5, pady=2)
        set_power_frame = ttk.Frame(node_test_frame)
        set_power_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=2)
        ttk.Label(set_power_frame, text="TxPower (-32~10):").pack(side="left", padx=5)
        self.node_txpower_entry = ttk.Entry(set_power_frame, width=10)
        self.node_txpower_entry.pack(side="left", padx=5)
        ttk.Button(set_power_frame, text="set_node_txpower", command=self._run_set_node_txpower).pack(side="left", padx=5, fill='x', expand=True)
        gw_test_frame = ttk.LabelFrame(test_frame, text="Gateway Tests")
        gw_test_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        ttk.Button(gw_test_frame, text="get_gw_txpower", command=self._run_get_gw_txpower).pack(fill="x", padx=5, pady=2)
        gw_set_frame = ttk.Frame(gw_test_frame)
        gw_set_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(gw_set_frame, text="TxPower (-32~10):").pack(side="left")
        self.gw_txpower_entry = ttk.Entry(gw_set_frame, width=10)
        self.gw_txpower_entry.pack(side="left", padx=5)
        ttk.Button(gw_set_frame, text="set_gw_txpower", command=self._run_set_gw_txpower).pack(side="left", fill="x", expand=True)

        # --- Log & Capture Frame ---
        log_display_frame = ttk.Frame(log_frame)
        log_display_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_display_frame, height=10)
        log_scrollbar = ttk.Scrollbar(log_display_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        log_scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        capture_control_frame = ttk.Frame(log_frame)
        capture_control_frame.pack(fill="x", padx=5, pady=5)
        self.capture_button = ttk.Button(capture_control_frame, text="Start Capture", command=self._toggle_capture)
        self.capture_button.pack(side="left", padx=5)
        
        # <<< CHANGED: Save 버튼 UI 변경 >>>
        self.save_led_button = ttk.Button(capture_control_frame, text="Save LED Log", command=self._save_led_data)
        self.save_led_button.pack(side="left", padx=5)
        self.save_led_button.state(['disabled'])

        self.save_test_button = ttk.Button(capture_control_frame, text="Save Test Log", command=self._save_test_data)
        self.save_test_button.pack(side="left", padx=5)
        self.save_test_button.state(['disabled'])

        self.capture_status_label = ttk.Label(capture_control_frame, text="Capture OFF")
        self.capture_status_label.pack(side="left", padx=10)
    
    def _populate_initial_data(self):
        for group in self.groups:
            self.group_listbox.insert(tk.END, str(group))
    def _connect_serial(self):
        port = self.port_combo.get()
        baud = self.baud_entry.get()
        if not port:
            messagebox.showerror("Error", "COM 포트를 선택하세요.")
            return
        if self.serial.connect(port, baud):
            self.connect_button.config(text="Disconnect")
            self.connect_button.config(command=self._disconnect_serial)
        else:
            messagebox.showerror("Error", "연결에 실패했습니다. 로그를 확인하세요.")
    def _disconnect_serial(self):
        self.serial.disconnect()
        self.connect_button.config(text="Connect")
        self.connect_button.config(command=self._connect_serial)
    def _add_node(self):
        text = self.node_entry.get().strip()
        if not text:
            messagebox.showerror("Error", "주소를 입력하세요.")
            return
        try:
            if '-' in text:
                start, end = map(int, text.split('-'))
                new_nodes = [str(n) for n in range(start, end + 1)]
            else:
                new_nodes = [str(int(text))]
        except ValueError:
            messagebox.showerror("Error", "잘못된 숫자 형식입니다.")
            return
        added_count = 0
        for node in new_nodes:
            if node not in self.nodes:
                self.nodes.append(node)
                added_count += 1
        if added_count > 0:
            self.nodes.sort(key=int)
            self._update_node_listbox()
            self.log_message(f"[INFO] {added_count}개의 노드가 추가되었습니다.")
        else:
            messagebox.showinfo("Info", "이미 존재하는 노드입니다.")
        self.node_entry.delete(0, tk.END)
    def _delete_node(self):
        selected_idx = self.node_listbox.curselection()
        if not selected_idx:
            messagebox.showerror("Error", "삭제할 노드를 선택하세요.")
            return
        address = self.node_listbox.get(selected_idx[0])
        self.nodes.remove(address)
        self._update_node_listbox()
        self.log_message(f"[INFO] 노드 {address} 삭제됨")
    def _update_node_listbox(self):
        self.node_listbox.delete(0, tk.END)
        for node in self.nodes:
            self.node_listbox.insert(tk.END, node)
    def _add_node_to_groups(self):
        node_idx = self.node_listbox.curselection()
        if len(node_idx) != 1:
            messagebox.showerror("Error", "노드를 하나만 선택하세요.")
            return
        group_indices = self.group_listbox.curselection()
        if not group_indices:
            messagebox.showerror("Error", "하나 이상의 그룹을 선택하세요.")
            return
        node_addr = self.node_listbox.get(node_idx[0])
        group_addrs = [self.group_listbox.get(i) for i in group_indices]
        cmd = f"set_group({node_addr},{','.join(group_addrs)})"
        self.serial.send_command(cmd)
    def _load_txt_and_set_groups(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not filepath: return
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line: continue
                    node_part, groups_part = [x.strip() for x in line.split(':', 1)]
                    groups_str = ",".join([g.strip() for g in groups_part.split(',') if g.strip().isdigit()])
                    if groups_str:
                        cmd = f"set_group({node_part},{groups_str})"
                        self.serial.send_command(cmd)
                        self.root.update()
                        self.root.after(100)
        except Exception as e:
            messagebox.showerror("Error", f"파일 처리 중 오류: {e}")
    def _get_selected_addresses(self):
        addresses = []
        node_idx = self.node_listbox.curselection()
        group_indices = self.group_listbox.curselection()
        if node_idx:
            addresses.append(self.node_listbox.get(node_idx[0]))
        elif group_indices:
            for i in group_indices:
                addresses.append(self.group_listbox.get(i))
        return addresses
    def _set_led_state(self, state):
        addresses = self._get_selected_addresses()
        if not addresses:
            messagebox.showerror("Error", "노드 또는 그룹을 선택하세요.")
            return
        for addr in addresses:
            cmd = f"set_led({addr},{state})"
            self.serial.send_command(cmd)
    def _start_toggle_loop(self):
        try:
            self.interval = float(self.interval_entry.get())
            if self.interval <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "유효한 간격(초)을 입력하세요. (예: 0.5)")
            return
        if not self._get_selected_addresses():
            messagebox.showerror("Error", "루프를 실행할 노드 또는 그룹을 선택하세요.")
            return
        self.loop_running = True
        self.log_message("[INFO] 반복 실행 시작")
        self._toggle_loop()
    def _stop_loop(self):
        self.loop_running = False
        self.log_message("[INFO] 반복 실행 중지")
    def _toggle_loop(self):
        if not self.loop_running: return
        state = 1 if not self.loop_state else 0
        self.loop_state = not self.loop_state
        self._set_led_state(state)
        self.root.after(int(self.interval * 1000), self._toggle_loop)
    def _toggle_node_selection(self, event):
        widget = event.widget
        clicked_index = widget.nearest(event.y)
        if clicked_index in widget.curselection():
            widget.selection_clear(clicked_index)
        else:
            widget.selection_clear(0, tk.END)
            widget.selection_set(clicked_index)
        return "break"
    def _run_test_all(self):
        address = self._get_node_address_for_test("test_all")
        if address:
            cmd = f"test_all({address})"
            self.serial.send_command(cmd)
    def _get_node_address_for_test(self, command_name):
        addr_input = self.node_test_addr_entry.get().strip()
        if addr_input:
            return addr_input
        else:
            selected_nodes = self.node_listbox.curselection()
            if not selected_nodes:
                messagebox.showerror("Error", f"노드 주소를 입력하거나 리스트에서 노드를 선택하세요 ({command_name}).")
                return None
            return self.node_listbox.get(selected_nodes[0])
    def _run_test_rtt(self):
        address = self._get_node_address_for_test("test_rtt")
        if address:
            cmd = f"test_rtt({address})"
            self.serial.send_command(cmd)
    def _run_test_latency(self):
        address = self._get_node_address_for_test("test_latency")
        if address:
            cmd = f"test_latency({address})"
            self.serial.send_command(cmd)
    def _run_test_hop(self):
        address = self._get_node_address_for_test("test_hop")
        if address:
            cmd = f"test_hop({address})"
            self.serial.send_command(cmd)
    def _run_test_rssi(self):
        address = self._get_node_address_for_test("test_rssi")
        if address:
            cmd = f"test_rssi({address})"
            self.serial.send_command(cmd)
    def _run_get_node_txpower(self):
        address = self._get_node_address_for_test("get_node_txpower")
        if address:
            cmd = f"get_node_txpower({address})"
            self.serial.send_command(cmd)
    def _run_set_node_txpower(self):
        address = self._get_node_address_for_test("set_node_txpower")
        if not address:
            return
        power_str = self.node_txpower_entry.get().strip()
        try:
            power = int(power_str)
            if power < -32 or power > 10:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "TxPower 값은 -32에서 10 사이의 정수여야 합니다.")
            return
        cmd = f"set_node_txpower({address},{power})"
        self.serial.send_command(cmd)
    def _run_get_gw_txpower(self):
        cmd = "get_gw_txpower()"
        self.serial.send_command(cmd)
    def _run_set_gw_txpower(self):
        power_str = self.gw_txpower_entry.get().strip()
        try:
            power = int(power_str)
            if power < -32 or power > 10:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "TxPower 값은 -32에서 10 사이의 정수여야 합니다.")
            return
        cmd = f"set_gw_txpower({power})"
        self.serial.send_command(cmd)

    # --- 로깅/캡처 관련 메소드 ---
    # 캡처 시작/중지 로직 수정
    def _toggle_capture(self):
        self.is_capturing = not self.is_capturing
        if self.is_capturing:
            # 캡처 시작: 데이터 리스트 초기화
            self.captured_led_res.clear()
            self.captured_test_res.clear()
            
            self.capture_button.config(text="Stop Capture")
            self.capture_status_label.config(text="Capturing... (0 records)")
            self.save_led_button.state(['disabled'])
            self.save_test_button.state(['disabled'])
        else:
            # 캡처 중지
            self.capture_button.config(text="Start Capture")
            total_records = len(self.captured_led_res) + len(self.captured_test_res)
            self.capture_status_label.config(text=f"Capture STOPPED ({total_records} records)")
            
            # 데이터가 있으면 해당 저장 버튼 활성화
            if self.captured_led_res:
                self.save_led_button.state(['!disabled'])
            if self.captured_test_res:
                self.save_test_button.state(['!disabled'])

    # LED 데이터 저장 메소드
    def _save_led_data(self):
        if not self.captured_led_res:
            messagebox.showinfo("Info", "저장할 LED 데이터가 없습니다.")
            return
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Save LED Log As"
            )
            if not filepath:
                return

            df = pd.DataFrame(self.captured_led_res)
            df['request_timestamp'] = df['request_time'].apply(
                lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            )
            df['response_timestamp'] = df['response_time'].apply(
                lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            )
            df_to_save = df[[
                'request_timestamp',
                'response_timestamp',
                'response_gap_ms',
                'command',
                'success',
                'filtered_response'
            ]]
            df_to_save.to_excel(filepath, index=False, engine='openpyxl')
            
            self.log_message(f"[INFO] LED 로그가 성공적으로 저장되었습니다: {filepath}")
            messagebox.showinfo("Success", f"LED 로그가 성공적으로 저장되었습니다:\n{filepath}")
            
            self.captured_led_res.clear()
            self.save_led_button.state(['disabled'])
            total_records = len(self.captured_led_res) + len(self.captured_test_res)
            self.capture_status_label.config(text=f"Capture STOPPED ({total_records} records)")

        except Exception as e:
            self.log_message(f"[ERROR] LED 로그 저장 실패: {e}")
            messagebox.showerror("Error", f"LED 로그 저장 중 오류가 발생했습니다:\n{e}")

    # Test 데이터 저장 메소드
    def _save_test_data(self):
        if not self.captured_test_res:
            messagebox.showinfo("Info", "저장할 Test 데이터가 없습니다.")
            return
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Save Test Log As"
            )
            if not filepath:
                return

            df = pd.DataFrame(self.captured_test_res)
            df['request_timestamp'] = df['request_time'].apply(
                lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            )
            df['response_timestamp'] = df['response_time'].apply(
                lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            )
            
            # 파싱된 열을 포함하여 저장할 열 목록 정의
            df_to_save = df[[
                'request_timestamp',
                'response_timestamp',
                'response_gap_ms',
                'command',
                'success',
                'filtered_response',
                'rtt',
                'latency',
                'down_hop',
                'up_hop',
                'rssi'
            ]]
            df_to_save.to_excel(filepath, index=False, engine='openpyxl')
            
            self.log_message(f"[INFO] Test 로그가 성공적으로 저장되었습니다: {filepath}")
            messagebox.showinfo("Success", f"Test 로그가 성공적으로 저장되었습니다:\n{filepath}")
            
            self.captured_test_res.clear()
            self.save_test_button.state(['disabled'])
            total_records = len(self.captured_led_res) + len(self.captured_test_res)
            self.capture_status_label.config(text=f"Capture STOPPED ({total_records} records)")

        except Exception as e:
            self.log_message(f"[ERROR] Test 로그 저장 실패: {e}")
            messagebox.showerror("Error", f"Test 로그 저장 중 오류가 발생했습니다:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()