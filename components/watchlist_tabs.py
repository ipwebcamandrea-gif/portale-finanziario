from html import escape

import streamlit as st

from utils.symbols import slug_safe
from utils.market_data import watchlist_has_sma200_zone
from utils.watchlist_storage import salva_sessione_su_disco


# =========================
# ORDINAMENTO WATCHLIST
# =========================

def sposta_elemento(lista, elemento, direzione):
    lista_nuova = list(lista)

    if elemento not in lista_nuova:
        return lista_nuova

    indice = lista_nuova.index(elemento)
    nuovo_indice = indice + direzione

    if nuovo_indice < 0 or nuovo_indice >= len(lista_nuova):
        return lista_nuova

    lista_nuova[indice], lista_nuova[nuovo_indice] = (
        lista_nuova[nuovo_indice],
        lista_nuova[indice],
    )

    return lista_nuova


def sposta_watchlist(nome_lista, direzione):
    data = st.session_state["tv_watchlists_data"]
    watchlists = data["watchlists"]
    nomi = list(watchlists.keys())
    nuovi_nomi = sposta_elemento(nomi, nome_lista, direzione)

    if nuovi_nomi == nomi:
        return

    nuova_struttura = {}

    for nome in nuovi_nomi:
        nuova_struttura[nome] = watchlists[nome]

    data["watchlists"] = nuova_struttura
    data["active_watchlist"] = st.session_state["tv_current_list"]

    salva_sessione_su_disco()


# =========================
# AZIONI WATCHLIST
# =========================

def elimina_watchlist_attiva():
    data = st.session_state["tv_watchlists_data"]
    watchlists = data["watchlists"]
    current = st.session_state["tv_current_list"]

    if len(watchlists) <= 1:
        st.warning("Non puoi eliminare l'unica watchlist rimasta.")
        return

    nomi = list(watchlists.keys())
    indice_corrente = nomi.index(current) if current in nomi else 0

    if current in watchlists:
        del watchlists[current]

    nuovi_nomi = list(watchlists.keys())
    nuovo_indice = min(indice_corrente, len(nuovi_nomi) - 1)
    nuovo_corrente = nuovi_nomi[nuovo_indice]

    st.session_state["tv_current_list"] = nuovo_corrente
    data["active_watchlist"] = nuovo_corrente
    st.session_state["tv_confirm_delete_tab"] = False

    salva_sessione_su_disco()
    st.cache_data.clear()


def rinomina_watchlist_attiva(nuovo_nome):
    data = st.session_state["tv_watchlists_data"]
    watchlists = data["watchlists"]
    current = st.session_state["tv_current_list"]

    nuovo_nome = str(nuovo_nome or "").strip()

    if not nuovo_nome:
        st.warning("Inserisci un nome valido.")
        return False

    if nuovo_nome == current:
        st.session_state["tv_show_rename_panel"] = False
        return True

    if nuovo_nome in watchlists:
        st.warning("Esiste gia una watchlist con questo nome.")
        return False

    nuova_struttura = {}

    for nome, simboli in watchlists.items():
        if nome == current:
            nuova_struttura[nuovo_nome] = simboli
        else:
            nuova_struttura[nome] = simboli

    data["watchlists"] = nuova_struttura
    data["active_watchlist"] = nuovo_nome

    st.session_state["tv_current_list"] = nuovo_nome
    st.session_state["tv_show_rename_panel"] = False

    salva_sessione_su_disco()
    st.cache_data.clear()

    return True


def crea_watchlist(nuovo_nome):
    nuovo_nome = str(nuovo_nome or "").strip()

    if not nuovo_nome:
        st.warning("Inserisci un nome valido.")
        return False

    watchlists = st.session_state["tv_watchlists_data"]["watchlists"]

    if nuovo_nome in watchlists:
        st.warning("Questa watchlist esiste gia.")
        return False

    watchlists[nuovo_nome] = []

    st.session_state["tv_current_list"] = nuovo_nome
    st.session_state["tv_watchlists_data"]["active_watchlist"] = nuovo_nome
    st.session_state["tv_show_create_panel"] = False
    st.session_state["tv_confirm_delete_tab"] = False
    st.session_state["tv_show_rename_panel"] = False

    salva_sessione_su_disco()
    st.cache_data.clear()

    return True


# =========================
# VISTA COMPATTA: SELECTBOX WATCHLIST
# =========================

def format_compact_watchlist_name(name):
    if watchlist_has_sma200_zone(name):
        return "🟠 " + name

    return name


