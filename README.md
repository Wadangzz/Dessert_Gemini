# JLT 디저트 챗봇

간단한 디저트 재고 관리 챗봇입니다.

## 요구 사항

- Python 3.12+
- `uv` (패키지 설치용)

## 설치

1. **`uv` 설치:**

   공식 안내에 따라 `uv`를 설치합니다: https://github.com/astral-sh/uv  
   또는  
   ```bash
   pip install uv
   ```

2. **가상 환경 생성 및 의존성 설치:**

   ```bash
   uv venv
   uv pip sync pyproject.toml
   ```

## 사용법

1. **환경 변수 설정:**

   프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

   ```
   URL="YOUR_SUPABASE_URL"
   API="YOUR_SUPABASE_API_KEY"
   GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
   SERVICE_ROLE_API="YOUR_SUPABASE_SERVICE_ROLE_KEY"
   ```

2. **애플리케이션 실행:**

   ```bash
   python main.py
   ```