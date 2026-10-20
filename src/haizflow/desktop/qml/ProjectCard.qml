import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

Control {
    id: root

    required property int index
    required property string projectName
    required property string projectKey
    property string menuProjectKey: ""
    required property string projectType
    required property int videoCount
    required property string status
    required property int progress
    required property string thumbnailSource
    required property string videoSize

    signal activated
    signal openRequested
    signal projectFolderRequested
    signal deleteRequested
    signal renameRequested(string key)

    readonly property string statusLabel: status === "pending" ? qsTr("Đang chờ") : status === "empty" ? qsTr("Chưa chọn video nguồn") : status === "ready" || status === "manual_ready" ? qsTr("Sẵn sàng") : status === "processing" ? qsTr("Đang xử lý") : status === "done" ? qsTr("Hoàn tất") : status === "failed" ? qsTr("Lỗi") : status === "cancelled" ? qsTr("Đã hủy") : status === "paused" ? qsTr("Đã tạm dừng") : status === "awaiting_review" ? qsTr("Cần duyệt") : I18n.taskStateLabel(status)
    readonly property string typeLabel: projectType === "manual" ? qsTr("Thủ công")
        : projectType === "batch" ? qsTr("Hàng loạt")
        : projectType === "download" ? qsTr("Tải xuống")
        : projectType === "publish" ? qsTr("Đăng mạng xã hội") : qsTr("Tự động")
    readonly property color statusColor: status === "done" ? Theme.success : status === "failed" || status === "cancelled" ? Theme.danger : status === "processing" ? Theme.warning : status === "awaiting_review" || status === "manual_ready" ? Theme.interactive : Theme.textMuted

    height: Math.round(width * 0.56 + 70)
    padding: 0
    background: Rectangle {
        id: cardBg
        objectName: "projectCardBackground"
        radius: Theme.radius
        color: "transparent"
        clip: true
        border.width: 1.5
        border.color: "#FFFFFF"
        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: hoverHandler.hovered ? "#58FFFFFF" : "#33FFFFFF"
            }
            GradientStop {
                position: 0.5
                color: hoverHandler.hovered ? "#22FFFFFF" : "#12FFFFFF"
            }
            GradientStop {
                position: 1.0
                color: hoverHandler.hovered ? "#44FFFFFF" : "#26FFFFFF"
            }
        }

        // Diagonal specular light sweep across project card on hover
        Rectangle {
            id: cardShimmer
            y: -parent.height * 0.25
            x: -width * 1.5
            width: Math.max(48, parent.width * 0.35)
            height: parent.height * 1.6
            rotation: 22
            opacity: 0
            visible: opacity > 0.01
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#00FFFFFF" }
                GradientStop { position: 0.5; color: "#B0FFFFFF" }
                GradientStop { position: 1.0; color: "#00FFFFFF" }
            }

            ParallelAnimation {
                id: cardShimmerAnim
                NumberAnimation { target: cardShimmer; property: "x"; from: -cardShimmer.width * 1.4; to: cardBg.width + cardShimmer.width; duration: 620; easing.type: Easing.OutCubic }
                SequentialAnimation {
                    NumberAnimation { target: cardShimmer; property: "opacity"; from: 0.0; to: 0.85; duration: 160 }
                    NumberAnimation { target: cardShimmer; property: "opacity"; from: 0.85; to: 0.0; duration: 460 }
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: Theme.radius
            color: "transparent"
            border.width: root.visualFocus ? 2 : 1
            border.color: root.visualFocus ? "#09090B"
                : hoverHandler.hovered ? "#45000000" : "#24000000"
        }
    }
    focusPolicy: Qt.TabFocus
    Accessible.role: Accessible.Button
    Accessible.name: projectName
    scale: tapHandler.pressed ? 0.96 : hoverHandler.hovered ? 1.026 : 1.0

    transform: Translate {
        y: tapHandler.pressed ? 1 : hoverHandler.hovered ? -5 : 0
        Behavior on y {
            NumberAnimation { duration: 300; easing.type: Easing.OutBack; easing.overshoot: 1.8 }
        }
    }

    Behavior on scale {
        NumberAnimation { duration: 300; easing.type: Easing.OutBack; easing.overshoot: 1.9 }
    }

    Connections {
        target: hoverHandler
        function onHoveredChanged() {
            if (hoverHandler.hovered && Theme.motionEnabled) {
                cardShimmerAnim.restart();
            }
        }
    }

    function resetFocusState() {
        root.focus = false;
        projectContextMenu.close();
    }

    Keys.onReturnPressed: root.activated()
    Keys.onSpacePressed: root.activated()

    HoverHandler {
        id: hoverHandler
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        id: tapHandler

        acceptedButtons: Qt.LeftButton
        onTapped: {
            root.focus = false;
            root.forceActiveFocus(Qt.MouseFocusReason);
            root.activated();
        }
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: function (eventPoint) {
            root.focus = false;
            root.forceActiveFocus(Qt.MouseFocusReason);
            const position = root.mapToItem(Overlay.overlay, eventPoint.position.x, eventPoint.position.y);
            projectContextMenu.x = Math.round(position.x);
            projectContextMenu.y = Math.round(position.y);
            projectContextMenu.open();
        }
    }

    Menu {
        id: projectContextMenu
        objectName: "projectContextMenu"

        parent: Overlay.overlay
        width: 224
        padding: 6
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        onAboutToShow: root.menuProjectKey = root.projectKey

        background: Rectangle {
            radius: 20
            border.width: 1.5
            border.color: "#FFFFFF"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FAFFFFFF" }
                GradientStop { position: 1.0; color: "#F2F3F5FA" }
            }
            Rectangle {
                anchors.fill: parent
                radius: 20
                color: "transparent"
                border.width: 1
                border.color: "#22000000"
            }
        }

        AppMenuItem {
            text: qsTr("Mở dự án")
            iconGlyph: "\uE8A7"
            onTriggered: root.openRequested()
        }

        AppMenuItem {
            text: qsTr("Mở thư mục dự án")
            iconGlyph: "\uE8B7"
            onTriggered: root.projectFolderRequested()
        }

        MenuSeparator {}

        AppMenuItem {
            text: qsTr("Đổi tên")
            iconGlyph: IconCatalog.glyph("edit")
            onTriggered: root.renameRequested(root.menuProjectKey)
        }

        AppMenuItem {
            text: qsTr("Xóa dự án")
            iconGlyph: "\uE74D"
            tone: "danger"
            onTriggered: root.deleteRequested()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.round(root.width * 0.56)
            Layout.topMargin: 6
            Layout.leftMargin: 6
            Layout.rightMargin: 6
            radius: 19
            color: "transparent"
            clip: true

            MediaThumbnail {
                anchors.fill: parent
                source: root.thumbnailSource
                fallbackIcon: root.projectType === "download" ? "download"
                    : root.projectType === "publish" ? "share" : "video"
            }

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.margins: 10
                visible: true
                implicitWidth: batchLabel.implicitWidth + 16
                implicitHeight: 24
                radius: 12
                color: "#55FFFFFF"
                border.width: 1
                border.color: "#FFFFFF"

                Text {
                    id: batchLabel
                    anchors.centerIn: parent
                    text: root.typeLabel
                    color: "#09090B"
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    textFormat: Text.PlainText
                }
            }

            Rectangle {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 10
                visible: (root.projectType === "single" || root.projectType === "manual") && root.videoSize.length > 0
                implicitWidth: sizeLabel.implicitWidth + 14
                implicitHeight: 24
                radius: 12
                color: "#55FFFFFF"
                border.width: 1
                border.color: "#FFFFFF"

                Text {
                    id: sizeLabel
                    anchors.centerIn: parent
                    text: root.videoSize
                    color: "#09090B"
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    textFormat: Text.PlainText
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 3
                visible: root.status === "processing" && root.projectType !== "download" && root.projectType !== "publish"
                color: Theme.surfaceStrong

                Rectangle {
                    width: parent.width * Math.max(0, Math.min(100, root.progress)) / 100
                    height: parent.height
                    color: root.progress >= 100 ? Theme.success : Theme.interactive
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 14
            Layout.rightMargin: 14
            Layout.topMargin: 12
            Layout.bottomMargin: 12
            spacing: 4

            Text {
                Layout.fillWidth: true
                text: root.projectName
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.bodyLarge
                font.weight: Font.Medium
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                Rectangle {
                    width: 6
                    height: 6
                    radius: 3
                    color: root.statusColor
                    visible: root.projectType !== "batch" && root.projectType !== "publish"
                }

                Text {
                    Layout.fillWidth: true
                    text: root.projectType === "batch"
                        ? qsTr("%1 video").arg(root.videoCount)
                        : root.projectType === "publish"
                            ? qsTr("%1 bài đăng").arg(root.videoCount)
                            : root.statusLabel
                    color: root.status === "failed" ? Theme.danger : Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.label
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                }

                Text {
                    visible: root.status === "processing" && root.projectType !== "download" && root.projectType !== "publish"
                    text: qsTr("%1%").arg(root.progress)
                    color: root.statusColor
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.label
                    font.weight: Font.Medium
                    textFormat: Text.PlainText
                }
            }
        }
    }
}
