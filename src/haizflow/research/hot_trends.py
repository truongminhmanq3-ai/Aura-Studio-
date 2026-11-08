"""Hot Trends & Trending Keywords provider for Douyin and Xiaohongshu."""
from __future__ import annotations

import json
import logging
import ssl
import threading
import time
from typing import Any
from urllib import request

import certifi

logger = logging.getLogger(__name__)

# Curated high-converting niche keywords with bilingual Vietnamese hints
NICHE_TRENDS: dict[str, list[dict[str, str]]] = {
    "all": [
        {"keyword": "露营新手指南", "label": "🏕️ Cẩm nang cắm trại cho người mới", "category": "camping"},
        {"keyword": "幼犬防咬训练", "label": "🐶 Dạy chó con không cắn tay", "category": "pets"},
        {"keyword": "独居好物分享", "label": "🏠 Đồ gia dụng thông minh sống 1 mình", "category": "home"},
        {"keyword": "空气炸锅美食", "label": "🍳 Món ngon nồi chiên không dầu", "category": "food"},
        {"keyword": "新手养猫必存", "label": "🐱 Checklist nuôi mèo không tốn kém", "category": "pets"},
        {"keyword": "沉浸式收纳整理", "label": "✨ Mẹo dọn dẹp sắp xếp phòng gọn gàng", "category": "home"},
        {"keyword": "早八通勤伪素颜", "label": "💄 Trang điểm 5 phút tự nhiên đi làm", "category": "beauty"},
        {"keyword": "户外露营装备推荐", "label": "⛺ Đồ cắm trại dã ngoại bền rẻ", "category": "camping"},
    ],
    "pets": [
        {"keyword": "幼犬防咬训练", "label": "🐶 Dạy chó con bỏ tật cắn tay", "category": "pets"},
        {"keyword": "新手养猫必存", "label": "🐱 Cẩm nang người mới nuôi mèo", "category": "pets"},
        {"keyword": "狗狗定点上厕所", "label": "🚽 Dạy chó đi vệ sinh đúng chỗ", "category": "pets"},
        {"keyword": "自制猫饭生骨肉", "label": "🥩 Tự làm pate thức ăn cho mèo", "category": "pets"},
        {"keyword": "平价宠物好物测评", "label": "⭐ Review đồ thú cưng ngon bổ rẻ", "category": "pets"},
    ],
    "home": [
        {"keyword": "独居好物分享", "label": "🏠 Đồ gia dụng cho người sống 1 mình", "category": "home"},
        {"keyword": "沉浸式收纳整理", "label": "✨ Mẹo dọn dẹp và sắp xếp nhà cửa", "category": "home"},
        {"keyword": "出租房低成本改造", "label": "🛠️ Cải tạo phòng trọ chi phí rẻ", "category": "home"},
        {"keyword": "厨房清洁黑科技", "label": "🧼 Đồ tẩy rửa nhà bếp siêu sạch", "category": "home"},
        {"keyword": "提升幸福感居家小物件", "label": "🛋️ Đồ decor phòng ngủ ấm cúng", "category": "home"},
    ],
    "camping": [
        {"keyword": "露营新手指南", "label": "🏕️ Cẩm nang cắm trại cho người mới", "category": "camping"},
        {"keyword": "户外露营装备推荐", "label": "⛺ Đồ cắm trại dã ngoại tiết kiệm", "category": "camping"},
        {"keyword": "湖边露营体验", "label": "🌲 Trải nghiệm cắm trại ven hồ", "category": "camping"},
        {"keyword": "露营野炊做饭", "label": "🍲 Món ăn dã ngoại ngoài trời cực dễ", "category": "camping"},
        {"keyword": "汽车后备箱露营", "label": "🚗 Độ cốp xe ô tô đi cắm trại", "category": "camping"},
    ],
    "food": [
        {"keyword": "空气炸锅美食", "label": "🍳 Món ngon nồi chiên không dầu", "category": "food"},
        {"keyword": "一人食快手晚餐", "label": "🍜 Bữa tối 1 người nấu trong 10 phút", "category": "food"},
        {"keyword": "减脂低卡掉秤餐", "label": "🥗 Thực đơn giảm cân ăn kiêng ngon", "category": "food"},
        {"keyword": "街头小吃家庭复刻", "label": "🍢 Làm đồ ăn vặt đường phố tại nhà", "category": "food"},
        {"keyword": "自制神仙饮品", "label": "🍹 Tự pha đồ uống trà sữa tại nhà", "category": "food"},
    ],
    "beauty": [
        {"keyword": "早八通勤伪素颜", "label": "💄 Trang điểm 5 phút tự nhiên đi làm", "category": "beauty"},
        {"keyword": "精简护肤抗老流程", "label": "✨ Quy trình skincare tối giản hiệu quả", "category": "beauty"},
        {"keyword": "油痘肌平价护肤", "label": "🌿 Skincare da dầu mụn học sinh sinh viên", "category": "beauty"},
        {"keyword": "日常显瘦发型打理", "label": "💇 Kiểu tóc che khuyết điểm mặt tròn", "category": "beauty"},
    ],
}

