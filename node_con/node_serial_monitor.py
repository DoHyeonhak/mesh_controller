import tkinter as tk
from tkinter import ttk, filedialog
import serial
import serial.tools.list_ports
import time
import re
from datetime import datetime

import pandas as pd


SEND_DATA_PATTERN = re.compile(r"send_data\((\d+(?:,\s*\d+)*)\)")


def parse_send_data(line):
    """Parse send_data(...) → (src, flow, seq, packet_size). Returns None on failure."""
    m = SEND_DATA_PATTERN.search(line.strip())
    if not m:
        return None
    args = [int(x.strip()) for x in m.group(1).split(",")]
    if len(args) < 3:
        return None
    src, flow, seq = args[0], args[1], args[2]
    packet_size = len(args) - 1 + 2  # payload bytes + 2-byte src address
    return src, flow, seq, packet_size


class ThroughputSession:
    """Tracks received packets for one flow and computes throughput.

    Formula (from spec):
        d_rx  = d_end - d_start
        Tput  = (received × packet_size × 8) / d_rx  (bps)
        lost  = (max(seq) + 1) - received
    """

    def __init__(self, flow, packet_size):
        self.flow = flow
        self.packet_size = packet_size

        self.received_seqs = set()
        self.d_start = None
        self.d_end = None

    def record_packet(self, seq):
        now = time.time()
        if self.d_start is None:
            self.d_start = now
        self.d_end = now
        self.received_seqs.add(seq)

    def compute(self):
        """Returns (throughput_bps, lost, received, inferred_total).
        throughput_bps is None if only one packet was received (d_rx == 0).
        Returns None if no packets recorded.
        """
        if self.d_start is None or self.d_end is None:
            return None
        received = len(self.received_seqs)
        inferred_total = max(self.received_seqs) + 1
        lost = max(inferred_total - received, 0)
        drx = self.d_end - self.d_start
        if drx <= 0:
            return None, lost, received, inferred_total
        total_bits = received * self.packet_size * 8
        throughput_bps = total_bits / drx
        return throughput_bps, lost, received, inferred_total


