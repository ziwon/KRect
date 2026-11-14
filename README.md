# KRect 0.1.0

KDE Plasma 6에서 Rectangle처럼 단축키로 창을 배치하는 KWin 확장 프로토타입.
Ubuntu에 KDE를 설치한 환경 또는 Kubuntu의 **Plasma 6 세션**을 대상으로 한다.
독립 창 관리자를 새로 실행하지 않고, 기존 KWin이 관리하는 활성 창을 조작한다.

**상태:** 배치 계산·창 상태 처리의 Node 모의 테스트는 통과했다. 실제 KWin/Wayland/X11 세션,
Qt 설정 화면, KPackage 설치는 이 제작 환경에서 실행하지 못했다. 실사용 검증 전 버전이다.
GNOME과 Plasma 5는 대상이 아니다. 배포판 이름보다 `plasmashell --version`으로 확인한 Plasma 버전이 중요하다.

## 포함 기능

- 좌우·상하 반쪽, 네 모서리 4분할, ⅓·⅔ 배치
- 같은 반쪽 단축키를 1.2초 안에 반복하면 ½ → ⅔ → ⅓ → ½ 순환
- 중앙 정렬, KDE 기본 최대화, 처음 배치 직전의 위치·크기 복원
- 이전/다음 모니터로 이동; 배치 비율 유지, 세로 모니터의 3분할 자동 변환
- 패널을 제외한 작업 영역 사용, 논리 좌표 기준 간격 설정
- 앱별 제외, KDE 설정 화면과 전역 단축키 설정 연동
- 창 제목 표시줄 우클릭 또는 `Alt+F3` 창 메뉴의 **KRect** 하위 메뉴

이번 버전에는 별도 트레이 앱, 마우스 드래그 스냅 미리보기, 창 전체의 자동 타일링,
앱별 영구 레이아웃 저장은 없다. KWin의 기존 드래그 동작 설정은 변경하지 않는다.
Rectangle의 코드를 이식하지 않은 독립 구현이며 Rectangle/KDE 공식 제품이 아니다.

## 설치

GitHub에서 가져오는 경우 다음과 같이 설치한다. `package/`에 설치용 코드가 포함되어 있어
별도 빌드는 필요 없다.

```bash
git clone https://github.com/ziwon/KRect.git
cd KRect
plasmashell --version
bash install.sh
```

ZIP 파일을 내려받았다면 다음 순서를 따른다.

1. ZIP 압축을 풀고 `krect` 디렉터리에서 실행한다. Node/Python 빌드 없이 설치할 수 있다.

   ```bash
   plasmashell --version
   bash install.sh
   ```

2. **시스템 설정 → 창 관리 → KWin 스크립트**를 연다.
3. **KRect**를 체크하고 **적용**한다. 설정 화면이 이미 열려 있었다면 다시 열어 목록을 새로고침한다.
4. **키보드 → 단축키**에서 `KRect`를 검색한다. 버전에 따라 전역 단축키의 KWin 항목 안에 표시될 수 있다.

설치에는 `kpackagetool6`가 필요하다. `sudo`로 설치 스크립트를 실행하지 않는다.
사용자 범위의 KPackage만 설치하며 설치 스크립트는 데스크톱 설정을 바꾸지 않는다.
설치 위치는 보통 `~/.local/share/kwin/scripts/krect`이다.

GUI 설치도 가능하다. KWin 스크립트 화면의 **파일에서 설치**로
`dist/krect-0.1.0.kwinscript`를 선택한 뒤 활성화한다.
Git clone으로 가져왔다면 먼저 `python3 tools/build.py`로 이 파일을 생성한다.
`dist/`의 ZIP과 `.kwinscript` 빌드 결과는 Git에서 추적하지 않는다.

기존 버전을 업데이트할 때는 먼저 KRect를 해제하고 적용한 다음 `bash install.sh`를 실행하고 다시 활성화한다.

## 기본 단축키

| 기능 | 기본 단축키 |
| --- | --- |
| 왼쪽 / 오른쪽 반쪽 | `Ctrl+Alt+←` / `Ctrl+Alt+→` |
| 위 / 아래 반쪽 | `Ctrl+Alt+↑` / `Ctrl+Alt+↓` |
| 왼쪽 위 / 오른쪽 위 ¼ | `Ctrl+Alt+U` / `Ctrl+Alt+I` |
| 왼쪽 아래 / 오른쪽 아래 ¼ | `Ctrl+Alt+J` / `Ctrl+Alt+K` |
| 첫 / 가운데 / 마지막 ⅓ | `Ctrl+Alt+D` / `Ctrl+Alt+F` / `Ctrl+Alt+G` |
| 첫 / 마지막 ⅔ | `Ctrl+Alt+E` / `Ctrl+Alt+T` |
| 중앙 정렬 | `Ctrl+Alt+C` |
| 최대화 | `Ctrl+Alt+Enter` |
| 원래 배치 복원 | `Ctrl+Alt+Backspace` |
| 이전 / 다음 모니터 | `Ctrl+Alt+Shift+←` / `Ctrl+Alt+Shift+→` |

이미 다른 기능에 할당된 키는 충돌할 수 있다. 해당 키를 KDE 단축키 설정에서 재할당한다.
설치 스크립트가 기존 단축키를 강제로 덮어쓰지 않는다.

## 설정과 동작

KWin 스크립트 목록에서 KRect의 설정 버튼을 연다. 설정 UI는 현재 영어로 제공된다.

