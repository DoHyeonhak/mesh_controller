
class AppModel:
    """애플리케이션의 데이터와 상태를 관리하는 클래스 (Model)"""
    def __init__(self):
        self.nodes = []
        self.groups = list(range(0xF000, 0xFFFF))
        self.loop_running = False
        self.loop_state = False
        self.is_capturing = False
        self.captured_led_res = []
        self.captured_test_res = []
        self.interval = 1.0
        self.test_loop_running = False
        self.test_interval = 1.0
        self.test_loop_node_address = None

        self.test_statistics = self._init_stats()
        self.command_counts = self._init_counts()

    def _init_stats(self):
        """통계 데이터 구조를 초기화합니다."""
        return {
            'response_gap_ms': {'min': None, 'max': None, 'sum': 0, 'count': 0},
            'rtt': {'min': None, 'max': None, 'sum': 0, 'count': 0},
            'latency': {'min': None, 'max': None, 'sum': 0, 'count': 0},
            'down_hop': {'min': None, 'max': None, 'sum': 0, 'count': 0},
            'up_hop': {'min': None, 'max': None, 'sum': 0, 'count': 0},
        }

    def _init_counts(self):
        """명령 카운트 구조를 초기화합니다."""
        return {'total': 0, 'success': 0, 'failure': 0}

    def add_nodes(self, new_nodes):
        """노드들을 추가하고 정렬합니다."""
        added_count = 0
        for node in new_nodes:
            if node not in self.nodes:
                self.nodes.append(node)
                added_count += 1
        if added_count > 0:
            self.nodes.sort(key=int)
        return added_count

    def delete_node(self, node_address):
        """주어진 주소의 노드를 삭제합니다."""
        if node_address in self.nodes:
            self.nodes.remove(node_address)
            return True
        return False

    def toggle_capture(self):
        """캡처 상태를 토글하고, 시작 시 데이터를 초기화합니다."""
        self.is_capturing = not self.is_capturing
        if self.is_capturing:
            self.clear_captured_data()
        return self.is_capturing

    def clear_captured_data(self):
        """캡처된 모든 데이터를 초기화합니다."""
        self.captured_led_res.clear()
        self.captured_test_res.clear()
        self.test_statistics = self._init_stats()
        self.command_counts = self._init_counts()

    def add_led_capture(self, data):
        """캡처된 LED 응답을 추가합니다."""
        if self.is_capturing:
            self.captured_led_res.append(data)

    def add_test_capture(self, data):
        """캡처된 테스트 응답을 추가합니다."""
        if self.is_capturing:
            self.captured_test_res.append(data)

    def update_test_statistics(self, record):
        """새로운 테스트 결과로 통계를 업데이트합니다."""
        if not self.is_capturing:
            return

        self.command_counts['total'] += 1
        
        # 'no response'와 같은 실패 케이스 (-1) 확인
        if record.get('rtt', -1) == -1 and record.get('latency', -1) == -1:
            self.command_counts['failure'] += 1
            return
        
        self.command_counts['success'] += 1

        for metric in self.test_statistics.keys():
            value = record.get(metric)
            if value is not None and value != -1:
                stats = self.test_statistics[metric]
                
                if stats['min'] is None or value < stats['min']:
                    stats['min'] = value
                if stats['max'] is None or value > stats['max']:
                    stats['max'] = value
                
                stats['sum'] += value
                stats['count'] += 1
    
    def clear_led_captures(self):
        """캡처된 LED 데이터만 초기화합니다."""
        self.captured_led_res.clear()

    def clear_test_captures(self):
        """캡처된 Test 데이터만 초기화합니다."""
        self.captured_test_res.clear()

    def start_loop(self):
        """반복 실행을 시작합니다."""
        self.loop_running = True

    def stop_loop(self):
        """반복 실행을 중지합니다."""
        self.loop_running = False

    def toggle_loop_state(self):
        """LED 루프 상태를 토글합니다."""
        self.loop_state = not self.loop_state
        return self.loop_state
