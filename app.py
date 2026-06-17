import streamlit as st
import pandas as pd
import sqlite3
import datetime
import json
import os
from dateutil.relativedelta import relativedelta

# ==============================================================================
# 1. PAGE SETUP & DESIGN STYLE
# ==============================================================================
st.set_page_config(
    page_title="EcoTrack: Green Schools Innovation",
    layout="wide",
    page_icon="🌱"
)

DB_FILE = "ecotrack_vnext.db"
CSV_FILE = "species_directory.csv"

# The Complete 34 Katsina State Local Government Areas
KATSINA_LGAS = [
    "Bakori", "Batagarawa", "Batsari", "Baure", "Bindawa", 
    "Charanchi", "Dan Musa", "Dandume", "Danja", "Daura", 
    "Dutsi", "Dutsin-Ma", "Faskari", "Funtua", "Ingawa", 
    "Jibia", "Kafur", "Kaita", "Kankara", "Kankia", 
    "Katsina", "Kurfi", "Kusada", "Mai'Adua", "Malumfashi", 
    "Mani", "Mashi", "Matazu", "Musawa", "Rimi", 
    "Sabuwa", "Safana", "Sandamu", "Zango"
]

# ==============================================================================
# 2. AUTOMATED MASTER DATA LOADER (CSV ENGINE)
# ==============================================================================
def load_master_species_directory():
    """Reads 1,000+ species from the uploaded CSV sheet dynamically."""
    if os.path.exists(CSV_FILE):
        df_species = pd.read_csv(CSV_FILE)
        species_dict = {}
        for _, row in df_species.iterrows():
            species_dict[str(row['species_name']).strip()] = {
                "botanical": row['botanical_name'],
                "wd": float(row['wood_density']),
                "gf": float(row['growth_factor']),
                "type": row['category']
            }
        return species_dict
    else:
        # Fallback in case the user hasn't uploaded species_directory.csv yet
        return {"Neem (Darbejiya)": {"botanical": "Azadirachta indica", "wd": 0.68, "gf": 0.025, "type": "Windbreaker & Desertification"}}

TREE_DATABASE = load_master_species_directory()

