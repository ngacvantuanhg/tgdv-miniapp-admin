"""
Trang quản trị Mini App - Ban Tuyên giáo và Dân vận Tuyên Quang
================================================================
Dùng để: đăng/sửa/xoá tin tức, xem và trả lời phản ánh, tạo/quản lý
khảo sát, xem kết quả khảo sát.

Chạy thử trên máy: streamlit run app.py
"""

import json
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from supabase import Client, create_client

st.set_page_config(
    page_title="Quản trị Mini App - TG&DV Tuyên Quang",
    page_icon="🏛️",
    layout="wide",
)

FEEDBACK_TYPES = [
    {"code": "an_ninh", "title": "An ninh trật tự"},
    {"code": "moi_truong", "title": "Môi trường"},
    {"code": "chinh_sach", "title": "Chính sách, chế độ"},
    {"code": "thu_tuc_hanh_chinh", "title": "Thủ tục hành chính"},
    {"code": "khac", "title": "Khác"},
]
FEEDBACK_CODE_TO_TITLE = {t["code"]: t["title"] for t in FEEDBACK_TYPES}

NEWS_CATEGORIES = [
    ("thong_bao", "Thông báo"),
    ("hoat_dong", "Hoạt động"),
    ("chinh_sach", "Chính sách"),
    ("huong_dan_nghiep_vu", "Hướng dẫn nghiệp vụ"),
]

FEEDBACK_STATUSES = [
    ("moi", "Mới"),
    ("dang_xu_ly", "Đang xử lý"),
    ("da_xu_ly", "Đã xử lý"),
]
FEEDBACK_STATUS_TITLE = dict(FEEDBACK_STATUSES)

QUESTION_TYPES = [
    ("single_choice", "Chọn 1 đáp án"),
    ("multi_choice", "Chọn nhiều đáp án"),
    ("text", "Trả lời tự do"),
]
QUESTION_TYPE_TITLE = dict(QUESTION_TYPES)


# ----------------------------------------------------------------
# Kết nối Supabase bằng service_role key - bỏ qua mọi RLS, vì đây là
# trang quản trị nội bộ, chỉ cán bộ Ban mới có mật khẩu vào được.
# TUYỆT ĐỐI không đưa key này vào code của Mini App (chỉ dùng ở đây).
# ----------------------------------------------------------------
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


supabase = get_supabase()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------
# Đăng nhập bằng 1 mật khẩu chung cho cán bộ Ban (đơn giản, phù hợp
# quy mô 1 phòng ban). Mật khẩu đặt trong st.secrets, không hardcode.
# ----------------------------------------------------------------
def check_password() -> bool:
    def password_entered():
        if st.session_state.get("password") == st.secrets["ADMIN_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct"):
        return True

    st.text_input(
        "Mật khẩu quản trị",
        type="password",
        on_change=password_entered,
        key="password",
    )
    if st.session_state.get("password_correct") is False:
        st.error("Sai mật khẩu, vui lòng thử lại.")
    return False


if not check_password():
    st.stop()


st.title("🏛️ Quản trị Mini App - Tuyên giáo và Dân vận Tuyên Quang")

tab_news, tab_feedback, tab_survey, tab_survey_result = st.tabs(
    ["📰 Tin tức", "💬 Phản ánh", "📋 Khảo sát", "📊 Kết quả khảo sát"]
)

