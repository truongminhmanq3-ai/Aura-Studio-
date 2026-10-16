pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

Rectangle {
    id: root

    property bool compact: false
    property string currentSection: "home"
    signal sectionRequested(string section)

    implicitWidth: compact ? UiMetrics.navigationCompact : UiMetrics.navigationExpanded
    radius: 28
    color: "transparent"
    border.width: 1.5
    border.color: "#E6FFFFFF"
    clip: true

    readonly property var navItemsModel: [
        { key: "home", label: qsTr("Trang chủ"), icon: "home" },
        { key: "single", label: qsTr("Tự động"), icon: "play" },
        { key: "manual", label: qsTr("Thủ công"), icon: "edit" },
        { key: "batch", label: qsTr("Hàng loạt"), icon: "projects" },
        { key: "downloads", label: qsTr("Tải xuống"), icon: "download" },
        { key: "social", label: qsTr("Đăng mạng xã hội"), icon: "share" }
    ]

    readonly property int selectedNavIndex: {
        for (let i = 0; i < navItemsModel.length; ++i) {
            if (navItemsModel[i].key === root.currentSection)
                return i;
        }
        return -1;
    }

    property bool dropletDragging: false
    property real dragDropletY: 0
    property real pressStartY: 0

    readonly property real targetDropletY: {
        if (dropletDragging)
            return dragDropletY;
        if (selectedNavIndex >= 0)
            return selectedNavIndex * 44;
        return 0;
    }

    // Outer subtle glass refraction hairline
    Rectangle {
        anchors.fill: parent
        radius: 28
        color: "transparent"
        border.width: 1
        border.color: "#22000000"
        z: 10
    }

    // Crystal-clear transparent Liquid Glass sidebar body
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#30FFFFFF" }
        GradientStop { position: 0.5; color: "#14FFFFFF" }
        GradientStop { position: 1.0; color: "#28FFFFFF" }
    }

    // Top specular water-droplet highlight rim
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 22
        anchors.rightMargin: 22
        height: 1.5
        radius: 1
        color: "#FFFFFF"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        anchors.topMargin: 18
        anchors.bottomMargin: 16
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            Layout.leftMargin: root.compact ? 0 : 6
            Layout.bottomMargin: 10
            spacing: 10

            Image {
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                Layout.alignment: root.compact ? Qt.AlignHCenter : Qt.AlignVCenter
                source: Qt.resolvedUrl("../assets/branding/haizflow-mark.png")
                sourceSize.width: 64
                sourceSize.height: 64
                fillMode: Image.PreserveAspectFit
                asynchronous: true
            }

            RowLayout {
                Layout.fillWidth: true
                visible: !root.compact
                spacing: 6
                Text {
                    text: "Aura"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: 18
                    font.weight: Font.Bold
                    font.letterSpacing: -0.3
                    textFormat: Text.PlainText
                }
                Text {
                    text: "Studio"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: 18
                    font.weight: Font.Light
                    font.letterSpacing: -0.2
                    textFormat: Text.PlainText
                }
            }
        }

        Text {
            visible: !root.compact
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.bottomMargin: 4
            text: qsTr("KHÔNG GIAN")
            color: Theme.textSubtle
            font.family: Theme.fontFamily
            font.pixelSize: 10
            font.weight: Font.DemiBold
            font.letterSpacing: 1.0
            textFormat: Text.PlainText
        }

        // Draggable Transparent Water-Droplet Navigation Container
        Item {
            id: navTrack
            Layout.fillWidth: true
            Layout.preferredHeight: root.navItemsModel.length * 44 - 6

            // Clear Transparent Water Droplet with Liquid Splash & Ripple Wave
            Rectangle {
                id: waterDroplet
                x: 0
                y: root.targetDropletY
                width: navTrack.width
                height: 38
                radius: height / 2
                visible: root.selectedNavIndex >= 0 || root.dropletDragging
                color: "transparent"
                border.width: 1.5
                border.color: "#FFFFFF"

                transform: Scale {
                    id: dropletScale
                    origin.x: waterDroplet.width / 2
                    origin.y: waterDroplet.height / 2
                    xScale: root.dropletDragging ? 0.96 : 1.0
                    yScale: root.dropletDragging ? 1.12 : 1.0
                }

                // Expanding concentric water ripple ring on click/release
                Rectangle {
                    id: dropletRippleRing
                    anchors.centerIn: parent
                    width: parent.width
                    height: parent.height
                    radius: height / 2
                    color: "transparent"
                    border.width: 1.5
                    border.color: "#8009090B"
                    opacity: 0
                    scale: 1.0
                    visible: opacity > 0.01
                }

                ParallelAnimation {
                    id: dropletSplashAnim
                    SequentialAnimation {
                        NumberAnimation { target: dropletScale; property: "xScale"; from: 0.88; to: 1.06; duration: 150; easing.type: Easing.OutQuad }
                        NumberAnimation { target: dropletScale; property: "xScale"; from: 1.06; to: 1.0; duration: 340; easing.type: Easing.OutElastic; easing.amplitude: 1.2; easing.period: 0.4 }
                    }
                    SequentialAnimation {
                        NumberAnimation { target: dropletScale; property: "yScale"; from: 1.24; to: 0.92; duration: 150; easing.type: Easing.OutQuad }
                        NumberAnimation { target: dropletScale; property: "yScale"; from: 0.92; to: 1.0; duration: 340; easing.type: Easing.OutElastic; easing.amplitude: 1.2; easing.period: 0.4 }
                    }
                    NumberAnimation { target: dropletRippleRing; property: "scale"; from: 0.85; to: 1.28; duration: 460; easing.type: Easing.OutExpo }
                    NumberAnimation { target: dropletRippleRing; property: "opacity"; from: 0.55; to: 0.0; duration: 460; easing.type: Easing.OutCubic }
                }

                // Crystal-clear water droplet refraction (trong suốt như giọt nước thật)
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#58FFFFFF" }
                    GradientStop { position: 0.45; color: "#16FFFFFF" }
                    GradientStop { position: 1.0; color: "#44FFFFFF" }
                }

                // Outer meniscus hairline
                Rectangle {
                    anchors.fill: parent
                    radius: height / 2
                    color: "transparent"
                    border.width: 1
                    border.color: "#2E000000"
                }

                // Top water droplet glossy reflection arc
                Rectangle {
                    anchors.top: parent.top
                    anchors.topMargin: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    height: 8
                    radius: 4
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#C8FFFFFF" }
                        GradientStop { position: 1.0; color: "#00FFFFFF" }
                    }
                }
            }

            Column {
                anchors.fill: parent
                spacing: 6

                Repeater {
                    model: root.navItemsModel

                    delegate: Control {
                        id: navItem
                        objectName: "workspaceNav_" + modelData.key
                        required property var modelData
                        required property int index
                        readonly property bool isSelected: root.currentSection === navItem.modelData.key
                        readonly property bool isHighlighted: root.dropletDragging
                            ? (Math.round(root.dragDropletY / 44) === index)
                            : isSelected
                        width: navTrack.width
                        height: 38
                        focusPolicy: Qt.TabFocus
                        padding: 0
                        background: Item {}
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData.label

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: root.compact ? 0 : 14
                            anchors.rightMargin: root.compact ? 0 : 14
                            spacing: 11

                            FluentIcon {
                                Layout.preferredWidth: root.compact ? parent.width : 18
                                Layout.preferredHeight: 18
                                name: navItem.modelData.icon
                                iconColor: navItem.isHighlighted ? Theme.interactive : Theme.textMuted
                                iconSize: 16
                                scale: navItem.isHighlighted ? 1.18 : 1.0
                                Behavior on scale {
                                    NumberAnimation { duration: 320; easing.type: Easing.OutBack; easing.overshoot: 2.4 }
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: !root.compact
                                text: navItem.modelData.label
                                color: navItem.isHighlighted ? Theme.text : Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: TypeScale.control
                                font.weight: navItem.isHighlighted ? Font.DemiBold : Font.Normal
                                textFormat: Text.PlainText
                                elide: Text.ElideRight
                            }
                        }

                        Keys.onReturnPressed: root.sectionRequested(navItem.modelData.key)
                        Keys.onSpacePressed: root.sectionRequested(navItem.modelData.key)
                    }
                }
            }

            // Click bình thường chọn ngay kèm hiệu ứng giọt nước nảy đàn hồi; nhấn giữ và kéo thì trượt giọt nước theo tay
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                cursorShape: root.dropletDragging ? Qt.ClosedHandCursor : Qt.PointingHandCursor
                onPressed: function(mouse) {
                    root.pressStartY = mouse.y;
                    root.dropletDragging = false;
                }
                onPositionChanged: function(mouse) {
                    if (pressed && Math.abs(mouse.y - root.pressStartY) > 4) {
                        const maxY = (root.navItemsModel.length - 1) * 44;
                        root.dropletDragging = true;
                        root.dragDropletY = Math.max(0, Math.min(maxY, mouse.y - 19));
                    }
                }
                onReleased: function(mouse) {
                    root.dropletDragging = false;
                    const idx = Math.max(0, Math.min(root.navItemsModel.length - 1, Math.round((mouse.y - 19) / 44)));
                    root.sectionRequested(root.navItemsModel[idx].key);
                    if (Theme.motionEnabled) {
                        dropletSplashAnim.restart();
                    }
                }
                onCanceled: {
                    root.dropletDragging = false;
                }
            }
        }

        Item { Layout.fillHeight: true }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.leftMargin: 10
            Layout.rightMargin: 10
            Layout.bottomMargin: 4
            color: "#18000000"
        }

        Control {
            id: settingsNavItem
            objectName: "workspaceNav_settings"
            readonly property bool isSelected: root.currentSection === "settings"
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            focusPolicy: Qt.TabFocus
            padding: 0
            background: Rectangle {
                radius: 19
                visible: settingsNavItem.isSelected || settingsHover.hovered
                color: "transparent"
                border.width: 1.5
                border.color: "#FFFFFF"
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#45FFFFFF" }
                    GradientStop { position: 0.5; color: "#12FFFFFF" }
                    GradientStop { position: 1.0; color: "#36FFFFFF" }
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 19
                    color: "transparent"
                    border.width: 1
                    border.color: "#28000000"
                }
            }
            Accessible.role: Accessible.Button
            Accessible.name: qsTr("Cài đặt")

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: root.compact ? 0 : 14
                anchors.rightMargin: root.compact ? 0 : 14
                spacing: 11

                FluentIcon {
                    Layout.preferredWidth: root.compact ? parent.width : 18
                    Layout.preferredHeight: 18
                    name: "settings"
                    iconColor: settingsNavItem.isSelected || settingsHover.hovered ? Theme.interactive : Theme.textMuted
                    iconSize: 16
                }
                Text {
                    Layout.fillWidth: true
                    visible: !root.compact
                    text: qsTr("Cài đặt")
                    color: settingsNavItem.isSelected || settingsHover.hovered ? Theme.text : Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: TypeScale.control
                    font.weight: settingsNavItem.isSelected ? Font.DemiBold : Font.Normal
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                }
            }

            HoverHandler { id: settingsHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: {
                    settingsNavItem.focus = false;
                    settingsNavItem.forceActiveFocus(Qt.MouseFocusReason);
                    root.sectionRequested("settings");
                }
            }
            Keys.onReturnPressed: root.sectionRequested("settings")
            Keys.onSpacePressed: root.sectionRequested("settings")
        }
    }
}
