@echo off
chcp 65001 >nul

echo === CleanCut Studio Pro 깃허브 자동 백업 ===

:: 1. 타임스탬프(시간) 생성
for /f "usebackq tokens=*" %%a in (`powershell -Command "Get-Date -Format yyyyMMddHHmm"`) do set TIMESTAMP=%%a

:: 2. 깃허브 저장소 초기화
if not exist ".git" (
    git init
    git branch -M main
)

:: 3. 깃허브 주소 강제 연결 (중복 에러 방지)
git remote remove origin 2>nul
git remote add origin https://github.com/sowble123-commits/CleanCut-Studio.git

:: 4. 백업 진행
echo.
echo [1/3] 변경된 파일 모으는 중...
git add .

echo [2/3] 변경사항 저장 중 (%TIMESTAMP%)...
git commit -m "%TIMESTAMP%"

echo [3/3] 깃허브로 전송 중...
git push -u origin main

echo.
echo === 모든 백업 작업이 완료되었습니다! ===
pause