# ==================================================================
# TAB 1: TIN TỨC
# ==================================================================
with tab_news:
    st.subheader("Đăng tin mới")

    with st.expander("➕ Thêm tin mới", expanded=False):
        with st.form("form_new_news", clear_on_submit=True):
            n_title = st.text_input("Tiêu đề*")
            n_summary = st.text_area("Tóm tắt ngắn (hiện ở danh sách)", height=70)
            n_content = st.text_area("Nội dung đầy đủ*", height=200)
            col1, col2 = st.columns(2)
            with col1:
                n_category = st.selectbox(
                    "Phân loại",
                    options=[c[0] for c in NEWS_CATEGORIES],
                    format_func=lambda c: dict(NEWS_CATEGORIES)[c],
                )
                n_cover_image_url = st.text_input("Link ảnh đại diện (nếu có)")
            with col2:
                n_external_link = st.text_input(
                    "Link bài viết gốc (nếu là tin chia sẻ lại từ "
                    "baotuyenquang.com.vn / Facebook...) - để trống nếu là "
                    "tin Ban tự soạn"
                )
                n_is_published = st.checkbox("Đăng công khai ngay", value=True)

            submitted = st.form_submit_button("Đăng tin")
            if submitted:
                if not n_title.strip() or not n_content.strip():
                    st.error("Vui lòng nhập Tiêu đề và Nội dung.")
                else:
                    supabase.table("news").insert(
                        {
                            "title": n_title.strip(),
                            "summary": n_summary.strip() or None,
                            "content": n_content.strip(),
                            "category": n_category,
                            "cover_image_url": n_cover_image_url.strip() or None,
                            "external_link": n_external_link.strip() or None,
                            "is_published": n_is_published,
                            "published_at": now_iso() if n_is_published else None,
                        }
                    ).execute()
                    st.success("Đã đăng tin thành công!")
                    st.rerun()

    st.divider()
    st.subheader("Danh sách tin đã đăng")

    news_resp = (
        supabase.table("news")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    news_rows = news_resp.data or []

    if not news_rows:
        st.info("Chưa có tin nào.")

    for row in news_rows:
        status_label = "🟢 Đã đăng" if row.get("is_published") else "⚪ Bản nháp"
        with st.expander(f"{status_label} — {row['title']}"):
            with st.form(f"form_edit_news_{row['id']}"):
                e_title = st.text_input("Tiêu đề", value=row["title"])
                e_summary = st.text_area(
                    "Tóm tắt ngắn", value=row.get("summary") or "", height=70
                )
                e_content = st.text_area(
                    "Nội dung đầy đủ", value=row.get("content") or "", height=200
                )
                col1, col2 = st.columns(2)
                with col1:
                    cat_options = [c[0] for c in NEWS_CATEGORIES]
                    cur_cat = row.get("category") or cat_options[0]
                    e_category = st.selectbox(
                        "Phân loại",
                        options=cat_options,
                        index=cat_options.index(cur_cat)
                        if cur_cat in cat_options
                        else 0,
                        format_func=lambda c: dict(NEWS_CATEGORIES)[c],
                        key=f"cat_{row['id']}",
                    )
                    e_cover = st.text_input(
                        "Link ảnh đại diện",
                        value=row.get("cover_image_url") or "",
                    )
                with col2:
                    e_link = st.text_input(
                        "Link bài viết gốc",
                        value=row.get("external_link") or "",
                    )
                    e_published = st.checkbox(
                        "Đăng công khai", value=bool(row.get("is_published"))
                    )

                col_save, col_delete = st.columns([3, 1])
                with col_save:
                    save_clicked = st.form_submit_button(
                        "💾 Lưu thay đổi", use_container_width=True
                    )
                with col_delete:
                    delete_clicked = st.form_submit_button(
                        "🗑️ Xoá", use_container_width=True
                    )

                if save_clicked:
                    was_published = bool(row.get("is_published"))
                    update_data = {
                        "title": e_title.strip(),
                        "summary": e_summary.strip() or None,
                        "content": e_content.strip(),
                        "category": e_category,
                        "cover_image_url": e_cover.strip() or None,
                        "external_link": e_link.strip() or None,
                        "is_published": e_published,
                        "updated_at": now_iso(),
                    }
                    # Lần đầu chuyển từ nháp -> đăng công khai mới gán published_at
                    if e_published and not was_published:
                        update_data["published_at"] = now_iso()
                    supabase.table("news").update(update_data).eq(
                        "id", row["id"]
                    ).execute()
                    st.success("Đã lưu thay đổi!")
                    st.rerun()

                if delete_clicked:
                    supabase.table("news").delete().eq("id", row["id"]).execute()
                    st.success("Đã xoá tin.")
                    st.rerun()

# ==================================================================
# TAB 2: PHẢN ÁNH - KIẾN NGHỊ
# ==================================================================
with tab_feedback:
    st.subheader("Danh sách phản ánh")

    filter_status = st.selectbox(
        "Lọc theo trạng thái",
        options=["tat_ca"] + [s[0] for s in FEEDBACK_STATUSES],
        format_func=lambda s: "Tất cả"
        if s == "tat_ca"
        else FEEDBACK_STATUS_TITLE[s],
    )

    fb_query = supabase.table("feedback").select("*").order(
        "created_at", desc=True
    )
    if filter_status != "tat_ca":
        fb_query = fb_query.eq("status", filter_status)
    fb_rows = fb_query.execute().data or []

    if not fb_rows:
        st.info("Không có phản ánh nào.")

    status_icon = {"moi": "🆕", "dang_xu_ly": "⏳", "da_xu_ly": "✅"}

    for row in fb_rows:
        type_label = FEEDBACK_CODE_TO_TITLE.get(row.get("category"), "Khác")
        icon = status_icon.get(row.get("status"), "🆕")
        with st.expander(f"{icon} [{type_label}] {row['title']}"):
            who = "Ẩn danh" if row.get("is_anonymous") else (
                row.get("full_name") or "(không rõ tên)"
            )
            st.caption(
                f"Người gửi: {who}"
                + (f" — SĐT: {row['phone']}" if row.get("phone") else "")
                + f" — Zalo ID: {row.get('zalo_user_id', '')}"
                + f" — Gửi lúc: {row.get('created_at', '')}"
            )
            st.write(row.get("content") or "")

            if row.get("attachment_url"):
                st.image(row["attachment_url"], width=200)

            with st.form(f"form_fb_{row['id']}"):
                status_options = [s[0] for s in FEEDBACK_STATUSES]
                cur_status = row.get("status") or "moi"
                new_status = st.selectbox(
                    "Trạng thái xử lý",
                    options=status_options,
                    index=status_options.index(cur_status)
                    if cur_status in status_options
                    else 0,
                    format_func=lambda s: FEEDBACK_STATUS_TITLE[s],
                    key=f"status_{row['id']}",
                )
                new_response = st.text_area(
                    "Phản hồi của Ban",
                    value=row.get("admin_response") or "",
                    height=120,
                )
                saved = st.form_submit_button("💾 Lưu phản hồi")
                if saved:
                    update_data = {
                        "status": new_status,
                        "admin_response": new_response.strip() or None,
                    }
                    if new_response.strip() and not row.get("admin_response"):
                        update_data["responded_at"] = now_iso()
                    supabase.table("feedback").update(update_data).eq(
                        "id", row["id"]
                    ).execute()
                    st.success("Đã lưu!")
                    st.rerun()

# ==================================================================
# TAB 3: KHẢO SÁT
# ==================================================================
with tab_survey:
    st.subheader("Tạo khảo sát mới")

    if "qb_count" not in st.session_state:
        st.session_state.qb_count = 1

    s_title = st.text_input("Tên khảo sát*", key="new_survey_title")
    s_description = st.text_area(
        "Mô tả ngắn (hiện dưới tên khảo sát)", key="new_survey_desc", height=70
    )

    col_active, col_enddate = st.columns(2)
    with col_active:
        s_is_active = st.checkbox("Mở khảo sát ngay", value=True, key="new_survey_active")
    with col_enddate:
        s_has_enddate = st.checkbox("Đặt hạn trả lời", key="new_survey_has_enddate")
        s_enddate = None
        if s_has_enddate:
            s_enddate = st.date_input("Hạn trả lời", key="new_survey_enddate")

    st.markdown("**Câu hỏi**")

    for i in range(st.session_state.qb_count):
        with st.container(border=True):
            st.text_input(f"Câu hỏi {i + 1}", key=f"q_text_{i}")
            q_type = st.selectbox(
                "Dạng câu hỏi",
                options=[q[0] for q in QUESTION_TYPES],
                format_func=lambda q: QUESTION_TYPE_TITLE[q],
                key=f"q_type_{i}",
            )
            if q_type in ("single_choice", "multi_choice"):
                st.text_area(
                    "Các đáp án (mỗi đáp án 1 dòng)",
                    key=f"q_options_{i}",
                    height=100,
                    placeholder="Rất tốt\nTốt\nBình thường\nChưa tốt",
                )

    col_add, col_remove = st.columns(2)
    with col_add:
        if st.button("➕ Thêm câu hỏi"):
            st.session_state.qb_count += 1
            st.rerun()
    with col_remove:
        if st.button("➖ Bớt câu hỏi cuối") and st.session_state.qb_count > 1:
            last = st.session_state.qb_count - 1
            for key_prefix in ("q_text_", "q_type_", "q_options_"):
                st.session_state.pop(f"{key_prefix}{last}", None)
            st.session_state.qb_count -= 1
            st.rerun()

    if st.button("✅ Tạo khảo sát", type="primary"):
        questions = []
        for i in range(st.session_state.qb_count):
            text = (st.session_state.get(f"q_text_{i}") or "").strip()
            if not text:
                continue
            q_type = st.session_state.get(f"q_type_{i}", "text")
            question = {
                "id": f"q{i + 1}",
                "text": text,
                "type": q_type,
            }
            if q_type in ("single_choice", "multi_choice"):
                raw_options = st.session_state.get(f"q_options_{i}", "") or ""
                options = [o.strip() for o in raw_options.splitlines() if o.strip()]
                question["options"] = options
            questions.append(question)

        if not s_title.strip():
            st.error("Vui lòng nhập tên khảo sát.")
        elif not questions:
            st.error("Vui lòng nhập ít nhất 1 câu hỏi.")
        else:
            insert_data = {
                "title": s_title.strip(),
                "description": s_description.strip() or None,
                "questions": questions,
                "is_active": s_is_active,
            }
            if s_enddate:
                insert_data["end_date"] = datetime.combine(
                    s_enddate, datetime.max.time()
                ).isoformat()
            supabase.table("surveys").insert(insert_data).execute()
            st.success("Đã tạo khảo sát!")

            # reset form
            for i in range(st.session_state.qb_count):
                for key_prefix in ("q_text_", "q_type_", "q_options_"):
                    st.session_state.pop(f"{key_prefix}{i}", None)
            st.session_state.qb_count = 1
            for k in (
                "new_survey_title",
                "new_survey_desc",
                "new_survey_active",
                "new_survey_has_enddate",
                "new_survey_enddate",
            ):
                st.session_state.pop(k, None)
            st.rerun()

    st.divider()
    st.subheader("Danh sách khảo sát")

    survey_rows = (
        supabase.table("surveys")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )

    if not survey_rows:
        st.info("Chưa có khảo sát nào.")

    for row in survey_rows:
        status_label = "🟢 Đang mở" if row.get("is_active") else "⚪ Đã đóng"
        with st.expander(f"{status_label} — {row['title']}"):
            st.write(row.get("description") or "")
            st.caption(f"Số câu hỏi: {len(row.get('questions') or [])}")

            col1, col2 = st.columns(2)
            with col1:
                if row.get("is_active"):
                    if st.button("⏹️ Đóng khảo sát", key=f"close_{row['id']}"):
                        supabase.table("surveys").update(
                            {"is_active": False}
                        ).eq("id", row["id"]).execute()
                        st.rerun()
                else:
                    if st.button("▶️ Mở lại khảo sát", key=f"open_{row['id']}"):
                        supabase.table("surveys").update(
                            {"is_active": True}
                        ).eq("id", row["id"]).execute()
                        st.rerun()
            with col2:
                if st.button("🗑️ Xoá khảo sát", key=f"del_survey_{row['id']}"):
                    supabase.table("surveys").delete().eq(
                        "id", row["id"]
                    ).execute()
                    st.rerun()

# ==================================================================
# TAB 4: KẾT QUẢ KHẢO SÁT
# ==================================================================
with tab_survey_result:
    st.subheader("Xem kết quả khảo sát")

    if not survey_rows:
        st.info("Chưa có khảo sát nào để xem kết quả.")
    else:
        survey_options = {row["id"]: row["title"] for row in survey_rows}
        selected_id = st.selectbox(
            "Chọn khảo sát",
            options=list(survey_options.keys()),
            format_func=lambda sid: survey_options[sid],
        )
        selected_survey = next(
            r for r in survey_rows if r["id"] == selected_id
        )
        questions = selected_survey.get("questions") or []

        responses = (
            supabase.table("survey_responses")
            .select("*")
            .eq("survey_id", selected_id)
            .execute()
            .data
            or []
        )

        st.metric("Số lượt trả lời", len(responses))

        if not responses:
            st.info("Chưa có ai trả lời khảo sát này.")
        else:
            for q in questions:
                st.markdown(f"**{q['text']}**")
                q_type = q.get("type")

                if q_type in ("single_choice", "multi_choice"):
                    tally: dict = {}
                    for resp in responses:
                        answer = (resp.get("answers") or {}).get(q["id"])
                        if answer is None:
                            continue
                        values = answer if isinstance(answer, list) else [answer]
                        for v in values:
                            tally[v] = tally.get(v, 0) + 1
                    if tally:
                        chart_df = pd.DataFrame(
                            {"Số lượt chọn": tally.values()}, index=tally.keys()
                        )
                        st.bar_chart(chart_df)
                    else:
                        st.caption("Chưa có ai trả lời câu này.")
                else:
                    texts = [
                        (resp.get("answers") or {}).get(q["id"])
                        for resp in responses
                    ]
                    texts = [t for t in texts if t]
                    if texts:
                        for t in texts:
                            st.write(f"- {t}")
                    else:
                        st.caption("Chưa có ai trả lời câu này.")
                st.divider()

            # Xuất toàn bộ dữ liệu thô để lưu/báo cáo
            flat_rows = []
            for resp in responses:
                flat = {
                    "submitted_at": resp.get("submitted_at"),
                    "zalo_user_id": resp.get("zalo_user_id"),
                }
                for q in questions:
                    answer = (resp.get("answers") or {}).get(q["id"])
                    if isinstance(answer, list):
                        answer = ", ".join(answer)
                    flat[q["text"]] = answer
                flat_rows.append(flat)

            df = pd.DataFrame(flat_rows)
            st.download_button(
                "⬇️ Tải dữ liệu thô (CSV)",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"ket_qua_khao_sat_{selected_id}.csv",
                mime="text/csv",
            )