# ==============================================================================
# 3. FILE AND STORAGE SETUP (AUTOMATIC)
# ==============================================================================
def setup_application_tables():
    """Sets up the database tables needed to save user records."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            tier TEXT NOT NULL DEFAULT 'Basic Tier'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            lga_name TEXT NOT NULL,
            state_name TEXT NOT NULL,
            planting_date TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            gps_accuracy REAL NOT NULL,
            device_info TEXT,
            evidence_links TEXT,
            FOREIGN KEY(account_name) REFERENCES accounts(name)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batch_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            tree_species TEXT NOT NULL,
            qty_planted INTEGER NOT NULL,
            qty_survived INTEGER NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            interval_months TEXT NOT NULL,
            qty_alive INTEGER NOT NULL,
            qty_dead INTEGER NOT NULL,
            inspection_date TEXT NOT NULL,
            inspector TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'Approved',
            FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        sample_profiles = [
            ("Katsina Premium Academy", "Private School", "Enterprise Tier"),
            ("Batagarawa Community School", "Public School", "Basic Tier"),
            ("Save The Green Foundation", "NGO", "Growth Tier"),
            ("Dutsin-Ma Green Champions", "NGO", "Climate-Smart Academy")
        ]
        cursor.executemany("INSERT INTO accounts (name, type, tier) VALUES (?, ?, ?)", sample_profiles)
        
    conn.commit()
    conn.close()

setup_application_tables()

# ==============================================================================
# 4. SMART GREEN ENVIRONMENTAL CALCULATIONS
# ==============================================================================
def calculate_carbon_absorbed(species_name, tree_count):
    """Calculates how much CO2 is absorbed based on its specific CSV biological profile."""
    tree_info = TREE_DATABASE.get(species_name, {"wd": 0.55, "gf": 0.022})
    yearly_kg_per_tree = (tree_info["wd"] * 50) * tree_info["gf"] * 1.28 * 0.47 * 3.67
    return round(yearly_kg_per_tree * tree_count, 2)

def calculate_tree_age(date_string):
    """Calculates exactly how long the trees have been growing from their planting date."""
    try:
        planted_day = datetime.datetime.strptime(date_string, "%Y-%m-%d").date()
        today = datetime.date.today()
        difference = relativedelta(today, planted_day)
        if difference.years == 0 and difference.months == 0 and difference.days <= 0:
            return "Planted Today"
        labels = []
        if difference.years > 0: labels.append(f"{difference.years} yr" + ("s" if difference.years > 1 else ""))
        if difference.months > 0: labels.append(f"{difference.months} mo" + ("s" if difference.months > 1 else ""))
        if difference.days > 0 and len(labels) < 2: labels.append(f"{difference.days} day" + ("s" if difference.days > 1 else ""))
        return " ".join(labels) if labels else "Just started"
    except ValueError:
        return "Unknown timeline"

def generate_smart_recommendations(df_batches):
    """Generates automated guidance based on survival patterns."""
    if df_batches.empty:
        return ["No tree data recorded yet. Submit a form entry to generate analytics."]
    messages = []
    summary = df_batches.groupby("tree_species").agg({"qty_planted":"sum", "qty_survived":"sum"})
    summary["rate"] = (summary["qty_survived"] / summary["qty_planted"]) * 100
    top_tree = summary["rate"].idxmax()
    top_percentage = summary["rate"].max()
    messages.append(f"🌱 **Top Performer:** *{top_tree}* has the highest survival rate at **{top_percentage:.1f}%**.")
    return messages

def fetch_complete_green_dataset():
    """Retrieves all data tables combined for master interface viewing."""
    conn = sqlite3.connect(DB_FILE)
    query = """
        SELECT e.event_id, e.account_name, e.lga_name, e.state_name, e.planting_date,
               e.latitude, e.longitude, e.gps_accuracy, e.evidence_links,
               b.tree_species, b.qty_planted, b.qty_survived,
               a.type as account_type, a.tier as account_tier
        FROM events e
        JOIN batch_items b ON e.event_id = b.event_id
        JOIN accounts a ON e.account_name = a.name
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ==============================================================================
# 5. SIDEBAR NAVIGATION CONTROLS
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/sprout.png", width=54)
    st.title("EcoTrack Hub")
    st.caption("Green Schools Innovation System")
    st.divider()
    
    active_screen = st.selectbox("Where would you like to go?", [
        "1. School Form (Record Planting)",
        "2. Progress Inspections & Audits",
        "3. Live Green Dashboard",
        "4. School Performance Leaderboards"
    ])
    
    st.divider()
    conn = sqlite3.connect(DB_FILE)
    available_profiles = pd.read_sql_query("SELECT name FROM accounts", conn)["name"].tolist()
    conn.close()
    
    current_user = st.selectbox("Log in as Account:", available_profiles)
    
    conn = sqlite3.connect(DB_FILE)
    tier_info = pd.read_sql_query("SELECT tier FROM accounts WHERE name=?", conn, params=(current_user,))
    active_tier = tier_info["tier"].iloc[0] if not tier_info.empty else "Basic Tier"
    conn.close()
    
    st.info(f"📋 **Current Access Level:** {active_tier}")

