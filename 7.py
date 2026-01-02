import streamlit as st
from groq import Groq
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import time
import re

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

# دالة تنظيف النص الجذري (تنظيف المسافات والرموز الزائدة)
def clean_text_optimized(text):
    if not text: return ""
    # إزالة الفراغات المتكررة والأسطر الفارغة
    text = re.sub(r'\s+', ' ', text)
    # أخذ قدر كافٍ للتحليل دون إرهاق الـ API (حوالي 4000 حرف صافي)
    return text[:4000]

def ask_elena_groq(user_prompt, context=""):
    cleaned_context = clean_text_optimized(context)
    
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192", # استخدمت موديل 8b لأنه أخف وأسرع للطلبات المتكررة
            messages=[
                {"role": "system", "content": "You are Elena, a professional academic assistant. Use the provided portal context to answer concisely in English."},
                {"role": "user", "content": f"Context: {cleaned_context}\n\nQuestion: {user_prompt}"}
            ],
            temperature=0.3,
            max_tokens=800
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error with AI: {str(e)}"

# --- 3. المحرك التقني (Selenium) ---
def run_selenium_task(username, password, task_type="timeline", course_url=None):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium"
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass")
        time.sleep(3)
        if "username" in driver.page_source:
            driver.find_element(By.ID, "username").send_keys(username)
            driver.find_element(By.ID, "password").send_keys(password)
            driver.find_element(By.ID, "password").send_keys(Keys.ENTER)
        
        time.sleep(10)
        if task_type == "timeline":
            time.sleep(70) 
            body_text = driver.find_element(By.TAG_NAME, "body").text
            course_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='course/view.php?id=']")
            courses = {el.text: el.get_attribute("href") for el in course_elements if len(el.text) > 3}
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
    u_pass = st.text_input("Password", type="password")
    
    if st.button("🚀 Sync My Data"):
        with st.spinner("Elena is accessing Moodle..."):
            result = run_selenium_task(u_id, u_pass, "timeline")
            if "error" in result: st.error("Sync Failed. Check credentials.")
            else:
                st.session_state.timeline_data = result['text']
                st.session_state.courses = result['courses']
                st.balloons()

tab1, tab2, tab3 = st.tabs(["📅 Timeline", "📚 Courses", "💬 Chat"])

with tab1:
    if "timeline_data" in st.session_state:
        if st.button("✨ Analyze Deadlines"):
            with st.spinner("Processing..."):
                ans = ask_elena_groq("Identify only specific upcoming tasks and dates.", st.session_state.timeline_data)
                st.markdown(f"<div class='course-card'>{ans}</div>", unsafe_allow_html=True)
    else: st.info("Sync data first.")

with tab2:
    if st.session_state.get("courses"):
        sel = st.selectbox("Select Course:", list(st.session_state.courses.keys()))
        if st.button(f"Analyze {sel}"):
            with st.spinner("Diving deep..."):
                res = run_selenium_task(u_id, u_pass, "course_deep_dive", st.session_state.courses[sel])
                if "text" in res:
                    sum_ans = ask_elena_groq(f"Summarize lectures for {sel}", res['text'])
                    st.markdown(f"<div class='course-card'>{sum_ans}</div>", unsafe_allow_html=True)
    else: st.info("Sync data first.")

with tab3:
    for c in st.session_state.chat_history:
        with st.chat_message(c["role"]): st.markdown(c["content"])

    if prompt := st.chat_input("Ask anything..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        ctx = st.session_state.get("timeline_data", "")
        reply = ask_elena_groq(prompt, ctx)
        
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"): st.markdown(reply)
