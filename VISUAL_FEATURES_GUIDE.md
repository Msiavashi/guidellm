# Visual Guide: All Features Working Together

## Complete Feature Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    GuideLLM Benchmark Run                       │
│                                                                 │
│  Features: 4 powerful enhancements for reliable benchmarking   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 🔄 UPDATE MODE (--update)                                       │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ Load existing benchmarks.json if present                │   │
│ │ • Found: Will merge results later                       │   │
│ │ • Not found: Create fresh report                        │   │
│ └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   FOR EACH RATE IN SEQUENCE                     │
│                                                                 │
│  Example: --rate 1 --rate 8 --rate 16                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
        ╔═══════════════════════════════════════╗
        ║   RATE 1 (Low Rate - No Issues)      ║
        ╚═══════════════════════════════════════╝
                            ↓
    ┌───────────────────────────────────────────┐
    │ [1] ⏱️ DELAY (--delay 0)                  │
    │ • Skip (0 seconds)                        │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ [2] ⏸️ PAUSE (--pause-for-enter)          │
    │ • If set: "Press Enter to continue..."   │
    │ • Wait for user input                     │
    │ • If not set: Skip                        │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ [3] 🔄 BACKEND RESTART (first run)        │
    │ • Skip for first run                      │
    │ • (No restart needed)                     │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ [4] 🚀 RUN BENCHMARK                      │
    │ • Execute benchmark for rate 1            │
    │ • Collect metrics                         │
    │ • Save to report                          │
    └───────────────────────────────────────────┘
                            ↓
        ╔═══════════════════════════════════════╗
        ║   RATE 8 (Medium Rate - Some Load)   ║
        ╚═══════════════════════════════════════╝
                            ↓
    ┌───────────────────────────────────────────┐
    │ [1] ⏱️ DELAY (--delay 10)                 │
    │ • Wait 10 seconds                         │
    │ • Server recovery time                    │
    │ • Connections still alive                 │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ [2] ⏸️ PAUSE (--pause-for-enter)          │
    │ • If set: "Press Enter to continue..."   │
    │ • You: Check server health                │
    │ • You: curl http://server:8000/health     │
    │ • You: Press Enter when ready             │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ [3] 🔄 BACKEND RESTART                    │
    │ • Shutdown: Close ALL connections         │
    │ • Startup: Open FRESH connections         │
    │ • Validate: Ensure backend ready          │
    │ • Time: ~2 seconds                        │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ [4] 🚀 RUN BENCHMARK                      │
    │ • Execute benchmark for rate 8            │
    │ • With fresh connections ✅               │
    │ • Clean server state ✅                   │
    │ • Collect metrics                         │
    └───────────────────────────────────────────┘
                            ↓
        ╔═══════════════════════════════════════╗
        ║   RATE 16 (High Rate - Heavy Load)   ║
        ╚═══════════════════════════════════════╝
                            ↓
    ┌───────────────────────────────────────────┐
    │ [1] ⏱️ DELAY (--delay 30)                 │
    │ • Wait 30 seconds                         │
    │ • Extended server recovery                │
    │ • Critical for high rates                 │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ [2] ⏸️ PAUSE (--pause-for-enter)          │
    │ • Manual verification before high load    │
    │ • Check: Server resources available?      │
    │ • Check: No lingering connections?        │
    │ • Press Enter when confirmed ready        │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ [3] 🔄 BACKEND RESTART                    │
    │ • Critical for high rates!                │
    │ • Shutdown: Clean slate                   │
    │ • Startup: Maximum freshness              │
    │ • Validate: Double-check ready            │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ [4] 🚀 RUN BENCHMARK                      │
    │ • Execute benchmark for rate 16           │
    │ • Fresh connections ✅                    │
    │ • Server recovered ✅                     │
    │ • Manually verified ✅                    │
    │ • Success! ✅                             │
    └───────────────────────────────────────────┘
                            ↓
                    [Continue for remaining rates...]
                            ↓
        ╔═══════════════════════════════════════╗
        ║   ALL BENCHMARKS COMPLETE              ║
        ╚═══════════════════════════════════════╝
                            ↓
    ┌───────────────────────────────────────────┐
    │ 🔄 UPDATE MODE MERGE (if --update set)    │
    │                                           │
    │ Existing: [Rate 1, Rate 2, Rate 8]       │
    │     +                                     │
    │ New:      [Rate 8, Rate 16]              │
    │     =                                     │
    │ Merged:   [Rate 1, Rate 2, Rate 8*, Rate 16] │
    │                            ↑             │
    │                         Updated          │
    └───────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────┐
    │ 💾 SAVE RESULTS                           │
    │ • benchmarks.json (merged if --update)    │
    │ • benchmarks.csv (regenerated)            │
    │ • benchmarks.html (regenerated)           │
    └───────────────────────────────────────────┘
```

## Feature Interaction Diagram

```
                    ┌─────────────────┐
                    │  User Command   │
                    │  with Flags     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
    ┌───▼───┐          ┌────▼────┐         ┌────▼────┐
    │--delay│          │--restart│         │--pause  │
    │  ⏱️   │          │   🔄    │         │   ⏸️    │
    └───┬───┘          └────┬────┘         └────┬────┘
        │                   │                    │
        └───────────┬───────┴────────────────────┘
                    │
            ┌───────▼──────┐
            │ Benchmarker  │
            │   Executes   │
            │  Each Rate   │
            └───────┬──────┘
                    │
                ┌───▼───┐
                │Results│
                └───┬───┘
                    │
            ┌───────▼──────────┐
            │   --update ?     │
            │      🔄          │
            └───────┬──────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
    Yes │                   No  │
        │                       │
