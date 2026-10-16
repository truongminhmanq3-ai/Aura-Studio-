import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import Qt.labs.platform as Platform
import "."

Item {
    id: root

    property Window hostWindow: null
    property string currentTitle: "Aura Studio"
    property string currentMessage: ""

    function notify(title, message) {
        currentTitle = title && title.length > 0 ? title : "Aura Studio";
        currentMessage = message || "";

        // 1. Trigger native OS notification center via Qt Platform SystemTrayIcon
        if (osTray.available) {
            if (!osTray.visible)
                osTray.visible = true;
            osTray.showMessage(currentTitle, currentMessage, Platform.SystemTrayIcon.Information, 6000);
        }

        // 2. Bounce macOS Dock icon / flash taskbar if app is in background
        if (hostWindow && !hostWindow.active) {
            hostWindow.alert(0);
        }

        // 3. Show guaranteed OS-level Top-Right macOS Notification Banner Window over any desktop app
        bannerWindow.x = Screen.desktopAvailableWidth - bannerWindow.width - 18;
        bannerWindow.y = 42;
        bannerWindow.visible = true;
        bannerWindow.raise();
        slideInAnim.restart();
        autoHideTimer.restart();
    }

    Platform.SystemTrayIcon {
        id: osTray
        visible: false
        icon.source: Qt.resolvedUrl("../assets/branding/haizflow-mark.png")
        tooltip: "Aura Studio"
        onMessageClicked: {
            if (root.hostWindow) {
                root.hostWindow.show();
                root.hostWindow.raise();
                root.hostWindow.requestActivate();
            }
        }
    }

    Timer {
        id: autoHideTimer
        interval: 6200
        repeat: false
        onTriggered: slideOutAnim.restart()
    }

    Window {
        id: bannerWindow
        width: 368
        height: 86
        visible: false
        color: "transparent"
        flags: Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus

        Item {
            id: bannerCardWrap
            anchors.fill: parent
            anchors.margins: 4

            transform: Translate {
                id: bannerTranslate
                x: 0
            }

            ParallelAnimation {
                id: slideInAnim
                NumberAnimation {
                    target: bannerCardWrap
                    property: "opacity"
                    from: 0.0
                    to: 1.0
                    duration: 240
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    target: bannerTranslate
                    property: "x"
                    from: 80
                    to: 0
                    duration: 380
                    easing.type: Easing.OutBack
                    easing.overshoot: 1.15
                }
            }

            ParallelAnimation {
                id: slideOutAnim
                NumberAnimation {
                    target: bannerCardWrap
                    property: "opacity"
                    from: 1.0
                    to: 0.0
                    duration: 220
                    easing.type: Easing.InCubic
                }
                NumberAnimation {
                    target: bannerTranslate
                    property: "x"
                    from: 0
                    to: 60
                    duration: 220
                    easing.type: Easing.InCubic
                }
                onFinished: {
                    bannerWindow.visible = false;
                }
            }

            // macOS Sequoia style Liquid Glass Notification Banner
            Rectangle {
                anchors.fill: parent
                radius: 22
                color: "#F2FFFFFF"
                border.width: 1.5
                border.color: "#FFFFFF"

                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#FAFFFFFF" }
                    GradientStop { position: 0.5; color: "#EBFFFFFF" }
                    GradientStop { position: 1.0; color: "#F5F5F7" }
                }

                // Outer subtle dark hairline contour
                Rectangle {
                    anchors.fill: parent
                    radius: 22
                    color: "transparent"
                    border.width: 1
                    border.color: "#2E000000"
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    anchors.topMargin: 10
                    anchors.bottomMargin: 10
                    spacing: 12

                    Image {
                        Layout.preferredWidth: 42
                        Layout.preferredHeight: 42
                        Layout.alignment: Qt.AlignVCenter
                        source: Qt.resolvedUrl("../assets/branding/haizflow-mark.png")
                        sourceSize.width: 84
                        sourceSize.height: 84
                        fillMode: Image.PreserveAspectFit
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                Layout.fillWidth: true
                                text: root.currentTitle
                                color: "#1D1D1F"
                                font.family: Theme.fontFamily
                                font.pixelSize: 13
                                font.weight: Font.Bold
                                elide: Text.ElideRight
                                textFormat: Text.PlainText
                            }

                            Text {
                                text: qsTr("Bây giờ")
                                color: "#86868B"
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                textFormat: Text.PlainText
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.currentMessage
                            color: "#52525B"
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            textFormat: Text.PlainText
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        autoHideTimer.stop();
                        slideOutAnim.restart();
                        if (root.hostWindow) {
                            root.hostWindow.show();
                            root.hostWindow.raise();
                            root.hostWindow.requestActivate();
                        }
                    }
                }
            }
        }
    }
}
