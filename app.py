"""
Trang quản trị Mini App - Ban Tuyên giáo và Dân vận Tuyên Quang
================================================================
v2.0 — Giao diện mới, thêm tab Tổng quan với thống kê theo thời gian
"""

import json
from datetime import datetime, timezone, date
from dateutil.relativedelta import relativedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import Client, create_client

# ================================================================
# CẤU HÌNH TRANG
# ================================================================
st.set_page_config(
    page_title="Quản trị Mini App - TG&DV Tuyên Quang",
    page_icon="🏛️",
    layout="wide",
)

# ================================================================
# CSS CUSTOM
# ================================================================
st.markdown("""
<style>
/* --- Màu chủ đạo --- */
:root {
    --red:    #C8102E;
    --gold:   #F5A623;
    --navy:   #0D1B2A;
    --light:  #F7F8FA;
    --border: #E2E6EA;
    --text:   #1A1A2E;
    --muted:  #6B7280;
}

/* --- Header trang --- */
.admin-header {
    background: linear-gradient(135deg, var(--navy) 0%, #1a3a5c 100%);
    color: white;
    padding: 1.2rem 1.8rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    border-left: 5px solid var(--red);
}
.admin-header h1 {
    font-size: 1.4rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: 0.01em;
}
.admin-header .subtitle {
    font-size: 0.82rem;
    opacity: 0.7;
    margin: 0;
}

/* --- Thẻ chỉ số (metric card) --- */
.metric-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.metric-card {
    background: white;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    border: 1px solid var(--border);
    border-top: 4px solid var(--red);
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.metric-card.gold  { border-top-color: var(--gold); }
.metric-card.navy  { border-top-color: var(--navy); }
.metric-card.green { border-top-color: #16A34A; }
.metric-card .num {
    font-size: 2.2rem;
    font-weight: 800;
    color: var(--navy);
    line-height: 1;
}
.metric-card .label {
    font-size: 0.78rem;
    color: var(--muted);
    margin-top: 0.35rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.metric-card .delta {
    font-size: 0.8rem;
    color: #16A34A;
    margin-top: 0.2rem;
}

/* --- Tiêu đề section --- */
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--navy);
    padding-bottom: 0.4rem;
    border-bottom: 2px solid var(--red);
    margin-bottom: 1rem;
    display: inline-block;
}

/* --- Badge trạng thái --- */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-green  { background: #D1FAE5; color: #065F46; }
.badge-yellow { background: #FEF3C7; color: #92400E; }
.badge-gray   { background: #F3F4F6; color: #374151; }
.badge-red    { background: #FEE2E2; color: #991B1B; }

/* --- Bộ lọc thời gian --- */
.period-selector {
    background: white;
    border-radius: 8px;
    padding: 0.8rem 1.2rem;
    border: 1px solid var(--border);
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* --- Tab styling --- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    font-weight: 600;
    font-size: 0.88rem;
}
.stTabs [aria-selected="true"] {
    background-color: #FFF0F2 !important;
    color: var(--red) !important;
}

/* --- Divider --- */
.styled-divider {
    height: 1px;
    background: linear-gradient(to right, var(--red), transparent);
    margin: 1.2rem 0;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# ================================================================
# HẰNG SỐ
# ================================================================
FEEDBACK_TYPES = [
    {"code": "an_ninh",               "title": "An ninh trật tự"},
    {"code": "moi_truong",            "title": "Môi trường"},
    {"code": "chinh_sach",            "title": "Chính sách, chế độ"},
    {"code": "thu_tuc_hanh_chinh",    "title": "Thủ tục hành chính"},
    {"code": "khac",                  "title": "Khác"},
]
FEEDBACK_CODE_TO_TITLE = {t["code"]: t["title"] for t in FEEDBACK_TYPES}

NEWS_CATEGORIES = [
    ("thong_bao",           "Thông báo"),
    ("hoat_dong",           "Hoạt động"),
    ("chinh_sach",          "Chính sách"),
    ("huong_dan_nghiep_vu", "Hướng dẫn nghiệp vụ"),
]

FEEDBACK_STATUSES = [
    ("moi",        "Mới"),
    ("dang_xu_ly", "Đang xử lý"),
    ("da_xu_ly",   "Đã xử lý"),
]
FEEDBACK_STATUS_TITLE = dict(FEEDBACK_STATUSES)

QUESTION_TYPES = [
    ("single_choice", "Chọn 1 đáp án"),
    ("multi_choice",  "Chọn nhiều đáp án"),
    ("text",          "Trả lời tự do"),
]
QUESTION_TYPE_TITLE = dict(QUESTION_TYPES)

COLOR_RED   = "#C8102E"
COLOR_GOLD  = "#F5A623"
COLOR_NAVY  = "#0D1B2A"
COLOR_GREEN = "#16A34A"

# ================================================================
# SUPABASE
# ================================================================
@st.cache_resource
def get_supabase() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )

supabase = get_supabase()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ================================================================
# ĐĂNG NHẬP
# ================================================================
def check_password() -> bool:
    def _entered():
        if st.session_state.get("pw") == st.secrets["ADMIN_PASSWORD"]:
            st.session_state["auth_ok"] = True
            del st.session_state["pw"]
        else:
            st.session_state["auth_ok"] = False

    if st.session_state.get("auth_ok"):
        return True

    col_mid = st.columns([1, 1.5, 1])[1]
    with col_mid:
        st.markdown("""
        <div style="text-align:center;padding:2rem 0 1rem">
            <span style="font-size:3rem">🏛️</span>
            <h2 style="color:#0D1B2A;margin:.5rem 0 .2rem">Quản trị Mini App</h2>
            <p style="color:#6B7280;font-size:.9rem">Tuyên giáo và Dân vận Tuyên Quang</p>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("Mật khẩu quản trị", type="password",
                      on_change=_entered, key="pw")
        if st.session_state.get("auth_ok") is False:
            st.error("Sai mật khẩu, vui lòng thử lại.")
    return False


if not check_password():
    st.stop()

# ================================================================
# HEADER
# ================================================================
st.markdown("""
<div class="admin-header">
    <span style="font-size:2.2rem">🏛️</span>
    <div>
        <h1>Quản trị Mini App</h1>
        <p class="subtitle">Ban Tuyên giáo và Dân vận · Tỉnh ủy Tuyên Quang</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ================================================================
# TABS
# ================================================================
tab_overview, tab_news, tab_feedback, tab_survey, tab_survey_result = st.tabs(
    ["📊 Tổng quan", "📰 Tin tức", "💬 Phản ánh", "📋 Khảo sát", "📈 Kết quả KS"]
)


# ================================================================
# TIỆN ÍCH THỐNG KÊ
# ================================================================
PERIOD_OPTIONS = {
    "Tháng này":  0,
    "Quý này":    1,
    "6 tháng":    2,
    "9 tháng":    3,
    "Năm nay":    4,
}

def get_period_start(option: str) -> datetime:
    now = datetime.now(timezone.utc)
    if option == "Tháng này":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if option == "Quý này":
        q_month = ((now.month - 1) // 3) * 3 + 1
        return now.replace(month=q_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    if option == "6 tháng":
        return (now - relativedelta(months=6)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
    if option == "9 tháng":
        return (now - relativedelta(months=9)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
    if option == "Năm nay":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def parse_dt(s) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def to_month_label(dt: datetime) -> str:
    return dt.strftime("%m/%Y")


def make_monthly_df(rows, date_field: str, period_start: datetime) -> pd.DataFrame:
    """Đếm số bản ghi theo tháng trong khoảng thời gian đã chọn."""
    filtered = []
    for r in rows:
        dt = parse_dt(r.get(date_field))
        if dt and dt >= period_start:
            filtered.append(dt)

    if not filtered:
        return pd.DataFrame(columns=["Tháng", "Số lượng"])

    months_series = pd.Series([to_month_label(d) for d in filtered])
    counts = months_series.value_counts().sort_index().reset_index()
    counts.columns = ["Tháng", "Số lượng"]
    return counts


# ================================================================
# TAB 0: TỔNG QUAN
# ================================================================
with tab_overview:

    # Chọn khoảng thời gian
    col_period, col_spacer = st.columns([2, 5])
    with col_period:
        selected_period = st.selectbox(
            "📅 Khoảng thời gian",
            options=list(PERIOD_OPTIONS.keys()),
            index=4,       # mặc định: Năm nay
            key="period_select",
        )

    period_start = get_period_start(selected_period)

    # --- Lấy dữ liệu ---
    with st.spinner("Đang tải dữ liệu..."):
        all_news      = supabase.table("news").select("id,is_published,created_at,category").execute().data or []
        all_feedback  = supabase.table("feedback").select("id,status,category,created_at").execute().data or []
        all_surveys   = supabase.table("surveys").select("id,is_active,created_at").execute().data or []
        all_responses = supabase.table("survey_responses").select("id,survey_id,submitted_at").execute().data or []

    # --- Lọc theo khoảng thời gian ---
    def in_period(rows, field):
        return [r for r in rows if parse_dt(r.get(field)) and parse_dt(r.get(field)) >= period_start]

    news_period      = in_period(all_news,      "created_at")
    feedback_period  = in_period(all_feedback,  "created_at")
    surveys_period   = in_period(all_surveys,   "created_at")
    responses_period = in_period(all_responses, "submitted_at")

    news_published  = [r for r in news_period if r.get("is_published")]
    fb_new          = [r for r in feedback_period if r.get("status") == "moi"]
    surveys_active  = [r for r in all_surveys if r.get("is_active")]

    # --- Metric cards ---
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="num">{len(news_published)}</div>
            <div class="label">📰 Tin đã đăng</div>
            <div class="delta">/ {len(news_period)} tin tổng cộng</div>
        </div>
        <div class="metric-card gold">
            <div class="num">{len(feedback_period)}</div>
            <div class="label">💬 Phản ánh nhận được</div>
            <div class="delta">{len(fb_new)} chưa xử lý</div>
        </div>
        <div class="metric-card navy">
            <div class="num">{len(surveys_active)}</div>
            <div class="label">📋 Khảo sát đang mở</div>
            <div class="delta">/ {len(all_surveys)} khảo sát tổng</div>
        </div>
        <div class="metric-card green">
            <div class="num">{len(responses_period)}</div>
            <div class="label">📈 Lượt trả lời KS</div>
            <div class="delta">trong {selected_period.lower()}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)

    # --- Biểu đồ ---
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown('<span class="section-title">Tin tức theo tháng</span>', unsafe_allow_html=True)
        df_news = make_monthly_df(news_period, "created_at", period_start)
        if not df_news.empty:
            fig_news = px.bar(
                df_news, x="Tháng", y="Số lượng",
                color_discrete_sequence=[COLOR_RED],
                text="Số lượng",
            )
            fig_news.update_traces(textposition="outside")
            fig_news.update_layout(
                margin=dict(t=20, b=20, l=0, r=0),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(family="sans-serif", size=12),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
                height=280,
            )
            st.plotly_chart(fig_news, use_container_width=True)
        else:
            st.info("Không có tin tức nào trong khoảng này.")

    with col_chart2:
        st.markdown('<span class="section-title">Phản ánh theo trạng thái</span>', unsafe_allow_html=True)
        if feedback_period:
            status_counts = {}
            for r in feedback_period:
                s = FEEDBACK_STATUS_TITLE.get(r.get("status"), "Mới")
                status_counts[s] = status_counts.get(s, 0) + 1

            df_fb_status = pd.DataFrame(
                {"Trạng thái": list(status_counts.keys()),
                 "Số lượng":   list(status_counts.values())}
            )
            fig_fb = px.pie(
                df_fb_status, names="Trạng thái", values="Số lượng",
                color_discrete_sequence=[COLOR_RED, COLOR_GOLD, COLOR_GREEN],
                hole=0.45,
            )
            fig_fb.update_traces(textposition="outside", textinfo="label+value")
            fig_fb.update_layout(
                margin=dict(t=20, b=20, l=0, r=0),
                paper_bgcolor="white",
                font=dict(family="sans-serif", size=12),
                showlegend=False,
                height=280,
            )
            st.plotly_chart(fig_fb, use_container_width=True)
        else:
            st.info("Không có phản ánh nào trong khoảng này.")

    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        st.markdown('<span class="section-title">Phản ánh theo tháng</span>', unsafe_allow_html=True)
        df_fb_month = make_monthly_df(feedback_period, "created_at", period_start)
        if not df_fb_month.empty:
            fig_fb_month = px.bar(
                df_fb_month, x="Tháng", y="Số lượng",
                color_discrete_sequence=[COLOR_GOLD],
                text="Số lượng",
            )
            fig_fb_month.update_traces(textposition="outside")
            fig_fb_month.update_layout(
                margin=dict(t=20, b=20, l=0, r=0),
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family="sans-serif", size=12),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
                height=280,
            )
            st.plotly_chart(fig_fb_month, use_container_width=True)
        else:
            st.info("Không có phản ánh nào trong khoảng này.")

    with col_chart4:
        st.markdown('<span class="section-title">Phản ánh theo loại</span>', unsafe_allow_html=True)
        if feedback_period:
            cat_counts = {}
            for r in feedback_period:
                c = FEEDBACK_CODE_TO_TITLE.get(r.get("category"), "Khác")
                cat_counts[c] = cat_counts.get(c, 0) + 1
            df_cat = pd.DataFrame({
                "Loại":     list(cat_counts.keys()),
                "Số lượng": list(cat_counts.values()),
            }).sort_values("Số lượng", ascending=True)
            fig_cat = px.bar(
                df_cat, x="Số lượng", y="Loại",
                orientation="h",
                color_discrete_sequence=[COLOR_NAVY],
                text="Số lượng",
            )
            fig_cat.update_traces(textposition="outside")
            fig_cat.update_layout(
                margin=dict(t=20, b=20, l=0, r=0),
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family="sans-serif", size=12),
                xaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
                yaxis=dict(showgrid=False),
                height=280,
            )
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Không có dữ liệu phân loại.")

    # Lượt trả lời KS theo tháng
    st.markdown('<span class="section-title">Lượt trả lời khảo sát theo tháng</span>', unsafe_allow_html=True)
    df_resp = make_monthly_df(responses_period, "submitted_at", period_start)
    if not df_resp.empty:
        fig_resp = px.bar(
            df_resp, x="Tháng", y="Số lượng",
            color_discrete_sequence=[COLOR_GREEN],
            text="Số lượng",
        )
        fig_resp.update_traces(textposition="outside")
        fig_resp.update_layout(
            margin=dict(t=20, b=20, l=0, r=0),
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="sans-serif", size=12),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
            height=260,
        )
        st.plotly_chart(fig_resp, use_container_width=True)
    else:
        st.info("Không có lượt trả lời nào trong khoảng này.")


# ==================================================================
# TAB 1: TIN TỨC
# ==================================================================
with tab_news:
    st.markdown('<span class="section-title">Đăng tin mới</span>', unsafe_allow_html=True)

    with st.expander("➕ Thêm tin mới", expanded=False):
        with st.form("form_new_news", clear_on_submit=True):
            n_title = st.text_input("Tiêu đề *")
            n_summary = st.text_area("Tóm tắt ngắn (hiện ở danh sách)", height=70)
            n_content = st.text_area("Nội dung đầy đủ *", height=200)
            col1, col2 = st.columns(2)
            with col1:
                n_category = st.selectbox(
                    "Phân loại",
                    options=[c[0] for c in NEWS_CATEGORIES],
                    format_func=lambda c: dict(NEWS_CATEGORIES)[c],
                )
                n_cover_image_url = st.text_input("Link ảnh đại diện (nếu có)")
            with col2:
                n_external_link = st.text_input("Link bài viết gốc (nếu chia sẻ lại)")
                n_is_published = st.checkbox("Đăng công khai ngay", value=True)

            if st.form_submit_button("📤 Đăng tin", type="primary"):
                if not n_title.strip() or not n_content.strip():
                    st.error("Vui lòng nhập Tiêu đề và Nội dung.")
                else:
                    supabase.table("news").insert({
                        "title":           n_title.strip(),
                        "summary":         n_summary.strip() or None,
                        "content":         n_content.strip(),
                        "category":        n_category,
                        "cover_image_url": n_cover_image_url.strip() or None,
                        "external_link":   n_external_link.strip() or None,
                        "is_published":    n_is_published,
                        "published_at":    now_iso() if n_is_published else None,
                    }).execute()
                    st.success("Đăng tin thành công!")
                    st.rerun()

    st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)
    st.markdown('<span class="section-title">Danh sách tin đã đăng</span>', unsafe_allow_html=True)

    news_resp = (
        supabase.table("news").select("*").order("created_at", desc=True).execute()
    )
    news_rows = news_resp.data or []

    if not news_rows:
        st.info("Chưa có tin nào.")

    for row in news_rows:
        status_label = "🟢 Đã đăng" if row.get("is_published") else "⚪ Bản nháp"
        with st.expander(f"{status_label} — {row['title']}"):
            with st.form(f"form_edit_news_{row['id']}"):
                e_title   = st.text_input("Tiêu đề", value=row["title"])
                e_summary = st.text_area("Tóm tắt ngắn", value=row.get("summary") or "", height=70)
                e_content = st.text_area("Nội dung đầy đủ", value=row.get("content") or "", height=200)
                col1, col2 = st.columns(2)
                with col1:
                    cat_options = [c[0] for c in NEWS_CATEGORIES]
                    cur_cat = row.get("category") or cat_options[0]
                    e_category = st.selectbox(
                        "Phân loại",
                        options=cat_options,
                        index=cat_options.index(cur_cat) if cur_cat in cat_options else 0,
                        format_func=lambda c: dict(NEWS_CATEGORIES)[c],
                        key=f"cat_{row['id']}",
                    )
                    e_cover = st.text_input("Link ảnh đại diện", value=row.get("cover_image_url") or "")
                with col2:
                    e_link      = st.text_input("Link bài viết gốc", value=row.get("external_link") or "")
                    e_published = st.checkbox("Đăng công khai", value=bool(row.get("is_published")))

                col_save, col_delete = st.columns([3, 1])
                with col_save:
                    save_clicked   = st.form_submit_button("💾 Lưu thay đổi", use_container_width=True)
                with col_delete:
                    delete_clicked = st.form_submit_button("🗑️ Xoá", use_container_width=True)

                if save_clicked:
                    was_published = bool(row.get("is_published"))
                    update_data   = {
                        "title":           e_title.strip(),
                        "summary":         e_summary.strip() or None,
                        "content":         e_content.strip(),
                        "category":        e_category,
                        "cover_image_url": e_cover.strip() or None,
                        "external_link":   e_link.strip() or None,
                        "is_published":    e_published,
                        "updated_at":      now_iso(),
                    }
                    if e_published and not was_published:
                        update_data["published_at"] = now_iso()
                    supabase.table("news").update(update_data).eq("id", row["id"]).execute()
                    st.success("Đã lưu thay đổi!")
                    st.rerun()

                if delete_clicked:
                    supabase.table("news").delete().eq("id", row["id"]).execute()
                    st.success("Đã xoá tin.")
                    st.rerun()


# ==================================================================
# TAB 2: PHẢN ÁNH
# ==================================================================
with tab_feedback:
    st.markdown('<span class="section-title">Danh sách phản ánh</span>', unsafe_allow_html=True)

    col_filter, col_spacer = st.columns([2, 4])
    with col_filter:
        filter_status = st.selectbox(
            "Lọc theo trạng thái",
            options=["tat_ca"] + [s[0] for s in FEEDBACK_STATUSES],
            format_func=lambda s: "Tất cả" if s == "tat_ca" else FEEDBACK_STATUS_TITLE[s],
        )

    fb_query = supabase.table("feedback").select("*").order("created_at", desc=True)
    if filter_status != "tat_ca":
        fb_query = fb_query.eq("status", filter_status)
    fb_rows = fb_query.execute().data or []

    if not fb_rows:
        st.info("Không có phản ánh nào.")

    status_icon = {"moi": "🆕", "dang_xu_ly": "⏳", "da_xu_ly": "✅"}

    for row in fb_rows:
        type_label = FEEDBACK_CODE_TO_TITLE.get(row.get("category"), "Khác")
        icon       = status_icon.get(row.get("status"), "🆕")
        with st.expander(f"{icon} [{type_label}] {row['title']}"):
            who = "Ẩn danh" if row.get("is_anonymous") else (
                row.get("full_name") or "(không rõ tên)"
            )
            st.caption(
                f"Người gửi: **{who}**"
                + (f" · SĐT: {row['phone']}" if row.get("phone") else "")
                + f" · Zalo ID: {row.get('zalo_user_id', '')}"
                + f" · Gửi lúc: {row.get('created_at', '')[:10]}"
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
                    index=status_options.index(cur_status) if cur_status in status_options else 0,
                    format_func=lambda s: FEEDBACK_STATUS_TITLE[s],
                    key=f"status_{row['id']}",
                )
                new_response = st.text_area(
                    "Phản hồi của Ban",
                    value=row.get("admin_response") or "",
                    height=120,
                )
                if st.form_submit_button("💾 Lưu phản hồi"):
                    update_data = {
                        "status":         new_status,
                        "admin_response": new_response.strip() or None,
                    }
                    if new_response.strip() and not row.get("admin_response"):
                        update_data["responded_at"] = now_iso()
                    supabase.table("feedback").update(update_data).eq("id", row["id"]).execute()
                    st.success("Đã lưu!")
                    st.rerun()


# ==================================================================
# TAB 3: KHẢO SÁT
# ==================================================================
with tab_survey:
    st.markdown('<span class="section-title">Tạo khảo sát mới</span>', unsafe_allow_html=True)

    if "qb_count" not in st.session_state:
        st.session_state.qb_count = 1

    s_title       = st.text_input("Tên khảo sát *", key="new_survey_title")
    s_description = st.text_area("Mô tả ngắn", key="new_survey_desc", height=70)

    col_active, col_enddate = st.columns(2)
    with col_active:
        s_is_active = st.checkbox("Mở khảo sát ngay", value=True, key="new_survey_active")
    with col_enddate:
        s_has_enddate = st.checkbox("Đặt hạn trả lời", key="new_survey_has_enddate")
        s_enddate = None
        if s_has_enddate:
            s_enddate = st.date_input("Hạn trả lời", key="new_survey_enddate")

    st.markdown("**Danh sách câu hỏi**")

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
            for kp in ("q_text_", "q_type_", "q_options_"):
                st.session_state.pop(f"{kp}{last}", None)
            st.session_state.qb_count -= 1
            st.rerun()

    if st.button("✅ Tạo khảo sát", type="primary"):
        questions = []
        for i in range(st.session_state.qb_count):
            text = (st.session_state.get(f"q_text_{i}") or "").strip()
            if not text:
                continue
            q_type = st.session_state.get(f"q_type_{i}", "text")
            question = {"id": f"q{i + 1}", "text": text, "type": q_type}
            if q_type in ("single_choice", "multi_choice"):
                raw = st.session_state.get(f"q_options_{i}", "") or ""
                question["options"] = [o.strip() for o in raw.splitlines() if o.strip()]
            questions.append(question)

        if not s_title.strip():
            st.error("Vui lòng nhập tên khảo sát.")
        elif not questions:
            st.error("Vui lòng nhập ít nhất 1 câu hỏi.")
        else:
            insert_data = {
                "title":       s_title.strip(),
                "description": s_description.strip() or None,
                "questions":   questions,
                "is_active":   s_is_active,
            }
            if s_enddate:
                insert_data["end_date"] = datetime.combine(
                    s_enddate, datetime.max.time()
                ).isoformat()
            supabase.table("surveys").insert(insert_data).execute()
            st.success("Đã tạo khảo sát!")
            for i in range(st.session_state.qb_count):
                for kp in ("q_text_", "q_type_", "q_options_"):
                    st.session_state.pop(f"{kp}{i}", None)
            st.session_state.qb_count = 1
            for k in ("new_survey_title", "new_survey_desc", "new_survey_active",
                      "new_survey_has_enddate", "new_survey_enddate"):
                st.session_state.pop(k, None)
            st.rerun()

    st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)
    st.markdown('<span class="section-title">Danh sách khảo sát</span>', unsafe_allow_html=True)

    survey_rows = (
        supabase.table("surveys").select("*").order("created_at", desc=True).execute().data or []
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
                        supabase.table("surveys").update({"is_active": False}).eq("id", row["id"]).execute()
                        st.rerun()
                else:
                    if st.button("▶️ Mở lại", key=f"open_{row['id']}"):
                        supabase.table("surveys").update({"is_active": True}).eq("id", row["id"]).execute()
                        st.rerun()
            with col2:
                if st.button("🗑️ Xoá khảo sát", key=f"del_survey_{row['id']}"):
                    supabase.table("surveys").delete().eq("id", row["id"]).execute()
                    st.rerun()


# ==================================================================
# TAB 4: KẾT QUẢ KHẢO SÁT
# ==================================================================
with tab_survey_result:
    st.markdown('<span class="section-title">Xem kết quả khảo sát</span>', unsafe_allow_html=True)

    survey_rows_ks = (
        supabase.table("surveys").select("*").order("created_at", desc=True).execute().data or []
    )

    if not survey_rows_ks:
        st.info("Chưa có khảo sát nào để xem kết quả.")
    else:
        survey_options = {row["id"]: row["title"] for row in survey_rows_ks}
        selected_id    = st.selectbox(
            "Chọn khảo sát",
            options=list(survey_options.keys()),
            format_func=lambda sid: survey_options[sid],
        )
        selected_survey = next(r for r in survey_rows_ks if r["id"] == selected_id)
        questions       = selected_survey.get("questions") or []

        responses = (
            supabase.table("survey_responses")
            .select("*").eq("survey_id", selected_id).execute().data or []
        )

        st.metric("Tổng số lượt trả lời", len(responses))

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
                        df_tally = pd.DataFrame(
                            {"Đáp án": list(tally.keys()),
                             "Số lượt": list(tally.values())}
                        ).sort_values("Số lượt", ascending=False)
                        fig_q = px.bar(
                            df_tally, x="Đáp án", y="Số lượt",
                            color_discrete_sequence=[COLOR_RED],
                            text="Số lượt",
                        )
                        fig_q.update_traces(textposition="outside")
                        fig_q.update_layout(
                            margin=dict(t=10, b=10, l=0, r=0),
                            plot_bgcolor="white", paper_bgcolor="white",
                            height=250, font=dict(size=12),
                            xaxis=dict(showgrid=False),
                            yaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
                        )
                        st.plotly_chart(fig_q, use_container_width=True)
                    else:
                        st.caption("Chưa có ai trả lời câu này.")
                else:
                    texts = [(resp.get("answers") or {}).get(q["id"]) for resp in responses]
                    texts = [t for t in texts if t]
                    if texts:
                        for t in texts:
                            st.write(f"- {t}")
                    else:
                        st.caption("Chưa có ai trả lời câu này.")
                st.divider()

            # Xuất CSV
            flat_rows = []
            for resp in responses:
                flat = {
                    "submitted_at":  resp.get("submitted_at"),
                    "zalo_user_id":  resp.get("zalo_user_id"),
                }
                for q in questions:
                    answer = (resp.get("answers") or {}).get(q["id"])
                    if isinstance(answer, list):
                        answer = ", ".join(answer)
                    flat[q["text"]] = answer
                flat_rows.append(flat)

            df_export = pd.DataFrame(flat_rows)
            st.download_button(
                "⬇️ Tải dữ liệu thô (CSV)",
                data=df_export.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"ket_qua_khao_sat_{selected_id}.csv",
                mime="text/csv",
            )
