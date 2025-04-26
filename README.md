# 🎹 MIDI 파일 플레이어 v1.0

이 프로젝트는 **Tkinter 기반 GUI 애플리케이션**으로, MIDI 파일 재생과 함께 **가상 오류 발생 시스템**, **페달 효과 제어** 기능을 제공합니다.  
음악 학습과 코딩 교육용으로 개발되었으며, 실시간 속도 조정, 오류 시뮬레이션 등을 통해 재미있게 활용할 수 있습니다.

---

## ✨ 주요 기능
- **MIDI 파일 재생**
  - 재생 속도 조절 (0.2x ~ 3.0x)
  - 벨로시티 조정 (0 ~ 127)
  - 실시간 탐색(Seek) 지원
- **가상 오류 발생기**
  - 음정 오차 조정 (±12 반음)
  - 오타 발생 확률 조정 (0% ~ 100%)
  - 타이밍 오차 적용 (0% ~ 100%)
- **테마 커스터마이징**
  - 10개 이상의 `ttk` 테마 지원 (clam, alt, darkly 등)
- **페달 모드 제어**
  - Sustain 페달 효과 설정 가능
- **MIDI 포트 관리**
  - 실시간 MIDI 출력 포트 감지 및 선택

---

## 🛠️ 설치 및 실행 방법

### 1. 의존성 설치
다음 명령어를 통해 필요한 라이브러리를 설치하세요:
```bash
pip install mido python-rtmidi ttkthemes
```

### 2. 실행 방법
`app.py` 파일을 실행하면 프로그램이 시작됩니다:
```bash
python app.py
```

---

## 🚨 주의사항
- **Pretendard 폰트 설치 권장**  
  프로젝트에 포함된 `Pretendard.otf` 파일을 설치하면 UI가 최적화되어 보입니다.
- **가상 MIDI 포트 필요**  
  실제 MIDI 장비가 없다면, `LoopMIDI`와 같은 가상 MIDI 케이블 프로그램을 미리 설치하세요.
- **python-rtmidi 설치 오류 발생 시**  
  Visual C++ Build Tools가 필요할 수 있습니다. 아래 명령어로 재설치를 시도하세요:
  ```bash
  pip uninstall python-rtmidi
  pip install python-rtmidi
  ```

---

## 📂 프로젝트 구조
```
midi-player/
├── app.py                # 메인 애플리케이션 파일
├── midi/                 # 사용자 저장 MIDI 파일 디렉토리
├── Pretendard.otf        # UI 최적화용 폰트
└── README.md             # 프로젝트 설명 문서
```

---

## 📜 라이선스
MIT License © 2025 Riha Studio  
[![License](https://img.shields.io/badge/License-MIT-6183ff.svg)](LICENSE)

---

## 📮 연락처
[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=flat&logo=YouTube&logoColor=white)](https://www.youtube.com/@riha_cats)
[![Discord](https://img.shields.io/badge/Discord-5865F2?style=flat&logo=Discord&logoColor=white)](https://discord.com/users/1007560755123589210)
[![Gmail](https://img.shields.io/badge/Gmail-D14836?style=flat&logo=Gmail&logoColor=white)](mailto:ytlullu2021@gmail.com)

버그 리포트 및 개선 제안은 언제든 환영합니다!
