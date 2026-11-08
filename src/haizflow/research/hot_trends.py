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

# Curated high-converting niche keywords with bilingual Vietnamese hints across 21 creator niches
NICHE_TRENDS: dict[str, list[dict[str, str]]] = {
    "all": [
        {"keyword": "AI实用生产力工具", "label": "🤖 Tool AI tăng hiệu suất x10", "category": "tech_ai"},
        {"keyword": "一人食快手晚餐", "label": "🍳 Bữa tối 1 người nấu 10 phút", "category": "food"},
        {"keyword": "沉浸式桌面改造", "label": "🖥️ Setup góc làm việc chill", "category": "home"},
        {"keyword": "幼犬防咬训练", "label": "🐶 Dạy chó con bỏ cắn tay", "category": "pets"},
        {"keyword": "早八通勤伪素颜", "label": "💄 Makeup 5 phút tự nhiên đi làm", "category": "beauty"},
        {"keyword": "普通人攒钱存钱技巧", "label": "💰 Mẹo tiết kiệm tiền thực tế", "category": "finance"},
        {"keyword": "未解之谜真实悬案", "label": "🔍 Kỳ án có thật chưa có lời giải", "category": "mystery_history"},
        {"keyword": "沉浸式老物件翻新修复", "label": "🛠️ Phục hồi đồ cổ nát thành như mới", "category": "repair_restoration"},
        {"keyword": "摆摊真实利润揭秘", "label": "💼 Bóc trần lợi nhuận bán hàng vỉa hè", "category": "business"},
        {"keyword": "阳台种菜新手指南", "label": "🌱 Trồng rau ban công chung cư", "category": "rural_life"},
        {"keyword": "穷游保姆级攻略", "label": "🎒 Cẩm nang du lịch tiết kiệm", "category": "travel"},
        {"keyword": "微胖女生显瘦穿搭技巧", "label": "👗 Mẹo phối đồ giấu dáng", "category": "fashion"},
    ],
    "beauty": [
        {"keyword": "早八通勤伪素颜", "label": "💄 Makeup 5 phút tự nhiên đi làm", "category": "beauty"},
        {"keyword": "精简护肤抗老流程", "label": "✨ Skincare tối giản chống lão hoá", "category": "beauty"},
        {"keyword": "油痘肌平价护肤", "label": "🌿 Skincare da dầu mụn học sinh", "category": "beauty"},
        {"keyword": "日常显瘦发型打理", "label": "💇 Kiểu tóc che khuyết điểm mặt tròn", "category": "beauty"},
        {"keyword": "冷白皮防晒美白法", "label": "☀️ Mẹo chống nắng dưỡng trắng da", "category": "beauty"},
    ],
    "food": [
        {"keyword": "一人食快手晚餐", "label": "🍜 Bữa tối 1 người nấu trong 10 phút", "category": "food"},
        {"keyword": "空气炸锅美食", "label": "🍳 Món ngon nồi chiên không dầu", "category": "food"},
        {"keyword": "减脂低卡掉秤餐", "label": "🥗 Thực đơn giảm cân ăn kiêng ngon", "category": "food"},
        {"keyword": "街头小吃家庭复刻", "label": "🍢 Làm đồ ăn vặt đường phố tại nhà", "category": "food"},
        {"keyword": "自制神仙饮品", "label": "🍹 Tự pha đồ uống trà sữa tại nhà", "category": "food"},
    ],
    "fitness": [
        {"keyword": "居家无器械燃脂", "label": "🔥 Đốt mỡ tại nhà không cần tạ", "category": "fitness"},
        {"keyword": "改善体态假胯宽", "label": "🧘 Chỉnh dáng hông to chân vòng kiềng", "category": "fitness"},
        {"keyword": "新手健身房动作指导", "label": "🏋️ Hướng dẫn tập gym cho người mới", "category": "fitness"},
        {"keyword": "马甲线高效训练", "label": "⚡ Bài tập cơ bụng săn chắc nhanh", "category": "fitness"},
        {"keyword": "跑步燃脂正确姿势", "label": "🏃 Tư thế chạy bộ bền không đau khớp", "category": "fitness"},
    ],
    "finance": [
        {"keyword": "普通人攒钱存钱技巧", "label": "💰 Mẹo tiết kiệm tiền thực tế dễ áp dụng", "category": "finance"},
        {"keyword": "副业搞钱新手入门", "label": "📈 Nghề tay trái kiếm thêm thu nhập", "category": "finance"},
        {"keyword": "打工人职场向上沟通", "label": "🤝 Kỹ năng giao tiếp khéo léo với sếp", "category": "finance"},
        {"keyword": "简历优化面试干货", "label": "📝 Tối ưu CV và mẹo phỏng vấn xin việc", "category": "finance"},
        {"keyword": "理财新手避坑指南", "label": "🛡️ Tránh bẫy tài chính cho người mới", "category": "finance"},
    ],
    "home": [
        {"keyword": "沉浸式桌面改造", "label": "🖥️ Setup góc làm việc chill tối giản", "category": "home"},
        {"keyword": "独居好物分享", "label": "🏠 Đồ gia dụng thông minh sống 1 mình", "category": "home"},
        {"keyword": "沉浸式收纳整理", "label": "✨ Mẹo dọn dẹp sắp xếp phòng gọn gàng", "category": "home"},
        {"keyword": "出租房低成本改造", "label": "🛠️ Cải tạo phòng trọ chi phí hạt dẻ", "category": "home"},
        {"keyword": "提升幸福感居家好物", "label": "🛋️ Decor phòng ngủ ấm cúng hiện đại", "category": "home"},
    ],
    "travel": [
        {"keyword": "穷游穷玩保姆级攻略", "label": "🎒 Cẩm nang du lịch tiết kiệm chi phí", "category": "travel"},
        {"keyword": "小众冷门绝美旅游地", "label": "🌲 Điểm du lịch ít người biết tuyệt đẹp", "category": "travel"},
        {"keyword": "露营新手实用指南", "label": "⛺ Cắm trại dã ngoại cuối tuần cực chill", "category": "travel"},
        {"keyword": "自驾游沿途风景记录", "label": "🚗 Review cung đường phượt tự lái đẹp mê", "category": "travel"},
        {"keyword": "一个人旅行真实体验", "label": "🚶 Kinh nghiệm du lịch bụi 1 mình an toàn", "category": "travel"},
    ],
    "tech_ai": [
        {"keyword": "AI实用生产力工具", "label": "🤖 Top công cụ AI tăng hiệu suất x10", "category": "tech_ai"},
        {"keyword": "手机隐藏神仙功能", "label": "📱 Tính năng ẩn cực hay trên điện thoại", "category": "tech_ai"},
        {"keyword": "提高效率的办公技巧", "label": "⚡ Mẹo văn phòng tiết kiệm 2 giờ mỗi ngày", "category": "tech_ai"},
        {"keyword": "自媒体AI剪辑做视频", "label": "🎬 Dùng AI tạo video ngắn tự động", "category": "tech_ai"},
        {"keyword": "数码平价好物测评", "label": "🎧 Review đồ công nghệ ngon bổ rẻ", "category": "tech_ai"},
    ],
    "business": [
        {"keyword": "地摊摆摊真实利润揭秘", "label": "🍢 Bóc trần lợi nhuận bán hàng vỉa hè", "category": "business"},
        {"keyword": "开店创业踩坑经验", "label": "🏪 Bài học xương máu khi mở quán kinh doanh", "category": "business"},
        {"keyword": "爆款商品选品逻辑", "label": "📦 Tư duy chọn sản phẩm triệu đơn Douyin", "category": "business"},
        {"keyword": "小成本创业项目复盘", "label": "💡 Phân tích mô hình khởi nghiệp vốn nhỏ", "category": "business"},
        {"keyword": "实体店引流获客技巧", "label": "🎯 Cách kéo khách nườm nượp vào cửa hàng", "category": "business"},
    ],
    "psychology": [
        {"keyword": "摆脱精神内耗的习惯", "label": "🧠 Thói quen ngừng overthinking suy nghĩ nhiều", "category": "psychology"},
        {"keyword": "拒绝讨好型人格", "label": "🛡️ Học cách nói không và yêu bản thân", "category": "psychology"},
        {"keyword": "高情商沟通心理学", "label": "🗣️ Tâm lý học giao tiếp nói chuyện cuốn hút", "category": "psychology"},
        {"keyword": "睡前沉浸式情绪疗愈", "label": "🌙 Chữa lành tâm hồn bình yên trước khi ngủ", "category": "psychology"},
        {"keyword": "如何建立真正自信", "label": "⭐ Bí quyết xây dựng sự tự tin từ bên trong", "category": "psychology"},
    ],
    "parenting": [
        {"keyword": "高质量育儿不吼不叫", "label": "👨‍👩‍👧 Nuôi dạy con không đòn roi quát mắng", "category": "parenting"},
        {"keyword": "宝宝辅食简单营养做法", "label": "🥣 Ăn dặm dinh dưỡng dễ làm cho bé", "category": "parenting"},
        {"keyword": "儿童专注力训练游戏", "label": "🎯 Trò chơi rèn luyện sự tập trung cho trẻ", "category": "parenting"},
        {"keyword": "新手爸妈带娃省心好物", "label": "🍼 Đồ dùng thông minh chăm con nhàn tênh", "category": "parenting"},
        {"keyword": "家庭沟通与情绪管理", "label": "🏡 Bí quyết giữ không khí gia đình êm ấm", "category": "parenting"},
    ],
    "fashion": [
        {"keyword": "微胖女生显瘦穿搭技巧", "label": "👗 Mẹo phối đồ giấu dáng cho người tròn", "category": "fashion"},
        {"keyword": "胶囊衣橱一衣多穿", "label": "🧥 Tủ đồ tối giản 1 áo phối 5 phong cách", "category": "fashion"},
        {"keyword": "不同身材穿衣搭配指南", "label": "📐 Phối đồ chuẩn xác theo từng dáng người", "category": "fashion"},
        {"keyword": "小个子女生显高穿搭", "label": "👠 Bí quyết hack chiều cao cho nàng nấm lùn", "category": "fashion"},
        {"keyword": "四季常青百搭单品推荐", "label": "✨ Món đồ cơ bản không bao giờ lỗi mốt", "category": "fashion"},
    ],
    "pets": [
        {"keyword": "幼犬防咬训练", "label": "🐶 Dạy chó con bỏ tật cắn tay", "category": "pets"},
        {"keyword": "新手养猫必存指南", "label": "🐱 Cẩm nang người mới nuôi mèo không tốn kém", "category": "pets"},
        {"keyword": "狗狗定点上厕所", "label": "🚽 Dạy chó đi vệ sinh đúng chỗ trong 3 ngày", "category": "pets"},
        {"keyword": "自制猫饭生骨肉", "label": "🥩 Tự làm pate thức ăn dinh dưỡng cho mèo", "category": "pets"},
        {"keyword": "平价宠物好物测评", "label": "⭐ Review đồ thú cưng ngon bổ rẻ chất lượng", "category": "pets"},
    ],
    "mystery_history": [
        {"keyword": "未解之谜真实悬案", "label": "🔍 Kỳ án có thật chưa có lời giải chấn động", "category": "mystery_history"},
        {"keyword": "趣味历史冷知识", "label": "📜 Sự thật lịch sử thú vị ít người biết", "category": "mystery_history"},
        {"keyword": "古代硬核冷兵器揭秘", "label": "⚔️ Bí mật các loại vũ khí cổ đại độc đáo", "category": "mystery_history"},
        {"keyword": "沉浸式硬核案情还原", "label": "🎙️ Tái hiện chi tiết vụ án giật gân thế giới", "category": "mystery_history"},
        {"keyword": "民间离奇传说解析", "label": "🌌 Giải mã những câu chuyện huyền bí dân gian", "category": "mystery_history"},
    ],
    "repair_restoration": [
        {"keyword": "沉浸式老物件翻新修复", "label": "✨ Phục hồi đồ cổ nát thành bóng loáng như mới", "category": "repair_restoration"},
        {"keyword": "报废工具除锈抛光", "label": "🔧 Tẩy rỉ sét đánh bóng dụng cụ cũ hỏng", "category": "repair_restoration"},
        {"keyword": "家庭水暖电路小修小补", "label": "🛠️ Tự sửa điện nước vặt trong nhà không cần thợ", "category": "repair_restoration"},
        {"keyword": "破旧皮鞋清洗翻新保养", "label": "👞 Spa phục hồi giày da cũ thành hàng hiệu", "category": "repair_restoration"},
        {"keyword": "废旧物品DIY改造神器", "label": "♻️ Tái chế đồ bỏ đi thành dụng cụ tiện ích", "category": "repair_restoration"},
    ],
    "language_study": [
        {"keyword": "零基础学英语口语发音", "label": "🗣️ Luyện phát âm tiếng Anh chuẩn cho người mới", "category": "language_study"},
        {"keyword": "高效背单词记忆法", "label": "🧠 Mẹo nhớ 1000 từ vựng không bao giờ quên", "category": "language_study"},
        {"keyword": "费曼学习法高效备考", "label": "📚 Phương pháp Feynman ôn thi điểm cao", "category": "language_study"},
        {"keyword": "日常英语地道表达", "label": "💬 Câu giao tiếp tiếng Anh tự nhiên hằng ngày", "category": "language_study"},
        {"keyword": "自学一门语言的路线图", "label": "🗺️ Lộ trình tự học ngoại ngữ tại nhà từ số 0", "category": "language_study"},
    ],
    "cars": [
        {"keyword": "新能源电车真实用车成本", "label": "⚡ Chi phí thực tế nuôi xe ô tô điện 1 năm", "category": "cars"},
        {"keyword": "新手买车防坑避雷指南", "label": "🚗 Mẹo chọn mua xe cũ không bị lừa bổ máy", "category": "cars"},
        {"keyword": "汽车隐藏实用冷功能", "label": "🔑 Tính năng ẩn cực tiện lợi trên xe hơi", "category": "cars"},
        {"keyword": "雨天夜间安全驾驶技巧", "label": "🌧️ Kỹ năng lái xe an toàn ban đêm trời mưa", "category": "cars"},
        {"keyword": "自驾露营床车改装方案", "label": "🛏️ Độ xe ô tô thành phòng ngủ đi phượt dã ngoại", "category": "cars"},
    ],
    "insider_secrets": [
        {"keyword": "行业内幕真实潜规则", "label": "🕵️ Bí mật nghề nghiệp ít ai kể bạn nghe", "category": "insider_secrets"},
        {"keyword": "酒店行业避坑卫生揭秘", "label": "🏨 Sự thật về vệ sinh phòng khách sạn", "category": "insider_secrets"},
        {"keyword": "餐饮后厨不为人知的真相", "label": "🍳 Hậu trường nhà bếp ẩm thực ít người biết", "category": "insider_secrets"},
        {"keyword": "汽车维修保养水太深", "label": "🚘 Chiêu trò sửa xe người đi ô tô cần biết", "category": "insider_secrets"},
        {"keyword": "装修行业避坑黑幕", "label": "🏗️ Bẫy đội giá trong thiết kế thi công nhà cửa", "category": "insider_secrets"},
    ],
    "rural_life": [
        {"keyword": "阳台种菜新手丰收指南", "label": "🌱 Trồng rau ban công chung cư sai trĩu quả", "category": "rural_life"},
        {"keyword": "田园乡村治愈慢生活", "label": "🌾 Cuộc sống thôn dã bình yên chữa lành tâm hồn", "category": "rural_life"},
        {"keyword": "自制有机肥料厨余堆肥", "label": "🍂 Tự ủ phân hữu cơ từ rác nhà bếp siêu sạch", "category": "rural_life"},
        {"keyword": "无土栽培水培蔬菜实验", "label": "🥗 Kỹ thuật trồng rau thuỷ canh xanh mướt tại nhà", "category": "rural_life"},
        {"keyword": "山野采摘野生菌野果", "label": "🍄 Trải nghiệm hái nấm dại hoa quả trên rừng", "category": "rural_life"},
    ],
    "books_movies": [
        {"keyword": "高分神作电影细节伏笔", "label": "🎬 Phân tích chi tiết ẩn và plot twist phim đỉnh cao", "category": "books_movies"},
        {"keyword": "改变人生的3本神书推荐", "label": "📖 3 cuốn sách thay đổi tư duy nên đọc 1 lần", "category": "books_movies"},
        {"keyword": "硬核悬疑反转电影解说", "label": "🍿 Tóm tắt phim trinh thám ly kỳ cuốn hút", "category": "books_movies"},
        {"keyword": "经典文学金句深度拆解", "label": "✒️ Cắt nghĩa những câu nói triết lý sâu sắc", "category": "books_movies"},
        {"keyword": "一口气看懂一部世界名著", "label": "🏛️ Hiểu trọn vẹn danh tác thế giới trong 10 phút", "category": "books_movies"},
    ],
    "crafts": [
        {"keyword": "解压治愈流体画制作", "label": "🎨 Vẽ tranh Acrylic lỏng xả stress cực chill", "category": "crafts"},
        {"keyword": "超轻粘土手工软陶制作", "label": "🧸 Nặn đất sét tự khô siêu xinh xắn", "category": "crafts"},
        {"keyword": "木工手工雕刻新手入门", "label": "🪵 Điêu khắc gỗ thủ công đơn giản mà tinh xảo", "category": "crafts"},
        {"keyword": "毛线钩针编织教程", "label": "🧶 Hướng dẫn móc len đan khăn áo cho người mới", "category": "crafts"},
        {"keyword": "滴胶树脂唯美手工艺品", "label": "💎 Làm trang sức resin epoxy trong veo lung linh", "category": "crafts"},
    ],
    "floristry": [
        {"keyword": "新手插花万能配色公式", "label": "💐 Công thức phối màu cắm hoa bất bại", "category": "floristry"},
        {"keyword": "鲜花延长花期保鲜秘诀", "label": "🌿 Mẹo giữ hoa tươi lâu cả tuần không thối cành", "category": "floristry"},
        {"keyword": "韩式自然风花束包装", "label": "🎁 Gói bó hoa phong cách Hàn Quốc sang xịn", "category": "floristry"},
        {"keyword": "餐桌瓶插花摆放技巧", "label": "🏺 Cách cắm bình hoa để bàn ăn đẹp thanh lịch", "category": "floristry"},
        {"keyword": "野花野草插出高级感", "label": "🌾 Biến hoa cỏ dại ven đường thành tác phẩm nghệ thuật", "category": "floristry"},
    ],
}

