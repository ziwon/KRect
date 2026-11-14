# KRect 사용 가이드

[한국어 소개](../README.md) · [English overview](../README.en.md)

소스 설치, 전체 단축키, 설정과 동작의 세부 사항입니다.
이 문서의 명령은 KRect 소스 디렉터리에서 실행합니다. `.deb` 설치는 [README](../README.md#설치)를 참고하세요.

## 소스에서 설치

GitHub에서 가져오는 경우 다음과 같이 설치한다. `package/`에 설치용 코드가 포함되어 있어
별도 빌드는 필요 없다.

```bash
git clone https://github.com/ziwon/KRect.git
cd KRect
plasmashell --version
# Ubuntu 24.04 / Plasma 5.27:
sudo apt install python3-pyqt5 python3-dbus libqt5svg5
# Ubuntu 26.04 / Plasma 6에서는 python3-pyqt6 python3-dbus libqt6svg6 qt6-svg-plugins 사용
bash install.sh
```

ZIP 파일을 내려받았다면 다음 순서를 따른다.

1. ZIP 압축을 풀고 `krect` 디렉터리에서 실행한다. Node/Python 빌드 없이 설치할 수 있다.

   ```bash
   plasmashell --version
   bash install.sh
   ```

2. 앱 실행기에서 **KRect**를 검색한다. 바로 실행하려면 `~/.local/bin/krect`를 사용한다.
3. 앱의 **Enable KRect**를 누른다. 작업할 창을 한 번 선택한 뒤 KRect의 배치 버튼이나 트레이 메뉴를 사용한다.
4. **Shortcuts**에서 단축키를 편집하고 저장한다. 기존 KDE 단축키와의 충돌은 저장 전에 표시한다.

설치 스크립트는 `plasmashell --version`을 확인해 Plasma 5.27에서는 `kpackagetool5`,
Plasma 6에서는 `kpackagetool6`를 사용한다. 두 도구가 모두 설치돼 있어도 Plasma 버전에 맞춰 선택한다.
`sudo`로 설치 스크립트를 실행하지 않는다.
사용자 범위에 앱과 KPackage를 설치하며, 앱을 켜기 전까지 창 배치 기능을 활성화하지 않는다.
위치는 보통 `~/.local/share/krect`, `~/.local/bin/krect`, `~/.local/share/kwin/scripts/krect`이다.
`bash install.sh --script-only`는 기존처럼 KWin 엔진만 설치한다.

GUI 설치도 가능하다. KWin 스크립트 화면의 **파일에서 설치**로
`dist/krect-0.3.1.kwinscript`를 선택한 뒤 활성화한다. 이 파일에는 데스크톱 앱이 포함되지 않는다.
Git clone으로 가져왔다면 먼저 `python3 tools/build.py`로 이 파일을 생성한다.
`dist/`의 ZIP과 `.kwinscript` 빌드 결과는 Git에서 추적하지 않는다.

업데이트할 때는 앱을 종료하고 `bash install.sh`를 실행한 다음 다시 연다.
실행 중인 앱에서 KRect를 껐다 켜면 새 엔진을 읽는다. 이때 원래 배치 기록은 초기화된다.

## 앱 사용

**Layouts**는 마지막으로 선택한 작업 창을 대상으로 한다. KRect 자신의 창은 제외하며,
선택한 창이 닫히거나 다른 가상 데스크톱·활동으로 바뀌면 적용을 중단한다.
미리보기의 화면 번호는 실제 좌표 순서다. 세로 화면에서는 ⅓ 아이콘과 실제 배치가 위아래로 바뀐다.

**Preferences**에서 간격, 연속 입력 시간, 세로 3분할, 제외 앱을 조정하고 적용한다.
현재 작업 창의 앱 ID를 제외 목록에 추가할 수도 있다. 로그인 시 실행은 선택 사항이다.
설정을 적용하면 KWin에 다시 읽히고 원래 배치 기록이 초기화된다.

창 닫기는 트레이가 있을 때 기본적으로 트레이에 유지한다. **Quit**는 앱을 종료하며
KWin 단축키는 계속 작동한다. 배치 기능도 끄려면 먼저 앱의 KRect 버튼을 끈다.
화면은 시스템 언어에 따라 한국어 또는 영어로 표시한다. `krect --language ko`로 바꿔 실행할 수 있다.

## 상단 드래그 배치

0.3.0부터 사용할 수 있다. 기존 앱을 종료하고 새 패키지를 설치한 뒤 다시 실행한다.

1. KRect를 켜고 트레이에서 실행해 둔다.
2. 작업 창의 제목 표시줄을 잡고 **사용할 모니터의 상단 중앙**으로 끈다.
3. 나타난 막대에서 원하는 작은 영역으로 마우스를 옮긴다. 실제 배치될 위치가 화면에 미리 표시된다.
4. 마우스를 놓으면 배치된다. 막대를 벗어나면 일반 드래그를 계속하고, `Esc`는 이동을 취소한다.

좌우·상하 2분할, 3분할, ⅔+⅓, ⅓+⅔, 4분할을 제공한다. 패널을 제외한 작업 영역과
설정한 창 간격을 사용하며, 세로 모니터에서는 ⅓·⅔ 구성이 위아래로 바뀐다.
복원 단축키는 이 드래그를 시작하기 전의 위치로 돌아간다.

**Preferences → 창을 화면 상단으로 끌면 배치 막대 표시**에서 끌 수 있다.
KRect 앱을 종료하면 막대가 나타나지 않는다. 기존 단축키와 KDE 모서리 배치는 계속 사용할 수 있다.
최대화 버튼에 마우스를 올리는 방식은 포함하지 않는다.
Plasma 5.27/X11에서 실제 드래그를 확인했으며, Plasma 6/Wayland의 실제 드래그 검증은 남아 있다.

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

앱의 **Preferences**를 연다. 엔진만 설치했다면 KWin 스크립트 목록의 설정 버튼을 사용한다.

| 설정 | 기본값 | 의미 |
| --- | --- | --- |
| Window gap | 8 | 화면 가장자리와 창 사이의 간격. 물리 픽셀이 아닌 논리 픽셀 |
| Cycle repeated half actions | 켬 | 반쪽 단축키의 ½ → ⅔ → ⅓ 순환 |
| Repeat interval | 1200ms | 같은 창에서 같은 단축키를 반복했다고 판단하는 시간 |
| Portrait thirds | 켬 | 세로 화면에서 ⅓·⅔ 배치를 위→아래 방향으로 적용 |
| Snap bar | 켬 | 상단 중앙 드래그 시 배치 막대 표시. KRect 앱 실행 필요 |
| Ignored apps | 비어 있음 | 쉼표로 구분한 resource class/name 또는 desktop-file name |

설정 저장 후 KRect를 해제/적용하고 다시 활성화/적용하면 확실하게 다시 읽는다.
최대화는 KDE의 기본 최대화이며 간격을 적용하지 않는다.
모니터 순서는 논리 좌표의 x, y, 이름 순으로 정렬하고 끝에서 순환한다.
Plasma 5.27은 모니터 인덱스 API를 사용하고, 복원 대상은 화면 geometry로 식별한다.
화면 위치·해상도·회전이 바뀌어 원래 geometry를 찾지 못하면 현재 화면에 맞춰 복원한다.

복원은 **해당 창에 처음 KRect 명령을 적용하기 직전**의 배치를 기준으로 한다.
다른 KRect 배치로 바꿔도 그 기준은 유지된다. 복원 후에는 기록을 지운다.
일반 드래그·리사이즈가 끝나면 기록을 지우고, 다음 명령에서 새 기준을 잡는다.
배치 막대로 드롭하면 해당 드래그 시작 위치를 새 복원 기준으로 저장한다.
창을 닫거나 스크립트를 다시 시작하면 기록은 사라진다.
원래 모니터가 연결 해제되었으면 현재 모니터의 작업 영역에 맞게 복원한다.

## 실제 환경에서 확인할 부분

- Wayland 앱의 resize는 비동기 요청이다. 앱의 최소 크기·고정 종횡비·KWin 창 규칙 때문에
  ⅓이나 ¼ 크기와 정확히 일치하지 않을 수 있다. 요청을 무한히 재시도하지 않는다.
- 전체 화면, 고정 크기 창, 패널, 메뉴, 최소화된 창은 제외한다. 이동/크기 변경 중에는
  단축키·앱 배치를 적용하지 않으며, 배치 막대는 드래그가 끝난 뒤 적용한다.
- 창 배치 시 기존 타일 연결은 해제한다. 복원은 geometry와 확인 가능한 최대화 상태를 복구하며,
  원래 사용자 정의 타일 그룹 소속까지 복구하지는 않는다.
- Plasma 5.27과 초기 Plasma 6에는 현재 최대화 모드를 읽는 속성이 없다. 스크립트 시작 **전부터** 최대화된 창은
  원래 화면 크기로는 복원되더라도 최대화 플래그까지 복구되지 않을 수 있다.
  모드를 읽을 수 있는 버전 또는 실행 중 관찰한 최대화 변경은 복원한다.
- 디스플레이 배율을 geometry에 다시 곱하지 않는다. 혼합 배율, fractional scaling,
  모니터 분리/재연결, Chromium/Electron 및 XWayland 앱은 실기 검증이 필요하다.
- 다른 자동 타일링 스크립트와 함께 쓰면 서로 창 배치를 바꿀 수 있다.

짧은 검증 순서는 [docs/VALIDATION.md](VALIDATION.md)에 있다.

## 제거

`.deb` 설치는 `sudo apt remove krect`로 제거합니다. 실행 중인 KRect를 끄거나 다시 로그인하면 적용됩니다.
소스로 설치했다면 앱을 종료한 뒤 아래 명령을 사용합니다.

```bash
bash uninstall.sh
```

자동 활성화 설정을 끄고 현재 사용자의 KRect 패키지를 제거한다.
D-Bus에 접근할 수 있으면 실행 중인 KRect 스크립트만 종료한다.
접근할 수 없으면 로그아웃 후 다시 로그인하면 적용된다.
개인 설정과 수정한 단축키 항목은 남겨 재설치 시 사용할 수 있다.

## 개발

KWin 엔진은 JavaScript만 사용한다. 데스크톱 앱은 배포판의 `/usr/bin/python3`,
`python3-dbus`, PyQt 5/6을 사용한다. 네트워크나 Node 런타임은 필요 없다.
테스트에는 Node 18 이상, 패키징에는 Python 3.9 이상이 필요하다.

```bash
node --test tests/*.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tools/build.py
/usr/bin/python3 app/main.py
QT_QPA_PLATFORM=offscreen /usr/bin/python3 app/main.py --smoke-test
```

- `src/main.js`: geometry 계산과 KWin 연결. 의존성 없이 한 파일로 패키징
- `app/`: Qt 데스크톱 앱, 트레이, KDE D-Bus 연결과 실행기
- `package/`: KPackage 메타데이터, KConfig 스키마와 Qt Designer 설정 UI
- `tests/`: geometry, 복원, 모니터 이동, 지연된 geometry 반영, 설치 명령의 모의 테스트
- `tools/build.py`: 소스를 패키지로 복사하고 `.kwinscript`와 소스 ZIP 생성

수정한 `src/main.js`를 설치에 반영하려면 **다시 빌드**한 뒤 설치한다.
`package/contents/code/main.js`는 생성 파일이므로 직접 수정하지 않는다.

다음 검증 범위는 Plasma 6 / Wayland 실기, 물리 키 입력의 충돌과 혼합 배율이다.
상단 드래그 배치 막대는 0.3.0부터 제공한다. 사용자 지정 배치 프리셋은 아직 구현하지 않았다.

현재 Ubuntu 24.04.5 데스크톱의 Plasma 6 업그레이드 검토는
[docs/UPGRADE.md](UPGRADE.md)에 있다.

## 구현 근거

2026-11-14 확인. KWin 튜토리얼의 일부 예제는 Plasma 5 명칭을 사용하므로
`activeWindow`, `windowAdded`, `screens`, `frameGeometry` 등은 Plasma 6 API와 소스를 확인했다.

- [KDE: KWin scripting tutorial](https://develop.kde.org/docs/plasma/kwin/)
- [KDE: KWin scripting API](https://develop.kde.org/docs/plasma/kwin/api/)
- [KDE KWin Plasma 5.27 workspace API](https://github.com/KDE/kwin/blob/Plasma/5.27/src/scripting/workspace_wrapper.h)
- [KDE KWin Plasma 5.27 window API](https://github.com/KDE/kwin/blob/Plasma/5.27/src/window.h)
- [KDE KWin Plasma 6.0 window.h](https://github.com/KDE/kwin/blob/Plasma/6.0/src/window.h)
- [KDE KWin Plasma 6.4 window.h](https://github.com/KDE/kwin/blob/Plasma/6.4/src/window.h)
- [KDE KWin Plasma 6.4 tile API](https://github.com/KDE/kwin/blob/Plasma/6.4/src/tiles/tile.h)
- [Rectangle: upstream project and interaction reference](https://github.com/rxhanson/Rectangle)

MIT License. 자세한 내용은 [LICENSE](../LICENSE)를 참고하세요.
