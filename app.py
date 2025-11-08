import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os

# ===== AUTO-LOAD OLLAMA URL =====
try:
    with open('ollama_url.txt', 'r') as f:
        OLLAMA_URL = f.read().strip()
except:
    OLLAMA_URL = "https://copyright-landscapes-pop-adoption.trycloudflare.com/"

# 🔥 FIREBASE WEB API KEY
try:
    FIREBASE_API_KEY = st.secrets["firebase_api"]["key"]
except:
    # ✅ Fallback với key thật (Key này có thể chạy bên google colab)
    FIREBASE_API_KEY = "FIREBASE_API_KEY"

# ===== SESSION STATE =====
if 'user_logged_in' not in st.session_state:
    st.session_state.user_logged_in = False
if 'db' not in st.session_state:
    st.session_state.db = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'show_reset_password' not in st.session_state:
    st.session_state.show_reset_password = False

# ===== FIREBASE INIT  =====
def init_firebase():
    if not st.session_state.db:
        try:
            if not firebase_admin._apps:
                # ĐỌC TỪ STREAMLIT SECRETS
                try:
                    firebase_config = dict(st.secrets["firebase"])
                    cred = credentials.Certificate(firebase_config)
                except KeyError:
                    st.error("❌ Chưa cấu hình Firebase Secrets!")
                    st.info("👉 Vào: Manage app → Settings → Secrets")
                    st.stop()
                except Exception as e:
                    st.error(f"❌ Lỗi đọc secrets: {e}")
                    st.stop()
                
                firebase_admin.initialize_app(cred)
            st.session_state.db = firestore.client()
            return True
        except Exception as e:
            st.error(f"❌ Firebase lỗi: {e}")
            return False
    return True

# ===== PASSWORD RESET =====
def send_password_reset_email(email):
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
        response = requests.post(url, json={
            "requestType": "PASSWORD_RESET",
            "email": email
        }, timeout=10)
        
        if response.status_code == 200:
            st.success(f"✅ Email khôi phục đã gửi đến {email}")
            st.info("💡 Kiểm tra cả thư mục Spam")
            return True
        else:
            error = response.json().get('error', {}).get('message', '')
            if 'EMAIL_NOT_FOUND' in error:
                st.error("❌ Email này chưa được đăng ký!")
            else:
                st.error(f"❌ Lỗi: {error}")
            return False
    except Exception as e:
        st.error(f"❌ Lỗi: {e}")
        return False

