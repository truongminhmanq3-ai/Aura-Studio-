import QtQuick
import QtQuick.Controls.Basic
import "."

Button {
    id: root

    property bool menuWasOpenOnPress: false

    implicitHeight: 28
    leftPadding: 12
    rightPadding: 12
    topPadding: 0
    bottomPadding: 0
    focusPolicy: Qt.TabFocus
    Accessible.name: text

    scale: down ? 0.90 : hovered ? 1.05 : 1.0

    Behavior on scale {
        NumberAnimation { duration: 260; easing.type: Easing.OutBack; easing.overshoot: 2.3 }
    }

    onPressed: {
        if (Theme.motionEnabled) {
            topRippleAnim.restart();
        }
    }

    contentItem: Text {
        text: root.text
        color: root.enabled
            ? (root.hovered || root.down ? Theme.text : Theme.textMuted)
            : Theme.textDisabled
        font.family: Theme.fontFamily
        font.pixelSize: Theme.caption
        font.weight: Font.Medium
        verticalAlignment: Text.AlignVCenter
        textFormat: Text.PlainText
    }

    background: Rectangle {
        id: topBtnBg
        radius: 14
        visible: root.down || root.hovered || root.visualFocus || topRipple.opacity > 0.01
        color: "transparent"
        clip: true
        border.width: 1
        border.color: "#28000000"
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#4DFFFFFF" }
            GradientStop { position: 0.5; color: "#14FFFFFF" }
            GradientStop { position: 1.0; color: "#3DFFFFFF" }
        }

        Rectangle {
            id: topRipple
            anchors.centerIn: parent
            width: 0
            height: width
            radius: width / 2
            color: "#38FFFFFF"
            border.width: 1.5
            border.color: "#B8FFFFFF"
            opacity: 0

            ParallelAnimation {
                id: topRippleAnim
                NumberAnimation { target: topRipple; property: "width"; from: 8; to: topBtnBg.width * 2.2; duration: 420; easing.type: Easing.OutExpo }
                NumberAnimation { target: topRipple; property: "opacity"; from: 0.85; to: 0.0; duration: 420; easing.type: Easing.OutCubic }
            }
        }
    }
}
