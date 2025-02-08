# Level 4 - Upstage 해커톤: 인사를 부탁해
<img width="374" alt="Image" src="https://github.com/user-attachments/assets/1c406613-6cd8-4f0a-99cf-f4c3406fadff"/>

## 📝 Abstract
- [Wrap-Up Report](추가예정)
- 부스트캠프 AI Tech의 최종 프로젝트인 Upstage 해커톤으로, **AGI for Work - Upstage API를 이용한 AI 프로덕트 개발**을 주제로 하였다.

<br>

## 👔 Team Introduction 

> **Team NLP크민**

### 👨🏼‍💻 Members
권지수 | 김성은 | 김태원 | 이다현 | 이한서 | 정주현
:-: | :-: | :-: | :-: | :-: | :-:
<img src='https://github.com/user-attachments/assets/ab4b7189-ec53-41be-8569-f40619b596ce' height=125 width=100></img> | <img src='https://github.com/user-attachments/assets/49dc0e59-93ee-4e08-9126-4a3deca9d530' height=125 width=100></img> | <img src='https://github.com/user-attachments/assets/a15b0f0b-cd89-412b-9b3d-f59eb9787613' height=125 width=100></img> | <img src='https://github.com/user-attachments/assets/4064f03a-a1dc-4dd1-ac84-d9ac8636418a' height=125 width=100></img> | <img src='https://github.com/user-attachments/assets/11b2ed88-bf94-4741-9df5-5eb2b9641a9b' height=125 width=100></img> | <img src='https://github.com/user-attachments/assets/3e2d2a7e-1c64-4cb7-97f6-a2865de0c594' height=125 width=100></img>
<a href="mailto:wltn80609@ajou.ac.kr" target="_blank"><img src="https://img.shields.io/badge/Gmail-EA4335?style&logo=Gmail&logoColor=white"/></a> | <a href="mailto:sunny020111@ajou.ac.kr" target="_blank"><img src="https://img.shields.io/badge/Gmail-EA4335?style&logo=Gmail&logoColor=white"/></a> | <a href="mailto:chris40461@gmail.com" target="_blank"><img src="https://img.shields.io/badge/Gmail-EA4335?style&logo=Gmail&logoColor=white"/></a> | <a href="mailto:dhdh09290929@gmail.com" target="_blank"><img src="https://img.shields.io/badge/Gmail-EA4335?style&logo=Gmail&logoColor=white"/></a> | <a href="mailto:beaver.zip@gmail.com" target="_blank"><img src="https://img.shields.io/badge/Gmail-EA4335?style&logo=Gmail&logoColor=white"/></a> | <a href="mailto:peter520416@gmail.com" target="_blank"><img src="https://img.shields.io/badge/Gmail-EA4335?style&logo=Gmail&logoColor=white"/></a>|
<a href="https://github.com/Kwon-Jisu" target="_blank"><img src="https://img.shields.io/badge/GitHub-Kwon--Jisu-181717?style&logo=GitHub&logoColor=white" /></a> | <a href="https://github.com/ssungni" target="_blank"><img src="https://img.shields.io/badge/GitHub-ssungni-181717?style&logo=GitHub&logoColor=white" /></a> | <a href="https://github.com/chris40461" target="_blank"><img src="https://img.shields.io/badge/GitHub-chris40461-181717?style&logo=GitHub&logoColor=white" /></a> | <a href="https://github.com/dhl0929" target="_blank"><img src="https://img.shields.io/badge/GitHub-dhl0929-181717?style&logo=GitHub&logoColor=white" /></a> | <a href="https://github.com/beaver-zip" target="_blank"><img src="https://img.shields.io/badge/GitHub-beaver--zip-181717?style&logo=GitHub&logoColor=white" /></a> | <a href="https://github.com/peter520416" target="_blank"><img src="https://img.shields.io/badge/GitHub-peter520416-181717?style&logo=GitHub&logoColor=white" /></a>

### 🧑🏻‍💻 Role

