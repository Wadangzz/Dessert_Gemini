class HTMLTemplates:
    @staticmethod
    def get_table_header_style():
        """테이블 헤더의 CSS 스타일을 반환"""
        return (
            "style='background-color: white; font-weight: bold; color: #333; "
            "text-align: left; padding: 10px; border-bottom: 2px solid #ccc;'"
        )

    @staticmethod
    def get_table_cell_style():
        """테이블 셀의 CSS 스타일을 반환"""
        return "style='padding: 10px; border-bottom: 1px solid #eee;'"

    @staticmethod
    def get_table_attributes():
        """테이블의 HTML 속성을 반환"""
        return (
            "border='0' style='width: 95%; border-collapse: collapse; "
            "margin-left: 10px; font-family: sans-serif;'"
        )

    @staticmethod
    def generate_purchase_logs_html(logs):
        """구매 기록을 위한 HTML 테이블을 생성"""
        if not logs:
            return HTMLTemplates.generate_system_message("구매 기록이 없습니다.")

        th_attributes = HTMLTemplates.get_table_header_style()
        td_attributes = HTMLTemplates.get_table_cell_style()
        table_attributes = HTMLTemplates.get_table_attributes()

        log_html = (
            "<div align='left'><p style='color: #555; margin-left: 10px;'>"
            "-> <b>최근 구매 기록 (최대 20개):</b></p>"
        )
        log_html += f"<table {table_attributes}>"
        log_html += (
            f"<thead><tr>"
            f"<th {th_attributes}>일시</th>"
            f"<th {th_attributes}>사용자</th>"
            f"<th {th_attributes}>제품</th>"
            f"<th {th_attributes}>수량</th>"
            f"</tr></thead><tbody>"
        )
        
        for log in logs:
            log_html += (
                f"<tr>"
                f"<td {td_attributes}>{log.get('created_at_kst', '')}</td>"
                f"<td {td_attributes}>{log.get('employee_id', '')}</td>"
                f"<td {td_attributes}>{log.get('product_name', '')}</td>"
                f"<td {td_attributes}>{log.get('quantity', '')}</td>"
                f"</tr>"
            )
        
        log_html += "</tbody></table></div>"
        return log_html

    @staticmethod
    def generate_employees_html(employees):
        """직원 목록을 위한 HTML 테이블을 생성"""
        if not employees:
            return HTMLTemplates.generate_system_message("등록된 직원이 없습니다.")

        th_attributes = HTMLTemplates.get_table_header_style()
        td_attributes = HTMLTemplates.get_table_cell_style()
        table_attributes = HTMLTemplates.get_table_attributes()

        log_html = (
            "<div align='left'><p style='color: #555; margin-left: 10px;'>"
            "-> <b>직원 목록:</b></p>"
        )
        log_html += f"<table {table_attributes}>"
        log_html += (
            f"<thead><tr>"
            f"<th {th_attributes}>사번</th>"
            f"<th {th_attributes}>이름</th>"
            f"<th {th_attributes}>역할</th>"
            f"</tr></thead><tbody>"
        )
        
        for employee in employees:
            log_html += (
                f"<tr>"
                f"<td {td_attributes}>{employee.get('employee_id', '')}</td>"
                f"<td {td_attributes}>{employee.get('name', '')}</td>"
                f"<td {td_attributes}>{employee.get('role', '')}</td>"
                f"</tr>"
            )
            
        log_html += "</tbody></table></div>"
        return log_html

    @staticmethod
    def generate_user_message(user_name, command):
        """사용자 메시지 버블을 위한 HTML을 생성"""
        return (
            f"<table width='100%' style='table-layout: fixed;'><tr>"
            f"<td width='25%'></td>"
            f"<td width='75%' align='right'>"
            f"<span style='display: inline-block; text-align: left; margin: 5px; padding: 10px; "
            f"background-color: #FFFFFF; color: black; border-radius: 12px; "
            f"border-bottom-right-radius: 0px;'><b>{user_name}:</b><br>{command}</span>"
            f"</td>"
            f"</tr></table>"
        )

    @staticmethod
    def generate_gemini_message(message: str = "알겠습니다. 요청을 처리하겠습니다."):
        """Gemini의 응답 메시지 버블을 위한 HTML을 생성합니다."""
        return (
            f"<table width='100%' style='table-layout: fixed;'><tr>"
            f"<td width='75%'>"
            f"<span style='display: inline-block; text-align: left; margin: 5px; padding: 10px; "
            f"background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 12px; "
            f"border-bottom-left-radius: 0px;'><b>Gemini:</b><br>{message}</span>"
            f"</td>"
            f"<td width='25%'></td>"
            f"</tr></table>"
        )

    @staticmethod
    def generate_welcome_message():
        """초기 환영 메시지를 생성"""
        return "<p><b>환영합니다!</b> 디저트 재고 관리 시스템에 오신 것을 환영합니다!</p>"

    @staticmethod
    def generate_login_info_message(user_email, is_admin):
        """로그인 정보 메시지를 생성"""
        role = '관리자' if is_admin else '일반'
        return f"<p><b>로그인 정보:</b> {user_email} ({role})</p>"

    @staticmethod
    def generate_system_message(message, is_error=False):
        """표준 스타일의 시스템 메시지를 생성"""
        color = 'red' if is_error else '#555'
        return (
            f"<table width='100%'><tr><td align='left'>"
            f"<p style='color: {color}; margin-left: 10px;'>-> {message}</p>"
            f"</td></tr></table>"
        )