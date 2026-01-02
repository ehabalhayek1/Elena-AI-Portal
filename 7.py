import streamlit as st
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
import json

# --- 1. إعدادات الصفحة والتصميم (The Designer Touch) ---
st.set_page_config(page_title="Elena AI | Smart Student Portal", page_icon="🎓", layout="wide")

# تصميم CSS مخصص لجعل الموقع يبدو كأنه تطبيق احترافي
st.markdown("""
    <style>
    /* تغيير الخلفية العامة */
    .stApp {
        background-color: #f8f9fa;
    }
    /* تصميم البطاقات */
    .course-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #4e73df;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    /* تصميم العناوين */
    h1 {
        color: #2e59d9;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Sidebar تصميم الـ */
    [data-testid="stSidebar"] {
        background-color: #1a1c23;
        color: white;
    }
    .stButton>button {
        border-radius: 10px;
        background-color: #4e73df;
        color: white;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #2e59d9;
        transform: scale(1.02);
    }
    </style>
    """, unsafe_allow_html=True)

# إعداد Gemini
genai.configure(api_key="AIzaSyD6iUk6Jw-HO-q_y9vA08QJFosAVI3I9ng")
if "chat_session" not in st.session_state:
    model = genai.GenerativeModel("models/gemini-flash-latest")
    st.session_state.chat_session = model.start_chat(history=[])

if "courses" not in st.session_state: st.session_state.courses = {}

# --- 2. المحرك التقني (نفس الوظائف السابقة) ---
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

def run_selenium_task(username, password, task_type="timeline", course_url=None):
    options = Options()
    # إعدادات التشغيل على السيرفر (ضرورية جداً)
    options.add_argument("--headless")  # تشغيل بدون شاشة
    options.add_argument("--no-sandbox") # للأمان داخل السيرفر
    options.add_argument("--disable-dev-shm-usage") # لتجنب مشاكل الذاكرة
    options.add_argument("--disable-gpu")
    
    # تحديد مسار الكروم في سيرفرات ستريم ليت
    options.binary_location = "/usr/bin/chromium"
    try:
        # استخدام الخدمة الافتراضية للينكس
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
            time.sleep(80) 
            timeline_text = driver.find_element(By.TAG_NAME, "body").text
            course_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='course/view.php?id=']")
            courses = {el.text: el.get_attribute("href") for el in course_elements if len(el.text) > 5}
            return {"text": timeline_text, "courses": courses}
        elif task_type == "course_deep_dive":
            driver.get(course_url)
            time.sleep(10)
            return {"text": driver.find_element(By.TAG_NAME, "body").text}
    except Exception as e: return {"error": str(e)}
    finally: driver.quit()

# --- 3. واجهة المستخدم الرسومية (Elegant UI) ---

# الهيدر العلوي
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("https://cdn-icons-png.flaticon.com/512/3449/3449692.png", width=80)
with col_title:
    st.markdown("<h1>Elena AI <span style='color:#5a5c69; font-size:20px;'>| Student Academic Hub</span></h1>", unsafe_allow_html=True)

# القائمة الجانبية بتصميم مودرن
with st.sidebar:
    st.markdown("<br><h2 style='text-align:center; color:white;'>🔒 Access Portal</h2>", unsafe_allow_html=True)
    u_id = st.text_input("Student ID", placeholder="120XXXXXX")
    u_pass = st.text_input("Password", type="password", placeholder="••••••••")
    
    st.markdown("---")
    if st.button("🚀 Sync My Data"):
        with st.spinner("Logging into IUG Moodle..."):
            result = run_selenium_task(u_id, u_pass, "timeline")
            if "error" in result: st.error("Login Failed")
            else:
                st.session_state.timeline_data = result['text']
                st.session_state.courses = result['courses']
                st.balloons()

# التبويبات بتصميم احترافي
tab1, tab2, tab3 = st.tabs(["📅 Daily Timeline", "🔍 Course Navigator", "💬 Ask Elena"])

with tab1:
    st.markdown("### 📋 Upcoming Deadlines & Events")
    if "timeline_data" in st.session_state:
        if st.button("✨ Smart Analysis"):
            with st.spinner("Elena is reading your timeline..."):
                prompt = f"Summarize upcoming tasks from this text: {st.session_state.timeline_data}"
                resp = st.session_state.chat_session.send_message(prompt)
                st.markdown(f"<div class='course-card'>{resp.text}</div>", unsafe_allow_html=True)
    else:
        st.warning("Please login and sync your data to view the timeline.")

with tab2:
    st.markdown("### 📚 Your Registered Courses")
    if st.session_state.courses:
        # عرض المواد في بطاقات أنيقة
        selected_course = st.selectbox("Choose a subject to analyze:", list(st.session_state.courses.keys()))
        
        if st.button(f"📘 Deep Analysis for {selected_course}"):
            with st.spinner(f"Diving deep into {selected_course}..."):
                course_url = st.session_state.courses[selected_course]
                result = run_selenium_task(u_id, u_pass, "course_deep_dive", course_url)
                if "text" in result:
                    summary_prompt = f"Extract core topics and notes from this course in English: {result['text']}"
                    resp = st.session_state.chat_session.send_message(summary_prompt)
                    st.markdown(f"<div class='course-card'><h4>Summary for {selected_course}</h4><p>{resp.text}</p></div>", unsafe_allow_html=True)
    else:
        st.info("No courses found yet.")

with tab3:
    st.markdown("### 💬 AI Tutoring & Support")
    # تصميم صندوق الشات
    for message in st.session_state.chat_session.history:
        with st.chat_message("assistant" if message.role == "model" else "user"):
            st.markdown(message.parts[0].text)

    if chat_input := st.chat_input("How can I help you today?"):
        with st.chat_message("user"): st.markdown(chat_input)
        context = st.session_state.get("timeline_data", "")
        response = st.session_state.chat_session.send_message(f"Context: {context}\n\nUser: {chat_input}")

        with st.chat_message("assistant"): st.markdown(response.text)
