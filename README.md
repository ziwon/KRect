# KRect 0.2.0

KDE Plasma 5.27·6에서 Mac Rectangle처럼 창을 배치하는 네이티브 데스크톱 앱.
Ubuntu에 KDE를 설치한 환경 또는 Kubuntu의 **Plasma 5.27 / 6 세션**을 대상으로 한다.
독립 창 관리자를 새로 실행하지 않고, 기존 KWin이 관리하는 활성 창을 조작한다.

**상태:** 0.2.0은 앱 검색, 전용 창, 트레이 배치 메뉴, 모니터 미리보기와 단축키 편집을 제공한다.
자동 테스트 63개(Node 45개, Python 18개)를 통과했다.
현재 Plasma 5.27.12 / KWin 5.27.11 / X11에서 새 앱의 실제 동작 14개를 확인했다.
Plasma 6 / Wayland의 실기 검증은 아직 남아 있다.
환경·배율과 설치 시도 결과는 [검증 기록](docs/VALIDATION.md#desktop-preflight-2026-11-14)에 있다.
GNOME과 Plasma 5.26 이하는 대상이 아니다. 배포판 이름보다 `plasmashell --version`으로 확인한 Plasma 버전이 중요하다.

## 포함 기능

- 앱 실행기와 KRunner에서 **KRect** 검색, 네이티브 Qt 5/6 설정 창과 시스템 트레이
- 실제 모니터 위치·방향과 선택한 작업 창을 보여주는 배치 미리보기
- 앱에서 KDE 전역 단축키 편집·충돌 확인, 간격·앱 제외·로그인 시 실행 설정
- 좌우·상하 반쪽, 네 모서리 4분할, ⅓·⅔ 배치
- 같은 반쪽 단축키를 1.2초 안에 반복하면 ½ → ⅔ → ⅓ → ½ 순환
- 중앙 정렬, KDE 기본 최대화, 처음 배치 직전의 위치·크기 복원
- 이전/다음 모니터로 이동; 배치 비율 유지, 세로 모니터의 3분할 자동 변환
- 패널을 제외한 작업 영역 사용, 논리 좌표 기준 간격 설정
- 앱별 제외, KDE 설정 화면과 전역 단축키 설정 연동
- 창 제목 표시줄 우클릭 또는 `Alt+F3` 창 메뉴의 **KRect** 하위 메뉴

이번 버전에는 마우스 드래그 스냅 미리보기, 창 전체의 자동 타일링,
앱별 영구 레이아웃 저장은 없다. KWin의 기존 드래그 동작 설정은 변경하지 않는다.
Rectangle의 코드를 이식하지 않은 독립 구현이며 Rectangle/KDE 공식 제품이 아니다.

## 설치

[0.2.0 릴리즈](https://github.com/ziwon/KRect/releases/tag/v0.2.0)에서
Ubuntu 버전에 맞는 설치 파일을 선택한다. 소스에서 설치하는 방법도 아래에 있다.

| Ubuntu | Plasma | 파일명 예시 |
| --- | --- | --- |
| 24.04 LTS | 5.27 / Qt 5 | `krect_0.2.0-1ubuntu24.04_all.deb` |
| 26.04 LTS | 6 / Qt 6 | `krect_0.2.0-1ubuntu26.04_all.deb` |

```bash
sudo apt install ./krect_0.2.0-1ubuntu24.04_all.deb
```

`.deb`는 앱, 아이콘, 실행기와 `/usr/share/kwin/scripts/krect` 엔진을 설치하고
필요한 Python/Qt 패키지를 의존성으로 설치한다. 앱 실행기에서 **KRect**를 열고 **Enable KRect**를 누른다.
기존 사용자 범위 설치가 있으면 그 복사본이 우선하므로 먼저 아래 `uninstall.sh`로 제거한다.
`.deb` 제거는 `sudo apt remove krect`를 사용하고, 실행 중인 스크립트는 해제하거나 다시 로그인한다.
빌드·태그 릴리즈 절차는 [docs/RELEASING.md](docs/RELEASING.md)에 있다.

GitHub에서 가져오는 경우 다음과 같이 설치한다. `package/`에 설치용 코드가 포함되어 있어
별도 빌드는 필요 없다.

```bash
git clone https://github.com/ziwon/KRect.git
cd KRect
plasmashell --version
# Ubuntu 24.04 / Plasma 5.27:
sudo apt install python3-pyqt5 python3-dbus libqt5svg5
# Ubuntu 26.04 / Plasma 6에서는 python3-pyqt6 python3-dbus libqt6svg6 사용
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
`dist/krect-0.2.0.kwinscript`를 선택한 뒤 활성화한다. 이 파일에는 데스크톱 앱이 포함되지 않는다.
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
| Ignored apps | 비어 있음 | 쉼표로 구분한 resource class/name 또는 desktop-file name |

설정 저장 후 KRect를 해제/적용하고 다시 활성화/적용하면 확실하게 다시 읽는다.
최대화는 KDE의 기본 최대화이며 간격을 적용하지 않는다.
모니터 순서는 논리 좌표의 x, y, 이름 순으로 정렬하고 끝에서 순환한다.
Plasma 5.27은 모니터 인덱스 API를 사용하고, 복원 대상은 화면 geometry로 식별한다.
화면 위치·해상도·회전이 바뀌어 원래 geometry를 찾지 못하면 현재 화면에 맞춰 복원한다.

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
- Plasma 5.27과 초기 Plasma 6에는 현재 최대화 모드를 읽는 속성이 없다. 스크립트 시작 **전부터** 최대화된 창은
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
드래그 스냅 영역과 사용자 지정 배치 프리셋은 아직 구현하지 않았다.

현재 Ubuntu 24.04.5 데스크톱의 Plasma 6 업그레이드 검토는
[docs/UPGRADE.md](docs/UPGRADE.md)에 있다.

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

MIT License. 자세한 내용은 `LICENSE` 참조.