| 이름 | 역할 |
| :---: | --- |
| **`권지수`** | ** ** |
| **`김성은`** | ** ** |
| **`김태원`** | ** ** |
| **`이다현`** | ** ** |
| **`이한서`** | ** ** |
| **`정주현`** | ** ** |

<br>

## 🖥️ Project Introduction 

| **주제** | AGI for Work - Upstage API를 이용한 AI 프로덕트 개발 |
| :---: | --- |
| **구현 내용** | 부스트캠프 내에서 수행하는 동료 피드백에서 착안해, 360도 다면평가를 통한 인사 고과 평가 및 보고서 자동 생성 솔루션을 구현하였다. |
| **개발 환경** | **• `GPU`:** NVIDIA Tesla V100 32GB 서버 4개 <br> **• `Tool`:** VS Code, Jupyter Notebook |
| **협업 환경** | **• `Zoom`:** 실시간 비대면 회의 <br> **• `Github`:** 코드, 데이터 공유 및 버전 관리 <br> **• `Notion`:** 회의록 작성 및 경과 공유 |

<br>

## 📁 Project Structure
```
📦demo
 ┣ 📂backend
 ┃ ┣ 📂book_chunk
 ┃ ┃ ┣ 📜save_book_info.py
 ┃ ┃ ┣ 📜books_chunk_0.pkl
 ┃ ┃ ┣ 📜books_chunk_1.pkl
 ┃ ┃ ┗ ...
 ┃ ┣ 📂build_pdf
 ┃ ┃ ┣ 📜book_recommendation.py
 ┃ ┃ ┣ 📜feedback_summary.py
 ┃ ┃ ┣ 📜load_book_chunk.py
 ┃ ┃ ┗ 📜make_pdf.py
 ┃ ┣ 📂db
 ┃ ┃ ┣ 📂models
 ┃ ┃ ┃ ┣ 📜file.py
 ┃ ┃ ┃ ┣ 📜pdf.py
 ┃ ┃ ┃ ┣ 📜qa.py
 ┃ ┃ ┃ ┗ ...
 ┃ ┃ ┣ 📂persona_db
 ┃ ┃ ┃ ┣ 📜feedback.db
 ┃ ┃ ┃ ┣ 📜result.db
 ┃ ┃ ┃ ┗ 📜user.db
 ┃ ┃ ┣ 📜__init__.py
 ┃ ┃ ┗ 📜file_uploads.db
 ┃ ┣ 📂mail_service
 ┃ ┃ ┣ 📜__init__.py
 ┃ ┃ ┣ 📜reminder.py
 ┃ ┃ ┗ 📜send_email.py
 ┃ ┣ 📂routes
 ┃ ┃ ┣ 📜__init__.py
 ┃ ┃ ┣ 📜admin_questions.py
 ┃ ┃ ┣ 📜auth.py
 ┃ ┃ ┗ ...
 ┃ ┗ 📜main.py
 ┣ 📂frontend
 ┃ ┣ 📂.streamlit
 ┃ ┃ ┗ 📜config.toml
 ┃ ┣ 📂modules
 ┃ ┃ ┣ 📜account.py
 ┃ ┃ ┣ 📜admin_feedback.py
 ┃ ┃ ┣ 📜admin_group_manage.py
 ┃ ┃ ┗ ...
 ┃ ┗ 📜app.py
 ┣ 📂image_store
 ┃ ┣ 📜logo.png
 ┃ ┗ 📜profile.png
 ┣ 📜.env
 ┣ 📜install_requirements.sh
 ┣ 📜requirements.txt
 ┗ 📜run_demo.sh
 ```

<br>

## 🗓 Project Time Line
> 2025.01.03.(금)-02.10.(월)
<img width="902" alt="Image" src="https://github.com/user-attachments/assets/8017c4fe-9f23-4675-9983-4906981b5fef" />

<br>

## 💻 Getting Started

### ⌨️ How To Install Requirements
```bash
chmod +x install_requirements.sh
./install_requirements.sh

# 페르소나 데이터를 사용해보고 싶으시다면:
mv demo/backend/db/persona_db/* demo/backend/db/
cp 
```

### ⌨️ How To Run
```bash
chmod +x run_demo.sh
./run_demo.sh
```