# ===== AUTHENTICATION =====
def authenticate_user(email, password, is_register=False):
    if not init_firebase():
        return False

    try:
        if is_register:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
        else:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        
        response = requests.post(url, json={
            "email": email,
            "password": password,
            "returnSecureToken": True
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.user_id = data['localId']
            st.session_state.user_email = email
            st.session_state.user_logged_in = True
            
            if is_register:
                st.success("✅ Đăng ký thành công!")
            else:
                st.success(f"✅ Chào {email}!")
            return True
        else:
            error_msg = response.json().get('error', {}).get('message', '')
            
            if 'EMAIL_EXISTS' in error_msg:
                st.error("❌ Email đã được đăng ký!")
            elif 'INVALID_PASSWORD' in error_msg or 'INVALID_LOGIN_CREDENTIALS' in error_msg:
                st.error("❌ Sai email hoặc mật khẩu!")
            elif 'EMAIL_NOT_FOUND' in error_msg:
                st.error("❌ Email chưa được đăng ký!")
            elif 'WEAK_PASSWORD' in error_msg:
                st.error("❌ Password cần ít nhất 6 ký tự!")
            else:
                st.error(f"❌ Lỗi: {error_msg}")
            return False
            
    except Exception as e:
        st.error(f"❌ Lỗi: {e}")
        return False

# ===== LLM GENERATION =====
def generate_itinerary(origin, dest, dates, interests, pace, ollama_url):
    interest_str = ", ".join(interests) if interests else "du lịch tổng hợp"

    prompt = f"""Lịch trình du lịch {dest} trong {dates}.

Xuất phát: {origin}
Sở thích: {interest_str}
Tốc độ: {pace}

Format:
**Ngày 1:**
- Sáng (7h-11h): [Địa điểm] - [Hoạt động]
- Chiều (14h-18h): [Địa điểm] - [Hoạt động]
- Tối (19h-22h): [Địa điểm] - [Hoạt động]

Chỉ viết lịch trình, bắt đầu từ "**Ngày 1:**"
"""

    try:
        test_conn = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if test_conn.status_code != 200:
            return "❌ Ollama Tunnel ngắt. Chạy lại Cell 3"

        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 700
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=70
        )

        if response.status_code == 200:
            result = response.json().get('response', '')
            if "**Ngày 1" in result:
                result = result[result.index("**Ngày 1"):]
            return result if result else "❌ Không có phản hồi"
        else:
            return f"❌ Lỗi {response.status_code}"

    except requests.exceptions.Timeout:
        return "❌ Timeout 70s. Thử lịch trình ngắn hơn"
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"

# ===== UI =====
st.set_page_config(page_title="AI Travel Assistant", page_icon="✈️", layout="wide")

with st.sidebar:
    st.subheader("🔧 System Status")
    if "trycloudflare.com" in OLLAMA_URL:
        st.success("✅ Ollama Connected")
        st.caption(f"URL: {OLLAMA_URL[:40]}...")
    else:
        st.error("❌ Ollama chưa kết nối")

st.title("✈️ AI Travel Recommendation Assistant")

# ===== LOGIN =====
if not st.session_state.user_logged_in:
    
    if st.session_state.show_reset_password:
        st.subheader("🔑 Quên Mật Khẩu")
        
        with st.form("reset_form"):
            reset_email = st.text_input("📧 Email")
            col1, col2 = st.columns(2)
            
            with col1:
                send_reset = st.form_submit_button("📧 Gửi Email", use_container_width=True)
            with col2:
                back_to_login = st.form_submit_button("⬅️ Quay lại", use_container_width=True)
        
        if send_reset and reset_email:
            send_password_reset_email(reset_email)
        
        if back_to_login:
            st.session_state.show_reset_password = False
            st.rerun()
    
    else:
        st.subheader("🔐 Đăng nhập/Đăng ký")

        with st.form("login_form"):
            email = st.text_input("📧 Email")
            password = st.text_input("🔑 Password", type="password")

            col1, col2 = st.columns(2)
            with col1:
                login = st.form_submit_button("🚪 Đăng nhập", use_container_width=True)
            with col2:
                register = st.form_submit_button("📝 Đăng ký", use_container_width=True)

        if st.button("🔓 Quên mật khẩu?", use_container_width=True):
            st.session_state.show_reset_password = True
            st.rerun()

        if login and email and password:
            if authenticate_user(email, password):
                st.rerun()
                
        if register and email and password:
            if len(password) < 6:
                st.error("❌ Password phải có ít nhất 6 ký tự!")
            else:
                if authenticate_user(email, password, is_register=True):
                    st.rerun()

# ===== MAIN APP =====
else:
    init_firebase()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"👋 Xin chào, **{st.session_state.user_email}**!")
    with col2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.divider()

    tab1, tab2 = st.tabs(["🗺️ Lập Kế hoạch", "📚 Lịch sử"])

    with tab1:
        st.header("📝 Tạo Lịch trình Mới")

        with st.form("travel_form"):
            col1, col2 = st.columns(2)

            with col1:
                origin = st.text_input("🏙️ Xuất phát", "Hà Nội")
                dest = st.text_input("🎯 Điểm đến", "Đà Nẵng")

            with col2:
                dates = st.text_input("📅 Thời gian", "2 ngày 1 đêm")
                pace = st.selectbox("⚡ Tốc độ",
                    ["Nhàn nhã (Relaxed)", "Bình thường (Normal)", "Gấp gáp (Tight)"])

            interests = st.multiselect(
                "🎨 Sở thích",
                ['Ẩm thực (Food)', 'Bảo tàng/Văn hóa (Museums)',
                 'Thiên nhiên (Nature)', 'Giải trí đêm (Nightlife)',
                 'Mua sắm (Shopping)', 'Thể thao (Adventure)'],
                default=['Ẩm thực (Food)']
            )

            submitted = st.form_submit_button("🚀 Tạo Lịch trình",
                use_container_width=True, type="primary")

        if submitted and dest:
            with st.spinner(f'⏳ AI đang tạo lịch trình...'):
                itinerary = generate_itinerary(origin, dest, dates, interests, pace, OLLAMA_URL)

                if itinerary.startswith("❌"):
                    st.error(itinerary)
                else:
                    st.success(f"✅ Lịch trình {dest} ({dates})")
                    st.divider()
                    st.markdown(itinerary)

                    if st.session_state.db:
                        try:
                            st.session_state.db.collection('itineraries').add({
                                'user_id': st.session_state.user_id,
                                'destination': dest,
                                'input': {
                                    'origin': origin,
                                    'dates': dates,
                                    'interests': interests,
                                    'pace': pace
                                },
                                'itinerary': itinerary,
                                'timestamp': firestore.SERVER_TIMESTAMP
                            })
                            st.success("💾 Đã lưu")
                        except Exception as e:
                            st.warning(f"⚠️ Không lưu được: {e}")

    with tab2:
        st.header("📖 Lịch sử")

        if st.session_state.db:
            try:
                docs = st.session_state.db.collection('itineraries')\
                    .where('user_id', '==', st.session_state.user_id)\
                    .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                    .limit(20).stream()

                items = list(docs)

                if not items:
                    st.info("📭 Chưa có lịch sử")
                else:
                    for i, doc in enumerate(items, 1):
                        data = doc.to_dict()
                        inp = data.get('input', {})

                        with st.expander(f"#{i} - {data.get('destination')} ({inp.get('dates')})"):
                            st.markdown(f"**🏙️ Từ:** {inp.get('origin')}")
                            st.markdown(f"**⚡ Tốc độ:** {inp.get('pace')}")
                            st.markdown(f"**🎨 Sở thích:** {', '.join(inp.get('interests', []))}")
                            st.divider()
                            st.markdown(data.get('itinerary'))
            except Exception as e:
                st.error(f"❌ Lỗi: {e}")
