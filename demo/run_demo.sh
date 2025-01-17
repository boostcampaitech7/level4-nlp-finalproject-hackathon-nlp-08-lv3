#!/bin/bash

# tmux 세션 생성
tmux new-session -d -s mysession

# 첫 번째 창에서 backend 실행
tmux send-keys -t mysession 'cd backend' C-m
tmux send-keys -t mysession 'python main.py' C-m

# 두 번째 창 생성 및 frontend 실행
tmux new-window -t mysession
tmux send-keys -t mysession:1 'cd frontend' C-m
tmux send-keys -t mysession:1 'streamlit run app.py' C-m

# tmux 세션 연결
tmux attach -t mysession