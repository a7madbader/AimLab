# Development status

**Phase 1: PASSED** - owner confirmed on Windows that the installer builds, the window opens, navigation and EN/AR switching work.
**Phase 2: written; logic tested here; Windows/hardware parts await owner test.**

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


## Phase 2 - Mouse calibration (v0.2.0)
| Item | State | How verified |
|---|---|---|
| cm/360, eDPI, sensitivity-for-target, mousepad degrees, DPI-from-counts | Done | 7 unit tests incl. published reference values (800 DPI CS2 sens 1 = 51.95 cm) |
| Polling-rate analysis (rate, median, p95, jitter; ignores pauses, robust to bursty delivery) | Done | unit tests with synthetic 500/1000 Hz data, pauses, bursts, too-little-data; deliberately broken code was caught |
| DPI measurement analysis | Done | unit tests (800 DPI over 20 cm, sideways drift, no data) |
| Acceleration detection from equal-distance swipes at 3 speeds | Done (heuristic thresholds 8% / 15%) | unit tests: none / possible / likely / inconclusive |
| Swipe smoothness (straightness, sideways wobble, speed variation) | Done | unit tests (steady, wobbly, uneven-speed, insufficient) |
| Mouse profiles + calibration history in database, upgrade of existing v1 databases, restore of older backups | Done | 5 unit tests |
| EN/AR texts incl. what/why/measures/how/results/improve/limits for every tool | Done | key-parity + completeness tests; Arabic wording needs owner's review |
| Windows Raw Input capture (ctypes, hidden window, WM_INPUT) | **Written, never run** | CI runs an injection test (informational) and the packaged .exe tries start/stop in its self-test |
| Windows pointer settings (Enhance Pointer Precision, speed) | **Written, never run** | parse logic unit-tested; the Windows call itself untested |
| Calibration page (7 tabs) | **Written, never run** | CI UI smoke test drives the whole workflow with a fake mouse (DB, Arabic, dashboard) |

### Not verifiable without the owner's real mouse
- Whether measured polling rate / DPI match reality on real hardware (needs the owner to run the tools and compare with the mouse spec and a ruler).
- Whether the Space-to-finish flow feels right.

### Known limits / gaps (documented honestly in the app)
- Timestamps are taken when the program receives the report, not in the mouse. 4000 Hz+ may read low (GetRawInputBuffer batching is a later improvement).
- Acceleration test only sees acceleration present in raw data; Windows' own acceleration is checked via the pointer-settings tab. Thresholds are wide because humans cannot repeat distances precisely.
- "Mouse movement path recording": swipe metrics are computed, but raw paths are not stored or plotted yet.
- Only games with well-established yaw values are in the calculator (CS2, Valorant, Apex, Overwatch 2, CoD) plus custom yaw. Others come in Phase 6.
- Mouse profile "notes" exist in the database but have no UI field yet.
