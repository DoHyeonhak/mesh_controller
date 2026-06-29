import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from serial_controller import SerialController
from app_model import AppModel
from app_controller import AppController


class App:

    def __init__(self, root, model):
        self.root = root
        self.model = model
        self.controller = None

        self.root.title("Mesh GW Controller")
        self.root.geometry("1300x850")

        self._create_widgets()
        self._populate_initial_data()

    def set_controller(self, controller):
        self.controller = controller
        self._bind_commands()

    def log_message(self, message):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.insert(tk.END, f"[{ts}] {message}\n")
        self.log_text.see(tk.END)
        self.model.add_tp_raw_log(ts, message)

    def _create_widgets(self):
        main_canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(
            self.root, orient="vertical", command=main_canvas.yview)
        main_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollable_frame = ttk.Frame(main_canvas)
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(
                scrollregion=main_canvas.bbox("all"))
        )

        connection_frame = ttk.LabelFrame(scrollable_frame, text="Connection")
        node_frame = ttk.LabelFrame(scrollable_frame, text="Node Management")
        group_frame = ttk.LabelFrame(scrollable_frame, text="Group Management")

        right_container = ttk.Frame(scrollable_frame)
        control_frame = ttk.LabelFrame(right_container, text="LED Control")
        loop_control_frame = ttk.LabelFrame(right_container, text="Loop Control")

        test_frame = ttk.LabelFrame(scrollable_frame, text="Test Commands")

        bottom_frame = ttk.Frame(scrollable_frame)
        log_frame = ttk.LabelFrame(bottom_frame, text="Log & Capture")
        stats_frame = ttk.LabelFrame(bottom_frame, text="Statistics")

        connection_frame.grid(row=0, column=0, columnspan=2,
                              sticky="ew", padx=5, pady=5)
        node_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        group_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        right_container.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)
        control_frame.pack(fill="x")
        loop_control_frame.pack(fill="x", pady=(5, 0))

        test_frame.grid(row=2, column=0, columnspan=3,
                        sticky="ew", padx=5, pady=5)

        throughput_frame = ttk.LabelFrame(scrollable_frame, text="Throughput Test")
        throughput_frame.grid(row=3, column=0, columnspan=3,
                              sticky="ew", padx=5, pady=5)

        bottom_frame.grid(row=4, column=0, columnspan=3,
                          sticky="nsew", padx=5, pady=5)
        bottom_frame.grid_columnconfigure(0, weight=3)
        bottom_frame.grid_columnconfigure(1, weight=1)
        bottom_frame.grid_rowconfigure(0, weight=1)

        log_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        stats_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 0))

        scrollable_frame.grid_rowconfigure(1, weight=1)
        scrollable_frame.grid_rowconfigure(4, weight=2)
        scrollable_frame.grid_columnconfigure(0, weight=1)
        scrollable_frame.grid_columnconfigure(1, weight=1)
        scrollable_frame.grid_columnconfigure(2, weight=1)

        # Connection
        ttk.Label(connection_frame, text="Port:").grid(
            row=0, column=0, padx=5, pady=5)
        self.port_combo = ttk.Combobox(connection_frame)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(connection_frame, text="Baudrate:").grid(
            row=0, column=2, padx=5, pady=5)
        self.baud_entry = ttk.Entry(connection_frame)
        self.baud_entry.grid(row=0, column=3, padx=5, pady=5)
        self.baud_entry.insert(0, "115200")
        self.refresh_ports_button = ttk.Button(connection_frame, text="Refresh")
        self.refresh_ports_button.grid(row=0, column=4, padx=5, pady=5)
        self.connect_button = ttk.Button(connection_frame, text="Connect")
        self.connect_button.grid(row=0, column=5, padx=5, pady=5)

        # Node Management
        node_input_frame = ttk.Frame(node_frame)
        node_input_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(node_input_frame, text="Address (e.g., 45 or 45:50):").pack(side="left")
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
        self.node_listbox = tk.Listbox(
            list_frame_node, selectmode=tk.EXTENDED, exportselection=False, highlightthickness=0)
        self.node_listbox.pack(side="left", fill="both", expand=True)
        node_scrollbar = ttk.Scrollbar(
            list_frame_node, orient=tk.VERTICAL, command=self.node_listbox.yview)
        node_scrollbar.pack(side="right", fill="y")
        self.node_listbox.config(yscrollcommand=node_scrollbar.set)

        # Group Management
        group_btn_frame = ttk.Frame(group_frame)
        group_btn_frame.pack(fill="x", padx=5, pady=5)
        self.add_to_group_button = ttk.Button(
            group_btn_frame, text="Assign Group Membership")
        self.add_to_group_button.pack(side="left", expand=True, fill="x")
        self.load_txt_button = ttk.Button(
            group_btn_frame, text="Load Groups from TXT")
        self.load_txt_button.pack(side="left", expand=True, fill="x", padx=(5, 0))

        list_frame_group = ttk.Frame(group_frame)
        list_frame_group.pack(fill="both", expand=True, padx=5, pady=5)
        self.group_listbox = tk.Listbox(
            list_frame_group, selectmode=tk.EXTENDED, exportselection=False, highlightthickness=0)
        self.group_listbox.pack(side="left", fill="both", expand=True)
        group_scrollbar = ttk.Scrollbar(
            list_frame_group, orient=tk.VERTICAL, command=self.group_listbox.yview)
        group_scrollbar.pack(side="right", fill="y")
        self.group_listbox.config(yscrollcommand=group_scrollbar.set)

        # LED Control
        led_basic_frame = ttk.Frame(control_frame)
        led_basic_frame.pack(fill="x", padx=5, pady=5)
        self.led_on_button = ttk.Button(led_basic_frame, text="LED ON")
        self.led_on_button.pack(side="left", fill="x", expand=True, padx=2)
        self.led_off_button = ttk.Button(led_basic_frame, text="LED OFF")
        self.led_off_button.pack(side="left", fill="x", expand=True, padx=2)

        leds_frame = ttk.Frame(control_frame)
        leds_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(leds_frame, text="Length:").pack(side="left", padx=(5, 0))
        self.leds_length_entry = ttk.Entry(leds_frame, width=5)
        self.leds_length_entry.pack(side="left", padx=5)
        self.leds_length_entry.insert(0, "80")
        self.leds_on_button = ttk.Button(leds_frame, text="ON")
        self.leds_on_button.pack(side="left", fill="x", expand=True, padx=2)
        self.leds_off_button = ttk.Button(leds_frame, text="OFF")
        self.leds_off_button.pack(side="left", fill="x", expand=True, padx=2)

        # Loop Control
        led_loop_frame = ttk.LabelFrame(loop_control_frame, text="LED/LEDs Loop")
        led_loop_frame.pack(fill="x", padx=5, pady=5)

        led_loop_row = ttk.Frame(led_loop_frame)
        led_loop_row.pack(fill='x', padx=2, pady=4)
        ttk.Label(led_loop_row, text="Interval (s):").pack(side="left", padx=(5, 0))
        self.interval_entry = ttk.Entry(led_loop_row, width=5)
        self.interval_entry.pack(side="left", padx=4)
        self.interval_entry.insert(0, "1")
        ttk.Label(led_loop_row, text="Length:").pack(side="left", padx=(5, 0))
        self.loop_length_entry = ttk.Entry(led_loop_row, width=5)
        self.loop_length_entry.pack(side="left", padx=4)
        self.loop_length_entry.insert(0, "-1")
        self.start_loop_button = ttk.Button(led_loop_row, text="Start")
        self.start_loop_button.pack(side="left", fill="x", expand=True, padx=(8, 2))
        self.stop_loop_button = ttk.Button(led_loop_row, text="Stop")
        self.stop_loop_button.pack(side="left", fill="x", expand=True, padx=2)

        test_loop_frame = ttk.LabelFrame(loop_control_frame, text="Test Loop")
        test_loop_frame.pack(fill="x", padx=5, pady=5)

        test_loop_row1 = ttk.Frame(test_loop_frame)
        test_loop_row1.pack(fill="x", padx=2, pady=(4, 2))
        ttk.Label(test_loop_row1, text="Interval (s):").pack(side="left", padx=(5, 0))
        self.test_interval_entry = ttk.Entry(test_loop_row1, width=6)
        self.test_interval_entry.pack(side="left", padx=4)
        self.test_interval_entry.insert(0, "1")
        ttk.Label(test_loop_row1, text="Delay (ms):").pack(side="left", padx=(5, 0))
        self.test_all_ms_entry_loop = ttk.Entry(test_loop_row1, width=6)
        self.test_all_ms_entry_loop.pack(side="left", padx=4)
        self.test_all_ms_entry_loop.insert(0, "1000")

        test_loop_row2 = ttk.Frame(test_loop_frame)
        test_loop_row2.pack(fill="x", padx=2, pady=(0, 4))
        self.start_test_all_with_delay_loop_button = ttk.Button(
            test_loop_row2, text="Start")
        self.start_test_all_with_delay_loop_button.pack(
            side="left", padx=(5, 2), fill='x', expand=True)
        self.stop_test_loop_button = ttk.Button(test_loop_row2, text="Stop")
        self.stop_test_loop_button.pack(side="left", padx=2, fill='x', expand=True)

        # Test Commands
        test_frame.grid_columnconfigure(0, weight=2)
        test_frame.grid_columnconfigure(1, weight=1)

        node_test_frame = ttk.Frame(test_frame)
        node_test_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        gw_test_frame = ttk.Frame(test_frame)
        gw_test_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        ttk.Label(node_test_frame, text="Node Addr:").grid(
            row=0, column=0, padx=5, pady=3, sticky="w")
        self.node_test_addr_entry = ttk.Entry(node_test_frame, width=15)
        self.node_test_addr_entry.grid(
            row=0, column=1, columnspan=3, padx=5, pady=3, sticky="ew")

        self.test_rtt_button = ttk.Button(node_test_frame, text="test_rtt")
        self.test_rtt_button.grid(row=1, column=0, columnspan=1, sticky="ew", padx=5, pady=2)
        self.test_hop_button = ttk.Button(node_test_frame, text="test_hop")
        self.test_hop_button.grid(row=1, column=1, columnspan=1, sticky="ew", padx=5, pady=2)
        self.test_rssi_button = ttk.Button(node_test_frame, text="test_rssi")
        self.test_rssi_button.grid(row=1, column=2, columnspan=2, sticky="ew", padx=5, pady=2)

        test_latency_frame = ttk.Frame(node_test_frame)
        test_latency_frame.grid(row=2, column=0, columnspan=4, sticky='ew', pady=2)
        self.test_latency_button = ttk.Button(test_latency_frame, text="test_latency")
        self.test_latency_button.pack(side="left", padx=5, fill='x', expand=True)

        test_all_frame = ttk.Frame(node_test_frame)
        test_all_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=2)
        ttk.Label(test_all_frame, text="ms:").pack(side="left", padx=(5, 0))
        self.test_all_ms_entry_single = ttk.Entry(test_all_frame, width=10)
        self.test_all_ms_entry_single.pack(side="left", padx=5)
        self.test_all_ms_entry_single.insert(0, "1000")
        self.test_all_button = ttk.Button(test_all_frame, text="test_all")
        self.test_all_button.pack(side="left", padx=5, fill='x', expand=True)

        netoff_frame = ttk.Frame(node_test_frame)
        netoff_frame.grid(row=4, column=0, columnspan=4, sticky='ew', pady=2)
        ttk.Label(netoff_frame, text="NetOff Time(s):").pack(side="left", padx=(5, 0))
        self.netoff_time_entry = ttk.Entry(netoff_frame, width=7)
        self.netoff_time_entry.pack(side="left", padx=5)
        self.netoff_time_entry.insert(0, "10")
        ttk.Label(netoff_frame, text="LED Mode:").pack(side="left", padx=(5, 0))
        self.netoff_led_combo = ttk.Combobox(
            netoff_frame, width=8, state="readonly", values=["0: OFF", "1: ON", "2: BLINK"])
        self.netoff_led_combo.pack(side="left", padx=5)
        self.netoff_led_combo.current(0)
        self.network_off_button = ttk.Button(netoff_frame, text="network_off")
        self.network_off_button.pack(side="left", padx=5, fill='x', expand=True)

        # GW Tests
        self.get_gw_tx_button = ttk.Button(gw_test_frame, text="get_gw_txpower")
        self.get_gw_tx_button.pack(fill="x", padx=5, pady=2)
        gw_set_frame = ttk.Frame(gw_test_frame)
        gw_set_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(gw_set_frame, text="TxPower (-32~10):").pack(side="left")
        self.gw_txpower_entry = ttk.Entry(gw_set_frame, width=10)
        self.gw_txpower_entry.pack(side="left", padx=5)
        self.set_gw_tx_button = ttk.Button(gw_set_frame, text="set_gw_txpower")
        self.set_gw_tx_button.pack(side="left", fill="x", expand=True)

        self.get_gw_channel_button = ttk.Button(gw_test_frame, text="get_gw_channel")
        self.get_gw_channel_button.pack(fill="x", padx=5, pady=2)
        gw_set_channel_frame = ttk.Frame(gw_test_frame)
        gw_set_channel_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(gw_set_channel_frame, text="Channel:").pack(side="left")
        self.gw_channel_entry = ttk.Entry(gw_set_channel_frame, width=10)
        self.gw_channel_entry.pack(side="left", padx=5)
        self.set_gw_channel_button = ttk.Button(gw_set_channel_frame, text="set_gw_channel")
        self.set_gw_channel_button.pack(side="left", fill="x", expand=True)

        ttk.Separator(gw_test_frame, orient='horizontal').pack(fill='x', pady=10, padx=5)

        gw_node_addr_frame = ttk.Frame(gw_test_frame)
        gw_node_addr_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(gw_node_addr_frame, text="Node Addr:").pack(side="left")
        self.gw_node_addr_entry = ttk.Entry(gw_node_addr_frame, width=15)
        self.gw_node_addr_entry.pack(side="left", padx=5)
        self.get_node_tx_button = ttk.Button(gw_node_addr_frame, text="get_node_txpower")
        self.get_node_tx_button.pack(side="left", fill="x", expand=True, padx=5)

        set_node_power_frame = ttk.Frame(gw_test_frame)
        set_node_power_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(set_node_power_frame, text="TxPower (-32~10):").pack(side="left")
        self.gw_node_txpower_entry = ttk.Entry(set_node_power_frame, width=10)
        self.gw_node_txpower_entry.pack(side="left", padx=5)
        self.set_gw_node_tx_button = ttk.Button(set_node_power_frame, text="set_node_txpower")
        self.set_gw_node_tx_button.pack(side="left", fill="x", expand=True)

        gw_node_channel_frame = ttk.Frame(gw_test_frame)
        gw_node_channel_frame.pack(fill='x', padx=5, pady=2)
        self.get_node_channel_button = ttk.Button(
            gw_node_channel_frame, text="get_node_channel")
        self.get_node_channel_button.pack(side="left", fill="x", expand=True, padx=5)

        set_node_channel_frame = ttk.Frame(gw_test_frame)
        set_node_channel_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(set_node_channel_frame, text="Channel:").pack(side="left")
        self.node_channel_entry = ttk.Entry(set_node_channel_frame, width=10)
        self.node_channel_entry.pack(side="left", padx=5)
        self.set_node_channel_button = ttk.Button(set_node_channel_frame, text="set_node_channel")
        self.set_node_channel_button.pack(side="left", fill="x", expand=True)

        # Throughput Test
        tp_input_frame = ttk.Frame(throughput_frame)
        tp_input_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(tp_input_frame, text="Target Addr:").pack(side="left", padx=(5, 0))
        self.tp_addr_entry = ttk.Entry(tp_input_frame, width=10)
        self.tp_addr_entry.pack(side="left", padx=5)

        ttk.Label(tp_input_frame, text="IFS (ms):").pack(side="left", padx=(10, 0))
        self.tp_ifs_entry = ttk.Entry(tp_input_frame, width=8)
        self.tp_ifs_entry.insert(0, "10")
        self.tp_ifs_entry.pack(side="left", padx=5)

        ttk.Label(tp_input_frame, text="Packet Size (Bytes):").pack(side="left", padx=(10, 0))
        self.tp_size_entry = ttk.Entry(tp_input_frame, width=8)
        self.tp_size_entry.insert(0, "10")
        self.tp_size_entry.pack(side="left", padx=5)

        ttk.Label(tp_input_frame, text="Packet Count:").pack(side="left", padx=(10, 0))
        self.tp_count_entry = ttk.Entry(tp_input_frame, width=8)
        self.tp_count_entry.insert(0, "100")
        self.tp_count_entry.pack(side="left", padx=5)

        self.tp_start_button = ttk.Button(tp_input_frame, text="Start Throughput Test")
        self.tp_start_button.pack(side="left", padx=(10, 5))

        tp_result_frame = ttk.Frame(throughput_frame)
        tp_result_frame.pack(fill="x", padx=5, pady=(0, 5))

        ttk.Label(tp_result_frame, text="Flow #:").pack(side="left", padx=(5, 0))
        self.tp_flow_label = ttk.Label(tp_result_frame, text="-", font=("Helvetica", 10, "bold"))
        self.tp_flow_label.pack(side="left", padx=(2, 15))

        ttk.Label(tp_result_frame, text="Sent:").pack(side="left", padx=(5, 0))
        self.tp_sent_label = ttk.Label(tp_result_frame, text="-", font=("Helvetica", 10, "bold"))
        self.tp_sent_label.pack(side="left", padx=(2, 15))

        ttk.Label(tp_result_frame, text="Status:").pack(side="left", padx=(5, 0))
        self.tp_status_label = ttk.Label(tp_result_frame, text="Idle")
        self.tp_status_label.pack(side="left", padx=(2, 5))

        # Statistics
        self.stats_labels = {}
        stats_display_frame = ttk.Frame(stats_frame)
        stats_display_frame.pack(fill='x', padx=5, pady=5)

        headers = ["Metric", "Min", "Max", "Average"]
        for i, header in enumerate(headers):
            ttk.Label(stats_display_frame, text=header, font=('Helvetica', 10, 'bold')).grid(
                row=0, column=i, padx=5, pady=2, sticky='w')

        metrics = {
            'response_gap_ms': 'GAP (ms)',
            'rtt': 'RTT (ms)',
            'latency': 'LATENCY (ms)',
            'down_hop': 'DOWN HOP',
            'up_hop': 'UP HOP'
        }
        for i, (metric, label) in enumerate(metrics.items(), 1):
            ttk.Label(stats_display_frame, text=label).grid(
                row=i, column=0, padx=5, pady=2, sticky='w')
            self.stats_labels[f'{metric}_min'] = ttk.Label(stats_display_frame, text="N/A")
            self.stats_labels[f'{metric}_min'].grid(row=i, column=1, padx=5, pady=2, sticky='w')
            self.stats_labels[f'{metric}_max'] = ttk.Label(stats_display_frame, text="N/A")
            self.stats_labels[f'{metric}_max'].grid(row=i, column=2, padx=5, pady=2, sticky='w')
            self.stats_labels[f'{metric}_avg'] = ttk.Label(stats_display_frame, text="N/A")
            self.stats_labels[f'{metric}_avg'].grid(row=i, column=3, padx=5, pady=2, sticky='w')

        tp_row = len(metrics) + 1
        ttk.Label(stats_display_frame, text="THROUGHPUT (bps)").grid(
            row=tp_row, column=0, padx=5, pady=2, sticky='w')
        self.stats_labels['tp_min'] = ttk.Label(stats_display_frame, text="N/A")
        self.stats_labels['tp_min'].grid(row=tp_row, column=1, padx=5, pady=2, sticky='w')
        self.stats_labels['tp_max'] = ttk.Label(stats_display_frame, text="N/A")
        self.stats_labels['tp_max'].grid(row=tp_row, column=2, padx=5, pady=2, sticky='w')
        self.stats_labels['tp_avg'] = ttk.Label(stats_display_frame, text="N/A")
        self.stats_labels['tp_avg'].grid(row=tp_row, column=3, padx=5, pady=2, sticky='w')

        lost_row = tp_row + 1
        ttk.Label(stats_display_frame, text="LOST (pkts)").grid(
            row=lost_row, column=0, padx=5, pady=2, sticky='w')
        self.stats_labels['lost_min'] = ttk.Label(stats_display_frame, text="N/A")
        self.stats_labels['lost_min'].grid(row=lost_row, column=1, padx=5, pady=2, sticky='w')
        self.stats_labels['lost_max'] = ttk.Label(stats_display_frame, text="N/A")
        self.stats_labels['lost_max'].grid(row=lost_row, column=2, padx=5, pady=2, sticky='w')
        self.stats_labels['lost_avg'] = ttk.Label(stats_display_frame, text="N/A")
        self.stats_labels['lost_avg'].grid(row=lost_row, column=3, padx=5, pady=2, sticky='w')

        counts_frame = ttk.Frame(stats_frame)
        counts_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(counts_frame, text="Total:", font=('Helvetica', 10, 'bold')).pack(side='left', padx=(5, 0))
        self.stats_labels['total'] = ttk.Label(counts_frame, text="0")
        self.stats_labels['total'].pack(side='left', padx=(0, 10))
        ttk.Label(counts_frame, text="Success:", font=('Helvetica', 10, 'bold')).pack(side='left')
        self.stats_labels['success'] = ttk.Label(counts_frame, text="0")
        self.stats_labels['success'].pack(side='left', padx=(0, 10))
        ttk.Label(counts_frame, text="Failure:", font=('Helvetica', 10, 'bold')).pack(side='left')
        self.stats_labels['failure'] = ttk.Label(counts_frame, text="0")
        self.stats_labels['failure'].pack(side='left', padx=(0, 10))
        ttk.Label(counts_frame, text="Flow Count:", font=('Helvetica', 10, 'bold')).pack(side='left', padx=(10, 0))
        self.stats_labels['tp_count'] = ttk.Label(counts_frame, text="0")
        self.stats_labels['tp_count'].pack(side='left', padx=(0, 10))

        # Log & Capture
        log_display_frame = ttk.Frame(log_frame)
        log_display_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_display_frame, height=10)
        log_scrollbar = ttk.Scrollbar(
            log_display_frame, orient=tk.VERTICAL, command=self.log_text.yview)
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
        self.save_tp_button = ttk.Button(capture_control_frame, text="Save Throughput Log")
        self.save_tp_button.pack(side="left", padx=5)
        self.save_tp_button.state(['disabled'])
        self.capture_status_label = ttk.Label(capture_control_frame, text="Capture OFF")
        self.capture_status_label.pack(side="left", padx=10)

    def _bind_commands(self):
        self.refresh_ports_button.config(command=self.controller.refresh_ports)
        self.connect_button.config(command=self.controller.connect_serial)
        self.add_node_button.config(command=self.controller.add_node)
        self.delete_node_button.config(command=self.controller.delete_node)
        self.add_to_group_button.config(command=self.controller.assign_group_membership)
        self.load_txt_button.config(command=self.controller.load_txt_and_set_groups)
        self.led_on_button.config(command=lambda: self.controller.set_led_state(1))
        self.led_off_button.config(command=lambda: self.controller.set_led_state(0))
        self.leds_on_button.config(command=lambda: self.controller.run_set_leds(1))
        self.leds_off_button.config(command=lambda: self.controller.run_set_leds(0))
        self.start_loop_button.config(command=self.controller.start_led_loop)
        self.stop_loop_button.config(command=self.controller.stop_loop)
        self.test_rtt_button.config(command=self.controller.run_test_rtt)
        self.test_latency_button.config(command=self.controller.run_test_latency)
        self.test_hop_button.config(command=self.controller.run_test_hop)
        self.test_rssi_button.config(command=self.controller.run_test_rssi)
        self.test_all_button.config(command=self.controller.run_test_all)
        self.network_off_button.config(command=self.controller.run_network_off)
        self.get_gw_tx_button.config(command=self.controller.run_get_gw_txpower)
        self.set_gw_tx_button.config(command=self.controller.run_set_gw_txpower)
        self.get_node_tx_button.config(command=self.controller.run_get_node_txpower)
        self.set_gw_node_tx_button.config(command=self.controller.run_set_node_txpower)
        self.get_gw_channel_button.config(command=self.controller.run_get_gw_channel)
        self.set_gw_channel_button.config(command=self.controller.run_set_gw_channel)
        self.get_node_channel_button.config(command=self.controller.run_get_node_channel)
        self.set_node_channel_button.config(command=self.controller.run_set_node_channel)
        self.tp_start_button.config(command=self.controller.run_throughput_test)
        self.capture_button.config(command=self.controller.toggle_capture)
        self.save_led_button.config(command=self.controller.save_led_data)
        self.save_test_button.config(command=self.controller.save_test_data)
        self.save_tp_button.config(command=self.controller.save_tp_data)
        self.start_test_all_with_delay_loop_button.config(
            command=self.controller.start_test_all_with_delay_loop)
        self.stop_test_loop_button.config(command=self.controller.stop_test_loop)

    def _populate_initial_data(self):
        self.port_combo['values'] = SerialController.scan_ports()
        for group in self.model.groups:
            self.group_listbox.insert(tk.END, str(group))
        self.update_statistics_display()
        self.set_led_loop_buttons(running=False)
        self.set_test_loop_buttons(running=False)

    def update_node_listbox(self):
        self.node_listbox.delete(0, tk.END)
        for node in self.model.nodes:
            self.node_listbox.insert(tk.END, node)

    def update_connection_status(self, connected):
        if connected:
            self.connect_button.config(
                text="Disconnect", command=self.controller.disconnect_serial)
        else:
            self.connect_button.config(
                text="Connect", command=self.controller.connect_serial)

    def update_capture_status(self, text):
        self.capture_status_label.config(text=text)

    def update_capture_state(self, is_capturing):
        if is_capturing:
            self.capture_button.config(text="Stop Capture")
            self.update_capture_status("Capturing... (0 records)")
            self.save_led_button.state(['disabled'])
            self.save_test_button.state(['disabled'])
            self.save_tp_button.state(['disabled'])
        else:
            self.capture_button.config(text="Start Capture")
            total_records = len(self.model.captured_led_res) + \
                len(self.model.captured_test_res)
            self.update_capture_status(
                f"Capture STOPPED ({total_records} records)")
            if self.model.captured_led_res:
                self.save_led_button.state(['!disabled'])
            if self.model.captured_test_res:
                self.save_test_button.state(['!disabled'])
            if self.model.captured_tp_res:
                self.save_tp_button.state(['!disabled'])
        self.update_statistics_display()

    def set_led_loop_buttons(self, running: bool):
        if running:
            self.start_loop_button.state(['disabled'])
            self.stop_loop_button.state(['!disabled'])
        else:
            self.start_loop_button.state(['!disabled'])
            self.stop_loop_button.state(['disabled'])

    def set_test_loop_buttons(self, running: bool):
        if running:
            self.start_test_all_with_delay_loop_button.state(['disabled'])
            self.stop_test_loop_button.state(['!disabled'])
        else:
            self.start_test_all_with_delay_loop_button.state(['!disabled'])
            self.stop_test_loop_button.state(['disabled'])

    def update_throughput_status(self, flow, sent, status):
        self.tp_flow_label.config(text=str(flow))
        self.tp_sent_label.config(text=str(sent))
        self.tp_status_label.config(text=status)

    def update_statistics_display(self):
        stats = self.model.test_statistics
        counts = self.model.command_counts

        for metric, data in stats.items():
            count = data['count']
            if count > 0:
                avg = data['sum'] / count
                self.stats_labels[f'{metric}_min'].config(text=f"{data['min']:.2f}")
                self.stats_labels[f'{metric}_max'].config(text=f"{data['max']:.2f}")
                self.stats_labels[f'{metric}_avg'].config(text=f"{avg:.2f}")
            else:
                self.stats_labels[f'{metric}_min'].config(text="N/A")
                self.stats_labels[f'{metric}_max'].config(text="N/A")
                self.stats_labels[f'{metric}_avg'].config(text="N/A")

        self.stats_labels['total'].config(text=str(counts['total']))
        self.stats_labels['success'].config(text=str(counts['success']))
        self.stats_labels['failure'].config(text=str(counts['failure']))

        tp = self.model.tp_stats
        self.stats_labels['tp_count'].config(text=str(tp['count']))
        if tp['count'] > 0:
            tp_avg = tp['sum'] / tp['count']
            lost_avg = tp['lost_sum'] / tp['count']
            self.stats_labels['tp_min'].config(text=f"{tp['min']:.2f}")
            self.stats_labels['tp_max'].config(text=f"{tp['max']:.2f}")
            self.stats_labels['tp_avg'].config(text=f"{tp_avg:.2f}")
            self.stats_labels['lost_min'].config(text=str(tp['lost_min']))
            self.stats_labels['lost_max'].config(text=str(tp['lost_max']))
            self.stats_labels['lost_avg'].config(text=f"{lost_avg:.2f}")
        else:
            self.stats_labels['tp_min'].config(text="N/A")
            self.stats_labels['tp_max'].config(text="N/A")
            self.stats_labels['tp_avg'].config(text="N/A")
            self.stats_labels['lost_min'].config(text="N/A")
            self.stats_labels['lost_max'].config(text="N/A")
            self.stats_labels['lost_avg'].config(text="N/A")


if __name__ == "__main__":
    root = tk.Tk()

    model = AppModel()

    view = App(root, model)
    serial = SerialController(root, log_callback=view.log_message)
    controller = AppController(model, serial, view)

    view.set_controller(controller)

    root.mainloop()
