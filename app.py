import streamlit as st
import pandas as pd
import sqlite3
import datetime

# ==============================================================================
# 1. GLOBAL PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="EcoTrack: Green Schools Innovation",
    layout="wide",
    page_icon="🌱"
)

# ==============================================================================
# 2. THE COMPLETE SPECIES INTEL DATABASE (26 UNIQUE ENTRIES)
# ==============================================================================
SPECIES_DATABASE = {
    # INDIGENOUS & CLIMATE FOCUS
    "Neem (Darbejiya)": {"botanical": "Azadirachta indica", "wd": 0.68, "gf": 0.025, "type": "Climate"},
    "Acacia (Gum Arabic/Karo)": {"botanical": "Acacia senegal", "wd": 0.78, "gf": 0.022, "type": "Desert Control"},
    "Baobab (Kuka)": {"botanical": "Adansonia digitata", "wd": 0.32, "gf": 0.035, "type": "Indigenous/Climate"},
    "Tamarind (Tsamiya)": {"botanical": "Tamarindus indica", "wd": 0.85, "gf": 0.015, "type": "Fruit/Climate"},
    "Desert Date (Adua)": {"botanical": "Balanites aegyptiaca", "wd": 0.74, "gf": 0.018, "type": "Desert Control"},
    "African Locust Bean (Kalwa)": {"botanical": "Parkia biglobosa", "wd": 0.62, "gf": 0.021,
                                    "type": "Indigenous/Climate"},
    "Acacia nilotica (Bagaruwa)": {"botanical": "Vachellia nilotica", "wd": 0.80, "gf": 0.019,
                                   "type": "Desert Control"},
    "Moringa (Zogale)": {"botanical": "Moringa oleifera", "wd": 0.40, "gf": 0.045, "type": "Food/Climate"},
    "Winterthorn (Gawo)": {"botanical": "Faidherbia albida", "wd": 0.58, "gf": 0.028, "type": "Climate"},

    # FRUIT TREES
    "Mango (Mangwaro)": {"botanical": "Mangifera indica", "wd": 0.52, "gf": 0.030, "type": "Fruit"},
    "Cashew (Kashu)": {"botanical": "Anacardium occidentale", "wd": 0.50, "gf": 0.032, "type": "Fruit"},
    "Guava (Gwayaba)": {"botanical": "Psidium guajava", "wd": 0.60, "gf": 0.028, "type": "Fruit"},
    "Orange (Lemu)": {"botanical": "Citrus sinensis", "wd": 0.65, "gf": 0.020, "type": "Fruit"},
    "Date Palm (Dabino)": {"botanical": "Phoenix dactylifera", "wd": 0.45, "gf": 0.025, "type": "Fruit"},
    "Coconut Palm": {"botanical": "Cocos nucifera", "wd": 0.42, "gf": 0.028, "type": "Fruit"},
    "Sheanut (Kade)": {"botanical": "Vitellaria paradoxa", "wd": 0.70, "gf": 0.014, "type": "Fruit/Economic"},

    # TIMBER & FAST GROWTH
    "Mahogany (Savanna)": {"botanical": "Khaya senegalensis", "wd": 0.72, "gf": 0.018, "type": "Timber/Climate"},
    "African Mahogany (Rainforest)": {"botanical": "Khaya ivorensis", "wd": 0.65, "gf": 0.022,
                                      "type": "Timber/Climate"},
    "Teak": {"botanical": "Tectona grandis", "wd": 0.65, "gf": 0.024, "type": "Timber/Climate"},
    "Iroko": {"botanical": "Milicia excelsa", "wd": 0.68, "gf": 0.017, "type": "Timber/Climate"},
    "Gmelina": {"botanical": "Gmelina arborea", "wd": 0.45, "gf": 0.040, "type": "Timber/Climate"},
    "Eucalyptus": {"botanical": "Eucalyptus camaldulensis", "wd": 0.55, "gf": 0.045, "type": "Timber"},

    # ORNAMENTAL & SHADE
    "Royal Palm": {"botanical": "Roystonea regia", "wd": 0.35, "gf": 0.030, "type": "Ornamental"},
    "Flamboyant": {"botanical": "Delonix regia", "wd": 0.40, "gf": 0.035, "type": "Ornamental/Shade"},
    "Bougainvillea": {"botanical": "Bougainvillea spp.", "wd": 0.45, "gf": 0.020, "type": "Ornamental"},
    "Terminalia (Madagascar Almond)": {"botanical": "Terminalia mantaly", "wd": 0.55, "gf": 0.038,
                                       "type": "Roadside/Shade"}
}

