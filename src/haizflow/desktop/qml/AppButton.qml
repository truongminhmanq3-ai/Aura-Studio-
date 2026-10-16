import QtQuick
import QtQuick.Controls.Basic
import "."

Button {
    id: root

    property string tone: "secondary"
    property bool compact: false
    property string iconGlyph: ""
    property string toolTipText: ""
    property bool showToolTip: false
    readonly property bool showLeadingIcon: iconGlyph.length > 0

    implicitHeight: compact ? UiMetrics.compactControlHeight : tone === "primary" ? UiMetrics.primaryControlHeight : UiMetrics.controlHeight
    implicitWidth: Math.max(compact ? 68 : 84, buttonContent.implicitWidth + leftPadding + rightPadding)
    leftPadding: compact ? 15 : 18
    rightPadding: compact ? 15 : 18
    font.family: Theme.fontFamily
    font.pixelSize: TypeScale.control
    font.weight: tone === "primary" ? Font.DemiBold : Font.Medium
    focusPolicy: Qt.TabFocus
    Accessible.name: text.length > 0 ? text : toolTipText
    Accessible.description: toolTipText
    scale: down ? 0.92 : hovered ? 1.035 : 1.0

    onPressed: {
        if (Theme.motionEnabled) {
            rippleAnim.restart();
            shimmerAnim.restart();
        }
    }

    onHoveredChanged: {
        if (hovered && Theme.motionEnabled) {
            shimmerAnim.restart();
        }
    }

    readonly property color foregroundColor: !enabled ? Theme.textDisabled : tone === "danger" ? Theme.danger : Theme.text

    contentItem: Item {
        implicitWidth: buttonContent.implicitWidth
        implicitHeight: Math.max(buttonContent.implicitHeight, Theme.icon)

        Row {
            id: buttonContent
            anchors.centerIn: parent
            spacing: root.showLeadingIcon && root.text.length > 0 ? 6 : 0

            AppIcon {
                objectName: "buttonLeadingIcon"
                width: root.showLeadingIcon ? (root.compact ? Theme.iconSmall : Theme.icon) : 0
                height: parent.height
                visible: root.showLeadingIcon
                glyph: root.iconGlyph
                iconColor: root.foregroundColor
                iconSize: root.compact ? 12 : Theme.iconSmall
                scale: root.down ? 0.88 : root.hovered ? 1.14 : 1.0
                Behavior on scale {
                    NumberAnimation { duration: 240; easing.type: Easing.OutBack; easing.overshoot: 2.0 }
                }
            }

            Text {
                height: Math.max(20, implicitHeight)
                text: root.text
                color: root.foregroundColor
                font: root.font
                verticalAlignment: Text.AlignVCenter
                textFormat: Text.PlainText
                elide: Text.ElideNone
            }
        }
    }

    background: Rectangle {
        id: buttonBackground
        radius: Math.round(root.height / 2)
        color: "transparent"
        clip: true
        border.width: root.visualFocus ? 2 : (root.tone === "ghost" && !root.hovered && !root.down ? 0 : 1.5)
        border.color: "#FFFFFF"
        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: !root.enabled ? "#18FFFFFF"
                    : root.tone === "ghost" && !root.hovered && !root.down ? "transparent"
                    : (root.down ? "#66FFFFFF" : root.hovered ? "#54FFFFFF" : "#38FFFFFF")
            }
            GradientStop {
                position: 0.5
                color: !root.enabled ? "#08FFFFFF"
                    : root.tone === "ghost" && !root.hovered && !root.down ? "transparent"
                    : (root.down ? "#2EFFFFFF" : root.hovered ? "#20FFFFFF" : "#0DFFFFFF")
            }
            GradientStop {
                position: 1.0
                color: !root.enabled ? "#14FFFFFF"
                    : root.tone === "ghost" && !root.hovered && !root.down ? "transparent"
                    : (root.down ? "#52FFFFFF" : root.hovered ? "#44FFFFFF" : "#2DFFFFFF")
            }
        }

        // Expanding Liquid Ripple Wave on Click
        Rectangle {
            id: clickRipple
            anchors.centerIn: parent
            width: 0
            height: width
            radius: width / 2
            color: "#38FFFFFF"
            border.width: 1.5
            border.color: "#B0FFFFFF"
            opacity: 0
            visible: opacity > 0.01

            ParallelAnimation {
                id: rippleAnim
                NumberAnimation {
                    target: clickRipple
                    property: "width"
                    from: 10
                    to: Math.max(buttonBackground.width, buttonBackground.height) * 2.2
                    duration: 480
                    easing.type: Easing.OutExpo
                }
                NumberAnimation {
                    target: clickRipple
                    property: "opacity"
                    from: 0.85
                    to: 0.0
                    duration: 480
                    easing.type: Easing.OutCubic
                }
            }
        }

        // Specular Light Sweep Shimmer across glass button
        Rectangle {
            id: shimmerBar
            y: -parent.height * 0.25
            x: -width * 1.5
            width: Math.max(28, parent.width * 0.38)
            height: parent.height * 1.5
            rotation: 22
            opacity: 0
            visible: opacity > 0.01
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#00FFFFFF" }
                GradientStop { position: 0.5; color: "#B8FFFFFF" }
                GradientStop { position: 1.0; color: "#00FFFFFF" }
            }

            ParallelAnimation {
                id: shimmerAnim
                NumberAnimation {
                    target: shimmerBar
                    property: "x"
                    from: -shimmerBar.width * 1.4
                    to: buttonBackground.width + shimmerBar.width
                    duration: 520
                    easing.type: Easing.OutCubic
                }
                SequentialAnimation {
                    NumberAnimation { target: shimmerBar; property: "opacity"; from: 0.0; to: 0.9; duration: 140 }
                    NumberAnimation { target: shimmerBar; property: "opacity"; from: 0.9; to: 0.0; duration: 380 }
                }
            }
        }

        // Top water-droplet gloss arc
        Rectangle {
            anchors.top: parent.top
            anchors.topMargin: 2
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            height: 7
            radius: 3.5
            visible: root.tone === "primary" || root.tone === "secondary"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#B8FFFFFF" }
                GradientStop { position: 1.0; color: "#00FFFFFF" }
            }
        }

        // Crisp outer water-droplet meniscus contour
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            visible: root.tone !== "ghost" || root.hovered || root.down
            border.width: root.tone === "primary" ? 1.2 : 1
            border.color: root.tone === "danger" ? Theme.danger
                : root.tone === "primary" ? "#6609090B" : "#28000000"
        }
    }

    Behavior on scale {
        NumberAnimation {
            duration: 280
            easing.type: Easing.OutBack
            easing.overshoot: 2.2
        }
    }

    ToolTip.visible: root.showToolTip && hovered && !down && toolTipText.length > 0
    ToolTip.text: toolTipText
    ToolTip.delay: 500
}