def render_compact_watchlist_selector():
    watchlists = st.session_state["tv_watchlists_data"]["watchlists"]
    watchlist_names = list(watchlists.keys())

    if not watchlist_names:
        st.warning("Nessuna watchlist disponibile.")
        return

    current = st.session_state.get("tv_current_list")

    if current not in watchlists:
        current = watchlist_names[0]
        st.session_state["tv_current_list"] = current
        st.session_state["tv_watchlists_data"]["active_watchlist"] = current
        salva_sessione_su_disco()

    # In vista compatta chiudiamo eventuali pannelli aperti della modalita normale.
    st.session_state["tv_show_create_panel"] = False
    st.session_state["tv_show_rename_panel"] = False
    st.session_state["tv_confirm_delete_tab"] = False

    current_index = watchlist_names.index(current)

    selected = st.selectbox(
        "📂 Watchlist",
        options=watchlist_names,
        index=current_index,
        format_func=format_compact_watchlist_name,
        key="tv_compact_watchlist_selector",
        help="Seleziona la watchlist da visualizzare",
    )

    if selected != current:
        st.session_state["tv_current_list"] = selected
        st.session_state["tv_watchlists_data"]["active_watchlist"] = selected
        salva_sessione_su_disco()
        st.rerun()


# =========================
# RENDER TAB PRINCIPALI
# =========================

def render_tabs_header():
    compact_mode = bool(st.session_state.get("tv_compact_rows", False))

    if compact_mode:
        render_compact_watchlist_selector()
        return

    watchlists = st.session_state["tv_watchlists_data"]["watchlists"]
    watchlist_names = list(watchlists.keys())

    if not watchlist_names:
        st.warning("Nessuna watchlist disponibile.")
        return

    current = st.session_state.get("tv_current_list")

    if current not in watchlists:
        current = watchlist_names[0]
        st.session_state["tv_current_list"] = current
        st.session_state["tv_watchlists_data"]["active_watchlist"] = current
        salva_sessione_su_disco()

    cols = st.columns(len(watchlist_names) + 1)

    for idx, name in enumerate(watchlist_names):
        in_zone = watchlist_has_sma200_zone(name)
        is_active = name == st.session_state["tv_current_list"]

        tab_kind = "zone" if in_zone else "normal"
        active_part = "_active_tab" if is_active else ""
        tab_wrap_key = "tv_" + tab_kind + "_tab" + active_part + "_" + slug_safe(name)
        tab_label = ("▶ " if is_active else "") + name

        with cols[idx]:
            with st.container(key=tab_wrap_key):
                if st.button(
                    tab_label,
                    key="tv_tab_btn_" + slug_safe(name),
                    use_container_width=True,
                ):
                    st.session_state["tv_current_list"] = name
                    st.session_state["tv_watchlists_data"]["active_watchlist"] = name
                    st.session_state["tv_confirm_delete_tab"] = False
                    st.session_state["tv_show_rename_panel"] = False
                    salva_sessione_su_disco()
                    st.rerun()

    with cols[-1]:
        plus_col, rename_col, minus_col = st.columns(3, gap="small")

        with plus_col:
            with st.container(key="tv_tab_action_btn_plus"):
                if st.button(
                    "+",
                    key="tv_create_toggle",
                    use_container_width=True,
                    help="Crea nuova watchlist",
                ):
                    st.session_state["tv_show_create_panel"] = not st.session_state["tv_show_create_panel"]
                    st.session_state["tv_confirm_delete_tab"] = False
                    st.session_state["tv_show_rename_panel"] = False
                    st.rerun()

        with rename_col:
            with st.container(key="tv_tab_action_btn_rename"):
                if st.button(
                    "✎",
                    key="tv_rename_current_list",
                    use_container_width=True,
                    help="Rinomina la watchlist attiva",
                ):
                    st.session_state["tv_show_rename_panel"] = not st.session_state["tv_show_rename_panel"]
                    st.session_state["tv_show_create_panel"] = False
                    st.session_state["tv_confirm_delete_tab"] = False
                    st.rerun()

        with minus_col:
            with st.container(key="tv_tab_action_btn_minus"):
                if st.button(
                    "−",
                    key="tv_delete_current_list",
                    use_container_width=True,
                    help="Elimina la watchlist attiva",
                ):
                    st.session_state["tv_confirm_delete_tab"] = True
                    st.session_state["tv_show_create_panel"] = False
                    st.session_state["tv_show_rename_panel"] = False
                    st.rerun()


# =========================
# TOOLBAR TAB
# =========================

