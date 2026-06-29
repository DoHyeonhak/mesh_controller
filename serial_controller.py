import serial
import serial.tools.list_ports
import time

class SerialController:
    """시리얼 통신과 관련된 모든 책임을 담당하는 클래스"""

    def __init__(self, root, log_callback=None, data_callback=None): # data_callback 추가
        self.ser = None
        self.root = root
        self.log_callback = log_callback
        self.data_callback = data_callback # data_callback 저장

        self._waiting_response = False
        self._response_data = ""
        self._start_time = 0
        self._last_command = ""

        self._unsolicited_callback = None
        self._unsolicited_buffer = ""

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    @staticmethod
    def scan_ports():
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self, port, baudrate):
        if self.is_connected():
            self.disconnect()
        try:
            self.ser = serial.Serial(port, int(baudrate), timeout=0.1)
            self.log(f"[INFO] {port} 연결 성공")
            return True
        except Exception as e:
            self.log(f"[ERROR] 시리얼 연결 실패: {e}")
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.log("[INFO] 연결이 종료되었습니다.")
        self.ser = None

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def is_waiting_response(self):
        return self._waiting_response

    def start_unsolicited_reader(self, callback):
        """Starts a background poller that captures lines arriving outside request-response cycles."""
        self._unsolicited_callback = callback
        self._unsolicited_buffer = ""
        self.root.after(100, self._poll_unsolicited)

    def _poll_unsolicited(self):
        if not self.is_connected():
            self._unsolicited_buffer = ""
            return
        if not self._waiting_response and self.ser.in_waiting > 0:
            try:
                chunk = self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                self._unsolicited_buffer += chunk
                while "\n" in self._unsolicited_buffer:
                    line, self._unsolicited_buffer = self._unsolicited_buffer.split("\n", 1)
                    line = line.strip()
                    if line and self._unsolicited_callback:
                        self._unsolicited_callback(line)
            except Exception:
                pass
        self.root.after(100, self._poll_unsolicited)

    def send_command(self, command):
        if not self.is_connected():
            self.log("[ERROR] 포트가 연결되지 않았습니다.")
            return

        if self._waiting_response:
            self.log(f"[WARN] 이전 응답 대기 중... '{command}' 명령이 무시됩니다.")
            return

        self._last_command = command
        self._waiting_response = True
        self._start_time = time.time()
        self._response_data = ""

        try:
            self.ser.write((command + '\r\n').encode())
            self.log(f"> {command}")
            self.root.after(10, self._check_response)
        except Exception as e:
            self.log(f"[ERROR] 명령어 전송 실패: {e}")
            self._waiting_response = False
            
    def _check_response(self):
        """
        프롬프트 문자('>')가 수신될 때까지 응답을 수집합니다.
        타임아웃 없이 장치의 응답을 끝까지 기다립니다.
        """
        if not self._waiting_response:
            return

        if self.ser.in_waiting > 0:
            try:
                chunk = self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                self._response_data += chunk
            except Exception as e:
                self.log(f"[ERROR] 데이터 수신 중 오류: {e}")
                self._waiting_response = False
                return

        is_response_complete = "\n>" in self._response_data or self._response_data.endswith('>')

        if is_response_complete:
            response_time = time.time()
            elapsed = response_time - self._start_time
            
            raw_response = self._response_data.strip()
            lines = raw_response.splitlines()
            
            filtered_lines = [
                line.strip() for line in lines 
                if line.strip() and \
                   line.strip() != self._last_command.strip() and \
                   line.strip() != '>'
            ]

            # <<< START: 로직 수정 (1/2) --- 'no response' 메시지 변환 제거 >>>
            # 기존에는 'no response'를 다른 문자열로 바꿨으나, 이제는 원본을 그대로 사용합니다.
            final_response = "\n".join(filtered_lines)
            # <<< END: 로직 수정 (1/2) >>>
            
            if final_response:
                self.log(final_response)

            # <<< START: 로직 수정 (2/2) --- 'is_success' 판단 로직 강화 >>>
            lower_response = final_response.lower()
            is_success = True  # 기본값을 True로 설정하고, 실패 조건에 해당하면 False로 변경

            # 실패 조건들:
            # 1. 응답에 'fail'이 포함된 경우 (예: 'led_fail')
            # 2. 응답에 'error'가 포함된 경우
            # 3. 응답에 'no response'가 포함된 경우
            # 4. 필터링된 응답이 아예 없는 경우 (프롬프트만 받은 경우)
            if "fail" in lower_response or \
               "error" in lower_response or \
               "no response" in lower_response or \
               not final_response:
                is_success = False
            # <<< END: 로직 수정 (2/2) >>>

            data_to_log = {
                "command": self._last_command,
                "request_time": self._start_time,
                "response_time": response_time,
                "response_gap_ms": elapsed * 1000,
                "success": is_success, # 강화된 로직의 결과가 저장됨
                "filtered_response": final_response,
                "raw_response": raw_response,
            }

            self._waiting_response = False

            if self.data_callback:
                self.data_callback(data_to_log)

            return

        self.root.after(10, self._check_response)