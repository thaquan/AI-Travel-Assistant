AI TRAVEL ASSISTANT 

**Họ và Tên: Trần Hà Anh Quân**

*MSSV: 24127228*

GitHub: https://github.com/thaquan/AI-Travel-Assistant

I. Tổng quan hệ thống
1. Mục tiêu:
- Tạo lịch trình tự động theo yêu cầu
- Tùy chỉnh theo thời gian, sở thích, tốc độ di chuyển
- Lưu trữ và xem lại lịch sử lịch trình
2. Yêu cầu từ người dùng:
Input từ người dùng:
- Origin city (Thành phố xuất phát)
- Destination city (Điểm đến)
- Dates (Thời gian: VD "3 ngày 2 đêm")
- Interests (Sở thích: food/museums/nature/nightlife/shopping/adventure)
- Pace (Tốc độ: relaxed/normal/tight)
Output:
- Lịch trình theo ngày (day-by-day)
- Chi tiết từng buổi (morning/afternoon/evening)
- Giải thích ngắn gọn cho mỗi hoạt động
LLM Server:
- Ollama + Model Mistral 78
- Có thể chạy trên Google Colab hay clone từ https://github.com/thaquan/AI-Travel-Assistant để chạy local trên máy
- Public qua Cloudflare Tunnel
Authentication & History:
- Đăng nhập / Đăng kí với Firebase Authentication
- Quên mật khẩu (gửi email reset)
- Lưu lịch sử vào Firestore
- Xem lại lịch sử tài khoản đã tạo 
II. Luồng hoạt động chi tiết
A. Đăng kí tài khoản:
1. User mở link web -> Màn hình đăng nhập / đăng kí
2. User nhập email và password 
3. Nhấn vào đăng kí để tự động đăng nhập 
4. Hệ thống gọi Firebase REST API:
POST https://identitytoolkit.googleapis.com/v1/accounts:signUp
5. Firebase tạo user mới
6. Lưu user_id, email vào session_state

B. Đăng nhập
1. User nhập user và password 
2. Hệ thống gọi Firebase REST API:
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword
3. Firebase xác thực thông tin 
4. Nếu đúng -> Trả về localId (user_id) + idToken. Nếu sai -> Trả về thông báo "Sai email hoặc password"
5. Lưu vào session_state
6. Chuyển màn hình chính

C. Quên mật khẩu
1. User chọn "Quên mật khẩu" 
2. Nhập email
3. Hệ thống gọi Firebase REST API:
POST https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode
4. Firebase gửi email reset link
5. User click link trong email
6. Đặt lại password mới

D. Tạo lịch trình 
1. User đăng nhập thành công
2. Tab "tạo lập kế hoạch" - Nhập thông tin: 
- User điền đầy đủ thông tin như "Xuất phát", "Điểm đến", "Thời gian", "Tốc độ", "Sở thích"
3. Nhấn "Tạo Lịch Trình"
4. Streamlit gọi hàm generate_itinerary():
- Tạo prompt cho LLM
- Gửi POST request đến Ollama server
5. Ollama xử lí:
- Nhận prompt
- Model Mistral generate text 
- Trả về Json response 
6. Streamlit nhận kết quả:
- Parse response
- Hiển thị markdown lịch trình 
7. Lưu vào Firebase
8. Hiển thị thông báo "Đã lưu"

E. Xem lại lịch trình 
1. User click tab "Lịch sử"
2. Frontend query Firestore:
- WHERE user_id = current_user_id
- ORDER BY timestamp DESC
- LIMIT 20
3. Hiển thị danh sách expander:
- Mỗi item: Destination + Dates
- Click mở → Xem chi tiết lịch trình

III. Giải thích từng cell trong file "mini-travel-application.ipynb"
1. Giải thích từng cell trong google colab
Cell 1: Cài đặt thư viện Ollama và thư viện

Cell 2: Khởi động Ollama Server 

Cell 3: Tải Model và tạo Cloudflare -> sau khi chạy xong cell sẽ ra 1 link dùng link này để dán vào file app.py trong phần ollama_url 

Cell 4: File app.py -> chứa các chức năng chính của web mini-travel-application 

Cell 5: Upload Firebase Service Account Key 

Cell 6: Khởi động Streamlit web -> chỉ cần nhấn vào link sẽ điều hướng qua 1 tab khác -> đây chính là chương trình mà chúng ta mong đợi

3. Hướng dẫn chạy trên local 
Bước 1: Clone repo:
```bash
git clone https://github.com/thaquan/AI-Travel-Assistant.git

cd AI-Travel-Assistant
```

Bước 2: Cài đặt thư viện cần thiết:
```bash
pip install streamlit firebase-admin requests ollama
```

Bước 3: Start Ollama:

ollama serve

ollama pull mistral

Bước 4: Tạo file ollama_url.txt: (File ở trên là khi chạy trên google colab nên khi chayj local cần tạo file ollama_url.txt mới)

echo "http://localhost:11434" > ollama_url.txt

Bước 5: Chạy app 

streamlit run app.py
