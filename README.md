# Merlot Macro 컨트롤러 개요

본 문서는 Merlot Macro 애플리케이션의 컨트롤러 구성 요소에 대한 상세 설명서입니다. 애플리케이션은 Model-View-Controller (MVC) 아키텍처 패턴을 기반으로 설계되었으며, 이를 통해 데이터, 사용자 인터페이스, 비즈니스 로직이 명확하게 분리되어 있습니다. 본 문서에서는 두 가지 핵심 컨트롤러인 `AppController`와 `SerialController`의 역할, 책임, 그리고 상호 작용 방식에 대해 기술합니다.

## 1. 아키텍처 및 주요 구성 요소

애플리케이션의 핵심 아키텍처는 다음과 같은 4개의 주요 파이썬 파일로 구성됩니다.

- **`main_app.py`**: 애플리케이션의 진입점(Entry Point). MVC 구성 요소(Model, View, Controllers)를 초기화하고 서로 연결합니다.
- **`app_model.py` (`Model`)**: 애플리케이션의 모든 데이터와 상태(노드 목록, 그룹 정보, 캡처된 로그 데이터 등)를 저장하고 관리합니다.
- **`main_app.py 내 App 클래스` (`View`)**: `tkinter`를 사용하여 사용자 인터페이스(UI)를 생성하고 사용자 입력을 받습니다.
- **`app_controller.py` (`Controller`)**: 주 컨트롤러. UI(View)로부터의 이벤트를 처리하고, 비즈니스 로직을 수행하며, Model의 데이터를 갱신합니다.
- **`serial_controller.py` (`Controller`)**: 하드웨어와의 시리얼 통신을 전담하는 특수 컨트롤러입니다.

### 1.1. `app_controller.py`

`AppController`는 애플리케이션의 중앙 두뇌 역할을 수행합니다. 사용자의 UI 조작(버튼 클릭, 텍스트 입력 등)에 직접적으로 반응하며, 비즈니스 로직의 대부분을 처리합니다.

#### 주요 책임:
- **사용자 입력 처리**: View로부터 발생하는 이벤트를 받아 적절한 로직을 실행합니다. (예: '노드 추가' 버튼 클릭 시 `add_node` 메소드 호출)
- **비즈니스 로직 수행**: 노드 및 그룹 관리, LED 상태 제어, 테스트 명령 실행, 데이터 캡처 및 저장 등 애플리케이션의 핵심 기능을 담당합니다.
- **모델 업데이트**: 로직 수행 결과에 따라 `AppModel`의 상태를 변경합니다. 예를 들어, 시리얼 통신으로 새로운 데이터를 수신하면 `handle_serial_data` 콜백을 통해 모델의 데이터 목록을 업데이트합니다.
- **시리얼 통신 조율**: 실제 하드웨어에 명령을 보내야 할 경우, `SerialController`의 `send_command` 메소드를 호출하여 통신을 위임합니다.

### 1.2. `serial_controller.py`

`SerialController`는 하드웨어 장치와의 저수준(low-level) 시리얼(Serial) 통신을 전담합니다. 이를 통해 메인 애플리케이션 스레드가 블로킹(blocking)되는 것을 방지하고 비동기적인 통신을 원활하게 처리합니다.

#### 주요 책임:
- **포트 관리**: 사용 가능한 시리얼 포트를 스캔하고, 지정된 포트와의 연결 및 연결 해제를 관리합니다.
- **비동기 명령 전송 및 수신**: `AppController`로부터 받은 명령 문자열을 하드웨어에 전송합니다. `tkinter`의 `after` 메소드를 활용하여 비동기적으로 응답을 지속적으로 확인합니다.
- **응답 처리 및 파싱**: 하드웨어로부터 응답이 오면, 이를 수신하고 정리(parsing)하여 유의미한 데이터로 가공합니다. 이 과정에서 명령어, 프롬프트, 불필요한 공백 등을 제거합니다.
- **콜백 실행**: 응답 처리가 완료되면, 가공된 데이터(성공 여부, 응답 시간, 파싱된 결과 등)를 `AppController`에 등록된 `data_callback` 함수를 통해 전달합니다.

## 2. 동작 방식 및 데이터 흐름

컨트롤러 중심의 데이터 흐름은 다음과 같습니다.

1.  **초기화**: `main_app.py`가 실행되면 Model, View, `SerialController`, `AppController` 순서로 객체가 생성됩니다. 이때 Model과 `SerialController`의 인스턴스가 `AppController`에 주입되고, `AppController`는 View에 연결됩니다.
2.  **사용자 이벤트 발생**: 사용자가 View에서 버튼을 클릭합니다.
3.  **`AppController` 로직 호출**: View는 연결된 `AppController`의 해당 메소드를 호출합니다.
4.  **명령 전송 (필요시)**: `AppController`가 하드웨어 제어가 필요한 명령이라고 판단하면, `SerialController`의 `send_command`를 호출하여 명령 문자열을 전달합니다.
5.  **`SerialController` 통신 수행**:
    - `SerialController`는 포트가 연결되어 있는지 확인하고 명령을 시리얼 포트에 기록합니다.
    - 이후 비동기적으로 응답을 기다리며, 응답이 감지되면 데이터를 수신하고 파싱합니다.
6.  **데이터 콜백 및 모델 업데이트**:
    - 파싱된 데이터는 `AppController`의 `handle_serial_data` 콜백 함수로 전달됩니다.
    - `AppController`는 이 데이터를 기반으로 `AppModel`의 상태를 업데이트합니다. (예: `model.add_test_capture(record)`)
7.  **View 업데이트**: `AppController` 또는 `AppModel`의 데이터 변경을 감지한 View는 UI를 스스로 갱신하여 사용자에게 최신 상태를 보여줍니다. (예: `view.update_statistics_display()`)

이러한 구조를 통해 각 컴포넌트는 자신의 책임에만 집중할 수 있으며, 특히 복잡한 시리얼 통신 로직이 `AppController`의 비즈니스 로직과 분리되어 코드의 유지보수성과 확장성이 향상됩니다.
