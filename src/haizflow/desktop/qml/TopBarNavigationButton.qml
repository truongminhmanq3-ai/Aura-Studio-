import QtQuick
import QtQuick.Controls.Basic
import "."

Button {
    id: root

    property string glyph: ""
    property string toolTipText: ""
    property bool menuWasOpenOnPress: false

    implicitWidth: 30
    implicitHeight: 30
    leftPadding: 0
    rightPadding: 0
    topPadding: 0
    bottomPadding: 0
    focusPolicy: Qt.TabFocus
    Accessible.name: toolTipText
    ToolTip.visible: false
    ToolTip.text: toolTipText
    ToolTip.delay: 450

    scale: down ? 0.88 : (enabled && hovered) ? 1.08 : 1.0

    Behavior on scale {
        NumberAnimation { duration: 260; easing.type: Easing.OutBack; easing.overshoot: 2.3 }
    }

    onPressed: {
        if (Theme.motionEnabled) {
            navRippleAnim.restart();
        }
    }

    contentItem: AppIcon {
        glyph: root.glyph
        iconSize: 15
        iconColor: root.enabled
            ? (root.hovered || root.down ? Theme.text : Theme.textMuted)
            : Theme.textDisabled
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        id: navBtnBg
        radius: 15
        visible: root.down || (root.enabled && root.hovered) || root.visualFocus || navRipple.opacity > 0.01
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
            id: navRipple
            anchors.centerIn: parent
            width: 0
            height: width
            radius: width / 2
            color: "#38FFFFFF"
            border.width: 1.5
            border.color: "#B8FFFFFF"
            opacity: 0

            ParallelAnimation {
                id: navRippleAnim
                NumberAnimation { target: navRipple; property: "width"; from: 6; to: navBtnBg.width * 2.2; duration: 400; easing.type: Easing.OutExpo }
                NumberAnimation { target: navRipple; property: "opacity"; from: 0.85; to: 0.0; duration: 400; easing.type: Easing.OutCubic }
            }
        }
    }
}
