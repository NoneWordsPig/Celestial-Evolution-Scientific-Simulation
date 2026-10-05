"""Optional frozen release verification, inactive during normal startup."""
import os
if os.environ.get('CE_SIMULATION_SMOKE_OUTPUT'):
    import json
    import traceback
    from pathlib import Path
    output = Path(os.environ['CE_SIMULATION_SMOKE_OUTPUT'])
    try:
        from PyQt6.QtWidgets import QApplication
        from physics import kernels
        from scientific.precision import load_scene_preserving_precision
        from scientific.simulator import SimulationConfig, build_state_from_scene, run_simulation
        from ui.startup_window import StartupWindow
        from ui.playback_window import PlaybackWindow
        app = QApplication([])
        startup = StartupWindow()
        scenes = startup.scene_manager.scan_scenes()
        assert len(scenes) == 9, scenes
        scene = load_scene_preserving_precision(next(s['path'] for s in scenes if Path(s['path']).stem == 'figure8'))
        initial = build_state_from_scene(scene)
        assert kernels.NUMBA_AVAILABLE
        modes = []
        for digits in (None, 50):
            result = run_simulation(initial, SimulationConfig(.02, .001, 1, requested_digits=digits))
            assert result is not None and result.total_steps == 20 and result.frame_count >= 2
            modes.append(result.precision_mode)
            playback = PlaybackWindow(result)
            playback.show()
            app.processEvents()
            playback.close()
        assert modes == ['float64', 'decimal'], modes
        startup.show()
        app.processEvents()
        startup.close()
        output.write_text(json.dumps({'ok': True, 'presets': len(scenes), 'modes': modes, 'numba': True}), encoding='utf-8')
    except Exception:
        output.write_text(traceback.format_exc(), encoding='utf-8')
        os._exit(1)
    os._exit(0)
