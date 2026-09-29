import os
import datetime

# 스캔에서 제외할 불필요한 폴더 및 파일들
IGNORE_DIRS = {'.git', '__pycache__', 'venv', 'env', '.vscode', '.idea', 'CleanCut_결과물'}
IGNORE_FILES = {'AI_HANDOFF.txt', 'make_handoff.py'}
# 코드를 읽어올 파일 확장자
TARGET_EXTENSIONS = {'.py', '.json', '.txt', '.md'}

def build_handoff_document():
    output_filename = "AI_HANDOFF.txt"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write("=== CleanCut Studio Pro - AI 인수인계 마스터 문서 ===\n")
        f.write(f"생성 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 1. 폴더 및 파일 구조(Tree) 작성
        f.write("=== [1] 현재 프로젝트 파일 구조 ===\n")
        for root, dirs, files in os.walk('.'):
            # 제외할 폴더 걸러내기
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            level = root.replace('.', '').count(os.sep)
            indent = ' ' * 4 * level
            if root != '.':
                f.write(f"{indent}📂 {os.path.basename(root)}/\n")
            
            sub_indent = ' ' * 4 * (level + 1)
            for file in files:
                if file not in IGNORE_FILES and not file.endswith('.pyc'):
                    f.write(f"{sub_indent}📄 {file}\n")
        
        # 2. 핵심 소스코드 내용 복사
        f.write("\n\n=== [2] 전체 소스 코드 상세 ===\n")
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if file in IGNORE_FILES:
                    continue
                
                ext = os.path.splitext(file)[1].lower()
                if ext in TARGET_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    # 윈도우 경로(\)를 깔끔하게(/) 정리
                    display_path = file_path.replace('.\\', '').replace('\\', '/')
                    
                    f.write(f"\n\n{'='*60}\n")
                    f.write(f"📁 FILE: {display_path}\n")
                    f.write(f"{'='*60}\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as code_file:
                            f.write(code_file.read())
                    except Exception as e:
                        f.write(f"(파일을 읽을 수 없습니다: {e})\n")

    print(f"✅ 완료! [{output_filename}] 파일이 성공적으로 생성/업데이트 되었습니다.")
    print("이제 이 텍스트 파일의 내용을 복사해서 새 AI 채팅방에 붙여넣기만 하면 인수인계가 끝납니다!")

if __name__ == "__main__":
    build_handoff_document()