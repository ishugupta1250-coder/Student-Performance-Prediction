import streamlit as st
import pandas as pd
import os
from io import BytesIO
from reportlab.platypus 
import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Student Portal", layout="wide")

FILE_NAME = "student_performance.xlsx"
LOGIN_IMAGE = "portal_image.png"

# =========================
# DATA FUNCTIONS
# =========================
def load_data():
    if not os.path.exists(FILE_NAME):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    xls = pd.ExcelFile(FILE_NAME)

    df_students = pd.read_excel(FILE_NAME, sheet_name="Students_Data") if "Students_Data" in xls.sheet_names else pd.DataFrame()
    df_users = pd.read_excel(FILE_NAME, sheet_name="Users") if "Users" in xls.sheet_names else pd.DataFrame()
    df_preds = pd.read_excel(FILE_NAME, sheet_name="Predictions") if "Predictions" in xls.sheet_names else pd.DataFrame(columns=["Student_ID","Predicted_Result"])

    return df_students, df_users, df_preds


def save_data(s, u, p):
    with pd.ExcelWriter(FILE_NAME, engine="openpyxl") as writer:
        s.to_excel(writer, sheet_name="Students_Data", index=False)
        u.to_excel(writer, sheet_name="Users", index=False)
        p.to_excel(writer, sheet_name="Predictions", index=False)


# =========================
# LOGIC FUNCTIONS
# =========================
def calculate_performance(att, marks, assign, study):
    return (marks * 0.4) + (assign * 0.3) + (att * 0.2) + (study * 2)


def add_ranking(df):
    df = df.copy()
    df["Rank"] = df["Performance_Index"].rank(ascending=False, method="dense")
    return df


