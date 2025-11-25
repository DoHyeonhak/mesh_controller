import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
import pandas as pd
import re
import time

class AppController:
    """애플리케이션의 비즈니스 로직과 사용자 입력을 처리하는 컨트롤러"""

    def __init__(self, model, serial, view):
        self.model = model
        self.serial = serial
        self.view = view
        self.serial.data_callback = self.handle_serial_data

    # Callback & Core Logic Methods
    def handle_serial_data(self, data):
        """SerialController로부터 구조화된 데이터를 받아 모델에 저장하는 콜백"""
        if not self.model.is_capturing:
            return

        cmd = data.get("command", "")
        
        if cmd.startswith("set_led"):
            self.model.add_led_capture(data)
        
        elif cmd.startswith("test_all") or cmd.startswith("network_off"):
            parsed_results = { 'rtt': -1, 'latency': -1, 'down_hop': -1, 'up_hop': -1, 'rssi': -1 }
            if cmd.startswith("test_all"):
                response_str = data.get('filtered_response', '')
                parsed_results = self._parse_test_all_response(response_str)
            
            record = {**data, **parsed_results}
            self.model.add_test_capture(record)

            if cmd.startswith("test_all"):
                self.model.update_test_statistics(record)
                self.view.update_statistics_display()

        total_records = len(self.model.captured_led_res) + len(self.model.captured_test_res)
        self.view.update_capture_status(f"Capturing... ({total_records} records)")

    def connect_serial(self):
        port = self.view.port_combo.get()
        baud = self.view.baud_entry.get()
        if not port:
            messagebox.showerror("Error", "COM 포트를 선택하세요.")
            return
        if self.serial.connect(port, baud):
            self.view.update_connection_status(connected=True)
        else:
            messagebox.showerror("Error", "연결에 실패했습니다. 로그를 확인하세요.")

    def disconnect_serial(self):
        self.serial.disconnect()
        self.view.update_connection_status(connected=False)

    def add_node(self):
        text = self.view.node_entry.get().strip()
        if not text:
            messagebox.showerror("Error", "주소를 입력하세요.")
            return
        try:
            if ':' in text:
                start, end = map(int, text.split(':'))
                new_nodes = [str(n) for n in range(start, end + 1)]
            else:
                new_nodes = [str(int(text))]
        except ValueError:
            messagebox.showerror("Error", "잘못된 숫자 형식입니다. 단일 숫자(예: 45, -1) 또는 범위(예: 45:50) 형식으로 입력하세요.")
            return
        
        added_count = self.model.add_nodes(new_nodes)
        
        if added_count > 0:
            self.view.update_node_listbox()
            self.view.log_message(f"[INFO] {added_count}개의 노드가 추가되었습니다.")
        else:
            messagebox.showinfo("Info", "이미 존재하는 노드입니다.")
        self.view.node_entry.delete(0, tk.END)

    def delete_node(self):
        selected_idx = self.view.node_listbox.curselection()
        if not selected_idx:
            messagebox.showerror("Error", "삭제할 노드를 선택하세요.")
            return
        address = self.view.node_listbox.get(selected_idx[0])
        
        if self.model.delete_node(address):
            self.view.update_node_listbox()
            self.view.log_message(f"[INFO] 노드 {address} 삭제됨")

    # 1 : 1 or N
    def add_node_to_groups(self):
        node_idx = self.view.node_listbox.curselection()
        if len(node_idx) != 1:
            messagebox.showerror("Error", "노드를 하나만 선택하세요.")
            return
        group_indices = self.view.group_listbox.curselection()
        if not group_indices:
            messagebox.showerror("Error", "하나 이상의 그룹을 선택하세요.")
            return
        node_addr = self.view.node_listbox.get(node_idx[0])
        group_addrs = [self.view.group_listbox.get(i) for i in group_indices]
        cmd = f"set_group({node_addr},{','.join(group_addrs)})"
        self.serial.send_command(cmd)

    # N : 1
    def assign_group_membership(self):
        """선택된 노드와 그룹의 수에 따라 그룹 멤버십을 할당합니다.
        - 1개 노드, N개 그룹: 노드에 여러 그룹을 할당합니다. (function : add_node_to_groups 기능)
        - N개 노드, 1개 그룹: 여러 노드를 하나의 그룹에 할당합니다.
        """
        node_indices = self.view.node_listbox.curselection()
        group_indices = self.view.group_listbox.curselection()
        num_nodes = len(node_indices)
        num_groups = len(group_indices)

        # 한 개의 노드를 여러 그룹에 할당
        if num_nodes == 1 and num_groups >= 1:
            node_addr = self.view.node_listbox.get(node_indices[0])
            group_addrs = [self.view.group_listbox.get(i) for i in group_indices]
            cmd = f"set_group({node_addr},{','.join(group_addrs)})"
            self.serial.send_command(cmd)
            self.view.log_message(f"[INFO] 노드 {node_addr}에 {num_groups}개의 그룹을 할당했습니다.")

        # 여러 개의 노드를 한 그룹에 할당
        elif num_nodes > 1 and num_groups == 1:
            node_addrs = [self.view.node_listbox.get(i) for i in node_indices]
            group_addr = self.view.group_listbox.get(group_indices[0])
            
            ignored_nodes = []
            successful_nodes = []

            for node_addr in node_addrs:
                cmd = f"set_group({node_addr},{group_addr})"
                self.serial.send_command(cmd)
                
                # waiting response (2 seconds)
                wait_start_time = time.time()
                while self.serial.is_waiting_response():
                    time.sleep(0.05) # 50ms 간격으로 확인
                    self.view.root.update()
                    if time.time() - wait_start_time > 2.0:
                        ignored_nodes.append(node_addr)
                        break 
                else:
                    successful_nodes.append(node_addr)

            # display the result
            if successful_nodes:
                self.view.log_message(f"[INFO] {len(successful_nodes)}개의 노드를 그룹 {group_addr}에 할당했습니다: {', '.join(successful_nodes)}")
            if ignored_nodes:
                self.view.log_message(f"[WARN] 다음 노드에 대한 응답이 없어 명령이 무시되었을 수 있습니다: {', '.join(ignored_nodes)}")
                messagebox.showwarning("Timeout", f"다음 노드에 대한 응답이 없어 명령이 무시되었을 수 있습니다:{', '.join(ignored_nodes)}")

        else:
            messagebox.showerror("Error", "잘못된 선택입니다.\n\n- 한 개의 노드와 하나 이상의 그룹, 또는\n- 여러 개의 노드와 한 개의 그룹을 선택하세요.")

    # def load_txt_and_set_groups(self):
    #     filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    #     if not filepath: return
    #     try:
    #         with open(filepath, 'r') as f:
    #             for line in f:
    #                 line = line.strip()
    #                 if not line or ':' not in line: continue
    #                 node_part, groups_part = [x.strip() for x in line.split(':', 1)]
    #                 groups_str = ",".join([g.strip() for g in groups_part.split(',') if g.strip().isdigit()])
    #                 if groups_str:
    #                     cmd = f"set_group({node_part},{groups_str})"
    #                     self.serial.send_command(cmd)
    #                     self.view.root.update()
    #                     self.view.root.after(100)
    #     except Exception as e:
    #         messagebox.showerror("Error", f"파일 처리 중 오류: {e}")

    def set_led_state(self, state):
        addresses = self._get_selected_addresses()
        if not addresses:
            messagebox.showerror("Error", "노드 또는 그룹을 선택하세요.")
            return
        for addr in addresses:
            cmd = f"set_led({addr},{state})"
            self.serial.send_command(cmd)

    def run_set_leds(self, state):
        try:
            length = int(self.view.leds_length_entry.get())
            if not (2 <= length <= 100): raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Length는 2에서 100 사이의 정수여야 합니다.")
            return

        addresses = self._get_selected_addresses()
        if not addresses:
            messagebox.showerror("Error", "노드 또는 그룹을 선택하세요.")
            return
        
        for addr in addresses:
            cmd = f"set_leds({addr},{state},{length})"
            self.serial.send_command(cmd)
    
    def start_toggle_loop(self):
        try:
            interval = float(self.view.interval_entry.get())
            if interval <= 0: raise ValueError
            self.model.interval = interval
        except ValueError:
            messagebox.showerror("Error", "유효한 간격(초)을 입력하세요. (예: 0.5)")
            return
        if not self._get_selected_addresses():
            messagebox.showerror("Error", "루프를 실행할 노드 또는 그룹을 선택하세요.")
            return
        
        self.model.start_loop()
        self.view.log_message("[INFO] 반복 실행 시작")
        self._toggle_loop()

    def stop_loop(self):
        self.model.stop_loop()
        self.view.log_message("[INFO] 반복 실행 중지")

    def _toggle_loop(self):
        if not self.model.loop_running: return
        
        new_state = self.model.toggle_loop_state()
        self.set_led_state(1 if new_state else 0)
        
        self.view.root.after(int(self.model.interval * 1000), self._toggle_loop)

    def start_test_loop(self):
        try:
            interval = float(self.view.test_interval_entry.get())
            if interval <= 0: raise ValueError
            self.model.test_interval = interval
        except ValueError:
            messagebox.showerror("Error", "유효한 간격(초)을 입력하세요. (예: 0.5)")
            return

        node_address = self._get_node_address_for_test("test_all_loop")
        if not node_address:
            messagebox.showerror("Error", "루프를 실행할 노드를 선택하세요.")
            return
        
        self.model.test_loop_node_address = node_address
        self.model.test_loop_running = True
        self.view.log_message(f"[INFO] Test 루프 시작 (Node: {node_address})")
        self._test_loop()

    def stop_test_loop(self):
        self.model.test_loop_running = False
        self.view.log_message("[INFO] Test 루프 중지")

    def _test_loop(self):
        if not self.model.test_loop_running: return
        
        self.serial.send_command(f"test_all({self.model.test_loop_node_address})")
        
        self.view.root.after(int(self.model.test_interval * 1000), self._test_loop)

    def run_test_all(self):
        address = self._get_node_address_for_test("test_all")
        if address: self.serial.send_command(f"test_all({address})")

    def run_test_rtt(self):
        address = self._get_node_address_for_test("test_rtt")
        if address: self.serial.send_command(f"test_rtt({address})")

    def run_test_latency(self):
        address = self._get_node_address_for_test("test_latency")
        if address: self.serial.send_command(f"test_latency({address})")

    def run_test_hop(self):
        address = self._get_node_address_for_test("test_hop")
        if address: self.serial.send_command(f"test_hop({address})")

    def run_test_rssi(self):
        address = self._get_node_address_for_test("test_rssi")
        if address: self.serial.send_command(f"test_rssi({address})")

    def run_get_node_txpower(self):
        address = self._get_node_address_for_test("get_node_txpower")
        if address: self.serial.send_command(f"get_node_txpower({address})")

    def run_set_node_txpower(self):
        address = self._get_node_address_for_test("set_node_txpower")
        if not address: return
        try:
            power = int(self.view.node_txpower_entry.get().strip())
            if not (-32 <= power <= 10): raise ValueError
        except ValueError:
            messagebox.showerror("Error", "TxPower 값은 -32에서 10 사이의 정수여야 합니다.")
            return
        self.serial.send_command(f"set_node_txpower({address},{power})")

    def run_network_off(self):
        address = self._get_node_address_for_test("network_off")
        if not address: return
        try:
            time_val = int(self.view.netoff_time_entry.get().strip())
            if not (1 <= time_val <= 65535): raise ValueError
        except ValueError:
            messagebox.showerror("Error", "NetOff Time은 1에서 65535 사이의 정수여야 합니다.")
            return
        try:
            led_val = int(self.view.netoff_led_combo.get().split(':')[0])
        except Exception:
            messagebox.showerror("Error", "유효한 LED Mode를 선택하세요.")
            return
        self.serial.send_command(f"network_off({address},{time_val},{led_val})")

    def run_get_gw_txpower(self):
        self.serial.send_command("get_gw_txpower()")

    def run_set_gw_txpower(self):
        try:
            power = int(self.view.gw_txpower_entry.get().strip())
            if not (-32 <= power <= 10): raise ValueError
        except ValueError:
            messagebox.showerror("Error", "TxPower 값은 -32에서 10 사이의 정수여야 합니다.")
            return
        self.serial.send_command(f"set_gw_txpower({power})")

    def toggle_capture(self):
        is_capturing = self.model.toggle_capture()
        self.view.update_capture_state(is_capturing)

    def save_led_data(self):
        if not self.model.captured_led_res:
            messagebox.showinfo("Info", "저장할 LED 데이터가 없습니다.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")], title="Save LED Log As")
        if not filepath: return
        try:
            df = pd.DataFrame(self.model.captured_led_res)
            df['request_timestamp'] = df['request_time'].apply(lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
            df['response_timestamp'] = df['response_time'].apply(lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
            df_to_save = df[['request_timestamp', 'response_timestamp', 'response_gap_ms', 'command', 'success', 'filtered_response']]
            df_to_save.to_excel(filepath, index=False, engine='openpyxl')
            
            self.view.log_message(f"[INFO] LED 로그가 성공적으로 저장되었습니다: {filepath}")
            messagebox.showinfo("Success", f"LED 로그가 성공적으로 저장되었습니다:\n{filepath}")
            
            self.model.clear_led_captures()
            self.view.update_capture_state(is_capturing=False)
        except Exception as e:
            self.view.log_message(f"[ERROR] LED 로그 저장 실패: {e}")
            messagebox.showerror("Error", f"LED 로그 저장 중 오류가 발생했습니다:\n{e}")

    def save_test_data(self):
        if not self.model.captured_test_res:
            messagebox.showinfo("Info", "저장할 Test 데이터가 없습니다.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")], title="Save Test Log As")
        if not filepath: return
        try:
            df = pd.DataFrame(self.model.captured_test_res)
            df['request_timestamp'] = df['request_time'].apply(lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
            df['response_timestamp'] = df['response_time'].apply(lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
            df_to_save = df[['request_timestamp', 'response_timestamp', 'response_gap_ms', 'command', 'success', 'filtered_response', 'rtt', 'latency', 'down_hop', 'up_hop', 'rssi']]
            df_to_save.to_excel(filepath, index=False, engine='openpyxl')
            
            self.view.log_message(f"[INFO] Test 로그가 성공적으로 저장되었습니다: {filepath}")
            messagebox.showinfo("Success", f"Test 로그가 성공적으로 저장되었습니다:\n{filepath}")
            
            self.model.clear_test_captures()
            self.view.update_capture_state(is_capturing=False)
        except Exception as e:
            self.view.log_message(f"[ERROR] Test 로그 저장 실패: {e}")
            messagebox.showerror("Error", f"Test 로그 저장 중 오류가 발생했습니다:\n{e}")

    def _parse_test_all_response(self, response_str):
        """test_all 명령어의 응답 문자열을 파싱하여 딕셔너리로 반환합니다."""
        if "no response" in response_str.lower():
            return { 'rtt': -1, 'latency': -1, 'down_hop': -1, 'up_hop': -1, 'rssi': -1 }

        results = { 'rtt': -1, 'latency': -1, 'down_hop': -1, 'up_hop': -1, 'rssi': -1 }
        
        rtt_match = re.search(r"rtt=([\d\.]+)", response_str)
        if rtt_match: results['rtt'] = float(rtt_match.group(1))

        latency_match = re.search(r"latency=([\d\.]+)", response_str)
        if latency_match: results['latency'] = float(latency_match.group(1))

        hop_match = re.search(r"down hop=(\d+), up hop=(\d+)", response_str)
        if hop_match:
            results['down_hop'] = int(hop_match.group(1))
            results['up_hop'] = int(hop_match.group(2))

        rssi_match = re.search(r"rssi=(-?\d+)", response_str)
        if rssi_match: results['rssi'] = int(rssi_match.group(1))
            
        return results

    def _get_selected_addresses(self):
        addresses = []
        node_idx = self.view.node_listbox.curselection()
        group_indices = self.view.group_listbox.curselection()
        if node_idx:
            addresses.append(self.view.node_listbox.get(node_idx[0]))
        elif group_indices:
            for i in group_indices:
                addresses.append(self.view.group_listbox.get(i))
        return addresses

    def _get_node_address_for_test(self, command_name):
        addr_input = self.view.node_test_addr_entry.get().strip()
        if addr_input:
            return addr_input
        else:
            selected_nodes = self.view.node_listbox.curselection()
            if not selected_nodes:
                messagebox.showerror("Error", f"노드 주소를 입력하거나 리스트에서 노드를 선택하세요 ({command_name}).")
                return None
            return self.view.node_listbox.get(selected_nodes[0])

    def toggle_node_selection(self, event):
        widget = event.widget
        clicked_index = widget.nearest(event.y)
        if clicked_index in widget.curselection():
            widget.selection_clear(clicked_index)
        else:
            widget.selection_clear(0, tk.END)
            widget.selection_set(clicked_index)
        return "break"
