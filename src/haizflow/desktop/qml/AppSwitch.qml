import QtQuick
import QtQuick.Controls.Basic
import "."

Switch {
    id: root

    spacing: Theme.space8
    font.family: Theme.fontFamily
    font.pixelSize: TypeScale.control
    focusPolicy: Qt.TabFocus
    Accessible.name: text

    indicator: Rectangle {
        implicitWidth: 44
        implicitHeight: 24
        radius: 12
        color: root.checked ? "#09090B" : "#DCE0EC"
        border.width: 1
        border.color: root.visualFocus ? "#09090B" : "#22000000"

        Behavior on color { ColorAnimation { duration: 200 } }

        Rectangle {
            id: switchDroplet
            x: root.checked ? parent.width - width - 3 : 3
            anchors.verticalCenter: parent.verticalCenter
            width: switchXAnim.running || root.down ? 22 : 18
            height: 18
            radius: 9
            border.width: 1
            border.color: "#FFFFFF"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FFFFFF" }
                GradientStop { position: 1.0; color: "#E6E9F2" }
            }

            Behavior on x {
                NumberAnimation {
                    id: switchXAnim
                    duration: 280
                    easing.type: Easing.OutBack
                    easing.overshoot: 0.8
                }
            }
            Behavior on width {
                NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
            }
        }
    }

    contentItem: Text {
        leftPadding: root.indicator.width + root.spacing
        text: root.text
        color: root.enabled ? Theme.text : Theme.textDisabled
        font: root.font
        verticalAlignment: Text.AlignVCenter
        textFormat: Text.PlainText
    }
}
