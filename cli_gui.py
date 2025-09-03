import os
import json
import tomllib
import google.generativeai as genai
from supabase import create_client, Client
from supabase_auth.types import Session


from PySide6.QtWidgets import (
                               QApplication, QMainWindow, QWidget, 
                               QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
                               QTextEdit, QSplitter, QHeaderView)
from PySide6.QtCore import Qt

class InventoryApp(QMainWindow):
    def __init__(self, user_session: Session):
        super().__init__()
        self.user_session = user_session
        self.supabase = None
        self.gemini_model = None
        self.is_admin = False
        self.employee_id = None
        self.system_prompt = ""

        self.setWindowTitle("디저트 재고 관리 시스템")
        self.setGeometry(100, 100, 1200, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 화면을 좌우로 나누기 위한 스플리터
        splitter = QSplitter(Qt.Horizontal)

        # --- 왼쪽 패널 (채팅) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        left_layout.addWidget(self.chat_display)

        # 입력 라인과 버튼
        self.input_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("명령을 입력하세요...")
        self.input_button = QPushButton("전송")
        self.input_button.clicked.connect(self.process_input)
        self.input_line.returnPressed.connect(self.process_input)

        self.input_layout.addWidget(self.input_line)
        self.input_layout.addWidget(self.input_button)
        left_layout.addLayout(self.input_layout)

        # --- 오른쪽 패널 (재고 현황) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        self.inventory_display = QTableWidget()
        self.inventory_display.setEditTriggers(QTableWidget.NoEditTriggers)
        self.inventory_display.setColumnCount(2)
        self.inventory_display.setHorizontalHeaderLabels(["제품명", "수량"])
        self.inventory_display.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.inventory_display.verticalHeader().setVisible(False)
        self.inventory_display.setAlternatingRowColors(True)

        right_layout.addWidget(self.inventory_display)

        # 스플리터에 패널 추가
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 400]) # 초기 사이즈 분배

        self.main_layout.addWidget(splitter)

        self.initialize_backend()
        self.update_inventory_display()

    def initialize_backend(self):
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
            #supabase.json 로드
            supabase_json_path = os.path.join(base_path, 'supabase.json')
            with open(supabase_json_path, 'r') as f:
                config = json.load(f)
                self.url: str = config.get("URL")
                key: str = config.get("API")
                gemini_api_key: str = config.get("GEMINI_API_KEY")
                self.service_role_key: str = config.get("SERVICE_ROLE_API")
            
            if not all([self.url, key, gemini_api_key, self.service_role_key]):
                raise ValueError("supabase.json에 URL, API, GEMINI_API_KEY, SERVICE_ROLE_API가 모두 필요합니다.")
            
            # prompts.toml 로드
            prompts_toml_path = os.path.join(base_path, 'prompts.toml')
            with open(prompts_toml_path, "rb") as f:
                cfg = tomllib.load(f)

            base_prompt_str   = cfg["base_prompt"]
            admin_actions_str = cfg["admin_actions"]
            common_actions_str= cfg["common_actions"]

            if not all([base_prompt_str, admin_actions_str, common_actions_str]):
                raise ValueError("prompts.toml 파일에 필요한 프롬프트 섹션이 누락되었습니다.")

            self.supabase = create_client(self.url, key)
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel(model_name='gemini-1.5-flash')

            self.supabase.auth.set_session(self.user_session.session.access_token, self.user_session.session.refresh_token)

            # 사용자 역할 확인
            user_email = self.user_session.user.email
            self.employee_id = user_email.split('@')[0]
            
            try:
                response = self.supabase.rpc('get_my_role').execute()
                user_role = response.data
                if user_role == '관리자':
                    self.is_admin = True
            except Exception as e:
                self.show_message("오류", f"사용자 역할 확인 중 오류 발생: {e}")
                return

            # 역할에 따른 시스템 프롬프트 동적 생성
            self.system_prompt = base_prompt_str
            if self.is_admin:
                self.system_prompt += admin_actions_str + common_actions_str.replace("- 'decrement'", "4. 'decrement'")
            else:
                self.system_prompt += common_actions_str.replace("- 'decrement'", "1. 'decrement'")

            self.chat_display.append("<p><b>환영합니다!</b> 디저트 재고 관리 시스템에 오신 것을 환영합니다!</p>")
            self.chat_display.append(f"<p><b>로그인 정보:</b> {user_email} ({ '관리자' if self.is_admin else '일반'})</p>")

        except Exception as e:
            self.show_message("초기화 오류", f"초기화 오류: {e}")

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)

    def update_inventory_display(self):
        try:
            if self.supabase:
                data, count = self.supabase.table("inventory").select("product_name, quantity").order("product_name").execute()
                
                self.inventory_display.setRowCount(0) # Clear existing rows
                
                if data[1]:
                    for row_idx, product in enumerate(data[1]):
                        self.inventory_display.insertRow(row_idx)
                        self.inventory_display.setItem(row_idx, 0, QTableWidgetItem(str(product['product_name'])))
                        self.inventory_display.setItem(row_idx, 1, QTableWidgetItem(str(product['quantity'])))
                else:
                    self.inventory_display.setRowCount(1)
                    self.inventory_display.setItem(0, 0, QTableWidgetItem("재고가 비어있습니다."))
                    self.inventory_display.setItem(0, 1, QTableWidgetItem("")) # Empty cell for quantity
            else:
                self.inventory_display.setRowCount(1)
                self.inventory_display.setItem(0, 0, QTableWidgetItem("재고 정보를 불러올 수 없습니다. 백엔드 초기화 실패."))
                self.inventory_display.setItem(0, 1, QTableWidgetItem("")) # Empty cell for quantity
        except Exception as e:
            self.show_message("재고 현황 업데이트 오류", f"재고 현황을 불러오는 중 오류 발생: {e}")

    def process_input(self):
        command = self.input_line.text().strip()
        self.input_line.clear()

        if not command:
            return

        if command.lower() == 'exit':
            self.close()
            return

        user_msg_html = f"""
        <table width='100%'><tr><td align='right'>
            <span style='display: inline-block; text-align: left; margin: 5px; padding: 10px; background-color: #409eff; color: white; border-radius: 12px; border-bottom-right-radius: 0px;'>{command}</span>
        </td></tr></table>
        """
        self.chat_display.append(user_msg_html)

        full_prompt = self.system_prompt + "\n사용자 요청: " + command
        
        try:
            gemini_response = self.gemini_model.generate_content(full_prompt)
            response_text = gemini_response.text.strip()
            
            gemini_msg_html = f"""
            <table width='100%'><tr><td align='left'>
                <span style='display: inline-block; text-align: left; margin: 5px; padding: 10px; background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 12px; border-bottom-left-radius: 0px;'><b>Gemini:</b><br>알겠습니다. 요청을 처리합니다.</span>
            </td></tr></table>
            """
            self.chat_display.append(gemini_msg_html)

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
                # Non-JSON responses from Gemini are treated as simple text messages
                pass
            except Exception as e:
                self.show_message("오류", f"JSON 파싱 중 알 수 없는 오류: {e}\n받은 내용:" + response_text)
                return

            for task in tasks_to_execute:
                action = task.get("action")
                payload = task.get("payload", {})

                if action in ["query_all", "query_one", "increment", "show_purchase_logs", "delete_item", "add_employee", "delete_employee"] and not self.is_admin:
                    self.show_message("오류", "이 명령을 실행할 권한이 없습니다.")
                    continue

                if action == "query_all":
                    self.update_inventory_display()
                    self.chat_display.append("<p style='color: #555; margin-left: 10px;'>-&gt; 재고 현황을 새로고침했습니다.</p>")

                elif action == "decrement":
                    product_name = payload.get("name")
                    change_quantity = payload.get("quantity", 0)
                    if not product_name or change_quantity <= 0:
                        self.show_message("오류", "제품명과 수량이 명확하지 않습니다.")
                        continue
                    
                    data, count = self.supabase.table("inventory").select("item_id, quantity").eq("product_name", product_name).execute()
                    if not data[1]:
                        self.show_message("오류", f"'{product_name}'(을)를 찾을 수 없습니다.")
                        continue

                    item_id = data[1][0]['item_id']
                    current_quantity = data[1][0]['quantity']

                    if current_quantity < change_quantity:
                        self.show_message("오류", f"'{product_name}'의 재고({current_quantity}개)가 부족합니다!")
                        continue
                    
                    new_quantity = current_quantity - change_quantity
                    self.supabase.table("inventory").update({"quantity": new_quantity}).eq("product_name", product_name).execute()
                    
                    self.supabase.table("purchase_logs").insert({
                        "employee_id": self.employee_id,
                        "item_id": item_id,
                        "product_name": product_name,
                        "quantity": change_quantity
                    }).execute()
                    self.chat_display.append(f"<p style='color: #555; margin-left: 10px;'>-&gt; '{product_name}' {change_quantity}개가 차감되었습니다. 현재 재고: {new_quantity}개</p>")
                    self.update_inventory_display()

                elif action == "increment":
                    product_name = payload.get("name")
                    change_quantity = payload.get("quantity", 0)
                    if not product_name or change_quantity <= 0:
                        self.show_message("오류", "제품명과 수량이 명확하지 않습니다.")
                        continue

                    data, count = self.supabase.table("inventory").select("id, quantity").eq("product_name", product_name).execute()
                    current_quantity = data[1][0]['quantity'] if data[1] else 0
                    new_quantity = current_quantity + change_quantity
                    
                    if not data[1]:
                        insert_response = self.supabase.table("inventory").insert({
                            "product_name": product_name, 
                            "quantity": new_quantity
                        }).execute()

                        if insert_response.data:
                            newly_inserted_id = insert_response.data[0]['id']
                            
                            self.supabase.table("inventory").update({
                                "item_id": newly_inserted_id
                            }).eq("id", newly_inserted_id).execute()
                    else:
                        self.supabase.table("inventory").update({"quantity": new_quantity}).eq("product_name", product_name).execute()
                    self.chat_display.append(f"<p style='color: #555; margin-left: 10px;'>-&gt; '{product_name}' {change_quantity}개가 추가되었습니다. 현재 재고: {new_quantity}개</p>")
                    self.update_inventory_display()

                elif action == "query_one":
                    product_name = payload.get("name")
                    if not product_name:
                        self.show_message("오류", "제품명이 명확하지 않습니다.")
                        continue
                    
                    data, count = self.supabase.table("inventory").select("quantity").eq("product_name", product_name).execute()
                    if data[1]:
                        self.chat_display.append(f"<p style='color: #555; margin-left: 10px;'>-&gt; '{product_name}'의 현재 재고는 {data[1][0]['quantity']}개 입니다.</p>")
                    else:
                        self.chat_display.append(f"<p style='color: #555; margin-left: 10px;'>-&gt; '{product_name}'은(는) 재고에 없습니다.</p>")
                
                elif action == "show_purchase_logs":
                    self.chat_display.append("<p style='color: #555; margin-left: 10px;'>-&gt; 최근 구매 로그를 조회합니다...</p>")
                    response = self.supabase.rpc('get_purchase_logs_kst').execute()
                    if not response.data:
                        self.chat_display.append("<p style='color: #555; margin-left: 10px;'>-&gt; 구매 기록이 없습니다.</p>")
                    else:
                        log_html = "<p style='color: #555; margin-left: 10px;'>-&gt; <b>최근 구매 기록 (최대 20개):</b></p>"
                        log_html += "<table border='1' style='border-collapse: collapse; margin-left: 10px;'><tr><th>일시</th><th>사용자</th><th>제품</th><th>수량</th></tr>"
                        for log in response.data:
                            log_html += f"<tr><td>{log['created_at']}</td><td>{log['employee_id']}</td><td>{log['product_name']}</td><td>{log['quantity']}</td></tr>"
                        log_html += "</table>"
                        self.chat_display.append(log_html)
                
                elif action == "delete_item":
                    product_name = payload.get("name")
                    if not product_name:
                        self.show_message("오류", "삭제할 제품명이 명확하지 않습니다.")
                        continue
                    
                    data, count = self.supabase.table("inventory").delete().eq("product_name", product_name).execute()
                    
                    if data[1]:
                         self.chat_display.append(f"<p style='color: #555; margin-left: 10px;'>-&gt; '{product_name}'이(가) 재고에서 삭제되었습니다.</p>")
                         self.update_inventory_display()
                    else:
                         self.chat_display.append(f"<p style='color: #555; margin-left: 10px;'>-&gt; 오류: '{product_name}'을(를) 찾을 수 없거나 삭제하지 못했습니다.</p>")

                elif action == "add_employee":
                    employee_id_to_add = payload.get("employee_id")
                    name = payload.get("name")
                    password = payload.get("password")
                    role = payload.get("role", "")

                    if not all([employee_id_to_add, name, password]):
                        self.show_message("오류", "사번, 이름, 비밀번호는 필수입니다.")
                        continue
                    
                    email = f"{employee_id_to_add}@company.test"
                    
                    try:
                        auth_response = self.supabase.auth.sign_up({"email": email, "password": password})
                        
                        if auth_response.user:
                            auth_user_id = auth_response.user.id
                            
                            data, count = self.supabase.table("employees").insert({
                                "employee_id": employee_id_to_add,
                                "name": name,
                                "role": role,
                                "auth_user_id": auth_user_id
                            }).execute()

                            if data[1]:
                                self.chat_display.append(f"<p style='color: #555; margin-left: 10px;'>-&gt; 임직원 '{name}'이(가) 추가되었습니다.</p>")
                            else:
                                self.show_message("오류", "임직원 정보 추가에 실패했습니다. 생성된 인증 계정을 수동으로 삭제해야 할 수 있습니다.")
                        else:
                            self.show_message("오류", f"인증 계정 생성에 실패했습니다. {auth_response}")

                    except Exception as e:
                        self.show_message("오류", f"계정 생성 중 오류 발생: {e}")

                elif action == "delete_employee":
                    employee_id_to_delete = payload.get("employee_id")
                    name = payload.get("name")
                    
                    if not employee_id_to_delete and not name:
                        self.show_message("오류", "사번 또는 이름은 필수입니다.")
                        continue

                    query = self.supabase.table("employees").select("auth_user_id")
                    if employee_id_to_delete:
                        query = query.eq("employee_id", employee_id_to_delete)
                    else:
                        query = query.eq("name", name)
                    
                    data, count = query.execute()

                    if not data[1]:
                        self.show_message("오류", "해당 임직원을 찾을 수 없습니다.")
                        continue

                    auth_user_id_to_delete = data[1][0].get('auth_user_id')

                    if not auth_user_id_to_delete:
                        if employee_id_to_delete:
                            self.supabase.table("employees").delete().eq("employee_id", employee_id_to_delete).execute()
                        else:
                            self.supabase.table("employees").delete().eq("name", name).execute()
                        self.chat_display.append("<p style='color: #555; margin-left: 10px;'>-&gt; employees 테이블에서만 임직원이 삭제되었습니다.</p>")
                        continue

                    try:
                        admin_supabase: Client = create_client(self.url, self.service_role_key)
                        admin_supabase.auth.admin.delete_user(auth_user_id_to_delete)
                        
                        if employee_id_to_delete:
                            self.supabase.table("employees").delete().eq("employee_id", employee_id_to_delete).execute()
                        else:
                            self.supabase.table("employees").delete().eq("name", name).execute()
                        
                        self.chat_display.append(f"<p style='color: #555; margin-left: 10px;'>-&gt; 임직원이 삭제되었습니다.</p>")

                    except Exception as e:
                        self.show_message("오류", f"임직원 삭제 중 오류 발생: {e}")

                elif action == "error":
                    error_message = payload.get("message", "알 수 없는 오류입니다.")
                    self.chat_display.append(f"<p style='color: red; margin-left: 10px;'>-&gt; 오류: {error_message}</p>")

                else:
                    # Gemini가 JSON action을 반환하지 않고 일반 텍스트로만 응답한 경우, 그대로 채팅창에 표시
                    pass

        except Exception as e:
            self.show_message("처리 중 오류", f"처리 중 오류가 발생했습니다: {e}")

def main(user_session: Session):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Load stylesheet
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