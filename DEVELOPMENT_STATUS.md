# Development status

## Phase 1 - Foundation
| Item | State | How verified |
|---|---|---|
| Project structure, architecture docs | Done | - |
| SQLite database, users, settings, persistence | Done | 6 automated tests (run here) |
| Backup / restore (with validation) | Done (logic) | automated tests; no UI button yet (Phase 8) |
| English + Arabic text, RTL flag, key parity | Done | 5 automated tests (run here) |
| Logging with crash hook | Written | not separately tested |
| Main window, 10-page navigation, dashboard, settings page (language switch, profiles) | **Written, NOT yet run** | Syntax-checked only. First real run happens in the GitHub build (UI smoke test + packaged .exe self-test) |
| Dark theme, high-DPI | Written, not run | Qt6 is high-DPI by default; visual check needs the owner |
| Application icon | Done | generated and visible in assets/ |
| PyInstaller spec, Inno Setup installer, desktop shortcut | Written, NOT yet built | Needs the GitHub Windows build |
| GitHub Actions: tests -> build exe -> launch exe in self-test -> build installer | Written | YAML validated only; not yet executed |

## Not verified / known gaps
- Arabic layout appearance (alignment, shaping) must be checked visually on Windows.
- No test of the installer on a clean Windows machine yet.

## Next
1. Owner uploads project to GitHub and sends back the build result (green or error text).
2. Fix any build problems; owner confirms the window opens and looks right.
3. Start Phase 2 (Mouse calibration) only after Phase 1 passes.
