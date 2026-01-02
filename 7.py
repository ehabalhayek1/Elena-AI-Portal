import streamlit as st
from groq import Groq
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import time
import pandas as pd
import json

# --- 1. إعدادات الصفحة والتصميم ---
st.set_page_config(page_title="Elena AI | Smart Student Portal", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .course-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #4e73df;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    h1 { color: #2e59d9; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stSidebar"] { background-color: #1a1c23; color: white; }
    .stButton>button {
        border-radius: 10px;
        background-color: #4e73df;
        color: white;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #2e59d9; transform: scale(1.02); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. إعداد Groq Cloud ---
GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "courses" not in st.session_state: 
    st.session_state.courses = {}

# دالة ذكية لتنظيف وتقليص النص لتجنب خطأ BadRequest
def ask_elena_groq(user_prompt, context=""):
    # تنظيف النص: نأخذ أول 7000 حرف فقط لتجنب تجاوز حد الـ Tokens
    cleaned_context = str(context)[:7000] 
    
    system_msg = "You are Elena, a genius academic assistant. Analyze the university portal data provided. Be concise, professional, and answer in English."
    full_prompt = f"Context from Portal: {cleaned_context}\n\nUser Question: {user_prompt}"
    
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.5,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Error: The text might be too large or there is a connection issue. Details: {str(e)}"

# --- 3. المحرك التقني (Selenium) ---
def run_selenium_task(username, password, task_type="timeline", course_url=None):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass")
        time.sleep(3)
        if "sso.iugaza" in driver.current_url:
            driver.find_element(By.ID, "username").send_keys(username)
            driver.find_element(By.ID, "password").send_keys(password)
            driver.find_element(By.ID, "password").send_keys(Keys.ENTER)
        
        time.sleep(7)
        if task_type == "timeline":
            time.sleep(50) 
            body_text = driver.find_element(By.TAG_NAME, "body").text
            course_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='course/view.php?id=']")
            courses = {el.text: el.get_attribute("href") for el in course_elements if len(el.text) > 5}
            return {"text": body_text, "courses": courses}
        elif task_type == "course_deep_dive":
            driver.get(course_url)
            time.sleep(10)
            return {"text": driver.find_element(By.TAG_NAME, "body").text}
    except Exception as e: 
        return {"error": str(e)}
    finally: 
        driver.quit()

# --- 4. واجهة المستخدم ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("https://cdn-icons-png.flaticon.com/512/3449/3449692.png", width=80)
with col_title:
    st.markdown("<h1>Elena AI <span style='color:#5a5c69; font-size:20px;'>| Student Academic Hub</span></h1>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<br><h2 style='text-align:center; color:white;'>🔒 Access Portal</h2>", unsafe_allow_html=True)
    u_id = st.text_input("Student ID", placeholder="120XXXXXX")
    u_pass = st.text_input("Password", type="password", placeholder="••••••••")
    
    st.markdown("---")
    if st.button("🚀 Sync My Data"):
        with st.spinner("Logging into IUG Moodle..."):
            result = run_selenium_task(u_id, u_pass, "timeline")
            if "error" in result: 
                st.error("Login Failed")
            else:
                st.session_state.timeline_data = result['text']
                st.session_state.courses = result['courses']
                st.balloons()

tab1, tab2, tab3 = st.tabs(["📅 Daily Timeline", "🔍 Course Navigator", "💬 Ask Elena"])

with tab1:
    st.markdown("### 📋 Upcoming Deadlines & Events")
    if "timeline_data" in st.session_state:
        if st.button("✨ Smart Analysis"):
            with st.spinner("Elena is analyzing your timeline via Groq..."):
                analysis = ask_elena_groq("Summarize upcoming tasks and deadlines from this text", st.session_state.timeline_data)
                st.markdown(f"<div class='course-card'>{analysis}</div>", unsafe_allow_html=True)
    else:
        st.warning("Please login and sync your data to view the timeline.")

with tab2:
    st.markdown("### 📚 Your Registered Courses")
    if st.session_state.courses:
        selected_course = st.selectbox("Choose a subject to analyze:", list(st.session_state.courses.keys()))
        if st.button(f"📘 Deep Analysis for {selected_course}"):
            with st.spinner(f"Diving deep into {selected_course}..."):
                course_url = st.session_state.courses[selected_course]
                result = run_selenium_task(u_id, u_pass, "course_deep_dive", course_url)
                if "text" in result:
                    summary = ask_elena_groq(f"Extract core topics and notes from this course: {selected_course}", result['text'])
                    st.markdown(f"<div class='course-card'><h4>Summary for {selected_course}</h4><p>{summary}</p></div>", unsafe_allow_html=True)
    else:
        st.info("No courses found yet.")

with tab3:
    st.markdown("### 💬 AI Tutoring & Support")
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])

    if chat_input := st.chat_input("How can I help you today?"):
        st.session_state.chat_history.append({"role": "user", "content": chat_input})
        with st.chat_message("user"):
            st.markdown(chat_input)
        
        context = st.session_state.get("timeline_data", "No context available.")
        response = ask_elena_groq(chat_input, context)
        
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)