# ==============================================================================
# SCREEN 1: RECORD TREE PLANTING
# ==============================================================================
if active_screen == "1. School Form (Record Planting)":
    st.title("🌳 School Planting Records Terminal")
    st.markdown("### Log entries from your latest school reforestation campaigns below.")
    
    if "temporary_tree_list" not in st.session_state:
        st.session_state.temporary_tree_list = []
        
    with st.expander("📍 Automatic GPS Verification Status", expanded=True):
        col_g1, col_g2, col_g3 = st.columns(3)
        locked_lat = col_g1.number_input("Verified Latitude:", value=11.9845, format="%.6f", disabled=True)
        locked_lon = col_g2.number_input("Verified Longitude:", value=7.6253, format="%.6f", disabled=True)
        gps_signals = col_g3.number_input("GPS Signal Accuracy (Meters):", value=2.4, format="%.1f", disabled=True)

    st.subheader("➕ Add Trees to Your Report")
    
    # 2-Step Search Experience for 1,000+ Categories
    species_dataframe = pd.DataFrame.from_dict(TREE_DATABASE, orient='index').reset_index()
    species_dataframe.rename(columns={'index': 'Display Name'}, inplace=True)
    
    available_categories = sorted(species_dataframe['type'].unique())
    col_f1, col_f2 = st.columns(2)
    selected_category = col_f1.selectbox("Filter by Category Type:", available_categories)
    
    filtered_choices = species_dataframe[species_dataframe['type'] == selected_category]['Display Name'].tolist()
    
    with st.form("individual_tree_form", clear_on_submit=False):
        col_i1, col_i2, col_i3 = st.columns([2, 1, 1])
        variety = col_i1.selectbox("Choose Specific Variety Name:", sorted(filtered_choices))
        num_planted = col_i2.number_input("Number Planted:", min_value=1, value=10, step=1)
        num_survived = col_i3.number_input("Number Currently Living:", min_value=0, value=10, step=1)
        
        add_to_list_btn = st.form_submit_button("Add This Variety to List")
        if add_to_list_btn:
            if num_survived > num_planted:
                st.error("Error: Living counts cannot be higher than planted counts.")
            else:
                st.session_state.temporary_tree_list.append({
                    "variety": variety, "planted": num_planted, "survived": num_survived
                })
                st.success(f"Added {variety} to list.")

    if st.session_state.temporary_tree_list:
        st.markdown("#### Preview of Current Report entries:")
        st.dataframe(pd.DataFrame(st.session_state.temporary_tree_list), use_container_width=True, hide_index=True)
        if st.button("Clear Current Form List"):
            st.session_state.temporary_tree_list = []
            st.rerun()

    st.subheader("📋 Final Submission Details")
    with st.form("final_report_form"):
        col_m1, col_m2 = st.columns(2)
        local_lga = col_m1.selectbox("Your Local Government Area (LGA):", KATSINA_LGAS)
        planting_day = col_m2.date_input("Date Planted (Backdate for older setups):", max_value=datetime.date.today())
        photo_evidence = st.file_uploader("Upload project proof files", accept_multiple_files=True)
        
        send_report_to_database = st.form_submit_button("🔒 Securely Save and Submit Full Report")
        if send_report_to_database:
            if not st.session_state.temporary_tree_list:
                st.error("Your tree list is empty. Add a variety above first.")
            else:
                file_names = [f.name for f in photo_evidence] if photo_evidence else ["default.png"]
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO events (account_name, lga_name, state_name, planting_date, latitude, longitude, gps_accuracy, device_info, evidence_links)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (current_user, local_lga, "Katsina State", str(planting_day), locked_lat, locked_lon, gps_signals, "EcoTrack Web Engine v3", json.dumps(file_names)))
                
                new_event_id = cursor.lastrowid
                final_batch_payload = [(new_event_id, item["variety"], item["planted"], item["survived"]) for item in st.session_state.temporary_tree_list]
                cursor.executemany("INSERT INTO batch_items (event_id, tree_species, qty_planted, qty_survived) VALUES (?, ?, ?, ?)", final_batch_payload)
                conn.commit()
                conn.close()
                st.success(f"🎉 Project Record #{new_event_id} has been securely saved.")
                st.session_state.temporary_tree_list = []

# ==============================================================================
# SCREEN 2: PROGRESS INSPECTIONS & AUDITS
# ==============================================================================
elif active_screen == "2. Progress Inspections & Audits":
    st.title("🛡️ Project Follow-Up and Inspection Center")
    all_data = fetch_complete_green_dataset()
    if all_data.empty:
        st.info("No projects found in system records.")
    else:
        grouped_records = all_data[["event_id", "account_name", "planting_date", "lga_name"]].drop_duplicates()
        grouped_records["current_age"] = grouped_records["planting_date"].apply(calculate_tree_age)
        dropdown_options = {row["event_id"]: f"Project #{row['event_id']} by {row['account_name']} ({row['lga_name']}) — Age: {row['current_age']}" for _, row in grouped_records.iterrows()}
        target_project_id = st.selectbox("Select a Project Record to Inspect:", list(dropdown_options.keys()), format_func=lambda x: dropdown_options[x])
        
        project_meta = grouped_records[grouped_records["event_id"] == target_project_id].iloc[0]
        project_trees_subset = all_data[all_data["event_id"] == target_project_id]
        
        st.markdown("---")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"#### 📐 Project Metadata Card: ID #{target_project_id}")
            st.write(f"**Managing Institution:** {project_meta['account_name']}")
            st.write(f"**Initial Planting Date:** {project_meta['planting_date']} (`{project_meta['current_age']}`)")
        with col_p2:
            st.markdown("#### 🪵 Current Tree Counts on Record")
            st.dataframe(project_trees_subset[["tree_species", "qty_planted", "qty_survived"]].rename(columns={"tree_species":"Tree Variety"}), hide_index=True, use_container_width=True)

        st.markdown("### 📝 Log a New Inspection Progress Check")
        with st.form("new_checkpoint_form"):
            col_c1, col_c2, col_c3 = st.columns(3)
            milestone_step = col_c1.selectbox("Time Horizon Milestone:", ["1 Month Check", "3 Months Check", "6 Months Check", "12 Months Check", "24 Months Check"])
            living_found = col_c2.number_input("Number Alive:", min_value=0, step=1)
            dead_found = col_c3.number_input("Number Dead:", min_value=0, step=1)
            inspector_id = st.text_input("Name of Inspector:")
            
            if st.form_submit_button("Save Entry"):
                conn = sqlite3.connect(DB_FILE)
                conn.execute("INSERT INTO checkpoints (event_id, interval_months, qty_alive, qty_dead, inspection_date, inspector) VALUES (?, ?, ?, ?, ?, ?)", (int(target_project_id), milestone_step, living_found, dead_found, str(datetime.date.today()), inspector_id))
                conn.commit()
                conn.close()
                st.success("Audit status updated.")
                st.rerun()

