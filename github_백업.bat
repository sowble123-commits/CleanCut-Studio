@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo === CleanCut Studio Pro 깃허브 자동 백업 ===

:: Git 설치 여부 확인
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [오류] 컴퓨터에 Git 프로그램이 설치되어 있지 않거나 인식되지 않습니다.
    echo https://git-scm.com/ 에서 Git을 먼저 설치해주세요.
    pause
    exit /b
)

:: 타임스탬프 생성 (YYYYMMDDHHMM 형식)
for /f "usebackq tokens=*" %%a in (`powershell -Command "Get-Date -Format yyyyMMddHHmm"`) do set TIMESTAMP=%%a

:: Git 저장소 초기화 (처음 1회만 실행됨)
if not exist ".git" (
    echo [안내] 깃허브 관리를 시작합니다...
    git init
)

:: 원격 저장소 연결 확인 및 등록
git remote -v | find "origin" >nul
if %errorlevel% neq 0 (
    echo.
    echo [초기 설정] 연결된 GitHub 저장소가 없습니다.
    set /p REPO_URL="https://github.com/sowble123-commits/CleanCut-Studio.git "
    git remote add origin !REPO_URL!
    git branch -M main
)

:: 변경사항 추가 및 현재 시간으로 커밋
echo.
echo 변경된 코드를 모으는 중...
git add .
git commit -m "%TIMESTAMP%"

:: 깃허브로 전송
echo.
echo 깃허브로 안전하게 전송합니다...
git push -u origin main

echo.
echo === 백업이 완료되었습니다! ===
pause