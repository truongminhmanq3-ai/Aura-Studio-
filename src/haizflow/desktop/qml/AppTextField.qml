import QtQuick
import QtQuick.Controls.Basic
import "."

TextField {
    id: root

    implicitHeight: UiMetrics.controlHeight
    leftPadding: 15
    rightPadding: 15
    color: Theme.text
    selectionColor: Theme.interactive
    selectedTextColor: Theme.textOnAccent
    placeholderTextColor: Theme.textSubtle
    font.family: Theme.fontFamily
    font.pixelSize: TypeScale.control
    focusPolicy: Qt.StrongFocus
    selectByMouse: true
    Accessible.name: accessibleName.length > 0 ? accessibleName : placeholderText

    property string accessibleName: ""

    background: Rectangle {
        radius: Math.round(root.height / 2)
        color: "transparent"
        border.width: 1.5
        border.color: "#FFFFFF"
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.activeFocus ? "#48FFFFFF" : "#33FFFFFF" }
            GradientStop { position: 0.5; color: root.activeFocus ? "#18FFFFFF" : "#0DFFFFFF" }
            GradientStop { position: 1.0; color: root.activeFocus ? "#38FFFFFF" : "#28FFFFFF" }
        }
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.width: root.activeFocus ? 1.5 : 1
            border.color: root.activeFocus ? "#09090B" : (root.hovered ? "#42000000" : "#26000000")
        }
    }
}
