pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

Rectangle {
    id: root

    signal newSingleProjectRequested
    signal manualProjectRequested
    signal newBatchProjectRequested
    signal newDownloadProjectRequested
    signal newPublishProjectRequested
    signal settingsRequested
    signal apiKeysRequested
    signal packagesRequested
    signal undoRequested
    signal redoRequested
    signal aboutRequested
    signal copyrightRequested
    signal backRequested
    signal forwardRequested
    signal homeRequested

    property bool canGoBack: false
    property bool canGoForward: false
    property bool editAvailable: false
    property bool canUndo: false
    property bool canRedo: false
    property var updateController: AppController
    property bool helpWasOpenOnPress: false

    implicitHeight: UiMetrics.toolbarHeight
    radius: 21
    color: "transparent"
    border.width: 1.5
    border.color: "#E6FFFFFF"

    Rectangle {
        anchors.fill: parent
        radius: 21
        color: "transparent"
        border.width: 1
        border.color: "#22000000"
        z: 10
    }

    // Crystal-clear transparent Liquid Glass toolbar
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#30FFFFFF" }
        GradientStop { position: 0.5; color: "#14FFFFFF" }
        GradientStop { position: 1.0; color: "#28FFFFFF" }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 6

        TopBarNavigationButton {
            objectName: "homeNavigationButton"
            glyph: "\uE80F"
            toolTipText: qsTr("Trang chủ")
            onClicked: root.homeRequested()
        }

        Rectangle {
            Layout.preferredWidth: 1
            Layout.preferredHeight: 14
            Layout.leftMargin: 2
            Layout.rightMargin: 2
            color: "#18000000"
        }

        TopBarNavigationButton {
            objectName: "backNavigationButton"
            glyph: "\uE72B"
            toolTipText: qsTr("Quay lại")
            enabled: root.canGoBack
            onClicked: root.backRequested()
        }

        TopBarNavigationButton {
            objectName: "forwardNavigationButton"
            glyph: "\uE72A"
            toolTipText: qsTr("Tiến")
            enabled: root.canGoForward
            onClicked: root.forwardRequested()
        }

        Item {
            Layout.preferredWidth: Theme.space4
        }

        TopBarMenuButton {
            id: projectButton

            objectName: "projectMenuButton"
            text: qsTr("Dự án")
            onPressed: menuWasOpenOnPress = projectMenu.visible
            onClicked: root.toggleMenu(projectMenu, projectButton, menuWasOpenOnPress)
        }

        TopBarMenuButton {
            id: editButton

            objectName: "editMenuButton"
            text: qsTr("Chỉnh sửa")
            enabled: root.editAvailable
            onPressed: menuWasOpenOnPress = editMenu.visible
            onClicked: root.toggleMenu(editMenu, editButton, menuWasOpenOnPress)
        }

        TopBarMenuButton {
            id: settingsButton

            objectName: "settingsMenuButton"
            text: qsTr("Cài đặt")
            onPressed: menuWasOpenOnPress = settingsMenu.visible
            onClicked: root.toggleMenu(settingsMenu, settingsButton, menuWasOpenOnPress)
        }

        Item {
            Layout.fillWidth: true
        }

        // Minimalist Apple User Avatar Pill on Top Right
        Rectangle {
            Layout.preferredHeight: 30
            Layout.preferredWidth: avatarRow.implicitWidth + 14
            radius: 15
            color: "transparent"
            border.width: 1
            border.color: "#22000000"

            gradient: Gradient {
                GradientStop { position: 0.0; color: "#38FFFFFF" }
                GradientStop { position: 1.0; color: "#14FFFFFF" }
            }

            RowLayout {
                id: avatarRow
                anchors.centerIn: parent
                spacing: 6

                Image {
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                    source: Qt.resolvedUrl("../assets/branding/apple-avatar.png")
                    sourceSize.width: 40
                    sourceSize.height: 40
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                }

                Text {
                    text: "Studio"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    textFormat: Text.PlainText
                }
            }
        }
    }

    function toggleMenu(menu, anchorButton, wasOpenOnPress) {
        if (wasOpenOnPress || menu.visible) {
            menu.close();
            return;
        }

        projectMenu.close();
        editMenu.close();
        settingsMenu.close();
        const anchorPosition = anchorButton.mapToItem(Overlay.overlay, 0, 0);
        const barBottom = root.mapToItem(Overlay.overlay, 0, root.height);
        menu.x = Math.round(Math.max(Theme.space8, Math.min(anchorPosition.x,
            Overlay.overlay.width - menu.width - Theme.space8)));
        menu.y = Math.round(barBottom.y + Theme.space4);
        menu.open();
    }

    TopBarPopupMenu {
        id: editMenu

        objectName: "editMenuPopup"
        parent: Overlay.overlay
        menuContentWidth: Math.max(undoItem.implicitWidth, redoItem.implicitWidth)

        AppMenuItem {
            id: undoItem

            text: qsTr("Hoàn tác")
            enabled: root.canUndo
            onTriggered: root.undoRequested()
        }

        AppMenuItem {
            id: redoItem

            text: qsTr("Làm lại")
            enabled: root.canRedo
            onTriggered: root.redoRequested()
        }
    }

    TopBarPopupMenu {
        id: projectMenu

        objectName: "projectMenuPopup"
        parent: Overlay.overlay
        menuContentWidth: Math.max(
            newSingleProjectItem.implicitWidth,
            newManualProjectItem.implicitWidth,
            newBatchProjectItem.implicitWidth,
            newDownloadProjectItem.implicitWidth,
            newPublishProjectItem.implicitWidth)

        AppMenuItem {
            id: newSingleProjectItem

            text: qsTr("Dự án Tự động mới")
            onTriggered: root.newSingleProjectRequested()
        }

        AppMenuItem {
            id: newManualProjectItem

            text: qsTr("Dự án Thủ công mới")
            onTriggered: root.manualProjectRequested()
        }

        AppMenuItem {
            id: newBatchProjectItem

            text: qsTr("Dự án Hàng loạt mới")
            onTriggered: root.newBatchProjectRequested()
        }

        MenuSeparator {}

        AppMenuItem {
            id: newDownloadProjectItem

            text: qsTr("Dự án Tải xuống mới")
            onTriggered: root.newDownloadProjectRequested()
        }

        AppMenuItem {
            id: newPublishProjectItem

            text: qsTr("Dự án Đăng mạng xã hội mới")
            onTriggered: root.newPublishProjectRequested()
        }
    }

    TopBarPopupMenu {
        id: settingsMenu

        objectName: "settingsMenuPopup"
        parent: Overlay.overlay
        menuContentWidth: Math.max(
            settingsItem.implicitWidth,
            apiKeysItem.implicitWidth,
            packagesItem.implicitWidth)

        AppMenuItem {
            id: settingsItem

            text: qsTr("Cài đặt")
            onTriggered: root.settingsRequested()
        }

        AppMenuItem {
            id: apiKeysItem

            text: qsTr("API Key")
            onTriggered: root.apiKeysRequested()
        }

        AppMenuItem {
            id: packagesItem

            text: qsTr("Gói tài nguyên")
            onTriggered: root.packagesRequested()
        }
    }
}
