import QtQuick
import QtQuick.Layouts
import "."

// Label and live value on one line, full-width slider underneath.
ColumnLayout {
    id: root

    property string label: ""
    property real value: 0
    property real from: 0
    property real to: 100
    property string suffix: "%"
    property alias sliderObjectName: slider.objectName
    signal moved(int value)

    Layout.fillWidth: true
    spacing: 0

    RowLayout {
        Layout.fillWidth: true
        Text {
            Layout.fillWidth: true
            text: root.label
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.caption
            elide: Text.ElideRight
            textFormat: Text.PlainText
        }
        Text {
            text: Math.round(root.value) + root.suffix
            color: root.enabled ? Theme.text : Theme.textDisabled
            font.family: Theme.fontFamily
            font.pixelSize: Theme.caption
            font.weight: Font.Medium
            textFormat: Text.PlainText
        }
    }

    AppSlider {
        id: slider
        Layout.fillWidth: true
        from: root.from
        to: root.to
        stepSize: 1
        value: root.value
        onMoved: root.moved(Math.round(value))
    }
}
