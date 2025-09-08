"""
Gemini가 답변까지 처리하는 버전
"""

import os
import json
import tomllib
import google.generativeai as genai
from supabase import create_client, Client
from supabase_auth.types import Session

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, 
    QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QSplitter, QHeaderView, QDialog, QTabWidget
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from html_templates import HTMLTemplates as tmpl
from login_dialog import LoginDialog

class InventoryApp(QMainWindow):
    def __init__(self, user_session: Session = None):
        super().__init__()
        self.user_session = user_session
        self.supabase = None
        self.gemini_model = None
        self.is_admin = False
        self.employee_id = None
        self.user_name = ""
        self.system_prompt = ""

        self.setWindowTitle("JLT Dessert ChatBot")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        left_layout.addWidget(self.chat_display)

        self.input_layout = QHBoxLayout()
        self.input_line = QTextEdit() # QLineEdit -> QTextEdit
        self.input_line.setPlaceholderText("명령을 입력하세요")
        self.input_line.setMaximumHeight(90)
        self.input_line.installEventFilter(self)

        self.input_button = QPushButton("전송")
        self.input_button.clicked.connect(self.process_input)

        self.input_layout.addWidget(self.input_line)
        self.input_layout.addWidget(self.input_button, alignment=Qt.AlignBottom)
        left_layout.addLayout(self.input_layout)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        self.inventory_display_floor2 = self._create_inventory_table()
        self.inventory_display_floor3 = self._create_inventory_table()
        
        self.tabs.addTab(self.inventory_display_floor2, "2층")
        self.tabs.addTab(self.inventory_display_floor3, "3층")

        self.login_button = QPushButton("로그인")
        self.login_button.clicked.connect(self.handle_login)
        self.logout_button = QPushButton("로그아웃")
        self.logout_button.clicked.connect(self.handle_logout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.logout_button)

        right_layout.addWidget(self.tabs)
        right_layout.addLayout(button_layout)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 400])

        self.main_layout.addWidget(splitter)

        self.set_chat_enabled(False)
        self.logout_button.setEnabled(False)
        self.update_inventory_displays()

        self.chat_display.append(tmpl.generate_welcome_message())

    def eventFilter(self, obj, event):
        if obj is self.input_line and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if not (event.modifiers() & Qt.ShiftModifier):
                    self.process_input()
                    return True # 이벤트가 처리되었음을 알림
        return super().eventFilter(obj, event)

    def _create_inventory_table(self):
        table = QTableWidget()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["제품명", "수량"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        return table

    def set_chat_enabled(self, enabled: bool):
        self.input_line.setEnabled(enabled)
        self.input_button.setEnabled(enabled)
        if enabled:
            self.input_line.setPlaceholderText("명령을 입력하세요 (Shift+Enter로 줄바꿈)")
        else:
            self.input_line.setPlaceholderText("로그인 후 사용 가능합니다.")

    def handle_login(self):
        login_dialog = LoginDialog(self)
        if login_dialog.exec() == QDialog.Accepted:
            employee_id, password = login_dialog.get_credentials()
            email = f"{employee_id}@company.test"
            try:
                base_path = os.path.dirname(os.path.abspath(__file__))
                with open(os.path.join(base_path,'supabase.json'), 'r') as f:
                    config = json.load(f)
                    url = config.get("URL")
                    key = config.get("API")
                
                temp_supabase = create_client(url, key)
                self.user_session = temp_supabase.auth.sign_in_with_password({"email": email, "password": password})
                
                self.initialize_backend()
                self.update_inventory_displays()
                self.set_chat_enabled(True)
                self.login_button.setEnabled(False)
                self.logout_button.setEnabled(True)

            except Exception as e:
                self.chat_display.append(tmpl.generate_system_message(f"로그인 실패: {e}", is_error=True))

    def handle_logout(self):
        self.user_session = None
        self.supabase = None
        self.gemini_model = None
        self.is_admin = False
        self.employee_id = None
        self.user_name = ""
        self.system_prompt = ""
        
        self.set_chat_enabled(False)
        self.login_button.setEnabled(True)
        self.logout_button.setEnabled(False)
        self.update_inventory_displays()
        self.chat_display.append(tmpl.generate_system_message("로그아웃되었습니다."))

    def initialize_backend(self):
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
            with open(os.path.join(base_path, 'supabase.json'), 'r') as f:
                config = json.load(f)
                self.url: str = config.get("URL")
                key: str = config.get("API")
                gemini_api_key: str = config.get("GEMINI_API_KEY")
                self.service_role_key: str = config.get("SERVICE_ROLE_API")
            
            if not all([self.url, key, gemini_api_key, self.service_role_key]):
                raise ValueError("supabase.json에 필요한 모든 키가 없습니다.")
            
            with open(os.path.join(base_path, 'prompts.toml'), "rb") as f:
                cfg = tomllib.load(f)

            base_prompt_str   = cfg["base_prompt"]
            admin_actions_str = cfg["admin_actions"]
            common_actions_str= cfg["common_actions"]

            self.supabase = create_client(self.url, key)
            self.supabase.auth.set_session(self.user_session.session.access_token, self.user_session.session.refresh_token)
            
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel(model_name='gemini-2.0-flash')

            user_email = self.user_session.user.email
            self.employee_id = user_email.split('@')[0].upper()
            
            try:
                name_response = self.supabase.table("employees").select("name").eq("employee_id", self.employee_id).single().execute()
                if name_response.data:
                    self.user_name = name_response.data.get('name', self.employee_id)
                else:
                    self.user_name = self.employee_id

                role_response = self.supabase.rpc('get_my_role').execute()
                if role_response.data == '관리자':
                    self.is_admin = True
            except Exception as e:
                self.chat_display.append(tmpl.generate_system_message(f"사용자 정보 확인 중 오류 발생: {e}", is_error=True))
                return

            self.system_prompt = base_prompt_str
            if self.is_admin:
                self.system_prompt += admin_actions_str + common_actions_str.replace("- 'decrement'", "4. 'decrement'")
            else:
                self.system_prompt += common_actions_str.replace("- 'decrement'", "1. 'decrement'")

            self.chat_display.append(tmpl.generate_login_info_message(user_email, self.is_admin))

        except Exception as e:
            self.chat_display.append(tmpl.generate_system_message(f"초기화 오류: {e}", is_error=True))

    def get_natural_response_from_data(self, original_command: str, action: str, db_data: dict) -> str:
        """DB에서 받은 데이터를 바탕으로 Gemini를 호출하여 자연어 응답을 생성"""
        try:
            response_generation_prompt = f'''
            사용자의 원래 요청: '{original_command}'
            수행된 작업: '{action}'
            데이터베이스 결과: {json.dumps(db_data, ensure_ascii=False)}

            위 정보를 바탕으로 사용자에게 전달할 친절하고 자연스러운 응답 메시지를 한 문장으로 생성해줘.
            '''
            
            response = self.gemini_model.generate_content(response_generation_prompt)
            return response.text
        
        except Exception as e:
            return tmpl.generate_system_message(f"응답 생성 중 오류 발생: {e}", is_error=True)

    def update_inventory_displays(self):
        if not self.supabase:
            self._populate_table_logged_out(self.inventory_display_floor2)
            self._populate_table_logged_out(self.inventory_display_floor3)
            return

        try:
            data_f2, _ = self.supabase.table("inventory").select("product_name, quantity").eq("floor", 2).order("product_name").execute()
            self._populate_table(self.inventory_display_floor2, data_f2[1])

            data_f3, _ = self.supabase.table("inventory").select("product_name, quantity").eq("floor", 3).order("product_name").execute()
            self._populate_table(self.inventory_display_floor3, data_f3[1])

        except Exception as e:
            self.chat_display.append(tmpl.generate_system_message(f"재고 현황을 불러오는 중 오류 발생: {e}", is_error=True))

    def _populate_table(self, table_widget, data):
        table_widget.setRowCount(0)
        if data:
            for row_idx, product in enumerate(data):
                table_widget.insertRow(row_idx)
                table_widget.setItem(row_idx, 0, QTableWidgetItem(str(product['product_name'])))
                table_widget.setItem(row_idx, 1, QTableWidgetItem(str(product['quantity'])))
        else:
            table_widget.setRowCount(1)
            table_widget.setItem(0, 0, QTableWidgetItem("재고가 비어있습니다."))
            table_widget.setItem(0, 1, QTableWidgetItem(""))

    def _populate_table_logged_out(self, table_widget):
        table_widget.setRowCount(1)
        table_widget.setItem(0, 0, QTableWidgetItem("로그인 후 재고 정보를 볼 수 있습니다."))
        table_widget.setItem(0, 1, QTableWidgetItem(""))

    def process_input(self):
        command = self.input_line.toPlainText().strip()
        if not command or not self.supabase:
            return
        
        self.input_line.clear()

        if command.lower() == 'exit':
            self.close()
            return
        
        # HTML 표시에 사용할 메시지는 \n을 <br>로 변경
        html_command = command.replace('\n', '<br>')

        self.chat_display.append(tmpl.generate_user_message(self.user_name, html_command))

        full_prompt = self.system_prompt + "\n사용자 요청: " + command
        
        try:
            gemini_response = self.gemini_model.generate_content(full_prompt)
            response_text = gemini_response.text.strip()
            
            # self.chat_display.append(tmpl.generate_gemini_message())

            if response_text.startswith('```json'):
                response_text = response_text.lstrip('```json').strip()
            if response_text.endswith('```'):
                response_text = response_text.rstrip('```').strip()

            tasks_to_execute = []
            try:
                if response_text.startswith('['):
                    tasks_to_execute = json.loads(response_text)
                elif response_text.startswith('{'):
                    tasks_to_execute = [json.loads(response_text)]
                else:
                    fixed_text = f"[{response_text.replace('}{', '},{')}]"
                    tasks_to_execute = json.loads(fixed_text)

            except json.JSONDecodeError:
                self.chat_display.append(tmpl.generate_gemini_message(response_text))
                return
            except Exception as e:
                self.chat_display.append(tmpl.generate_system_message(f"JSON 파싱 중 알 수 없는 오류\n받은 내용:{response_text}", is_error=True))
                return

            execution_results = []
            update_required = False

            for task in tasks_to_execute:
                action = task.get("action")
                payload = task.get("payload", {})

                if action in ["query_all", "query_one", "increment", "show_purchase_logs", "delete_item", "add_employee", "delete_employee", "query_employees"] and not self.is_admin:
                    self.chat_display.append(tmpl.generate_system_message("이 명령을 실행할 권한이 없습니다.", is_error=True))
                    continue

                if action == "query_all":
                    self.update_inventory_displays()
                    self.chat_display.append(tmpl.generate_system_message("재고 현황을 새로고침했습니다."))
                    continue

                elif action == "query_one":
                    product_name = payload.get("name")
                    if not product_name:
                        self.chat_display.append(tmpl.generate_system_message("제품명이 명확하지 않습니다.", is_error=True))
                        continue
                    data, _ = self.supabase.table("inventory").select("product_name, quantity, floor").eq("product_name", product_name).execute()
                    natural_response = self.get_natural_response_from_data(command, action, data[1])
                    self.chat_display.append(tmpl.generate_gemini_message(natural_response))
                    continue

                elif action in ["show_purchase_logs", "query_employees"]:
                    if action == "show_purchase_logs":
                        self.chat_display.append(tmpl.generate_system_message("최근 구매 로그를 조회합니다..."))
                        response = self.supabase.rpc('get_purchase_logs_kst').execute()
                        html_table = tmpl.generate_purchase_logs_html(response.data)
                    else:
                        self.chat_display.append(tmpl.generate_system_message("직원 목록을 조회합니다..."))
                        response = self.supabase.table("employees").select("employee_id, name, role").execute()
                        html_table = tmpl.generate_employees_html(response.data)
                    
                    natural_response = self.get_natural_response_from_data(command, action, response.data)
                    self.chat_display.append(tmpl.generate_gemini_message(natural_response))
                    self.chat_display.append(html_table)
                    continue
                
                elif action == "decrement":
                    product_name = payload.get("name")
                    floor = payload.get("floor")
                    change_quantity = payload.get("quantity", 0)
                    if not all([product_name, floor, change_quantity > 0]):
                        execution_results.append({"action": action, "status": "fail", "reason": "제품명, 층, 수량 정보 누락"})
                        continue
                    
                    try:
                        data, _ = self.supabase.table("inventory").select("item_id, quantity").eq("product_name", product_name).eq("floor", floor).single().execute()
                        item_id = data[1]['item_id']
                        current_quantity = data[1]['quantity']

                        if current_quantity < change_quantity:
                            execution_results.append({"action": action, "product_name": product_name, "floor": floor, "status": "fail", "reason": f"재고 부족 (현재 {current_quantity}개)"})
                            continue
                        
                        new_quantity = current_quantity - change_quantity
                        self.supabase.table("inventory").update({"quantity": new_quantity}).eq("product_name", product_name).eq("floor", floor).execute()
                        self.supabase.table("purchase_logs").insert({"employee_id": self.employee_id, "item_id": item_id, "product_name": product_name, "quantity": change_quantity}).execute()
                        execution_results.append({"action": action, "product_name": product_name, "floor": floor, "quantity": change_quantity, "status": "success"})
                        update_required = True
                    except Exception as e:
                        execution_results.append({"action": action, "product_name": product_name, "floor": floor, "status": "fail", "reason": f"DB 오류: {e}"})

                elif action == "increment":
                    product_name = payload.get("name")
                    floor = payload.get("floor")
                    change_quantity = payload.get("quantity", 0)
                    if not all([product_name, floor, change_quantity > 0]):
                        execution_results.append({"action": action, "status": "fail", "reason": "제품명, 층, 수량 정보 누락"})
                        continue
                    
                    try:
                        data, _ = self.supabase.table("inventory").select("id, quantity").eq("product_name", product_name).eq("floor", floor).single().execute()
                        current_quantity = data[1]['quantity'] if data[1] else 0
                        new_quantity = current_quantity + change_quantity
                        
                        if not data[1]:
                            self.supabase.table("inventory").insert({"product_name": product_name, "quantity": new_quantity, "floor": floor}).execute()
                        else:
                            self.supabase.table("inventory").update({"quantity": new_quantity}).eq("product_name", product_name).eq("floor", floor).execute()
                        
                        execution_results.append({"action": action, "product_name": product_name, "floor": floor, "quantity": change_quantity, "status": "success"})
                        update_required = True
                    except Exception as e:
                        execution_results.append({"action": action, "product_name": product_name, "floor": floor, "status": "fail", "reason": f"DB 오류: {e}"})

                elif action == "delete_item":
                    product_name = payload.get("name")
                    floor = payload.get("floor")
                    if not all([product_name, floor]):
                        execution_results.append({"action": action, "status": "fail", "reason": "제품명, 층 정보 누락"})
                        continue
                    
                    try:
                        data, _ = self.supabase.table("inventory").delete().eq("product_name", product_name).eq("floor", floor).execute()
                        if data[1]:
                            execution_results.append({"action": action, "product_name": product_name, "floor": floor, "status": "success"})
                            update_required = True
                        else:
                            execution_results.append({"action": action, "product_name": product_name, "floor": floor, "status": "fail", "reason": "삭제할 아이템을 찾지 못함"})
                    except Exception as e:
                        execution_results.append({"action": action, "product_name": product_name, "floor": floor, "status": "fail", "reason": f"DB 오류: {e}"})

                elif action == "add_employee":
                    pass

                elif action == "delete_employee":
                    pass

                elif action == "error":
                    error_message = payload.get("message", "알 수 없는 오류입니다.")
                    self.chat_display.append(tmpl.generate_system_message(f"{error_message}", is_error=True))

                else:
                    self.chat_display.append(tmpl.generate_gemini_message(response_text))

            if execution_results:
                natural_response = self.get_natural_response_from_data(
                    original_command=command,
                    action="multiple_operations",
                    db_data=execution_results
                )
                self.chat_display.append(tmpl.generate_gemini_message(natural_response))
            
            if update_required:
                self.update_inventory_displays()

        except Exception as e:
            self.chat_display.append(tmpl.generate_system_message(f"처리 중 오류가 발생했습니다: {e}", is_error=True))

def main(user_session: Session):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        qss_path = os.path.join(base_path, 'style.qss')
        with open(qss_path, 'r') as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: style.qss not found. Running with default styles.")
    except Exception as e:
        print(f"Warning: Could not load stylesheet. {e}")

    window = InventoryApp(user_session)
    window.show()
    app.exec()
