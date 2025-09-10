import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

st.title("📆 Dynamic College Timetable Generator")

# --- Step 1: Choose Input Method ---
input_method = st.radio("Choose how to provide the timetable:", 
                        ["📤 Upload Excel/CSV", "⌨️ Enter Manually"])

ref_table = None

if input_method == "📤 Upload Excel/CSV":
    st.subheader("Upload Reference Timetable")
    file = st.file_uploader("Upload Timetable File", type=["xlsx", "csv"])
    if file:
        if file.name.endswith(".csv"):
            ref_table = pd.read_csv(file)
        else:
            ref_table = pd.read_excel(file)
        st.success("✅ Timetable uploaded successfully!")
        st.dataframe(ref_table)

elif input_method == "⌨️ Enter Manually":
    st.subheader("Enter Reference Timetable (Cycle Day Wise)")
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

    ref_table = pd.DataFrame(manual_data, columns=["Cycle Day"] + period_labels)
    st.success("✅ Timetable entered successfully!")
    st.dataframe(ref_table)

# --- Step 2: Generate Timetable if reference is ready ---
if ref_table is not None:
    cycle_days = ref_table["Cycle Day"].tolist()
    period_labels = ref_table.columns[1:].tolist()

    st.subheader("Semester Details")
    start_date = st.date_input("Semester Start Date", datetime(2025, 8, 4))
    end_date = st.date_input("Semester End Date", datetime(2025, 12, 1))
    first_day = st.selectbox("Cycle Day on Start Date", cycle_days)
    govt_holidays = st.multiselect("Government Holidays", 
                                   pd.date_range(start_date, end_date).strftime("%d-%m-%Y"))

    if st.button("Generate Timetable"):
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
                periods = ref_table.loc[ref_table["Cycle Day"] == cycle_days[cycle_index % len(cycle_days)]].values[0][1:]
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
        st.download_button("📥 Download Excel", data=buffer, 
                           file_name="Dynamic_Timetable.xlsx", 
                           mime="application/vnd.ms-excel")

        st.dataframe(df.head(15))
