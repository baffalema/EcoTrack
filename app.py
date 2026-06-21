import streamlit as st
import pandas as pd
import sqlite3
import datetime
import json
import os
import hashlib
import hmac
import binascii
from dateutil.relativedelta import relativedelta

# ==============================================================================
# 1. PAGE SETUP
# ==============================================================================
st.set_page_config(
    page_title="EcoTrack: Green Schools Innovation",
    layout="wide",
    page_icon="🌱"
)

DB_FILE = "ecotrack_nigeria.db"          # fresh schema (users + per-species audits)
CSV_FILE = "species_directory.csv"
NIGERIA_FILE = "nigeria_states_lgas.json"
UPLOAD_DIR = "uploaded_evidence"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ROLES = ["Participant", "Inspector", "Admin"]
INSTITUTION_TYPES = ["Public School", "Private School", "NGO", "Government Agency",
                     "Community Group", "Individual", "Other"]


# ==============================================================================
# 2. PASSWORD HASHING (stdlib only — PBKDF2-HMAC-SHA256)
# ==============================================================================
def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = binascii.unhexlify(salt)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode()

def verify_password(password, salt_hex, hash_hex):
    _, check = hash_password(password, salt_hex)
    return hmac.compare_digest(check, hash_hex)


# ==============================================================================
# 3. NIGERIA GEOGRAPHY (all 36 states + FCT, ~766 LGAs)
# ==============================================================================
def load_nigeria_geo():
    """Loads the {state: [lgas]} map. Falls back to a tiny stub if the file is missing."""
    if os.path.exists(NIGERIA_FILE):
        with open(NIGERIA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"Katsina": ["Katsina", "Batagarawa", "Dutsin-Ma"]}

NIGERIA = load_nigeria_geo()
STATES = sorted(NIGERIA.keys())

def state_lga_picker(key_prefix, default_state=None, default_lga=None):
    """Renders a cascading State -> LGA pair OUTSIDE any form so the LGA list
    refreshes the moment the state changes. Returns (state, lga)."""
    s_index = STATES.index(default_state) if default_state in STATES else 0
    col1, col2 = st.columns(2)
    state = col1.selectbox("State", STATES, index=s_index, key=f"{key_prefix}_state")
    lgas = NIGERIA.get(state, [])
    l_index = lgas.index(default_lga) if default_lga in lgas else 0
    lga = col2.selectbox("Local Government Area (LGA)", lgas, index=l_index, key=f"{key_prefix}_lga")
    return state, lga


