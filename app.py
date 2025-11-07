%%writefile app.py
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
    OLLAMA_URL = "https://olympics-instrumentation-beast-flowers.trycloudflare.com/"

# 🔥 FIREBASE WEB API KEY
try:
    # Trên Streamlit Cloud hoặc local với secrets.toml
    FIREBASE_API_KEY = st.secrets["firebase_api"]["key"]
except:
    # Fallback cho Colab 
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

# ===== FIREBASE INIT =====
def init_firebase():
    if not st.session_state.db:
        try:
            if not firebase_admin._apps:
                try:
                    firebase_config = dict(st.secrets["firebase"])
                    cred = credentials.Certificate(firebase_config)
                except:
                    # Fallback: Đọc từ file (chỉ dùng local/Colab)
                    if os.path.exists('mini-travel-new.json'):
                        cred = credentials.Certificate('mini-travel-new.json')
                    else:
                        st.error("❌ Không tìm thấy Firebase credentials!")
                        st.info("📌 Trên local: Thêm file mini-travel-new.json")
                        st.info("📌 Trên Streamlit Cloud: Cấu hình secrets")
                        return False
                
                firebase_admin.initialize_app(cred)
            st.session_state.db = firestore.client()
            return True
        except Exception as e:
            st.error(f"❌ Firebase lỗi: {e}")
            return False
    return True

# ===== PASSWORD RESET =====
def send_password_reset_email(email):
    """Gửi email reset password"""
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"

        response = requests.post(url, json={
            "requestType": "PASSWORD_RESET",
            "email": email
        }, timeout=10)

        if response.status_code == 200:
            st.success(f"✅ Email khôi phục đã gửi đến {email}. Kiểm tra hộp thư!")
            st.info("💡 Kiểm tra cả thư mục Spam nếu không thấy email")
            return True
        else:
            error = response.json().get('error', {}).get('message', 'Unknown error')
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

            response = requests.post(url, json={
                "email": email,
                "password": password,
                "returnSecureToken": True
            }, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Lưu session state
                st.session_state.user_id = data['localId']
                st.session_state.user_email = email
                st.session_state.user_logged_in = True

                st.success("✅ Đăng ký thành công! Đang đăng nhập...")
                return True
            else:
                error = response.json().get('error', {}).get('message', '')
                if 'EMAIL_EXISTS' in error:
                    st.error("❌ Email đã được đăng ký!")
                elif 'WEAK_PASSWORD' in error:
                    st.error("❌ Password quá yếu! Cần ít nhất 6 ký tự")
                else:
                    st.error(f"❌ Lỗi đăng ký: {error}")
                return False

        else:
            # Đăng nhập
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
                st.success(f"✅ Chào mừng {email}!")
                return True
            else:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')

                # Thông báo lỗi rõ ràng
                if 'INVALID_PASSWORD' in error_msg or 'INVALID_LOGIN_CREDENTIALS' in error_msg:
                    st.error("❌ Sai email hoặc mật khẩu!")
                elif 'EMAIL_NOT_FOUND' in error_msg:
                    st.error("❌ Email chưa được đăng ký!")
                elif 'INVALID_EMAIL' in error_msg:
                    st.error("❌ Email không hợp lệ!")
                elif 'USER_DISABLED' in error_msg:
                    st.error("❌ Tài khoản đã bị khóa!")
                elif 'TOO_MANY_ATTEMPTS_TRY_LATER' in error_msg:
                    st.error("❌ Quá nhiều lần thử! Vui lòng đợi vài phút")
                else:
                    st.error(f"❌ Lỗi đăng nhập: {error_msg}")
                return False

    except requests.exceptions.Timeout:
        st.error("❌ Timeout! Kiểm tra kết nối mạng")
        return False
    except Exception as e:
        st.error(f"❌ Lỗi: {e}")
        return False

# ===== LLM GENERATION =====
def generate_itinerary(origin, dest, dates, interests, pace, ollama_url):
    interest_str = ", ".join(interests) if interests else "general sightseeing"

    prompt = f"""Tạo lịch trình du lịch chi tiết từ {origin} đến {dest} trong CHÍNH XÁC {dates}.

**LƯU Ý QUAN TRỌNG: Lịch trình PHẢI phù hợp với thời gian \"{dates}\" mà người dùng yêu cầu.**

SỞ THÍCH: {interest_str}
TỐC ĐỘ: {pace}

YÊU CẦU:
1. Chia theo từng ngày (Sáng/Chiều/Tối) dựa trên thời gian \"{dates}\"
2. Gợi ý địa điểm cụ thể tại {dest}
3. Thêm mẹo thực tế (giá vé, thời gian, lưu ý)
4. Viết bằng tiếng Việt
5. **NẾU người dùng nhập thời gian tùy chỉnh (ví dụ: "5 ngày 4 đêm", "1 tuần"), hãy tạo lịch trình cho ĐÚNG thời gian đó**

VÍ DỤ FORMAT:
**Ngày 1:**
- **Sáng (7:00-11:00):** Tham quan [Địa điểm]. Mẹo: ...
- **Chiều (14:00-18:00):** ...
- **Tối (19:00-22:00):** ...

Hãy tạo lịch trình cho \"{dates}\" ngay:"""

    try:
        test_conn = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if test_conn.status_code != 200:
            return "❌ Ollama Tunnel đã ngắt kết nối. Vui lòng:\n1. Chạy lại CELL 3\n2. Reload lại trang Streamlit"

        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1500
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=180
        )

        if response.status_code == 200:
            return response.json().get('response', 'Không có phản hồi')
        else:
            return f"❌ Lỗi {response.status_code}: {response.text[:200]}"

    except requests.exceptions.Timeout:
        return "❌ Timeout! AI xử lý quá lâu. Thử lại với yêu cầu ngắn hơn."
    except requests.exceptions.ConnectionError:
        return "❌ Mất kết nối tới Ollama. Chạy lại CELL 3 để tạo tunnel mới."
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"

