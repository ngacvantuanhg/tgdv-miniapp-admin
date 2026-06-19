TRANG QUẢN TRỊ MINI APP - BAN TUYÊN GIÁO VÀ DÂN VẬN TUYÊN QUANG
==================================================================

Đây là một app Streamlit độc lập (khác với project "frontend" của Mini
App), dùng để cán bộ Ban đăng/sửa/xoá tin tức, xem và trả lời phản ánh
của người dân, tạo và quản lý khảo sát, xem kết quả khảo sát.

1) CHẠY THỬ TRÊN MÁY
-----------------------
- Giải nén thư mục này ra một vị trí riêng, ví dụ:
      C:\Users\VTBTGDV\Desktop\tgdv-miniapp\admin\
- Mở Command Prompt tại thư mục đó, chạy:
      pip install -r requirements.txt
- Đổi tên file ".streamlit/secrets.toml.example" thành
  ".streamlit/secrets.toml", mở file đó điền 3 giá trị:
    - SUPABASE_URL: giống file .env bên frontend (Project URL trong
      Supabase Settings > API)
    - SUPABASE_SERVICE_ROLE_KEY: vào Supabase Settings > API, lấy key
      "service_role" (KHÁC với key "anon" đã dùng ở Mini App). Key này
      có toàn quyền đọc/sửa/xoá mọi dữ liệu, bỏ qua mọi luật bảo mật
      (RLS) - đây là lý do trang này phải có mật khẩu, và secrets.toml
      đã được thêm vào .gitignore để không lỡ đẩy lên GitHub công khai.
    - ADMIN_PASSWORD: tự đặt một mật khẩu cho cán bộ Ban dùng để đăng
      nhập vào trang quản trị này.
- Chạy:
      streamlit run app.py
- Mở trình duyệt theo địa chỉ Streamlit hiện ra, nhập mật khẩu vừa đặt.

2) CÁC CHỨC NĂNG
-------------------
- Tab "Tin tức": thêm tin mới (có thể lưu nháp chưa đăng công khai),
  sửa/xoá tin đã có. Nếu tin là chia sẻ lại từ baotuyenquang.com.vn hay
  Facebook thì điền vào ô "Link bài viết gốc" - Mini App sẽ mở link đó
  khi người dùng bấm vào; để trống thì Mini App tự hiện nội dung đầy đủ
  ngay trong app.
- Tab "Phản ánh": lọc theo trạng thái (Mới / Đang xử lý / Đã xử lý),
  xem chi tiết từng phản ánh (kèm tên, SĐT người gửi - thông tin này
  KHÔNG hiển thị công khai trên Mini App, chỉ hiện ở đây), viết phản
  hồi và đổi trạng thái xử lý.
- Tab "Khảo sát": tạo khảo sát mới với số câu hỏi tuỳ ý, mỗi câu chọn
  1 trong 3 dạng (chọn 1 đáp án / chọn nhiều đáp án / trả lời tự do).
  Có thể đóng/mở lại hoặc xoá khảo sát đã tạo.
- Tab "Kết quả khảo sát": chọn 1 khảo sát để xem số lượt trả lời, biểu
  đồ cột cho các câu chọn đáp án, danh sách câu trả lời tự do, và nút
  tải toàn bộ dữ liệu thô về dạng file CSV.

3) KHI ĐƯA LÊN STREAMLIT COMMUNITY CLOUD
---------------------------------------------
Làm giống các app Streamlit khác Ban đã triển khai trước đây: đẩy code
lên GitHub (repo riêng tư là tốt nhất, dù secrets.toml đã bị
.gitignore loại trừ rồi), tạo app mới trên Streamlit Cloud chỉ tới repo
này, rồi vào phần "Secrets" trên Streamlit Cloud dán đúng 3 dòng nội
dung trong secrets.toml vào (giống cách đã làm với các app khác).

Nếu muốn tránh app này bị "ngủ" do gói miễn phí, có thể thêm app này
vào danh sách app được "đánh thức" trong workflow GitHub Actions
"keep-streamlit-alive.yml" đã có sẵn ở repo nuoi_streamlit.

4) BẢO MẬT
------------
- Mật khẩu hiện dùng chung 1 mật khẩu cho cả Ban (đơn giản, phù hợp
  quy mô phòng ban). Nếu sau này cần phân quyền nhiều người với mật
  khẩu riêng từng người, báo lại để nâng cấp.
- Không chia sẻ link app quản trị này hoặc mật khẩu cho người ngoài
  Ban, vì có toàn quyền với dữ liệu (kể cả xoá).