# Substring filters for matching live Douyin Hot Search into specific niches
CATEGORY_KEYWORDS_FILTER: dict[str, list[str]] = {
    "beauty": ["妆", "美", "护肤", "穿搭", "发型", "素颜", "口红", "粉底", "变美", "防晒", "精华", "洗面奶"],
    "food": ["美食", "吃", "饭", "菜", "做饭", "火锅", "甜品", "奶茶", "减脂餐", "小吃", "早餐", "夜宵", "烘焙", "烹饪"],
    "fitness": ["健身", "运动", "减脂", "燃脂", "体态", "跑步", "瑜伽", "动作", "核心", "塑形", "增肌", "锻炼"],
    "finance": ["攒钱", "存钱", "搞钱", "副业", "职场", "面试", "简历", "理财", "工作", "薪资", "升职", "跳槽"],
    "home": ["桌面", "收纳", "家", "房", "居家", "改造", "好物", "清洁", "卧室", "软装", "租房", "宿舍", "家具"],
    "travel": ["旅游", "旅行", "攻略", "自驾", "露营", "打卡", "风景", "游记", "景点", "徒步", "民宿"],
    "tech_ai": ["AI", "工具", "效率", "手机", "数码", "办公", "软件", "功能", "电脑", "大模型", "ChatGPT", "DeepSeek"],
    "business": ["商业", "搞钱", "创业", "摆摊", "开店", "选品", "实体店", "卖货", "利润", "生意", "电商", "直播"],
    "psychology": ["心理", "内耗", "情商", "治愈", "情绪", "沟通", "自信", "疗愈", "成长", "焦虑", "原生家庭"],
    "parenting": ["育儿", "宝宝", "带娃", "辅食", "孩子", "父母", "家庭", "妈妈", "专注力", "早教", "幼儿园"],
    "fashion": ["穿搭", "衣服", "显瘦", "显高", "身材", "衣橱", "搭配", "单品", "风格", "时尚", "外套", "裙子"],
    "pets": ["猫", "狗", "宠", "动物", "幼犬", "小猫", "毛孩子", "宠物", "萌宠", "汪星人", "喵星人"],
    "mystery_history": ["悬案", "历史", "解密", "未解之谜", "案件", "冷知识", "古代", "故事", "揭秘", "考古", "大案"],
    "repair_restoration": ["修复", "翻新", "清洗", "除锈", "DIY", "维修", "老物件", "改造", "手工", "拯救", "抛光"],
    "language_study": ["学英语", "背单词", "学习法", "口语", "备考", "外语", "发音", "自学", "记忆法", "语法", "听力"],
    "cars": ["买车", "用车", "电车", "汽车", "新能源", "自驾", "驾驶", "油耗", "改装", "二手车", "特斯拉"],
    "insider_secrets": ["内幕", "行业", "避坑", "真相", "黑幕", "揭秘", "潜规则", "经验", "猫腻", "套路", "内情"],
    "rural_life": ["种菜", "阳台", "乡村", "田园", "治愈", "农业", "堆肥", "水培", "采摘", "农家", "李子柒", "山村"],
    "books_movies": ["电影", "解说", "书单", "看书", "神作", "细节", "伏笔", "名著", "影视", "剧情", "台词", "导演"],
    "crafts": ["手工", "粘土", "绘画", "DIY", "雕刻", "编织", "滴胶", "艺术", "画画", "手作", "陶艺", "木工"],
    "floristry": ["插花", "鲜花", "花艺", "花束", "保鲜", "花瓶", "养花", "花道", "瓶插", "玫瑰", "郁金香"],
}

_CACHE_LOCK = threading.Lock()
_CACHED_DOUYIN_HOT: list[dict[str, Any]] = []
_LAST_FETCH_TIME: float = 0.0
_CACHE_TTL_SECONDS = 900.0  # 15 minutes


def fetch_douyin_hot_board(limit: int = 50) -> list[dict[str, Any]]:
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
