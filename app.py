import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as _go
import glob
import os

# Set page config
st.set_page_config(
    page_title="Year 10 KS4 Performance Dashboard",
    page_icon="📊",
    layout="wide"
)

# Load and process data
@st.cache_data
def load_data():
    csv_files = glob.glob("**/*.csv", recursive=True)
    csv_files = [f for f in csv_files if not os.path.basename(f).startswith(".") and "MACOSX" not in f]
    
    dfs = []
    for f in csv_files:
        fname = os.path.basename(f)
        if "Year 10 All data" in fname:
            subject = fname.replace("Year 10 All data - ", "").replace(".csv", "").strip()
            df = pd.read_csv(f)
            df['Subject'] = subject
            
            # Clean column names
            prog_col = [c for c in df.columns if c.strip() == 'Progress'][0]
            df['Progress_num'] = pd.to_numeric(df[prog_col], errors='coerce')
            df['Attendance_num'] = pd.to_numeric(df['% Attendance'], errors='coerce')
            df['PP'] = df['Pupil Premium Indicator'].fillna('N').apply(lambda x: 'PP' if str(x).strip().upper() == 'Y' else 'Non-PP')
            df['SEN'] = df['SEN Status'].fillna('N').apply(lambda x: 'SEN' if str(x).strip().upper() in ['K', 'E', 'S', 'Y'] else 'Non-SEN')
            df['EAL_Status'] = df['EAL'].fillna('N').apply(lambda x: 'EAL' if str(x).strip().upper() == 'Y' else 'Non-EAL')
            
            # Forecasted Grade cleaning
            if 'Forecasted' in df.columns:
                df['Forecast_Grade'] = df['Forecasted'].astype(str).str.strip()
            else:
                df['Forecast_Grade'] = 'N/A'
                
            dfs.append(df)
            
    master = pd.concat(dfs, ignore_index=True)
    return master

df = load_data()

# Sidebar Filters
st.sidebar.header("🔍 Dashboard Filters")

# Tutor / Reg Group Filter
reg_groups = ['All'] + sorted([x for x in df['Reg Group'].dropna().unique() if str(x) != 'nan'])
selected_reg = st.sidebar.selectbox("Registration Group", reg_groups)

# Demographic Filters
pp_filter = st.sidebar.multiselect("Pupil Premium Status", options=['PP', 'Non-PP'], default=['PP', 'Non-PP'])
sen_filter = st.sidebar.multiselect("SEN Status", options=['SEN', 'Non-SEN'], default=['SEN', 'Non-SEN'])
eal_filter = st.sidebar.multiselect("EAL Status", options=['EAL', 'Non-EAL'], default=['EAL', 'Non-EAL'])
sex_filter = st.sidebar.multiselect("Sex", options=['M', 'F'], default=['M', 'F'])

# Apply Sidebar Filters
filtered_df = df[
    (df['PP'].isin(pp_filter)) &
    (df['SEN'].isin(sen_filter)) &
    (df['EAL_Status'].isin(eal_filter)) &
    (df['Sex'].isin(sex_filter))
]

if selected_reg != 'All':
    filtered_df = filtered_df[filtered_df['Reg Group'] == selected_reg]

# Dashboard Header
st.title("🎓 Key Stage 4 (Year 10) Interactive Dashboard")
st.markdown("Real-time progress, attendance, and subject attainment performance metrics across 20 subject areas.")

# KPI Top Cards
col1, col2, col3, col4, col5 = st.columns(5)

total_students = filtered_df['Surname Forename'].nunique()
avg_progress = filtered_df['Progress_num'].mean()
avg_attendance = filtered_df['Attendance_num'].mean()

# English & Maths 9-4/9-5 estimation
eng_maths = filtered_df[filtered_df['Subject'].isin(['English', 'Maths'])]
em_pass_94 = (eng_maths['Progress_num'] >= -1.0).mean() * 100 if len(eng_maths) > 0 else 0

col1.metric("Students Count", f"{total_students}")
col2.metric("Avg Progress Score", f"{avg_progress:+.2f}")
col3.metric("Avg Attendance", f"{avg_attendance:.1f}%")
col4.metric("Eng & Maths 9-4 Pass Est.", f"{em_pass_94:.1f}%")
col5.metric("Total Enrolments", f"{len(filtered_df)}")

st.markdown("---")

# Section 1: Subject Progress Analysis
st.subheader("📚 Subject Performance vs. FFT20 Targets")

subj_summary = filtered_df.groupby('Subject').agg(
    Avg_Progress=('Progress_num', 'mean'),
    Student_Count=('Surname Forename', 'count'),
    Avg_Attendance=('Attendance_num', 'mean')
).reset_index().sort_values(by='Avg_Progress', ascending=True)

fig_subj = px.bar(
    subj_summary,
    x='Avg_Progress',
    y='Subject',
    orientation='h',
    color='Avg_Progress',
    color_continuous_scale=['#d62728', '#f7b6d2', '#c7c7c7', '#98df8a', '#2ca02c'],
    title="Average Subgrade Progress Score (+/- FFT20 Target)",
    text_auto='.2f'
)
fig_subj.add_vline(x=0, line_dash="dash", line_color="black")
fig_subj.update_layout(height=500, coloraxis_showscale=False)
st.plotly_chart(fig_subj, use_container_width=True)

st.markdown("---")

# Section 2: Attendance vs Progress Correlation
st.subheader("📈 Attendance vs. Progress Correlation")

fig_scatter = px.scatter(
    filtered_df,
    x='Attendance_num',
    y='Progress_num',
    color='PP',
    hover_data=['Surname Forename', 'Subject', 'Reg Group'],
    labels={'Attendance_num': 'Attendance %', 'Progress_num': 'Progress Score (+/- Target)'},
    title="Attendance % vs Subject Progress Score"
)
fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray")
st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")

# Section 3: Student Search & Individual Record Explorer
st.subheader("👤 Individual Student Explorer")

student_list = sorted(filtered_df['Surname Forename'].dropna().unique())
selected_student = st.selectbox("Select a Student:", student_list)

if selected_student:
    stud_df = filtered_df[filtered_df['Surname Forename'] == selected_student]
    
    st.write(f"**Reg Group:** {stud_df['Reg Group'].iloc[0]} | **Attendance:** {stud_df['Attendance_num'].iloc[0]:.1f}% | **PP Status:** {stud_df['PP'].iloc[0]} | **SEN Status:** {stud_df['SEN Status'].iloc[0]}")
    
    st.dataframe(
        stud_df[['Subject', 'GCSE FFT 20 Target', 'Forecasted', 'Progress_num']]
        .rename(columns={'Progress_num': 'Progress (+/- Target)'}),
        use_container_width=True
    )
