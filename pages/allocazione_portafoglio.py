from pathlib import Path
import runpy


TARGET_PAGE = Path(__file__).resolve().parent / "allocazione" / "allocazione_portafoglio.py"
runpy.run_path(str(TARGET_PAGE), run_name="__main__")
