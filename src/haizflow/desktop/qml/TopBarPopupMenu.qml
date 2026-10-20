import QtQuick
import QtQuick.Controls.Basic
import "."

Menu {
    id: root

    property real menuContentWidth: 0

    width: Math.min(menuContentWidth + padding * 2, 220)
    modal: false
    padding: 6
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnReleaseOutside

    background: Rectangle {
        radius: 20
        border.width: 1.5
        border.color: "#FFFFFF"
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#FAFFFFFF" }
            GradientStop { position: 1.0; color: "#F2F4F6FA" }
        }
        Rectangle {
            anchors.fill: parent
            radius: 20
            color: "transparent"
            border.width: 1
            border.color: "#22000000"
        }
    }
}