# ==============================================================================
# 3. ROBUST DATABASE MANAGEMENT
# ==============================================================================
DB_FILE = "ecotrack_governance.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tree_audits (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT NOT NULL,
            lga_name TEXT NOT NULL,
            tree_species TEXT NOT NULL,
            trees_planted INTEGER NOT NULL,
            trees_survived INTEGER NOT NULL,
            audit_date TEXT NOT NULL,
            green_credits REAL NOT NULL,
            verification_status TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


# ==============================================================================
# 4. SCIENTIFIC CARBON ENGINE
# ==============================================================================
def calculate_carbon_impact(species_name, count):
    spec = SPECIES_DATABASE.get(species_name, {"wd": 0.55, "gf": 0.022})
    annual_kg_per_tree = (spec["wd"] * 50) * spec["gf"] * 1.28 * 0.47 * 3.67
    return round(annual_kg_per_tree * count, 2)


# ==============================================================================
# 5. SIDEBAR MANAGEMENT CONTROL & NAVIGATION
# ==============================================================================
with st.sidebar:
    st.title("EcoTrack Gateway")
    role = st.selectbox("Select Access Portal Profile:", [
        "School Portal Gate",
        "Eco-Club Resources Hub",  # <-- NEW PORTAL SECTION
        "State Auditor Command"
    ])
    st.divider()
    st.info(
        "💡 Tip: Close this sidebar using the arrow ( < ) at the top left to maximize your interactive workspace views.")

