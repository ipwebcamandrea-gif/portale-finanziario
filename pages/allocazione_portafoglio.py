
from pathlib import Path
import runpy


# Wrapper necessario per registrare la pagina nel multipage router di Streamlit.
# Il codice reale resta nella cartella dedicata pages/allocazione/.
TARGET_PAGE = Path(__file__).resolve().parent / "allocazione" / "allocazione_portafoglio.py"

runpy.run_path(str(TARGET_PAGE), run_name="__main__")
