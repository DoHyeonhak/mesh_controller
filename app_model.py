
class AppModel:

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
        self.test_loop_mode = None

        self.test_statistics = self._init_stats()
        self.command_counts = self._init_counts()

        self.throughput_flow_number = 0

        self.captured_tp_res = []
        self.captured_tp_raw_log = []
        self.tp_stats = self._init_tp_stats()

    def _init_stats(self):
        return {
            'response_gap_ms': {'min': None, 'max': None, 'sum': 0, 'count': 0},
            'rtt': {'min': None, 'max': None, 'sum': 0, 'count': 0},
            'latency': {'min': None, 'max': None, 'sum': 0, 'count': 0},
            'down_hop': {'min': None, 'max': None, 'sum': 0, 'count': 0},
            'up_hop': {'min': None, 'max': None, 'sum': 0, 'count': 0},
        }

    def _init_counts(self):
        return {'total': 0, 'success': 0, 'failure': 0}

    def add_nodes(self, new_nodes):
        added_count = 0
        for node in new_nodes:
            if node not in self.nodes:
                self.nodes.append(node)
                added_count += 1
        if added_count > 0:
            self.nodes.sort(key=int)
        return added_count

    def delete_node(self, node_address):
        if node_address in self.nodes:
            self.nodes.remove(node_address)
            return True
        return False

    def toggle_capture(self):
        self.is_capturing = not self.is_capturing
        if self.is_capturing:
            self.clear_captured_data()
        return self.is_capturing

    def clear_captured_data(self):
        self.captured_led_res.clear()
        self.captured_test_res.clear()
        self.captured_tp_res.clear()
        self.captured_tp_raw_log.clear()
        self.test_statistics = self._init_stats()
        self.command_counts = self._init_counts()
        self.tp_stats = self._init_tp_stats()

    def add_led_capture(self, data):
        if self.is_capturing:
            self.captured_led_res.append(data)

    def add_test_capture(self, data):
        if self.is_capturing:
            self.captured_test_res.append(data)

    def update_test_statistics(self, record):
        if not self.is_capturing:
            return

        self.command_counts['total'] += 1

        # -1 sentinel indicates 'no response'
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
        self.captured_led_res.clear()

    def clear_test_captures(self):
        self.captured_test_res.clear()

    def start_loop(self):
        self.loop_running = True

    def stop_loop(self):
        self.loop_running = False

    def toggle_loop_state(self):
        self.loop_state = not self.loop_state
        return self.loop_state

    def next_throughput_flow(self):
        self.throughput_flow_number += 1
        return self.throughput_flow_number

    def _init_tp_stats(self):
        return {
            'min': None, 'max': None, 'sum': 0.0, 'count': 0,
            'lost_min': None, 'lost_max': None, 'lost_sum': 0,
        }

    def add_tp_raw_log(self, ts, message):
        if self.is_capturing:
            self.captured_tp_raw_log.append({"timestamp": ts, "message": message})

    def add_tp_capture(self, flow, throughput_bps, lost):
        if not self.is_capturing:
            return
        from datetime import datetime
        self.captured_tp_res.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'flow': flow,
            'throughput_bps': round(throughput_bps, 2),
            'throughput_kbps': round(throughput_bps / 1000, 4),
            'lost_packets': lost,
        })
        s = self.tp_stats
        s['count'] += 1
        s['sum'] += throughput_bps
        s['lost_sum'] += lost
        if s['min'] is None or throughput_bps < s['min']:
            s['min'] = throughput_bps
        if s['max'] is None or throughput_bps > s['max']:
            s['max'] = throughput_bps
        if s['lost_min'] is None or lost < s['lost_min']:
            s['lost_min'] = lost
        if s['lost_max'] is None or lost > s['lost_max']:
            s['lost_max'] = lost
