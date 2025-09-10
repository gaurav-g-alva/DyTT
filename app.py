import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# --- Reference timetable ---
timetable = {
    "DAY 1": ["BA(SM)", "PP(CD)", "SML(RHP)", "OE", "Project Phase-II", "Project Phase-II", ""],
    "DAY 2": ["PP(CD)", "BA(SM)", "SML(RHP)", "OE", "Project Phase-II", "Project Phase-II", ""],
    "DAY 3": ["CNS(NNS)", "BA(SM)", "SML(RHP)", "OE", "Project Phase-II", "Project Phase-II", ""],
    "DAY 4": ["PP(CD)", "CNS(NNS)", "Project", "", "SKILL LAB", "", ""],
    "DAY 5": ["PP LAB B1 & B2 (CD+HK)", "SML LAB B3 & B4 (RHP+AML)", "CNS(NNS)", "", "Project Phase-II", "", ""],
    "DAY 6": ["PP LAB B3 & B4 (CD+SKN)", "SML LAB B1 & B2 (RHP+AML)", "CNS(NNS)", "OE+", "Project Phase-II", "", ""],
}
period_labels = ["9:00–9:55", "9:55–10:50", "11:10–12:05", "12:05–1:00", "2:00–2:55", "2:55–3:50", "3:50–4:45"]
cycle_days = ["DAY 1", "DAY 2", "DAY 3", "DAY 4", "DAY 5", "DAY 6"]

# --- Streamlit UI ---
st.title("📆 Dynamic College Timetable Generator")

start_date = st.date_input("Semester Start Date", datetime(2025, 8, 4))
end_date = st.date_input("Semester End Date", datetime(2025, 12, 1))
first_day = st.selectbox("Cycle Day on Start Date", cycle_days)
govt_holidays = st.multiselect("Government Holidays", pd.date_range(start_date, end_date).strftime("%d-%m-%Y"))

generate_btn = st.button("Generate Timetable")

if generate_btn:
    records = []
    current_day = start_date
    cycle_index = cycle_days.index(first_day)

    while current_day <= end_date:
        weekday = current_day.weekday()  # Monday=0, Sunday=6
        date_str = current_day.strftime("%d-%m-%Y")

        holiday = False
        reasons = []

        # Sunday holiday
        if weekday == 6:
            holiday = True
            reasons.append("Sunday")

        # Odd Saturday holiday (1st, 3rd), except 5th
        elif weekday == 5:
            first_day_month = current_day.replace(day=1)
            sat_count = sum(1 for i in range(current_day.day) if (first_day_month + timedelta(days=i)).weekday() == 5)
            nth_saturday = sat_count + 1
            if nth_saturday % 2 == 1 and nth_saturday != 5:
                holiday = True
                reasons.append(f"{nth_saturday} Saturday")

        # Government holidays
        if date_str in govt_holidays:
            holiday = True
            reasons.append("Govt. Holiday")

        # Build record
        record = {
            "Date": date_str,
            "Weekday": current_day.strftime("%A"),
            "Cycle Day": "" if holiday else cycle_days[cycle_index % 6],
        }

        if holiday:
            reason_text = " + ".join(reasons) + " - Holiday"
            record.update({label: reason_text for label in period_labels})
        else:
            periods = timetable[cycle_days[cycle_index % 6]]
            record.update({label: slot for label, slot in zip(period_labels, periods)})
            cycle_index += 1

        records.append(record)
        current_day += timedelta(days=1)

    df = pd.DataFrame(records)

    # --- Downloadable Excel ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Timetable")
    buffer.seek(0)

    st.success("✅ Timetable generated successfully!")
    st.download_button("📥 Download Excel", data=buffer, file_name="Dynamic_Timetable.xlsx", mime="application/vnd.ms-excel")

    st.dataframe(df.head(15))  # Preview first rows