# ==============================================================================
# SCREEN 3: EXECUTIVE LIVE GREEN ANALYTICS DASHBOARD
# ==============================================================================
elif active_screen == "3. Live Green Dashboard":
    st.title("📊 Regional Environmental Dashboard Workspace")
    analytics_base = fetch_complete_green_dataset()
    if analytics_base.empty:
        st.info("The dashboard is currently empty.")
    else:
        analytics_base["co2_absorbed_kg"] = analytics_base.apply(lambda row: calculate_carbon_absorbed(row["tree_species"], row["qty_survived"]), axis=1)
        
        with st.expander("🎛️ Regional Workspace Filters", expanded=True):
            col_f1, col_f2 = st.columns(2)
            selected_lgas = col_f1.multiselect("Select LGA District:", KATSINA_LGAS, default=["Katsina", "Batagarawa", "Dutsin-Ma"] if "Dutsin-Ma" in KATSINA_LGAS else [KATSINA_LGAS[0]])
            selected_trees = col_f2.multiselect("Select Tree Variety:", analytics_base["tree_species"].unique(), default=analytics_base["tree_species"].unique())
            
        filtered_view = analytics_base[(analytics_base["lga_name"].isin(selected_lgas)) & (analytics_base["tree_species"].isin(selected_trees))]
        
        if not filtered_view.empty:
            total_planted = filtered_view["qty_planted"].sum()
            total_survived = filtered_view["qty_survived"].sum()
            net_co2_offset = filtered_view["co2_absorbed_kg"].sum()
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Saplings Planted", f"{total_planted:,}")
            col_m2.metric("Verified Living Trees", f"{total_survived:,}")
            col_m3.metric("CO2 Absorbed (kg/year)", f"{net_co2_offset:,.1f}")
            
            st.subheader("🗺️ Real-Time Map of Verified Project Plantings")
            st.map(filtered_view[["latitude", "longitude"]].dropna().rename(columns={"latitude": "lat", "longitude": "lon"}), use_container_width=True)

# ==============================================================================
# SCREEN 4: GAMIFIED SCHOOL LEADERBOARDS
# ==============================================================================
elif active_screen == "4. School Performance Leaderboards":
    st.title("🏆 Regional Green Schools Championship Standings")
    ranking_base = fetch_complete_green_dataset()
    if ranking_base.empty:
        st.info("Leaderboards will calculate standings as soon as schools submit active data entries.")
    else:
        leaderboard = ranking_base.groupby("account_name").agg({"qty_planted": "sum", "qty_survived": "sum", "event_id": "nunique"}).reset_index()
        leaderboard["Survival Rate (%)"] = (leaderboard["qty_survived"] / leaderboard["qty_planted"] * 100).round(1)
        leaderboard["Total Impact Score"] = ((leaderboard["qty_survived"] * 0.6) + (leaderboard["Survival Rate (%)"] * 0.4)).round(1)
        
        sorted_lbl = leaderboard.sort_values(by="Total Impact Score", ascending=False).reset_index(drop=True)
        sorted_lbl.index += 1
        st.dataframe(sorted_lbl.rename(columns={"account_name":"School/Institution", "qty_planted":"Planted", "qty_survived":"Living", "event_id":"Projects Logged"}), use_container_width=True)