def render_tabs_toolbar():
    # La toolbar sotto i tab serve solo in modalita normale.
    # In vista compatta i tab sono sostituiti dalla selectbox.
    if bool(st.session_state.get("tv_compact_rows", False)):
        return

    move_tab_col_1, move_tab_col_2, spacer_col = st.columns([0.55, 0.55, 5.9])

    with move_tab_col_1:
        if st.button(
            "◀",
            key="tv_move_tab_left",
            use_container_width=True,
            help="Sposta la watchlist attiva a sinistra",
        ):
            st.session_state["tv_confirm_delete_tab"] = False
            st.session_state["tv_show_rename_panel"] = False
            sposta_watchlist(st.session_state["tv_current_list"], -1)
            st.rerun()

    with move_tab_col_2:
        if st.button(
            "▶",
            key="tv_move_tab_right",
            use_container_width=True,
            help="Sposta la watchlist attiva a destra",
        ):
            st.session_state["tv_confirm_delete_tab"] = False
            st.session_state["tv_show_rename_panel"] = False
            sposta_watchlist(st.session_state["tv_current_list"], 1)
            st.rerun()


# =========================
# PANNELLI TAB
# =========================

def render_delete_confirm_panel():
    if bool(st.session_state.get("tv_compact_rows", False)):
        return

    if not st.session_state.get("tv_confirm_delete_tab", False):
        return

    current_confirm = st.session_state.get("tv_current_list", "")

    st.markdown(
        f"""
        <div class="tv-delete-confirm-panel">
            <div class="tv-delete-confirm-title">Conferma eliminazione watchlist</div>
            <div class="tv-delete-confirm-text">
                Vuoi eliminare definitivamente la watchlist <b>{escape(current_confirm)}</b> e tutti i simboli contenuti?
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    confirm_col_1, confirm_col_2, confirm_col_3 = st.columns([1.25, 1.0, 4.75])

    with confirm_col_1:
        if st.button(
            "Elimina",
            key="tv_confirm_delete_current_list",
            use_container_width=True,
        ):
            elimina_watchlist_attiva()
            st.rerun()

    with confirm_col_2:
        if st.button(
            "Annulla",
            key="tv_cancel_delete_current_list",
            use_container_width=True,
        ):
            st.session_state["tv_confirm_delete_tab"] = False
            st.rerun()


def render_rename_panel():
    if bool(st.session_state.get("tv_compact_rows", False)):
        return

    if not st.session_state.get("tv_show_rename_panel", False):
        return

    current_rename = st.session_state.get("tv_current_list", "")

    st.markdown(
        f"""
        <div class="tv-delete-confirm-panel">
            <div class="tv-delete-confirm-title">Rinomina watchlist</div>
            <div class="tv-delete-confirm-text">
                Nome attuale: <b>{escape(current_rename)}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rename_col_1, rename_col_2, rename_col_3, rename_col_4 = st.columns([3, 1, 1, 3])

    with rename_col_1:
        nuovo_nome_watchlist = st.text_input(
            "Nuovo nome watchlist",
            value=current_rename,
            key="tv_rename_list_name_" + slug_safe(current_rename),
            label_visibility="collapsed",
        ).strip()

    with rename_col_2:
        if st.button(
            "Salva",
            key="tv_confirm_rename_current_list",
            use_container_width=True,
        ):
            if rinomina_watchlist_attiva(nuovo_nome_watchlist):
                st.success("Watchlist rinominata.")
                st.rerun()

    with rename_col_3:
        if st.button(
            "Annulla",
            key="tv_cancel_rename_current_list",
            use_container_width=True,
        ):
            st.session_state["tv_show_rename_panel"] = False
            st.rerun()


def render_create_panel():
    if bool(st.session_state.get("tv_compact_rows", False)):
        return

    if not st.session_state.get("tv_show_create_panel", False):
        return

    create_col_1, create_col_2, create_col_3 = st.columns([3, 1, 1])

    with create_col_1:
        new_list_name = st.text_input(
            "Nome nuova watchlist",
            placeholder="Esempio: Tech USA, ETF, Italia",
            key="tv_new_list_name",
        ).strip()

    with create_col_2:
        st.write("")
        st.write("")

        if st.button("Crea", key="tv_create_list", use_container_width=True):
            if crea_watchlist(new_list_name):
                st.success("Watchlist creata.")
                st.rerun()

    with create_col_3:
        st.write("")
        st.write("")

        if st.button("Annulla", key="tv_cancel_create", use_container_width=True):
            st.session_state["tv_show_create_panel"] = False
            st.rerun()


# =========================
# ENTRY POINT COMPONENTE
# =========================

def render_watchlist_tabs():
    render_tabs_header()
    render_tabs_toolbar()
    render_delete_confirm_panel()
    render_rename_panel()
    render_create_panel()
