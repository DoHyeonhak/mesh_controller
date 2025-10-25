import tkinter as tk
from tkinter import ttk, messagebox
from serial_controller import SerialController
from app_model import AppModel
from app_controller import AppController


# Class for View
class App:
    """애플리케이션의 UI를 담당하는 View 클래스"""

    def __init__(self, root, model):
        self.root = root
        self.model = model
        self.controller = None  # Controller는 나중에 설정

        self.root.title("LED & Group Control with Logging")
        self.root.geometry("760x800")

        self._create_widgets()
        self._populate_initial_data()

    def set_controller(self, controller):
        """컨트롤러를 설정하고 위젯 커맨드를 연결합니다."""
        self.controller = controller
        self._bind_commands()

    def log_message(self, message):
        """로그 창에 메시지를 표시합니다."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    # UI Creation & Update Methods
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
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        # --- Main Layout Frames ---
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

        # --- Connection Frame ---
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.port_combo = ttk.Combobox(connection_frame) # Values set later
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(connection_frame, text="Baudrate:").grid(row=0, column=2, padx=5, pady=5)
        self.baud_entry = ttk.Entry(connection_frame)
        self.baud_entry.grid(row=0, column=3, padx=5, pady=5)
        self.baud_entry.insert(0, "115200")
        self.connect_button = ttk.Button(connection_frame, text="Connect")
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)

        # --- Node Management Frame ---
        node_input_frame = ttk.Frame(node_frame)
        node_input_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(node_input_frame, text="Address (e.g., 45 or 45-50):").pack(side="left")
        self.node_entry = ttk.Entry(node_input_frame)
        self.node_entry.pack(side="left", fill="x", expand=True)
        node_btn_frame = ttk.Frame(node_frame)
        node_btn_frame.pack(fill="x", padx=5)
        self.add_node_button = ttk.Button(node_btn_frame, text="Add")
        self.add_node_button.pack(side="left", expand=True, fill="x")
        self.delete_node_button = ttk.Button(node_btn_frame, text="Delete")
        self.delete_node_button.pack(side="left", expand=True, fill="x")
        list_frame_node = ttk.Frame(node_frame)
        list_frame_node.pack(fill="both", expand=True, padx=5, pady=5)
        self.node_listbox = tk.Listbox(list_frame_node, selectmode=tk.SINGLE, exportselection=False)
        self.node_listbox.pack(side="left", fill="both", expand=True)
        node_scrollbar = ttk.Scrollbar(list_frame_node, orient=tk.VERTICAL, command=self.node_listbox.yview)
        node_scrollbar.pack(side="right", fill="y")
        self.node_listbox.config(yscrollcommand=node_scrollbar.set)

        # --- Group Management Frame ---
        self.group_listbox = tk.Listbox(group_frame, selectmode=tk.EXTENDED, exportselection=False)
        group_scrollbar = ttk.Scrollbar(group_frame, orient=tk.VERTICAL, command=self.group_listbox.yview)
        self.group_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        group_scrollbar.pack(side="right", fill="y")
        self.group_listbox.config(yscrollcommand=group_scrollbar.set)
        group_btn_frame = ttk.Frame(group_frame)
        group_btn_frame.pack(fill="x", padx=5, pady=(0,5))
        self.add_to_group_button = ttk.Button(group_btn_frame, text="Add Node to Group(s)")
        self.add_to_group_button.pack(side="left", expand=True, fill="x")
        self.load_txt_button = ttk.Button(group_btn_frame, text="Load TXT & Set")
        self.load_txt_button.pack(side="left", expand=True, fill="x")

        # --- LED Control Frame ---
        self.led_on_button = ttk.Button(control_frame, text="LED ON")
        self.led_on_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.led_off_button = ttk.Button(control_frame, text="LED OFF")
        self.led_off_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(control_frame, text="Length (2-100):").grid(row=0, column=2, padx=(10, 0), pady=5, sticky="e")
        self.leds_length_entry = ttk.Entry(control_frame, width=10)
        self.leds_length_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.leds_length_entry.insert(0, "80")
        self.leds_on_button = ttk.Button(control_frame, text="LEDs ON (set_leds)")
        self.leds_on_button.grid(row=0, column=4, padx=5, pady=5, sticky="ew")
        self.leds_off_button = ttk.Button(control_frame, text="LEDs OFF (set_leds)")
        self.leds_off_button.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        ttk.Label(control_frame, text="Interval (s):").grid(row=1, column=0)
        self.interval_entry = ttk.Entry(control_frame, width=10)
        self.interval_entry.grid(row=1, column=1)
        self.interval_entry.insert(0, "1")
        self.start_loop_button = ttk.Button(control_frame, text="Start Loop")
        self.start_loop_button.grid(row=1, column=2, padx=5, sticky="ew")
        self.stop_loop_button = ttk.Button(control_frame, text="Stop Loop")
        self.stop_loop_button.grid(row=1, column=3, padx=5, sticky="ew")
        control_frame.grid_columnconfigure((0,1,2,3), weight=1)

        # --- Test Commands Frame ---
        node_test_frame = ttk.LabelFrame(test_frame, text="Node Specific Tests")
        node_test_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        gw_test_frame = ttk.LabelFrame(test_frame, text="Gateway Tests")
        gw_test_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # --- Node Specific Tests ---
        ttk.Label(node_test_frame, text="Node Addr:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.node_test_addr_entry = ttk.Entry(node_test_frame, width=15)
        self.node_test_addr_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=3, sticky="ew")
        self.test_rtt_button = ttk.Button(node_test_frame, text="test_rtt")
        self.test_rtt_button.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        self.test_latency_button = ttk.Button(node_test_frame, text="test_latency")
        self.test_latency_button.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.test_hop_button = ttk.Button(node_test_frame, text="test_hop")
        self.test_hop_button.grid(row=1, column=2, sticky="ew", padx=5, pady=2)
        self.test_rssi_button = ttk.Button(node_test_frame, text="test_rssi")
        self.test_rssi_button.grid(row=1, column=3, sticky="ew", padx=5, pady=2)
        self.get_node_tx_button = ttk.Button(node_test_frame, text="get_node_txpower")
        self.get_node_tx_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        self.test_all_button = ttk.Button(node_test_frame, text="test_all")
        self.test_all_button.grid(row=2, column=2, columnspan=2, sticky="ew", padx=5, pady=2)
        set_power_frame = ttk.Frame(node_test_frame)
        set_power_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=2)
        ttk.Label(set_power_frame, text="TxPower (-32~10):").pack(side="left", padx=5)
        self.node_txpower_entry = ttk.Entry(set_power_frame, width=10)
        self.node_txpower_entry.pack(side="left", padx=5)
        self.set_node_tx_button = ttk.Button(set_power_frame, text="set_node_txpower")
        self.set_node_tx_button.pack(side="left", padx=5, fill='x', expand=True)
        netoff_frame = ttk.Frame(node_test_frame)
        netoff_frame.grid(row=4, column=0, columnspan=4, sticky='ew', pady=2)
        ttk.Label(netoff_frame, text="NetOff Time(s):").pack(side="left", padx=(5,0))
        self.netoff_time_entry = ttk.Entry(netoff_frame, width=7)
        self.netoff_time_entry.pack(side="left", padx=5)
        self.netoff_time_entry.insert(0, "10")
        ttk.Label(netoff_frame, text="LED Mode:").pack(side="left", padx=(5,0))
        self.netoff_led_combo = ttk.Combobox(netoff_frame, width=8, state="readonly", values=["0: OFF", "1: ON", "2: BLINK"])
        self.netoff_led_combo.pack(side="left", padx=5)
        self.netoff_led_combo.current(0)
        self.network_off_button = ttk.Button(netoff_frame, text="network_off")
        self.network_off_button.pack(side="left", padx=5, fill='x', expand=True)

        # --- Gateway Tests ---
        self.get_gw_tx_button = ttk.Button(gw_test_frame, text="get_gw_txpower")
        self.get_gw_tx_button.pack(fill="x", padx=5, pady=2)
        gw_set_frame = ttk.Frame(gw_test_frame)
        gw_set_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(gw_set_frame, text="TxPower (-32~10):").pack(side="left")
        self.gw_txpower_entry = ttk.Entry(gw_set_frame, width=10)
        self.gw_txpower_entry.pack(side="left", padx=5)
        self.set_gw_tx_button = ttk.Button(gw_set_frame, text="set_gw_txpower")
        self.set_gw_tx_button.pack(side="left", fill="x", expand=True)

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
        self.capture_button = ttk.Button(capture_control_frame, text="Start Capture")
        self.capture_button.pack(side="left", padx=5)
        self.save_led_button = ttk.Button(capture_control_frame, text="Save LED Log")
        self.save_led_button.pack(side="left", padx=5)
        self.save_led_button.state(['disabled'])
        self.save_test_button = ttk.Button(capture_control_frame, text="Save Test Log")
        self.save_test_button.pack(side="left", padx=5)
        self.save_test_button.state(['disabled'])
        self.capture_status_label = ttk.Label(capture_control_frame, text="Capture OFF")
        self.capture_status_label.pack(side="left", padx=10)

    def _bind_commands(self):
        """컨트롤러의 메소드에 위젯 이벤트를 바인딩합니다."""
        self.connect_button.config(command=self.controller.connect_serial)
        self.add_node_button.config(command=self.controller.add_node)
        self.delete_node_button.config(command=self.controller.delete_node)
        self.node_listbox.bind("<Button-1>", self.controller.toggle_node_selection)
        self.add_to_group_button.config(command=self.controller.add_node_to_groups)
        self.load_txt_button.config(command=self.controller.load_txt_and_set_groups)
        self.led_on_button.config(command=lambda: self.controller.set_led_state(1))
        self.led_off_button.config(command=lambda: self.controller.set_led_state(0))
        self.leds_on_button.config(command=lambda: self.controller.run_set_leds(1))
        self.leds_off_button.config(command=lambda: self.controller.run_set_leds(0))
        self.start_loop_button.config(command=self.controller.start_toggle_loop)
        self.stop_loop_button.config(command=self.controller.stop_loop)
        self.test_rtt_button.config(command=self.controller.run_test_rtt)
        self.test_latency_button.config(command=self.controller.run_test_latency)
        self.test_hop_button.config(command=self.controller.run_test_hop)
        self.test_rssi_button.config(command=self.controller.run_test_rssi)
        self.get_node_tx_button.config(command=self.controller.run_get_node_txpower)
        self.test_all_button.config(command=self.controller.run_test_all)
        self.set_node_tx_button.config(command=self.controller.run_set_node_txpower)
        self.network_off_button.config(command=self.controller.run_network_off)
        self.get_gw_tx_button.config(command=self.controller.run_get_gw_txpower)
        self.set_gw_tx_button.config(command=self.controller.run_set_gw_txpower)
        self.capture_button.config(command=self.controller.toggle_capture)
        self.save_led_button.config(command=self.controller.save_led_data)
        self.save_test_button.config(command=self.controller.save_test_data)

    def _populate_initial_data(self):
        """모델의 데이터로 UI를 채웁니다."""
        self.port_combo['values'] = SerialController.scan_ports()
        for group in self.model.groups:
            self.group_listbox.insert(tk.END, str(group))

    def update_node_listbox(self):
        """모델의 노드 목록을 기반으로 UI를 업데이트합니다."""
        self.node_listbox.delete(0, tk.END)
        for node in self.model.nodes:
            self.node_listbox.insert(tk.END, node)

    def update_connection_status(self, connected):
        """시리얼 연결 상태에 따라 UI를 업데이트합니다."""
        if connected:
            self.connect_button.config(text="Disconnect", command=self.controller.disconnect_serial)
        else:
            self.connect_button.config(text="Connect", command=self.controller.connect_serial)

    def update_capture_status(self, text):
        """캡처 상태 레이블을 업데이트합니다."""
        self.capture_status_label.config(text=text)

    def update_capture_state(self, is_capturing):
        """캡처 상태에 따라 UI(버튼, 레이블)를 업데이트합니다."""
        if is_capturing:
            self.capture_button.config(text="Stop Capture")
            self.update_capture_status("Capturing... (0 records)")
            self.save_led_button.state(['disabled'])
            self.save_test_button.state(['disabled'])
        else:
            self.capture_button.config(text="Start Capture")
            total_records = len(self.model.captured_led_res) + len(self.model.captured_test_res)
            self.update_capture_status(f"Capture STOPPED ({total_records} records)")
            if self.model.captured_led_res:
                self.save_led_button.state(['!disabled'])
            if self.model.captured_test_res:
                self.save_test_button.state(['!disabled'])


if __name__ == "__main__":
    root = tk.Tk()
    
    model = AppModel()

    view = App(root, model)
    serial = SerialController(root, log_callback=view.log_message)
    controller = AppController(model, serial, view)
    
    view.set_controller(controller)
    
    root.mainloop()
