import json
import re
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="V12 AI ວິເຄາະບານ",
    page_icon="⚽",
    layout="wide"
)

API_URL = "https://goal7.co/data/update2_backup_json.php"

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://goal7.co/",
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6,en;q=0.5",
}


def ຂໍ້ຄວາມ(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def ຕົວເລກ(x: Any, default: float = 0.0) -> float:
    try:
        s = str(x).replace(",", "").replace("%", "").strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def ດຶງຂໍ້ມູນ(cookie: str) -> Dict[str, Any]:
    headers = HEADERS_BASE.copy()
    if cookie.strip():
        headers["Cookie"] = cookie.strip()

    try:
        r = requests.get(API_URL, headers=headers, timeout=25)
        return {
            "ສຳເລັດ": r.status_code == 200,
            "ສະຖານະ": r.status_code,
            "ຂໍ້ຄວາມ": r.text,
            "header": dict(r.headers),
            "error": "",
        }
    except Exception as e:
        return {
            "ສຳເລັດ": False,
            "ສະຖານະ": 0,
            "ຂໍ້ຄວາມ": "",
            "header": {},
            "error": str(e),
        }


def ແປງ_json(text: str) -> List[list]:
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
    except Exception:
        pass
    return []


def ສ້າງຄໍລຳ(max_len: int) -> List[str]:
    cols = [
        "ລະຫັດ",
        "ປະຕູເຈົ້າບ້ານ",
        "ປະຕູທີມຢາມ",
        "ສະຖານະ1",
        "ສະຖານະ2",
        "ສະຖານະ3",
        "ສະຖານະ4",
        "ສະຖານະ5",
        "ເວລາ",
        "ເຈົ້າບ້ານ",
        "ທີມຢາມ",
        "ລີກ",
    ]
    while len(cols) < max_len:
        cols.append(f"ດິບ_{len(cols)}")
    return cols[:max_len]


def ແປງເປັນຕາຕະລາງ(rows: List[list]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    max_len = max(len(r) for r in rows if isinstance(r, list))
    cols = ສ້າງຄໍລຳ(max_len)

    fixed = []
    for r in rows:
        if not isinstance(r, list):
            continue
        rr = r + [""] * (max_len - len(r))
        fixed.append(rr[:max_len])

    return pd.DataFrame(fixed, columns=cols)


def ວິເຄາະແຖວ(row: pd.Series) -> Dict[str, Any]:
    ປະຕູເຈົ້າ = ຕົວເລກ(row.get("ປະຕູເຈົ້າບ້ານ", 0))
    ປະຕູຢາມ = ຕົວເລກ(row.get("ປະຕູທີມຢາມ", 0))

    ຄະແນນ = 50
    ເຫດຜົນ = []
    ສັນຍານ = "ລໍຖ້າ"

    if ປະຕູເຈົ້າ > ປະຕູຢາມ:
        ຄະແນນ += 12
        ສັນຍານ = "ເຈົ້າບ້ານໄດ້ປຽບ"
        ເຫດຜົນ.append("ເຈົ້າບ້ານນຳປະຕູ")
    elif ປະຕູຢາມ > ປະຕູເຈົ້າ:
        ຄະແນນ += 12
        ສັນຍານ = "ທີມຢາມໄດ້ປຽບ"
        ເຫດຜົນ.append("ທີມຢາມນຳປະຕູ")
    else:
        ເຫດຜົນ.append("ຄະແນນຍັງສູສີ")

    raw = " ".join([ຂໍ້ຄວາມ(v) for v in row.values])
    ລາຄາ = [ຕົວເລກ(x) for x in re.findall(r"\b\d+\.\d+\b", raw)]

    if ລາຄາ:
        ຄ່າສະເລ່ຍ = sum(ລາຄາ[:8]) / min(len(ລາຄາ), 8)
        if ຄ່າສະເລ່ຍ >= 2.00:
            ຄະແນນ += 10
            ເຫດຜົນ.append("ພົບລາຄາທີ່ອາດມີ Value")
        else:
            ຄະແນນ += 4
            ເຫດຜົນ.append("ມີຂໍ້ມູນລາຄາປະກອບ")

    if len(raw) > 80:
        ຄະແນນ += 5
        ເຫດຜົນ.append("ຂໍ້ມູນດິບມີຫຼາຍພໍສຳລັບວິເຄາະ")

    ຄະແນນ = max(1, min(99, ຄະແນນ))

    if ຄະແນນ >= 75:
        ລະດັບ = "🔥 ຄູ່ເດັດ"
    elif ຄະແນນ >= 63:
        ລະດັບ = "✅ ນ່າສົນໃຈ"
    elif ຄະແນນ >= 55:
        ລະດັບ = "🟡 ພໍເບິ່ງໄດ້"
    else:
        ລະດັບ = "⚠️ ລໍຖ້າ"

    return {
        "ສັນຍານ": ສັນຍານ,
        "ຄວາມໝັ້ນໃຈ": ຄະແນນ,
        "ລະດັບ": ລະດັບ,
        "ເຫດຜົນ": " | ".join(ເຫດຜົນ),
    }


def ສ້າງຜົນວິເຄາະ(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        a = ວິເຄາະແຖວ(r)
        rows.append({
            "ລີກ": ຂໍ້ຄວາມ(r.get("ລີກ", "")),
            "ລະຫັດ": ຂໍ້ຄວາມ(r.get("ລະຫັດ", "")),
            "ເວລາ": ຂໍ້ຄວາມ(r.get("ເວລາ", "")),
            "ເຈົ້າບ້ານ": ຂໍ້ຄວາມ(r.get("ເຈົ້າບ້ານ", "")),
            "ທີມຢາມ": ຂໍ້ຄວາມ(r.get("ທີມຢາມ", "")),
            "ຄະແນນ": f"{ຂໍ້ຄວາມ(r.get('ປະຕູເຈົ້າບ້ານ',''))}-{ຂໍ້ຄວາມ(r.get('ປະຕູທີມຢາມ',''))}",
            "ສັນຍານ": a["ສັນຍານ"],
            "ຄວາມໝັ້ນໃຈ": a["ຄວາມໝັ້ນໃຈ"],
            "ລະດັບ": a["ລະດັບ"],
            "ເຫດຜົນ": a["ເຫດຜົນ"],
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("ຄວາມໝັ້ນໃຈ", ascending=False)
    return out


st.title("⚽ V12 AI ວິເຄາະບານ")
st.caption("ດຶງ XHR ຈິງ + Cookie + ວິເຄາະ AI + ຈັດອັນດັບຄູ່ເດັດ")

cookie = st.text_area(
    "ວາງ Cookie ທັງແຖວ",
    height=120,
    placeholder="_ga=...; cf_clearance=...; PHPSESSID=..."
)

show_raw = st.checkbox("ສະແດງຂໍ້ມູນດິບ", value=False)

if st.button("🚀 ດຶງຂໍ້ມູນ ແລະ ວິເຄາະ AI", use_container_width=True):
    res = ດຶງຂໍ້ມູນ(cookie)

    c1, c2, c3 = st.columns(3)
    c1.metric("ສະຖານະ", res["ສະຖານະ"])
    c2.metric("ປະເພດຂໍ້ມູນ", res["header"].get("content-type", "-"))
    c3.metric("ຂະໜາດ", len(res["ຂໍ້ຄວາມ"]))

    if not res["ສຳເລັດ"]:
        st.error(res["error"] or res["ຂໍ້ຄວາມ"][:500])
        st.stop()

    rows = ແປງ_json(res["ຂໍ້ຄວາມ"])
    if not rows:
        st.warning("ດຶງໄດ້ ແຕ່ແປງ JSON ບໍ່ໄດ້")
        st.code(res["ຂໍ້ຄວາມ"][:1000])
        st.stop()

    df = ແປງເປັນຕາຕະລາງ(rows)
    df_ai = ສ້າງຜົນວິເຄາະ(df)

    st.success(f"ດຶງຂໍ້ມູນໄດ້ {len(df)} ແຖວ")

    st.subheader("🔥 5 ຄູ່ເດັດອັນດັບຕົ້ນ")
    st.dataframe(df_ai.head(5), use_container_width=True)

    st.subheader("📊 ຜົນວິເຄາະທັງໝົດ")
    st.dataframe(df_ai, use_container_width=True)

    st.subheader("📋 ຂໍ້ມູນທີ່ແປງແລ້ວ")
    st.dataframe(df, use_container_width=True)

    if show_raw:
        st.subheader("ຂໍ້ມູນດິບ")
        st.json(rows[:10])

st.info("Cookie ຈະໝົດອາຍຸໄດ້. ຖ້າດຶງບໍ່ໄດ້ ໃຫ້ຈັບ Cookie ໃໝ່ຈາກ HTTP Sniffer.")