| 설정 | 기본값 | 의미 |
| --- | --- | --- |
| Window gap | 8 | 화면 가장자리와 창 사이의 간격. 물리 픽셀이 아닌 논리 픽셀 |
| Cycle repeated half actions | 켬 | 반쪽 단축키의 ½ → ⅔ → ⅓ 순환 |
| Repeat interval | 1200ms | 같은 창에서 같은 단축키를 반복했다고 판단하는 시간 |
| Portrait thirds | 켬 | 세로 화면에서 ⅓·⅔ 배치를 위→아래 방향으로 적용 |
| Ignored apps | 비어 있음 | 쉼표로 구분한 resource class/name 또는 desktop-file name |

설정 저장 후 KRect를 해제/적용하고 다시 활성화/적용하면 확실하게 다시 읽는다.
최대화는 KDE의 기본 최대화이며 간격을 적용하지 않는다.
모니터 순서는 논리 좌표의 x, y, 이름 순으로 정렬하고 끝에서 순환한다.

복원은 **해당 창에 처음 KRect 명령을 적용하기 직전**의 배치를 기준으로 한다.
다른 KRect 배치로 바꿔도 그 기준은 유지된다. 복원 후에는 기록을 지운다.
사용자가 창을 직접 이동·리사이즈하면 기록을 지우고, 다음 명령에서 새 기준을 잡는다.
창을 닫거나 스크립트를 다시 시작하면 기록은 사라진다.
원래 모니터가 연결 해제되었으면 현재 모니터의 작업 영역에 맞게 복원한다.

## 실제 환경에서 확인할 부분

- Wayland 앱의 resize는 비동기 요청이다. 앱의 최소 크기·고정 종횡비·KWin 창 규칙 때문에
  ⅓이나 ¼ 크기와 정확히 일치하지 않을 수 있다. 요청을 무한히 재시도하지 않는다.
- 전체 화면, 고정 크기 창, 패널, 메뉴, 최소화된 창, 이동/크기 변경 중인 창은 건드리지 않는다.
- 창 배치 시 기존 타일 연결은 해제한다. 복원은 geometry와 확인 가능한 최대화 상태를 복구하며,
  원래 사용자 정의 타일 그룹 소속까지 복구하지는 않는다.
- 초기 Plasma 6에는 현재 최대화 모드를 읽는 속성이 없다. 스크립트 시작 **전부터** 최대화된 창은
  원래 화면 크기로는 복원되더라도 최대화 플래그까지 복구되지 않을 수 있다.
  모드를 읽을 수 있는 버전 또는 실행 중 관찰한 최대화 변경은 복원한다.
- 디스플레이 배율을 geometry에 다시 곱하지 않는다. 혼합 배율, fractional scaling,
  모니터 분리/재연결, Chromium/Electron 및 XWayland 앱은 실기 검증이 필요하다.
- 다른 자동 타일링 스크립트와 함께 쓰면 서로 창 배치를 바꿀 수 있다.

짧은 검증 순서는 [docs/VALIDATION.md](docs/VALIDATION.md)에 있다.

## 제거

```bash
bash uninstall.sh
```

자동 활성화 설정을 끄고 현재 사용자의 KRect 패키지를 제거한다.
D-Bus에 접근할 수 있으면 실행 중인 KRect 스크립트만 종료한다.
접근할 수 없으면 로그아웃 후 다시 로그인하면 적용된다.
개인 설정과 수정한 단축키 항목은 남겨 재설치 시 사용할 수 있다.

## 개발

런타임에는 Node, Python, 외부 데몬이나 네트워크 연결이 필요 없다.
테스트에는 Node 18 이상, 패키징에는 Python 3.9 이상이 필요하다.

```bash
node --test tests/*.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tools/build.py
```

- `src/main.js`: geometry 계산과 KWin 연결. 의존성 없이 한 파일로 패키징
- `package/`: KPackage 메타데이터, KConfig 스키마와 Qt Designer 설정 UI
- `tests/`: geometry, 복원, 모니터 이동, 지연된 geometry 반영, 설치 명령의 모의 테스트
- `tools/build.py`: 소스를 패키지로 복사하고 `.kwinscript`와 소스 ZIP 생성

수정한 `src/main.js`를 설치에 반영하려면 **다시 빌드**한 뒤 설치한다.
`package/contents/code/main.js`는 생성 파일이므로 직접 수정하지 않는다.

추가 개발 순서로는 실제 KDE 통합 테스트, Qt/QML 트레이와 배치 선택 UI,
드래그 스냅 영역·미리보기, 사용자 지정 배치 프리셋을 권장한다.

## 구현 근거

2026-11-14 확인. KWin 튜토리얼의 일부 예제는 Plasma 5 명칭을 사용하므로
`activeWindow`, `windowAdded`, `screens`, `frameGeometry` 등은 Plasma 6 API와 소스를 확인했다.

- [KDE: KWin scripting tutorial](https://develop.kde.org/docs/plasma/kwin/)
- [KDE: KWin scripting API](https://develop.kde.org/docs/plasma/kwin/api/)
- [KDE KWin Plasma 6.0 window.h](https://github.com/KDE/kwin/blob/Plasma/6.0/src/window.h)
- [KDE KWin Plasma 6.4 window.h](https://github.com/KDE/kwin/blob/Plasma/6.4/src/window.h)
- [KDE KWin Plasma 6.4 tile API](https://github.com/KDE/kwin/blob/Plasma/6.4/src/tiles/tile.h)
- [Rectangle: upstream project and interaction reference](https://github.com/rxhanson/Rectangle)

MIT License. 자세한 내용은 `LICENSE` 참조.