# ==============================================================================
# 6. APP ROUTING: SCHOOL ADMIN DATA ENTRY TERMINAL
# ==============================================================================
if role == "School Portal Gate":
    st.title("🌱 EcoTrack: Green Schools Innovation")
    st.markdown("### Regional School Environmental Reporting Hub")

    st.subheader("📝 Log Tree Monitoring Activity")
    with st.form("audit_form", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        school = col_f1.text_input("Official School Name:")
        lga = col_f2.selectbox("Local Government Area (LGA):", [
            "Katsina", "Dutsin-Ma", "Funtua", "Daura", "Batagarawa", "Mani", "Malumfashi", "Kaita", "Jibia", "Bakori"
        ])

        species = st.selectbox("Select Tree Species Asset Category:", sorted(list(SPECIES_DATABASE.keys())))
        st.caption(
            f"🧬 **Botanical Name:** *{SPECIES_DATABASE[species]['botanical']}* | 🌿 **Category:** {SPECIES_DATABASE[species]['type']}")

        col_n1, col_n2, col_n3 = st.columns(3)
        p_count = col_n1.number_input("Total Saplings Planted:", min_value=1, value=50)
        s_count = col_n2.number_input("Verified Living Stands Survived:", min_value=1, value=45)
        date = col_n3.date_input("Audit Collection Timestamp:", max_value=datetime.date.today())

        submit = st.form_submit_button("Transmit Metrics to Vetting Pipeline")

        if submit:
            if s_count > p_count:
                st.error("❌ Data Entry Paradox: Survived asset totals cannot exceed planted amounts.")
            else:
                impact = calculate_carbon_impact(species, s_count)
                credits = round(impact / 100, 2)

                conn = sqlite3.connect(DB_FILE)
                conn.execute("""INSERT INTO tree_audits 
                    (school_name, lga_name, tree_species, trees_planted, trees_survived, audit_date, green_credits, verification_status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                             (school, lga, species, p_count, s_count, str(date), credits, "Pending Approval"))
                conn.commit()
                conn.close()

                st.success(
                    f"🎉 Audit Data Dispatched! Estimated sequestration: **{impact:,} kg CO2e/year** (Yielding {credits} Pending Credits).")

# ==============================================================================
# 7. NEW FEATURE ROUTING: ECO-CLUB RESOURCES & ACTION PLAN HUB
# ==============================================================================
elif role == "Eco-Club Resources Hub":
    st.title("📚 Eco-Club Toolkits & Resources Center")
    st.markdown("### Empowering Student Environmental Clubs with Practical Frameworks")

    tab_templates, tab_seasonal_guide = st.tabs([
        "📋 Action Plan & Reporting Templates",
        "🌦 Climatic Care Guide"
    ])

    with tab_templates:
        st.subheader("Downloadable Club Resources")
        st.write("Equip your environmental club coordinators and students with standardized planning frameworks.")

        # 1. Action Plan Template Content Generation
        action_plan_text = """================================================================
ECOTRACK ENVIRONMENTAL CLUB: ANNUAL SCHOOL GREENING ACTION PLAN
================================================================
School Name: __________________________________
LGA Location: _________________________________
Academic Session/Year: 2026 / 2027
Club Coordinator Name: ________________________

1. TARGET SETTING
   * Target Number of Seedlings to Plant: _________
   * Chosen Primary Tree Species: _________________
   * Expected Minimum Survival Rate Target: ______ %

2. STUDENT LAND STEWARDSHIP ASSIGNMENTS
   * Team Lead for Nursery Care: __________________
   * Team Lead for Watering Schedule: ____________
   * Team Lead for Weekly Audit Counting: ________

3. STRATEGIC TIMELINES & MAINTENANCE
   * Date of Initial Soil Preparation: ___________
   * Projected Tree Planting Launch Date: _________
   * Arid Weather Protective Measures (Dry Season Care):
     ___________________________________________________________
     ___________________________________________________________

4. MONITORING LOG FRAMEWORK
   * Month 1 Count: _____ Alive | Month 3 Count: _____ Alive
   * Month 6 Count: _____ Alive | Month 12 Count: _____ Alive

Approved By Principal / Coordinator Sign-off: __________________
"""

        # 2. Club Constitution Setup Text
        constitution_text = """================================================================
STANDARD MANUAL: ECO-CLUB STRUCTURE & CONSTITUTION GUIDELINES
================================================================
1. CORE OBJECTIVE
   To foster strict environmental accountability, build active leadership skills 
   among youth, and institutionalize green governance at the grassroots local school level.

2. EXEC BOARD STRUCTURE
   - President / Climate Captain: Runs bi-weekly meetings and sets planting targets.
   - Vice President / Data Lead: Inputs survival tracking field data into EcoTrack.
   - Logistics Officer: Manages organic compost supplies, tools, and mulch storage.

3. SUSTAINABILITY COMMITMENT
   Every club member is assigned custody over specific seedling zones. Members are 
   responsible for daily watering and shielding seedlings from roaming livestock.
"""

        c1, c2 = st.columns(2)
        with c1:
            st.info("📋 **Club Activity Action Plan Template**")
            st.caption("A structured blueprint to map targets, student roles, schedules, and maintenance routines.")
            st.download_button(
                label="📥 Download Action Plan Template (TXT)",
                data=action_plan_text,
                file_name="EcoTrack_School_Action_Plan.txt",
                mime="text/plain"
            )

        with c2:
            st.info("📜 **Standard Eco-Club Constitution Manual**")
            st.caption(
                "Guidelines for structural leadership roles, responsibilities, and establishing active club branches.")
            st.download_button(
                label="📥 Download Club Structure Manual (TXT)",
                data=constitution_text,
                file_name="EcoTrack_Club_Structure_Manual.txt",
                mime="text/plain"
            )

    with tab_seasonal_guide:
        st.subheader("🌦 Interactive Localized Climate Care Guide")
        st.write(
            "Select the current local climatic window to view immediate practical steps required to maintain tree stock survival numbers:")

        season_select = st.radio("Current Weather Season Scope:",
                                 ["Dry Arid Season (Harmattan / Intense Sun)", "Wet Rainy Season"])

        if season_select == "Dry Arid Season (Harmattan / Intense Sun)":
            st.warning("⚠️ **Dry Season Maintenance Pipeline Activated (High Risk to Saplings)**")
            st.markdown("""
            * **Watering Frequencies:** Seedlings must be watered consistently every early morning (before 8:30 AM) or late evening to reduce evaporative losses.
            * **Mulching Layers:** Place dry leaves, grass, or agricultural wood waste around the base of the trunk to retain subsoil moisture.
            * **Livestock Barriers:** Construct secure bamboo or recycled wood tree guards around young saplings to block damage from roaming cattle, goats, and sheep.
            """)
        else:
            st.success("🌧️ **Wet Season Abundance Phase Activated**")
            st.markdown("""
            * **Soil Aeration:** Gently loosen waterlogged topsoil around root areas to promote proper drainage and nitrogen absorption.
            * **Weeding Controls:** Pull out competing grasses and invasive weeds within a 1-meter radius around your tree assets to ensure full sunlight exposure.
            * **Data Update:** Take clean baseline audit verification photos while growth cycles are peaking!
            """)

# ==============================================================================
# 8. APP ROUTING: STATE AUDITOR COMMAND CONSOLE
# ==============================================================================
elif role == "State Auditor Command":
    st.title("🛡️ State Auditor Control Console")
    st.markdown("### Real-Time Pipeline Verification & Validation Engine")

    conn = sqlite3.connect(DB_FILE)
    pending = pd.read_sql_query("SELECT * FROM tree_audits WHERE verification_status='Pending Approval'", conn)
    conn.close()

    if pending.empty:
        st.info("✅ The real-time review queue is completely clear. No entries are pending verification.")
    else:
        st.warning(f"⚠️ Found {len(pending)} monitoring submissions awaiting formal verification vetting.")
        st.dataframe(pending, use_container_width=True, hide_index=True)

        with st.expander("👉 Open Action Validation Drawer"):
            audit_id_to_approve = st.number_input("Enter Audit ID Target to Approve:", min_value=1, step=1)
            action_btn = st.button("Approve & Merge into Public Dashboard")

            if action_btn:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tree_audits WHERE audit_id=?", (audit_id_to_approve,))
                if cursor.fetchone() is None:
                    st.error("Target verification ID not found in relational ledger data indexes.")
                else:
                    cursor.execute("UPDATE tree_audits SET verification_status='Approved' WHERE audit_id=?",
                                   (audit_id_to_approve,))
                    conn.commit()
                    st.success(
                        f"Audit Record #{audit_id_to_approve} successfully validated and merged into analytics stream!")
                    st.rerun()
                conn.close()

# ==============================================================================
# 9. LIVE COMPREHENSIVE ANALYTICS DISPLAY PANEL
# ==============================================================================
st.divider()
st.subheader("📊 Live EcoTrack Regional Sustainability Standings")

conn = sqlite3.connect(DB_FILE)
df = pd.read_sql_query("SELECT * FROM tree_audits", conn)
conn.close()

if not df.empty and "lga_name" in df.columns:
    total_p = df["trees_planted"].sum()
    total_s = df["trees_survived"].sum()
    overall_survival_rate = (total_s / total_p * 100) if total_p > 0 else 0
    total_credits = round(df["green_credits"].sum(), 2)
    total_co2_kg = total_s * 22

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Total Planted Trees", f"{total_p:,}")
    col_m2.metric("Verified Survived Trees", f"{total_s:,} ({overall_survival_rate:.1f}%)")
    col_m3.metric("Aggregated Carbon Offset (kg/yr)", f"{total_co2_kg:,.2f}")
    col_m4.metric("Total Generated Green Credits", f"{total_credits:,}")

    tab_overview, tab_lga, tab_seasonal = st.tabs([
        "🌳 Botanical Asset Profiles",
        "🏆 LGA Sustainability Leaderboard",
        "🌦 Climatic Seasonal Patterns"
    ])

    with tab_overview:
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            st.write("#### Verified Living Trees by Botanical Common Specification")
            species_chart_df = df.groupby("tree_species")["trees_survived"].sum().sort_values(ascending=False)
            st.bar_chart(species_chart_df, color="#2E8B57")
        with col_c2:
            st.write("#### Active Ledger Sync")
            st.dataframe(df[["school_name", "tree_species", "trees_survived", "verification_status"]],
                         use_container_width=True, hide_index=True)

    with tab_lga:
        st.write("#### 🏆 Top Performing Local Government Areas (LGAs)")
        lga_chart_df = df.groupby("lga_name")["trees_survived"].sum().sort_values(ascending=False)
        st.bar_chart(lga_chart_df, color="#4C9A2A")

    with tab_seasonal:
        st.write("#### 🌦 Deployment Survival Rates split by Seasonal Windows")
        df['audit_date'] = pd.to_datetime(df['audit_date'])
        df['Season'] = df['audit_date'].dt.month.apply(
            lambda m: 'Wet Season (June-Sept)' if m in [6, 7, 8, 9] else 'Dry Season (Arid/Harmattan)')

        seasonal_summary = df.groupby('Season').agg({
            'trees_planted': 'sum',
            'trees_survived': 'sum'
        }).reset_index()
        seasonal_summary['Survival Rate (%)'] = (
                    seasonal_summary['trees_survived'] / seasonal_summary['trees_planted'] * 100).round(1)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.bar_chart(data=seasonal_summary, x='Season', y='Survival Rate (%)', color="#D2691E")
        with col_s2:
            st.dataframe(seasonal_summary, use_container_width=True, hide_index=True)
else:
    st.info(
        "The localized database file is clear. Submit your first school activity report above to initiate live analytics charts.")
