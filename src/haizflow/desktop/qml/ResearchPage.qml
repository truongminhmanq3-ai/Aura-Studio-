import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

Item {
    id: root

    readonly property var controller: AppController.researchController
    readonly property var selected: controller ? controller.selectedPost : ({})
    readonly property var decision: controller ? controller.currentDecision : ({})
    readonly property bool hasSelected: Boolean(selected && selected.id !== undefined && selected.id.length > 0)
    readonly property bool hasDecision: Boolean(decision && decision.has_decision)

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
                                color: postCard.modelData.platform === "douyin" ? "#16000000" : "#22FF2442"
                                border.width: 1
                                border.color: postCard.modelData.platform === "douyin" ? "#33000000" : "#66FF2442"

                                Text {
                                    anchors.centerIn: parent
                                    text: postCard.modelData.platform === "douyin" ? "DY" : "XHS"
                                    font.bold: true
                                    font.pixelSize: 13
                                    color: postCard.modelData.platform === "douyin" ? Theme.text : "#FF2442"
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
                            Layout.preferredHeight: 70
                            radius: 12
                            color: "#1209090B"
                            border.color: "#22FFFFFF"

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 4
                                Text {
                                    text: (root.selected && root.selected.title) ? root.selected.title : ""
                                    font.bold: true
                                    font.pixelSize: TypeScale.body
                                    color: Theme.text
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                RowLayout {
                                    spacing: 12
                                    Text {
                                        text: "Link: " + ((root.selected && root.selected.url) ? root.selected.url : "")
                                        font.pixelSize: 11
                                        color: Theme.textMuted
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
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

                            // 1-Click Action to Video Pipeline
                            Rectangle {
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
                                            if (root.selected && root.selected.url) {
                                                AppController.copyToClipboard(root.selected.url);
                                                root.controller.selectPost(root.selected.id);
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
    }
}