# ==============================================================================
# 4. DATABASE
# ==============================================================================
def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def setup_application_tables():
    conn = get_connection()
    cur = conn.cursor()

    # ---- individual user accounts (registration + login) --------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Participant',
            institution_name TEXT,
            institution_type TEXT,
            home_state TEXT,
            home_lga TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by TEXT NOT NULL,
            institution_name TEXT,
            state_name TEXT NOT NULL,
            lga_name TEXT NOT NULL,
            planting_date TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            gps_accuracy REAL NOT NULL,
            device_info TEXT,
            evidence_links TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(created_by) REFERENCES users(username)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS batch_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            tree_species TEXT NOT NULL,
            qty_planted INTEGER NOT NULL,
            qty_survived INTEGER NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )
    """)

    # ---- per-species inspections (exact, not estimated) ---------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            tree_species TEXT NOT NULL,
            interval_months TEXT NOT NULL,
            qty_alive INTEGER NOT NULL,
            qty_dead INTEGER NOT NULL,
            inspection_date TEXT NOT NULL,
            inspector TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'Approved',
            FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY(item_id) REFERENCES batch_items(item_id) ON DELETE CASCADE
        )
    """)

    # Seed a default admin so the system is usable on first run
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        salt, ph = hash_password("admin123")
        cur.execute("""INSERT INTO users
            (username,email,full_name,password_hash,password_salt,role,
             institution_name,institution_type,home_state,home_lga,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            ("admin", "admin@ecotrack.ng", "System Administrator", ph, salt, "Admin",
             "EcoTrack HQ", "Government Agency", "Federal Capital Territory (Abuja)",
             "Abuja Municipal (AMAC)", datetime.datetime.now().isoformat(timespec="seconds")))

    conn.commit()
    conn.close()


# ==============================================================================
# 5. USER MANAGEMENT
# ==============================================================================
def register_user(username, email, full_name, password, role,
                  institution_name, institution_type, home_state, home_lga):
    salt, ph = hash_password(password)
    conn = get_connection()
    try:
        conn.execute("""INSERT INTO users
            (username,email,full_name,password_hash,password_salt,role,
             institution_name,institution_type,home_state,home_lga,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (username, email, full_name, ph, salt, role, institution_name,
             institution_type, home_state, home_lga,
             datetime.datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return True, "Account created. Switch to the Log In tab to sign in."
    except sqlite3.IntegrityError as e:
        msg = "Username already taken." if "username" in str(e) else \
              "Email already registered." if "email" in str(e) else f"Could not register: {e}"
        return False, msg
    finally:
        conn.close()

def authenticate(username, password):
    conn = get_connection()
    row = conn.execute(
        "SELECT username,email,full_name,password_hash,password_salt,role,"
        "institution_name,home_state,home_lga "
        "FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not row:
        return None
    if verify_password(password, row[4], row[3]):
        return {"username": row[0], "email": row[1], "full_name": row[2],
                "role": row[5], "institution_name": row[6],
                "home_state": row[7], "home_lga": row[8]}
    return None


# ==============================================================================
# 6. SPECIES DIRECTORY (CSV ENGINE)
# ==============================================================================
def load_master_species_directory():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        d = {}
        for _, row in df.iterrows():
            d[str(row['species_name']).strip()] = {
                "botanical": row['botanical_name'],
                "wd": float(row['wood_density']),
                "gf": float(row['growth_factor']),
                "type": row['category']
            }
        return d
    return {"Neem (Darbejiya)": {"botanical": "Azadirachta indica", "wd": 0.68,
                                 "gf": 0.025, "type": "Windbreaker & Desertification"}}

TREE_DATABASE = load_master_species_directory()


# ==============================================================================
# 7. ENVIRONMENTAL CALCULATIONS
# ==============================================================================
def calculate_carbon_absorbed(species_name, tree_count):
    info = TREE_DATABASE.get(species_name, {"wd": 0.55, "gf": 0.022})
    yearly_kg = (info["wd"] * 50) * info["gf"] * 1.28 * 0.47 * 3.67
    return round(yearly_kg * tree_count, 2)

def calculate_tree_age(date_string):
    try:
        planted = datetime.datetime.strptime(date_string, "%Y-%m-%d").date()
        today = datetime.date.today()
        diff = relativedelta(today, planted)
        if diff.years == 0 and diff.months == 0 and diff.days <= 0:
            return "Planted Today"
        labels = []
        if diff.years > 0: labels.append(f"{diff.years} yr" + ("s" if diff.years > 1 else ""))
        if diff.months > 0: labels.append(f"{diff.months} mo" + ("s" if diff.months > 1 else ""))
        if diff.days > 0 and len(labels) < 2: labels.append(f"{diff.days} day" + ("s" if diff.days > 1 else ""))
        return " ".join(labels) if labels else "Just started"
    except ValueError:
        return "Unknown timeline"

def generate_smart_recommendations(df):
    if df.empty or df["qty_planted"].sum() == 0:
        return ["No tree data recorded yet. Submit a planting record to generate analytics."]
    summary = df.groupby("tree_species").agg({"qty_planted": "sum", "qty_survived": "sum"})
    summary = summary[summary["qty_planted"] > 0]
    if summary.empty:
        return ["Not enough data to generate recommendations yet."]
    summary["rate"] = summary["qty_survived"] / summary["qty_planted"] * 100
    msgs = []
    top = summary["rate"].idxmax()
    msgs.append(f"🌱 **Top performer:** *{top}* leads with **{summary['rate'].max():.1f}%** survival.")
    weak = summary["rate"].idxmin()
    if weak != top:
        msgs.append(f"⚠️ **Needs attention:** *{weak}* is at **{summary['rate'].min():.1f}%** — "
                    f"consider extra watering, shade, or replacement stock.")
    return msgs


# ==============================================================================
# 8. DATA RETRIEVAL + INSPECTION RECONCILIATION
# ==============================================================================
def fetch_complete_green_dataset():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT e.event_id, e.created_by, e.institution_name, e.state_name, e.lga_name,
               e.planting_date, e.latitude, e.longitude, e.gps_accuracy, e.evidence_links,
               b.item_id, b.tree_species, b.qty_planted, b.qty_survived
        FROM events e
        JOIN batch_items b ON e.event_id = b.event_id
    """, conn)
    conn.close()
    return df

def fetch_latest_checkpoints():
    """Most recent inspection PER SPECIES ROW (item_id). MAX(checkpoint_id) is a
    reliable 'latest' marker because the id is monotonic."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT c.item_id, c.qty_alive, c.inspection_date
        FROM checkpoints c
        JOIN (SELECT item_id, MAX(checkpoint_id) AS max_id
              FROM checkpoints GROUP BY item_id) latest
        ON c.checkpoint_id = latest.max_id
    """, conn)
    conn.close()
    return df

def apply_inspection_survival(df):
    """Exact reconciliation: each species row takes its latest inspection's
    alive-count if one exists, else the original survived count. No estimation."""
    df = df.copy()
    latest = fetch_latest_checkpoints()
    alive_map = dict(zip(latest["item_id"], latest["qty_alive"])) if not latest.empty else {}
    df["effective_survived"] = df.apply(
        lambda r: int(alive_map.get(r["item_id"], r["qty_survived"])), axis=1)
    return df


# ==============================================================================
# 9. AUTH GATE
# ==============================================================================
setup_application_tables()

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

def login_screen():
    st.title("🌱 EcoTrack — Green Schools Innovation")
    st.caption("Track tree-planting and survival across all 36 states + FCT of Nigeria.")
    tab_login, tab_register = st.tabs(["🔑 Log In", "📝 Register"])

    with tab_login:
        st.subheader("Welcome back")
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                user = authenticate(u.strip(), p)
                if user:
                    st.session_state.auth_user = user
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        st.caption("First time here? Use the **Register** tab to create your account.")

    with tab_register:
        st.subheader("Create your individual account")
        full_name = st.text_input("Full name", key="reg_name")
        col_a, col_b = st.columns(2)
        username = col_a.text_input("Choose a username", key="reg_user")
        email = col_b.text_input("Email", key="reg_email")
        col_c, col_d = st.columns(2)
        password = col_c.text_input("Password", type="password", key="reg_pw")
        password2 = col_d.text_input("Confirm password", type="password", key="reg_pw2")

        st.markdown("**Your institution / group**")
        col_e, col_f = st.columns(2)
        institution_name = col_e.text_input("Institution or group name", key="reg_inst")
        institution_type = col_f.selectbox("Type", INSTITUTION_TYPES, key="reg_insttype")
        role = st.selectbox("Role", ROLES,
                            help="Inspectors and Admins can log follow-up audits.", key="reg_role")

        st.markdown("**Where are you based?**")
        home_state, home_lga = state_lga_picker("reg")

        if st.button("Create Account", type="primary"):
            if not all([full_name.strip(), username.strip(), email.strip(), password]):
                st.error("Please fill in name, username, email and password.")
            elif password != password2:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, msg = register_user(username.strip(), email.strip(), full_name.strip(),
                                        password, role, institution_name.strip(),
                                        institution_type, home_state, home_lga)
                st.success(msg) if ok else st.error(msg)

if st.session_state.auth_user is None:
    login_screen()
    st.stop()

USER = st.session_state.auth_user
IS_INSPECTOR = USER["role"] in ("Inspector", "Admin")


# ==============================================================================
# 10. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/sprout.png", width=54)
    st.title("EcoTrack Hub")
    st.caption("Green Schools Innovation System")
    st.divider()
    st.markdown(f"👤 **{USER['full_name']}**")
    st.caption(f"{USER['role']} · {USER.get('institution_name') or '—'}")
    if st.button("Log out"):
        st.session_state.auth_user = None
        st.rerun()
    st.divider()
    active_screen = st.radio("Navigate to:", [
        "1. Record Planting",
        "2. Inspections & Audits",
        "3. Live Green Dashboard",
        "4. Leaderboards",
    ])


# ==============================================================================
# SCREEN 1: RECORD PLANTING
# ==============================================================================
if active_screen == "1. Record Planting":
    st.title("🌳 Record a Planting Campaign")

    if "temp_trees" not in st.session_state:
        st.session_state.temp_trees = []

    try:
        from streamlit_geolocation import streamlit_geolocation
        HAS_GEO = True
    except ImportError:
        HAS_GEO = False

    with st.expander("📍 GPS Verification", expanded=True):
        if HAS_GEO:
            st.caption("Tap the marker to capture this site's real coordinates.")
            loc = streamlit_geolocation()
            if loc and loc.get("latitude") is not None:
                st.session_state.gps_lat = float(loc["latitude"])
                st.session_state.gps_lon = float(loc["longitude"])
                st.session_state.gps_acc = float(loc.get("accuracy") or 0.0)
        else:
            st.caption("Install `streamlit-geolocation` for one-tap capture, "
                       "or type the coordinates for this site manually.")
        c1, c2, c3 = st.columns(3)
        lat = c1.number_input("Latitude", value=float(st.session_state.get("gps_lat", 9.0820)), format="%.6f")
        lon = c2.number_input("Longitude", value=float(st.session_state.get("gps_lon", 8.6753)), format="%.6f")
        acc = c3.number_input("GPS accuracy (m)", value=float(st.session_state.get("gps_acc", 0.0)), format="%.1f")

    st.subheader("➕ Add Trees")
    sp_df = pd.DataFrame.from_dict(TREE_DATABASE, orient="index").reset_index().rename(columns={"index": "name"})
    categories = sorted(sp_df["type"].unique())
    cat = st.selectbox("Filter by category", categories)
    choices = sorted(sp_df[sp_df["type"] == cat]["name"].tolist())

    with st.form("add_tree_form", clear_on_submit=False):
        a, b, c = st.columns([2, 1, 1])
        variety = a.selectbox("Variety", choices)
        planted = b.number_input("Planted", min_value=1, value=10, step=1)
        survived = c.number_input("Currently living", min_value=0, value=10, step=1)
        if st.form_submit_button("Add to list"):
            if survived > planted:
                st.error("Living count cannot exceed planted count.")
            else:
                st.session_state.temp_trees.append(
                    {"variety": variety, "planted": planted, "survived": survived})
                st.success(f"Added {variety}.")

    if st.session_state.temp_trees:
        st.markdown("#### Current batch")
        st.dataframe(pd.DataFrame(st.session_state.temp_trees), use_container_width=True, hide_index=True)
        if st.button("Clear batch"):
            st.session_state.temp_trees = []
            st.rerun()

    st.subheader("📋 Submission Details")
    ev_state, ev_lga = state_lga_picker("event",
                                        default_state=USER.get("home_state"),
                                        default_lga=USER.get("home_lga"))
    with st.form("final_form"):
        plant_date = st.date_input("Date planted (backdate allowed)", max_value=datetime.date.today())
        inst = st.text_input("Institution / group for this project", value=USER.get("institution_name") or "")
        photos = st.file_uploader("Upload proof photos", accept_multiple_files=True)
        if st.form_submit_button("🔒 Save & Submit Report"):
            if not st.session_state.temp_trees:
                st.error("Add at least one tree variety first.")
            else:
                saved = []
                if photos:
                    stamp = int(datetime.datetime.now().timestamp())
                    for f in photos:
                        dest = os.path.join(UPLOAD_DIR, f"{stamp}_{f.name}")
                        with open(dest, "wb") as out:
                            out.write(f.getbuffer())
                        saved.append(dest)
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""INSERT INTO events
                    (created_by,institution_name,state_name,lga_name,planting_date,
                     latitude,longitude,gps_accuracy,device_info,evidence_links,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (USER["username"], inst.strip(), ev_state, ev_lga, str(plant_date),
                     lat, lon, acc, "EcoTrack Web", json.dumps(saved),
                     datetime.datetime.now().isoformat(timespec="seconds")))
                eid = cur.lastrowid
                cur.executemany(
                    "INSERT INTO batch_items (event_id,tree_species,qty_planted,qty_survived) VALUES (?,?,?,?)",
                    [(eid, t["variety"], t["planted"], t["survived"]) for t in st.session_state.temp_trees])
                conn.commit()
                conn.close()
                st.success(f"🎉 Project #{eid} saved in {ev_lga}, {ev_state}.")
                st.session_state.temp_trees = []


# ==============================================================================
# SCREEN 2: INSPECTIONS & AUDITS (per species)
# ==============================================================================
elif active_screen == "2. Inspections & Audits":
    st.title("🛡️ Inspections & Audits")
    if not IS_INSPECTOR:
        st.warning("Only **Inspector** or **Admin** accounts can log audits. "
                   "You can still view projects below.")

    data = fetch_complete_green_dataset()
    if data.empty:
        st.info("No projects recorded yet.")
    else:
        projects = data[["event_id", "created_by", "institution_name", "state_name",
                         "lga_name", "planting_date"]].drop_duplicates()
        projects["age"] = projects["planting_date"].apply(calculate_tree_age)
        opts = {r["event_id"]: f"#{r['event_id']} · {r['institution_name'] or r['created_by']} "
                                f"· {r['lga_name']}, {r['state_name']} · {r['age']}"
                for _, r in projects.iterrows()}
        eid = st.selectbox("Select a project", list(opts.keys()), format_func=lambda x: opts[x])

        rows = data[data["event_id"] == eid]
        meta = projects[projects["event_id"] == eid].iloc[0]
        st.markdown(f"**Logged by:** {meta['created_by']}  ·  "
                    f"**Planted:** {meta['planting_date']} (`{meta['age']}`)")

        conn = get_connection()
        hist = pd.read_sql_query(
            "SELECT tree_species,interval_months,qty_alive,qty_dead,inspection_date,inspector "
            "FROM checkpoints WHERE event_id=? ORDER BY checkpoint_id DESC", conn, params=(int(eid),))
        conn.close()
        if not hist.empty:
            st.markdown("#### 🗂️ Inspection history")
            st.dataframe(hist.rename(columns={
                "tree_species": "Species", "interval_months": "Milestone", "qty_alive": "Alive",
                "qty_dead": "Dead", "inspection_date": "Date", "inspector": "Inspector"}),
                hide_index=True, use_container_width=True)

        if IS_INSPECTOR:
            st.markdown("### 📝 Log a new inspection (per species)")
            with st.form("audit_form"):
                milestone = st.selectbox("Milestone",
                    ["1 Month", "3 Months", "6 Months", "12 Months", "24 Months"])
                st.caption("Enter current alive / dead counts for each species:")
                entries = []
                for _, r in rows.iterrows():
                    st.markdown(f"**{r['tree_species']}**  (planted {r['qty_planted']})")
                    ca, cd = st.columns(2)
                    alive = ca.number_input(f"Alive — {r['tree_species']}", min_value=0,
                                            value=int(r["qty_survived"]), step=1, key=f"al_{r['item_id']}")
                    dead = cd.number_input(f"Dead — {r['tree_species']}", min_value=0,
                                           value=0, step=1, key=f"dd_{r['item_id']}")
                    entries.append((int(r["item_id"]), r["tree_species"], alive, dead))
                if st.form_submit_button("Save inspection"):
                    today = str(datetime.date.today())
                    conn = get_connection()
                    conn.executemany(
                        """INSERT INTO checkpoints
                           (event_id,item_id,tree_species,interval_months,qty_alive,qty_dead,
                            inspection_date,inspector)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        [(int(eid), iid, sp, milestone, al, dd, today, USER["full_name"])
                         for iid, sp, al, dd in entries])
                    conn.commit()
                    conn.close()
                    st.success("Inspection saved — live numbers now reflect these counts.")
                    st.rerun()


# ==============================================================================
# SCREEN 3: LIVE DASHBOARD
# ==============================================================================
elif active_screen == "3. Live Green Dashboard":
    st.title("📊 National Green Dashboard")
    base = fetch_complete_green_dataset()
    if base.empty:
        st.info("Dashboard is empty — record a planting to begin.")
    else:
        base = apply_inspection_survival(base)
        base["co2_kg"] = base.apply(
            lambda r: calculate_carbon_absorbed(r["tree_species"], r["effective_survived"]), axis=1)

        with st.expander("🎛️ Filters", expanded=True):
            f1, f2 = st.columns(2)
            present_states = sorted(base["state_name"].unique())
            sel_states = f1.multiselect("State", present_states, default=present_states)
            sel_trees = f2.multiselect("Species", sorted(base["tree_species"].unique()),
                                       default=sorted(base["tree_species"].unique()))
        view = base[base["state_name"].isin(sel_states) & base["tree_species"].isin(sel_trees)]

        if view.empty:
            st.warning("No records match the current filters.")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Saplings planted", f"{view['qty_planted'].sum():,}")
            m2.metric("Verified living trees", f"{view['effective_survived'].sum():,}")
            m3.metric("CO₂ absorbed (kg/yr)", f"{view['co2_kg'].sum():,.1f}")
            st.caption("Living counts reflect the most recent inspection per species where one exists.")

            st.subheader("💡 Smart Recommendations")
            rec = view.copy()
            rec["qty_survived"] = rec["effective_survived"]
            for line in generate_smart_recommendations(rec):
                st.markdown(f"- {line}")

            st.subheader("🌍 By state")
            by_state = view.groupby("state_name").agg(
                Planted=("qty_planted", "sum"),
                Living=("effective_survived", "sum"),
                CO2_kg=("co2_kg", "sum")).reset_index().rename(columns={"state_name": "State"})
            st.dataframe(by_state, use_container_width=True, hide_index=True)

            st.subheader("🗺️ Project map")
            pts = view[["latitude", "longitude"]].dropna().rename(columns={"latitude": "lat", "longitude": "lon"})
            if not pts.empty:
                st.map(pts, use_container_width=True)


# ==============================================================================
# SCREEN 4: LEADERBOARDS
# ==============================================================================
elif active_screen == "4. Leaderboards":
    st.title("🏆 Green Champions Leaderboard")
    base = fetch_complete_green_dataset()
    if base.empty:
        st.info("Standings appear once participants submit data.")
    else:
        base = apply_inspection_survival(base)
        view = st.radio("Rank by:", ["Institution", "Individual"], horizontal=True)
        group_col = "institution_name" if view == "Institution" else "created_by"
        base[group_col] = base[group_col].fillna("—").replace("", "—")

        lb = base.groupby(group_col).agg(
            Planted=("qty_planted", "sum"),
            Living=("effective_survived", "sum"),
            Projects=("event_id", "nunique")).reset_index()
        lb["Survival %"] = (lb["Living"] / lb["Planted"] * 100).round(1)
        lb["Impact Score"] = (lb["Living"] * 0.6 + lb["Survival %"] * 0.4).round(1)
        lb = lb.sort_values("Impact Score", ascending=False).reset_index(drop=True)
        lb.index += 1
        st.dataframe(lb.rename(columns={group_col: view}), use_container_width=True)