class NodeSerialMonitor:

    SILENCE_TIMEOUT_MS = 500

    def __init__(self, root, log_callback, result_callback):
        self.root = root
        self.log_callback = log_callback
        self.result_callback = result_callback

        self.ser = None
        self._monitoring = False
        self._buffer = ""

        self._session = None
        self._silence_check_id = None

        self.target_flow = None

        self._uplink_state = 'IDLE'   # 'IDLE' | 'WAITING_ACK'
        self._uplink_flow = None
        self._uplink_cmd = ""
        self._uplink_retries = 0
        self._uplink_ack_timer_id = None
        self.MAX_UPLINK_RETRIES = 3
        self.UPLINK_ACK_TIMEOUT_MS = 2000

    @staticmethod
    def scan_ports():
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self, port, baudrate):
        if self.is_connected():
            self.disconnect()
        try:
            self.ser = serial.Serial(port, int(baudrate), timeout=0.1)
            self.log_callback(f"[INFO] {port} connected")
            return True
        except Exception as e:
            self.log_callback(f"[ERROR] Connection failed: {e}")
            return False

    def disconnect(self):
        self.stop_monitoring()
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.log_callback("[INFO] Disconnected")
        self.ser = None
        self._buffer = ""

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def start_monitoring(self):
        if not self.is_connected():
            self.log_callback("[ERROR] Port not connected")
            return
        self._monitoring = True
        self._buffer = ""
        self.root.after(10, self._poll)

    def stop_monitoring(self):
        self._monitoring = False
        if self._silence_check_id:
            self.root.after_cancel(self._silence_check_id)
            self._silence_check_id = None
        if self._uplink_ack_timer_id:
            self.root.after_cancel(self._uplink_ack_timer_id)
            self._uplink_ack_timer_id = None

    def is_monitoring(self):
        return self._monitoring

    def _poll(self):
        if not self._monitoring:
            return
        if not self.is_connected():
            self.log_callback("[WARN] Connection lost")
            self._monitoring = False
            return
        try:
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                self._buffer += chunk
                self._flush_lines()
        except Exception as e:
            self.log_callback(f"[ERROR] Receive error: {e}")
            self._monitoring = False
            return
        self.root.after(10, self._poll)

    def _flush_lines(self):
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            self.log_callback(line)
            self._handle_line(line)

    def _handle_line(self, line):
        parsed = parse_send_data(line)
        if parsed is None:
            return

        src, flow, seq, packet_size = parsed

        # flow=0 is reserved for GW ACK packets.
        # GW sends: send_data_noack(node_addr, 0, 0, acked_flow)
        # Node sees: send_data(gw_src, 0, acked_flow, ...)
        if flow == 0:
            if self._uplink_state == 'WAITING_ACK' and seq == self._uplink_flow:
                self._on_uplink_ack_received()
            return

        if self.target_flow is not None and flow != self.target_flow:
            return

        if self._session is None:
            self._session = ThroughputSession(flow, packet_size)
            self.target_flow = flow  # lock onto first flow; ignore others
        elif self._session.flow != flow:
            return

        self._session.record_packet(seq)

        if self._silence_check_id:
            self.root.after_cancel(self._silence_check_id)
        self._silence_check_id = self.root.after(
            self.SILENCE_TIMEOUT_MS, self._on_silence_timeout
        )

    def _on_silence_timeout(self):
        self._silence_check_id = None
        if self._session is None:
            return

        result = self._session.compute()
        flow = self._session.flow

        if result is None:
            self.log_callback(f"[WARN] Flow {flow}: no packets received")
            self._session = None
            self.target_flow = None
            return

        throughput_bps, lost, received, inferred_total = result

        if throughput_bps is None:
            self.log_callback(
                f"[INFO] Flow {flow} | Only 1 packet received — "
                f"throughput N/A | Received: {received}/{inferred_total} | Lost: {lost}"
            )
        else:
            packet_size = self._session.packet_size
            self.log_callback(
                f"[RESULT] Flow {flow} | "
                f"Throughput: {throughput_bps:.1f} bps ({throughput_bps/1000:.2f} kbps) | "
                f"Received: {received}/{inferred_total} | Lost: {lost} | Packet Size: {packet_size}B"
            )
            self.result_callback(throughput_bps, lost, received, inferred_total, flow)
            self._send_uplink_result(flow, throughput_bps, lost)

        self._session = None
        self.target_flow = None

    def _send_uplink_result(self, flow, throughput_bps, lost):
        """Send throughput result to GW via uplink_data() using Stop-and-Wait.

        Throughput is scaled ×100 (unit: 0.01 bps) to preserve 2 decimal places.
        GW decodes by dividing by 100. Supports up to ~42.9 Mbps.
        """
        tput_scaled = min(int(round(throughput_bps * 100)), 0xFFFFFFFF)
        t3 = (tput_scaled >> 24) & 0xFF
        t2 = (tput_scaled >> 16) & 0xFF
        t1 = (tput_scaled >> 8) & 0xFF
        t0 = tput_scaled & 0xFF
        lost_clamped = min(int(lost), 0xFFFF)
        lost_hi = (lost_clamped >> 8) & 0xFF
        lost_lo = lost_clamped & 0xFF
        cmd = f"uplink_data(0,{flow},{t3},{t2},{t1},{t0},{lost_hi},{lost_lo})"

        self._uplink_state = 'WAITING_ACK'
        self._uplink_flow = flow
        self._uplink_cmd = cmd
        self._uplink_retries = 0
        self._do_send_uplink()

    def _do_send_uplink(self):
        """Transmit (or retransmit) uplink_data and arm ACK timer."""
        try:
            self.ser.write((self._uplink_cmd + '\r\n').encode())
            self.log_callback(
                f"[TX] {self._uplink_cmd} "
                f"(attempt {self._uplink_retries + 1}/{self.MAX_UPLINK_RETRIES})"
            )
        except Exception as e:
            self.log_callback(f"[ERROR] uplink_data send failed: {e}")
            self._uplink_state = 'IDLE'
            self._uplink_flow = None
            return
        self._uplink_ack_timer_id = self.root.after(
            self.UPLINK_ACK_TIMEOUT_MS, self._on_uplink_ack_timeout
        )

    def _on_uplink_ack_received(self):
        if self._uplink_ack_timer_id:
            self.root.after_cancel(self._uplink_ack_timer_id)
            self._uplink_ack_timer_id = None
        self.log_callback(f"[ACK] Flow {self._uplink_flow} acknowledged by GW")
        self._uplink_state = 'IDLE'
        self._uplink_flow = None

    def _on_uplink_ack_timeout(self):
        self._uplink_ack_timer_id = None
        if self._uplink_state != 'WAITING_ACK':
            return
        self._uplink_retries += 1
        if self._uplink_retries >= self.MAX_UPLINK_RETRIES:
            self.log_callback(
                f"[WARN] Flow {self._uplink_flow}: "
                f"uplink_data no ACK after {self.MAX_UPLINK_RETRIES} attempts, giving up"
            )
            self._uplink_state = 'IDLE'
            self._uplink_flow = None
            return
        self.log_callback(f"[WARN] Flow {self._uplink_flow}: uplink_data no ACK, retrying...")
        self._do_send_uplink()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Mesh Node Monitor")
        self.root.geometry("750x750")

        self.monitor = NodeSerialMonitor(
            root,
            log_callback=self._append_log,
            result_callback=self._on_result,
        )

        self._is_capturing = False
        self._captured_results = []
        self._captured_raw_log = []
        self.stats_labels = {}

        self._build_ui()

    def _build_ui(self):
        conn_frame = ttk.LabelFrame(self.root, text="Connection")
        conn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.port_combo = ttk.Combobox(conn_frame, values=NodeSerialMonitor.scan_ports(), width=15)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        if self.port_combo['values']:
            self.port_combo.current(0)

        ttk.Label(conn_frame, text="Baudrate:").grid(row=0, column=2, padx=5, pady=5)
        self.baud_entry = ttk.Entry(conn_frame, width=10)
        self.baud_entry.insert(0, "115200")
        self.baud_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(conn_frame, text="Refresh", command=self._refresh_ports).grid(row=0, column=4, padx=5, pady=5)
        self.conn_btn = ttk.Button(conn_frame, text="Connect", command=self._toggle_connect)
        self.conn_btn.grid(row=0, column=5, padx=5, pady=5)

        self.conn_status = ttk.Label(conn_frame, text="Not connected", foreground="red")
        self.conn_status.grid(row=0, column=6, padx=10, pady=5)

        capture_frame = ttk.LabelFrame(self.root, text="Capture")
        capture_frame.pack(fill="x", padx=10, pady=5)

        self.capture_btn = ttk.Button(capture_frame, text="Start Capture", command=self._toggle_capture)
        self.capture_btn.pack(side="left", padx=5, pady=5)

        self.save_btn = ttk.Button(capture_frame, text="Save Log", command=self._save_log, state="disabled")
        self.save_btn.pack(side="left", padx=5, pady=5)

        self.capture_status_lbl = ttk.Label(capture_frame, text="Capture OFF")
        self.capture_status_lbl.pack(side="left", padx=10, pady=5)

        stats_frame = ttk.LabelFrame(self.root, text="Statistics")
        stats_frame.pack(fill="x", padx=10, pady=5)

        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill="x", padx=5, pady=5)

        headers = ["Metric", "Min", "Max", "Average"]
        for col, header in enumerate(headers):
            ttk.Label(stats_grid, text=header, font=("Helvetica", 10, "bold")).grid(
                row=0, column=col, padx=8, pady=2, sticky="w")

        ttk.Label(stats_grid, text="THROUGHPUT (bps)").grid(row=1, column=0, padx=8, pady=2, sticky="w")
        self.stats_labels["tp_min"] = ttk.Label(stats_grid, text="N/A")
        self.stats_labels["tp_min"].grid(row=1, column=1, padx=8, pady=2, sticky="w")
        self.stats_labels["tp_max"] = ttk.Label(stats_grid, text="N/A")
        self.stats_labels["tp_max"].grid(row=1, column=2, padx=8, pady=2, sticky="w")
        self.stats_labels["tp_avg"] = ttk.Label(stats_grid, text="N/A")
        self.stats_labels["tp_avg"].grid(row=1, column=3, padx=8, pady=2, sticky="w")

        ttk.Label(stats_grid, text="LOST (pkts)").grid(row=2, column=0, padx=8, pady=2, sticky="w")
        self.stats_labels["lost_min"] = ttk.Label(stats_grid, text="N/A")
        self.stats_labels["lost_min"].grid(row=2, column=1, padx=8, pady=2, sticky="w")
        self.stats_labels["lost_max"] = ttk.Label(stats_grid, text="N/A")
        self.stats_labels["lost_max"].grid(row=2, column=2, padx=8, pady=2, sticky="w")
        self.stats_labels["lost_avg"] = ttk.Label(stats_grid, text="N/A")
        self.stats_labels["lost_avg"].grid(row=2, column=3, padx=8, pady=2, sticky="w")

        counts_frame = ttk.Frame(stats_frame)
        counts_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Label(counts_frame, text="Flow Count:", font=("Helvetica", 10, "bold")).pack(side="left", padx=(8, 0))
        self.stats_labels["tp_count"] = ttk.Label(counts_frame, text="0")
        self.stats_labels["tp_count"].pack(side="left", padx=(4, 0))

        log_frame = ttk.LabelFrame(self.root, text="Receive Log")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = tk.Text(log_frame, state="disabled", wrap="word")
        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=sb.set)
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        sb.pack(side="right", fill="y")

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="Clear Log", command=self._clear_log).pack(side="left", padx=5)

    def _refresh_ports(self):
        ports = NodeSerialMonitor.scan_ports()
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)

    def _toggle_connect(self):
        if self.monitor.is_connected():
            self.monitor.disconnect()
            self.conn_btn.config(text="Connect")
            self.conn_status.config(text="Not connected", foreground="red")
        else:
            port = self.port_combo.get()
            baud = self.baud_entry.get()
            if not port:
                return
            if self.monitor.connect(port, baud):
                self.conn_btn.config(text="Disconnect")
                self.conn_status.config(text=f"Connected: {port}", foreground="green")
                self.monitor.start_monitoring()

    def _toggle_capture(self):
        if self._is_capturing:
            self._is_capturing = False
            self.capture_btn.config(text="Start Capture")
            count = len(self._captured_results)
            self.capture_status_lbl.config(text=f"Capture STOPPED ({count} records)")
            if self._captured_results:
                self.save_btn.config(state="normal")
        else:
            self._is_capturing = True
            self._captured_results.clear()
            self._captured_raw_log.clear()
            self.capture_btn.config(text="Stop Capture")
            self.capture_status_lbl.config(text="Capturing... (0 records)")
            self.save_btn.config(state="disabled")
            self._reset_stats_display()

    def _on_result(self, throughput_bps, lost, received, inferred_total, flow):
        if self._is_capturing:
            self._captured_results.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "flow": flow,
                "throughput_bps": round(throughput_bps, 2),
                "throughput_kbps": round(throughput_bps / 1000, 4),
                "received_packets": received,
                "inferred_total": inferred_total,
                "lost_packets": lost,
            })
            count = len(self._captured_results)
            self.capture_status_lbl.config(text=f"Capturing... ({count} records)")
            self._update_stats_display()

    def _reset_stats_display(self):
        self.stats_labels["tp_count"].config(text="0")
        for key in ("tp_min", "tp_max", "tp_avg", "lost_min", "lost_max", "lost_avg"):
            self.stats_labels[key].config(text="N/A")

    def _update_stats_display(self):
        results = self._captured_results
        count = len(results)
        self.stats_labels["tp_count"].config(text=str(count))
        if count == 0:
            self._reset_stats_display()
            return
        tputs = [r["throughput_bps"] for r in results]
        losts = [r["lost_packets"] for r in results]
        self.stats_labels["tp_min"].config(text=f"{min(tputs):.2f}")
        self.stats_labels["tp_max"].config(text=f"{max(tputs):.2f}")
        self.stats_labels["tp_avg"].config(text=f"{sum(tputs) / count:.2f}")
        self.stats_labels["lost_min"].config(text=str(min(losts)))
        self.stats_labels["lost_max"].config(text=str(max(losts)))
        self.stats_labels["lost_avg"].config(text=f"{sum(losts) / count:.2f}")

    def _save_log(self):
        if not self._captured_results:
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Save Throughput Log As"
        )
        if not filepath:
            return
        try:
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                pd.DataFrame(self._captured_results).to_excel(
                    writer, sheet_name="Throughput Results", index=False
                )
                pd.DataFrame(self._captured_raw_log).to_excel(
                    writer, sheet_name="Raw Log", index=False
                )
            self._append_log(f"[INFO] Saved: {filepath}")
        except Exception as e:
            self._append_log(f"[ERROR] Save failed: {e}")

    def _append_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

        if self._is_capturing:
            self._captured_raw_log.append({"timestamp": ts, "message": msg})

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
