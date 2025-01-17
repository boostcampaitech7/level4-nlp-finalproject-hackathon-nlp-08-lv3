#!/bin/bash

# 통합 디렉토리에서 backend와 frontend의 requirements.txt 설치

# backend requirements 설치
if [ -f "./backend/requirements.txt" ]; then
    echo "Installing backend requirements..."
    pip install -r ./backend/requirements.txt
else
    echo "backend/requirements.txt 파일을 찾을 수 없습니다."
fi

# frontend requirements 설치
if [ -f "./frontend/requirements.txt" ]; then
    echo "Installing frontend requirements..."
    pip install -r ./frontend/requirements.txt
else
    echo "frontend/requirements.txt 파일을 찾을 수 없습니다."
fi