# =========================
# PDF GENERATOR
# =========================
def generate_pdf(row):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph("STUDENT REPORT CARD", styles['Title']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Name: {row['Name']}", styles['Normal']))
    elements.append(Paragraph(f"ID: {row['Student_ID']}", styles['Normal']))
    elements.append(Spacer(1, 12))

    data = [
        ["Metric", "Value"],
        ["Attendance", f"{row['Attendence']}%"],
        ["Marks", row["Internal_Marks"]],
        ["Assignment", row["Assignment_Score"]],
        ["Study Hours", row["Study_Hours"]],
        ["Performance Index", round(row["Performance_Index"], 2)],
        ["Result", row["Final_Result"]]
    ]

    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.blue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


# =========================
# LOAD DATA
# =========================
df_students, df_users, df_preds = load_data()

if "login" not in st.session_state:
    st.session_state.login = False


# =========================
# LOGIN PAGE WITH IMAGE
# =========================
if not st.session_state.login:

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.title("🎓Student Portal")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            match = df_users[
                (df_users["Username"].astype(str) == username) &
                (df_users["Password"].astype(str) == password)
            ]

            if not match.empty:
                st.session_state.login = True
                st.session_state.role = match.iloc[0]["Role"].lower()
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Invalid Login")

    with col2:
        if os.path.exists(LOGIN_IMAGE):
            st.image(LOGIN_IMAGE, use_container_width=True)

# =========================
# MAIN APP
# =========================
else:

    role = st.session_state.role
    user = st.session_state.user

    # Sidebar
    with st.sidebar:
        st.success(f"👋 {user}")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    # ================= ADMIN =================
    if role == "admin":
        st.title("🛡️ Admin Dashboard")

        tab1, tab2 = st.tabs(["➕ Add Student", "🗑️ Delete Student"])

        # ADD STUDENT
        with tab1:
            with st.form("add_student"):
                c1, c2 = st.columns(2)

                sid = c1.text_input("Student ID")
                name = c2.text_input("Name")

                att = c1.slider("Attendance", 0, 100, 80)
                marks = c2.number_input("Marks", 0, 100, 50)

                assign = c1.number_input("Assignment Score", 0, 100, 50)
                study = c2.slider("Study Hours", 0, 12, 5)

                result = st.selectbox("Final Result", ["Pass", "Fail"])

                if st.form_submit_button("Add Student"):

                    perf = calculate_performance(att, marks, assign, study)

                    new_student = pd.DataFrame([{
                        "Student_ID": sid,
                        "Name": name,
                        "Attendence": att,
                        "Internal_Marks": marks,
                        "Assignment_Score": assign,
                        "Study_Hours": study,
                        "Final_Result": result,
                        "Performance_Index": perf
                    }])

                    df_students = pd.concat([df_students, new_student], ignore_index=True)

                    # create login for student
                    new_user = pd.DataFrame([{
                        "Username": sid,
                        "Password": "123",
                        "Role": "student"
                    }])

                    df_users = pd.concat([df_users, new_user], ignore_index=True)

                    # prediction sheet
                    new_pred = pd.DataFrame([{
                        "Student_ID": sid,
                        "Predicted_Result": result
                    }])

                    df_preds = pd.concat([df_preds, new_pred], ignore_index=True)

                    save_data(df_students, df_users, df_preds)

                    st.success("✅ Student Added Successfully")
                    st.rerun()

        # DELETE STUDENT
        with tab2:
            st.dataframe(df_students)

            del_id = st.text_input("Enter Student ID")

            if st.button("Delete"):
                df_students = df_students[df_students["Student_ID"].astype(str) != del_id]
                df_users = df_users[df_users["Username"].astype(str) != del_id]
                df_preds = df_preds[df_preds["Student_ID"].astype(str) != del_id]

                save_data(df_students, df_users, df_preds)

                st.warning("Deleted Successfully")
                st.rerun()

    # ================= TEACHER =================
    elif role == "teacher":
        st.title("👨‍🏫 Teacher Dashboard")

        if not df_students.empty:

            df_students = add_ranking(df_students)

            st.metric("Total Students", len(df_students))

            topper = df_students.loc[df_students["Performance_Index"].idxmax()]
            lowest = df_students.loc[df_students["Performance_Index"].idxmin()]

            st.success(f"🏆 Topper: {topper['Name']}")
            st.error(f"⚠️ Lowest: {lowest['Name']}")

            st.subheader("📊 Ranking Table")
            st.dataframe(df_students.sort_values("Rank"))

            st.bar_chart(df_students.set_index("Name")["Performance_Index"])

            # COMPARE
            st.subheader("🔍 Compare Students")

            names = df_students["Name"].tolist()
            s1 = st.selectbox("Student 1", names)
            s2 = st.selectbox("Student 2", names)

            if s1 and s2:
                d1 = df_students[df_students["Name"] == s1].iloc[0]
                d2 = df_students[df_students["Name"] == s2].iloc[0]

                comp = pd.DataFrame({
                    "Metric": ["Marks", "Attendance", "Assignment", "Study Hours", "Performance"],
                    s1: [d1["Internal_Marks"], d1["Attendence"], d1["Assignment_Score"], d1["Study_Hours"], d1["Performance_Index"]],
                    s2: [d2["Internal_Marks"], d2["Attendence"], d2["Assignment_Score"], d2["Study_Hours"], d2["Performance_Index"]]
                })

                st.dataframe(comp)

    # ================= STUDENT =================
    elif role == "student":
        st.title("🎓 My Dashboard")

        student_data = df_students[df_students["Student_ID"].astype(str) == user]

        if not student_data.empty:

            row = student_data.iloc[-1]

            st.subheader("📊 Current Performance")

            c1, c2, c3 = st.columns(3)
            c1.metric("Marks", row["Internal_Marks"])
            c2.metric("Attendance", f"{row['Attendence']}%")
            c3.metric("Performance Index", round(row["Performance_Index"], 2))

            st.progress(int(row["Attendence"]))

            st.subheader("📜 Previous Records")
            st.dataframe(student_data)

            if len(student_data) > 1:
                st.line_chart(student_data["Performance_Index"])

            pdf = generate_pdf(row)
            st.download_button("📥 Download Report", pdf, file_name="report.pdf")

        else:
            st.error("No data found")