┌───────▼────────┐     ┌───────▼────────┐
│ Load Existing  │     │  Save Fresh    │
│ Merge Results  │     │    Report      │
│ Save Updated   │     │                │
└────────────────┘     └────────────────┘
```

## Timeline Visualization

### Without Any Features (Original)
```
Time →
0s────────60s────────120s────────180s
├─────────┤├─────────┤├──────────┤
Rate 1     Rate 2     Rate 3
           ↑          ↑
      Reuses     Reuses
    connections  connections
                      ↑
                  Eventually
                    fails ❌
```

### With All Features
```
Time →
0s──2s──┤├──12s──┤├──42s──┤
   ⏱️  ⏸️ 🔄     ⏱️ ⏸️ 🔄
   
0s: Start
2s: Delay (0s) + Pause → Run Rate 1 → Complete
    └─ Benchmark 1 saved

12s: Delay (0s) + Pause + Restart (~2s) → Run Rate 2 → Complete
     └─ Benchmark 2 saved

42s: Delay (30s) + Pause + Restart (~2s) → Run Rate 8 → Complete
     └─ Benchmark 3 saved

Done: Update merge (if --update set)
      └─ Load existing benchmarks
      └─ Merge new results
      └─ Save updated report ✅
```

## Decision Matrix

```
┌─────────────────────────────────────────────────────────────┐
│ What do you need?                                           │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        Server recovery        Connection errors
         needed?                at high rates?
                │                       │
                Yes                     Yes
                │                       │
            ┌───▼───┐              ┌────▼────┐
            │--delay│              │--restart│
            │  ⏱️   │              │   🔄    │
            └───────┘              └─────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        Need manual         Update existing
         control?              results?
                │                       │
                Yes                     Yes
                │                       │
            ┌───▼───┐              ┌────▼────┐
            │--pause│              │--update │
            │  ⏸️   │              │   🔄    │
            └───────┘              └─────────┘
                            │
                    ┌───────▼────────┐
                    │  YOUR COMMAND  │
                    │  WITH FLAGS    │
                    └────────────────┘
```

## Feature Checklist for Your Use Case

### TensorRT-LLM Server Benchmarking

- [x] ⏱️ **Delays**: 0s for low rates, increasing for high rates
  - Prevents server overload
  - Automatic recovery time

- [x] 🔄 **Backend Restart**: Enabled for all multi-rate runs
  - Fixes `CancelledError` issues
  - Fresh connections = reliable results

- [x] ⏸️ **Pause for Enter**: Optional (debugging only)
  - Use for first test run
  - Disable for production

- [x] 🔄 **Update Mode**: Use for fixing/adding rates
  - Fix failed rates without losing others
  - Build dataset incrementally
  - Refine configurations iteratively

## Success Path

```
Start
  ↓
Run Full Sweep (Automated)
  ├─ Delays: 0s → 60s
  ├─ Backend Restart: Yes
  ├─ Pause: No
  └─ Update: No
  ↓
Some rates failed?
  ↓ Yes
Re-run Failed Rates (Manual + Update)
  ├─ Delays: Higher values
  ├─ Backend Restart: Yes
  ├─ Pause: Yes (for inspection)
  └─ Update: Yes (preserve good results)
  ↓
All rates successful!
  ↓
✅ Complete, reliable benchmark dataset
```

## Summary Card

```
╔══════════════════════════════════════════════════════════╗
║           GuideLLM Enhanced Features v1.0                ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ⏱️  Per-Rate Delays                                     ║
║     • Multiple --delay values                            ║
║     • Match rates positionally                           ║
║     • Server recovery time                               ║
║                                                          ║
║  🔄 Backend Restart Between Runs                         ║
║     • --restart-backend-between-runs                     ║
║     • Fresh connections each rate                        ║
║     • Fixes CancelledError issues                        ║
║                                                          ║
║  ⏸️  Pause for Enter                                     ║
║     • --pause-for-enter                                  ║
║     • Manual control                                     ║
║     • Inspect before each run                            ║
║                                                          ║
║  🔄 Update Mode                                          ║
║     • --update                                           ║
║     • Merge with existing results                        ║
║     • Preserve non-matching benchmarks                   ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║  Status: ✅ Production Ready                             ║
║  Tests:  ✅ Comprehensive E2E                            ║
║  Docs:   ✅ Complete                                     ║
║  Compat: ✅ 100% Backward Compatible                     ║
╚══════════════════════════════════════════════════════════╝
```

## Quick Command Builder

### Choose Your Mode:

#### 🤖 **Automated Production**
```bash
--restart-backend-between-runs \
--delay 0 --delay 0 --delay 10 --delay 30 --delay 60
```

#### 🔍 **Debugging/First Test**
```bash
--restart-backend-between-runs \
--pause-for-enter \
--delay 0 --delay 0 --delay 10 --delay 30 --delay 60
```

#### 🔧 **Fix Specific Rate**
```bash
--rate <FAILED_RATE> \
--restart-backend-between-runs \
--pause-for-enter \
--update
```

#### 📊 **Add New Rates**
```bash
--rate <NEW1> --rate <NEW2> \
--restart-backend-between-runs \
--delay <appropriate_delays> \
--update
```

---

**🎉 Complete Toolkit for Reliable, Flexible Benchmarking!**

All features work together seamlessly to ensure successful benchmarks against even the most challenging servers!
