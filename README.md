<p align="center">
  <img src="assets/readme/icon.svg" width="88" alt="KRect 아이콘">
</p>

<h1 align="center">KRect</h1>

<p align="center">
  <b>한국어</b> · <a href="README.en.md">English</a>
</p>

<p align="center">
  <b>모든 창을, 원하는 자리에.</b><br>
  Rectangle의 익숙한 창 배치를 Ubuntu·Kubuntu KDE에서.
</p>

<p align="center">
  <a href="https://github.com/ziwon/KRect/releases/tag/v0.2.0">v0.2.0 다운로드</a> ·
  KDE Plasma 5.27 / 6 ·
  <a href="LICENSE">MIT License</a>
</p>

<p align="center">
  <a href="assets/readme/layouts.png"><img src="assets/readme/layouts.png" width="600" alt="KRect의 창 배치 화면: 가로·세로 듀얼 모니터 미리보기와 18개 배치 동작"></a><br>
  <sub>Plasma 5.27 / X11에서 확인한 실제 앱 화면. 시스템 언어에 따라 한국어·영어로 표시합니다.</sub>
</p>

KRect는 단축키, 앱 버튼, 트레이 메뉴로 작업 중인 창을 배치하는 네이티브 Qt 앱입니다.
기존 KWin 위에서 동작하며 KDE의 작업 영역과 전역 단축키를 사용합니다.

## KDE에서 편하게 창 정리

- **18가지 동작** — 반쪽·4분할·⅓·⅔ 배치, 중앙 정렬, 최대화, 원래 배치 복원과 모니터 이동.
- **가로·세로 모니터 함께** — 실제 모니터 위치를 미리 보고, 세로 화면의 3분할은 위아래로 배치합니다.
- **KDE와 자연스럽게** — 패널을 피해서 배치하고, 앱에서 전역 단축키를 편집하며 충돌을 확인합니다.
- **내 작업 방식에 맞게** — 창 간격, 제외할 앱, 로그인 시 실행을 설정합니다. 창을 닫아도 트레이에서 사용할 수 있습니다.

## 설치

Ubuntu·Kubuntu의 **KDE Plasma 세션**이 필요합니다. GNOME에서는 동작하지 않습니다.
`plasmashell --version`으로 버전을 확인한 뒤 설치 파일을 선택하세요.

| 환경 | 다운로드 |
| --- | --- |
| Ubuntu 24.04 · Plasma 5.27 · Qt 5 | [24.04용 .deb](https://github.com/ziwon/KRect/releases/download/v0.2.0/krect_0.2.0-1ubuntu24.04_all.deb) |
| Ubuntu 26.04 · Plasma 6 · Qt 6 | [26.04용 .deb](https://github.com/ziwon/KRect/releases/download/v0.2.0/krect_0.2.0-1ubuntu26.04_all.deb) |

다운로드한 폴더에서 실행하세요. 26.04에서는 해당 파일명으로 바꿉니다.

```bash
sudo apt install ./krect_0.2.0-1ubuntu24.04_all.deb
```

앱, 실행기, 트레이와 KWin 엔진을 함께 설치합니다.
기존에 소스로 설치했다면 앱을 종료하고 소스 폴더에서 `bash uninstall.sh`로 사용자 설치를 제거한 뒤 진행하세요.
0.1.0 시스템 패키지는 위 명령으로 업그레이드할 수 있습니다.

[소스 설치·업데이트·제거](docs/GUIDE.md#소스에서-설치) · [전체 릴리즈 파일과 체크섬](https://github.com/ziwon/KRect/releases/tag/v0.2.0)

## 시작하기

1. 앱 실행기나 KRunner에서 **KRect**를 찾아 열고 **KRect 켜기**를 누르세요.
2. 배치할 창을 한 번 선택한 뒤, KRect의 **창 배치** 버튼이나 트레이 메뉴를 사용하세요.
3. **단축키**에서 원하는 키를 저장하고, **환경설정**에서 간격과 제외 앱을 조정하세요.

KRect는 마지막으로 선택한 작업 창을 기억합니다. KRect 자신의 창은 배치 대상에서 제외합니다.
앱을 종료해도 KWin 단축키는 계속 작동합니다. 배치 기능까지 멈추려면 KRect를 끄세요.

## 자주 쓰는 단축키

| 동작 | 기본 단축키 |
| --- | --- |
| 왼쪽 / 오른쪽 반쪽 | `Ctrl+Alt+←` / `Ctrl+Alt+→` |
| 위 / 아래 반쪽 | `Ctrl+Alt+↑` / `Ctrl+Alt+↓` |
| 중앙 정렬 | `Ctrl+Alt+C` |
| 최대화 | `Ctrl+Alt+Enter` |
| 원래 배치 복원 | `Ctrl+Alt+Backspace` |
| 이전 / 다음 모니터 | `Ctrl+Alt+Shift+←` / `Ctrl+Alt+Shift+→` |

같은 반쪽 단축키를 1.2초 안에 반복하면 **½ → ⅔ → ⅓**로 순환합니다.
기존 KDE 단축키는 강제로 덮어쓰지 않습니다. [전체 단축키와 설정](docs/GUIDE.md#기본-단축키)을 확인하세요.

## 지원 범위

0.2.0은 자동 테스트 63개와 **Plasma 5.27 / X11 실제 앱 동작 14개**를 통과했습니다.
Ubuntu 24.04·26.04 컨테이너에서 패키지 설치·제거와 Qt 5/6 화면 생성도 확인했습니다.
**Plasma 6 / Wayland 실기, 혼합 배율, 물리 단축키 입력과 로그인 자동 시작은 추가 검증이 필요합니다.**

마우스 드래그 스냅, 모든 창의 자동 타일링, 사용자 지정 배치 프리셋은 아직 제공하지 않습니다.
앱의 최소 크기나 KWin 창 규칙에 따라 실제 배치 크기가 달라질 수 있습니다.
[검증 기록](docs/VALIDATION.md)과 [세부 동작·제약](docs/GUIDE.md#실제-환경에서-확인할-부분)을 참고하세요.

## 더 알아보기

- [사용 가이드](docs/GUIDE.md) — 소스 설치, 전체 단축키, 설정, 제거와 개발 방법
- [빌드·릴리즈](docs/RELEASING.md) · [Plasma 6 업그레이드 검토](docs/UPGRADE.md)
- [버그 신고·제안](https://github.com/ziwon/KRect/issues)

[MIT License](LICENSE). Rectangle에서 영감을 받은 독립 구현이며, Rectangle이나 KDE의 공식 제품은 아닙니다.
