import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

Item {
    id: root

    signal requestUrlImport(string mode, string initialUrl)
    signal requestNavigate(string route)
    signal requestNewProject(string projectType, string returnRoute)
    signal requestNotification(string title, string message)

    readonly property var controller: AppController.researchController
    readonly property var selected: controller ? controller.selectedPost : ({})
    readonly property var decision: controller ? controller.currentDecision : ({})
    readonly property bool hasSelected: Boolean(selected && selected.id !== undefined && selected.id.length > 0)
    readonly property bool hasDecision: Boolean(decision && decision.has_decision)

    function startVideoProduction() {
        let bestUrl = "";
        let clip = "";
        try {
            clip = AppController.clipboardText().trim();
        } catch (e) {
            clip = "";
        }

        const isDirect = function(u) {
            if (!u || typeof u !== "string") return false;
            const s = u.trim();
            return s.indexOf("/video/") >= 0 ||
                   s.indexOf("v.douyin.com/") >= 0 ||
                   s.indexOf("tiktok.com/") >= 0 ||
                   s.indexOf("youtube.com/") >= 0 ||
                   s.indexOf("youtu.be/") >= 0 ||
                   s.indexOf("weibo.com/") >= 0 ||
                   s.indexOf("weibo.cn/") >= 0;
        };

        if (clip && isDirect(clip)) {
            bestUrl = clip;
        } else if (root.selected && root.selected.url && isDirect(root.selected.url)) {
            bestUrl = root.selected.url;
        } else if (root.selected && root.selected.url) {
            bestUrl = root.selected.url;
        } else if (clip) {
            bestUrl = clip;
        }

        if (!clip || !isDirect(clip)) {
            if (root.selected && root.selected.url) {
                AppController.copyToClipboard(root.selected.url);
            }
        }

        if (AppController.hasOpenProject) {
            const destRoute = (AppController.projectType === "manual") ? "manual-workspace" : "single-workspace";
            root.requestNavigate(destRoute);
            root.requestUrlImport("single", bestUrl);
            root.requestNotification(qsTr("Aura Studio · Chuyển sang Dựng video"), qsTr("Đang mở hộp thoại tải và nhập video."));
        } else {
            AppController.prepareProjectCreationDirectory();
            let projName = "";
            if (root.selected && root.selected.title) {
                projName = root.selected.title.split(" - ")[0].trim()
                    .replace(/[\\/:*?"<>|#]/g, "")
                    .slice(0, 32)
                    .trim();
            }
            if (!projName) {
                projName = qsTr("Dự án nghiên cứu");
            }

            if (AppController.prepareProject(projName, AppController.projectDirectory, "single")) {
                root.requestUrlImport("single", bestUrl);
                root.requestNotification(qsTr("Aura Studio · Đã tạo dự án mới"), qsTr("Dự án '%1' đã sẵn sàng. Dán link video để bắt đầu dựng!").arg(projName));
            } else {
                root.requestNewProject("single", "research");
            }
        }
    }

    function doSearch() {
        const q = searchInput.text.trim();
        console.log("[RESEARCH_UI] doSearch called with:", q, "controller:", root.controller);
        if (!q) return;
        if (!root.controller) {
            console.error("[RESEARCH_UI] Error: root.controller is missing!");
            return;
        }
        if (q.startsWith("http://") || q.startsWith("https://")) {
            root.controller.importUrl(q);
        } else {
            root.controller.searchKeyword(q, "all");
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: UiMetrics.pageMargin
        spacing: Theme.space16

        // Page Header
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space12

            ColumnLayout {
                spacing: 4
                Text {
                    text: qsTr("Nghiên cứu Thị trường & Giám đốc Nội dung AI")
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: TypeScale.title
                    font.weight: Font.Bold
                }
                Text {
                    text: qsTr("Quét xu hướng Douyin & RedNote, khai thác nỗi đau từ bình luận và ra quyết định bằng AI")
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: TypeScale.metadata
                }
            }

            Item { Layout.fillWidth: true }

            // Busy indicator
            RowLayout {
                visible: Boolean(root.controller && root.controller.busy)
                spacing: 8
                BusyIndicator {
                    running: true
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                }
                Text {
                    text: root.controller ? root.controller.statusMessage : ""
                    color: Theme.interactive
                    font.family: Theme.fontFamily
                    font.pixelSize: TypeScale.metadata
                }
            }
        }

        // Search & Filter Toolbar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            radius: 18
            color: "transparent"
            border.width: 1.5
            border.color: "#E6FFFFFF"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#22FFFFFF" }
                GradientStop { position: 1.0; color: "#0CFFFFFF" }
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12

                AppTextField {
                    id: searchInput
                    Layout.fillWidth: true
                    placeholderText: qsTr("Nhập từ khóa (vd: cắm trại, podcast chữa lành...) hoặc dán link Douyin / Xiaohongshu...")
                    text: ""
                    onAccepted: root.doSearch()
                    Keys.onReturnPressed: function(event) { root.doSearch(); event.accepted = true; }
                    Keys.onEnterPressed: function(event) { root.doSearch(); event.accepted = true; }
                }

                StudioButton {
                    id: searchBtn
                    text: root.controller && root.controller.busy ? qsTr("Đang quét...") : qsTr("Khám phá & Quét")
                    variant: "primary"
                    iconName: root.controller && root.controller.busy ? "" : "search"
                    enabled: Boolean(root.controller && !root.controller.busy)
                    onClicked: root.doSearch()
                }

                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 28
                    color: "#22000000"
                }

                // Filter Buttons
                RowLayout {
                    spacing: 6
                    StudioButton {
                        text: qsTr("Tất cả")
                        variant: root.controller && root.controller.activeFilter === "all" ? "primary" : "secondary"
                        onClicked: root.controller.setFilter("all")
                    }
                    StudioButton {
                        text: qsTr("🔥 Top Outlier")
                        variant: root.controller && root.controller.activeFilter === "outliers" ? "primary" : "secondary"
                        onClicked: root.controller.setFilter("outliers")
                    }
                    StudioButton {
                        text: qsTr("📚 Top Lưu (Saves)")
                        variant: root.controller && root.controller.activeFilter === "useful" ? "primary" : "secondary"
                        onClicked: root.controller.setFilter("useful")
                    }
                    StudioButton {
                        text: qsTr("🗑 Xóa lịch sử")
                        variant: "secondary"
                        visible: Boolean(root.controller && root.controller.postCount > 0)
                        onClicked: if (root.controller) root.controller.clearAllPosts()
                    }
                }
            }
        }

        // Real-time Status / Feedback Banner
        Rectangle {
            id: statusBar
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            radius: Theme.radiusTiny
            visible: Boolean(root.controller && root.controller.statusMessage.length > 0)
            color: root.controller && root.controller.busy
                   ? "#1A3B82F6"
                   : (root.controller && root.controller.statusMessage.indexOf("Lỗi") !== -1 ? "#1AEF4444" : "#1A10B981")
            border.width: 1
            border.color: root.controller && root.controller.busy
                          ? "#503B82F6"
                          : (root.controller && root.controller.statusMessage.indexOf("Lỗi") !== -1 ? "#50EF4444" : "#5010B981")

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 14
                spacing: 10

                BusyIndicator {
                    running: Boolean(root.controller && root.controller.busy)
                    visible: running
                    Layout.preferredWidth: 16
                    Layout.preferredHeight: 16
                }

                Text {
                    text: root.controller ? root.controller.statusMessage : ""
                    color: root.controller && root.controller.busy
                           ? "#2563EB"
                           : (root.controller && root.controller.statusMessage.indexOf("Lỗi") !== -1 ? Theme.danger : "#059669")
                    font.family: Theme.fontFamily
                    font.pixelSize: TypeScale.metadata
                    font.weight: Font.Medium
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
        }

        // Trending Keywords & Niche Explorer Bar
        Rectangle {
            id: trendingSection
            Layout.fillWidth: true
            Layout.preferredHeight: 98
            radius: 16
            color: "#08000000"
            border.width: 1
            border.color: "#18000000"

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 14
                anchors.topMargin: 10
                anchors.bottomMargin: 10
                spacing: 8

                // Category selector bar
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        text: qsTr("🔥 Xu hướng:")
                        font.family: Theme.fontFamily
                        font.bold: true
                        font.pixelSize: 13
                        color: Theme.text
                    }

                    // Horizontal Scrollable Category Pills
                    Flickable {
                        id: catFlickable
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        contentWidth: catRow.implicitWidth
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        flickableDirection: Flickable.HorizontalFlick

                        RowLayout {
                            id: catRow
                            spacing: 6
                            height: parent.height

                            Repeater {
                                model: [
                                    { id: "all", label: "Tất cả" },
                                    { id: "douyin_hot", label: "🎵 Douyin Hot" },
                                    { id: "rednote_hot", label: "📕 RedNote Hot" },
                                    { id: "weibo_hot", label: "🔥 Weibo Hot" },
                                    { id: "beauty", label: "💄 Làm đẹp" },
                                    { id: "food", label: "🍳 Nấu ăn" },
                                    { id: "fitness", label: "💪 Thể hình" },
                                    { id: "finance", label: "💰 Tài chính" },
                                    { id: "home", label: "🏠 Nhà cửa & Setup" },
                                    { id: "travel", label: "🏕️ Du lịch" },
                                    { id: "tech_ai", label: "🤖 Công nghệ & AI" },
                                    { id: "business", label: "💼 Kinh doanh" },
                                    { id: "psychology", label: "🌿 Tâm lý" },
                                    { id: "parenting", label: "👶 Nuôi dạy con" },
                                    { id: "fashion", label: "👗 Thời trang" },
                                    { id: "pets", label: "🐶 Thú cưng" },
                                    { id: "mystery_history", label: "🔍 Kỳ án & Lịch sử" },
                                    { id: "repair_restoration", label: "🛠️ Phục hồi đồ cũ" },
                                    { id: "language_study", label: "📖 Học ngoại ngữ" },
                                    { id: "cars", label: "🚗 Xe cộ" },
                                    { id: "insider_secrets", label: "🕵️ Bí mật nghề" },
                                    { id: "rural_life", label: "🌾 Thôn dã" },
                                    { id: "books_movies", label: "🎬 Sách & Phim" },
                                    { id: "crafts", label: "🎨 Thủ công" },
                                    { id: "floristry", label: "💐 Cắm hoa" }
                                ]

                                Rectangle {
                                    id: catChip
                                    required property var modelData
                                    readonly property bool isSelected: Boolean(root.controller && root.controller.trendingCategory === modelData.id)
                                    Layout.preferredHeight: 28
                                    Layout.preferredWidth: catText.implicitWidth + 20
                                    radius: 8
                                    color: isSelected ? Theme.interactive : (catMouse.containsMouse ? "#1C000000" : "#0A000000")
                                    border.width: 1
                                    border.color: isSelected ? Theme.interactive : (catMouse.containsMouse ? "#2E000000" : "#18000000")

                                    Text {
                                        id: catText
                                        anchors.centerIn: parent
                                        text: catChip.modelData.label
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 12
                                        font.weight: catChip.isSelected ? Font.Bold : Font.Normal
                                        color: catChip.isSelected ? Theme.textOnAccent : Theme.text
                                    }

                                    MouseArea {
                                        id: catMouse
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        hoverEnabled: true
                                        onClicked: {
                                            if (root.controller) {
                                                root.controller.setTrendingCategory(catChip.modelData.id);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Horizontal Flickable of Clickable Trending Keyword Chips
                Flickable {
                    id: tagFlickable
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    contentWidth: tagRow.implicitWidth
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    RowLayout {
                        id: tagRow
                        spacing: 10
                        height: parent.height

                        // Quick Action Button to open full Top 50 Board when a platform category is active
                        Rectangle {
                            id: fullBoardBtn
                            visible: Boolean(root.controller && (
                                root.controller.trendingCategory === "douyin_hot" ||
                                root.controller.trendingCategory === "weibo_hot" ||
                                root.controller.trendingCategory === "rednote_hot"
                            ))
                            Layout.preferredHeight: 32
                            Layout.preferredWidth: fullBoardText.implicitWidth + 24
                            radius: 9
                            color: fullBoardMouse.containsMouse
                                   ? (root.controller && root.controller.trendingCategory === "rednote_hot" ? "#D91B36" : (root.controller && root.controller.trendingCategory === "weibo_hot" ? "#E07300" : "#1A1A1A"))
                                   : (root.controller && root.controller.trendingCategory === "rednote_hot" ? "#22FF2442" : (root.controller && root.controller.trendingCategory === "weibo_hot" ? "#22FF8200" : "#22000000"))
                            border.width: 1.5
                            border.color: root.controller && root.controller.trendingCategory === "rednote_hot" ? "#FF2442" : (root.controller && root.controller.trendingCategory === "weibo_hot" ? "#FF8200" : "#33000000")

                            RowLayout {
                                id: fullBoardText
                                anchors.centerIn: parent
                                spacing: 6
                                Text {
                                    text: {
                                        if (!root.controller) return "";
                                        if (root.controller.trendingCategory === "douyin_hot") return "📊 Xem bảng xếp hạng Top 50 Douyin ↗";
                                        if (root.controller.trendingCategory === "weibo_hot") return "🔥 Xem bảng xếp hạng Top 50 Weibo ↗";
                                        if (root.controller.trendingCategory === "rednote_hot") return "📕 Xem cẩm nang Top 50 RedNote ↗";
                                        return "";
                                    }
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: fullBoardMouse.containsMouse
                                           ? "#FFFFFF"
                                           : (root.controller && root.controller.trendingCategory === "rednote_hot" ? "#FF2442" : (root.controller && root.controller.trendingCategory === "weibo_hot" ? "#FF8200" : Theme.text))
                                }
                            }

                            MouseArea {
                                id: fullBoardMouse
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                hoverEnabled: true
                                onClicked: {
                                    if (!root.controller) return;
                                    if (root.controller.trendingCategory === "douyin_hot") {
                                        root.controller.loadDouyinHotBoard();
                                        hotBoardPopup.open();
                                    } else if (root.controller.trendingCategory === "weibo_hot") {
                                        root.controller.loadWeiboHotBoard();
                                        weiboHotBoardPopup.open();
                                    } else if (root.controller.trendingCategory === "rednote_hot") {
                                        root.controller.loadRednoteHotBoard();
                                        rednoteHotBoardPopup.open();
                                    }
                                }
                            }
                        }

                        Repeater {
                            model: root.controller ? root.controller.trendingKeywords : []

                            Rectangle {
                                id: tagChip
                                required property var modelData
                                Layout.preferredHeight: 32
                                Layout.preferredWidth: tagChipText.implicitWidth + 24
                                radius: 9
                                color: chipMouse.containsMouse ? Theme.interactive : "#0D000000"
                                border.width: 1
                                border.color: chipMouse.containsMouse ? Theme.interactive : "#1A000000"

                                Text {
                                    id: tagChipText
                                    anchors.centerIn: parent
                                    text: tagChip.modelData.label || tagChip.modelData.keyword
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 12
                                    font.weight: chipMouse.containsMouse ? Font.DemiBold : Font.Medium
                                    color: chipMouse.containsMouse ? Theme.textOnAccent : Theme.text
                                }

                                MouseArea {
                                    id: chipMouse
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    hoverEnabled: true
                                    onClicked: {
                                        const kw = tagChip.modelData.keyword;
                                        if (kw) {
                                            searchInput.text = kw;
                                            if (root.controller) {
                                                root.controller.searchKeyword(kw, "all");
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Two-Column Work Area
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            // Left Column: Discovered Posts List
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 480
                radius: 20
                color: "transparent"
                border.width: 1
                border.color: "#33FFFFFF"
                clip: true

                ListView {
                    id: postListView
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10
                    model: root.controller ? root.controller.posts : []
                    clip: true

                    delegate: Rectangle {
                        id: postCard
                        required property var modelData
                        required property int index
                        readonly property bool isSelected: Boolean(root.selected && root.selected.id === modelData.id)

                        width: postListView.width
                        height: 98
                        radius: 14
                        color: isSelected ? "#3009090B" : (cardMouse.containsMouse ? "#18FFFFFF" : "#0DFFFFFF")
                        border.width: isSelected ? 1.5 : 1
                        border.color: isSelected ? Theme.interactive : "#22FFFFFF"

                        MouseArea {
                            id: cardMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.controller.selectPost(postCard.modelData.id)
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 14

                            // Platform Icon / Tag Box
                            Rectangle {
                                Layout.preferredWidth: 44
                                Layout.preferredHeight: 44
                                radius: 10
                                color: postCard.modelData.platform === "douyin" ? "#16000000" : (postCard.modelData.platform === "weibo" ? "#22FF8200" : "#22FF2442")
                                border.width: 1
                                border.color: postCard.modelData.platform === "douyin" ? "#33000000" : (postCard.modelData.platform === "weibo" ? "#66FF8200" : "#66FF2442")

                                Text {
                                    anchors.centerIn: parent
                                    text: postCard.modelData.platform === "douyin" ? "DY" : (postCard.modelData.platform === "weibo" ? "WB" : "XHS")
                                    font.bold: true
                                    font.pixelSize: 13
                                    color: postCard.modelData.platform === "douyin" ? Theme.text : (postCard.modelData.platform === "weibo" ? "#FF8200" : "#FF2442")
                                }
                            }

                            // Info Body
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Text {
                                        Layout.fillWidth: true
                                        text: postCard.modelData.title
                                        font.bold: true
                                        font.pixelSize: TypeScale.body
                                        color: Theme.text
                                        elide: Text.ElideRight
                                    }

                                    // Outlier pill
                                    Rectangle {
                                        visible: Boolean(postCard.modelData.is_outlier)
                                        Layout.preferredHeight: 20
                                        Layout.preferredWidth: 84
                                        radius: 6
                                        color: "#22E85A2A"
                                        border.color: "#E85A2A"
                                        Text {
                                            anchors.centerIn: parent
                                            text: "🔥 " + postCard.modelData.outlier_score
                                            font.pixelSize: 11
                                            font.bold: true
                                            color: "#E85A2A"
                                        }
                                    }

                                    // Utility pill
                                    Rectangle {
                                        visible: Boolean(postCard.modelData.is_useful)
                                        Layout.preferredHeight: 20
                                        Layout.preferredWidth: 80
                                        radius: 6
                                        color: "#2210B981"
                                        border.color: "#10B981"
                                        Text {
                                            anchors.centerIn: parent
                                            text: "📚 Lưu " + postCard.modelData.utility
                                            font.pixelSize: 11
                                            font.bold: true
                                            color: "#10B981"
                                        }
                                    }
                                }

                                Text {
                                    text: "@" + postCard.modelData.author_name + " • " + (postCard.modelData.ip_location ? postCard.modelData.ip_location : "TQ")
                                    font.pixelSize: TypeScale.metadata
                                    color: Theme.textMuted
                                }

                                // Metrics bar
                                RowLayout {
                                    spacing: 16
                                    Text {
                                        text: "👍 " + postCard.modelData.likes
                                        font.pixelSize: 11
                                        color: Theme.textMuted
                                    }
                                    Text {
                                        text: "⭐ " + postCard.modelData.saves
                                        font.pixelSize: 11
                                        color: Theme.textMuted
                                    }
                                    Text {
                                        text: "💬 " + postCard.modelData.comments
                                        font.pixelSize: 11
                                        color: Theme.textMuted
                                    }
                                    Text {
                                        text: "⚡ ER: " + postCard.modelData.er
                                        font.pixelSize: 11
                                        font.bold: true
                                        color: Theme.interactive
                                    }
                                }
                            }
                        }

                        // Quick Delete Button on Card
                        Rectangle {
                            anchors.top: parent.top
                            anchors.right: parent.right
                            anchors.margins: 6
                            width: 20
                            height: 20
                            radius: 10
                            color: deleteBtnMouse.containsMouse ? "#FFEBEA" : "transparent"
                            visible: cardMouse.containsMouse || postCard.isSelected
                            z: 2

                            Text {
                                anchors.centerIn: parent
                                text: "✕"
                                font.pixelSize: 11
                                font.bold: true
                                color: deleteBtnMouse.containsMouse ? Theme.danger : Theme.textSubtle
                            }

                            MouseArea {
                                id: deleteBtnMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: if (root.controller) root.controller.deletePost(postCard.modelData.id)
                            }
                        }
                    }
                }
            }

            // Right Column: AI Decision Card
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 420
                radius: 20
                color: "transparent"
                border.width: 1
                border.color: "#33FFFFFF"
                clip: true

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 18
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: 14

                        // Header of Right Column
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: qsTr("Quyết định Giám đốc Nội dung AI")
                                font.bold: true
                                font.pixelSize: TypeScale.section
                                color: Theme.text
                            }
                            Item { Layout.fillWidth: true }
                            StudioButton {
                                text: qsTr("Xóa bài này")
                                variant: "secondary"
                                visible: root.hasSelected
                                onClicked: if (root.controller && root.hasSelected) root.controller.deletePost(root.selected.id)
                            }
                            StudioButton {
                                text: qsTr("🤖 Đánh giá bằng AI")
                                variant: "primary"
                                visible: root.hasSelected
                                onClicked: root.controller.evaluateSelectedPost()
                            }
                        }

                        // Empty State if no post selected
                        ColumnLayout {
                            visible: !root.hasSelected
                            Layout.alignment: Qt.AlignHCenter
                            Layout.topMargin: 80
                            spacing: 10
                            Text {
                                text: "👈 Chọn một bài viết ở danh sách bên trái"
                                font.pixelSize: TypeScale.body
                                color: Theme.textMuted
                                Layout.alignment: Qt.AlignHCenter
                            }
                            Text {
                                text: "AI Agent sẽ phân tích transcript, bình luận và đề xuất công thức kịch bản cho bạn."
                                font.pixelSize: TypeScale.metadata
                                color: Theme.textSubtle
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }

                        // Selected Post Summary Header
                        Rectangle {
                            visible: root.hasSelected
                            Layout.fillWidth: true
                            Layout.preferredHeight: 82
                            radius: 12
                            color: "#1209090B"
                            border.color: "#22FFFFFF"

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 6
                                Text {
                                    text: (root.selected && root.selected.title) ? root.selected.title : ""
                                    font.bold: true
                                    font.pixelSize: TypeScale.body
                                    color: Theme.text
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 30
                                        radius: 6
                                        color: "#0F000000"
                                        border.width: 1
                                        border.color: "#1A000000"

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 8
                                            anchors.rightMargin: 8
                                            spacing: 6

                                            Text {
                                                text: "🔗"
                                                font.pixelSize: 11
                                            }

                                            Text {
                                                id: linkLabel
                                                text: ((root.selected && root.selected.url) ? root.selected.url : "")
                                                font.pixelSize: 11
                                                color: "#2563EB"
                                                font.underline: true
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        if (root.selected && root.selected.url) {
                                                            AppController.openExternalUrl(root.selected.url);
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    StudioButton {
                                        text: qsTr("🌐 Mở web kiểm tra")
                                        variant: "primary"
                                        onClicked: {
                                            if (root.selected && root.selected.url) {
                                                AppController.openExternalUrl(root.selected.url);
                                            }
                                        }
                                    }

                                    StudioButton {
                                        text: qsTr("Sao chép link")
                                        variant: "secondary"
                                        onClicked: {
                                            if (root.selected && root.selected.url) {
                                                AppController.copyToClipboard(root.selected.url);
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // AI Decision Result Box
                        ColumnLayout {
                            visible: root.hasSelected && root.hasDecision
                            Layout.fillWidth: true
                            spacing: 12

                            // Verdict and Score Banner
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 56
                                radius: 12
                                color: root.decision.verdict === "remake_now" ? "#2210B981" : (root.decision.verdict === "adapt_script" ? "#22F59E0B" : "#1A6B7280")
                                border.width: 1.5
                                border.color: root.decision.verdict === "remake_now" ? "#10B981" : (root.decision.verdict === "adapt_script" ? "#F59E0B" : "#6B7280")

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12
                                    Text {
                                        text: root.decision.verdict === "remake_now" ? "✅ LÀM NGAY (REMAKE NOW)" : (root.decision.verdict === "adapt_script" ? "⚡ NÊN CHUYỂN THỂ KỊCH BẢN" : "⛔ NÊN BỎ QUA")
                                        font.bold: true
                                        font.pixelSize: 14
                                        color: root.decision.verdict === "remake_now" ? "#10B981" : (root.decision.verdict === "adapt_script" ? "#F59E0B" : "#9CA3AF")
                                    }
                                    Item { Layout.fillWidth: true }
                                    Text {
                                        text: "Điểm tiềm năng: " + (root.decision.score || 0) + " / 100"
                                        font.bold: true
                                        font.pixelSize: 14
                                        color: Theme.text
                                    }
                                }
                            }

                            // Executive Summary
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: summaryText.implicitHeight + 20
                                radius: 10
                                color: "#0AFFFFFF"
                                border.color: "#18FFFFFF"
                                Text {
                                    id: summaryText
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    text: root.decision.summary ? root.decision.summary : ""
                                    font.pixelSize: TypeScale.metadata
                                    color: Theme.text
                                    wrapMode: Text.WordWrap
                                }
                            }

                            // 3 Vietnamese Hooks Proposals
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Text {
                                    text: qsTr("🎯 3 Câu Hook tiếng Việt đề xuất (3 giây đầu):")
                                    font.bold: true
                                    font.pixelSize: TypeScale.metadata
                                    color: Theme.interactive
                                }
                                Repeater {
                                    model: root.decision.hooks || []
                                    delegate: Rectangle {
                                        required property var modelData
                                        required property int index
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: hookLabel.implicitHeight + 14
                                        radius: 8
                                        color: "#12FFFFFF"
                                        border.color: "#22FFFFFF"

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            spacing: 8
                                            Text {
                                                id: hookLabel
                                                Layout.fillWidth: true
                                                text: (index + 1) + ". " + modelData
                                                font.pixelSize: 12
                                                color: Theme.text
                                                wrapMode: Text.WordWrap
                                            }
                                            StudioButton {
                                                text: qsTr("Copy")
                                                variant: "secondary"
                                                onClicked: AppController.copyToClipboard(modelData)
                                            }
                                        }
                                    }
                                }
                            }

                            // Pain points mined from comments
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Text {
                                    text: qsTr("💡 Khai thác Nỗi đau & Nhu cầu từ Bình luận:")
                                    font.bold: true
                                    font.pixelSize: TypeScale.metadata
                                    color: "#F59E0B"
                                }
                                Repeater {
                                    model: root.decision.pain_points || []
                                    delegate: Text {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        text: "• " + modelData
                                        font.pixelSize: 11
                                        color: Theme.textMuted
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }

                            // Adaptation notes
                            ColumnLayout {
                                visible: Boolean(root.decision.adaptation_notes && root.decision.adaptation_notes.length > 0)
                                Layout.fillWidth: true
                                spacing: 4
                                Text {
                                    text: qsTr("📝 Lưu ý khi Việt hóa kịch bản:")
                                    font.bold: true
                                    font.pixelSize: TypeScale.metadata
                                    color: Theme.text
                                }
                                Text {
                                    text: root.decision.adaptation_notes || ""
                                    font.pixelSize: 11
                                    color: Theme.textMuted
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }

                        }

                        // 1-Click Action to Video Pipeline
                        Rectangle {
                            visible: root.hasSelected
                            Layout.fillWidth: true
                            Layout.preferredHeight: 52
                            radius: 12
                            color: "#2209090B"
                            border.color: Theme.interactive

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 12
                                Text {
                                    Layout.fillWidth: true
                                    text: qsTr("Sẵn sàng dựng video này bằng Aura Studio?")
                                    font.bold: true
                                    font.pixelSize: TypeScale.metadata
                                    color: Theme.text
                                }
                                StudioButton {
                                    text: qsTr("🎬 Dán link & Bắt đầu Dựng")
                                    variant: "primary"
                                    onClicked: {
                                        root.startVideoProduction();
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Popup Top 50 Douyin Hot Search
    Popup {
        id: hotBoardPopup
        anchors.centerIn: parent
        width: Math.min(root.width * 0.85, 640)
        height: Math.min(root.height * 0.85, 580)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: 18
            color: "#FFFFFF"
            border.width: 1
            border.color: "#33000000"
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: qsTr("📊 Bảng Xếp Hạng Douyin Hot Search Thời Gian Thực (Top 50)")
                    font.family: Theme.fontFamily
                    font.pixelSize: 15
                    font.bold: true
                    color: Theme.text
                }
                Item { Layout.fillWidth: true }
                StudioButton {
                    text: "✕ Đóng"
                    variant: "secondary"
                    onClicked: hotBoardPopup.close()
                }
            }

            Text {
                text: qsTr("Click vào bất kỳ từ khóa nào để Aura Studio tự động phân tích và bắt trend ngay lập tức:")
                font.pixelSize: 12
                color: Theme.textMuted
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 12
                color: "#08000000"
                border.width: 1
                border.color: "#14000000"
                clip: true

                ListView {
                    id: hotListView
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6
                    model: root.controller ? root.controller.douyinHotBoard : []
                    clip: true

                    delegate: Rectangle {
                        id: hotItemRow
                        required property var modelData
                        required property int index
                        width: hotListView.width
                        height: 38
                        radius: 8
                        color: hotItemMouse.containsMouse ? "#182563EB" : "transparent"
                        border.width: hotItemMouse.containsMouse ? 1 : 0
                        border.color: "#402563EB"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 10

                            Rectangle {
                                Layout.preferredWidth: 26
                                Layout.preferredHeight: 22
                                radius: 4
                                color: hotItemRow.index === 0 ? "#FF3B30" : (hotItemRow.index === 1 ? "#FF9500" : (hotItemRow.index === 2 ? "#FFCC00" : "#E5E5EA"))
                                Text {
                                    anchors.centerIn: parent
                                    text: String(hotItemRow.index + 1)
                                    font.bold: true
                                    font.pixelSize: 11
                                    color: hotItemRow.index < 3 ? "#FFFFFF" : "#666666"
                                }
                            }

                            Text {
                                text: hotItemRow.modelData.keyword || ""
                                font.pixelSize: 13
                                font.bold: hotItemRow.index < 3
                                color: Theme.text
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: "🔥 " + (hotItemRow.modelData.hot_value || "")
                                font.pixelSize: 11
                                color: "#FF3B30"
                            }
                        }

                        MouseArea {
                            id: hotItemMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                const kw = hotItemRow.modelData.keyword;
                                if (kw) {
                                    searchInput.text = kw;
                                    hotBoardPopup.close();
                                    if (root.controller) {
                                        root.controller.searchKeyword(kw, "all");
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Popup Top 50 Weibo Hot Search
    Popup {
        id: weiboHotBoardPopup
        anchors.centerIn: parent
        width: Math.min(root.width * 0.85, 640)
        height: Math.min(root.height * 0.85, 580)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: 18
            color: "#FFFFFF"
            border.width: 1.5
            border.color: "#FF8200"
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: qsTr("🔥 Bảng Xếp Hạng Weibo Hot Search Thời Gian Thực (Top 50 热搜)")
                    font.family: Theme.fontFamily
                    font.pixelSize: 15
                    font.bold: true
                    color: "#D96B00"
                }
                Item { Layout.fillWidth: true }
                StudioButton {
                    text: "✕ Đóng"
                    variant: "secondary"
                    onClicked: weiboHotBoardPopup.close()
                }
            }

            Text {
                text: qsTr("Click vào bất kỳ chủ đề nóng nào để Aura Studio tự động phân tích và bắt trend:")
                font.pixelSize: 12
                color: Theme.textMuted
                Layout.fillWidth: true
            }

            ListView {
                id: weiboHotListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: root.controller ? root.controller.weiboHotBoard : []

                delegate: Rectangle {
                    id: wbHotItemRow
                    required property var modelData
                    required property int index
                    width: weiboHotListView.width
                    height: 44
                    radius: 10
                    color: wbHotItemMouse.containsMouse ? "#12FF8200" : "#05000000"
                    border.width: 1
                    border.color: wbHotItemMouse.containsMouse ? "#FF8200" : "#10000000"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 12

                        Text {
                            text: String(wbHotItemRow.index + 1)
                            font.bold: true
                            font.pixelSize: 14
                            color: wbHotItemRow.index < 3 ? "#D96B00" : Theme.textMuted
                            Layout.preferredWidth: 24
                        }

                        Text {
                            text: wbHotItemRow.modelData.keyword
                            font.pixelSize: 13
                            font.bold: wbHotItemRow.index < 3
                            color: Theme.text
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            visible: Boolean(wbHotItemRow.modelData.tag)
                            Layout.preferredHeight: 20
                            Layout.preferredWidth: 48
                            radius: 4
                            color: "#22FF8200"
                            Text {
                                anchors.centerIn: parent
                                text: wbHotItemRow.modelData.tag || ""
                                font.pixelSize: 10
                                font.bold: true
                                color: "#D96B00"
                            }
                        }

                        Text {
                            text: wbHotItemRow.modelData.hot_value
                            font.pixelSize: 11
                            color: Theme.textMuted
                        }
                    }

                    MouseArea {
                        id: wbHotItemMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            const kw = wbHotItemRow.modelData.keyword;
                            if (kw) {
                                searchInput.text = kw;
                                weiboHotBoardPopup.close();
                                if (root.controller) {
                                    root.controller.searchKeyword(kw, "all");
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Popup Top 50 RedNote Viral Guides & Lifestyle Trends
    Popup {
        id: rednoteHotBoardPopup
        anchors.centerIn: parent
        width: Math.min(parent.width - 60, 680)
        height: Math.min(parent.height - 80, 640)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: 16
            color: "#FFFFFF"
            border.width: 1.5
            border.color: "#FF2442"
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: qsTr("📕 Bảng Xu Hướng & Cẩm Nang RedNote (Xiaohongshu Top 50 热门指南)")
                    font.family: Theme.fontFamily
                    font.pixelSize: 15
                    font.bold: true
                    color: "#D91B36"
                }
                Item { Layout.fillWidth: true }
                StudioButton {
                    text: "✕ Đóng"
                    variant: "secondary"
                    onClicked: rednoteHotBoardPopup.close()
                }
            }

            Text {
                text: qsTr("Click vào chủ đề cẩm nang bất kỳ để AI Agent phân tích công thức nội dung và nỗi đau người dùng:")
                font.pixelSize: 12
                color: Theme.textMuted
                Layout.fillWidth: true
            }

            ListView {
                id: rednoteHotListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: root.controller ? root.controller.rednoteHotBoard : []

                delegate: Rectangle {
                    id: rnHotItemRow
                    required property var modelData
                    required property int index
                    width: rednoteHotListView.width
                    height: 52
                    radius: 10
                    color: rnHotItemMouse.containsMouse ? "#12FF2442" : "#05000000"
                    border.width: 1
                    border.color: rnHotItemMouse.containsMouse ? "#FF2442" : "#10000000"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 12

                        Text {
                            text: String(rnHotItemRow.index + 1)
                            font.bold: true
                            font.pixelSize: 14
                            color: rnHotItemRow.index < 3 ? "#D91B36" : Theme.textMuted
                            Layout.preferredWidth: 24
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: rnHotItemRow.modelData.keyword
                                font.pixelSize: 13
                                font.bold: true
                                color: Theme.text
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: rnHotItemRow.modelData.desc_vi || ""
                                font.pixelSize: 11
                                color: Theme.textMuted
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                                visible: Boolean(rnHotItemRow.modelData.desc_vi)
                            }
                        }

                        Rectangle {
                            visible: Boolean(rnHotItemRow.modelData.tag)
                            Layout.preferredHeight: 20
                            Layout.preferredWidth: 54
                            radius: 4
                            color: "#22FF2442"
                            Text {
                                anchors.centerIn: parent
                                text: rnHotItemRow.modelData.tag || ""
                                font.pixelSize: 10
                                font.bold: true
                                color: "#D91B36"
                            }
                        }

                        Text {
                            text: rnHotItemRow.modelData.hot_value
                            font.pixelSize: 11
                            color: Theme.textMuted
                        }
                    }

                    MouseArea {
                        id: rnHotItemMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            const kw = rnHotItemRow.modelData.keyword;
                            if (kw) {
                                searchInput.text = kw;
                                rednoteHotBoardPopup.close();
                                if (root.controller) {
                                    root.controller.searchKeyword(kw, "all");
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
