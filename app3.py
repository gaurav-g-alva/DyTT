import streamlit as st
import pandas as pd
import sqlite3, hashlib, io, json
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ====================== DATABASE ======================
conn = sqlite3.connect("timetable.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT,
    password TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS timetables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)""")
conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

# ====================== AUTH ======================
def register_user(username, email, password):
    try:
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                  (username, email, hash_password(password)))
        conn.commit()
        return True
    except:
        return False

def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    if user and verify_password(password, user[3]):
        return user
    return None

# ====================== PDF EXPORT ======================
def generate_pdf(df):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, height - 40, "College Timetable")

    p.setFont("Helvetica", 8)
    x_offset, y_offset = 40, height - 80
    row_height = 15

    # Draw headers
    for i, col in enumerate(df.columns):
        p.drawString(x_offset + i*70, y_offset, str(col))

    # Draw rows
    for row_num, row in df.iterrows():
        for col_num, value in enumerate(row):
            p.drawString(x_offset + col_num*70, y_offset - row_height*(row_num+1), str(value))

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# ====================== APP STATE ======================
if "page" not in st.session_state:
    st.session_state.page = "Login"
if "user" not in st.session_state:
    st.session_state.user = None
if "timetable" not in st.session_state:
    st.session_state.timetable = None
if "generated" not in st.session_state:
    st.session_state.generated = None

# ====================== PAGE: LOGIN ======================
if st.session_state.page == "Login":
    st.title("🔑 Login / Register")

    option = st.radio("Choose Action", ["Login", "Register"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if option == "Register":
        email = st.text_input("Email")
        if st.button("Register"):
            if register_user(username, email, password):
                st.success("User registered! Please login.")
            else:
                st.error("Username already exists.")

    if option == "Login":
        if st.button("Login"):
            user = login_user(username, password)
            if user:
                st.session_state.user = user
                st.session_state.page = "Upload"
                st.rerun()
            else:
                st.error("Invalid credentials.")

# ====================== PAGE: UPLOAD/ENTER ======================
elif st.session_state.page == "Upload":
    st.title("📤 Upload or Enter Timetable")

    method = st.radio("Choose input method", ["Upload File", "Enter Manually"])

    if method == "Upload File":
        file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
        if file:
            if file.name.endswith(".csv"):
                st.session_state.timetable = pd.read_csv(file)
            else:
                st.session_state.timetable = pd.read_excel(file)
            st.success("Timetable uploaded.")
            st.dataframe(st.session_state.timetable)

    else:
        st.write("Enter timetable manually (Day wise & periods):")
        period_labels = ["9:00–9:55", "9:55–10:50", "11:10–12:05",
                         "12:05–1:00", "2:00–2:55", "2:55–3:50", "3:50–4:45"]
        cycle_days = ["DAY 1", "DAY 2", "DAY 3", "DAY 4", "DAY 5", "DAY 6"]

        manual_data = []
        for day in cycle_days:
            st.markdown(f"**{day}**")
            periods = []
            for p in period_labels:
                periods.append(st.text_input(f"{day} - {p}", key=f"{day}_{p}"))
            manual_data.append([day] + periods)

        st.session_state.timetable = pd.DataFrame(manual_data, columns=["Cycle Day"] + period_labels)

    if st.button("Next → Generate"):
        if st.session_state.timetable is not None:
            st.session_state.page = "Generate"
            st.rerun()

# ====================== PAGE: GENERATE ======================
elif st.session_state.page == "Generate":
    st.title("⚙️ Generate Timetable")

    start_date = st.date_input("Semester Start", datetime(2025,8,4))
    end_date = st.date_input("Semester End", datetime(2025,12,1))
    first_day = st.selectbox("Cycle Day on Start Date", st.session_state.timetable["Cycle Day"].tolist())
    govt_holidays = st.multiselect("Government Holidays",
                                   pd.date_range(start_date, end_date).strftime("%d-%m-%Y"))

    if st.button("Generate"):
        ref_table = st.session_state.timetable
        cycle_days = ref_table["Cycle Day"].tolist()
        period_labels = ref_table.columns[1:].tolist()

        records = []
        current_day = start_date
        cycle_index = cycle_days.index(first_day)

        while current_day <= end_date:
            weekday = current_day.weekday()
            date_str = current_day.strftime("%d-%m-%Y")

            holiday = False
            reasons = []

            # Sunday
            if weekday == 6:
                holiday = True
                reasons.append("Sunday")

            # Odd Saturday (except 5th)
            elif weekday == 5:
                first_day_month = current_day.replace(day=1)
                sat_count = sum(1 for i in range(current_day.day)
                                if (first_day_month + timedelta(days=i)).weekday() == 5)
                nth_saturday = sat_count + 1
                if nth_saturday % 2 == 1 and nth_saturday != 5:
                    holiday = True
                    reasons.append(f"{nth_saturday} Saturday")

            # Government holiday
            if date_str in govt_holidays:
                holiday = True
                reasons.append("Govt. Holiday")

            record = {
                "Date": date_str,
                "Weekday": current_day.strftime("%A"),
                "Cycle Day": "" if holiday else cycle_days[cycle_index % len(cycle_days)],
            }

            if holiday:
                reason_text = " + ".join(reasons) + " - Holiday"
                record.update({label: reason_text for label in period_labels})
            else:
                periods = ref_table.loc[ref_table["Cycle Day"] ==
                                        cycle_days[cycle_index % len(cycle_days)]].values[0][1:]
                record.update({label: slot for label, slot in zip(period_labels, periods)})
                cycle_index += 1

            records.append(record)
            current_day += timedelta(days=1)

        df = pd.DataFrame(records)
        st.session_state.generated = df

        st.success("✅ Timetable generated successfully!")
        st.dataframe(df.head(15))

        # Excel download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Timetable")
        buffer.seek(0)
        st.download_button("📥 Download Excel", data=buffer, file_name="Dynamic_Timetable.xlsx")

        # PDF download
        pdf_buffer = generate_pdf(df)
        st.download_button("📄 Download PDF", data=pdf_buffer, file_name="Dynamic_Timetable.pdf")

        # Save to DB
        if st.button("Save to Database"):
            c.execute("INSERT INTO timetables (user_id, name, data) VALUES (?, ?, ?)",
                      (st.session_state.user[0], "My Timetable", df.to_json()))
            conn.commit()
            st.success("Saved to database!")
            st.session_state.page = "Manage"
            st.rerun()

# ====================== PAGE: MANAGE ======================
elif st.session_state.page == "Manage":
    st.title("📂 Manage Saved Timetables")

    c.execute("SELECT id, name, created_at FROM timetables WHERE user_id=?", (st.session_state.user[0],))
    rows = c.fetchall()

    if not rows:
        st.info("No timetables saved yet.")
    else:
        for r in rows:
            st.write(f"📄 **{r[1]}** ({r[2]})")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Load {r[0]}"):
                    c.execute("SELECT data FROM timetables WHERE id=?", (r[0],))
                    data = pd.read_json(c.fetchone()[0])
                    st.dataframe(data)
            with col2:
                if st.button(f"Delete {r[0]}"):
                    c.execute("DELETE FROM timetables WHERE id=?", (r[0],))
                    conn.commit()
                    st.warning("Deleted.")
