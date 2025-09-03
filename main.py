import sys
import json
import os
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
)
from supabase import create_client, Client
from supabase_auth.errors import AuthApiError
from pathlib import Path
from cli_gui import main
# from cli import start_cli

# Supabase 클라이언트 설정

try:
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'supabase.json')
    
    with open(json_path, 'r') as f:
        config = json.load(f)
        url = config.get("URL")
        key = config.get("API")

        if not url or not key:
            raise ValueError("supabase.json 파일에 URL과 API 키를 제공해야 합니다.")
        
    supabase: Client = create_client(url, key)

except (FileNotFoundError, ValueError) as e:
    print(f"오류:{e}", file=sys.stderr)
    sys.exit(1)


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini CLI - 로그인")
        self.resize(350, 200)
        self.session = None

        # 메인 레이아웃
        main_layout = QVBoxLayout(self)

        # 이메일 입력
        employee_id_layout = QHBoxLayout()
        employee_id_label = QLabel("사번:")
        self.employee_id_input = QLineEdit()
        self.employee_id_input.setPlaceholderText("예: 12345")
        employee_id_layout.addWidget(employee_id_label)
        employee_id_layout.addWidget(self.employee_id_input)

        # 비밀번호 입력
        password_layout = QHBoxLayout()
        password_label = QLabel("비밀번호:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)

        # 로그인 버튼
        self.login_button = QPushButton("로그인")
        self.login_button.clicked.connect(self.handle_login)

        # 상태 메시지 라벨
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red")

        # 레이아웃에 위젯 추가
        main_layout.addLayout(employee_id_layout)
        main_layout.addLayout(password_layout)
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        main_layout.addWidget(self.login_button)
        main_layout.addWidget(self.status_label)
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))


    def handle_login(self):
        employee_id = self.employee_id_input.text()
        password = self.password_input.text()

        if not employee_id or not password:
            self.status_label.setText("사번과 비밀번호를 모두 입력하세요.")
            return

        # TODO: Supabase 인증 로직 추가
        email = f"{employee_id}@company.test"
        print(f"로그인 시도 (내부 이메일): {email}")
        self.status_label.setText(f"로그인 시도 중...")
        QApplication.processEvents() # UI가 멈추지 않도록 이벤트 처리

        try:
            self.session = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            self.status_label.setStyleSheet("color: blue")
            self.status_label.setText("로그인 성공!")
            # self.upsert_user_to_json(json_path,employee_id)
            QApplication.processEvents()
            self.close()

        except AuthApiError as e:
            self.status_label.setStyleSheet("color: red")
            self.status_label.setText(f"로그인 실패: {e.message}")
        except Exception as e:
            self.status_label.setStyleSheet("color: red")
            self.status_label.setText(f"알 수 없는 오류: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    app.exec()

     # 로그인 창이 닫힌 후, 세션 정보가 있는지 확인
    if window.session:
        print("--- 로그인 성공 ---")
        print("사용자 ID:", window.session.user.id)
        print("인증 토큰(일부):", window.session.session.access_token[:30] + "...")

        # start_cli(window.session)
        main(window.session)
    else:
        print("로그인이 취소되었거나 실패했습니다.")