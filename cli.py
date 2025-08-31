import os
import json
import tomllib
import google.generativeai as genai
from supabase import create_client, Client
from supabase_auth.types import Session

def start_cli(user_session: Session):
    """인증된 세션을 기반으로 대화형 CLI를 시작합니다."""

    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        #supabase.json 로드
        supabase_json_path = os.path.join(base_path, 'supabase.json')
        with open(supabase_json_path, 'r') as f:
            config = json.load(f)
            url: str = config.get("URL")
            key: str = config.get("API")
            gemini_api_key: str = config.get("GEMINI_API_KEY")
            service_role_key: str = config.get("SERVICE_ROLE_API") # Added service_role_key
        
        if not all([url, key, gemini_api_key, service_role_key]):
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

        supabase: Client = create_client(url, key)
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(model_name='gemini-2.0-flash')

    except Exception as e:
        print(f"초기화 오류: {e}")
        return

    supabase.auth.set_session(user_session.session.access_token, user_session.session.refresh_token)

    # --- 1. 사용자 역할 확인 ---
    is_admin = False
    user_email = user_session.user.email
    employee_id = user_email.split('@')[0]
    
    try:
        response = supabase.rpc('get_my_role').execute()
        user_role = response.data
        if user_role == '관리자':
            is_admin = True
    except Exception as e:
        print(f"사용자 역할 확인 중 오류 발생: {e}")
        return

    # --- 2. 역할에 따른 시스템 프롬프트 동적 생성 ---
    system_prompt = base_prompt_str
    if is_admin:
        system_prompt += admin_actions_str + common_actions_str.replace("- 'decrement'", "4. 'decrement'")
    else:
        system_prompt += common_actions_str.replace("- 'decrement'", "1. 'decrement'")


    print("\n========================================")
    print(" 디저트 재고 관리 CLI (MCP)에 오신 것을 환영합니다!")
    print(f" 로그인된 사용자: {user_email} ({ '관리자' if is_admin else '일반'})")
    print("========================================")
    print("명령을 입력하세요. (종료하려면 'exit' 또는 Ctrl+C 입력)")

    while True:
        try:
            command = input("> ").strip()
            if command.lower() == 'exit':
                break
            if not command:
                continue

            full_prompt = system_prompt + "\n사용자 요청: " + command
            gemini_response = model.generate_content(full_prompt)
            
            response_text = gemini_response.text.strip()
            # Gemini 응답에서 Markdown 코드 블록 마커 제거
            if response_text.startswith('```json'):
                response_text = response_text.lstrip('```json').strip()
            if response_text.endswith('```'):
                response_text = response_text.rstrip('```').strip()

            # JSON 파싱 로직 개선: 단일 객체 또는 배열 처리
            tasks_to_execute = []
            try:
                # 응답이 배열 형태일 경우
                if response_text.startswith('['):
                    tasks_to_execute = json.loads(response_text)
                # 응답이 단일 객체 형태일 경우
                elif response_text.startswith('{'):
                    tasks_to_execute = [json.loads(response_text)]
                else:
                    # Gemini가 여러 객체를 배열 없이 반환한 경우 (예: }{)를 처리
                    # 이 부분은 Gemini가 프롬프트 지시를 따르지 않을 때의 방어 로직
                    fixed_text = f"[{response_text.replace('}{', ',')}]"
                    tasks_to_execute = json.loads(fixed_text)

            except json.JSONDecodeError:
                print("오류: Gemini가 보낸 응답이 올바른 JSON 형식이 아닙니다.")
                print("받은 내용:", response_text)
                continue
            except Exception as e:
                print(f"JSON 파싱 중 알 수 없는 오류: {e}")
                print("받은 내용:", response_text)
                continue

            # 각 작업을 순서대로 실행
            for task in tasks_to_execute:
                action = task.get("action")
                payload = task.get("payload", {})

                if action in ["query_all", "query_one", "increment", "show_purchase_logs", "delete_item", "add_employee", "delete_employee"] and not is_admin:
                    print("  -> 오류: 이 명령을 실행할 권한이 없습니다.")
                    continue

                if action == "query_all":
                    data, count = supabase.table("inventory").select("product_name, quantity").execute()
                    if not data[1]:
                        print("  -> 재고가 비어있습니다.")
                    else:
                        print("  -> 현재 재고:")
                        for product in data[1]:
                            print(f"    - {product['product_name']}: {product['quantity']}개")

                elif action == "decrement":
                    product_name = payload.get("name")
                    change_quantity = payload.get("quantity", 0)
                    if not product_name or change_quantity <= 0:
                        print("  -> 오류: 제품명과 수량이 명확하지 않습니다.")
                        continue
                    
                    data, count = supabase.table("inventory").select("item_id, quantity").eq("product_name", product_name).execute()
                    if not data[1]:
                        print(f"  -> 오류: '{product_name}'을(를) 찾을 수 없습니다.")
                        continue

                    item_id = data[1][0]['item_id']
                    current_quantity = data[1][0]['quantity']

                    if current_quantity < change_quantity:
                        print(f"  -> 오류: '{product_name}'의 재고({current_quantity}개)가 부족합니다!")
                        continue
                    
                    print(f"  -> '{product_name}' {change_quantity}개 차감 및 로그 기록...")
                    new_quantity = current_quantity - change_quantity
                    supabase.table("inventory").update({"quantity": new_quantity}).eq("product_name", product_name).execute()
                    
                    supabase.table("purchase_logs").insert({
                        "employee_id": employee_id,
                        "item_id": item_id,
                        "product_name": product_name,
                        "quantity": change_quantity
                    }).execute()
                    print(f"  -> 완료! '{product_name}'의 현재 재고는 {new_quantity}개 입니다.")

                elif action == "increment":
                    product_name = payload.get("name")
                    change_quantity = payload.get("quantity", 0)
                    if not product_name or change_quantity <= 0:
                        print("  -> 오류: 제품명과 수량이 명확하지 않습니다.")
                        continue

                    data, count = supabase.table("inventory").select("id, quantity").eq("product_name", product_name).execute()
                    current_quantity = data[1][0]['quantity'] if data[1] else 0
                    new_quantity = current_quantity + change_quantity
                    
                    print(f"  -> '{product_name}' {change_quantity}개 추가...")
                    if not data[1]:
                        insert_response = supabase.table("inventory").insert({
                            "product_name": product_name, 
                            "quantity": new_quantity
                        }).execute()

                        # item_id를 일단은 id랑 동일하게 하고 나중에 바코드 같은걸로 변경하자
                        if insert_response.data:
                            newly_inserted_id = insert_response.data[0]['id']
                            
                            supabase.table("inventory").update({
                                "item_id": newly_inserted_id
                            }).eq("id", newly_inserted_id).execute()
                    else:
                        supabase.table("inventory").update({"quantity": new_quantity}).eq("product_name", product_name).execute()
                    print(f"  -> 완료! '{product_name}'의 현재 재고는 {new_quantity}개 입니다.")

                elif action == "query_one":
                    product_name = payload.get("name")
                    if not product_name:
                        print("  -> 오류: 제품명이 명확하지 않습니다.")
                        continue
                    
                    data, count = supabase.table("inventory").select("quantity").eq("product_name", product_name).execute()
                    if data[1]:
                        print(f"  -> '{product_name}'의 현재 재고는 {data[1][0]['quantity']}개 입니다.")
                    else:
                        print(f"  -> '{product_name}'은(는) 재고에 없습니다.")
                
                elif action == "show_purchase_logs":
                    print("  -> 최근 구매 로그를 조회합니다...")
                    response = supabase.rpc('get_purchase_logs_kst').execute()
                    if not response.data:
                        print("  -> 구매 기록이 없습니다.")
                    else:
                        print("  -> 최근 구매 기록 (최대 20개):")
                        for log in response.data:
                            print(f"    - 일시: {log['created_at']}, 사용자: {log['employee_id']}, 품목ID: {log['item_id']}, 제품: {log['product_name']}, 수량: {log['quantity']}개")
                
                elif action == "delete_item":
                    product_name = payload.get("name")
                    if not product_name:
                        print("  -> 오류: 삭제할 제품명이 명확하지 않습니다.")
                        continue
                    
                    print(f"  -> '{product_name}'을(를) 재고에서 삭제합니다...")
                    data, count = supabase.table("inventory").delete().eq("product_name", product_name).execute()
                    
                    if data[1]:
                         print(f"  -> 완료! '{product_name}'이(가) 재고에서 삭제되었습니다.")
                    else:
                         print(f"  -> 오류: '{product_name}'을(를) 찾을 수 없거나 삭제하지 못했습니다.")

                elif action == "add_employee":
                    # payload에서 임직원 정보 추출
                    employee_id_to_add = payload.get("employee_id")
                    name = payload.get("name")
                    password = payload.get("password")
                    role = payload.get("role", "") # 역할 미지정시 빈 문자열로 기본값 설정

                    # 필수 정보 확인
                    if not all([employee_id_to_add, name, password]):
                        print("  -> 오류: 사번, 이름, 비밀번호는 필수입니다.")
                        continue
                    
                    # 인증 계정 생성을 위한 이메일 주소 생성
                    email = f"{employee_id_to_add}@company.test"
                    print(f"  -> 인증 계정 생성 중: {email}...")
                    
                    try:
                        # Supabase Auth에 사용자 등록
                        auth_response = supabase.auth.sign_up({"email": email, "password": password})
                        
                        if auth_response.user:
                            auth_user_id = auth_response.user.id
                            print(f"  -> 인증 계정 생성 완료. 임직원 정보 추가 중...")
                            
                            # employees 테이블에 임직원 정보 저장
                            data, count = supabase.table("employees").insert({
                                "employee_id": employee_id_to_add,
                                "name": name,
                                "role": role,
                                "auth_user_id": auth_user_id
                            }).execute()

                            if data[1]:
                                print(f"  -> 완료! 임직원 '{name}'이(가) 추가되었습니다.")
                            else:
                                # 테이블 저장 실패 시 생성된 인증 계정 삭제 필요성에 대한 안내
                                print("  -> 오류: 임직원 정보 추가에 실패했습니다. 생성된 인증 계정을 수동으로 삭제해야 할 수 있습니다.")
                        else:
                            print(f"  -> 오류: 인증 계정 생성에 실패했습니다. {auth_response}")

                    except Exception as e:
                        print(f"  -> 오류: 계정 생성 중 오류 발생: {e}")

                elif action == "delete_employee":
                    # payload에서 삭제할 임직원 정보 추출
                    employee_id_to_delete = payload.get("employee_id")
                    name = payload.get("name")
                    
                    if not employee_id_to_delete and not name:
                        print("  -> 오류: 사번 또는 이름은 필수입니다.")
                        continue

                    # employees 테이블에서 auth_user_id 조회
                    print("  -> 삭제할 임직원의 인증 정보를 조회합니다...")
                    query = supabase.table("employees").select("auth_user_id")
                    if employee_id_to_delete:
                        query = query.eq("employee_id", employee_id_to_delete)
                    else:
                        query = query.eq("name", name)
                    
                    data, count = query.execute()

                    if not data[1]:
                        print("  -> 오류: 해당 임직원을 찾을 수 없습니다.")
                        continue

                    auth_user_id_to_delete = data[1][0].get('auth_user_id')

                    # auth_user_id가 없는 경우, 테이블에서만 정보 삭제
                    if not auth_user_id_to_delete:
                        print("  -> 오류: 해당 임직원의 인증 계정 정보를 찾을 수 없습니다. 테이블 정보만 삭제합니다.")
                        if employee_id_to_delete:
                            supabase.table("employees").delete().eq("employee_id", employee_id_to_delete).execute()
                        else:
                            supabase.table("employees").delete().eq("name", name).execute()
                        print("  -> 완료! employees 테이블에서만 임직원이 삭제되었습니다.")
                        continue

                    try:
                        # Supabase Auth에서 사용자 삭제
                        print(f"  -> 인증 계정 삭제 중: {auth_user_id_to_delete}...")
                        admin_supabase: Client = create_client(url, service_role_key)
                        admin_supabase.auth.admin.delete_user(auth_user_id_to_delete)
                        print("  -> 인증 계정 삭제 완료. 임직원 정보 삭제 중...")
                        
                        # employees 테이블에서 임직원 정보 삭제
                        if employee_id_to_delete:
                            supabase.table("employees").delete().eq("employee_id", employee_id_to_delete).execute()
                        else:
                            supabase.table("employees").delete().eq("name", name).execute()
                        
                        print(f"  -> 완료! 임직원이 삭제되었습니다.")

                    except Exception as e:
                        print(f"  -> 오류: 임직원 삭제 중 오류 발생: {e}")

                else:
                    print(f"  -> 오류: 알 수 없는 action '{action}' 입니다.")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"처리 중 오류가 발생했습니다: {e}")
    
    print("CLI를 종료합니다.")