_CACHE_LOCK = threading.Lock()
_CACHED_DOUYIN_HOT: list[dict[str, Any]] = []
_LAST_FETCH_TIME: float = 0.0
_CACHE_TTL_SECONDS = 900.0  # 15 minutes


def fetch_douyin_hot_board(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch live real-time trending search board from Douyin."""
    global _CACHED_DOUYIN_HOT, _LAST_FETCH_TIME

    with _CACHE_LOCK:
        if _CACHED_DOUYIN_HOT and (time.time() - _LAST_FETCH_TIME < _CACHE_TTL_SECONDS):
            return _CACHED_DOUYIN_HOT[:limit]

    try:
        ctx = ssl.create_default_context(cafile=certifi.where())
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.douyin.com/",
            "Accept": "application/json, text/plain, */*",
        }
        req = request.Request("https://www.douyin.com/aweme/v1/web/hot/search/list/", headers=headers)
        with request.urlopen(req, context=ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_words = data.get("data", {}).get("word_list", [])

            results: list[dict[str, Any]] = []
            for idx, item in enumerate(raw_words):
                word = str(item.get("word") or "").strip()
                if not word:
                    continue
                hot_val = int(item.get("hot_value") or 0)
                hot_str = f"{hot_val / 10000:.1f}万" if hot_val >= 10000 else str(hot_val)
                label_type = item.get("label", 0)
                tag_label = "🔥 Hot" if label_type == 1 else ("⚡ Mới" if label_type == 2 else "")

                results.append({
                    "keyword": word,
                    "label": f"#{idx + 1} {word}",
                    "hot_value": hot_str,
                    "tag": tag_label,
                    "category": "douyin_hot",
                })

            if results:
                with _CACHE_LOCK:
                    _CACHED_DOUYIN_HOT = results
                    _LAST_FETCH_TIME = time.time()
                return results[:limit]

    except Exception as exc:
        logger.warning(f"Could not fetch Douyin live hot board: {exc}")

    # Fallback if network drops
    return [
        {"keyword": item["keyword"], "label": item["label"], "hot_value": "Viral", "tag": "🔥 Hot", "category": "douyin_hot"}
        for item in NICHE_TRENDS["all"][:limit]
    ]


CATEGORY_KEYWORDS_FILTER: dict[str, list[str]] = {
    "pets": ["猫", "狗", "宠", "动物", "幼犬", "小猫", "毛孩子"],
    "home": ["家", "房", "居家", "收纳", "改造", "好物", "厨房", "清洁", "卫生间", "租房", "宿舍"],
    "camping": ["露营", "户外", "野外", "帐篷", "徒步", "旅行", "自驾", "野炊", "登山", "探险"],
    "food": ["美食", "吃", "饭", "菜", "做饭", "火锅", "甜品", "奶茶", "减脂餐", "小吃", "早餐", "夜宵", "烘焙"],
    "beauty": ["妆", "美", "护肤", "穿搭", "发型", "素颜", "口红", "粉底", "变美", "防晒", "精华", "洗面奶"],
}


def get_trending_keywords(category: str = "all", limit: int = 15) -> list[dict[str, Any]]:
    """Return categorized trending keywords or live Douyin hot board."""
    if category == "douyin_hot":
        return fetch_douyin_hot_board(limit=limit)

    items = NICHE_TRENDS.get(category, NICHE_TRENDS["all"])
    
    # If category is "all", include top 3 live Douyin hot keywords at the front
    if category == "all":
        live_hot = fetch_douyin_hot_board(limit=3)
        combined = []
        for h in live_hot:
            combined.append({
                "keyword": h["keyword"],
                "label": f"🔥 {h['keyword']} ({h['hot_value']})",
                "category": "douyin_hot",
            })
        for item in items:
            combined.append(item)
        return combined[:limit]

    # For specific niche category, check if any current Douyin live hot search matches this niche
    filter_words = CATEGORY_KEYWORDS_FILTER.get(category, [])
    if filter_words:
        live_hot = fetch_douyin_hot_board(limit=50)
        matched_live = []
        for h in live_hot:
            if any(w in h["keyword"] for w in filter_words):
                matched_live.append({
                    "keyword": h["keyword"],
                    "label": f"🔥 {h['keyword']} ({h['hot_value']})",
                    "category": category,
                })
        if matched_live:
            combined = matched_live[:3] + list(items)
            return combined[:limit]

    return items[:limit]