# ===== UI =====
st.set_page_config(page_title="AI Travel Assistant", page_icon="✈️", layout="wide")

with st.sidebar:
    st.subheader("🔧 System Status")
    if "trycloudflare.com" in OLLAMA_URL:
        st.success(f"✅ Ollama Connected")
        st.caption(f"URL: {OLLAMA_URL[:40]}...")
    else:
        st.error("❌ Ollama chưa kết nối")
        st.warning("Chạy CELL 3 để tạo tunnel")

    if os.path.exists('mini-travel.json'):
        st.success("✅ Firebase OK")
    else:
        st.error("❌ Thiếu mini-travel.json")

st.title("✈️ AI Travel Recommendation Assistant")

# ===== LOGIN =====
if not st.session_state.user_logged_in:

    # QUÊN MẬT KHẨU
    if st.session_state.show_reset_password:
        st.subheader("🔑 Quên Mật Khẩu")

        with st.form("reset_form"):
            reset_email = st.text_input("📧 Nhập email của bạn", placeholder="example@gmail.com")
            col1, col2 = st.columns(2)

            with col1:
                send_reset = st.form_submit_button("📧 Gửi Email", use_container_width=True, type="primary")
            with col2:
                back_to_login = st.form_submit_button("⬅️ Quay lại", use_container_width=True)

        if send_reset and reset_email:
            send_password_reset_email(reset_email)

        if back_to_login:
            st.session_state.show_reset_password = False
            st.rerun()

    # ĐĂNG NHẬP/ĐĂNG KÝ
    else:
        st.subheader("🔐 Đăng nhập/Đăng ký")

        with st.form("login_form"):
            email = st.text_input("📧 Email", placeholder="example@gmail.com")
            password = st.text_input("🔑 Password", type="password", placeholder="Tối thiểu 6 ký tự")

            col1, col2 = st.columns(2)
            with col1:
                login = st.form_submit_button("🚪 Đăng nhập", use_container_width=True)
            with col2:
                register = st.form_submit_button("📝 Đăng ký", use_container_width=True, type="primary")

        # NÚT QUÊN MẬT KHẨU
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
                dates = st.text_input("📅 Thời gian (VD: 3 ngày 2 đêm, 1 tuần, 5 ngày)", "3 ngày 2 đêm")
                pace = st.selectbox("⚡ Tốc độ",
                    ["Nhàn nhã (Relaxed)", "Bình thường (Normal)", "Gấp gáp (Tight)"])

            interests = st.multiselect(
                "🎨 Sở thích",
                ['Ẩm thực (Food)', 'Bảo tàng/Văn hóa (Museums)',
                 'Thiên nhiên (Nature)', 'Giải trí đêm (Nightlife)',
                 'Mua sắm (Shopping)', 'Thể thao (Adventure)'],
                default=['Ẩm thực (Food)', 'Thiên nhiên (Nature)']
            )

            submitted = st.form_submit_button("🚀 Tạo Lịch trình",
                use_container_width=True, type="primary")

        if submitted and dest:
            with st.spinner(f'⏳ AI đang tạo lịch trình cho {dates}... (30-90s)'):
                itinerary = generate_itinerary(origin, dest, dates, interests, pace, OLLAMA_URL)

                if itinerary.startswith("❌"):
                    st.error(itinerary)
                else:
                    st.success(f"✅ Lịch trình cho **{dest}** trong **{dates}**")
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

                        with st.expander(f"#{i} - {data.get('destination', 'N/A')} ({inp.get('dates', 'N/A')})"):
                            st.markdown(f"**🏙️ Từ:** {inp.get('origin', 'N/A')}")
                            st.markdown(f"**⚡ Tốc độ:** {inp.get('pace', 'N/A')}")
                            st.markdown(f"**🎨 Sở thích:** {', '.join(inp.get('interests', []))}")
                            st.divider()
                            st.markdown(data.get('itinerary', 'N/A'))
            except Exception as e:
                st.error(f"❌ Lỗi: {e}")
